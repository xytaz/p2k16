import os

from p2k16.core.log import configure_logging

configure_logging("p2k16", os.getenv("P2K16_LOGGING"))

accesslog = "log/access.log"

bind = "127.0.0.1:5000"

pidfile = "p2k16.pid"
