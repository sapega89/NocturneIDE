# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsMercurial/FastexportExtension/HgFastexportConfigDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_HgFastexportConfigDialog(object):
    def setupUi(self, HgFastexportConfigDialog):
        HgFastexportConfigDialog.setObjectName("HgFastexportConfigDialog")
        HgFastexportConfigDialog.resize(600, 172)
        HgFastexportConfigDialog.setSizeGripEnabled(True)
        self.gridLayout = QtWidgets.QGridLayout(HgFastexportConfigDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.exportMarksPicker = EricPathPicker(parent=HgFastexportConfigDialog)
        self.exportMarksPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.exportMarksPicker.setObjectName("exportMarksPicker")
        self.gridLayout.addWidget(self.exportMarksPicker, 4, 1, 1, 1)
        self.outputPicker = EricPathPicker(parent=HgFastexportConfigDialog)
        self.outputPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.outputPicker.setObjectName("outputPicker")
        self.gridLayout.addWidget(self.outputPicker, 0, 1, 1, 1)
        self.label = QtWidgets.QLabel(parent=HgFastexportConfigDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.importMarksPicker = EricPathPicker(parent=HgFastexportConfigDialog)
        self.importMarksPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.importMarksPicker.setObjectName("importMarksPicker")
        self.gridLayout.addWidget(self.importMarksPicker, 3, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=HgFastexportConfigDialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=HgFastexportConfigDialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=HgFastexportConfigDialog)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=HgFastexportConfigDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.revisionsEdit = QtWidgets.QLineEdit(parent=HgFastexportConfigDialog)
        self.revisionsEdit.setClearButtonEnabled(True)
        self.revisionsEdit.setObjectName("revisionsEdit")
        self.gridLayout.addWidget(self.revisionsEdit, 1, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=HgFastexportConfigDialog)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 5, 0, 1, 2)
        self.authormapPicker = EricPathPicker(parent=HgFastexportConfigDialog)
        self.authormapPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.authormapPicker.setObjectName("authormapPicker")
        self.gridLayout.addWidget(self.authormapPicker, 2, 1, 1, 1)

        self.retranslateUi(HgFastexportConfigDialog)
        self.buttonBox.accepted.connect(HgFastexportConfigDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(HgFastexportConfigDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(HgFastexportConfigDialog)
        HgFastexportConfigDialog.setTabOrder(self.outputPicker, self.revisionsEdit)
        HgFastexportConfigDialog.setTabOrder(self.revisionsEdit, self.authormapPicker)
        HgFastexportConfigDialog.setTabOrder(self.authormapPicker, self.importMarksPicker)
        HgFastexportConfigDialog.setTabOrder(self.importMarksPicker, self.exportMarksPicker)

    def retranslateUi(self, HgFastexportConfigDialog):
        _translate = QtCore.QCoreApplication.translate
        HgFastexportConfigDialog.setWindowTitle(_translate("HgFastexportConfigDialog", "fastexport Configuration"))
        self.exportMarksPicker.setToolTip(_translate("HgFastexportConfigDialog", "Enter the path of the file for the exported marks."))
        self.outputPicker.setToolTip(_translate("HgFastexportConfigDialog", "Enter the path of the output file."))
        self.label.setText(_translate("HgFastexportConfigDialog", "Revisions:"))
        self.importMarksPicker.setToolTip(_translate("HgFastexportConfigDialog", "Enter the path of the file containing already exported marks."))
        self.label_3.setText(_translate("HgFastexportConfigDialog", "Author Map:"))
        self.label_4.setText(_translate("HgFastexportConfigDialog", "Import Marks:"))
        self.label_5.setText(_translate("HgFastexportConfigDialog", "Export Marks:"))
        self.label_2.setText(_translate("HgFastexportConfigDialog", "Output File:"))
        self.revisionsEdit.setToolTip(_translate("HgFastexportConfigDialog", "Enter the revisions, tags or branches to be exported (separated by comma)."))
        self.authormapPicker.setToolTip(_translate("HgFastexportConfigDialog", "Enter the path of the author map file."))
from eric7.EricWidgets.EricPathPicker import EricPathPicker
