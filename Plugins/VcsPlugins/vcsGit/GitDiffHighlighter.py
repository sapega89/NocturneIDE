# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a syntax highlighter for diff outputs.
"""

from PyQt6.QtGui import QColor

from eric7.EricGui.EricGenericDiffHighlighter import (
    TERMINAL,
    EricGenericDiffHighlighter,
)


class GitDiffHighlighter(EricGenericDiffHighlighter):
    """
    Class implementing a diff highlighter for Git.
    """

    def __init__(self, doc, whitespace=True):
        """
        Constructor

        @param doc reference to the text document
        @type QTextDocument
        @param whitespace flag indicating to highlight whitespace
            at the end of a line
        @type bool
        """
        self.whitespace = whitespace

        super().__init__(doc)

    def generateRules(self):
        """
        Public method to generate the rule set.
        """
        diffHeader = self.makeFormat(fg=self.textColor, bg=self.headerColor)
        diffHeaderBold = self.makeFormat(
            fg=self.textColor, bg=self.headerColor, bold=True
        )
        diffContext = self.makeFormat(fg=self.textColor, bg=self.contextColor)

        diffAdded = self.makeFormat(fg=self.textColor, bg=self.addedColor)
        diffRemoved = self.makeFormat(fg=self.textColor, bg=self.removedColor)

        if self.whitespace:
            try:
                badWhitespace = self.makeFormat(
                    fg=self.textColor, bg=self.whitespaceColor
                )
            except AttributeError:
                badWhitespace = self.makeFormat(
                    fg=self.textColor, bg=QColor(255, 0, 0, 192)
                )

        # We specify the whitespace rule last so that it is
        # applied after the diff addition/removal rules.
        diffOldRegex = TERMINAL(r"^--- ")
        diffNewRegex = TERMINAL(r"^\+\+\+ ")
        diffContextRegex = TERMINAL(r"^@@ ")

        diffHeader1Regex = TERMINAL(r"^diff --git a/.*b/.*")
        diffHeader2Regex = TERMINAL(r"^index \S+\.\.\S+")
        diffHeader3Regex = TERMINAL(r"^new file mode")
        diffHeader4Regex = TERMINAL(r"^deleted file mode")

        diffAddedRegex = TERMINAL(r"^\+")
        diffRemovedRegex = TERMINAL(r"^-")
        diffBarRegex = TERMINAL(r"^([ ]+.*)(\|[ ]+\d+[ ]+[+-]+)$")
        diffStsRegex = r"(.+\|.+?)(\d+)(.+?)([\+]*?)([-]*?)$"
        diffSummaryRegex = (
            r"(\s+\d+ files changed[^\d]*)"
            r"(:?\d+ insertions[^\d]*)"
            r"(:?\d+ deletions.*)$"
        )

        if self.whitespace:
            self.createRules((r"(..*?)(\s+)$", (None, badWhitespace)))
        self.createRules(
            (diffOldRegex, diffRemoved),
            (diffNewRegex, diffAdded),
            (diffContextRegex, diffContext),
            (diffBarRegex, (diffHeaderBold, diffHeader)),
            (diffHeader1Regex, diffHeader),
            (diffHeader2Regex, diffHeader),
            (diffHeader3Regex, diffHeader),
            (diffHeader4Regex, diffHeader),
            (diffAddedRegex, diffAdded),
            (diffRemovedRegex, diffRemoved),
            (diffStsRegex, (None, diffHeader, None, diffHeader, diffHeader)),
            (diffSummaryRegex, (diffHeader, diffHeader, diffHeader)),
        )
