import os

from nose2.events import Plugin

from langnet.logging import setup_logging


class GlobalSetup(Plugin):
    configSection = "global-setup"

    def startTestRun(self, event):
        # Respect current LANGNET_LOG_LEVEL but force it to CRITICAL during tests
        original_level = os.environ.get("LANGNET_LOG_LEVEL")
        os.environ["LANGNET_LOG_LEVEL"] = "CRITICAL"
        setup_logging()

        # If there was an original level, restore it after setup
        if original_level:
            os.environ["LANGNET_LOG_LEVEL"] = original_level
            setup_logging()
