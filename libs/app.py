"""
global share
"""


def initialize(application, database, userinteract, logger, preferences, persistent_preferences):
    global app, db, ui, log, pref, ppref, TERMINATE, DEBUG
    app = application
    db = database
    log = logger
    pref = preferences
    ppref = persistent_preferences
    ui = userinteract
    TERMINATE = False
    DEBUG = False

