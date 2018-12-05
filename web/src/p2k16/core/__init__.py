import logging
import os

from flask import Flask

logger = logging.getLogger(__name__)


class P2k16UserException(Exception):
    """Exception that happened because the user did something silly. The message will be shown to the user"""

    def __init__(self, msg):
        self.msg = msg


class P2k16TechnicalException(Exception):
    """Exception for unexpected stuff."""

    def __init__(self, msg=None):
        self.msg = msg


def make_app():
    app = Flask("p2k16", static_folder="web/static")

    app.config.BOWER_KEEP_DEPRECATED = False
    app.config['BOWER_COMPONENTS_ROOT'] = '../web/bower_components'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from p2k16.core.log import load_config
    cfg = load_config()
    app.config.from_mapping(cfg)

    return app
