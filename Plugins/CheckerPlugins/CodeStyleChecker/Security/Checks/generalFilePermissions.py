# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for setting too permissive file permissions.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#

import stat


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Call": [
            (checkFilePermissions, ("S102",)),
        ],
    }


def _statIsDangerous(mode):
    """
    Function to check for dangerous stat values.

    @param mode file mode to be checked
    @type int
    @return mode with masked dangerous values
    @rtype int
    """
    return (
        mode & stat.S_IWOTH
        or mode & stat.S_IWGRP
        or mode & stat.S_IXGRP
        or mode & stat.S_IXOTH
    )


def checkFilePermissions(reportError, context, _config):
    """
    Function to check for setting too permissive file permissions.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if "chmod" in context.callFunctionName and context.callArgsCount == 2:
        mode = context.getCallArgAtPosition(1)

        if mode is not None and isinstance(mode, int) and _statIsDangerous(mode):
            # world writable is an HIGH, group executable is a MEDIUM
            if mode & stat.S_IWOTH:
                severity = "H"
            else:
                severity = "M"

            filename = context.getCallArgAtPosition(0)
            if filename is None:
                filename = "NOT PARSED"

            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S103",
                severity,
                "H",
                oct(mode),
                filename,
            )
