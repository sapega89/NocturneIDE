# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for insecure usage of tmp file/directory.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
# ...r\Security\Checks\generalHardcodedTmp.py

from Security.SecurityDefaults import SecurityDefaults


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Str": [
            (checkHardcodedTmpDirectory, ("S108",)),
        ],
    }


def checkHardcodedTmpDirectory(reportError, context, config):
    """
    Function to check for insecure usage of tmp file/directory.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    tmpDirs = (
        config["hardcoded_tmp_directories"]
        if config and "hardcoded_tmp_directories" in config
        else SecurityDefaults["hardcoded_tmp_directories"]
    )

    if any(context.stringVal.startswith(s) for s in tmpDirs):
        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S108",
            "M",
            "M",
        )
