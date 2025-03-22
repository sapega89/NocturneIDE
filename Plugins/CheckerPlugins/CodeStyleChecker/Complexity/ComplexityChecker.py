# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a checker for code complexity.
"""

import ast
import copy

from .mccabe import PathGraphingAstVisitor


class ComplexityChecker:
    """
    Class implementing a checker for code complexity.
    """

    Codes = [
        "C101",
        "C111",
        "C112",
    ]

    def __init__(self, source, filename, tree, select, ignore, args):
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
        @param args dictionary of arguments for the miscellaneous checks
        @type dict
        """
        self.__filename = filename
        self.__source = source[:]
        self.__tree = copy.deepcopy(tree)
        self.__select = tuple(select)
        self.__ignore = ("",) if select else tuple(ignore)
        self.__args = args

        self.__defaultArgs = {
            "McCabeComplexity": 10,
            "LineComplexity": 15,
            "LineComplexityScore": 10,
        }

        # statistics counters
        self.counters = {}

        # collection of detected errors
        self.errors = []

        checkersWithCodes = [
            (self.__checkMcCabeComplexity, ("C101",)),
            (self.__checkLineComplexity, ("C111", "C112")),
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

        if code:
            # record the issue with one based line number
            self.errors.append(
                {
                    "file": self.__filename,
                    "line": lineNumber,
                    "offset": offset,
                    "code": code,
                    "args": args,
                }
            )

    def run(self):
        """
        Public method to check the given source for code complexity.
        """
        if not self.__filename or not self.__source:
            # don't do anything, if essential data is missing
            return

        if not self.__checkers:
            # don't do anything, if no codes were selected
            return

        for check in self.__checkers:
            check()

    def __checkMcCabeComplexity(self):
        """
        Private method to check the McCabe code complexity.
        """
        try:
            # create the AST again because it is modified by the checker
            tree = compile(
                "".join(self.__source), self.__filename, "exec", ast.PyCF_ONLY_AST
            )
        except (SyntaxError, TypeError):
            # compile errors are already reported by the run() method
            return

        maxComplexity = self.__args.get(
            "McCabeComplexity", self.__defaultArgs["McCabeComplexity"]
        )

        visitor = PathGraphingAstVisitor()
        visitor.preorder(tree, visitor)
        for graph in visitor.graphs.values():
            if graph.complexity() > maxComplexity:
                self.__error(graph.lineno, 0, "C101", graph.entity, graph.complexity())

    def __checkLineComplexity(self):
        """
        Private method to check the complexity of a single line of code and
        the median line complexity of the source code.

        Complexity is defined as the number of AST nodes produced by a line
        of code.
        """
        maxLineComplexity = self.__args.get(
            "LineComplexity", self.__defaultArgs["LineComplexity"]
        )
        maxLineComplexityScore = self.__args.get(
            "LineComplexityScore", self.__defaultArgs["LineComplexityScore"]
        )

        visitor = LineComplexityVisitor()
        visitor.visit(self.__tree)

        sortedItems = visitor.sortedList()
        score = visitor.score()

        for line, complexity in sortedItems:
            if complexity > maxLineComplexity:
                self.__error(line, 0, "C111", complexity)

        if score > maxLineComplexityScore:
            self.__error(0, 0, "C112", score)


class LineComplexityVisitor(ast.NodeVisitor):
    """
    Class calculating the number of AST nodes per line of code
    and the median nodes/line score.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.__count = {}

    def visit(self, node):
        """
        Public method to recursively visit all the nodes and add up the
        instructions.

        @param node reference to the node
        @type ast.AST
        """
        if hasattr(node, "lineno"):
            self.__count[node.lineno] = self.__count.get(node.lineno, 0) + 1
        self.generic_visit(node)

    def sortedList(self):
        """
        Public method to get a sorted list of (line, nodes) tuples.

        @return sorted list of (line, nodes) tuples
        @rtype list of tuple of (int,int)
        """
        lst = [(line, self.__count[line]) for line in sorted(self.__count)]
        return lst

    def score(self):
        """
        Public method to calculate the median.

        @return median line complexity value
        @rtype float
        """
        sortedList = sorted(self.__count.values())
        listLength = len(sortedList)
        medianIndex = (listLength - 1) // 2

        if listLength == 0:
            return 0.0
        elif listLength % 2:
            return float(sortedList[medianIndex])
        else:
            return (sortedList[medianIndex] + sortedList[medianIndex + 1]) / 2.0
