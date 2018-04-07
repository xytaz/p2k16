import logging
import os
from typing import Mapping

import flask.config

model_should_use_flask = True
model_should_use_version_tables = True


def find_config_files():
    p2k16_config = os.getenv('P2K16_CONFIG')
    files = []
    if p2k16_config:
        p2k16_config = os.path.abspath(p2k16_config)

        config_default = os.path.join(os.path.dirname(p2k16_config), "config-default.cfg")
        config_default = os.path.abspath(config_default)

        files = [config_default, p2k16_config]

    return files


def load_config() -> Mapping[str, str]:
    if hasattr(load_config, "config"):
        return load_config.config

    logger = logging.getLogger(__name__)
    basedir = os.getcwd()

    c = flask.config.Config(basedir)

    for f in find_config_files():
        logger.info("Loading config from {}".format(f))
        c.from_pyfile(f)

    # TODO: Load the rest from the environment

    cfg = {k: v for k, v in c.items()}

    load_config.config = cfg
    return cfg
