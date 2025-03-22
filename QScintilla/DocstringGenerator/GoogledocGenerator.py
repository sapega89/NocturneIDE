# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the docstring generator for the 'googledoc' style.
"""


def generateDoc(functionInfo, editor):
    """
    Function to generate the docstring line list iaw. Google documentation
    style.

    Note: Text is created with DESCRIPTION placeholders for descriptions and
    TYPE placeholders for type information

    @param functionInfo object containing the function information to base
        the docstring on
    @type FunctionInfo
    @param editor reference to the editor
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

    # determine additional indentation string
    indentWidth = editor.indentationWidth()
    if indentWidth == 0:
        indentWidth = editor.tabWidth()
    indent = indentWidth * " "

    # add the parameters section
    if functionInfo.argumentsList:
        lines.append("")
        lines.append("Args:")
        for argName, argType, argValue in functionInfo.argumentsList:
            argLine = "{0}{1} ".format(indent, argName)
            argLine += "("
            if argType:
                argLine += "{0}".format(argType)
            else:
                argLine += "TYPE"
            argLine += "):"
            lines.append(argLine)
            argLine = "{0}".format(2 * indent)
            if argValue:
                argLine += "Optional; "
            argLine += "DESCRIPTION"
            if argValue:
                argLine += " Defaults to {0}.".format(argValue)
            lines.append(argLine)

    # add return section
    lines.append("")
    if functionInfo.hasYield:
        lines.append("Yields:")
    else:
        lines.append("Returns:")
    if functionInfo.returnTypeAnnotated:
        lines.append(
            "{0}{1}: DESCRIPTION".format(indent, functionInfo.returnTypeAnnotated)
        )
    elif functionInfo.returnValueInBody:
        lines.append("{0}TYPE: DESCRIPTION".format(indent))
    else:
        lines.append("{0}None".format(indent))

    # add an exceptions section, if function raises something
    if functionInfo.raiseList:
        lines.append("")
        lines.append("Raises:")
        for exc in sorted(functionInfo.raiseList):
            lines.append("{0}{1}: DESCRIPTION".format(indent, exc))

    return lines
