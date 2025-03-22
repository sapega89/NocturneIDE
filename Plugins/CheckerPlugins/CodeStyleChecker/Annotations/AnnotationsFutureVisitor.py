# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a node visitor for function type annotations.
"""

#
# The visitor and associated classes are adapted from flake8-future-annotations v1.1.0
#

import ast


class AnnotationsFutureVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor to check __future__ imports.
    """

    SimplifyableTypes = (
        "DefaultDict",
        "Deque",
        "Dict",
        "FrozenSet",
        "List",
        "Optional",
        "Set",
        "Tuple",
        "Union",
        "Type",
    )
    SimplifiedTypes = (
        "defaultdict",
        "deque",
        "dict",
        "frozenset",
        "list",
        "set",
        "tuple",
        "type",
    )

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__typingAliases = []
        self.__importsFutureAnnotations = False

        # e.g. from typing import List, typing.List, t.List
        self.__typingImports = []
        self.__simplifiedTypes = set()

    def visit_Import(self, node):
        """
        Public method to check imports for typing related stuff.

        This looks like:
        import typing
        or
        import typing as t

        typing or t will be added to the list of typing aliases.

        @param node reference to the AST Import node
        @type ast.Import
        """
        for alias in node.names:
            if alias.name == "typing":
                self.__typingAliases.append("typing")
            if alias.asname is not None:
                self.__typingAliases.append(alias.asname)

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """
        Public method to detect the 'from __future__ import annotations'
        import if present.

        If 'from typing import ...' is used, add simplifiable names that were
        imported.

        @param node reference to the AST ImportFrom node
        @type ast.ImportFrom
        """
        if node.module == "__future__":
            for alias in node.names:
                if alias.name == "annotations":
                    self.__importsFutureAnnotations = True

        if node.module == "typing":
            for alias in node.names:
                if alias.name in AnnotationsFutureVisitor.SimplifyableTypes:
                    self.__typingImports.append(alias.name)

        self.generic_visit(node)

    def visit_Attribute(self, node):
        """
        Public method to record simplifiable names.

        If 'import typing' or 'import typing as t' is used, add simplifiable
        names that were used later on in the code.

        @param node reference to the AST Attribute node
        @type ast.Attribute
        """
        if (
            node.attr in AnnotationsFutureVisitor.SimplifyableTypes
            and isinstance(node.value, ast.Name)
            and node.value.id in self.__typingAliases
        ):
            self.__typingImports.append(f"{node.value.id}.{node.attr}")

        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        """
        Public method to check type annotations.

        @param node reference to the AST Assign node
        @type ast.AnnAssign
        """
        if not self.__importsFutureAnnotations and node.annotation is not None:
            self.__processAnnotation(node.annotation)

        self.generic_visit(node)

    def visit_arg(self, node: ast.arg):
        """
        Public method to check argument annotations.

        @param node reference to the AST argument node
        @type ast.arg
        """
        if not self.__importsFutureAnnotations and node.annotation is not None:
            self.__processAnnotation(node.annotation)

        self.generic_visit(node)

    def __processAnnotation(self, node):
        """
        Private method to process the given annotations.

        @param node reference to the AST node containing the annotations
        @type ast.expr
        """
        if (
            isinstance(node, ast.Name)
            and node.id in AnnotationsFutureVisitor.SimplifiedTypes
        ):
            self.__simplifiedTypes.add(node.id)
        elif isinstance(node, ast.Subscript):
            self.__processAnnotation(node.value)
            self.__processAnnotation(node.slice)
        elif isinstance(node, ast.Tuple):
            for subNode in node.elts:
                self.__processAnnotation(subNode)
        elif isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.BitOr):
                self.__simplifiedTypes.add("union")
            self.__processAnnotation(node.left)
            self.__processAnnotation(node.right)
        elif isinstance(node, ast.Index):
            # Index is only used in Python 3.7 and 3.8, deprecated after.
            self.__processAnnotation(node.value)

    def importsFutureAnnotations(self):
        """
        Public method to check, if the analyzed code uses future annotation.

        @return flag indicatung the use of future annotation
        @rtype bool
        """
        return self.__importsFutureAnnotations

    def hasTypingImports(self):
        """
        Public method to check, if the analyzed code includes typing imports.

        @return flag indicating the use of typing imports
        @rtype bool
        """
        return bool(self.__typingImports)

    def getTypingImports(self):
        """
        Public method to get the list of typing imports.

        @return list of typing imports
        @rtype list of str
        """
        return self.__typingImports[:]

    def hasSimplifiedTypes(self):
        """
        Public method to check, if the analyzed code includes annotations with
        simplified types.

        @return flag indicating the presence of simplified types
        @rtype bool
        """
        return bool(self.__simplifiedTypes)

    def getSimplifiedTypes(self):
        """
        Public method Public method to get the list of detected simplified types.

        @return list of simplified types
        @rtype list of str
        """
        return list(self.__simplifiedTypes)
