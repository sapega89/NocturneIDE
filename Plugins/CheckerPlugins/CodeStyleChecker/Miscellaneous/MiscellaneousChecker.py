# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a checker for miscellaneous checks.
"""

import ast
import builtins
import contextlib
import copy
import itertools
import math
import re
import sys
import tokenize

from collections import defaultdict, namedtuple
from dataclasses import dataclass
from keyword import iskeyword
from string import Formatter

try:
    # Python 3.10+
    from itertools import pairwise
except ImportError:
    # replacement for Python < 3.10
    from itertools import tee

    def pairwise(iterable):
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)


import AstUtilities

from .eradicate import Eradicator
from .MiscellaneousDefaults import MiscellaneousCheckerDefaultArgs

BugbearMutableLiterals = ("Dict", "List", "Set")
BugbearMutableComprehensions = ("ListComp", "DictComp", "SetComp")
BugbearMutableCalls = (
    "Counter",
    "OrderedDict",
    "collections.Counter",
    "collections.OrderedDict",
    "collections.defaultdict",
    "collections.deque",
    "defaultdict",
    "deque",
    "dict",
    "list",
    "set",
)
BugbearImmutableCalls = (
    "tuple",
    "frozenset",
    "types.MappingProxyType",
    "MappingProxyType",
    "re.compile",
    "operator.attrgetter",
    "operator.itemgetter",
    "operator.methodcaller",
    "attrgetter",
    "itemgetter",
    "methodcaller",
)


def composeCallPath(node):
    """
    Generator function to assemble the call path of a given node.

    @param node node to assemble call path for
    @type ast.Node
    @yield call path components
    @ytype str
    """
    if isinstance(node, ast.Attribute):
        yield from composeCallPath(node.value)
        yield node.attr
    elif isinstance(node, ast.Call):
        yield from composeCallPath(node.func)
    elif isinstance(node, ast.Name):
        yield node.id


class MiscellaneousChecker:
    """
    Class implementing a checker for miscellaneous checks.
    """

    Codes = [
        ## Coding line
        "M101",
        "M102",
        ## Copyright
        "M111",
        "M112",
        ## Shadowed Builtins
        "M131",
        "M132",
        ## Comprehensions
        "M180",
        "M181",
        "M182",
        "M183",
        "M184",
        "M185",
        "M186",
        "M188",
        "M189",
        "M189a",
        "M189b",
        "M190",
        "M190a",
        "M190b",
        "M191",
        "M193",
        "M193a",
        "M193b",
        "M193c",
        "M194",
        "M195",
        "M196",
        "M197",
        "M198",
        "M199",
        "M200",
        ## Dictionaries with sorted keys
        "M251",
        ## Property
        "M260",
        "M261",
        "M262",
        "M263",
        "M264",
        "M265",
        "M266",
        "M267",
        ## Naive datetime usage
        "M301",
        "M302",
        "M303",
        "M304",
        "M305",
        "M306",
        "M307",
        "M308",
        "M311",
        "M312",
        "M313",
        "M314",
        "M315",
        "M321",
        ## sys.version and sys.version_info usage
        "M401",
        "M402",
        "M403",
        "M411",
        "M412",
        "M413",
        "M414",
        "M421",
        "M422",
        "M423",
        ## Bugbear
        "M501",
        "M502",
        "M503",
        "M504",
        "M505",
        "M506",
        "M507",
        "M508",
        "M509",
        "M510",
        "M511",
        "M512",
        "M513",
        "M514",
        "M515",
        "M516",
        "M517",
        "M518",
        "M519",
        "M520",
        "M521",
        "M522",
        "M523",
        "M524",
        "M525",
        "M526",
        "M527",
        "M528",
        "M529",
        "M530",
        "M531",
        "M532",
        "M533",
        "M534",
        "M535",
        "M536",
        "M537",
        "M539",
        "M540",
        ## Bugbear, opininonated
        "M569",
        ## Bugbear++
        "M581",
        "M582",
        ## Format Strings
        "M601",
        "M611",
        "M612",
        "M613",
        "M621",
        "M622",
        "M623",
        "M624",
        "M625",
        "M631",
        "M632",
        ## Future statements
        "M701",
        "M702",
        ## Gettext
        "M711",
        ## print() statements
        "M801",
        ## one element tuple
        "M811",
        ## return statements
        "M831",
        "M832",
        "M833",
        "M834",
        ## line continuation
        "M841",
        ## implicitly concatenated strings
        "M851",
        "M852",
        "M853",
        ## commented code
        "M891",
    ]

    Formatter = Formatter()
    FormatFieldRegex = re.compile(r"^((?:\s|.)*?)(\..*|\[.*\])?$")

    BuiltinsWhiteList = [
        "__name__",
        "__doc__",
        "credits",
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
        @param args dictionary of arguments for the miscellaneous checks
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

        linesIterator = iter(self.__source)
        self.__tokens = list(tokenize.generate_tokens(lambda: next(linesIterator)))

        self.__pep3101FormatRegex = re.compile(
            r'^(?:[^\'"]*[\'"][^\'"]*[\'"])*\s*%|^\s*%'
        )

        self.__builtins = [b for b in dir(builtins) if b not in self.BuiltinsWhiteList]

        self.__eradicator = Eradicator()

        # statistics counters
        self.counters = {}

        # collection of detected errors
        self.errors = []

        checkersWithCodes = [
            (self.__checkCoding, ("M101", "M102")),
            (self.__checkCopyright, ("M111", "M112")),
            (self.__checkBuiltins, ("M131", "M132")),
            (
                self.__checkComprehensions,
                (
                    "M180",
                    "M181",
                    "M182",
                    "M183",
                    "M184",
                    "M185",
                    "M186",
                    "M188",
                    "M189",
                    "M189a",
                    "M189b",
                    "M190",
                    "M190a",
                    "M190b",
                    "M191",
                    "M193",
                    "M193a",
                    "M193b",
                    "M193c",
                    "M194",
                    "M195",
                    "M196",
                    "M197",
                    "M198",
                    "M199",
                    "M200",
                ),
            ),
            (self.__checkDictWithSortedKeys, ("M251",)),
            (
                self.__checkProperties,
                ("M260", "M261", "M262", "M263", "M264", "M265", "M266", "M267"),
            ),
            (
                self.__checkDateTime,
                (
                    "M301",
                    "M302",
                    "M303",
                    "M304",
                    "M305",
                    "M306",
                    "M307",
                    "M308",
                    "M311",
                    "M312",
                    "M313",
                    "M314",
                    "M315",
                    "M321",
                ),
            ),
            (
                self.__checkSysVersion,
                (
                    "M401",
                    "M402",
                    "M403",
                    "M411",
                    "M412",
                    "M413",
                    "M414",
                    "M421",
                    "M422",
                    "M423",
                ),
            ),
            (
                self.__checkBugBear,
                (
                    "M501",
                    "M502",
                    "M503",
                    "M504",
                    "M505",
                    "M506",
                    "M507",
                    "M508",
                    "M509",
                    "M510",
                    "M511",
                    "M512",
                    "M513",
                    "M514",
                    "M515",
                    "M516",
                    "M517",
                    "M518",
                    "M519",
                    "M520",
                    "M521",
                    "M522",
                    "M523",
                    "M524",
                    "M525",
                    "M526",
                    "M527",
                    "M528",
                    "M529",
                    "M530",
                    "M531",
                    "M532",
                    "M533",
                    "M534",
                    "M535",
                    "M536",
                    "M537",
                    "M539",
                    "M540",
                    "M569",
                    "M581",
                    "M582",
                ),
            ),
            (self.__checkPep3101, ("M601",)),
            (
                self.__checkFormatString,
                (
                    "M611",
                    "M612",
                    "M613",
                    "M621",
                    "M622",
                    "M623",
                    "M624",
                    "M625",
                    "M631",
                    "M632",
                ),
            ),
            (self.__checkFuture, ("M701", "M702")),
            (self.__checkGettext, ("M711",)),
            (self.__checkPrintStatements, ("M801",)),
            (self.__checkTuple, ("M811",)),
            (self.__checkReturn, ("M831", "M832", "M833", "M834")),
            (self.__checkLineContinuation, ("M841",)),
            (self.__checkImplicitStringConcat, ("M851", "M852")),
            (self.__checkExplicitStringConcat, ("M853",)),
            (self.__checkCommentedCode, ("M891",)),
        ]

        # the eradicate whitelist
        commentedCodeCheckerArgs = self.__args.get(
            "CommentedCodeChecker",
            MiscellaneousCheckerDefaultArgs["CommentedCodeChecker"],
        )
        commentedCodeCheckerWhitelist = commentedCodeCheckerArgs.get(
            "WhiteList",
            MiscellaneousCheckerDefaultArgs["CommentedCodeChecker"]["WhiteList"],
        )
        self.__eradicator.update_whitelist(
            commentedCodeCheckerWhitelist, extend_default=False
        )

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

    def __getCoding(self):
        """
        Private method to get the defined coding of the source.

        @return tuple containing the line number and the coding
        @rtype tuple of int and str
        """
        for lineno, line in enumerate(self.__source[:5]):
            matched = re.search(r"coding[:=]\s*([-\w_.]+)", line, re.IGNORECASE)
            if matched:
                return lineno, matched.group(1)
        else:
            return 0, ""

    def __checkCoding(self):
        """
        Private method to check the presence of a coding line and valid
        encodings.
        """
        if len(self.__source) == 0:
            return

        encodings = [
            e.lower().strip()
            for e in self.__args.get(
                "CodingChecker", MiscellaneousCheckerDefaultArgs["CodingChecker"]
            ).split(",")
        ]
        lineno, coding = self.__getCoding()
        if coding:
            if coding.lower() not in encodings:
                self.__error(lineno, 0, "M102", coding)
        else:
            self.__error(0, 0, "M101")

    def __checkCopyright(self):
        """
        Private method to check the presence of a copyright statement.
        """
        source = "".join(self.__source)
        copyrightArgs = self.__args.get(
            "CopyrightChecker", MiscellaneousCheckerDefaultArgs["CopyrightChecker"]
        )
        copyrightMinFileSize = copyrightArgs.get(
            "MinFilesize",
            MiscellaneousCheckerDefaultArgs["CopyrightChecker"]["MinFilesize"],
        )
        copyrightAuthor = copyrightArgs.get(
            "Author", MiscellaneousCheckerDefaultArgs["CopyrightChecker"]["Author"]
        )
        copyrightRegexStr = (
            r"Copyright\s+(\(C\)\s+)?(\d{{4}}\s+-\s+)?\d{{4}}\s+{author}"
        )

        tocheck = max(1024, copyrightMinFileSize)
        topOfSource = source[:tocheck]
        if len(topOfSource) < copyrightMinFileSize:
            return

        copyrightRe = re.compile(copyrightRegexStr.format(author=r".*"), re.IGNORECASE)
        if not copyrightRe.search(topOfSource):
            self.__error(0, 0, "M111")
            return

        if copyrightAuthor:
            copyrightAuthorRe = re.compile(
                copyrightRegexStr.format(author=copyrightAuthor), re.IGNORECASE
            )
            if not copyrightAuthorRe.search(topOfSource):
                self.__error(0, 0, "M112")

    def __checkCommentedCode(self):
        """
        Private method to check for commented code.
        """
        source = "".join(self.__source)
        commentedCodeCheckerArgs = self.__args.get(
            "CommentedCodeChecker",
            MiscellaneousCheckerDefaultArgs["CommentedCodeChecker"],
        )
        aggressive = commentedCodeCheckerArgs.get(
            "Aggressive",
            MiscellaneousCheckerDefaultArgs["CommentedCodeChecker"]["Aggressive"],
        )
        for markedLine in self.__eradicator.commented_out_code_line_numbers(
            source, aggressive=aggressive
        ):
            self.__error(markedLine - 1, 0, "M891")

    def __checkLineContinuation(self):
        """
        Private method to check line continuation using backslash.
        """
        # generate source lines without comments
        comments = [tok for tok in self.__tokens if tok[0] == tokenize.COMMENT]
        stripped = self.__source[:]
        for comment in comments:
            lineno = comment[3][0]
            start = comment[2][1]
            stop = comment[3][1]
            content = stripped[lineno - 1]
            withoutComment = content[:start] + content[stop:]
            stripped[lineno - 1] = withoutComment.rstrip()

        # perform check with 'cleaned' source
        for lineIndex, line in enumerate(stripped):
            strippedLine = line.strip()
            if strippedLine.endswith("\\") and not strippedLine.startswith(
                ("assert", "with")
            ):
                self.__error(lineIndex, len(line), "M841")

    def __checkPrintStatements(self):
        """
        Private method to check for print statements.
        """
        for node in ast.walk(self.__tree):
            if (
                isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print"
            ) or (hasattr(ast, "Print") and isinstance(node, ast.Print)):
                self.__error(node.lineno - 1, node.col_offset, "M801")

    def __checkTuple(self):
        """
        Private method to check for one element tuples.
        """
        for node in ast.walk(self.__tree):
            if isinstance(node, ast.Tuple) and len(node.elts) == 1:
                self.__error(node.lineno - 1, node.col_offset, "M811")

    def __checkFuture(self):
        """
        Private method to check the __future__ imports.
        """
        expectedImports = {
            i.strip()
            for i in self.__args.get("FutureChecker", "").split(",")
            if bool(i.strip())
        }
        if len(expectedImports) == 0:
            # nothing to check for; disabling the check
            return

        imports = set()
        node = None
        hasCode = False

        for node in ast.walk(self.__tree):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                imports |= {name.name for name in node.names}
            elif isinstance(node, ast.Expr):
                if not AstUtilities.isString(node.value):
                    hasCode = True
                    break
            elif not (AstUtilities.isString(node) or isinstance(node, ast.Module)):
                hasCode = True
                break

        if isinstance(node, ast.Module) or not hasCode:
            return

        if imports < expectedImports:
            if imports:
                self.__error(
                    node.lineno - 1,
                    node.col_offset,
                    "M701",
                    ", ".join(expectedImports),
                    ", ".join(imports),
                )
            else:
                self.__error(
                    node.lineno - 1, node.col_offset, "M702", ", ".join(expectedImports)
                )

    def __checkPep3101(self):
        """
        Private method to check for old style string formatting.
        """
        for lineno, line in enumerate(self.__source):
            match = self.__pep3101FormatRegex.search(line)
            if match:
                lineLen = len(line)
                pos = line.find("%")
                formatPos = pos
                formatter = "%"
                if line[pos + 1] == "(":
                    pos = line.find(")", pos)
                c = line[pos]
                while c not in "diouxXeEfFgGcrs":
                    pos += 1
                    if pos >= lineLen:
                        break
                    c = line[pos]
                if c in "diouxXeEfFgGcrs":
                    formatter += c
                self.__error(lineno, formatPos, "M601", formatter)

    def __checkFormatString(self):
        """
        Private method to check string format strings.
        """
        coding = self.__getCoding()[1]
        if not coding:
            # default to utf-8
            coding = "utf-8"

        visitor = TextVisitor()
        visitor.visit(self.__tree)
        for node in visitor.nodes:
            text = node.value
            if isinstance(text, bytes):
                try:
                    text = text.decode(coding)
                except UnicodeDecodeError:
                    continue
            fields, implicit, explicit = self.__getFields(text)
            if implicit:
                if node in visitor.calls:
                    self.__error(node.lineno - 1, node.col_offset, "M611")
                else:
                    if node.is_docstring:
                        self.__error(node.lineno - 1, node.col_offset, "M612")
                    else:
                        self.__error(node.lineno - 1, node.col_offset, "M613")

            if node in visitor.calls:
                call, strArgs = visitor.calls[node]

                numbers = set()
                names = set()
                # Determine which fields require a keyword and which an arg
                for name in fields:
                    fieldMatch = self.FormatFieldRegex.match(name)
                    try:
                        number = int(fieldMatch.group(1))
                    except ValueError:
                        number = -1
                    # negative numbers are considered keywords
                    if number >= 0:
                        numbers.add(number)
                    else:
                        names.add(fieldMatch.group(1))

                keywords = {keyword.arg for keyword in call.keywords}
                numArgs = len(call.args)
                if strArgs:
                    numArgs -= 1
                hasKwArgs = any(kw.arg is None for kw in call.keywords)
                hasStarArgs = sum(
                    1 for arg in call.args if isinstance(arg, ast.Starred)
                )

                if hasKwArgs:
                    keywords.discard(None)
                if hasStarArgs:
                    numArgs -= 1

                # if starargs or kwargs is not None, it can't count the
                # parameters but at least check if the args are used
                if hasKwArgs and not names:
                    # No names but kwargs
                    self.__error(call.lineno - 1, call.col_offset, "M623")
                if hasStarArgs and not numbers:
                    # No numbers but args
                    self.__error(call.lineno - 1, call.col_offset, "M624")

                if not hasKwArgs and not hasStarArgs:
                    # can actually verify numbers and names
                    for number in sorted(numbers):
                        if number >= numArgs:
                            self.__error(
                                call.lineno - 1, call.col_offset, "M621", number
                            )

                    for name in sorted(names):
                        if name not in keywords:
                            self.__error(call.lineno - 1, call.col_offset, "M622", name)

                for arg in range(numArgs):
                    if arg not in numbers:
                        self.__error(call.lineno - 1, call.col_offset, "M631", arg)

                for keyword in keywords:
                    if keyword not in names:
                        self.__error(call.lineno - 1, call.col_offset, "M632", keyword)

                if implicit and explicit:
                    self.__error(call.lineno - 1, call.col_offset, "M625")

    def __getFields(self, string):
        """
        Private method to extract the format field information.

        @param string format string to be parsed
        @type str
        @return format field information as a tuple with fields, implicit
            field definitions present and explicit field definitions present
        @rtype tuple of set of str, bool, bool
        """
        fields = set()
        cnt = itertools.count()
        implicit = False
        explicit = False
        try:
            for _literal, field, spec, conv in self.Formatter.parse(string):
                if field is not None and (conv is None or conv in "rsa"):
                    if not field:
                        field = str(next(cnt))
                        implicit = True
                    else:
                        explicit = True
                    fields.add(field)
                    fields.update(
                        parsedSpec[1]
                        for parsedSpec in self.Formatter.parse(spec)
                        if parsedSpec[1] is not None
                    )
        except ValueError:
            return set(), False, False
        else:
            return fields, implicit, explicit

    def __checkBuiltins(self):
        """
        Private method to check, if built-ins are shadowed.
        """
        functionDefs = [ast.FunctionDef]
        with contextlib.suppress(AttributeError):
            functionDefs.append(ast.AsyncFunctionDef)

        ignoreBuiltinAssignments = self.__args.get(
            "BuiltinsChecker", MiscellaneousCheckerDefaultArgs["BuiltinsChecker"]
        )

        for node in ast.walk(self.__tree):
            if isinstance(node, ast.Assign):
                # assign statement
                for element in node.targets:
                    if isinstance(element, ast.Name) and element.id in self.__builtins:
                        value = node.value
                        if (
                            isinstance(value, ast.Name)
                            and element.id in ignoreBuiltinAssignments
                            and value.id in ignoreBuiltinAssignments[element.id]
                        ):
                            # ignore compatibility assignments
                            continue
                        self.__error(
                            element.lineno - 1, element.col_offset, "M131", element.id
                        )
                    elif isinstance(element, (ast.Tuple, ast.List)):
                        for tupleElement in element.elts:
                            if (
                                isinstance(tupleElement, ast.Name)
                                and tupleElement.id in self.__builtins
                            ):
                                self.__error(
                                    tupleElement.lineno - 1,
                                    tupleElement.col_offset,
                                    "M131",
                                    tupleElement.id,
                                )
            elif isinstance(node, ast.For):
                # for loop
                target = node.target
                if isinstance(target, ast.Name) and target.id in self.__builtins:
                    self.__error(
                        target.lineno - 1, target.col_offset, "M131", target.id
                    )
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for element in target.elts:
                        if (
                            isinstance(element, ast.Name)
                            and element.id in self.__builtins
                        ):
                            self.__error(
                                element.lineno - 1,
                                element.col_offset,
                                "M131",
                                element.id,
                            )
            elif any(isinstance(node, functionDef) for functionDef in functionDefs):
                # (asynchronous) function definition
                for arg in node.args.args:
                    if isinstance(arg, ast.arg) and arg.arg in self.__builtins:
                        self.__error(arg.lineno - 1, arg.col_offset, "M132", arg.arg)

    def __checkComprehensions(self):
        """
        Private method to check some comprehension related things.

        This method is adapted from: flake8-comprehensions v3.15.0
        Original: Copyright (c) 2017 Adam Johnson
        """
        compType = {
            ast.DictComp: "dict",
            ast.ListComp: "list",
            ast.SetComp: "set",
        }

        visitedMapCalls = set()

        for node in ast.walk(self.__tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                numPositionalArgs = len(node.args)
                numKeywordArgs = len(node.keywords)

                if (
                    numPositionalArgs == 1
                    and isinstance(node.args[0], ast.GeneratorExp)
                    and node.func.id in ("list", "set")
                ):
                    errorCode = {
                        "list": "M180",
                        "set": "M181",
                    }[node.func.id]
                    self.__error(node.lineno - 1, node.col_offset, errorCode)

                elif (
                    numPositionalArgs == 1
                    and node.func.id == "dict"
                    and len(node.keywords) == 0
                    and isinstance(node.args[0], (ast.GeneratorExp, ast.ListComp))
                    and isinstance(node.args[0].elt, ast.Tuple)
                    and len(node.args[0].elt.elts) == 2
                ):
                    if isinstance(node.args[0], ast.GeneratorExp):
                        errorCode = "M182"
                    else:
                        errorCode = "M184"
                    self.__error(node.lineno - 1, node.col_offset, errorCode)

                elif (
                    numPositionalArgs == 1
                    and isinstance(node.args[0], ast.ListComp)
                    and node.func.id in ("list", "set", "any", "all")
                ):
                    errorCode = {
                        "list": "M191",
                        "set": "M183",
                        "any": "M199",
                        "all": "M199",
                    }[node.func.id]
                    self.__error(
                        node.lineno - 1, node.col_offset, errorCode, node.func.id
                    )

                elif numPositionalArgs == 1 and (
                    isinstance(node.args[0], ast.Tuple)
                    and node.func.id == "tuple"
                    or isinstance(node.args[0], ast.List)
                    and node.func.id == "list"
                ):
                    errorCode = {
                        "tuple": "M189a",
                        "list": "M190a",
                    }[node.func.id]
                    self.__error(
                        node.lineno - 1,
                        node.col_offset,
                        errorCode,
                        type(node.args[0]).__name__.lower(),
                        node.func.id,
                    )

                elif (
                    numPositionalArgs == 1
                    and numKeywordArgs == 0
                    and isinstance(node.args[0], (ast.Dict, ast.DictComp))
                    and node.func.id == "dict"
                ):
                    if isinstance(node.args[0], ast.Dict):
                        type_ = "dict"
                    else:
                        type_ = "dict comprehension"
                    self.__error(
                        node.lineno - 1,
                        node.col_offset,
                        "M198",
                        type_,
                    )

                elif (
                    numPositionalArgs == 1
                    and isinstance(node.args[0], (ast.Tuple, ast.List))
                    and (
                        node.func.id in ("tuple", "list", "set")
                        or (
                            node.func.id == "dict"
                            and all(
                                isinstance(elt, ast.Tuple) and len(elt.elts) == 2
                                for elt in node.args[0].elts
                            )
                        )
                    )
                ):
                    errorCode = {
                        "tuple": "M189b",
                        "list": "M190b",
                        "set": "M185",
                        "dict": "M186",
                    }[node.func.id]
                    self.__error(
                        node.lineno - 1,
                        node.col_offset,
                        errorCode,
                        type(node.args[0]).__name__.lower(),
                        node.func.id,
                    )

                elif (
                    numPositionalArgs == 0
                    and not any(isinstance(a, ast.Starred) for a in node.args)
                    and not any(k.arg is None for k in node.keywords)
                    and node.func.id == "dict"
                ) or (
                    numPositionalArgs == 0
                    and numKeywordArgs == 0
                    and node.func.id in ("tuple", "list")
                ):
                    self.__error(node.lineno - 1, node.col_offset, "M188", node.func.id)

                elif (
                    node.func.id in {"list", "reversed"}
                    and numPositionalArgs > 0
                    and isinstance(node.args[0], ast.Call)
                    and isinstance(node.args[0].func, ast.Name)
                    and node.args[0].func.id == "sorted"
                ):
                    if node.func.id == "reversed":
                        reverseFlagValue = False
                        for kw in node.args[0].keywords:
                            if kw.arg != "reverse":
                                continue
                            reverseFlagValue = (
                                bool(kw.value.value)
                                if isinstance(kw.value, ast.Constant)
                                else None
                            )

                        if reverseFlagValue is None:
                            self.__error(
                                node.lineno - 1,
                                node.col_offset,
                                "M193a",
                                node.func.id,
                                node.args[0].func.id,
                            )
                        else:
                            self.__error(
                                node.lineno - 1,
                                node.col_offset,
                                "M193b",
                                node.func.id,
                                node.args[0].func.id,
                                not reverseFlagValue,
                            )

                    else:
                        self.__error(
                            node.lineno - 1,
                            node.col_offset,
                            "M193c",
                            node.func.id,
                            node.args[0].func.id,
                        )

                elif (
                    numPositionalArgs > 0
                    and isinstance(node.args[0], ast.Call)
                    and isinstance(node.args[0].func, ast.Name)
                    and (
                        (
                            node.func.id in {"set", "sorted"}
                            and node.args[0].func.id
                            in {"list", "reversed", "sorted", "tuple"}
                        )
                        or (
                            node.func.id in {"list", "tuple"}
                            and node.args[0].func.id in {"list", "tuple"}
                        )
                        or (node.func.id == "set" and node.args[0].func.id == "set")
                    )
                ):
                    self.__error(
                        node.lineno - 1,
                        node.col_offset,
                        "M194",
                        node.args[0].func.id,
                        node.func.id,
                    )

                elif (
                    node.func.id in {"reversed", "set", "sorted"}
                    and numPositionalArgs > 0
                    and isinstance(node.args[0], ast.Subscript)
                    and isinstance(node.args[0].slice, ast.Slice)
                    and node.args[0].slice.lower is None
                    and node.args[0].slice.upper is None
                    and isinstance(node.args[0].slice.step, ast.UnaryOp)
                    and isinstance(node.args[0].slice.step.op, ast.USub)
                    and isinstance(node.args[0].slice.step.operand, ast.Constant)
                    and node.args[0].slice.step.operand.n == 1
                ):
                    self.__error(node.lineno - 1, node.col_offset, "M195", node.func.id)

                elif (
                    node.func.id == "map"
                    and node not in visitedMapCalls
                    and len(node.args) == 2
                    and isinstance(node.args[0], ast.Lambda)
                ):
                    self.__error(
                        node.lineno - 1, node.col_offset, "M197", "generator expression"
                    )

                elif (
                    node.func.id in ("list", "set", "dict")
                    and len(node.args) == 1
                    and isinstance(node.args[0], ast.Call)
                    and isinstance(node.args[0].func, ast.Name)
                    and node.args[0].func.id == "map"
                    and len(node.args[0].args) == 2
                    and isinstance(node.args[0].args[0], ast.Lambda)
                ):
                    # To avoid raising M197 on the map() call inside the list/set/dict.
                    mapCall = node.args[0]
                    visitedMapCalls.add(mapCall)

                    rewriteable = True
                    if node.func.id == "dict":
                        # For the generator expression to be rewriteable as a
                        # dict comprehension, its lambda must return a 2-tuple.
                        lambdaNode = node.args[0].args[0]
                        if (
                            not isinstance(lambdaNode.body, (ast.List, ast.Tuple))
                            or len(lambdaNode.body.elts) != 2
                        ):
                            rewriteable = False

                    if rewriteable:
                        comprehensionType = f"{node.func.id} comprehension"
                        self.__error(
                            node.lineno - 1, node.col_offset, "M197", comprehensionType
                        )

            elif isinstance(node, (ast.DictComp, ast.ListComp, ast.SetComp)) and (
                len(node.generators) == 1
                and not node.generators[0].ifs
                and not node.generators[0].is_async
            ):
                if (
                    isinstance(node, (ast.ListComp, ast.SetComp))
                    and isinstance(node.elt, ast.Name)
                    and isinstance(node.generators[0].target, ast.Name)
                    and node.elt.id == node.generators[0].target.id
                ) or (
                    isinstance(node, ast.DictComp)
                    and isinstance(node.key, ast.Name)
                    and isinstance(node.value, ast.Name)
                    and isinstance(node.generators[0].target, ast.Tuple)
                    and len(node.generators[0].target.elts) == 2
                    and isinstance(node.generators[0].target.elts[0], ast.Name)
                    and node.generators[0].target.elts[0].id == node.key.id
                    and isinstance(node.generators[0].target.elts[1], ast.Name)
                    and node.generators[0].target.elts[1].id == node.value.id
                ):
                    self.__error(
                        node.lineno - 1,
                        node.col_offset,
                        "M196",
                        compType[node.__class__],
                    )

                elif (
                    isinstance(node, ast.DictComp)
                    and isinstance(node.key, ast.Name)
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.generators[0].target, ast.Name)
                    and node.key.id == node.generators[0].target.id
                ):
                    self.__error(
                        node.lineno - 1,
                        node.col_offset,
                        "M200",
                        compType[node.__class__],
                    )

    def __dictShouldBeChecked(self, node):
        """
        Private function to test, if the node should be checked.

        @param node reference to the AST node
        @type ast.Dict
        @return flag indicating to check the node
        @rtype bool
        """
        if not all(AstUtilities.isString(key) for key in node.keys):
            return False

        if (
            "__IGNORE_WARNING__" in self.__source[node.lineno - 1]
            or "__IGNORE_WARNING_M251__" in self.__source[node.lineno - 1]
        ):
            return False

        lineNumbers = [key.lineno for key in node.keys]
        return len(lineNumbers) == len(set(lineNumbers))

    def __checkDictWithSortedKeys(self):
        """
        Private method to check, if dictionary keys appear in sorted order.
        """
        for node in ast.walk(self.__tree):
            if isinstance(node, ast.Dict) and self.__dictShouldBeChecked(node):
                for key1, key2 in zip(node.keys, node.keys[1:]):
                    if key2.value < key1.value:
                        self.__error(
                            key2.lineno - 1,
                            key2.col_offset,
                            "M251",
                            key2.value,
                            key1.value,
                        )

    def __checkGettext(self):
        """
        Private method to check the 'gettext' import statement.
        """
        for node in ast.walk(self.__tree):
            if isinstance(node, ast.ImportFrom) and any(
                name.asname == "_" for name in node.names
            ):
                self.__error(
                    node.lineno - 1, node.col_offset, "M711", node.names[0].name
                )

    def __checkBugBear(self):
        """
        Private method for bugbear checks.
        """
        visitor = BugBearVisitor()
        visitor.visit(self.__tree)
        for violation in visitor.violations:
            node = violation[0]
            reason = violation[1]
            params = violation[2:]
            self.__error(node.lineno - 1, node.col_offset, reason, *params)

    def __checkReturn(self):
        """
        Private method to check return statements.
        """
        visitor = ReturnVisitor()
        visitor.visit(self.__tree)
        for violation in visitor.violations:
            node = violation[0]
            reason = violation[1]
            self.__error(node.lineno - 1, node.col_offset, reason)

    def __checkDateTime(self):
        """
        Private method to check use of naive datetime functions.
        """
        # step 1: generate an augmented node tree containing parent info
        #         for each child node
        tree = copy.deepcopy(self.__tree)
        for node in ast.walk(tree):
            for childNode in ast.iter_child_nodes(node):
                childNode._dtCheckerParent = node

        # step 2: perform checks and report issues
        visitor = DateTimeVisitor()
        visitor.visit(tree)
        for violation in visitor.violations:
            node = violation[0]
            reason = violation[1]
            self.__error(node.lineno - 1, node.col_offset, reason)

    def __checkSysVersion(self):
        """
        Private method to check the use of sys.version and sys.version_info.
        """
        visitor = SysVersionVisitor()
        visitor.visit(self.__tree)
        for violation in visitor.violations:
            node = violation[0]
            reason = violation[1]
            self.__error(node.lineno - 1, node.col_offset, reason)

    def __checkProperties(self):
        """
        Private method to check for issue with property related methods.
        """
        properties = []
        for node in ast.walk(self.__tree):
            if isinstance(node, ast.ClassDef):
                properties.clear()

            elif isinstance(node, ast.FunctionDef):
                propertyCount = 0
                for decorator in node.decorator_list:
                    # property getter method
                    if isinstance(decorator, ast.Name) and decorator.id == "property":
                        propertyCount += 1
                        properties.append(node.name)
                        if len(node.args.args) != 1:
                            self.__error(
                                node.lineno - 1,
                                node.col_offset,
                                "M260",
                                len(node.args.args),
                            )

                    if isinstance(decorator, ast.Attribute):
                        # property setter method
                        if decorator.attr == "setter":
                            propertyCount += 1
                            if node.name != decorator.value.id:
                                if node.name in properties:
                                    self.__error(
                                        node.lineno - 1,
                                        node.col_offset,
                                        "M265",
                                        node.name,
                                        decorator.value.id,
                                    )
                                else:
                                    self.__error(
                                        node.lineno - 1,
                                        node.col_offset,
                                        "M263",
                                        decorator.value.id,
                                        node.name,
                                    )
                            if len(node.args.args) != 2:
                                self.__error(
                                    node.lineno - 1,
                                    node.col_offset,
                                    "M261",
                                    len(node.args.args),
                                )

                        # property deleter method
                        if decorator.attr == "deleter":
                            propertyCount += 1
                            if node.name != decorator.value.id:
                                if node.name in properties:
                                    self.__error(
                                        node.lineno - 1,
                                        node.col_offset,
                                        "M266",
                                        node.name,
                                        decorator.value.id,
                                    )
                                else:
                                    self.__error(
                                        node.lineno - 1,
                                        node.col_offset,
                                        "M264",
                                        decorator.value.id,
                                        node.name,
                                    )
                            if len(node.args.args) != 1:
                                self.__error(
                                    node.lineno - 1,
                                    node.col_offset,
                                    "M262",
                                    len(node.args.args),
                                )

                if propertyCount > 1:
                    self.__error(node.lineno - 1, node.col_offset, "M267", node.name)

    #######################################################################
    ## The following methods check for implicitly concatenated strings.
    ##
    ## These methods are adapted from: flake8-implicit-str-concat v0.5.0
    ## Original: Copyright (c) 2023 Dylan Turner
    #######################################################################

    if sys.version_info < (3, 12):

        def __isImplicitStringConcat(self, first, second):
            """
            Private method to check, if the given strings indicate an implicit string
            concatenation.

            @param first first token
            @type tuple
            @param second second token
            @type tuple
            @return flag indicating an implicit string concatenation
            @rtype bool
            """
            return first.type == second.type == tokenize.STRING

    else:

        def __isImplicitStringConcat(self, first, second):
            """
            Private method to check, if the given strings indicate an implicit string
            concatenation.

            @param first first token
            @type tuple
            @param second second token
            @type tuple
            @return flag indicating an implicit string concatenation
            @rtype bool
            """
            return (
                (first.type == second.type == tokenize.STRING)
                or (
                    first.type == tokenize.STRING
                    and second.type == tokenize.FSTRING_START
                )
                or (
                    first.type == tokenize.FSTRING_END
                    and second.type == tokenize.STRING
                )
                or (
                    first.type == tokenize.FSTRING_END
                    and second.type == tokenize.FSTRING_START
                )
            )

    def __checkImplicitStringConcat(self):
        """
        Private method to check for implicitly concatenated strings.
        """
        tokensWithoutWhitespace = (
            tok
            for tok in self.__tokens
            if tok.type
            not in (
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.COMMENT,
            )
        )
        for a, b in pairwise(tokensWithoutWhitespace):
            if self.__isImplicitStringConcat(a, b):
                self.__error(
                    a.end[0] - 1, a.end[1], "M851" if a.end[0] == b.start[0] else "M852"
                )

    def __checkExplicitStringConcat(self):
        """
        Private method to check for explicitly concatenated strings.
        """
        for node in ast.walk(self.__tree):
            if (
                isinstance(node, ast.BinOp)
                and isinstance(node.op, ast.Add)
                and all(
                    AstUtilities.isBaseString(operand)
                    or isinstance(operand, ast.JoinedStr)
                    for operand in (node.left, node.right)
                )
            ):
                self.__error(node.lineno - 1, node.col_offset, "M853")


class TextVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor for bytes and str instances.

    It tries to detect docstrings as string of the first expression of each
    module, class or function.
    """

    # modeled after the string format flake8 extension

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.nodes = []
        self.calls = {}

    def __addNode(self, node):
        """
        Private method to add a node to our list of nodes.

        @param node reference to the node to add
        @type ast.AST
        """
        if not hasattr(node, "is_docstring"):
            node.is_docstring = False
        self.nodes.append(node)

    def visit_Constant(self, node):
        """
        Public method to handle constant nodes.

        @param node reference to the bytes node
        @type ast.Constant
        """
        if AstUtilities.isBaseString(node):
            self.__addNode(node)
        else:
            super().generic_visit(node)

    def __visitDefinition(self, node):
        """
        Private method handling class and function definitions.

        @param node reference to the node to handle
        @type ast.FunctionDef, ast.AsyncFunctionDef or ast.ClassDef
        """
        # Manually traverse class or function definition
        # * Handle decorators normally
        # * Use special check for body content
        # * Don't handle the rest (e.g. bases)
        for decorator in node.decorator_list:
            self.visit(decorator)
        self.__visitBody(node)

    def __visitBody(self, node):
        """
        Private method to traverse the body of the node manually.

        If the first node is an expression which contains a string or bytes it
        marks that as a docstring.

        @param node reference to the node to traverse
        @type ast.AST
        """
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and AstUtilities.isBaseString(node.body[0].value)
        ):
            node.body[0].value.is_docstring = True

        for subnode in node.body:
            self.visit(subnode)

    def visit_Module(self, node):
        """
        Public method to handle a module.

        @param node reference to the node to handle
        @type ast.Module
        """
        self.__visitBody(node)

    def visit_ClassDef(self, node):
        """
        Public method to handle a class definition.

        @param node reference to the node to handle
        @type ast.ClassDef
        """
        # Skipped nodes: ('name', 'bases', 'keywords', 'starargs', 'kwargs')
        self.__visitDefinition(node)

    def visit_FunctionDef(self, node):
        """
        Public method to handle a function definition.

        @param node reference to the node to handle
        @type ast.FunctionDef
        """
        # Skipped nodes: ('name', 'args', 'returns')
        self.__visitDefinition(node)

    def visit_AsyncFunctionDef(self, node):
        """
        Public method to handle an asynchronous function definition.

        @param node reference to the node to handle
        @type ast.AsyncFunctionDef
        """
        # Skipped nodes: ('name', 'args', 'returns')
        self.__visitDefinition(node)

    def visit_Call(self, node):
        """
        Public method to handle a function call.

        @param node reference to the node to handle
        @type ast.Call
        """
        if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
            if AstUtilities.isBaseString(node.func.value):
                self.calls[node.func.value] = (node, False)
            elif (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "str"
                and node.args
                and AstUtilities.isBaseString(node.args[0])
            ):
                self.calls[node.args[0]] = (node, True)
        super().generic_visit(node)


