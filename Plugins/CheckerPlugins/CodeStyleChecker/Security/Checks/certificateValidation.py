# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for switched off certificate validation.
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
        "Call": [
            (checkNoCertificateValidation, ("S501",)),
        ],
    }


def checkNoCertificateValidation(reportError, context, _config):
    """
    Function to check for switched off certificate validation.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    httpVerbs = {"get", "options", "head", "post", "put", "patch", "delete"}
    httpxAttrs = {"request", "stream", "Client", "AsyncClient"} | httpVerbs
    qualName = context.callFunctionNameQual.split(".")[0]
    if (
        (qualName == "requests" and context.callFunctionName in httpVerbs)
        or (qualName == "httpx" and context.callFunctionName in httpxAttrs)
    ) and context.checkCallArgValue("verify", "False"):
        reportError(
            context.getLinenoForCallArg("verify") - 1,
            context.getOffsetForCallArg("verify"),
            "S501",
            "H",
            "H",
        )
