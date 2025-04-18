# Form implementation generated from reading ui file 'src/eric7/PluginManager/PluginUninstallDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_PluginUninstallDialog(object):
    def setupUi(self, PluginUninstallDialog):
        PluginUninstallDialog.setObjectName("PluginUninstallDialog")
        PluginUninstallDialog.resize(400, 450)
        self.verticalLayout = QtWidgets.QVBoxLayout(PluginUninstallDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_3 = QtWidgets.QLabel(parent=PluginUninstallDialog)
        self.label_3.setObjectName("label_3")
        self.verticalLayout.addWidget(self.label_3)
        self.pluginDirectoryCombo = QtWidgets.QComboBox(parent=PluginUninstallDialog)
        self.pluginDirectoryCombo.setObjectName("pluginDirectoryCombo")
        self.verticalLayout.addWidget(self.pluginDirectoryCombo)
        self.label_2 = QtWidgets.QLabel(parent=PluginUninstallDialog)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.pluginsList = QtWidgets.QListWidget(parent=PluginUninstallDialog)
        self.pluginsList.setAlternatingRowColors(True)
        self.pluginsList.setObjectName("pluginsList")
        self.verticalLayout.addWidget(self.pluginsList)
        self.keepConfigurationCheckBox = QtWidgets.QCheckBox(parent=PluginUninstallDialog)
        self.keepConfigurationCheckBox.setObjectName("keepConfigurationCheckBox")
        self.verticalLayout.addWidget(self.keepConfigurationCheckBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=PluginUninstallDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(PluginUninstallDialog)
        QtCore.QMetaObject.connectSlotsByName(PluginUninstallDialog)
        PluginUninstallDialog.setTabOrder(self.pluginDirectoryCombo, self.pluginsList)
        PluginUninstallDialog.setTabOrder(self.pluginsList, self.keepConfigurationCheckBox)

    def retranslateUi(self, PluginUninstallDialog):
        _translate = QtCore.QCoreApplication.translate
        PluginUninstallDialog.setWindowTitle(_translate("PluginUninstallDialog", "Plugin Uninstallation"))
        self.label_3.setText(_translate("PluginUninstallDialog", "Plugin directory:"))
        self.pluginDirectoryCombo.setToolTip(_translate("PluginUninstallDialog", "Select the plugin area containing the plugin to uninstall"))
        self.label_2.setText(_translate("PluginUninstallDialog", "Plugins:"))
        self.pluginsList.setToolTip(_translate("PluginUninstallDialog", "Check the plugins to be uninstalled"))
        self.pluginsList.setSortingEnabled(True)
        self.keepConfigurationCheckBox.setToolTip(_translate("PluginUninstallDialog", "Select to keep the configuration data"))
        self.keepConfigurationCheckBox.setText(_translate("PluginUninstallDialog", "Keep configuration data"))
