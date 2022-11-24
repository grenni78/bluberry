"""
Queue for sensor data
"""
import logging
from peewee import Model, IdentityField, BareField, BooleanField, DoesNotExist
from libs.app import app

log = logging.getLogger(__name__)

class SensorSendQueue(Model):

    _ID = IdentityField(column_name = "_ID")

    sensor = BareField()

    success = BooleanField(index = True)

    class Meta:
        legacy_table_names = False
        database = app.db

    @staticmethod
    def nextSensorJob():
        try:
            return SensorSendQueue.get(SensorSendQueue.success == False).order_by("_ID desc")
        except:
            return None


    @staticmethod
    def queue():
        try:
            return SensorSendQueue.get(SensorSendQueue.success == False)
        except DoesNotExist:
            log.info("Queue is empty")
            return None

    @staticmethod
    def addToQueue(sensor):
        SensorSendQueue.SendToFollower(sensor)
        sensorSendQueue = SensorSendQueue()
        sensorSendQueue.sensor = sensor
        sensorSendQueue.success = False
        sensorSendQueue.save()



