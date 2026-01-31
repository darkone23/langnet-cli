import logging as stdlib_logging
import os

from nose2.events import Plugin

from langnet.logging import setup_logging


class NullWriter:
    """Fake file object that discards output"""

    def write(self, s):
        pass

    def flush(self):
        pass


class GlobalSetup(Plugin):
    configSection = "global-setup"

    def startTestRun(self, event):
        original_level = os.environ.get("LANGNET_LOG_LEVEL")

        os.environ["LANGNET_LOG_LEVEL"] = "CRITICAL"
        setup_logging()

        root_logger = stdlib_logging.getLogger()
        root_logger.setLevel(stdlib_logging.CRITICAL)
        root_logger.addHandler(stdlib_logging.StreamHandler(NullWriter()))
        stdlib_logging.getLogger("langnet").addHandler(stdlib_logging.StreamHandler(NullWriter()))

        if original_level:
            os.environ["LANGNET_LOG_LEVEL"] = original_level
            setup_logging()
