# Form implementation generated from reading ui file 'src/eric7/WebBrowser/Passwords/PasswordsDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_PasswordsDialog(object):
    def setupUi(self, PasswordsDialog):
        PasswordsDialog.setObjectName("PasswordsDialog")
        PasswordsDialog.resize(500, 350)
        PasswordsDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(PasswordsDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.searchEdit = QtWidgets.QLineEdit(parent=PasswordsDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.searchEdit.sizePolicy().hasHeightForWidth())
        self.searchEdit.setSizePolicy(sizePolicy)
        self.searchEdit.setMinimumSize(QtCore.QSize(300, 0))
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setObjectName("searchEdit")
        self.horizontalLayout.addWidget(self.searchEdit)
        self.horizontalLayout_2.addLayout(self.horizontalLayout)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.passwordsTable = EricTableView(parent=PasswordsDialog)
        self.passwordsTable.setAlternatingRowColors(True)
        self.passwordsTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.passwordsTable.setTextElideMode(QtCore.Qt.TextElideMode.ElideMiddle)
        self.passwordsTable.setShowGrid(False)
        self.passwordsTable.setSortingEnabled(True)
        self.passwordsTable.setObjectName("passwordsTable")
        self.verticalLayout.addWidget(self.passwordsTable)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.removeButton = QtWidgets.QPushButton(parent=PasswordsDialog)
        self.removeButton.setAutoDefault(False)
        self.removeButton.setObjectName("removeButton")
        self.horizontalLayout_3.addWidget(self.removeButton)
        self.removeAllButton = QtWidgets.QPushButton(parent=PasswordsDialog)
        self.removeAllButton.setAutoDefault(False)
        self.removeAllButton.setObjectName("removeAllButton")
        self.horizontalLayout_3.addWidget(self.removeAllButton)
        spacerItem1 = QtWidgets.QSpacerItem(208, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.passwordsButton = QtWidgets.QPushButton(parent=PasswordsDialog)
        self.passwordsButton.setText("")
        self.passwordsButton.setObjectName("passwordsButton")
        self.horizontalLayout_3.addWidget(self.passwordsButton)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=PasswordsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(PasswordsDialog)
        self.buttonBox.accepted.connect(PasswordsDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(PasswordsDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(PasswordsDialog)
        PasswordsDialog.setTabOrder(self.searchEdit, self.passwordsTable)
        PasswordsDialog.setTabOrder(self.passwordsTable, self.removeButton)
        PasswordsDialog.setTabOrder(self.removeButton, self.removeAllButton)
        PasswordsDialog.setTabOrder(self.removeAllButton, self.passwordsButton)
        PasswordsDialog.setTabOrder(self.passwordsButton, self.buttonBox)

    def retranslateUi(self, PasswordsDialog):
        _translate = QtCore.QCoreApplication.translate
        PasswordsDialog.setWindowTitle(_translate("PasswordsDialog", "Saved Passwords"))
        self.searchEdit.setToolTip(_translate("PasswordsDialog", "Enter search term"))
        self.removeButton.setToolTip(_translate("PasswordsDialog", "Press to remove the selected entries"))
        self.removeButton.setText(_translate("PasswordsDialog", "&Remove"))
        self.removeAllButton.setToolTip(_translate("PasswordsDialog", "Press to remove all entries"))
        self.removeAllButton.setText(_translate("PasswordsDialog", "Remove &All"))
        self.passwordsButton.setToolTip(_translate("PasswordsDialog", "Press to toggle the display of passwords"))
from eric7.EricWidgets.EricTableView import EricTableView
