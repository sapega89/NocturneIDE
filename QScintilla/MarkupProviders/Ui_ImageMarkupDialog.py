# Form implementation generated from reading ui file 'src/eric7/QScintilla/MarkupProviders/ImageMarkupDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_ImageMarkupDialog(object):
    def setupUi(self, ImageMarkupDialog):
        ImageMarkupDialog.setObjectName("ImageMarkupDialog")
        ImageMarkupDialog.resize(500, 231)
        ImageMarkupDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(ImageMarkupDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(parent=ImageMarkupDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.imagePicker = EricPathPicker(parent=ImageMarkupDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.imagePicker.sizePolicy().hasHeightForWidth())
        self.imagePicker.setSizePolicy(sizePolicy)
        self.imagePicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.imagePicker.setObjectName("imagePicker")
        self.gridLayout.addWidget(self.imagePicker, 0, 1, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=ImageMarkupDialog)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 1, 0, 1, 1)
        self.titleEdit = QtWidgets.QLineEdit(parent=ImageMarkupDialog)
        self.titleEdit.setObjectName("titleEdit")
        self.gridLayout.addWidget(self.titleEdit, 1, 1, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=ImageMarkupDialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 2, 0, 1, 1)
        self.altTextEdit = QtWidgets.QLineEdit(parent=ImageMarkupDialog)
        self.altTextEdit.setObjectName("altTextEdit")
        self.gridLayout.addWidget(self.altTextEdit, 2, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.sizeCheckBox = QtWidgets.QCheckBox(parent=ImageMarkupDialog)
        self.sizeCheckBox.setToolTip("")
        self.sizeCheckBox.setObjectName("sizeCheckBox")
        self.verticalLayout.addWidget(self.sizeCheckBox)
        self.aspectRatioCheckBox = QtWidgets.QCheckBox(parent=ImageMarkupDialog)
        self.aspectRatioCheckBox.setObjectName("aspectRatioCheckBox")
        self.verticalLayout.addWidget(self.aspectRatioCheckBox)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_2 = QtWidgets.QLabel(parent=ImageMarkupDialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_3.addWidget(self.label_2)
        self.widthSpinBox = QtWidgets.QSpinBox(parent=ImageMarkupDialog)
        self.widthSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.widthSpinBox.setMaximum(9999)
        self.widthSpinBox.setObjectName("widthSpinBox")
        self.horizontalLayout_3.addWidget(self.widthSpinBox)
        self.label_3 = QtWidgets.QLabel(parent=ImageMarkupDialog)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_3.addWidget(self.label_3)
        self.heightSpinBox = QtWidgets.QSpinBox(parent=ImageMarkupDialog)
        self.heightSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.heightSpinBox.setMaximum(9999)
        self.heightSpinBox.setObjectName("heightSpinBox")
        self.horizontalLayout_3.addWidget(self.heightSpinBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=ImageMarkupDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(ImageMarkupDialog)
        self.buttonBox.accepted.connect(ImageMarkupDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(ImageMarkupDialog.reject) # type: ignore
        self.sizeCheckBox.toggled['bool'].connect(self.aspectRatioCheckBox.setDisabled) # type: ignore
        self.sizeCheckBox.toggled['bool'].connect(self.widthSpinBox.setDisabled) # type: ignore
        self.sizeCheckBox.toggled['bool'].connect(self.heightSpinBox.setDisabled) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(ImageMarkupDialog)
        ImageMarkupDialog.setTabOrder(self.imagePicker, self.titleEdit)
        ImageMarkupDialog.setTabOrder(self.titleEdit, self.altTextEdit)
        ImageMarkupDialog.setTabOrder(self.altTextEdit, self.sizeCheckBox)
        ImageMarkupDialog.setTabOrder(self.sizeCheckBox, self.aspectRatioCheckBox)
        ImageMarkupDialog.setTabOrder(self.aspectRatioCheckBox, self.widthSpinBox)
        ImageMarkupDialog.setTabOrder(self.widthSpinBox, self.heightSpinBox)

    def retranslateUi(self, ImageMarkupDialog):
        _translate = QtCore.QCoreApplication.translate
        ImageMarkupDialog.setWindowTitle(_translate("ImageMarkupDialog", "Add Image"))
        self.label.setText(_translate("ImageMarkupDialog", "Image Address:"))
        self.imagePicker.setToolTip(_translate("ImageMarkupDialog", "Enter the image path or URL"))
        self.label_5.setText(_translate("ImageMarkupDialog", "Title:"))
        self.label_4.setText(_translate("ImageMarkupDialog", "Alternative Text:"))
        self.sizeCheckBox.setText(_translate("ImageMarkupDialog", "Keep Original Size"))
        self.aspectRatioCheckBox.setText(_translate("ImageMarkupDialog", "Keep Aspect Ratio"))
        self.label_2.setText(_translate("ImageMarkupDialog", "Width:"))
        self.widthSpinBox.setSuffix(_translate("ImageMarkupDialog", " px"))
        self.label_3.setText(_translate("ImageMarkupDialog", "Height:"))
        self.heightSpinBox.setSuffix(_translate("ImageMarkupDialog", " px"))
from eric7.EricWidgets.EricPathPicker import EricPathPicker
