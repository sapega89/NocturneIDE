# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage the list of defined virtual
environments.
"""

import datetime
import os

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricListSelectionDialog import EricListSelectionDialog
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import OSUtilities

from .Ui_VirtualenvManagerWidget import Ui_VirtualenvManagerWidget
from .VirtualenvMeta import VirtualenvMetaData


class VirtualenvManagerWidget(QWidget, Ui_VirtualenvManagerWidget):
    """
    Class implementing a widget to manage the list of defined virtual
    environments.
    """

    MetadataRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the virtual environment manager
        @type VirtualenvManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.layout().setContentsMargins(0, 3, 0, 0)

        self.__manager = manager

        self.refreshButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.addButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.newButton.setIcon(EricPixmapCache.getIcon("new"))
        self.searchNewButton.setIcon(EricPixmapCache.getIcon("question"))
        self.editButton.setIcon(EricPixmapCache.getIcon("edit"))
        self.upgradeButton.setIcon(EricPixmapCache.getIcon("upgrade"))
        self.removeButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.removeAllButton.setIcon(EricPixmapCache.getIcon("minus_3"))
        self.deleteButton.setIcon(EricPixmapCache.getIcon("fileDelete"))
        self.deleteAllButton.setIcon(EricPixmapCache.getIcon("fileDeleteList"))
        self.saveButton.setIcon(EricPixmapCache.getIcon("fileSave"))

        baseDir = self.__manager.getVirtualEnvironmentsBaseDir()
        if not baseDir:
            baseDir = OSUtilities.getHomeDir()

        self.envBaseDirectoryPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.envBaseDirectoryPicker.setWindowTitle(self.tr("Virtualenv Base Directory"))
        self.envBaseDirectoryPicker.setText(baseDir)

        self.__populateVenvList()
        self.__updateButtons()

        self.venvList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.__manager.virtualEnvironmentsListChanged.connect(self.__refresh)

    def __updateButtons(self):
        """
        Private method to update the enabled state of the various buttons.
        """
        selectedItemsCount = len(self.venvList.selectedItems())
        topLevelItemCount = self.venvList.topLevelItemCount()

        deletableSelectedItemCount = 0
        for itm in self.venvList.selectedItems():
            if (
                itm.text(0) != "<default>"
                and bool(itm.text(1))
                and not itm.data(0, VirtualenvManagerWidget.MetadataRole).is_global
                and not itm.data(0, VirtualenvManagerWidget.MetadataRole).is_remote
            ):
                deletableSelectedItemCount += 1

        deletableItemCount = 0
        for index in range(topLevelItemCount):
            itm = self.venvList.topLevelItem(index)
            if (
                itm.text(0) != "<default>"
                and bool(itm.text(1))
                and not itm.data(0, VirtualenvManagerWidget.MetadataRole).is_remote
            ):
                deletableItemCount += 1

        canBeRemoved = (
            selectedItemsCount == 1
            and self.venvList.selectedItems()[0].text(0) != "<default>"
        )
        canAllBeRemoved = (
            topLevelItemCount == 1
            and self.venvList.topLevelItem(0).text(0) != "<default>"
        )

        self.editButton.setEnabled(selectedItemsCount == 1)

        self.removeButton.setEnabled(selectedItemsCount > 1 or canBeRemoved)
        self.removeAllButton.setEnabled(topLevelItemCount > 1 or canAllBeRemoved)

        self.deleteButton.setEnabled(deletableSelectedItemCount)
        self.deleteAllButton.setEnabled(deletableItemCount)

        if selectedItemsCount == 1:
            venvName = self.venvList.selectedItems()[0].text(0)
            venvDirectory = self.__manager.getVirtualenvDirectory(venvName)
            self.upgradeButton.setEnabled(
                os.path.exists(os.path.join(venvDirectory, "pyvenv.cfg"))
            )
        else:
            self.upgradeButton.setEnabled(False)

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the list of virtual environments.
        """
        self.__manager.reloadSettings()
        self.__refresh()

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a new entry.
        """
        from .VirtualenvAddEditDialog import VirtualenvAddEditDialog

        dlg = VirtualenvAddEditDialog(
            self.__manager, baseDir=self.envBaseDirectoryPicker.text(), parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            metadata = dlg.getMetaData()
            self.__manager.addVirtualEnv(metadata)

    @pyqtSlot()
    def on_newButton_clicked(self):
        """
        Private slot to create a new virtual environment.
        """
        self.__manager.createVirtualEnv(baseDir=self.envBaseDirectoryPicker.text())

    @pyqtSlot()
    def on_searchNewButton_clicked(self):
        """
        Private slot to search for new (not yet registered) Python interpreters.
        """
        potentialInterpreters = self.__manager.searchUnregisteredInterpreters()

        if not bool(potentialInterpreters):
            EricMessageBox.information(
                self,
                self.tr("Search Virtual Environments"),
                self.tr("""No unregistered virtual environments were found."""),
            )
            return

        baseDir = self.__manager.getVirtualEnvironmentsBaseDir()
        if not baseDir:
            baseDir = OSUtilities.getHomeDir()

        selectionList = []
        for interpreter in potentialInterpreters:
            if not interpreter.startswith(baseDir):
                realpath = os.path.realpath(interpreter)
                if realpath != interpreter:
                    # interpreter is a link
                    selectionList.append(
                        (
                            self.tr("{0}\n(=> {1})").format(interpreter, realpath),
                            interpreter,
                        )
                    )
                    continue

            selectionList.append((interpreter, interpreter))

        dlg = EricListSelectionDialog(
            sorted(selectionList),
            title=self.tr("Search Virtual Environments"),
            message=self.tr(
                "Select the interpreters to create environment entries for:"
            ),
            checkBoxSelection=True,
            emptySelectionOk=True,
            showSelectAll=True,
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selectedInterpreters = [env[1] for env in dlg.getSelection()]

            nameTemplate = "Environment #{0} added " + datetime.datetime.now().strftime(
                # noqa: M305
                "%Y-%m-%d %H:%M"
            )
            for interpreter in selectedInterpreters:
                metadata = VirtualenvMetaData(
                    name=nameTemplate.format(
                        selectedInterpreters.index(interpreter) + 1
                    ),
                    path=(
                        os.path.abspath(os.path.join(interpreter, "..", ".."))
                        if interpreter.startswith(baseDir)
                        else ""
                    ),
                    interpreter=interpreter,
                    is_global=not interpreter.startswith(baseDir),
                )
                self.__manager.addVirtualEnv(metadata)

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to edit the selected entry.
        """
        from .VirtualenvAddEditDialog import VirtualenvAddEditDialog

        selectedItem = self.venvList.selectedItems()[0]
        oldVenvName = selectedItem.text(0)

        dlg = VirtualenvAddEditDialog(
            self.__manager,
            selectedItem.data(0, VirtualenvManagerWidget.MetadataRole),
            baseDir=self.envBaseDirectoryPicker.text(),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            metadata = dlg.getMetaData()
            if metadata.name != oldVenvName:
                self.__manager.renameVirtualEnv(oldVenvName, metadata)
            else:
                self.__manager.setVirtualEnv(metadata)

    @pyqtSlot()
    def on_upgradeButton_clicked(self):
        """
        Private slot to upgrade a virtual environment.
        """
        self.__manager.upgradeVirtualEnv(self.venvList.selectedItems()[0].text(0))

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove all selected entries from the list but keep
        their directories.
        """
        selectedVenvs = []
        for itm in self.venvList.selectedItems():
            selectedVenvs.append(itm.text(0))

        if selectedVenvs:
            self.__manager.removeVirtualEnvs(selectedVenvs)

    @pyqtSlot()
    def on_removeAllButton_clicked(self):
        """
        Private slot to remove all entries from the list but keep their
        directories.
        """
        venvNames = []
        for index in range(self.venvList.topLevelItemCount()):
            itm = self.venvList.topLevelItem(index)
            venvNames.append(itm.text(0))

        if venvNames:
            self.__manager.removeVirtualEnvs(venvNames)

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete all selected entries from the list and disk.
        """
        selectedVenvs = []
        for itm in self.venvList.selectedItems():
            selectedVenvs.append(itm.text(0))

        if selectedVenvs:
            self.__manager.deleteVirtualEnvs(selectedVenvs)

    @pyqtSlot()
    def on_deleteAllButton_clicked(self):
        """
        Private slot to delete all entries from the list and disk.
        """
        venvNames = []
        for index in range(self.venvList.topLevelItemCount()):
            itm = self.venvList.topLevelItem(index)
            venvNames.append(itm.text(0))

        if venvNames:
            self.__manager.deleteVirtualEnvs(venvNames)

    @pyqtSlot()
    def on_venvList_itemSelectionChanged(self):
        """
        Private slot handling a change of the selected items.
        """
        self.__updateButtons()

        selectedItems = self.venvList.selectedItems()
        if len(selectedItems) == 1:
            self.descriptionEdit.setPlainText(
                selectedItems[0]
                .data(0, VirtualenvManagerWidget.MetadataRole)
                .description
            )
        else:
            self.descriptionEdit.clear()

    @pyqtSlot()
    def __refresh(self):
        """
        Private slot to refresh the list of shown items.
        """
        # 1. remember selected entries
        selectedVenvs = []
        for itm in self.venvList.selectedItems():
            selectedVenvs.append(itm.text(0))

        # 2. clear the list
        self.venvList.clear()

        # 3. re-populate the list
        self.__populateVenvList()

        # 4. re-establish selection
        for venvName in selectedVenvs:
            itms = self.venvList.findItems(venvName, Qt.MatchFlag.MatchExactly, 0)
            if itms:
                itms[0].setSelected(True)

    def __populateVenvList(self):
        """
        Private method to populate the list of virtual environments.
        """
        for environment in self.__manager.getEnvironmentEntries():
            itm = QTreeWidgetItem(
                self.venvList,
                [
                    environment.name,
                    environment.path,
                    environment.interpreter,
                ],
            )
            itm.setData(0, VirtualenvManagerWidget.MetadataRole, environment)

            # show remote environments with underlined font
            if environment.is_remote:
                font = itm.font(0)
                font.setUnderline(True)
                for column in range(itm.columnCount()):
                    itm.setFont(column, font)

            # show global environments with bold font
            elif environment.is_global:
                font = itm.font(0)
                font.setBold(True)
                for column in range(itm.columnCount()):
                    itm.setFont(column, font)

            # show Anaconda environments with italic font
            elif environment.is_conda:
                font = itm.font(0)
                font.setItalic(True)
                for column in range(itm.columnCount()):
                    itm.setFont(column, font)

            # show eric-ide server environments with underlined italic font
            elif environment.is_eric_server:
                font = itm.font(0)
                font.setItalic(True)
                font.setUnderline(True)
                for column in range(itm.columnCount()):
                    itm.setFont(column, font)

        self.__resizeSections()

    def __resizeSections(self):
        """
        Private method to resize the sections of the environment list to their
        contents.
        """
        self.venvList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.venvList.header().setStretchLastSection(True)

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot to save the base directory name.
        """
        baseDir = self.envBaseDirectoryPicker.text()
        self.__manager.setVirtualEnvironmentsBaseDir(baseDir)


class VirtualenvManagerDialog(QDialog):
    """
    Class implementing the virtual environments manager dialog variant.
    """

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the virtual environment manager
        @type VirtualenvManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setSizeGripEnabled(True)

        self.__layout = QVBoxLayout(self)
        self.setLayout(self.__layout)

        self.cw = VirtualenvManagerWidget(manager, self)
        self.__layout.addWidget(self.cw)

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, Qt.Orientation.Horizontal, self
        )
        self.__layout.addWidget(self.buttonBox)

        self.resize(700, 500)
        self.setWindowTitle(self.tr("Manage Virtual Environments"))

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)


class VirtualenvManagerWindow(EricMainWindow):
    """
    Main window class for the standalone virtual environments manager.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        from eric7.VirtualEnv.VirtualenvManager import VirtualenvManager

        super().__init__(parent)

        self.__virtualenvManager = VirtualenvManager(self)

        self.__centralWidget = QWidget(self)
        self.__layout = QVBoxLayout(self.__centralWidget)
        self.__centralWidget.setLayout(self.__layout)

        self.__virtualenvManagerWidget = VirtualenvManagerWidget(
            self.__virtualenvManager, self.__centralWidget
        )
        self.__layout.addWidget(self.__virtualenvManagerWidget)

        self.__buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, Qt.Orientation.Horizontal, self
        )
        self.__layout.addWidget(self.__buttonBox)

        self.setCentralWidget(self.__centralWidget)
        self.resize(700, 500)
        self.setWindowTitle(self.tr("Manage Virtual Environments"))

        self.__buttonBox.accepted.connect(self.close)
        self.__buttonBox.rejected.connect(self.close)