#######################################################################
## BugBearVisitor
##
## adapted from: flake8-bugbear v24.8.19
##
## Original: Copyright (c) 2016 Łukasz Langa
#######################################################################

BugBearContext = namedtuple("BugBearContext", ["node", "stack"])


@dataclass
class M540CaughtException:
    """
    Class to hold the data for a caught exception.
    """

    name: str
    hasNote: bool


class BugBearVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor to check for various topics.
    """

    CONTEXTFUL_NODES = (
        ast.Module,
        ast.ClassDef,
        ast.AsyncFunctionDef,
        ast.FunctionDef,
        ast.Lambda,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )

    FUNCTION_NODES = (
        ast.AsyncFunctionDef,
        ast.FunctionDef,
        ast.Lambda,
    )

    NodeWindowSize = 4

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.nodeWindow = []
        self.violations = []
        self.contexts = []

        self.__M523Seen = set()
        self.__M505Imports = set()
        self.__M540CaughtException = None

    @property
    def nodeStack(self):
        """
        Public method to get a reference to the most recent node stack.

        @return reference to the most recent node stack
        @rtype list
        """
        if len(self.contexts) == 0:
            return []

        context, stack = self.contexts[-1]
        return stack

    def __isIdentifier(self, arg):
        """
        Private method to check if arg is a valid identifier.

        See https://docs.python.org/2/reference/lexical_analysis.html#identifiers

        @param arg reference to an argument node
        @type ast.Node
        @return flag indicating a valid identifier
        @rtype TYPE
        """
        if not AstUtilities.isString(arg):
            return False

        return (
            re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", AstUtilities.getValue(arg))
            is not None
        )

    def toNameStr(self, node):
        """
        Public method to turn Name and Attribute nodes to strings, handling any
        depth of attribute accesses.


        @param node reference to the node
        @type ast.Name or ast.Attribute
        @return string representation
        @rtype str
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self.toNameStr(node.func)
        elif isinstance(node, ast.Attribute):
            inner = self.toNameStr(node.value)
            if inner is None:
                return None
            return f"{inner}.{node.attr}"
        else:
            return None

    def __typesafeIssubclass(self, obj, classOrTuple):
        """
        Private method implementing a type safe issubclass() function.

        @param obj reference to the object to be tested
        @type Any
        @param classOrTuple type to check against
        @type type
        @return flag indicating a subclass
        @rtype bool
        """
        try:
            return issubclass(obj, classOrTuple)
        except TypeError:
            # User code specifies a type that is not a type in our current run.
            # Might be their error, might be a difference in our environments.
            # We don't know so we ignore this.
            return False

    def __getAssignedNames(self, loopNode):
        """
        Private method to get the names of a for loop.

        @param loopNode reference to the node to be processed
        @type ast.For
        @yield DESCRIPTION
        @ytype TYPE
        """
        loopTargets = (ast.For, ast.AsyncFor, ast.comprehension)
        for node in self.__childrenInScope(loopNode):
            if isinstance(node, (ast.Assign)):
                for child in node.targets:
                    yield from self.__namesFromAssignments(child)
            if isinstance(node, loopTargets + (ast.AnnAssign, ast.AugAssign)):
                yield from self.__namesFromAssignments(node.target)

    def __namesFromAssignments(self, assignTarget):
        """
        Private method to get names of an assignment.

        @param assignTarget reference to the node to be processed
        @type ast.Node
        @yield name of the assignment
        @ytype str
        """
        if isinstance(assignTarget, ast.Name):
            yield assignTarget.id
        elif isinstance(assignTarget, ast.Starred):
            yield from self.__namesFromAssignments(assignTarget.value)
        elif isinstance(assignTarget, (ast.List, ast.Tuple)):
            for child in assignTarget.elts:
                yield from self.__namesFromAssignments(child)

    def __childrenInScope(self, node):
        """
        Private method to get all child nodes in the given scope.

        @param node reference to the node to be processed
        @type ast.Node
        @yield reference to a child node
        @ytype ast.Node
        """
        yield node
        if not isinstance(node, BugBearVisitor.FUNCTION_NODES):
            for child in ast.iter_child_nodes(node):
                yield from self.__childrenInScope(child)

    def __flattenExcepthandler(self, node):
        """
        Private method to flatten the list of exceptions handled by an except handler.

        @param node reference to the node to be processed
        @type ast.Node
        @yield reference to the exception type node
        @ytype ast.Node
        """
        if not isinstance(node, ast.Tuple):
            yield node
            return

        exprList = node.elts.copy()
        while len(exprList):
            expr = exprList.pop(0)
            if isinstance(expr, ast.Starred) and isinstance(
                expr.value, (ast.List, ast.Tuple)
            ):
                exprList.extend(expr.value.elts)
                continue
            yield expr

    def __checkRedundantExcepthandlers(self, names, node):
        """
        Private method to check for redundant exception types in an exception handler.

        @param names list of exception types to be checked
        @type list of ast.Name
        @param node reference to the exception handler node
        @type ast.ExceptionHandler
        @return tuple containing the error data
        @rtype tuple of (ast.Node, str, str, str, str)
        """
        redundantExceptions = {
            "OSError": {
                # All of these are actually aliases of OSError since Python 3.3
                "IOError",
                "EnvironmentError",
                "WindowsError",
                "mmap.error",
                "socket.error",
                "select.error",
            },
            "ValueError": {
                "binascii.Error",
            },
        }

        # See if any of the given exception names could be removed, e.g. from:
        #    (MyError, MyError)  # duplicate names
        #    (MyError, BaseException)  # everything derives from the Base
        #    (Exception, TypeError)  # builtins where one subclasses another
        #    (IOError, OSError)  # IOError is an alias of OSError since Python3.3
        # but note that other cases are impractical to handle from the AST.
        # We expect this is mostly useful for users who do not have the
        # builtin exception hierarchy memorised, and include a 'shadowed'
        # subtype without realising that it's redundant.
        good = sorted(set(names), key=names.index)
        if "BaseException" in good:
            good = ["BaseException"]
        # Remove redundant exceptions that the automatic system either handles
        # poorly (usually aliases) or can't be checked (e.g. it's not an
        # built-in exception).
        for primary, equivalents in redundantExceptions.items():
            if primary in good:
                good = [g for g in good if g not in equivalents]

        for name, other in itertools.permutations(tuple(good), 2):
            if (
                self.__typesafeIssubclass(
                    getattr(builtins, name, type), getattr(builtins, other, ())
                )
                and name in good
            ):
                good.remove(name)
        if good != names:
            desc = good[0] if len(good) == 1 else "({0})".format(", ".join(good))
            as_ = " as " + node.name if node.name is not None else ""
            return (node, "M514", ", ".join(names), as_, desc)

        return None

    def __walkList(self, nodes):
        """
        Private method to walk a given list of nodes.

        @param nodes list of nodes to walk
        @type list of ast.Node
        @yield node references as determined by the ast.walk() function
        @ytype ast.Node
        """
        for node in nodes:
            yield from ast.walk(node)

    def __getNamesFromTuple(self, node):
        """
        Private method to get the names from an ast.Tuple node.

        @param node ast node to be processed
        @type ast.Tuple
        @yield names
        @ytype str
        """
        for dim in node.elts:
            if isinstance(dim, ast.Name):
                yield dim.id
            elif isinstance(dim, ast.Tuple):
                yield from self.__getNamesFromTuple(dim)

    def __getDictCompLoopAndNamedExprVarNames(self, node):
        """
        Private method to get the names of comprehension loop variables.

        @param node ast node to be processed
        @type ast.DictComp
        @yield loop variable names
        @ytype str
        """
        finder = NamedExprFinder()
        for gen in node.generators:
            if isinstance(gen.target, ast.Name):
                yield gen.target.id
            elif isinstance(gen.target, ast.Tuple):
                yield from self.__getNamesFromTuple(gen.target)

            finder.visit(gen.ifs)

        yield from finder.getNames().keys()

    def __inClassInit(self):
        """
        Private method to check, if we are inside an '__init__' method.

        @return flag indicating being within the '__init__' method
        @rtype bool
        """
        return (
            len(self.contexts) >= 2
            and isinstance(self.contexts[-2].node, ast.ClassDef)
            and isinstance(self.contexts[-1].node, ast.FunctionDef)
            and self.contexts[-1].node.name == "__init__"
        )

    def visit_Return(self, node):
        """
        Public method to handle 'Return' nodes.

        @param node reference to the node to be processed
        @type ast.Return
        """
        if self.__inClassInit() and node.value is not None:
            self.violations.append((node, "M537"))

        self.generic_visit(node)

    def visit_Yield(self, node):
        """
        Public method to handle 'Yield' nodes.

        @param node reference to the node to be processed
        @type ast.Yield
        """
        if self.__inClassInit():
            self.violations.append((node, "M537"))

        self.generic_visit(node)

    def visit_YieldFrom(self, node) -> None:
        """
        Public method to handle 'YieldFrom' nodes.

        @param node reference to the node to be processed
        @type ast.YieldFrom
        """
        if self.__inClassInit():
            self.violations.append((node, "M537"))

        self.generic_visit(node)

    def visit(self, node):
        """
        Public method to traverse a given AST node.

        @param node AST node to be traversed
        @type ast.Node
        """
        isContextful = isinstance(node, BugBearVisitor.CONTEXTFUL_NODES)

        if isContextful:
            context = BugBearContext(node, [])
            self.contexts.append(context)

        self.nodeStack.append(node)
        self.nodeWindow.append(node)
        self.nodeWindow = self.nodeWindow[-BugBearVisitor.NodeWindowSize :]

        super().visit(node)

        self.nodeStack.pop()

        if isContextful:
            self.contexts.pop()

        self.__checkForM518(node)

    def visit_ExceptHandler(self, node):
        """
        Public method to handle exception handlers.

        @param node reference to the node to be processed
        @type ast.ExceptHandler
        """
        if node.type is None:
            # bare except is handled by pycodestyle already
            self.generic_visit(node)
            return

        oldM540CaughtException = self.__M540CaughtException
        if node.name is None:
            self.__M540CaughtException = None
        else:
            self.__M540CaughtException = M540CaughtException(node.name, False)

        names = self.__checkForM513_M529_M530(node)

        if "BaseException" in names and not ExceptBaseExceptionVisitor(node).reRaised():
            self.violations.append((node, "M536"))

        self.generic_visit(node)

        if (
            self.__M540CaughtException is not None
            and self.__M540CaughtException.hasNote
        ):
            self.violations.append((node, "M540"))
        self.__M540CaughtException = oldM540CaughtException

    def visit_UAdd(self, node):
        """
        Public method to handle unary additions.

        @param node reference to the node to be processed
        @type ast.UAdd
        """
        trailingNodes = list(map(type, self.nodeWindow[-4:]))
        if trailingNodes == [ast.UnaryOp, ast.UAdd, ast.UnaryOp, ast.UAdd]:
            originator = self.nodeWindow[-4]
            self.violations.append((originator, "M502"))

        self.generic_visit(node)

    def visit_Call(self, node):
        """
        Public method to handle a function call.

        @param node reference to the node to be processed
        @type ast.Call
        """
        isM540AddNote = False

        if isinstance(node.func, ast.Attribute):
            self.__checkForM505(node)
            isM540AddNote = self.__checkForM540AddNote(node.func)
        else:
            with contextlib.suppress(AttributeError, IndexError):
                # bad super() call
                if isinstance(node.func, ast.Name) and node.func.id == "super":
                    args = node.args
                    if (
                        len(args) == 2
                        and isinstance(args[0], ast.Attribute)
                        and isinstance(args[0].value, ast.Name)
                        and args[0].value.id == "self"
                        and args[0].attr == "__class__"
                    ):
                        self.violations.append((node, "M582"))

                # bad getattr and setattr
                if (
                    node.func.id in ("getattr", "hasattr")
                    and node.args[1].value == "__call__"
                ):
                    self.violations.append((node, "M504"))
                if (
                    node.func.id == "getattr"
                    and len(node.args) == 2
                    and self.__isIdentifier(node.args[1])
                    and iskeyword(AstUtilities.getValue(node.args[1]))
                ):
                    self.violations.append((node, "M509"))
                elif (
                    node.func.id == "setattr"
                    and len(node.args) == 3
                    and self.__isIdentifier(node.args[1])
                    and iskeyword(AstUtilities.getValue(node.args[1]))
                ):
                    self.violations.append((node, "M510"))

        self.__checkForM526(node)

        self.__checkForM528(node)
        self.__checkForM534(node)
        self.__checkForM539(node)

        # no need for copying, if used in nested calls it will be set to None
        currentM540CaughtException = self.__M540CaughtException
        if not isM540AddNote:
            self.__checkForM540Usage(node.args)
            self.__checkForM540Usage(node.keywords)

        self.generic_visit(node)

        if isM540AddNote:
            # Avoid nested calls within the parameter list using the variable itself.
            # e.g. `e.add_note(str(e))`
            self.__M540CaughtException = currentM540CaughtException

    def visit_Module(self, node):
        """
        Public method to handle a module node.

        @param node reference to the node to be processed
        @type ast.Module
        """
        self.generic_visit(node)

    def visit_Assign(self, node):
        """
        Public method to handle assignments.

        @param node reference to the node to be processed
        @type ast.Assign
        """
        self.__checkForM540Usage(node.value)
        if len(node.targets) == 1:
            target = node.targets[0]
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and (target.value.id, target.attr) == ("os", "environ")
            ):
                self.violations.append((node, "M503"))

        self.generic_visit(node)

    def visit_For(self, node):
        """
        Public method to handle 'for' statements.

        @param node reference to the node to be processed
        @type ast.For
        """
        self.__checkForM507(node)
        self.__checkForM520(node)
        self.__checkForM523(node)
        self.__checkForM531(node)
        self.__checkForM569(node)

        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        """
        Public method to handle 'for' statements.

        @param node reference to the node to be processed
        @type ast.AsyncFor
        """
        self.__checkForM507(node)
        self.__checkForM520(node)
        self.__checkForM523(node)
        self.__checkForM531(node)

        self.generic_visit(node)

    def visit_While(self, node):
        """
        Public method to handle 'while' statements.

        @param node reference to the node to be processed
        @type ast.While
        """
        self.__checkForM523(node)

        self.generic_visit(node)

    def visit_ListComp(self, node):
        """
        Public method to handle list comprehensions.

        @param node reference to the node to be processed
        @type ast.ListComp
        """
        self.__checkForM523(node)

        self.generic_visit(node)

    def visit_SetComp(self, node):
        """
        Public method to handle set comprehensions.

        @param node reference to the node to be processed
        @type ast.SetComp
        """
        self.__checkForM523(node)

        self.generic_visit(node)

    def visit_DictComp(self, node):
        """
        Public method to handle dictionary comprehensions.

        @param node reference to the node to be processed
        @type ast.DictComp
        """
        self.__checkForM523(node)
        self.__checkForM535(node)

        self.generic_visit(node)

    def visit_GeneratorExp(self, node):
        """
        Public method to handle generator expressions.

        @param node reference to the node to be processed
        @type ast.GeneratorExp
        """
        self.__checkForM523(node)

        self.generic_visit(node)

    def visit_Assert(self, node):
        """
        Public method to handle 'assert' statements.

        @param node reference to the node to be processed
        @type ast.Assert
        """
        if (
            AstUtilities.isNameConstant(node.test)
            and AstUtilities.getValue(node.test) is False
        ):
            self.violations.append((node, "M511"))

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """
        Public method to handle async function definitions.

        @param node reference to the node to be processed
        @type ast.AsyncFunctionDef
        """
        self.__checkForM506_M508(node)

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """
        Public method to handle function definitions.

        @param node reference to the node to be processed
        @type ast.FunctionDef
        """
        self.__checkForM506_M508(node)
        self.__checkForM519(node)
        self.__checkForM521(node)

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """
        Public method to handle class definitions.

        @param node reference to the node to be processed
        @type ast.ClassDef
        """
        self.__checkForM521(node)
        self.__checkForM524_M527(node)

        self.generic_visit(node)

    def visit_Try(self, node):
        """
        Public method to handle 'try' statements'.

        @param node reference to the node to be processed
        @type ast.Try
        """
        self.__checkForM512(node)
        self.__checkForM525(node)

        self.generic_visit(node)

    def visit_Compare(self, node):
        """
        Public method to handle comparison statements.

        @param node reference to the node to be processed
        @type ast.Compare
        """
        self.__checkForM515(node)

        self.generic_visit(node)

    def visit_Raise(self, node):
        """
        Public method to handle 'raise' statements.

        @param node reference to the node to be processed
        @type ast.Raise
        """
        if node.exc is None:
            self.__M540CaughtException = None
        else:
            self.__checkForM540Usage(node.exc)
            self.__checkForM540Usage(node.cause)
        self.__checkForM516(node)

        self.generic_visit(node)

    def visit_With(self, node):
        """
        Public method to handle 'with' statements.

        @param node reference to the node to be processed
        @type ast.With
        """
        self.__checkForM517(node)
        self.__checkForM522(node)

        self.generic_visit(node)

    def visit_JoinedStr(self, node):
        """
        Public method to handle f-string arguments.

        @param node reference to the node to be processed
        @type ast.JoinedStr
        """
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                return

        self.violations.append((node, "M581"))

    def visit_AnnAssign(self, node):
        """
        Public method to check annotated assign statements.

        @param node reference to the node to be processed
        @type ast.AnnAssign
        """
        self.__checkForM532(node)
        self.__checkForM540Usage(node.value)

        self.generic_visit(node)

    def visit_Import(self, node):
        """
        Public method to check imports.

        @param node reference to the node to be processed
        @type ast.Import
        """
        self.__checkForM505(node)

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """
        Public method to check from imports.

        @param node reference to the node to be processed
        @type ast.Import
        """
        self.visit_Import(node)

    def visit_Set(self, node):
        """
        Public method to check a set.

        @param node reference to the node to be processed
        @type ast.Set
        """
        self.__checkForM533(node)

        self.generic_visit(node)

    def __checkForM505(self, node):
        """
        Private method to check the use of *strip().

        @param node reference to the node to be processed
        @type ast.Call
        """
        if isinstance(node, ast.Import):
            for name in node.names:
                self.__M505Imports.add(name.asname or name.name)
        elif isinstance(node, ast.ImportFrom):
            for name in node.names:
                self.__M505Imports.add(f"{node.module}.{name.name or name.asname}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr not in ("lstrip", "rstrip", "strip"):
                return  # method name doesn't match

            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in self.__M505Imports
            ):
                return  # method is being run on an imported module

            if len(node.args) != 1 or not AstUtilities.isString(node.args[0]):
                return  # used arguments don't match the builtin strip

            value = AstUtilities.getValue(node.args[0])
            if len(value) == 1:
                return  # stripping just one character

            if len(value) == len(set(value)):
                return  # no characters appear more than once

            self.violations.append((node, "M505"))

    def __checkForM506_M508(self, node):
        """
        Private method to check the use of mutable literals, comprehensions and calls.

        @param node reference to the node to be processed
        @type ast.AsyncFunctionDef or ast.FunctionDef
        """
        visitor = FunctionDefDefaultsVisitor("M506", "M508")
        visitor.visit(node.args.defaults + node.args.kw_defaults)
        self.violations.extend(visitor.errors)

    def __checkForM507(self, node):
        """
        Private method to check for unused loop variables.

        @param node reference to the node to be processed
        @type ast.For or ast.AsyncFor
        """
        targets = NameFinder()
        targets.visit(node.target)
        ctrlNames = set(filter(lambda s: not s.startswith("_"), targets.getNames()))
        body = NameFinder()
        for expr in node.body:
            body.visit(expr)
        usedNames = set(body.getNames())
        for name in sorted(ctrlNames - usedNames):
            n = targets.getNames()[name][0]
            self.violations.append((n, "M507", name))

    def __checkForM512(self, node):
        """
        Private method to check for return/continue/break inside finally blocks.

        @param node reference to the node to be processed
        @type ast.Try
        """

        def _loop(node, badNodeTypes):
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                return

            if isinstance(node, (ast.While, ast.For)):
                badNodeTypes = (ast.Return,)

            elif isinstance(node, badNodeTypes):
                self.violations.append((node, "M512"))

            for child in ast.iter_child_nodes(node):
                _loop(child, badNodeTypes)

        for child in node.finalbody:
            _loop(child, (ast.Return, ast.Continue, ast.Break))

    def __checkForM513_M529_M530(self, node):
        """
        Private method to check various exception handler situations.

        @param node reference to the node to be processed
        @type ast.ExceptHandler
        @return list of exception handler names
        @rtype list of str
        """
        handlers = self.__flattenExcepthandler(node.type)
        names = []
        badHandlers = []
        ignoredHandlers = []

        for handler in handlers:
            if isinstance(handler, (ast.Name, ast.Attribute)):
                name = self.toNameStr(handler)
                if name is None:
                    ignoredHandlers.append(handler)
                else:
                    names.append(name)
            elif isinstance(handler, (ast.Call, ast.Starred)):
                ignoredHandlers.append(handler)
            else:
                badHandlers.append(handler)
        if badHandlers:
            self.violations.append((node, "M530"))
        if len(names) == 0 and not badHandlers and not ignoredHandlers:
            self.violations.append((node, "M529"))
        elif (
            len(names) == 1
            and not badHandlers
            and not ignoredHandlers
            and isinstance(node.type, ast.Tuple)
        ):
            self.violations.append((node, "M513", *names))
        else:
            maybeError = self.__checkRedundantExcepthandlers(names, node)
            if maybeError is not None:
                self.violations.append(maybeError)
        return names

    def __checkForM515(self, node):
        """
        Private method to check for pointless comparisons.

        @param node reference to the node to be processed
        @type ast.Compare
        """
        if isinstance(self.nodeStack[-2], ast.Expr):
            self.violations.append((node, "M515"))

    def __checkForM516(self, node):
        """
        Private method to check for raising a literal instead of an exception.

        @param node reference to the node to be processed
        @type ast.Raise
        """
        if (
            AstUtilities.isNameConstant(node.exc)
            or AstUtilities.isNumber(node.exc)
            or AstUtilities.isString(node.exc)
        ):
            self.violations.append((node, "M516"))

    def __checkForM517(self, node):
        """
        Private method to check for use of the evil syntax
        'with assertRaises(Exception): or 'with pytest.raises(Exception):'.

        @param node reference to the node to be processed
        @type ast.With
        """
        item = node.items[0]
        itemContext = item.context_expr
        if (
            hasattr(itemContext, "func")
            and (
                (
                    isinstance(itemContext.func, ast.Attribute)
                    and (
                        itemContext.func.attr == "assertRaises"
                        or (
                            itemContext.func.attr == "raises"
                            and isinstance(itemContext.func.value, ast.Name)
                            and itemContext.func.value.id == "pytest"
                            and "match" not in (kwd.arg for kwd in itemContext.keywords)
                        )
                    )
                )
                or (
                    isinstance(itemContext.func, ast.Name)
                    and itemContext.func.id == "raises"
                    and isinstance(itemContext.func.ctx, ast.Load)
                    and "pytest.raises" in self.__M505Imports
                    and "match" not in (kwd.arg for kwd in itemContext.keywords)
                )
            )
            and len(itemContext.args) == 1
            and isinstance(itemContext.args[0], ast.Name)
            and itemContext.args[0].id in ("Exception", "BaseException")
            and not item.optional_vars
        ):
            self.violations.append((node, "M517"))

    def __checkForM518(self, node):
        """
        Private method to check for useless expressions.

        @param node reference to the node to be processed
        @type ast.FunctionDef
        """
        if not isinstance(node, ast.Expr):
            return

        if isinstance(
            node.value,
            (ast.List, ast.Set, ast.Dict, ast.Tuple),
        ) or (
            isinstance(node.value, ast.Constant)
            and (
                isinstance(
                    node.value.value,
                    (int, float, complex, bytes, bool),
                )
                or node.value.value is None
            )
        ):
            self.violations.append((node, "M518", node.value.__class__.__name__))

    def __checkForM519(self, node):
        """
        Private method to check for use of 'functools.lru_cache' or 'functools.cache'.

        @param node reference to the node to be processed
        @type ast.FunctionDef
        """
        caches = {
            "functools.cache",
            "functools.lru_cache",
            "cache",
            "lru_cache",
        }

        if (
            len(node.decorator_list) == 0
            or len(self.contexts) < 2
            or not isinstance(self.contexts[-2].node, ast.ClassDef)
        ):
            return

        # Preserve decorator order so we can get the lineno from the decorator node
        # rather than the function node (this location definition changes in Python 3.8)
        resolvedDecorators = (
            ".".join(composeCallPath(decorator)) for decorator in node.decorator_list
        )
        for idx, decorator in enumerate(resolvedDecorators):
            if decorator in {"classmethod", "staticmethod"}:
                return

            if decorator in caches:
                self.violations.append((node.decorator_list[idx], "M519"))
                return

    def __checkForM520(self, node):
        """
        Private method to check for a loop that modifies its iterable.

        @param node reference to the node to be processed
        @type ast.For or ast.AsyncFor
        """
        targets = NameFinder()
        targets.visit(node.target)
        ctrlNames = set(targets.getNames())

        iterset = M520NameFinder()
        iterset.visit(node.iter)
        itersetNames = set(iterset.getNames())

        for name in sorted(ctrlNames):
            if name in itersetNames:
                n = targets.getNames()[name][0]
                self.violations.append((n, "M520"))

    def __checkForM521(self, node):
        """
        Private method to check for use of an f-string as docstring.

        @param node reference to the node to be processed
        @type ast.FunctionDef or ast.ClassDef
        """
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.JoinedStr)
        ):
            self.violations.append((node.body[0].value, "M521"))

    def __checkForM522(self, node):
        """
        Private method to check for use of an f-string as docstring.

        @param node reference to the node to be processed
        @type ast.With
        """
        item = node.items[0]
        itemContext = item.context_expr
        if (
            hasattr(itemContext, "func")
            and hasattr(itemContext.func, "value")
            and hasattr(itemContext.func.value, "id")
            and itemContext.func.value.id == "contextlib"
            and hasattr(itemContext.func, "attr")
            and itemContext.func.attr == "suppress"
            and len(itemContext.args) == 0
        ):
            self.violations.append((node, "M522"))

    def __checkForM523(self, loopNode):
        """
        Private method to check that functions (including lambdas) do not use loop
        variables.

        @param loopNode reference to the node to be processed
        @type ast.For, ast.AsyncFor, ast.While, ast.ListComp, ast.SetComp,ast.DictComp,
            or ast.GeneratorExp
        """
        safe_functions = []
        suspiciousVariables = []
        for node in ast.walk(loopNode):
            # check if function is immediately consumed to avoid false alarm
            if isinstance(node, ast.Call):
                # check for filter&reduce
                if (
                    isinstance(node.func, ast.Name)
                    and node.func.id in ("filter", "reduce", "map")
                ) or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "reduce"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "functools"
                ):
                    for arg in node.args:
                        if isinstance(arg, BugBearVisitor.FUNCTION_NODES):
                            safe_functions.append(arg)

                # check for key=
                for keyword in node.keywords:
                    if keyword.arg == "key" and isinstance(
                        keyword.value, BugBearVisitor.FUNCTION_NODES
                    ):
                        safe_functions.append(keyword.value)

            # mark `return lambda: x` as safe
            # does not (currently) check inner lambdas in a returned expression
            # e.g. `return (lambda: x, )
            if isinstance(node, ast.Return) and isinstance(
                node.value, BugBearVisitor.FUNCTION_NODES
            ):
                safe_functions.append(node.value)

            # find unsafe functions
            if (
                isinstance(node, BugBearVisitor.FUNCTION_NODES)
                and node not in safe_functions
            ):
                argnames = {
                    arg.arg for arg in ast.walk(node.args) if isinstance(arg, ast.arg)
                }
                if isinstance(node, ast.Lambda):
                    bodyNodes = ast.walk(node.body)
                else:
                    bodyNodes = itertools.chain.from_iterable(map(ast.walk, node.body))
                errors = []
                for name in bodyNodes:
                    if isinstance(name, ast.Name) and name.id not in argnames:
                        if isinstance(name.ctx, ast.Load):
                            errors.append((name.lineno, name.col_offset, name.id, name))
                        elif isinstance(name.ctx, ast.Store):
                            argnames.add(name.id)
                for err in errors:
                    if err[2] not in argnames and err not in self.__M523Seen:
                        self.__M523Seen.add(err)  # dedupe across nested loops
                        suspiciousVariables.append(err)

        if suspiciousVariables:
            reassignedInLoop = set(self.__getAssignedNames(loopNode))

        for err in sorted(suspiciousVariables):
            if reassignedInLoop.issuperset(err[2]):
                self.violations.append((err[3], "M523", err[2]))

    def __checkForM524_M527(self, node):
        """
        Private method to check for inheritance from abstract classes in abc and lack of
        any methods decorated with abstract*.

        @param node reference to the node to be processed
        @type ast.ClassDef
        """  # __IGNORE_WARNING_D234r__

        def isAbcClass(value, name="ABC"):
            if isinstance(value, ast.keyword):
                return value.arg == "metaclass" and isAbcClass(value.value, "ABCMeta")

            # class foo(ABC)
            # class foo(abc.ABC)
            return (isinstance(value, ast.Name) and value.id == name) or (
                isinstance(value, ast.Attribute)
                and value.attr == name
                and isinstance(value.value, ast.Name)
                and value.value.id == "abc"
            )

        def isAbstractDecorator(expr):
            return (isinstance(expr, ast.Name) and expr.id[:8] == "abstract") or (
                isinstance(expr, ast.Attribute) and expr.attr[:8] == "abstract"
            )

        def isOverload(expr):
            return (isinstance(expr, ast.Name) and expr.id == "overload") or (
                isinstance(expr, ast.Attribute) and expr.attr == "overload"
            )

        def emptyBody(body):
            def isStrOrEllipsis(node):
                return isinstance(node, ast.Constant) and (
                    node.value is Ellipsis or isinstance(node.value, str)
                )

            # Function body consist solely of `pass`, `...`, and/or (doc)string literals
            return all(
                isinstance(stmt, ast.Pass)
                or (isinstance(stmt, ast.Expr) and isStrOrEllipsis(stmt.value))
                for stmt in body
            )

        # don't check multiple inheritance
        if len(node.bases) + len(node.keywords) > 1:
            return

        # only check abstract classes
        if not any(map(isAbcClass, (*node.bases, *node.keywords))):
            return

        hasMethod = False
        hasAbstractMethod = False

        if not any(map(isAbcClass, (*node.bases, *node.keywords))):
            return

        for stmt in node.body:
            # Ignore abc's that declares a class attribute that must be set
            if isinstance(stmt, (ast.AnnAssign, ast.Assign)):
                hasAbstractMethod = True
                continue

            # only check function defs
            if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            hasMethod = True

            hasAbstractDecorator = any(map(isAbstractDecorator, stmt.decorator_list))

            hasAbstractMethod |= hasAbstractDecorator

            if (
                not hasAbstractDecorator
                and emptyBody(stmt.body)
                and not any(map(isOverload, stmt.decorator_list))
            ):
                self.violations.append((stmt, "M527", stmt.name))

        if hasMethod and not hasAbstractMethod:
            self.violations.append((node, "M524", node.name))

    def __checkForM525(self, node):
        """
        Private method to check for exceptions being handled multiple times.

        @param node reference to the node to be processed
        @type ast.Try
        """
        seen = []

        for handler in node.handlers:
            if isinstance(handler.type, (ast.Name, ast.Attribute)):
                name = ".".join(composeCallPath(handler.type))
                seen.append(name)
            elif isinstance(handler.type, ast.Tuple):
                # to avoid checking the same as M514, remove duplicates per except
                uniques = set()
                for entry in handler.type.elts:
                    name = ".".join(composeCallPath(entry))
                    uniques.add(name)
                seen.extend(uniques)

        # sort to have a deterministic output
        duplicates = sorted({x for x in seen if seen.count(x) > 1})
        for duplicate in duplicates:
            self.violations.append((node, "M525", duplicate))

    def __checkForM526(self, node):
        """
        Private method to check for Star-arg unpacking after keyword argument.

        @param node reference to the node to be processed
        @type ast.Call
        """
        if not node.keywords:
            return

        starreds = [arg for arg in node.args if isinstance(arg, ast.Starred)]
        if not starreds:
            return

        firstKeyword = node.keywords[0].value
        for starred in starreds:
            if (starred.lineno, starred.col_offset) > (
                firstKeyword.lineno,
                firstKeyword.col_offset,
            ):
                self.violations.append((node, "M526"))

    def __checkForM528(self, node):
        """
        Private method to check for warn without stacklevel.

        @param node reference to the node to be processed
        @type ast.Call
        """
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "warn"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "warnings"
            and not any(kw.arg == "stacklevel" for kw in node.keywords)
            and len(node.args) < 3
        ):
            self.violations.append((node, "M528"))

    def __checkForM531(self, loopNode):
        """
        Private method to check that 'itertools.groupby' isn't iterated over more than
        once.

        A warning is emitted when the generator returned by 'groupby()' is used
        more than once inside a loop body or when it's used in a nested loop.

        @param loopNode reference to the node to be processed
        @type ast.For or ast.AsyncFor
        """
        # for <loop_node.target> in <loop_node.iter>: ...
        if isinstance(loopNode.iter, ast.Call):
            node = loopNode.iter
            if (isinstance(node.func, ast.Name) and node.func.id in ("groupby",)) or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "groupby"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "itertools"
            ):
                # We have an invocation of groupby which is a simple unpacking
                if isinstance(loopNode.target, ast.Tuple) and isinstance(
                    loopNode.target.elts[1], ast.Name
                ):
                    groupName = loopNode.target.elts[1].id
                else:
                    # Ignore any 'groupby()' invocation that isn't unpacked
                    return

                numUsages = 0
                for node in self.__walkList(loopNode.body):
                    # Handled nested loops
                    if isinstance(node, ast.For):
                        for nestedNode in self.__walkList(node.body):
                            if (
                                isinstance(nestedNode, ast.Name)
                                and nestedNode.id == groupName
                            ):
                                self.violations.append((nestedNode, "M531"))

                    # Handle multiple uses
                    if isinstance(node, ast.Name) and node.id == groupName:
                        numUsages += 1
                        if numUsages > 1:
                            self.violations.append((nestedNode, "M531"))

    def __checkForM532(self, node):
        """
        Private method to check for possible unintentional typing annotation.

        @param node reference to the node to be processed
        @type ast.AnnAssign
        """
        if (
            node.value is None
            and hasattr(node.target, "value")
            and isinstance(node.target.value, ast.Name)
            and (
                isinstance(node.target, ast.Subscript)
                or (
                    isinstance(node.target, ast.Attribute)
                    and node.target.value.id != "self"
                )
            )
        ):
            self.violations.append((node, "M532"))

    def __checkForM533(self, node):
        """
        Private method to check a set for duplicate items.

        @param node reference to the node to be processed
        @type ast.Set
        """
        seen = set()
        for elt in node.elts:
            if not isinstance(elt, ast.Constant):
                continue
            if elt.value in seen:
                self.violations.append((node, "M533", repr(elt.value)))
            else:
                seen.add(elt.value)

    def __checkForM534(self, node):
        """
        Private method to check that re.sub/subn/split arguments flags/count/maxsplit
        are passed as keyword arguments.

        @param node reference to the node to be processed
        @type ast.Call
        """
        if not isinstance(node.func, ast.Attribute):
            return
        func = node.func
        if not isinstance(func.value, ast.Name) or func.value.id != "re":
            return

        def check(numArgs, paramName):
            if len(node.args) > numArgs:
                arg = node.args[numArgs]
                self.violations.append((arg, "M534", func.attr, paramName))

        if func.attr in ("sub", "subn"):
            check(3, "count")
        elif func.attr == "split":
            check(2, "maxsplit")

    def __checkForM535(self, node):
        """
        Private method to check that a static key isn't used in a dict comprehension.

        Record a warning if a likely unchanging key is used - either a constant,
        or a variable that isn't coming from the generator expression.

        @param node reference to the node to be processed
        @type ast.DictComp
        """
        if isinstance(node.key, ast.Constant):
            self.violations.append((node, "M535", node.key.value))
        elif isinstance(
            node.key, ast.Name
        ) and node.key.id not in self.__getDictCompLoopAndNamedExprVarNames(node):
            self.violations.append((node, "M535", node.key.id))

    def __checkForM539(self, node):
        """
        Private method to check for correct ContextVar usage.

        @param node reference to the node to be processed
        @type ast.Call
        """
        if not (
            (isinstance(node.func, ast.Name) and node.func.id == "ContextVar")
            or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "ContextVar"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "contextvars"
            )
        ):
            return

        # ContextVar only takes one kw currently, but better safe than sorry
        for kw in node.keywords:
            if kw.arg == "default":
                break
        else:
            return

        visitor = FunctionDefDefaultsVisitor("M539", "M539")
        visitor.visit(kw.value)
        self.violations.extend(visitor.errors)

    def __checkForM540AddNote(self, node):
        """
        Private method to check add_note usage.

        @param node reference to the node to be processed
        @type ast.Attribute
        @return flag
        @rtype bool
        """
        if (
            node.attr == "add_note"
            and isinstance(node.value, ast.Name)
            and self.__M540CaughtException
            and node.value.id == self.__M540CaughtException.name
        ):
            self.__M540CaughtException.hasNote = True
            return True

        return False

    def __checkForM540Usage(self, node):
        """
        Private method to check the usage of exceptions with added note.

        @param node reference to the node to be processed
        @type ast.expr or None
        """  # noqa: D234y

        def superwalk(node: ast.AST | list[ast.AST]):
            """
            Function to walk an AST node or a list of AST nodes.

            @param node reference to the node or a list of nodes to be processed
            @type ast.AST or list[ast.AST]
            @yield next node to be processed
            @ytype ast.AST
            """
            if isinstance(node, list):
                for n in node:
                    yield from ast.walk(n)
            else:
                yield from ast.walk(node)

        if not self.__M540CaughtException or node is None:
            return

        for n in superwalk(node):
            if isinstance(n, ast.Name) and n.id == self.__M540CaughtException.name:
                self.__M540CaughtException = None
                break

    def __checkForM569(self, node):
        """
        Private method to check for changes to a loop's mutable iterable.

        @param node loop node to be checked
        @type ast.For
        """
        if isinstance(node.iter, ast.Name):
            name = self.toNameStr(node.iter)
        elif isinstance(node.iter, ast.Attribute):
            name = self.toNameStr(node.iter)
        else:
            return
        checker = M569Checker(name, self)
        checker.visit(node.body)
        for mutation in checker.mutations:
            self.violations.append((mutation, "M569"))


