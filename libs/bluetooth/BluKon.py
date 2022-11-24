
import threading
import logging
import binascii
import _thread
import libs.tools.ratelimits as ratelimits
import libs.tools.TimeHelpers as TimeHelpers
import libs.app as app
import libs.models.Sensor as Sensor
import libs.models.bgReading as BgReading
from libs.models.LibreBlock import LibreBlock
from libs.models.transmitterData import TransmitterData
from libs.bluetooth.bluetoothDevice import BluetoothDevice


BLUKON_GETSENSORAGE_TIMER = "blukon-getSensorAge-timer"
BLUKON_DECODE_SERIAL_TIMER = "blukon-decodeSerial-timer"
BLUKON_PIN_PREF = "devices.bluetooth.blukon.pin"
BLUKON_SERVICE = "436a62c0-082e-4ce8-a08b-01d81f195b24"
BLUKON_UART_TX = "436aa6e9-082e-4ce8-a08b-01d81f195b24"
BLUKON_UART_RX = "436a0c82-082e-4ce8-a08b-01d81f195b24"
GET_PATCH_INFO = "010d0900"
GET_SENSOR_AGE_DELAY    = 3 * 3600
GET_DECODE_SERIAL_DELAY = 12 * 3600

CMD_RESET             = "cb010000"
CMD_ACK               = "8b0a00"
CMD_SEND_ACK          = "810a00"
CMD_NACK              = "8b1a02"
CMD_TIMEOUT           = "8b1a020014"
CMD_SENSOR_REMOVED    = "8b1a02000f"
CMD_PATCH_READ_ERROR  = "8b1a020011"
CMD_UNKNOWN1          = "8b1a020009"
CMD_UNKNOWN2          = "010d0b00"
CMD_UNKNOWN4          = "010d0a00"
CMD_SLEEP             = "010c0e00"
CMD_GET_PATCH_INFO    = "010d0900"
CMD_PATCH_INFO        = "8bd9"
CMD_UNKNOWN3          = "8bdb"
CMD_UNKNOWN5          = "8bda"
CMD_UNKNOWN6          = "8bde"
CMD_BATT_LOW          = "8bda02"
CMD_WAKEUP            = "cb010000"
CMD_SENSOR_AGE        = "010d0e0127"
CMD_GET_HISTORIC_DATA = "010d0f02002b"
CMD_GLUCOSE_DATA_IDX = "010d0e0103"
CMD_GLUCOSE_DATA = "010d0e01"
PATCH_READ_ERROR = "8b1a020011"


log = logging.getLogger(__name__)

