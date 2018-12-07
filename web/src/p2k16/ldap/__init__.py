import logging
import sys

from ldaptor._encoder import to_unicode
from ldaptor.entry import BaseLDAPEntry
from ldaptor.interfaces import IConnectedLDAPEntry
from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap import ldaperrors
from ldaptor.protocols.ldap.distinguishedname import DistinguishedName, RelativeDistinguishedName
from ldaptor.protocols.ldap.distinguishedname import LDAPAttributeTypeAndValue
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from p2k16.core import crypto
from twisted.application import service
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.internet.endpoints import serverFromString
from twisted.internet.protocol import ServerFactory
from twisted.python import log
from twisted.python.components import registerAdapter
from twisted.python.failure import Failure
from txpostgres import txpostgres, reconnection
from typing import Set

logger = logging.getLogger(__name__)


class LoggingDetector(reconnection.DeadConnectionDetector):

    def startReconnecting(self, f):
        logger.warning("Database connection is down (error: {})".format(f.value))
        return reconnection.DeadConnectionDetector.startReconnecting(self, f)

    def reconnect(self):
        logger.warning("Database reconnecting...")
        return reconnection.DeadConnectionDetector.reconnect(self)

    def connectionRecovered(self):
        logger.warning("Database connection recovered")
        return reconnection.DeadConnectionDetector.connectionRecovered(self)


con = None  # type: txpostgres.Connection


def configure_db(dsn: str):
    def connection_error(f):
        logger.info("Database connection failed with {}".format(f))

    def connected(_, _con):
        global con
        con = _con
        logger.info("Database connected")

    conn = txpostgres.Connection(detector=LoggingDetector())
    d = conn.connect(dsn)

    # if the connection failed, log the error and start reconnecting
    d.addErrback(conn.detector.checkForDeadConnection)
    d.addErrback(connection_error)
    d.addCallback(connected, conn)


def filter_object_to_where(filter_object):
    if isinstance(filter_object, pureldap.LDAPFilter_present):
        object_class = to_unicode(filter_object.value)

        if object_class.lower() in Account.valid_object_classes:
            return ["1=1"], []

    elif isinstance(filter_object, pureldap.LDAPFilter_equalityMatch):
        field = to_unicode(filter_object.attributeDesc.value)
        value = to_unicode(filter_object.assertionValue.value)

        logger.debug("equality-match: field={}, value={}".format(field, value))

        if field in Account.valid_fields:
            return ["{}=%s".format(field)], [value]

    # elif isinstance(filter_object, pureldap.LDAPFilter_substrings):
    #     field = to_unicode(filter_object.type)
    #     value = filter_object.asText()
    #
    #     logger.debug("substrings: field={}, value={}".format(field, value))
    #
    #     if field in Account.valid_fields:
    #         return ["{} LIKE %s || '%'".format(field)], [value]

    logger.warning("Unsupported filter object: {}".format(repr(filter_object)))
    raise ldaperrors.LDAPInappropriateMatching()


class Account(BaseLDAPEntry):
    valid_object_classes = {oc.lower() for oc in {
        "objectClass",
        "posixAccount"}}

    valid_fields = {f.lower() for f in {
        "uid",
        "name",
        "mail"}}

    def __init__(self, dn, attrs=None):
        super().__init__(dn, attrs or {})
        # self.dn = DistinguishedName(dn)
        # self.attrs = attrs or {}

    @property
    def uid(self):
        return self.dn.listOfRDNs[0].split()[0].value

    def _bind(self, password):
        password = password.decode("utf-8")

        for key in self._user_password_keys:
            for digest in self.get(key, []):
                if crypto.check_password(digest, password):
                    return self
        raise ldaperrors.LDAPInvalidCredentials()


def _create_account(row, people_dn):
    base = list(people_dn.listOfRDNs)
    (uid, displayName, mail, userPassword) = row
    attrs = {"uid": [uid]}

    if displayName is not None:
        attrs["displayName"] = [displayName]

    if mail is not None:
        attrs["mail"] = [mail]

    if userPassword is not None:
        attrs["userPassword"] = [userPassword]
    attrs["foo"] = ["bar"]

    av = LDAPAttributeTypeAndValue(attributeType="uid", value=uid)
    dn = [RelativeDistinguishedName(attributeTypesAndValues=[av])] + base
    return Account(dn, attrs)


