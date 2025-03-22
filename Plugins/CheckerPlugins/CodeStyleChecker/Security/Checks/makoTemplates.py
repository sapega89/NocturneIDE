# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for use of mako templates.
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
            (checkMakoTemplateUsage, ("S702",)),
        ],
    }


def checkMakoTemplateUsage(reportError, context, _config):
    """
    Function to check for use of mako templates.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if isinstance(context.callFunctionNameQual, str):
        qualnameList = context.callFunctionNameQual.split(".")
        func = qualnameList[-1]
        if "mako" in qualnameList and func == "Template":
            # unlike Jinja2, mako does not have a template wide autoescape
            # feature and thus each variable must be carefully sanitized.
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S702",
                "M",
                "H",
            )
