# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a checker for logging related issues.
"""

import copy


class LoggingChecker:
    """
    Class implementing a checker for logging related issues.
    """

    Codes = [
        ## Logging
        "L101",
        "L102",
        "L103",
        "L104",
        "L105",
        "L106",
        "L107",
        "L108",
        "L109",
        "L110",
        "L111",
        "L112",
        "L113",
        "L114",
        "L115",
    ]

    def __init__(self, source, filename, tree, select, ignore, expected, repeat, args):
        """
        Constructor

        @param source source code to be checked
        @type list of str
        @param filename name of the source file
        @type str
        @param tree AST tree of the source code
        @type ast.Module
        @param select list of selected codes
        @type list of str
        @param ignore list of codes to be ignored
        @type list of str
        @param expected list of expected codes
        @type list of str
        @param repeat flag indicating to report each occurrence of a code
        @type bool
        @param args dictionary of arguments for the various checks
        @type dict
        """
        self.__select = tuple(select)  # noqa: M188
        self.__ignore = ("",) if select else tuple(ignore)  # noqa: M188
        self.__expected = expected[:]
        self.__repeat = repeat
        self.__filename = filename
        self.__source = source[:]
        self.__tree = copy.deepcopy(tree)
        self.__args = args

        # statistics counters
        self.counters = {}

        # collection of detected errors
        self.errors = []

        checkersWithCodes = [
            (
                self.__checkLogging,
                (
                    "L101",
                    "L102",
                    "L103",
                    "L104",
                    "L105",
                    "L106",
                    "L107",
                    "L108",
                    "L109",
                    "L110",
                    "L111",
                    "L112",
                    "L113",
                    "L114",
                    "L115",
                ),
            ),
        ]

        self.__checkers = []
        for checker, codes in checkersWithCodes:
            if any(not (code and self.__ignoreCode(code)) for code in codes):
                self.__checkers.append(checker)

    def __ignoreCode(self, code):
        """
        Private method to check if the message code should be ignored.

        @param code message code to check for
        @type str
        @return flag indicating to ignore the given code
        @rtype bool
        """
        return code.startswith(self.__ignore) and not code.startswith(self.__select)

    def __error(self, lineNumber, offset, code, *args):
        """
        Private method to record an issue.

        @param lineNumber line number of the issue
        @type int
        @param offset position within line of the issue
        @type int
        @param code message code
        @type str
        @param args arguments for the message
        @type list
        """
        if self.__ignoreCode(code):
            return

        if code in self.counters:
            self.counters[code] += 1
        else:
            self.counters[code] = 1

        # Don't care about expected codes
        if code in self.__expected:
            return

        if code and (self.counters[code] == 1 or self.__repeat):
            # record the issue with one based line number
            self.errors.append(
                {
                    "file": self.__filename,
                    "line": lineNumber + 1,
                    "offset": offset,
                    "code": code,
                    "args": args,
                }
            )

    def run(self):
        """
        Public method to check the given source against miscellaneous
        conditions.
        """
        if not self.__filename:
            # don't do anything, if essential data is missing
            return

        if not self.__checkers:
            # don't do anything, if no codes were selected
            return

        for check in self.__checkers:
            check()

    def __checkLogging(self):
        """
        Private method to check logging statements.
        """
        from .LoggingVisitor import LoggingVisitor

        visitor = LoggingVisitor(errorCallback=self.__error)
        visitor.visit(self.__tree)
