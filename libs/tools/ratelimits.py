"""
Mange Ratelimits
"""

from libs.tools import datetime

_rates = {}

# removes a rate limit named "name" from the dictionary
def clearRatelimit(name):
    if name in _rates:
        _rates.pop(name)

# return true if below rate limit in milliseconds
def ratelimitmilli(name, milliseconds):
    # check if over limit
    if name in _rates and (datetime.tsl() - _rates[name] < milliseconds ):
        return False

    # not over limit
    _rates[name] = datetime.tsl()
    return True

# alias for ratelimit
quietratelimit = lambda name, seconds: ratelimit(name, seconds)

# return true if below rate limit in seconds
ratelimit = lambda name, seconds: ratelimitmilli(name, seconds * 1000)

