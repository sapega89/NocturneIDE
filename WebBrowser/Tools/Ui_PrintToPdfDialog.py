# Form implementation generated from reading ui file 'src/eric7/WebBrowser/Tools/PrintToPdfDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_PrintToPdfDialog(object):
    def setupUi(self, PrintToPdfDialog):
        PrintToPdfDialog.setObjectName("PrintToPdfDialog")
        PrintToPdfDialog.resize(600, 105)
        PrintToPdfDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(PrintToPdfDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(parent=PrintToPdfDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.pdfFilePicker = EricPathPicker(parent=PrintToPdfDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pdfFilePicker.sizePolicy().hasHeightForWidth())
        self.pdfFilePicker.setSizePolicy(sizePolicy)
        self.pdfFilePicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.pdfFilePicker.setObjectName("pdfFilePicker")
        self.gridLayout.addWidget(self.pdfFilePicker, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=PrintToPdfDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pageLayoutLabel = QtWidgets.QLabel(parent=PrintToPdfDialog)
        self.pageLayoutLabel.setText("")
        self.pageLayoutLabel.setObjectName("pageLayoutLabel")
        self.horizontalLayout.addWidget(self.pageLayoutLabel)
        self.pageLayoutButton = QtWidgets.QToolButton(parent=PrintToPdfDialog)
        self.pageLayoutButton.setObjectName("pageLayoutButton")
        self.horizontalLayout.addWidget(self.pageLayoutButton)
        self.gridLayout.addLayout(self.horizontalLayout, 1, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=PrintToPdfDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(PrintToPdfDialog)
        self.buttonBox.accepted.connect(PrintToPdfDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(PrintToPdfDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(PrintToPdfDialog)

    def retranslateUi(self, PrintToPdfDialog):
        _translate = QtCore.QCoreApplication.translate
        PrintToPdfDialog.setWindowTitle(_translate("PrintToPdfDialog", "Print to PDF"))
        self.label.setText(_translate("PrintToPdfDialog", "Save as:"))
        self.pdfFilePicker.setToolTip(_translate("PrintToPdfDialog", "Enter the file name of the PDF document"))
        self.label_2.setText(_translate("PrintToPdfDialog", "Page Layout:"))
        self.pageLayoutButton.setToolTip(_translate("PrintToPdfDialog", "Select the page layout via a dialog"))
        self.pageLayoutButton.setText(_translate("PrintToPdfDialog", "..."))
from eric7.EricWidgets.EricPathPicker import EricPathPicker
