"""
import com.eveningoutpost.dexdrip.G5Model.BatteryInfoRxMessage;
import com.eveningoutpost.dexdrip.G5Model.BluetoothServices;
import com.eveningoutpost.dexdrip.G5Model.Extensions;
import com.eveningoutpost.dexdrip.G5Model.Ob1G5StateMachine;
import com.eveningoutpost.dexdrip.G5Model.TransmitterStatus;
import com.eveningoutpost.dexdrip.G5Model.VersionRequestRxMessage;
import com.eveningoutpost.dexdrip.Home;
import com.eveningoutpost.dexdrip.Models.JoH;
import com.eveningoutpost.dexdrip.Models.UserError;
import com.eveningoutpost.dexdrip.R;
import com.eveningoutpost.dexdrip.UtilityModels.CollectionServiceStarter;
import com.eveningoutpost.dexdrip.UtilityModels.Constants;
import com.eveningoutpost.dexdrip.UtilityModels.PersistentStore;
import com.eveningoutpost.dexdrip.UtilityModels.Pref;
import com.eveningoutpost.dexdrip.UtilityModels.StatusItem;
import com.eveningoutpost.dexdrip.utils.DexCollectionType;
import com.eveningoutpost.dexdrip.xdrip;
import com.google.common.collect.Sets;
import com.polidea.rxandroidble.RxBleClient;
import com.polidea.rxandroidble.RxBleConnection;
import com.polidea.rxandroidble.RxBleCustomOperation;
import com.polidea.rxandroidble.RxBleDevice;
import com.polidea.rxandroidble.RxBleDeviceServices;
import com.polidea.rxandroidble.exceptions.BleScanException;
import com.polidea.rxandroidble.internal.RxBleLog;
import com.polidea.rxandroidble.internal.connection.RxBleGattCallback;
import com.polidea.rxandroidble.scan.ScanResult;
import com.polidea.rxandroidble.scan.ScanSettings;

import static com.eveningoutpost.dexdrip.G5Model.BluetoothServices.getUUIDName;
"""

"""
 OB1 G5 collector
 
 
"""


