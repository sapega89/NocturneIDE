# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing utility functions used by the security checks.
"""

import ast
import contextlib
import os

import AstUtilities


class InvalidModulePathError(Exception):
    """
    Class defining an exception for invalid module paths.
    """

    pass


def getModuleQualnameFromPath(path):
    """
    Function to get the module's qualified name by analysis of the
    path.

    Resolve the absolute pathname and eliminate symlinks. This could result
    in an incorrect name if symlinks are used to restructure the python lib
    directory.

    Starting from the right-most directory component look for __init__.py
    in the directory component. If it exists then the directory name is
    part of the module name. Move left to the subsequent directory
    components until a directory is found without __init__.py.

    @param path path of the module to be analyzed
    @type str
    @return qualified name of the module
    @rtype str
    @exception InvalidModulePathError raised to indicate an invalid module path
    """
    (head, tail) = os.path.split(path)
    if head == "" or tail == "":
        raise InvalidModulePathError(
            'Invalid python file path: "{0}" Missing path or file name'.format(path)
        )

    qname = [os.path.splitext(tail)[0]]
    while head not in ["/", ".", ""]:
        if os.path.isfile(os.path.join(head, "__init__.py")):
            (head, tail) = os.path.split(head)
            qname.insert(0, tail)
        else:
            break

    qualname = ".".join(qname)
    return qualname


def namespacePathJoin(namespace, name):
    """
    Function to extend a given namespace path.

    @param namespace namespace to be extended
    @type str
    @param name node name to be appended
    @type str
    @return extended namespace
    @rtype str
    """
    return "{0}.{1}".format(namespace, name)


def namespacePathSplit(path):
    """
    Function to split a namespace path into a head and tail.

    Tail will be the last namespace path component and head will
    be everything leading up to that in the path. This is similar to
    os.path.split.

    @param path namespace path to be split
    @type str
    @return tuple containing the namespace path head and tail
    @rtype tuple of (str, str)
    """
    return tuple(path.rsplit(".", 1))


def getAttrQualName(node, aliases):
    """
    Function to get a the full name for the attribute node.

    This will resolve a pseudo-qualified name for the attribute
    rooted at node as long as all the deeper nodes are Names or
    Attributes. This will give you how the code referenced the name but
    will not tell you what the name actually refers to. If we
    encounter a node without a static name we punt with an
    empty string. If this encounters something more complex, such as
    foo.mylist[0](a,b) we just return empty string.

    @param node attribute node to be treated
    @type ast.Attribute
    @param aliases dictionary of import aliases
    @type dict
    @return qualified name of the attribute
    @rtype str
    """
    if isinstance(node, ast.Name):
        if node.id in aliases:
            return aliases[node.id]
        return node.id
    elif isinstance(node, ast.Attribute):
        name = "{0}.{1}".format(getAttrQualName(node.value, aliases), node.attr)
        if name in aliases:
            return aliases[name]
        return name
    else:
        return ""


def getCallName(node, aliases):
    """
    Function to extract the call name from an ast.Call node.

    @param node node to extract information from
    @type ast.Call
    @param aliases dictionary of import aliases
    @type dict
    @return name of the ast.Call node
    @rtype str
    """
    if isinstance(node.func, ast.Name):
        if deepgetattr(node, "func.id") in aliases:
            return aliases[deepgetattr(node, "func.id")]
        return deepgetattr(node, "func.id")
    elif isinstance(node.func, ast.Attribute):
        return getAttrQualName(node.func, aliases)
    else:
        return ""


def getQualAttr(node, aliases):
    """
    Function to extract the qualified name from an ast.Attribute node.

    @param node node to extract information from
    @type ast.Attribute
    @param aliases dictionary of import aliases
    @type dict
    @return qualified attribute name
    @rtype str
    """
    prefix = ""
    if isinstance(node, ast.Attribute):
        with contextlib.suppress(AttributeError):
            val = deepgetattr(node, "value.id")
            prefix = aliases[val] if val in aliases else deepgetattr(node, "value.id")
            # Id we can't get the fully qualified name for an attr, just return
            # its base name.

        return "{0}.{1}".format(prefix, node.attr)
    else:
        return ""


def deepgetattr(obj, attr):
    """
    Function to recurs through an attribute chain to get the ultimate value.

    @param obj reference to the object to be recursed
    @type ast.Name or ast.Attribute
    @param attr attribute chain to be parsed
    @type ast.Attribute
    @return ultimate value
    @rtype ast.AST
    """
    for key in attr.split("."):
        obj = getattr(obj, key)
    return obj


def calcLineRange(node):
    """
    Function to calculate the line range for a subtree.

    @param node node to calculate the line range for
    @type ast.AST
    @return tuple containing the start and end line of the subtree
    @rtype tuple of (int, int)
    """
    if hasattr(node, "_securityLineRange"):
        return node._securityLineRange

    lines_min = 9999999999
    lines_max = -1
    if hasattr(node, "lineno"):
        lines_min = node.lineno
        lines_max = node.lineno
    for n in ast.iter_child_nodes(node):
        lines_minmax = calcLineRange(n)
        lines_min = min(lines_min, lines_minmax[0])
        lines_max = max(lines_max, lines_minmax[1])

    node._securityLineRange = (lines_min, lines_max)

    return (lines_min, lines_max)


def linerange(node):
    """
    Function to get line number range from a node.

    @param node node to extract a line range from
    @type ast.AST
    @return list containing the line number range
    @rtype list of int
    """
    if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
        return list(range(node.lineno, node.end_lineno + 1))
    else:
        if hasattr(node, "_securityLineRangeStripped"):
            lines_minmax = node._securityLineRangeStripped
            return list(range(lines_minmax[0], lines_minmax[1] + 1))

        strip = {
            "body": None,
            "orelse": None,
            "handlers": None,
            "finalbody": None,
        }
        for key in strip:
            if hasattr(node, key):
                strip[key] = getattr(node, key)
                setattr(node, key, [])

        lines_min = 9999999999
        lines_max = -1
        if hasattr(node, "lineno"):
            lines_min = node.lineno
            lines_max = node.lineno
        for n in ast.iter_child_nodes(node):
            lines_minmax = calcLineRange(n)
            lines_min = min(lines_min, lines_minmax[0])
            lines_max = max(lines_max, lines_minmax[1])

        for key in strip:
            if strip[key] is not None:
                setattr(node, key, strip[key])

        if lines_max == -1:
            lines_min = 0
            lines_max = 1

        node._securityLineRangeStripped = (lines_min, lines_max)

        lines = list(range(lines_min, lines_max + 1))
        # deal with multi-line strings lineno behavior (Python issue #16806)
        if hasattr(node, "_securitySibling") and hasattr(
            node._securitySibling, "lineno"
        ):
            start = min(lines)
            delta = node._securitySibling.lineno - start
            if delta > 1:
                return list(range(start, node._securitySibling.lineno))

        return lines


def escapedBytesRepresentation(b):
    """
    Function to escape bytes for comparison with other strings.

    In practice it turns control characters into acceptable codepoints then
    encodes them into bytes again to turn unprintable bytes into printable
    escape sequences.

    This is safe to do for the whole range 0..255 and result matches
    unicode_escape on a unicode string.

    @param b bytes object to be escaped
    @type bytes
    @return escaped bytes object
    @rtype bytes
    """
    return b.decode("unicode_escape").encode("unicode_escape")


def concatString(node, stop=None):
    """
    Function to build a string from an ast.BinOp chain.

    This will build a string from a series of ast.Constant nodes
    wrapped in ast.BinOp nodes. Something like "a" + "b" + "c" or "a %s" % val
    etc. The provided node can be any participant in the BinOp chain.

    @param node node to be processed
    @type ast.BinOp or ast.Constant
    @param stop base node to stop at
    @type ast.BinOp or ast.Constant
    @return tuple containing the root node of the expression and the string
        value
    @rtype tuple of (ast.AST, str)
    """

    def _get(node, bits, stop=None):
        if node != stop:
            bits.append(
                _get(node.left, bits, stop)
                if isinstance(node.left, ast.BinOp)
                else node.left
            )
            bits.append(
                _get(node.right, bits, stop)
                if isinstance(node.right, ast.BinOp)
                else node.right
            )

    bits = [node]
    while isinstance(node._securityParent, ast.BinOp):
        node = node._securityParent
    if isinstance(node, ast.BinOp):
        _get(node, bits, stop)

    return (node, " ".join([x.value for x in bits if AstUtilities.isString(x)]))


def getCalledName(node):
    """
    Function to get the function name from an ast.Call node.

    An ast.Call node representing a method call will present differently to one
    wrapping a function call: thing.call() vs call(). This helper will grab the
    unqualified call name correctly in either case.

    @param node reference to the call node
    @type ast.Call
    @return function name of the node
    @rtype str
    """
    func = node.func
    try:
        return func.attr if isinstance(func, ast.Attribute) else func.id
    except AttributeError:
        return ""


#
# eflag: noqa = M601
