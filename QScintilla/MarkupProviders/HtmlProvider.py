# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the HTML markup provider.
"""

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QDialog, QInputDialog

from .MarkupBase import MarkupBase


class HtmlProvider(MarkupBase):
    """
    Class implementing the HTML markup provider.
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
        return "html"

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
        self.__insertMarkup("b", editor)

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
        self.__insertMarkup("i", editor)

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
        self.__insertMarkup("del", editor)

    def hasUnderline(self):
        """
        Public method to indicate the availability of underline markup.

        @return flag indicating the availability of underline markup
        @rtype bool
        """
        return True

    def underline(self, editor):
        """
        Public method to generate underline text.

        @param editor reference to the editor to work on
        @type Editor
        """
        self.__insertMarkup("u", editor)

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
        if level <= 6:
            self.__insertMarkup("h{0}".format(level), editor)

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
        self.__insertMarkup("code", editor)

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
            newText = "<pre><code>{0}{1}</code></pre>{0}".format(
                lineSeparator, editor.selectedText()
            )
            editor.replaceSelectedText(newText)
        else:
            editor.insert("<pre><code>{0}{0}</code></pre>{0}".format(lineSeparator))
            cline, cindex = editor.getCursorPosition()
            editor.setCursorPosition(cline + 1, 0)
        editor.endUndoAction()

    def __insertMarkup(self, markup, editor, addEol=False):
        """
        Private method to insert the specified markup.

        If the editor has selected text, this text is enclosed by the given
        markup. If no text is selected, the markup is inserted at the cursor
        position and the cursor is positioned in between.

        @param markup markup string to be inserted
        @type str
        @param editor reference to the editor to work on
        @type Editor
        @param addEol flag indicating to add an eol string after the tag
        @type bool
        """
        if editor is None:
            return

        lineSeparator = editor.getLineSeparator() if addEol else ""
        editor.beginUndoAction()
        if editor.hasSelectedText():
            newText = "<{0}>{2}{1}</{0}>{2}".format(
                markup, editor.selectedText(), lineSeparator
            )
            editor.replaceSelectedText(newText)
        else:
            editor.insert("<{0}>{1}{1}</{0}>{1}".format(markup, lineSeparator))
            cline, cindex = editor.getCursorPosition()
            if addEol:
                editor.setCursorPosition(cline + 1, 0)
            else:
                editor.setCursorPosition(cline, cindex + len(markup) + 2)
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

        dlg = HyperlinkMarkupDialog(True, False, parent=editor)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            text, target, title = dlg.getData()
            if not text:
                text = target

            if title:
                link = '<a href="{0}" title="{2}">{1}</a>'.format(target, text, title)
            else:
                link = '<a href="{0}">{1}</a>'.format(target, text)

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

        editor.beginUndoAction()
        markup = "<hr />"
        editor.insert(markup)
        cline, cindex = editor.getCursorPosition()
        editor.setCursorPosition(cline, cindex + len(markup))
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
        self.__insertMarkup("blockquote", editor, True)

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

        dlg = ImageMarkupDialog(ImageMarkupMode.Html, parent=editor)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            address, altText, title, originalSize, width, height = dlg.getData()

            markup = '<img src="{0}"'.format(address)
            if altText:
                markup = '{0} alt="{1}"'.format(markup, altText)
            if title:
                markup = '{0} title="{1}"'.format(markup, title)
            if not originalSize:
                markup = '{0} width="{1}" height="{2}"'.format(markup, width, height)
            markup = "{0} />".format(markup)

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
        self.__makeList(editor, "ul")

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
        self.__makeList(editor, "ol")

    def __makeList(self, editor, listType):
        """
        Private method to generate the desired list markup.

        @param editor reference to the editor to work on
        @type Editor
        @param listType type of the desired list (should be ul or ol)
        @type str
        """
        if editor is None:
            return

        lineSeparator = editor.getLineSeparator()
        editor.beginUndoAction()
        if editor.hasSelectedText():
            startLine, _startIndex, endLine, endIndex = editor.getSelection()
            if endIndex == 0:
                endLine -= 1
            for line in range(startLine, endLine + 1):
                editor.insertAt("</li>", line, len(editor.text(line).rstrip()))
                editor.insertAt("  <li>", line, 0)
            if line == editor.lines() - 1:
                editor.insertAt(lineSeparator, line, 1000)
            editor.insertAt("</{1}>{0}".format(lineSeparator, listType), endLine + 1, 0)
            editor.insertAt("<{1}>{0}".format(lineSeparator, listType), startLine, 0)
            editor.setCursorPosition(endLine + 3, 0)
        else:
            listElements, ok = QInputDialog.getInt(
                None,
                QCoreApplication.translate("HtmlProvider", "Create List"),
                QCoreApplication.translate(
                    "HtmlProvider", "Enter desired number of list elements:"
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
                listBody = listElements * "  <li></li>{0}".format(lineSeparator)
                markup = "<{1}>{0}{2}</{1}>{0}".format(
                    lineSeparator, listType, listBody
                )
                if cindex == 0:
                    editor.insertAt(markup, cline, cindex)
                    editor.setCursorPosition(cline + 1, 6)
                else:
                    if cline == editor.lines() - 1:
                        editor.insertAt(lineSeparator, cline, 1000)
                    editor.insertAt(markup, cline + 1, 0)
                    editor.setCursorPosition(cline + 2, 6)
        editor.endUndoAction()


def createProvider():
    """
    Function to instantiate a markup provider object.

    @return reference to the instantiated markup provider opject
    @rtype HtmlProvider
    """
    return HtmlProvider()
