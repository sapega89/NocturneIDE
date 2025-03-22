# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for shell injection.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#

import ast
import re

import AstUtilities

from Security.SecurityDefaults import SecurityDefaults

# This regex starts with a windows drive letter (eg C:)
# or one of our path delimeter characters (/, \, .)
fullPathMatchRe = re.compile(r"^(?:[A-Za-z](?=\:)|[\\\/\.])")


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Call": [
            (checkSubprocessPopenWithShell, ("S602",)),
            (checkSubprocessPopenWithoutShell, ("S603",)),
            (checkOtherFunctionWithShell, ("S604",)),
            (checkStartProcessWithShell, ("S605",)),
            (checkStartProcessWithNoShell, ("S606",)),
            (checkStartProcessWithPartialPath, ("S607",)),
        ],
    }


def _evaluateShellCall(context):
    """
    Function to determine the severity of a shell call.

    @param context context to be inspected
    @type SecurityContext
    @return severity level (L, M or H)
    @rtype str
    """
    noFormatting = AstUtilities.isString(context.node.args[0])

    if noFormatting:
        return "L"
    else:
        return "H"


def hasShell(context):
    """
    Function to check, if the node of the context contains the shell keyword.

    @param context context to be inspected
    @type SecurityContext
    @return flag indicating the value of the 'shell' argument
    @rtype bool
    """
    keywords = context.node.keywords
    result = False
    if "shell" in context.callKeywords:
        for key in keywords:
            if key.arg == "shell":
                val = key.value
                if AstUtilities.isNumber(val):
                    result = bool(val.value)
                elif isinstance(val, ast.List):
                    result = bool(val.elts)
                elif isinstance(val, ast.Dict):
                    result = bool(val.keys)
                elif isinstance(val, ast.Name) and val.id in ["False", "None"]:
                    result = False
                elif AstUtilities.isNameConstant(val):
                    result = val.value
                else:
                    result = True

    return result


def checkSubprocessPopenWithShell(reportError, context, config):
    """
    Function to check for use of popen with shell equals true.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    functionNames = (
        config["shell_injection_subprocess"]
        if config and "shell_injection_subprocess" in config
        else SecurityDefaults["shell_injection_subprocess"]
    )

    if (
        context.callFunctionNameQual in functionNames
        and hasShell(context)
        and len(context.callArgs) > 0
    ):
        sev = _evaluateShellCall(context)
        if sev == "L":
            reportError(
                context.getLinenoForCallArg("shell") - 1,
                context.getOffsetForCallArg("shell"),
                "S602.L",
                sev,
                "H",
            )
        else:
            reportError(
                context.getLinenoForCallArg("shell") - 1,
                context.getOffsetForCallArg("shell"),
                "S602.H",
                sev,
                "H",
            )


def checkSubprocessPopenWithoutShell(reportError, context, config):
    """
    Function to check for use of popen without shell equals true.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    functionNames = (
        config["shell_injection_subprocess"]
        if config and "shell_injection_subprocess" in config
        else SecurityDefaults["shell_injection_subprocess"]
    )

    if context.callFunctionNameQual in functionNames and not hasShell(context):
        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S603",
            "L",
            "H",
        )


def checkOtherFunctionWithShell(reportError, context, config):
    """
    Function to check for any function with shell equals true.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    functionNames = (
        config["shell_injection_subprocess"]
        if config and "shell_injection_subprocess" in config
        else SecurityDefaults["shell_injection_subprocess"]
    )

    if context.callFunctionNameQual not in functionNames and hasShell(context):
        reportError(
            context.getLinenoForCallArg("shell") - 1,
            context.getOffsetForCallArg("shell"),
            "S604",
            "M",
            "L",
        )


def checkStartProcessWithShell(reportError, context, config):
    """
    Function to check for starting a process with a shell.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    functionNames = (
        config["shell_injection_shell"]
        if config and "shell_injection_shell" in config
        else SecurityDefaults["shell_injection_shell"]
    )

    if context.callFunctionNameQual in functionNames and len(context.callArgs) > 0:
        sev = _evaluateShellCall(context)
        if sev == "L":
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S605.L",
                sev,
                "H",
            )
        else:
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S605.H",
                sev,
                "H",
            )


def checkStartProcessWithNoShell(reportError, context, config):
    """
    Function to check for starting a process with no shell.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    functionNames = (
        config["shell_injection_noshell"]
        if config and "shell_injection_noshell" in config
        else SecurityDefaults["shell_injection_noshell"]
    )

    if context.callFunctionNameQual in functionNames:
        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S606",
            "L",
            "M",
        )


def checkStartProcessWithPartialPath(reportError, context, config):
    """
    Function to check for starting a process with no shell.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    functionNames = (
        config["shell_injection_subprocess"]
        if config and "shell_injection_subprocess" in config
        else SecurityDefaults["shell_injection_subprocess"]
    )

    if config and "shell_injection_shell" in config:
        functionNames += config["shell_injection_shell"]
    else:
        functionNames += SecurityDefaults["shell_injection_shell"]

    if config and "shell_injection_noshell" in config:
        functionNames += config["shell_injection_noshell"]
    else:
        functionNames += SecurityDefaults["shell_injection_noshell"]

    if len(context.callArgs) and context.callFunctionNameQual in functionNames:
        node = context.node.args[0]

        # some calls take an arg list, check the first part
        if isinstance(node, ast.List) and node.elts:
            node = node.elts[0]

        # make sure the param is a string literal and not a var name
        if AstUtilities.isString(node) and not fullPathMatchRe.match(node.value):
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S607",
                "L",
                "H",
            )
