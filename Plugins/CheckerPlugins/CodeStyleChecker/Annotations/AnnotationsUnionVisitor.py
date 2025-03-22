# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a node visitor for checking the import of typing.Union.
"""

#
# The visitor is adapted from flake8-pep604 v1.1.0
#

import ast


class AnnotationsUnionVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor for checking the import of typing.Union.
    """

    ModuleName = "typing"
    AttributeName = "Union"
    FullName = "typing.Union"

    def __init__(self):
        """
        Constructor
        """
        self.__unionImports = []
        self.__aliasedUnionImports = set()

    def visit_Import(self, node):
        """
        Public method to handle an ast.Import node.

        @param node reference to the node to be handled
        @type ast.Import
        """
        for name in node.names:
            if name.name == self.FullName:
                self.__unionImports.append(node)
            elif name.name == self.ModuleName and name.asname:
                self.__aliasedUnionImports.add(name.asname)

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """
        Public method to handle an ast.ImportFrom node.

        @param node reference to the node to be handled
        @type ast.ImportFrom
        """
        if node.module == self.ModuleName:
            for name in node.names:
                if name.name == self.AttributeName:
                    self.__unionImports.append(node)
                    if name.asname:
                        self.__aliasedUnionImports.add(name.asname)

        self.generic_visit(node)

    def visit_Attribute(self, node):
        """
        Public method to handle an ast.Attribute node.

        @param node reference to the node to be handled
        @type ast.Attribute
        """
        if (
            isinstance(node.value, ast.Name)
            and (
                node.value.id in self.__aliasedUnionImports
                or node.value.id == self.ModuleName
            )
            and node.attr == self.AttributeName
        ):
            self.__unionImports.append(node)

        self.generic_visit(node)

    def visit_Subscript(self, node):
        """
        Public method to handle an ast.Subscript node.

        @param node reference to the node to be handled
        @type ast.Subscript
        """
        if isinstance(node.value, ast.Name) and (
            node.value.id in self.__aliasedUnionImports
            or node.value.id == self.AttributeName
        ):
            self.__unionImports.append(node)

        self.generic_visit(node)

    def getIssues(self):
        """
        Public method to get the collected Union nodes.

        @return list of collected nodes
        @rtype list of ast.AST
        """
        return self.__unionImports
