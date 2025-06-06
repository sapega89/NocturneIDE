# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsSubversion/SvnCommandDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_SvnCommandDialog(object):
    def setupUi(self, SvnCommandDialog):
        SvnCommandDialog.setObjectName("SvnCommandDialog")
        SvnCommandDialog.resize(628, 129)
        self.gridLayout = QtWidgets.QGridLayout(SvnCommandDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.textLabel1 = QtWidgets.QLabel(parent=SvnCommandDialog)
        self.textLabel1.setToolTip("")
        self.textLabel1.setObjectName("textLabel1")
        self.gridLayout.addWidget(self.textLabel1, 0, 0, 1, 1)
        self.commandCombo = QtWidgets.QComboBox(parent=SvnCommandDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.commandCombo.sizePolicy().hasHeightForWidth())
        self.commandCombo.setSizePolicy(sizePolicy)
        self.commandCombo.setEditable(True)
        self.commandCombo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.InsertAtTop)
        self.commandCombo.setDuplicatesEnabled(False)
        self.commandCombo.setObjectName("commandCombo")
        self.gridLayout.addWidget(self.commandCombo, 0, 1, 1, 1)
        self.textLabel2 = QtWidgets.QLabel(parent=SvnCommandDialog)
        self.textLabel2.setObjectName("textLabel2")
        self.gridLayout.addWidget(self.textLabel2, 1, 0, 1, 1)
        self.workdirPicker = EricComboPathPicker(parent=SvnCommandDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.workdirPicker.sizePolicy().hasHeightForWidth())
        self.workdirPicker.setSizePolicy(sizePolicy)
        self.workdirPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.WheelFocus)
        self.workdirPicker.setObjectName("workdirPicker")
        self.gridLayout.addWidget(self.workdirPicker, 1, 1, 1, 1)
        self.textLabel3 = QtWidgets.QLabel(parent=SvnCommandDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textLabel3.sizePolicy().hasHeightForWidth())
        self.textLabel3.setSizePolicy(sizePolicy)
        self.textLabel3.setObjectName("textLabel3")
        self.gridLayout.addWidget(self.textLabel3, 2, 0, 1, 1)
        self.projectDirLabel = QtWidgets.QLabel(parent=SvnCommandDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.projectDirLabel.sizePolicy().hasHeightForWidth())
        self.projectDirLabel.setSizePolicy(sizePolicy)
        self.projectDirLabel.setObjectName("projectDirLabel")
        self.gridLayout.addWidget(self.projectDirLabel, 2, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=SvnCommandDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 3, 0, 1, 2)

        self.retranslateUi(SvnCommandDialog)
        self.buttonBox.accepted.connect(SvnCommandDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(SvnCommandDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(SvnCommandDialog)
        SvnCommandDialog.setTabOrder(self.commandCombo, self.workdirPicker)

    def retranslateUi(self, SvnCommandDialog):
        _translate = QtCore.QCoreApplication.translate
        SvnCommandDialog.setWindowTitle(_translate("SvnCommandDialog", "Subversion Command"))
        self.textLabel1.setText(_translate("SvnCommandDialog", "Subversion Command:"))
        self.commandCombo.setToolTip(_translate("SvnCommandDialog", "Enter the Subversion command to be executed with all necessary parameters"))
        self.commandCombo.setWhatsThis(_translate("SvnCommandDialog", "<b>Subversion Command</b>\n"
"<p>Enter the Subversion command to be executed including all necessary \n"
"parameters. If a parameter of the commandline includes a space you have to \n"
"surround this parameter by single or double quotes. Do not include the name \n"
"of the subversion client executable (i.e. svn).</p>"))
        self.textLabel2.setText(_translate("SvnCommandDialog", "Working Directory:<br>(optional)"))
        self.workdirPicker.setToolTip(_translate("SvnCommandDialog", "Enter the working directory for the Subversion command"))
        self.workdirPicker.setWhatsThis(_translate("SvnCommandDialog", "<b>Working directory</b>\n"
"<p>Enter the working directory for the Subversion command.\n"
"This is an optional entry. The button to the right will open a \n"
"directory selection dialog.</p>"))
        self.textLabel3.setText(_translate("SvnCommandDialog", "Project Directory:"))
        self.projectDirLabel.setToolTip(_translate("SvnCommandDialog", "This shows the root directory of the current project."))
        self.projectDirLabel.setText(_translate("SvnCommandDialog", "project directory"))
from eric7.EricWidgets.EricPathPicker import EricComboPathPicker
