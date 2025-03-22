# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing functions to map QScintilla keyboard commands to
QKeySequence standard keys.
"""

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QKeySequence

__all__ = ["s2qTranslate"]

Scintilla2QKeySequence = {
    QsciScintilla.SCI_CHARLEFT: QKeySequence.StandardKey.MoveToPreviousChar,
    QsciScintilla.SCI_CHARRIGHT: QKeySequence.StandardKey.MoveToNextChar,
    QsciScintilla.SCI_LINEUP: QKeySequence.StandardKey.MoveToPreviousLine,
    QsciScintilla.SCI_LINEDOWN: QKeySequence.StandardKey.MoveToNextLine,
    QsciScintilla.SCI_WORDPARTLEFT: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_WORDPARTRIGHT: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_WORDLEFT: QKeySequence.StandardKey.MoveToNextWord,
    QsciScintilla.SCI_WORDRIGHT: QKeySequence.StandardKey.MoveToPreviousWord,
    QsciScintilla.SCI_VCHOME: QKeySequence.StandardKey.MoveToStartOfLine,
    QsciScintilla.SCI_HOMEDISPLAY: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEEND: QKeySequence.StandardKey.MoveToEndOfLine,
    QsciScintilla.SCI_LINESCROLLDOWN: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINESCROLLUP: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_PARAUP: QKeySequence.StandardKey.MoveToStartOfBlock,
    QsciScintilla.SCI_PARADOWN: QKeySequence.StandardKey.MoveToEndOfBlock,
    QsciScintilla.SCI_PAGEUP: QKeySequence.StandardKey.MoveToPreviousPage,
    QsciScintilla.SCI_PAGEDOWN: QKeySequence.StandardKey.MoveToNextPage,
    QsciScintilla.SCI_DOCUMENTSTART: QKeySequence.StandardKey.MoveToStartOfDocument,
    QsciScintilla.SCI_DOCUMENTEND: QKeySequence.StandardKey.MoveToEndOfDocument,
    QsciScintilla.SCI_TAB: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_BACKTAB: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_CHARLEFTEXTEND: QKeySequence.StandardKey.SelectPreviousChar,
    QsciScintilla.SCI_CHARRIGHTEXTEND: QKeySequence.StandardKey.SelectNextChar,
    QsciScintilla.SCI_LINEUPEXTEND: QKeySequence.StandardKey.SelectPreviousLine,
    QsciScintilla.SCI_LINEDOWNEXTEND: QKeySequence.StandardKey.SelectNextLine,
    QsciScintilla.SCI_WORDPARTLEFTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_WORDPARTRIGHTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_WORDLEFTEXTEND: QKeySequence.StandardKey.SelectPreviousWord,
    QsciScintilla.SCI_WORDRIGHTEXTEND: QKeySequence.StandardKey.SelectNextWord,
    QsciScintilla.SCI_VCHOMEEXTEND: QKeySequence.StandardKey.SelectStartOfLine,
    QsciScintilla.SCI_LINEENDEXTEND: QKeySequence.StandardKey.SelectEndOfLine,
    QsciScintilla.SCI_PARAUPEXTEND: QKeySequence.StandardKey.SelectStartOfBlock,
    QsciScintilla.SCI_PARADOWNEXTEND: QKeySequence.StandardKey.SelectEndOfBlock,
    QsciScintilla.SCI_PAGEUPEXTEND: QKeySequence.StandardKey.SelectPreviousPage,
    QsciScintilla.SCI_PAGEDOWNEXTEND: QKeySequence.StandardKey.SelectNextPage,
    QsciScintilla.SCI_DOCUMENTSTARTEXTEND: (
        QKeySequence.StandardKey.SelectStartOfDocument
    ),
    QsciScintilla.SCI_DOCUMENTENDEXTEND: QKeySequence.StandardKey.SelectEndOfDocument,
    QsciScintilla.SCI_DELETEBACK: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_DELETEBACKNOTLINE: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_CLEAR: QKeySequence.StandardKey.Delete,
    QsciScintilla.SCI_DELWORDLEFT: QKeySequence.StandardKey.DeleteStartOfWord,
    QsciScintilla.SCI_DELWORDRIGHT: QKeySequence.StandardKey.DeleteEndOfWord,
    QsciScintilla.SCI_DELLINELEFT: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_DELLINERIGHT: QKeySequence.StandardKey.DeleteEndOfLine,
    QsciScintilla.SCI_NEWLINE: QKeySequence.StandardKey.InsertLineSeparator,
    QsciScintilla.SCI_LINEDELETE: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEDUPLICATE: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINETRANSPOSE: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINECUT: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINECOPY: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_EDITTOGGLEOVERTYPE: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEENDDISPLAY: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEENDDISPLAYEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_FORMFEED: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_CANCEL: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEDOWNRECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEUPRECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_CHARLEFTRECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_CHARRIGHTRECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_VCHOMERECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEENDRECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_PAGEUPRECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_PAGEDOWNRECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_SELECTIONDUPLICATE: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_SCROLLTOSTART: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_SCROLLTOEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_VERTICALCENTRECARET: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_WORDRIGHTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_WORDRIGHTENDEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_WORDLEFTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_WORDLEFTENDEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_HOME: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_HOMEEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_HOMERECTEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_HOMEDISPLAYEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_HOMEWRAP: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_HOMEWRAPEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_VCHOMEWRAP: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_VCHOMEWRAPEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEENDWRAP: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEENDWRAPEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_STUTTEREDPAGEUP: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_STUTTEREDPAGEUPEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_STUTTEREDPAGEDOWN: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_STUTTEREDPAGEDOWNEXTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_DELWORDRIGHTEND: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_MOVESELECTEDLINESUP: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_MOVESELECTEDLINESDOWN: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LOWERCASE: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_UPPERCASE: QKeySequence.StandardKey.UnknownKey,
    QsciScintilla.SCI_LINEDELETE: QKeySequence.StandardKey.DeleteCompleteLine,
    QsciScintilla.SCI_DELETEBACK: QKeySequence.StandardKey.Backspace,
}


def s2qTranslate(scintillaCommand):
    """
    Function to translate a QScintilla command to a QKeySequence.

    @param scintillaCommand QScintilla command
    @type int
    @return Qt key sequence
    @rtype QKeySequence.StandardKey
    """
    return Scintilla2QKeySequence[scintillaCommand]
