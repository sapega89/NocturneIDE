# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show outdated modules of a connected device.
"""

import circup

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTreeWidgetItem
from semver import VersionInfo

from .Ui_ShowOutdatedDialog import Ui_ShowOutdatedDialog


class ShowOutdatedDialog(QDialog, Ui_ShowOutdatedDialog):
    """
    Class implementing a dialog to show outdated modules of a connected device.
    """

    def __init__(self, devicePath, selectionMode=False, parent=None):
        """
        Constructor

        @param devicePath path to the connected board
        @type str
        @param selectionMode flag indicating the activation of the selection mode
            (defaults to False)
        @type bool (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.header.clear()
        self.modulesList.clear()

        self.__checkCount = 0
        self.__selectionMode = selectionMode
        if self.__selectionMode:
            self.buttonBox.setStandardButtons(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
        else:
            self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)

        backend = circup.DiskBackend(devicePath, circup.logger)
        self.__modules = {
            m.name: m
            for m in circup.find_modules(backend, circup.get_bundles_list())
            if m.outofdate
        }
        if self.__modules:
            self.header.setText(
                self.tr(
                    "The following modules are out of date or probably need an update."
                    "\nMajor Updates may include breaking changes. Review before"
                    " updating.\nMPY Format changes require an update."
                )
            )
            try:
                versionIsValid = VersionInfo.is_valid
            except AttributeError:
                versionIsValid = VersionInfo.isvalid
            for module in self.__modules.values():
                if isinstance(module.bundle_version, str) and not versionIsValid(
                    module.bundle_version
                ):
                    reason = self.tr("Incorrect '__version__' Metadata")
                    needsUpdate = True
                elif module.bad_format:
                    reason = self.tr("Corrupted or Unknown MPY Format")
                    needsUpdate = True
                elif module.mpy_mismatch:
                    reason = self.tr("MPY Format")
                    needsUpdate = True
                elif module.major_update:
                    reason = self.tr("Major Version")
                    needsUpdate = False
                else:
                    reason = self.tr("Minor Version")
                    needsUpdate = False
                itm = QTreeWidgetItem(
                    self.modulesList,
                    [
                        module.name,
                        (
                            module.device_version
                            if module.device_version
                            else self.tr("unknown")
                        ),
                        (
                            module.bundle_version
                            if module.bundle_version
                            else self.tr("unknown")
                        ),
                        reason,
                    ],
                )
                if self.__selectionMode:
                    itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    itm.setCheckState(
                        0,
                        (
                            Qt.CheckState.Checked
                            if needsUpdate
                            else Qt.CheckState.Unchecked
                        ),
                    )
                    if needsUpdate:
                        self.__checkCount += 1
        else:
            self.header.setText(self.tr("All modules are up-to-date."))

        self.modulesList.sortItems(0, Qt.SortOrder.AscendingOrder)
        for column in range(self.modulesList.columnCount()):
            self.modulesList.resizeColumnToContents(column)

        self.__checkCountUpdated()

    @pyqtSlot(QTreeWidgetItem, int)
    def on_modulesList_itemChanged(self, item, column):
        """
        Private slot to handle a change of the check state of an item.

        @param item reference to the changed item
        @type QTreeWidgetItem
        @param column changed column
        @type int
        """
        if self.__selectionMode:
            if item.checkState(0) == Qt.CheckState.Checked:
                self.__checkCount += 1
            elif self.__checkCount > 0:
                self.__checkCount -= 1

            self.__checkCountUpdated()

    def __checkCountUpdated(self):
        """
        Private method to handle an update of the check count.
        """
        if self.__selectionMode:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                self.__checkCount > 0
            )

    def getSelection(self):
        """
        Public method to get the list of selected modules.

        @return list of selected modules
        @rtype circup.module.Module
        """
        results = []
        if self.__selectionMode:
            for row in range(self.modulesList.topLevelItemCount()):
                itm = self.modulesList.topLevelItem(row)
                if itm.checkState(0) == Qt.CheckState.Checked:
                    results.append(self.__modules[itm.text(0)])

        return results
