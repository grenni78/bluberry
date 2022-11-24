import gatt
import libs.app as app
import logging
import re
import numbers
import time
import struct
from threading import Thread, Event

ENABLE_NOTIFICATION_VALUE = b'\x02\x00'
CLIENT_CHARACTERISTIC_CONFIG = "00002902-0000-1000-8000-00805f9b34fb"

log = logging.getLogger(__name__)

class BluetoothDevice(gatt.Device):

    def __init__(self, autoconnect=False, address=None, reconnect_count=5, manager = None, managed = False):

        self._BTaddress = address.upper()
        self.manager = manager
        super(BluetoothDevice,self).__init__(mac_address=self._BTaddress,manager=manager, managed = managed)
        #take primary interface

        self._BTifaceAddr = None

        self._device = None
        self._service = None
        self._RX = None
        self._TX = None
        self._MAX_RECONNECTS = reconnect_count
        self._reconnects = 0

        if not self.is_connected():
            if autoconnect:
                log.info("..BluetoothDevice.__init__: connecting")
                self.connect()
        else:
            log.info("..BluetoothDevice.__init__: device is already connected")


    def connect_succeeded(self):
        super().connect_succeeded()
        log.info("[{}] Connected".format(self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        log.warn("[{}] Connection failed: {}".format(self.mac_address, str(error)))
        log.info("..waiting 5 seconds and retrying")
        time.sleep(5)
        self.connect()

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        log.info("[{}] Disconnected".format(self.mac_address))
