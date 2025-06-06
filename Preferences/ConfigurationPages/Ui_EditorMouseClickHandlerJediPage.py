# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/EditorMouseClickHandlerJediPage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_EditorMouseClickHandlerJediPage(object):
    def setupUi(self, EditorMouseClickHandlerJediPage):
        EditorMouseClickHandlerJediPage.setObjectName("EditorMouseClickHandlerJediPage")
        EditorMouseClickHandlerJediPage.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(EditorMouseClickHandlerJediPage)
        self.verticalLayout.setObjectName("verticalLayout")
        self.headerLabel = QtWidgets.QLabel(parent=EditorMouseClickHandlerJediPage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout.addWidget(self.headerLabel)
        self.line15 = QtWidgets.QFrame(parent=EditorMouseClickHandlerJediPage)
        self.line15.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line15.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line15.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line15.setObjectName("line15")
        self.verticalLayout.addWidget(self.line15)
        self.jediClickHandlerCheckBox = QtWidgets.QCheckBox(parent=EditorMouseClickHandlerJediPage)
        self.jediClickHandlerCheckBox.setObjectName("jediClickHandlerCheckBox")
        self.verticalLayout.addWidget(self.jediClickHandlerCheckBox)
        self.groupBox = QtWidgets.QGroupBox(parent=EditorMouseClickHandlerJediPage)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.groupBox)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(parent=self.groupBox)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.gotoClickEdit = QtWidgets.QLineEdit(parent=self.groupBox)
        self.gotoClickEdit.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.gotoClickEdit.setReadOnly(True)
        self.gotoClickEdit.setObjectName("gotoClickEdit")
        self.horizontalLayout.addWidget(self.gotoClickEdit)
        self.changeGotoButton = QtWidgets.QPushButton(parent=self.groupBox)
        self.changeGotoButton.setObjectName("changeGotoButton")
        self.horizontalLayout.addWidget(self.changeGotoButton)
        self.verticalLayout.addWidget(self.groupBox)
        spacerItem = QtWidgets.QSpacerItem(20, 147, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(EditorMouseClickHandlerJediPage)
        QtCore.QMetaObject.connectSlotsByName(EditorMouseClickHandlerJediPage)

    def retranslateUi(self, EditorMouseClickHandlerJediPage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("EditorMouseClickHandlerJediPage", "<b>Configure Jedi Mouse Click Handler Support</b>"))
        self.jediClickHandlerCheckBox.setToolTip(_translate("EditorMouseClickHandlerJediPage", "Select, whether the jedi mouse click handler support shall be enabled."))
        self.jediClickHandlerCheckBox.setText(_translate("EditorMouseClickHandlerJediPage", "Enable Mouse Click Handler"))
        self.groupBox.setTitle(_translate("EditorMouseClickHandlerJediPage", "Go To Definition"))
        self.label.setText(_translate("EditorMouseClickHandlerJediPage", "Click Sequence:"))
        self.gotoClickEdit.setToolTip(_translate("EditorMouseClickHandlerJediPage", "Shows the mouse click sequence"))
        self.changeGotoButton.setToolTip(_translate("EditorMouseClickHandlerJediPage", "Press to open a dialog to configure the mouse click sequence"))
        self.changeGotoButton.setText(_translate("EditorMouseClickHandlerJediPage", "Change..."))
