# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a node visitor to check async functions for use of synchronous
functions.
"""

import ast
import itertools
import re

try:
    from ast import unparse
except ImportError:
    # Python < 3.9
    from ast_unparse import unparse

#######################################################################
## AsyncVisitor
##
## adapted from: flake8-async v22.11.14
#######################################################################


class AsyncVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor for checking async functions for use of
    synchronous functions.
    """

    HttpPackages = (
        "requests",
        "httpx",
    )

    HttpMethods = (
        "close",
        "delete",
        "get",
        "head",
        "options",
        "patch",
        "post",
        "put",
        "request",
        "send",
        "stream",
    )

    Urllib3DangerousClasses = (
        "HTTPConnectionPool",
        "HTTPSConnectionPool",
        "PoolManager",
        "ProxyManager",
        "connectionpool.ConnectionPool",
        "connectionpool.HTTPConnectionPool",
        "connectionpool.HTTPSConnectionPool",
        "poolmanager.PoolManager",
        "poolmanager.ProxyManager",
        "request.RequestMethods",
    )

    SubprocessMethods = (
        "run",
        "Popen",
        # deprecated methods
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
    )

    OsProcessMethods = (
        "popen",
        "posix_spawn",
        "posix_spawnp",
        "spawnl",
        "spawnle",
        "spawnlp",
        "spawnlpe",
        "spawnv",
        "spawnve",
        "spawnvp",
        "spawnvpe",
        "system",
    )

    OsWaitMethods = (
        "wait",
        "wait3",
        "wait4",
        "waitid",
        "waitpid",
    )

    OsPathFuncs = (
        "_path_normpath",
        "normpath",
        "_joinrealpath",
        "islink",
        "lexists",
        "ismount",  # safe on windows, unsafe on posix
        "realpath",
        "exists",
        "isdir",
        "isfile",
        "getatime",
        "getctime",
        "getmtime",
        "getsize",
        "samefile",
        "sameopenfile",
        "relpath",
    )

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

    def visit_AsyncFunctionDef(self, node):
        """
        Public method to handle an async function definition.

        @param node reference to the node to be processed
        @type ast.AsyncFunctionDef
        """
        for inner in itertools.chain.from_iterable(
            map(ast.iter_child_nodes, node.body)
        ):
            errorCode = None
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "open"
            ):
                errorCode = "ASY101"

            elif (
                isinstance(inner, ast.withitem)
                and isinstance(inner.context_expr, ast.Call)
                and isinstance(inner.context_expr.func, ast.Name)
                and inner.context_expr.func.id == "open"
            ):
                errorCode = "ASY103"
                inner = inner.context_expr

            elif isinstance(inner, ast.Call):
                funcName = unparse(inner.func)

                if funcName in (
                    "urllib3.request",
                    "urllib.request.urlopen",
                    "request.urlopen",
                    "urlopen",
                ):
                    errorCode = "ASY100"
                elif funcName == "time.sleep":
                    errorCode = "ASY101"
                else:
                    match = re.fullmatch(
                        r"(?P<package>{0}|os\.path|os|subprocess|urllib3)\."
                        r"(?P<method>.*)".format("|".join(self.HttpPackages)),
                        funcName,
                    )
                    if match:
                        if (
                            match.group("package") in self.HttpPackages
                            and match.group("method") in self.HttpMethods
                        ):
                            errorCode = "ASY100"

                        elif (
                            match.group("package") == "subprocess"
                            and match.group("method") in self.SubprocessMethods
                        ) or (
                            match.group("package") == "os"
                            and match.group("method") in self.OsWaitMethods
                        ):
                            errorCode = "ASY101"

                        elif (
                            match.group("package") == "os"
                            and match.group("method") in self.OsProcessMethods
                        ):
                            errorCode = "ASY102"

                        elif (
                            match.group("package") == "os.path"
                            and match.group("method") in self.OsPathFuncs
                        ):
                            errorCode = "ASY104"

                        elif (
                            match.group("package") == "httpx"
                            and match.group("method") == "Client"
                        ) or (
                            match.group("package") == "urllib3"
                            and match.group("method") in self.Urllib3DangerousClasses
                        ):
                            errorCode = "ASY105"

            if errorCode:
                self.violations.append((inner, errorCode))

        self.generic_visit(node)