class M569Checker(ast.NodeVisitor):
    """
    Class traversing a 'for' loop body to check for modifications to a loop's
    mutable iterable.
    """

    # https://docs.python.org/3/library/stdtypes.html#mutable-sequence-types
    MUTATING_FUNCTIONS = (
        "append",
        "sort",
        "reverse",
        "remove",
        "clear",
        "extend",
        "insert",
        "pop",
        "popitem",
    )

    def __init__(self, name, bugbear):
        """
        Constructor

        @param name name of the iterator
        @type str
        @param bugbear reference to the bugbear visitor
        @type BugBearVisitor
        """
        self.__name = name
        self.__bb = bugbear
        self.mutations = []

    def visit_Delete(self, node):
        """
        Public method handling 'Delete' nodes.

        @param node reference to the node to be processed
        @type ast.Delete
        """
        for target in node.targets:
            if isinstance(target, ast.Subscript):
                name = self.__bb.toNameStr(target.value)
            elif isinstance(target, (ast.Attribute, ast.Name)):
                name = self.__bb.toNameStr(target)
            else:
                name = ""  # fallback
                self.generic_visit(target)

            if name == self.__name:
                self.mutations.append(node)

    def visit_Call(self, node):
        """
        Public method handling 'Call' nodes.

        @param node reference to the node to be processed
        @type ast.Call
        """
        if isinstance(node.func, ast.Attribute):
            name = self.__bb.toNameStr(node.func.value)
            functionObject = name
            functionName = node.func.attr

            if (
                functionObject == self.__name
                and functionName in self.MUTATING_FUNCTIONS
            ):
                self.mutations.append(node)

        self.generic_visit(node)

    def visit(self, node):
        """
        Public method to inspect an ast node.

        Like super-visit but supports iteration over lists.

        @param node AST node to be traversed
        @type TYPE
        @return reference to the last processed node
        @rtype ast.Node
        """
        if not isinstance(node, list):
            return super().visit(node)

        for elem in node:
            super().visit(elem)
        return node


