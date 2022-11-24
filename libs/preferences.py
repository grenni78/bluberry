"""
Manage Preferences
"""
import json
import os
import os.path
import sys
from bluberry import *

class Preferences:
    _prefObj = {}
    _file = ""
    _changed = False

    def __init__(self, file):
        super().__init__()
        self._file = file
        
        if os.path.isfile(self._file):
            with open(file) as f:
                self._prefObj = json.load(f)
        else:
            self._prefObj = {}

    def saveSettings(self):
        if self._changed:
            os.rename(self._file, self._file + "~")
            with open(self._file, "w") as write_file:
                json.dump(self._prefObj, write_file, skipkeys=True, indent=4, sort_keys=False)
            print(json.dumps(self._prefObj,skipkeys=True, indent=4, sort_keys=False))
            self._changed = False

    # returns a value from the configuration
    # e.g. 'log.file'
    def getValue(self, valueName, default=None):
        parts = valueName.split('.')

        node = self._prefObj
        i = 0

        while parts[i] in node:
            node = node[parts[i]]

            i += 1
            if i >= len(parts):
                break

        if i > 0:
            return node

        self.setValue(valueName, default, True)
        return default
    # stores a value
    # if the key exists, the value is overridden
    # if the key does not exist it is created recursivly
    def setValue(self, valueName, value, internal_call=False):
        if not internal_call:
            oldValue = self.getValue(valueName, None)
        else:
            oldValue = None
        
        try:
            if oldValue is not None:
                # value with this name is already present -> overwrite
                parts = valueName.rsplit('.', 1)
                node = self.getValue(parts[0],None)
                node[parts[1]] = value
            else:
                #value is not present -> create
                i = 0
                parts = valueName.split('.')
                lastPart = len(parts)-1
                node = self._prefObj

                for i in range(lastPart - 1):
                    if parts[i] not in node:
                        node[parts[i]] = {}
                    node = node[parts[i]]

                node[parts[lastPart]] = value

            self._changed = True
            self.saveSettings()

        except:
            pass






