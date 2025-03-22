# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter some user data.
"""

import contextlib
import os

from configparser import ConfigParser

from PyQt6.QtCore import QEvent, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import OSUtilities

from .HgUserConfigHostFingerprintDialog import HgUserConfigHostFingerprintDialog
from .HgUserConfigHostMinimumProtocolDialog import HgUserConfigHostMinimumProtocolDialog
from .HgUtilities import getConfigPath
from .Ui_HgUserConfigDialog import Ui_HgUserConfigDialog


class HgUserConfigDialog(QDialog, Ui_HgUserConfigDialog):
    """
    Class implementing a dialog to enter some user data.
    """

    def __init__(self, version=(0, 0, 0), parent=None):
        """
        Constructor

        @param version Mercurial version info
        @type tuple of three integers
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__version = version

        self.__minimumProtocols = {
            "tls1.0": self.tr("TLS 1.0"),
            "tls1.1": self.tr("TLS 1.1"),
            "tls1.2": self.tr("TLS 1.2"),
        }

        self.lfUserCachePicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        if OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
            self.lfUserCachePicker.setDefaultDirectory(
                os.path.expanduser("~/.cache/largefiles")
            )
        elif OSUtilities.isMacPlatform():
            self.lfUserCachePicker.setDefaultDirectory(
                os.path.expanduser("~/Library/Caches/largefiles")
            )
        else:
            self.lfUserCachePicker.setDefaultDirectory(
                os.path.expanduser("~\\AppData\\Local\\largefiles")
            )

        self.fpAddButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.fpDeleteButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.fpEditButton.setIcon(EricPixmapCache.getIcon("edit"))

        self.protocolAddButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.protocolDeleteButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.protocolEditButton.setIcon(EricPixmapCache.getIcon("edit"))

        self.minimumProtocolComboBox.addItem(self.tr("Default"), "")
        for protocol in sorted(self.__minimumProtocols):
            self.minimumProtocolComboBox.addItem(
                self.__minimumProtocols[protocol], protocol
            )

        self.fingerprintsList.headerItem().setText(
            self.fingerprintsList.columnCount(), ""
        )
        self.protocolsList.headerItem().setText(self.protocolsList.columnCount(), "")

        self.tabWidget.setCurrentIndex(0)

        self.__editor = None

        self.__config = None
        self.readUserConfig()

        self.__updateFingerprintsButtons()
        self.__updateProtocolsButtons()

    def writeUserConfig(self):
        """
        Public method to write the user configuration file.
        """
        if self.__config is None:
            self.__config = ConfigParser()

        ###################################################################
        ## ui section
        ###################################################################
        if "ui" not in self.__config:
            self.__config["ui"] = {}
        self.__config["ui"]["username"] = "{0} <{1}>".format(
            self.userNameEdit.text(),
            self.emailEdit.text(),
        )

        ###################################################################
        ## extensions section
        ###################################################################
        if "extensions" not in self.__config:
            self.__config["extensions"] = {}

        if self.gpgCheckBox.isChecked():
            self.__config["extensions"]["gpg"] = ""
        else:
            if "gpg" in self.__config["extensions"]:
                del self.__config["extensions"]["gpg"]
            self.__config["extensions"]["#gpg"] = ""

        if self.queuesCheckBox.isChecked():
            self.__config["extensions"]["mq"] = ""
        else:
            if "mq" in self.__config["extensions"]:
                del self.__config["extensions"]["mq"]
            self.__config["extensions"]["#mq"] = ""

        if self.rebaseCheckBox.isChecked():
            self.__config["extensions"]["rebase"] = ""
        else:
            if "rebase" in self.__config["extensions"]:
                del self.__config["extensions"]["rebase"]
            self.__config["extensions"]["#rebase"] = ""

        if self.histeditCheckBox.isChecked():
            self.__config["extensions"]["histedit"] = ""
        else:
            if "histedit" in self.__config["extensions"]:
                del self.__config["extensions"]["histedit"]
            self.__config["extensions"]["#histedit"] = ""

        if self.largefilesCheckBox.isChecked():
            self.__config["extensions"]["largefiles"] = ""
            ###############################################################
            ## largefiles section
            ###############################################################
            if "largefiles" not in self.__config:
                self.__config["largefiles"] = {}
            self.__config["largefiles"]["minsize"] = str(self.lfFileSizeSpinBox.value())
            lfFilePatterns = self.lfFilePatternsEdit.text()
            if lfFilePatterns:
                self.__config["largefiles"]["patterns"] = lfFilePatterns
            elif "patterns" in self.__config["largefiles"]:
                del self.__config["largefiles"]["patterns"]
            lfUserCache = self.lfUserCachePicker.text()
            if lfUserCache:
                self.__config["largefiles"]["usercache"] = lfUserCache
            elif "usercache" in self.__config["largefiles"]:
                del self.__config["largefiles"]["usercache"]
        else:
            if "largefiles" in self.__config["extensions"]:
                del self.__config["extensions"]["largefiles"]
            self.__config["extensions"]["#largefiles"] = ""

        if self.closeheadCheckBox.isChecked():
            self.__config["extensions"]["closehead"] = ""
        else:
            if "closehead" in self.__config["extensions"]:
                del self.__config["extensions"]["closehead"]
            self.__config["extensions"]["#closehead"] = ""

        if self.fastexportCheckBox.isChecked():
            self.__config["extensions"]["fastexport"] = ""
        else:
            if "fastexport" in self.__config["extensions"]:
                del self.__config["extensions"]["fastexport"]
            self.__config["extensions"]["#fastexport"] = ""

        if self.uncommitCheckBox.isChecked():
            self.__config["extensions"]["uncommit"] = ""
        else:
            if "uncommit" in self.__config["extensions"]:
                del self.__config["extensions"]["uncommit"]
            self.__config["extensions"]["#uncommit"] = ""

        ###################################################################
        ## http_proxy section
        ###################################################################
        if self.proxyHostEdit.text():
            self.__config["http_proxy"] = {
                "host": self.proxyHostEdit.text(),
                "user": self.proxyUserEdit.text(),
                "passwd": self.proxyPasswordEdit.text(),
            }
            if self.proxyBypassEdit.text():
                self.__config["http_proxy"]["no"] = self.proxyBypassEdit.text()
        else:
            if "http_proxy" in self.__config:
                del self.__config["http_proxy"]

        ###################################################################
        ## hostfingerprints/hostsecurity section
        ###################################################################
        #
        # hostsecurity section
        #
        if "hostsecurity" not in self.__config:
            self.__config["hostsecurity"] = {}

        if self.fingerprintsList.topLevelItemCount() > 0:
            self.__clearFingerprints()
            fingerprints = self.__assembleFingerprints()
            for host in fingerprints:
                key = "{0}:fingerprints".format(host)
                self.__config["hostsecurity"][key] = ", ".join(fingerprints[host])
        else:
            self.__clearFingerprints()

        disabletls10warning = (
            "true" if self.disableTls10WarningCheckBox.isChecked() else "false"
        )
        self.__config["hostsecurity"]["disabletls10warning"] = disabletls10warning

        if self.minimumProtocolComboBox.currentIndex() == 0:
            self.__config.remove_option("hostsecurity", "minimumprotocol")
        else:
            minimumProtocol = self.minimumProtocolComboBox.itemData(
                self.minimumProtocolComboBox.currentIndex()
            )
            self.__config["hostsecurity"]["minimumprotocol"] = minimumProtocol

        if self.protocolsList.topLevelItemCount() > 0:
            self.__clearMinimumProtocols()
            minimumProtocols = self.__assembleMinimumProtocols()
            for host in minimumProtocols:
                key = "{0}:minimumprotocol".format(host)
                self.__config["hostsecurity"][key] = minimumProtocols[host]
        else:
            self.__clearMinimumProtocols()

        if len(self.__config.options("hostsecurity")) == 0:
            del self.__config["hostsecurity"]
        ###################################################################

        cfgFile = getConfigPath()
        with open(cfgFile, "w") as configFile:
            self.__config.write(configFile)

    def readUserConfig(self):
        """
        Public method to read the user configuration file.
        """
        cfgFile = getConfigPath()

        self.__config = ConfigParser(delimiters=("=",))
        if self.__config.read(cfgFile):
            # step 1: extract user name and email
            with contextlib.suppress(KeyError):
                username = self.__config["ui"]["username"].strip()
                if "<" in username and username.endswith(">"):
                    name, email = username[:-1].rsplit("<", 1)
                else:
                    name = username
                    email = ""
                self.userNameEdit.setText(name.strip())
                self.emailEdit.setText(email.strip())

            # step 2: extract extensions information
            if "extensions" in self.__config:
                self.gpgCheckBox.setChecked("gpg" in self.__config["extensions"])
                self.queuesCheckBox.setChecked("mq" in self.__config["extensions"])
                self.rebaseCheckBox.setChecked("rebase" in self.__config["extensions"])
                self.largefilesCheckBox.setChecked(
                    "largefiles" in self.__config["extensions"]
                )
                self.histeditCheckBox.setChecked(
                    "histedit" in self.__config["extensions"]
                )
                self.closeheadCheckBox.setChecked(
                    "closehead" in self.__config["extensions"]
                )
                self.fastexportCheckBox.setChecked(
                    "fastexport" in self.__config["extensions"]
                )
                self.uncommitCheckBox.setChecked(
                    "uncommit" in self.__config["extensions"]
                )

            # step 3: extract large files information
            if "largefiles" in self.__config:
                if "minsize" in self.__config["largefiles"]:
                    self.lfFileSizeSpinBox.setValue(
                        self.__config.getint("largefiles", "minsize")
                    )
                if "patterns" in self.__config["largefiles"]:
                    self.lfFilePatternsEdit.setText(
                        self.__config["largefiles"]["patterns"]
                    )
                if "usercache" in self.__config["largefiles"]:
                    self.lfUserCachePicker.setText(
                        self.__config["largefiles"]["usercache"]
                    )

            # step 4: extract http proxy information
            if "http_proxy" in self.__config:
                if "host" in self.__config["http_proxy"]:
                    self.proxyHostEdit.setText(self.__config["http_proxy"]["host"])
                if "user" in self.__config["http_proxy"]:
                    self.proxyUserEdit.setText(self.__config["http_proxy"]["user"])
                if "passwd" in self.__config["http_proxy"]:
                    self.proxyPasswordEdit.setText(
                        self.__config["http_proxy"]["passwd"]
                    )
                if "no" in self.__config["http_proxy"]:
                    self.proxyBypassEdit.setText(self.__config["http_proxy"]["no"])

            # step 5: extract hostsecurity fingerprints
            if "hostsecurity" in self.__config:
                for key in self.__config.options("hostsecurity"):
                    if key.endswith(":fingerprints"):
                        host = key.replace(":fingerprints", "")
                        fingerprints = self.__config["hostsecurity"][key].split(",")
                        for fingerprint in fingerprints:
                            QTreeWidgetItem(
                                self.fingerprintsList,
                                [host, fingerprint.replace("\\", "").strip()],
                            )

                    elif key == "disabletls10warning":
                        self.disableTls10WarningCheckBox.setChecked(
                            self.__config.getboolean(
                                "hostsecurity", "disabletls10warning"
                            )
                        )

                    elif key == "minimumprotocol":
                        minimumProtocol = self.__config["hostsecurity"][key]
                        index = self.minimumProtocolComboBox.findData(minimumProtocol)
                        if index == -1:
                            index = 0
                        self.minimumProtocolComboBox.setCurrentIndex(index)

                    elif key.endswith(":minimumprotocol"):
                        host = key.replace(":minimumprotocol", "")
                        protocol = self.__config["hostsecurity"][key].strip()
                        if protocol in self.__minimumProtocols:
                            itm = QTreeWidgetItem(
                                self.protocolsList,
                                [host, self.__minimumProtocols[protocol]],
                            )
                            itm.setData(1, Qt.ItemDataRole.UserRole, protocol)

            self.__finalizeFingerprintsColumns()
            self.__finalizeProtocolsColumns()

    @pyqtSlot()
    def accept(self):
        """
        Public slot to accept the dialog.
        """
        self.writeUserConfig()

        super().accept()

    def __clearDialog(self):
        """
        Private method to clear the data of the dialog.
        """
        # User tab
        self.userNameEdit.clear()
        self.emailEdit.clear()

        # Extensions tab
        self.gpgCheckBox.setChecked(False)
        self.queuesCheckBox.setChecked(False)
        self.rebaseCheckBox.setChecked(False)
        self.histeditCheckBox.setChecked(False)
        self.closeheadCheckBox.setChecked(False)
        self.fastexportCheckBox.setChecked(False)
        self.uncommitCheckBox.setChecked(False)
        self.largefilesCheckBox.setChecked(False)

        self.lfFileSizeSpinBox.setValue(10)
        self.lfFilePatternsEdit.clear()
        self.lfUserCachePicker.clear()

        # Network tab
        self.proxyHostEdit.clear()
        self.proxyUserEdit.clear()
        self.proxyPasswordEdit.clear()
        self.proxyBypassEdit.clear()

        # Security tab
        self.fingerprintsList.clear()
        self.__finalizeFingerprintsColumns()
        self.__updateFingerprintsButtons()

        self.protocolsList.clear()
        self.__finalizeProtocolsColumns()
        self.__updateProtocolsButtons()

    #######################################################################
    ## Methods and slots for the host fingerprint handling below
    #######################################################################

    def __clearFingerprints(self):
        """
        Private method to clear the fingerprints from the hostsecurity section.
        """
        if "hostsecurity" in self.__config:
            for key in self.__config.options("hostsecurity"):
                if key.endswith(":fingerprints"):
                    self.__config.remove_option("hostsecurity", key)

    def __assembleFingerprints(self):
        """
        Private method to assemble a list of host fingerprints.

        @return dictionary with list of fingerprints per host
        @rtype dict with str as key and list of str as value
        """
        hostFingerprints = {}
        for row in range(self.fingerprintsList.topLevelItemCount()):
            itm = self.fingerprintsList.topLevelItem(row)
            host = itm.text(0)
            fingerprint = itm.text(1)
            if host in hostFingerprints:
                hostFingerprints[host].append(fingerprint)
            else:
                hostFingerprints[host] = [fingerprint]
        return hostFingerprints

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_fingerprintsList_currentItemChanged(self, _current, _previous):
        """
        Private slot handling a change of the current fingerprints item.

        @param _current reference to the current item (unused)
        @type QTreeWidgetItem
        @param _previous reference to the previous current item (unused)
        @type QTreeWidgetItem
        """
        self.__updateFingerprintsButtons()

    @pyqtSlot()
    def on_fpAddButton_clicked(self):
        """
        Private slot to add a fingerprints entry.
        """
        dlg = HgUserConfigHostFingerprintDialog(parent=self, version=self.__version)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            host, fingerprint = dlg.getData()
            itm = QTreeWidgetItem(self.fingerprintsList, [host, fingerprint])
            self.__finalizeFingerprintsColumns()
            self.fingerprintsList.setCurrentItem(itm)
            self.fingerprintsList.scrollToItem(itm)

    @pyqtSlot()
    def on_fpDeleteButton_clicked(self):
        """
        Private slot to delete the current fingerprints item.
        """
        itm = self.fingerprintsList.currentItem()
        if itm is not None:
            host = itm.text(0)
            yes = EricMessageBox.yesNo(
                self,
                self.tr("Delete Host Fingerprint"),
                self.tr(
                    """<p>Shall the fingerprint for host <b>{0}</b>"""
                    """ really be deleted?</p>"""
                ).format(host),
            )
            if yes:
                self.fingerprintsList.takeTopLevelItem(
                    self.fingerprintsList.indexOfTopLevelItem(itm)
                )
                del itm
                self.__finalizeFingerprintsColumns()

    @pyqtSlot()
    def on_fpEditButton_clicked(self):
        """
        Private slot to edit the current fingerprints item.
        """
        itm = self.fingerprintsList.currentItem()
        if itm is not None:
            host = itm.text(0)
            fingerprint = itm.text(1)
            dlg = HgUserConfigHostFingerprintDialog(
                parent=self, host=host, fingerprint=fingerprint, version=self.__version
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                host, fingerprint = dlg.getData()
                itm.setText(0, host)
                itm.setText(1, fingerprint)
                self.__finalizeFingerprintsColumns()
                self.fingerprintsList.scrollToItem(itm)

    def __finalizeFingerprintsColumns(self):
        """
        Private method to resize and sort the host fingerprints columns.
        """
        for col in range(self.fingerprintsList.columnCount()):
            self.fingerprintsList.resizeColumnToContents(col)
        self.fingerprintsList.sortItems(0, Qt.SortOrder.AscendingOrder)

    def __updateFingerprintsButtons(self):
        """
        Private slot to update the host fingerprints edit buttons.
        """
        enable = self.fingerprintsList.currentItem() is not None
        self.fpDeleteButton.setEnabled(enable)
        self.fpEditButton.setEnabled(enable)

    #######################################################################
    ## Methods and slots for the host minimum protocol handling below
    #######################################################################

    def __clearMinimumProtocols(self):
        """
        Private method to clear the minimum protocols from the hostsecurity
        section.
        """
        if "hostsecurity" in self.__config:
            for key in self.__config.options("hostsecurity"):
                if key.endswith(":minimumprotocol"):
                    self.__config.remove_option("hostsecurity", key)

    def __assembleMinimumProtocols(self):
        """
        Private method to assemble a list of host minimum protocols.

        @return dictionary with list of minimum protocol per host
        @rtype dict with str as key and str as value
        """
        minimumProtocols = {}
        for row in range(self.protocolsList.topLevelItemCount()):
            itm = self.protocolsList.topLevelItem(row)
            host = itm.text(0)
            minimumProtocol = itm.data(1, Qt.ItemDataRole.UserRole)
            minimumProtocols[host] = minimumProtocol
        return minimumProtocols

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_protocolsList_currentItemChanged(self, _current, _previous):
        """
        Private slot handling a change of the current minimum protocol item.

        @param _current reference to the current item (unused)
        @type QTreeWidgetItem
        @param _previous reference to the previous current item (unused)
        @type QTreeWidgetItem
        """
        self.__updateProtocolsButtons()

    @pyqtSlot()
    def on_protocolAddButton_clicked(self):
        """
        Private slot to add a minimum protocol entry.
        """
        dlg = HgUserConfigHostMinimumProtocolDialog(
            self.__minimumProtocols, parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            host, protocol = dlg.getData()
            itm = QTreeWidgetItem(
                self.protocolsList, [host, self.__minimumProtocols[protocol]]
            )
            itm.setData(1, Qt.ItemDataRole.UserRole, protocol)
            self.__finalizeProtocolsColumns()
            self.protocolsList.setCurrentItem(itm)
            self.protocolsList.scrollToItem(itm)

    @pyqtSlot()
    def on_protocolDeleteButton_clicked(self):
        """
        Private slot to delete the current minimum protocol item.
        """
        itm = self.protocolsList.currentItem()
        if itm is not None:
            host = itm.text(0)
            yes = EricMessageBox.yesNo(
                self,
                self.tr("Delete Host Minimum Protocol"),
                self.tr(
                    """<p>Shall the minimum protocol entry for host"""
                    """ <b>{0}</b> really be deleted?</p>"""
                ).format(host),
            )
            if yes:
                self.protocolsList.takeTopLevelItem(
                    self.protocolsList.indexOfTopLevelItem(itm)
                )
                del itm
                self.__finalizeProtocolsColumns()

    @pyqtSlot()
    def on_protocolEditButton_clicked(self):
        """
        Private slot to edit the current minimum protocol item.
        """
        itm = self.protocolsList.currentItem()
        if itm is not None:
            host = itm.text(0)
            protocol = itm.data(1, Qt.ItemDataRole.UserRole)
            dlg = HgUserConfigHostMinimumProtocolDialog(
                self.__minimumProtocols, parent=self, host=host, protocol=protocol
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                host, protocol = dlg.getData()
                itm.setText(0, host)
                itm.setText(1, self.__minimumProtocols[protocol])
                itm.setData(1, Qt.ItemDataRole.UserRole, protocol)
                self.__finalizeProtocolsColumns()
                self.protocolsList.scrollToItem(itm)

    def __finalizeProtocolsColumns(self):
        """
        Private method to resize and sort the host fingerprints columns.
        """
        for col in range(self.protocolsList.columnCount()):
            self.protocolsList.resizeColumnToContents(col)
        self.protocolsList.sortItems(0, Qt.SortOrder.AscendingOrder)

    def __updateProtocolsButtons(self):
        """
        Private slot to update the host minimum protocol edit buttons.
        """
        enable = self.protocolsList.currentItem() is not None
        self.protocolDeleteButton.setEnabled(enable)
        self.protocolEditButton.setEnabled(enable)

    #######################################################################
    ## Slot to edit the user configuration in an editor below
    #######################################################################

    @pyqtSlot()
    def on_editorButton_clicked(self):
        """
        Private slot to open the user configuration file in a text editor.
        """
        from eric7.QScintilla.MiniEditor import MiniEditor

        cfgFile = getConfigPath()

        yes = EricMessageBox.yesNo(
            self,
            self.tr("Edit User Configuration"),
            self.tr(
                """You will loose all changes made in this dialog."""
                """ Shall the data be saved first?"""
            ),
            icon=EricMessageBox.Warning,
            yesDefault=True,
        )
        if yes:
            self.writeUserConfig()

        self.__editor = MiniEditor(cfgFile, "Properties", self)
        self.__editor.setWindowModality(Qt.WindowModality.WindowModal)
        self.__editor.installEventFilter(self)
        self.__editor.show()

    def eventFilter(self, watched, event):
        """
        Public method called to filter the event queue.

        @param watched reference to the object being watched
        @type QObject
        @param event event to be handled
        @type QEvent
        @return flag indicating, if we handled the event
        @rtype bool
        """
        if watched is self.__editor and event.type() == QEvent.Type.Close:
            self.__editor.closeEvent(event)
            if event.isAccepted():
                self.__clearDialog()
                self.readUserConfig()
                return True

        return False
