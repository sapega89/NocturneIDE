# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsPySvn/SvnPropDelDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_SvnPropDelDialog(object):
    def setupUi(self, SvnPropDelDialog):
        SvnPropDelDialog.setObjectName("SvnPropDelDialog")
        SvnPropDelDialog.resize(494, 98)
        SvnPropDelDialog.setSizeGripEnabled(True)
        self.vboxlayout = QtWidgets.QVBoxLayout(SvnPropDelDialog)
        self.vboxlayout.setObjectName("vboxlayout")
        self.gridlayout = QtWidgets.QGridLayout()
        self.gridlayout.setObjectName("gridlayout")
        self.propNameEdit = QtWidgets.QLineEdit(parent=SvnPropDelDialog)
        self.propNameEdit.setObjectName("propNameEdit")
        self.gridlayout.addWidget(self.propNameEdit, 0, 1, 1, 1)
        self.recurseCheckBox = QtWidgets.QCheckBox(parent=SvnPropDelDialog)
        self.recurseCheckBox.setObjectName("recurseCheckBox")
        self.gridlayout.addWidget(self.recurseCheckBox, 1, 0, 1, 2)
        self.textLabel1 = QtWidgets.QLabel(parent=SvnPropDelDialog)
        self.textLabel1.setObjectName("textLabel1")
        self.gridlayout.addWidget(self.textLabel1, 0, 0, 1, 1)
        self.vboxlayout.addLayout(self.gridlayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=SvnPropDelDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.vboxlayout.addWidget(self.buttonBox)
        self.textLabel1.setBuddy(self.propNameEdit)

        self.retranslateUi(SvnPropDelDialog)
        self.buttonBox.accepted.connect(SvnPropDelDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(SvnPropDelDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(SvnPropDelDialog)
        SvnPropDelDialog.setTabOrder(self.propNameEdit, self.recurseCheckBox)

    def retranslateUi(self, SvnPropDelDialog):
        _translate = QtCore.QCoreApplication.translate
        SvnPropDelDialog.setWindowTitle(_translate("SvnPropDelDialog", "Delete Subversion Property"))
        self.propNameEdit.setToolTip(_translate("SvnPropDelDialog", "Enter the name of the property to be deleted"))
        self.recurseCheckBox.setToolTip(_translate("SvnPropDelDialog", "Select to apply the property recursively"))
        self.recurseCheckBox.setText(_translate("SvnPropDelDialog", "Apply &recursively"))
        self.textLabel1.setText(_translate("SvnPropDelDialog", "Property &Name:"))
