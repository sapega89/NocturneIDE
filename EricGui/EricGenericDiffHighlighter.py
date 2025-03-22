# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a syntax highlighter for diff outputs.
"""

import re

from PyQt6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat


def TERMINAL(pattern):
    """
    Function to mark a pattern as the final one to search for.

    @param pattern pattern to be marked
    @type str
    @return marked pattern
    @rtype str
    """
    return "__TERMINAL__:{0}".format(pattern)


# Cache the results of re.compile for performance reasons
_REGEX_CACHE = {}


class EricGenericDiffHighlighter(QSyntaxHighlighter):
    """
    Class implementing a generic diff highlighter.
    """

    def __init__(self, doc):
        """
        Constructor

        @param doc reference to the text document
        @type QTextDocument
        """
        super().__init__(doc)

    def createRules(self, *rules):
        """
        Public method to create the highlighting rules.

        @param rules set of highlighting rules (list of tuples of rule
            pattern and highlighting format)
        @type set of tuple of (str, QTextCharFormat)
        """
        for _idx, ruleFormat in enumerate(rules):
            rule, formats = ruleFormat
            terminal = rule.startswith(TERMINAL(""))
            if terminal:
                rule = rule[len(TERMINAL("")) :]
            try:
                regex = _REGEX_CACHE[rule]
            except KeyError:
                regex = _REGEX_CACHE[rule] = re.compile(rule)
            self._rules.append((regex, formats, terminal))

    def formats(self, line):
        """
        Public method to determine the highlighting formats for a line of
        text.

        @param line text line to be highlighted
        @type str
        @return list of matched highlighting rules (list of tuples of match
            object and format)
        @rtype list of tuple of (re.Match, QTextCharFormat)
        """
        matched = []
        for rx, formats, terminal in self._rules:
            match = rx.match(line)
            if not match:
                continue
            matched.append([match, formats])
            if terminal:
                return matched

        return matched

    def makeFormat(self, fg=None, bg=None, bold=False):
        """
        Public method to generate a format definition.

        @param fg foreground color
        @type QColor
        @param bg background color
        @type QColor
        @param bold flag indicating bold text
        @type bool
        @return format definiton
        @rtype QTextCharFormat
        """
        font = QFont(self.baseFont)
        charFormat = QTextCharFormat()
        charFormat.setFontFamilies([font.family()])
        charFormat.setFontPointSize(font.pointSize())

        if fg:
            charFormat.setForeground(fg)

        if bg:
            charFormat.setBackground(bg)

        if bold:
            charFormat.setFontWeight(QFont.Weight.Bold)

        return charFormat

    def highlightBlock(self, text):
        """
        Public method to highlight a block of text.

        @param text text to be highlighted
        @type str
        """
        formats = self.formats(text)
        if not formats:
            # nothing matched
            self.setFormat(0, len(text), self.normalFormat)
            return

        for match, formatStr in formats:
            start = match.start()
            groups = match.groups()

            # No groups in the regex, assume this is a single rule
            # that spans the entire line
            if not groups:
                self.setFormat(0, len(text), formatStr)
                continue

            # Groups exist, rule is a tuple corresponding to group
            for groupIndex, group in enumerate(groups):
                if not group:
                    # empty match
                    continue

                # allow None as a no-op format
                length = len(group)
                if formatStr[groupIndex]:
                    self.setFormat(start, start + length, formatStr[groupIndex])
                start += length

    def regenerateRules(self, colors, font):
        """
        Public method to initialize or regenerate the syntax highlighter rules.

        @param colors dictionary containing the different color values (keys are
            "text", "added", "removed","replaced", "context", "header", "whitespace")
        @type dict[str: QColor]
        @param font font
        @type QFont
        """
        self.baseFont = font
        self.normalFormat = self.makeFormat()

        self.textColor = colors["text"]
        self.addedColor = colors["added"]
        self.removedColor = colors["removed"]
        self.replacedColor = colors["replaced"]
        self.contextColor = colors["context"]
        self.headerColor = colors["header"]
        self.whitespaceColor = colors["whitespace"]

        self._rules = []
        self.generateRules()

    def generateRules(self):
        """
        Public method to generate the rule set.

        Note: This method must me implemented by derived syntax
        highlighters.
        """
        pass
