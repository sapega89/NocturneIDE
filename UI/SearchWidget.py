# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the search box for the shell and log viewer.
"""

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QSizePolicy, QSpacerItem, QWidget

from eric7.EricGui import EricPixmapCache


class SearchWidget(QWidget):
    """
    Class implementing the search box for the shell and log viewer.

    @signal searchNext(text, caseSensitive, wholeWord, regexp) emitted when the
        user pressed the next button (string, boolean, boolean)
    @signal searchPrevious(text, caseSensitive, wholeWord, regexp) emitted when
        the user pressed the previous button (string, boolean, boolean)
    """

    searchNext = pyqtSignal(str, bool, bool, bool)
    searchPrevious = pyqtSignal(str, bool, bool, bool)

    def __init__(self, mainWindow, parent=None, spacer=True, showLine=False):
        """
        Constructor

        @param mainWindow reference to the main window
        @type QWidget
        @param parent reference to the parent widget
        @type QWidget
        @param spacer flag indicating to add a vertical spacer to the
            main layout
        @type bool
        @param showLine flag indicating to show all widget in one row
        @type bool
        """
        super().__init__(parent)

        if showLine:
            from .Ui_SearchWidgetLine import (  # __IGNORE_WARNING_I101__
                Ui_SearchWidgetLine,
            )

            self.__ui = Ui_SearchWidgetLine()
        else:
            from .Ui_SearchWidget import Ui_SearchWidget  # __IGNORE_WARNING_I101__

            self.__ui = Ui_SearchWidget()
        self.__ui.setupUi(self)

        if not showLine:
            if spacer:
                spacerItem = QSpacerItem(
                    20, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
                )
                self.__ui.verticalLayout.addItem(spacerItem)
            else:
                # change the size policy of the search combo if the spacer is
                # not wanted, i.e. it is below the to be searched widget
                sizePolicy = self.__ui.findtextCombo.sizePolicy()
                sizePolicy.setHorizontalPolicy(QSizePolicy.Policy.Expanding)
                self.__ui.findtextCombo.setSizePolicy(sizePolicy)

        self.__mainWindow = mainWindow
        self.__findBackwards = True

        self.__ui.closeButton.setIcon(EricPixmapCache.getIcon("close"))
        self.__ui.findPrevButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.__ui.findNextButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))

        self.findHistory = []

        self.__ui.findtextCombo.setCompleter(None)
        self.__ui.findtextCombo.lineEdit().returnPressed.connect(
            self.__findByReturnPressed
        )
        self.__ui.findtextCombo.lineEdit().setClearButtonEnabled(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def on_closeButton_clicked(self):
        """
        Private slot to close the widget.
        """
        self.close()

    def keyPressEvent(self, event):
        """
        Protected slot to handle key press events.

        @param event reference to the key press event
        @type QKeyEvent
        """
        if event.key() == Qt.Key.Key_Escape:
            self.__mainWindow.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            event.accept()
            self.close()

    @pyqtSlot()
    def on_findNextButton_clicked(self):
        """
        Private slot to find the next occurrence.
        """
        txt = self.__ui.findtextCombo.currentText()
        if not txt and not self.isVisible():
            self.showFind()
            return

        self.__findBackwards = False

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if txt in self.findHistory:
            self.findHistory.remove(txt)
        self.findHistory.insert(0, txt)
        self.__ui.findtextCombo.clear()
        self.__ui.findtextCombo.addItems(self.findHistory)

        self.searchNext.emit(
            txt,
            self.__ui.caseCheckBox.isChecked(),
            self.__ui.wordCheckBox.isChecked(),
            self.__ui.regexpCheckBox.isChecked(),
        )

    @pyqtSlot()
    def on_findPrevButton_clicked(self):
        """
        Private slot to find the previous occurrence.
        """
        txt = self.__ui.findtextCombo.currentText()
        if not txt and not self.isVisible():
            self.showFind()
            return

        self.__findBackwards = True

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if txt in self.findHistory:
            self.findHistory.remove(txt)
        self.findHistory.insert(0, txt)
        self.__ui.findtextCombo.clear()
        self.__ui.findtextCombo.addItems(self.findHistory)

        self.searchPrevious.emit(
            txt,
            self.__ui.caseCheckBox.isChecked(),
            self.__ui.wordCheckBox.isChecked(),
            self.__ui.regexpCheckBox.isChecked(),
        )

    @pyqtSlot(str)
    def on_findtextCombo_editTextChanged(self, txt):
        """
        Private slot to enable/disable the find buttons.

        @param txt text of the combobox
        @type str
        """
        self.__setSearchButtons(txt != "")

    def __setSearchButtons(self, enabled):
        """
        Private slot to set the state of the search buttons.

        @param enabled flag indicating the state
        @type bool
        """
        self.__ui.findPrevButton.setEnabled(enabled)
        self.__ui.findNextButton.setEnabled(enabled)

    def __findByReturnPressed(self):
        """
        Private slot to handle the returnPressed signal of the findtext
        combobox.
        """
        if self.__findBackwards:
            self.on_findPrevButton_clicked()
        else:
            self.on_findNextButton_clicked()

    def showFind(self, txt=""):
        """
        Public method to display this widget.

        @param txt text to be shown in the combo
        @type str
        """
        self.__ui.findtextCombo.clear()
        self.__ui.findtextCombo.addItems(self.findHistory)
        self.__ui.findtextCombo.setEditText(txt)
        self.__ui.findtextCombo.setFocus()

        self.__setSearchButtons(txt != "")

        self.show()

    def searchStringFound(self, found):
        """
        Public slot to indicate that the search string was found.

        @param found flag indicating success
        @type bool
        """
        if found:
            self.__ui.statusLabel.clear()
        else:
            txt = self.__ui.findtextCombo.currentText()
            self.__ui.statusLabel.setText(self.tr("'{0}' was not found.").format(txt))
