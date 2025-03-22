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

import ast


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Call": [
            (checkSshNoHostKeyVerification, ("S507",)),
        ],
    }


def checkSshNoHostKeyVerification(reportError, context, _config):
    """
    Function to check for use of mako templates.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if (
        context.isModuleImportedLike("paramiko")
        and context.callFunctionName == "set_missing_host_key_policy"
        and context.node.args
    ):
        policyArgument = context.node.args[0]

        policyArgumentValue = None
        if isinstance(policyArgument, ast.Attribute):
            policyArgumentValue = policyArgument.attr
        elif isinstance(policyArgument, ast.Name):
            policyArgumentValue = policyArgument.id
        elif isinstance(policyArgument, ast.Call):
            if isinstance(policyArgument.func, ast.Attribute):
                policyArgumentValue = policyArgument.func.attr
            elif isinstance(policyArgument.func, ast.Name):
                policyArgumentValue = policyArgument.func.id

        if policyArgumentValue in ["AutoAddPolicy", "WarningPolicy"]:
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S507",
                "H",
                "M",
            )
