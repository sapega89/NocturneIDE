# Form implementation generated from reading ui file 'src/eric7/UI/NumbersWidget.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_NumbersWidget(object):
    def setupUi(self, NumbersWidget):
        NumbersWidget.setObjectName("NumbersWidget")
        NumbersWidget.resize(749, 160)
        self.gridLayout_2 = QtWidgets.QGridLayout(NumbersWidget)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.binaryGroup = QtWidgets.QGroupBox(parent=NumbersWidget)
        self.binaryGroup.setObjectName("binaryGroup")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.binaryGroup)
        self.horizontalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.binInButton = QtWidgets.QToolButton(parent=self.binaryGroup)
        self.binInButton.setObjectName("binInButton")
        self.horizontalLayout_2.addWidget(self.binInButton)
        self.binEdit = QtWidgets.QLineEdit(parent=self.binaryGroup)
        self.binEdit.setMaxLength(64)
        self.binEdit.setObjectName("binEdit")
        self.horizontalLayout_2.addWidget(self.binEdit)
        self.binOutButton = QtWidgets.QToolButton(parent=self.binaryGroup)
        self.binOutButton.setObjectName("binOutButton")
        self.horizontalLayout_2.addWidget(self.binOutButton)
        self.horizontalLayout_6.addWidget(self.binaryGroup)
        self.octalGroup = QtWidgets.QGroupBox(parent=NumbersWidget)
        self.octalGroup.setObjectName("octalGroup")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.octalGroup)
        self.horizontalLayout_3.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.octInButton = QtWidgets.QToolButton(parent=self.octalGroup)
        self.octInButton.setObjectName("octInButton")
        self.horizontalLayout_3.addWidget(self.octInButton)
        self.octEdit = QtWidgets.QLineEdit(parent=self.octalGroup)
        self.octEdit.setMaxLength(24)
        self.octEdit.setObjectName("octEdit")
        self.horizontalLayout_3.addWidget(self.octEdit)
        self.octOutButton = QtWidgets.QToolButton(parent=self.octalGroup)
        self.octOutButton.setObjectName("octOutButton")
        self.horizontalLayout_3.addWidget(self.octOutButton)
        self.horizontalLayout_6.addWidget(self.octalGroup)
        self.decimalGroup = QtWidgets.QGroupBox(parent=NumbersWidget)
        self.decimalGroup.setObjectName("decimalGroup")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.decimalGroup)
        self.horizontalLayout_4.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.decInButton = QtWidgets.QToolButton(parent=self.decimalGroup)
        self.decInButton.setObjectName("decInButton")
        self.horizontalLayout_4.addWidget(self.decInButton)
        self.decEdit = QtWidgets.QLineEdit(parent=self.decimalGroup)
        self.decEdit.setMaxLength(22)
        self.decEdit.setObjectName("decEdit")
        self.horizontalLayout_4.addWidget(self.decEdit)
        self.decOutButton = QtWidgets.QToolButton(parent=self.decimalGroup)
        self.decOutButton.setObjectName("decOutButton")
        self.horizontalLayout_4.addWidget(self.decOutButton)
        self.horizontalLayout_6.addWidget(self.decimalGroup)
        self.hexGroup = QtWidgets.QGroupBox(parent=NumbersWidget)
        self.hexGroup.setObjectName("hexGroup")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.hexGroup)
        self.horizontalLayout_5.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.hexInButton = QtWidgets.QToolButton(parent=self.hexGroup)
        self.hexInButton.setObjectName("hexInButton")
        self.horizontalLayout_5.addWidget(self.hexInButton)
        self.hexEdit = QtWidgets.QLineEdit(parent=self.hexGroup)
        self.hexEdit.setMaxLength(16)
        self.hexEdit.setObjectName("hexEdit")
        self.horizontalLayout_5.addWidget(self.hexEdit)
        self.hexOutButton = QtWidgets.QToolButton(parent=self.hexGroup)
        self.hexOutButton.setObjectName("hexOutButton")
        self.horizontalLayout_5.addWidget(self.hexOutButton)
        self.horizontalLayout_6.addWidget(self.hexGroup)
        self.gridLayout_2.addLayout(self.horizontalLayout_6, 0, 0, 1, 2)
        self.binTable = QtWidgets.QTableView(parent=NumbersWidget)
        self.binTable.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.AllEditTriggers)
        self.binTable.setTabKeyNavigation(False)
        self.binTable.setProperty("showDropIndicator", False)
        self.binTable.setDragDropOverwriteMode(False)
        self.binTable.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.binTable.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.binTable.setShowGrid(False)
        self.binTable.setCornerButtonEnabled(False)
        self.binTable.setObjectName("binTable")
        self.binTable.verticalHeader().setVisible(False)
        self.gridLayout_2.addWidget(self.binTable, 1, 0, 1, 1)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(parent=NumbersWidget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.formatBox = EricTextSpinBox(parent=NumbersWidget)
        self.formatBox.setWrapping(True)
        self.formatBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.formatBox.setObjectName("formatBox")
        self.gridLayout.addWidget(self.formatBox, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=NumbersWidget)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.sizeBox = EricTextSpinBox(parent=NumbersWidget)
        self.sizeBox.setWrapping(True)
        self.sizeBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.sizeBox.setObjectName("sizeBox")
        self.gridLayout.addWidget(self.sizeBox, 1, 1, 1, 1)
        self.byteOrderButton = QtWidgets.QPushButton(parent=NumbersWidget)
        self.byteOrderButton.setObjectName("byteOrderButton")
        self.gridLayout.addWidget(self.byteOrderButton, 2, 0, 1, 2)
        spacerItem = QtWidgets.QSpacerItem(62, 13, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout.addItem(spacerItem, 3, 1, 1, 1)
        self.gridLayout_2.addLayout(self.gridLayout, 1, 1, 1, 1)

        self.retranslateUi(NumbersWidget)
        QtCore.QMetaObject.connectSlotsByName(NumbersWidget)
        NumbersWidget.setTabOrder(self.binInButton, self.binEdit)
        NumbersWidget.setTabOrder(self.binEdit, self.binOutButton)
        NumbersWidget.setTabOrder(self.binOutButton, self.octInButton)
        NumbersWidget.setTabOrder(self.octInButton, self.octEdit)
        NumbersWidget.setTabOrder(self.octEdit, self.octOutButton)
        NumbersWidget.setTabOrder(self.octOutButton, self.decInButton)
        NumbersWidget.setTabOrder(self.decInButton, self.decEdit)
        NumbersWidget.setTabOrder(self.decEdit, self.decOutButton)
        NumbersWidget.setTabOrder(self.decOutButton, self.hexInButton)
        NumbersWidget.setTabOrder(self.hexInButton, self.hexEdit)
        NumbersWidget.setTabOrder(self.hexEdit, self.hexOutButton)
        NumbersWidget.setTabOrder(self.hexOutButton, self.binTable)
        NumbersWidget.setTabOrder(self.binTable, self.formatBox)
        NumbersWidget.setTabOrder(self.formatBox, self.sizeBox)
        NumbersWidget.setTabOrder(self.sizeBox, self.byteOrderButton)

    def retranslateUi(self, NumbersWidget):
        _translate = QtCore.QCoreApplication.translate
        NumbersWidget.setWindowTitle(_translate("NumbersWidget", "Numbers Formats"))
        self.binaryGroup.setTitle(_translate("NumbersWidget", "Binary"))
        self.binInButton.setToolTip(_translate("NumbersWidget", "Press to import the selected binary number"))
        self.binEdit.setToolTip(_translate("NumbersWidget", "Enter the binary number"))
        self.binOutButton.setToolTip(_translate("NumbersWidget", "Press to send the binary number to the current editor"))
        self.octalGroup.setTitle(_translate("NumbersWidget", "Octal"))
        self.octInButton.setToolTip(_translate("NumbersWidget", "Press to import the selected octal number"))
        self.octEdit.setToolTip(_translate("NumbersWidget", "Enter the octal number"))
        self.octOutButton.setToolTip(_translate("NumbersWidget", "Press to send the octal number to the current editor"))
        self.decimalGroup.setTitle(_translate("NumbersWidget", "Decimal"))
        self.decInButton.setToolTip(_translate("NumbersWidget", "Press to import the selected decimal number"))
        self.decEdit.setToolTip(_translate("NumbersWidget", "Enter the decimal number"))
        self.decOutButton.setToolTip(_translate("NumbersWidget", "Press to send the decimal number to the current editor"))
        self.hexGroup.setTitle(_translate("NumbersWidget", "Hexadecimal"))
        self.hexInButton.setToolTip(_translate("NumbersWidget", "Press to import the selected hex number"))
        self.hexEdit.setToolTip(_translate("NumbersWidget", "Enter the hex number"))
        self.hexOutButton.setToolTip(_translate("NumbersWidget", "Press to send the hex number to the current editor"))
        self.label.setText(_translate("NumbersWidget", "Input Format:"))
        self.formatBox.setToolTip(_translate("NumbersWidget", "Select the input format"))
        self.label_2.setText(_translate("NumbersWidget", "Bitsize:"))
        self.sizeBox.setToolTip(_translate("NumbersWidget", "Select the bit size"))
        self.byteOrderButton.setToolTip(_translate("NumbersWidget", "Press to swap the current byte order"))
        self.byteOrderButton.setText(_translate("NumbersWidget", "Swap byte order"))
from eric7.EricWidgets.EricTextSpinBox import EricTextSpinBox
