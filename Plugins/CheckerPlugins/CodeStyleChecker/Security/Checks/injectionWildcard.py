# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for use of wildcard injection.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#

from Security.SecurityDefaults import SecurityDefaults


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Call": [
            (checkLinuxCommandsWildcardInjection, ("S609",)),
        ],
    }


def checkLinuxCommandsWildcardInjection(reportError, context, config):
    """
    Function to check for use of wildcard injection.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    subProcessFunctionNames = (
        config["shell_injection_subprocess"]
        if config and "shell_injection_subprocess" in config
        else SecurityDefaults["shell_injection_subprocess"]
    )

    shellFunctionNames = (
        config["shell_injection_shell"]
        if config and "shell_injection_shell" in config
        else SecurityDefaults["shell_injection_shell"]
    )

    vulnerableFunctions = ["chown", "chmod", "tar", "rsync"]
    if (
        context.callFunctionNameQual in shellFunctionNames
        or (
            context.callFunctionNameQual in subProcessFunctionNames
            and context.checkCallArgValue("shell", "True")
        )
    ) and context.callArgsCount >= 1:
        callArgument = context.getCallArgAtPosition(0)
        argumentString = ""
        if isinstance(callArgument, list):
            for li in callArgument:
                argumentString += " {0}".format(li)
        elif isinstance(callArgument, str):
            argumentString = callArgument

        if argumentString != "":
            for vulnerableFunction in vulnerableFunctions:
                if vulnerableFunction in argumentString and "*" in argumentString:
                    lineNo = context.getLinenoForCallArg("shell")
                    if lineNo < 1:
                        lineNo = context.node.lineno
                    offset = context.getOffsetForCallArg("shell")
                    if offset < 0:
                        offset = context.node.col_offset
                    reportError(
                        lineNo - 1,
                        offset,
                        "S609",
                        "H",
                        "M",
                        context.callFunctionNameQual,
                    )
