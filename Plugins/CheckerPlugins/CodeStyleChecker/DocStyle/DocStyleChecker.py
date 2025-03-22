# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a checker for documentation string conventions.
"""

#
# The routines of the checker class are modeled after the ones found in
# pep257.py (version 0.2.4).
#

import ast
import contextlib
import tokenize

from io import StringIO

try:
    ast.AsyncFunctionDef  # __IGNORE_EXCEPTION__
except AttributeError:
    ast.AsyncFunctionDef = ast.FunctionDef


class DocStyleContext:
    """
    Class implementing the source context.
    """

    def __init__(self, source, startLine, contextType):
        """
        Constructor

        @param source source code of the context
        @type list of str or str
        @param startLine line number the context starts in the source
        @type int
        @param contextType type of the context object
        @type str
        """
        if isinstance(source, str):
            self.__source = source.splitlines(True)
        else:
            self.__source = source[:]
        self.__start = startLine
        self.__indent = ""
        self.__type = contextType
        self.__special = ""

        # ensure first line is left justified
        if self.__source:
            self.__indent = self.__source[0].replace(self.__source[0].lstrip(), "")
            self.__source[0] = self.__source[0].lstrip()

    def source(self):
        """
        Public method to get the source.

        @return source
        @rtype list of str
        """
        return self.__source

    def ssource(self):
        """
        Public method to get the joined source lines.

        @return source
        @rtype str
        """
        return "".join(self.__source)

    def start(self):
        """
        Public method to get the start line number.

        @return start line number
        @rtype int
        """
        return self.__start

    def end(self):
        """
        Public method to get the end line number.

        @return end line number
        @rtype int
        """
        return self.__start + len(self.__source) - 1

    def indent(self):
        """
        Public method to get the indentation of the first line.

        @return indentation string
        @rtype str
        """
        return self.__indent

    def contextType(self):
        """
        Public method to get the context type.

        @return context type
        @rtype str
        """
        return self.__type

    def setSpecial(self, special):
        """
        Public method to set a special attribute for the context.

        @param special attribute string
        @type str
        """
        self.__special = special

    def special(self):
        """
        Public method to get the special context attribute string.

        @return attribute string
        @rtype str
        """
        return self.__special


class DocStyleChecker:
    """
    Class implementing a checker for documentation string conventions.
    """

    Codes = [
        "D101",
        "D102",
        "D103",
        "D104",
        "D105",
        "D111",
        "D112",
        "D121",
        "D122",
        "D130",
        "D131",
        "D132",
        "D133",
        "D134",
        "D141",
        "D142",
        "D143",
        "D144",
        "D145",
        "D201",
        "D202.1",
        "D202.2",
        "D203",
        "D205",
        "D206",
        "D221",
        "D222",
        "D231",
        "D232",
        "D234r",
        "D234y",
        "D235r",
        "D235y",
        "D236",
        "D237",
        "D238",
        "D239",
        "D242",
        "D243",
        "D244",
        "D245",
        "D246",
        "D247",
        "D250",
        "D251",
        "D252",
        "D253",
        "D260",
        "D261",
        "D262",
        "D263",
        "D270",
        "D271",
        "D272",
        "D273",
    ]

    def __init__(
        self,
        source,
        filename,
        select,
        ignore,
        expected,
        repeat,
        maxLineLength=88,
        docType="pep257",
    ):
        """
        Constructor

        @param source source code to be checked
        @type list of str
        @param filename name of the source file
        @type str
        @param select list of selected codes
        @type list of str
        @param ignore list of codes to be ignored
        @type list of str
        @param expected list of expected codes
        @type list of str
        @param repeat flag indicating to report each occurrence of a code
        @type bool
        @param maxLineLength allowed line length
        @type int
        @param docType type of the documentation strings (one of 'eric' or 'pep257')
        @type str
        """
        self.__select = tuple(select)
        self.__ignore = ("",) if select else tuple(ignore)
        self.__expected = expected[:]
        self.__repeat = repeat
        self.__maxLineLength = maxLineLength
        self.__docType = docType
        self.__filename = filename
        self.__source = source[:]

        # statistics counters
        self.counters = {}

        # collection of detected errors
        self.errors = []

        self.__lineNumber = 0

        # caches
        self.__functionsCache = None
        self.__classesCache = None
        self.__methodsCache = None

        self.__keywords = [
            "moduleDocstring",
            "functionDocstring",
            "classDocstring",
            "methodDocstring",
            "defDocstring",
            "docstring",
        ]
        if self.__docType == "pep257":
            checkersWithCodes = {
                "moduleDocstring": [
                    (self.__checkModulesDocstrings, ("D101",)),
                ],
                "functionDocstring": [],
                "classDocstring": [
                    (self.__checkClassDocstring, ("D104", "D105")),
                    (self.__checkBlankBeforeAndAfterClass, ("D142", "D143")),
                ],
                "methodDocstring": [],
                "defDocstring": [
                    (self.__checkFunctionDocstring, ("D102", "D103")),
                    (self.__checkImperativeMood, ("D132",)),
                    (self.__checkNoSignature, ("D133",)),
                    (self.__checkReturnType, ("D134",)),
                    (self.__checkNoBlankLineBefore, ("D141",)),
                ],
                "docstring": [
                    (self.__checkTripleDoubleQuotes, ("D111",)),
                    (self.__checkBackslashes, ("D112",)),
                    (self.__checkOneLiner, ("D121",)),
                    (self.__checkIndent, ("D122",)),
                    (self.__checkSummary, ("D130",)),
                    (self.__checkEndsWithPeriod, ("D131",)),
                    (self.__checkBlankAfterSummary, ("D144",)),
                    (self.__checkBlankAfterLastParagraph, ("D145",)),
                ],
            }
        elif self.__docType in ("eric", "eric_black"):
            checkersWithCodes = {
                "moduleDocstring": [
                    (self.__checkModulesDocstrings, ("D101", "D201")),
                ],
                "functionDocstring": [],
                "classDocstring": [
                    (self.__checkClassDocstring, ("D104", "D205", "D206")),
                    (
                        self.__checkEricNoBlankBeforeAndAfterClassOrFunction,
                        ("D242", "D243"),
                    ),
                    (self.__checkEricSignal, ("D260", "D261", "D262", "D263")),
                ],
                "methodDocstring": [
                    (self.__checkEricSummary, ("D232")),
                ],
                "defDocstring": [
                    (
                        self.__checkFunctionDocstring,
                        ("D102", "D202.1", "D202.2", "D203"),
                    ),
                    (self.__checkImperativeMood, ("D132",)),
                    (self.__checkNoSignature, ("D133",)),
                    (self.__checkEricReturn, ("D234r", "D235r")),
                    (self.__checkEricYield, ("D234y", "D235y")),
                    (
                        self.__checkEricFunctionArguments,
                        ("D236", "D237", "D238", "D239"),
                    ),
                    (
                        self.__checkEricNoBlankBeforeAndAfterClassOrFunction,
                        ("D244", "D245"),
                    ),
                    (self.__checkEricException, ("D250", "D251", "D252", "D253")),
                    (self.__checkEricDocumentationSequence, ("D270", "D271")),
                    (self.__checkEricDocumentationDeprecatedTags, ("D272",)),
                    (self.__checkEricDocumentationIndent, ("D273",)),
                ],
                "docstring": [
                    (self.__checkTripleDoubleQuotes, ("D111",)),
                    (self.__checkBackslashes, ("D112",)),
                    (self.__checkIndent, ("D122",)),
                    (self.__checkSummary, ("D130",)),
                    (self.__checkEricEndsWithPeriod, ("D231",)),
                    (self.__checkEricBlankAfterSummary, ("D246",)),
                    (self.__checkEricNBlankAfterLastParagraph, ("D247",)),
                    (self.__checkEricQuotesOnSeparateLines, ("D222", "D223")),
                ],
            }

        self.__checkers = {}
        for key, checkers in checkersWithCodes.items():
            for checker, codes in checkers:
                if any(not (code and self.__ignoreCode(code)) for code in codes):
                    if key not in self.__checkers:
                        self.__checkers[key] = []
                    self.__checkers[key].append(checker)

    def __ignoreCode(self, code):
        """
        Private method to check if the error code should be ignored.

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

    def __resetReadline(self):
        """
        Private method to reset the internal readline function.
        """
        self.__lineNumber = 0

    def __readline(self):
        """
        Private method to get the next line from the source.

        @return next line of source
        @rtype str
        """
        self.__lineNumber += 1
        if self.__lineNumber > len(self.__source):
            return ""
        return self.__source[self.__lineNumber - 1]

    def run(self):
        """
        Public method to check the given source for violations of doc string
        conventions.
        """
        if not self.__filename:
            # don't do anything, if essential data is missing
            return

        if not self.__checkers:
            # don't do anything, if no codes were selected
            return

        for keyword in self.__keywords:
            if keyword in self.__checkers:
                for check in self.__checkers[keyword]:
                    for context in self.__parseContexts(keyword):
                        docstring = self.__parseDocstring(context, keyword)
                        check(docstring, context)

    def __getSummaryLine(self, docstringContext):
        """
        Private method to extract the summary line.

        @param docstringContext docstring context
        @type DocStyleContext
        @return summary line (string) and the line it was found on
        @rtype int
        """
        lines = docstringContext.source()

        line = (
            lines[0]
            .replace('r"""', "", 1)
            .replace('u"""', "", 1)
            .replace('"""', "")
            .replace("r'''", "", 1)
            .replace("u'''", "", 1)
            .replace("'''", "")
            .strip()
        )

        if len(lines) == 1 or len(line) > 0:
            return line, 0
        return lines[1].strip().replace('"""', "").replace("'''", ""), 1

    def __getSummaryLines(self, docstringContext):
        """
        Private method to extract the summary lines.

        @param docstringContext docstring context
        @type DocStyleContext
        @return summary lines (list of string) and the line it was found on
        @rtype int
        """
        summaries = []
        lines = docstringContext.source()

        line0 = (
            lines[0]
            .replace('r"""', "", 1)
            .replace('u"""', "", 1)
            .replace('"""', "")
            .replace("r'''", "", 1)
            .replace("u'''", "", 1)
            .replace("'''", "")
            .strip()
        )
        line1 = (
            lines[1].strip().replace('"""', "").replace("'''", "")
            if len(lines) > 1
            else ""
        )
        line2 = (
            lines[2].strip().replace('"""', "").replace("'''", "")
            if len(lines) > 2
            else ""
        )
        if line0:
            lineno = 0
            summaries.append(line0)
            if not line0.endswith(".") and line1:
                # two line summary
                summaries.append(line1)
        elif line1:
            lineno = 1
            summaries.append(line1)
            if not line1.endswith(".") and line2:
                # two line summary
                summaries.append(line2)
        else:
            lineno = 2
            summaries.append(line2)
        return summaries, lineno

    def __getArgNames(self, node):
        """
        Private method to get the argument names of a function node.

        @param node AST node to extract arguments names from
        @type ast.AST
        @return tuple of two list of argument names, one for arguments
            and one for keyword arguments
        @rtype tuple of (list of str, list of str)
        """
        arguments = []
        arguments.extend([arg.arg for arg in node.args.args])
        if node.args.vararg is not None:
            arguments.append(node.args.vararg.arg)

        kwarguments = []
        kwarguments.extend([arg.arg for arg in node.args.kwonlyargs])
        if node.args.kwarg is not None:
            kwarguments.append(node.args.kwarg.arg)
        return arguments, kwarguments

    ##################################################################
    ## Parsing functionality below
    ##################################################################

    def __parseModuleDocstring(self, source):
        """
        Private method to extract a docstring given a module source.

        @param source source to parse
        @type list of str
        @return context of extracted docstring
        @rtype DocStyleContext
        """
        for kind, value, (line, _char), _, _ in tokenize.generate_tokens(
            StringIO("".join(source)).readline
        ):
            if kind in [tokenize.COMMENT, tokenize.NEWLINE, tokenize.NL]:
                continue
            elif kind == tokenize.STRING:  # first STRING should be docstring
                return DocStyleContext(value, line - 1, "docstring")
            else:
                return None

        return None

    def __parseDocstring(self, context, what=""):
        """
        Private method to extract a docstring given `def` or `class` source.

        @param context context data to get the docstring from
        @type DocStyleContext
        @param what string denoting what is being parsed
        @type str
        @return context of extracted docstring
        @rtype DocStyleContext
        """
        moduleDocstring = self.__parseModuleDocstring(context.source())
        if what.startswith("module") or context.contextType() == "module":
            return moduleDocstring
        if moduleDocstring:
            return moduleDocstring

        tokenGenerator = tokenize.generate_tokens(StringIO(context.ssource()).readline)
        with contextlib.suppress(StopIteration):
            kind = None
            while kind != tokenize.INDENT:
                kind, _, _, _, _ = next(tokenGenerator)
            kind, value, (line, char), _, _ = next(tokenGenerator)
            if kind == tokenize.STRING:  # STRING after INDENT is a docstring
                return DocStyleContext(value, context.start() + line - 1, "docstring")

        return None

    def __parseTopLevel(self, keyword):
        """
        Private method to extract top-level functions or classes.

        @param keyword keyword signaling what to extract
        @type str
        @return extracted function or class contexts
        @rtype list of DocStyleContext
        """
        self.__resetReadline()
        tokenGenerator = tokenize.generate_tokens(self.__readline)
        kind, value, char = None, None, None
        contexts = []
        try:
            while True:
                start, end = None, None
                while not (kind == tokenize.NAME and value == keyword and char == 0):
                    kind, value, (line, char), _, _ = next(tokenGenerator)
                start = line - 1, char
                while not (kind == tokenize.DEDENT and value == "" and char == 0):
                    kind, value, (line, char), _, _ = next(tokenGenerator)
                end = line - 1, char
                contexts.append(
                    DocStyleContext(self.__source[start[0] : end[0]], start[0], keyword)
                )
        except StopIteration:
            return contexts

    def __parseFunctions(self):
        """
        Private method to extract top-level functions.

        @return extracted function contexts
        @rtype list of DocStyleContext
        """
        if not self.__functionsCache:
            self.__functionsCache = self.__parseTopLevel("def")
        return self.__functionsCache

    def __parseClasses(self):
        """
        Private method to extract top-level classes.

        @return extracted class contexts
        @rtype list of DocStyleContext
        """
        if not self.__classesCache:
            self.__classesCache = self.__parseTopLevel("class")
        return self.__classesCache

    def __skipIndentedBlock(self, tokenGenerator):
        """
        Private method to skip over an indented block of source code.

        @param tokenGenerator token generator
        @type str iterator
        @return last token of the indented block
        @rtype tuple
        """
        kind, value, start, end, raw = next(tokenGenerator)
        while kind != tokenize.INDENT:
            kind, value, start, end, raw = next(tokenGenerator)
        indent = 1
        for kind, value, start, end, raw in tokenGenerator:
            if kind == tokenize.INDENT:
                indent += 1
            elif kind == tokenize.DEDENT:
                indent -= 1
            if indent == 0:
                return kind, value, start, end, raw

        return None

    def __parseMethods(self):
        """
        Private method to extract methods of all classes.

        @return extracted method contexts
        @rtype list of DocStyleContext
        """
        if not self.__methodsCache:
            contexts = []
            for classContext in self.__parseClasses():
                tokenGenerator = tokenize.generate_tokens(
                    StringIO(classContext.ssource()).readline
                )
                kind, value, char = None, None, None
                with contextlib.suppress(StopIteration):
                    while True:
                        start, end = None, None
                        while not (kind == tokenize.NAME and value == "def"):
                            kind, value, (line, char), _, _ = next(tokenGenerator)
                        start = line - 1, char
                        kind, value, (line, char), _, _ = self.__skipIndentedBlock(
                            tokenGenerator
                        )
                        end = line - 1, char
                        startLine = classContext.start() + start[0]
                        endLine = classContext.start() + end[0]
                        context = DocStyleContext(
                            self.__source[startLine:endLine], startLine, "def"
                        )
                        if startLine > 0:
                            if self.__source[startLine - 1].strip() == "@staticmethod":
                                context.setSpecial("staticmethod")
                            elif self.__source[startLine - 1].strip() == "@classmethod":
                                context.setSpecial("classmethod")
                        contexts.append(context)
            self.__methodsCache = contexts

        return self.__methodsCache

    def __parseContexts(self, kind):
        """
        Private method to extract a context from the source.

        @param kind kind of context to extract
        @type str
        @return requested contexts
        @rtype list of DocStyleContext
        """
        if kind == "moduleDocstring":
            return [DocStyleContext(self.__source, 0, "module")]
        if kind == "functionDocstring":
            return self.__parseFunctions()
        if kind == "classDocstring":
            return self.__parseClasses()
        if kind == "methodDocstring":
            return self.__parseMethods()
        if kind == "defDocstring":
            return self.__parseFunctions() + self.__parseMethods()
        if kind == "docstring":
            return (
                [DocStyleContext(self.__source, 0, "module")]
                + self.__parseFunctions()
                + self.__parseClasses()
                + self.__parseMethods()
            )
        return []  # fall back

    ##################################################################
    ## Checking functionality below (PEP-257)
    ##################################################################

    def __checkModulesDocstrings(self, docstringContext, context):
        """
        Private method to check, if the module has a docstring.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            self.__error(context.start(), 0, "D101")
            return

        docstring = docstringContext.ssource()
        if not docstring or not docstring.strip() or not docstring.strip("'\""):
            self.__error(context.start(), 0, "D101")

        if (
            self.__docType == "eric"
            and docstring.strip("'\"").strip() == "Module documentation goes here."
        ):
            self.__error(docstringContext.end(), 0, "D201")
            return

    def __checkFunctionDocstring(self, docstringContext, context):
        """
        Private method to check, that all public functions and methods
        have a docstring.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        functionName = context.source()[0].lstrip().split()[1].split("(")[0]
        if functionName.startswith("_") and not functionName.endswith("__"):
            if self.__docType == "eric":
                code = "D203"
            else:
                code = "D103"
        else:
            code = "D102"

        if docstringContext is None:
            self.__error(context.start(), 0, code)
            return

        docstring = docstringContext.ssource()
        if not docstring or not docstring.strip() or not docstring.strip("'\""):
            self.__error(context.start(), 0, code)

        if self.__docType == "eric":
            if docstring.strip("'\"").strip() == "Function documentation goes here.":
                self.__error(docstringContext.end(), 0, "D202.1")
                return

            if "DESCRIPTION" in docstring or "TYPE" in docstring:
                self.__error(docstringContext.end(), 0, "D202.2")
                return

    def __checkClassDocstring(self, docstringContext, context):
        """
        Private method to check, that all public functions and methods
        have a docstring.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        className = context.source()[0].lstrip().split()[1].split("(")[0]
        if className.startswith("_"):
            if self.__docType == "eric":
                code = "D205"
            else:
                code = "D105"
        else:
            code = "D104"

        if docstringContext is None:
            self.__error(context.start(), 0, code)
            return

        docstring = docstringContext.ssource()
        if not docstring or not docstring.strip() or not docstring.strip("'\""):
            self.__error(context.start(), 0, code)
            return

        if (
            self.__docType == "eric"
            and docstring.strip("'\"").strip() == "Class documentation goes here."
        ):
            self.__error(docstringContext.end(), 0, "D206")
            return

    def __checkTripleDoubleQuotes(self, docstringContext, _context):
        """
        Private method to check, that all docstrings are surrounded
        by triple double quotes.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        docstring = docstringContext.ssource().strip()
        if not docstring.startswith(('"""', 'r"""', 'u"""')):
            self.__error(docstringContext.start(), 0, "D111")

    def __checkBackslashes(self, docstringContext, _context):
        """
        Private method to check, that all docstrings containing
        backslashes are surrounded by raw triple double quotes.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        docstring = docstringContext.ssource().strip()
        if "\\" in docstring and not docstring.startswith('r"""'):
            self.__error(docstringContext.start(), 0, "D112")

    def __checkOneLiner(self, docstringContext, context):
        """
        Private method to check, that one-liner docstrings fit on
        one line with quotes.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        lines = docstringContext.source()
        if len(lines) > 1:
            nonEmptyLines = [line for line in lines if line.strip().strip("'\"")]
            if len(nonEmptyLines) == 1:
                modLen = len(
                    context.indent() + '"""' + nonEmptyLines[0].strip() + '"""'
                )
                if context.contextType() != "module":
                    modLen += 4
                if not nonEmptyLines[0].strip().endswith("."):
                    # account for a trailing dot
                    modLen += 1
                if modLen <= self.__maxLineLength:
                    self.__error(docstringContext.start(), 0, "D121")

    def __checkIndent(self, docstringContext, context):
        """
        Private method to check, that docstrings are properly indented.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        lines = docstringContext.source()
        if len(lines) == 1:
            return

        nonEmptyLines = [line.rstrip() for line in lines[1:] if line.strip()]
        if not nonEmptyLines:
            return

        indent = min(len(line) - len(line.strip()) for line in nonEmptyLines)
        expectedIndent = (
            0 if context.contextType() == "module" else len(context.indent()) + 4
        )
        if indent != expectedIndent:
            self.__error(docstringContext.start(), 0, "D122")

    def __checkSummary(self, docstringContext, _context):
        """
        Private method to check, that docstring summaries contain some text.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        summary, lineNumber = self.__getSummaryLine(docstringContext)
        if summary == "":
            self.__error(docstringContext.start() + lineNumber, 0, "D130")

    def __checkEndsWithPeriod(self, docstringContext, _context):
        """
        Private method to check, that docstring summaries end with a period.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        summary, lineNumber = self.__getSummaryLine(docstringContext)
        if not summary.endswith("."):
            self.__error(docstringContext.start() + lineNumber, 0, "D131")

    def __checkImperativeMood(self, docstringContext, _context):
        """
        Private method to check, that docstring summaries are in
        imperative mood.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        summary, lineNumber = self.__getSummaryLine(docstringContext)
        if summary:
            firstWord = summary.strip().split()[0]
            if firstWord.endswith("s") and not firstWord.endswith("ss"):
                self.__error(docstringContext.start() + lineNumber, 0, "D132")

    def __checkNoSignature(self, docstringContext, context):
        """
        Private method to check, that docstring summaries don't repeat
        the function's signature.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        functionName = context.source()[0].lstrip().split()[1].split("(")[0]
        summary, lineNumber = self.__getSummaryLine(docstringContext)
        if functionName + "(" in summary.replace(
            " ", ""
        ) and functionName + "()" not in summary.replace(" ", ""):
            # report only, if it is not an abbreviated form (i.e. function() )
            self.__error(docstringContext.start() + lineNumber, 0, "D133")

    def __checkReturnType(self, docstringContext, context):
        """
        Private method to check, that docstrings mention the return value type.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        if "return" not in docstringContext.ssource().lower():
            tokens = list(
                tokenize.generate_tokens(StringIO(context.ssource()).readline)
            )
            return_ = [
                tokens[i + 1][0]
                for i, token in enumerate(tokens)
                if token[1] == "return"
            ]
            if (
                set(return_) - {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE}
                != set()
            ):
                self.__error(docstringContext.end(), 0, "D134")

    def __checkNoBlankLineBefore(self, docstringContext, context):
        """
        Private method to check, that function/method docstrings are not
        preceded by a blank line.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        contextLines = context.source()
        cti = 0
        while cti < len(contextLines) and not contextLines[cti].strip().startswith(
            ('"""', 'r"""', 'u"""', "'''", "r'''", "u'''")
        ):
            cti += 1
        if cti == len(contextLines):
            return

        if not contextLines[cti - 1].strip():
            self.__error(docstringContext.start(), 0, "D141")

    def __checkBlankBeforeAndAfterClass(self, docstringContext, context):
        """
        Private method to check, that class docstrings have one
        blank line around them.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        contextLines = context.source()
        cti = 0
        while cti < len(contextLines) and not contextLines[cti].strip().startswith(
            ('"""', 'r"""', 'u"""', "'''", "r'''", "u'''")
        ):
            cti += 1
        if cti == len(contextLines):
            return

        start = cti
        if contextLines[cti].strip() in ('"""', 'r"""', 'u"""', "'''", "r'''", "u'''"):
            # it is a multi line docstring
            cti += 1

        while cti < len(contextLines) and not contextLines[cti].strip().endswith(
            ('"""', "'''")
        ):
            cti += 1
        end = cti
        if cti >= len(contextLines) - 1:
            return

        if contextLines[start - 1].strip():
            self.__error(docstringContext.start(), 0, "D142")
        if contextLines[end + 1].strip():
            self.__error(docstringContext.end(), 0, "D143")

    def __checkBlankAfterSummary(self, docstringContext, _context):
        """
        Private method to check, that docstring summaries are followed
        by a blank line.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        docstrings = docstringContext.source()
        if len(docstrings) <= 3:
            # correct/invalid one-liner
            return

        summary, lineNumber = self.__getSummaryLine(docstringContext)
        if len(docstrings) > 2 and docstrings[lineNumber + 1].strip():
            self.__error(docstringContext.start() + lineNumber, 0, "D144")

    def __checkBlankAfterLastParagraph(self, docstringContext, _context):
        """
        Private method to check, that the last paragraph of docstrings is
        followed by a blank line.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        docstrings = docstringContext.source()
        if len(docstrings) <= 3:
            # correct/invalid one-liner
            return

        if docstrings[-2].strip():
            self.__error(docstringContext.end(), 0, "D145")

    ##################################################################
    ## Checking functionality below (eric specific ones)
    ##################################################################

    def __checkEricQuotesOnSeparateLines(self, docstringContext, _context):
        """
        Private method to check, that leading and trailing quotes are on
        a line by themselves.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        lines = docstringContext.source()
        if lines[0].strip().strip("ru\"'"):
            self.__error(docstringContext.start(), 0, "D221")
        if lines[-1].strip().strip("\"'"):
            self.__error(docstringContext.end(), 0, "D222")

    def __checkEricEndsWithPeriod(self, docstringContext, _context):
        """
        Private method to check, that docstring summaries end with a period.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        summaryLines, lineNumber = self.__getSummaryLines(docstringContext)
        if summaryLines:
            if summaryLines[-1].lstrip().startswith("@"):
                summaryLines.pop(-1)
            summary = " ".join([s.strip() for s in summaryLines if s])
            if (
                summary
                and not summary.endswith(".")
                and summary.split(None, 1)[0].lower() != "constructor"
            ):
                self.__error(
                    docstringContext.start() + lineNumber + len(summaryLines) - 1,
                    0,
                    "D231",
                )

    def __checkEricReturn(self, docstringContext, context):
        """
        Private method to check, that docstrings contain an &#64;return line
        if they return anything and don't otherwise.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        tokens = list(tokenize.generate_tokens(StringIO(context.ssource()).readline))
        return_ = [
            tokens[i + 1][0] for i, token in enumerate(tokens) if token[1] == "return"
        ]
        if "@return" not in docstringContext.ssource():
            if (
                set(return_) - {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE}
                != set()
            ):
                self.__error(docstringContext.end(), 0, "D234r")
        else:
            if (
                set(return_) - {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE}
                == set()
            ):
                self.__error(docstringContext.end(), 0, "D235r")

    def __checkEricYield(self, docstringContext, context):
        """
        Private method to check, that docstrings contain an &#64;yield line
        if they return anything and don't otherwise.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        tokens = list(tokenize.generate_tokens(StringIO(context.ssource()).readline))
        yield_ = [
            tokens[i + 1][0] for i, token in enumerate(tokens) if token[1] == "yield"
        ]
        if "@yield" not in docstringContext.ssource():
            if set(yield_) - {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE} != set():
                self.__error(docstringContext.end(), 0, "D234y")
        else:
            if set(yield_) - {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE} == set():
                self.__error(docstringContext.end(), 0, "D235y")

    def __checkEricFunctionArguments(self, docstringContext, context):
        """
        Private method to check, that docstrings contain an &#64;param and/or
        &#64;keyparam line for each argument.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        try:
            tree = ast.parse(context.ssource())
        except (SyntaxError, TypeError):
            return
        if (
            isinstance(tree, ast.Module)
            and len(tree.body) == 1
            and isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef))
        ):
            functionDef = tree.body[0]
            argNames, kwNames = self.__getArgNames(functionDef)
            if "self" in argNames:
                argNames.remove("self")
            if "cls" in argNames:
                argNames.remove("cls")

            tagstring = "".join(
                line.lstrip()
                for line in docstringContext.source()
                if line.lstrip().startswith("@")
            )
            if tagstring.count("@param") + tagstring.count("@keyparam") < len(
                argNames + kwNames
            ):
                self.__error(docstringContext.end(), 0, "D236")
            elif tagstring.count("@param") + tagstring.count("@keyparam") > len(
                argNames + kwNames
            ):
                self.__error(docstringContext.end(), 0, "D237")
            else:
                # extract @param and @keyparam from docstring
                args = []
                kwargs = []
                for line in docstringContext.source():
                    if line.strip().startswith(("@param", "@keyparam")):
                        paramParts = line.strip().split(None, 2)
                        if len(paramParts) >= 2:
                            at, name = paramParts[:2]
                            if at == "@keyparam":
                                kwargs.append(name.lstrip("*"))
                            args.append(name.lstrip("*"))

                # do the checks
                for name in kwNames:
                    if name not in kwargs:
                        self.__error(docstringContext.end(), 0, "D238")
                        return
                if argNames + kwNames != args:
                    self.__error(docstringContext.end(), 0, "D239")

    def __checkEricException(self, docstringContext, context):
        """
        Private method to check, that docstrings contain an &#64;exception line
        if they raise an exception and don't otherwise.

        Note: This method also checks the raised and documented exceptions for
        completeness (i.e. raised exceptions that are not documented or
        documented exceptions that are not raised)

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        tokens = list(tokenize.generate_tokens(StringIO(context.ssource()).readline))
        exceptions = set()
        raisedExceptions = set()
        tokensLen = len(tokens)
        for i, token in enumerate(tokens):
            if token[1] == "raise":
                exceptions.add(tokens[i + 1][0])
                if tokens[i + 1][0] == tokenize.NAME:
                    if tokensLen > (i + 2) and tokens[i + 2][1] == ".":
                        raisedExceptions.add(
                            "{0}.{1}".format(tokens[i + 1][1], tokens[i + 3][1])
                        )
                    else:
                        raisedExceptions.add(tokens[i + 1][1])

        if (
            "@exception" not in docstringContext.ssource()
            and "@throws" not in docstringContext.ssource()
            and "@raise" not in docstringContext.ssource()
        ):
            if exceptions - {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE} != set():
                self.__error(docstringContext.end(), 0, "D250")
        else:
            if exceptions - {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE} == set():
                self.__error(docstringContext.end(), 0, "D251")
            else:
                # step 1: extract documented exceptions
                documentedExceptions = set()
                for line in docstringContext.source():
                    line = line.strip()
                    if line.startswith(("@exception", "@throws", "@raise")):
                        exceptionTokens = line.split(None, 2)
                        if len(exceptionTokens) >= 2:
                            documentedExceptions.add(exceptionTokens[1])

                # step 2: report undocumented exceptions
                for exception in raisedExceptions:
                    if exception not in documentedExceptions:
                        self.__error(docstringContext.end(), 0, "D252", exception)

                # step 3: report undefined signals
                for exception in documentedExceptions:
                    if exception not in raisedExceptions:
                        self.__error(docstringContext.end(), 0, "D253", exception)

    def __checkEricSignal(self, docstringContext, context):
        """
        Private method to check, that docstrings contain an &#64;signal line
        if they define signals and don't otherwise.

        Note: This method also checks the defined and documented signals for
        completeness (i.e. defined signals that are not documented or
        documented signals that are not defined)

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        tokens = list(tokenize.generate_tokens(StringIO(context.ssource()).readline))
        definedSignals = set()
        for i, token in enumerate(tokens):
            if token[1] in ("pyqtSignal", "Signal"):
                if tokens[i - 1][1] == "." and tokens[i - 2][1] == "QtCore":
                    definedSignals.add(tokens[i - 4][1])
                elif tokens[i - 1][1] == "=":
                    definedSignals.add(tokens[i - 2][1])

        if "@signal" not in docstringContext.ssource() and definedSignals:
            self.__error(docstringContext.end(), 0, "D260")
        elif "@signal" in docstringContext.ssource():
            if not definedSignals:
                self.__error(docstringContext.end(), 0, "D261")
            else:
                # step 1: extract documented signals
                documentedSignals = set()
                for line in docstringContext.source():
                    line = line.strip()
                    if line.startswith("@signal"):
                        signalTokens = line.split(None, 2)
                        if len(signalTokens) >= 2:
                            signal = signalTokens[1]
                            if "(" in signal:
                                signal = signal.split("(", 1)[0]
                            documentedSignals.add(signal)

                # step 2: report undocumented signals
                for signal in definedSignals:
                    if signal not in documentedSignals:
                        self.__error(docstringContext.end(), 0, "D262", signal)

                # step 3: report undefined signals
                for signal in documentedSignals:
                    if signal not in definedSignals:
                        self.__error(docstringContext.end(), 0, "D263", signal)

    def __checkEricBlankAfterSummary(self, docstringContext, _context):
        """
        Private method to check, that docstring summaries are followed
        by a blank line.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        docstrings = docstringContext.source()
        if len(docstrings) <= 3:
            # correct/invalid one-liner
            return

        summaryLines, lineNumber = self.__getSummaryLines(docstringContext)
        if (
            len(docstrings) - 2 > lineNumber + len(summaryLines) - 1
            and docstrings[lineNumber + len(summaryLines)].strip()
        ):
            self.__error(docstringContext.start() + lineNumber, 0, "D246")

    def __checkEricNoBlankBeforeAndAfterClassOrFunction(
        self, docstringContext, context
    ):
        """
        Private method to check, that class and function/method docstrings
        have no blank line around them.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        contextLines = context.source()
        isClassContext = contextLines[0].lstrip().startswith("class ")
        cti = 0
        while cti < len(contextLines) and not contextLines[cti].strip().startswith(
            ('"""', 'r"""', 'u"""', "'''", "r'''", "u'''")
        ):
            cti += 1
        if cti == len(contextLines):
            return

        start = cti
        if contextLines[cti].strip() in ('"""', 'r"""', 'u"""', "'''", "r'''", "u'''"):
            # it is a multi line docstring
            cti += 1

        while cti < len(contextLines) and not contextLines[cti].strip().endswith(
            ('"""', "'''")
        ):
            cti += 1
        end = cti
        if cti >= len(contextLines) - 1:
            return

        if isClassContext:
            if not contextLines[start - 1].strip():
                self.__error(docstringContext.start(), 0, "D242")
            if not contextLines[end + 1].strip() and self.__docType == "eric":
                self.__error(docstringContext.end(), 0, "D243")
            elif contextLines[end + 1].strip() and self.__docType == "eric_black":
                self.__error(docstringContext.end(), 0, "D143")
        else:
            if not contextLines[start - 1].strip():
                self.__error(docstringContext.start(), 0, "D244")
            if not contextLines[end + 1].strip():
                if (
                    self.__docType == "eric_black"
                    and len(contextLines) > end + 2
                    and contextLines[end + 2].strip().startswith("def ")
                ):
                    return

                self.__error(docstringContext.end(), 0, "D245")

    def __checkEricNBlankAfterLastParagraph(self, docstringContext, _context):
        """
        Private method to check, that the last paragraph of docstrings is
        not followed by a blank line.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        docstrings = docstringContext.source()
        if len(docstrings) <= 3:
            # correct/invalid one-liner
            return

        if not docstrings[-2].strip():
            self.__error(docstringContext.end(), 0, "D247")

    def __checkEricSummary(self, docstringContext, context):
        """
        Private method to check, that method docstring summaries start with
        specific words.

        @param docstringContext docstring context
        @type DocStyleContext
        @param context context of the docstring
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        summary, lineNumber = self.__getSummaryLine(docstringContext)
        if summary:
            # check, if the first word is 'Constructor', 'Public',
            # 'Protected' or 'Private'
            functionName, arguments = (
                context.source()[0].lstrip().split()[1].split("(", 1)
            )
            firstWord = summary.strip().split(None, 1)[0].lower()
            if functionName == "__init__":
                if firstWord != "constructor":
                    self.__error(
                        docstringContext.start() + lineNumber, 0, "D232", "constructor"
                    )
            elif functionName.startswith("__") and functionName.endswith("__"):
                if firstWord != "special":
                    self.__error(
                        docstringContext.start() + lineNumber, 0, "D232", "special"
                    )
            elif context.special() == "staticmethod":
                secondWord = summary.strip().split(None, 2)[1].lower()
                if firstWord != "static" and secondWord != "static":
                    self.__error(
                        docstringContext.start() + lineNumber, 0, "D232", "static"
                    )
                elif secondWord == "static":
                    if functionName.startswith(("__", "on_")):
                        if firstWord != "private":
                            self.__error(
                                docstringContext.start() + lineNumber,
                                0,
                                "D232",
                                "private static",
                            )
                    elif functionName.startswith("_") or functionName.endswith("Event"):
                        if firstWord != "protected":
                            self.__error(
                                docstringContext.start() + lineNumber,
                                0,
                                "D232",
                                "protected static",
                            )
                    else:
                        if firstWord != "public":
                            self.__error(
                                docstringContext.start() + lineNumber,
                                0,
                                "D232",
                                "public static",
                            )
            elif (
                arguments.startswith(("cls,", "cls)"))
                or context.special() == "classmethod"
            ):
                secondWord = summary.strip().split(None, 2)[1].lower()
                if firstWord != "class" and secondWord != "class":
                    self.__error(
                        docstringContext.start() + lineNumber, 0, "D232", "class"
                    )
                elif secondWord == "class":
                    if functionName.startswith(("__", "on_")):
                        if firstWord != "private":
                            self.__error(
                                docstringContext.start() + lineNumber,
                                0,
                                "D232",
                                "private class",
                            )
                    elif functionName.startswith("_") or functionName.endswith("Event"):
                        if firstWord != "protected":
                            self.__error(
                                docstringContext.start() + lineNumber,
                                0,
                                "D232",
                                "protected class",
                            )
                    else:
                        if firstWord != "public":
                            self.__error(
                                docstringContext.start() + lineNumber,
                                0,
                                "D232",
                                "public class",
                            )
            elif functionName.startswith(("__", "on_")):
                if firstWord != "private":
                    self.__error(
                        docstringContext.start() + lineNumber, 0, "D232", "private"
                    )
            elif functionName.startswith("_") or functionName.endswith("Event"):
                if firstWord != "protected":
                    self.__error(
                        docstringContext.start() + lineNumber, 0, "D232", "protected"
                    )
            else:
                if firstWord != "public":
                    self.__error(
                        docstringContext.start() + lineNumber, 0, "D232", "public"
                    )

    def __checkEricDocumentationSequence(
        self,
        docstringContext,
        _context,
    ):
        """
        Private method to check, that method docstring follows the correct sequence
        of entries (e.g. @param is followed by @type).

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        docTokens = []
        lines = docstringContext.source()
        for lineno, line in enumerate(lines):
            strippedLine = line.lstrip()
            if strippedLine.startswith("@"):
                docToken = strippedLine.split(None, 1)[0]
                docTokens.append((docToken, lineno))

                # check, that a type tag is not preceded by an empty line
                if (
                    docToken in ("@type", "@rtype", "@ytype")
                    and lineno > 0
                    and lines[lineno - 1].strip() == ""
                ):
                    self.__error(docstringContext.start() + lineno, 0, "D271", docToken)

        # check the correct sequence of @param/@return/@yield and their accompanying
        # type tag
        for index in range(len(docTokens)):
            docToken, lineno = docTokens[index]
            try:
                docToken2, _ = docTokens[index + 1]
            except IndexError:
                docToken2 = ""

            if docToken in ("@param", "@keyparam") and docToken2 != "@type":
                self.__error(
                    docstringContext.start() + lineno, 0, "D270", docToken, "@type"
                )
            elif docToken == "@return" and docToken2 != "@rtype":
                self.__error(
                    docstringContext.start() + lineno, 0, "D270", docToken, "@rtype"
                )
            elif docToken == "@yield" and docToken2 != "@ytype":
                self.__error(
                    docstringContext.start() + lineno, 0, "D270", docToken, "@ytype"
                )

    def __checkEricDocumentationDeprecatedTags(
        self,
        docstringContext,
        _context,
    ):
        """
        Private method to check the use of deprecated documentation tags.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None:
            return

        deprecationsList = {
            # key is deprecated tag, value is the tag to be used
            "@ireturn": "@return",
            "@ptype": "@type",
            "@raise": "@exception",
            "@throws": "@exception",
        }

        for lineno, line in enumerate(docstringContext.source()):
            strippedLine = line.lstrip()
            if strippedLine.startswith("@"):
                # it is a tag line
                tag = strippedLine.split(None, 1)[0]
                with contextlib.suppress(KeyError):
                    self.__error(
                        docstringContext.start() + lineno,
                        0,
                        "D272",
                        tag,
                        deprecationsList[tag],
                    )

    def __checkEricDocumentationIndent(
        self,
        docstringContext,
        _context,
    ):
        """
        Private method to check the the correct indentation of the tag lines.

        @param docstringContext docstring context
        @type DocStyleContext
        @param _context context of the docstring (unused)
        @type DocStyleContext
        """
        if docstringContext is None or not docstringContext.source():
            return

        lines = docstringContext.source()
        for line in lines[1:]:
            if line.strip():
                indentationLength = len(line) - len(line.lstrip())
                break
        else:
            # only empty lines except the first one
            return

        for lineno, line in enumerate(lines):
            strippedLine = line.lstrip()
            if strippedLine.startswith("@"):
                tag = strippedLine.split(None, 1)[0]
                currentIndentation = len(line) - len(strippedLine)
                if currentIndentation != indentationLength:
                    self.__error(docstringContext.start() + lineno, 0, "D273", tag)
