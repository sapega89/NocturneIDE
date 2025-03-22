# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for insecure use of logging.config.listen function.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright (c) 2022 Rajesh Pangare
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
            (checkLoggingConfigListen, ("S612",)),
        ],
    }


def checkLoggingConfigListen(reportError, context, _config):
    """
    Function to check for insecure use of logging.config.listen function.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if (
        context.callFunctionNameQual == "logging.config.listen"
        and "verify" not in context.callKeywords
    ):
        reportError(context.node.lineno - 1, context.node.col_offset, "S612", "M", "H")
