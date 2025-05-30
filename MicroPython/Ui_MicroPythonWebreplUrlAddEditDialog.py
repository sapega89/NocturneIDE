# Form implementation generated from reading ui file 'src/eric7/MicroPython/MicroPythonWebreplUrlAddEditDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MicroPythonWebreplUrlAddEditDialog(object):
    def setupUi(self, MicroPythonWebreplUrlAddEditDialog):
        MicroPythonWebreplUrlAddEditDialog.setObjectName("MicroPythonWebreplUrlAddEditDialog")
        MicroPythonWebreplUrlAddEditDialog.resize(400, 236)
        MicroPythonWebreplUrlAddEditDialog.setSizeGripEnabled(True)
        self.gridLayout = QtWidgets.QGridLayout(MicroPythonWebreplUrlAddEditDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(parent=MicroPythonWebreplUrlAddEditDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.nameEdit = QtWidgets.QLineEdit(parent=MicroPythonWebreplUrlAddEditDialog)
        self.nameEdit.setClearButtonEnabled(True)
        self.nameEdit.setObjectName("nameEdit")
        self.gridLayout.addWidget(self.nameEdit, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=MicroPythonWebreplUrlAddEditDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.descriptionEdit = QtWidgets.QLineEdit(parent=MicroPythonWebreplUrlAddEditDialog)
        self.descriptionEdit.setClearButtonEnabled(True)
        self.descriptionEdit.setObjectName("descriptionEdit")
        self.gridLayout.addWidget(self.descriptionEdit, 1, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=MicroPythonWebreplUrlAddEditDialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.hostEdit = QtWidgets.QLineEdit(parent=MicroPythonWebreplUrlAddEditDialog)
        self.hostEdit.setClearButtonEnabled(True)
        self.hostEdit.setObjectName("hostEdit")
        self.gridLayout.addWidget(self.hostEdit, 2, 1, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=MicroPythonWebreplUrlAddEditDialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)
        self.portEdit = QtWidgets.QLineEdit(parent=MicroPythonWebreplUrlAddEditDialog)
        self.portEdit.setClearButtonEnabled(True)
        self.portEdit.setObjectName("portEdit")
        self.gridLayout.addWidget(self.portEdit, 3, 1, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=MicroPythonWebreplUrlAddEditDialog)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)
        self.passwordEdit = QtWidgets.QLineEdit(parent=MicroPythonWebreplUrlAddEditDialog)
        self.passwordEdit.setClearButtonEnabled(True)
        self.passwordEdit.setObjectName("passwordEdit")
        self.gridLayout.addWidget(self.passwordEdit, 4, 1, 1, 1)
        self.label_6 = QtWidgets.QLabel(parent=MicroPythonWebreplUrlAddEditDialog)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 5, 0, 1, 1)
        self.deviceTypeComboBox = QtWidgets.QComboBox(parent=MicroPythonWebreplUrlAddEditDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.deviceTypeComboBox.sizePolicy().hasHeightForWidth())
        self.deviceTypeComboBox.setSizePolicy(sizePolicy)
        self.deviceTypeComboBox.setObjectName("deviceTypeComboBox")
        self.gridLayout.addWidget(self.deviceTypeComboBox, 5, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=MicroPythonWebreplUrlAddEditDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 6, 0, 1, 2)

        self.retranslateUi(MicroPythonWebreplUrlAddEditDialog)
        self.buttonBox.accepted.connect(MicroPythonWebreplUrlAddEditDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(MicroPythonWebreplUrlAddEditDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(MicroPythonWebreplUrlAddEditDialog)

    def retranslateUi(self, MicroPythonWebreplUrlAddEditDialog):
        _translate = QtCore.QCoreApplication.translate
        MicroPythonWebreplUrlAddEditDialog.setWindowTitle(_translate("MicroPythonWebreplUrlAddEditDialog", "WebREPL URL"))
        self.label.setText(_translate("MicroPythonWebreplUrlAddEditDialog", "Name:"))
        self.nameEdit.setToolTip(_translate("MicroPythonWebreplUrlAddEditDialog", "Enter a unique name for the WebREPL connection."))
        self.label_2.setText(_translate("MicroPythonWebreplUrlAddEditDialog", "Description:"))
        self.descriptionEdit.setToolTip(_translate("MicroPythonWebreplUrlAddEditDialog", "Enter a short description to be shown in the selector."))
        self.label_3.setText(_translate("MicroPythonWebreplUrlAddEditDialog", "Host:"))
        self.hostEdit.setToolTip(_translate("MicroPythonWebreplUrlAddEditDialog", "Enter the host name or IPv4 address of the device."))
        self.label_4.setText(_translate("MicroPythonWebreplUrlAddEditDialog", "Port:"))
        self.portEdit.setToolTip(_translate("MicroPythonWebreplUrlAddEditDialog", "Enter the port of the WebREPL (empty for default port 8266)."))
        self.label_5.setText(_translate("MicroPythonWebreplUrlAddEditDialog", "Password:"))
        self.passwordEdit.setToolTip(_translate("MicroPythonWebreplUrlAddEditDialog", "Enter the password for this device connection."))
        self.label_6.setText(_translate("MicroPythonWebreplUrlAddEditDialog", "Device Type:"))
        self.deviceTypeComboBox.setToolTip(_translate("MicroPythonWebreplUrlAddEditDialog", "Select the device type"))
