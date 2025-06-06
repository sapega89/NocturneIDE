# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsMercurial/LargefilesExtension/LfConvertDataDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_LfConvertDataDialog(object):
    def setupUi(self, LfConvertDataDialog):
        LfConvertDataDialog.setObjectName("LfConvertDataDialog")
        LfConvertDataDialog.resize(500, 144)
        LfConvertDataDialog.setSizeGripEnabled(True)
        self.gridLayout = QtWidgets.QGridLayout(LfConvertDataDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.currentProjectLabel = EricSqueezeLabelPath(parent=LfConvertDataDialog)
        self.currentProjectLabel.setObjectName("currentProjectLabel")
        self.gridLayout.addWidget(self.currentProjectLabel, 0, 0, 1, 3)
        self.label = QtWidgets.QLabel(parent=LfConvertDataDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.newProjectPicker = EricPathPicker(parent=LfConvertDataDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.newProjectPicker.sizePolicy().hasHeightForWidth())
        self.newProjectPicker.setSizePolicy(sizePolicy)
        self.newProjectPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.newProjectPicker.setObjectName("newProjectPicker")
        self.gridLayout.addWidget(self.newProjectPicker, 1, 1, 1, 2)
        self.label_4 = QtWidgets.QLabel(parent=LfConvertDataDialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 2, 0, 1, 1)
        self.lfFileSizeSpinBox = QtWidgets.QSpinBox(parent=LfConvertDataDialog)
        self.lfFileSizeSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.lfFileSizeSpinBox.setMinimum(1)
        self.lfFileSizeSpinBox.setProperty("value", 10)
        self.lfFileSizeSpinBox.setObjectName("lfFileSizeSpinBox")
        self.gridLayout.addWidget(self.lfFileSizeSpinBox, 2, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(297, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout.addItem(spacerItem, 2, 2, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=LfConvertDataDialog)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 3, 0, 1, 1)
        self.lfFilePatternsEdit = QtWidgets.QLineEdit(parent=LfConvertDataDialog)
        self.lfFilePatternsEdit.setObjectName("lfFilePatternsEdit")
        self.gridLayout.addWidget(self.lfFilePatternsEdit, 3, 1, 1, 2)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=LfConvertDataDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 4, 0, 1, 3)

        self.retranslateUi(LfConvertDataDialog)
        self.buttonBox.accepted.connect(LfConvertDataDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(LfConvertDataDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(LfConvertDataDialog)
        LfConvertDataDialog.setTabOrder(self.newProjectPicker, self.lfFileSizeSpinBox)
        LfConvertDataDialog.setTabOrder(self.lfFileSizeSpinBox, self.lfFilePatternsEdit)

    def retranslateUi(self, LfConvertDataDialog):
        _translate = QtCore.QCoreApplication.translate
        LfConvertDataDialog.setWindowTitle(_translate("LfConvertDataDialog", "Convert Repository Format"))
        self.label.setText(_translate("LfConvertDataDialog", "New project directory:"))
        self.newProjectPicker.setToolTip(_translate("LfConvertDataDialog", "Enter the directory name of the new project directory"))
        self.label_4.setText(_translate("LfConvertDataDialog", "Minimum file size:"))
        self.lfFileSizeSpinBox.setToolTip(_translate("LfConvertDataDialog", "Enter the minimum file size in MB for files to be treated as Large Files"))
        self.lfFileSizeSpinBox.setSuffix(_translate("LfConvertDataDialog", " MB"))
        self.label_5.setText(_translate("LfConvertDataDialog", "Patterns:"))
        self.lfFilePatternsEdit.setToolTip(_translate("LfConvertDataDialog", "Enter file patterns (space separated) for files to be treated as Large Files"))
from eric7.EricWidgets.EricPathPicker import EricPathPicker
from eric7.EricWidgets.EricSqueezeLabels import EricSqueezeLabelPath
