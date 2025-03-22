# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a compatability interface class to QsciScintilla.
"""

import contextlib
import enum

from PyQt6.Qsci import QsciScintilla, QsciScintillaBase
from PyQt6.QtCore import QPoint, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QListWidget


class QsciScintillaPrintColorMode(enum.IntEnum):
    """
    Class defining the various print color modes.
    """

    Normal = QsciScintillaBase.SC_PRINT_NORMAL
    InvertLight = QsciScintillaBase.SC_PRINT_INVERTLIGHT
    BlackOnWhite = QsciScintillaBase.SC_PRINT_BLACKONWHITE
    ColorOnWhite = QsciScintillaBase.SC_PRINT_COLOURONWHITE
    ColorOnWhiteDefaultBackground = QsciScintillaBase.SC_PRINT_COLOURONWHITEDEFAULTBG
    ScreenColors = QsciScintillaBase.SC_PRINT_SCREENCOLOURS


class QsciScintillaCompat(QsciScintilla):
    """
    Class implementing a compatability interface to QsciScintilla.

    This class implements all the functions, that were added to
    QsciScintilla incrementally. This class ensures compatibility
    to older versions of QsciScintilla.

    @signal zoomValueChanged(int) emitted to signal a change of the zoom value
    """

    zoomValueChanged = pyqtSignal(int)

    ArrowFoldStyle = QsciScintilla.FoldStyle.BoxedTreeFoldStyle.value + 1
    ArrowTreeFoldStyle = ArrowFoldStyle + 1

    UserSeparator = "\x04"

    IndicatorStyleMax = QsciScintilla.INDIC_GRADIENTCENTRE

    # Maps PyQt6.QFont.Weight to the weights used by QScintilla
    QFontWeightMapping = {
        100: 0,
        200: 12,
        300: 25,
        400: 50,
        500: 57,
        600: 63,
        700: 75,
        800: 81,
        900: 87,
    }

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.zoom = 0

        self.__targetSearchFlags = 0
        self.__targetSearchExpr = ""
        self.__targetSearchStart = 0
        self.__targetSearchEnd = -1
        self.__targetSearchActive = False

        self.__modified = False

        self.userListActivated.connect(self.__userListActivated)
        self.modificationChanged.connect(self.__modificationChanged)

        self.setAutoCompletionWidgetSize(40, 5)

    def __modificationChanged(self, m):
        """
        Private slot to handle the modificationChanged signal.

        @param m modification status
        @type bool
        """
        self.__modified = m

    def isModified(self):
        """
        Public method to return the modification status.

        @return flag indicating the modification status
        @rtype bool
        """
        return self.__modified

    def setModified(self, m):
        """
        Public slot to set the modification status.

        @param m new modification status
        @type bool
        """
        self.__modified = m
        super().setModified(m)
        self.modificationChanged.emit(m)

    def setLexer(self, lex=None):
        """
        Public method to set the lexer.

        @param lex lexer to be set or None to reset it.
        @type QsciScintilla.QLexer
        """
        super().setLexer(lex)
        if lex is None:
            self.clearStyles()

    def clearStyles(self):
        """
        Public method to set the styles according the selected Qt style.
        """
        palette = QApplication.palette()
        self.SendScintilla(
            QsciScintilla.SCI_STYLESETFORE,
            QsciScintilla.STYLE_DEFAULT,
            palette.color(QPalette.ColorRole.Text),
        )
        self.SendScintilla(
            QsciScintilla.SCI_STYLESETBACK,
            QsciScintilla.STYLE_DEFAULT,
            palette.color(QPalette.ColorRole.Base),
        )
        self.SendScintilla(QsciScintilla.SCI_STYLECLEARALL)
        self.SendScintilla(QsciScintilla.SCI_CLEARDOCUMENTSTYLE)

    def monospacedStyles(self, font):
        """
        Public method to set the current style to be monospaced.

        @param font font to be used
        @type QFont
        """
        try:
            rangeLow = list(range(self.STYLE_DEFAULT))
        except AttributeError:
            rangeLow = list(range(32))
        try:
            rangeHigh = list(range(self.STYLE_LASTPREDEFINED + 1, self.STYLE_MAX + 1))
        except AttributeError:
            rangeHigh = list(range(40, 128))

        f = font.family().encode("utf-8")
        ps = font.pointSize()
        weight = -QsciScintillaCompat.QFontWeightMapping[font.weight()]
        italic = font.italic()
        underline = font.underline()
        bold = font.bold()
        for style in rangeLow + rangeHigh:
            self.SendScintilla(QsciScintilla.SCI_STYLESETFONT, style, f)
            self.SendScintilla(QsciScintilla.SCI_STYLESETSIZE, style, ps)
            try:
                self.SendScintilla(QsciScintilla.SCI_STYLESETWEIGHT, style, weight)
            except AttributeError:
                self.SendScintilla(QsciScintilla.SCI_STYLESETBOLD, style, bold)
            self.SendScintilla(QsciScintilla.SCI_STYLESETITALIC, style, italic)
            self.SendScintilla(QsciScintilla.SCI_STYLESETUNDERLINE, style, underline)

    def linesOnScreen(self):
        """
        Public method to get the amount of visible lines.

        @return amount of visible lines
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_LINESONSCREEN)

    def lineAt(self, pos):
        """
        Public method to calculate the line at a position.

        This variant is able to calculate the line for positions in the
        margins and for empty lines.

        @param pos position to calculate the line for
        @type int or QPoint
        @return linenumber at position or -1, if there is no line at pos (zero based)
        @rtype int
        """
        scipos = (
            pos
            if isinstance(pos, int)
            else self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMPOINT, pos.x(), pos.y()
            )
        )
        line = self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, scipos)
        if line >= self.lines():
            line = -1
        return line

    def currentPosition(self):
        """
        Public method to get the current position.

        @return absolute position of the cursor
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)

    def styleAt(self, pos):
        """
        Public method to get the style at a position in the text.

        @param pos position in the text
        @type int
        @return style at the requested position or 0, if the position
            is negative or past the end of the document
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_GETSTYLEAT, pos)

    def currentStyle(self):
        """
        Public method to get the style at the current position.

        @return style at the current position
        @rtype int
        """
        return self.styleAt(self.currentPosition())

    def getSubStyleRange(self, styleNr):
        """
        Public method to get the sub style range for given style number.

        @param styleNr Number of the base style
        @type int
        @return start index of the sub style and their count
        @rtype int, int
        """
        start = self.SendScintilla(QsciScintilla.SCI_GETSUBSTYLESSTART, styleNr)
        count = self.SendScintilla(QsciScintilla.SCI_GETSUBSTYLESLENGTH, styleNr)
        return start, count

    def getEndStyled(self):
        """
        Public method to get the last styled position.

        @return end position of the last styling run
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_GETENDSTYLED)

    def startStyling(self, pos, mask):
        """
        Public method to prepare styling.

        @param pos styling positition to start at
        @type int
        @param mask mask of bits to use for styling
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_STARTSTYLING, pos, mask)

    def setStyling(self, length, style):
        """
        Public method to style some text.

        @param length length of text to style
        @type int
        @param style style to set for text
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_SETSTYLING, length, style)

    def charAt(self, pos):
        """
        Public method to get the character at a position in the text observing
        multibyte characters.

        @param pos position in the text
        @type int
        @return character at the requested position or empty string, if the
            position is negative or past the end of the document
        @rtype str
        """
        ch = self.byteAt(pos)
        if ch and ord(ch) > 127 and self.isUtf8():
            if (ch[0] & 0xF0) == 0xF0:
                utf8Len = 4
            elif (ch[0] & 0xE0) == 0xE0:
                utf8Len = 3
            elif (ch[0] & 0xC0) == 0xC0:
                utf8Len = 2
            else:
                utf8Len = 1
            while len(ch) < utf8Len:
                pos += 1
                ch += self.byteAt(pos)
            try:
                return ch.decode("utf8")
            except UnicodeDecodeError:
                if pos > 0:
                    # try it one position before; maybe we are in the
                    # middle of a unicode character
                    return self.charAt(pos - 1)
                else:
                    return ""
        else:
            return ch.decode()

    def byteAt(self, pos):
        """
        Public method to get the raw character (bytes) at a position in the
        text.

        @param pos position in the text
        @type int
        @return raw character at the requested position or empty bytes, if the
            position is negative or past the end of the document
        @rtype bytes
        """
        char = self.SendScintilla(QsciScintilla.SCI_GETCHARAT, pos)
        if char == 0:
            return bytearray()
        if char < 0:
            char += 256
        return bytearray((char,))

    def foldLevelAt(self, line):
        """
        Public method to get the fold level of a line of the document.

        @param line line number
        @type int
        @return fold level of the given line
        @rtype int
        """
        lvl = self.SendScintilla(QsciScintilla.SCI_GETFOLDLEVEL, line)
        return (
            lvl & QsciScintilla.SC_FOLDLEVELNUMBERMASK
        ) - QsciScintilla.SC_FOLDLEVELBASE

    def foldFlagsAt(self, line):
        """
        Public method to get the fold flags of a line of the document.

        @param line line number
        @type int
        @return fold flags of the given line
        @rtype int
        """
        lvl = self.SendScintilla(QsciScintilla.SCI_GETFOLDLEVEL, line)
        return lvl & ~QsciScintilla.SC_FOLDLEVELNUMBERMASK

    def foldHeaderAt(self, line):
        """
        Public method to determine, if a line of the document is a fold header
        line.

        @param line line number
        @type int
        @return flag indicating a fold header line
        @rtype bool
        """
        lvl = self.SendScintilla(QsciScintilla.SCI_GETFOLDLEVEL, line)
        return lvl & QsciScintilla.SC_FOLDLEVELHEADERFLAG

    def foldExpandedAt(self, line):
        """
        Public method to determine, if a fold is expanded.

        @param line line number
        @type int
        @return flag indicating the fold expansion state of the line
        @rtype bool
        """
        return self.SendScintilla(QsciScintilla.SCI_GETFOLDEXPANDED, line)

    def setIndentationGuideView(self, view):
        """
        Public method to set the view of the indentation guides.

        @param view view of the indentation guides (SC_IV_NONE, SC_IV_REAL,
            SC_IV_LOOKFORWARD or SC_IV_LOOKBOTH)
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_SETINDENTATIONGUIDES, view)

    def indentationGuideView(self):
        """
        Public method to get the indentation guide view.

        @return indentation guide view (SC_IV_NONE, SC_IV_REAL,
            SC_IV_LOOKFORWARD or SC_IV_LOOKBOTH)
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_GETINDENTATIONGUIDES)

    ###########################################################################
    ## methods below are missing from QScintilla
    ###########################################################################

    def setAutoCompletionWidgetSize(self, chars, lines):
        """
        Public method to set the size of completion and user lists.

        @param chars max. number of chars to show
        @type int
        @param lines max. number of lines to show
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_AUTOCSETMAXWIDTH, chars)
        self.SendScintilla(QsciScintilla.SCI_AUTOCSETMAXHEIGHT, lines)

    def zoomIn(self, zoom=1):
        """
        Public method used to increase the zoom factor.

        @param zoom zoom factor increment
        @type int
        """
        super().zoomIn(zoom)
        self.zoomValueChanged.emit(self.zoom)

    def zoomOut(self, zoom=1):
        """
        Public method used to decrease the zoom factor.

        @param zoom zoom factor decrement
        @type int
        """
        super().zoomOut(zoom)
        self.zoomValueChanged.emit(self.zoom)

    def zoomTo(self, zoom):
        """
        Public method used to zoom to a specific zoom factor.

        @param zoom zoom factor
        @type int
        """
        self.zoom = zoom
        super().zoomTo(zoom)
        self.zoomValueChanged.emit(self.zoom)

    def getZoom(self):
        """
        Public method used to retrieve the current zoom factor.

        @return zoom factor
        @rtype int
        """
        return self.zoom

    def editorCommand(self, cmd):
        """
        Public method to perform a simple editor command.

        @param cmd the scintilla command to be performed
        @type int
        """
        self.SendScintilla(cmd)

    def scrollVertical(self, lines):
        """
        Public method to scroll the text area.

        @param lines number of lines to scroll (negative scrolls up,
            positive scrolls down)
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_LINESCROLL, 0, lines)

    def moveCursorToEOL(self):
        """
        Public method to move the cursor to the end of line.
        """
        self.SendScintilla(QsciScintilla.SCI_LINEEND)

    def moveCursorLeft(self):
        """
        Public method to move the cursor left.
        """
        self.SendScintilla(QsciScintilla.SCI_CHARLEFT)

    def moveCursorRight(self):
        """
        Public method to move the cursor right.
        """
        self.SendScintilla(QsciScintilla.SCI_CHARRIGHT)

    def moveCursorWordLeft(self):
        """
        Public method to move the cursor left one word.
        """
        self.SendScintilla(QsciScintilla.SCI_WORDLEFT)

    def moveCursorWordRight(self):
        """
        Public method to move the cursor right one word.
        """
        self.SendScintilla(QsciScintilla.SCI_WORDRIGHT)

    def newLineBelow(self):
        """
        Public method to insert a new line below the current one.
        """
        self.SendScintilla(QsciScintilla.SCI_LINEEND)
        self.SendScintilla(QsciScintilla.SCI_NEWLINE)

    def deleteBack(self):
        """
        Public method to delete the character to the left of the cursor.
        """
        self.SendScintilla(QsciScintilla.SCI_DELETEBACK)

    def delete(self):
        """
        Public method to delete the character to the right of the cursor.
        """
        self.SendScintilla(QsciScintilla.SCI_CLEAR)

    def deleteWordLeft(self):
        """
        Public method to delete the word to the left of the cursor.
        """
        self.SendScintilla(QsciScintilla.SCI_DELWORDLEFT)

    def deleteWordRight(self):
        """
        Public method to delete the word to the right of the cursor.
        """
        self.SendScintilla(QsciScintilla.SCI_DELWORDRIGHT)

    def deleteLineLeft(self):
        """
        Public method to delete the line to the left of the cursor.
        """
        self.SendScintilla(QsciScintilla.SCI_DELLINELEFT)

    def deleteLineRight(self):
        """
        Public method to delete the line to the right of the cursor.
        """
        self.SendScintilla(QsciScintilla.SCI_DELLINERIGHT)

    def extendSelectionLeft(self):
        """
        Public method to extend the selection one character to the left.
        """
        self.SendScintilla(QsciScintilla.SCI_CHARLEFTEXTEND)

    def extendSelectionRight(self):
        """
        Public method to extend the selection one character to the right.
        """
        self.SendScintilla(QsciScintilla.SCI_CHARRIGHTEXTEND)

    def extendSelectionWordLeft(self):
        """
        Public method to extend the selection one word to the left.
        """
        self.SendScintilla(QsciScintilla.SCI_WORDLEFTEXTEND)

    def extendSelectionWordRight(self):
        """
        Public method to extend the selection one word to the right.
        """
        self.SendScintilla(QsciScintilla.SCI_WORDRIGHTEXTEND)

    def extendSelectionToBOL(self):
        """
        Public method to extend the selection to the beginning of the line.
        """
        self.SendScintilla(QsciScintilla.SCI_VCHOMEEXTEND)

    def extendSelectionToEOL(self):
        """
        Public method to extend the selection to the end of the line.
        """
        self.SendScintilla(QsciScintilla.SCI_LINEENDEXTEND)

    def hasSelection(self):
        """
        Public method to check for a selection.

        @return flag indicating the presence of a selection
        @rtype bool
        """
        return self.getSelection()[0] != -1

    def hasSelectedText(self):
        """
        Public method to indicate the presence of selected text.

        This is an overriding method to cope with a bug in QsciScintilla.

        @return flag indicating the presence of selected text
        @rtype bool
        """
        return bool(self.selectedText())

    def selectionIsRectangle(self):
        """
        Public method to check, if the current selection is rectangular.

        @return flag indicating a rectangular selection
        @rtype bool
        """
        startLine, startIndex, endLine, endIndex = self.getSelection()
        return (
            startLine != -1
            and startLine != endLine
            and self.SendScintilla(QsciScintilla.SCI_SELECTIONISRECTANGLE)
        )

    def getRectangularSelection(self):
        """
        Public method to retrieve the start and end of a rectangular selection.

        @return tuple with start line and index and end line and index
        @rtype tuple of (int, int, int, int)
        """
        if not self.selectionIsRectangle():
            return (-1, -1, -1, -1)

        startPos = self.SendScintilla(QsciScintilla.SCI_GETRECTANGULARSELECTIONANCHOR)
        endPos = self.SendScintilla(QsciScintilla.SCI_GETRECTANGULARSELECTIONCARET)
        startLine, startIndex = self.lineIndexFromPosition(startPos)
        endLine, endIndex = self.lineIndexFromPosition(endPos)

        return (startLine, startIndex, endLine, endIndex)

    def setRectangularSelection(self, startLine, startIndex, endLine, endIndex):
        """
        Public method to set a rectangular selection.

        @param startLine line number of the start of the selection
        @type int
        @param startIndex index number of the start of the selection
        @type int
        @param endLine line number of the end of the selection
        @type int
        @param endIndex index number of the end of the selection
        @type int
        """
        startPos = self.positionFromLineIndex(startLine, startIndex)
        endPos = self.positionFromLineIndex(endLine, endIndex)

        self.SendScintilla(QsciScintilla.SCI_SETRECTANGULARSELECTIONANCHOR, startPos)
        self.SendScintilla(QsciScintilla.SCI_SETRECTANGULARSELECTIONCARET, endPos)

    def setRectangularSelectionModifier(self, modifier):
        """
        Public method to set the modifier key used to create a rectangular selection by
        doing a mouse drag.

        @param modifier modifier key to be used
        @type Qt.KeyboardModifier
        """
        sciModifier = {
            Qt.KeyboardModifier.ControlModifier: QsciScintilla.SCMOD_CTRL,
            Qt.KeyboardModifier.AltModifier: QsciScintilla.SCMOD_ALT,
            Qt.KeyboardModifier.MetaModifier: QsciScintilla.SCMOD_SUPER,
        }.get(modifier, QsciScintilla.SCMOD_CTRL)
        self.SendScintilla(
            QsciScintilla.SCI_SETRECTANGULARSELECTIONMODIFIER, sciModifier
        )

    def getSelectionCount(self):
        """
        Public method to get the number of active selections.

        @return number of active selection
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_GETSELECTIONS)

    def getSelectionN(self, index):
        """
        Public method to get the start and end of a selection given by its
        index.

        @param index index of the selection
        @type int
        @return tuple with start line and index and end line and index for the
            given selection
        @rtype tuple of (int, int, int, int)
        """
        startPos = self.SendScintilla(QsciScintilla.SCI_GETSELECTIONNSTART, index)
        endPos = self.SendScintilla(QsciScintilla.SCI_GETSELECTIONNEND, index)
        startLine, startIndex = self.lineIndexFromPosition(startPos)
        endLine, endIndex = self.lineIndexFromPosition(endPos)

        return (startLine, startIndex, endLine, endIndex)

    def getSelections(self):
        """
        Public method to get the start and end coordinates of all active
        selections.

        @return list of tuples with start line and index and end line and index
            of each active selection
        @rtype list of [tuple of (int, int, int, int)]
        """
        selections = []
        for index in range(self.getSelectionCount()):
            selections.append(self.getSelectionN(index))
        return selections

    def addCursor(self, line, index):
        """
        Public method to add an additional cursor.

        @param line line number for the cursor
        @type int
        @param index index number for the cursor
        @type int
        """
        pos = self.positionFromLineIndex(line, index)

        if self.getSelectionCount() == 0:
            self.SendScintilla(QsciScintilla.SCI_SETSELECTION, pos, pos)
        else:
            self.SendScintilla(QsciScintilla.SCI_ADDSELECTION, pos, pos)

    def enableMultiCursorSupport(self):
        """
        Public method to enable support for multi cursor editing.
        """
        # typing and pasting should insert in all selections at the same time
        self.SendScintilla(QsciScintilla.SCI_SETMULTIPLESELECTION, True)
        self.SendScintilla(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING, True)
        self.SendScintilla(
            QsciScintilla.SCI_SETMULTIPASTE, QsciScintilla.SC_MULTIPASTE_EACH
        )

    def setVirtualSpaceOptions(self, options):
        """
        Public method to set the virtual space usage options.

        @param options usage options to set (0 to 3)
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_SETVIRTUALSPACEOPTIONS, options)

    def getLineSeparator(self):
        """
        Public method to get the line separator for the current eol mode.

        @return eol string
        @rtype str
        """
        m = self.eolMode()
        if m == QsciScintilla.EolMode.EolWindows:
            eol = "\r\n"
        elif m == QsciScintilla.EolMode.EolUnix:
            eol = "\n"
        elif m == QsciScintilla.EolMode.EolMac:
            eol = "\r"
        else:
            eol = ""
        return eol

    def getEolIndicator(self):
        """
        Public method to get the eol indicator for the current eol mode.

        @return eol indicator
        @rtype str
        """
        m = self.eolMode()
        if m == QsciScintilla.EolMode.EolWindows:
            eol = "CRLF"
        elif m == QsciScintilla.EolMode.EolUnix:
            eol = "LF"
        elif m == QsciScintilla.EolMode.EolMac:
            eol = "CR"
        else:
            eol = ""
        return eol

    def setEolModeByEolString(self, eolStr):
        """
        Public method to set the eol mode given the eol string.

        @param eolStr eol string
        @type str
        """
        if eolStr == "\r\n":
            self.setEolMode(QsciScintilla.EolMode.EolWindows)
        elif eolStr == "\n":
            self.setEolMode(QsciScintilla.EolMode.EolUnix)
        elif eolStr == "\r":
            self.setEolMode(QsciScintilla.EolMode.EolMac)

    def detectEolString(self, txt):
        """
        Public method to determine the eol string used.

        @param txt text from which to determine the eol string
        @type str
        @return eol string
        @rtype str
        """
        if len(txt.split("\r\n", 1)) == 2:
            return "\r\n"
        elif len(txt.split("\n", 1)) == 2:
            return "\n"
        elif len(txt.split("\r", 1)) == 2:
            return "\r"
        else:
            return None

    def getCursorFlashTime(self):
        """
        Public method to get the flash (blink) time of the cursor in
        milliseconds.

        The flash time is the time required to display, invert and restore the
        caret display. Usually the text cursor is displayed for half the cursor
        flash time, then hidden for the same amount of time.

        @return flash time of the cursor in milliseconds
        @rtype int
        """
        return 2 * self.SendScintilla(QsciScintilla.SCI_GETCARETPERIOD)

    def setCursorFlashTime(self, time):
        """
        Public method to set the flash (blink) time of the cursor in
        milliseconds.

        The flash time is the time required to display, invert and restore the
        caret display. Usually the text cursor is displayed for half the cursor
        flash time, then hidden for the same amount of time.

        @param time flash time of the cursor in milliseconds
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_SETCARETPERIOD, time // 2)

    def getCaretLineAlwaysVisible(self):
        """
        Public method to determine, if the caret line is visible even if
        the editor doesn't have the focus.

        @return flag indicating an always visible caret line
        @rtype bool
        """
        try:
            return self.SendScintilla(QsciScintilla.SCI_GETCARETLINEVISIBLEALWAYS)
        except AttributeError:
            return False

    def setCaretLineAlwaysVisible(self, alwaysVisible):
        """
        Public method to set the caret line visible even if the editor doesn't
        have the focus.

        @param alwaysVisible flag indicating that the caret line shall be
            visible even if the editor doesn't have the focus
        @type bool
        """
        with contextlib.suppress(AttributeError):
            self.SendScintilla(
                QsciScintilla.SCI_SETCARETLINEVISIBLEALWAYS, alwaysVisible
            )

    def canPaste(self):
        """
        Public method to test, if the paste action is available (i.e. if the
        clipboard contains some text).

        @return flag indicating the availability of 'paste'
        @rtype bool
        """
        return self.SendScintilla(QsciScintilla.SCI_CANPASTE)

    ###########################################################################
    ## methods to perform searches in target range
    ###########################################################################

    def positionFromPoint(self, point):
        """
        Public method to calculate the scintilla position from a point in the
        window.

        @param point point in the window
        @type QPoint
        @return scintilla position or -1 to indicate, that the point is not near
            any character
        @rtype int
        """
        return self.SendScintilla(
            QsciScintilla.SCI_POSITIONFROMPOINTCLOSE, point.x(), point.y()
        )

    def positionBefore(self, pos):
        """
        Public method to get the position before the given position taking into
        account multibyte characters.

        @param pos position
        @type int
        @return position before the given one
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_POSITIONBEFORE, pos)

    def positionAfter(self, pos):
        """
        Public method to get the position after the given position taking into
        account multibyte characters.

        @param pos position
        @type int
        @return position after the given one
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_POSITIONAFTER, pos)

    def lineEndPosition(self, line):
        """
        Public method to determine the line end position of the given line.

        @param line line number
        @type int
        @return position of the line end disregarding line end characters
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_GETLINEENDPOSITION, line)

    def __doSearchTarget(self):
        """
        Private method to perform the search in target.

        @return flag indicating a successful search
        @rtype bool
        """
        if self.__targetSearchStart == self.__targetSearchEnd:
            self.__targetSearchActive = False
            return False

        self.SendScintilla(QsciScintilla.SCI_SETTARGETSTART, self.__targetSearchStart)
        self.SendScintilla(QsciScintilla.SCI_SETTARGETEND, self.__targetSearchEnd)
        self.SendScintilla(QsciScintilla.SCI_SETSEARCHFLAGS, self.__targetSearchFlags)
        targetSearchExpr = self._encodeString(self.__targetSearchExpr)
        pos = self.SendScintilla(
            QsciScintilla.SCI_SEARCHINTARGET, len(targetSearchExpr), targetSearchExpr
        )

        if pos == -1:
            self.__targetSearchActive = False
            return False

        targetEnd = self.SendScintilla(QsciScintilla.SCI_GETTARGETEND)
        if targetEnd == self.__targetSearchStart:
            return False

        self.__targetSearchStart = targetEnd
        return True

    def getFoundTarget(self):
        """
        Public method to get the recently found target.

        @return found target as a tuple of starting position and target length
        @rtype tuple of (int, int)
        """
        if self.__targetSearchActive:
            spos = self.SendScintilla(QsciScintilla.SCI_GETTARGETSTART)
            epos = self.SendScintilla(QsciScintilla.SCI_GETTARGETEND)
            return (spos, epos - spos)
        else:
            return (0, 0)

    def findFirstTarget(
        self,
        expr_,
        re_,
        cs_,
        wo_,
        begline=-1,
        begindex=-1,
        endline=-1,
        endindex=-1,
        ws_=False,
        posix=False,
        cxx11=False,
    ):
        """
        Public method to search in a specified range of text without
        setting the selection.

        @param expr_ search expression
        @type str
        @param re_ flag indicating a regular expression
        @type bool
        @param cs_ flag indicating a case sensitive search
        @type bool
        @param wo_ flag indicating a word only search
        @type bool
        @param begline line number to start from (-1 to indicate current
            position)
        @type int
        @param begindex index to start from (-1 to indicate current position)
        @type int
        @param endline line number to stop at (-1 to indicate end of document)
        @type int
        @param endindex index number to stop at (-1 to indicate end of
            document)
        @type int
        @param ws_ flag indicating a word start search
        @type bool
        @param posix flag indicating a POSIX regular expression
        @type bool
        @param cxx11 flag indicating a CXX-11 regular expression
        @type bool
        @return flag indicating a successful search
        @rtype bool
        """
        self.__targetSearchFlags = 0
        if re_:
            self.__targetSearchFlags |= QsciScintilla.SCFIND_REGEXP
        if cs_:
            self.__targetSearchFlags |= QsciScintilla.SCFIND_MATCHCASE
        if wo_:
            self.__targetSearchFlags |= QsciScintilla.SCFIND_WHOLEWORD
        if ws_:
            self.__targetSearchFlags |= QsciScintilla.SCFIND_WORDSTART
        if posix:
            self.__targetSearchFlags |= QsciScintilla.SCFIND_POSIX
        with contextlib.suppress(AttributeError):
            if cxx11:
                self.__targetSearchFlags |= QsciScintilla.SCFIND_CXX11REGEX
            # defined for QScintilla >= 2.11.0

        if begline < 0 or begindex < 0:
            self.__targetSearchStart = self.SendScintilla(
                QsciScintilla.SCI_GETCURRENTPOS
            )
        else:
            self.__targetSearchStart = self.positionFromLineIndex(begline, begindex)

        if endline < 0 or endindex < 0:
            self.__targetSearchEnd = self.SendScintilla(QsciScintilla.SCI_GETTEXTLENGTH)
        else:
            self.__targetSearchEnd = self.positionFromLineIndex(endline, endindex)

        self.__targetSearchExpr = expr_

        if self.__targetSearchExpr:
            self.__targetSearchActive = True

            return self.__doSearchTarget()

        return False

    def findNextTarget(self):
        """
        Public method to find the next occurrence in the target range.

        @return flag indicating a successful search
        @rtype bool
        """
        if not self.__targetSearchActive:
            return False

        return self.__doSearchTarget()

    def replaceTarget(self, replaceStr):
        """
        Public method to replace the string found by the last search in target.

        @param replaceStr replacement string or regexp
        @type str
        """
        if not self.__targetSearchActive:
            return

        cmd = (
            QsciScintilla.SCI_REPLACETARGETRE
            if self.__targetSearchFlags & QsciScintilla.SCFIND_REGEXP
            else QsciScintilla.SCI_REPLACETARGET
        )
        r = self._encodeString(replaceStr)

        start = self.SendScintilla(QsciScintilla.SCI_GETTARGETSTART)
        self.SendScintilla(cmd, len(r), r)

        self.__targetSearchStart = start + len(r)

    ###########################################################################
    ## indicator handling methods
    ###########################################################################

    def indicatorDefine(self, indicator, style, color):
        """
        Public method to define the appearance of an indicator.

        @param indicator number of the indicator (integer,
            QsciScintilla.INDIC_CONTAINER .. QsciScintilla.INDIC_MAX)
        @type int
        @param style style to be used for the indicator
            (QsciScintilla.INDIC_PLAIN, QsciScintilla.INDIC_SQUIGGLE,
            QsciScintilla.INDIC_TT, QsciScintilla.INDIC_DIAGONAL,
            QsciScintilla.INDIC_STRIKE, QsciScintilla.INDIC_HIDDEN,
            QsciScintilla.INDIC_BOX, QsciScintilla.INDIC_ROUNDBOX,
            QsciScintilla.INDIC_STRAIGHTBOX, QsciScintilla.INDIC_FULLBOX,
            QsciScintilla.INDIC_DASH, QsciScintilla.INDIC_DOTS,
            QsciScintilla.INDIC_SQUIGGLELOW, QsciScintilla.INDIC_DOTBOX,
            QsciScintilla.INDIC_GRADIENT, QsciScintilla.INDIC_GRADIENTCENTRE,
            QsciScintilla.INDIC_SQUIGGLEPIXMAP,
            QsciScintilla.INDIC_COMPOSITIONTHICK,
            QsciScintilla.INDIC_COMPOSITIONTHIN, QsciScintilla.INDIC_TEXTFORE,
            QsciScintilla.INDIC_POINT, QsciScintilla.INDIC_POINTCHARACTER
            depending upon QScintilla version)
        @type int
        @param color color to be used by the indicator
        @type QColor
        @exception ValueError the indicator or style are not valid
        """
        if (
            indicator < QsciScintilla.INDIC_CONTAINER
            or indicator > QsciScintilla.INDIC_MAX
        ):
            raise ValueError("indicator number out of range")

        if style < QsciScintilla.INDIC_PLAIN or style > self.IndicatorStyleMax:
            raise ValueError("style out of range")

        self.SendScintilla(QsciScintilla.SCI_INDICSETSTYLE, indicator, style)
        self.SendScintilla(QsciScintilla.SCI_INDICSETFORE, indicator, color)
        with contextlib.suppress(AttributeError):
            self.SendScintilla(
                QsciScintilla.SCI_INDICSETALPHA, indicator, color.alpha()
            )
            if style in (
                QsciScintilla.INDIC_ROUNDBOX,
                QsciScintilla.INDIC_STRAIGHTBOX,
                QsciScintilla.INDIC_DOTBOX,
                QsciScintilla.INDIC_FULLBOX,
            ):
                # set outline alpha less transparent
                self.SendScintilla(
                    QsciScintilla.SCI_INDICSETOUTLINEALPHA,
                    indicator,
                    color.alpha() + 20,
                )

    def setCurrentIndicator(self, indicator):
        """
        Public method to set the current indicator.

        @param indicator number of the indicator (integer,
            QsciScintilla.INDIC_CONTAINER .. QsciScintilla.INDIC_MAX)
        @type int
        @exception ValueError the indicator or style are not valid
        """
        if (
            indicator < QsciScintilla.INDIC_CONTAINER
            or indicator > QsciScintilla.INDIC_MAX
        ):
            raise ValueError("indicator number out of range")

        self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, indicator)

    def setIndicatorRange(self, indicator, spos, length):
        """
        Public method to set an indicator for the given range.

        @param indicator number of the indicator (integer,
            QsciScintilla.INDIC_CONTAINER .. QsciScintilla.INDIC_MAX)
        @type int
        @param spos position of the indicator start
        @type int
        @param length length of the indicator
        @type int
        """
        self.setCurrentIndicator(indicator)
        self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, spos, length)

    def setIndicator(self, indicator, sline, sindex, eline, eindex):
        """
        Public method to set an indicator for the given range.

        @param indicator number of the indicator (integer,
            QsciScintilla.INDIC_CONTAINER .. QsciScintilla.INDIC_MAX)
        @type int
        @param sline line number of the indicator start
        @type int
        @param sindex index of the indicator start
        @type int
        @param eline line number of the indicator end
        @type int
        @param eindex index of the indicator end
        @type int
        """
        spos = self.positionFromLineIndex(sline, sindex)
        epos = self.positionFromLineIndex(eline, eindex)
        self.setIndicatorRange(indicator, spos, epos - spos)

    def clearIndicatorRange(self, indicator, spos, length):
        """
        Public method to clear an indicator for the given range.

        @param indicator number of the indicator (integer,
            QsciScintilla.INDIC_CONTAINER .. QsciScintilla.INDIC_MAX)
        @type int
        @param spos position of the indicator start
        @type int
        @param length length of the indicator
        @type int
        """
        self.setCurrentIndicator(indicator)
        self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, spos, length)

    def clearIndicator(self, indicator, sline, sindex, eline, eindex):
        """
        Public method to clear an indicator for the given range.

        @param indicator number of the indicator (integer,
            QsciScintilla.INDIC_CONTAINER .. QsciScintilla.INDIC_MAX)
        @type int
        @param sline line number of the indicator start
        @type int
        @param sindex index of the indicator start
        @type int
        @param eline line number of the indicator end
        @type int
        @param eindex index of the indicator end
        @type int
        """
        spos = self.positionFromLineIndex(sline, sindex)
        epos = self.positionFromLineIndex(eline, eindex)
        self.clearIndicatorRange(indicator, spos, epos - spos)

    def clearAllIndicators(self, indicator):
        """
        Public method to clear all occurrences of an indicator.

        @param indicator number of the indicator (integer,
            QsciScintilla.INDIC_CONTAINER .. QsciScintilla.INDIC_MAX)
        @type int
        """
        self.clearIndicatorRange(indicator, 0, self.length())

    def hasIndicator(self, indicator, pos):
        """
        Public method to test for the existence of an indicator.

        @param indicator number of the indicator (integer,
            QsciScintilla.INDIC_CONTAINER .. QsciScintilla.INDIC_MAX)
        @type int
        @param pos position to test
        @type int
        @return flag indicating the existence of the indicator
        @rtype bool
        """
        res = self.SendScintilla(QsciScintilla.SCI_INDICATORVALUEAT, indicator, pos)
        return res

    def showFindIndicator(self, sline, sindex, eline, eindex):
        """
        Public method to show the find indicator for the given range.

        @param sline line number of the indicator start
        @type int
        @param sindex index of the indicator start
        @type int
        @param eline line number of the indicator end
        @type int
        @param eindex index of the indicator end
        @type int
        """
        if hasattr(QsciScintilla, "SCI_FINDINDICATORSHOW"):
            spos = self.positionFromLineIndex(sline, sindex)
            epos = self.positionFromLineIndex(eline, eindex)
            self.SendScintilla(QsciScintilla.SCI_FINDINDICATORSHOW, spos, epos)

    def flashFindIndicator(self, sline, sindex, eline, eindex):
        """
        Public method to flash the find indicator for the given range.

        @param sline line number of the indicator start
        @type int
        @param sindex index of the indicator start
        @type int
        @param eline line number of the indicator end
        @type int
        @param eindex index of the indicator end
        @type int
        """
        if hasattr(QsciScintilla, "SCI_FINDINDICATORFLASH"):
            spos = self.positionFromLineIndex(sline, sindex)
            epos = self.positionFromLineIndex(eline, eindex)
            self.SendScintilla(QsciScintilla.SCI_FINDINDICATORFLASH, spos, epos)

    def hideFindIndicator(self):
        """
        Public method to hide the find indicator.
        """
        if hasattr(QsciScintilla, "SCI_FINDINDICATORHIDE"):
            self.SendScintilla(QsciScintilla.SCI_FINDINDICATORHIDE)

    def getIndicatorStartPos(self, indicator, pos):
        """
        Public method to get the start position of an indicator at a position.

        @param indicator ID of the indicator
        @type int
        @param pos position within the indicator
        @type int
        @return start position of the indicator
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_INDICATORSTART, indicator, pos)

    def getIndicatorEndPos(self, indicator, pos):
        """
        Public method to get the end position of an indicator at a position.

        @param indicator ID of the indicator
        @type int
        @param pos position within the indicator
        @type int
        @return end position of the indicator
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_INDICATOREND, indicator, pos)

    def getIndicatorRange(self, indicator, pos=None):
        """
        Public method to get the range of the indicator at the given position.

        If the position is given as 'None', the current cursor position is used.

        @param indicator ID of the indicator
        @type int
        @param pos position within the indicator (defaults to None)
        @type int (optional)
        @return start position and length of the indicator
        @rtype tuple of (int, int)
        """
        if pos is None:
            pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)

        isInIndicator = self.hasIndicator(indicator, pos)
        if isInIndicator:
            posStart = self.getIndicatorStartPos(indicator, pos)
            posEnd = self.getIndicatorEndPos(indicator, pos)
            return posStart, posEnd - posStart
        else:
            return 0, 0

    def getIndicator(self, indicator, pos=None):
        """
        Public method to get the start and end of the indicator at the given position.

        If the position is given as 'None', the current cursor position is used.

        @param indicator ID of the indicator
        @type int
        @param pos position within the indicator (defaults to None)
        @type int (optional)
        @return tuple containing the start line and index and the end line and index
        @rtype tuple of (int, int, int, int)
        """
        if pos is None:
            pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)

        isInIndicator = self.hasIndicator(indicator, pos)
        if isInIndicator:
            posStart = self.getIndicatorStartPos(indicator, pos)
            sline, sindex = self.lineIndexFromPosition(posStart)
            posEnd = self.getIndicatorEndPos(indicator, pos)
            eline, eindex = self.lineIndexFromPosition(posEnd)
            return sline, sindex, eline, eindex
        else:
            return 0, 0, 0, 0

    def gotoPreviousIndicator(self, indicator, wrap):
        """
        Public method to move the cursor to the previous position of an
        indicator.

        This method ensures, that the position found is visible (i.e. unfolded
        and inside the visible range). The text containing the indicator is
        selected.

        @param indicator ID of the indicator to search
        @type int
        @param wrap flag indicating to wrap around at the beginning of the text
        @type bool
        @return flag indicating if the indicator was found
        @rtype bool
        """
        pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
        docLen = self.SendScintilla(QsciScintilla.SCI_GETTEXTLENGTH)
        isInIndicator = self.hasIndicator(indicator, pos)
        posStart = self.getIndicatorStartPos(indicator, pos)
        posEnd = self.getIndicatorEndPos(indicator, pos)

        if posStart == 0 and posEnd == docLen - 1:
            # indicator does not exist
            return False

        if posStart <= 0:
            if not wrap:
                return False

            isInIndicator = self.hasIndicator(indicator, docLen - 1)
            posStart = self.getIndicatorStartPos(indicator, docLen - 1)

        if isInIndicator:
            # get out of it
            posStart = self.getIndicatorStartPos(indicator, posStart - 1)
            if posStart <= 0:
                if not wrap:
                    return False

                posStart = self.getIndicatorStartPos(indicator, docLen - 1)

        newPos = posStart - 1
        posStart = self.getIndicatorStartPos(indicator, newPos)
        posEnd = self.getIndicatorEndPos(indicator, newPos)

        if self.hasIndicator(indicator, posStart):
            # found it
            line, index = self.lineIndexFromPosition(posEnd)
            self.ensureLineVisible(line)
            self.SendScintilla(QsciScintilla.SCI_SETSEL, posEnd, posStart)
            self.SendScintilla(QsciScintilla.SCI_SCROLLCARET)
            return True

        return False

    def gotoNextIndicator(self, indicator, wrap):
        """
        Public method to move the cursor to the next position of an indicator.

        This method ensures, that the position found is visible (i.e. unfolded
        and inside the visible range). The text containing the indicator is
        selected.

        @param indicator ID of the indicator to search
        @type int
        @param wrap flag indicating to wrap around at the beginning of the text
        @type bool
        @return flag indicating if the indicator was found
        @rtype bool
        """
        pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
        docLen = self.SendScintilla(QsciScintilla.SCI_GETTEXTLENGTH)
        isInIndicator = self.hasIndicator(indicator, pos)
        posStart = self.getIndicatorStartPos(indicator, pos)
        posEnd = self.getIndicatorEndPos(indicator, pos)

        if posStart == 0 and posEnd == docLen - 1:
            # indicator does not exist
            return False

        if posEnd >= docLen:
            if not wrap:
                return False

            isInIndicator = self.hasIndicator(indicator, 0)
            posEnd = self.getIndicatorEndPos(indicator, 0)

        if isInIndicator:
            # get out of it
            posEnd = self.getIndicatorEndPos(indicator, posEnd)
            if posEnd >= docLen:
                if not wrap:
                    return False

                posEnd = self.getIndicatorEndPos(indicator, 0)

        newPos = posEnd + 1
        posStart = self.getIndicatorStartPos(indicator, newPos)
        posEnd = self.getIndicatorEndPos(indicator, newPos)

        if self.hasIndicator(indicator, posStart):
            # found it
            line, index = self.lineIndexFromPosition(posEnd)
            self.ensureLineVisible(line)
            self.SendScintilla(QsciScintilla.SCI_SETSEL, posStart, posEnd)
            self.SendScintilla(QsciScintilla.SCI_SCROLLCARET)
            return True

        return False

    ###########################################################################
    ## methods to perform folding related stuff
    ###########################################################################

    def __setFoldMarker(self, marknr, mark=QsciScintilla.SC_MARK_EMPTY):
        """
        Private method to define a fold marker.

        @param marknr marker number to define
        @type int
        @param mark fold mark symbol to be used
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_MARKERDEFINE, marknr, mark)

        if mark != QsciScintilla.SC_MARK_EMPTY:
            self.SendScintilla(
                QsciScintilla.SCI_MARKERSETFORE, marknr, QColor(Qt.GlobalColor.white)
            )
            self.SendScintilla(
                QsciScintilla.SCI_MARKERSETBACK, marknr, QColor(Qt.GlobalColor.black)
            )

    def setFolding(self, style, margin=2):
        """
        Public method to set the folding style and margin.

        @param style folding style to set
        @type int
        @param margin margin number
        @type int
        """
        if isinstance(style, QsciScintilla.FoldStyle):
            super().setFolding(QsciScintilla.FoldStyle(style), margin)
        else:
            super().setFolding(QsciScintilla.FoldStyle.PlainFoldStyle, margin)

            if style == self.ArrowFoldStyle:
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDER, QsciScintilla.SC_MARK_ARROW
                )
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDEROPEN, QsciScintilla.SC_MARK_ARROWDOWN
                )
                self.__setFoldMarker(QsciScintilla.SC_MARKNUM_FOLDERSUB)
                self.__setFoldMarker(QsciScintilla.SC_MARKNUM_FOLDERTAIL)
                self.__setFoldMarker(QsciScintilla.SC_MARKNUM_FOLDEREND)
                self.__setFoldMarker(QsciScintilla.SC_MARKNUM_FOLDEROPENMID)
                self.__setFoldMarker(QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)
            elif style == self.ArrowTreeFoldStyle:
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDER, QsciScintilla.SC_MARK_ARROW
                )
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDEROPEN, QsciScintilla.SC_MARK_ARROWDOWN
                )
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDERSUB, QsciScintilla.SC_MARK_VLINE
                )
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDERTAIL, QsciScintilla.SC_MARK_LCORNER
                )
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDEREND, QsciScintilla.SC_MARK_ARROW
                )
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDEROPENMID,
                    QsciScintilla.SC_MARK_ARROWDOWN,
                )
                self.__setFoldMarker(
                    QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL,
                    QsciScintilla.SC_MARK_TCORNER,
                )

    def setFoldMarkersColors(self, foreColor, backColor):
        """
        Public method to set the foreground and background colors of the
        fold markers.

        @param foreColor foreground color
        @type QColor
        @param backColor background color
        @type QColor
        """
        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETFORE, QsciScintilla.SC_MARKNUM_FOLDER, foreColor
        )
        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETBACK, QsciScintilla.SC_MARKNUM_FOLDER, backColor
        )

        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETFORE,
            QsciScintilla.SC_MARKNUM_FOLDEROPEN,
            foreColor,
        )
        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETBACK,
            QsciScintilla.SC_MARKNUM_FOLDEROPEN,
            backColor,
        )

        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETFORE,
            QsciScintilla.SC_MARKNUM_FOLDEROPENMID,
            foreColor,
        )
        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETBACK,
            QsciScintilla.SC_MARKNUM_FOLDEROPENMID,
            backColor,
        )

        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETFORE,
            QsciScintilla.SC_MARKNUM_FOLDERSUB,
            foreColor,
        )
        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETBACK,
            QsciScintilla.SC_MARKNUM_FOLDERSUB,
            backColor,
        )

        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETFORE,
            QsciScintilla.SC_MARKNUM_FOLDERTAIL,
            foreColor,
        )
        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETBACK,
            QsciScintilla.SC_MARKNUM_FOLDERTAIL,
            backColor,
        )

        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETFORE,
            QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL,
            foreColor,
        )
        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETBACK,
            QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL,
            backColor,
        )

        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETFORE,
            QsciScintilla.SC_MARKNUM_FOLDEREND,
            foreColor,
        )
        self.SendScintilla(
            QsciScintilla.SCI_MARKERSETBACK,
            QsciScintilla.SC_MARKNUM_FOLDEREND,
            backColor,
        )

    def getVisibleLineFromDocLine(self, docLine):
        """
        Public method to convert a document line number to a visible line
        number (i.e. respect folded lines and annotations).

        @param docLine document line number to be converted
        @type int
        @return visible line number
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_VISIBLEFROMDOCLINE, docLine)

    def getDocLineFromVisibleLine(self, displayLine):
        """
        Public method to convert a visible line number to a document line
        number (i.e. respect folded lines and annotations).

        @param displayLine display line number to be converted
        @type int
        @return document line number
        @rtype int
        """
        return self.SendScintilla(QsciScintilla.SCI_DOCLINEFROMVISIBLE, displayLine)

    ###########################################################################
    ## interface methods to the standard keyboard command set
    ###########################################################################

    def clearKeys(self):
        """
        Public method to clear the key commands.
        """
        # call into the QsciCommandSet
        self.standardCommands().clearKeys()

    def clearAlternateKeys(self):
        """
        Public method to clear the alternate key commands.
        """
        # call into the QsciCommandSet
        self.standardCommands().clearAlternateKeys()

    ###########################################################################
    ## specialized event handlers
    ###########################################################################

    def focusOutEvent(self, event):
        """
        Protected method called when the editor loses focus.

        @param event event object
        @type QFocusEvent
        """
        if self.isListActive():
            if event.reason() in [
                Qt.FocusReason.ActiveWindowFocusReason,
                Qt.FocusReason.OtherFocusReason,
            ]:
                aw = QApplication.activeWindow()
                if aw is None or aw.parent() is not self:
                    self.cancelList()
            else:
                self.cancelList()

        if self.isCallTipActive():
            if event.reason() in [
                Qt.FocusReason.ActiveWindowFocusReason,
                Qt.FocusReason.OtherFocusReason,
            ]:
                aw = QApplication.activeWindow()
                if aw is None or aw.parent() is not self:
                    self.cancelCallTips()
            else:
                self.cancelCallTips()

        super().focusOutEvent(event)

    def event(self, evt):
        """
        Public method to handle events.

        Note: We are not interested in the standard QsciScintilla event
        handling because we do it ourselves.

        @param evt event object to handle
        @type QEvent
        @return result of the event handling
        @rtype bool
        """
        return QsciScintillaBase.event(self, evt)

    ###########################################################################
    ## interface methods to the mini editor
    ###########################################################################

    def getFileName(self):
        """
        Public method to return the name of the file being displayed.

        @return filename of the displayed file
        @rtype str
        """
        p = self.parent()
        if p is None:
            return ""
        else:
            try:
                return p.getFileName()
            except AttributeError:
                return ""

    ###########################################################################
    ## replacements for buggy methods
    ###########################################################################

    def showUserList(self, listId, lst):
        """
        Public method to show a user supplied list.

        @param listId id of the list
        @type int
        @param lst list to be show
        @type list of str
        """
        if listId <= 0:
            return

        # Setup seperator for user lists
        self.SendScintilla(QsciScintilla.SCI_AUTOCSETSEPARATOR, ord(self.UserSeparator))
        self.SendScintilla(
            QsciScintilla.SCI_USERLISTSHOW,
            listId,
            self._encodeString(self.UserSeparator.join(lst)),
        )

        self.updateUserListSize()

    def autoCompleteFromDocument(self):
        """
        Public method to resize list box after creation.
        """
        super().autoCompleteFromDocument()
        self.updateUserListSize()

    def autoCompleteFromAPIs(self):
        """
        Public method to resize list box after creation.
        """
        super().autoCompleteFromAPIs()
        self.updateUserListSize()

    def autoCompleteFromAll(self):
        """
        Public method to resize list box after creation.
        """
        super().autoCompleteFromAll()
        self.updateUserListSize()

    ###########################################################################
    ## work-around for buggy behavior
    ###########################################################################

    def updateUserListSize(self):
        """
        Public method to resize the completion list to fit with contents.
        """
        children = self.findChildren(QListWidget)
        if children:
            userListWidget = children[-1]
            hScrollbar = userListWidget.horizontalScrollBar()
            if hScrollbar.isVisible():
                hScrollbarHeight = hScrollbar.sizeHint().height()

                geom = userListWidget.geometry()
                geom.setHeight(geom.height() + hScrollbarHeight)

                charPos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)
                currentYPos = self.SendScintilla(
                    QsciScintilla.SCI_POINTYFROMPOSITION, 0, charPos
                )
                if geom.y() < currentYPos:
                    geom.setY(geom.y() - hScrollbarHeight)
                    moveY = True
                else:
                    moveY = False

                userListWidget.setGeometry(geom)
                if moveY:
                    userListWidget.move(geom.x(), geom.y() - hScrollbarHeight)

    @pyqtSlot(int, str)
    def __userListActivated(self, listId, txt):
        """
        Private slot to handle the selection from the completion list.

        Note: This works around an issue of some window managers taking
        focus away from the application when clicked inside a completion
        list but not giving it back when an item is selected via a
        double-click.

        @param listId the ID of the user list
        @type int
        @param txt the selected text
        @type str
        """
        self.activateWindow()

    def updateVerticalScrollBar(self):
        """
        Public method to update the vertical scroll bar to reflect the
        additional lines added by annotations.
        """
        # Workaround because Scintilla.Redraw isn't implemented
        self.SendScintilla(QsciScintilla.SCI_SETVSCROLLBAR, 0)
        self.SendScintilla(QsciScintilla.SCI_SETVSCROLLBAR, 1)

    ###########################################################################
    ## utility methods
    ###########################################################################

    def _encodeString(self, string):
        """
        Protected method to encode a string depending on the current mode.

        @param string string to be encoded
        @type str
        @return encoded string
        @rtype bytes
        """
        if isinstance(string, bytes):
            return string
        else:
            if self.isUtf8():
                return string.encode("utf-8")
            else:
                return string.encode("latin-1")

    #########################################################################
    ## Methods below are missing from QScintilla.
    #########################################################################

    if "setWrapStartIndent" not in QsciScintilla.__dict__:

        def setWrapStartIndent(self, indent):
            """
            Public method to set a the amount of characters wrapped sublines
            shall be indented.

            @param indent amount of characters to indent
            @type int
            """
            self.SendScintilla(QsciScintilla.SCI_SETWRAPSTARTINDENT, indent)

    if "getGlobalCursorPosition" not in QsciScintilla.__dict__:

        def getGlobalCursorPosition(self):
            """
            Public method to determine the point of the cursor.

            @return point of the cursor
            @rtype QPoint
            """
            pos = self.currentPosition()
            x = self.SendScintilla(QsciScintilla.SCI_POINTXFROMPOSITION, 0, pos)
            y = self.SendScintilla(QsciScintilla.SCI_POINTYFROMPOSITION, 0, pos)
            return QPoint(x, y)

    if "cancelCallTips" not in QsciScintilla.__dict__:

        def cancelCallTips(self):
            """
            Public method to cancel displayed call tips.
            """
            self.SendScintilla(QsciScintilla.SCI_CALLTIPCANCEL)

    if "lineIndexFromPoint" not in QsciScintilla.__dict__:

        def lineIndexFromPoint(self, point):
            """
            Public method to convert a point to line and index.

            @param point point to be converted
            @type QPoint
            @return tuple containing the line number and index number
            @rtype tuple of (int, int)
            """
            pos = self.positionFromPoint(point)
            return self.lineIndexFromPosition(pos)

    if "setPrintColorMode" not in QsciScintilla.__dict__:

        def setPrintColorMode(self, colorMode):
            """
            Public method to set the print color mode (i.e. background handling).

            @param colorMode color mode to be set
            @type QsciScintillaPrintColorMode
            """
            self.SendScintilla(QsciScintilla.SCI_SETPRINTCOLOURMODE, colorMode)


##    #########################################################################
##    ## Methods below have been added to QScintilla starting with version 2.x.
##    #########################################################################
##
##    if "newMethod" not in QsciScintilla.__dict__:
##        def newMethod(self, param):
##            """
##            Public method to do something.
##
##            @param param parameter for method
##            """
##            pass
##
