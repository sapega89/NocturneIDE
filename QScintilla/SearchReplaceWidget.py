# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the search and replace widget.
"""

import contextlib

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from eric7 import Preferences, Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox

from .Editor import Editor
from .Ui_SearchReplaceWidget import Ui_SearchReplaceWidget


class SearchReplaceWidget(QWidget, Ui_SearchReplaceWidget):
    """
    Class implementing the search and replace widget.

    @signal searchListChanged() emitted to indicate a change of the search list
    """

    searchListChanged = pyqtSignal()

    def __init__(self, vm, parent=None, sliding=False):
        """
        Constructor

        @param vm reference to the viewmanager object
        @type ViewManager
        @param parent parent widget of this widget (defaults to None)
        @type QWidget (optional)
        @param sliding flag indicating the widget is embedded in the
            sliding widget (defaults to False)
        @type bool (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.layout().setContentsMargins(1, 1, 1, 1)

        self.__viewmanager = vm
        self.__isMiniEditor = vm is parent
        self.__sliding = sliding
        if sliding:
            self.__topWidget = parent

        self.__findHistory = vm.getSRHistory("search")
        self.__replaceHistory = vm.getSRHistory("replace")
        whatsThis = self.tr(
            """<b>Find and Replace</b>
<p>This dialog is used to find some text and replace it with another text.
By checking the various checkboxes, the search can be made more specific.
The search string might be a regular expression. In a regular expression,
special characters interpreted are:</p>
"""
        )
        whatsThis += self.tr(
            """<table border="0">
<tr><td><code>.</code></td><td>Matches any character</td></tr>
<tr><td><code>(</code></td><td>This marks the start of a region for tagging a
match.</td></tr>
<tr><td><code>)</code></td><td>This marks the end of a tagged region.
</td></tr>
<tr><td><code>\\n</code></td>
<td>Where <code>n</code> is 1 through 9 refers to the first through ninth
tagged region when replacing. For example, if the search string was
<code>Fred([1-9])XXX</code> and the replace string was
<code>Sam\\1YYY</code>, when applied to <code>Fred2XXX</code> this would
generate <code>Sam2YYY</code>.</td></tr>
<tr><td><code>\\&lt;</code></td>
<td>This matches the start of a word using Scintilla's definitions of words.
</td></tr>
<tr><td><code>\\&gt;</code></td>
<td>This matches the end of a word using Scintilla's definition of words.
</td></tr>
<tr><td><code>\\x</code></td>
<td>This allows you to use a character x that would otherwise have a special
meaning. For example, \\[ would be interpreted as [ and not as the start of a
character set.</td></tr>
<tr><td><code>[...]</code></td>
<td>This indicates a set of characters, for example, [abc] means any of the
characters a, b or c. You can also use ranges, for example [a-z] for any lower
case character.</td></tr>
<tr><td><code>[^...]</code></td>
<td>The complement of the characters in the set. For example, [^A-Za-z] means
any character except an alphabetic character.</td></tr>
<tr><td><code>^</code></td>
<td>This matches the start of a line (unless used inside a set, see above).
</td></tr>
<tr><td><code>$</code></td> <td>This matches the end of a line.</td></tr>
<tr><td><code>*</code></td>
<td>This matches 0 or more times. For example, <code>Sa*m</code> matches
<code>Sm</code>, <code>Sam</code>, <code>Saam</code>, <code>Saaam</code>
and so on.</td></tr>
<tr><td><code>+</code></td>
<td>This matches 1 or more times. For example, <code>Sa+m</code> matches
<code>Sam</code>, <code>Saam</code>, <code>Saaam</code> and so on.</td></tr>
</table>
<p>When using the Extended (C++11) regular expression mode more features are
available, generally similar to regular expression support in JavaScript. See
the documentation of your C++ runtime for details on what is supported.<p>
"""
        )
        self.setWhatsThis(whatsThis)

        # set icons
        self.closeButton.setIcon(EricPixmapCache.getIcon("close"))
        self.findPrevButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.findNextButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))
        self.extendButton.setIcon(EricPixmapCache.getIcon("2rightarrow"))

        self.replaceButton.setIcon(EricPixmapCache.getIcon("editReplace"))
        self.replaceSearchButton.setIcon(EricPixmapCache.getIcon("editReplaceSearch"))
        self.replaceAllButton.setIcon(EricPixmapCache.getIcon("editReplaceAll"))

        # set line edit completers
        self.findtextCombo.setCompleter(None)
        self.findtextCombo.lineEdit().returnPressed.connect(self.__findByReturnPressed)
        self.findtextCombo.lineEdit().setClearButtonEnabled(True)
        self.replacetextCombo.setCompleter(None)
        self.replacetextCombo.lineEdit().returnPressed.connect(
            self.on_replaceButton_clicked
        )
        self.replacetextCombo.lineEdit().setClearButtonEnabled(True)

        self.__currentEditor = None
        self.__replaceMode = False

        self.findtextCombo.lineEdit().textEdited.connect(self.__quickSearch)
        self.caseCheckBox.toggled.connect(self.__updateQuickSearchMarkers)
        self.wordCheckBox.toggled.connect(self.__updateQuickSearchMarkers)
        self.regexpCheckBox.toggled.connect(self.__updateQuickSearchMarkers)

        self.replacetextCombo.installEventFilter(self)

        self.__findtextComboStyleSheet = self.findtextCombo.styleSheet()

        self.modeToggleButton.clicked.connect(self.__toggleReplaceMode)

        self.__quickSearchMarkOccurrencesTimer = QTimer(self)
        self.__quickSearchMarkOccurrencesTimer.setSingleShot(True)
        self.__quickSearchMarkOccurrencesTimer.timeout.connect(
            self.__quickSearchMarkOccurrences
        )

        # define actions
        self.modeToggleAct = EricAction(
            self.tr("Toggle Mode"),
            self.tr("Toggle Mode"),
            0,
            0,
            self,
            "search_widget_togle_mode",
        )
        self.modeToggleAct.triggered.connect(self.__toggleReplaceMode)
        self.modeToggleAct.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )

        self.findNextAct = EricAction(
            self.tr("Find Next"),
            self.tr("Find Next"),
            0,
            0,
            self,
            "search_widget_find_next",
        )
        self.findNextAct.triggered.connect(self.on_findNextButton_clicked)
        self.findNextAct.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )

        self.findPrevAct = EricAction(
            self.tr("Find Prev"),
            self.tr("Find Prev"),
            0,
            0,
            self,
            "search_widget_find_prev",
        )
        self.findPrevAct.triggered.connect(self.on_findPrevButton_clicked)
        self.findPrevAct.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )

        self.replaceAndSearchAct = EricAction(
            self.tr("Replace and Search"),
            self.tr("Replace and Search"),
            0,
            0,
            self,
            "replace_widget_replace_search",
        )
        self.replaceAndSearchAct.triggered.connect(self.on_replaceSearchButton_clicked)
        self.replaceAndSearchAct.setEnabled(False)
        self.replaceAndSearchAct.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )

        self.replaceSelectionAct = EricAction(
            self.tr("Replace Occurrence"),
            self.tr("Replace Occurrence"),
            0,
            0,
            self,
            "replace_widget_replace_occurrence",
        )
        self.replaceSelectionAct.triggered.connect(self.on_replaceButton_clicked)
        self.replaceSelectionAct.setEnabled(False)
        self.replaceSelectionAct.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )

        self.replaceAllAct = EricAction(
            self.tr("Replace All"),
            self.tr("Replace All"),
            0,
            0,
            self,
            "replace_widget_replace_all",
        )
        self.replaceAllAct.triggered.connect(self.on_replaceAllButton_clicked)
        self.replaceAllAct.setEnabled(False)
        self.replaceAllAct.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )

        self.addAction(self.modeToggleAct)
        self.addAction(self.findNextAct)
        self.addAction(self.findPrevAct)
        self.addAction(self.replaceAndSearchAct)
        self.addAction(self.replaceSelectionAct)
        self.addAction(self.replaceAllAct)

        # disable search and replace buttons and actions
        self.__setFindNextEnabled(False)
        self.__setFindPrevEnabled(False)
        self.__setReplaceAndSearchEnabled(False)
        self.__setReplaceSelectionEnabled(False)
        self.__setReplaceAllEnabled(False)

        self.adjustSize()

        self.havefound = False
        self.__pos = None
        self.__findBackwards = False
        self.__selections = []
        self.__finding = False

    def eventFilter(self, obj, evt):
        """
        Public method to handle events for other objects.

        @param obj reference to the object
        @type QObject
        @param evt reference to the event
        @type QEvent
        @return flag indicating that the event should be filtered out
        @rtype bool
        """
        if (
            obj is self.replacetextCombo
            and evt.type() == QEvent.Type.FocusIn
            and self.__replaceMode
        ):
            if not bool(self.replacetextCombo.currentText()):
                self.replacetextCombo.setCurrentText(self.findtextCombo.currentText())
            self.replacetextCombo.lineEdit().selectAll()

        return super().eventFilter(obj, evt)

    def changeEvent(self, evt):
        """
        Protected method handling state changes.

        @param evt event containing the state change
        @type QEvent
        """
        if evt.type() == QEvent.Type.FontChange:
            self.adjustSize()

    def __setShortcuts(self):
        """
        Private method to set the local action's shortcuts to the same key
        sequences as in the view manager.
        """
        if not self.__isMiniEditor:
            if self.__replaceMode:
                self.modeToggleAct.setShortcuts(
                    self.__viewmanager.searchAct.shortcuts()
                )
            else:
                self.modeToggleAct.setShortcuts(
                    self.__viewmanager.replaceAct.shortcuts()
                )
            self.findNextAct.setShortcuts(self.__viewmanager.searchNextAct.shortcuts())
            self.findPrevAct.setShortcuts(self.__viewmanager.searchPrevAct.shortcuts())

            self.replaceAndSearchAct.setShortcuts(
                self.__viewmanager.replaceAndSearchAct.shortcuts()
            )
            self.replaceSelectionAct.setShortcuts(
                self.__viewmanager.replaceSelectionAct.shortcuts()
            )
            self.replaceAllAct.setShortcuts(
                self.__viewmanager.replaceAllAct.shortcuts()
            )

            # Set the tooltips of the associated buttons to include the action
            # shortcuts.
            self.findNextButton.setToolTip(
                self.tr("Press to find the next occurrence ({0})").format(
                    self.findNextAct.shortcut().toString(
                        QKeySequence.SequenceFormat.NativeText
                    )
                )
            )
            self.findPrevButton.setToolTip(
                self.tr("Press to find the previous occurrence ({0})").format(
                    self.findPrevAct.shortcut().toString(
                        QKeySequence.SequenceFormat.NativeText
                    )
                )
            )
            self.replaceSearchButton.setToolTip(
                self.tr(
                    "Press to replace the selection and search for the next occurence"
                    " ({0})"
                ).format(
                    self.replaceAndSearchAct.shortcut().toString(
                        QKeySequence.SequenceFormat.NativeText
                    )
                )
            )
            self.replaceButton.setToolTip(
                self.tr("Press to replace the selection ({0})").format(
                    self.replaceSelectionAct.shortcut().toString(
                        QKeySequence.SequenceFormat.NativeText
                    )
                )
            )
            self.replaceAllButton.setToolTip(
                self.tr("Press to replace all occurrences ({0})").format(
                    self.replaceAllAct.shortcut().toString(
                        QKeySequence.SequenceFormat.NativeText
                    )
                )
            )

    def __setFindNextEnabled(self, enable):
        """
        Private method to set the enabled state of "Find Next".

        @param enable flag indicating the enable state to be set
        @type bool
        """
        self.findNextButton.setEnabled(enable)
        self.findNextAct.setEnabled(enable)

    def __setFindPrevEnabled(self, enable):
        """
        Private method to set the enabled state of "Find Prev".

        @param enable flag indicating the enable state to be set
        @type bool
        """
        self.findPrevButton.setEnabled(enable)
        self.findPrevAct.setEnabled(enable)

    def __setReplaceAndSearchEnabled(self, enable):
        """
        Private method to set the enabled state of "Replace And Search".

        @param enable flag indicating the enable state to be set
        @type bool
        """
        enable &= self.__replaceMode
        self.replaceSearchButton.setEnabled(enable)
        self.replaceAndSearchAct.setEnabled(enable)

    def __setReplaceSelectionEnabled(self, enable):
        """
        Private method to set the enabled state of "Replace Occurrence".

        @param enable flag indicating the enable state to be set
        @type bool
        """
        enable &= self.__replaceMode
        self.replaceButton.setEnabled(enable)
        self.replaceSelectionAct.setEnabled(enable)

    def __setReplaceAllEnabled(self, enable):
        """
        Private method to set the enabled state of "Replace All".

        @param enable flag indicating the enable state to be set
        @type bool
        """
        enable &= self.__replaceMode
        self.replaceAllButton.setEnabled(enable)
        self.replaceAllAct.setEnabled(enable)

    def __selectionBoundary(self, selections=None):
        """
        Private method to calculate the current selection boundary.

        @param selections optional parameter giving the selections to
            calculate the boundary for (defaults to None)
        @type list of tuples of four int
        @return tuple of start line and index and end line and index
        @rtype tuple (int, int, int, int)
        """
        aw = self.__viewmanager.activeWindow()

        if selections is None:
            selectionMarkerRange = aw.getSearchSelectionHighlight()
            if selectionMarkerRange == (0, 0, 0, 0):
                selections = self.__selections
            else:
                selections = [selectionMarkerRange]
        if selections:
            lineNumbers = [sel[0] for sel in selections] + [
                sel[2] for sel in selections
            ]
            indexNumbers = [sel[1] for sel in selections] + [
                sel[3] for sel in selections
            ]
            startLine, startIndex, endLine, endIndex = (
                min(lineNumbers),
                min(indexNumbers),
                max(lineNumbers),
                max(indexNumbers),
            )
        else:
            startLine, startIndex, endLine, endIndex = -1, -1, -1, -1

        return startLine, startIndex, endLine, endIndex

    @pyqtSlot()
    def __toggleReplaceMode(self):
        """
        Private slot to toggle the widget mode.
        """
        replaceMode = not self.__replaceMode
        if self.__sliding:
            self.__topWidget.show(
                text=self.findtextCombo.currentText(), replaceMode=replaceMode
            )
        else:
            self.show(text=self.findtextCombo.currentText(), replaceMode=replaceMode)

    @pyqtSlot(str)
    def on_findtextCombo_editTextChanged(self, txt):
        """
        Private slot to enable/disable the find buttons.

        @param txt text of the find text combo
        @type str
        """
        enable = bool(txt)

        self.__setFindNextEnabled(enable)
        self.__setFindPrevEnabled(enable)
        self.extendButton.setEnabled(enable)
        if not Preferences.getEditor("QuickSearchEnabled") or not bool(txt):
            self.__setReplaceSelectionEnabled(False)
            self.__setReplaceAndSearchEnabled(False)
        self.__setReplaceAllEnabled(enable)

    @pyqtSlot(bool)
    def on_regexpCheckBox_toggled(self, checked):
        """
        Private slot handling a change of the regexp selector.

        @param checked state of the regexp selector
        @type bool
        """
        if checked:
            # only one of regexp or escape can be selected
            self.escapeCheckBox.setChecked(False)

    @pyqtSlot(bool)
    def on_escapeCheckBox_toggled(self, checked):
        """
        Private slot handling a change of the escape selector.

        @param checked state of the escape selector
        @type bool
        """
        if checked:
            # only one of regexp or escape can be selected
            self.regexpCheckBox.setChecked(False)

    @pyqtSlot(str)
    def __quickSearch(self, txt):
        """
        Private slot to search for the entered text while typing.

        @param txt text of the search edit
        @type str
        """
        if Preferences.getEditor("QuickSearchEnabled"):
            aw = self.__viewmanager.activeWindow()
            aw.hideFindIndicator()

            if self.escapeCheckBox.isChecked():
                txt = Utilities.unslash(txt)

            if Preferences.getEditor("QuickSearchMarkersEnabled"):
                self.__quickSearchMarkOccurrencesTimer.start(
                    Preferences.getEditor("QuickSearchMarkOccurrencesTimeout")
                )

            if self.selectionCheckBox.isChecked():
                lineFrom, indexFrom, lineTo, indexTo = self.__selectionBoundary()
                aw.highlightSearchSelection(lineFrom, indexFrom, lineTo, indexTo)
            else:
                # start quick search at the current cursor position adjusted to a
                # previous quicksearch
                lineFrom, indexFrom = aw.getCursorPosition()
                sline, sindex, eline, eindex = aw.getSelection()
                if (lineFrom, indexFrom) == (eline, eindex):
                    lineFrom, indexFrom = sline, sindex
                lineTo = lineFrom
                indexTo = indexFrom - 1 if bool(indexFrom) else 0
            posixMode = (
                Preferences.getEditor("SearchRegexpMode") == 0
                and self.regexpCheckBox.isChecked()
            )
            cxx11Mode = (
                Preferences.getEditor("SearchRegexpMode") == 1
                and self.regexpCheckBox.isChecked()
            )

            self.__finding = True
            ok = aw.findFirst(
                txt,
                self.regexpCheckBox.isChecked(),
                self.caseCheckBox.isChecked(),
                self.wordCheckBox.isChecked(),
                self.wrapCheckBox.isChecked(),
                forward=not self.__findBackwards,
                line=lineFrom,
                index=indexFrom,
                posix=posixMode,
                cxx11=cxx11Mode,
            )
            if ok:
                sline, sindex, eline, eindex = aw.getSelection()
                if (
                    (sline == lineFrom and sindex >= indexFrom)
                    or (sline > lineFrom and sline < lineTo)
                    or (sline == lineTo and sindex <= indexTo)
                ):
                    aw.showFindIndicator(sline, sindex, eline, eindex)

            self.__finding = False

            self.__setReplaceSelectionEnabled(ok)
            self.__setReplaceAndSearchEnabled(ok)

            if not txt:
                ok = True  # reset the color in case of an empty text

            self.__setSearchEditColors(ok)

    @pyqtSlot()
    def __quickSearchMarkOccurrences(self):
        """
        Private slot to mark all occurrences of the current search text.
        """
        aw = self.__viewmanager.activeWindow()

        txt = self.findtextCombo.currentText()
        if self.escapeCheckBox.isChecked():
            txt = Utilities.unslash(txt)

        if self.selectionCheckBox.isChecked():
            lineFrom, indexFrom, lineTo, indexTo = self.__selectionBoundary()
        else:
            lineFrom, indexFrom, lineTo, indexTo = 0, 0, -1, -1

        aw.clearSearchIndicators()
        posixMode = (
            Preferences.getEditor("SearchRegexpMode") == 0
            and self.regexpCheckBox.isChecked()
        )
        cxx11Mode = (
            Preferences.getEditor("SearchRegexpMode") == 1
            and self.regexpCheckBox.isChecked()
        )
        ok = aw.findFirstTarget(
            txt,
            self.regexpCheckBox.isChecked(),
            self.caseCheckBox.isChecked(),
            self.wordCheckBox.isChecked(),
            lineFrom,
            indexFrom,
            lineTo,
            indexTo,
            posix=posixMode,
            cxx11=cxx11Mode,
        )
        while ok:
            tgtPos, tgtLen = aw.getFoundTarget()
            if tgtLen == 0:
                break
            if len(self.__selections) > 1:
                sline, sindex = aw.lineIndexFromPosition(tgtPos)
                eline, eindex = aw.lineIndexFromPosition(tgtPos + tgtLen)
                indicate = (
                    (sline == lineFrom and sindex >= indexFrom)
                    or (sline > lineFrom and sline < lineTo)
                    or (sline == lineTo and sindex <= indexTo)
                )
            else:
                indicate = True
            if indicate:
                aw.setSearchIndicator(tgtPos, tgtLen)
            ok = aw.findNextTarget()

    def __setSearchEditColors(self, ok):
        """
        Private method to set the search edit colors.

        @param ok flag indicating a match
        @type bool
        """
        if not ok:
            self.findtextCombo.setStyleSheet(
                "color: #000000; background-color: #ff6666;"
            )
        else:
            self.findtextCombo.setStyleSheet(self.__findtextComboStyleSheet)

    @pyqtSlot()
    def on_extendButton_clicked(self):
        """
        Private slot to handle the quick search extend action.
        """
        aw = self.__viewmanager.activeWindow()
        if aw is None:
            return

        txt = self.findtextCombo.currentText()
        if not txt:
            return

        line, index = aw.getCursorPosition()
        word = aw.getWord(line, index)
        self.findtextCombo.setEditText(word)
        self.findtextCombo.lineEdit().selectAll()
        self.__quickSearch(word)

    @pyqtSlot(bool)
    def __updateQuickSearchMarkers(self, _on):
        """
        Private slot to handle the selection of the various check boxes.

        @param _on status of the check box (unused)
        @type bool
        """
        txt = self.findtextCombo.currentText()
        self.__quickSearch(txt)

    @pyqtSlot()
    def on_findNextButton_clicked(self):
        """
        Private slot to find the next occurrence of text.
        """
        self.findNext()

    @pyqtSlot()
    def findNext(self):
        """
        Public slot to find the next occurrence of text.
        """
        if not self.havefound or not self.findtextCombo.currentText():
            self.__viewmanager.showSearchWidget()
            return

        self.__findBackwards = False
        txt = self.findtextCombo.currentText()

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if txt in self.__findHistory:
            self.__findHistory.remove(txt)
        self.__findHistory.insert(0, txt)
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.__findHistory)
        self.searchListChanged.emit()

        ok = self.__findNextPrev(txt, False)
        self.__setSearchEditColors(ok)
        if ok:
            self.__setReplaceSelectionEnabled(True)
            self.__setReplaceAndSearchEnabled(True)
        else:
            EricMessageBox.information(
                self, self.windowTitle(), self.tr("'{0}' was not found.").format(txt)
            )

    @pyqtSlot()
    def on_findPrevButton_clicked(self):
        """
        Private slot to find the previous occurrence of text.
        """
        self.findPrev()

    @pyqtSlot()
    def findPrev(self):
        """
        Public slot to find the next previous of text.
        """
        if not self.havefound or not self.findtextCombo.currentText():
            self.show(self.__viewmanager.textForFind())
            return

        self.__findBackwards = True
        txt = self.findtextCombo.currentText()

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if txt in self.__findHistory:
            self.__findHistory.remove(txt)
        self.__findHistory.insert(0, txt)
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.__findHistory)
        self.searchListChanged.emit()

        ok = self.__findNextPrev(txt, True)
        self.__setSearchEditColors(ok)
        if ok:
            self.__setReplaceSelectionEnabled(True)
            self.__setReplaceAndSearchEnabled(True)
        else:
            EricMessageBox.information(
                self, self.windowTitle(), self.tr("'{0}' was not found.").format(txt)
            )

    @pyqtSlot()
    def __findByReturnPressed(self):
        """
        Private slot to handle the returnPressed signal of the findtext
        combobox.
        """
        if self.__findBackwards:
            self.findPrev()
        else:
            self.findNext()

    def __markOccurrences(self, txt):
        """
        Private method to mark all occurrences of the search text.

        @param txt text to search for
        @type str
        """
        aw = self.__viewmanager.activeWindow()
        if self.selectionCheckBox.isChecked():
            lineFrom, indexFrom, lineTo, indexTo = self.__selectionBoundary()
        else:
            lineFrom, indexFrom, lineTo, indexTo = 0, 0, -1, -1
        posixMode = (
            Preferences.getEditor("SearchRegexpMode") == 0
            and self.regexpCheckBox.isChecked()
        )
        cxx11Mode = (
            Preferences.getEditor("SearchRegexpMode") == 1
            and self.regexpCheckBox.isChecked()
        )

        aw.clearSearchIndicators()
        ok = aw.findFirstTarget(
            txt,
            self.regexpCheckBox.isChecked(),
            self.caseCheckBox.isChecked(),
            self.wordCheckBox.isChecked(),
            lineFrom,
            indexFrom,
            lineTo,
            indexTo,
            posix=posixMode,
            cxx11=cxx11Mode,
        )
        while ok:
            tgtPos, tgtLen = aw.getFoundTarget()
            if tgtLen == 0:
                break
            if len(self.__selections) > 1:
                lineFrom, indexFrom = aw.lineIndexFromPosition(tgtPos)
                lineTo, indexTo = aw.lineIndexFromPosition(tgtPos + tgtLen)
                for sel in self.__selections:
                    if lineFrom == sel[0] and indexFrom >= sel[1] and indexTo <= sel[3]:
                        indicate = True
                        break
                else:
                    indicate = False
            else:
                indicate = True
            if indicate:
                aw.setSearchIndicator(tgtPos, tgtLen)
            ok = aw.findNextTarget()
        with contextlib.suppress(AttributeError):
            aw.updateMarkerMap()
            # ignore it for MiniEditor

    def __findNextPrev(self, txt, backwards):
        """
        Private method to find the next occurrence of the search text.

        @param txt text to search for
        @type str
        @param backwards flag indicating a backwards search
        @type bool
        @return flag indicating success
        @rtype bool
        """
        self.__finding = True

        if self.escapeCheckBox.isChecked():
            txt = Utilities.unslash(txt)

        if Preferences.getEditor("SearchMarkersEnabled"):
            self.__markOccurrences(txt)

        aw = self.__viewmanager.activeWindow()
        aw.hideFindIndicator()
        cline, cindex = aw.getCursorPosition()

        ok = True
        lineFrom, indexFrom, lineTo, indexTo = aw.getSelection()
        boundary = self.__selectionBoundary()
        if self.selectionCheckBox.isChecked():
            aw.highlightSearchSelection(*boundary)
        if backwards:
            if (
                self.selectionCheckBox.isChecked()
                and (lineFrom, indexFrom, lineTo, indexTo) == boundary
            ):
                # initial call
                line, index = boundary[2:]
            else:
                if (lineFrom, indexFrom) == (-1, -1):
                    # no selection present
                    line = cline
                    index = cindex
                else:
                    line = lineFrom
                    index = indexFrom
            if (
                self.selectionCheckBox.isChecked()
                and line == boundary[0]
                and index >= 0
                and index < boundary[1]
            ):
                ok = False

            if ok and index < 0:
                line -= 1
                if self.selectionCheckBox.isChecked():
                    if line < boundary[0]:
                        if self.wrapCheckBox.isChecked():
                            line, index = boundary[2:]
                        else:
                            ok = False
                    else:
                        index = aw.lineLength(line)
                else:
                    if line < 0:
                        if self.wrapCheckBox.isChecked():
                            line = aw.lines() - 1
                            index = aw.lineLength(line)
                        else:
                            ok = False
                    else:
                        index = aw.lineLength(line)
        else:
            if (
                self.selectionCheckBox.isChecked()
                and (lineFrom, indexFrom, lineTo, indexTo) == boundary
            ):
                # initial call
                line, index = boundary[:2]
            else:
                line = lineTo
                index = indexTo

        if ok:
            posixMode = (
                Preferences.getEditor("SearchRegexpMode") == 0
                and self.regexpCheckBox.isChecked()
            )
            cxx11Mode = (
                Preferences.getEditor("SearchRegexpMode") == 1
                and self.regexpCheckBox.isChecked()
            )
            ok = aw.findFirst(
                txt,
                self.regexpCheckBox.isChecked(),
                self.caseCheckBox.isChecked(),
                self.wordCheckBox.isChecked(),
                self.wrapCheckBox.isChecked(),
                forward=not backwards,
                line=line,
                index=index,
                posix=posixMode,
                cxx11=cxx11Mode,
            )

        if ok and self.selectionCheckBox.isChecked():
            lineFrom, indexFrom, lineTo, indexTo = aw.getSelection()
            if len(self.__selections) > 1:
                for sel in self.__selections:
                    if lineFrom == sel[0] and indexFrom >= sel[1] and indexTo <= sel[3]:
                        ok = True
                        break
                else:
                    ok = False
            elif (
                (lineFrom == boundary[0] and indexFrom >= boundary[1])
                or (lineFrom > boundary[0] and lineFrom < boundary[2])
                or (lineFrom == boundary[2] and indexFrom <= boundary[3])
            ):
                ok = True
            else:
                ok = False
            if not ok and len(self.__selections) > 1:
                # try again
                while not ok and (
                    (backwards and lineFrom >= boundary[0])
                    or (not backwards and lineFrom <= boundary[2])
                ):
                    for ind in range(len(self.__selections)):
                        if lineFrom == self.__selections[ind][0]:
                            after = indexTo > self.__selections[ind][3]
                            if backwards:
                                if after:
                                    line, index = self.__selections[ind][2:]
                                else:
                                    if ind > 0:
                                        line, index = self.__selections[ind - 1][2:]
                            else:
                                if after:
                                    if ind < len(self.__selections) - 1:
                                        line, index = self.__selections[ind + 1][:2]
                                else:
                                    line, index = self.__selections[ind][:2]
                            break
                    else:
                        break
                    ok = aw.findFirst(
                        txt,
                        self.regexpCheckBox.isChecked(),
                        self.caseCheckBox.isChecked(),
                        self.wordCheckBox.isChecked(),
                        self.wrapCheckBox.isChecked(),
                        forward=not backwards,
                        line=line,
                        index=index,
                        posix=posixMode,
                        cxx11=cxx11Mode,
                    )
                    if ok:
                        lineFrom, indexFrom, lineTo, indexTo = aw.getSelection()
                        if (
                            lineFrom < boundary[0]
                            or lineFrom > boundary[2]
                            or indexFrom < boundary[1]
                            or indexFrom > boundary[3]
                            or indexTo < boundary[1]
                            or indexTo > boundary[3]
                        ):
                            ok = False
                            break
            if not ok:
                if self.wrapCheckBox.isChecked():
                    # try it again
                    if backwards:
                        line, index = boundary[2:]
                    else:
                        line, index = boundary[:2]
                    ok = aw.findFirst(
                        txt,
                        self.regexpCheckBox.isChecked(),
                        self.caseCheckBox.isChecked(),
                        self.wordCheckBox.isChecked(),
                        self.wrapCheckBox.isChecked(),
                        forward=not backwards,
                        line=line,
                        index=index,
                        posix=posixMode,
                        cxx11=cxx11Mode,
                    )
                    if ok:
                        lineFrom, indexFrom, lineTo, indexTo = aw.getSelection()
                        if len(self.__selections) > 1:
                            for sel in self.__selections:
                                if (
                                    lineFrom == sel[0]
                                    and indexFrom >= sel[1]
                                    and indexTo <= sel[3]
                                ):
                                    ok = True
                                    break
                            else:
                                ok = False
                        elif (
                            (lineFrom == boundary[0] and indexFrom >= boundary[1])
                            or (lineFrom > boundary[0] and lineFrom < boundary[2])
                            or (lineFrom == boundary[2] and indexFrom <= boundary[3])
                        ):
                            ok = True
                        else:
                            ok = False
                else:
                    ok = False

            if not ok:
                aw.selectAll(False)
                aw.setCursorPosition(cline, cindex)
                aw.ensureCursorVisible()

        if ok:
            sline, sindex, eline, eindex = aw.getSelection()
            aw.showFindIndicator(sline, sindex, eline, eindex)

        self.__finding = False

        return ok

    def __showFind(self, text=""):
        """
        Private method to display this widget in find mode.

        @param text text to be shown in the findtext edit (defaults to "")
        @type str (optional)
        """
        self.modeToggleButton.setIcon(EricPixmapCache.getIcon("1downarrow"))

        # hide the replace related widgets
        for widget in (
            self.replaceLabel,
            self.replacetextCombo,
            self.replaceButton,
            self.replaceSearchButton,
            self.replaceAllButton,
        ):
            widget.setVisible(False)
            widget.setEnabled(False)

        self.__setSearchEditColors(True)
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.__findHistory)
        self.findtextCombo.setEditText(text)
        self.findtextCombo.lineEdit().selectAll()
        self.findtextCombo.setFocus()
        self.on_findtextCombo_editTextChanged(text)

        self.caseCheckBox.setChecked(False)
        self.wordCheckBox.setChecked(False)
        self.wrapCheckBox.setChecked(True)
        self.regexpCheckBox.setChecked(False)

        aw = self.__viewmanager.activeWindow()
        self.updateSelectionCheckBox(aw)

        self.havefound = True
        self.__findBackwards = False

        self.__setShortcuts()

    def selectionChanged(self, editor):
        """
        Public slot tracking changes of selected text.

        @param editor reference to the editor
        @type Editor
        """
        self.updateSelectionCheckBox(editor)

    @pyqtSlot(Editor)
    def updateSelectionCheckBox(self, editor):
        """
        Public slot to update the selection check box.

        @param editor reference to the editor
        @type Editor
        """
        from .MiniEditor import MiniScintilla

        if not self.__finding and isinstance(editor, (Editor, MiniScintilla)):
            if self.__currentEditor is not None and self.__currentEditor is not editor:
                self.__currentEditor.clearSearchSelectionHighlight()
            self.__currentEditor = editor

            if editor.hasSelectedText():
                selections = editor.getSelections()
                line1, index1, line2, _index2 = self.__selectionBoundary(selections)
                if line1 != line2:
                    self.selectionCheckBox.setEnabled(True)
                    self.selectionCheckBox.setChecked(True)
                    self.__selections = selections
                    self.__currentEditor.clearSearchSelectionHighlight()
                    return

            self.selectionCheckBox.setEnabled(False)
            self.selectionCheckBox.setChecked(False)
            self.__selections = []

    @pyqtSlot(Editor)
    def editorClosed(self, editor):
        """
        Public slot to handle the closing of an editor.

        @param editor reference to the closed editor
        @type Editor
        """
        if self.__currentEditor is not None and self.__currentEditor is editor:
            self.__currentEditor = None

    def replace(self):
        """
        Public method to replace the current selection.
        """
        if self.replaceButton.isEnabled():
            self.__doReplace(False)

    def replaceSearch(self):
        """
        Public method to replace the current selection and search again.
        """
        if self.replaceSearchButton.isEnabled():
            self.__doReplace(True)

    @pyqtSlot()
    def on_replaceButton_clicked(self):
        """
        Private slot to replace one occurrence of text.
        """
        self.__doReplace(False)

    @pyqtSlot()
    def on_replaceSearchButton_clicked(self):
        """
        Private slot to replace one occurrence of text and search for the next
        one.
        """
        self.__doReplace(True)

    def __doReplace(self, searchNext):
        """
        Private method to replace one occurrence of text.

        @param searchNext flag indicating to search for the next occurrence.
        @type bool
        """
        self.__finding = True

        # Check enabled status due to dual purpose usage of this method
        if (
            not self.replaceButton.isEnabled()
            and not self.replaceSearchButton.isEnabled()
        ):
            return

        ftxt = self.findtextCombo.currentText()
        rtxt = self.replacetextCombo.currentText()

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if rtxt in self.__replaceHistory:
            self.__replaceHistory.remove(rtxt)
        self.__replaceHistory.insert(0, rtxt)
        self.replacetextCombo.clear()
        self.replacetextCombo.addItems(self.__replaceHistory)

        aw = self.__viewmanager.activeWindow()
        aw.hideFindIndicator()
        if self.escapeCheckBox.isChecked():
            aw.replace(Utilities.unslash(rtxt))
        else:
            aw.replace(rtxt)

        if searchNext:
            ok = self.__findNextPrev(ftxt, self.__findBackwards)
            self.__setSearchEditColors(ok)

            if not ok:
                self.__setReplaceSelectionEnabled(False)
                self.__setReplaceAndSearchEnabled(False)
                EricMessageBox.information(
                    self,
                    self.windowTitle(),
                    self.tr("'{0}' was not found.").format(ftxt),
                )
        else:
            self.__setReplaceSelectionEnabled(False)
            self.__setReplaceAndSearchEnabled(False)
            self.__setSearchEditColors(True)

        self.__finding = False

    def replaceAll(self):
        """
        Public method to replace all occurrences.
        """
        if self.replaceAllButton.isEnabled():
            self.on_replaceAllButton_clicked()

    @pyqtSlot()
    def on_replaceAllButton_clicked(self):
        """
        Private slot to replace all occurrences of text.
        """
        self.__finding = True

        replacements = 0
        ftxt = self.findtextCombo.currentText()
        rtxt = self.replacetextCombo.currentText()

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if ftxt in self.__findHistory:
            self.__findHistory.remove(ftxt)
        self.__findHistory.insert(0, ftxt)
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.__findHistory)

        if rtxt in self.__replaceHistory:
            self.__replaceHistory.remove(rtxt)
        self.__replaceHistory.insert(0, rtxt)
        self.replacetextCombo.clear()
        self.replacetextCombo.addItems(self.__replaceHistory)

        selectionOnly = self.selectionCheckBox.isChecked()

        aw = self.__viewmanager.activeWindow()
        aw.hideFindIndicator()
        cline, cindex = aw.getCursorPosition()
        if selectionOnly:
            boundary = self.__selectionBoundary()
            aw.highlightSearchSelection(*boundary)
            aw.setSelection(*boundary)  # Just in case it was changed by quicksearch.
        else:
            line = 0
            index = 0
        posixMode = (
            Preferences.getEditor("SearchRegexpMode") == 0
            and self.regexpCheckBox.isChecked()
        )
        cxx11Mode = (
            Preferences.getEditor("SearchRegexpMode") == 1
            and self.regexpCheckBox.isChecked()
        )
        if self.escapeCheckBox.isChecked():
            ftxt = Utilities.unslash(ftxt)

        ok = (
            aw.findFirstInSelection(
                ftxt,
                self.regexpCheckBox.isChecked(),
                self.caseCheckBox.isChecked(),
                self.wordCheckBox.isChecked(),
                forward=True,
                posix=posixMode,
                cxx11=cxx11Mode,
            )
            if selectionOnly
            else aw.findFirst(
                ftxt,
                self.regexpCheckBox.isChecked(),
                self.caseCheckBox.isChecked(),
                self.wordCheckBox.isChecked(),
                False,
                forward=True,
                line=line,
                index=index,
                posix=posixMode,
                cxx11=cxx11Mode,
            )
        )
        found = ok

        aw.beginUndoAction()
        wordWrap = self.wrapCheckBox.isChecked()
        self.wrapCheckBox.setChecked(False)
        if self.escapeCheckBox.isChecked():
            rtxt = Utilities.unslash(rtxt)

        while ok:
            aw.replace(rtxt)
            replacements += 1
            ok = aw.findNext()
        aw.endUndoAction()
        if wordWrap:
            self.wrapCheckBox.setChecked(True)
        self.__setReplaceSelectionEnabled(False)
        self.__setReplaceAndSearchEnabled(False)

        if found:
            EricMessageBox.information(
                self,
                self.windowTitle(),
                self.tr("Replaced {0} occurrences.").format(replacements),
            )
        else:
            EricMessageBox.information(
                self,
                self.windowTitle(),
                self.tr("Nothing replaced because '{0}' was not found.").format(ftxt),
            )

        aw.setCursorPosition(cline, cindex)
        aw.ensureCursorVisible()

        self.__finding = False

        aw.clearSearchSelectionHighlight()
        self.updateSelectionCheckBox(aw)

    def __showReplace(self, text=""):
        """
        Private slot to display this widget in replace mode.

        @param text text to be shown in the findtext edit (defaults to "")
        @type str (optional)
        """
        self.modeToggleButton.setIcon(EricPixmapCache.getIcon("1uparrow"))

        # show the replace related widgets
        for widget in (
            self.replaceLabel,
            self.replacetextCombo,
            self.replaceButton,
            self.replaceSearchButton,
            self.replaceAllButton,
        ):
            widget.setVisible(True)
            widget.setEnabled(True)

        self.__setSearchEditColors(True)
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.__findHistory)
        self.findtextCombo.setEditText(text)
        self.findtextCombo.lineEdit().selectAll()
        self.findtextCombo.setFocus()
        self.on_findtextCombo_editTextChanged(text)

        self.replacetextCombo.clear()
        self.replacetextCombo.addItems(self.__replaceHistory)
        self.replacetextCombo.setEditText("")

        self.caseCheckBox.setChecked(False)
        self.wordCheckBox.setChecked(False)
        self.regexpCheckBox.setChecked(False)
        self.wrapCheckBox.setChecked(False)

        self.havefound = True

        aw = self.__viewmanager.activeWindow()
        self.updateSelectionCheckBox(aw)
        if aw.hasSelectedText():
            line1, index1, line2, _index2 = aw.getSelection()
            if line1 == line2:
                aw.setSelection(line1, index1, line1, index1)
                self.findNext()

        self.__setShortcuts()

    def show(self, text="", replaceMode=False):
        """
        Public slot to show the widget.

        @param text text to be shown in the findtext edit (defaults to "")
        @type str (optional)
        @param replaceMode flag indicating to show the widget in 'replace' mode
            (defaults to False)
        @type bool (optional)
        """
        super().hide()

        self.__replaceMode = replaceMode
        if replaceMode:
            self.__showReplace(text)
        else:
            self.__showFind(text)
        super().show()

        self.activateWindow()

    @pyqtSlot()
    def on_closeButton_clicked(self):
        """
        Private slot to close the widget.
        """
        aw = self.__viewmanager.activeWindow()
        if aw:
            aw.hideFindIndicator()
            self.__currentEditor.clearSearchSelectionHighlight()
            self.__currentEditor = None

        if self.__sliding:
            self.__topWidget.close()
        else:
            self.close()

    def keyPressEvent(self, event):
        """
        Protected slot to handle key press events.

        @param event reference to the key press event
        @type QKeyEvent
        """
        if event.key() == Qt.Key.Key_Escape:
            aw = self.__viewmanager.activeWindow()
            if aw:
                aw.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
                aw.hideFindIndicator()
                if self.__currentEditor is not None:
                    self.__currentEditor.clearSearchSelectionHighlight()
                self.__currentEditor = None
            event.accept()
            if self.__sliding:
                self.__topWidget.close()
            else:
                self.close()


