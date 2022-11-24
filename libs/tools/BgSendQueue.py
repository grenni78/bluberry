# pylint: disable = E0213
"""

import com.activeandroid.Model;
import com.activeandroid.annotation.Column;
import com.activeandroid.annotation.Table;
import com.activeandroid.query.Delete;
import com.activeandroid.query.Select;
import com.eveningoutpost.dexdrip.BestGlucose;
import com.eveningoutpost.dexdrip.GcmActivity;
import com.eveningoutpost.dexdrip.Home;
import com.eveningoutpost.dexdrip.Models.BgReading;
import com.eveningoutpost.dexdrip.Models.Calibration;
import com.eveningoutpost.dexdrip.Models.JoH;
import com.eveningoutpost.dexdrip.Models.LibreBlock;
import com.eveningoutpost.dexdrip.Models.Noise;
import com.eveningoutpost.dexdrip.Models.UserError;
import com.eveningoutpost.dexdrip.Models.UserError.Log;
import com.eveningoutpost.dexdrip.NewDataObserver;
import com.eveningoutpost.dexdrip.Services.SyncService;
import com.eveningoutpost.dexdrip.WidgetUpdateService;
import com.eveningoutpost.dexdrip.calibrations.PluggableCalibration;
import com.eveningoutpost.dexdrip.utils.PowerStateReceiver;
import com.eveningoutpost.dexdrip.xDripWidget;
import com.rits.cloning.Cloner;


"""

from peewee import *
from bluberry import *
from libs.models.bgReading import BgReading
from libs.models import Noise
from libs.models.UploaderQueue import *
from libs.tools import Intents


