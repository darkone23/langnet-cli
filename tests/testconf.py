from nose2.events import Plugin

from langnet.logging import setup_logging


class GlobalSetup(Plugin):
    configSection = "global-setup"

    def startTestRun(self, event):
        setup_logging()