class SearchReplaceSlidingWidget(QWidget):
    """
    Class implementing the search and replace widget with sliding behavior.

    @signal searchListChanged() emitted to indicate a change of the search list
    """

    searchListChanged = pyqtSignal()

    def __init__(self, vm, parent=None):
        """
        Constructor

        @param vm reference to the viewmanager object
        @type ViewManager
        @param parent parent widget of this widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.__searchReplaceWidget = SearchReplaceWidget(vm, self, True)
        self.__searchReplaceWidget.layout().setSizeConstraint(
            QLayout.SizeConstraint.SetMinAndMaxSize
        )

        self.__layout = QHBoxLayout(self)
        self.setLayout(self.__layout)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.__leftButton = QToolButton(self)
        self.__leftButton.setArrowType(Qt.ArrowType.LeftArrow)
        self.__leftButton.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding
        )
        self.__leftButton.setAutoRepeat(True)

        self.__scroller = QScrollArea(self)
        self.__scroller.setWidget(self.__searchReplaceWidget)
        self.__scroller.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.__scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.__scroller.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.__scroller.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.__scroller.setWidgetResizable(False)

        self.__rightButton = QToolButton(self)
        self.__rightButton.setArrowType(Qt.ArrowType.RightArrow)
        self.__rightButton.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding
        )
        self.__rightButton.setAutoRepeat(True)

        self.__layout.addWidget(self.__leftButton)
        self.__layout.addWidget(self.__scroller)
        self.__layout.addWidget(self.__rightButton)

        self.__searchReplaceWidget.searchListChanged.connect(self.searchListChanged)
        self.__leftButton.clicked.connect(self.__slideLeft)
        self.__rightButton.clicked.connect(self.__slideRight)

    def changeEvent(self, evt):
        """
        Protected method handling state changes.

        @param evt event containing the state change
        @type QEvent
        """
        if evt.type() == QEvent.Type.FontChange:
            self.setMaximumHeight(self.__searchReplaceWidget.sizeHint().height())
            self.adjustSize()

    def findNext(self):
        """
        Public slot to find the next occurrence of text.
        """
        self.__searchReplaceWidget.findNext()

    def findPrev(self):
        """
        Public slot to find the next previous of text.
        """
        self.__searchReplaceWidget.findPrev()

    def replace(self):
        """
        Public method to replace the current selection.
        """
        self.__searchReplaceWidget.replace()

    def replaceSearch(self):
        """
        Public method to replace the current selection and search again.
        """
        self.__searchReplaceWidget.replaceSearch()

    def replaceAll(self):
        """
        Public method to replace all occurrences.
        """
        self.__searchReplaceWidget.replaceAll()

    def selectionChanged(self, editor):
        """
        Public slot tracking changes of selected text.

        @param editor reference to the editor
        @type Editor
        """
        self.__searchReplaceWidget.updateSelectionCheckBox(editor)

    @pyqtSlot(Editor)
    def updateSelectionCheckBox(self, editor):
        """
        Public slot to update the selection check box.

        @param editor reference to the editor
        @type Editor
        """
        self.__searchReplaceWidget.updateSelectionCheckBox(editor)

    @pyqtSlot(Editor)
    def editorClosed(self, editor):
        """
        Public slot to handle the closing of an editor.

        @param editor reference to the closed editor
        @type Editor
        """
        self.__searchReplaceWidget.editorClosed(editor)

    def show(self, text="", replaceMode=False):
        """
        Public slot to show the widget.

        @param text text to be shown in the findtext edit (defaults to "")
        @type str (optional)
        @param replaceMode flag indicating to show the widget with replace mode enabled
            (defaults to False)
        @type bool (optional)
        """
        self.__searchReplaceWidget.show(text=text, replaceMode=replaceMode)
        super().show()

        self.__searchReplaceWidget.setMaximumHeight(
            self.__searchReplaceWidget.sizeHint().height()
        )
        self.setMaximumHeight(self.__searchReplaceWidget.sizeHint().height())

        self.__enableScrollerButtons()

    def __slideLeft(self):
        """
        Private slot to move the widget to the left, i.e. show contents to the
        right.
        """
        self.__slide(True)

    def __slideRight(self):
        """
        Private slot to move the widget to the right, i.e. show contents to
        the left.
        """
        self.__slide(False)

    def __slide(self, toLeft):
        """
        Private method to move the sliding widget.

        @param toLeft flag indicating to move to the left
        @type bool
        """
        scrollBar = self.__scroller.horizontalScrollBar()
        stepSize = scrollBar.singleStep()
        if toLeft:
            stepSize = -stepSize
        newValue = scrollBar.value() + stepSize
        if newValue < 0:
            newValue = 0
        elif newValue > scrollBar.maximum():
            newValue = scrollBar.maximum()
        scrollBar.setValue(newValue)
        self.__enableScrollerButtons()

    def __enableScrollerButtons(self):
        """
        Private method to set the enabled state of the scroll buttons.
        """
        scrollBar = self.__scroller.horizontalScrollBar()
        self.__leftButton.setEnabled(scrollBar.value() > 0)
        self.__rightButton.setEnabled(scrollBar.value() < scrollBar.maximum())

    def resizeEvent(self, evt):
        """
        Protected method to handle resize events.

        @param evt reference to the resize event
        @type QResizeEvent
        """
        self.__enableScrollerButtons()

        super().resizeEvent(evt)
