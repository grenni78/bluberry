from libs.tools import datetime
from libs.tools import ratelimits
import binascii
from libs.bluetooth import BluetoothDevice
from libs.base import Base



class Blucon(bluetoothDevice.BluetoothDevice, Base):
    _glucoseOffset = 0
    _currentBlockNumber = 0
    _currentOffset = 0
    _minutesDiffToLastReading = 0
    _minutesBack = 0
    _getOlderReading = False
    _communicationStarted = False
    _currentTrendIndex = 0
    _getNowGlucoseDataIndexCommand = False
    GET_SENSOR_AGE_DELAY = 3 * 3600
    BLUKON_GETSENSORAGE_TIMER = "blukon-getSensorAge-timer"
    BLUKON_DECODE_SERIAL_TIMER = "blukon-decodeSerial-timer"
    GET_DECODE_SERIAL_DELAY = 12 * 3600
    _getNowGlucoseDataCommand = False
    _timeLastBg = 0
    _persistentTimeLastBg = 0
    _blockNumber = 0
    _full_data = []
    _timeLastCmdReceived = 0

    _bridgeBattery = 0
    _nfcSensorAge = 0

    currentCommand = ""

    def __init__(self, application, autoconnect=False, address=None, addrType=btle.ADDR_TYPE_PUBLIC, iface=None):
        Base().__init__(application)
        BluetoothDevice().__init__(autoconnect=False, address=None, addrType=btle.ADDR_TYPE_PUBLIC, iface=None)

    # initializes device
    def _initDevice(self):
        self.app.log.info("initialize BluCon")
        self.deviceId = self.app.pref.getValue("devices.bluetooth.blucon.deviceID")
        self.bridgeBattery = 0 # force battery to no-value before first reading
        self.nfcSensorAge = 0  # force sensor age to no-value before first reading
        ratelimit.clearRatelimit(BLUKON_GETSENSORAGE_TIMER)
        self._getNowGlucoseDataCommand = False
        self._getNowGlucoseDataIndexCommand = False

        self._getOlderReading = False
        self._blockNumber = 0

    # gets the pin for the BT Connection
    def getPin(self):
        thepin = self.app.pref.getValue(BLUKON_PIN_PREF, None)
        if thepin is not None and len(thepin) >= 3:
            return thepin
        return None

    # sets the pin for the BT Connection
    def setPin(self, thepin = None):
        if thepin is None:
            return
        self.app.pref.setValue(BLUKON_PIN_PREF, thepin)

    # checks if byte sequence is command
    def isCommand(self,sequence, command):
        if sequence.tolower().startswith(command) :
            return true
        return False

    # decides if currently data is collected
    def isCollecting(self):
        # use internal logic to decide if we are collecting something, if we return true here
        # then we will never get reset due to missed reading service restarts
        _minutesDiff = 0

        _minutesDiff = ((((datetime.tsl() - self._timeLastCmdReceived) / 1000) + 30) / 60)
        self.app.log.info("_minutesDiff to last cmd=" + _minutesDiff + ", last cmd received at: " + datetime.dateTimeText(self._timeLastCmdReceived));

        if _communicationStarted:
            #we need to make sure communication did not stop a long time ago because of another issue
            if _minutesDiff > 2: # min. a cmd should be received within a few ms so if after this time nothing has been received we overwrite this flag
                self._communicationStarted = False

        return self._communicationStarted

    def isBlukonPacket(self,buffer):
        # -53  0xCB -117 0x8B #
        if buffer is not None and len(buffer) > 2:
            if (buffer[0] == 0xCB) or (buffer[0] == 0x8B):
                return True
        return False

    # determines if sensor is ready
    def isSensorReady(self, sensorStatusByte):
        sensorStatusString = ""
        ret = False

        if sensorStatusByte == 0x01:
            sensorStatusString = "not yet started";
        elif sensorStatusByte == 0x02:
            sensorStatusString = "starting"
            ret = true
        elif sensorStatusByte == 0x03:
            # status for 14 days and 12 h of normal operation, abbott reader quits after 14 days
            sensorStatusString = "ready"
            ret = true
        elif sensorStatusByte == 0x04:
            # status of the following 12 h, sensor delivers last BG reading constantly
            sensorStatusString = "expired"
        elif sensorStatusByte ==  0x05:
            # sensor stops operation after 15d after start
            sensorStatusString = "shutdown";
        elif sensorStatusByte ==  0x06:
            sensorStatusString = "in failure";
        else:
            sensorStatusString = "in an unknown state";

        self.app.log.info("Sensor status is: " + sensorStatusString)

        if not ret:
            self.app.userInteract.message("Error", "Can't use this sensor as it is " + sensorStatusString)

        return ret

    # returns the sensor age
    def sensorAge(input):
        sensorAge = ((input[3 + 5] & 0xFF) << 8) | (input[3 + 4] & 0xFF)
        app.log.info("sensorAge=" + sensorAge)

        return sensorAge

    # check if package is a blukon package
    def checkBlukonPacket(self,buffer):
        return isBlukonPacket(buffer) and getPin() is not None

    # decodes a sensor's serial number
    def decodeSerialNumber(self, input):

        uuid = [0, 0, 0, 0, 0, 0, 0, 0]
        lookupTable = [
                        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                        "A", "C", "D", "E", "F", "G", "H", "J", "K", "L",
                        "M", "N", "P", "Q", "R", "T", "U", "V", "W", "X",
                        "Y", "Z"
        ]
        uuidShort = [0, 0, 0, 0, 0, 0, 0, 0]

        for i in range(2,7):
            uuidShort[i - 2] = input[(2 + 8) - i]

        uuidShort[6] = 0x00
        uuidShort[7] = 0x00

        binary = ""
        binS = ""
        for i in range(7):
            # convert hex in binary string
            binS = bin(int( uuidShort[i] & 0xFF , 16))[2:].zfill(8)
            binary += binS

        v = "0"
        pozS = [0, 0, 0, 0, 0]

        #get 5 byte chunks for lookup
        for i in range(9):
            value = int( binary[(5 * i):(5*i) + 4], 2)
            v += lookupTable[value]

        self.app.log.info("decodeSerialNumber=" + v)

        self.app.pref.setValue("devices.bluetooth.blucon.blukon-serial-number", v)
        return v

    # decodes sent packages


    """
    @keencave
    extract trend index from FRAM block #3 from the libre sensor
    input: blucon answer to trend index request, including 6 starting protocol bytes
    return: 2 byte containing the next absolute block index to be read from
    the libre sensor
    """

    def blockNumberForNowGlucoseData(self,input):
        nowGlucoseIndex2 = 0
        nowGlucoseIndex3 = 0

        nowGlucoseIndex2 = (input[5] & 0x0F)

        self._currentTrendIndex = nowGlucoseIndex2

        # calculate byte position in sensor body
        nowGlucoseIndex2 = (nowGlucoseIndex2 * 6) + 4

        # decrement index to get the index where the last valid BG reading is stored
        nowGlucoseIndex2 -= 6
        # adjust round robin
        if nowGlucoseIndex2 < 4:
            nowGlucoseIndex2 = nowGlucoseIndex2 + 96

        # calculate the absolute block number which correspond to trend index
        nowGlucoseIndex3 = 3 + (nowGlucoseIndex2 / 8)

        # calculate offset of the 2 bytes in the block
        self._nowGlucoseOffset = nowGlucoseIndex2 % 8

        self.app.log.info("++++++++currentTrendData: index " + self._currentTrendIndex + ", block " + nowGlucoseIndex3 + ", offset " + self._nowGlucoseOffset)

        return nowGlucoseIndex3

    def blockNumberForNowGlucoseDataDelayed(delayedIndex):
        # calculate byte offset in libre FRAM
        ngi2 = (delayedIndex * 6) + 4

        ngi2 -= 6
        if ngi2 < 4:
            ngi2 = ngi2 + 96

        # calculate the block number where to get the BG reading
        ngi3 = 3 + (ngi2 / 8)

        # calculate the offset in the block
        self._nowGlucoseOffset = ngi2 % 8
        self.app.log.info("++++++++backfillingTrendData: index " + delayedIndex + ", block " + ngi3 + ", offset " + self._nowGlucoseOffset)

        return ngi3

    """
    @keencave
    rescale raw BG reading to BG data format used in xDrip+
    use 8.5 devider
    raw format is in 1000 range
    """
    getGlucose = lambda rawGlucose: int(rawGlucose * Constants.LIBRE_MULTIPLIER)

    """
    @keencave
    extract BG reading from the raw data block containing the most recent BG reading
    input: bytearray with blucon answer including 3 header protocol bytes
    uses nowGlucoseOffset to calculate the offset of the two bytes needed
    return: BG reading as int
    """
    def nowGetGlucoseValue(input):

        # grep 2 bytes with BG data from input bytearray, mask out 12 LSB bits and rescale for xDrip+
        rawGlucose = ((input[3 + self._nowGlucoseOffset + 1] & 0x1F) << 8) | (input[3 + self._nowGlucoseOffset] & 0xFF)
        self.app.log.info("rawGlucose=" + rawGlucose + ", m_nowGlucoseOffset=" + self._nowGlucoseOffset)

        # rescale
        curGluc = getGlucose(rawGlucose)

        return curGluc

    def processNewTransmitterData(transmitterData):
        if transmitterData is None:
            app.log.warn("Got duplicated data! Last BG at " + datetime.dateTimeText(self._timeLastBg))
            return

        sensor = Sensor.currentSensor()
        if sensor is None:
            self.log.info("processNewTransmitterData: No Active Sensor, Data only stored in Transmitter Data")
            return None

        DexCollectionService.last_transmitter_Data = transmitterData
        self.log.info("BgReading.create: new BG reading at " + transmitterData.timestamp)
        BgReading.create(transmitterData.raw_data, transmitterData.filtered_data, xdrip.getAppContext(), transmitterData.timestamp)
        return True
