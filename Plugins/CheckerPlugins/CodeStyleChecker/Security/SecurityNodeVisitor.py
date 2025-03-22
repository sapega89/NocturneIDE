# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an AST node visitor for security checks.
"""

import ast

from . import SecurityUtils
from .SecurityContext import SecurityContext


class SecurityNodeVisitor:
    """
    Class implementing an AST node visitor for security checks.
    """

    def __init__(self, checker, secCheckers, filename, fileData):
        """
        Constructor

        @param checker reference to the main security checker object
        @type SecurityChecker
        @param secCheckers dictionary containing the available checker routines
        @type dict
        @param filename name of the checked file
        @type str
        @param fileData contents of the checked file
        @type str
        """
        self.__checker = checker
        self.__securityCheckers = secCheckers

        self.depth = 0
        self.filename = filename
        self.fileData = fileData
        self.imports = set()
        self.import_aliases = {}

        # in some cases we can't determine a qualified name
        try:
            self.namespace = SecurityUtils.getModuleQualnameFromPath(filename)
        except SecurityUtils.InvalidModulePathError:
            self.namespace = ""

    def __runChecks(self, checkType):
        """
        Private method to run all enabled checks for a given check type.

        @param checkType type of checks to be run
        @type str
        """
        if checkType in self.__securityCheckers:
            for check in self.__securityCheckers[checkType]:
                check(
                    self.__checker.reportError,
                    SecurityContext(self.__context),
                    self.__checker.getConfig(),
                )

    def visit_ClassDef(self, node):
        """
        Public method defining a visitor for AST ClassDef nodes.

        Add class name to current namespace for all descendants.

        @param node reference to the node being inspected
        @type ast.ClassDef
        """
        # For all child nodes, add this class name to current namespace
        self.namespace = SecurityUtils.namespacePathJoin(self.namespace, node.name)

    def visit_FunctionDef(self, node):
        """
        Public method defining a visitor for AST FunctionDef nodes.

        @param node reference to the node being inspected
        @type ast.FunctionDef
        """
        self.__visitFunctionDefinition(node)

    def visit_AsyncFunctionDef(self, node):
        """
        Public method defining a visitor for AST AsyncFunctionDef nodes.

        @param node reference to the node being inspected
        @type ast.AsyncFunctionDef
        """
        self.__visitFunctionDefinition(node)

    def __visitFunctionDefinition(self, node):
        """
        Private method defining a visitor for AST FunctionDef and
        AsyncFunctionDef nodes.

        Add relevant information about the node to the context for use in tests
        which inspect function definitions. Add the function name to the
        current namespace for all descendants.

        @param node reference to the node being inspected
        @type ast.FunctionDef, ast.AsyncFunctionDef
        """
        self.__context["function"] = node
        qualname = SecurityUtils.namespacePathJoin(self.namespace, node.name)
        name = qualname.split(".")[-1]
        self.__context["qualname"] = qualname
        self.__context["name"] = name

        # For all child nodes and any tests run, add this function name to
        # current namespace
        self.namespace = SecurityUtils.namespacePathJoin(self.namespace, node.name)

        self.__runChecks("FunctionDef")

    def visit_Call(self, node):
        """
        Public method defining a visitor for AST Call nodes.

        Add relevant information about the node to the context for use in tests
        which inspect function calls.

        @param node reference to the node being inspected
        @type ast.Call
        """
        self.__context["call"] = node
        qualname = SecurityUtils.getCallName(node, self.import_aliases)
        name = qualname.split(".")[-1]
        self.__context["qualname"] = qualname
        self.__context["name"] = name
        self.__runChecks("Call")

    def visit_Import(self, node):
        """
        Public method defining a visitor for AST Import nodes.

        @param node reference to the node being inspected
        @type ast.Import
        """
        for nodename in node.names:
            if nodename.asname:
                self.import_aliases[nodename.asname] = nodename.name
            self.imports.add(nodename.name)
            self.__context["module"] = nodename.name
        self.__runChecks("Import")

    def visit_ImportFrom(self, node):
        """
        Public method defining a visitor for AST Import nodes.

        This adds relevant information about the node to
        the context for use in tests which inspect imports.

        @param node reference to the node being inspected
        @type ast.ImportFrom
        """
        module = node.module
        if module is None:
            self.visit_Import(node)
            return

        for nodename in node.names:
            if nodename.asname:
                self.import_aliases[nodename.asname] = module + "." + nodename.name
            else:
                # Even if import is not aliased we need an entry that maps
                # name to module.name.  For example, with 'from a import b'
                # b should be aliased to the qualified name a.b
                self.import_aliases[nodename.name] = module + "." + nodename.name
            self.imports.add(module + "." + nodename.name)
            self.__context["module"] = module
            self.__context["name"] = nodename.name
        self.__runChecks("ImportFrom")

    def visit_Constant(self, node):
        """
        Public method defining a visitor for Constant nodes.

        This calls the appropriate method for the node type.
        It maintains compatibility with <3.6 and 3.8+

        @param node reference to the node being inspected
        @type ast.Constant
        """
        if isinstance(node.value, str):
            self.__context["str"] = node.value
            if not isinstance(node._securityParent, ast.Expr):  # docstring
                self.__context["linerange"] = SecurityUtils.linerange(
                    node._securityParent
                )
                self.__runChecks("Str")
        elif isinstance(node.value, bytes):
            self.__context["bytes"] = node.value
            if not isinstance(node._securityParent, ast.Expr):  # docstring
                self.__context["linerange"] = SecurityUtils.linerange(
                    node._securityParent
                )
                self.__runChecks("Bytes")

    def __preVisit(self, node):
        """
        Private method to set up a context for the visit method.

        @param node node to base the context on
        @type ast.AST
        @return flag indicating to visit the node
        @rtype bool
        """
        self.__context = {}
        self.__context["imports"] = self.imports
        self.__context["import_aliases"] = self.import_aliases

        if hasattr(node, "lineno"):
            self.__context["lineno"] = node.lineno

        if hasattr(node, "col_offset"):
            self.__context["col_offset"] = node.col_offset
        if hasattr(node, "end_col_offset"):
            self.__context["end_col_offset"] = node.end_col_offset

        self.__context["node"] = node
        self.__context["linerange"] = SecurityUtils.linerange(node)
        self.__context["filename"] = self.filename
        self.__context["filedata"] = self.fileData

        self.depth += 1

        return True

    def visit(self, node):
        """
        Public method to inspected an AST node.

        @param node AST node to be inspected
        @type ast.AST
        """
        name = node.__class__.__name__
        method = "visit_" + name
        visitor = getattr(self, method, None)
        if visitor is not None:
            visitor(node)
        else:
            self.__runChecks(name)

    def __postVisit(self, node):
        """
        Private method to clean up after a node was visited.

        @param node AST node that was visited
        @type ast.AST
        """
        self.depth -= 1
        # Clean up post-recursion stuff that gets setup in the visit methods
        # for these node types.
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            self.namespace = SecurityUtils.namespacePathSplit(self.namespace)[0]

    def generic_visit(self, node):
        """
        Public method to drive the node visitor.

        @param node node to be inspected
        @type ast.AST
        """
        for _, value in ast.iter_fields(node):
            if isinstance(value, list):
                maxIndex = len(value) - 1
                for index, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        if index < maxIndex:
                            item._securitySibling = value[index + 1]
                        else:
                            item._securitySibling = None
                        item._securityParent = node

                        if self.__preVisit(item):
                            self.visit(item)
                            self.generic_visit(item)
                            self.__postVisit(item)

            elif isinstance(value, ast.AST):
                value._securitySibling = None
                value._securityParent = node
                if self.__preVisit(value):
                    self.visit(value)
                    self.generic_visit(value)
                    self.__postVisit(value)

    def checkFile(self):
        """
        Public method to run File type checks, that don't operate on the AST.
        """
        self.__runChecks("File")
