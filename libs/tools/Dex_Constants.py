# pylint: disable=E0213

from enum import Enum


NULL = 0
ACK = 1
NAK = 2
INVALID_COMMAND = 3
INVALID_PARAM = 4
INCOMPLETE_PACKET_RECEIVED = 5
RECEIVER_ERROR = 6
INVALID_MODE = 7
PING = 10
READ_FIRMWARE_HEADER = 11
READ_DATABASE_PARTITION_INFO = 15
READ_DATABASE_PAGE_RANGE = 16
READ_DATABASE_PAGES = 17
READ_DATABASE_PAGE_HEADER = 18
READ_TRANSMITTER_ID = 25
WRITE_TRANSMITTER_ID = 26
READ_LANGUAGE = 27
WRITE_LANGUAGE = 28
READ_DISPLAY_TIME_OFFSET = 29
WRITE_DISPLAY_TIME_OFFSET = 30
READ_RTC = 31
RESET_RECEIVER = 32
READ_BATTERY_LEVEL = 33
READ_SYSTEM_TIME = 34
READ_SYSTEM_TIME_OFFSET = 35
WRITE_SYSTEM_TIME = 36
READ_GLUCOSE_UNIT = 37
WRITE_GLUCOSE_UNIT = 38
READ_BLINDED_MODE = 39
WRITE_BLINDED_MODE = 40
READ_CLOCK_MODE = 41
WRITE_CLOCK_MODE = 42
READ_DEVICE_MODE = 43
ERASE_DATABASE = 45
SHUTDOWN_RECEIVER = 46
WRITE_PC_PARAMETERS = 47
READ_BATTERY_STATE = 48
READ_HARDWARE_BOARD_ID = 49
READ_FIRMWARE_SETTINGS = 54
READ_ENABLE_SETUP_WIZARD_FLAG = 55
READ_SETUP_WIZARD_STATE = 57
MAX_COMMAND = 59
MAX_POSSIBLE_COMMAND = 255
EGV_VALUE_MASK = 1023
EGV_DISPLAY_ONLY_MASK = 32768
EGV_TREND_ARROW_MASK = 15
EGV_NOISE_MASK = 112
MG_DL_TO_MMOL_L = 0.05556
CRC_LEN = 2
TRANSMITTER_BATTERY_LOW = 210
TRANSMITTER_BATTERY_EMPTY = 207

class BATTERY_STATES(Enum):
    NONE = 1
    CHARGING = 2
    NOT_CHARGING = 3
    NTC_FAULT = 4
    BAD_BATTERY = 5


class RECORD_TYPES(Enum):
    MANUFACTURING_DATA = 1
    FIRMWARE_PARAMETER_DATA = 2
    PC_SOFTWARE_PARAMETER = 3
    SENSOR_DATA = 4
    EGV_DATA = 5
    CAL_SET = 6
    DEVIATION = 7
    INSERTION_TIME = 8
    RECEIVER_LOG_DATA = 9
    RECEIVER_ERROR_DATA = 10
    METER_DATA = 11
    USER_EVENT_DATA = 12
    USER_SETTING_DATA = 13
    MAX_VALUE = 14


class TREND_ARROW_VALUES(Enum):
    NONE = (0)
    DOUBLE_UP = (1,"\u21C8", "DoubleUp")
    SINGLE_UP = (2,"\u2191", "SingleUp")
    UP_45 = (3,"\u2197", "FortyFiveUp")
    FLAT = (4,"\u2192", "Flat")
    DOWN_45 = (5,"\u2198", "FortyFiveDown")
    SINGLE_DOWN = (6,"\u2193", "SingleDown")
    DOUBLE_DOWN = (7,"\u21CA", "DoubleDown")
    NOT_COMPUTABLE = (8, "", "NOT_COMPUTABLE")
    OUT_OF_RANGE = (9, "", "OUT_OF_RANGE")

    def __init__(self, id, a = None, t= None):
        self.myID=id
        self.arrowSymbol = a
        self.trendName = t


    def Symbol(self):
        if self.arrowSymbol == None:
            return "\u2194"
        else:
            return self.arrowSymbol


    def friendlyTrendName(self):
        if self.trendName == None:
            return self.__name__.replace("_", " ")
        else:
            return self.trendName

    def getID(self):
        return self.myID

class SPECIALBGVALUES_MGDL(Enum):
    NONE = ("??0", 0)
    SENSORNOTACTIVE = ("?SN", 1)
    MINIMALLYEGVAB = ("??2", 2)
    NOANTENNA = ("?NA", 3)
    SENSOROUTOFCAL = ("?NC", 5)
    COUNTSAB = ("?CD", 6)
    ABSOLUTEAB = ("?AD", 9)
    POWERAB = ("???", 10)
    RFBADSTATUS = ("?RF", 12)


    def __init__(self, s, i):
        self.__name__=s
        self.val=i

    @property
    def value(self):
        return self.val


    def __str__(self):
        return self.name


    def getEGVSpecialValue(val):
        for e in SPECIALBGVALUES_MGDL:
            if e.val == val:
                return e
        return None


    def isSpecialValue(val):
        for e in SPECIALBGVALUES_MGDL:
            if e.val == val:
                return True
        return False

class InsertionState(Enum):
    NONE = 1
    REMOVED = 2
    EXPIRED = 3
    RESIDUAL_DEVIATION = 4
    COUNTS_DEVIATION = 5
    SECOND_SESSION = 6
    OFF_TIME_LOSS = 7
    STARTED = 8
    BAD_TRANSMITTER = 9
    MANUFACTURING_MODE = 10
    MAX_VALUE = 11


class NOISE(Enum):
    NOISE_NONE = (0)
    CLEAN = (1)
    LIGHT = (2)
    MEDIUM = (3)
    HEAVY = (4)
    NOT_COMPUTED = (5)
    MAX = (6)

