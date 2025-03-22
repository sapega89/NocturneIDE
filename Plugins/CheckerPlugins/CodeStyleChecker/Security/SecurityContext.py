# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a context class for security related checks.
"""

#
# This code is a modified version of the one in 'bandit'.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#

import ast
import copy

import AstUtilities

from . import SecurityUtils


class SecurityContext:
    """
    Class implementing a context class for security related checks.
    """

    def __init__(self, contextObject=None):
        """
        Constructor

        Initialize the class with a context dictionary or an empty
        dictionary.

        @param contextObject context dictionary to be used to populate the
            class
        @type dict
        """
        if contextObject is not None:
            self.__context = copy.copy(contextObject)
        else:
            self.__context = {}

    def __repr__(self):
        """
        Special method to generate representation of object for printing or
        interactive use.

        @return string representation of the object
        @rtype str
        """
        return "<SecurityContext {0}>".format(self.__context)

    @property
    def callArgs(self):
        """
        Public method to get a list of function args.

        @return list of function args
        @rtype list
        """
        args = []
        if "call" in self.__context and hasattr(self.__context["call"], "args"):
            for arg in self.__context["call"].args:
                if hasattr(arg, "attr"):
                    args.append(arg.attr)
                else:
                    args.append(self.__getLiteralValue(arg))
        return args

    @property
    def callArgsCount(self):
        """
        Public method to get the number of args a function call has.

        @return number of args a function call has
        @rtype int
        """
        if "call" in self.__context and hasattr(self.__context["call"], "args"):
            return len(self.__context["call"].args)
        else:
            return None

    @property
    def callFunctionName(self):
        """
        Public method to get the name (not FQ) of a function call.

        @return name (not FQ) of a function call
        @rtype str
        """
        return self.__context.get("name")

    @property
    def callFunctionNameQual(self):
        """
        Public method to get the FQ name of a function call.

        @return FQ name of a function call
        @rtype str
        """
        return self.__context.get("qualname")

    @property
    def callKeywords(self):
        """
        Public method to get a dictionary of keyword parameters.

        @return dictionary of keyword parameters
        @rtype dict
        """
        if "call" in self.__context and hasattr(self.__context["call"], "keywords"):
            returnDict = {}
            for kw in self.__context["call"].keywords:
                if hasattr(kw.value, "attr"):
                    returnDict[kw.arg] = kw.value.attr
                else:
                    returnDict[kw.arg] = self.__getLiteralValue(kw.value)
            return returnDict

        else:
            return None

    @property
    def node(self):
        """
        Public method to get the raw AST node associated with the context.

        @return raw AST node associated with the context
        @rtype ast.AST
        """
        return self.__context.get("node")

    @property
    def stringVal(self):
        """
        Public method to get the value of a standalone string object.

        @return value of a standalone string object
        @rtype str
        """
        return self.__context.get("str")

    @property
    def bytesVal(self):
        """
        Public method to get the value of a standalone bytes object.

        @return value of a standalone bytes object
        @rtype bytes
        """
        return self.__context.get("bytes")

    @property
    def stringValAsEscapedBytes(self):
        r"""
        Public method to get the escaped value of the object.

        Turn the value of a string or bytes object into a byte sequence with
        unknown, control, and \\ characters escaped.

        This function should be used when looking for a known sequence in a
        potentially badly encoded string in the code.

        @return sequence of printable ascii bytes representing original string
        @rtype str
        """
        val = self.stringVal
        if val is not None:
            return val.encode("unicode_escape")

        val = self.bytesVal
        if val is not None:
            return SecurityUtils.escapedBytesRepresentation(val)

        return None

    @property
    def statement(self):
        """
        Public method to get the raw AST for the current statement.

        @return raw AST for the current statement
        @rtype ast.AST
        """
        return self.__context.get("statement")

    @property
    def functionDefDefaultsQual(self):
        """
        Public method to get a list of fully qualified default values in a
        function def.

        @return list of fully qualified default values in a function def
        @rtype list
        """
        defaults = []
        if (
            "node" in self.__context
            and hasattr(self.__context["node"], "args")
            and hasattr(self.__context["node"].args, "defaults")
        ):
            for default in self.__context["node"].args.defaults:
                defaults.append(
                    SecurityUtils.getQualAttr(default, self.__context["import_aliases"])
                )

        return defaults

    def __getLiteralValue(self, literal):
        """
        Private method to turn AST literals into native Python types.

        @param literal AST literal to be converted
        @type ast.AST
        @return converted Python object
        @rtype Any
        """
        if (
            AstUtilities.isNumber(literal)
            or AstUtilities.isString(literal)
            or AstUtilities.isBytes(literal)
        ):
            literalValue = literal.value

        elif isinstance(literal, ast.List):
            returnList = []
            for li in literal.elts:
                returnList.append(self.__getLiteralValue(li))
            literalValue = returnList

        elif isinstance(literal, ast.Tuple):
            returnTuple = ()
            for ti in literal.elts:
                returnTuple += (self.__getLiteralValue(ti),)
            literalValue = returnTuple

        elif isinstance(literal, ast.Set):
            returnSet = set()
            for si in literal.elts:
                returnSet.add(self.__getLiteralValue(si))
            literalValue = returnSet

        elif isinstance(literal, ast.Dict):
            literalValue = dict(zip(literal.keys, literal.values))

        elif AstUtilities.isEllipsis(literal):
            # what do we want to do with this?
            literalValue = None

        elif isinstance(literal, ast.Name):
            literalValue = literal.id

        elif AstUtilities.isNameConstant(literal):
            literalValue = str(literal.value)

        else:
            literalValue = None

        return literalValue

    def getCallArgValue(self, argumentName):
        """
        Public method to get the value of a named argument in a function call.

        @param argumentName name of the argument to get the value for
        @type str
        @return value of the named argument
        @rtype Any
        """
        kwdValues = self.callKeywords
        if kwdValues is not None and argumentName in kwdValues:
            return kwdValues[argumentName]

        return None

    def checkCallArgValue(self, argumentName, argumentValues=None):
        """
        Public method to check for a value of a named argument in a function
        call.

        @param argumentName name of the argument to be checked
        @type str
        @param argumentValues value or list of values to test against
        @type Any or list of Any
        @return True if argument found and matched, False if found and not
            matched, None if argument not found at all
        @rtype bool or None
        """
        argValue = self.getCallArgValue(argumentName)
        if argValue is not None:
            if not isinstance(argumentValues, list):
                # if passed a single value, or a tuple, convert to a list
                argumentValues = [argumentValues]
            return any(argValue == val for val in argumentValues)
        else:
            # argument name not found, return None to allow testing for this
            # eventuality
            return None

    def getLinenoForCallArg(self, argumentName):
        """
        Public method to get the line number for a specific named argument.

        @param argumentName name of the argument to get the line number for
        @type str
        @return line number of the found argument or -1
        @rtype int
        """
        if hasattr(self.node, "keywords"):
            for key in self.node.keywords:
                if key.arg == argumentName:
                    return key.value.lineno

        return -1

    def getOffsetForCallArg(self, argumentName):
        """
        Public method to get the offset for a specific named argument.

        @param argumentName name of the argument to get the column offset for
        @type str
        @return offset of the found argument or -1
        @rtype int
        """
        if hasattr(self.node, "keywords"):
            for key in self.node.keywords:
                if key.arg == argumentName:
                    return key.value.col_offset

        return -1

    def getCallArgAtPosition(self, positionNum):
        """
        Public method to get a positional argument at the specified position
        (if it exists).

        @param positionNum index of the argument to get the value for
        @type int
        @return value of the argument at the specified position if it exists
        @rtype Any or None
        """
        maxArgs = self.callArgsCount
        if maxArgs and positionNum < maxArgs:
            arg = self.__context["call"].args[positionNum]
            return getattr(arg, "attr", None) or self.__getLiteralValue(arg)
        else:
            return None

    def isModuleBeingImported(self, module):
        """
        Public method to check for the given module is currently being
        imported.

        @param module module name to look for
        @type str
        @return flag indicating the given module was found
        @rtype bool
        """
        return self.__context.get("module") == module

    def isModuleImportedExact(self, module):
        """
        Public method to check if a given module has been imported; only exact
        matches.

        @param module module name to look for
        @type str
        @return flag indicating the given module was found
        @rtype bool
        """
        return module in self.__context.get("imports", [])

    def isModuleImportedLike(self, module):
        """
        Public method to check if a given module has been imported; given
        module exists.

        @param module module name to look for
        @type str
        @return flag indicating the given module was found
        @rtype bool
        """
        try:
            return any(module in imp for imp in self.__context["imports"])
        except KeyError:
            return False

    @property
    def filename(self):
        """
        Public method to get the file name.

        @return file name
        @rtype str
        """
        return self.__context.get("filename")

    @property
    def fileData(self):
        """
        Public method to get the file contents.

        @return file contents
        @rtype str
        """
        return self.__context.get("filedata")