class ExceptBaseExceptionVisitor(ast.NodeVisitor):
    """
    Class to determine, if a 'BaseException' is re-raised.
    """

    def __init__(self, exceptNode):
        """
        Constructor

        @param exceptNode exception node to be inspected
        @type ast.ExceptHandler
        """
        super().__init__()
        self.__root = exceptNode
        self.__reRaised = False

    def reRaised(self) -> bool:
        """
        Public method to check, if the exception is re-raised.

        @return flag indicating a re-raised exception
        @rtype bool
        """
        self.visit(self.__root)
        return self.__reRaised

    def visit_Raise(self, node):
        """
        Public method to handle 'Raise' nodes.

        If we find a corresponding `raise` or `raise e` where e was from
        `except BaseException as e:` then we mark re_raised as True and can
        stop scanning.

        @param node reference to the node to be processed
        @type ast.Raise
        """
        if node.exc is None or (
            isinstance(node.exc, ast.Name) and node.exc.id == self.__root.name
        ):
            self.__reRaised = True
            return

        super().generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """
        Public method to handle 'ExceptHandler' nodes.

        @param node reference to the node to be processed
        @type ast.ExceptHandler
        """
        if node is not self.__root:
            return  # entered a nested except - stop searching

        super().generic_visit(node)


