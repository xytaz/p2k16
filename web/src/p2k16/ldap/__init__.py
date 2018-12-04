from ldaptor.entry import BaseLDAPEntry
from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap.distinguishedname import DistinguishedName, RelativeDistinguishedName
from ldaptor.protocols.ldap.distinguishedname import LDAPAttributeTypeAndValue
from twisted.internet import defer, error
from twisted.internet.defer import inlineCallbacks, returnValue
from ldaptor.protocols.ldap import distinguishedname, ldaperrors, ldifprotocol
from twisted.application import service, internet
from twisted.internet.endpoints import serverFromString
from twisted.internet.protocol import ServerFactory
from twisted.python.components import registerAdapter
from twisted.python import log
from ldaptor.inmemory import fromLDIFFile
from ldaptor.interfaces import IConnectedLDAPEntry
from ldaptor.protocols.ldap import distinguishedname
from ldaptor.protocols.ldap.ldapserver import LDAPServer
import tempfile
import sys
from txpostgres import txpostgres, reconnection
from twisted.internet import reactor, task
from twisted.enterprise import adbapi
from p2k16.core import crypto


class LoggingDetector(reconnection.DeadConnectionDetector):

    def startReconnecting(self, f):
        print("[*] database connection is down (error: {})".format(f.value))
        return reconnection.DeadConnectionDetector.startReconnecting(self, f)

    def reconnect(self):
        print("[*] reconnecting...")
        return reconnection.DeadConnectionDetector.reconnect(self)

    def connectionRecovered(self):
        print("[*] connection recovered")
        return reconnection.DeadConnectionDetector.connectionRecovered(self)


con = None  # type: txpostgres.Connection


def configure_db():
    def connectionError(f):
        print("-> connecting failed with {}".format(f))

    def connected(_, _con):
        global con
        con = _con
        print("-> connected, running a query periodically")

    #     lc = task.LoopingCall(runLoopingQuery, conn)
    #     return lc.start(2)
    #
    # def result(res):
    #     print("-> query returned result: {}".format(res))
    #
    # def onError(f):
    #     print("-> query failed with {}".format(f.value))
    #
    # def runLoopingQuery(conn):
    #     d = conn.runQuery("select 1")
    #     d.addCallbacks(result, onError)

    # connect to the database using reconnection
    conn = txpostgres.Connection(detector=LoggingDetector())
    d = conn.connect('dbname=p2k16')

    # if the connection failed, log the error and start reconnecting
    d.addErrback(conn.detector.checkForDeadConnection)
    d.addErrback(connectionError)
    d.addCallback(connected, conn)


class Account(BaseLDAPEntry):
    def __init__(self, dn, attrs=None):
        super().__init__(dn, attrs or {})
        # self.dn = DistinguishedName(dn)
        # self.attrs = attrs or {}

    def _bind(self, password):
        password = password.decode("utf-8")
        log.msg("Account.bind: password={}".format(password))

        for key in self._user_password_keys:
            for digest in self.get(key, []):
                log.msg("Account.bind: userPassword={}".format(digest))
                if crypto.check_password(digest, password):
                    return self
        raise ldaperrors.LDAPInvalidCredentials()


def _create_account(row, people_dn):
    base = list(people_dn.listOfRDNs)
    (username, name, email, password) = row
    attrs = {"uid": [username]}

    if name is not None:
        attrs["displayName"] = [name]

    if email is not None:
        attrs["mail"] = [email]

    if password is not None:
        attrs["userPassword"] = [password]

    av = LDAPAttributeTypeAndValue(attributeType="uid", value=username)
    dn = [RelativeDistinguishedName(attributeTypesAndValues=[av])] + base
    return Account(dn, attrs)


@inlineCallbacks
def lookup_account(username, bound_dn: Account, people_dn):
    log.msg("bound_dn={}".format(bound_dn.toWire() if bound_dn is not None else ""))
    res = yield con.runQuery("select username, name, email, password from account where username=%s", [username])

    if len(res) == 1:
        return _create_account(res[0], people_dn)
    return None


