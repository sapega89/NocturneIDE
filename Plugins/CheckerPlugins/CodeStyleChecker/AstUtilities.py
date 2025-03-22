# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some utility and compatibility functions for working with
the ast module.
"""

import ast
import numbers


def isNumber(node):
    """
    Function to check that a node is a number.

    @param node reference to the node to check
    @type ast.AST
    @return flag indicating a number
    @rtype bool
    """
    return isinstance(node, ast.Constant) and isinstance(node.value, numbers.Number)


def isString(node):
    """
    Function to check that a node is a string.

    @param node reference to the node to check
    @type ast.AST
    @return flag indicating a string
    @rtype bool
    """
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def isBytes(node):
    """
    Function to check that a node is a bytes.

    @param node reference to the node to check
    @type ast.AST
    @return flag indicating a bytes
    @rtype bool
    """
    return isinstance(node, ast.Constant) and isinstance(node.value, bytes)


def isBaseString(node):
    """
    Function to check that a node is a bytes or string.

    @param node reference to the node to check
    @type ast.AST
    @return flag indicating a bytes or string
    @rtype bool
    """
    return isinstance(node, ast.Constant) and isinstance(node.value, (bytes, str))


def isNameConstant(node):
    """
    Function to check that a node is a name constant.

    @param node reference to the node to check
    @type ast.AST
    @return flag indicating a name constant
    @rtype bool
    """
    return isinstance(node, ast.Constant) and not isinstance(
        node.value, (bytes, str, numbers.Number)
    )


def isEllipsis(node):
    """
    Function to check that a node is an ellipsis.

    @param node reference to the node to check
    @type ast.AST
    @return flag indicating an ellipsis
    @rtype bool
    """
    return isinstance(node, ast.Constant) and node.value is Ellipsis


def getValue(node):
    """
    Function to extract the value of a node.

    @param node reference to the node to extract the value from
    @type ast.Constant
    @return value of the node
    @rtype Any
    @exception TypeError raised to indicate an unsupported type
    """
    if not isinstance(node, ast.Constant):
        raise TypeError("Illegal node type passed.")

    return node.value
