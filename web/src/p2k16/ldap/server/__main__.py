import argparse
import os
import sys

from p2k16.core.log import configure_logging

parser = argparse.ArgumentParser(description="LDAP frontend for P2k16")

parser.add_argument("--logging",
                    metavar="LOGGING_YAML",
                    dest="logging",
                    action="store",
                    help="A Python logging file in YAML format")

parser.add_argument("--ldap-port",
                    default=389,
                    metavar="PORT",
                    dest="ldap_port",
                    action="store",
                    help="Port for plain LDAP")

# parser.add_argument("--ldaps-port",
#                     default=636,
#                     metavar="PORT",
#                     dest="ldaps_port",
#                     action="store",
#                     help="Port for LDAP over TLS")
#
# parser.add_argument("--ldaps-cert",
#                     metavar="PATH",
#                     dest="ldaps_cert",
#                     action="store",
#                     help="Certificate for TLS")
#
# parser.add_argument("--ldaps-key",
#                     metavar="PATH",
#                     dest="ldaps_key",
#                     action="store",
#                     help="Private key for TLS")

args = parser.parse_args()

logging = args.logging if args.logging is not None else os.getenv("P2K16_LOGGING")

if logging is None:
    parser.print_usage(sys.stderr)
    print("Either --logging has to be given or P2K16_LOGGING has to be set.", file=sys.stderr)
    sys.exit(1)

configure_logging("p2k16-ldap", logging)

# This is here after logging has been configured.
import p2k16.ldap
p2k16.ldap.run_ldap_server(args.ldap_port, args.ldaps_port, args.ldaps_cert, args.ldaps_key)
