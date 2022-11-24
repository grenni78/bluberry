# pylint: disable=E0213,E0211
"""
package com.eveningoutpost.dexdrip.utils;

import com.eveningoutpost.dexdrip.Services.DexCollectionService;
import com.eveningoutpost.dexdrip.Services.DexShareCollectionService;
import com.eveningoutpost.dexdrip.Services.G5CollectionService;
import com.eveningoutpost.dexdrip.Services.Ob1G5CollectionService;
import com.eveningoutpost.dexdrip.Services.WifiCollectionService;
import com.eveningoutpost.dexdrip.UtilityModels.Pref;
"""
from enum import Enum
from libs.tools import (
    Dex_Constants
)
from bluberry import *
import bluberry

class DexcomCollectionType(Enum):

    Nothing            = ("Nothing")
    BluetoothWixel     = ("BluetoothWixel")
    DexcomShare        = ("DexcomShare")
    DexbridgeWixel     = ("DexbridgeWixel")
    LimiTTer           = ("LimiTTer")
    WifiBlueToothWixel = ("WifiBlueToothWixel")
    WifiWixel          = ("WifiWixel")
    DexcomG5           = ("DexcomG5")
    WifiDexBridgeWixel = ("WifiDexbridgeWixel")
    Follower           = ("Follower")
    LibreAlarm         = ("LibreAlarm")
    NSEmulator         = ("NSEmulator")
    Disabled           = ("Disabled")
    Mock               = ("Mock")
    Manual             = ("Manual")

    internalName = ""

    usesBluetooth =  {"BluetoothWixel", "DexcomShare", "DexbridgeWixel", "LimiTTer", "WifiBlueToothWixel", "DexcomG5", "WifiDexbridgeWixel"}
    usesBtWixel = {"BluetoothWixel", "LimiTTer", "WifiBlueToothWixel"}
    usesWifi = {"WifiBlueToothWixel","WifiWixel","WifiDexBridgeWixel", "Mock"}
    usesXbridge = {"DexbridgeWixel","WifiDexbridgeWixel"}
    usesFiltered = {"DexbridgeWixel", "WifiDexbridgeWixel", "DexcomG5", "WifiWixel", "Follower", "Mock"}
    usesLibre = {"LimiTTer", "LibreAlarm"}
    usesBattery = {"BluetoothWixel", "DexbridgeWixel", "WifiBlueToothWixel", "WifiDexBridgeWixel", "Follower", "LimiTTer", "LibreAlarm"}
    usesDexcomRaw = {"BluetoothWixel", "DexbridgeWixel", "WifiWixel", "WifiBlueToothWixel", "DexcomG5", "WifiDexbridgeWixel"}
    usesTransmitterBattery = {"WifiWixel", "BluetoothWixel", "DexbridgeWixel", "WifiBlueToothWixel", "WifiDexBridgeWixel"}

    DEX_COLLECTION_METHOD = "dex_collection_method"

    does_have_filtered = False # TODO this could get messy with GC


    def  getType(dexCollectionType):
        return DexcomCollectionType(dexCollectionType)


    def  getDexCollectionType():
        return DexcomCollectionType.getType(bluberry.app.pref.getValue(DexcomCollectionType.DEX_COLLECTION_METHOD, "BluetoothWixel"))


    def setDexCollectionType(t):
        bluberry.app.pref.setValue(DexcomCollectionType.DEX_COLLECTION_METHOD, t.internalName)


    def hasBluetooth():
        if DexcomCollectionType.getDexCollectionType() in DexcomCollectionType.usesBluetooth:
            return True
        return False


    def hasBtWixel():
        if DexcomCollectionType.getDexCollectionType() in DexcomCollectionType.usesBtWixel:
            return True
        return False

    
    def hasXbridgeWixel():
        if DexcomCollectionType.getDexCollectionType() in DexcomCollectionType.usesXbridge:
            return True
        return False

    def hasWifi():
        if DexcomCollectionType.getDexCollectionType() in DexcomCollectionType.usesWifi:
            return True
        return False

    def hasLibre(t=None):
        if t is None:
            t = DexcomCollectionType.getDexCollectionType()
        if t in DexcomCollectionType.usesLibre:
            return True
        return False


    def hasBattery():
        if DexcomCollectionType.getDexCollectionType() in DexcomCollectionType.usesBattery:
            return True
        return False

    def hasSensor():
        if DexcomCollectionType.getDexCollectionType() != DexcomCollectionType.Manual:
            return True
        return False


    def hasDexcomRaw(t=None):
        if t is None:
            t = DexcomCollectionType.getDexCollectionType()
        if t in DexcomCollectionType.usesDexcomRaw:
            return True
        return False

    def usesDexCollectionService(t):
        if t in DexcomCollectionType.usesBtWixel or t in DexcomCollectionType.usesXbridge or t == DexcomCollectionType.LimiTTer:
          return True
        return False

    def usesClassicTransmitterBattery():
        if DexcomCollectionType.getDexCollectionType() in DexcomCollectionType.usesTransmitterBattery:
            return True
        return False


    def isFlakey():
        if DexcomCollectionType.getDexCollectionType() == DexcomCollectionType.DexcomG5:
            return True
        return False


    def hasFiltered():
        if DexcomCollectionType.does_have_filtered or DexcomCollectionType.getDexCollectionType() in DexcomCollectionType.usesFiltered:
            return True
        return False


    def isLibreOOPAlgorithm( collector):
        if collector is None:
            collector = DexcomCollectionType.getDexCollectionType()

        if collector == DexcomCollectionType.LimiTTer and bluberry.app.pref.getValue("external_blukon_algorithm", False):
            return True
        return False


    def getCollectorServiceClass():
        t = DexcomCollectionType.getDexCollectionType()
        """
        if t == DexcomCollectionType.DexcomG5:
            if bluberry.app.pref.getValue(Ob1G5CollectionService.OB1G5_PREFS, False):
                return Ob1G5CollectionService
            else:
                return G5CollectionService
        elif t == DexcomCollectionType.DexcomShare:
            return DexShareCollectionService
        elif t == DexcomCollectionType.WifiWixel:
            return WifiCollectionService
        else:
            return DexCollectionService
"""
    # using reflection to access static methods, could cache if needed maybe


    def getBestCollectorHardwareName():
        dct = DexcomCollectionType.getDexCollectionType()
        if dct == DexcomCollectionType.NSEmulator:
            return "Other App"
        elif dct == DexcomCollectionType.WifiWixel:
            return "Network G4"
#        elif dct == DexcomCollectionType.LimiTTer:
            #return DexcomCollectionService.getBestLimitterHardwareName()
        elif dct == DexcomCollectionType.WifiDexBridgeWixel:
            return "Network G4 and xBridge"
        elif dct == DexcomCollectionType.WifiBlueToothWixel:
            return "Network G4 and Classic xDrip"
        else:
            return dct.name


    def getBestBridgeBatteryPercent():
        if DexcomCollectionType.hasBattery():
            dct = DexcomCollectionType.getDexCollectionType()
                        
            return app.pref.getValue("bridge_battery", -1)

        elif DexcomCollectionType.hasWifi():
            return app.pref.getValue("parakeet_battery", -3)
        else:
            return -2

    def getBestBridgeBatteryPercentString():
        battery = DexcomCollectionType.getBestBridgeBatteryPercent()
        if battery > 0:
            return "" + battery
        else:
            return ""

