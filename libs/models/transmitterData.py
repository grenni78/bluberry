from peewee import *
import logging
from bitstring import Bits, BitArray
import libs.tools.TimeHelpers as TimeHelpers
from libs.app import app
from libs.tools import CheckBridgeBattery
from libs.models.Sensor import Sensor
from libs import Constants

import bluberry

log = logging.getLogger(__name__)

class TransmitterData(Model):

    _ID                  = IdentityField(column_name = "_ID")
    timestamp            = TimestampField(index = True)
    raw_data             = BigIntegerField()
    filtered_data        = BigIntegerField()
    sensor_battery_level = IntegerField()
    uuid                 = CharField(index = True)

    class Meta:
        legacy_table_names = False
        database = app.db


    def create(self, buffer=None, length=0, raw_data=None, filtered_data=None, sensor_battery_level=None, timestamp=None):

        lastTransmitterData = self.last()

        if buffer is None:
            if filtered_data is None:
                if raw_data is None:
                    log.warn("insufficent Data given!")
                    return None
                
                if (lastTransmitterData is not None) and (lastTransmitterData.raw_data == raw_data) and (abs(lastTransmitterData.timestamp - TimeHelpers.tsl()) < (Constants.MINUTE_IN_MS * 2)):
                    return None

                transmitterData = TransmitterData(database = self.app.db)
                transmitterData.sensor_battery_level = sensor_battery_level
                transmitterData.raw_data = raw_data
                transmitterData.timestamp = timestamp
                transmitterData.uuid = uuid.uuid4()
                transmitterData.save()
                return transmitterData


            if (lastTransmitterData is not None) and ( lastTransmitterData.raw_data == raw_data ) and ( abs(lastTransmitterData.timestamp - TimeHelpers.tsl()) < (Constants.MINUTE_IN_MS * 2)):
                return None

            transmitterData = TransmitterData()
            transmitterData.sensor_battery_level = sensor_battery_level
            transmitterData.raw_data = raw_data
            transmitterData.filtered_data = filtered_data
            transmitterData.timestamp = timestamp
            transmitterData.uuid = uuid.uuid4()
            transmitterData.save()
            return transmitterData


        if length < 6:
            return None

        transmitterData = TransmitterData(database = self.app.db)
        try:
            if ((buffer[0] == 0x11 or buffer[0] == 0x15) and buffer[1] == 0x00):
                #this is a dexbridge packet.  Process accordingly.
                # ! Byte Operations untested !
                log.info("create Processing a Dexbridge packet")
                txData = BitArray(uintle = buffer)
                transmitterData.raw_data = Bits(txData[2 * 8: 2 * 8 + 4 * 8]).uintle      # get 4 bytes beginning at position 2 * 8
                transmitterData.filtered_data = Bits(txData[6 * 8: 6 * 8 + 4 * 8]).uintle # get 4 bytes beginning at position 6 * 8
                # bitwise and with 0xff (1111....1) to avoid that the byte is treated as signed.
                transmitterData.sensor_battery_level = Bits(txData[10 * 8:10 * 8 + 4 * 8]).uintle & 0xff  # get 4 bytes beginning at position 10 * 8
                
                if buffer[0] == 0x15:
                    log.info("create Processing a Dexbridge packet includes delay information")
                    transmitterData.timestamp = timestamp - Bits(txData[16 * 8: 16 * 8 + 4]).uintle # get 4 bytes beginning at position 16 * 9 
                else:
                    transmitterData.timestamp = timestamp
                
                log.info("Created transmitterData record with Raw value of " + transmitterData.raw_data + " and Filtered value of " + transmitterData.filtered_data + " at " + timestamp + " with timestamp " + transmitterData.timestamp)
            else:  # this is NOT a dexbridge packet.  Process accordingly.
                
                log.info("create Processing a BTWixel or IPWixel packet")

                data_string = ""
                for i in range(length):
                    data_string += chr(buffer[i])

                data = data_string.split("\\s+")

                if len(data) > 1:
                    transmitterData.sensor_battery_level = int(data[1])
                    if len(data) > 2:
                        try:
                            self.pref.setValue("devices.bluetooth.bridge_battery", int(data[2]))
                            GcmActivity.sendBridgeBattery(self.pref.getValue("devices.bluetooth.bridge_battery", -1))
                            CheckBridgeBattery.checkBridgeBattery()
                        except AssertionError as err:
                            log.debug("Got exception processing classic wixel or limitter battery value: {}".format(err))

                        if data.length > 3:
                            if ((DexCollectionType.getDexCollectionType() == DexCollectionType.LimiTTer) and (not self.pref.getValue("use_transmiter_pl_bluetooth", False))):
                                try:
                                    # reported sensor age in minutes
                                    sensorAge = int(data[3])
                                    if ((sensorAge > 0) and (sensorAge < 200000)):
                                        self.pref.setValue("devices.bluetooth.blucon.nfc_sensor_age", sensorAge)
                                except err:
                                    log.debug("Got exception processing field 4 in classic limitter protocol: {}".format(err))
                transmitterData.raw_data = int(data[0])
                transmitterData.filtered_data = int(data[0])
                # TODO process does_have_filtered_here with extended protocol
                transmitterData.timestamp = timestamp

            if ( lastTransmitterData is not None ) and ( lastTransmitterData.timestamp >= transmitterData.timestamp):
                log.info("Rejecting TransmitterData constraint: last: " + TimeHelpers.dateTimeText(lastTransmitterData.timestamp) + " >= this: " + TimeHelpers.dateTimeText(transmitterData.timestamp))
                return None

            if ( lastTransmitterData is not None ) and ( lastTransmitterData.raw_data == transmitterData.raw_data ) and ( abs(lastTransmitterData.timestamp - transmitterData.timestamp) < (Constants.MINUTE_IN_MS * 2)):
                log.info("Rejecting identical TransmitterData constraint: last: " + TimeHelpers.dateTimeText(lastTransmitterData.timestamp) + " due to 2 minute rule this: " + TimeHelpers.dateTimeText(transmitterData.timestamp))
                return None

            lastCalibration = Calibration.lastValid()
            if ( lastCalibration is not None ) and ( lastCalibration.timestamp > transmitterData.timestamp ):
                log.info("Rejecting historical TransmitterData constraint: calib: " + TimeHelpers.dateTimeText(lastCalibration.timestamp) + " > this: " + TimeHelpers.dateTimeText(transmitterData.timestamp))
                return None

            transmitterData.uuid = uuid.uuid4()
            transmitterData.save()
            return transmitterData
        except err:
            log.debug("Got exception processing fields in protocol: {}".format(err))

        return None



    def last(self):
        return TransmitterData.select().order_by("_ID desc").limit(1).execute()

    def lastByTimestamp(self):
        return TransmitterData.select().order_by("timestamp desc").limit(1).execute()

    def getForTimestamp(self, timestamp):
        try:
            sensor = Sensor.currentSensor()
            if sensor is not None:
                # 1 minute padding (should never be that far off, but why not)
                bgReading = TransmitterData.select().where(TransmitterData.timestamp <= (timestamp + (60 * 1000))).order_by("timestamp desc")

                if (bgReading is not None) and (abs(bgReading.timestamp - timestamp) < (3 * 60 * 1000)): #cool, so was it actually within 4 minutes of that bg reading?
                    log.info("getForTimestamp: Found a BG timestamp match")
                    return bgReading

        except err:
            log.debug("getForTimestamp() Got exception on Select : ", err)
            return None

        log.info("getForTimestamp: No luck finding a BG timestamp match")
        return None

    def findByUuid(self, uuid):
        try:
            return TrasnmitterData.select().where(TransmitterData.uuid == uuid)
        except err:
            log.debug("findByUuid() Got exception on Select : ", err)
            return None

    def updateTransmitterBatteryFromSync(self, battery_level):
        try:
            td = TransmitterData.last()
            if (td is None) or (td.raw_data !=0 ):
                td = TransmitterData.create(0, battery_level, datetime.ts())
                log.info("Created new fake transmitter data record for battery sync")
                if td is None:
                    return

            if (battery_level != td.sensor_battery_level) or ((TimeHelpers.tsl()-td.timestamp)>(1000*60*60)):
                td.sensor_battery_level = battery_level
                td.timestamp = TimeHelpers.tsl() # freshen timestamp on this bogus record for system status
                app.log.info("Saving synced sensor battery, new level: "+battery_level)
                td.save()
            else:
                log.info("Synced sensor battery level same as existing: "+battery_level)

        except err:
            log.debug("Got exception updating sensor battery from sync: ", err)


