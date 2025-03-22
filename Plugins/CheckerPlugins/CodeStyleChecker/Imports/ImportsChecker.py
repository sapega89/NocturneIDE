# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a checker for import statements.
"""

import ast
import copy
import re


class ImportsChecker:
    """
    Class implementing a checker for import statements.
    """

    Codes = [
        ## Local imports
        "I101",
        "I102",
        "I103",
        ## Various other import related
        "I901",
        "I902",
        "I903",
        "I904",
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

        # statistics counters
        self.counters = {}

        # collection of detected errors
        self.errors = []

        checkersWithCodes = [
            (self.__checkLocalImports, ("I101", "I102", "I103")),
            (self.__tidyImports, ("I901", "I902", "I903", "I904")),
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
    ## Local imports
    ##
    ## adapted from: flake8-local-import v1.0.6
    #######################################################################

    def __checkLocalImports(self):
        """
        Private method to check local imports.
        """
        from .LocalImportVisitor import LocalImportVisitor

        visitor = LocalImportVisitor(self.__args, self)
        visitor.visit(copy.deepcopy(self.__tree))
        for violation in visitor.violations:
            if not self.__ignoreCode(violation[1]):
                node = violation[0]
                reason = violation[1]
                self.__error(node.lineno - 1, node.col_offset, reason)

    #######################################################################
    ## Tidy imports
    ##
    ## adapted from: flake8-tidy-imports v4.10.0
    #######################################################################

    def __tidyImports(self):
        """
        Private method to check various other import related topics.
        """
        self.__banRelativeImports = self.__args.get("BanRelativeImports", "")
        self.__bannedModules = []
        self.__bannedStructuredPatterns = []
        self.__bannedUnstructuredPatterns = []
        for module in self.__args.get("BannedModules", []):
            module = module.strip()
            if "*" in module[:-1] or module == "*":
                # unstructured
                self.__bannedUnstructuredPatterns.append(
                    self.__compileUnstructuredGlob(module)
                )
            elif module.endswith(".*"):
                # structured
                self.__bannedStructuredPatterns.append(module)
                # Also check for exact matches without the wildcard
                # e.g. "foo.*" matches "foo"
                prefix = module[:-2]
                if prefix not in self.__bannedModules:
                    self.__bannedModules.append(prefix)
            else:
                self.__bannedModules.append(module)

        # Sort the structured patterns so we match the specifc ones first.
        self.__bannedStructuredPatterns.sort(key=lambda x: len(x[0]), reverse=True)

        ruleMethods = []
        if not self.__ignoreCode("I901"):
            ruleMethods.append(self.__checkUnnecessaryAlias)
        if not self.__ignoreCode("I902") and bool(self.__bannedModules):
            ruleMethods.append(self.__checkBannedImport)
        if (
            not self.__ignoreCode("I903") and self.__banRelativeImports == "parents"
        ) or (not self.__ignoreCode("I904") and self.__banRelativeImports == "true"):
            ruleMethods.append(self.__checkBannedRelativeImports)

        for node in ast.walk(self.__tree):
            for method in ruleMethods:
                method(node)

    def __compileUnstructuredGlob(self, module):
        """
        Private method to convert a pattern to a regex such that ".*" matches zero or
        more modules.

        @param module module pattern to be converted
        @type str
        @return compiled regex
        @rtype re.regex object
        """
        parts = module.split(".")
        transformedParts = [
            "(\\..*)?" if p == "*" else "\\." + re.escape(p) for p in parts
        ]
        if parts[0] == "*":
            transformedParts[0] = ".*"
        else:
            transformedParts[0] = re.escape(parts[0])
        return re.compile("".join(transformedParts) + "\\Z")

    def __checkUnnecessaryAlias(self, node):
        """
        Private method to check unnecessary import aliases.

        @param node reference to the node to be checked
        @type ast.AST
        """
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "." not in alias.name:
                    fromName = None
                    importedName = alias.name
                else:
                    fromName, importedName = alias.name.rsplit(".", 1)

                if importedName == alias.asname:
                    if fromName:
                        rewritten = f"from {fromName} import {importedName}"
                    else:
                        rewritten = f"import {importedName}"

                    self.__error(node.lineno - 1, node.col_offset, "I901", rewritten)

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == alias.asname:
                    rewritten = f"from {node.module} import {alias.name}"

                    self.__error(node.lineno - 1, node.col_offset, "I901", rewritten)

    def __isModuleBanned(self, moduleName):
        """
        Private method to check, if the given module name banned.

        @param moduleName module name to be checked
        @type str
        @return flag indicating a banned module
        @rtype bool
        """
        if moduleName in self.__bannedModules:
            return True

        # Check unustructed wildcards
        if any(
            bannedPattern.match(moduleName)
            for bannedPattern in self.__bannedUnstructuredPatterns
        ):
            return True

        # Check structured wildcards
        if any(
            moduleName.startswith(bannedPrefix[:-1])
            for bannedPrefix in self.__bannedStructuredPatterns
        ):
            return True

        return False

    def __checkBannedImport(self, node):
        """
        Private method to check import of banned modules.

        @param node reference to the node to be checked
        @type ast.AST
        """
        if (
            not bool(self.__bannedModules)
            and not bool(self.__bannedUnstructuredPatterns)
            and not bool(self.__bannedStructuredPatterns)
        ):
            # nothing to check
            return

        if isinstance(node, ast.Import):
            moduleNames = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            nodeModule = node.module or ""
            moduleNames = [nodeModule]
            for alias in node.names:
                moduleNames.append("{0}.{1}".format(nodeModule, alias.name))
        else:
            return

        # Sort from most to least specific paths.
        moduleNames.sort(key=len, reverse=True)

        warned = set()

        for moduleName in moduleNames:
            if self.__isModuleBanned(moduleName):
                if any(mod.startswith(moduleName) for mod in warned):
                    # Do not show an error for this line if we already showed
                    # a more specific error.
                    continue
                else:
                    warned.add(moduleName)
                self.__error(node.lineno - 1, node.col_offset, "I902", moduleName)

    def __checkBannedRelativeImports(self, node):
        """
        Private method to check if relative imports are banned.

        @param node reference to the node to be checked
        @type ast.AST
        """
        if not self.__banRelativeImports:
            # nothing to check
            return

        elif self.__banRelativeImports == "parents":
            minNodeLevel = 1
            msgCode = "I903"
        else:
            minNodeLevel = 0
            msgCode = "I904"

        if isinstance(node, ast.ImportFrom) and node.level > minNodeLevel:
            self.__error(node.lineno - 1, node.col_offset, msgCode)
