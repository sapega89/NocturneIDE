# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a file manager for MicroPython devices.
"""

import contextlib
import os
import shutil

from PyQt6.QtCore import QPoint, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox, EricPathPickerDialog
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricFileSaveConfirmDialog import confirmOverwrite
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog
from eric7.Utilities import MimeTypes

from .MicroPythonFileSystemUtilities import (
    decoratedName,
    listdirStat,
    mode2string,
    mtime2string,
)
from .Ui_MicroPythonFileManagerWidget import Ui_MicroPythonFileManagerWidget


class MicroPythonFileManagerWidget(QWidget, Ui_MicroPythonFileManagerWidget):
    """
    Class implementing a file manager for MicroPython devices.
    """

    def __init__(self, fileManager, parent=None):
        """
        Constructor

        @param fileManager reference to the device file manager interface
        @type MicroPythonFileManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__repl = parent

        self.syncButton.setIcon(EricPixmapCache.getIcon("2rightarrow"))
        self.putButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))
        self.putAsButton.setIcon(EricPixmapCache.getIcon("putAs"))
        self.getButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.getAsButton.setIcon(EricPixmapCache.getIcon("getAs"))
        self.localUpButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.localHomeButton.setIcon(EricPixmapCache.getIcon("home"))
        self.localReloadButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.deviceUpButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.deviceHomeButton.setIcon(EricPixmapCache.getIcon("home"))
        self.deviceReloadButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.openButton.setIcon(EricPixmapCache.getIcon("open"))
        self.saveButton.setIcon(EricPixmapCache.getIcon("fileSave"))
        self.saveAsButton.setIcon(EricPixmapCache.getIcon("fileSaveAs"))

        isMicrobitDeviceWithMPy = self.__repl.isMicrobit()

        self.deviceUpButton.setEnabled(not isMicrobitDeviceWithMPy)
        self.deviceHomeButton.setEnabled(not isMicrobitDeviceWithMPy)

        self.putButton.setEnabled(False)
        self.putAsButton.setEnabled(False)
        self.getButton.setEnabled(False)
        self.getAsButton.setEnabled(False)

        self.openButton.setEnabled(False)
        self.saveButton.setEnabled(False)
        self.saveAsButton.setEnabled(False)

        self.localFileTreeWidget.header().setSortIndicator(
            0, Qt.SortOrder.AscendingOrder
        )
        self.deviceFileTreeWidget.header().setSortIndicator(
            0, Qt.SortOrder.AscendingOrder
        )

        self.__progressInfoDialog = None
        self.__fileManager = fileManager

        self.__fileManager.longListFiles.connect(self.__handleLongListFiles)
        self.__fileManager.currentDir.connect(self.__handleCurrentDir)
        self.__fileManager.currentDirChanged.connect(self.__handleCurrentDir)
        self.__fileManager.putFileDone.connect(self.__newDeviceList)
        self.__fileManager.getFileDone.connect(self.__handleGetDone)
        self.__fileManager.rsyncDone.connect(self.__handleRsyncDone)
        self.__fileManager.rsyncProgressMessage.connect(
            self.__handleRsyncProgressMessage
        )
        self.__fileManager.removeDirectoryDone.connect(self.__newDeviceList)
        self.__fileManager.createDirectoryDone.connect(self.__newDeviceList)
        self.__fileManager.deleteFileDone.connect(self.__newDeviceList)
        self.__fileManager.fsinfoDone.connect(self.__fsInfoResultReceived)
        self.__fileManager.putDataDone.connect(self.__newDeviceList)

        self.__fileManager.error.connect(self.__handleError)

        self.localFileTreeWidget.customContextMenuRequested.connect(
            self.__showLocalContextMenu
        )
        self.deviceFileTreeWidget.customContextMenuRequested.connect(
            self.__showDeviceContextMenu
        )

        ########################################################################
        ## Context menu for the local directory tree.
        ########################################################################

        self.__localMenu = QMenu(self)
        self.__localMenu.addAction(
            self.tr("Change Directory"), self.__changeLocalDirectory
        )
        self.__localMenu.addAction(
            self.tr("Create Directory"), self.__createLocalDirectory
        )
        self.__localDelDirTreeAct = self.__localMenu.addAction(
            self.tr("Delete Directory Tree"), self.__deleteLocalDirectoryTree
        )
        self.__localMenu.addSeparator()
        self.__localMenu.addAction(self.tr("New File"), self.__newLocalFile)
        self.__openLocalFileAct = self.__localMenu.addAction(
            self.tr("Open File"), self.__openLocalFile
        )
        self.__localRenameFileAct = self.__localMenu.addAction(
            self.tr("Rename File"), self.__renameLocalFile
        )
        self.__localDelFileAct = self.__localMenu.addAction(
            self.tr("Delete File"), self.__deleteLocalFile
        )
        self.__localMenu.addSeparator()
        act = self.__localMenu.addAction(self.tr("Show Hidden Files"))
        act.setCheckable(True)
        act.setChecked(Preferences.getMicroPython("ShowHiddenLocal"))
        act.triggered[bool].connect(self.__localHiddenChanged)
        self.__localMenu.addSeparator()
        self.__localClearSelectionAct = self.__localMenu.addAction(
            self.tr("Clear Selection"), self.__clearLocalSelection
        )

        ########################################################################
        ## Context menu for the device directory tree.
        ########################################################################

        self.__deviceMenu = QMenu(self)
        if not isMicrobitDeviceWithMPy:
            self.__deviceMenu.addAction(
                self.tr("Change Directory"), self.__changeDeviceDirectory
            )
            self.__deviceMenu.addAction(
                self.tr("Create Directory"), self.__createDeviceDirectory
            )
            self.__devDelDirAct = self.__deviceMenu.addAction(
                self.tr("Delete Directory"), self.__deleteDeviceDirectory
            )
            self.__devDelDirTreeAct = self.__deviceMenu.addAction(
                self.tr("Delete Directory Tree"), self.__deleteDeviceDirectoryTree
            )
            self.__deviceMenu.addSeparator()
        self.__deviceMenu.addAction(self.tr("New File"), self.__newDeviceFile)
        self.__openDeviceFileAct = self.__deviceMenu.addAction(
            self.tr("Open File"), self.__openDeviceFile
        )
        self.__devRenameFileAct = self.__deviceMenu.addAction(
            self.tr("Rename File"), self.__renameDeviceFile
        )
        self.__devDelFileAct = self.__deviceMenu.addAction(
            self.tr("Delete File"), self.__deleteDeviceFile
        )
        self.__deviceMenu.addSeparator()
        act = self.__deviceMenu.addAction(self.tr("Show Hidden Files"))
        act.setCheckable(True)
        act.setChecked(Preferences.getMicroPython("ShowHiddenDevice"))
        act.triggered[bool].connect(self.__deviceHiddenChanged)
        if not isMicrobitDeviceWithMPy:
            self.__deviceMenu.addSeparator()
            self.__deviceMenu.addAction(
                self.tr("Show Filesystem Info"), self.__showFileSystemInfo
            )
        self.__deviceMenu.addSeparator()
        self.__deviceClearSelectionAct = self.__deviceMenu.addAction(
            self.tr("Clear Selection"), self.__clearDeviceSelection
        )

    def start(self):
        """
        Public method to start the widget.
        """
        self.__viewmanager = ericApp().getObject("ViewManager")
        self.__viewmanager.editorCountChanged.connect(self.__updateSaveButtonStates)

        dirname = ""
        aw = self.__viewmanager.activeWindow()
        if aw and FileSystemUtilities.isPlainFileName(aw.getFileName()):
            dirname = os.path.dirname(aw.getFileName())
        if not dirname:
            dirname = (
                Preferences.getMicroPython("MpyWorkspace")
                or Preferences.getMultiProject("Workspace")
                or os.path.expanduser("~")
            )
        self.__listLocalFiles(dirname=dirname)

        if self.__repl.deviceSupportsLocalFileAccess():
            dirname = self.__repl.getDeviceWorkspace()
            if dirname:
                self.__listLocalFiles(dirname=dirname, localDevice=True)
                return

        # list files via device script
        self.__expandedDeviceEntries = []
        self.__fileManager.pwd()

    def stop(self):
        """
        Public method to stop the widget.
        """
        self.__viewmanager.editorCountChanged.disconnect(self.__updateSaveButtonStates)

    @pyqtSlot()
    def __updateSaveButtonStates(self):
        """
        Private slot to update the enabled state of the save buttons.
        """
        enable = bool(len(self.deviceFileTreeWidget.selectedItems()))
        if enable:
            enable &= not (
                self.deviceFileTreeWidget.selectedItems()[0].text(0).endswith("/")
            )
        editorsCount = self.__viewmanager.getOpenEditorsCount()

        self.saveButton.setEnabled(enable and bool(editorsCount))
        self.saveAsButton.setEnabled(bool(editorsCount))

    @pyqtSlot(str, str)
    def __handleError(self, method, error):
        """
        Private slot to handle errors.

        @param method name of the method the error occured in
        @type str
        @param error error message
        @type str
        """
        EricMessageBox.warning(
            self,
            self.tr("Error handling device"),
            self.tr(
                "<p>There was an error communicating with the connected"
                " device.</p><p>Method: {0}</p><p>Message: {1}</p>"
            ).format(method, error),
        )

    @pyqtSlot(str)
    def __handleCurrentDir(self, dirname):
        """
        Private slot to handle a change of the current directory of the device.

        @param dirname name of the current directory
        @type str
        """
        self.deviceCwd.setText(dirname)
        self.__newDeviceList()

    def __findDirectoryItem(self, dirPath, fileTreeWidget):
        """
        Private method to find a file tree item for the given path.

        @param dirPath path to be searched for
        @type str
        @param fileTreeWidget reference to the file list to be searched
        @type QTreeWidget
        @return reference to the item for the path
        @rtype QTreeWidgetItem
        """
        itm = fileTreeWidget.topLevelItem(0)
        while itm is not None:
            if itm.data(0, Qt.ItemDataRole.UserRole) == dirPath:
                return itm
            itm = fileTreeWidget.itemBelow(itm)

        return None

    @pyqtSlot(tuple)
    def __handleLongListFiles(self, filesList):
        """
        Private slot to receive a long directory listing.

        @param filesList tuple containing tuples with name, mode, size and time
            for each directory entry
        @type tuple of (str, str, str, str)
        """
        if filesList:
            dirPath = os.path.dirname(filesList[0][-1])
            dirItem = (
                self.__findDirectoryItem(dirPath, self.deviceFileTreeWidget)
                if dirPath != self.deviceCwd.text()
                else None
            )

            if dirItem:
                dirItem.takeChildren()
            else:
                self.deviceFileTreeWidget.clear()

            for name, mode, size, dateTime, filePath in filesList:
                itm = QTreeWidgetItem(
                    self.deviceFileTreeWidget if dirItem is None else dirItem,
                    [name, mode, size, dateTime],
                )
                itm.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)
                itm.setTextAlignment(2, Qt.AlignmentFlag.AlignRight)
                itm.setData(0, Qt.ItemDataRole.UserRole, filePath)
                if name.endswith("/"):
                    itm.setChildIndicatorPolicy(
                        QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                    )
        self.deviceFileTreeWidget.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )

        if self.__expandedDeviceEntries:
            dirPath = self.__expandedDeviceEntries.pop(0)
            dirItem = self.__findDirectoryItem(dirPath, self.deviceFileTreeWidget)
            if dirItem:
                dirItem.setExpanded(True)

    def __listLocalFiles(self, dirname="", localDevice=False, parentItem=None):
        """
        Private method to populate the local files list.

        @param dirname name of the local directory to be listed (defaults to "")
        @type str (optional)
        @param localDevice flag indicating device access via local file system
            (defaults to False)
        @type bool (optional)
        @param parentItem reference to the parent item (defaults to None)
        @type QTreeWidgetItem (optional)
        """
        if parentItem:
            dirname = parentItem.data(0, Qt.ItemDataRole.UserRole)
            showHidden = (
                Preferences.getMicroPython("ShowHiddenDevice")
                if localDevice
                else Preferences.getMicroPython("ShowHiddenLocal")
            )
        else:
            if not dirname:
                dirname = os.getcwd()
            if dirname != os.sep and dirname.endswith(os.sep):
                dirname = dirname[:-1]
            if localDevice:
                self.deviceCwd.setText(dirname)
                showHidden = Preferences.getMicroPython("ShowHiddenDevice")
            else:
                self.localCwd.setText(dirname)
                showHidden = Preferences.getMicroPython("ShowHiddenLocal")

        filesStatList = listdirStat(dirname, showHidden=showHidden)
        filesList = [
            (
                decoratedName(f, s[0], os.path.isdir(os.path.join(dirname, f))),
                mode2string(s[0]),
                str(s[6]),
                mtime2string(s[8]),
                os.path.join(dirname, f),
            )
            for f, s in filesStatList
        ]
        fileTreeWidget = (
            self.deviceFileTreeWidget if localDevice else self.localFileTreeWidget
        )
        if parentItem:
            parentItem.takeChildren()
        else:
            fileTreeWidget.clear()
            parentItem = fileTreeWidget
        for item in filesList:
            itm = QTreeWidgetItem(parentItem, item[:4])
            itm.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)
            itm.setTextAlignment(2, Qt.AlignmentFlag.AlignRight)
            itm.setData(0, Qt.ItemDataRole.UserRole, item[4])
            if os.path.isdir(item[4]):
                itm.setChildIndicatorPolicy(
                    QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                )
        fileTreeWidget.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)

    def __repopulateLocalFilesList(self, dirname="", localDevice=False):
        """
        Private method to re-populate the local files tree.

        @param dirname name of the local directory to be listed (defaults to "")
        @type str (optional)
        @param localDevice flag indicating device access via local file system
            (defaults to False)
        @type bool (optional)
        """
        fileTreeWidget = (
            self.deviceFileTreeWidget if localDevice else self.localFileTreeWidget
        )

        # Step 1: record all expanded directories
        expanded = []
        itm = fileTreeWidget.topLevelItem(0)
        while itm:
            if itm.isExpanded():
                expanded.append(itm.data(0, Qt.ItemDataRole.UserRole))
            itm = fileTreeWidget.itemBelow(itm)

        # Step 2: re-populate the top level directory
        self.__listLocalFiles(dirname=dirname, localDevice=localDevice)

        # Step 3: re-populate expanded directories
        itm = fileTreeWidget.topLevelItem(0)
        while itm:
            if itm.data(0, Qt.ItemDataRole.UserRole) in expanded:
                itm.setExpanded(True)
            itm = fileTreeWidget.itemBelow(itm)

    @pyqtSlot(QTreeWidgetItem, int)
    def on_localFileTreeWidget_itemActivated(self, item, _column):
        """
        Private slot to handle the activation of a local item.

        If the item is a directory, the list will be re-populated for this
        directory.

        @param item reference to the activated item
        @type QTreeWidgetItem
        @param _column column of the activation (unused)
        @type int
        """
        name = item.data(0, Qt.ItemDataRole.UserRole)
        if item.text(0).endswith("/"):
            # directory names end with a '/'
            self.__listLocalFiles(dirname=name)
        elif MimeTypes.isTextFile(name):
            self.__viewmanager.getEditor(name)

    @pyqtSlot()
    def on_localFileTreeWidget_itemSelectionChanged(self):
        """
        Private slot handling a change of selection in the local pane.
        """
        enable = bool(self.localFileTreeWidget.selectedItems())
        self.__localClearSelectionAct.setEnabled(enable)

        if enable:
            enable &= not (
                self.localFileTreeWidget.selectedItems()[0].text(0).endswith("/")
            )
        self.putButton.setEnabled(enable)
        self.putAsButton.setEnabled(enable)

    @pyqtSlot(QTreeWidgetItem)
    def on_localFileTreeWidget_itemExpanded(self, item):
        """
        Private slot handling the expansion of a local directory item.

        @param item reference to the directory item
        @type QTreeWidgetItem
        """
        if item.childCount() == 0:
            # it was not populated yet
            self.__listLocalFiles(parentItem=item)

    @pyqtSlot(str)
    def on_localCwd_textChanged(self, cwd):
        """
        Private slot handling a change of the current local working directory.

        @param cwd current local working directory
        @type str
        """
        self.localUpButton.setEnabled(cwd != os.sep)

    @pyqtSlot()
    def on_localUpButton_clicked(self):
        """
        Private slot to go up one directory level.
        """
        cwd = self.localCwd.text()
        dirname = os.path.dirname(cwd)
        self.__listLocalFiles(dirname=dirname)

    @pyqtSlot()
    def on_localHomeButton_clicked(self):
        """
        Private slot to change directory to the configured workspace.
        """
        dirname = (
            Preferences.getMicroPython("MpyWorkspace")
            or Preferences.getMultiProject("Workspace")
            or os.path.expanduser("~")
        )
        self.__listLocalFiles(dirname=dirname)

    @pyqtSlot()
    def on_localReloadButton_clicked(self):
        """
        Private slot to reload the local list.
        """
        dirname = self.localCwd.text()
        self.__repopulateLocalFilesList(dirname=dirname)

    @pyqtSlot(QTreeWidgetItem, int)
    def on_deviceFileTreeWidget_itemActivated(self, item, _column):
        """
        Private slot to handle the activation of a device item.

        If the item is a directory, the current working directory is changed
        and the list will be re-populated for this directory.

        @param item reference to the activated item
        @type QTreeWidgetItem
        @param _column column of the activation (unused)
        @type int
        """
        name = item.data(0, Qt.ItemDataRole.UserRole)
        if self.__repl.deviceSupportsLocalFileAccess():
            if item.text(0).endswith("/"):
                # directory names end with a '/'
                self.__listLocalFiles(dirname=name)
            else:
                if not os.path.exists(name):
                    EricMessageBox.warning(
                        self,
                        self.tr("Open Device File"),
                        self.tr(
                            """<p>The file <b>{0}</b> does not exist.</p>"""
                        ).format(name),
                    )
                    return
                if MimeTypes.isTextFile(name):
                    self.__viewmanager.getEditor(name)
        else:
            if item.text(0).endswith("/"):
                # directory names end with a '/'
                self.__fileManager.cd(name)
            else:
                data = self.__fileManager.getData(name)
                try:
                    text = data.decode(encoding="utf-8")
                    self.__viewmanager.newEditorWithText(
                        text, fileName=FileSystemUtilities.deviceFileName(name)
                    )
                except UnicodeDecodeError:
                    EricMessageBox.warning(
                        self,
                        self.tr("Open Device File"),
                        self.tr(
                            "<p>The file <b>{0}</b> does not contain Unicode text.</p>"
                        ).format(name),
                    )
                    return

    @pyqtSlot()
    def on_deviceFileTreeWidget_itemSelectionChanged(self):
        """
        Private slot handling a change of selection in the local pane.
        """
        enable = bool(self.deviceFileTreeWidget.selectedItems())
        self.__deviceClearSelectionAct.setEnabled(enable)

        if enable:
            enable &= not (
                self.deviceFileTreeWidget.selectedItems()[0].text(0).endswith("/")
            )

        self.getButton.setEnabled(enable)
        self.getAsButton.setEnabled(enable)

        self.openButton.setEnabled(enable)

        self.__updateSaveButtonStates()

    @pyqtSlot(QTreeWidgetItem)
    def on_deviceFileTreeWidget_itemExpanded(self, item):
        """
        Private slot handling the expansion of a local directory item.

        @param item reference to the directory item
        @type QTreeWidgetItem
        """
        if item.childCount() == 0:
            # it was not populated yet
            if self.__repl.deviceSupportsLocalFileAccess():
                self.__listLocalFiles(localDevice=True, parentItem=item)
            else:
                self.__fileManager.lls(
                    item.data(0, Qt.ItemDataRole.UserRole),
                    showHidden=Preferences.getMicroPython("ShowHiddenDevice"),
                )

    @pyqtSlot(str)
    def on_deviceCwd_textChanged(self, cwd):
        """
        Private slot handling a change of the current device working directory.

        @param cwd current device working directory
        @type str
        """
        self.deviceUpButton.setEnabled(cwd != "/")

    @pyqtSlot()
    def on_deviceUpButton_clicked(self):
        """
        Private slot to go up one directory level on the device.
        """
        cwd = self.deviceCwd.text()
        dirname = os.path.dirname(cwd)
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__listLocalFiles(dirname=dirname, localDevice=True)
        else:
            self.__fileManager.cd(dirname)

    @pyqtSlot()
    def on_deviceHomeButton_clicked(self):
        """
        Private slot to move to the device home directory.
        """
        if self.__repl.deviceSupportsLocalFileAccess():
            dirname = self.__repl.getDeviceWorkspace()
            if dirname:
                self.__listLocalFiles(dirname=dirname, localDevice=True)
                return

        # list files via device script
        self.__fileManager.cd("/")

    @pyqtSlot()
    def on_deviceReloadButton_clicked(self):
        """
        Private slot to reload the device list.
        """
        dirname = self.deviceCwd.text()
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__repopulateLocalFilesList(dirname=dirname, localDevice=True)
        else:
            if dirname:
                self.__newDeviceList()
            else:
                self.__fileManager.pwd()

    def __isFileInList(self, filename, parent):
        """
        Private method to check, if a file name is contained in a tree widget.

        @param filename name of the file to check
        @type str
        @param parent reference to the parent to be checked against
        @type QTreeWidget or QTreeWidgetItem
        @return flag indicating that the file name is present
        @rtype bool
        """
        if isinstance(parent, QTreeWidgetItem):
            itemCount = parent.childCount()
            return itemCount > 0 and any(
                parent.child(row).text(0) == filename for row in range(itemCount)
            )
        else:
            itemCount = parent.topLevelItemCount()
            return itemCount > 0 and any(
                parent.topLevelItem(row).text(0) == filename for row in range(itemCount)
            )

    @pyqtSlot()
    def on_putButton_clicked(self, putAs=False):
        """
        Private slot to copy the selected file to the connected device.

        @param putAs flag indicating to give it a new name
        @type bool
        """
        selectedItems = self.localFileTreeWidget.selectedItems()
        if selectedItems:
            filepath = selectedItems[0].data(0, Qt.ItemDataRole.UserRole)
            filename = os.path.basename(filepath)
            if not selectedItems[0].text(0).endswith("/"):
                # it is really a file
                if putAs:
                    deviceFilename, ok = QInputDialog.getText(
                        self,
                        self.tr("Put File As"),
                        self.tr("Enter a new name for the file"),
                        QLineEdit.EchoMode.Normal,
                        filename,
                    )
                    if not ok or not deviceFilename:
                        return
                else:
                    deviceFilename = filename

                selectedDeviceItems = self.deviceFileTreeWidget.selectedItems()
                if selectedDeviceItems:
                    item = selectedDeviceItems[0]
                    if not item.text(0).endswith("/"):
                        # it is no directory, take its parent
                        item = item.parent()
                    devicePath = (
                        self.deviceCwd.text()
                        if item is None
                        else item.data(0, Qt.ItemDataRole.UserRole)
                    )
                    deviceParent = self.deviceFileTreeWidget if item is None else item
                else:
                    devicePath = self.deviceCwd.text()
                    deviceParent = self.deviceFileTreeWidget

                if self.__isFileInList(deviceFilename, deviceParent):
                    # ask for overwrite permission
                    action, resultFilename = confirmOverwrite(
                        deviceFilename,
                        self.tr("Copy File to Device"),
                        self.tr(
                            "The given file exists already (Enter file name only)."
                        ),
                        False,
                        parent=self,
                    )
                    if action == "cancel":
                        return
                    elif action == "rename":
                        deviceFilename = os.path.basename(resultFilename)

                if self.__repl.deviceSupportsLocalFileAccess():
                    shutil.copy2(filepath, os.path.join(devicePath, deviceFilename))
                    self.__listLocalFiles(dirname=devicePath, localDevice=True)
                else:
                    if devicePath:
                        deviceFilename = (
                            f"{devicePath}/{deviceFilename}"
                            if devicePath != "/"
                            else f"/{deviceFilename}"
                        )
                    self.__fileManager.put(filepath, deviceFilename)

    @pyqtSlot()
    def on_putAsButton_clicked(self):
        """
        Private slot to copy the selected file to the connected device
        with a different name.
        """
        self.on_putButton_clicked(putAs=True)

    @pyqtSlot()
    def on_getButton_clicked(self, getAs=False):
        """
        Private slot to copy the selected file from the connected device.

        @param getAs flag indicating to give it a new name
        @type bool
        """
        selectedItems = self.deviceFileTreeWidget.selectedItems()
        if selectedItems:
            filename = selectedItems[0].text(0).strip()
            deviceFilename = selectedItems[0].data(0, Qt.ItemDataRole.UserRole)
            if not filename.endswith("/"):
                # it is really a file
                if getAs:
                    localFilename, ok = QInputDialog.getText(
                        self,
                        self.tr("Get File As"),
                        self.tr("Enter a new name for the file"),
                        QLineEdit.EchoMode.Normal,
                        filename,
                    )
                    if not ok or not filename:
                        return
                else:
                    localFilename = filename

                selectedLocalItems = self.localFileTreeWidget.selectedItems()
                if selectedLocalItems:
                    item = selectedLocalItems[0]
                    if not item.text(0).endswith("/"):
                        # it is no directory, take its parent
                        item = item.parent()
                    localPath = (
                        self.localCwd.text()
                        if item is None
                        else item.data(0, Qt.ItemDataRole.UserRole)
                    )
                    localParent = self.localFileTreeWidget if item is None else item
                else:
                    localPath = self.localCwd.text()
                    localParent = self.localFileTreeWidget

                if self.__isFileInList(localFilename, localParent):
                    # ask for overwrite permission
                    action, resultFilename = confirmOverwrite(
                        localFilename,
                        self.tr("Copy File from Device"),
                        self.tr("The given file exists already."),
                        True,
                        parent=self,
                    )
                    if action == "cancel":
                        return
                    elif action == "rename":
                        localFilename = resultFilename

                if self.__repl.deviceSupportsLocalFileAccess():
                    shutil.copy2(
                        deviceFilename,
                        os.path.join(localPath, localFilename),
                    )
                    if isinstance(localParent, QTreeWidgetItem):
                        self.__listLocalFiles(parentItem=localParent)
                    else:
                        self.__listLocalFiles(dirname=localPath)
                else:
                    self.__fileManager.get(
                        deviceFilename, os.path.join(localPath, localFilename)
                    )

    @pyqtSlot()
    def on_getAsButton_clicked(self):
        """
        Private slot to copy the selected file from the connected device
        with a different name.
        """
        self.on_getButton_clicked(getAs=True)

    @pyqtSlot(str, str)
    def __handleGetDone(self, _deviceFile, localFile):
        """
        Private slot handling a successful copy of a file from the device.

        @param _deviceFile name of the file on the device (unused)
        @type str
        @param localFile name of the local file
        @type str
        """
        localPath = os.path.dirname(localFile)

        # find the directory entry associated with the new file
        localParent = self.__findDirectoryItem(localPath, self.localFileTreeWidget)

        if localParent:
            self.__listLocalFiles(parentItem=localParent)
        else:
            self.__listLocalFiles(dirname=self.localCwd.text())

    @pyqtSlot()
    def on_syncButton_clicked(self):
        """
        Private slot to synchronize the local directory to the device.
        """
        # 1. local directory
        selectedItems = self.localFileTreeWidget.selectedItems()
        if selectedItems:
            localName = selectedItems[0].text(0)
            if localName.endswith("/"):
                localDirPath = selectedItems[0].data(0, Qt.ItemDataRole.UserRole)
            else:
                # it is not a directory
                localDirPath = os.path.dirname(
                    selectedItems[0].data(0, Qt.ItemDataRole.UserRole)
                )
        else:
            localName = ""
            localDirPath = self.localCwd.text()

        # 2. device directory
        selectedItems = self.deviceFileTreeWidget.selectedItems()
        if selectedItems:
            if not selectedItems[0].text(0).endswith("/"):
                # it is not a directory
                deviceDirPath = os.path.dirname(
                    selectedItems[0].data(0, Qt.ItemDataRole.UserRole)
                )
            else:
                deviceDirPath = selectedItems[0].data(0, Qt.ItemDataRole.UserRole)
        else:
            if localDirPath == self.localCwd.text():
                # syncronize complete local directory
                deviceDirPath = self.deviceCwd.text()
            else:
                deviceCwd = self.deviceCwd.text()
                deviceDirPath = (
                    f"{deviceCwd}{localName[:-1]}"
                    if deviceCwd.endswith("/")
                    else f"{deviceCwd}/{localName[:-1]}"
                )

        self.__fileManager.rsync(
            localDirPath,
            deviceDirPath,
            mirror=True,
            localDevice=self.__repl.deviceSupportsLocalFileAccess(),
        )

    @pyqtSlot(str, str)
    def __handleRsyncDone(self, _localDir, _deviceDir):
        """
        Private method to handle the completion of the rsync operation.

        @param _localDir name of the local directory (unused)
        @type str
        @param _deviceDir name of the device directory (unused)
        @type str
        """
        # simulate button presses to reload the two lists
        self.on_localReloadButton_clicked()
        self.on_deviceReloadButton_clicked()

    @pyqtSlot(str)
    def __handleRsyncProgressMessage(self, message):
        """
        Private slot handling progress messages sent by the file manager.

        @param message message to be shown
        @type str
        """
        from .MicroPythonProgressInfoDialog import MicroPythonProgressInfoDialog

        if self.__progressInfoDialog is None:
            self.__progressInfoDialog = MicroPythonProgressInfoDialog(parent=self)
            self.__progressInfoDialog.finished.connect(
                self.__progressInfoDialogFinished
            )
        self.__progressInfoDialog.show()
        self.__progressInfoDialog.addMessage(message)

    @pyqtSlot()
    def __progressInfoDialogFinished(self):
        """
        Private slot handling the closing of the progress info dialog.
        """
        self.__progressInfoDialog.deleteLater()
        self.__progressInfoDialog = None

    @pyqtSlot()
    def __newDeviceList(self):
        """
        Private slot to initiate a new long list of the device directory.
        """
        self.__expandedDeviceEntries.clear()
        itm = self.deviceFileTreeWidget.topLevelItem(0)
        while itm:
            if itm.isExpanded():
                self.__expandedDeviceEntries.append(
                    itm.data(0, Qt.ItemDataRole.UserRole)
                )
            itm = self.deviceFileTreeWidget.itemBelow(itm)

        self.__fileManager.lls(
            self.deviceCwd.text(),
            showHidden=Preferences.getMicroPython("ShowHiddenDevice"),
        )

    @pyqtSlot()
    def on_openButton_clicked(self):
        """
        Private slot to open the selected file in a new editor.
        """
        selectedItems = self.deviceFileTreeWidget.selectedItems()
        if selectedItems:
            name = selectedItems[0].data(0, Qt.ItemDataRole.UserRole)
            if self.__repl.deviceSupportsLocalFileAccess():
                if not selectedItems[0].text(0).endswith("/") and MimeTypes.isTextFile(
                    name
                ):
                    self.__viewmanager.getEditor(name)
            else:
                if not selectedItems[0].text(0).endswith("/"):
                    data = self.__fileManager.getData(name)
                    text = data.decode(encoding="utf-8")
                    self.__viewmanager.newEditorWithText(
                        text, "Python3", FileSystemUtilities.deviceFileName(name)
                    )

    @pyqtSlot()
    def on_saveButton_clicked(self, saveAs=False):
        """
        Private slot to save the text of the current editor to a file on the device.

        @param saveAs flag indicating to save the file with a new name
        @type bool
        """
        aw = self.__viewmanager.activeWindow()
        if aw:
            selectedItems = self.deviceFileTreeWidget.selectedItems()

            if selectedItems:
                filepath = selectedItems[0].data(0, Qt.ItemDataRole.UserRole)
                filename = os.path.basename(filepath)
                if selectedItems[0].text(0).endswith("/"):
                    saveAs = True
            else:
                saveAs = True
                filename = ""

            if saveAs:
                filename, ok = QInputDialog.getText(
                    self,
                    self.tr("Save File As"),
                    self.tr("Enter a new name for the file:"),
                    QLineEdit.EchoMode.Normal,
                    filename,
                )
                if not ok or not filename:
                    return

            if not saveAs:
                # check editor and selected file names for an implicit 'save as'
                editorFileName = os.path.basename(
                    FileSystemUtilities.plainFileName(aw.getFileName())
                )
                if editorFileName != filename:
                    saveAs = True

            if selectedItems:
                item = selectedItems[0]
                if not item.text(0).endswith("/"):
                    # it is no directory, take its parent
                    item = item.parent()
                devicePath = (
                    self.deviceCwd.text()
                    if item is None
                    else item.data(0, Qt.ItemDataRole.UserRole)
                )
                deviceParent = self.deviceFileTreeWidget if item is None else item
            else:
                devicePath = self.deviceCwd.text()
                deviceParent = self.deviceFileTreeWidget

            if saveAs and self.__isFileInList(filename, deviceParent):
                # ask for overwrite permission
                action, resultFilename = confirmOverwrite(
                    filename,
                    self.tr("Save File As"),
                    self.tr("The given file exists already (Enter file name only)."),
                    False,
                    parent=self,
                )
                if action == "cancel":
                    return
                elif action == "rename":
                    filename = os.path.basename(resultFilename)

            text = aw.text()
            if self.__repl.deviceSupportsLocalFileAccess():
                filename = os.path.join(devicePath, filename)
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "w") as f:
                    f.write(text)
                self.__newDeviceList()
                aw.setFileName(filename)
            else:
                filename = (
                    f"{devicePath}/{filename}" if devicePath != "/" else f"/{filename}"
                )
                dirname = filename.rsplit("/", 1)[0]
                self.__fileManager.makedirs(dirname)
                self.__fileManager.putData(filename, text.encode("utf-8"))
                aw.setFileName(FileSystemUtilities.deviceFileName(filename))

            aw.setModified(False)
            with contextlib.suppress(AttributeError):
                aw.resetOnlineChangeTraceInfo()

    @pyqtSlot()
    def on_saveAsButton_clicked(self):
        """
        Private slot to save the current editor in a new file on the connected device.
        """
        self.on_saveButton_clicked(saveAs=True)

    ##################################################################
    ## Context menu methods for the local files below
    ##################################################################

    @pyqtSlot(QPoint)
    def __showLocalContextMenu(self, pos):
        """
        Private slot to show the REPL context menu.

        @param pos position to show the menu at
        @type QPoint
        """
        hasSelection = bool(len(self.localFileTreeWidget.selectedItems()))
        if hasSelection:
            name = self.localFileTreeWidget.selectedItems()[0].text(0)
            isDir = name.endswith("/")
            isLink = name.endswith("@")
            isFile = not (isDir or isLink)
        else:
            isDir = False
            isFile = False
        self.__localDelDirTreeAct.setEnabled(isDir)
        self.__localRenameFileAct.setEnabled(isFile)
        self.__localDelFileAct.setEnabled(isFile)
        self.__openLocalFileAct.setEnabled(isFile)

        self.__localMenu.exec(self.localFileTreeWidget.mapToGlobal(pos))

    @pyqtSlot()
    def __changeLocalDirectory(self, localDevice=False):
        """
        Private slot to change the local directory.

        @param localDevice flag indicating device access via local file system
        @type bool
        """
        cwdWidget = self.deviceCwd if localDevice else self.localCwd
        fileTreeWidget = (
            self.deviceFileTreeWidget if localDevice else self.localFileTreeWidget
        )

        if fileTreeWidget.selectedItems():
            defaultPath = fileTreeWidget.selectedItems()[0].data(
                0, Qt.ItemDataRole.UserRole
            )
            if not os.path.isdir(defaultPath):
                defaultPath = os.path.dirname(defaultPath)
        else:
            defaultPath = cwdWidget.text()
        dirPath, ok = EricPathPickerDialog.getStrPath(
            self,
            self.tr("Change Directory"),
            self.tr("Select Directory"),
            EricPathPickerModes.DIRECTORY_SHOW_FILES_MODE,
            strPath=defaultPath,
            defaultDirectory=defaultPath,
        )
        if ok and dirPath:
            if not os.path.isabs(dirPath):
                dirPath = os.path.join(cwdWidget.text(), dirPath)
            cwdWidget.setText(dirPath)
            self.__listLocalFiles(dirname=dirPath, localDevice=localDevice)

    @pyqtSlot()
    def __createLocalDirectory(self, localDevice=False):
        """
        Private slot to create a local directory.

        @param localDevice flag indicating device access via local file system
        @type bool
        """
        cwdWidget = self.deviceCwd if localDevice else self.localCwd
        fileTreeWidget = (
            self.deviceFileTreeWidget if localDevice else self.localFileTreeWidget
        )

        if fileTreeWidget.selectedItems():
            localItem = fileTreeWidget.selectedItems()[0]
            defaultPath = localItem.data(0, Qt.ItemDataRole.UserRole)
            if not os.path.isdir(defaultPath):
                defaultPath = os.path.dirname(defaultPath)
                localItem = localItem.parent()
        else:
            defaultPath = cwdWidget.text()
            localItem = None

        dirPath, ok = QInputDialog.getText(
            self,
            self.tr("Create Directory"),
            self.tr("Enter directory name:"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and dirPath:
            dirPath = os.path.join(defaultPath, dirPath)
            try:
                os.mkdir(dirPath)
                if localItem:
                    self.__listLocalFiles(localDevice=localDevice, parentItem=localItem)
                else:
                    self.__listLocalFiles(
                        dirname=cwdWidget.text(), localDevice=localDevice
                    )
            except OSError as exc:
                EricMessageBox.critical(
                    self,
                    self.tr("Create Directory"),
                    self.tr(
                        """<p>The directory <b>{0}</b> could not be"""
                        """ created.</p><p>Reason: {1}</p>"""
                    ).format(dirPath, str(exc)),
                )

    @pyqtSlot()
    def __deleteLocalDirectoryTree(self, localDevice=False):
        """
        Private slot to delete a local directory tree.

        @param localDevice flag indicating device access via local file system
        @type bool
        """
        if localDevice:
            cwdWidget = self.deviceCwd
            fileTreeWidget = self.deviceFileTreeWidget
        else:
            cwdWidget = self.localCwd
            fileTreeWidget = self.localFileTreeWidget

        if bool(fileTreeWidget.selectedItems()):
            localItem = fileTreeWidget.selectedItems()[0]
            parentItem = localItem.parent()
            dirname = localItem.data(0, Qt.ItemDataRole.UserRole)
            dlg = DeleteFilesConfirmationDialog(
                self,
                self.tr("Delete Directory Tree"),
                self.tr("Do you really want to delete this directory tree?"),
                [dirname],
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                try:
                    shutil.rmtree(dirname)
                    if parentItem:
                        self.__listLocalFiles(
                            localDevice=localDevice, parentItem=parentItem
                        )
                    else:
                        self.__listLocalFiles(
                            dirname=cwdWidget.text(), localDevice=localDevice
                        )
                except Exception as exc:
                    EricMessageBox.critical(
                        self,
                        self.tr("Delete Directory Tree"),
                        self.tr(
                            """<p>The directory <b>{0}</b> could not be"""
                            """ deleted.</p><p>Reason: {1}</p>"""
                        ).format(dirname, str(exc)),
                    )

    @pyqtSlot()
    def __deleteLocalFile(self, localDevice=False):
        """
        Private slot to delete a local file.

        @param localDevice flag indicating device access via local file system
        @type bool
        """
        if localDevice:
            cwdWidget = self.deviceCwd
            fileTreeWidget = self.deviceFileTreeWidget
        else:
            cwdWidget = self.localCwd
            fileTreeWidget = self.localFileTreeWidget

        if bool(len(fileTreeWidget.selectedItems())):
            localItem = fileTreeWidget.selectedItems()[0]
            parentItem = localItem.parent()
            filename = localItem.data(0, Qt.ItemDataRole.UserRole)
            dlg = DeleteFilesConfirmationDialog(
                self,
                self.tr("Delete File"),
                self.tr("Do you really want to delete this file?"),
                [filename],
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                try:
                    os.remove(filename)
                    if parentItem:
                        self.__listLocalFiles(
                            localDevice=localDevice, parentItem=parentItem
                        )
                    else:
                        self.__listLocalFiles(
                            dirname=cwdWidget.text(), localDevice=localDevice
                        )
                except OSError as exc:
                    EricMessageBox.critical(
                        self,
                        self.tr("Delete File"),
                        self.tr(
                            """<p>The file <b>{0}</b> could not be"""
                            """ deleted.</p><p>Reason: {1}</p>"""
                        ).format(filename, str(exc)),
                    )

    @pyqtSlot()
    def __renameLocalFile(self, localDevice=False):
        """
        Private slot to rename a file on the device.

        @param localDevice flag indicating device access via local file system
            (defaults to False)
        @type bool (optional)
        """
        fileTreeWidget = (
            self.deviceFileTreeWidget if localDevice else self.localFileTreeWidget
        )

        if bool(len(fileTreeWidget.selectedItems())):
            localItem = fileTreeWidget.selectedItems()[0]
            filename = localItem.data(0, Qt.ItemDataRole.UserRole)
            newname, ok = QInputDialog.getText(
                self,
                self.tr("Rename File"),
                self.tr("Enter the new path for the file"),
                QLineEdit.EchoMode.Normal,
                filename,
            )
            if ok and newname:
                try:
                    os.rename(filename, newname)
                except OSError as exc:
                    EricMessageBox.critical(
                        self,
                        self.tr("Rename File"),
                        self.tr(
                            """<p>The file <b>{0}</b> could not be"""
                            """ renamed to <b>{1}</b>.</p><p>Reason: {2}</p>"""
                        ).format(filename, newname, str(exc)),
                    )

                # reload the directory listing
                if localDevice:
                    self.on_deviceReloadButton_clicked()
                else:
                    self.on_localReloadButton_clicked()

    @pyqtSlot(bool)
    def __localHiddenChanged(self, checked):
        """
        Private slot handling a change of the local show hidden menu entry.

        @param checked new check state of the action
        @type bool
        """
        Preferences.setMicroPython("ShowHiddenLocal", checked)
        self.on_localReloadButton_clicked()

    @pyqtSlot()
    def __clearLocalSelection(self):
        """
        Private slot to clear the local selection.
        """
        for item in self.localFileTreeWidget.selectedItems()[:]:
            item.setSelected(False)

    ##################################################################
    ## Context menu methods for the device files below
    ##################################################################

    @pyqtSlot(QPoint)
    def __showDeviceContextMenu(self, pos):
        """
        Private slot to show the REPL context menu.

        @param pos position to show the menu at
        @type QPoint
        """
        hasSelection = bool(len(self.deviceFileTreeWidget.selectedItems()))
        if hasSelection:
            name = self.deviceFileTreeWidget.selectedItems()[0].text(0)
            isDir = name.endswith("/")
            isFile = not isDir
        else:
            isDir = False
            isFile = False
        if not self.__repl.isMicrobit():
            self.__devDelDirAct.setEnabled(isDir)
            self.__devDelDirTreeAct.setEnabled(isDir)
        self.__devRenameFileAct.setEnabled(isFile)
        self.__devDelFileAct.setEnabled(isFile)
        self.__openDeviceFileAct.setEnabled(isFile)

        self.__deviceMenu.exec(self.deviceFileTreeWidget.mapToGlobal(pos))

    @pyqtSlot()
    def __changeDeviceDirectory(self):
        """
        Private slot to change the current directory of the device.

        Note: This triggers a re-population of the device list for the new
        current directory.
        """
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__changeLocalDirectory(True)
        else:
            selectedItems = self.deviceFileTreeWidget.selectedItems()
            if selectedItems:
                item = selectedItems[0]
                dirName = (
                    item.data(0, Qt.ItemDataRole.UserRole)
                    if item.text(0).endswith("/")
                    else os.path.dirname(item.data(0, Qt.ItemDataRole.UserRole))
                )
            else:
                dirName = self.deviceCwd.text()
            dirPath, ok = QInputDialog.getText(
                self,
                self.tr("Change Directory"),
                self.tr("Enter the directory path on the device:"),
                QLineEdit.EchoMode.Normal,
                dirName,
            )
            if ok and dirPath:
                if not dirPath.startswith("/"):
                    dirPath = self.deviceCwd.text() + "/" + dirPath
                self.__fileManager.cd(dirPath)

    @pyqtSlot()
    def __createDeviceDirectory(self):
        """
        Private slot to create a directory on the device.
        """
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__createLocalDirectory(True)
        else:
            selectedItems = self.deviceFileTreeWidget.selectedItems()
            if selectedItems:
                item = selectedItems[0]
                defaultPath = (
                    item.data(0, Qt.ItemDataRole.UserRole)
                    if item.text(0).endswith("/")
                    else os.path.dirname(item.data(0, Qt.ItemDataRole.UserRole))
                )
            else:
                defaultPath = self.deviceCwd.text()
            dirPath, ok = QInputDialog.getText(
                self,
                self.tr("Create Directory"),
                self.tr("Enter directory name:"),
                QLineEdit.EchoMode.Normal,
                defaultPath,
            )
            if ok and dirPath:
                self.__fileManager.mkdir(dirPath)

    @pyqtSlot()
    def __deleteDeviceDirectory(self):
        """
        Private slot to delete an empty directory on the device.
        """
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__deleteLocalDirectoryTree(True)
        else:
            if bool(self.deviceFileTreeWidget.selectedItems()):
                dirname = self.deviceFileTreeWidget.selectedItems()[0].data(
                    0, Qt.ItemDataRole.UserRole
                )
                dlg = DeleteFilesConfirmationDialog(
                    self,
                    self.tr("Delete Directory"),
                    self.tr("Do you really want to delete this directory?"),
                    [dirname],
                )
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self.__fileManager.rmdir(dirname)

    @pyqtSlot()
    def __deleteDeviceDirectoryTree(self):
        """
        Private slot to delete a directory and all its subdirectories
        recursively.
        """
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__deleteLocalDirectoryTree(True)
        else:
            if bool(len(self.deviceFileTreeWidget.selectedItems())):
                dirname = self.deviceFileTreeWidget.selectedItems()[0].data(
                    0, Qt.ItemDataRole.UserRole
                )
                dlg = DeleteFilesConfirmationDialog(
                    self,
                    self.tr("Delete Directory Tree"),
                    self.tr("Do you really want to delete this directory tree?"),
                    [dirname],
                )
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self.__fileManager.rmdir(dirname, recursive=True)

    @pyqtSlot()
    def __deleteDeviceFile(self):
        """
        Private slot to delete a file.
        """
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__deleteLocalFile(True)
        else:
            if bool(self.deviceFileTreeWidget.selectedItems()):
                filename = self.deviceFileTreeWidget.selectedItems()[0].data(
                    0, Qt.ItemDataRole.UserRole
                )
                dlg = DeleteFilesConfirmationDialog(
                    self,
                    self.tr("Delete File"),
                    self.tr("Do you really want to delete this file?"),
                    [filename],
                )
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    self.__fileManager.delete(filename)

    @pyqtSlot()
    def __renameDeviceFile(self):
        """
        Private slot to rename a file on the device.
        """
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__renameLocalFile(True)
        else:
            if bool(self.deviceFileTreeWidget.selectedItems()):
                filename = self.deviceFileTreeWidget.selectedItems()[0].data(
                    0, Qt.ItemDataRole.UserRole
                )
                newname, ok = QInputDialog.getText(
                    self,
                    self.tr("Rename File"),
                    self.tr("Enter the new path for the file"),
                    QLineEdit.EchoMode.Normal,
                    filename,
                )
                if ok and newname:
                    success = self.__fileManager.rename(filename, newname)
                    if success:
                        self.on_deviceReloadButton_clicked()

    @pyqtSlot(bool)
    def __deviceHiddenChanged(self, checked):
        """
        Private slot handling a change of the device show hidden menu entry.

        @param checked new check state of the action
        @type bool
        """
        Preferences.setMicroPython("ShowHiddenDevice", checked)
        self.on_deviceReloadButton_clicked()

    @pyqtSlot()
    def __showFileSystemInfo(self):
        """
        Private slot to show some file system information.
        """
        self.__fileManager.fileSystemInfo()

    @pyqtSlot(tuple)
    def __fsInfoResultReceived(self, fsinfo):
        """
        Private slot to show the file system information of the device.

        @param fsinfo tuple of tuples containing the file system name, the
            total size, the used size and the free size
        @type tuple of tuples of (str, int, int, int)
        """
        msg = self.tr("<h3>Filesystem Information</h3>")
        if fsinfo:
            for name, totalSize, usedSize, freeSize in fsinfo:
                msg += self.tr(
                    "<h4>{0}</h4"
                    "<table>"
                    "<tr><td>Total Size: </td><td align='right'>{1}</td></tr>"
                    "<tr><td>Used Size: </td><td align='right'>{2}</td></tr>"
                    "<tr><td>Free Size: </td><td align='right'>{3}</td></tr>"
                    "</table>"
                ).format(
                    name,
                    EricUtilities.dataString(totalSize),
                    EricUtilities.dataString(usedSize),
                    EricUtilities.dataString(freeSize),
                )
        else:
            msg += self.tr(
                "<p>No file systems or file system information available.</p>"
            )
        EricMessageBox.information(self, self.tr("Filesystem Information"), msg)

    @pyqtSlot()
    def __clearDeviceSelection(self):
        """
        Private slot to clear the local selection.
        """
        for item in self.deviceFileTreeWidget.selectedItems()[:]:
            item.setSelected(False)

    ############################################################################
    ## Methods for the MicroPython window variant.
    ############################################################################

    @pyqtSlot()
    def __newLocalFile(self, localDevice=False):
        """
        Private slot to create a new local file.

        @param localDevice flag indicating device access via local file system
        @type bool
        """
        cwdWidget = self.deviceCwd if localDevice else self.localCwd
        fileTreeWidget = (
            self.deviceFileTreeWidget if localDevice else self.localFileTreeWidget
        )

        if fileTreeWidget.selectedItems():
            localItem = fileTreeWidget.selectedItems()[0]
            defaultPath = localItem.data(0, Qt.ItemDataRole.UserRole)
            if not os.path.isdir(defaultPath):
                defaultPath = os.path.dirname(defaultPath)
                localItem = localItem.parent()
        else:
            defaultPath = cwdWidget.text()
            localItem = None

        filePath, ok = QInputDialog.getText(
            self,
            self.tr("New File"),
            self.tr("Enter file name:"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and filePath:
            filePath = os.path.join(defaultPath, filePath)
            try:
                with open(filePath, "w") as f:
                    f.close()
                if localItem:
                    self.__listLocalFiles(localDevice=localDevice, parentItem=localItem)
                else:
                    self.__listLocalFiles(
                        dirname=cwdWidget.text(), localDevice=localDevice
                    )
            except OSError as exc:
                EricMessageBox.critical(
                    self,
                    self.tr("New File"),
                    self.tr(
                        """<p>The file <b>{0}</b> could not be"""
                        """ created.</p><p>Reason: {1}</p>"""
                    ).format(filePath, str(exc)),
                )

    @pyqtSlot()
    def __openLocalFile(self):
        """
        Private slot to open the selected local file in an editor window.
        """
        self.on_localFileTreeWidget_itemActivated(
            self.localFileTreeWidget.selectedItems()[0], 0
        )

    @pyqtSlot()
    def __newDeviceFile(self):
        """
        Private slot to create a new file on the connected device.
        """
        if self.__repl.deviceSupportsLocalFileAccess():
            self.__newLocalFile(True)
        else:
            selectedItems = self.deviceFileTreeWidget.selectedItems()
            if selectedItems:
                item = selectedItems[0]
                defaultPath = (
                    item.data(0, Qt.ItemDataRole.UserRole)
                    if item.text(0).endswith("/")
                    else os.path.dirname(item.data(0, Qt.ItemDataRole.UserRole))
                )
            else:
                defaultPath = self.deviceCwd.text()
            fileName, ok = QInputDialog.getText(
                self,
                self.tr("New File"),
                self.tr("Enter file name:"),
                QLineEdit.EchoMode.Normal,
                defaultPath,
            )
            if ok and fileName:
                self.__fileManager.writeFile(fileName, "")

    @pyqtSlot()
    def __openDeviceFile(self):
        """
        Private slot to open the selected device file in an editor window.
        """
        self.on_deviceFileTreeWidget_itemActivated(
            self.deviceFileTreeWidget.selectedItems()[0], 0
        )
