from ldaptor.protocols import pureldap, pureber
from p2k16.ldap import filter_object_to_where


def desc(string):
    return pureldap.LDAPAttributeDescription(string)


def ber(string):
    return pureber.BEROctetString(string)


def eq(a, b):
    return pureldap.LDAPFilter_equalityMatch(attributeDesc=a, assertionValue=b)


def test_filter_object():
    fo = eq(desc("uid"), ber("foo"))
    assert (["uid=%s"], ["foo"]) == filter_object_to_where(fo)
