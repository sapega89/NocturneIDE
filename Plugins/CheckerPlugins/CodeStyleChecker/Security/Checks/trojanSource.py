# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for the presence of unicode bidirectional control
characters in Python source files.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright (c) 2024
#
# SPDX-License-Identifier: Apache-2.0
#

from tokenize import detect_encoding


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "File": [
            (checkTrojanSource, ("S613",)),
        ],
    }


BIDI_CHARACTERS = (
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
    "\u200f",
)


def checkTrojanSource(reportError, context, _config):
    """
    Function to check for the presence of unicode bidirectional control
    characters in Python source files.

    Those characters can be embedded in comments and strings to reorder
    source code characters in a way that changes its logic.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    with open(context.filename, "rb") as srcFile:
        encoding, _ = detect_encoding(srcFile.readline)
    with open(context.filename, encoding=encoding) as srcFile:
        for lineno, line in enumerate(srcFile.readlines(), start=0):
            for char in BIDI_CHARACTERS:
                try:
                    colOffset = line.index(char)
                except ValueError:
                    continue
                reportError(
                    lineno,
                    colOffset,
                    "S613",
                    "H",
                    "M",
                    repr(char),
                )