class NameFinder(ast.NodeVisitor):
    """
    Class to extract a name out of a tree of nodes.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__names = {}

    def visit_Name(self, node):
        """
        Public method to handle 'Name' nodes.

        @param node reference to the node to be processed
        @type ast.Name
        """
        self.__names.setdefault(node.id, []).append(node)

    def visit(self, node):
        """
        Public method to traverse a given AST node.

        @param node AST node to be traversed
        @type ast.Node
        @return reference to the last processed node
        @rtype ast.Node
        """
        if isinstance(node, list):
            for elem in node:
                super().visit(elem)
            return node
        else:
            return super().visit(node)

    def getNames(self):
        """
        Public method to return the extracted names and Name nodes.

        @return dictionary containing the names as keys and the list of nodes
        @rtype dict
        """
        return self.__names


class NamedExprFinder(ast.NodeVisitor):
    """
    Class to extract names defined through an ast.NamedExpr.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__names = {}

    def visit_NamedExpr(self, node: ast.NamedExpr):
        """
        Public method handling 'NamedExpr' nodes.

        @param node reference to the node to be processed
        @type ast.NamedExpr
        """
        self.__names.setdefault(node.target.id, []).append(node.target)

        self.generic_visit(node)

    def visit(self, node):
        """
        Public method to traverse a given AST node.

        Like super-visit but supports iteration over lists.

        @param node AST node to be traversed
        @type TYPE
        @return reference to the last processed node
        @rtype ast.Node
        """
        if not isinstance(node, list):
            super().visit(node)

        for elem in node:
            super().visit(elem)

        return node

    def getNames(self):
        """
        Public method to return the extracted names and Name nodes.

        @return dictionary containing the names as keys and the list of nodes
        @rtype dict
        """
        return self.__names


