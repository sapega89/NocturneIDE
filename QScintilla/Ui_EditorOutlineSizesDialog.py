# Form implementation generated from reading ui file 'src/eric7/QScintilla/EditorOutlineSizesDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_EditorOutlineSizesDialog(object):
    def setupUi(self, EditorOutlineSizesDialog):
        EditorOutlineSizesDialog.setObjectName("EditorOutlineSizesDialog")
        EditorOutlineSizesDialog.resize(400, 77)
        EditorOutlineSizesDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(EditorOutlineSizesDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtWidgets.QLabel(parent=EditorOutlineSizesDialog)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.sourceOutlineWidthSpinBox = QtWidgets.QSpinBox(parent=EditorOutlineSizesDialog)
        self.sourceOutlineWidthSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.sourceOutlineWidthSpinBox.setMinimum(50)
        self.sourceOutlineWidthSpinBox.setMaximum(498)
        self.sourceOutlineWidthSpinBox.setSingleStep(50)
        self.sourceOutlineWidthSpinBox.setObjectName("sourceOutlineWidthSpinBox")
        self.horizontalLayout.addWidget(self.sourceOutlineWidthSpinBox)
        spacerItem = QtWidgets.QSpacerItem(58, 17, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=EditorOutlineSizesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(EditorOutlineSizesDialog)
        self.buttonBox.accepted.connect(EditorOutlineSizesDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(EditorOutlineSizesDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(EditorOutlineSizesDialog)

    def retranslateUi(self, EditorOutlineSizesDialog):
        _translate = QtCore.QCoreApplication.translate
        EditorOutlineSizesDialog.setWindowTitle(_translate("EditorOutlineSizesDialog", "Editor Outline Sizes"))
        self.label_2.setText(_translate("EditorOutlineSizesDialog", "Default Width:"))
        self.sourceOutlineWidthSpinBox.setToolTip(_translate("EditorOutlineSizesDialog", "Enter the default width of the source code outline view"))
