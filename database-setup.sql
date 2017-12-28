REVOKE ALL PRIVILEGES ON DATABASE p2k16 FROM "p2k16-admin";
REVOKE ALL PRIVILEGES ON SCHEMA public FROM "p2k16-admin";
REVOKE ALL PRIVILEGES ON SCHEMA public FROM "p2k16-web";

DROP DATABASE IF EXISTS "p2k16";

DROP USER IF EXISTS "p2k16-admin";
DROP USER IF EXISTS "p2k16-web";
DROP USER IF EXISTS "p2k16";

-- This is the default owner of all objects
CREATE USER "p2k16"
  NOLOGIN;

-- Regular users that can log in
CREATE USER "p2k16-admin"
  ENCRYPTED PASSWORD 'p2k16-admin';

CREATE USER "p2k16-web"
  ENCRYPTED PASSWORD 'p2k16-web';

CREATE DATABASE p2k16;

GRANT USAGE ON SCHEMA PUBLIC TO "p2k16-admin";
GRANT USAGE ON SCHEMA PUBLIC TO "p2k16-web";

GRANT CREATE ON DATABASE p2k16 TO "p2k16-admin";
