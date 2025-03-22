# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Markdown markup provider.
"""

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QDialog, QInputDialog

from .MarkupBase import MarkupBase


class MarkdownProvider(MarkupBase):
    """
    Class implementing the Markdown markup provider.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

    def kind(self):
        """
        Public method to get the markup kind.

        @return string with markup kind
        @rtype str
        """
        return "markdown"

    def hasBold(self):
        """
        Public method to indicate the availability of bold markup.

        @return flag indicating the availability of bold markup
        @rtype bool
        """
        return True

    def bold(self, editor):
        """
        Public method to generate bold text.

        @param editor reference to the editor to work on
        @type Editor
        """
        self.__insertMarkup("**", editor)

    def hasItalic(self):
        """
        Public method to indicate the availability of italic markup.

        @return flag indicating the availability of italic markup
        @rtype bool
        """
        return True

    def italic(self, editor):
        """
        Public method to generate italic text.

        @param editor reference to the editor to work on
        @type Editor
        """
        self.__insertMarkup("_", editor)

    def hasStrikethrough(self):
        """
        Public method to indicate the availability of strikethrough markup.

        @return flag indicating the availability of strikethrough markup
        @rtype bool
        """
        return True

    def strikethrough(self, editor):
        """
        Public method to generate strikethrough text.

        @param editor reference to the editor to work on
        @type Editor
        """
        self.__insertMarkup("~~", editor)

    def headerLevels(self):
        """
        Public method to determine the available header levels.

        @return supported header levels
        @rtype int
        """
        return 6

    def header(self, editor, level):
        """
        Public method to generate a header.

        @param editor reference to the editor to work on
        @type Editor
        @param level header level
        @type int
        """
        if editor is None or level > self.headerLevels():
            return

        editor.beginUndoAction()
        cline, cindex = editor.getCursorPosition()
        editor.insertAt(level * "#" + " ", cline, 0)
        editor.setCursorPosition(cline, level + 1)
        editor.endUndoAction()

    def hasCode(self):
        """
        Public method to indicate the availability of inline code markup.

        @return flag indicating the availability of inline code markup
        @rtype bool
        """
        return True

    def code(self, editor):
        """
        Public method to generate inline code text.

        @param editor reference to the editor to work on
        @type Editor
        """
        self.__insertMarkup("`", editor)

    def hasCodeBlock(self):
        """
        Public method to indicate the availability of code block markup.

        @return flag indicating the availability of code block markup
        @rtype bool
        """
        return True

    def codeBlock(self, editor):
        """
        Public method to generate code block text.

        @param editor reference to the editor to work on
        @type Editor
        """
        if editor is None:
            return

        lineSeparator = editor.getLineSeparator()
        editor.beginUndoAction()
        if editor.hasSelectedText():
            newText = "```{0}{1}```{0}".format(lineSeparator, editor.selectedText())
            editor.replaceSelectedText(newText)
        else:
            editor.insert("```{0}{0}```{0}".format(lineSeparator))
            cline, cindex = editor.getCursorPosition()
            editor.setCursorPosition(cline + 1, 0)
        editor.endUndoAction()

    def __insertMarkup(self, markup, editor):
        """
        Private method to insert the specified markup.

        If the editor has selected text, this text is enclosed by the given
        markup. If no text is selected, the markup is inserted at the cursor
        position and the cursor is positioned in between.

        @param markup markup string to be inserted
        @type str
        @param editor reference to the editor to work on
        @type Editor
        """
        if editor is None:
            return

        editor.beginUndoAction()
        if editor.hasSelectedText():
            newText = "{0}{1}{0}".format(markup, editor.selectedText())
            editor.replaceSelectedText(newText)
        else:
            editor.insert(2 * markup)
            cline, cindex = editor.getCursorPosition()
            editor.setCursorPosition(cline, cindex + len(markup))
        editor.endUndoAction()

    def hasHyperlink(self):
        """
        Public method to indicate the availability of hyperlink markup.

        @return flag indicating the availability of hyperlink markup
        @rtype bool
        """
        return True

    def hyperlink(self, editor):
        """
        Public method to generate hyperlink text.

        @param editor reference to the editor to work on
        @type Editor
        """
        from .HyperlinkMarkupDialog import HyperlinkMarkupDialog

        if editor is None:
            return

        dlg = HyperlinkMarkupDialog(False, True, parent=editor)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text, target, title = dlg.getData()

            link = "[{0}]".format(text)
            if target and title:
                link = '{0}({1} "{2}")'.format(link, target, title)
            elif target:
                link = "{0}({1})".format(link, target)
            elif title:
                link = '{0}("{1}")'.format(link, title)

            editor.beginUndoAction()
            cline, cindex = editor.getCursorPosition()
            editor.insert(link)
            editor.setCursorPosition(cline, cindex + len(link))
            editor.endUndoAction()

    def hasLine(self):
        """
        Public method to indicate the availability of a horizontal line markup.

        @return flag indicating the availability of a horizontal line markup
        @rtype bool
        """
        return True

    def line(self, editor):
        """
        Public method to generate a horizontal line text.

        @param editor reference to the editor to work on
        @type Editor
        """
        if editor is None:
            return

        lineSeparator = editor.getLineSeparator()
        editor.beginUndoAction()
        markup = "{0}-----{0}{0}".format(lineSeparator)
        editor.insert(markup)
        cline, cindex = editor.getCursorPosition()
        editor.setCursorPosition(cline + 3, 0)
        editor.endUndoAction()

    def hasQuote(self):
        """
        Public method to indicate the availability of block quote markup.

        @return flag indicating the availability of block quote markup
        @rtype bool
        """
        return True

    def quote(self, editor):
        """
        Public method to generate block quote text.

        @param editor reference to the editor to work on
        @type Editor
        """
        if editor is None:
            return

        editor.beginUndoAction()
        markup = "> "
        sline, _sindex, eline, eindex = editor.getSelection()
        for line in range(sline, eline + 1 if eindex > 0 else eline):
            editor.insertAt(markup, line, 0)
        editor.endUndoAction()

    def hasImage(self):
        """
        Public method to indicate the availability of image markup.

        @return flag indicating the availability of image markup
        @rtype bool
        """
        return True

    def image(self, editor):
        """
        Public method to generate image text.

        @param editor reference to the editor to work on
        @type Editor
        """
        from .ImageMarkupDialog import ImageMarkupDialog, ImageMarkupMode

        if editor is None:
            return

        dlg = ImageMarkupDialog(ImageMarkupMode.MarkDown, parent=editor)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            address, altText, title, _originalSize, _width, _height = dlg.getData()

            if title:
                markup = '![{0}]({1} "{2}")'.format(altText, address, title)
            else:
                markup = "![{0}]({1})".format(altText, address)

            editor.beginUndoAction()
            editor.insert(markup)
            cline, cindex = editor.getCursorPosition()
            editor.setCursorPosition(cline, cindex + len(markup))
            editor.endUndoAction()

    def hasBulletedList(self):
        """
        Public method to indicate the availability of bulleted list markup.

        @return flag indicating the availability of bulleted list markup
        @rtype bool
        """
        return True

    def bulletedList(self, editor):
        """
        Public method to generate bulleted list text.

        @param editor reference to the editor to work on
        @type Editor
        """
        self.__makeList(editor, False)

    def hasNumberedList(self):
        """
        Public method to indicate the availability of numbered list markup.

        @return flag indicating the availability of numbered list markup
        @rtype bool
        """
        return True

    def numberedList(self, editor):
        """
        Public method to generate numbered list text.

        @param editor reference to the editor to work on
        @type Editor
        """
        self.__makeList(editor, True)

    def __makeList(self, editor, numberedList):
        """
        Private method to generate the desired list markup.

        @param editor reference to the editor to work on
        @type Editor
        @param numberedList flag indicating the generation of a numbered list
        @type bool
        """
        if editor is None:
            return

        markup = "  1. " if numberedList else "  * "
        lineSeparator = editor.getLineSeparator()
        editor.beginUndoAction()
        if editor.hasSelectedText():
            startLine, _startIndex, endLine, endIndex = editor.getSelection()
            if endIndex == 0:
                endLine -= 1
            for line in range(startLine, endLine + 1):
                editor.insertAt(markup, line, 0)
            editor.setCursorPosition(endLine + 1, 0)
        else:
            listElements, ok = QInputDialog.getInt(
                None,
                QCoreApplication.translate("MarkdownProvider", "Create List"),
                QCoreApplication.translate(
                    "MarkdownProvider", "Enter desired number of list elements:"
                ),
                0,
                0,
                99,
                1,
            )
            if ok:
                if listElements == 0:
                    listElements = 1
                cline, cindex = editor.getCursorPosition()
                listBody = listElements * "{1}{0}".format(lineSeparator, markup)
                if cindex == 0:
                    editor.insertAt(listBody, cline, cindex)
                    editor.setCursorPosition(cline, len(markup))
                else:
                    if cline == editor.lines() - 1:
                        editor.insertAt(lineSeparator, cline, 1000)
                    editor.insertAt(listBody, cline + 1, 0)
                    editor.setCursorPosition(cline + 1, len(markup))
        editor.endUndoAction()


def createProvider():
    """
    Function to instantiate a markup provider object.

    @return reference to the instantiated markup provider opject
    @rtype MarkdownProvider
    """
    return MarkdownProvider()