class FunctionDefDefaultsVisitor(ast.NodeVisitor):
    """
    Class used by M506, M508 and M539.
    """

    def __init__(
        self,
        errorCodeCalls,  # M506 or M539
        errorCodeLiterals,  # M508 or M539
    ):
        """
        Constructor

        @param errorCodeCalls error code for ast.Call nodes
        @type str
        @param errorCodeLiterals error code for literal nodes
        @type str
        """
        self.__errorCodeCalls = errorCodeCalls
        self.__errorCodeLiterals = errorCodeLiterals
        for nodeType in BugbearMutableLiterals + BugbearMutableComprehensions:
            setattr(
                self, f"visit_{nodeType}", self.__visitMutableLiteralOrComprehension
            )
        self.errors = []
        self.__argDepth = 0

        super().__init__()

    def __visitMutableLiteralOrComprehension(self, node):
        """
        Private method to flag mutable literals and comprehensions.

        @param node AST node to be processed
        @type ast.Dict, ast.List, ast.Set, ast.ListComp, ast.DictComp or ast.SetComp
        """
        # Flag M506 if mutable literal/comprehension is not nested.
        # We only flag these at the top level of the expression as we
        # cannot easily guarantee that nested mutable structures are not
        # made immutable by outer operations, so we prefer no false positives.
        # e.g.
        # >>> def this_is_fine(a=frozenset({"a", "b", "c"})): ...
        #
        # >>> def this_is_not_fine_but_hard_to_detect(a=(lambda x: x)([1, 2, 3]))
        #
        # We do still search for cases of B008 within mutable structures though.
        if self.__argDepth == 1:
            self.errors.append((node, self.__errorCodeCalls))

        # Check for nested functions.
        self.generic_visit(node)

    def visit_Call(self, node):
        """
        Public method to process Call nodes.

        @param node AST node to be processed
        @type ast.Call
        """
        callPath = ".".join(composeCallPath(node.func))
        if callPath in BugbearMutableCalls:
            self.errors.append((node, self.__errorCodeCalls))
            self.generic_visit(node)
            return

        if callPath in BugbearImmutableCalls:
            self.generic_visit(node)
            return

        # Check if function call is actually a float infinity/NaN literal
        if callPath == "float" and len(node.args) == 1:
            try:
                value = float(ast.literal_eval(node.args[0]))
            except Exception:  # secok
                pass
            else:
                if math.isfinite(value):
                    self.errors.append((node, self.__errorCodeLiterals))
        else:
            self.errors.append((node, self.__errorCodeLiterals))

        # Check for nested functions.
        self.generic_visit(node)

    def visit_Lambda(self, node):
        """
        Public method to process Lambda nodes.

        @param node AST node to be processed
        @type ast.Lambda
        """
        # Don't recurse into lambda expressions
        # as they are evaluated at call time.
        pass

    def visit(self, node):
        """
        Public method to traverse an AST node or a list of AST nodes.

        This is an extended method that can also handle a list of AST nodes.

        @param node AST node or list of AST nodes to be processed
        @type ast.AST or list of ast.AST
        """
        self.__argDepth += 1
        if isinstance(node, list):
            for elem in node:
                if elem is not None:
                    super().visit(elem)
        else:
            super().visit(node)
        self.__argDepth -= 1


