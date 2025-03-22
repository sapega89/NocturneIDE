# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for insecure except blocks.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#

import ast

from Security.SecurityDefaults import SecurityDefaults


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "ExceptHandler": [
            (checkTryExceptPass, ("S110",)),
            (checkTryExceptContinue, ("S112",)),
        ],
        "Call": [
            (checkContextlibSuppress, ("S113",)),
        ],
    }


def checkTryExceptPass(reportError, context, config):
    """
    Function to check for a pass in the except block.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    checkTypedException = (
        config["check_typed_exception"]
        if config and "check_typed_exception" in config
        else SecurityDefaults["check_typed_exception"]
    )

    node = context.node
    if len(node.body) == 1:
        if (
            not checkTypedException
            and node.type is not None
            and getattr(node.type, "id", None) not in ("BaseException", "Exception")
        ):
            return

        if isinstance(node.body[0], ast.Pass):
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S110",
                "L",
                "H",
            )


def checkTryExceptContinue(reportError, context, config):
    """
    Function to check for a continue in the except block.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    checkTypedException = (
        config["check_typed_exception"]
        if config and "check_typed_exception" in config
        else SecurityDefaults["check_typed_exception"]
    )

    node = context.node
    if len(node.body) == 1:
        if (
            not checkTypedException
            and node.type is not None
            and getattr(node.type, "id", None) not in ("BaseException", "Exception")
        ):
            return

        if isinstance(node.body[0], ast.Continue):
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S112",
                "L",
                "H",
            )


def checkContextlibSuppress(reportError, context, config):
    """
    Function to check for a contextlib.suppress with a non-specific Exception.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    checkTypedException = (
        config["check_typed_exception"]
        if config and "check_typed_exception" in config
        else SecurityDefaults["check_typed_exception"]
    )

    imported = context.isModuleImportedExact("contextlib")
    qualname = context.callFunctionNameQual
    if not imported and isinstance(qualname, str):
        return

    qualnameList = qualname.split(".")
    func = qualnameList[-1]
    if func == "suppress":
        if (
            not checkTypedException
            and "Exception" not in context.callArgs
            and "BaseException" not in context.callArgs
        ):
            return

        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S113",
            "L",
            "H",
        )
