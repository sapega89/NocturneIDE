# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to show numbers in different formats.
"""

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QHeaderView, QWidget

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp

from .Ui_NumbersWidget import Ui_NumbersWidget


class BinaryModel(QAbstractTableModel):
    """
    Class implementing a model for entering binary numbers.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__bits = 0
        self.__value = 0

    def rowCount(self, _parent):
        """
        Public method to get the number of rows of the model.

        @param _parent parent index (unused)
        @type QModelIndex
        @return number of columns
        @rtype int
        """
        return 1

    def columnCount(self, _parent):
        """
        Public method to get the number of columns of the model.

        @param _parent parent index (unused)
        @type QModelIndex
        @return number of columns
        @rtype int
        """
        return self.__bits

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get data from the model.

        @param index index to get data for
        @type QModelIndex
        @param role role of the data to retrieve
        @type int
        @return requested data
        @rtype Any
        """
        if role == Qt.ItemDataRole.CheckStateRole:
            if (self.__value >> (self.__bits - index.column() - 1)) & 1:
                return Qt.CheckState.Checked
            else:
                return Qt.CheckState.Unchecked

        elif role == Qt.ItemDataRole.DisplayRole:
            return ""

        return None

    def flags(self, _index):
        """
        Public method to get flags from the model.

        @param _index index to get flags for (unused)
        @type QModelIndex
        @return flags
        @rtype Qt.ItemFlags
        """
        return (
            Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get header data from the model.

        @param section section number
        @type int
        @param orientation orientation
        @type Qt.Orientation
        @param role role of the data to retrieve
        @type Qt.ItemDataRole
        @return requested data
        @rtype Any
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return str(self.__bits - section - 1)

        return QAbstractTableModel.headerData(self, section, orientation, role)

    def setBits(self, bits):
        """
        Public slot to set the number of bits.

        @param bits number of bits to show
        @type int
        """
        self.beginResetModel()
        self.__bits = bits
        self.endResetModel()

    def setValue(self, value):
        """
        Public slot to set the value to show.

        @param value value to show
        @type int
        """
        self.beginResetModel()
        self.__value = value
        self.endResetModel()

    def setBitsAndValue(self, bits, value):
        """
        Public slot to set the number of bits and the value to show.

        @param bits number of bits to show
        @type int
        @param value value to show
        @type int
        """
        self.__bits = bits
        self.__value = value
        self.beginResetModel()
        self.endResetModel()

    def getValue(self):
        """
        Public slot to get the current value.

        @return current value of the model
        @rtype int
        """
        return self.__value

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """
        Public method to set the data of a node cell.

        @param index index of the node cell
        @type QModelIndex
        @param value value to be set
        @type Any
        @param role role of the data
        @type int
        @return flag indicating success
        @rtype boolean)
        """
        if role == Qt.ItemDataRole.CheckStateRole:
            if Qt.CheckState(value) == Qt.CheckState.Checked:
                self.__value |= 1 << self.__bits - index.column() - 1
            else:
                self.__value &= ~(1 << self.__bits - index.column() - 1)
            self.dataChanged.emit(index, index)
            return True

        return False


class NumbersWidget(QWidget, Ui_NumbersWidget):
    """
    Class implementing a widget to show numbers in different formats.

    @signal insertNumber(str) emitted after the user has entered a number
            and selected the number format
    """

    insertNumber = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

        self.__badNumberSheet = (
            "background-color: #b31b1b;"
            if ericApp().usesDarkPalette()
            else "background-color: #ffa0a0;"
        )

        self.binInButton.setIcon(EricPixmapCache.getIcon("2downarrow"))
        self.binOutButton.setIcon(EricPixmapCache.getIcon("2uparrow"))
        self.octInButton.setIcon(EricPixmapCache.getIcon("2downarrow"))
        self.octOutButton.setIcon(EricPixmapCache.getIcon("2uparrow"))
        self.decInButton.setIcon(EricPixmapCache.getIcon("2downarrow"))
        self.decOutButton.setIcon(EricPixmapCache.getIcon("2uparrow"))
        self.hexInButton.setIcon(EricPixmapCache.getIcon("2downarrow"))
        self.hexOutButton.setIcon(EricPixmapCache.getIcon("2uparrow"))

        self.formatBox.addItem(self.tr("Auto"), 0)
        self.formatBox.addItem(self.tr("Dec"), 10)
        self.formatBox.addItem(self.tr("Hex"), 16)
        self.formatBox.addItem(self.tr("Oct"), 8)
        self.formatBox.addItem(self.tr("Bin"), 2)

        self.sizeBox.addItem("8", 8)
        self.sizeBox.addItem("16", 16)
        self.sizeBox.addItem("32", 32)
        self.sizeBox.addItem("64", 64)

        self.__input = 0
        self.__inputValid = True
        self.__bytes = 1

        self.__model = BinaryModel(self)
        self.binTable.setModel(self.__model)
        self.binTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.__model.setBitsAndValue(self.__bytes * 8, self.__input)
        self.__model.dataChanged.connect(self.__binModelDataChanged)

    def __formatNumbers(self, numberFormat):
        """
        Private method to format the various number inputs.

        @param numberFormat number format indicator
        @type int
        """
        self.__block(True)

        self.binEdit.setStyleSheet("")
        self.octEdit.setStyleSheet("")
        self.decEdit.setStyleSheet("")
        self.hexEdit.setStyleSheet("")

        # determine byte count
        byteCount = 8
        tmp = self.__input
        for _ in range(8):
            c = (tmp & 0xFF00000000000000) >> 7 * 8
            if c != 0 and self.__input >= 0:
                break
            if c != 0xFF and self.__input < 0:
                break
            tmp <<= 8
            byteCount -= 1
        if byteCount == 0:
            byteCount = 1
        self.__bytes = byteCount

        bytesIn = self.sizeBox.itemData(self.sizeBox.currentIndex()) // 8
        if bytesIn and byteCount > bytesIn:
            self.sizeBox.setStyleSheet(self.__badNumberSheet)
        else:
            self.sizeBox.setStyleSheet("")

        # octal
        if numberFormat != 8:
            self.octEdit.setText("{0:0{1}o}".format(self.__input, bytesIn * 3))

        # decimal
        if numberFormat != 10:
            self.decEdit.setText("{0:d}".format(self.__input))

        # hexadecimal
        if numberFormat != 16:
            self.hexEdit.setText("{0:0{1}x}".format(self.__input, bytesIn * 2))

        # octal
        if numberFormat != 8:
            self.octEdit.setText("{0:0{1}o}".format(self.__input, bytesIn * 3))

        # binary
        if numberFormat != 2:
            num = "{0:0{1}b}".format(self.__input, bytesIn * 8)
            self.binEdit.setText(num)

        self.__model.setBitsAndValue(len(self.binEdit.text()), self.__input)

        self.__block(False)

    def __block(self, b):
        """
        Private slot to block some signals.

        @param b flah indicating the blocking state
        @type bool
        """
        self.hexEdit.blockSignals(b)
        self.decEdit.blockSignals(b)
        self.octEdit.blockSignals(b)
        self.binEdit.blockSignals(b)
        self.binTable.blockSignals(b)

    @pyqtSlot(int)
    def on_sizeBox_valueChanged(self, value):
        """
        Private slot handling a change of the bit size.

        @param value selected bit size
        @type int
        """
        self.__formatNumbers(10)

    @pyqtSlot()
    def on_byteOrderButton_clicked(self):
        """
        Private slot to swap the byte order.
        """
        bytesIn = self.sizeBox.itemData(self.sizeBox.currentIndex()) // 8
        if bytesIn == 0:
            bytesIn = self.__bytes

        tmp1 = self.__input
        tmp2 = 0
        for _ in range(bytesIn):
            tmp2 <<= 8
            tmp2 |= tmp1 & 0xFF
            tmp1 >>= 8

        self.__input = tmp2
        self.__formatNumbers(0)

    @pyqtSlot()
    def on_binInButton_clicked(self):
        """
        Private slot to retrieve a binary number from the current editor.
        """
        number = ericApp().getObject("ViewManager").getNumber()
        if number == "":
            return

        self.binEdit.setText(number)
        self.binEdit.setFocus()

    @pyqtSlot(str)
    def on_binEdit_textChanged(self, txt):
        """
        Private slot to handle input of a binary number.

        @param txt text entered
        @type str
        """
        try:
            self.__input = int(txt, 2)
            self.__inputValid = True
        except ValueError:
            self.__inputValid = False

        if self.__inputValid:
            self.__formatNumbers(2)
        else:
            self.binEdit.setStyleSheet(self.__badNumberSheet)

    @pyqtSlot()
    def on_binOutButton_clicked(self):
        """
        Private slot to send a binary number.
        """
        self.insertNumber.emit(self.binEdit.text())

    @pyqtSlot(QModelIndex, QModelIndex)
    def __binModelDataChanged(self, _start, _end):
        """
        Private slot to handle a change of the binary model value by the user.

        @param _start start index (unused)
        @type QModelIndex
        @param _end end index (unused)
        @type QModelIndex
        """
        val = self.__model.getValue()
        bytesIn = self.sizeBox.itemData(self.sizeBox.currentIndex()) // 8
        num = "{0:0{1}b}".format(val, bytesIn * 8)
        self.binEdit.setText(num)

    @pyqtSlot()
    def on_octInButton_clicked(self):
        """
        Private slot to retrieve an octal number from the current editor.
        """
        number = ericApp().getObject("ViewManager").getNumber()
        if number == "":
            return

        self.octEdit.setText(number)
        self.octEdit.setFocus()

    @pyqtSlot(str)
    def on_octEdit_textChanged(self, txt):
        """
        Private slot to handle input of an octal number.

        @param txt text entered
        @type str
        """
        try:
            self.__input = int(txt, 8)
            self.__inputValid = True
        except ValueError:
            self.__inputValid = False

        if self.__inputValid:
            self.__formatNumbers(8)
        else:
            self.octEdit.setStyleSheet(self.__badNumberSheet)

    @pyqtSlot()
    def on_octOutButton_clicked(self):
        """
        Private slot to send an octal number.
        """
        self.insertNumber.emit(self.octEdit.text())

    @pyqtSlot()
    def on_decInButton_clicked(self):
        """
        Private slot to retrieve a decimal number from the current editor.
        """
        number = ericApp().getObject("ViewManager").getNumber()
        if number == "":
            return

        self.decEdit.setText(number)
        self.decEdit.setFocus()

    @pyqtSlot(str)
    def on_decEdit_textChanged(self, txt):
        """
        Private slot to handle input of a decimal number.

        @param txt text entered
        @type str
        """
        try:
            self.__input = int(txt, 10)
            self.__inputValid = True
        except ValueError:
            self.__inputValid = False

        if self.__inputValid:
            self.__formatNumbers(10)
        else:
            self.decEdit.setStyleSheet(self.__badNumberSheet)

    @pyqtSlot()
    def on_decOutButton_clicked(self):
        """
        Private slot to send a decimal number.
        """
        self.insertNumber.emit(self.decEdit.text())

    @pyqtSlot()
    def on_hexInButton_clicked(self):
        """
        Private slot to retrieve a hexadecimal number from the current editor.
        """
        number = ericApp().getObject("ViewManager").getNumber()
        if number == "":
            return

        self.hexEdit.setText(number)
        self.hexEdit.setFocus()

    @pyqtSlot(str)
    def on_hexEdit_textChanged(self, txt):
        """
        Private slot to handle input of a hexadecimal number.

        @param txt text entered
        @type str
        """
        try:
            self.__input = int(txt, 16)
            self.__inputValid = True
        except ValueError:
            self.__inputValid = False

        if self.__inputValid:
            self.__formatNumbers(16)
        else:
            self.hexEdit.setStyleSheet(self.__badNumberSheet)

    @pyqtSlot()
    def on_hexOutButton_clicked(self):
        """
        Private slot to send a hexadecimal number.
        """
        self.insertNumber.emit(self.hexEdit.text())
