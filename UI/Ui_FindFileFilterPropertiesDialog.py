# Form implementation generated from reading ui file 'src/eric7/UI/FindFileFilterPropertiesDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_FindFileFilterPropertiesDialog(object):
    def setupUi(self, FindFileFilterPropertiesDialog):
        FindFileFilterPropertiesDialog.setObjectName("FindFileFilterPropertiesDialog")
        FindFileFilterPropertiesDialog.resize(500, 128)
        FindFileFilterPropertiesDialog.setSizeGripEnabled(True)
        self.gridLayout = QtWidgets.QGridLayout(FindFileFilterPropertiesDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.textEdit = QtWidgets.QLineEdit(parent=FindFileFilterPropertiesDialog)
        self.textEdit.setClearButtonEnabled(True)
        self.textEdit.setObjectName("textEdit")
        self.gridLayout.addWidget(self.textEdit, 0, 1, 1, 1)
        self.patternEdit = QtWidgets.QLineEdit(parent=FindFileFilterPropertiesDialog)
        self.patternEdit.setClearButtonEnabled(True)
        self.patternEdit.setObjectName("patternEdit")
        self.gridLayout.addWidget(self.patternEdit, 1, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=FindFileFilterPropertiesDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=FindFileFilterPropertiesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 3, 0, 1, 2)
        self.label = QtWidgets.QLabel(parent=FindFileFilterPropertiesDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.errorLabel = QtWidgets.QLabel(parent=FindFileFilterPropertiesDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.errorLabel.sizePolicy().hasHeightForWidth())
        self.errorLabel.setSizePolicy(sizePolicy)
        self.errorLabel.setWordWrap(True)
        self.errorLabel.setObjectName("errorLabel")
        self.gridLayout.addWidget(self.errorLabel, 2, 0, 1, 2)

        self.retranslateUi(FindFileFilterPropertiesDialog)
        self.buttonBox.accepted.connect(FindFileFilterPropertiesDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(FindFileFilterPropertiesDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(FindFileFilterPropertiesDialog)

    def retranslateUi(self, FindFileFilterPropertiesDialog):
        _translate = QtCore.QCoreApplication.translate
        FindFileFilterPropertiesDialog.setWindowTitle(_translate("FindFileFilterPropertiesDialog", "File Filter Properties"))
        self.textEdit.setToolTip(_translate("FindFileFilterPropertiesDialog", "Enter the name of the file filter."))
        self.patternEdit.setToolTip(_translate("FindFileFilterPropertiesDialog", "Enter the pattern of the file filter. Multiple patterns must be separated by spaces."))
        self.label_2.setText(_translate("FindFileFilterPropertiesDialog", "Pattern:"))
        self.label.setText(_translate("FindFileFilterPropertiesDialog", "Name:"))
