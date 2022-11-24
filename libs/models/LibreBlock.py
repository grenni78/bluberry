#import com.eveningoutpost.dexdrip.UtilityModels.Constants;
from peewee import *
import logging
import libs.tools.TimeHelpers as TimeHelpers
import libs.Constants as Constants

log = logging.getLogger(__name__)

class LibreBlock(Model):


    schema = {
        "CREATE TABLE LibreBlock (_id INTEGER PRIMARY KEY AUTOINCREMENT);",
        "ALTER TABLE LibreBlock ADD COLUMN timestamp INTEGER;",
        "ALTER TABLE LibreBlock ADD COLUMN reference TEXT;",
        "ALTER TABLE LibreBlock ADD COLUMN blockbytes BLOB;",
        "ALTER TABLE LibreBlock ADD COLUMN bytestart INTEGER;",
        "ALTER TABLE LibreBlock ADD COLUMN byteend INTEGER;",
        "ALTER TABLE LibreBlock ADD COLUMN calculatedbg REAL;",
        "CREATE INDEX index_LibreBlock_timestamp on LibreBlock(timestamp);",
        "CREATE INDEX index_LibreBlock_bytestart on LibreBlock(bytestart);",
        "CREATE INDEX index_LibreBlock_byteend on LibreBlock(byteend);"
    }


    _id = IdentityField()
    timestamp = IntegerField(index=True)

    byte_start = IntegerField(index=True)

    byte_end = IntegerField(index=True)

    reference = CharField(index=True)

    blockbytes = BlobField()

    calculated_bg = FloatField()

    # if you are indexing by block then just * 8 to get byte start
    @staticmethod
    def createAndSave(reference, timestamp, blocks, byte_start):
        lb = LibreBlock.LibreBLock.create(reference, timestamp, blocks, byte_start)
        if lb is not None:
            lb.save()

        return lb


    @staticmethod
    def create(reference, timestamp, blocks, byte_start):
        log.debug("Create new LibreBlock {}-{}-{}-{}".format(reference,timestamp,blocks,byte_start))
        if reference is None:
            log.error("Cannot save block with null reference")
            return None

        if blocks is None:
            log.error("Cannot save block with null data")
            return None

        lb = LibreBlock()
        lb.reference = reference
        lb.blockbytes = blocks
        lb.byte_start = byte_start
        lb.byte_end = byte_start + blocks.length
        lb.timestamp = timestamp
        return lb


    def getLatestForTrend(self, start_time=None, end_time=None):
        if start_time is None:
            start_time = TimeHelpers.tsl() - Constants.DAY_IN_MS

        if end_time is None:
            end_time = TimeHelpers.tsl()

        return self.get(LibreBlock.bytestart == 0 and LibreBlock.byteend >= 344 and LibreBlock.timestamp >= start_time and LibreBlock.timestamp <= end_time).order_by("timestamp desc")


    def getForTimestamp(self, timestamp):
        margin = (3 * 1000)

        return self.get(LibreBlock.timestamp >= timestamp-margin and LibreBlock.timestamp <= timestamp + margin)


    def UpdateBgVal(self, timestamp, calculated_value):
        libreBlock = self.getForTimestamp(timestamp)
        if libreBlock is None:
            return

        log.info("Updating bg for timestamp {}".format(timestamp))
        libreBlock.calculated_bg = calculated_value
        libreBlock.save()
