# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing utility functions for the code style checker dialogs.
"""

from eric7.EricGui import EricPixmapCache

from .translations import messageCategoryRe


def setItemIcon(itm, column, msgCode, severity=None):
    """
    Function to set the icon of the passed message item.

    @param itm reference to the message item
    @type QTreeWidgetItem
    @param column column for the icon
    @type int
    @param msgCode message code
    @type str
    @param severity severity for message code 'S' (defaults to None)
    @type str (optional)
    """
    match = messageCategoryRe.match(msgCode)
    if match:
        # the message code is OK
        messageCategory = match.group(1)

        if messageCategory in ("W", "C", "M"):
            itm.setIcon(column, EricPixmapCache.getIcon("warning"))
        elif messageCategory == "E":
            itm.setIcon(column, EricPixmapCache.getIcon("syntaxError"))
        elif messageCategory in ("A", "N"):
            itm.setIcon(column, EricPixmapCache.getIcon("namingError"))
        elif messageCategory == "D":
            itm.setIcon(column, EricPixmapCache.getIcon("docstringError"))
        elif messageCategory == "I":
            itm.setIcon(column, EricPixmapCache.getIcon("imports"))
        elif messageCategory == "L":
            itm.setIcon(column, EricPixmapCache.getIcon("logViewer"))
        elif messageCategory == "NO":
            itm.setIcon(column, EricPixmapCache.getIcon("nameOrderError"))
        elif messageCategory == "P":
            itm.setIcon(column, EricPixmapCache.getIcon("dirClosed"))
        elif messageCategory == "Y":
            itm.setIcon(column, EricPixmapCache.getIcon("filePython"))
        elif messageCategory == "S":
            if severity is None:
                itm.setIcon(column, EricPixmapCache.getIcon("securityLow"))
            else:
                if severity == "H":
                    itm.setIcon(column, EricPixmapCache.getIcon("securityLow"))
                elif severity == "M":
                    itm.setIcon(column, EricPixmapCache.getIcon("securityMedium"))
                elif severity == "L":
                    itm.setIcon(column, EricPixmapCache.getIcon("securityHigh"))
                else:
                    itm.setIcon(column, EricPixmapCache.getIcon("securityLow"))
        else:
            # unknown category prefix => warning
            itm.setIcon(column, EricPixmapCache.getIcon("warning"))
    elif msgCode.startswith("-"):
        itm.setIcon(column, EricPixmapCache.getIcon("warning"))
    else:
        # unknown category prefix => warning
        itm.setIcon(column, EricPixmapCache.getIcon("warning"))
