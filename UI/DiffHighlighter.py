# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a syntax highlighter for unified and context diff outputs.
"""

from eric7.EricGui.EricGenericDiffHighlighter import (
    TERMINAL,
    EricGenericDiffHighlighter,
)


class DiffHighlighter(EricGenericDiffHighlighter):
    """
    Class implementing a diff highlighter for Git.
    """

    def __init__(self, doc):
        """
        Constructor

        @param doc reference to the text document
        @type QTextDocument
        """
        super().__init__(doc)

    def generateRules(self):
        """
        Public method to generate the rule set.
        """
        diffHeaderBold = self.makeFormat(
            fg=self.textColor, bg=self.headerColor, bold=True
        )
        diffContext = self.makeFormat(fg=self.textColor, bg=self.contextColor)

        diffAdded = self.makeFormat(fg=self.textColor, bg=self.addedColor)
        diffRemoved = self.makeFormat(fg=self.textColor, bg=self.removedColor)
        diffReplaced = self.makeFormat(fg=self.textColor, bg=self.replacedColor)

        diffBarRegex = TERMINAL(r"^\*+$")

        diffOldRegex = TERMINAL(r"^--- ")
        diffNewRegex = TERMINAL(r"^\+\+\+ |^\*\*\*")
        diffContextRegex = TERMINAL(r"^@@ ")

        diffAddedRegex = TERMINAL(r"^[+>]")
        diffRemovedRegex = TERMINAL(r"^[-<]")
        diffReplacedRegex = TERMINAL(r"^!")

        self.createRules(
            (diffBarRegex, diffHeaderBold),
            (diffOldRegex, diffRemoved),
            (diffNewRegex, diffAdded),
            (diffContextRegex, diffContext),
            (diffAddedRegex, diffAdded),
            (diffRemovedRegex, diffRemoved),
            (diffReplacedRegex, diffReplaced),
        )
