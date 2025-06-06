# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsMercurial/HgClientPromptDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_HgClientPromptDialog(object):
    def setupUi(self, HgClientPromptDialog):
        HgClientPromptDialog.setObjectName("HgClientPromptDialog")
        HgClientPromptDialog.resize(400, 400)
        HgClientPromptDialog.setSizeGripEnabled(True)
        self.gridLayout = QtWidgets.QGridLayout(HgClientPromptDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(parent=HgClientPromptDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)
        self.messageEdit = QtWidgets.QPlainTextEdit(parent=HgClientPromptDialog)
        self.messageEdit.setTabChangesFocus(True)
        self.messageEdit.setReadOnly(True)
        self.messageEdit.setObjectName("messageEdit")
        self.gridLayout.addWidget(self.messageEdit, 1, 0, 1, 2)
        self.passwordCheckBox = QtWidgets.QCheckBox(parent=HgClientPromptDialog)
        self.passwordCheckBox.setObjectName("passwordCheckBox")
        self.gridLayout.addWidget(self.passwordCheckBox, 2, 0, 1, 2)
        self.label_2 = QtWidgets.QLabel(parent=HgClientPromptDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 3, 0, 1, 1)
        self.inputEdit = QtWidgets.QLineEdit(parent=HgClientPromptDialog)
        self.inputEdit.setObjectName("inputEdit")
        self.gridLayout.addWidget(self.inputEdit, 3, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=HgClientPromptDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 4, 0, 1, 2)

        self.retranslateUi(HgClientPromptDialog)
        self.buttonBox.accepted.connect(HgClientPromptDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(HgClientPromptDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(HgClientPromptDialog)
        HgClientPromptDialog.setTabOrder(self.passwordCheckBox, self.inputEdit)
        HgClientPromptDialog.setTabOrder(self.inputEdit, self.messageEdit)

    def retranslateUi(self, HgClientPromptDialog):
        _translate = QtCore.QCoreApplication.translate
        HgClientPromptDialog.setWindowTitle(_translate("HgClientPromptDialog", "Mercurial Client Input"))
        self.label.setText(_translate("HgClientPromptDialog", "Message:"))
        self.messageEdit.setToolTip(_translate("HgClientPromptDialog", "Shows the message sent by the Mercurial server"))
        self.passwordCheckBox.setToolTip(_translate("HgClientPromptDialog", "Select to switch the input field to password mode"))
        self.passwordCheckBox.setText(_translate("HgClientPromptDialog", "&Password Mode"))
        self.passwordCheckBox.setShortcut(_translate("HgClientPromptDialog", "Alt+P"))
        self.label_2.setText(_translate("HgClientPromptDialog", "Input:"))
        self.inputEdit.setToolTip(_translate("HgClientPromptDialog", "Enter the response to be sent to the Mercurial server"))
