import logging
import logging.handlers
import inspect
import os
import libs.app as app


class Logger:
    def __init__(self):

        self.logfile = "{}/../log/{}".format(os.path.dirname(os.path.realpath(__file__)), app.pref.getValue('log.file'))
        print("Using logfile: {}".format(self.logfile))
        loglevel = app.pref.getValue('log.level')
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)

        self.logging = logging.getLogger(__name__)
        self.logging.basicConfig(filename=self.logfile, level = numeric_level)

    def getLogger(self):
        return self.logging


    def _addCallerToMsg(self, msg):
        stack = inspect.stack()
        the_class = stack[1][0].f_locals["self"].__class__
        the_method = stack[1][0].f_code.co_name
        msg = "{}.{}(): {}".format(the_class,the_method,msg)
        return msg

    def info(self, msg):
        self.logging.info(self._addCallerToMsg(msg))

    def warning(self, msg):
        self.warn(msg)

    def warn(self, msg):
        self.logging.warning(self._addCallerToMsg(msg))

    def debug(self, msg, obj=None):
        self.logging.debug(self._addCallerToMsg(msg))
        if obj is not None:
            self.logging.debug(str(obj))

    def crit(self, msg, obj = None):
        self.debug("CRITICAL: " + msg, obj)


