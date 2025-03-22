# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the security checker.
"""

import collections
import copy

from . import Checks
from .SecurityNodeVisitor import SecurityNodeVisitor


class SecurityChecker:
    """
    Class implementing a checker for security issues.
    """

    Codes = [
        # assert used
        "S101",
        # exec used
        "S102",
        # bad file permissions
        "S103",
        # bind to all interfaces
        "S104",
        # hardcoded passwords
        "S105",
        "S106",
        "S107"
        # hardcoded tmp directory
        "S108",
        # try-except
        "S110",
        "S112",
        # flask app
        "S201",
        # insecure function calls (prohibited)
        "S301",
        "S302",
        "S303",
        "S304",
        "S305",
        "S306",
        "S307",
        "S308",
        "S310",
        "S311",
        "S312",
        "S313",
        "S314",
        "S315",
        "S316",
        "S317",
        "S318",
        "S319",
        "S320",
        "S321",
        "S322",
        "S323",
        # hashlib.new
        "S331",
        # insecure imports (prohibited)
        "S401",
        "S402",
        "S403",
        "S404",
        "S405",
        "S406",
        "S407",
        "S408",
        "S409",
        "S410",
        "S411",
        "S412",
        "S413",
        # insecure certificate usage
        "S501",
        # insecure SSL/TLS protocol version
        "S502",
        "S503",
        "S504",
        # weak cryptographic keys
        "S505",
        # YAML load
        "S506",
        # SSH host key verification
        "S507",
        # Shell injection
        "S601",
        "S602",
        "S603",
        "S604",
        "S605",
        "S606",
        "S607",
        # SQL injection
        "S608",
        # Wildcard injection
        "S609",
        # Django SQL injection
        "S610",
        "S611",
        # insecure logging.config.listen()
        "S612",
        "S613",
        "S614",
        # Jinja2 templates
        "S701",
        # Mako templates
        "S702",
        # Django XSS vulnerability
        "S703",
        # hardcoded AWS passwords
        "S801",
        "S802",
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
        @param args dictionary of arguments for the security checks
        @type dict
        """
        self.__select = tuple(select)
        self.__ignore = ("",) if select else tuple(ignore)
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

        checkersWithCodes = Checks.generateCheckersDict()

        self.__checkers = collections.defaultdict(list)
        for checkType, checkersList in checkersWithCodes.items():
            for checker, codes in checkersList:
                if any(not (code and self.__ignoreCode(code)) for code in codes):
                    self.__checkers[checkType].append(checker)

    def __ignoreCode(self, code):
        """
        Private method to check if the message code should be ignored.

        @param code message code to check for
        @type str
        @return flag indicating to ignore the given code
        @rtype bool
        """
        return code.startswith(self.__ignore) and not code.startswith(self.__select)

    def reportError(self, lineNumber, offset, code, severity, confidence, *args):
        """
        Public method to record an issue.

        @param lineNumber line number of the issue
        @type int
        @param offset position within line of the issue
        @type int
        @param code message code
        @type str
        @param severity severity code (H = high, M = medium, L = low,
            U = undefined)
        @type str
        @param confidence confidence code (H = high, M = medium, L = low,
            U = undefined)
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
                    "severity": severity,
                    "confidence": confidence,
                }
            )

    def getConfig(self):
        """
        Public method to get the configuration dictionary.

        @return dictionary containing the configuration
        @rtype dict
        """
        return self.__args

    def run(self):
        """
        Public method to check the given source against security related
        conditions.
        """
        if not self.__filename:
            # don't do anything, if essential data is missing
            return

        if not self.__checkers:
            # don't do anything, if no codes were selected
            return

        securityNodeVisitor = SecurityNodeVisitor(
            self, self.__checkers, self.__filename, self.__source
        )
        securityNodeVisitor.generic_visit(self.__tree)
        securityNodeVisitor.checkFile()
