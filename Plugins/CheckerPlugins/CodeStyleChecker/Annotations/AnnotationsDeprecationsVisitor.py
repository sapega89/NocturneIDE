# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a node visitor for checking the use of deprecated 'typing' symbols.
"""

#
# The visitors are adapted and extended variants of the ones found in
# flake8-pep585 v0.1.7
#

import ast


class AnnotationsDeprecationsVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor for checking the use of deprecated 'typing'
    symbols.
    """

    NameReplacements = {
        "Tuple": "tuple",
        "List": "list",
        "Dict": "dict",
        "Set": "set",
        "FrozenSet": "frozenset",
        "Type": "type",
        "Deque": "collections.deque",
        "DefaultDict": "collections.defaultdict",
        "OrderedDict": "collections.OrderedDict",
        "Counter": "collections.Counter",
        "ChainMap": "collections.ChainMap",
        "Awaitable": "collections.abc.Awaitable",
        "Coroutine": "collections.abc.Coroutine",
        "AsyncIterable": "collections.abc.AsyncIterable",
        "AsyncIterator": "collections.abc.AsyncIterator",
        "AsyncGenerator": "collections.abc.AsyncGenerator",
        "Iterable": "collections.abc.Iterable",
        "Iterator": "collections.abc.Iterator",
        "Generator": "collections.abc.Generator",
        "Reversible": "collections.abc.Reversible",
        "Container": "collections.abc.Container",
        "Collection": "collections.abc.Collection",
        "Callable": "collections.abc.Callable",
        "AbstractSet": "collections.abc.Set",
        "MutableSet": "collections.abc.MutableSet",
        "Mapping": "collections.abc.Mapping",
        "MutableMapping": "collections.abc.MutableMapping",
        "Sequence": "collections.abc.Sequence",
        "MutableSequence": "collections.abc.MutableSequence",
        "ByteString": "collections.abc.ByteString",
        "MappingView": "collections.abc.MappingView",
        "KeysView": "collections.abc.KeysView",
        "ItemsView": "collections.abc.ItemsView",
        "ValuesView": "collections.abc.ValuesView",
        "ContextManager": "contextlib.AbstractContextManager",
        "AsyncContextManager": "contextlib.AbstractAsyncContextManager",
        "Pattern": "re.Pattern",
        "Match": "re.Match",
    }

    def __init__(self, exemptedList):
        """
        Constructor

        @param exemptedList list of typing symbols exempted from checking
        @type list of str
        """
        self.__exemptedList = exemptedList[:]
        self.__typingAliases = set()

        self.__issues = []

    def getIssues(self):
        """
        Public method to get the list of detected issues.

        @return list of detected issues consisting of a tuple of a reference to the node
            and a tuple containing the used name and the suggested replacement
        @rtype list of tuples of (ast.AST, (str, str))
        """
        return self.__issues

    def __checkDeprecation(self, node, name):
        """
        Private method to check, if the given name is deprecated.

        @param node reference to the node
        @type ast.ImportFrom, ast.Attribute
        @param name name to be checked
        @type str
        """
        if name not in self.__exemptedList:
            replacement = self.NameReplacements.get(name)
            if replacement is not None:
                self.__issues.append((node, (name, replacement)))

    def visit_ImportFrom(self, node):
        """
        Public method to handle an ast.ImportFrom node.

        @param node reference to the node to be handled
        @type ast.ImportFrom
        """
        if node.module == "typing":
            for alias in node.names:
                self.__checkDeprecation(node, alias.name)

    def visit_Import(self, node):
        """
        Public method to handle an ast.Import node.

        @param node reference to the node to be handled
        @type ast.Import
        """
        for alias in node.names:
            if alias.name == "typing":
                self.__typingAliases.add(alias.asname or "typing")

    def visit_Attribute(self, node):
        """
        Public method to handle an ast.Attribute node.

        @param node reference to the node to be handled
        @type ast.Attribute
        """
        if (
            isinstance(node.value, ast.Name)
            and node.value.id in self.__typingAliases
            and node.attr not in self.__exemptedList
        ):
            self.__checkDeprecation(node, node.attr)

    def visit_AnnAssign(self, node):
        """
        Public method to handle an ast.AnnAssign node.

        @param node reference to the node to be handled
        @type ast.AnnAssign
        """
        if isinstance(node.annotation, ast.Name):
            self.__checkDeprecation(node, node.annotation.id)
        elif isinstance(node.annotation, ast.Subscript) and isinstance(
            node.annotation.value, ast.Name
        ):
            self.__checkDeprecation(node, node.annotation.value.id)

    def visit_FunctionDef(self, node):
        """
        Public method to handle an ast.FunctionDef or ast.AsyncFunctionDef node.

        @param node reference to the node to be handled
        @type ast.FunctionDef or ast.AsyncFunctionDef
        """
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if isinstance(arg.annotation, ast.Name):
                self.__checkDeprecation(arg, arg.annotation.id)
            elif isinstance(arg.annotation, ast.Subscript) and isinstance(
                arg.annotation.value, ast.Name
            ):
                self.__checkDeprecation(arg, arg.annotation.value.id)

    visit_AsyncFunctionDef = visit_FunctionDef


class AnnotationsFutureImportVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor to dtermine, if the annotations __future__
    import is present.

    This class is used to determine usage of annotations for Python 3.8.
    """

    def __init__(self):
        """
        Constructor
        """
        self.__futureImport = False

    def futureImportPresent(self):
        """
        Public method to check, if a 'from __future__ import annotations' statement
        exists.

        @return flag indicating the existence of the import statement
        @rtype bool
        """
        return self.__futureImport

    def visit_ImportFrom(self, node):
        """
        Public method to handle an ast.ImportFrom node.

        @param node reference to the node to be handled
        @type ast.ImportFrom
        """
        if node.module == "__future__" and "annotations" in {
            alias.name for alias in node.names
        }:
            self.__futureImport = True
