# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/EditorMouseClickHandlerPage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_EditorMouseClickHandlerPage(object):
    def setupUi(self, EditorMouseClickHandlerPage):
        EditorMouseClickHandlerPage.setObjectName("EditorMouseClickHandlerPage")
        EditorMouseClickHandlerPage.resize(506, 246)
        self.verticalLayout = QtWidgets.QVBoxLayout(EditorMouseClickHandlerPage)
        self.verticalLayout.setObjectName("verticalLayout")
        self.headerLabel = QtWidgets.QLabel(parent=EditorMouseClickHandlerPage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout.addWidget(self.headerLabel)
        self.line6 = QtWidgets.QFrame(parent=EditorMouseClickHandlerPage)
        self.line6.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line6.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line6.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line6.setObjectName("line6")
        self.verticalLayout.addWidget(self.line6)
        self.mcEnabledCheckBox = QtWidgets.QCheckBox(parent=EditorMouseClickHandlerPage)
        self.mcEnabledCheckBox.setObjectName("mcEnabledCheckBox")
        self.verticalLayout.addWidget(self.mcEnabledCheckBox)
        spacerItem = QtWidgets.QSpacerItem(456, 51, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(EditorMouseClickHandlerPage)
        QtCore.QMetaObject.connectSlotsByName(EditorMouseClickHandlerPage)

    def retranslateUi(self, EditorMouseClickHandlerPage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("EditorMouseClickHandlerPage", "<b>Configure Mouse Click Handler Support</b>"))
        self.mcEnabledCheckBox.setToolTip(_translate("EditorMouseClickHandlerPage", "Select this to enable support for mouse click handlers"))
        self.mcEnabledCheckBox.setWhatsThis(_translate("EditorMouseClickHandlerPage", "<b>Mouse Click Handlers Enabled</b><p>Select to enable support for mouse click handlers. Individual mouse click handlers may be configured on subordinate pages, if such have been installed and registered. This is usually done by plug-ins.</p>"))
        self.mcEnabledCheckBox.setText(_translate("EditorMouseClickHandlerPage", "Mouse Click Handlers Enabled"))
