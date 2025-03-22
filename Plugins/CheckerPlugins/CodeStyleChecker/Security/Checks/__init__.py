# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package containing the various security checker modules.
"""

import collections
import importlib
import os


def generateCheckersDict():
    """
    Function to generate the dictionary with checkers.

    Checker modules are searched for inside this package. Each module
    defining some checks must contain a function 'getChecks()' returning
    a dictionary containing the check type as key and a list of tuples
    with the check function and associated message codes.

    @return dictionary containing list of tuples with checker data
    @rtype dict
    """
    checkersDict = collections.defaultdict(list)

    checkersDirectory = os.path.dirname(__file__)
    checkerModules = [
        os.path.splitext(m)[0]
        for m in os.listdir(checkersDirectory)
        if m != "__init__.py" and m.endswith(".py")
    ]

    for checkerModule in checkerModules:
        try:
            mod = importlib.import_module(".{0}".format(checkerModule), __package__)
        except ImportError:
            continue

        if not hasattr(mod, "getChecks"):
            continue

        modCheckersDict = mod.getChecks()
        for checktype, checks in modCheckersDict.items():
            checkersDict[checktype].extend(checks)

    return checkersDict
