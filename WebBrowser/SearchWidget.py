# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the search bar for the web browser.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QWidget

from eric7.EricGui import EricPixmapCache

from .Ui_SearchWidget import Ui_SearchWidget


class SearchWidget(QWidget, Ui_SearchWidget):
    """
    Class implementing the search bar for the web browser.
    """

    def __init__(self, mainWindow, parent=None):
        """
        Constructor

        @param mainWindow reference to the main window
        @type QMainWindow
        @param parent parent widget of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__mainWindow = mainWindow

        self.closeButton.setIcon(EricPixmapCache.getIcon("close"))
        self.findPrevButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.findNextButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))

        self.__defaultBaseColor = (
            self.findtextCombo.lineEdit().palette().color(QPalette.ColorRole.Base)
        )
        self.__defaultTextColor = (
            self.findtextCombo.lineEdit().palette().color(QPalette.ColorRole.Text)
        )

        self.__findHistory = []
        self.__havefound = False
        self.__findBackwards = False

        self.findtextCombo.setCompleter(None)
        self.findtextCombo.lineEdit().returnPressed.connect(self.__findByReturnPressed)
        self.findtextCombo.lineEdit().textEdited.connect(self.__searchTextEdited)
        self.findtextCombo.lineEdit().setClearButtonEnabled(True)

    @pyqtSlot(str)
    def on_findtextCombo_editTextChanged(self, txt):
        """
        Private slot to enable/disable the find buttons.

        @param txt text of the combobox
        @type str
        """
        self.findPrevButton.setEnabled(txt != "")
        self.findNextButton.setEnabled(txt != "")

    @pyqtSlot(str)
    def __searchTextEdited(self, txt):
        """
        Private slot to perform an incremental search.

        @param txt current text of the search combos line edit
        @type str
            (unused)
        """
        self.__findNextPrev()

    def __findNextPrev(self):
        """
        Private slot to find the next occurrence of text.
        """
        self.infoLabel.clear()
        self.__setFindtextComboBackground(False)

        if not self.findtextCombo.currentText():
            return

        self.__mainWindow.currentBrowser().findNextPrev(
            self.findtextCombo.currentText(),
            self.caseCheckBox.isChecked(),
            self.__findBackwards,
            self.__findNextPrevCallback,
        )

    def __findNextPrevCallback(self, result):
        """
        Private method to process the result of the last search.

        @param result reference to the search result
        @type QWebEngineFindTextResult
        """
        if result.numberOfMatches() == 0:
            self.infoLabel.setText(self.tr("Expression was not found."))
            self.__setFindtextComboBackground(True)
        else:
            self.infoLabel.setText(
                self.tr("Match {0} of {1}").format(
                    result.activeMatch(), result.numberOfMatches()
                )
            )

    @pyqtSlot()
    def on_findNextButton_clicked(self):
        """
        Private slot to find the next occurrence.
        """
        txt = self.findtextCombo.currentText()

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if txt in self.__findHistory:
            self.__findHistory.remove(txt)
        self.__findHistory.insert(0, txt)
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.__findHistory)

        self.__findBackwards = False
        self.__findNextPrev()

    def findNext(self):
        """
        Public slot to find the next occurrence.
        """
        if not self.__havefound or not self.findtextCombo.currentText():
            self.showFind()
            return

        self.on_findNextButton_clicked()

    @pyqtSlot()
    def on_findPrevButton_clicked(self):
        """
        Private slot to find the previous occurrence.
        """
        txt = self.findtextCombo.currentText()

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if txt in self.__findHistory:
            self.__findHistory.remove(txt)
        self.__findHistory.insert(0, txt)
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.__findHistory)

        self.__findBackwards = True
        self.__findNextPrev()

    def findPrevious(self):
        """
        Public slot to find the previous occurrence.
        """
        if not self.__havefound or not self.findtextCombo.currentText():
            self.showFind()
            return

        self.on_findPrevButton_clicked()

    @pyqtSlot()
    def __findByReturnPressed(self):
        """
        Private slot to handle the returnPressed signal of the findtext
        combobox.
        """
        if self.__findBackwards:
            self.on_findPrevButton_clicked()
        else:
            self.on_findNextButton_clicked()

    def showFind(self):
        """
        Public method to display this dialog.
        """
        self.__havefound = True
        self.__findBackwards = False

        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.__findHistory)
        self.findtextCombo.setEditText("")
        self.findtextCombo.setFocus()

        self.caseCheckBox.setChecked(False)

        if self.__mainWindow.currentBrowser().hasSelection():
            self.findtextCombo.setEditText(
                self.__mainWindow.currentBrowser().selectedText()
            )

        self.__setFindtextComboBackground(False)
        self.show()

    def __resetSearch(self):
        """
        Private method to reset the last search.
        """
        self.__mainWindow.currentBrowser().findText("")

    @pyqtSlot()
    def on_closeButton_clicked(self):
        """
        Private slot to close the widget.
        """
        self.__resetSearch()
        self.close()

    def keyPressEvent(self, event):
        """
        Protected slot to handle key press events.

        @param event reference to the key press event
        @type QKeyEvent
        """
        if event.key() == Qt.Key.Key_Escape:
            cb = self.__mainWindow.currentBrowser()
            if cb:
                cb.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            event.accept()
            self.__resetSearch()
            self.close()

    def __setFindtextComboBackground(self, error):
        """
        Private slot to change the findtext combo background to indicate
        errors.

        @param error flag indicating an error condition
        @type bool
        """
        styleSheet = (
            "color: #000000; background-color: #ff6666"
            if error
            else f"color: {self.__defaultTextColor};"
            f" background-color: {self.__defaultBaseColor}"
        )
        self.findtextCombo.setStyleSheet(styleSheet)
