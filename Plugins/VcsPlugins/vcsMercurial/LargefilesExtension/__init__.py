# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing the largefiles extension support interface.
"""


def getDefaults():
    """
    Function to get the default values of the extension.

    @return dictionary with default values and parameter as key
    @rtype dict
    """
    return {
        "minsize": 10,  # minimum size in MB
        "pattern": [],  # file name patterns
    }