@inlineCallbacks
def search_account(bound_dn: Account, people_dn):
    log.msg("bound_dn={}".format(bound_dn.toWire() if bound_dn is not None else ""))
    res = yield con.runQuery("select username, name, email, NULL as password from account")

    return [_create_account(row, people_dn) for row in res]


class Forest(object):
    def __init__(self, ldap_server):
        self.ldap_server = ldap_server
        self.roots = {}

    def bound_user(self):
        return self.ldap_server.boundUser

    def add_tree(self, tree: "Tree"):
        self.roots[tree.mount_point] = tree

    def lookup(self, dn: DistinguishedName):
        for tree in self.roots.values():  # type: Tree
            if tree.mount_point.contains(dn):
                return tree.lookup(self, dn)

        return defer.fail()


class Tree(object):
    def __init__(self, mount_point, con):
        self.mount_point = mount_point  # type: DistinguishedName
        self.people_dn = DistinguishedName([RelativeDistinguishedName("ou=People")] + list(mount_point.listOfRDNs))
        self.con = con

    @inlineCallbacks
    def lookup(self, context, dn: DistinguishedName, *args):
        log.msg("lookup: dn={}, args={}".format(dn.toWire(), args))
        # log.msg("rdn={}".format(dn.listOfRDNs))
        # log.msg("dn.up={}".format(dn.up().toWire()))

        if dn == self.people_dn:
            return Focus(self, context, dn)

        if dn.up() == self.people_dn:
            kv = dn.listOfRDNs[0].split()[0]  # type: LDAPAttributeTypeAndValue
            (field, name) = (kv.attributeType, kv.value)

            if field == "uid":
                account = yield lookup_account(name, context.bound_user(), self.people_dn)
                if account is not None:
                    # TODO: check password
                    # ldaperrors.LDAPInvalidCredentials()
                    return account

                return None
            else:
                return None

        raise ldaperrors.LDAPProtocolError("lookup!!")


class Focus(object):
    def __init__(self, tree: Tree, context, base_dn: DistinguishedName):
        self.tree = tree
        self.context = context
        self.base_dn = base_dn

    @inlineCallbacks
    def search(self, filterObject, attributes, scope, derefAliases, sizeLimit, timeLimit, typesOnly, callback, *args,
               **kwargs):
        log.msg("Focus.search: args={}, kwargs={}".format(args, kwargs))
        # log.msg("filterObject={}".format([filterObject]))
        # log.msg("attributes={}".format(attributes))
        # log.msg("scope={}".format(scope))
        # log.msg("derefAliases={}".format(derefAliases))
        # log.msg("sizeLimit={}".format(sizeLimit))
        # log.msg("timeLimit={}".format(timeLimit))
        # log.msg("typesOnly={}".format(typesOnly))

        accounts = yield search_account(self.context.bound_user(), self.tree.people_dn)
        for account in accounts:
            callback(account)


class LDAPServerFactory(ServerFactory):
    protocol = LDAPServer

    def __init__(self):
        self.current_proto = None

    def buildProtocol(self, addr):
        proto = self.protocol()
        proto.debug = self.debug
        proto.factory = self
        self.current_proto = proto
        return proto


if __name__ == "__main__":
    from twisted.internet import reactor

    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    else:
        port = 8080

    base_dn = DistinguishedName(stringValue="dc=bitraf,dc=no")

    log.startLogging(sys.stderr)


    def make_forest(factory):
        # print("x={}".format(x))
        forest = Forest(factory.current_proto)
        forest.add_tree(Tree(base_dn, con))
        return forest


    registerAdapter(make_forest, LDAPServerFactory, IConnectedLDAPEntry)
    factory = LDAPServerFactory()
    factory.debug = True
    application = service.Application("ldaptor-server")
    myService = service.IServiceCollection(application)
    serverEndpointStr = "tcp:{0}".format(port)
    e = serverFromString(reactor, serverEndpointStr)
    d = e.listen(factory)

    configure_db()

    reactor.run()
