# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsGit/GitListDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_GitListDialog(object):
    def setupUi(self, GitListDialog):
        GitListDialog.setObjectName("GitListDialog")
        GitListDialog.resize(400, 300)
        GitListDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(GitListDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(parent=GitListDialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.selectionList = QtWidgets.QListWidget(parent=GitListDialog)
        self.selectionList.setAlternatingRowColors(True)
        self.selectionList.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.selectionList.setObjectName("selectionList")
        self.verticalLayout.addWidget(self.selectionList)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=GitListDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(GitListDialog)
        self.buttonBox.accepted.connect(GitListDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(GitListDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(GitListDialog)

    def retranslateUi(self, GitListDialog):
        _translate = QtCore.QCoreApplication.translate
        GitListDialog.setWindowTitle(_translate("GitListDialog", "Git Select"))
        self.label.setText(_translate("GitListDialog", "Select from the list:"))
