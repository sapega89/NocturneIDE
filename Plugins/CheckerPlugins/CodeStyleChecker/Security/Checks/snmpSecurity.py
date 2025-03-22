# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for the insecure use of SNMP.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright (c) 2018 SolarWinds, Inc.
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
            (checkInsecureVersion, ("S508",)),
            (checkWeakCryptography, ("S509",)),
        ],
    }


def checkInsecureVersion(reportError, context, _config):
    """
    Function to check for the use of insecure SNMP version like
    v1, v2c.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if context.callFunctionNameQual == "pysnmp.hlapi.CommunityData" and (
        context.checkCallArgValue("mpModel", 0)
        or context.check_call_arg_value("mpModel", 1)
    ):
        # We called community data. Lets check our args
        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S508",
            "M",
            "H",
        )


def checkWeakCryptography(reportError, context, _config):
    """
    Function to check for the use of insecure SNMP cryptography
    (i.e. v3 using noAuthNoPriv).

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if (
        context.callFunctionNameQual == "pysnmp.hlapi.UsmUserData"
        and context.callArgsCount < 3
    ):
        reportError(context.node.lineno - 1, context.node.col_offset, "S509", "M", "H")
