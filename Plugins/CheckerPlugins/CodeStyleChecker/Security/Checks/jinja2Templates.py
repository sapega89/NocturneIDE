# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for not auto escaping in jinja2.
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
            (checkJinja2Autoescape, ("S701",)),
        ],
    }


def checkJinja2Autoescape(reportError, context, _config):
    """
    Function to check for not auto escaping in jinja2.

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
        if "jinja2" in qualnameList and func == "Environment":
            for node in ast.walk(context.node):
                if isinstance(node, ast.keyword):
                    # definite autoescape = False
                    if getattr(node, "arg", None) == "autoescape" and (
                        getattr(node.value, "id", None) == "False"
                        or getattr(node.value, "value", None) is False
                    ):
                        reportError(
                            context.node.lineno - 1,
                            context.node.col_offset,
                            "S701.1",
                            "H",
                            "H",
                        )
                        return

                    # found autoescape
                    if getattr(node, "arg", None) == "autoescape":
                        value = getattr(node, "value", None)
                        if (
                            getattr(value, "id", None) == "True"
                            or getattr(value, "value", None) is True
                            or (
                                isinstance(value, ast.Call)
                                and (
                                    getattr(value.func, "attr", None)
                                    == "select_autoescape"
                                    or getattr(value.func, "id", None)
                                    == "select_autoescape"
                                )
                            )
                        ):
                            return

                        else:
                            reportError(
                                context.node.lineno - 1,
                                context.node.col_offset,
                                "S701.1",
                                "H",
                                "M",
                            )
                            return

            # We haven't found a keyword named autoescape, indicating default
            # behavior
            reportError(
                context.node.lineno - 1,
                context.node.col_offset,
                "S701.2",
                "H",
                "H",
            )
