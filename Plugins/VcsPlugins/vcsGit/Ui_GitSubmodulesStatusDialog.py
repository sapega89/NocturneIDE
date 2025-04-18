# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsGit/GitSubmodulesStatusDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_GitSubmodulesStatusDialog(object):
    def setupUi(self, GitSubmodulesStatusDialog):
        GitSubmodulesStatusDialog.setObjectName("GitSubmodulesStatusDialog")
        GitSubmodulesStatusDialog.resize(700, 400)
        GitSubmodulesStatusDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(GitSubmodulesStatusDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.statusList = QtWidgets.QTreeWidget(parent=GitSubmodulesStatusDialog)
        self.statusList.setAlternatingRowColors(True)
        self.statusList.setRootIsDecorated(False)
        self.statusList.setItemsExpandable(False)
        self.statusList.setObjectName("statusList")
        self.verticalLayout.addWidget(self.statusList)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.indexCheckBox = QtWidgets.QCheckBox(parent=GitSubmodulesStatusDialog)
        self.indexCheckBox.setObjectName("indexCheckBox")
        self.horizontalLayout.addWidget(self.indexCheckBox)
        self.recursiveCheckBox = QtWidgets.QCheckBox(parent=GitSubmodulesStatusDialog)
        self.recursiveCheckBox.setObjectName("recursiveCheckBox")
        self.horizontalLayout.addWidget(self.recursiveCheckBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.errorGroup = QtWidgets.QGroupBox(parent=GitSubmodulesStatusDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.errorGroup.sizePolicy().hasHeightForWidth())
        self.errorGroup.setSizePolicy(sizePolicy)
        self.errorGroup.setObjectName("errorGroup")
        self.vboxlayout = QtWidgets.QVBoxLayout(self.errorGroup)
        self.vboxlayout.setObjectName("vboxlayout")
        self.errors = QtWidgets.QTextEdit(parent=self.errorGroup)
        self.errors.setReadOnly(True)
        self.errors.setAcceptRichText(False)
        self.errors.setObjectName("errors")
        self.vboxlayout.addWidget(self.errors)
        self.verticalLayout.addWidget(self.errorGroup)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=GitSubmodulesStatusDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(GitSubmodulesStatusDialog)
        self.buttonBox.accepted.connect(GitSubmodulesStatusDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(GitSubmodulesStatusDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(GitSubmodulesStatusDialog)
        GitSubmodulesStatusDialog.setTabOrder(self.statusList, self.indexCheckBox)
        GitSubmodulesStatusDialog.setTabOrder(self.indexCheckBox, self.recursiveCheckBox)
        GitSubmodulesStatusDialog.setTabOrder(self.recursiveCheckBox, self.errors)

    def retranslateUi(self, GitSubmodulesStatusDialog):
        _translate = QtCore.QCoreApplication.translate
        GitSubmodulesStatusDialog.setWindowTitle(_translate("GitSubmodulesStatusDialog", "Submodules Status"))
        self.statusList.headerItem().setText(0, _translate("GitSubmodulesStatusDialog", "Submodule"))
        self.statusList.headerItem().setText(1, _translate("GitSubmodulesStatusDialog", "Status"))
        self.statusList.headerItem().setText(2, _translate("GitSubmodulesStatusDialog", "Commit ID"))
        self.statusList.headerItem().setText(3, _translate("GitSubmodulesStatusDialog", "Info"))
        self.indexCheckBox.setToolTip(_translate("GitSubmodulesStatusDialog", "Select to show the status for the index"))
        self.indexCheckBox.setText(_translate("GitSubmodulesStatusDialog", "Show Status for Index"))
        self.recursiveCheckBox.setToolTip(_translate("GitSubmodulesStatusDialog", "Perform a recursive operation"))
        self.recursiveCheckBox.setText(_translate("GitSubmodulesStatusDialog", "Recursive"))
        self.errorGroup.setTitle(_translate("GitSubmodulesStatusDialog", "Errors"))
