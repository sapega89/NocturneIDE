# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a node visitor to check for logging issues.
"""

#######################################################################
## LoggingVisitor
##
## adapted from: flake8-logging v1.5.0
##
## Original: Copyright (c) 2023 Adam Johnson
#######################################################################

import ast
import re
import sys

from functools import lru_cache
from typing import cast

_LoggerMethods = frozenset(
    (
        "debug",
        "info",
        "warn",
        "warning",
        "error",
        "critical",
        "log",
        "exception",
    )
)

_LogrecordAttributes = frozenset(
    (
        "asctime",
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    )
)


@lru_cache(maxsize=None)
def _modposPlaceholderRe():
    """
    Function to generate a regular expression object for '%' formatting codes.

    @return regular expression object
    @rtype re.Pattern
    """
    # https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting
    return re.compile(
        r"""
            %  # noqa: M601
            (?P<spec>
                % |  # raw % character  # noqa: M601
                (?:
                    ([-#0 +]+)?  # conversion flags
                    (?P<minwidth>\d+|\*)?  # minimum field width
                    (?P<precision>\.\d+|\.\*)?  # precision
                    [hlL]?  # length modifier
                    [acdeEfFgGiorsuxX]  # conversion type
                )
            )
        """,
        re.VERBOSE,
    )


@lru_cache(maxsize=None)
def _modnamedPlaceholderRe():
    """
    Function to generate a regular expression object for '%' formatting codes using
    names.

    @return regular expression object
    @rtype re.Pattern
    """
    # https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting
    return re.compile(
        r"""
            %  # noqa: M601
            \(
                (?P<name>.*?)
            \)
            ([-#0 +]+)?  # conversion flags
            (\d+)?  # minimum field width
            (\.\d+)?  # precision
            [hlL]?  # length modifier
            [acdeEfFgGiorsuxX]  # conversion type
        """,
        re.VERBOSE,
    )


class LoggingVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor to check for logging issues.
    """

    GetLoggerNames = frozenset(("__cached__", "__file__"))

    def __init__(self, errorCallback):
        """
        Constructor

        @param errorCallback callback function to register an error
        @type func
        """
        super().__init__()

        self.__error = errorCallback

        self.__loggingName = None
        self.__loggerName = None
        self.__fromImports = {}
        self.__stack = []

    def visit(self, node):
        """
        Public method to handle ast nodes.

        @param node reference to the node to be processed
        @type ast.AST
        """
        self.__stack.append(node)
        super().visit(node)
        self.__stack.pop()

    def visit_Import(self, node):
        """
        Public method to handle Import nodes.

        @param node reference to the node to be processed
        @type ast.Import
        """
        for alias in node.names:
            if alias.name == "logging":
                self.__loggingName = alias.asname or alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """
        Public method to handle ImportFrom nodes.

        @param node reference to the node to be processed
        @type ast.ImportFrom
        """
        if node.module == "logging":
            for alias in node.names:
                if alias.name == "WARN":
                    if sys.version_info >= (3, 10):
                        lineno = alias.lineno
                        colOffset = alias.col_offset
                    else:
                        lineno = node.lineno
                        colOffset = node.col_offset
                    self.__error(lineno - 1, colOffset, "L109")
                if not alias.asname:
                    self.__fromImports[alias.name] = node.module

        self.generic_visit(node)

    def visit_Attribute(self, node):
        """
        Public method to handle  Attribute nodes.

        @param node reference to the node to be processed
        @type ast.Attribute
        """
        if (
            self.__loggingName
            and isinstance(node.value, ast.Name)
            and node.value.id == self.__loggingName
            and node.attr == "WARN"
        ):
            self.__error(node.lineno - 1, node.col_offset, "L109")

        self.generic_visit(node)

    def visit_Call(self, node):
        """
        Public method to handle Call nodes.

        @param node reference to the node to be processed
        @type ast.Call
        """
        if (
            (
                self.__loggingName
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "Logger"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == self.__loggingName
            )
            or (
                isinstance(node.func, ast.Name)
                and node.func.id == "Logger"
                and self.__fromImports.get("Logger") == "logging"
            )
        ) and not self.__atModuleLevel():
            self.__error(node.lineno - 1, node.col_offset, "L101")

        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _LoggerMethods
            and isinstance(node.func.value, ast.Name)
            and self.__loggingName
            and node.func.value.id == self.__loggingName
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id in _LoggerMethods
            and self.__fromImports.get(node.func.id) == "logging"
        ):
            self.__error(node.lineno - 1, node.col_offset, "L115")

        if (
            self.__loggingName
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "getLogger"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == self.__loggingName
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id == "getLogger"
            and self.__fromImports.get("getLogger") == "logging"
        ):
            if (
                len(self.__stack) >= 2
                and isinstance(assign := self.__stack[-2], ast.Assign)
                and len(assign.targets) == 1
                and isinstance(assign.targets[0], ast.Name)
                and not self.__atModuleLevel()
            ):
                self.__loggerName = assign.targets[0].id

            if (
                node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in self.GetLoggerNames
            ):
                self.__error(node.args[0].lineno - 1, node.args[0].col_offset, "L102")

        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _LoggerMethods
            and isinstance(node.func.value, ast.Name)
        ) and (
            (self.__loggingName and node.func.value.id == self.__loggingName)
            or (self.__loggerName and node.func.value.id == self.__loggerName)
        ):
            excHandler = self.__currentExceptHandler()

            # L108
            if node.func.attr == "warn":
                self.__error(node.lineno - 1, node.col_offset, "L108")

            # L103
            extraKeys = []
            if any((extraNode := kw).arg == "extra" for kw in node.keywords):
                if isinstance(extraNode.value, ast.Dict):
                    extraKeys = [
                        (k.value, k)
                        for k in extraNode.value.keys
                        if isinstance(k, ast.Constant)
                    ]
                elif (
                    isinstance(extraNode.value, ast.Call)
                    and isinstance(extraNode.value.func, ast.Name)
                    and extraNode.value.func.id == "dict"
                ):
                    extraKeys = [
                        (k.arg, k)
                        for k in extraNode.value.keywords
                        if k.arg is not None
                    ]

            for key, keyNode in extraKeys:
                if key in _LogrecordAttributes:
                    if isinstance(keyNode, ast.keyword):
                        lineno, colOffset = self.__keywordPos(keyNode)
                    else:
                        lineno = keyNode.lineno
                        colOffset = keyNode.col_offset
                    self.__error(lineno - 1, colOffset, "L103", repr(key))

            if node.func.attr == "exception":
                # L104
                if not excHandler:
                    self.__error(node.lineno - 1, node.col_offset, "L104")

                if any((excInfo := kw).arg == "exc_info" for kw in node.keywords):
                    # L106
                    if (
                        isinstance(excInfo.value, ast.Constant) and excInfo.value.value
                    ) or (
                        excHandler
                        and isinstance(excInfo.value, ast.Name)
                        and excInfo.value.id == excHandler.name
                    ):
                        lineno, colOffset = self.__keywordPos(excInfo)
                        self.__error(lineno - 1, colOffset, "L106")

                    # L107
                    elif (
                        isinstance(excInfo.value, ast.Constant)
                        and not excInfo.value.value
                    ):
                        lineno, colOffset = self.__keywordPos(excInfo)
                        self.__error(lineno - 1, colOffset, "L107")

            # L105
            elif node.func.attr == "error" and excHandler is not None:
                rewritable = False
                if any((excInfo := kw).arg == "exc_info" for kw in node.keywords):
                    if isinstance(excInfo.value, ast.Constant) and excInfo.value.value:
                        rewritable = True
                    elif (
                        isinstance(excInfo.value, ast.Name)
                        and excInfo.value.id == excHandler.name
                    ):
                        rewritable = True
                else:
                    rewritable = True

                if rewritable:
                    self.__error(node.lineno - 1, node.col_offset, "L105")

            # L114
            elif (
                excHandler is None
                and any((excInfo := kw).arg == "exc_info" for kw in node.keywords)
                and isinstance(excInfo.value, ast.Constant)
                and excInfo.value.value
            ):
                lineno, colOffset = self.__keywordPos(excInfo)
                self.__error(lineno - 1, colOffset, "L114")

            # L110
            if (
                node.func.attr == "exception"
                and len(node.args) >= 1
                and isinstance(node.args[0], ast.Name)
                and excHandler is not None
                and node.args[0].id == excHandler.name
            ):
                self.__error(node.args[0].lineno - 1, node.args[0].col_offset, "L110")

            msgArgKwarg = False
            if node.func.attr == "log" and len(node.args) >= 2:
                msgArg = node.args[1]
            elif node.func.attr != "log" and len(node.args) >= 1:
                msgArg = node.args[0]
            else:
                try:
                    msgArg = [k for k in node.keywords if k.arg == "msg"][0].value
                    msgArgKwarg = True
                except IndexError:
                    msgArg = None

            # L111
            if isinstance(msgArg, ast.JoinedStr):
                self.__error(msgArg.lineno - 1, msgArg.col_offset, "L111a")
            elif (
                isinstance(msgArg, ast.Call)
                and isinstance(msgArg.func, ast.Attribute)
                and isinstance(msgArg.func.value, ast.Constant)
                and isinstance(msgArg.func.value.value, str)
                and msgArg.func.attr == "format"
            ):
                self.__error(msgArg.lineno - 1, msgArg.col_offset, "L111b")
            elif (
                isinstance(msgArg, ast.BinOp)
                and isinstance(msgArg.op, ast.Mod)
                and isinstance(msgArg.left, ast.Constant)
                and isinstance(msgArg.left.value, str)
            ):
                self.__error(msgArg.lineno - 1, msgArg.col_offset, "L111c")
            elif isinstance(msgArg, ast.BinOp) and self.__isAddChainWithNonStr(msgArg):
                self.__error(msgArg.lineno - 1, msgArg.col_offset, "L111d")

            # L112
            if (
                msgArg is not None
                and not msgArgKwarg
                and (msg := self.__flattenStrChain(msgArg))
                and not any(isinstance(arg, ast.Starred) for arg in node.args)
            ):
                self.__checkMsgAndArgs(node, msgArg, msg)

        self.generic_visit(node)

    def __checkMsgAndArgs(self, node, msgArg, msg):
        """
        Private method to check the message and arguments a given Call node.

        @param node reference to the Call node
        @type ast.Call
        @param msgArg message argument nodes
        @type ast.AST
        @param msg message
        @type str
        """
        if not isinstance(node.func, ast.Attribute):
            return

        if (
            (
                (node.func.attr != "log" and (dictIdx := 1))
                or (node.func.attr == "log" and (dictIdx := 2))
            )
            and len(node.args) == dictIdx + 1
            and (dictNode := node.args[dictIdx])
            and isinstance(dictNode, ast.Dict)
            and all(
                isinstance(k, ast.Constant) and isinstance(k.value, str)
                for k in dictNode.keys
            )
            and (
                modnames := {m["name"] for m in _modnamedPlaceholderRe().finditer(msg)}
            )
        ):
            # L113
            given = {cast(ast.Constant, k).value for k in dictNode.keys}
            if missing := modnames - given:
                self.__error(
                    msgArg.lineno - 1,
                    msgArg.col_offset,
                    "L113a",  # missing keys
                    ", ".join([repr(k) for k in missing]),
                )

            if missing := given - modnames:
                self.__error(
                    msgArg.lineno - 1,
                    msgArg.col_offset,
                    "L113b",  # unreferenced keys
                    ", ".join([repr(k) for k in missing]),
                )

            return

        # L112
        modposCount = sum(
            1 + (m["minwidth"] == "*") + (m["precision"] == ".*")
            for m in _modposPlaceholderRe().finditer(msg)
            if m["spec"] != "%"
        )
        argCount = len(node.args) - 1 - (node.func.attr == "log")

        if modposCount > 0 and modposCount != argCount:
            self.__error(
                msgArg.lineno - 1,
                msgArg.col_offset,
                "L112",
                modposCount,
                "'%'",  # noqa: M601
                argCount,
            )
            return

    def __atModuleLevel(self):
        """
        Private method to check, if we are on the module level.

        @return flag indicating the module level
        @rtype bool
        """
        return any(
            isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
            for parent in self.__stack
        )

    def __currentExceptHandler(self):
        """
        Private method to determine the current exception handler node.

        @return reference to the current exception handler node or None
        @rtype ast.ExceptHandler
        """
        for node in reversed(self.__stack):
            if isinstance(node, ast.ExceptHandler):
                return node
            elif isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                break

        return None

    def __keywordPos(self, node):
        """
        Private method determine line number and column offset of a given keyword node.

        @param node reference to the keyword node
        @type ast.keyword
        @return tuple containing the line number and the column offset
        @rtype tuple of (int, int)
        """
        if sys.version_info >= (3, 9):
            return (node.lineno, node.col_offset)
        else:
            # Educated guess
            return (
                node.value.lineno,
                max(0, node.value.col_offset - 1 - len(node.arg)),
            )

    def __isAddChainWithNonStr(self, node):
        """
        Private method to check, if the node is an Add with a non string argument.

        @param node reference to the binary operator node
        @type ast.BinOp
        @return flag indicating an Add with a non string argument
        @rtype bool
        """
        if not isinstance(node.op, ast.Add):
            return False

        for side in (node.left, node.right):
            if isinstance(side, ast.BinOp):
                if self.__isAddChainWithNonStr(side):
                    return True
            elif not (isinstance(side, ast.Constant) and isinstance(side.value, str)):
                return True

        return False

    def __flattenStrChain(self, node):
        """
        Private method to flatten the given string chain.

        @param node reference to the AST node
        @type ast.AST
        @return flattened string
        @rtype str
        """
        parts = []

        def visit(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                parts.append(node.value)
                return True
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                return visit(node.left) and visit(node.right)
            return False

        result = visit(node)
        if result:
            return "".join(parts)
        else:
            return None