class BgSendQueue(Model):

    _ID = IdentityField()

    bgReading = BareField(index = True)

    success = BooleanField(index = True)

    mongo_success = BooleanField(index = True)

    operation_type = CharField()

    def mongoQueue(self):
        return self.get(BgSendQueue.mongo_success == False and BgSendQueue.operation_type == "create").order_by("_ID desc").limit(30)


    def cleanQueue(self):
        return self.delete().where(BgSendQueue.mongo_success == True and BgSendQueue.operation_type == "create")


    def addToQueue(self, bgReading, operation_type):
        bgSendQueue = BgSendQueue()
        bgSendQueue.operation_type = operation_type
        bgSendQueue.bgReading = bgReading
        bgSendQueue.success = False
        bgSendQueue.mongo_success = False
        bgSendQueue.save()
        app.log.info("BGQueue", "New value added to queue!")


    def handleNewBgReading(bgReading, operation_type, quick = False):

        try:
            UploaderQueue.newEntry(operation_type, bgReading)

            # all this other UI stuff probably shouldn't be here but in lieu of a better method we keep with it..

            if not quick:
                # start Service
                pass
            # TODO extract to separate class/method and put in to new data observer

            dg = None
            bundle = {}

            if app.ppref.getValue("broadcast_data_through_intents", False) :
                app.log.info("SENSOR QUEUE:", "Broadcast data")

                # TODO this cannot handle out of sequence data due to displayGlucose taking most recent?!
                # TODO can we do something with munging for quick data and getDisplayGlucose for non quick?
                # use display glucose if enabled and available

                noiseBlockLevel = Noise.getNoiseBlockLevel()
                bundle[Intents.EXTRA_NOISE_BLOCK_LEVEL] = noiseBlockLevel
                bundle[Intents.EXTRA_NS_NOISE_LEVEL] = bgReading.noise

                dg = BestGlucose.getDisplayGlucose()

                if app.ppref.getValue("broadcast_data_use_best_glucose", False) and dg is not None :
                    bundle[Intents.EXTRA_NOISE] = dg.noise
                    bundle[Intents.EXTRA_NOISE_WARNING] = dg.warning

                    if dg.noise <= noiseBlockLevel :
                        bundle[Intents.EXTRA_BG_ESTIMATE] = dg.mgdl
                        bundle[Intents.EXTRA_BG_SLOPE] = dg.slope

                        # hide slope possibly needs to be handled properly
                        if bgReading.hide_slope:
                            bundle[Intents.EXTRA_BG_SLOPE_NAME] = "9"   # not sure if this is right has been this way for a long time
                        else:
                            bundle[Intents.EXTRA_BG_SLOPE_NAME] = dg.delta_name
                    else:
                        msg = "Not locally broadcasting due to noise block level of: " + noiseBlockLevel + " and noise of; " + MathHelpers.roundDouble(dg.noise, 1)
                        app.log.info("LocalBroadcast: " + msg)
                        userinteract.warn(msg)
                else:
                    # better to use the display glucose version above
                    bundle[Intents.EXTRA_NOISE] = BgGraphBuilder.last_noise
                    if BgGraphBuilder.last_noise <= noiseBlockLevel :
                        # standard xdrip-classic data set
                        bundle[Intents.EXTRA_BG_ESTIMATE] = bgReading.calculated_value

                        #TODO: change back to bgReading.calculated_value_slope if it will also get calculated for Share data
                        # bundle.putDouble(Intents.EXTRA_BG_SLOPE, bgReading.calculated_value_slope);
                        bundle[Intents.EXTRA_BG_SLOPE] = bgReading.currentSlope()
                        if bgReading.hide_slope:
                            bundle[Intents.EXTRA_BG_SLOPE_NAME] = "9" # not sure if this is right but has been this way for a long time
                        else:
                            bundle[Intents.EXTRA_BG_SLOPE_NAME] = bgReading.slopeName()

                    else:
                        msg = "Not locally broadcasting due to noise block level of: " + noiseBlockLevel + " and noise of; " + MathHelpers.roundDouble(BgGraphBuilder.last_noise, 1)
                        app.Log.info("LocalBroadcast " + msg)
                        userinteract.warn(msg)


                bundle[Intents.EXTRA_SENSOR_BATTERY] = PowerStateReceiver.getBatteryLevel(context)
                bundle[Intents.EXTRA_TIMESTAMP] = bgReading.timestamp

                # raw value
                slope = 0
                intercept = 0
                scale = 0
                filtered = 0
                unfiltered = 0
                raw = 0
                cal = Calibration.lastValid()
                if cal is not None:
                    # slope/intercept/scale like uploaded to NightScout
                    if cal.check_in:
                        slope = cal.first_slope
                        intercept = cal.first_intercept
                        scale = cal.first_scale
                    else:
                        slope = 1000 / cal.slope
                        intercept = (cal.intercept * -1000) / (cal.slope)
                        scale = 1

                    unfiltered = bgReading.usedRaw() * 1000
                    filtered = bgReading.ageAdjustedFiltered() * 1000

                # raw logic from https://github.com/nightscout/cgm-remote-monitor/blob/master/lib/plugins/rawbg.js#L59
                if slope != 0 and intercept != 0 and scale != 0 :
                    if (filtered == 0) or (bgReading.calculated_value < 40) :
                        raw = scale * (unfiltered - intercept) / slope
                    else:
                        ratio = scale * (filtered - intercept) / slope / bgReading.calculated_value
                        raw = scale * (unfiltered - intercept) / slope / ratio

                bundle[Intents.EXTRA_RAW] = raw
                intent = Intent(Intents.ACTION_NEW_BG_ESTIMATE)
                intent.putExtras(bundle)
                intent.addFlags(Intent.FLAG_INCLUDE_STOPPED_PACKAGES)

                userinteract.broadcast(intent)

            if not quick:
                NewDataObserver.newBgReading(bgReading)
                LibreBlock.UpdateBgVal(bgReading.timestamp, bgReading.calculated_value) # TODO move this to NewDataObserver


            if app.ppref.getValue("plus_follow_master", False):
                if app.ppref.getValue("display_glucose_from_plugin", False):
                    # TODO does this currently ignore noise or is noise properly calculated on the follower?
                    # munge bgReading for follower TODO will probably want extra option for this in future
                    # TODO we maybe don't need deep clone for this! Check how value will be used below
                    GcmActivity.syncBGReading(PluggableCalibration.mungeBgReading(copy.deep_copy(bgReading)))
                else:
                    # send as is
                    GcmActivity.syncBGReading(bgReading)


            # process the uploader queue
            if ratelimits.ratelimit("start-sync-service", 30):
                Services.startService(SyncService)
        except:
            pass


    def markMongoSuccess(self):
        self.mongo_success = True
        self.save()

