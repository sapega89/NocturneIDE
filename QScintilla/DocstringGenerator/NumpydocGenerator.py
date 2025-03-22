# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the docstring generator for the 'numpydoc' style.
"""


def generateDoc(functionInfo, editor):
    """
    Function to generate the docstring line list iaw. NumPy documentation
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
        lines.append("Parameters")
        lines.append("----------")
        for argName, argType, argValue in functionInfo.argumentsList:
            argLine = "{0} : ".format(argName)
            if argType:
                argLine += "{0}".format(argType)
            else:
                argLine += "TYPE"
            if argValue:
                argLine += ", optional"
            lines.append(argLine)
            argLine = "{0}DESCRIPTION.".format(indent)
            if argValue:
                argLine += " The default is {0}".format(argValue)
            lines.append(argLine)

    # add an exceptions section, if function raises something
    if functionInfo.raiseList:
        lines.append("")
        lines.append("Raises")
        lines.append("------")
        for exc in sorted(functionInfo.raiseList):
            lines.append("{0}".format(exc))
            lines.append("{0}DESCRIPTION".format(indent))

    # add return section
    lines.append("")
    if functionInfo.hasYield:
        lines.append("Yields")
        lines.append("------")
    else:
        lines.append("Returns")
        lines.append("-------")
    if functionInfo.returnTypeAnnotated:
        lines.append("{0}".format(functionInfo.returnTypeAnnotated))
        lines.append("{0}DESCRIPTION.".format(indent))
    elif functionInfo.returnValueInBody:
        lines.append("TYPE")
        lines.append("{0}DESCRIPTION.".format(indent))
    else:
        lines.append("{0}None".format(indent))

    return lines
