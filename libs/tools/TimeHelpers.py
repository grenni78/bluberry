import time
from datetime import timedelta, datetime
from email import utils
from libs.tools.DexcomCollectionType import DexcomCollectionType

# timestamp (number milliseconds since epoch)
ts = lambda: tsl()

# timestamp (number milliseconds since epoch)
tsl = lambda: int(round(time.time() * 1000))

# time delta from now
msSince = lambda when: tsl() - when

# time delta from when
msTill = lambda when: when - tsl()

absMsSince= lambda when: abs(msSince(when))

# dateteime string from UNIX timestamp yyyy-mm-dd HH:MM:SS
dateTimeText = lambda timestamp: datetime.fromtimestamp(timestamp / 1e3).strftime('%Y-%m-%d %H:%M:%S')

# date string from UNIX timestamp yyyy-mm-dd
dateText = lambda timestamp: datetime.fromtimestamp(timestamp / 1e3).strftime('%Y-%m-%d')

# human radable time difference from time period in ms
def niceTimeSince(diffms):
    ms = msSince(diffms)
    td = timedelta(milliseconds=ms)

    periodString = ""

    if td.days >= 7:
        periodString = str(td.days // 7) + " Wochen"
    elif td.days > 0 and td.days < 7:
        periodString = str(td.days) + " Tage"
    elif td.seconds > 3600:
        periodString = str(td.seconds // 3600) + " Stunden"
    elif td.seconds > 60:
        periodString = str(td.seconds // 60) + " Minuten"
    else:
        periodString = str(td.seconds) + " Sekunden"

    return periodString

# human readable time difference to future time
niceTimeTill = lambda t: niceTimeSince(-msSince(t))

# get RFC822 date string
def getRFC822String(timestamp):
    dt = datetime.fromtimestamp(timestamp / 1e3)
    tt = dt.timetuple()
    ts = time.mktime(tt)
    return utils.formatdate(ts)
    #return dt.strftime("%a, %d %m %Y %H:%m:%S +0100")

def stale_data_millis():
    if DexcomCollectionType.getDexCollectionType() == DexcomCollectionType.LibreAlarm:
        return (60000 * 13)
    return (60000 * 11)