@inlineCallbacks
def lookup_account(uid: str, bound_dn: Account, people_dn):
    logger.info("lookup_account: uid={}, bind={}".format(uid, bound_dn.uid if bound_dn is not None else "<anon>"))
    args = [uid]
    res = yield con.runQuery('SELECT uid, "displayName", mail, "userPassword" FROM ldap_people WHERE uid=%s', args)

    if len(res) == 1:
        return _create_account(res[0], people_dn)
    return None


@inlineCallbacks
def search_account(bound_dn: Account, people_dn, filter_object, attributes, size_limit):
    logger.info("search_account: bound_dn={}".format(bound_dn.uid if bound_dn is not None else "<anon>"))

    attributes = set([to_unicode(a) for a in attributes])
    if "*" in attributes or b"*" in attributes:
        attributes = None

    args = []
    parts = [
        "uid",
        '"displayName"' if attributes is None or "displayName" in attributes else "NULL",
        "mail" if attributes is None or "mail" in attributes else "NULL"
    ]
    if attributes is None or "userPassword" in attributes:
        parts += ['(CASE WHEN uid=%s THEN "userPassword" ELSE NULL END)']
        args = [bound_dn.uid]
    else:
        parts += ["NULL"]
    q = "SELECT {} FROM ldap_people".format(", ".join(parts))

    (where, where_args) = filter_object_to_where(filter_object)

    if where is None:
        logger.warning("Unsupported filter")
        return []

    if len(where):
        q += " WHERE " + " AND ".join(where)
        args += where_args

    if size_limit is not None and size_limit > 0:
        q += " LIMIT %s"
        args += [size_limit]

    logger.debug("sql={}, args={}".format(q, args))
    cursor = yield con.runQuery(q, args)

    return [_create_account(row, people_dn) for row in cursor]


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

        raise ldaperrors.LDAPNoSuchObject(dn)


class Tree(object):
    def __init__(self, mount_point, con):
        self.mount_point = mount_point  # type: DistinguishedName
        self.people_dn = DistinguishedName([RelativeDistinguishedName("ou=People")] + list(mount_point.listOfRDNs))
        self.con = con

    @inlineCallbacks
    def lookup(self, context, dn: DistinguishedName, *args):
        # logger.info("lookup: dn={}, args={}".format(dn.toWire(), args))

        if dn == self.people_dn or dn == self.mount_point:
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

        raise ldaperrors.LDAPNoSuchObject(dn)


class Focus(object):
    def __init__(self, tree: Tree, context, base_dn: DistinguishedName):
        self.tree = tree
        self.context = context
        self.base_dn = base_dn

    @inlineCallbacks
    def search(self, filterObject, attributes, scope, derefAliases, sizeLimit, timeLimit, typesOnly, callback, *args,
               **kwargs):
        logger.info("filterObject={}".format([filterObject]))
        logger.info("attributes={}".format(attributes))
        # logger.info("scope={}".format(scope))
        # logger.info("derefAliases={}".format(derefAliases))
        # logger.info("sizeLimit={}".format(sizeLimit))
        # logger.info("timeLimit={}".format(timeLimit))
        # logger.info("typesOnly={}".format(typesOnly))

        accounts = yield search_account(self.context.bound_user(), self.tree.people_dn, filterObject, attributes,
                                        sizeLimit)
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


def run_ldap_server(ldap_port, dsn, ldaps_port, ldaps_cert, ldaps_key):
    # Configure logging
    logging_observer = log.PythonLoggingObserver()
    logging_observer.start()

    base_dn = DistinguishedName(stringValue="dc=bitraf,dc=no")

    def make_forest(factory):
        forest = Forest(factory.current_proto)
        forest.add_tree(Tree(base_dn, con))
        return forest

    registerAdapter(make_forest, LDAPServerFactory, IConnectedLDAPEntry)
    factory = LDAPServerFactory()
    factory.debug = False
    application = service.Application("ldaptor-server")
    my_service = service.IServiceCollection(application)
    e = serverFromString(reactor, "tcp:{0}".format(ldap_port))
    d = e.listen(factory)

    def server_started(*args):
        # logger.info("Launching LDAP server. LDAP port: {}, LDAPS port: {}".format(ldap_port, ldaps_port))
        configure_db(dsn)
        reactor.run()

    def server_failed(x: Failure):
        print(x.value, file=sys.stderr)

    d.addCallback(server_started)
    d.addErrback(server_failed)
