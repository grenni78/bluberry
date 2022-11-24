"""
Schnittstelle zum Benutzer
"""
def message(type, message):
    print ("User interaction '"+type+"'")
    print ("  " + message)

def warning(type, message):
    print("User warning '" + type + "'")
    print("  " + message)

def info(type, message):
    print("User Info '" + type + "'")
    print("  " + message)

def refreshBgCharts():
    pass