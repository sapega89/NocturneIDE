# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for insecure use of 'tarfile.extracall()'.
"""

#
# This is a modified version of the one found in the bandit package.
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
            (checkTarfileUnsafeMembers, ("S202",)),
        ],
    }


def _getMembersValue(context):
    """
    Function to extract the value of the 'members' argument.

    @param context security context object
    @type SecurityContext
    @return dictionary containing the argument value
    @rtype dict
    """
    for kw in context.node.keywords:
        if kw.arg == "members":
            arg = kw.value
            if isinstance(arg, ast.Call):
                return {"Function": arg.func.id}
            else:
                value = arg.id if isinstance(arg, ast.Name) else arg
                return {"Other": value}

    return {}


def _isFilterData(context):
    """
    Function to check for the filter argument to be 'data'.

    @param context security context object
    @type SecurityContext
    @return flag indicating the 'data' filter
    @rtype bool
    """
    for kw in context.node.keywords:
        if kw.arg == "filter":
            arg = kw.value
            return isinstance(arg, ast.Str) and arg.s == "data"

    return False


def checkTarfileUnsafeMembers(reportError, context, _config):
    """
    Function to check for insecure use of 'tarfile.extracall()'.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if all(
        [
            context.isModuleImportedExact("tarfile"),
            "extractall" in context.callFunctionName,
        ]
    ):
        if "filter" in context.callKeywords and _isFilterData(context):
            return

        if "members" in context.callKeywords:
            members = _getMembersValue(context)
            if "Function" in members:
                reportError(
                    context.node.lineno - 1,
                    context.node.col_offset,
                    "S202.1",
                    "L",
                    "L",
                    str(members),
                )
            else:
                reportError(
                    context.node.lineno - 1,
                    context.node.col_offset,
                    "S202.2",
                    "M",
                    "M",
                    str(members),
                )
        else:
            reportError(
                context.node.lineno - 1, context.node.col_offset, "S202.3", "H", "H"
            )
