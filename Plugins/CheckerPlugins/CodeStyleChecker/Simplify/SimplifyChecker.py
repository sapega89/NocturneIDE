# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the checker for simplifying Python code.
"""

import ast
import copy

from .SimplifyNodeVisitor import SimplifyNodeVisitor


class SimplifyChecker:
    """
    Class implementing a checker for to help simplifying Python code.
    """

    Codes = [
        # Python-specifics
        "Y101",
        "Y102",
        "Y103",
        "Y104",
        "Y105",
        "Y106",
        "Y107",
        "Y108",
        "Y109",
        "Y110",
        "Y111",
        "Y112",
        "Y113",
        "Y114",
        "Y115",
        "Y116",
        "Y117",
        "Y118",
        "Y119",
        "Y120",
        "Y121",
        "Y122",
        "Y123",
        # Python-specifics not part of flake8-simplify
        "Y181",
        "Y182",
        # Comparations
        "Y201",
        "Y202",
        "Y203",
        "Y204",
        "Y205",
        "Y206",
        "Y207",
        "Y208",
        "Y211",
        "Y212",
        "Y213",
        "Y221",
        "Y222",
        "Y223",
        "Y224",
        # Opinionated
        "Y301",
        # General Code Style
        "Y401",
        "Y402",
        # Additional Checks
        "Y901",
        "Y904",
        "Y905",
        "Y906",
        "Y907",
        "Y909",
        "Y910",
        "Y911",
    ]

    def __init__(self, source, filename, tree, selected, ignored, expected, repeat):
        """
        Constructor

        @param source source code to be checked
        @type list of str
        @param filename name of the source file
        @type str
        @param tree AST tree of the source code
        @type ast.Module
        @param selected list of selected codes
        @type list of str
        @param ignored list of codes to be ignored
        @type list of str
        @param expected list of expected codes
        @type list of str
        @param repeat flag indicating to report each occurrence of a code
        @type bool
        """
        self.__select = tuple(selected)
        self.__ignore = ("",) if selected else tuple(ignored)
        self.__expected = expected[:]
        self.__repeat = repeat
        self.__filename = filename
        self.__source = source[:]
        self.__tree = copy.deepcopy(tree)

        # statistics counters
        self.counters = {}

        # collection of detected errors
        self.errors = []

        self.__checkCodes = (code for code in self.Codes if not self.__ignoreCode(code))

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

        # record the issue with one based line number
        errorInfo = {
            "file": self.__filename,
            "line": lineNumber + 1,
            "offset": offset,
            "code": code,
            "args": args,
        }

        if errorInfo not in self.errors:
            # this issue was not seen before
            if code in self.counters:
                self.counters[code] += 1
            else:
                self.counters[code] = 1

            # Don't care about expected codes
            if code in self.__expected:
                return

            if code and (self.counters[code] == 1 or self.__repeat):
                self.errors.append(errorInfo)

    def run(self):
        """
        Public method to check the given source against functions
        to be replaced by 'pathlib' equivalents.
        """
        if not self.__filename:
            # don't do anything, if essential data is missing
            return

        if not self.__checkCodes:
            # don't do anything, if no codes were selected
            return

        # Add parent information
        self.__addMeta(self.__tree)

        visitor = SimplifyNodeVisitor(self.__error)
        visitor.visit(self.__tree)

    def __addMeta(self, root, level=0):
        """
        Private method to amend the nodes of the given AST tree with backward and
        forward references.

        @param root reference to the root node of the tree
        @type ast.AST
        @param level nesting level (defaults to 0)
        @type int (optional)
        """
        previousSibling = None
        for node in ast.iter_child_nodes(root):
            if level == 0:
                node.parent = root
            node.previous_sibling = previousSibling
            node.next_sibling = None
            if previousSibling:
                node.previous_sibling.next_sibling = node
            previousSibling = node
            for child in ast.iter_child_nodes(node):
                child.parent = node
            self.__addMeta(node, level=level + 1)
