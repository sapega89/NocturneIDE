# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a check for SQL injection.
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

from Security import SecurityUtils


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Str": [
            (checkHardcodedSqlExpressions, ("S608",)),
        ],
    }


SIMPLE_SQL_RE = re.compile(
    r"(select\s.*from\s|"
    r"delete\s+from\s|"
    r"insert\s+into\s.*values\s|"
    r"update\s.*set\s)",
    re.IGNORECASE | re.DOTALL,
)


def _checkString(data):
    """
    Function to check a given string against the list of search patterns.

    @param data string data to be checked
    @type str
    @return flag indicating a match
    @rtype bool
    """
    return SIMPLE_SQL_RE.search(data) is not None


def _evaluateAst(node):
    """
    Function to analyze the given ast node.

    @param node ast node to be analyzed
    @type ast.Constant
    @return tuple containing a flag indicating an execute call, the resulting
        statement and a flag indicating a string replace call
    @rtype tuple of (bool, str, bool)
    """
    wrapper = None
    statement = ""
    strReplace = False

    if isinstance(node._securityParent, ast.BinOp):
        out = SecurityUtils.concatString(node, node._securityParent)
        wrapper = out[0]._securityParent
        statement = out[1]
    elif isinstance(
        node._securityParent, ast.Attribute
    ) and node._securityParent.attr in ("format", "replace"):
        statement = node.value
        # Hierarchy for "".format() is Wrapper -> Call -> Attribute -> Str
        wrapper = node._securityParent._securityParent._securityParent
        if node._securityParent.attr == "replace":
            strReplace = True
    elif hasattr(ast, "JoinedStr") and isinstance(node._securityParent, ast.JoinedStr):
        substrings = [
            child
            for child in node._securityParent.values
            if isinstance(child, ast.Constant) and isinstance(node.value, str)
        ]
        # JoinedStr consists of list of Constant and FormattedValue
        # instances. Let's perform one test for the whole string
        # and abandon all parts except the first one to raise one
        # failed test instead of many for the same SQL statement.
        if substrings and node == substrings[0]:
            statement = "".join([str(child.value) for child in substrings])
            wrapper = node._securityParent._securityParent

    if isinstance(wrapper, ast.Call):  # wrapped in "execute" call?
        names = ["execute", "executemany"]
        name = SecurityUtils.getCalledName(wrapper)
        return (name in names, statement, strReplace)
    else:
        return (False, statement, strReplace)


def checkHardcodedSqlExpressions(reportError, context, _config):
    """
    Function to check for SQL injection.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    executeCall, statement, strReplace = _evaluateAst(context.node)
    if _checkString(statement):
        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S608",
            "M",
            "M" if executeCall and not strReplace else "L",
        )