class BluKon(BluetoothDevice):

    def __init__(self, autoconnect=False, address=None, reconnect_count=5, manager=None, managed=False):
        super().__init__(self, autoconnect, address, reconnect_count, manager, managed)
        self.blukon_service = None
        self._RX = None
        self._TX = None
        self.bridgeBattery = 0 # force battery to no-value before first reading
        self.nfcSensorAge = 0  # force sensor age to no-value before first reading
        self._getNowGlucoseDataCommand = False
        self._getNowGlucoseDataIndexCommand = False
        self._nowGlucoseOffset = 0

        self._getOlderReading = False
        self._blockNumber = 0
        self._timeLastCmdReceived = 0
        self.currentCommand = ""
        self._communicationStarted = False

        self._persistentTimeLastBg = 0
        self._minutesDiffToLastReading = 0
        self._currentBlockNumber = 0
        self._currentOffset = 0
        self._minutesBack = 0
        self._timeLastBg = 0


    def services_resolved(self):
        super().services_resolved()

        log.info("..Blukon: services_resolved")

        self.blukon_service = next(
            bs for bs in self.services
            if bs.uuid == BLUKON_SERVICE)

        self._RX = next(
            rxc for rxc in self.blukon_service.characteristics
            if rxc.uuid == BLUKON_UART_RX)

        self._TX = next(
            txc for txc in self.blukon_service.characteristics
            if txc.uuid == BLUKON_UART_TX)

        self._RX.enable_notifications()

        ratelimits.clearRatelimit(BLUKON_GETSENSORAGE_TIMER)

        log.info("..Blukon: sending data request")
        self.sendRequestData()


    def characteristic_enable_notification_succeeded(self):
        log.info("notification successfully enabled")


    def characteristic_enable_notification_failed(self):
        log.info("notifications could not be enabled!")


    def characteristic_value_updated(self, characteristic, value):
        if characteristic == self._RX:
            log.info("..RX: data received.")
            self.decodeBlukonPacket(value)
        elif characteristic == self._TX:
            # should not happen!
            log.info("..TX: data received.")
            self.decodeBlukonPacket(value)
        else:
            log.info("...Unknown characteristic '%s' has sent data: %s", characteristic, value)


    def sendRequestData(self):
        self._TX.write_value(CMD_PATCH_INFO)

    @staticmethod
    def getPin():
        thepin = app.pref.getValue(BLUKON_PIN_PREF, None)
        if thepin is not None and len(thepin) >= 3:
            return thepin
        return None

    # sets the pin for the BT Connection
    @staticmethod
    def setPin(thepin=None):
        if thepin is None:
            return
        app.pref.setValue(BLUKON_PIN_PREF, thepin)

    # returns the sensor age
    @staticmethod
    def sensorAge(input):
        sensorAge = ((input[3 + 5] & 0xFF) << 8) | (input[3 + 4] & 0xFF)
        log.info("sensorAge= %d", sensorAge)

        return sensorAge

    ##
    def decodeBlukonPacket(self, buffer):

        def getDelayedTrendIndex(ti, mb):
            if mb < ti:
                return (ti - (mb - 1)) % 15
            else:
                return (ti - (mb - 2)) % 15

        cmdFound = 0
        gotLowBat = False

        if buffer is None:
            log.info("no buffer passed to decodeBlukonPacket")
            return None

        self._timeLastCmdReceived = TimeHelpers.tsl()

        strRecCmd = binascii.hexlify(buffer)
        log.info("Blukon data: %s ", strRecCmd)

        if self.app.pref.getValue("external_blukon_algorithm", False):
            log.info(binascii.hexlify(buffer))

        if strRecCmd.startsWith(CMD_RESET):
            log.info("reset currentCommand")
            self.currentCommand = ""
            cmdFound = 1
            self._communicationStarted = True

        # BluconACKRespons will come in two different situations
        # 1) after we have sent an ackwakeup command
        # 2) after we have a sleep command
        elif strRecCmd.startswith(CMD_ACK):
            cmdFound = 1
            log.info("Got ACK")

            if self.currentCommand.startswith(CMD_ACK):
                #ack received
                self.currentCommand = CMD_UNKNOWN2
                log.info("getUnknownCmd1: %s", self.currentCommand)

            else:
                log.info("Got sleep ACK, rsetting initialstate!")
                self.currentCommand = ""

        elif strRecCmd.startswith(CMD_NACK):
            cmdFound = 1
            log.warn("Got NACK on cmd=" + self.currentCommand + " with error=" + strRecCmd[:6])

            if strRecCmd.startswith(CMD_TIMEOUT):
                log.warn("Timeout: please wait 5min or push button to restart!")

            elif strRecCmd.startswidth(CMD_SENSOR_REMOVED):
                log.warn("Libre sensor has been removed!")

            elif strRecCmd.startwith(PATCH_READ_ERROR):
                log.warn("Patch read error.. please check the connectivity and re-initiate... or maybe battery is low?")
                app.pref.setValue("devices.bluetooth.bridge_battery", 1)
                gotLowBat = True

            elif strRecCmd.startwith(CMD_UNKNOWN1):
                log.warn("unknown command 1")

            self._getNowGlucoseDataCommand = False
            self._getNowGlucoseDataIndexCommand = False

            self.currentCommand = CMD_SLEEP
            log.info("Send sleep cmd")
            self._communicationStarted = False

            ratelimits.clearRatelimit(BLUKON_GETSENSORAGE_TIMER) # set to current time to force timer to be set back

        elif strRecCmd.startwith(CMD_WAKEUP) and self.currentCommand == "":
            cmdFound = 1
            log.info("wakeup received")

            # must be first cmd to be sent otherwise get NACK!
            self.currentCommand = CMD_GET_PATCH_INFO
            log.info("getPatchInfo")

        elif self.currentCommand.startwith(GET_PATCH_INFO) and strRecCmd.startwith(CMD_PATCH_INFO):
            cmdFound = 1
            log.info("Patch Info received")

            #
            #    in getPatchInfo: blucon answer is 20 bytes long.
            #    Bytes 13 - 19 (0 indexing) contains the bytes 0 ... 6 of block #0
            #    Bytes 11 to 12: ?
            #    Bytes 3 to 10: Serial Number reverse order
            #    Byte 2: 04: ?
            #    Bytes 0 - 1 (0 indexing) is the ordinary block request answer (0x8B 0xD9).
            #
            #    Remark: Byte #17 (0 indexing) contains the SensorStatusByte.

            if ratelimits.ratelimit(BLUKON_DECODE_SERIAL_TIMER, GET_DECODE_SERIAL_DELAY) :
                self.decodeSerialNumber(buffer)

            if self.isSensorReady(buffer[17]):
                self.currentCommand = CMD_SEND_ACK
                log.info("Send ACK")
            else:
                log.warn("Sensor is not ready, stop!")
                self.currentCommand = CMD_SLEEP
                log.info("Send sleep command")
                self._communicationStarted = False
        elif self.currentCommand.startwith(CMD_UNKNOWN2) and strRecCmd.startwith(CMD_UNKNOWN3):
            cmdFound = 1
            log.info("gotUnknownCmd1 (010d0b00): %s", strRecCmd)

            if strRecCmd != "8bdb0101041711" :
                log.info("gotUnknownCmd1 (010d0b00): %s", strRecCmd)

            self.currentCommand = CMD_UNKNOWN4
            log.info("getUnknownCmd2: %s", self.currentCommand)

        elif self.currentCommand.startswith(CMD_UNKNOWN4) and strRecCmd.startwith(CMD_UNKNOWN5):
            cmdFound = 1
            log.info("gotUnknownCmd2 (010d0a00): %s", strRecCmd)

            if strRecCmd != "8bdaaa":
                log.info("gotUnknownCmd2 (010d0a00): %s", strRecCmd)

            if strRecCmd.startwith(CMD_BATT_LOW):
                log.info("gotUnknownCmd2: is maybe battery low????")
                app.pref.setValue("devices.bluetooth.bridge_battery", 5)
                gotLowBat = True

            if ratelimits.ratelimit(BLUKON_GETSENSORAGE_TIMER, GET_SENSOR_AGE_DELAY):
                self.currentCommand = CMD_SENSOR_AGE
                log.info("getSensorAge")
            else:
                if app.pref.getValue("devices.bluetooth.blucon.external_blukon_algorithm",False):
                    # Send the command to getHistoricData (read all blcoks from 0 to 0x2b)
                    log.info("getHistoricData (2)")
                    self.currentCommand = CMD_GET_HISTORIC_DATA
                    self._blockNumber = 0
                else:
                    self.currentCommand = CMD_GLUCOSE_DATA_IDX
                    self._getNowGlucoseDataIndexCommand = True # to avoid issue when gotNowDataIndex cmd could be same as getNowGlucoseData (case block=3)
                    log.info("getNowGlucoseDataIndexCommand")
        elif self.currentCommand.startwith(CMD_SENSOR_AGE) and strRecCmd.startwith(CMD_UNKNOWN6):
            cmdFound = 1
            log.info("SensorAge received")

            sensorAge = BluKon.sensorAge(buffer)

            if sensorAge > 0 and sensorAge < 200000:
                app.pref.setValue("devices.bluetooth.blucon.nfc_sensor_age", sensorAge) #in minutes

            if self.app.pref.getValue("devices.bluetooth.blucon.external_blukon_algorithm", False):
                # Send the command to getHistoricData (read all blcoks from 0 to 0x2b)
                log.info("getHistoricData (3)")
                self.currentCommand = CMD_GET_HISTORIC_DATA
                self._blockNumber = 0
            else:
                self.currentCommand = CMD_GLUCOSE_DATA_IDX
                self._getNowGlucoseDataIndexCommand = True # to avoid issue when gotNowDataIndex cmd could be same as getNowGlucoseData (case block=3)
                log.info("getNowGlucoseDataIndexCommand")

        elif self.currentCommand.startwith(CMD_GLUCOSE_DATA_IDX) and self._getNowGlucoseDataIndexCommand is True and strRecCmd.startwith(CMD_UNKNOWN6):
            cmdFound = 1
            # calculate time delta to last valid BG reading
            self._persistentTimeLastBg = app.pref.getValue("devices.bluetooth.blucon.blukon-time-of-last-reading", 0)
            self._minutesDiffToLastReading = ((((TimeHelpers.tsl() - self._persistentTimeLastBg) / 1000) + 30) / 60)
            log.info("_minutesDiffToLastReading=%d , last reading: %d", self._minutesDiffToLastReading, TimeHelpers.dateTimeText(self._persistentTimeLastBg))

            # check time range for valid backfilling
            if self._minutesDiffToLastReading > 7 and self._minutesDiffToLastReading < (8 * 60):
                log.info("start backfilling")
                self._getOlderReading = True
            else:
                self._getOlderReading = False

            # get index to current BG reading
            self._currentBlockNumber = self.blockNumberForNowGlucoseData(buffer)
            self._currentOffset = self._nowGlucoseOffset
            # time diff must be > 5,5 min and less than the complete trend buffer
            if not self._getOlderReading:
                self.currentCommand = "010d0e010" + binascii.hexlify(self._currentBlockNumber) # getNowGlucoseData for Block -> CMD_GLUCOSE_DATA_IDX + block
                self._nowGlucoseOffset = self._currentOffset
                log.info("getNowGlucoseData")
            else:
                self._minutesBack = self._minutesDiffToLastReading
                delayedTrendIndex = self._currentTrendIndex
                # ensure to have min 3 mins distance to last reading to avoid doible draws (even if they are distict)
                if self._minutesBack > 17:
                    self._minutesBack = 15
                elif self._minutesBack > 12:
                    self._minutesBack = 10
                elif self._minutesBack > 7:
                    self._minutesBack = 5

                log.info("read %d mins old trend data", self._minutesBack)

                delayedTrendIndex = getDelayedTrendIndex(delayedTrendIndex, self._minutesBack)

                delayedBlockNumber = self.blockNumberForNowGlucoseDataDelayed(delayedTrendIndex)
                currentCommand = "010d0e010" + binascii.hexlify(delayedBlockNumber) #getNowGlucoseData for block -> CMD_GLUCOSE_DATA_IDX + block
                log.info("getNowGlucoseData backfilling")

            self._getNowGlucoseDataIndexCommand = False
            self._getNowGlucoseDataCommand = True

        elif self.currentCommand.startwith(CMD_GLUCOSE_DATA) and self._getNowGlucoseDataCommand is True and strRecCmd.startwith(CMD_UNKNOWN6):
            log.info("Before Saving data: + currentCommand = %s", self.currentCommand)
            blockId = self.currentCommand[(len(CMD_GLUCOSE_DATA)):]
            now = TimeHelpers.tsl()
            if blockId == "":
                try:
                    blockNum = int(blockId, 16)
                    log.info("Saving data: + blockid = %d", blockNum)
                    LibreBlock.createAndSave("blukon", now, buffer, blockNum * 8)
                except AssertionError as e:
                    log.info("invalid blockId %s", e)

            cmdFound = 1
            currentGlucose = self.nowGetGlucoseValue(buffer)

            log.info("********got getNowGlucoseData= %s", currentGlucose)

            if not self._getOlderReading:
                self.processNewTransmitterData(TransmitterData.create(currentGlucose, currentGlucose, 0, now))

                self._timeLastBg = now

                app.ppref.setValue("blukon-time-of-last-reading", self._timeLastBg)
                log.info("time of current reading: %d", TimeHelpers.dateTimeText(self._timeLastBg))

                currentCommand = "010c0e00"
                log.info("Send sleep cmd")
                self._communicationStarted = False

                self._getNowGlucoseDataCommand = False
            else:
                log.info("bf: processNewTransmitterData with delayed timestamp of %d min", self._minutesBack)
                self.processNewTransmitterData(TransmitterData.create(currentGlucose, currentGlucose, 0 , now - (self._minutesBack * 60 * 1000)))
                # @keencave - count down for next backfilling entry
                self._minutesBack -= 5
                if self._minutesBack < 5:
                    self._getOlderReading = False

                log.info("bf: calculate next trend buffer with %d min timestamp", self._minutesBack)
                delayedTrendIndex = self._currentTrendIndex

                delayedTrendIndex = getDelayedTrendIndex(delayedTrendIndex, self._minutesBack)

                delayedBlockNumber = self.blockNumberForNowGlucoseDataDelayed(delayedTrendIndex)
                currentCommand = "010d0e010" + binascii.hexlify(bytearray(delayedBlockNumber)) # getNowGlucoseData
                log.info("bf: read next block: %s", currentCommand)

        elif ((currentCommand.startsWith("010d0f02002b") or (currentCommand == "" and self._blockNumber > 0)) and strRecCmd.startsWith("8bdf")):
            cmdFound = 1
            self.handlegetHistoricDataResponse(buffer)
        elif strRecCmd.startsWith("cb020000"):
            cmdFound = 1
            log.error("is bridge battery low????!")
            app.pref.setValue("bridge_battery", 3)
            gotLowBat = True
        elif strRecCmd.startsWith("cbdb0000"):
            cmdFound = 1
            log.error("is bridge battery really low????!")
            app.pref.setValue("bridge_battery", 2)
            gotLowBat = True


        if not gotLowBat:
            app.pref.setInt("bridge_battery", 100)

        self.CheckBridgeBattery.checkBridgeBattery()

        if currentCommand and cmdFound == 1:
            log.info("Sending reply: {}".format(currentCommand))
            return currentCommand
        else:
            if cmdFound == 0:
                log.error("***COMMAND NOT FOUND! -> {} on currentCmd={}".format(strRecCmd,currentCommand))

            currentCommand = ""
            return None

    @staticmethod
    def processNewTransmitterData(transmitterData):
        if transmitterData is None:
            log.warn("Got duplicated data!")
            return

        sensor = Sensor.currentSensor()

        if sensor is None:
            log.info("processNewTransmitterData: No Active Sensor, Data only stored in Transmitter Data")
            return None

        #DexCollectionService.last_transmitter_Data = transmitterData
        log.info("BgReading.create: new BG reading at %d", transmitterData.timestamp)
        BgReading.create(transmitterData.raw_data, transmitterData.filtered_data, transmitterData.timestamp)
        return True
