DROP VIEW IF EXISTS ldap_people;

CREATE VIEW ldap_people AS
SELECT
  username AS uid,
  name     AS "displayName",
  email    AS mail,
  password AS "userPassword"
FROM account
WHERE NOT system;

GRANT SELECT ON ldap_people TO "p2k16-ldap";
