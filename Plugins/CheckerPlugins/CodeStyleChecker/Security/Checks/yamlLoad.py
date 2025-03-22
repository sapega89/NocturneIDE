# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for the use of yaml load functions.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright (c) 2016 Rackspace, Inc.
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
        "Call": [
            (checkYamlLoad, ("S506",)),
        ],
    }


def checkYamlLoad(reportError, context, _config):
    """
    Function to check for the use of yaml load functions.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    imported = context.isModuleImportedExact("yaml")
    qualname = context.callFunctionNameQual
    if not imported and isinstance(qualname, str):
        return

    qualnameList = qualname.split(".")
    func = qualnameList[-1]
    if all(
        [
            "yaml" in qualnameList,
            func == "load",
            not context.checkCallArgValue("Loader", "SafeLoader"),
            not context.checkCallArgValue("Loader", "CSafeLoader"),
            context.getCallArgAtPosition(1) != "SafeLoader",
            context.getCallArgAtPosition(1) != "CSafeLoader",
        ]
    ):
        reportError(context.node.lineno - 1, context.node.col_offset, "S506", "M", "H")
