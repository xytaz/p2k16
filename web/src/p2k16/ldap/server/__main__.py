import argparse
import os
import sys

from p2k16.core.log import configure_logging, load_config

parser = argparse.ArgumentParser(description="LDAP frontend for P2k16")

parser.add_argument("--logging",
                    metavar="LOGGING_YAML",
                    dest="logging",
                    action="store",
                    help="A Python logging file in YAML format")

args = parser.parse_args()

logging = args.logging if args.logging is not None else os.getenv("P2K16_LOGGING")

if logging is None:
    parser.print_usage(sys.stderr)
    print("Either --logging has to be given or P2K16_LOGGING has to be set.", file=sys.stderr)
    sys.exit(1)

configure_logging("p2k16-ldap", logging)

cfg = load_config()

# This is here after logging has been configured.
import p2k16.ldap
p2k16.ldap.run_ldap_server(cfg["LDAP_PORT"],
                           cfg["LDAP_DB"],
                           cfg.get("ldaps_port", None),
                           cfg.get("ldaps_cert", None),
                           cfg.get("ldaps_key", None))
