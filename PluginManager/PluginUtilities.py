# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing common utility functions needed for plugin management.
"""


def getPluginHeaderEntry(plugin, entry, default):
    """
    Function to get an entry of the plugin header.

    @param plugin reference to the plugin module
    @type module
    @param entry name of the entry
    @type str
    @param default value to be returned if the entry does not exist
    @type Any
    @return requested value
    @rtype Any
    """
    header = getattr(plugin, "__header__", None)
    if header:
        return header.get(entry, default)
    else:
        # old-style plugin header
        return getattr(plugin, entry, default)


def hasPluginHeaderEntry(plugin, entry):
    """
    Function to check, if the plugin header contains the given entry.

    @param plugin reference to the plugin module
    @type module
    @param entry name of the entry
    @type str
    @return flag indicating the existence
    @rtype bool
    """
    header = getattr(plugin, "__header__", None)
    if header:
        return entry in header
    else:
        # old-style plugin header
        return hasattr(plugin, entry)
