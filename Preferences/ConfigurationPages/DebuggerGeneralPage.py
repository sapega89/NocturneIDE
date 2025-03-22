# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Debugger General configuration page.
"""

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt, pyqtSlot
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtNetwork import QAbstractSocket, QHostAddress, QNetworkInterface
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QListWidgetItem

from eric7 import Preferences, Utilities
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricCompleters import EricDirCompleter, EricFileCompleter

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_DebuggerGeneralPage import Ui_DebuggerGeneralPage


class DebuggerGeneralPage(ConfigurationPageBase, Ui_DebuggerGeneralPage):
    """
    Class implementing the Debugger General configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("DebuggerGeneralPage")

        t = self.execLineEdit.whatsThis()
        if t:
            t += Utilities.getPercentReplacementHelp()
            self.execLineEdit.setWhatsThis(t)

        try:
            backends = ericApp().getObject("DebugServer").getSupportedLanguages()
            for backend in sorted(backends):
                self.passiveDbgBackendCombo.addItem(backend)
        except KeyError:
            self.passiveDbgGroup.setEnabled(False)

        t = self.consoleDbgEdit.whatsThis()
        if t:
            t += Utilities.getPercentReplacementHelp()
            self.consoleDbgEdit.setWhatsThis(t)

        self.consoleDbgCompleter = EricFileCompleter(self.consoleDbgEdit)
        self.dbgTranslationLocalCompleter = EricDirCompleter(
            self.dbgTranslationLocalEdit
        )

        self.interfaceSelectorComboBox.addItem(
            self.tr("All Network Interfaces (IPv4 & IPv6)"),
            "all",
        )
        self.interfaceSelectorComboBox.addItem(
            self.tr("All Network Interfaces (IPv4)"),
            "allv4",
        )
        self.interfaceSelectorComboBox.addItem(
            self.tr("All Network Interfaces (IPv6)"),
            "allv6",
        )
        self.interfaceSelectorComboBox.addItem(
            self.tr("Localhost (IPv4)"),
            "localv4",
        )
        self.interfaceSelectorComboBox.addItem(
            self.tr("Localhost (IPv6)"),
            "localv6",
        )
        self.interfaceSelectorComboBox.addItem(
            self.tr("Selected Interface"),
            "selected",
        )

        networkInterfaces = QNetworkInterface.allInterfaces()
        for networkInterface in networkInterfaces:
            addressEntries = networkInterface.addressEntries()
            if len(addressEntries) > 0:
                for addressEntry in addressEntries:
                    ip = addressEntry.ip().toString()
                    self.interfacesCombo.addItem(
                        "{0} ({1})".format(networkInterface.humanReadableName(), ip), ip
                    )

        # set initial values
        interface = Preferences.getDebugger("NetworkInterface")
        selectorIndex = self.interfaceSelectorComboBox.findData(interface)
        if selectorIndex != -1:
            self.interfaceSelectorComboBox.setCurrentIndex(selectorIndex)
        else:
            # Interface given by IP address
            self.interfaceSelectorComboBox.setCurrentIndex(
                self.interfaceSelectorComboBox.count() - 1
            )
            self.interfacesCombo.setCurrentIndex(
                self.interfacesCombo.findData(interface)
            )
        self.on_interfaceSelectorComboBox_currentIndexChanged(
            self.interfacesCombo.currentIndex()
        )
        self.serverPortStaticGroup.setChecked(
            Preferences.getDebugger("NetworkPortFixed")
        )
        self.serverPortIncrementCheckBox.setChecked(
            Preferences.getDebugger("NetworkPortIncrement")
        )
        self.serverPortSpinBox.setValue(Preferences.getDebugger("NetworkPort"))

        self.allowedHostsList.addItems(Preferences.getDebugger("AllowedHosts"))

        self.remoteDebuggerGroup.setChecked(Preferences.getDebugger("RemoteDbgEnabled"))
        self.hostLineEdit.setText(Preferences.getDebugger("RemoteHost"))
        self.execLineEdit.setText(Preferences.getDebugger("RemoteExecution"))
        self.remoteDebugClientEdit.setText(Preferences.getDebugger("RemoteDebugClient"))

        if self.passiveDbgGroup.isEnabled():
            self.passiveDbgGroup.setChecked(
                Preferences.getDebugger("PassiveDbgEnabled")
            )
            self.passiveDbgPortSpinBox.setValue(
                Preferences.getDebugger("PassiveDbgPort")
            )
            index = self.passiveDbgBackendCombo.findText(
                Preferences.getDebugger("PassiveDbgType")
            )
            if index == -1:
                index = 0
            self.passiveDbgBackendCombo.setCurrentIndex(index)
            self.passiveAutoContinueCheckBox.setChecked(
                Preferences.getDebugger("PassivAutoContinue")
            )

        self.debugEnvironReplaceCheckBox.setChecked(
            Preferences.getDebugger("DebugEnvironmentReplace")
        )
        self.debugEnvironEdit.setText(Preferences.getDebugger("DebugEnvironment"))
        self.automaticResetCheckBox.setChecked(
            Preferences.getDebugger("AutomaticReset")
        )
        self.debugAutoSaveScriptsCheckBox.setChecked(
            Preferences.getDebugger("Autosave")
        )
        self.consoleDebuggerGroup.setChecked(
            Preferences.getDebugger("ConsoleDbgEnabled")
        )
        self.consoleDbgEdit.setText(Preferences.getDebugger("ConsoleDbgCommand"))
        self.dbgPathTranslationGroup.setChecked(
            Preferences.getDebugger("PathTranslation")
        )
        self.dbgTranslationRemoteEdit.setText(
            Preferences.getDebugger("PathTranslationRemote")
        )
        self.dbgTranslationLocalEdit.setText(
            Preferences.getDebugger("PathTranslationLocal")
        )
        self.multiprocessCheckBox.setChecked(
            Preferences.getDebugger("MultiProcessEnabled")
        )
        self.debugThreeStateBreakPoint.setChecked(
            Preferences.getDebugger("ThreeStateBreakPoints")
        )
        self.intelligentBreakPointCheckBox.setChecked(
            Preferences.getDebugger("IntelligentBreakpoints")
        )
        self.recentFilesSpinBox.setValue(Preferences.getDebugger("RecentNumber"))
        self.exceptionBreakCheckBox.setChecked(Preferences.getDebugger("BreakAlways"))
        self.exceptionShellCheckBox.setChecked(
            Preferences.getDebugger("ShowExceptionInShell")
        )
        self.maxSizeSpinBox.setValue(Preferences.getDebugger("MaxVariableSize"))
        # Set the colours for debug viewer backgrounds
        self.previewMdl = PreviewModel()
        self.preView.setModel(self.previewMdl)
        self.colourChanged.connect(self.previewMdl.setColor)
        self.initColour(
            "BgColorNew",
            self.backgroundNewButton,
            Preferences.getDebugger,
            hasAlpha=True,
        )
        self.initColour(
            "BgColorChanged",
            self.backgroundChangedButton,
            Preferences.getDebugger,
            hasAlpha=True,
        )

        self.showOnlyCheckBox.setChecked(Preferences.getDebugger("ShowOnlyAsDefault"))

        self.autoViewSourcecodeCheckBox.setChecked(
            Preferences.getDebugger("AutoViewSourceCode")
        )

    def save(self):
        """
        Public slot to save the Debugger General (1) configuration.
        """
        Preferences.setDebugger(
            "RemoteDbgEnabled", self.remoteDebuggerGroup.isChecked()
        )
        Preferences.setDebugger("RemoteHost", self.hostLineEdit.text())
        Preferences.setDebugger("RemoteExecution", self.execLineEdit.text())
        Preferences.setDebugger("RemoteDebugClient", self.remoteDebugClientEdit.text())

        if self.passiveDbgGroup.isEnabled():
            Preferences.setDebugger(
                "PassiveDbgEnabled", self.passiveDbgGroup.isChecked()
            )
            Preferences.setDebugger(
                "PassiveDbgPort", self.passiveDbgPortSpinBox.value()
            )
            Preferences.setDebugger(
                "PassiveDbgType", self.passiveDbgBackendCombo.currentText()
            )
            Preferences.setDebugger(
                "PassivAutoContinue", self.passiveAutoContinueCheckBox.isChecked()
            )

        interface = self.interfaceSelectorComboBox.currentData()
        if interface == "selected":
            interface = self.interfacesCombo.currentData()
        Preferences.setDebugger("NetworkInterface", interface)
        Preferences.setDebugger(
            "NetworkPortFixed", self.serverPortStaticGroup.isChecked()
        )
        Preferences.setDebugger(
            "NetworkPortIncrement", self.serverPortIncrementCheckBox.isChecked()
        )
        Preferences.setDebugger("NetworkPort", self.serverPortSpinBox.value())

        allowedHosts = []
        for row in range(self.allowedHostsList.count()):
            allowedHosts.append(self.allowedHostsList.item(row).text())
        Preferences.setDebugger("AllowedHosts", allowedHosts)

        Preferences.setDebugger(
            "DebugEnvironmentReplace", self.debugEnvironReplaceCheckBox.isChecked()
        )
        Preferences.setDebugger("DebugEnvironment", self.debugEnvironEdit.text())
        Preferences.setDebugger(
            "AutomaticReset", self.automaticResetCheckBox.isChecked()
        )
        Preferences.setDebugger(
            "Autosave", self.debugAutoSaveScriptsCheckBox.isChecked()
        )
        Preferences.setDebugger(
            "ConsoleDbgEnabled", self.consoleDebuggerGroup.isChecked()
        )
        Preferences.setDebugger("ConsoleDbgCommand", self.consoleDbgEdit.text())
        Preferences.setDebugger(
            "PathTranslation", self.dbgPathTranslationGroup.isChecked()
        )
        Preferences.setDebugger(
            "PathTranslationRemote", self.dbgTranslationRemoteEdit.text()
        )
        Preferences.setDebugger(
            "PathTranslationLocal", self.dbgTranslationLocalEdit.text()
        )
        Preferences.setDebugger(
            "MultiProcessEnabled", self.multiprocessCheckBox.isChecked()
        )
        Preferences.setDebugger(
            "ThreeStateBreakPoints", self.debugThreeStateBreakPoint.isChecked()
        )
        Preferences.setDebugger(
            "IntelligentBreakpoints", self.intelligentBreakPointCheckBox.isChecked()
        )
        Preferences.setDebugger("RecentNumber", self.recentFilesSpinBox.value())
        Preferences.setDebugger("BreakAlways", self.exceptionBreakCheckBox.isChecked())
        Preferences.setDebugger(
            "ShowExceptionInShell", self.exceptionShellCheckBox.isChecked()
        )
        Preferences.setDebugger("MaxVariableSize", self.maxSizeSpinBox.value())
        # Store background colors for debug viewer
        self.saveColours(Preferences.setDebugger)

        Preferences.setDebugger("ShowOnlyAsDefault", self.showOnlyCheckBox.isChecked())
        Preferences.setDebugger(
            "AutoViewSourceCode", self.autoViewSourcecodeCheckBox.isChecked()
        )

    @pyqtSlot(int)
    def on_interfaceSelectorComboBox_currentIndexChanged(self, index):
        """
        Private slot to handle the selection of a network interface type.

        @param index index of the selected entry
        @type int
        """
        self.interfacesCombo.setEnabled(
            index == self.interfaceSelectorComboBox.count() - 1
        )

    @pyqtSlot(QListWidgetItem, QListWidgetItem)
    def on_allowedHostsList_currentItemChanged(self, current, _previous):
        """
        Private method to set the state of the edit and delete button.

        @param current new current item
        @type QListWidgetItem
        @param _previous previous current item (unused)
        @type QListWidgetItem
        """
        self.editAllowedHostButton.setEnabled(current is not None)
        self.deleteAllowedHostButton.setEnabled(current is not None)

    @pyqtSlot()
    def on_addAllowedHostButton_clicked(self):
        """
        Private slot called to add a new allowed host.
        """
        allowedHost, ok = QInputDialog.getText(
            None,
            self.tr("Add allowed host"),
            self.tr("Enter the IP address of an allowed host"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and allowedHost:
            if QHostAddress(allowedHost).protocol() in [
                QAbstractSocket.NetworkLayerProtocol.IPv4Protocol,
                QAbstractSocket.NetworkLayerProtocol.IPv6Protocol,
            ]:
                self.allowedHostsList.addItem(allowedHost)
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Add allowed host"),
                    self.tr(
                        """<p>The entered address <b>{0}</b> is not"""
                        """ a valid IP v4 or IP v6 address."""
                        """ Aborting...</p>"""
                    ).format(allowedHost),
                )

    @pyqtSlot()
    def on_deleteAllowedHostButton_clicked(self):
        """
        Private slot called to delete an allowed host.
        """
        self.allowedHostsList.takeItem(self.allowedHostsList.currentRow())

    @pyqtSlot()
    def on_editAllowedHostButton_clicked(self):
        """
        Private slot called to edit an allowed host.
        """
        allowedHost = self.allowedHostsList.currentItem().text()
        allowedHost, ok = QInputDialog.getText(
            None,
            self.tr("Edit allowed host"),
            self.tr("Enter the IP address of an allowed host"),
            QLineEdit.EchoMode.Normal,
            allowedHost,
        )
        if ok and allowedHost:
            if QHostAddress(allowedHost).protocol() in [
                QAbstractSocket.NetworkLayerProtocol.IPv4Protocol,
                QAbstractSocket.NetworkLayerProtocol.IPv6Protocol,
            ]:
                self.allowedHostsList.currentItem().setText(allowedHost)
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Edit allowed host"),
                    self.tr(
                        """<p>The entered address <b>{0}</b> is not"""
                        """ a valid IP v4 or IP v6 address."""
                        """ Aborting...</p>"""
                    ).format(allowedHost),
                )

    @pyqtSlot(bool)
    def on_passiveDbgGroup_toggled(self, checked):
        """
        Private slot to handle a change of the checked state of the passive debugging
        option.

        @param checked checked state
        @type bool
        """
        if checked:
            # Only one of passive debugging or remote debugging or none must be
            # selected.
            self.remoteDebuggerGroup.setChecked(False)

    @pyqtSlot(bool)
    def on_remoteDebuggerGroup_toggled(self, checked):
        """
        Private slot to handle a change of the checked state of the remote debugging
        option.

        @param checked checked state
        @type bool
        """
        if checked:
            # Only one of passive debugging or remote debugging or none must be
            # selected.
            self.passiveDbgGroup.setChecked(False)