class M520NameFinder(NameFinder):
    """
    Class to extract a name out of a tree of nodes ignoring names defined within the
    local scope of a comprehension.
    """

    def visit_GeneratorExp(self, node):
        """
        Public method to handle a generator expressions.

        @param node reference to the node to be processed
        @type ast.GeneratorExp
        """
        self.visit(node.generators)

    def visit_ListComp(self, node):
        """
        Public method  to handle a list comprehension.

        @param node reference to the node to be processed
        @type TYPE
        """
        self.visit(node.generators)

    def visit_DictComp(self, node):
        """
        Public method  to handle a dictionary comprehension.

        @param node reference to the node to be processed
        @type TYPE
        """
        self.visit(node.generators)

    def visit_comprehension(self, node):
        """
        Public method  to handle the 'for' of a comprehension.

        @param node reference to the node to be processed
        @type ast.comprehension
        """
        self.visit(node.iter)

    def visit_Lambda(self, node):
        """
        Public method  to handle a Lambda function.

        @param node reference to the node to be processed
        @type ast.Lambda
        """
        self.visit(node.body)
        for lambdaArg in node.args.args:
            self.getNames().pop(lambdaArg.arg, None)


class ReturnVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor to check return statements.
    """

    Assigns = "assigns"
    Refs = "refs"
    Returns = "returns"

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__stack = []
        self.violations = []
        self.__loopCount = 0

    @property
    def assigns(self):
        """
        Public method to get the Assign nodes.

        @return dictionary containing the node name as key and line number
            as value
        @rtype dict
        """
        return self.__stack[-1][ReturnVisitor.Assigns]

    @property
    def refs(self):
        """
        Public method to get the References nodes.

        @return dictionary containing the node name as key and line number
            as value
        @rtype dict
        """
        return self.__stack[-1][ReturnVisitor.Refs]

    @property
    def returns(self):
        """
        Public method to get the Return nodes.

        @return dictionary containing the node name as key and line number
            as value
        @rtype dict
        """
        return self.__stack[-1][ReturnVisitor.Returns]

    def visit_For(self, node):
        """
        Public method to handle a for loop.

        @param node reference to the for node to handle
        @type ast.For
        """
        self.__visitLoop(node)

    def visit_AsyncFor(self, node):
        """
        Public method to handle an async for loop.

        @param node reference to the async for node to handle
        @type ast.AsyncFor
        """
        self.__visitLoop(node)

    def visit_While(self, node):
        """
        Public method to handle a while loop.

        @param node reference to the while node to handle
        @type ast.While
        """
        self.__visitLoop(node)

    def __visitLoop(self, node):
        """
        Private method to handle loop nodes.

        @param node reference to the loop node to handle
        @type ast.For, ast.AsyncFor or ast.While
        """
        self.__loopCount += 1
        self.generic_visit(node)
        self.__loopCount -= 1

    def __visitWithStack(self, node):
        """
        Private method to traverse a given function node using a stack.

        @param node AST node to be traversed
        @type ast.FunctionDef or ast.AsyncFunctionDef
        """
        self.__stack.append(
            {
                ReturnVisitor.Assigns: defaultdict(list),
                ReturnVisitor.Refs: defaultdict(list),
                ReturnVisitor.Returns: [],
            }
        )

        self.generic_visit(node)
        self.__checkFunction(node)
        self.__stack.pop()

    def visit_FunctionDef(self, node):
        """
        Public method to handle a function definition.

        @param node reference to the node to handle
        @type ast.FunctionDef
        """
        self.__visitWithStack(node)

    def visit_AsyncFunctionDef(self, node):
        """
        Public method to handle a function definition.

        @param node reference to the node to handle
        @type ast.AsyncFunctionDef
        """
        self.__visitWithStack(node)

    def visit_Return(self, node):
        """
        Public method to handle a return node.

        @param node reference to the node to handle
        @type ast.Return
        """
        self.returns.append(node)
        self.generic_visit(node)

    def visit_Assign(self, node):
        """
        Public method to handle an assign node.

        @param node reference to the node to handle
        @type ast.Assign
        """
        if not self.__stack:
            return

        self.generic_visit(node.value)

        target = node.targets[0]
        if isinstance(target, ast.Tuple) and not isinstance(node.value, ast.Tuple):
            # skip unpacking assign
            return

        self.__visitAssignTarget(target)

    def visit_Name(self, node):
        """
        Public method to handle a name node.

        @param node reference to the node to handle
        @type ast.Name
        """
        if self.__stack:
            self.refs[node.id].append(node.lineno)

    def __visitAssignTarget(self, node):
        """
        Private method to handle an assign target node.

        @param node reference to the node to handle
        @type ast.AST
        """
        if isinstance(node, ast.Tuple):
            for elt in node.elts:
                self.__visitAssignTarget(elt)
            return

        if not self.__loopCount and isinstance(node, ast.Name):
            self.assigns[node.id].append(node.lineno)
            return

        self.generic_visit(node)

    def __checkFunction(self, node):
        """
        Private method to check a function definition node.

        @param node reference to the node to check
        @type ast.AsyncFunctionDef or ast.FunctionDef
        """
        if not self.returns or not node.body:
            return

        if len(node.body) == 1 and isinstance(node.body[-1], ast.Return):
            # skip functions that consist of `return None` only
            return

        if not self.__resultExists():
            self.__checkUnnecessaryReturnNone()
            return

        self.__checkImplicitReturnValue()
        self.__checkImplicitReturn(node.body[-1])

        for n in self.returns:
            if n.value:
                self.__checkUnnecessaryAssign(n.value)

    def __isNone(self, node):
        """
        Private method to check, if a node value is None.

        @param node reference to the node to check
        @type ast.AST
        @return flag indicating the node contains a None value
        @rtype bool
        """
        return AstUtilities.isNameConstant(node) and AstUtilities.getValue(node) is None

    def __isFalse(self, node):
        """
        Private method to check, if a node value is False.

        @param node reference to the node to check
        @type ast.AST
        @return flag indicating the node contains a False value
        @rtype bool
        """
        return (
            AstUtilities.isNameConstant(node) and AstUtilities.getValue(node) is False
        )

    def __resultExists(self):
        """
        Private method to check the existance of a return result.

        @return flag indicating the existence of a return result
        @rtype bool
        """
        for node in self.returns:
            value = node.value
            if value and not self.__isNone(value):
                return True

        return False

    def __checkImplicitReturnValue(self):
        """
        Private method to check for implicit return values.
        """
        for node in self.returns:
            if not node.value:
                self.violations.append((node, "M832"))

    def __checkUnnecessaryReturnNone(self):
        """
        Private method to check for an unnecessary 'return None' statement.
        """
        for node in self.returns:
            if self.__isNone(node.value):
                self.violations.append((node, "M831"))

    def __checkImplicitReturn(self, node):
        """
        Private method to check for an implicit return statement.

        @param node reference to the node to check
        @type ast.AST
        """
        if isinstance(node, ast.If):
            if not node.body or not node.orelse:
                self.violations.append((node, "M833"))
                return

            self.__checkImplicitReturn(node.body[-1])
            self.__checkImplicitReturn(node.orelse[-1])
            return

        if isinstance(node, (ast.For, ast.AsyncFor)) and node.orelse:
            self.__checkImplicitReturn(node.orelse[-1])
            return

        if isinstance(node, (ast.With, ast.AsyncWith)):
            self.__checkImplicitReturn(node.body[-1])
            return

        if isinstance(node, ast.Assert) and self.__isFalse(node.test):
            return

        try:
            okNodes = (ast.Return, ast.Raise, ast.While, ast.Try)
        except AttributeError:
            okNodes = (ast.Return, ast.Raise, ast.While)
        if not isinstance(node, okNodes):
            self.violations.append((node, "M833"))

    def __checkUnnecessaryAssign(self, node):
        """
        Private method to check for an unnecessary assign statement.

        @param node reference to the node to check
        @type ast.AST
        """
        if not isinstance(node, ast.Name):
            return

        varname = node.id
        returnLineno = node.lineno

        if varname not in self.assigns:
            return

        if varname not in self.refs:
            self.violations.append((node, "M834"))
            return

        if self.__hasRefsBeforeNextAssign(varname, returnLineno):
            return

        self.violations.append((node, "M834"))

    def __hasRefsBeforeNextAssign(self, varname, returnLineno):
        """
        Private method to check for references before a following assign
        statement.

        @param varname variable name to check for
        @type str
        @param returnLineno line number of the return statement
        @type int
        @return flag indicating the existence of references
        @rtype bool
        """
        beforeAssign = 0
        afterAssign = None

        for lineno in sorted(self.assigns[varname]):
            if lineno > returnLineno:
                afterAssign = lineno
                break

            if lineno <= returnLineno:
                beforeAssign = lineno

        for lineno in self.refs[varname]:
            if lineno == returnLineno:
                continue

            if afterAssign:
                if beforeAssign < lineno <= afterAssign:
                    return True

            elif beforeAssign < lineno:
                return True

        return False


class DateTimeVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor to check datetime function calls.

    Note: This class is modeled after flake8_datetimez checker.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.violations = []

    def __getFromKeywords(self, keywords, name):
        """
        Private method to get a keyword node given its name.

        @param keywords list of keyword argument nodes
        @type list of ast.AST
        @param name name of the keyword node
        @type str
        @return keyword node
        @rtype ast.AST
        """
        for keyword in keywords:
            if keyword.arg == name:
                return keyword

        return None

    def visit_Call(self, node):
        """
        Public method to handle a function call.

        Every datetime related function call is check for use of the naive
        variant (i.e. use without TZ info).

        @param node reference to the node to be processed
        @type ast.Call
        """
        # datetime.something()
        isDateTimeClass = (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "datetime"
        )

        # datetime.datetime.something()
        isDateTimeModuleAndClass = (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "datetime"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "datetime"
        )

        if isDateTimeClass:
            if node.func.attr == "datetime":
                # datetime.datetime(2000, 1, 1, 0, 0, 0, 0,
                #                   datetime.timezone.utc)
                isCase1 = len(node.args) >= 8 and not (
                    AstUtilities.isNameConstant(node.args[7])
                    and AstUtilities.getValue(node.args[7]) is None
                )

                # datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
                tzinfoKeyword = self.__getFromKeywords(node.keywords, "tzinfo")
                isCase2 = tzinfoKeyword is not None and not (
                    AstUtilities.isNameConstant(tzinfoKeyword.value)
                    and AstUtilities.getValue(tzinfoKeyword.value) is None
                )

                if not (isCase1 or isCase2):
                    self.violations.append((node, "M301"))

            elif node.func.attr == "time":
                # time(12, 10, 45, 0, datetime.timezone.utc)
                isCase1 = len(node.args) >= 5 and not (
                    AstUtilities.isNameConstant(node.args[4])
                    and AstUtilities.getValue(node.args[4]) is None
                )

                # datetime.time(12, 10, 45, tzinfo=datetime.timezone.utc)
                tzinfoKeyword = self.__getFromKeywords(node.keywords, "tzinfo")
                isCase2 = tzinfoKeyword is not None and not (
                    AstUtilities.isNameConstant(tzinfoKeyword.value)
                    and AstUtilities.getValue(tzinfoKeyword.value) is None
                )

                if not (isCase1 or isCase2):
                    self.violations.append((node, "M321"))

            elif node.func.attr == "date":
                self.violations.append((node, "M311"))

        if isDateTimeClass or isDateTimeModuleAndClass:
            if node.func.attr == "today":
                self.violations.append((node, "M302"))

            elif node.func.attr == "utcnow":
                self.violations.append((node, "M303"))

            elif node.func.attr == "utcfromtimestamp":
                self.violations.append((node, "M304"))

            elif node.func.attr in "now":
                # datetime.now(UTC)
                isCase1 = (
                    len(node.args) == 1
                    and len(node.keywords) == 0
                    and not (
                        AstUtilities.isNameConstant(node.args[0])
                        and AstUtilities.getValue(node.args[0]) is None
                    )
                )

                # datetime.now(tz=UTC)
                tzKeyword = self.__getFromKeywords(node.keywords, "tz")
                isCase2 = tzKeyword is not None and not (
                    AstUtilities.isNameConstant(tzKeyword.value)
                    and AstUtilities.getValue(tzKeyword.value) is None
                )

                if not (isCase1 or isCase2):
                    self.violations.append((node, "M305"))

            elif node.func.attr == "fromtimestamp":
                # datetime.fromtimestamp(1234, UTC)
                isCase1 = (
                    len(node.args) == 2
                    and len(node.keywords) == 0
                    and not (
                        AstUtilities.isNameConstant(node.args[1])
                        and AstUtilities.getValue(node.args[1]) is None
                    )
                )

                # datetime.fromtimestamp(1234, tz=UTC)
                tzKeyword = self.__getFromKeywords(node.keywords, "tz")
                isCase2 = tzKeyword is not None and not (
                    AstUtilities.isNameConstant(tzKeyword.value)
                    and AstUtilities.getValue(tzKeyword.value) is None
                )

                if not (isCase1 or isCase2):
                    self.violations.append((node, "M306"))

            elif node.func.attr == "strptime":
                # datetime.strptime(...).replace(tzinfo=UTC)
                parent = getattr(node, "_dtCheckerParent", None)
                pparent = getattr(parent, "_dtCheckerParent", None)
                if not (
                    isinstance(parent, ast.Attribute) and parent.attr == "replace"
                ) or not isinstance(pparent, ast.Call):
                    isCase1 = False
                else:
                    tzinfoKeyword = self.__getFromKeywords(pparent.keywords, "tzinfo")
                    isCase1 = tzinfoKeyword is not None and not (
                        AstUtilities.isNameConstant(tzinfoKeyword.value)
                        and AstUtilities.getValue(tzinfoKeyword.value) is None
                    )

                if not isCase1:
                    self.violations.append((node, "M307"))

            elif node.func.attr == "fromordinal":
                self.violations.append((node, "M308"))

        # date.something()
        isDateClass = (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "date"
        )

        # datetime.date.something()
        isDateModuleAndClass = (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "date"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "datetime"
        )

        if isDateClass or isDateModuleAndClass:
            if node.func.attr == "today":
                self.violations.append((node, "M312"))

            elif node.func.attr == "fromtimestamp":
                self.violations.append((node, "M313"))

            elif node.func.attr == "fromordinal":
                self.violations.append((node, "M314"))

            elif node.func.attr == "fromisoformat":
                self.violations.append((node, "M315"))

        self.generic_visit(node)


class SysVersionVisitor(ast.NodeVisitor):
    """
    Class implementing a node visitor to check the use of sys.version and
    sys.version_info.

    Note: This class is modeled after flake8-2020 checker.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.violations = []
        self.__fromImports = {}

    def visit_ImportFrom(self, node):
        """
        Public method to handle a from ... import ... statement.

        @param node reference to the node to be processed
        @type ast.ImportFrom
        """
        for alias in node.names:
            if node.module is not None and not alias.asname:
                self.__fromImports[alias.name] = node.module

        self.generic_visit(node)

    def __isSys(self, attr, node):
        """
        Private method to check for a reference to sys attribute.

        @param attr attribute name
        @type str
        @param node reference to the node to be checked
        @type ast.Node
        @return flag indicating a match
        @rtype bool
        """
        match = False
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "sys"
            and node.attr == attr
        ) or (
            isinstance(node, ast.Name)
            and node.id == attr
            and self.__fromImports.get(node.id) == "sys"
        ):
            match = True

        return match

    def __isSysVersionUpperSlice(self, node, n):
        """
        Private method to check the upper slice of sys.version.

        @param node reference to the node to be checked
        @type ast.Node
        @param n slice value to check against
        @type int
        @return flag indicating a match
        @rtype bool
        """
        return (
            self.__isSys("version", node.value)
            and isinstance(node.slice, ast.Slice)
            and node.slice.lower is None
            and AstUtilities.isNumber(node.slice.upper)
            and AstUtilities.getValue(node.slice.upper) == n
            and node.slice.step is None
        )

    def visit_Subscript(self, node):
        """
        Public method to handle a subscript.

        @param node reference to the node to be processed
        @type ast.Subscript
        """
        if self.__isSysVersionUpperSlice(node, 1):
            self.violations.append((node.value, "M423"))
        elif self.__isSysVersionUpperSlice(node, 3):
            self.violations.append((node.value, "M401"))
        elif (
            self.__isSys("version", node.value)
            and isinstance(node.slice, ast.Index)
            and AstUtilities.isNumber(node.slice.value)
            and AstUtilities.getValue(node.slice.value) == 2
        ):
            self.violations.append((node.value, "M402"))
        elif (
            self.__isSys("version", node.value)
            and isinstance(node.slice, ast.Index)
            and AstUtilities.isNumber(node.slice.value)
            and AstUtilities.getValue(node.slice.value) == 0
        ):
            self.violations.append((node.value, "M421"))

        self.generic_visit(node)

    def visit_Compare(self, node):
        """
        Public method to handle a comparison.

        @param node reference to the node to be processed
        @type ast.Compare
        """
        if (
            isinstance(node.left, ast.Subscript)
            and self.__isSys("version_info", node.left.value)
            and isinstance(node.left.slice, ast.Index)
            and AstUtilities.isNumber(node.left.slice.value)
            and AstUtilities.getValue(node.left.slice.value) == 0
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
            and AstUtilities.isNumber(node.comparators[0])
            and AstUtilities.getValue(node.comparators[0]) == 3
        ):
            self.violations.append((node.left, "M411"))
        elif (
            self.__isSys("version", node.left)
            and len(node.ops) == 1
            and isinstance(node.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE))
            and AstUtilities.isString(node.comparators[0])
        ):
            if len(AstUtilities.getValue(node.comparators[0])) == 1:
                errorCode = "M422"
            else:
                errorCode = "M403"
            self.violations.append((node.left, errorCode))
        elif (
            isinstance(node.left, ast.Subscript)
            and self.__isSys("version_info", node.left.value)
            and isinstance(node.left.slice, ast.Index)
            and AstUtilities.isNumber(node.left.slice.value)
            and AstUtilities.getValue(node.left.slice.value) == 1
            and len(node.ops) == 1
            and isinstance(node.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE))
            and AstUtilities.isNumber(node.comparators[0])
        ):
            self.violations.append((node, "M413"))
        elif (
            isinstance(node.left, ast.Attribute)
            and self.__isSys("version_info", node.left.value)
            and node.left.attr == "minor"
            and len(node.ops) == 1
            and isinstance(node.ops[0], (ast.Lt, ast.LtE, ast.Gt, ast.GtE))
            and AstUtilities.isNumber(node.comparators[0])
        ):
            self.violations.append((node, "M414"))

        self.generic_visit(node)

    def visit_Attribute(self, node):
        """
        Public method to handle an attribute.

        @param node reference to the node to be processed
        @type ast.Attribute
        """
        if (
            isinstance(node.value, ast.Name)
            and node.value.id == "six"
            and node.attr == "PY3"
        ):
            self.violations.append((node, "M412"))

        self.generic_visit(node)

    def visit_Name(self, node):
        """
        Public method to handle an name.

        @param node reference to the node to be processed
        @type ast.Name
        """
        if node.id == "PY3" and self.__fromImports.get(node.id) == "six":
            self.violations.append((node, "M412"))

        self.generic_visit(node)


#
# eflag: noqa = M891
