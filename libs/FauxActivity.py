
"""
  Wrapper for legacy Activity dependency
"""

from libs.base import Base

class FauxActivity(Base):

    def onCreate(self, savedInstanceState):
        self.log.info("onCreate called: ")

    def onResume(self):
        self.log.info("onResume called: ")

    def onPause(self):
        self.log.info("onPause called: ")

    def startService(self, intent):
        # ToDo start service
        pass

    def finish(self):
        self.log.info("finish() called: ")


