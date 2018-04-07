import logging

from flask import Flask
from flask_env import MetaFlaskEnv

from . import boot

logger = logging.getLogger(__name__)


class Configuration(metaclass=MetaFlaskEnv):
    pass


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

    for f in boot.find_config_files():
        logger.info("Loading config from {}".format(f))
        app.config.from_pyfile(f)

    # Allow the environment variables to override by loading them lastly
    app.config.from_object(Configuration)

    return app
