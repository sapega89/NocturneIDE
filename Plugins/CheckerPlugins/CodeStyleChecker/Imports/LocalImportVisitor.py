# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a node visitor for checking local import statements.
"""

import ast

#
# The visitor is adapted from flake8-local-import v1.0.6
#


class LocalImportVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor for checking local import statements.
    """

    def __init__(self, args, checker):
        """
        Constructor

        @param args dictionary containing the checker arguments
        @type dict
        @param checker reference to the checker
        @type ImportsChecker
        """
        self.__appImportNames = args.get("ApplicationPackageNames", [])
        self.__checker = checker

        self.violations = []

    def visit(self, node):
        """
        Public method to traverse the tree of an AST node.

        @param node AST node to parse
        @type ast.AST
        """
        previous = None
        isLocal = isinstance(node, ast.FunctionDef) or getattr(node, "is_local", False)
        for child in ast.iter_child_nodes(node):
            child.parent = node
            child.previous = previous
            child.is_local = isLocal
            previous = child

        super().visit(node)

    def visit_FunctionDef(self, node):
        """
        Public method to handle a function definition.

        @param node reference to the node to be processed
        @type ast.FunctionDef
        """
        children = list(ast.iter_child_nodes(node))
        if len(children) > 1:
            firstStatement = children[1]

            if isinstance(firstStatement, ast.Expr):
                value = getattr(firstStatement, "value", None)
                if isinstance(value, ast.Constant):
                    firstStatement.is_doc_str = True

        self.generic_visit(node)

    def visit_Import(self, node):
        """
        Public method to handle an import statement.

        @param node reference to the node to be processed
        @type ast.Import
        """
        if not getattr(node, "is_local", False):
            self.generic_visit(node)
            return

        for name in node.names:
            self.__assertExternalModule(node, name.name or "")

        self.__visitImportNode(node)

    def visit_ImportFrom(self, node):
        """
        Public method to handle an import from statement.

        @param node reference to the node to be processed
        @type ast.ImportFrom
        """
        if not getattr(node, "is_local", False):
            self.generic_visit(node)
            return

        self.__assertExternalModule(node, node.module or "")

        self.__visitImportNode(node)

    def __visitImportNode(self, node):
        """
        Private method to handle an import or import from statement.

        @param node reference to the node to be processed
        @type ast.Import or ast.ImportFrom
        """
        parent = getattr(node, "parent", None)
        if isinstance(parent, ast.Module):
            self.generic_visit(node)
            return

        previous = getattr(node, "previous", None)

        isAllowedPrevious = (
            isinstance(previous, ast.Expr) and getattr(previous, "is_doc_str", False)
        ) or isinstance(previous, (ast.Import, ast.ImportFrom, ast.arguments))

        if not isinstance(parent, ast.FunctionDef) or not isAllowedPrevious:
            self.violations.append((node, "I101"))

        self.generic_visit(node)

    def __assertExternalModule(self, node, module):
        """
        Private method to assert the given node.

        @param node reference to the node to be processed
        @type ast.stmt
        @param module name of the module
        @type str
        """
        from eric7.SystemUtilities import SysUtilities

        parent = getattr(node, "parent", None)
        if isinstance(parent, ast.Module):
            return

        modulePrefix = module + "."

        if getattr(node, "level", 0) != 0 or any(
            modulePrefix.startswith(appModule + ".")
            for appModule in self.__appImportNames
        ):
            return

        if module.split(".")[0] not in SysUtilities.getStandardModules():
            self.violations.append((node, "I102"))
        else:
            self.violations.append((node, "I103"))
