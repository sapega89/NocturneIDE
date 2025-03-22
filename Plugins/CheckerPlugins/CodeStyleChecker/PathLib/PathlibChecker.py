# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the checker for functions that can be replaced by use of
the pathlib module.
"""

#####################################################################################
## adapted from: flake8-use-pathlib v0.3.0                                         ##
##                                                                                 ##
## Original: Copyright (c) 2021 Rodolphe Pelloux-Prayer                            ##
##                                                                                 ##
## License:                                                                        ##
## Permission is hereby granted, free of charge, to any person obtaining a copy    ##
## of this software and associated documentation files (the "Software"), to deal   ##
## in the Software without restriction, including without limitation the rights    ##
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell       ##
## copies of the Software, and to permit persons to whom the Software is           ##
## furnished to do so, subject to the following conditions:                        ##
##                                                                                 ##
## The above copyright notice and this permission notice shall be included in all  ##
## copies or substantial portions of the Software.                                 ##
##                                                                                 ##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR      ##
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,        ##
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE     ##
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER          ##
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,   ##
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE   ##
#####################################################################################

import ast
import contextlib
import copy


class PathlibChecker:
    """
    Class implementing a checker for functions that can be replaced by use of
    the pathlib module.
    """

    Codes = [
        ## Replacements for the os module functions
        "P101",
        "P102",
        "P103",
        "P104",
        "P105",
        "P106",
        "P107",
        "P108",
        "P109",
        "P110",
        "P111",
        "P112",
        "P113",
        "P114",
        ## Replacements for the os.path module functions
        "P201",
        "P202",
        "P203",
        "P204",
        "P205",
        "P206",
        "P207",
        "P208",
        "P209",
        "P210",
        "P211",
        "P212",
        "P213",
        ## Replacements for some Python standard library functions
        "P301",
        ## Replacements for py.path.local
        "P401",
    ]

    # map functions to be replaced to error codes
    Function2Code = {
        "os.chmod": "P101",
        "os.mkdir": "P102",
        "os.makedirs": "P103",
        "os.rename": "P104",
        "os.replace": "P105",
        "os.rmdir": "P106",
        "os.remove": "P107",
        "os.unlink": "P108",
        "os.getcwd": "P109",
        "os.readlink": "P110",
        "os.stat": "P111",
        "os.listdir": "P112",
        "os.link": "P113",
        "os.symlink": "P114",
        "os.path.abspath": "P201",
        "os.path.exists": "P202",
        "os.path.expanduser": "P203",
        "os.path.isdir": "P204",
        "os.path.isfile": "P205",
        "os.path.islink": "P206",
        "os.path.isabs": "P207",
        "os.path.join": "P208",
        "os.path.basename": "P209",
        "os.path.dirname": "P210",
        "os.path.samefile": "P211",
        "os.path.splitext": "P212",
        "os.path.relpath": "P213",
        "open": "P301",
        "py.path.local": "P401",
    }

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
        Public method to check the given source against functions
        to be replaced by 'pathlib' equivalents.
        """
        if not self.__filename:
            # don't do anything, if essential data is missing
            return

        if not self.__checkCodes:
            # don't do anything, if no codes were selected
            return

        visitor = PathlibVisitor(self.__checkForReplacement)
        visitor.visit(self.__tree)

    def __checkForReplacement(self, node, name):
        """
        Private method to check the given node for the need for a
        replacement.

        @param node reference to the AST node to check
        @type ast.AST
        @param name resolved name of the node
        @type str
        """
        with contextlib.suppress(KeyError):
            errorCode = self.Function2Code[name]
            self.__error(node.lineno - 1, node.col_offset, errorCode)


class PathlibVisitor(ast.NodeVisitor):
    """
    Class to traverse the AST node tree and check for potential issues.
    """

    def __init__(self, checkCallback):
        """
        Constructor

        @param checkCallback callback function taking a reference to the
            AST node and the resolved name
        @type func
        """
        super().__init__()

        self.__checkCallback = checkCallback
        self.__importAlias = {}

    def visit_ImportFrom(self, node):
        """
        Public method handle the ImportFrom AST node.

        @param node reference to the ImportFrom AST node
        @type ast.ImportFrom
        """
        for imp in node.names:
            if imp.asname:
                self.__importAlias[imp.asname] = f"{node.module}.{imp.name}"
            else:
                self.__importAlias[imp.name] = f"{node.module}.{imp.name}"

    def visit_Import(self, node):
        """
        Public method to handle the Import AST node.

        @param node reference to the Import AST node
        @type ast.Import
        """
        for imp in node.names:
            if imp.asname:
                self.__importAlias[imp.asname] = imp.name

    def visit_Call(self, node):
        """
        Public method to handle the Call AST node.

        @param node reference to the Call AST node
        @type ast.Call
        """
        nameResolver = NameResolver(self.__importAlias)
        nameResolver.visit(node.func)

        self.__checkCallback(node, nameResolver.name())


class NameResolver(ast.NodeVisitor):
    """
    Class to resolve a Name or Attribute node.
    """

    def __init__(self, importAlias):
        """
        Constructor

        @param importAlias reference to the import aliases dictionary
        @type dict
        """
        self.__importAlias = importAlias
        self.__names = []

    def name(self):
        """
        Public method to resolve the name.

        @return resolved name
        @rtype str
        """
        with contextlib.suppress(KeyError, IndexError):
            attr = self.__importAlias[self.__names[-1]]
            self.__names[-1] = attr
            # do nothing if there is no such name or the names list is empty

        return ".".join(reversed(self.__names))

    def visit_Name(self, node):
        """
        Public method to handle the Name AST node.

        @param node reference to the Name AST node
        @type ast.Name
        """
        self.__names.append(node.id)

    def visit_Attribute(self, node):
        """
        Public method to handle the Attribute AST node.

        @param node reference to the Attribute AST node
        @type ast.Attribute
        """
        try:
            self.__names.append(node.attr)
            self.__names.append(node.value.id)
        except AttributeError:
            self.generic_visit(node)