class PreviewModel(QAbstractItemModel):
    """
    Class to show an example of the selected background colours for the debug
    viewer.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.bgColorNew = QBrush(QColor("#FFFFFF"))
        self.bgColorChanged = QBrush(QColor("#FFFFFF"))

    def setColor(self, key, bgcolour):
        """
        Public slot to update the background colour indexed by key.

        @param key the name of background
        @type str
        @param bgcolour the new background colour
        @type QColor
        """
        if key == "BgColorNew":
            self.bgColorNew = QBrush(bgcolour)
        else:
            self.bgColorChanged = QBrush(bgcolour)

        # Force update of preview view
        idxStart = self.index(0, 0, QModelIndex())
        idxEnd = self.index(0, 2, QModelIndex())
        self.dataChanged.emit(idxStart, idxEnd)

    def index(self, row, column, parent=None):
        """
        Public Qt slot to get the index of item at row:column of parent.

        @param row number of rows
        @type int
        @param column number of columns
        @type int
        @param parent the model parent (defaults to None)
        @type QModelIndex (optional)
        @return new model index for child
        @rtype QModelIndex
        """
        if parent is None:
            parent = QModelIndex()

        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        return self.createIndex(row, column, None)

    def parent(self, _child):
        """
        Public Qt slot to get the parent of the given child.

        @param _child the model child node (unused)
        @type QModelIndex
        @return new model index for parent
        @rtype QModelIndex
        """
        return QModelIndex()

    def columnCount(self, parent=None):  # noqa: U100
        """
        Public Qt slot to get the column count.

        @param parent the model parent (defaults to None) (unused)
        @type QModelIndex (optional)
        @return number of columns
        @rtype int
        """
        return 1

    def rowCount(self, parent=None):  # noqa: U100
        """
        Public Qt slot to get the row count.

        @param parent the model parent (defaults to None) (unused)
        @type QModelIndex (optional)
        @return number of rows
        @rtype int
        """
        return 4

    def flags(self, _index):
        """
        Public Qt slot to get the item flags.

        @param _index of item (unused)
        @type QModelIndex
        @return item flags
        @rtype QtCore.Qt.ItemFlag
        """
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Public Qt slot get the role data of item.

        @param index the model index
        @type QModelIndex
        @param role the requested data role
        @type QtCore.Qt.ItemDataRole
        @return role data of item
        @rtype str, QBrush or None
        """
        if role == Qt.ItemDataRole.DisplayRole:
            return self.tr("Variable Name")
        elif role == Qt.ItemDataRole.BackgroundRole:
            if index.row() >= 2:
                return self.bgColorChanged
            else:
                return self.bgColorNew

        return None


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    return DebuggerGeneralPage()


#
# eflag: noqa = M822
