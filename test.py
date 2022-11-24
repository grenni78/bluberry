# testing the time helper functions
from libs.tools import TimeHelpers
from libs import preferences
import os


ts = TimeHelpers.tsl()

print ("Test der tools:")
print ("Timestamp: ",TimeHelpers.ts())

print ("Milliseconds since: ",TimeHelpers.msSince(ts - 7890))

print ("Absolute milliseconds since: ",TimeHelpers.absMsSince(ts - 7890))

print ("Milliseconds till: ", TimeHelpers.msTill(ts + 12456))

print ("Date-time-text: ", TimeHelpers.dateTimeText(ts))

print ("Date-text: ", TimeHelpers.dateText(ts))

print ("Nice time since: ",TimeHelpers.niceTimeSince(ts - 12058))

print ("RFC822: ", TimeHelpers.getRFC822String(ts))


