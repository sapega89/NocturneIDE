# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/MainPasswordEntryDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainPasswordEntryDialog(object):
    def setupUi(self, MainPasswordEntryDialog):
        MainPasswordEntryDialog.setObjectName("MainPasswordEntryDialog")
        MainPasswordEntryDialog.resize(450, 322)
        MainPasswordEntryDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(MainPasswordEntryDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(parent=MainPasswordEntryDialog)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        spacerItem = QtWidgets.QSpacerItem(20, 28, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(spacerItem)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtWidgets.QLabel(parent=MainPasswordEntryDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.currentPasswordEdit = QtWidgets.QLineEdit(parent=MainPasswordEntryDialog)
        self.currentPasswordEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.currentPasswordEdit.setObjectName("currentPasswordEdit")
        self.gridLayout.addWidget(self.currentPasswordEdit, 0, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=MainPasswordEntryDialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.newPasswordEdit = QtWidgets.QLineEdit(parent=MainPasswordEntryDialog)
        self.newPasswordEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.newPasswordEdit.setObjectName("newPasswordEdit")
        self.gridLayout.addWidget(self.newPasswordEdit, 1, 1, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=MainPasswordEntryDialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 2, 0, 1, 1)
        self.newPasswordAgainEdit = QtWidgets.QLineEdit(parent=MainPasswordEntryDialog)
        self.newPasswordAgainEdit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.newPasswordAgainEdit.setObjectName("newPasswordAgainEdit")
        self.gridLayout.addWidget(self.newPasswordAgainEdit, 2, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.passwordMeter = EricPasswordMeter(parent=MainPasswordEntryDialog)
        self.passwordMeter.setObjectName("passwordMeter")
        self.verticalLayout.addWidget(self.passwordMeter)
        self.errorLabel = QtWidgets.QLabel(parent=MainPasswordEntryDialog)
        self.errorLabel.setStyleSheet("color : red;")
        self.errorLabel.setWordWrap(True)
        self.errorLabel.setObjectName("errorLabel")
        self.verticalLayout.addWidget(self.errorLabel)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=MainPasswordEntryDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(MainPasswordEntryDialog)
        self.buttonBox.accepted.connect(MainPasswordEntryDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(MainPasswordEntryDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(MainPasswordEntryDialog)
        MainPasswordEntryDialog.setTabOrder(self.currentPasswordEdit, self.newPasswordEdit)
        MainPasswordEntryDialog.setTabOrder(self.newPasswordEdit, self.newPasswordAgainEdit)
        MainPasswordEntryDialog.setTabOrder(self.newPasswordAgainEdit, self.buttonBox)

    def retranslateUi(self, MainPasswordEntryDialog):
        _translate = QtCore.QCoreApplication.translate
        MainPasswordEntryDialog.setWindowTitle(_translate("MainPasswordEntryDialog", "Main Password"))
        self.label.setText(_translate("MainPasswordEntryDialog", "<p>Enter your main password below. This password will be used to encrypt sensitive data. You will be asked once per session for this password when the data needs to be accessed for the first time.<br/><br/><b>Note: If you forget the main password, the encrypted data cannot be recovered!</b></p>"))
        self.label_2.setText(_translate("MainPasswordEntryDialog", "Current Password:"))
        self.currentPasswordEdit.setToolTip(_translate("MainPasswordEntryDialog", "Enter the current password"))
        self.label_3.setText(_translate("MainPasswordEntryDialog", "New Password:"))
        self.newPasswordEdit.setToolTip(_translate("MainPasswordEntryDialog", "Enter the new password"))
        self.label_4.setText(_translate("MainPasswordEntryDialog", "New Password (again):"))
        self.newPasswordAgainEdit.setToolTip(_translate("MainPasswordEntryDialog", "Repeat the new password"))
        self.passwordMeter.setToolTip(_translate("MainPasswordEntryDialog", "Shows an indication for the password strength"))
from eric7.EricWidgets.EricPasswordMeter import EricPasswordMeter
