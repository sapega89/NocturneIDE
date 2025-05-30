# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsGit/GitPushDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_GitPushDialog(object):
    def setupUi(self, GitPushDialog):
        GitPushDialog.setObjectName("GitPushDialog")
        GitPushDialog.resize(600, 400)
        GitPushDialog.setSizeGripEnabled(True)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(GitPushDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(parent=GitPushDialog)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.remotesComboBox = QtWidgets.QComboBox(parent=GitPushDialog)
        self.remotesComboBox.setObjectName("remotesComboBox")
        self.horizontalLayout.addWidget(self.remotesComboBox)
        self.remoteEdit = QtWidgets.QLineEdit(parent=GitPushDialog)
        self.remoteEdit.setReadOnly(True)
        self.remoteEdit.setObjectName("remoteEdit")
        self.horizontalLayout.addWidget(self.remoteEdit)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.groupBox = QtWidgets.QGroupBox(parent=GitPushDialog)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.branchesTree = QtWidgets.QTreeWidget(parent=self.groupBox)
        self.branchesTree.setAlternatingRowColors(True)
        self.branchesTree.setRootIsDecorated(False)
        self.branchesTree.setItemsExpandable(False)
        self.branchesTree.setExpandsOnDoubleClick(False)
        self.branchesTree.setObjectName("branchesTree")
        self.verticalLayout.addWidget(self.branchesTree)
        self.selectAllCheckBox = QtWidgets.QCheckBox(parent=self.groupBox)
        self.selectAllCheckBox.setTristate(True)
        self.selectAllCheckBox.setObjectName("selectAllCheckBox")
        self.verticalLayout.addWidget(self.selectAllCheckBox)
        self.forceWarningLabel = QtWidgets.QLabel(parent=self.groupBox)
        self.forceWarningLabel.setWordWrap(True)
        self.forceWarningLabel.setObjectName("forceWarningLabel")
        self.verticalLayout.addWidget(self.forceWarningLabel)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.tagsCheckBox = QtWidgets.QCheckBox(parent=GitPushDialog)
        self.tagsCheckBox.setObjectName("tagsCheckBox")
        self.verticalLayout_2.addWidget(self.tagsCheckBox)
        self.trackingCheckBox = QtWidgets.QCheckBox(parent=GitPushDialog)
        self.trackingCheckBox.setObjectName("trackingCheckBox")
        self.verticalLayout_2.addWidget(self.trackingCheckBox)
        self.groupBox_2 = QtWidgets.QGroupBox(parent=GitPushDialog)
        self.groupBox_2.setObjectName("groupBox_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.submodulesOnDemandButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.submodulesOnDemandButton.setChecked(True)
        self.submodulesOnDemandButton.setObjectName("submodulesOnDemandButton")
        self.horizontalLayout_2.addWidget(self.submodulesOnDemandButton)
        self.submodulesCheckButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.submodulesCheckButton.setObjectName("submodulesCheckButton")
        self.horizontalLayout_2.addWidget(self.submodulesCheckButton)
        self.submodulesOnlyButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.submodulesOnlyButton.setObjectName("submodulesOnlyButton")
        self.horizontalLayout_2.addWidget(self.submodulesOnlyButton)
        self.submodulesNoButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.submodulesNoButton.setObjectName("submodulesNoButton")
        self.horizontalLayout_2.addWidget(self.submodulesNoButton)
        self.verticalLayout_2.addWidget(self.groupBox_2)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=GitPushDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout_2.addWidget(self.buttonBox)

        self.retranslateUi(GitPushDialog)
        self.buttonBox.accepted.connect(GitPushDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(GitPushDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(GitPushDialog)
        GitPushDialog.setTabOrder(self.remotesComboBox, self.remoteEdit)
        GitPushDialog.setTabOrder(self.remoteEdit, self.branchesTree)
        GitPushDialog.setTabOrder(self.branchesTree, self.selectAllCheckBox)
        GitPushDialog.setTabOrder(self.selectAllCheckBox, self.tagsCheckBox)
        GitPushDialog.setTabOrder(self.tagsCheckBox, self.trackingCheckBox)

    def retranslateUi(self, GitPushDialog):
        _translate = QtCore.QCoreApplication.translate
        GitPushDialog.setWindowTitle(_translate("GitPushDialog", "Git Push"))
        self.label.setText(_translate("GitPushDialog", "Remote Repository:"))
        self.remotesComboBox.setToolTip(_translate("GitPushDialog", "Select the remote repository to push to"))
        self.groupBox.setTitle(_translate("GitPushDialog", "Branches to be pushed"))
        self.branchesTree.setSortingEnabled(True)
        self.branchesTree.headerItem().setText(0, _translate("GitPushDialog", "Push?"))
        self.branchesTree.headerItem().setText(1, _translate("GitPushDialog", "Local"))
        self.branchesTree.headerItem().setText(2, _translate("GitPushDialog", "Remote"))
        self.branchesTree.headerItem().setText(3, _translate("GitPushDialog", "Force?"))
        self.selectAllCheckBox.setToolTip(_translate("GitPushDialog", "Press to select all branches"))
        self.selectAllCheckBox.setText(_translate("GitPushDialog", "Select All"))
        self.forceWarningLabel.setText(_translate("GitPushDialog", "<b>WARNING: The \"Force\" option can result in dangling branches in the remote repository.</b>"))
        self.tagsCheckBox.setToolTip(_translate("GitPushDialog", "Select to push tags as well"))
        self.tagsCheckBox.setText(_translate("GitPushDialog", "Include tags"))
        self.trackingCheckBox.setToolTip(_translate("GitPushDialog", "Select this to associate a remote tracking branch"))
        self.trackingCheckBox.setText(_translate("GitPushDialog", "Set tracking information"))
        self.groupBox_2.setTitle(_translate("GitPushDialog", "Push Submodules"))
        self.submodulesOnDemandButton.setToolTip(_translate("GitPushDialog", "Select to push submodules automatically"))
        self.submodulesOnDemandButton.setText(_translate("GitPushDialog", "on-demand"))
        self.submodulesCheckButton.setToolTip(_translate("GitPushDialog", "Select to check, if submodules were pushed already"))
        self.submodulesCheckButton.setText(_translate("GitPushDialog", "check"))
        self.submodulesOnlyButton.setToolTip(_translate("GitPushDialog", "Select to push submodules only"))
        self.submodulesOnlyButton.setText(_translate("GitPushDialog", "only"))
        self.submodulesNoButton.setToolTip(_translate("GitPushDialog", "Select to not push any submodule"))
        self.submodulesNoButton.setText(_translate("GitPushDialog", "no"))
