# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a search and replace widget for the hex editor.
"""

from PyQt6.QtCore import QByteArray, QRegularExpression, Qt, pyqtSlot
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QWidget

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox


class HexEditSearchReplaceWidget(QWidget):
    """
    Class implementing a search and replace widget for the hex editor.
    """

    def __init__(self, editor, mainWindow, replace=False, parent=None):
        """
        Constructor

        @param editor reference to the hex editor widget
        @type HexEditWidget
        @param mainWindow reference to the main window
        @type HexEditMainWindow
        @param replace flag indicating a replace widget
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__replace = replace
        self.__editor = editor

        # keep this in sync with the logic in __getContent()
        self.__formatAndValidators = {
            "hex": (
                self.tr("Hex"),
                QRegularExpressionValidator(QRegularExpression("[0-9a-f]*")),
            ),
            "dec": (
                self.tr("Dec"),
                QRegularExpressionValidator(QRegularExpression("[0-9]*")),
            ),
            "oct": (
                self.tr("Oct"),
                QRegularExpressionValidator(QRegularExpression("[0-7]*")),
            ),
            "bin": (
                self.tr("Bin"),
                QRegularExpressionValidator(QRegularExpression("[01]*")),
            ),
            "iso-8859-1": (self.tr("Text"), None),
            # text as latin-1/iso-8859-1
            "utf-8": (self.tr("UTF-8"), None),
            # text as utf-8
        }
        formatOrder = ["hex", "dec", "oct", "bin", "iso-8859-1", "utf-8"]

        self.__currentFindFormat = ""
        self.__currentReplaceFormat = ""

        self.__findHistory = mainWindow.getSRHistory("search")
        if replace:
            from .Ui_HexEditReplaceWidget import (  # __IGNORE_WARNING_I101__
                Ui_HexEditReplaceWidget,
            )

            self.__replaceHistory = mainWindow.getSRHistory("replace")
            self.__ui = Ui_HexEditReplaceWidget()
        else:
            from .Ui_HexEditSearchWidget import (  # __IGNORE_WARNING_I101__
                Ui_HexEditSearchWidget,
            )

            self.__ui = Ui_HexEditSearchWidget()
        self.__ui.setupUi(self)

        self.__ui.closeButton.setIcon(EricPixmapCache.getIcon("close"))
        self.__ui.findPrevButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.__ui.findNextButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))

        if replace:
            self.__ui.replaceButton.setIcon(EricPixmapCache.getIcon("editReplace"))
            self.__ui.replaceSearchButton.setIcon(
                EricPixmapCache.getIcon("editReplaceSearch")
            )
            self.__ui.replaceAllButton.setIcon(
                EricPixmapCache.getIcon("editReplaceAll")
            )

        for dataFormat in formatOrder:
            formatStr, _validator = self.__formatAndValidators[dataFormat]
            self.__ui.findFormatCombo.addItem(formatStr, dataFormat)
        if replace:
            for dataFormat in formatOrder:
                formatStr, _validator = self.__formatAndValidators[dataFormat]
                self.__ui.replaceFormatCombo.addItem(formatStr, dataFormat)

        self.__ui.findtextCombo.setCompleter(None)
        self.__ui.findtextCombo.lineEdit().returnPressed.connect(
            self.__findByReturnPressed
        )
        self.__ui.findtextCombo.lineEdit().setClearButtonEnabled(True)
        if replace:
            self.__ui.replacetextCombo.setCompleter(None)
            self.__ui.replacetextCombo.lineEdit().returnPressed.connect(
                self.on_replaceButton_clicked
            )
            self.__ui.replacetextCombo.lineEdit().setClearButtonEnabled(True)

        self.findNextAct = EricAction(
            self.tr("Find Next"),
            self.tr("Find Next"),
            0,
            0,
            self,
            "hexEditor_search_widget_find_next",
        )
        self.findNextAct.triggered.connect(self.on_findNextButton_clicked)
        self.findNextAct.setEnabled(False)
        self.__ui.findtextCombo.addAction(self.findNextAct)

        self.findPrevAct = EricAction(
            self.tr("Find Prev"),
            self.tr("Find Prev"),
            0,
            0,
            self,
            "hexEditor_search_widget_find_prev",
        )
        self.findPrevAct.triggered.connect(self.on_findPrevButton_clicked)
        self.findPrevAct.setEnabled(False)
        self.__ui.findtextCombo.addAction(self.findPrevAct)

        self.__havefound = False

    @pyqtSlot(int)
    def on_findFormatCombo_currentIndexChanged(self, idx):
        """
        Private slot to handle a selection from the find format.

        @param idx index of the selected entry
        @type int
        """
        if idx >= 0:
            findFormat = self.__ui.findFormatCombo.itemData(idx)

            if findFormat != self.__currentFindFormat:
                txt = self.__ui.findtextCombo.currentText()
                newTxt = self.__convertText(txt, self.__currentFindFormat, findFormat)
                self.__currentFindFormat = findFormat

                self.__ui.findtextCombo.setValidator(
                    self.__formatAndValidators[findFormat][1]
                )

                self.__ui.findtextCombo.setEditText(newTxt)

    @pyqtSlot(str)
    def on_findtextCombo_editTextChanged(self, txt):
        """
        Private slot to enable/disable the find buttons.

        @param txt text of the find text combo
        @type str
        """
        if not txt:
            self.__ui.findNextButton.setEnabled(False)
            self.findNextAct.setEnabled(False)
            self.__ui.findPrevButton.setEnabled(False)
            self.findPrevAct.setEnabled(False)
            if self.__replace:
                self.__ui.replaceButton.setEnabled(False)
                self.__ui.replaceSearchButton.setEnabled(False)
                self.__ui.replaceAllButton.setEnabled(False)
        else:
            self.__ui.findNextButton.setEnabled(True)
            self.findNextAct.setEnabled(True)
            self.__ui.findPrevButton.setEnabled(True)
            self.findPrevAct.setEnabled(True)
            if self.__replace:
                self.__ui.replaceButton.setEnabled(False)
                self.__ui.replaceSearchButton.setEnabled(False)
                self.__ui.replaceAllButton.setEnabled(True)

    @pyqtSlot(int)
    def on_findtextCombo_activated(self, idx):
        """
        Private slot to handle a selection from the find history.

        @param idx index of the selected entry
        @type int
        """
        if idx >= 0:
            formatIndex = self.__ui.findtextCombo.itemData(idx)
            if formatIndex is not None:
                self.__ui.findFormatCombo.setCurrentIndex(formatIndex)

    def __getContent(self, replace=False):
        """
        Private method to get the contents of the find/replace combo as
        a bytearray.

        @param replace flag indicating to retrieve the replace contents
        @type bool
        @return search or replace term as text and binary data
        @rtype tuple of bytearray and str
        """
        if replace:
            textCombo = self.__ui.replacetextCombo
            formatCombo = self.__ui.replaceFormatCombo
            history = self.__replaceHistory
        else:
            textCombo = self.__ui.findtextCombo
            formatCombo = self.__ui.findFormatCombo
            history = self.__findHistory

        txt = textCombo.currentText()
        idx = formatCombo.currentIndex()
        findFormat = formatCombo.itemData(idx)
        ba = self.__text2bytearray(txt, findFormat)

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        historyEntry = (idx, txt)
        if historyEntry in history:
            history.remove(historyEntry)
        history.insert(0, historyEntry)
        textCombo.clear()
        for index, text in history:
            textCombo.addItem(text, index)

        return ba, txt

    @pyqtSlot()
    def on_findNextButton_clicked(self):
        """
        Private slot to find the next occurrence.
        """
        self.findPrevNext(False)

    @pyqtSlot()
    def on_findPrevButton_clicked(self):
        """
        Private slot to find the previous occurrence.
        """
        self.findPrevNext(True)

    def findPrevNext(self, prev=False):
        """
        Public slot to find the next occurrence of the search term.

        @param prev flag indicating a backwards search
        @type bool
        @return flag indicating a successful search
        @rtype bool
        """
        if not self.__havefound or not self.__ui.findtextCombo.currentText():
            self.show()
            return False

        self.__findBackwards = prev
        ba, txt = self.__getContent()

        idx = -1
        if len(ba) > 0:
            startIndex = self.__editor.cursorPosition() // 2
            if prev:
                if (
                    self.__editor.hasSelection()
                    and startIndex == self.__editor.getSelectionEnd()
                ):
                    # skip to the selection start
                    startIndex = self.__editor.getSelectionBegin()
                idx = self.__editor.lastIndexOf(ba, startIndex)
            else:
                if (
                    self.__editor.hasSelection()
                    and startIndex == self.__editor.getSelectionBegin() - 1
                ):
                    # skip to the selection end
                    startIndex = self.__editor.getSelectionEnd()
                idx = self.__editor.indexOf(ba, startIndex)

        if idx >= 0:
            if self.__replace:
                self.__ui.replaceButton.setEnabled(True)
                self.__ui.replaceSearchButton.setEnabled(True)
        else:
            EricMessageBox.information(
                self, self.windowTitle(), self.tr("'{0}' was not found.").format(txt)
            )

        return idx >= 0

    def __findByReturnPressed(self):
        """
        Private slot to handle a return pressed in the find combo.
        """
        if self.__findBackwards:
            self.findPrevNext(True)
        else:
            self.findPrevNext(False)

    @pyqtSlot(int)
    def on_replaceFormatCombo_currentIndexChanged(self, idx):
        """
        Private slot to handle a selection from the replace format.

        @param idx index of the selected entry
        @type int
        """
        if idx >= 0:
            replaceFormat = self.__ui.replaceFormatCombo.itemData(idx)

            if replaceFormat != self.__currentReplaceFormat:
                txt = self.__ui.replacetextCombo.currentText()
                newTxt = self.__convertText(
                    txt, self.__currentReplaceFormat, replaceFormat
                )
                self.__currentReplaceFormat = replaceFormat

                self.__ui.replacetextCombo.setValidator(
                    self.__formatAndValidators[replaceFormat][1]
                )

                self.__ui.replacetextCombo.setEditText(newTxt)

    @pyqtSlot(int)
    def on_replacetextCombo_activated(self, idx):
        """
        Private slot to handle a selection from the replace history.

        @param idx index of the selected entry
        @type int
        """
        if idx >= 0:
            formatIndex = self.__ui.replacetextCombo.itemData(idx)
            if formatIndex is not None:
                self.__ui.replaceFormatCombo.setCurrentIndex(formatIndex)

    @pyqtSlot()
    def on_replaceButton_clicked(self):
        """
        Private slot to replace one occurrence of data.
        """
        self.__doReplace(False)

    @pyqtSlot()
    def on_replaceSearchButton_clicked(self):
        """
        Private slot to replace one occurrence of data and search for the next
        one.
        """
        self.__doReplace(True)

    def __doReplace(self, searchNext):
        """
        Private method to replace one occurrence of data.

        @param searchNext flag indicating to search for the next occurrence
        @type bool
        """
        # Check enabled status due to dual purpose usage of this method
        if (
            not self.__ui.replaceButton.isEnabled()
            and not self.__ui.replaceSearchButton.isEnabled()
        ):
            return

        fba, ftxt = self.__getContent(False)
        rba, _rtxt = self.__getContent(True)

        ok = False
        if self.__editor.hasSelection():
            # we did a successful search before
            startIdx = self.__editor.getSelectionBegin()
            self.__editor.replaceByteArray(startIdx, len(fba), rba)

            if searchNext:
                ok = self.findPrevNext(self.__findBackwards)

        if not ok:
            self.__ui.replaceButton.setEnabled(False)
            self.__ui.replaceSearchButton.setEnabled(False)

    @pyqtSlot()
    def on_replaceAllButton_clicked(self):
        """
        Private slot to replace all occurrences of data.
        """
        replacements = 0

        cursorPosition = self.__editor.cursorPosition()

        fba, ftxt = self.__getContent(False)
        rba, _rtxt = self.__getContent(True)

        idx = 0
        while idx >= 0:
            idx = self.__editor.indexOf(fba, idx)
            if idx >= 0:
                self.__editor.replaceByteArray(idx, len(fba), rba)
                idx += len(rba)
                replacements += 1

        if replacements:
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

        self.__editor.setCursorPosition(cursorPosition)
        self.__editor.ensureVisible()

    def __showFind(self, text=""):
        """
        Private method to display this widget in find mode.

        @param text hex encoded text to be shown in the findtext edit
        @type str
        """
        self.__replace = False

        self.__ui.findtextCombo.clear()
        for index, txt in self.__findHistory:
            self.__ui.findtextCombo.addItem(txt, index)
        self.__ui.findFormatCombo.setCurrentIndex(0)  # 0 is always Hex
        self.on_findFormatCombo_currentIndexChanged(0)
        self.__ui.findtextCombo.setEditText(text)
        self.__ui.findtextCombo.lineEdit().selectAll()
        self.__ui.findtextCombo.setFocus()
        self.on_findtextCombo_editTextChanged(text)

        self.__havefound = True
        self.__findBackwards = False

    def __showReplace(self, text=""):
        """
        Private slot to display this widget in replace mode.

        @param text hex encoded text to be shown in the findtext edit
        @type str
        """
        self.__replace = True

        self.__ui.findtextCombo.clear()
        for index, txt in self.__findHistory:
            self.__ui.findtextCombo.addItem(txt, index)
        self.__ui.findFormatCombo.setCurrentIndex(0)  # 0 is always Hex
        self.on_findFormatCombo_currentIndexChanged(0)
        self.__ui.findtextCombo.setEditText(text)
        self.__ui.findtextCombo.lineEdit().selectAll()
        self.__ui.findtextCombo.setFocus()
        self.on_findtextCombo_editTextChanged(text)

        self.__ui.replacetextCombo.clear()
        for index, txt in self.__replaceHistory:
            self.__ui.replacetextCombo.addItem(txt, index)
        self.__ui.replaceFormatCombo.setCurrentIndex(0)  # 0 is always Hex
        self.on_replaceFormatCombo_currentIndexChanged(0)
        self.__ui.replacetextCombo.setEditText("")

        self.__havefound = True
        self.__findBackwards = False

    def show(self, text=""):
        """
        Public slot to show the widget.

        @param text hex encoded text to be shown in the findtext edit
        @type str
        """
        if self.__replace:
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
        self.__editor.setFocus(Qt.FocusReason.OtherFocusReason)
        self.close()

    def keyPressEvent(self, event):
        """
        Protected slot to handle key press events.

        @param event reference to the key press event
        @type QKeyEvent
        """
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def __convertText(self, txt, oldFormat, newFormat):
        """
        Private method to convert text from one format into another.

        @param txt text to be converted
        @type str
        @param oldFormat current format of the text
        @type str
        @param newFormat format to convert to
        @type str
        @return converted text
        @rtype str
        """
        if txt and oldFormat and newFormat and oldFormat != newFormat:
            # step 1: convert the text to a byte array using the old format
            byteArray = self.__text2bytearray(txt, oldFormat)

            # step 2: convert the byte array to text using the new format
            txt = self.__bytearray2text(byteArray, newFormat)

        return txt

    def __int2bytearray(self, value):
        """
        Private method to convert an integer to a byte array.

        @param value value to be converted
        @type int
        @return byte array for the given value
        @rtype bytearray
        """
        ba = bytearray()
        while value > 0:
            value, modulus = divmod(value, 256)
            ba.insert(0, modulus)

        return ba

    def __bytearray2int(self, array):
        """
        Private method to convert a byte array to an integer value.

        @param array byte array to be converted
        @type bytearray
        @return integer value of the given array
        @rtype int
        """
        value = 0
        for b in array:
            value = value * 256 + b

        return value

    def __text2bytearray(self, txt, dataFormat):
        """
        Private method to convert a text to a byte array.

        @param txt text to be converted
        @type str
        @param dataFormat format of the text
        @type str
        @return converted text
        @rtype bytearray
        @exception ValueError raised to indicate an invalid dataFormat
            parameter
        """
        if dataFormat not in self.__formatAndValidators:
            raise ValueError("Bad value for 'dataFormat' parameter.")

        if dataFormat == "hex":  # hex format
            ba = bytearray(QByteArray.fromHex(bytes(txt, encoding="ascii")))
        elif dataFormat == "dec":  # decimal format
            ba = self.__int2bytearray(int(txt, 10))
        elif dataFormat == "oct":  # octal format
            ba = self.__int2bytearray(int(txt, 8))
        elif dataFormat == "bin":  # binary format
            ba = self.__int2bytearray(int(txt, 2))
        elif dataFormat == "iso-8859-1":  # latin-1/iso-8859-1 text
            ba = bytearray(txt, encoding="iso-8859-1")
        elif dataFormat == "utf-8":  # utf-8 text
            ba = bytearray(txt, encoding="utf-8")

        return ba

    def __bytearray2text(self, array, dataFormat):
        """
        Private method to convert a byte array to a text.

        @param array byte array to be converted
        @type bytearray
        @param dataFormat format of the text
        @type str
        @return formatted text
        @rtype str
        @exception ValueError raised to indicate an invalid dataFormat
            parameter
        """
        if dataFormat not in self.__formatAndValidators:
            raise ValueError("Bad value for 'dataFormat' parameter.")

        if dataFormat == "hex":  # hex format
            txt = "{0:x}".format(self.__bytearray2int(array))
        elif dataFormat == "dec":  # decimal format
            txt = "{0:d}".format(self.__bytearray2int(array))
        elif dataFormat == "oct":  # octal format
            txt = "{0:o}".format(self.__bytearray2int(array))
        elif dataFormat == "bin":  # binary format
            txt = "{0:b}".format(self.__bytearray2int(array))
        elif dataFormat == "iso-8859-1":  # latin-1/iso-8859-1 text
            txt = str(array, encoding="iso-8859-1")
        elif dataFormat == "utf-8":  # utf-8 text
            txt = str(array, encoding="utf-8", errors="replace")

        return txt
