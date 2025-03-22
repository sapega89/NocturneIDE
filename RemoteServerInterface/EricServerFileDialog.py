# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a file dialog showing the file system of the eric-ide server.
"""

import enum
import fnmatch
import re

from PyQt6.QtCore import QLocale, QPoint, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QDialog,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
)

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricFileIconProvider import EricFileIconProvider
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import dataString
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_EricServerFileDialog import Ui_EricServerFileDialog


class AcceptMode(enum.Enum):
    """
    Class defining the dialog accept modes.
    """

    AcceptOpen = 0
    AcceptSave = 1


class FileMode(enum.Enum):
    """
    Class defining what the user may select in the file dialog.
    """

    AnyFile = 0
    ExistingFile = 1
    Directory = 2
    ExistingFiles = 3


class EricServerFileDialog(QDialog, Ui_EricServerFileDialog):
    """
    Class implementing a file dialog showing the file system of the eric-ide server.
    """

    IsDirectoryRole = Qt.ItemDataRole.UserRole

    def __init__(self, parent=None, caption="", directory="", filter=""):  # noqa: M132
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        @param caption dialog title (defaults to "")
        @type str (optional)
        @param directory initial directory (defaults to "")
        @type str (optional)
        @param filter Qt file filter string (defaults to "")
        @type str (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        # finish UI setup
        self.backButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.forwardButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))
        self.upButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.newDirButton.setIcon(EricPixmapCache.getIcon("dirNew"))
        self.reloadButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.cancelButton.setIcon(EricPixmapCache.getIcon("dialog-cancel"))

        self.setWindowTitle(caption)

        self.__iconProvider = EricFileIconProvider()

        self.__nameCompleter = QCompleter()
        self.__nameCompleter.setModel(self.listing.model())
        self.__nameCompleter.setCompletionColumn(0)
        self.__nameCompleter.activated.connect(self.__nameCompleterActivated)
        self.nameEdit.setCompleter(self.__nameCompleter)

        self.__contextMenu = QMenu(self)

        self.__fsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        # set some default values
        self.__fileMode = FileMode.ExistingFile
        self.__dirsOnly = False
        self.__acceptMode = AcceptMode.AcceptOpen
        self.__showHidden = False
        self.__sep = "/"
        self.__filters = []

        self.__history = []
        self.__currentHistoryIndex = -1  # empty history
        self.__updateHistoryButtons()

        self.__filenameCache = []
        self.__directoryCache = []
        self.__selectedDirectory = None

        if filter:
            self.setNameFilters(filter.split(";;"))
        else:
            self.setNameFilters([self.tr("All Files (*)")])

        self.reloadButton.clicked.connect(self.__reload)
        self.cancelButton.clicked.connect(self.reject)

        self.treeCombo.currentTextChanged.connect(self.setDirectory)

        self.setDirectory(directory)

    def acceptMode(self):
        """
        Public method to get the accept mode of the dialog.

        @return accept mode
        @rtype AcceptMode
        """
        return self.__acceptMode

    def setAcceptMode(self, mode):
        """
        Public method to set the accept mode of the dialog.

        @param mode accept mode
        @type AcceptMode
        """
        self.__acceptMode = mode

        self.__updateOkButton()

    def fileMode(self):
        """
        Public method to get the current file mode of the dialog.

        @return file mode
        @rtype FileMode
        """
        return self.__fileMode

    def setFileMode(self, mode):
        """
        Public method to set the file mode of the dialog.

        @param mode file mode
        @type FileMode
        """
        self.__fileMode = mode

        self.listing.clearSelection()
        if mode == FileMode.ExistingFiles:
            self.listing.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
        else:
            self.listing.setSelectionMode(
                QAbstractItemView.SelectionMode.SingleSelection
            )

        if mode == FileMode.Directory:
            self.setNameFilters([self.tr("Directories")])

        self.__updateOkButton()

    def setNameFilters(self, filters):
        """
        Public method to set the list of file/directory name filters.

        @param filters list of filter expressions
            ("filter_name (pattern1 ... patternN)")
        @type list of str
        """
        self.__filters = []
        for f in filters:
            if " (" in f and ")" in f:
                self.__filters.append(f.split(" (", 1)[1].split(")", 1)[0].split())
            elif f:
                self.__filters.append(f)

        self.filterCombo.clear()
        self.filterCombo.addItems([f for f in filters if f])

    def setNameFilter(self, filter):  # noqa: M132
        """
        Public method to set the current name filter.

        @param filter filter text to make current
        @type str
        """
        self.filterCombo.setCurrentText(filter)

    def setDirectoriesOnly(self, dirsOnly):
        """
        Public method to set a flag to just show directories.

        @param dirsOnly flag indicating to just show directories
        @type bool
        """
        self.__dirsOnly = dirsOnly

        filters = self.__filters[self.filterCombo.currentIndex()]
        self.__filterList(filters)

    def __addToHistory(self, entry):
        """
        Private method to add a directory to the history list.

        @param entry name of the directory to be added
        @type str
        """
        try:
            # is in the history already?
            index = self.__history.index(entry)
            self.__currentHistoryIndex = index
        except ValueError:
            # new entry
            self.__history.append(entry)
            self.__currentHistoryIndex = len(self.__history) - 1

        self.__updateHistoryButtons()

    @pyqtSlot()
    def __updateHistoryButtons(self):
        """
        Private method to update the enabled state of the back and forward buttons.
        """
        if not self.__history:
            self.backButton.setEnabled(False)
            self.forwardButton.setEnabled(False)
        else:
            self.backButton.setEnabled(self.__currentHistoryIndex > 0)
            self.forwardButton.setEnabled(
                self.__currentHistoryIndex < len(self.__history) - 1
            )

    @pyqtSlot()
    def on_backButton_clicked(self):
        """
        Private slot to move back in history of visited directories.
        """
        self.setDirectory(self.__history[self.__currentHistoryIndex - 1])

    @pyqtSlot()
    def on_forwardButton_clicked(self):
        """
        Private slot to move forward in history of visited directories.
        """
        self.setDirectory(self.__history[self.__currentHistoryIndex + 1])

    @pyqtSlot()
    def __updateUpButton(self):
        """
        Private slot to update the enabled state of the 'Up' button.
        """
        self.upButton.setEnabled(
            self.treeCombo.currentIndex() < self.treeCombo.count() - 1
        )

    @pyqtSlot()
    def on_upButton_clicked(self):
        """
        Private slot to move up one level in the hierarchy.
        """
        self.treeCombo.setCurrentIndex(self.treeCombo.currentIndex() + 1)

    @pyqtSlot()
    def on_newDirButton_clicked(self):
        """
        Private slot to create a new directory.
        """
        newDir, ok = QInputDialog.getText(
            self,
            self.tr("New Directory"),
            self.tr("Enter the name for the new directory:"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and newDir:
            if newDir in self.__directoryCache or newDir in self.__filenameCache:
                EricMessageBox.warning(
                    self,
                    self.tr("New Directory"),
                    self.tr(
                        "<p>A file or directory with the name <b>{0}</b> exists"
                        " already. Aborting...</p>"
                    ).format(newDir),
                )
                return

            ok, error = self.__fsInterface.mkdir(self.__getFullPath(newDir))
            if ok:
                # refresh
                self.__reload()
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("New Directory"),
                    self.tr(
                        "<p>The directory <b>{0}</b> could not be created.</p>"
                        "<p>Reason: {1}</p>"
                    ).format(
                        self.__getFullPath(newDir),
                        error if error else self.tr("Unknown"),
                    ),
                )

    @pyqtSlot()
    def __reload(self):
        """
        Private slot to reload the directory listing.
        """
        self.setDirectory(self.treeCombo.currentText())

    @pyqtSlot(QTreeWidgetItem, int)
    def on_listing_itemActivated(self, item, column):
        """
        Private slot to handle the activation of an item in the list.

        @param item reference to the activated item
        @type QTreeWidgetItem
        @param column column number (unused)
        @type int
        """
        if item.data(0, EricServerFileDialog.IsDirectoryRole):
            self.setDirectory(self.__getFullPath(item.text(0)))
        else:
            self.accept()

    @pyqtSlot()
    def on_listing_itemSelectionChanged(self):
        """
        Private slot to handle the selection of listed items.
        """
        for itm in self.listing.selectedItems():
            if itm.data(0, EricServerFileDialog.IsDirectoryRole):
                self.__selectedDirectory = itm.text(0)
                break
        else:
            self.__selectedDirectory = None

        selectedNames = []
        selectedItems = self.listing.selectedItems()
        for itm in selectedItems:
            isDir = itm.data(0, EricServerFileDialog.IsDirectoryRole)
            if self.__fileMode == FileMode.Directory and isDir:
                selectedNames.append(itm.text(0))
            elif not isDir:
                selectedNames.append(itm.text(0))

        blocked = self.nameEdit.blockSignals(True)
        if len(selectedNames) == 1:
            self.nameEdit.setText(selectedNames[0])
        elif len(selectedNames) > 1:
            self.nameEdit.setText('"{0}"'.format('" "'.join(selectedNames)))
        self.nameEdit.blockSignals(blocked)

        self.__updateOkButton()

    @pyqtSlot()
    def __nameCompleterActivated(self):
        """
        Private slot handling the activation of the completer.
        """
        if self.okButton.isEnabled():
            self.okButton.animateClick()

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, name):
        """
        Private slot handling the editing of a file or directory name.

        @param name current text of the name edit
        @type str
        """
        self.listing.clearSelection()
        items = self.listing.findItems(name, Qt.MatchFlag.MatchExactly)
        for itm in items:
            itm.setSelected(True)

        self.__updateOkButton()

    def __getNames(self):
        """
        Private method to get the selected names list.

        @return list containing the selected names
        @rtype list of str
        """
        namesStr = self.nameEdit.text()
        if namesStr.startswith('"'):
            namesStr = namesStr[1:]
        if namesStr.endswith('"'):
            namesStr = namesStr[:-1]
        names = re.split(r'"\s+"', namesStr)
        return names

    def __getFullPath(self, name):
        """
        Private method to get the full path for a given file or directory name.

        @param name name of the file or directory
        @type str
        @return full path of the file or directory
        @rtype str
        """
        return "{0}{1}{2}".format(self.treeCombo.currentText(), self.__sep, name)

    @pyqtSlot()
    def __updateOkButton(self):
        """
        Private slot to set the 'OK' button state, icon and label.
        """
        # 1. adjust icon and label
        if (
            self.__acceptMode == AcceptMode.AcceptOpen
            or self.__selectedDirectory is not None
        ):
            self.okButton.setIcon(EricPixmapCache.getIcon("dialog-ok"))
            if self.__fileMode != FileMode.Directory:
                self.okButton.setText(self.tr("Open"))
            else:
                self.okButton.setText(self.tr("Choose"))
        else:
            self.okButton.setIcon(EricPixmapCache.getIcon("fileSave"))
            self.okButton.setText(self.tr("Save"))

        # 2. adjust enabled state
        if self.__selectedDirectory and self.__fileMode != FileMode.Directory:
            self.okButton.setEnabled(True)
        elif self.__fileMode == FileMode.AnyFile:
            self.okButton.setEnabled(bool(self.nameEdit.text()))
        elif self.__fileMode == FileMode.ExistingFile:
            self.okButton.setEnabled(self.nameEdit.text() in self.__filenameCache)
        elif self.__fileMode == FileMode.ExistingFiles:
            names = self.__getNames()
            self.okButton.setEnabled(all(n in self.__filenameCache for n in names))
        elif self.__fileMode == FileMode.Directory:
            self.okButton.setEnabled(True)
        else:
            self.okButton.setEnabled(False)

    @pyqtSlot()
    def on_okButton_clicked(self):
        """
        Private slot handling the press of the OK button.
        """
        if self.__selectedDirectory and self.__fileMode != FileMode.Directory:
            self.setDirectory(self.__getFullPath(self.__selectedDirectory))
        else:
            self.accept()

    @pyqtSlot(int)
    def on_filterCombo_currentIndexChanged(self, index):
        """
        Private slot handling the selection of a new file filter..

        @param index index of the selected entry
        @type int
        """
        filters = self.__filters[index]
        self.__filterList(filters)

    @pyqtSlot(str)
    def setDirectory(self, directory):
        """
        Public slot to set the current directory and populate the tree list.

        @param directory directory to be set as current. An empty directory sets the
            server's current directory.
        @type str
        """
        self.__filenameCache.clear()
        self.__directoryCache.clear()

        if self.__fsInterface.isfile(directory):
            directory, basename = self.__fsInterface.split(directory)
        else:
            basename = ""

        try:
            directory, sep, dirListing = self.__fsInterface.listdir(directory)

            self.__sep = sep

            # 1. populate the directory tree combo box
            self.treeCombo.blockSignals(True)
            self.treeCombo.clear()
            if len(directory) > 1 and directory.endswith(sep):
                directory = directory[:-1]
            if len(directory) > 2 and directory[1] == ":":
                # starts with a Windows drive letter
                directory = directory[2:]
            if sep:
                directoryParts = directory.split(sep)
                while directoryParts:
                    if directoryParts[-1]:
                        self.treeCombo.addItem(sep.join(directoryParts))
                    directoryParts.pop()
                self.treeCombo.addItem(sep)
            self.treeCombo.blockSignals(False)

            # 2. populate the directory listing
            self.listing.clear()
            for dirEntry in sorted(
                dirListing,
                key=lambda d: (
                    " " + d["name"].lower() if d["is_dir"] else d["name"].lower()
                ),
            ):
                if dirEntry["is_dir"]:
                    type_ = self.tr("Directory")
                    iconName = "dirClosed"
                    sizeStr = ""
                    self.__directoryCache.append(dirEntry["name"])
                else:
                    type_ = self.tr("File")
                    iconName = self.__iconProvider.fileIconName(dirEntry["name"])
                    sizeStr = dataString(dirEntry["size"], QLocale.system())
                    self.__filenameCache.append(dirEntry["name"])
                itm = QTreeWidgetItem(
                    self.listing,
                    [dirEntry["name"], sizeStr, type_, dirEntry["mtime_str"]],
                )
                itm.setIcon(0, EricPixmapCache.getIcon(iconName))
                itm.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)
                itm.setTextAlignment(2, Qt.AlignmentFlag.AlignHCenter)
                itm.setData(0, EricServerFileDialog.IsDirectoryRole, dirEntry["is_dir"])

            currentFilterIndex = self.filterCombo.currentIndex()
            filters = (
                [] if currentFilterIndex == -1 else self.__filters[currentFilterIndex]
            )
            self.__filterList(filters)

            # 3. add the directory to the history
            self.__addToHistory(directory)

        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Remote Directory Listing"),
                self.tr(
                    "<p>The directory <b>{0}</b> could not be listed due to an error"
                    " reported by the eric-ide server.</p><p>Reason: {1}</p>"
                ).format(directory, str(err)),
            )

        # 4. update some dependent states
        if basename:
            self.nameEdit.setText(basename)
        else:
            self.nameEdit.clear()
        self.__updateUpButton()

    @pyqtSlot(QPoint)
    def on_listing_customContextMenuRequested(self, pos):
        """
        Private slot to show a context menu.

        @param pos mouse pointer position to show the menu at
        @type QPoint
        """
        self.__contextMenu.clear()

        itm = self.listing.itemAt(pos)
        if itm is not None:
            self.__contextMenu.addAction(
                self.tr("Rename"), lambda: self.__renameItem(itm)
            )
            self.__contextMenu.addAction(
                self.tr("Delete"), lambda: self.__deleteItem(itm)
            )
            self.__contextMenu.addSeparator()
        act = self.__contextMenu.addAction(self.tr("Show Hidden Files"))
        act.setCheckable(True)
        act.setChecked(self.__showHidden)
        act.toggled.connect(self.__showHiddenToggled)
        self.__contextMenu.addAction(
            self.tr("New Directory"), self.on_newDirButton_clicked
        )

        self.__contextMenu.popup(self.listing.mapToGlobal(pos))

    @pyqtSlot(QTreeWidgetItem)
    def __renameItem(self, item):
        """
        Private slot to rename the given file/directory item.

        @param item reference to the item to be renamed
        @type QTreeWidgetItem
        """
        title = (
            self.tr("Rename Directory")
            if item.data(0, EricServerFileDialog.IsDirectoryRole)
            else self.tr("Rename File")
        )

        newName, ok = QInputDialog.getText(
            self,
            title,
            self.tr("<p>Enter the new name for <b>{0}</b>:</p>").format(item.text(0)),
            QLineEdit.EchoMode.Normal,
            item.text(0),
        )
        if ok and newName:
            if newName in self.__directoryCache or newName in self.__filenameCache:
                EricMessageBox.warning(
                    self,
                    title,
                    self.tr(
                        "<p>A file or directory with the name <b>{0}</b> exists"
                        " already. Aborting...</p>"
                    ).format(newName),
                )
                return

            ok, error = self.__fsInterface.replace(
                self.__getFullPath(item.text(0)), self.__getFullPath(newName)
            )
            if ok:
                # refresh
                self.__reload()
            else:
                EricMessageBox.critical(
                    self,
                    title,
                    self.tr(
                        "<p>The renaming operation failed.</p><p>Reason: {0}</p>"
                    ).format(error if error else self.tr("Unknown")),
                )

    @pyqtSlot(QTreeWidgetItem)
    def __deleteItem(self, item):
        """
        Private slot to delete the given file/directory  item.

        @param item reference to the item to be deleted
        @type QTreeWidgetItem
        """
        isDir = item.data(0, EricServerFileDialog.IsDirectoryRole)
        if isDir:
            title = self.tr("Delete Directory")
            question = self.tr("Shall the selected directory really be deleted?")
        else:
            title = self.tr("Delete File")
            question = self.tr("Shall the selected file really be deleted?")

        yes = EricMessageBox.yesNo(self, title, question)
        if yes:
            ok, error = (
                self.__fsInterface.rmdir(self.__getFullPath(item.text(0)))
                if isDir
                else self.__fsInterface.remove(self.__getFullPath(item.text(0)))
            )
            if ok:
                # refresh
                self.__reload()
            else:
                EricMessageBox.critical(
                    self,
                    title,
                    self.tr(
                        "<p>The deletion operation failed.</p><p>Reason: {0}</p>"
                    ).format(error if error else self.tr("Unknown")),
                )

    @pyqtSlot(bool)
    def __showHiddenToggled(self, on):
        """
        Private slot to handle toggling the display of hidden files/directories.

        @param on flag indicating to show hidden files and directories
        @type bool
        """
        self.__showHidden = on
        filters = self.__filters[self.filterCombo.currentIndex()]
        self.__filterList(filters)

    def selectedFiles(self):
        """
        Public method to get the selected files or the current viewport path.

        @return selected files or current viewport path
        @rtype str
        """
        if self.__fileMode == FileMode.Directory and not self.nameEdit.text():
            return [self.treeCombo.currentText()]
        else:
            return [self.__getFullPath(n) for n in self.__getNames()]

    def selectedNameFilter(self):
        """
        Public method to get the selected name filter.

        @return selected name filter
        @rtype str
        """
        return self.filterCombo.currentText()

    def __isHidden(self, name):
        """
        Private method to check, if the given name is indicating a hidden file or
        directory.

        @param name name of the file or directory
        @type str
        @return flag indicating a hidden file or directory
        @rtype bool
        """
        return name.startswith(".") or name.endswith("~")

    def __filterList(self, filters):
        """
        Private method to filter the files and directories list based on the given
        filters and whether hidden files/directories should be shown.

        @param filters list of filter patterns (only applied to files
        @type list of str
        """
        self.listing.clearSelection()
        for row in range(self.listing.topLevelItemCount()):
            itm = self.listing.topLevelItem(row)
            name = itm.text(0)
            if self.__dirsOnly and not itm.data(
                0, EricServerFileDialog.IsDirectoryRole
            ):
                itm.setHidden(True)
            elif not self.__showHidden and self.__isHidden(name):
                # applies to files and directories
                itm.setHidden(True)
            elif not itm.data(0, EricServerFileDialog.IsDirectoryRole):
                # it is a file item, apply the filter
                itm.setHidden(not any(fnmatch.fnmatch(name, pat) for pat in filters))
            else:
                itm.setHidden(False)

        # resize the columns
        for column in range(4):
            self.listing.resizeColumnToContents(column)


###########################################################################
## Module functions mimicing the interface of EricFileDialog/QFileDialog
###########################################################################


def getOpenFileName(
    parent=None,
    caption="",
    directory="",
    filterStr="",
    initialFilter="",
    withRemote=True,
):
    """
    Module function to get the name of a file for opening it.

    @param parent parent widget of the dialog (defaults to None)
    @type QWidget (optional)
    @param caption window title of the dialog (defaults to "")
    @type str (optional)
    @param directory working directory of the dialog (defaults to "")
    @type str (optional)
    @param filterStr filter string for the dialog (defaults to "")
    @type str (optional)
    @param initialFilter initial filter for the dialog (defaults to "")
    @type str (optional)
    @param withRemote flag indicating to create the file names with the remote
        indicator (defaults to True)
    @type bool (optional)
    @return name of file to be opened
    @rtype str
    """
    return getOpenFileNameAndFilter(
        parent, caption, directory, filterStr, initialFilter, withRemote
    )[0]


def getOpenFileNameAndFilter(
    parent=None,
    caption="",
    directory="",
    filterStr="",
    initialFilter="",
    withRemote=True,
):
    """
    Module function to get the name of a file for opening it and the selected
    file name filter.

    @param parent parent widget of the dialog (defaults to None)
    @type QWidget (optional)
    @param caption window title of the dialog (defaults to "")
    @type str (optional)
    @param directory working directory of the dialog (defaults to "")
    @type str (optional)
    @param filterStr filter string for the dialog (defaults to "")
    @type str (optional)
    @param initialFilter initial filter for the dialog (defaults to "")
    @type str (optional)
    @param withRemote flag indicating to create the file names with the remote
        indicator (defaults to True)
    @type bool (optional)
    @return tuple containing the list of file names to be opened and the
        selected file name filter
    @rtype tuple of (list of str, str)
    """
    dlg = EricServerFileDialog(
        parent=parent, caption=caption, directory=directory, filter=filterStr
    )
    dlg.setFileMode(FileMode.ExistingFile)
    dlg.setNameFilter(initialFilter)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        if withRemote:
            fileName = FileSystemUtilities.remoteFileName(dlg.selectedFiles()[0])
        else:
            fileName = dlg.selectedFiles()[0]
        selectedFilter = dlg.selectedNameFilter()
    else:
        fileName = ""
        selectedFilter = ""

    return fileName, selectedFilter


def getOpenFileNames(
    parent=None,
    caption="",
    directory="",
    filterStr="",
    initialFilter="",
    withRemote=True,
):
    """
    Module function to get a list of names of files for opening.

    @param parent parent widget of the dialog (defaults to None)
    @type QWidget (optional)
    @param caption window title of the dialog (defaults to "")
    @type str (optional)
    @param directory working directory of the dialog (defaults to "")
    @type str (optional)
    @param filterStr filter string for the dialog (defaults to "")
    @type str (optional)
    @param initialFilter initial filter for the dialog (defaults to "")
    @type str (optional)
    @param withRemote flag indicating to create the file names with the remote
        indicator (defaults to True)
    @type bool (optional)
    @return list of file names to be opened
    @rtype list of str
    """
    return getOpenFileNamesAndFilter(
        parent, caption, directory, filterStr, initialFilter, withRemote
    )[0]


def getOpenFileNamesAndFilter(
    parent=None,
    caption="",
    directory="",
    filterStr="",
    initialFilter="",
    withRemote=True,
):
    """
    Module function to get a list of names of files for opening and the
    selected file name filter.

    @param parent parent widget of the dialog (defaults to None)
    @type QWidget (optional)
    @param caption window title of the dialog (defaults to "")
    @type str (optional)
    @param directory working directory of the dialog (defaults to "")
    @type str (optional)
    @param filterStr filter string for the dialog (defaults to "")
    @type str (optional)
    @param initialFilter initial filter for the dialog (defaults to "")
    @type str (optional)
    @param withRemote flag indicating to create the file names with the remote
        indicator (defaults to True)
    @type bool (optional)
    @return tuple containing the list of file names to be opened and the
        selected file name filter
    @rtype tuple of (list of str, str)
    """
    dlg = EricServerFileDialog(
        parent=parent, caption=caption, directory=directory, filter=filterStr
    )
    dlg.setFileMode(FileMode.ExistingFiles)
    dlg.setNameFilter(initialFilter)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        if withRemote:
            filesList = [
                FileSystemUtilities.remoteFileName(f) for f in dlg.selectedFiles()
            ]
        else:
            filesList = dlg.selectedFiles()
        selectedFilter = dlg.selectedNameFilter()
    else:
        filesList = []
        selectedFilter = ""

    return filesList, selectedFilter


def getSaveFileName(
    parent=None,
    caption="",
    directory="",
    filterStr="",
    initialFilter="",
    withRemote=True,
):
    """
    Module function to get the name of a file for saving.

    @param parent parent widget of the dialog (defaults to None)
    @type QWidget (optional)
    @param caption window title of the dialog (defaults to "")
    @type str (optional)
    @param directory working directory of the dialog (defaults to "")
    @type str (optional)
    @param filterStr filter string for the dialog (defaults to "")
    @type str (optional)
    @param initialFilter initial filter for the dialog (defaults to "")
    @type str (optional)
    @param withRemote flag indicating to create the file names with the remote
        indicator (defaults to True)
    @type bool (optional)
    @return name of file to be saved
    @rtype str
    """
    return getSaveFileNameAndFilter(
        parent, caption, directory, filterStr, initialFilter, withRemote
    )[0]


def getSaveFileNameAndFilter(
    parent=None,
    caption="",
    directory="",
    filterStr="",
    initialFilter="",
    withRemote=True,
):
    """
    Module function to get the name of a file for saving and the selected file name
    filter.

    @param parent parent widget of the dialog (defaults to None)
    @type QWidget (optional)
    @param caption window title of the dialog (defaults to "")
    @type str (optional)
    @param directory working directory of the dialog (defaults to "")
    @type str (optional)
    @param filterStr filter string for the dialog (defaults to "")
    @type str (optional)
    @param initialFilter initial filter for the dialog (defaults to "")
    @type str (optional)
    @param withRemote flag indicating to create the file names with the remote
        indicator (defaults to True)
    @type bool (optional)
    @return name of file to be saved and selected filte
    @rtype tuple of (str, str)
    """
    dlg = EricServerFileDialog(
        parent=parent, caption=caption, directory=directory, filter=filterStr
    )
    dlg.setFileMode(FileMode.AnyFile)
    dlg.setNameFilter(initialFilter)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        if withRemote:
            fileName = FileSystemUtilities.remoteFileName(dlg.selectedFiles()[0])
        else:
            fileName = dlg.selectedFiles()[0]
        selectedFilter = dlg.selectedNameFilter()
    else:
        fileName = ""
        selectedFilter = ""

    return fileName, selectedFilter


def getExistingDirectory(
    parent=None, caption="", directory="", dirsOnly=True, withRemote=True
):
    """
    Module function to get the name of a directory.

    @param parent parent widget of the dialog (defaults to None)
    @type QWidget (optional)
    @param caption window title of the dialog (defaults to "")
    @type str (optional)
    @param directory working directory of the dialog (defaults to "")
    @type str (optional)
    @param dirsOnly flag indicating to just show directories (defaults to True)
    @type bool (optional)
    @param withRemote flag indicating to create the file names with the remote
        indicator (defaults to True)
    @type bool (optional)
    @return name of selected directory
    @rtype str
    """
    dlg = EricServerFileDialog(parent=parent, caption=caption, directory=directory)
    dlg.setFileMode(FileMode.Directory)
    dlg.setDirectoriesOnly(dirsOnly)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        if withRemote:
            dirName = FileSystemUtilities.remoteFileName(dlg.selectedFiles()[0])
        else:
            dirName = dlg.selectedFiles()[0]
    else:
        dirName = ""

    return dirName
