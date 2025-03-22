# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the docstring generator for the 'ericdoc' style.
"""


def generateDoc(functionInfo, _editor):
    """
    Function to generate the docstring line list iaw. eric documentation
    style.

    Note: Text is created with DESCRIPTION placeholders for descriptions and
    TYPE placeholders for type information

    @param functionInfo object containing the function information to base
        the docstring on
    @type FunctionInfo
    @param _editor reference to the editor  (unused)
    @type Editor
    @return list of docstring lines
    @rtype str
    """
    # __IGNORE_WARNING_D202__
    lines = []

    # create a basic/partial function description
    if functionInfo.functionType == "classmethod":
        descr = "Class method "
    elif functionInfo.functionType == "staticmethod":
        descr = "Static method "
    elif functionInfo.functionType == "constructor":
        descr = "Constructor"
    else:
        if functionInfo.visibility == "public":
            descr = "Public "
        elif functionInfo.visibility == "protected":
            descr = "Protected "
        elif functionInfo.visibility == "private":
            descr = "Private "
        elif functionInfo.visibility == "special":
            descr = "Special "
        else:
            descr = ""

        if len(functionInfo.argumentsList) > 0 and functionInfo.argumentsList[0][0] in (
            "self",
            "cls",
            "this",
        ):
            if functionInfo.isAsync:
                descr += "coroutine "
            elif functionInfo.functionType == "qtslot":
                descr += "slot "
            else:
                descr += "method "
        else:
            if functionInfo.isAsync:
                descr = "Coroutine "
            elif functionInfo.functionType == "qtslot":
                descr = "Slot "
            else:
                descr = "Function "
    lines.append(descr)

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
    tag = "@param"
    for argName, argType, argValue in functionInfo.argumentsList:
        if argName == "*":
            tag = "@keyparam"
            continue

        argLine = "{0} {1} DESCRIPTION".format(tag, argName)
        if argValue:
            argLine += " (defaults to {0})".format(argValue)
        lines.append(argLine)

        if argType is None:
            argType = "TYPE"
        argLine = "@type {0}".format(argType)
        if argValue:
            argLine += " (optional)"
        lines.append(argLine)

    # add return section
    if (
        functionInfo.hasYield
        or functionInfo.returnValueInBody
        or (
            functionInfo.returnTypeAnnotated
            and functionInfo.returnTypeAnnotated != "None"
        )
    ):
        if functionInfo.hasYield:
            lines.append("@yield DESCRIPTION")
            rType = "@ytype"
        else:
            lines.append("@return DESCRIPTION")
            rType = "@rtype"
        if functionInfo.returnTypeAnnotated:
            lines.append("{0} {1}".format(rType, functionInfo.returnTypeAnnotated))
        else:
            lines.append("{0} TYPE".format(rType))

    # add an exceptions section, if function raises something
    if functionInfo.raiseList:
        for exc in sorted(functionInfo.raiseList):
            lines.append("@exception {0} DESCRIPTION".format(exc))

    return lines
