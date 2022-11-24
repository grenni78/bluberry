"""
"""
from enum import Enum

class StatusItem:

    class Highlight(Enum):
        NORMAL = 0
        GOOD = 1
        BAD = 2
        NOTICE = 3
        CRITICAL = 4

    name = ""
    value = ""
    highlight = ""
    button_name = ""

    def __init__(self, name, value, highlight, button_name):
        self.name = name
        self.value = value
        self.highlight = highlight
        self.button_name = button_name


