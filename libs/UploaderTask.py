

"""

import com.eveningoutpost.dexdrip.InfluxDB.InfluxDBUploader;
import com.eveningoutpost.dexdrip.Models.BgReading;
import com.eveningoutpost.dexdrip.Models.BloodTest;
import com.eveningoutpost.dexdrip.Models.Calibration;
import com.eveningoutpost.dexdrip.Models.JoH;
import com.eveningoutpost.dexdrip.Models.Treatments;
import com.eveningoutpost.dexdrip.Models.UserError.Log;
import com.eveningoutpost.dexdrip.wearintegration.WatchUpdaterService;
import com.eveningoutpost.dexdrip.Services.SyncService;
import com.eveningoutpost.dexdrip.xdrip;

"""
from bluberry import *
from libs.models.UploaderQueue import UploaderQueue
from libs.models.bgReading import BgReading
from libs.models.Calibration import Calibration
## TODO unify treatment handling



exception = None

BACKFILLING_BOOSTER = "backfilling-nightscout"

def doInBackground(urls):
    try:
        circuits = []
        types = []

        types.append("BgReading");
        types.append("Calibration")
        types.append("BloodTest")
        types.append("Treatments")

        if app.pref.getValue("wear_sync",False):
            circuits.append(UploaderQueue.WATCH_WEARAPI)

        if app.pref.getValue("cloud_storage_mongodb_enable",False):
            circuits.append(UploaderQueue.MONGO_DIRECT)

        if app.pref.getValue("cloud_storage_api_enable", False):
            if app.pref.getValue("cloud_storage_api_use_mobile", True):
                circuits.append(UploaderQueue.NIGHTSCOUT_RESTAPI)
            else:
                app.log.warn("Skipping Nightscout upload due to mobile data only")

        if app.pref.getValue("cloud_storage_influxdb_enable",False):
            circuits.append(UploaderQueue.INFLUXDB_RESTAPI)


        for THIS_QUEUE in circuits:

            bgReadings = []
            calibrations = []
            bloodtests = []
            treatmentsAdd = []
            treatmentsDel = []
            items = []

            for t in types:
                bgups = UploaderQueue().getPendingbyType(t, THIS_QUEUE)
                if bgups is not None:
                    for up in bgups:
                        if up.action == "insert" or up.action == "update" or up.action == "create":
                            items.append(up)
                            if t is BgReading :
                                this_bg = BgReading().byid(up.reference_id)
                                if this_bg is not None:
                                    bgReadings.append(this_bg)
                                else:
                                    app.log.warn("BgReading with ID: " + up.reference_id + " appears to have been deleted")

                            elif t  is Calibration:
                                this_cal = Calibration().byid(up.reference_id)
                                if this_cal is not None and this_cal.isValid():
                                    calibrations.append(this_cal)
                                else:
                                    app.log.warn("Calibration with ID: " + up.reference_id + " appears to have been deleted")

                            elif t is BloodTest:
                                this_bt = BloodTest().byid(up.reference_id)
                                if this_bt is not None:
                                    bloodtests.append(this_bt)
                                else:
                                    app.log.warn("Bloodtest with ID: " + up.reference_id + " appears to have been deleted")

                            elif t is Treatments:
                                this_treat = Treatments().byid(up.reference_id)
                                if this_treat is not None:
                                    treatmentsAdd.append(this_treat)
                                else:
                                    app.log.warn("Treatments with ID: " + up.reference_id + " appears to have been deleted")
                        elif up.action == "delete":
                            if (THIS_QUEUE == UploaderQueue.WATCH_WEARAPI or THIS_QUEUE == UploaderQueue.NIGHTSCOUT_RESTAPI) and t is Treatments :
                                items.append(up)
                                app.log.warn("Delete Treatments with ID: " + up.reference_uuid)
                                treatmentsDel.append(up.reference_uuid)
                            else:
                                if up.reference_uuid is not None:
                                    app.log.info(UploaderQueue().getCircuitName(THIS_QUEUE) + " delete not yet implemented: " + up.reference_uuid)
                                    up.completed(THIS_QUEUE); # mark as completed so as not to tie up the queue for now
                        else:
                                app.log.info("Unsupported operation type for " + type + " " + up.action)

            if len(bgReadings) > 0 or len(calibrations) > 0 or len(bloodtests) > 0 or len(treatmentsAdd) > 0 or len(treatmentsDel) > 0 or len(UploaderQueue().getPendingbyType("Treatments", THIS_QUEUE, 1)) :

                app.log.info(UploaderQueue().getCircuitName(THIS_QUEUE) + " Processing: " + len(bgReadings) + " BgReadings and " + len(calibrations) + " Calibrations " + len(bloodtests) + " bloodtests " + len(treatmentsAdd) + " treatmentsAdd " + len(treatmentsDel) + " treatmentsDel")
                uploadStatus = False

                if THIS_QUEUE == UploaderQueue.MONGO_DIRECT:
                    uploader = NightscoutUploader()
                    uploadStatus = uploader.uploadMongo(bgReadings, calibrations, calibrations)
                elif THIS_QUEUE == UploaderQueue.NIGHTSCOUT_RESTAPI:
                    uploader = NightscoutUploader()
                    uploadStatus = uploader.uploadRest(bgReadings, bloodtests, calibrations)
                elif THIS_QUEUE == UploaderQueue.INFLUXDB_RESTAPI:
                    influxDBUploader =  InfluxDBUploader()
                    uploadStatus = influxDBUploader.upload(bgReadings, calibrations, calibrations)
                elif THIS_QUEUE == UploaderQueue.WATCH_WEARAPI:
                    uploadStatus = WatchUpdaterService.sendWearUpload(bgReadings, calibrations, bloodtests, treatmentsAdd, treatmentsDel)

                # TODO some kind of fail counter?
                if uploadStatus:
                    for up in items:
                        up.completed(THIS_QUEUE) # approve all types for this queue

                    app.log.info(UploaderQueue.getCircuitName(THIS_QUEUE) + " Marking: " + items.size() + " Items as successful")

                    if PersistentStore.getValue(BACKFILLING_BOOSTER, False):
                        app.log.info("Scheduling boosted repeat query")
                        SyncService.startSyncService(2000)

            else:
                app.log.info("Nothing to upload for: " + UploaderQueue().getCircuitName(THIS_QUEUE))
                if app.ppref.getValue(BACKFILLING_BOOSTER):
                    app.ppref.setValue(BACKFILLING_BOOSTER, False)
                    app.log.info("Switched off backfilling booster")

    except AssertionError as e:
        app.log.debug("caught exception", e)
        exception = e
        return None

    return 0

