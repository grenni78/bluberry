from libs.models import bgReading
from libs.tools import TimeHelpers
from libs import Base
from enum import Enum

"""
 Created by jamorham on 04/10/2016.
 
 Class for managing calibration plugins
"""

class PluggableCalibration(Base):

    memory_cache = {}
    current_plugin_cache = None

    # get calibration plugin instance by type
    def getCalibrationPlugin(self, t):
        if t in self.memory_cache:
            return self.memory_cache[t]

        plugin = None
        if t == self.Type.Datricsae:
            plugin = Datricsae()
        elif t == self.Type.FixedSlopeExample:
            plugin = FixedSlopeExample()
        elif t == self.Type.xDripOriginal:
            plugin = XDripOriginal()
        elif t == self.Type.Last7UnweightedA:
            plugin = LastSevenUnweightedA()

            # add new plugins here and also to the enum below

        else:
            self.log.warn("Unhandled plugin type: " + str(t))
            return None

        self.memory_cache[t] = plugin
        return plugin


    # enum for supported calibration plugins
    class Type(Enum):
        Nothing = ("Nothing")
        Datricsae = ("Datricsae")
        FixedSlopeExample = ("FixedSlopeExample")
        xDripOriginal = ("xDripOriginal")
        Last7UnweightedA = ("Last7UnweightedA")

        # add new algorithms here and also in to getCalibrationPlugin() above

        internalName = ""
        mapToInternalName = {}

        def __init__(self, name):
            self.internalName = name


    # populate a ListPreference with plugin choices
    def setListPreferenceData(self, p):
        entries = []
        entryValues = []
        for t in self.Type:
            # Not sure exactly of what the overhead of this will be
            # perhaps we should save it to a cache...

            plugin = self.getCalibrationPlugin(t)
            if plugin is None:
                entries.append("None")
            else:
                entries.append(plugin.getNiceNameAndDescription())
            entryValuesappend(str(plugin))
        p.setEntries(entries)
        p.setEntryValues(entryValues)


    # get calibration plugin instance by name
    def getCalibrationPluginByName(self, t):
        return self.getCalibrationPlugin(self.Type(t))

    # get calibration plugin instance from preference setting
    def getCalibrationPluginFromPreferences(self):
        if self.current_plugin_cache is None:
            self.current_plugin_cache = self.getCalibrationPluginByName(self.pref.getValue("current_calibration_plugin", "Nothing"))

        return self.current_plugin_cache


    def invalidatePluginCache():
        current_plugin_cache = null;
        memory_cache.clear();
        Log.d(TAG, "Invalidated Plugin Cache");


    # lazy helper function
    def getCalibrationData(self):
        try:
            return self.getCalibrationPluginFromPreferences().getCalibrationData()
        except AssertionError as err:
            self.log.debug("Error getting calibration data: ",err)
            return None


    # lazy helper function
    def getGlucoseFromBgReading(self, bgReading):
        try:
            plugin = self.getCalibrationPluginFromPreferences()
            cd = plugin.getCalibrationData()
            return plugin.getGlucoseFromBgReading(bgReading, cd)
        except AssertionError as err:
            return -1

    def mungeBgReading(self, bgReading):
        try:
            plugin = self.getCalibrationPluginFromPreferences()
            cd = plugin.getCalibrationData()
            bgReading.calculated_value = plugin.getGlucoseFromBgReading(bgReading, cd)
            bgReading.filtered_calculated_value = plugin.getGlucoseFromFilteredBgReading(bgReading, cd)
            return bgReading
        except AssertionError as err:
            self.log.debug("error munging bg reading: ", err)
            return bgReading


    # lazy helper function
    def newCloseSensorData(self):
        try:
            return self.getCalibrationPluginFromPreferences().newCloseSensorData()
        except AssertionError as err:
            self.log.debug("error getting new glucose sensor  data: ", err)
            return False


    # lazy helper function
    def newFingerStickData(self):
        try:
            return self.getCalibrationPluginFromPreferences().newFingerStickData()
        except AssertionError as err:
            self.log.debug("error getting finger stick data: ", err)
            return False


    # lazy helper function
    def invalidateCache(self):
        try:
            return self.getCalibrationPluginFromPreferences().invalidateCache()
        except AssertionError as err:
            self.log.debug("error invalidating cache: ", err)
            return False


    # lazy helper function
    def invalidateAllCaches(self):
        try:
            for key, value in self.memory_cache:
                
                try:
                    value.invalidateCache()
                    self.log.info("Invalidate cache for plugin: " + value.getAlgorithmName())
                except AssertionError as err:
                    self.log.debug("error invalidateAllCahces cache for element '" + key + "': ", err)

            return self.getCalibrationPluginFromPreferences().invalidateCache()
        except AssertionError as err2:
            self.log.debug("error in invalidateAllCaches cache: ", err)
            return False

    # lazy helper function
    def invalidateCache(self, tag):
        try:
            return self.getCalibrationPluginByName(tag).invalidateCache()
        except AssertionError as err:
            self.log.debug("error in invalidateCache : ", err)
            return False
