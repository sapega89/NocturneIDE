# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for potential SQL injections risks.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright (C) 2018 [Victor Torre](https://github.com/ehooo)
#
# SPDX-License-Identifier: Apache-2.0
#

import ast

import AstUtilities


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Call": [
            (checkDjangoExtraUsed, ("S610",)),
            (checkDjangoRawSqlUsed, ("S611",)),
        ],
    }


def keywords2dict(keywords):
    """
    Function to extract keywords arguments into a dictionary.

    @param keywords list of keyword nodes
    @type list of ast.keyword
    @return dictionary with keyword name and value
    @rtype dict
    """
    kwargs = {}
    for node in keywords:
        if isinstance(node, ast.keyword):
            kwargs[node.arg] = node.value
    return kwargs


def checkDjangoExtraUsed(reportError, context, _config):
    """
    Function to check for potential SQL injection on extra function.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if context.callFunctionName == "extra":
        kwargs = keywords2dict(context.node.keywords)
        args = context.node.args
        if args:
            if len(args) >= 1:
                kwargs["select"] = args[0]
            if len(args) >= 2:
                kwargs["where"] = args[1]
            if len(args) >= 3:
                kwargs["params"] = args[2]
            if len(args) >= 4:
                kwargs["tables"] = args[3]
            if len(args) >= 5:
                kwargs["order_by"] = args[4]
            if len(args) >= 6:
                kwargs["select_params"] = args[5]
        insecure = False
        for key in ["where", "tables"]:
            if key in kwargs:
                if isinstance(kwargs[key], ast.List):
                    for val in kwargs[key].elts:
                        if not AstUtilities.isString(val):
                            insecure = True
                            break
                else:
                    insecure = True
                    break
        if not insecure and "select" in kwargs:
            if isinstance(kwargs["select"], ast.Dict):
                for k in kwargs["select"].keys:
                    if not AstUtilities.isString(k):
                        insecure = True
                        break
                if not insecure:
                    for v in kwargs["select"].values:
                        if not AstUtilities.isString(v):
                            insecure = True
                            break
            else:
                insecure = True

        if insecure:
            reportError(
                context.node.lineno - 1, context.node.col_offset, "S610", "M", "M"
            )


def checkDjangoRawSqlUsed(reportError, context, _config):
    """
    Function to check for potential SQL injection on RawSQL function.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    if (
        context.isModuleImportedLike("django.db.models")
        and context.callFunctionName == "RawSQL"
    ):
        if context.node.args:
            sql = context.node.args[0]
        else:
            kwargs = keywords2dict(context.node.keywords)
            sql = kwargs["sql"]
        if not AstUtilities.isString(sql):
            reportError(
                context.node.lineno - 1, context.node.col_offset, "S611", "M", "M"
            )
