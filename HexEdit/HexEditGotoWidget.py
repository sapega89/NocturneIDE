# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a movement (goto) widget for the hex editor.
"""

from PyQt6.QtCore import QRegularExpression, Qt, pyqtSlot
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QWidget

from eric7 import EricUtilities
from eric7.EricGui import EricPixmapCache

from .Ui_HexEditGotoWidget import Ui_HexEditGotoWidget


class HexEditGotoWidget(QWidget, Ui_HexEditGotoWidget):
    """
    Class implementing a movement (goto) widget for the hex editor.
    """

    def __init__(self, editor, parent=None):
        """
        Constructor

        @param editor reference to the hex editor widget
        @type HexEditWidget
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__editor = editor

        # keep this in sync with the logic in on_gotoButton_clicked()
        self.__formatAndValidators = {
            "hex": (
                self.tr("Hex"),
                QRegularExpressionValidator(QRegularExpression("[0-9a-f:]*")),
            ),
            "dec": (
                self.tr("Dec"),
                QRegularExpressionValidator(QRegularExpression("[0-9]*")),
            ),
        }
        formatOrder = ["hex", "dec"]

        self.__currentFormat = ""

        self.closeButton.setIcon(EricPixmapCache.getIcon("close"))

        for dataFormat in formatOrder:
            formatStr, _validator = self.__formatAndValidators[dataFormat]
            self.formatCombo.addItem(formatStr, dataFormat)

        self.formatCombo.setCurrentIndex(0)

    @pyqtSlot()
    def on_closeButton_clicked(self):
        """
        Private slot to close the widget.
        """
        self.__editor.setFocus(Qt.FocusReason.OtherFocusReason)
        self.close()

    @pyqtSlot(int)
    def on_formatCombo_currentIndexChanged(self, idx):
        """
        Private slot to handle a selection of the format.

        @param idx index of the selected entry
        @type int
        """
        if idx >= 0:
            dataFormat = self.formatCombo.itemData(idx)

            if dataFormat != self.__currentFormat:
                txt = self.offsetEdit.text()
                newTxt = self.__convertText(txt, self.__currentFormat, dataFormat)
                self.__currentFormat = dataFormat

                self.offsetEdit.setValidator(self.__formatAndValidators[dataFormat][1])

                self.offsetEdit.setText(newTxt)

    @pyqtSlot(str)
    def on_offsetEdit_textChanged(self, offset):
        """
        Private slot handling a change of the entered offset.

        @param offset entered offset
        @type str
        """
        self.gotoButton.setEnabled(bool(offset))

    @pyqtSlot()
    def on_gotoButton_clicked(self):
        """
        Private slot to move the cursor and extend the selection.
        """
        dataFormat = self.formatCombo.itemData(self.formatCombo.currentIndex())
        if dataFormat == "hex":
            offset = self.offsetEdit.text().replace(":", "")
            # get rid of ':' address separators
            offset = int(offset, 16)
        else:
            offset = int(self.offsetEdit.text(), 10)

        fromCursor = self.cursorCheckBox.isChecked()
        backwards = self.backCheckBox.isChecked()
        extendSelection = self.selectionCheckBox.isChecked()

        self.__editor.goto(
            offset,
            fromCursor=fromCursor,
            backwards=backwards,
            extendSelection=extendSelection,
        )

    def show(self):
        """
        Public slot to show the widget.
        """
        self.offsetEdit.selectAll()
        self.offsetEdit.setFocus()
        super().show()

    def reset(self):
        """
        Public slot to reset the input widgets.
        """
        self.offsetEdit.clear()
        self.formatCombo.setCurrentIndex(0)
        self.cursorCheckBox.setChecked(False)
        self.backCheckBox.setChecked(False)
        self.selectionCheckBox.setChecked(False)

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
            # step 1: convert the text to an integer using the old format
            if oldFormat == "hex":
                txt = txt.replace(":", "")  # get rid of ':' address separators
                index = int(txt, 16)
            else:
                index = int(txt, 10)

            # step 2: convert the integer to text using the new format
            if newFormat == "hex":
                txt = "{0:x}".format(index)
                txt = EricUtilities.strGroup(txt, ":", 4)
            else:
                txt = "{0:d}".format(index)

        return txt
