# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the docstring generator for the 'sphinxdoc' style.
"""


def generateDoc(functionInfo, _editor):
    """
    Function to generate the docstring line list iaw. Sphinx documentation
    style.

    Note: Text is created with DESCRIPTION placeholders for descriptions and
    TYPE placeholders for type information

    @param functionInfo object containing the function information to base
        the docstring on
    @type FunctionInfo
    @param _editor reference to the editor (unused)
    @type Editor
    @return list of docstring lines
    @rtype str
    """
    # __IGNORE_WARNING_D202__
    lines = []

    # function description
    lines.append("")

    # remove 'self', 'this' or 'cls' from arguments list
    if len(functionInfo.argumentsList) > 0 and functionInfo.argumentsList[0][0] in (
        "self",
        "cls",
        "this",
    ):
        del functionInfo.argumentsList[0]

    # add an empty line if there is one of the other sections
    if (
        functionInfo.argumentsList
        or functionInfo.hasYield
        or functionInfo.returnTypeAnnotated
        or functionInfo.returnValueInBody
        or functionInfo.raiseList
    ):
        lines.append("")

    # add the parameters section
    for argName, argType, argValue in functionInfo.argumentsList:
        argLine = ":param {0}: DESCRIPTION".format(argName)
        if argValue:
            argLine += ", defaults to {0}".format(argValue)
        lines.append(argLine)

        argLine = ":type {0}: ".format(argName)
        if argType:
            argLine += "{0}".format(argType)
        else:
            argLine += "TYPE"
        if argValue:
            argLine += ", optional"
        lines.append(argLine)

    # add an exceptions section, if function raises something
    if functionInfo.raiseList:
        for exc in sorted(functionInfo.raiseList):
            lines.append(":raises {0}: DESCRIPTION".format(exc))

    # add return section
    if (
        functionInfo.hasYield
        or functionInfo.returnValueInBody
        or functionInfo.returnTypeAnnotated
    ):
        if functionInfo.hasYield:
            lines.append(":yield: DESCRIPTION")
        else:
            lines.append(":return: DESCRIPTION")
        if functionInfo.returnTypeAnnotated:
            lines.append(":rtype: {0}".format(functionInfo.returnTypeAnnotated))
        else:
            lines.append(":rtype: TYPE")

    lines.append("")

    return lines
