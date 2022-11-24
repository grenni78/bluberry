"""
 
"""

from libs.FauxActivity import FauxActivity
from libs.tools.ByteHelpers import *
import logging
import thread

log = logging.getLogger(__name__)
gcm_queue = []

class GcmActivity(FauxActivity):

    PLAY_SERVICES_RESOLUTION_REQUEST = 9000
    TASK_TAG_CHARGING = "charging"
    TASK_TAG_UNMETERED = "unmetered"

    last_sync_request = 0
    last_sync_fill = 0
    bg_sync_backoff = 0
    last_ping_request = 0
    last_rlcl_request = 0
    msgId = 1
    token = None
    senderid = None
    
    queue_lock = Object()
    mRegistrationBroadcastReceiver = None
    cease_all_activity = False
    cease_all_checked = False
    last_ack = -1
    last_send = -1
    last_send_previous = -1
    MAX_ACK_OUTSTANDING_MS = 3600000
    recursion_depth = 0
    last_bridge_battery = -1
    last_parakeet_battery = -1
    MAX_RECURSION = 30
    MAX_QUEUE_SIZE = 300
    RELIABLE_MAX_PAYLOAD = 1800
    RELIABLE_MAX_BINARY_PAYLOAD = 1400

    threads = []


    @staticmethod
    def getSensorCalibrations(son):
        sensorCalibrations = json.loads(json)
        log.info("After fromjson sensorCalibrations are {}".format(sensorCalibrations))
        return sensorCalibrations


    @staticmethod
    def sensorAndCalibrationsToJson(sensor, limit):
        sensorCalibrations = []
        sensorCalibrations.push(SensorCalibrations())
        sensorCalibrations[0].sensor = sensor
        sensorCalibrations[0].calibrations = Calibration().getCalibrationsForSensor(sensor, limit)
        log.debug("calibrations size ".format(len(sensorCalibrations[0].calibrations)))

        output = json.dumps(sensorCalibrations)
        log.debug("sensorAndCalibrationsToJson created the string {}".format(output))
        return output

    @staticmethod
    def getNewCalibration(json):
        try:
            newCalibrationArray = json.loads(json)
        except JSONDecodeError as err:
            log.debug("Error creating newCalibrationArray", err)
            return None
        
        log.debug("After fromjson NewCalibration are ", newCalibrationArray)
        return newCalibrationArray[0]


    @staticmethod
    def newCalibrationToJson(bgValue, uuid, offset):
        newCalibrationArray = []
        newCalibration = NewCalibration()
        newCalibration.bgValue = bgValue
        newCalibration.uuid = uuid
        newCalibration.timestamp = datetime.tsl()
        newCalibration.offset = offset
        newCalibrationArray[0] = newCalibration

        output = json.dumps(newCalibrationArray)
        log.info("newCalibrationToJson Created the string: {}".format(output))
        return output


    @staticmethod
    def upsertSensorCalibratonsFromJson(json):
        log.info("upsertSensorCalibratonsFromJson called")
        sensorCalibrations = GcmActivity.getSensorCalibrations(json)
        for SensorCalibration in sensorCalibrations:
            Sensor.upsertFromMaster(SensorCalibration.sensor)
            for calibration in calibrations:
                log.info("upsertSensorCalibratonsFromJson updating calibration: ".format(calibration.uuid))
                Calibration.upsertFromMaster(calibration)


    def queueAction(self, reference):
        log.info("Received ACK, Queue Size: " + len(gcm_queue) + " " + reference)
        last_ack = TimeHelpers.tsl()
        for datum in gcm_queue:
            thisref = datum.bundle.getString("action") + datum.bundle.getString("payload")
            if thisref == reference:
                gcm_queue.remove(datum)
                log.info( "Removing acked queue item: " + reference)
                break


    def checkCease(self):
        if not self.cease_all_checked and not self.cease_all_activity:
            self.cease_all_activity = app.pref.getValue("disable_all_sync", False)
            self.cease_all_checked = True


    def sendMessage(self, action, identity = None, payload = None, bpayload = None):
        self.checkCease();
        if cease_all_activity:
            return None
        if identity is None:
            identity = GcmActivity.myIdentity()
        
        start_new_thread(GcmActivity.sendMessageNow,(identity, action, payload, bpayload))
        return "sent async"


    def syncBGReading(self, bgReading):
        log.info("syncBGReading called")
        if (ratelimits.ratelimit("gcm-bgs-batch", 15)):
            GcmActivity.sendMessage(action = "bgs", payload = json.dunps(bgReading))
        else:
            self.ppref.appendBytes("gcm-bgs-batch-queue", bgReading.toMessage())
            app.ppref.setLong("gcm-bgs-batch-time", TimeHelpers.tsl())
            processBgsBatch(false)
        

    # called only from interactive or evaluated new data
    def syncBloodTests(self):
        log.debug("syncBloodTests called")
        if ratelimits.ratelimit("gcm-btmm-send", 4):
            this_btmm = BloodTest.toMultiMessage(BloodTest.last(12))
            if differentBytes("gcm-btmm-last-send", this_btmm):
                GcmActivity.sendMessage("btmm", compressBytesforPayload(this_btmm))
                userinteract.refreshBGCharts()
            else:
                log.debug("btmm message is identical to previously sent")

    def processBgsBatch(self, send_now):
        app.ppref.getValue("gcm-bgs-batch-queue")
        log.debug("Processing BgsBatch: length: {} now: {}".format(value.length, send_now))
        if send_now or len(value) > (RELIABLE_MAX_BINARY_PAYLOAD - 100):
            if len(value):
                app.ppref.setString("gcm-bgs-batch-queue", "")
                GcmActivity.sendMessage("bgmm", value)

            log.info("Sent batch")
        else:
            def runner():
                time.sleep(5)
                if TimeHelpers.msSince(app.ppref.getValue("gcm-bgs-batch-time")) > 4000:
                    log.debug("Progressing BGSbatch due to timeout")
                    self.processBgsBatch(True)

            start_new_thread(runner)


    def syncSensor(self, sensor, forceSend):
        log.info("syncSensor called")
        if sensor == None:
            log.error("syncSensor sensor is None")
            return

        if not forceSend and (not ratelimits.pratelimit("GcmSensorCalibrationsUpdate", 300)):
            log.info("syncSensor not sending data, because of rate limiter")
            return

        # automatically find a suitable volume of payload data
        for limit in range(9,0,-1):
            json = self.sensorAndCalibrationsToJson(sensor, limit)
            log.debug("sensor json size: limit: {} len: {}".format(limit, len(CipherUtils.compressEncryptString(json))))
            if len(CipherUtils.compressEncryptString(json)) <= RELIABLE_MAX_PAYLOAD:
                json_hash = CipherUtils.getSHA256(json)
                if not forceSend or (not app.ppref.getValue("last-syncsensor-json") == json_hash):
                    app.ppref.setValue("last-syncsensor-json", json_hash)
                    GcmActivity.sendMessage("sensorupdate", json)
                else:
                    log.debug("syncSensor: data is duplicate of last data: {}".format(json))
                    break

                break # send only one


    def requestPing(self):
        if (TimeHelpers.ts() - self.last_ping_request) > (60 * 1000 * 15):
            last_ping_request = TimeHelpers.ts()
            log.debug("Sending ping")
            if ratelimits.pratelimit("gcm-ping", 1199):
                GcmActivity.sendMessage("ping", "{}")
        else:
            log.debug("Already requested ping recently")


    def requestRollCall(self):
        if TimeHelpers.tsl() - self.last_rlcl_request > (60 * 1000):
            self.last_rlcl_request = TimeHelpers.tsl()
            if ratelimits.pratelimit("gcm-rlcl", 3600):
               GcmActivity.sendMessage("rlcl", "{}")


    @staticmethod
    def sendLocation(location):
        if ratelimits.pratelimit("gcm-plu", 180):
            GcmActivity.sendMessage("plu", location)


    @staticmethod
    def sendSensorBattery(battery):
        if ratelimits.pratelimit("gcm-sbu", 3600):
            GcmActivity.sendMessage("sbu", str(battery))


    def sendBridgeBattery(self, battery):
        if battery != self.last_bridge_battery:
            if ratelimits.pratelimit("gcm-bbu", 1800):
                GcmActivity.sendMessage("bbu", str(battery))
                last_bridge_battery = battery


    def sendParakeetBattery(self, battery):
        if battery != self.last_parakeet_battery:
            if ratelimits.pratelimit("gcm-pbu", 1800):
                GcmActivity.sendMessage("pbu", str(battery))
                self.last_parakeet_battery = battery


    @staticmethod
    def sendNotification(title, message):
        if ratelimits.pratelimit("gcm-not", 30):
            GcmActivity.sendMessage("not", title.replace("\\^", "") + "^" + message.replace("\\^", ""))


    @staticmethod
    def sendMotionUpdate(timestamp, activity):
        if ratelimits.pratelimit("gcm-amu", 5):
            GcmActivity.sendMessage("amu","{}^{}".format(timestamp,activity))

    @staticmethod
    def sendPumpStatus(json):
        if ratelimits.pratelimit("gcm-psu", 180):
            GcmActivity.sendMessage("psu", json)


    def requestBGsync(self):
        if self.token is not None:
            if TimeHelpers.ts() - self.last_sync_request > (60 * 1000 * (5 + self.bg_sync_backoff)):
                self.last_sync_request = TimeHelpers.ts()
                if ratelimits.pratelimit("gcm-bfr", 299):
                    GcmActivity.sendMessage("bfr", "")
                self.bg_sync_backoff += 1
            else:
                log.debug("Already requested BGsync recently, backoff: {}".format(self.bg_sync_backoff))
                if TimeHelpers.ratelimit("check-queue", 20):
                    self.queueCheckOld()
        else:
            log.debug("No token for BGSync")


    def syncBGTable2(self):
        if not Sensor.isActive():
            return
        def runner():
            if ratelimits.pratelimit("last-sync-fill", 60 * (5 + bg_sync_backoff)):
                self.last_sync_fill = TimeHelpers.ts()
                self.bg_sync_backoff += 1
                # Since this is a big update, also update sensor and calibrations
                self.syncSensor(Sensor.currentSensor(), True)

                bgReadings = BgReading.latestForGraph(300, TimeHelpers.ts() - (24 * 60 * 60 * 1000))
                records = ""
                for bgReading in bgReadings:
                    myrecord = bgReading.toJSON(False)
                    records += myrecord

                log.debug("Total BGreading sync packet size: {}".format(len(records)))
                if (len(mypacket) > 0):
                    pass
                    #DisplayQRCode.uploadBytes(mypacket.getBytes(Charset.forName("UTF-8")), 2);
                else:
                    log.info("Not uploading data due to zero length")
            else:
                log.debug("Ignoring recent sync request, backoff: {}".format(bg_sync_backoff))

        self.threads.append(start_new_thread(runner))


    # callback function
    @staticmethod
    def backfillLink(self, id, key):
        log.debug("sending bfb message: {}".format(id))
        GcmActivity.sendMessage("bfb","{}^{}".format(id,key))


    def processBFPbundle(self,bundle):
        bundlea = bundle.split("\\^")
        for bgr in bundlea:
            BgReading.bgReadingInsertFromJson(bgr, False)

        self.requestSensorBatteryUpdate()
        userinteract.refreshBGCharts()


    @staticmethod
    def requestSensorBatteryUpdate(self):
        if ratelimits.pratelimit("SensorBatteryUpdateRequest", 1200):
            log.debug("Requesting Sensor Battery Update")
            GcmActivity.sendMessage("sbr", "") # request sensor battery update


    @staticmethod
    def requestSensorCalibrationsUpdate(self):
        if ratelimits.pratelimit("SensorCalibrationsUpdateRequest", 300):
            log.debug("Requesting Sensor and calibrations Update")
            GcmActivity.sendMessage("sensor_calibrations_update", "")


    @staticmethod
    def pushTreatmentAsync(self, thistreatment):
        if (thistreatment.uuid == None) or (len(thistreatment.uuid) < 5):
            return
        json = thistreatment.toJSON()
        GcmActivity.sendMessage(GcmActivity.myIdentity(), "nt", json)


    @staticmethod
    def send_ping_reply():
        log.debug("Sending ping reply")
        GcmActivity.sendMessage(GcmActivity.myIdentity(), "q", "")

    @staticmethod
    def push_delete_all_treatments(self):
        log.info("Sending push for delete all treatments")
        GcmActivity.sendMessage(GcmActivity.myIdentity(), "dat", "")

    @staticmethod
    def push_delete_treatment(self, treatment):
        log.info("Sending push for specific treatment")
        GcmActivity.sendMessage(GcmActivity.myIdentity(), "dt", treatment.uuid)


    @staticmethod
    def myIdentity():
        # TODO prefs override possible
        return app.identity


    @staticmethod
    def pushTreatmentFromPayloadString(json):
        if len(json) < 3:
            return
        log.debug("Pushing json from GCM: {}".format(json))
        Treatments.pushTreatmentFromJson(json)


    @staticmethod
    def pushCalibration(bg_value, seconds_ago):
        pass

    @staticmethod
    def pushCalibration2(double bgValue, String uuid, long offset) {
        log.info("pushCalibration2 called: {%1f} {} {}".format(bgValue, uuid, offset))

        unit = app.pref.getValue("units", "mgdl")

        if unit == "mgdl":
            bgValue = bgValue * Constants.MMOLL_TO_MGDL

        if (bgValue < 40) or (bgValue > 400):
            log.error("Invalid out of range calibration glucose mg/dl value of: {}".format(bgValue)
            userinteract.error("Calibration out of range: {} mg/dl".format(bgValue))
            return

        json = CgmActivity.newCalibrationToJson(bgValue, uuid, offset)
        GcmActivity.sendMessage(myIdentity(), "cal2", json)


    @staticmethod
    def clearLastCalibration(uuid):
        GcmActivity.sendMessage(GcmActivity.myIdentity(), "clc", uuid)


    def sendMessageNow(identity, action, payload, bpayload):

        log.info("Sendmessage called: {} {} {}".format(identity, action, payload))
        msg = ""
        try:

            if identity == None:
                log.error("identity is null cannot sendMessage")
                return ""

            data = {}
            data["action"] = action
            data["identity"] = identity

            if action == "sensorupdate":
                ce_payload = CipherUtils.compressEncryptString(payload)
                log.info("sensor length CipherUtils.encryptBytes ce_payload length: " + len(ce_payload))
                data["payload"] = ce_payload
                log.debug("sending data (len:{}) {}".format(len(ce_payload), ce_payload))
            else:
                if (bpayload is not None) and (len(bpayload) > 0):
                    data["payload"] = CipherUtils.encryptBytesToString(b"".join([bpayload, ByteHelpers.bchecksum(bpayload)])) # don't double sum
                elif len(payload > 0:
                    data["payload"] = CipherUtils.encryptString(payload)
                else:
                    data["payload"] = ""

            if len(gcm_queue) < MAX_QUEUE_SIZE:
                if GcmActivity.shouldAddQueue(data):
                    gcm_queue.add(new GCM_data(data))
            else:
                log.error("Queue size exceeded")
                userinteraction.error("Maximum Sync Queue size Exceeded!")
            
            final GoogleCloudMessaging gcm = GoogleCloudMessaging.getInstance(xdrip.getAppContext());
            if (token == null) {
                Log.e(TAG, "GCM token is null - cannot sendMessage");
                return "";
            }
            String messageid = Integer.toString(msgId.incrementAndGet());
            gcm.send(senderid + "@gcm.googleapis.com", messageid, data);
            if (last_ack == -1) last_ack = JoH.ts();
            last_send_previous = last_send;
            last_send = JoH.ts();
            msg = "Sent message OK " + messageid;
        } catch (IOException ex) {
            msg = "Error :" + ex.getMessage();
        }
        Log.d(TAG, "Return msg in SendMessage: " + msg);
        return msg;
    }

    private static boolean shouldAddQueue(Bundle data) {
        final String action = data.getString("action");
        if (action == null) return false;
        switch (action) {
            // one shot action types where multi queuing is not needed
            case "ping":
            case "rlcl":
            case "sbr":
            case "bfr":
                synchronized (queue_lock) {
                    for (GCM_data qdata : gcm_queue) {
                        try {
                            if (qdata.bundle.getString("action").equals(action)) {
                                Log.d(TAG, "Skipping queue add for duplicate action: " + action);
                                return false;
                            }
                        } catch (NullPointerException e) {
                            //
                        }
                    }
                }
                return true;
            default:
                return true;
        }
    }

    private static void fmSend(Bundle data) {
        final FirebaseMessaging fm = FirebaseMessaging.getInstance();
        if (senderid != null) {
            fm.send(new RemoteMessage.Builder(senderid + "@gcm.googleapis.com")
                    .setMessageId(Integer.toString(msgId.incrementAndGet()))
                    .setData(JoH.bundleToMap(data))
                    .build());
        } else {
            Log.wtf(TAG, "senderid is null");
        }
    }

    private void tryGCMcreate() {
        Log.d(TAG, "try GCMcreate");
        checkCease();
        if (cease_all_activity) return;

        if (!InstalledApps.isGooglePlayInstalled(xdrip.getAppContext())) {
            if (JoH.pratelimit("gms-missing-msg", 86400)) {
                final String msg = "Google Play services - not installed!\nInstall it or disable xDrip+ sync options";
                JoH.static_toast_long(msg);
                Home.toaststaticnext(msg);
            }
            cease_all_activity = true;
            return;
        }

        mRegistrationBroadcastReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {

                SharedPreferences sharedPreferences =
                        PreferenceManager.getDefaultSharedPreferences(context);
                boolean sentToken = sharedPreferences
                        .getBoolean(PreferencesNames.SENT_TOKEN_TO_SERVER, false);
                if (sentToken) {
                    Log.i(TAG, "Token retrieved and sent");
                } else {
                    Log.e(TAG, "Error with token");
                }
            }
        };

        final Boolean play_result = checkPlayServices();
        if (play_result == null) {
            Log.d(TAG, "Indeterminate result for play services");
            PlusSyncService.backoff_a_lot();
        } else if (play_result) {
            final Intent intent = new Intent(xdrip.getAppContext(), RegistrationIntentService.class);
            xdrip.getAppContext().startService(intent);
        } else {
            cease_all_activity = true;
            final String msg = "ERROR: Connecting to Google Services - check google login or reboot?";
            JoH.static_toast_long(msg);
            Home.toaststaticnext(msg);
        }
    }

    // for starting FauxActivity
    public void jumpStart() {
        Log.d(TAG, "jumpStart() called");
        if (JoH.ratelimit("gcm-jumpstart", 5)) {
            onCreate(null);
        } else {
            Log.d(TAG, "Ratelimiting jumpstart");
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        try {
            super.onCreate(savedInstanceState);
            if (Pref.getBooleanDefaultFalse("disable_all_sync")) {
                cease_all_activity = true;
                Log.d(TAG, "Sync services disabled");
            }
            if (cease_all_activity) {
                finish();
                return;
            }
            Log.d(TAG, "onCreate");
            tryGCMcreate();
        } catch (Exception e) {
            Log.e(TAG, "Got exception in GCMactivity Oncreate: ", e);
        } finally {
            try {
                finish();
            } catch (Exception e) {
                Log.e(TAG, "Exception when finishing: " + e);
            }
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (cease_all_activity) return;
        LocalBroadcastManager.getInstance(xdrip.getAppContext()).registerReceiver(mRegistrationBroadcastReceiver,
                new IntentFilter(PreferencesNames.REGISTRATION_COMPLETE));
    }

    @Override
    protected void onPause() {
        try {
            LocalBroadcastManager.getInstance(xdrip.getAppContext()).unregisterReceiver(mRegistrationBroadcastReceiver);
        } catch (Exception e) {
            Log.e(TAG, "Exception onPause: ", e);
        }
        super.onPause();
    }

    static void checkSync(final Context context) {
        if ((GcmActivity.last_ack > -1) && (GcmActivity.last_send_previous > 0)) {
            if (GcmActivity.last_send_previous > GcmActivity.last_ack) {
                if (Pref.getLong("sync_warning_never", 0) == 0) {
                    if (PreferencesNames.SYNC_VERSION.equals("1") && JoH.isOldVersion(context)) {
                        final double since_send = JoH.ts() - GcmActivity.last_send_previous;
                        if (since_send > 60000) {
                            final double ack_outstanding = JoH.ts() - GcmActivity.last_ack;
                            if (ack_outstanding > MAX_ACK_OUTSTANDING_MS) {
                                if (JoH.ratelimit("ack-failure", 7200)) {
                                    if (JoH.isAnyNetworkConnected()) {
                                        AlertDialog.Builder builder = new AlertDialog.Builder(context);
                                        builder.setTitle("Possible Sync Problem");
                                        builder.setMessage("It appears we haven't been able to send/receive sync data for the last: " + JoH.qs(ack_outstanding / 60000, 0) + " minutes\n\nDo you want to perform a reset of the sync system?");
                                        builder.setPositiveButton("YES, Do it!", new DialogInterface.OnClickListener() {
                                            public void onClick(DialogInterface dialog, int which) {
                                                dialog.dismiss();
                                                JoH.static_toast(context, "Resetting...", Toast.LENGTH_LONG);
                                                SdcardImportExport.forceGMSreset();
                                            }
                                        });
                                        builder.setNeutralButton("Maybe Later", new DialogInterface.OnClickListener() {
                                            public void onClick(DialogInterface dialog, int which) {
                                                dialog.dismiss();
                                            }
                                        });
                                        builder.setNegativeButton("NO, Never", new DialogInterface.OnClickListener() {
                                            @Override
                                            public void onClick(DialogInterface dialog, int which) {
                                                dialog.dismiss();
                                                Pref.setLong("sync_warning_never", (long) JoH.ts());
                                            }
                                        });
                                        AlertDialog alert = builder.create();
                                        alert.show();
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    /**
     * Check the device to make sure it has the Google Play Services APK. If
     * it doesn't, display a dialog that allows users to download the APK from
     * the Google Play Store or enable it in the device's system settings.
     */

    private static Boolean checkPlayServices() {
        return checkPlayServices(xdrip.getAppContext(), null);
    }

    static Boolean checkPlayServices(Context context, Activity activity) {
        checkCease();
        if (cease_all_activity) return false;
        final GoogleApiAvailability apiAvailability = GoogleApiAvailability.getInstance();
        int resultCode = apiAvailability.isGooglePlayServicesAvailable(context);
        if (resultCode != ConnectionResult.SUCCESS) {
            try {
                if (apiAvailability.isUserResolvableError(resultCode)) {
                    if (activity != null) {
                        apiAvailability.getErrorDialog(activity, resultCode, PLAY_SERVICES_RESOLUTION_REQUEST)
                                .show();
                    } else {
                        if (JoH.ratelimit(Home.GCM_RESOLUTION_ACTIVITY, 60)) {
                            //apiAvailability.showErrorNotification(context, resultCode);
                            Home.startHomeWithExtra(context, Home.GCM_RESOLUTION_ACTIVITY, "1");
                            return null;
                        } else {
                            Log.e(TAG, "Ratelimit exceeded for " + Home.GCM_RESOLUTION_ACTIVITY);
                        }
                    }
                } else {
                    final String msg = "This device is not supported for play services.";
                    Log.i(TAG, msg);
                    JoH.static_toast_long(msg);
                    cease_all_activity = true;
                    return false;
                }
            } catch (Exception e) {
                Log.e(TAG, "Error resolving google play - probably no google");
                cease_all_activity = true;
            }
            return false;
        }
        return true;
    }

    private static class GCM_data {
        public Bundle bundle;
        public Double timestamp;
        private int resent;

        private GCM_data(Bundle data) {
            bundle = data;
            timestamp = JoH.ts();
            resent = 0;
        }
    }
}

class SensorCalibrations {
    @Expose
    Sensor sensor;

    @Expose
    List<Calibration> calibrations;
}

class NewCalibration {
    @Expose
    double bgValue; // Always in mgdl

    @Expose
    long timestamp;

    @Expose
    long offset;

    @Expose
    String uuid;
}

