# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a checker for import statements.
"""

import ast
import copy
import re


class NameOrderChecker:
    """
    Class implementing a checker for name ordering.

    Note: Name ordering is checked for import statements, the '__all__' statement
    and exception names of exception handlers.
    """

    Codes = [
        ## Imports order
        "NO101",
        "NO102",
        "NO103",
        "NO104",
        "NO105",
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
        self.__select = tuple(select)
        self.__ignore = ("",) if select else tuple(ignore)
        self.__expected = expected[:]
        self.__repeat = repeat
        self.__filename = filename
        self.__source = source[:]
        self.__tree = copy.deepcopy(tree)
        self.__args = args

        # parameters for import sorting
        if args["SortOrder"] == "native":
            self.__sortingFunction = sorted
        else:
            # naturally is the default sort order
            self.__sortingFunction = self.__naturally
        self.__sortCaseSensitive = args["SortCaseSensitive"]

        # statistics counters
        self.counters = {}

        # collection of detected errors
        self.errors = []

        checkersWithCodes = [
            (self.__checkNameOrder, ("NO101", "NO102", "NO103", "NO104", "NO105")),
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

    #######################################################################
    ## Name Order
    ##
    ## adapted from: flake8-alphabetize v0.0.21
    #######################################################################

    def __checkNameOrder(self):
        """
        Private method to check the order of import statements and handled exceptions.
        """
        from .ImportNode import ImportNode

        errors = []
        imports = []
        importNodes, aListNode, eListNodes = self.__findNodes(self.__tree)

        # check for an error in '__all__'
        allError = self.__findErrorInAll(aListNode)
        if allError is not None:
            errors.append(allError)

        errors.extend(self.__findExceptionListErrors(eListNodes))

        for importNode in importNodes:
            if isinstance(importNode, ast.Import) and len(importNode.names) > 1:
                # skip suck imports because its already handled by pycodestyle
                continue

            imports.append(
                ImportNode(
                    self.__args.get("ApplicationPackageNames", []),
                    importNode,
                    self,
                    self.__args.get("SortIgnoringStyle", False),
                    self.__args.get("SortFromFirst", False),
                )
            )

        lenImports = len(imports)
        if lenImports > 0:
            p = imports[0]
            if p.error is not None:
                errors.append(p.error)

            if lenImports > 1:
                for n in imports[1:]:
                    if n.error is not None:
                        errors.append(n.error)

                    if n == p:
                        if self.__args.get("CombinedAsImports", False) or (
                            not n.asImport and not p.asImport
                        ):
                            errors.append((n.node, "NO103", str(p), str(n)))
                    elif n < p:
                        errors.append((n.node, "NO101", str(n), str(p)))

                    p = n

        for error in errors:
            if not self.__ignoreCode(error[1]):
                node = error[0]
                reason = error[1]
                args = error[2:]
                self.__error(node.lineno - 1, node.col_offset, reason, *args)

    def __findExceptionListNodes(self, tree):
        """
        Private method to find all exception types handled by given tree.

        @param tree reference to the ast node tree to be parsed
        @type ast.AST
        @return list of exception types
        @rtype list of ast.Name
        """
        nodes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                nodeType = node.type
                if isinstance(nodeType, (ast.List, ast.Tuple)):
                    nodes.append(nodeType)

        return nodes

    def __findNodes(self, tree):
        """
        Private method to find all import and import from nodes of the given
        tree.

        @param tree reference to the ast node tree to be parsed
        @type ast.AST
        @return tuple containing a list of import nodes, the '__all__' node and
            exception nodes
        @rtype tuple of (ast.Import | ast.ImportFrom, ast.List | ast.Tuple,
            ast.List | ast.Tuple)
        """
        importNodes = []
        aListNode = None
        eListNodes = self.__findExceptionListNodes(tree)

        if isinstance(tree, ast.Module):
            body = tree.body

            for n in body:
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    importNodes.append(n)

                elif isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name) and t.id == "__all__":
                            value = n.value

                            if isinstance(value, (ast.List, ast.Tuple)):
                                aListNode = value

        return importNodes, aListNode, eListNodes

    def __findErrorInAll(self, node):
        """
        Private method to check the '__all__' node for errors.

        @param node reference to the '__all__' node
        @type ast.List or ast.Tuple
        @return tuple containing a reference to the node an error code and the error
            arguments
        @rtype tuple of (ast.List | ast.Tuple, str, str)
        """
        if node is not None:
            actualList = []
            for el in node.elts:
                if isinstance(el, ast.Constant):
                    actualList.append(el.value)
                else:
                    # Can't handle anything that isn't a string literal
                    return None

            expectedList = self.sorted(
                actualList,
                key=lambda k: self.moduleKey(k, subImports=True),
            )
            if expectedList != actualList:
                return (node, "NO104", ", ".join(expectedList))

        return None

    def __findExceptionListStr(self, node):
        """
        Private method to get the exception name out of an exception handler type node.

        @param node node to be treated
        @type ast.Name or ast.Attribute
        @return string containing the exception name
        @rtype str
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self.__findExceptionListStr(node.value)}.{node.attr}"

        return ""

    def __findExceptionListErrors(self, nodes):
        """
        Private method to check the exception node for errors.

        @param nodes list of exception nodes
        @type list of ast.List or ast.Tuple
        @return DESCRIPTION
        @rtype TYPE
        """
        errors = []

        for node in nodes:
            actualList = [self.__findExceptionListStr(elt) for elt in node.elts]

            expectedList = self.sorted(actualList)
            if expectedList != actualList:
                errors.append((node, "NO105", ", ".join(expectedList)))

        return errors

    def sorted(self, toSort, key=None, reverse=False):
        """
        Public method to sort the given list of names.

        @param toSort list of names to be sorted
        @type list of str
        @param key function to generate keys (defaults to None)
        @type function (optional)
        @param reverse flag indicating a reverse sort (defaults to False)
        @type bool (optional)
        @return sorted list of names
        @rtype list of str
        """
        return self.__sortingFunction(toSort, key=key, reverse=reverse)

    def __naturally(self, toSort, key=None, reverse=False):
        """
        Private method to sort the given list of names naturally.

        Note: Natural sorting maintains the sort order of numbers (i.e.
            [Q1, Q10, Q2] is sorted as [Q1, Q2, Q10] while the Python
            standard sort would yield [Q1, Q10, Q2].

        @param toSort list of names to be sorted
        @type list of str
        @param key function to generate keys (defaults to None)
        @type function (optional)
        @param reverse flag indicating a reverse sort (defaults to False)
        @type bool (optional)
        @return sorted list of names
        @rtype list of str
        """
        if key is None:
            keyCallback = self.__naturalKeys
        else:

            def keyCallback(text):
                return self.__naturalKeys(key(text))

        return sorted(toSort, key=keyCallback, reverse=reverse)

    def __atoi(self, text):
        """
        Private method to convert the given text to an integer number.

        @param text text to be converted
        @type str
        @return integer number
        @rtype int
        """
        return int(text) if text.isdigit() else text

    def __naturalKeys(self, text):
        """
        Private method to generate keys for natural sorting.

        @param text text to generate a key for
        @type str
        @return key for natural sorting
        @rtype list of str or int
        """
        return [self.__atoi(c) for c in re.split(r"(\d+)", text)]

    def moduleKey(self, moduleName, subImports=False):
        """
        Public method to generate a key for the given module name.

        @param moduleName module name
        @type str
        @param subImports flag indicating a sub import like in
            'from foo import bar, baz' (defaults to False)
        @type bool (optional)
        @return generated key
        @rtype str
        """
        prefix = ""

        if subImports:
            if moduleName.isupper() and len(moduleName) > 1:
                prefix = "A"
            elif moduleName[0:1].isupper():
                prefix = "B"
            else:
                prefix = "C"
        if not self.__sortCaseSensitive:
            moduleName = moduleName.lower()

        return f"{prefix}{moduleName}"