class Ob1G5CollectionService(G5BaseService):

    OB1G5_PREFS = "use_ob1_g5_collector_service"
    OB1G5_MACSTORE = "G5-mac-for-txid-"

    state = STATE.INIT
    last_automata_state = STATE.CLOSED

    private static RxBleClient rxBleClient;
    private static PendingIntent pendingIntent;

    private static String transmitterID;
    private static String transmitterMAC;
    private static String transmitterIDmatchingMAC;

    //private static String lastState = "Not running";
    //private static String lastStateWatch = "Not running";
    private static String lastScanError = null;
    private static volatile String static_connection_state = null;
    private static long static_last_connected = 0;
    //private static long static_last_timestamp = 0;
    //private static long static_last_timestamp_watch = 0;
    private static long last_transmitter_timestamp = 0;
    private static long lastStateUpdated = 0;
    private static long wakeup_time = 0;
    private static long wakeup_jitter = 0;
    private static long max_wakeup_jitter = 0;
    private static volatile long connecting_time = 0;


    public static boolean keep_running = true;

    public static boolean android_wear = false;

    private Subscription scanSubscription;
    private Subscription connectionSubscription;
    private static volatile Subscription stateSubscription;
    private Subscription discoverSubscription;
    private RxBleDevice bleDevice;
    private RxBleConnection connection;

    private PowerManager.WakeLock connection_linger;
    private PowerManager.WakeLock scanWakeLock;
    private volatile PowerManager.WakeLock floatingWakeLock;
    private PowerManager.WakeLock fullWakeLock;

    private boolean background_launch_waiting = false;
    private static long last_scan_started = -1;
    private static int error_count = 0;
    private static int connectNowFailures = 0;
    private static int connectFailures = 0;
    private static boolean auth_succeeded = false;
    private int error_backoff_ms = 1000;
    private static final int max_error_backoff_ms = 10000;
    private static final long TOLERABLE_JITTER = 10000;

    private static final boolean d = false;

    private static boolean always_scan = false;
    private static boolean always_discover = false;
    private static boolean always_connect = false;
    private static boolean do_discovery = true;
    private static final boolean do_auth = true;
    private static boolean initiate_bonding = false;

    //private static final Set<String> alwaysScanModels = Sets.newHashSet("SM-N910V","G Watch","SmartWatch 3");
    private static final Set<String> alwaysScanModels = Sets.newHashSet("SM-N910V","G Watch");
    private static final List<String> alwaysScanModelFamilies = Arrays.asList("SM-N910");
    private static final Set<String> alwaysConnectModels = Sets.newHashSet("G Watch");
    private static final Set<String> alwaysBuggyWakeupModels = Sets.newHashSet("Jelly-Pro", "SmartWatch 3");

    // Internal process state tracking
    public enum STATE {
        INIT("Initializing"),
        SCAN("Scanning"),
        CONNECT("Waiting connect"),
        CONNECT_NOW("Power connect"),
        DISCOVER("Examining"),
        CHECK_AUTH("Checking Auth"),
        PREBOND("Bond Prepare"),
        BOND("Bonding"),
        GET_DATA("Getting Data"),
        CLOSE("Sleeping"),
        CLOSED("Deep Sleeping");


        private String str;

        STATE(String custom) {
            this.str = custom;
        }

        STATE() {
            this.str = toString();
        }

        public String getString() {
            return str;
        }
    }

    public void authResult(boolean good) {
        auth_succeeded = good;
    }

    private synchronized void backoff_automata() {
        background_automata(error_backoff_ms);
        if (error_backoff_ms < max_error_backoff_ms) error_backoff_ms += 100;
    }

    public void background_automata() {
        background_automata(100);
    }

    public synchronized void background_automata(final int timeout) {
        if (background_launch_waiting) {
            UserError.Log.d(TAG, "Blocked by existing background automata pending");
            return;
        }
        final PowerManager.WakeLock wl = JoH.getWakeLock("jam-g5-background", timeout + 1000);
        background_launch_waiting = true;
        new Thread(() -> {
            try {
                Thread.sleep(timeout);
            } catch (InterruptedException e) {
                //
            }
            background_launch_waiting = false;
            JoH.releaseWakeLock(wl);
            automata();
        }).start();
    }

    private synchronized void automata() {

        if ((last_automata_state != state) || (JoH.ratelimit("jam-g5-dupe-auto", 2))) {
            last_automata_state = state;
            final PowerManager.WakeLock wl = JoH.getWakeLock("jam-g5-automata", 60000);
            try {
                switch (state) {

                    case INIT:
                        initialize();
                        break;
                    case SCAN:
                        // no connection? lets try a restart
                        if (JoH.msSince(static_last_connected) > 10 * 60 * 1000) {
                            if (JoH.pratelimit("ob1-collector-restart", 1200)) {
                                new Thread(() -> {
                                    CollectionServiceStarter.restartCollectionService(xdrip.getAppContext());
                                }).start();
                                break;
                            }
                        }
                        scan_for_device();
                        break;
                    case CONNECT_NOW:
                        connect_to_device(false);
                        break;
                    case CONNECT:
                        connect_to_device(true);
                        break;
                    case DISCOVER:
                        if (do_discovery) {
                            discover_services();
                        } else {
                            UserError.Log.d(TAG, "Skipping discovery");
                            changeState(STATE.CHECK_AUTH);
                        }
                        break;
                    case CHECK_AUTH:
                        if (do_auth) {
                            final PowerManager.WakeLock linger_wl_connect = JoH.getWakeLock("jam-g5-check-linger", 6000);
                            if (!Ob1G5StateMachine.doCheckAuth(this, connection)) resetState();
                        } else {
                            UserError.Log.d(TAG, "Skipping authentication");
                            changeState(STATE.GET_DATA);
                        }
                        break;
                    case PREBOND:
                        final PowerManager.WakeLock linger_wl_prebond = JoH.getWakeLock("jam-g5-prebond-linger", 16000);
                        if (!Ob1G5StateMachine.doKeepAliveAndBondRequest(this, connection))
                            resetState();
                        break;
                    case BOND:
                        //create_bond();
                        UserError.Log.d(TAG, "State bond currently does nothing");
                        break;
                    case GET_DATA:
                        final PowerManager.WakeLock linger_wl_get_data = JoH.getWakeLock("jam-g5-get-linger", 6000);
                        if (!Ob1G5StateMachine.doGetData(this, connection)) resetState();
                        break;
                    case CLOSE:
                        prepareToWakeup();
                        break;
                    case CLOSED:
                        handleWakeup();
                        break;
                }
            } finally {
                JoH.releaseWakeLock(wl);
            }
        } else {
            UserError.Log.d(TAG, "Ignoring duplicate automata state within 2 seconds: " + state);
        }
    }

    private void resetState() {
        UserError.Log.e(TAG, "Resetting sequence state to INIT");
        changeState(STATE.INIT);
    }

    public STATE getState() {
        return state;
    }

    public void changeState(STATE new_state) {
        UserError.Log.d(TAG, "Changing state from: " + state + " to " + new_state);
        state = new_state;
        background_automata();
    }

    private synchronized void initialize() {
        if (state == STATE.INIT) {
            msg("Initializing");
            static_connection_state = null;
            if (rxBleClient == null) {
                rxBleClient = RxBleClient.create(xdrip.getAppContext());
            }
            init_tx_id();
            // load prefs etc
            changeState(STATE.SCAN);
        } else {
            UserError.Log.wtf(TAG, "Attempt to initialize when not in INIT state");
        }
    }

    private static void init_tx_id() {
        transmitterID = Pref.getString("dex_txid", "NULL");
    }

    private synchronized void scan_for_device() {
        if (state == STATE.SCAN) {
            msg("Scanning");
            stopScan();
            tryLoadingSavedMAC(); // did we already find it?
            if (always_scan || (transmitterMAC == null) || (!transmitterID.equals(transmitterIDmatchingMAC)) || (static_last_timestamp < 1)) {
                transmitterMAC = null; // reset if set
                last_scan_started = JoH.tsl();
                scanWakeLock = JoH.getWakeLock("xdrip-jam-g5-scan", (int) Constants.MINUTE_IN_MS * 6);

                scanSubscription = rxBleClient.scanBleDevices(
                        new ScanSettings.Builder()
                                .setScanMode(static_last_timestamp < 1 ? ScanSettings.SCAN_MODE_LOW_LATENCY : ScanSettings.SCAN_MODE_BALANCED)
                                //.setCallbackType(ScanSettings.CALLBACK_TYPE_FIRST_MATCH)
                                .setCallbackType(ScanSettings.CALLBACK_TYPE_ALL_MATCHES)
                                .build()//,

                        // scan filter doesn't work reliable on android sdk 23+
                        //new ScanFilter.Builder()
                        //.
                        //          .setDeviceName(getTransmitterBluetoothName())
                        //         .build()

                )
                        // observe on?
                        // do unsubscribe?
                        //.doOnUnsubscribe(this::clearSubscription)
                        .subscribeOn(Schedulers.io())
                        .subscribe(this::onScanResult, this::onScanFailure);
                UserError.Log.d(TAG, "Scanning for: " + getTransmitterBluetoothName());
            } else {
                UserError.Log.d(TAG, "Transmitter mac already known: " + transmitterMAC);
                changeState(STATE.CONNECT);

            }
        } else {
            UserError.Log.wtf(TAG, "Attempt to scan when not in SCAN state");
        }
    }

    private synchronized void connect_to_device(boolean auto) {
        if ((state == STATE.CONNECT) || (state == STATE.CONNECT_NOW)) {
            // TODO check mac
            if (transmitterMAC != null) {
                msg("Connect request");
                if (state == STATE.CONNECT_NOW) {
                    if (connection_linger != null) JoH.releaseWakeLock(connection_linger);
                    connection_linger = JoH.getWakeLock("jam-g5-pconnect", 60000);
                }
                if (d)
                    UserError.Log.d(TAG, "Local bonding state: " + (isDeviceLocallyBonded() ? "BONDED" : "NOT Bonded"));
                stopConnect();

                bleDevice = rxBleClient.getBleDevice(transmitterMAC);

                        /// / Listen for connection state changes
                stateSubscription = bleDevice.observeConnectionStateChanges()
                        // .observeOn(AndroidSchedulers.mainThread())
                        .subscribeOn(Schedulers.io())
                        .subscribe(this::onConnectionStateChange, throwable -> {
                            UserError.Log.wtf(TAG, "Got Error from state subscription: " + throwable);
                        });

                // Attempt to establish a connection
                connectionSubscription = bleDevice.establishConnection(auto)
                        .timeout(7, TimeUnit.MINUTES)
                        // .flatMap(RxBleConnection::discoverServices)
                        // .observeOn(AndroidSchedulers.mainThread())
                        // .doOnUnsubscribe(this::clearSubscription)
                        .subscribeOn(Schedulers.io())

                        .subscribe(this::onConnectionReceived, this::onConnectionFailure);

            } else {
                UserError.Log.wtf(TAG, "No transmitter mac address!");

                state = STATE.SCAN;
                backoff_automata(); // note backoff
            }

        } else {
            UserError.Log.wtf(TAG, "Attempt to connect when not in CONNECT state");
        }
    }

    private synchronized void discover_services() {
        if (state == STATE.DISCOVER) {
            if (connection != null) {
                if (d)
                    UserError.Log.d(TAG, "Local bonding state: " + (isDeviceLocallyBonded() ? "BONDED" : "NOT Bonded"));
                stopDisover();
                discoverSubscription = connection.discoverServices(10, TimeUnit.SECONDS).subscribe(this::onServicesDiscovered, this::onDiscoverFailed);
            } else {
                UserError.Log.e(TAG, "No connection when in DISCOVER state - reset");
                state = STATE.INIT;
                background_automata();
            }
        } else {
            UserError.Log.wtf(TAG, "Attempt to discover when not in DISCOVER state");
        }
    }

    @TargetApi(Build.VERSION_CODES.KITKAT)
    private synchronized void create_bond() {
        if (state == STATE.BOND) {
            try {
                msg("Bonding");
                do_create_bond();
                //state = STATE.CONNECT_NOW;
                //background_automata(15000);
            } catch (Exception e) {
                UserError.Log.wtf(TAG, "Exception creating bond: " + e);
            }
        } else {
            UserError.Log.wtf(TAG, "Attempt to bond when not in BOND state");
        }
    }

    public synchronized void reset_bond(boolean allow) {
        if (allow || (JoH.pratelimit("ob1-bond-cycle", 7200))) {
            UserError.Log.e(TAG, "Attempting to refresh bond state");
            msg("Resetting Bond");
            do_create_bond();
        }
    }

    private synchronized void do_create_bond() {
        UserError.Log.d(TAG, "Attempting to create bond, device is : " + (isDeviceLocallyBonded() ? "BONDED" : "NOT Bonded"));
        try {
            unBond();
            instantCreateBond();
        } catch (Exception e) {
            UserError.Log.wtf(TAG, "Got exception in do_create_bond() " + e);
        }
    }

    private String getTransmitterBluetoothName() {
        final String transmitterIdLastTwo = Extensions.lastTwoCharactersOfString(transmitterID);
        // todo check for bad config
        return "Dexcom" + transmitterIdLastTwo;
    }

    private void tryLoadingSavedMAC() {
        if ((transmitterMAC == null) || (!transmitterIDmatchingMAC.equals(transmitterID))) {
            if (transmitterID != null) {
                final String this_mac = PersistentStore.getString(OB1G5_MACSTORE + transmitterID);
                if (this_mac.length() == 17) {
                    UserError.Log.d(TAG, "Loaded stored MAC for: " + transmitterID + " " + this_mac);
                    transmitterMAC = this_mac;
                    transmitterIDmatchingMAC = transmitterID;
                } else {
                    UserError.Log.d(TAG, "Did not find any saved MAC for: " + transmitterID);
                }
            } else {
                UserError.Log.e(TAG, "Could not load saved mac as transmitter id isn't set!");
            }
        } else {
            UserError.Log.d(TAG, "MAC for transmitter id already populated: " + transmitterID + " " + transmitterMAC);
        }
    }

    // should this service be running? Used to decide when to shut down
    private static boolean shouldServiceRun() {
        if (android.os.Build.VERSION.SDK_INT < Build.VERSION_CODES.KITKAT) return false;
        if (!Pref.getBooleanDefaultFalse(OB1G5_PREFS)) return false;
        if (!(DexCollectionType.getDexCollectionType() == DexCollectionType.DexcomG5)) return false;

        if (!android_wear) {
            if (Home.get_forced_wear()) {
                if (JoH.quietratelimit("forced-wear-notice", 3))
                    UserError.Log.d(TAG, "Not running due to forced wear");
                return false;
            }
        } else {
            // android wear code
            if (!PersistentStore.getBoolean(CollectionServiceStarter.pref_run_wear_collector))
                return false;
        }
        return true;
    }

    // check required permissions and warn the user if they are wrong
    private static void checkPermissions() {

    }

    private static synchronized boolean isDeviceLocallyBonded() {
        if (transmitterMAC == null) return false;
        final Set<RxBleDevice> pairedDevices = rxBleClient.getBondedDevices();
        if ((pairedDevices != null) && (pairedDevices.size() > 0)) {
            for (RxBleDevice device : pairedDevices) {
                if ((device.getMacAddress() != null) && (device.getMacAddress().equals(transmitterMAC))) {
                    return true;
                }
            }
        }
        return false;
    }

    private synchronized void checkAndEnableBT() {
        try {
            if (Pref.getBoolean("automatically_turn_bluetooth_on", true)) {
                final BluetoothAdapter mBluetoothAdapter = ((BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE)).getAdapter();
                if (!mBluetoothAdapter.isEnabled()) {
                    if (JoH.ratelimit("g5-enabling-bluetooth", 30)) {
                        JoH.setBluetoothEnabled(this, true);
                        UserError.Log.e(TAG, "Enabling bluetooth");
                    }
                }
            }

        } catch (Exception e) {
            UserError.Log.e(TAG, "Got exception checking BT: " + e);
        }
    }

    public synchronized void unBond() {

        UserError.Log.d(TAG, "unBond() start");
        if (transmitterMAC == null) return;

        final BluetoothAdapter mBluetoothAdapter = ((BluetoothManager) getSystemService(Context.BLUETOOTH_SERVICE)).getAdapter();

        final Set<BluetoothDevice> pairedDevices = mBluetoothAdapter.getBondedDevices();
        if (pairedDevices.size() > 0) {
            for (BluetoothDevice device : pairedDevices) {
                if (device.getAddress() != null) {
                    if (device.getAddress().equals(transmitterMAC)) {
                        try {
                            UserError.Log.e(TAG, "removingBond: " + transmitterMAC);
                            Method m = device.getClass().getMethod("removeBond", (Class[]) null);
                            m.invoke(device, (Object[]) null);

                        } catch (Exception e) {
                            UserError.Log.e(TAG, e.getMessage(), e);
                        }
                    }

                }
            }
        }
        UserError.Log.d(TAG, "unBond() finished");
    }


    public static String getTransmitterID() {
        return transmitterID;
    }

    private void handleWakeup() {
        if (always_scan) {
            UserError.Log.d(TAG, "Always scan mode");
            changeState(STATE.SCAN);
        } else {
            if (connectFailures > 0) {
                always_scan = true;
                UserError.Log.e(TAG, "Switching to scan always mode due to connect failures metric: " + connectFailures);
                changeState(STATE.SCAN);
            } else if ((connectNowFailures > 1) && (connectFailures < 0)) {
                UserError.Log.d(TAG, "Avoiding power connect due to failure metric: " + connectNowFailures + " " + connectFailures);
                changeState(STATE.CONNECT);
            } else {
                changeState(STATE.CONNECT_NOW);
            }
        }
    }


    private synchronized void prepareToWakeup() {
        if (JoH.ratelimit("g5-wakeup-timer", 5)) {
            scheduleWakeUp(Constants.SECOND_IN_MS * 285, "anticipate");
        }

        if ((android_wear && wakeup_jitter > TOLERABLE_JITTER) || always_connect) {
            // TODO should be max_wakeup_jitter perhaps or set always_connect flag
            UserError.Log.d(TAG, "Not stopping connect due to " + (always_connect ? "always_connect flag" : "unreliable wake up"));
            state = STATE.CONNECT;
            background_automata(6000);
        } else {
            state = STATE.CLOSED; // Don't poll automata as we want to do this on waking
            stopConnect();
        }

    }

    private void scheduleWakeUp(long future, final String info) {
        if (future < 0) future = 5000;
        UserError.Log.d(TAG, "Scheduling wakeup @ " + JoH.dateTimeText(JoH.tsl() + future) + " (" + info + ")");
        if (pendingIntent == null)
            pendingIntent = PendingIntent.getService(this, 0, new Intent(this, this.getClass()), 0);
        wakeup_time = JoH.tsl() + future;
        JoH.wakeUpIntent(this, future, pendingIntent);
    }

    public void incrementErrors() {
        error_count++;
        if (error_count > 1) {
            UserError.Log.e(TAG, "Error count reached: " + error_count);
        }
    }

    public void clearErrors() {
        error_count = 0;
    }

    private void checkAlwaysScanModels() {
        final String this_model = Build.MODEL;
        UserError.Log.d(TAG, "Checking model: " + this_model);

        if ((JoH.isSamsung() && PersistentStore.getLong(BUGGY_SAMSUNG_ENABLED) > 4)) {
            UserError.Log.d(TAG, "Enabling buggy samsung due to persistent metric");
            JoH.buggy_samsung = true;
        }

        always_connect = alwaysConnectModels.contains(this_model);

        if (alwaysBuggyWakeupModels.contains(this_model)) {
            UserError.Log.e(TAG,"Always buggy wakeup exact match for " + this_model);
            JoH.buggy_samsung = true;
        }

        if (alwaysScanModels.contains(this_model)) {
            UserError.Log.e(TAG, "Always scan model exact match for: " + this_model);
            always_scan = true;
            return;
        }

        for (String check : alwaysScanModelFamilies) {
            if (this_model.startsWith(check)) {
                UserError.Log.e(TAG, "Always scan model fuzzy match for: " + this_model);
                always_scan = true;
                return;
            }
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();

        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.KITKAT) {
            UserError.Log.wtf(TAG, "Not high enough Android version to run: " + Build.VERSION.SDK_INT);
        } else {

            registerReceiver(mBondStateReceiver, new IntentFilter(BluetoothDevice.ACTION_BOND_STATE_CHANGED));

            final IntentFilter pairingRequestFilter = new IntentFilter(BluetoothDevice.ACTION_PAIRING_REQUEST);
            pairingRequestFilter.setPriority(IntentFilter.SYSTEM_HIGH_PRIORITY - 1);
            registerReceiver(mPairingRequestRecevier, pairingRequestFilter);

            checkAlwaysScanModels();

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT_WATCH) {
                android_wear = (getResources().getConfiguration().uiMode & Configuration.UI_MODE_TYPE_MASK) == Configuration.UI_MODE_TYPE_WATCH;
                if (android_wear) {
                    UserError.Log.d(TAG,"We are running on Android Wear");
                }
            }
        }
        if (d) RxBleClient.setLogLevel(RxBleLog.DEBUG);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        xdrip.checkAppContext(getApplicationContext());
        final PowerManager.WakeLock wl = JoH.getWakeLock("g5-start-service", 310000);
        try {
            UserError.Log.d(TAG, "WAKE UP WAKE UP WAKE UP WAKE UP @ " + JoH.dateTimeText(JoH.tsl()));
            msg("Wake up");
            if (wakeup_time > 0) {
                wakeup_jitter = JoH.msSince(wakeup_time);
                if (wakeup_jitter < 0) {
                    UserError.Log.d(TAG, "Woke up Early..");
                } else {
                    if (wakeup_jitter > 1000) {
                        UserError.Log.d(TAG, "Wake up, time jitter: " + JoH.niceTimeScalar(wakeup_jitter));
                        if ((wakeup_jitter > TOLERABLE_JITTER) && (!JoH.buggy_samsung) && JoH.isSamsung()) {
                            UserError.Log.wtf(TAG, "Enabled Buggy Samsung workaround due to jitter of: " + JoH.niceTimeScalar(wakeup_jitter));
                            JoH.buggy_samsung = true;
                            PersistentStore.incrementLong(BUGGY_SAMSUNG_ENABLED);
                            max_wakeup_jitter = 0;
                        } else {
                            max_wakeup_jitter = Math.max(max_wakeup_jitter, wakeup_jitter);
                        }

                    }
                }
            }
            if (!shouldServiceRun()) {
                UserError.Log.d(TAG, "Stopping service due to shouldServiceRun() result");
                msg("Stopping");
                stopSelf();
                return START_NOT_STICKY;
            }


            scheduleWakeUp(Constants.MINUTE_IN_MS * 6, "fail-over");
            if ((state == STATE.BOND) || (state == STATE.PREBOND)) state = STATE.SCAN;

            checkAndEnableBT();

            automata(); // sequence logic

            UserError.Log.d(TAG, "Releasing service start");
            return START_STICKY;
        } finally {
            JoH.releaseWakeLock(wl);
        }
    }

    @Override
    public void onDestroy() {
        msg("Shutting down");
        if (pendingIntent != null) {
            JoH.cancelAlarm(this, pendingIntent);
            pendingIntent = null;
            wakeup_time = 0;
        }
        stopScan();
        stopDisover();
        stopConnect();
        scanSubscription = null;
        connectionSubscription = null;
        stateSubscription = null;
        discoverSubscription = null;

        unregisterPairingReceiver();

        try {
            unregisterReceiver(mBondStateReceiver);
        } catch (Exception e) {
            UserError.Log.e(TAG, "Got exception unregistering pairing receiver: "+ e);
        }

        state = STATE.INIT; // Should be STATE.END ?
        msg("Service Stopped");
        super.onDestroy();
    }

    public void unregisterPairingReceiver() {
        try {
            unregisterReceiver(mPairingRequestRecevier);
        } catch (Exception e) {
            UserError.Log.e(TAG, "Got exception unregistering pairing receiver: "+ e);
        }
    }

    private synchronized void stopScan() {
        if (scanSubscription != null) {
            scanSubscription.unsubscribe();
        }
        if (scanWakeLock != null) {
            JoH.releaseWakeLock(scanWakeLock);
        }
    }

    private synchronized void stopConnect() {
        if (connectionSubscription != null) {
            connectionSubscription.unsubscribe();
        }
        if (stateSubscription != null) {
            stateSubscription.unsubscribe();
        }
    }

    private synchronized void stopDisover() {
        if (discoverSubscription != null) {
            discoverSubscription.unsubscribe();
        }
    }

    // Successful result from our bluetooth scan
    private synchronized void onScanResult(ScanResult bleScanResult) {
        final String this_name = bleScanResult.getBleDevice().getName();
        final String search_name = getTransmitterBluetoothName();
        if ((this_name != null) && (this_name.equals(search_name))) {
            stopScan(); // we got one!
            last_scan_started = 0; // clear scanning for time
            lastScanError = null; // error should be cleared
            UserError.Log.d(TAG, "Got scan result match: " + bleScanResult.getBleDevice().getName() + " " + bleScanResult.getBleDevice().getMacAddress() + " rssi: " + bleScanResult.getRssi());
            transmitterMAC = bleScanResult.getBleDevice().getMacAddress();
            transmitterIDmatchingMAC = transmitterID;
            PersistentStore.setString(OB1G5_MACSTORE + transmitterID, transmitterMAC);
            if (always_scan) {
                changeState(STATE.CONNECT_NOW);
            } else {
                changeState(STATE.CONNECT);
            }
        } else {
            String this_mac = bleScanResult.getBleDevice().getMacAddress();
            if (this_mac == null) this_mac = "NULL";
            if (JoH.quietratelimit("bt-obi1-null-match" + this_mac, 15)) {
                UserError.Log.d(TAG, "Bluetooth scanned device doesn't match (" + search_name + ") found: " + this_name + " " + bleScanResult.getBleDevice().getMacAddress());
            }
        }
    }

    // Failed result from our bluetooth scan
    private synchronized void onScanFailure(Throwable throwable) {

        if (throwable instanceof BleScanException) {
            final String info = handleBleScanException((BleScanException) throwable);
            lastScanError = info;
            UserError.Log.d(TAG, info);
            if (((BleScanException) throwable).getReason() == BleScanException.BLUETOOTH_DISABLED) {
                // Attempt to turn bluetooth on
                if (JoH.ratelimit("bluetooth_toggle_on", 30)) {
                    UserError.Log.d(TAG, "Pause before Turn Bluetooth on");
                    try {
                        Thread.sleep(2000);
                    } catch (InterruptedException e) {
                        //
                    }
                    UserError.Log.e(TAG, "Trying to Turn Bluetooth on");
                    JoH.setBluetoothEnabled(xdrip.getAppContext(), true);
                }
            }
            // TODO count scan duration
            stopScan();
            backoff_automata();
        }
    }


    // Connection has been terminated or failed
    // - quite normal when device switches to sleep between readings
    private void onConnectionFailure(Throwable throwable) {
        // msg("Connection failure");
        // TODO under what circumstances should we change state or do something here?
        UserError.Log.d(TAG, "Connection Disconnected/Failed: " + throwable);

        if (state == STATE.DISCOVER) {
            // possible encryption failure
            if (Pref.getBoolean("ob1_g5_allow_resetbond", true)) {
                reset_bond(false);
            } else {
                UserError.Log.e(TAG, "Would have tried to unpair but preference setting prevents it.");
            }
        }

        if (state == STATE.CONNECT_NOW) {
            connectNowFailures++;
            UserError.Log.d(TAG, "Connect Now failures incremented to: " + connectNowFailures);
            changeState(STATE.CONNECT);
        }

        if (state == STATE.CONNECT) {
            connectFailures++;
            // TODO check bluetooth on or in connect section
          if (JoH.ratelimit("ob1-restart-scan-on-connect-failure",10)) {
              UserError.Log.d(TAG,"Restarting scan due to connect failure");
              tryGattRefresh();
              changeState(STATE.SCAN);
          }
        }

    }

    public void tryGattRefresh() {
        if (JoH.ratelimit("ob1-gatt-refresh", 60)) {
            try {
                if (connection != null)
                    UserError.Log.d(TAG, "Trying gatt refresh queue");
                connection.queue((new GattRefreshOperation(0))).timeout(2, TimeUnit.SECONDS).subscribe(
                        readValue -> {
                            UserError.Log.d(TAG, "Refresh OK: " + readValue);
                        }, throwable -> {
                            UserError.Log.d(TAG, "Refresh exception: " + throwable);
                        });
            } catch (Exception e) {
                UserError.Log.d(TAG, "Got exception trying gatt refresh: " + e);
            }
        } else {
            UserError.Log.d(TAG, "Gatt refresh rate limited");
        }
    }

    // We have connected to the device!
    private void onConnectionReceived(RxBleConnection this_connection) {
        msg("Connected");
        static_last_connected = JoH.tsl();
        // TODO check connection already exists - close etc?
        if (connection_linger != null) JoH.releaseWakeLock(connection_linger);
        connection = this_connection;

        if (state == STATE.CONNECT_NOW) {
            connectNowFailures = -3; // mark good
        }
        if (state == STATE.CONNECT) {
            connectFailures = -1; // mark good
        }

        if (JoH.ratelimit("g5-to-discover", 1)) {
            changeState(STATE.DISCOVER);
        }
    }

    private synchronized void onConnectionStateChange(RxBleConnection.RxBleConnectionState newState) {
        String connection_state = "Unknown";
        switch (newState) {
            case CONNECTING:
                connection_state = "Connecting";
                connecting_time = JoH.tsl();
                break;
            case CONNECTED:
                connection_state = "Connected";
                JoH.releaseWakeLock(floatingWakeLock);
                floatingWakeLock = JoH.getWakeLock("floating-connected", 40000);
                final long since_connecting = JoH.msSince(connecting_time);
                if ((connecting_time > static_last_timestamp) && (since_connecting > Constants.SECOND_IN_MS * 310) && (since_connecting < Constants.SECOND_IN_MS * 620)) {
                    if (!always_scan) {
                        UserError.Log.e(TAG, "Connection time shows missed reading, switching to always scan, metric: " + JoH.niceTimeScalar(since_connecting));
                        always_scan = true;
                    } else {
                        UserError.Log.e(TAG, "Connection time shows missed reading, despite always scan, metric: " + JoH.niceTimeScalar(since_connecting));
                    }
                }
                break;
            case DISCONNECTING:
                connection_state = "Disconnecting";
                break;
            case DISCONNECTED:
                connection_state = "Disconnected";
                JoH.releaseWakeLock(floatingWakeLock);
                break;
        }
        static_connection_state = connection_state;
        UserError.Log.d(TAG, "Bluetooth connection: " + static_connection_state);
        if (connection_state.equals("Disconnecting")) {
            //tryGattRefresh();
        }
    }

    public static void connectionStateChange(String connection_state) {
        static_connection_state = connection_state;
    }


    private void onServicesDiscovered(RxBleDeviceServices services) {
        for (BluetoothGattService service : services.getBluetoothGattServices()) {
            if (d) UserError.Log.d(TAG, "Service: " + getUUIDName(service.getUuid()));
            if (service.getUuid().equals(BluetoothServices.CGMService)) {
                if (d) UserError.Log.i(TAG, "Found CGM Service!");
                if (!always_discover) {
                    do_discovery = false;
                }
                changeState(STATE.CHECK_AUTH);
                return;
            }
        }
        UserError.Log.e(TAG, "Could not locate CGM service during discovery");
        incrementErrors();
    }

    private void onDiscoverFailed(Throwable throwable) {
        UserError.Log.e(TAG, "Discover failure: " + throwable.toString());
        incrementErrors();
    }

    private void clearSubscription() {
        scanSubscription = null;

    }

    private boolean g5BluetoothWatchdog() {
        return Pref.getBoolean("g5_bluetooth_watchdog", true);
    }

    public static void updateLast(long timestamp) {
        if ((static_last_timestamp == 0) && (transmitterID != null)) {
            final String ref = "last-ob1-data-" + transmitterID;
            if (PersistentStore.getLong(ref) == 0) {
                PersistentStore.setLong(ref, timestamp);
                if (!android_wear) JoH.playResourceAudio(R.raw.labbed_musical_chime);
            }
        }
        static_last_timestamp = timestamp;
    }

    private String handleBleScanException(BleScanException bleScanException) {
        final String text;

        switch (bleScanException.getReason()) {
            case BleScanException.BLUETOOTH_NOT_AVAILABLE:
                text = "Bluetooth is not available";
                break;
            case BleScanException.BLUETOOTH_DISABLED:
                text = "Enable bluetooth and try again";
                break;
            case BleScanException.LOCATION_PERMISSION_MISSING:
                text = "On Android 6.0+ location permission is required. Implement Runtime Permissions";
                break;
            case BleScanException.LOCATION_SERVICES_DISABLED:
                text = "Location services needs to be enabled on Android 6.0+";
                break;
            case BleScanException.SCAN_FAILED_ALREADY_STARTED:
                text = "Scan with the same filters is already started";
                break;
            case BleScanException.SCAN_FAILED_APPLICATION_REGISTRATION_FAILED:
                text = "Failed to register application for bluetooth scan";
                break;
            case BleScanException.SCAN_FAILED_FEATURE_UNSUPPORTED:
                text = "Scan with specified parameters is not supported";
                break;
            case BleScanException.SCAN_FAILED_INTERNAL_ERROR:
                text = "Scan failed due to internal error";
                break;
            case BleScanException.SCAN_FAILED_OUT_OF_HARDWARE_RESOURCES:
                text = "Scan cannot start due to limited hardware resources";
                break;
            case BleScanException.UNDOCUMENTED_SCAN_THROTTLE:
                text = String.format(
                        Locale.getDefault(),
                        "Android 7+ does not allow more scans. Try in %d seconds",
                        secondsTill(bleScanException.getRetryDateSuggestion())
                );
                break;
            case BleScanException.UNKNOWN_ERROR_CODE:
            case BleScanException.BLUETOOTH_CANNOT_START:
            default:
                text = "Unable to start scanning";
                break;
        }
        UserError.Log.w(TAG, text + " " + bleScanException);
        return text;

    }

    private static class GattRefreshOperation implements RxBleCustomOperation<Void> {
        private long delay_ms = 500;

        GattRefreshOperation() {
        }

        GattRefreshOperation(long delay_ms) {
            this.delay_ms = delay_ms;
        }

        @NonNull
        @Override
        public Observable<Void> asObservable(BluetoothGatt bluetoothGatt,
                                             RxBleGattCallback rxBleGattCallback,
                                             Scheduler scheduler) throws Throwable {

            return Observable.fromCallable(() -> refreshDeviceCache(bluetoothGatt))
                    .delay(delay_ms, TimeUnit.MILLISECONDS, Schedulers.computation())
                    .subscribeOn(scheduler);
        }

        private Void refreshDeviceCache(final BluetoothGatt gatt) {
            UserError.Log.d(TAG, "Gatt Refresh " + (JoH.refreshDeviceCache(TAG, gatt) ? "succeeded" : "failed"));
            return null;
        }
    }

    private int currentBondState = 0;
    public int waitingBondConfirmation = 0; // 0 = not waiting, 1 = waiting, 2 = received
    final BroadcastReceiver mBondStateReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (!keep_running) {
                try {
                    UserError.Log.e(TAG, "Rogue bond state receiver still active - unregistering");
                    unregisterReceiver(mBondStateReceiver);
                } catch (Exception e) {
                    //
                }
                return;
            }
            final String action = intent.getAction();
            UserError.Log.d(TAG, "BondState: onReceive ACTION: " + action);
            if (BluetoothDevice.ACTION_BOND_STATE_CHANGED.equals(action)) {
                final BluetoothDevice parcel_device = intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE);
                currentBondState = parcel_device.getBondState();
                final int bond_state_extra = intent.getIntExtra(BluetoothDevice.EXTRA_BOND_STATE, -1);
                final int previous_bond_state_extra = intent.getIntExtra(BluetoothDevice.EXTRA_PREVIOUS_BOND_STATE, -1);

                UserError.Log.e(TAG, "onReceive UPDATE Name " + parcel_device.getName() + " Value " + parcel_device.getAddress()
                        + " Bond state " + parcel_device.getBondState() + bondState(parcel_device.getBondState()) + " "
                        + "bs: " + bondState(bond_state_extra) + " was " + bondState(previous_bond_state_extra));
                try {
                    if (parcel_device.getAddress().equals(transmitterMAC)) {
                        msg(bondState(bond_state_extra).replace(" ", ""));
                        if (parcel_device.getBondState() == BluetoothDevice.BOND_BONDED) {

                            if (waitingBondConfirmation == 1) {
                                waitingBondConfirmation = 2; // received
                                UserError.Log.e(TAG, "Bond confirmation received!");
                                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                                    UserError.Log.d(TAG, "Sleeping before create bond");
                                    try {
                                        Thread.sleep(1000);
                                    } catch (InterruptedException e) {
                                        //
                                    }
                                    instantCreateBond();
                                }
                            }
                        }
                    }
                } catch (Exception e) {
                    UserError.Log.e(TAG, "Got exception trying to process bonded confirmation: ", e);
                }
            }
        }
    };

    public void instantCreateBond() {
        if (initiate_bonding) {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
                    UserError.Log.d(TAG, "instantCreateBond() called");
                    bleDevice.getBluetoothDevice().createBond();
                }
            } catch (Exception e) {
                UserError.Log.e(TAG, "Got exception in instantCreateBond() " + e);
            }
        } else {
            UserError.Log.e(TAG,"instantCreateBond blocked by initiate_bonding flag");
        }
    }


    private final BroadcastReceiver mPairingRequestRecevier = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (!keep_running) {
                try {
                    UserError.Log.e(TAG, "Rogue pairing request receiver still active - unregistering");
                    unregisterReceiver(mPairingRequestRecevier);
                } catch (Exception e) {
                    //
                }
                return;
            }
            if ((bleDevice != null) && (bleDevice.getBluetoothDevice().getAddress() != null)) {
                UserError.Log.e(TAG, "Processing mPairingRequestReceiver !!!");
                JoH.releaseWakeLock(fullWakeLock);
                fullWakeLock = JoH.fullWakeLock("pairing-screen-wake", 30 * Constants.SECOND_IN_MS);
                if (!android_wear) Home.startHomeWithExtra(context, Home.HOME_FULL_WAKEUP, "1");
                if (!JoH.doPairingRequest(context, this, intent, bleDevice.getBluetoothDevice().getAddress())) {
                    if (!android_wear) {
                        unregisterPairingReceiver();
                        UserError.Log.e(TAG, "Pairing failed so removing pairing automation"); // todo use flag
                    }
                }
            } else {
                UserError.Log.e(TAG, "Received pairing request but device was null !!!");
            }
        }
    };

    private static long secondsTill(Date retryDateSuggestion) {
        return TimeUnit.MILLISECONDS.toSeconds(retryDateSuggestion.getTime() - System.currentTimeMillis());
    }

    @Override
    public IBinder onBind(Intent intent) {
        throw new UnsupportedOperationException("Not yet implemented");
    }

    public static void msg(String msg) {
        lastState = msg + " " + JoH.hourMinuteString();
        UserError.Log.d(TAG, "Status: " + lastState);
        lastStateUpdated = JoH.tsl();
    }

   /* public static void setWatchStatus(DataMap dataMap) {
        lastStateWatch = dataMap.getString("lastState", "");
        static_last_timestamp_watch = dataMap.getLong("timestamp", 0);
    }

    public static DataMap getWatchStatus() {
        DataMap dataMap = new DataMap();
        dataMap.putString("lastState", lastState);
        dataMap.putLong("timestamp", static_last_timestamp);
        return dataMap;
    }

*/

    // data for MegaStatus
    public static List<StatusItem> megaStatus() {

        init_tx_id(); // needed if we have not passed through local INIT state

        final List<StatusItem> l = new ArrayList<>();

        l.add(new StatusItem("Phone Service State", lastState, JoH.msSince(lastStateUpdated) < 300000 ? (lastState.startsWith("Got data") ? StatusItem.Highlight.GOOD : StatusItem.Highlight.NORMAL) : (isWatchRunning() ? StatusItem.Highlight.GOOD : StatusItem.Highlight.CRITICAL)));
        if (last_scan_started > 0) {
            final long scanning_time = JoH.msSince(last_scan_started);
            l.add(new StatusItem("Time scanning", JoH.niceTimeScalar(scanning_time), scanning_time > Constants.MINUTE_IN_MS * 5 ? (scanning_time > Constants.MINUTE_IN_MS * 10 ? StatusItem.Highlight.BAD : StatusItem.Highlight.NOTICE) : StatusItem.Highlight.NORMAL));
        }
        if (lastScanError != null) {
            l.add(new StatusItem("Scan Error", lastScanError, StatusItem.Highlight.BAD));
        }

        if (transmitterID != null) {
            l.add(new StatusItem("Sensor Device", transmitterID + ((transmitterMAC != null && Home.get_engineering_mode()) ? "\n" + transmitterMAC : "")));
        }

        if (static_connection_state != null) {
            l.add(new StatusItem("Bluetooth Link", static_connection_state));
        }

        if (static_last_connected > 0) {
            l.add(new StatusItem("Last Connected", JoH.niceTimeScalar(JoH.msSince(static_last_connected)) + " ago"));
        }

        if ((!lastState.startsWith("Service Stopped")) && (!lastState.startsWith("Not running")))
            l.add(new StatusItem("Brain State", state.getString() + (error_count > 1 ? " Errors: " + error_count : ""), error_count > 1 ? StatusItem.Highlight.NOTICE : error_count > 4 ? StatusItem.Highlight.BAD : StatusItem.Highlight.NORMAL));

        if (max_wakeup_jitter > 5000) {
            l.add(new StatusItem("Slowest Wakeup ", JoH.niceTimeScalar(max_wakeup_jitter), max_wakeup_jitter > Constants.SECOND_IN_MS * 10 ? StatusItem.Highlight.CRITICAL : StatusItem.Highlight.NOTICE));
        }

        if (JoH.buggy_samsung) {
            l.add(new StatusItem("Buggy Samsung", "Using workaround", max_wakeup_jitter < TOLERABLE_JITTER ? StatusItem.Highlight.GOOD : StatusItem.Highlight.BAD));
        }

        final String tx_id = getTransmitterID();

        if (Pref.getBooleanDefaultFalse("wear_sync") &&
                Pref.getBooleanDefaultFalse("enable_wearG5")) {
            l.add(new StatusItem("Watch Service State", lastStateWatch));
            if (static_last_timestamp_watch > 0) {
                l.add(new StatusItem("Watch got Glucose", JoH.niceTimeSince(static_last_timestamp_watch) + " ago"));
            }
        }

        // firmware details
        final VersionRequestRxMessage vr = Ob1G5StateMachine.getFirmwareDetails(tx_id);
        try {
            if ((vr != null) && (vr.firmware_version_string.length() > 0)) {

                l.add(new StatusItem("Firmware Version", vr.firmware_version_string));
                if (Home.get_engineering_mode()) {
                    l.add(new StatusItem("Bluetooth Version", vr.bluetooth_firmware_version_string));
                    l.add(new StatusItem("Other Version", vr.other_firmware_version));
                    l.add(new StatusItem("Hardware Version", vr.hardwarev));
                    if (vr.asic != 61440)
                        l.add(new StatusItem("ASIC", vr.asic, StatusItem.Highlight.NOTICE)); // TODO color code
                }
            }
        } catch (NullPointerException e) {
            l.add(new StatusItem("Version", "Information corrupted", StatusItem.Highlight.BAD));
        }

        // battery details
        final BatteryInfoRxMessage bt = Ob1G5StateMachine.getBatteryDetails(tx_id);
        long last_battery_query = PersistentStore.getLong(G5_BATTERY_FROM_MARKER + tx_id);
        if (getBatteryStatusNow) {
            l.add(new StatusItem("Battery Status Request Queued", "Will attempt to read battery status on next sensor reading", StatusItem.Highlight.NOTICE, "long-press",
                    new Runnable() {
                        @Override
                        public void run() {
                            getBatteryStatusNow = false;
                        }
                    }));
        }
        if ((bt != null) && (last_battery_query > 0)) {
            l.add(new StatusItem("Battery Last queried", JoH.niceTimeSince(last_battery_query) + " " + "ago", StatusItem.Highlight.NORMAL, "long-press",
                    new Runnable() {
                        @Override
                        public void run() {
                            getBatteryStatusNow = true;
                        }
                    }));
            if (vr != null) {
                final String battery_status = TransmitterStatus.getBatteryLevel(vr.status).toString();
                if (!battery_status.equals("OK"))
                    l.add(new StatusItem("Transmitter Status", battery_status, StatusItem.Highlight.BAD));
            }
            l.add(new StatusItem("Transmitter Days", bt.runtime + ((last_transmitter_timestamp > 0) ? " / " + JoH.qs((double) last_transmitter_timestamp / 86400, 1) : "")));
            l.add(new StatusItem("Voltage A", bt.voltagea, bt.voltagea < LOW_BATTERY_WARNING_LEVEL ? StatusItem.Highlight.BAD : StatusItem.Highlight.NORMAL));
            l.add(new StatusItem("Voltage B", bt.voltageb, bt.voltageb < (LOW_BATTERY_WARNING_LEVEL - 10) ? StatusItem.Highlight.BAD : StatusItem.Highlight.NORMAL));
            l.add(new StatusItem("Resistance", bt.resist, bt.resist > 1400 ? StatusItem.Highlight.BAD : (bt.resist > 1000 ? StatusItem.Highlight.NOTICE : (bt.resist > 750 ? StatusItem.Highlight.NORMAL : StatusItem.Highlight.GOOD))));
            l.add(new StatusItem("Temperature", bt.temperature + " \u2103"));
        }

        return l;
    }
}
