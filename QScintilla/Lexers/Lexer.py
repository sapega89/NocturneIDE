# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the lexer mixin class.
"""

from eric7 import Preferences


class Lexer:
    """
    Class to implement the lexer mixin class.
    """

    def __init__(self):
        """
        Constructor
        """
        self.commentString = ""
        self.streamCommentString = {"start": "", "end": ""}
        self.boxCommentString = {"start": "", "middle": "", "end": ""}

        # last indented line wrapper
        self.lastIndented = -1
        self.lastIndentedIndex = -1

        # always keep tabs (for languages where tabs are esential
        self._alwaysKeepTabs = False

        # descriptions for keyword sets
        self.keywordSetDescriptions = []

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        # default implementation is a do nothing
        return

    def commentStr(self):
        """
        Public method to return the comment string.

        @return comment string
        @rtype str
        """
        return self.commentString

    def canBlockComment(self):
        """
        Public method to determine, whether the lexer language supports a
        block comment.

        @return flag indicating block comment is available
        @rtype bool
        """
        return self.commentString != ""

    def streamCommentStr(self):
        """
        Public method to return the stream comment strings.

        @return dictionary containing the start and end stream comment strings
        @rtype dict of {"start": str, "end": str}
        """
        return self.streamCommentString

    def canStreamComment(self):
        """
        Public method to determine, whether the lexer language supports a
        stream comment.

        @return flag indicating stream comment is available
        @rtype bool
        """
        return (
            self.streamCommentString["start"] != ""
            and self.streamCommentString["end"] != ""
        )

    def boxCommentStr(self):
        """
        Public method to return the box comment strings.

        @return dictionary containing the start, middle and end box comment strings
        @rtype dict of {"start": str, "middle": str, "end": str}
        """
        return self.boxCommentString

    def canBoxComment(self):
        """
        Public method to determine, whether the lexer language supports a
        box comment.

        @return flag box comment is available
        @rtype bool
        """
        return (
            (self.boxCommentString["start"] != "")
            and (self.boxCommentString["middle"] != "")
            and (self.boxCommentString["end"] != "")
        )

    def alwaysKeepTabs(self):
        """
        Public method to check, if tab conversion is allowed.

        @return flag indicating to keep tabs
        @rtype bool
        """
        return self._alwaysKeepTabs

    def hasSmartIndent(self):
        """
        Public method indicating whether lexer can do smart indentation.

        @return flag indicating availability of smartIndentLine and
            smartIndentSelection methods
        @rtype bool
        """
        return hasattr(self, "getIndentationDifference")

    def smartIndentLine(self, editor):
        """
        Public method to handle smart indentation for a line.

        @param editor reference to the QScintilla editor object
        @type Editor
        """
        cline, cindex = editor.getCursorPosition()

        # get leading spaces
        lead_spaces = editor.indentation(cline)

        # get the indentation difference
        indentDifference = self.getIndentationDifference(cline, editor)

        if indentDifference != 0:
            editor.setIndentation(cline, lead_spaces + indentDifference)
            editor.setCursorPosition(cline, cindex + indentDifference)

        self.lastIndented = cline

    def smartIndentSelection(self, editor):
        """
        Public method to handle smart indentation for a selection of lines.

        Note: The assumption is, that the first line determines the new
              indentation level.

        @param editor reference to the QScintilla editor object
        @type Editor
        """
        if not editor.hasSelectedText():
            return

        # get the selection
        lineFrom, indexFrom, lineTo, indexTo = editor.getSelection()
        if lineFrom != self.lastIndented:
            self.lastIndentedIndex = indexFrom

        endLine = lineTo if indexTo else lineTo - 1

        # get the indentation difference
        indentDifference = self.getIndentationDifference(lineFrom, editor)

        editor.beginUndoAction()
        # iterate over the lines
        for line in range(lineFrom, endLine + 1):
            editor.setIndentation(line, editor.indentation(line) + indentDifference)
        editor.endUndoAction()

        indexStart = indexFrom + indentDifference if self.lastIndentedIndex != 0 else 0
        if indexStart < 0:
            indexStart = 0
        indexEnd = indexTo != 0 and (indexTo + indentDifference) or 0
        if indexEnd < 0:
            indexEnd = 0
        editor.setSelection(lineFrom, indexStart, lineTo, indexEnd)

        self.lastIndented = lineFrom

    def autoCompletionWordSeparators(self):
        """
        Public method to return the list of separators for autocompletion.

        @return list of separators
        @rtype list of str
        """
        return []

    def isCommentStyle(self, style):  # noqa: U100
        """
        Public method to check, if a style is a comment style.

        @param style style to check (unused)
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return True

    def isStringStyle(self, style):  # noqa: U100
        """
        Public method to check, if a style is a string style.

        @param style style to check (unused)
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return True

    def keywords(self, kwSet):
        """
        Public method to get the keywords.

        @param kwSet number of the keyword set
        @type int
        @return space separated list of keywords
        @rtype str or None
        """
        keywords_ = Preferences.getEditorKeywords(self.language())
        if keywords_ and len(keywords_) > kwSet:
            kw = keywords_[kwSet]
            if kw == "":
                return self.defaultKeywords(kwSet)
            else:
                return kw
        else:
            return self.defaultKeywords(kwSet)

    def keywordsDescription(self, kwSet):
        """
        Public method to get the description for a keywords set.

        @param kwSet number of the keyword set
        @type int
        @return description of the keyword set
        @rtype str
        """
        if kwSet > len(self.keywordSetDescriptions):
            return ""
        else:
            return self.keywordSetDescriptions[kwSet - 1]

    def defaultKeywords(self, kwSet):  # noqa: U100
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set (unused)
        @type int
        @return space separated list of keywords
        @rtype str or None
        """
        return None  # __IGNORE_WARNING_M831__

    def maximumKeywordSet(self):
        """
        Public method to get the maximum keyword set.

        Note: A return value of 0 indicates to determine this dynamically.

        @return maximum keyword set
        @rtype int
        """
        return len(self.keywordSetDescriptions)

    def lexerName(self):
        """
        Public method to return the lexer name.

        @return lexer name
        @rtype str
        """
        return self.lexer()

    def hasSubstyles(self):
        """
        Public method to indicate the support of sub-styles.

        @return flag indicating sub-styling support
        @rtype bool
        """
        return False
