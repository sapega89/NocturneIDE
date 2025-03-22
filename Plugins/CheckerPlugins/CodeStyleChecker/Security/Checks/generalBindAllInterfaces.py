# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for binding to all interfaces.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Str": [
            (checkBindAllInterfaces, ("S104",)),
        ],
    }


def checkBindAllInterfaces(reportError, context, _config):
    """
    Function to check for binding to all interfaces.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if context.stringVal == "0.0.0.0":  # secok
        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S104",
            "M",
            "M",
        )
