# Form implementation generated from reading ui file 'src/eric7/WebBrowser/GreaseMonkey/GreaseMonkeyConfiguration/GreaseMonkeyConfigurationScriptInfoDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_GreaseMonkeyConfigurationScriptInfoDialog(object):
    def setupUi(self, GreaseMonkeyConfigurationScriptInfoDialog):
        GreaseMonkeyConfigurationScriptInfoDialog.setObjectName("GreaseMonkeyConfigurationScriptInfoDialog")
        GreaseMonkeyConfigurationScriptInfoDialog.resize(550, 500)
        GreaseMonkeyConfigurationScriptInfoDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(GreaseMonkeyConfigurationScriptInfoDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.iconLabel = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.iconLabel.setMinimumSize(QtCore.QSize(48, 48))
        self.iconLabel.setText("Icon")
        self.iconLabel.setObjectName("iconLabel")
        self.horizontalLayout.addWidget(self.iconLabel)
        self.label_8 = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.label_8.setObjectName("label_8")
        self.horizontalLayout.addWidget(self.label_8)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.nameLabel = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.nameLabel.setText("")
        self.nameLabel.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.nameLabel.setObjectName("nameLabel")
        self.gridLayout.addWidget(self.nameLabel, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.versionLabel = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.versionLabel.setText("")
        self.versionLabel.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.versionLabel.setObjectName("versionLabel")
        self.gridLayout.addWidget(self.versionLabel, 1, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.urlLabel = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.urlLabel.setText("")
        self.urlLabel.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.urlLabel.setObjectName("urlLabel")
        self.gridLayout.addWidget(self.urlLabel, 2, 1, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)
        self.startAtLabel = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.startAtLabel.setText("")
        self.startAtLabel.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse|QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.startAtLabel.setObjectName("startAtLabel")
        self.gridLayout.addWidget(self.startAtLabel, 3, 1, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.label_5.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)
        self.descriptionBrowser = QtWidgets.QTextBrowser(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.descriptionBrowser.setObjectName("descriptionBrowser")
        self.gridLayout.addWidget(self.descriptionBrowser, 4, 1, 1, 1)
        self.label_6 = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.label_6.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 5, 0, 1, 1)
        self.runsAtBrowser = QtWidgets.QTextBrowser(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.runsAtBrowser.setObjectName("runsAtBrowser")
        self.gridLayout.addWidget(self.runsAtBrowser, 5, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.label_7.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 6, 0, 1, 1)
        self.doesNotRunAtBrowser = QtWidgets.QTextBrowser(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.doesNotRunAtBrowser.setObjectName("doesNotRunAtBrowser")
        self.gridLayout.addWidget(self.doesNotRunAtBrowser, 6, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.showScriptSourceButton = QtWidgets.QPushButton(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.showScriptSourceButton.setObjectName("showScriptSourceButton")
        self.horizontalLayout_2.addWidget(self.showScriptSourceButton)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=GreaseMonkeyConfigurationScriptInfoDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.buttonBox.setObjectName("buttonBox")
        self.horizontalLayout_2.addWidget(self.buttonBox)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(GreaseMonkeyConfigurationScriptInfoDialog)
        self.buttonBox.accepted.connect(GreaseMonkeyConfigurationScriptInfoDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(GreaseMonkeyConfigurationScriptInfoDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(GreaseMonkeyConfigurationScriptInfoDialog)
        GreaseMonkeyConfigurationScriptInfoDialog.setTabOrder(self.descriptionBrowser, self.runsAtBrowser)
        GreaseMonkeyConfigurationScriptInfoDialog.setTabOrder(self.runsAtBrowser, self.doesNotRunAtBrowser)
        GreaseMonkeyConfigurationScriptInfoDialog.setTabOrder(self.doesNotRunAtBrowser, self.showScriptSourceButton)
        GreaseMonkeyConfigurationScriptInfoDialog.setTabOrder(self.showScriptSourceButton, self.buttonBox)

    def retranslateUi(self, GreaseMonkeyConfigurationScriptInfoDialog):
        _translate = QtCore.QCoreApplication.translate
        self.label_8.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "<h2>GreaseMonkey Script Details</h2>"))
        self.label.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "Name:"))
        self.label_2.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "Version:"))
        self.label_3.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "URL:"))
        self.label_4.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "Start at:"))
        self.label_5.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "Description:"))
        self.label_6.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "Runs at:"))
        self.label_7.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "Does not run at:"))
        self.showScriptSourceButton.setToolTip(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "Press to open an editor with the script\'s source"))
        self.showScriptSourceButton.setText(_translate("GreaseMonkeyConfigurationScriptInfoDialog", "Show source code of script"))
