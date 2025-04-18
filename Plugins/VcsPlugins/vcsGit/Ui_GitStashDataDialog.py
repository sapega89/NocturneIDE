# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsGit/GitStashDataDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_GitStashDataDialog(object):
    def setupUi(self, GitStashDataDialog):
        GitStashDataDialog.setObjectName("GitStashDataDialog")
        GitStashDataDialog.resize(500, 238)
        GitStashDataDialog.setSizeGripEnabled(True)
        self.gridLayout = QtWidgets.QGridLayout(GitStashDataDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.label_3 = QtWidgets.QLabel(parent=GitStashDataDialog)
        self.label_3.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 0, 0, 1, 1)
        self.messageEdit = QtWidgets.QLineEdit(parent=GitStashDataDialog)
        self.messageEdit.setObjectName("messageEdit")
        self.gridLayout.addWidget(self.messageEdit, 0, 1, 1, 1)
        self.keepCheckBox = QtWidgets.QCheckBox(parent=GitStashDataDialog)
        self.keepCheckBox.setObjectName("keepCheckBox")
        self.gridLayout.addWidget(self.keepCheckBox, 1, 0, 1, 2)
        self.groupBox = QtWidgets.QGroupBox(parent=GitStashDataDialog)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.noneRadioButton = QtWidgets.QRadioButton(parent=self.groupBox)
        self.noneRadioButton.setChecked(True)
        self.noneRadioButton.setObjectName("noneRadioButton")
        self.verticalLayout.addWidget(self.noneRadioButton)
        self.untrackedRadioButton = QtWidgets.QRadioButton(parent=self.groupBox)
        self.untrackedRadioButton.setObjectName("untrackedRadioButton")
        self.verticalLayout.addWidget(self.untrackedRadioButton)
        self.allRadioButton = QtWidgets.QRadioButton(parent=self.groupBox)
        self.allRadioButton.setObjectName("allRadioButton")
        self.verticalLayout.addWidget(self.allRadioButton)
        self.gridLayout.addWidget(self.groupBox, 2, 0, 1, 2)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=GitStashDataDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 3, 0, 1, 2)

        self.retranslateUi(GitStashDataDialog)
        self.buttonBox.accepted.connect(GitStashDataDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(GitStashDataDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(GitStashDataDialog)
        GitStashDataDialog.setTabOrder(self.messageEdit, self.keepCheckBox)
        GitStashDataDialog.setTabOrder(self.keepCheckBox, self.noneRadioButton)
        GitStashDataDialog.setTabOrder(self.noneRadioButton, self.untrackedRadioButton)
        GitStashDataDialog.setTabOrder(self.untrackedRadioButton, self.allRadioButton)

    def retranslateUi(self, GitStashDataDialog):
        _translate = QtCore.QCoreApplication.translate
        GitStashDataDialog.setWindowTitle(_translate("GitStashDataDialog", "Git Stash"))
        self.label_3.setText(_translate("GitStashDataDialog", "Message:"))
        self.messageEdit.setToolTip(_translate("GitStashDataDialog", "Enter a message for the stash"))
        self.keepCheckBox.setText(_translate("GitStashDataDialog", "Keep changes in staging area"))
        self.groupBox.setTitle(_translate("GitStashDataDialog", "Untracked/Ignored Files"))
        self.noneRadioButton.setToolTip(_translate("GitStashDataDialog", "Select to not stash untracked or ignored files"))
        self.noneRadioButton.setText(_translate("GitStashDataDialog", "Don\'t stash untracked or ignored files"))
        self.untrackedRadioButton.setToolTip(_translate("GitStashDataDialog", "Select to stash untracked files"))
        self.untrackedRadioButton.setText(_translate("GitStashDataDialog", "Stash untracked files"))
        self.allRadioButton.setToolTip(_translate("GitStashDataDialog", "Select to stash untracked and ignored files"))
        self.allRadioButton.setText(_translate("GitStashDataDialog", "Stash untracked and ignored files"))
