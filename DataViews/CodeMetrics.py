# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

#
# Code mainly borrowed from the Pythius package which is
# Copyright (c) 2001 by Jürgen Hermann <jh@web.de>
#

"""
Module implementing a simple Python code metrics analyzer.

@exception ValueError the tokenize module is too old
"""


import io
import keyword
import os
import token
import tokenize

from dataclasses import dataclass

from eric7 import Utilities
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities

KEYWORD = token.NT_OFFSET + 1
COMMENT = tokenize.COMMENT
INDENT = token.INDENT
DEDENT = token.DEDENT
NEWLINE = token.NEWLINE
EMPTY = tokenize.NL


@dataclass
class Token:
    """
    Class to store the token related info.
    """

    type: int
    text: str
    row: int
    col: int
    line: str


class Parser:
    """
    Class used to parse the source code of a Python file.
    """

    def parse(self, text):
        """
        Public method used to parse the source code.

        @param text source code as read from a Python source file
        @type str
        """
        self.tokenlist = []

        # convert eols
        text = Utilities.convertLineEnds(text, os.linesep)

        if not text.endswith(os.linesep):
            text = "{0}{1}".format(text, os.linesep)

        self.lines = text.count(os.linesep)

        source = io.BytesIO(text.encode("utf-8"))
        try:
            gen = tokenize.tokenize(source.readline)
            for toktype, toktext, start, _end, line in gen:
                (srow, scol) = start
                if toktype in [token.NEWLINE, tokenize.NL]:
                    self.__addToken(toktype, os.linesep, srow, scol, line)
                elif toktype in [token.INDENT, token.DEDENT]:
                    self.__addToken(toktype, "", srow, scol, line)
                elif toktype == token.NAME and keyword.iskeyword(toktext):
                    toktype = KEYWORD
                    self.__addToken(toktype, toktext, srow, scol, line)
                else:
                    self.__addToken(toktype, toktext, srow, scol, line)
        except tokenize.TokenError as msg:
            print("Token Error: {0}".format(str(msg)))
            # __IGNORE_WARNING_M801__
            return

        return

    def __addToken(self, toktype, toktext, srow, scol, line):
        """
        Private method used to add a token to our list of tokens.

        @param toktype the type of the token
        @type int
        @param toktext the text of the token
        @type str
        @param srow starting row of the token
        @type int
        @param scol starting column of the token
        @type int
        @param line logical line the token was found
        @type str
        """
        self.tokenlist.append(
            Token(type=toktype, text=toktext, row=srow, col=scol, line=line)
        )


class SourceStat:
    """
    Class used to calculate and store the source code statistics.
    """

    def __init__(self):
        """
        Constructor
        """
        self.identifiers = []
        # list of identifiers in order of appearance
        self.active = [("TOTAL ", -1, 0)]
        # stack of active identifiers and indent levels
        self.counters = {}
        # counters per identifier
        self.indent_level = 0

    def indent(self):
        """
        Public method used to increment the indentation level.
        """
        self.indent_level += 1

    def dedent(self, tok):
        """
        Public method used to decrement the indentation level.

        @param tok the token to be processed
        @type Token
        @exception ValueError raised to indicate an invalid indentation level
        """
        self.indent_level -= 1
        if self.indent_level < 0:
            raise ValueError("INTERNAL ERROR: Negative indent level")

        # remove identifiers of a higher indentation
        while self.active and self.active[-1][1] >= self.indent_level:
            counters = self.counters.setdefault(self.active[-1][0], {})
            counters["start"] = self.active[-1][2]
            counters["end"] = tok.row - 1
            counters["lines"] = tok.row - self.active[-1][2]
            del self.active[-1]

    def push(self, identifier, row):
        """
        Public method used to store an identifier.

        @param identifier the identifier to be remembered
        @type str
        @param row row, the identifier is defined in
        @type int
        """
        qualified = (
            self.active[-1][0] + "." + identifier
            if len(self.active) > 1 and self.indent_level > self.active[-1][1]
            else identifier
        )
        self.active.append((qualified, self.indent_level, row))
        self.identifiers.append(qualified)

    def inc(self, key, value=1):
        """
        Public method used to increment the value of a key.

        @param key key to be incremented
        @type str
        @param value the increment
        @type int
        """
        for counterId, _level, _row in self.active:
            counters = self.counters.setdefault(counterId, {})
            counters[key] = counters.setdefault(key, 0) + value

    def getCounter(self, counterId, key):
        """
        Public method used to get a specific counter value.

        @param counterId id of the counter
        @type str
        @param key key of the value to be retrieved
        @type str
        @return the value of the requested counter
        @rtype int
        """
        return self.counters.get(counterId, {}).get(key, 0)


def summarize(total, key, value):
    """
    Module function used to collect overall statistics.

    @param total dictionary of overall statistics
    @type dict
    @param key key to be summarized
    @type str
    @param value value to be added to the overall statistics
    @type int
    @return the value added to the overall statistics
    @rtype int
    """
    total[key] = total.setdefault(key, 0) + value
    return value


def analyze(filename, total):
    """
    Module function used analyze the source of a Python file.

    @param filename name of the Python file to be analyzed
    @type str
    @param total dictionary receiving the overall code statistics
    @type dict
    @return a statistics object with the collected code statistics
    @rtype SourceStat
    """
    try:
        if FileSystemUtilities.isRemoteFileName(filename):
            remotefsInterface = (
                ericApp().getObject("EricServer").getServiceInterface("FileSystem")
            )
            text = remotefsInterface.readEncodedFile(filename)[0]
        else:
            text = Utilities.readEncodedFile(filename)[0]
    except (OSError, UnicodeError):
        return SourceStat()

    parser = Parser()
    parser.parse(text)

    stats = SourceStat()
    stats.inc("lines", parser.lines)
    for idx in range(len(parser.tokenlist)):
        tok = parser.tokenlist[idx]

        # counting
        if tok.type == NEWLINE:
            stats.inc("nloc")
        elif tok.type == COMMENT:
            stats.inc("comments")
            if tok.line.strip() == tok.text:
                stats.inc("commentlines")
        elif tok.type == EMPTY:
            if parser.tokenlist[idx - 1].type == token.OP:
                stats.inc("nloc")
            elif parser.tokenlist[idx - 1].type == COMMENT:
                continue
            else:
                stats.inc("empty")
        elif tok.type == INDENT:
            stats.indent()
        elif tok.type == DEDENT:
            stats.dedent(tok)
        elif tok.type == KEYWORD and tok.text in ("class", "def"):
            stats.push(parser.tokenlist[idx + 1].text, tok.row)

    # collect overall statistics
    summarize(total, "lines", parser.lines)
    summarize(total, "bytes", len(text))
    summarize(total, "comments", stats.getCounter("TOTAL ", "comments"))
    summarize(total, "commentlines", stats.getCounter("TOTAL ", "commentlines"))
    summarize(total, "empty lines", stats.getCounter("TOTAL ", "empty"))
    summarize(total, "non-commentary lines", stats.getCounter("TOTAL ", "nloc"))

    return stats
