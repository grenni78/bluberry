
"""

import com.activeandroid.Cache;
import com.activeandroid.Model;
import com.activeandroid.annotation.Column;
import com.activeandroid.annotation.Table;
import com.activeandroid.query.Delete;
import com.activeandroid.query.Select;
import com.activeandroid.util.SQLiteUtils;
import com.eveningoutpost.dexdrip.Models.BgReading;
import com.eveningoutpost.dexdrip.Models.BloodTest;
import com.eveningoutpost.dexdrip.Models.Calibration;
import com.eveningoutpost.dexdrip.Models.JoH;
import com.eveningoutpost.dexdrip.Models.Treatments;
import com.eveningoutpost.dexdrip.Models.UserError;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.annotations.Expose;

import static com.eveningoutpost.dexdrip.Services.SyncService.startSyncService;
"""
from peewee import *
import json
import urllib
from bluberry import *
from libs.tools import TimeHelpers
from libs.StatusItem import *

class UploaderQueue(Model):
    d = False

    _ID = IdentityField()
    timestamp = IntegerField(index=True)
    action = CharField(index=True)
    otype = CharField(index=True)
    reference_id = IntegerField()
    reference_uuid = CharField()
    bitfield_wanted = IntegerField(index=True)
    bitfield_complete = IntegerField(index=True)


    # table creation
    patched = False
    last_cleanup = 0
    last_new_entry = 0
    last_query = 0

    # mega status cache
    processedBaseURIs = []
    processedBaseURInames = []


    # Bitfields
    MONGO_DIRECT = 1
    NIGHTSCOUT_RESTAPI = 1 << 1
    TEST_OUTPUT_PLUGIN = 1 << 2
    INFLUXDB_RESTAPI   = 1 << 3
    WATCH_WEARAPI      = 1 << 4


    DEFAULT_UPLOAD_CIRCUITS = 0

    circuits_for_stats = {
        MONGO_DIRECT : "Mongo Direct",
        NIGHTSCOUT_RESTAPI : "Nightscout REST",
        TEST_OUTPUT_PLUGIN : "Test Plugin",
        INFLUXDB_RESTAPI : "InfluxDB REST",
        WATCH_WEARAPI : "Watch Wear API"
    }


    # patches and saves
    def saveit(self):
        self.fixUpTable()
        self.save()


    def completed(self, bitfield):
        app.log.info("Marking bitfield " + bitfield + " completed on: " + self.getId() + " / " + self.action + " " + self.type + " " + self.reference_id)
        self.bitfield_complete = self.bitfield_complete | bitfield
        return self.saveit()


    def toS(self):
        return json.dumps(self)


    def newEntry(self, action, obj):
        app.log.info("new entry called")
        result = UploaderQueue()
        
        result.bitfield_wanted = self.DEFAULT_UPLOAD_CIRCUITS
        if app.pref.getValue("cloud_storage_mongodb_enable",False):
            result.bitfield_wanted = result.bitfield_wanted | self.MONGO_DIRECT
        if app.pref.getValue("cloud_storage_api_enable", False):
            result.bitfield_wanted = result.bitfield_wanted | self.NIGHTSCOUT_RESTAPI
        if app.pref.getValue("cloud_storage_influxdb_enable", False):
            result.bitfield_wanted = result.bitfield_wanted | self.INFLUXDB_RESTAPI
        if app.pref.getValue("wear_sync", False):
            result.bitfield_wanted = result.bitfield_wanted | self.WATCH_WEARAPI

        if result.bitfield_wanted == 0:
            return None; # no queue required
        result.timestamp = TimeHelpers.tsl()
        result.reference_id = obj.getId()

        if result.reference_uuid is None:
            try:
                result.reference_uuid = obj.uuid
            except:
                app.log.warn("reference_uuid was null so refusing to create new entry")
                return None

        if result.reference_id < 0 :
            app.log.warn("ERROR ref id was: " + result.reference_id + " for uuid: " + result.reference_uuid + " refusing to create")
            return None

        result.action = action

        result.bitfield_complete = 0
        result.type = obj.__class__.__name__
        result.saveit()
        if self.d:
            app.log.info(result.toS())

        self.last_new_entry = TimeHelpers.tsl()
        return result


    # TODO remove duplicated functionality, replace with generic multi-purpose method
    def newEntryForWatch(self, action, obj):
        app.log.info("new entry called for watch")
        result = UploaderQueue()
        result.bitfield_wanted = self.DEFAULT_UPLOAD_CIRCUITS
        if app.pref.getValue("wear_sync", False):
            result.bitfield_wanted = result.bitfield_wanted | self.WATCH_WEARAPI
        if result.bitfield_wanted == 0:
            return None # no queue required
        result.timestamp = TimeHelpers.tsl()
        result.reference_id = obj.getId()

        if result.reference_uuid is None:
            try:
                result.reference_uuid = obj.uuid
            except:
                app.log.warn("reference_uuid was null so refusing to create new entry")
                return None

        if result.reference_id < 0:
            app.log.warn("Watch ERROR ref id was: " + result.reference_id + " for uuid: " + result.reference_uuid + " refusing to create")
            return None

        result.action = action

        result.bitfield_complete = 0
        result.type = obj.__class__.__name__
        result.saveit()
        if self.d:
            app.log.info(result.toS())

        self.last_new_entry = TimeHelpers.tsl()
        return result


    def getPendingbyType(self, className, bitfield, limit = 300):
        if self.d:
            app.log.info("get Pending by type: " + className)

        self.last_query = TimeHelpers.tsl()
        try:
            return self.get(UploaderQueue.otype == className and (UploaderQueue.bitfield_wanted & bitfield) == bitfield and (UploaderQueue.bitfield_complete & bitfield) != bitfield).order_by("timestamp asc, _id asc").limit(limit)
        except AssertionError as e:
            app.log.info("Exception: ", e)
            self.fixUpTable()
            return []


    def getLegacyCount(self, which, rest, mongo, und):
        try:
            where = " "
            if rest is not None:
                where += " success = "
            if rest:
                where += "1 "
            else:
                where += "0 "
            if und is not None:
                if und:
                    where += " and "
                else:
                    where += " or "
            if mongo is not None:
                where += " mongo_success = "
                if mongo:
                    where += "1 "
                else:
                    where += "0 "
            query = " COUNT(*) as total FROM " + which
            if len(where) > 0:
                query += where
            resultCursor = self.database.query(query)
            return resultCursor.scalar()

        except AssertionError as e:
            app.log.info("Got exception getting count: ", e)
            return -1


    def getCount(self, where):
        try:
            query = UploaderQueue.Select(fn.COUNT("*")).where(where)

            return query.scalar()

        except AssertionError as e:
            app.log.info("Got exception getting count: ", e)
            return 0


    def getClasses(self):
        self.fixUpTable()
        results = []
        query = UploaderQueue.select("distinct otype as otypes")
        
        for result in query:
            results.append(result)

        return results


    def getQueueSizeByType(self, className, bitfield, completed):
        self.fixUpTable()
        if self.d:
            app.log.info("get Pending count by type: " + className)

        try:
            where = " where otype = '" + className + "'" + " and (bitfield_wanted & " + bitfield + ") == " + bitfield + " and (bitfield_complete & " + bitfield + ") "
            if completed:
                where += "== "
            else:
                where += "!= "
            where += bitfield

            return self.getCount(where)

        except AssertionError as e:
            app.log.info("Exception: ", e)
            self.fixUpTable()
            return 0


    def emptyQueue(self):
        self.fixUpTable()
        try:
            self.delete()
            self.last_cleanup = TimeHelpers.tsl()
            userinteract.info("emptyQueue", "Upload queue emptied")
        except AssertionError as e:
            app.log.warn("Exception cleaning uploader queue: ", e)


    def cleanQueue(self):
        # delete all completed records > 24 hours old
        self.fixUpTable()
        try:
            self.delete().where("timestamp < ?", TimeHelpers.tsl() - 86400000).where("bitfield_wanted == bitfield_complete")

            # delete everything > 7 days old
            self.delete().where("timestamp < ?", TimeHelpers.tsl() - 86400000 * 7)
        except AssertionError as e:
            app.log.info("Exception cleaning uploader queue: ", e)

        self.last_cleanup = TimeHelpers.tsl()


    def fixUpTable(self):
        pass


    def getCircuitName(self, i):
        try:
            return self.circuits_for_stats[1]
        except:
            return "Unknown Circuit"


    def megaStatus(self):
        l = []
        # per circuit
        for i in range(len(self.circuits_for_stats)) :
            for bitfield in self.circuits_for_stats:

                # per class of data
                for t in self.getClasses():
                    
                    count_pending = self.getQueueSizeByType(t, bitfield, False)
                    count_completed = self.getQueueSizeByType(t, bitfield, True)
                    count_total = count_pending + count_completed

                    if count_total > 0:
                        highlight = StatusItem.Highlight.NORMAL
                        if count_pending > 1000:
                            highlight = StatusItem.Highlight.BAD

                        l.append(StatusItem(self.circuits_for_stats[i], count_pending + " " + t, highlight,""))

        if UploaderTask.exception is not None:
            l.append(StatusItem("Exception", UploaderTask.exception, StatusItem.Highlight.BAD, "long-press"))

        if last_query > 0:
            l.append(StatusItem("Last poll", TimeHelpers.niceTimeSince(last_query) + " ago", StatusItem.Highlight.NORMAL, "long-press",))

        # enumerate status items for nightscout rest-api
        if app.pref.getValue("cloud_storage_api_enable",False):
            try:

                if (self.processedBaseURIs is None) or (ratelimits.ratelimit("uploader-base-urls-cache", 60)):
                    # Rebuild url cache
                    self.processedBaseURIs = []
                    self.processedBaseURInames = []
                    baseURLSettings = app.pref.getValue("cloud_storage_api_base","")
                    baseURIs = []

                    for baseURLSetting in baseURLSettings.split(" "):
                        baseURL = baseURLSetting.trim()
                        if len(baseURL) == 0:
                            continue
                        baseURL = baseURL.rstrip('/') + "/"
                        baseURIs.append(baseURL)

                    for baseURI in baseURIs:
                        uri = urllib.parse.urlparse(baseURI)
                        baseURL = re.sub("//[^@]+@", "//", baseURI)
                        self.processedBaseURIs.push(baseURL)
                        self.processedBaseURInames.push(uri.hostname)

                # lookup status for each url in cache
                for pu in processedBaseURIs :
                    try:
                        store_marker = "nightscout-status-poll-" + pu
                        status = json.loads(app.ppref.getValue(store_marker, "{}"))
                        highlight = StatusItem.Highlight.NORMAL
                        if hightlight[0:2] == "0.8":
                            highlight = StatusItem.Highlight.CRITICAL
                        l.append(StatusItem(pu, status.name + " " + status.version, highlight, "long-press"))

                        if "careportalEnabled" in status and not status.careportalEnabled:
                            l.append(StatusItem("Config error in Nightscout at " + pu, "You must enable the careportal plugin or treatment sync will be broken", StatusItem.Highlight.BAD, "long-press"))


                        extended = status.extendedSettings
                        dextended = extended.devicestatus
                        if dextended is None or (not "advanced" in dextended) or (not dextended.advanced) :
                            l.append(StatusItem("Config error in Nightscout at " + pu, "You must set DEVICESTATUS_ADVANCED env item to True for multiple battery status to work properly", StatusItem.Highlight.BAD, "long-press"))

                    except AssertionError as e:
                        app.log.debug("error in loading nightscout settings: ",e)

            except AssertionError as e:
                app.log.debug("error using cloud storage: ",e)

        ##

        if NightscoutUploader.last_exception_time > 0:
            highlight = StatusItem.Highlight.NORMAL
            if TimeHelpers.msSince(NightscoutUploader.last_exception_time) < (Constants.MINUTE_IN_MS * 6):
                highlight = StatusItem.Highlight.BAD
            l.append(StatusItem("REST-API problem\n" + TimeHelpers.dateTimeText(NightscoutUploader.last_exception_time) + " (" + NightscoutUploader.last_exception_count + ")", NightscoutUploader.last_exception, highlight))

        if last_cleanup > 0:
            l.append(StatusItem("Last clean up", TimeHelpers.niceTimeSince(last_cleanup) + " ago"))

        return l


    def refreshStatus(self, store_marker):
        app.ppref.setValue(store_marker, "")
        if ratelimits.ratelimit("nightscout-manual-poll", 15):
            self.startSyncService(100)
