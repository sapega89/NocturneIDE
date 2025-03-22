# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for the use of 'torch.load' and 'torch.save'.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright (c) 2024 Stacklok, Inc.
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
            (checkPytorchLoadSave, ("S614",)),
        ],
    }


def checkPytorchLoadSave(reportError, context, _config):
    """
    Function to check for the use of 'torch.load' and 'torch.save'.

    Using `torch.load` with untrusted data can lead to arbitrary code
    execution, and improper use of `torch.save` might expose sensitive
    data or lead to data corruption.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param _config dictionary with configuration data (unused)
    @type dict
    """
    imported = context.isModuleImportedExact("torch")
    qualname = context.callFunctionNameQual
    if not imported and isinstance(qualname, str):
        return

    qualnameList = qualname.split(".")
    func = qualnameList[-1]
    if all(
        [
            "torch" in qualnameList,
            func in ["load", "save"],
            not context.checkCallArgValue("map_location", "cpu"),
        ]
    ):
        reportError(
            context.node.lineno - 1,
            context.node.col_offset,
            "S614",
            "M",
            "H",
        )
