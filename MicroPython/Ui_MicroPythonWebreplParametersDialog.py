# Form implementation generated from reading ui file 'src/eric7/MicroPython/MicroPythonWebreplParametersDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MicroPythonWebreplParametersDialog(object):
    def setupUi(self, MicroPythonWebreplParametersDialog):
        MicroPythonWebreplParametersDialog.setObjectName("MicroPythonWebreplParametersDialog")
        MicroPythonWebreplParametersDialog.resize(400, 108)
        MicroPythonWebreplParametersDialog.setSizeGripEnabled(True)
        self.gridLayout = QtWidgets.QGridLayout(MicroPythonWebreplParametersDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(parent=MicroPythonWebreplParametersDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.passwordEdit = QtWidgets.QLineEdit(parent=MicroPythonWebreplParametersDialog)
        self.passwordEdit.setMaxLength(9)
        self.passwordEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.passwordEdit.setClearButtonEnabled(True)
        self.passwordEdit.setObjectName("passwordEdit")
        self.gridLayout.addWidget(self.passwordEdit, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=MicroPythonWebreplParametersDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.passwordConfirmEdit = QtWidgets.QLineEdit(parent=MicroPythonWebreplParametersDialog)
        self.passwordConfirmEdit.setMaxLength(9)
        self.passwordConfirmEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.passwordConfirmEdit.setClearButtonEnabled(True)
        self.passwordConfirmEdit.setObjectName("passwordConfirmEdit")
        self.gridLayout.addWidget(self.passwordConfirmEdit, 1, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=MicroPythonWebreplParametersDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 2)

        self.retranslateUi(MicroPythonWebreplParametersDialog)
        self.buttonBox.accepted.connect(MicroPythonWebreplParametersDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(MicroPythonWebreplParametersDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(MicroPythonWebreplParametersDialog)

    def retranslateUi(self, MicroPythonWebreplParametersDialog):
        _translate = QtCore.QCoreApplication.translate
        MicroPythonWebreplParametersDialog.setWindowTitle(_translate("MicroPythonWebreplParametersDialog", "WebREPL Server Parameters"))
        self.label.setText(_translate("MicroPythonWebreplParametersDialog", "Password (4-9 characters):"))
        self.passwordEdit.setToolTip(_translate("MicroPythonWebreplParametersDialog", "Enter the password for the device WebREPL server."))
        self.label_2.setText(_translate("MicroPythonWebreplParametersDialog", "Confirm Password:"))
        self.passwordConfirmEdit.setToolTip(_translate("MicroPythonWebreplParametersDialog", "Repeat the WebREPL server password."))
