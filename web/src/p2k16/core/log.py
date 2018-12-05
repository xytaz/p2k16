# Do not put any p2k16.* imports here!
import logging
import os
import yaml
from typing import Dict


class P2k16LoggingFilter(logging.Filter):
    _data = {}  # type: Dict[str, str]

    def filter(self, record):
        # Just to make sure that these are always set.
        record.p2k16ReqId = ""
        record.p2k16Username = ""
        record.p2k16HttpReq = ""

        data = P2k16LoggingFilter._data

        if data:
            username = P2k16LoggingFilter._data.get("username", None)
            if username:
                record.p2k16Username = " [{}]".format(username)

            method = P2k16LoggingFilter._data.get("method", None)
            path = P2k16LoggingFilter._data.get("path", None)

            if method and path:
                record.p2k16HttpReq = " [{} {}]".format(method, path)

        return True

    @classmethod
    def set(cls, **kwargs):
        cls._data = kwargs

    @classmethod
    def clear(cls):
        cls._data.clear()


def configure_logging(app: str, logging_yaml: str):
    import yaml
    import logging.config

    def interpolate(loader, node):
        string = loader.construct_scalar(node)
        return string.format(app=app)

    if not os.path.isdir("log"):
        os.mkdir("log")

    yaml.add_constructor(u'!interpolate', interpolate)
    with open(logging_yaml) as f:
        cfg = yaml.load(f)

    logging.config.dictConfig(cfg)


def load_config():
    logger = logging.getLogger(__name__)
    cfg = {}

    p2k16_config = os.getenv('P2K16_CONFIG')
    if p2k16_config is None:
        return cfg

    p2k16_config = os.path.abspath(p2k16_config)

    config_default = os.path.join(os.path.dirname(p2k16_config), "config-default.yaml")
    config_default = os.path.abspath(config_default)

    logger.info("Loading defaults from {}".format(config_default))

    try:
        with open(config_default, "r") as f:
            for k, v in yaml.load(f).items():
                cfg[k] = v
    except IOError:
        pass

    logger.info("Loading config from {}".format(p2k16_config))
    with open(p2k16_config, "r") as f:
        for k, v in yaml.load(f).items():
            cfg[k] = v

    return cfg
