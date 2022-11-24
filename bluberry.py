#!/usr/bin/python3
# -*- coding: utf-8 -*-
# bluberry
#
# lese-tool fuer den blukon - Freestyle Libre Adapter
#
import logging
from logging.handlers import SysLogHandler
import time

import os
import os.path
import io
import signal
import errno

from daemonize import Daemonize

#from libs.bluetooth.blucon import *
import libs.Constants
import libs.app as app
from libs import preferences
from libs import userinteract
from peewee import *
from libs.tools import TimeHelpers
from libs.bluetooth.BluKon import *


START_MESSAGE = "started with pid {pid:d}"

log = logging.getLogger(__name__)



class BluBerry(Daemonize):
    def __init__(self, foreground=False):

        app_name = "BluBerry"
        self.pref = preferences.Preferences(file=os.path.dirname(os.path.realpath(__file__)) + "/preferences.json")
        self.ppref = preferences.Preferences(file = os.path.dirname(os.path.realpath(__file__)) + "/data.json")
        pid_dir = self.pref.getValue("PID_FILE", "/var/run/bluberry.pid")
        #user = self.pref.getValue("USER")
        #group = self.pref.getValue("GROUP")
        verbose = int(self.pref.getValue("DEBUG", 0))
        if verbose != 0:
            verbose = True
        else:
            verbose = False

        logfile = "{}/log/{}".format(os.path.dirname(os.path.realpath(__file__)), self.pref.getValue('log.file'))
        print(" Logfile is: {}".format(logfile))
        logging.basicConfig(filename=logfile, level=getattr(logging, self.pref.getValue('log.level').upper(), None))

        self._initDatabase()

        app.initialize(None,self.db,userinteract,None,self.pref,self.ppref)

        app.log = log
        self._cgmDevice = None

        #super(BluBerry,self).__init__(app_name,pid_dir,self._run,user=user,group=group,verbose = verbose, keep_fds = [log.handler.stream.fileno()], logger = log.logging, foreground = foreground)
        super(BluBerry, self).__init__(app_name, pid_dir, self._run, verbose=verbose, foreground=foreground)

        self.gatt_manager = gatt.DeviceManager(adapter_name='hci0')

        log.info("..starting mail loop.")
        self.start()


    def _initDatabase(self):
        self._sql_file = app.pref.getValue("database.sqlite.path",None)
        self.db = SqliteDatabase(self._sql_file, pragmas={
            'foreign_keys': 1,
        })

    def sigterm(self, signum, frame):

        self.logger.warning("Caught signal {}. Stopping daemon.".format(signum))
        self._cgmDevice.disconnect()
        self.gatt_manager.stop()

        app.TERMINATE = True
        sys.exit(0)


    def _run(self, *args):

        self._cgmDevice = BluKon(True, address = app.pref.getValue("devices.bluetooth.blukon.deviceId"), manager = self.gatt_manager, managed=True )

        self.gatt_manager.run()

        #while True:
        #    # ticker
        #    if app.TERMINATE:
        #        break
        #    time.sleep(1)


###########################################################

###
# returns our PID
###
def get_pid():
    global pid
    pid = -1
    pidfile = preferences.Preferences(file=os.path.dirname(os.path.realpath(__file__)) + "/preferences.json").getValue("PID_FILE")
    if os.path.isfile(pidfile):
        with open(pidfile, "r") as f:
            pid = int(f.read())
    return pid
###
# checks if we are active
###
def is_running():
    if get_pid() > 0:
        return True
    return False

###
# main logic (if we are called as main application)
###
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        sys.exit("Syntax: {} [--no-detach] COMMAND".format(sys.argv[0]))

    foreground = False

    if sys.argv[1][:2] == "--":
        option = sys.argv[1][2:].lower()

        if option == "no-detach":
            foreground = True


    cmd = sys.argv[len(sys.argv)-1].lower()

    if cmd == 'start':
        print("...starting daemon")
        ## init Master class
        app.parent = BluBerry(foreground)

    elif cmd == 'stop':
        pid = get_pid()
        print("...trying to stop BluBerry")

        if pid > 0:
            print("....BluBerry is running (PID: {}). Stopping it now!".format(pid))
            os.kill(pid,signal.SIGTERM)
        else:
            print("....BluBerry is not running!")

    elif cmd == 'status':
        if is_running():
            print("bluberry is running.")
        else:
            print("bluberry is not running.")
    else:
        sys.exit('Unknown command "%s".' % cmd)
