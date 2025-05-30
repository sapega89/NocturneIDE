# Form implementation generated from reading ui file 'src/eric7/MicroPython/ShowModulesDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_ShowModulesDialog(object):
    def setupUi(self, ShowModulesDialog):
        ShowModulesDialog.setObjectName("ShowModulesDialog")
        ShowModulesDialog.resize(400, 700)
        ShowModulesDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(ShowModulesDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(parent=ShowModulesDialog)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.filterEdit = QtWidgets.QLineEdit(parent=ShowModulesDialog)
        self.filterEdit.setClearButtonEnabled(True)
        self.filterEdit.setObjectName("filterEdit")
        self.horizontalLayout.addWidget(self.filterEdit)
        self.filterButton = QtWidgets.QToolButton(parent=ShowModulesDialog)
        self.filterButton.setObjectName("filterButton")
        self.horizontalLayout.addWidget(self.filterButton)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.modulesList = QtWidgets.QListWidget(parent=ShowModulesDialog)
        self.modulesList.setAlternatingRowColors(True)
        self.modulesList.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.modulesList.setObjectName("modulesList")
        self.verticalLayout.addWidget(self.modulesList)
        self.infoLabel = QtWidgets.QLabel(parent=ShowModulesDialog)
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setObjectName("infoLabel")
        self.verticalLayout.addWidget(self.infoLabel)
        self.statusLabel = QtWidgets.QLabel(parent=ShowModulesDialog)
        self.statusLabel.setObjectName("statusLabel")
        self.verticalLayout.addWidget(self.statusLabel)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=ShowModulesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(ShowModulesDialog)
        self.buttonBox.accepted.connect(ShowModulesDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(ShowModulesDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(ShowModulesDialog)
        ShowModulesDialog.setTabOrder(self.filterEdit, self.filterButton)
        ShowModulesDialog.setTabOrder(self.filterButton, self.modulesList)

    def retranslateUi(self, ShowModulesDialog):
        _translate = QtCore.QCoreApplication.translate
        ShowModulesDialog.setWindowTitle(_translate("ShowModulesDialog", "Available Modules"))
        self.label.setText(_translate("ShowModulesDialog", "Filter:"))
        self.filterEdit.setToolTip(_translate("ShowModulesDialog", "Enter a string used to filter the list below."))
        self.filterEdit.setPlaceholderText(_translate("ShowModulesDialog", "Enter Filter String"))
        self.filterButton.setToolTip(_translate("ShowModulesDialog", "Press to apply the entered filter."))
        self.modulesList.setSortingEnabled(False)
