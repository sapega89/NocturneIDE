# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the browser model.
"""

import contextlib
import enum
import fnmatch
import json
import os

from PyQt6.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QDir,
    QModelIndex,
    QProcess,
    Qt,
)
from PyQt6.QtGui import QFont, QImageReader
from PyQt6.QtWidgets import QApplication

from eric7 import Preferences
from eric7.EricCore import EricFileSystemWatcher
from eric7.EricGui import EricPixmapCache
from eric7.SystemUtilities import FileSystemUtilities
from eric7.Utilities import ClassBrowsers
from eric7.Utilities.ClassBrowsers import ClbrBaseClasses


class BrowserItemType(enum.Enum):
    """
    Class defining the various browser item types.
    """

    # Base types used everywhere
    Root = 0
    SimpleDirectory = 1
    Directory = 2
    SysPath = 3
    File = 4
    Class = 5
    Method = 6
    Attributes = 7
    Attribute = 8
    Coding = 9
    Imports = 10
    Import = 11

    # Types used by the project browser model
    PbSimpleDirectory = 100
    PbDirectory = 101
    PbFile = 102


class BrowserModelType(enum.Enum):
    """
    Class defining the various browser model types.
    """

    Generic = 0
    Project = 1
    EditorOutline = 2


class BrowserModel(QAbstractItemModel):
    """
    Class implementing the browser model.
    """

    def __init__(
        self,
        parent=None,
        nopopulate=False,
        fsInterface=None,
        modelType=BrowserModelType.Generic,
    ):
        """
        Constructor

        @param parent reference to parent object (defaults to None)
        @type QObject (optional)
        @param nopopulate flag indicating to not populate the model (defaults to False)
        @type bool (optional)
        @param fsInterface reference to the 'eric-ide' server interface object
            (defaults to None)
        @type EricServerFileSystemInterface (optional)
        @param modelType type of the browser model (defaults to
            BrowserModelType.Generic)
        @type BrowserModelType (optional)
        """
        super().__init__(parent)

        self.progDir = None

        self.__sysPathInterpreter = ""
        self.__sysPathItem = None

        self.__remotefsInterface = fsInterface
        self._modelType = modelType

        if not nopopulate:
            self.watchedDirItems = {}
            self.watchedFileItems = {}
            watcher = EricFileSystemWatcher.instance()
            watcher.directoryCreated.connect(lambda x: self.entryCreated(x, isDir=True))
            watcher.directoryDeleted.connect(lambda x: self.entryDeleted(x, isDir=True))
            watcher.fileCreated.connect(lambda x: self.entryCreated(x, isDir=False))
            watcher.fileDeleted.connect(lambda x: self.entryDeleted(x, isDir=False))
            watcher.fileModified.connect(self.fileChanged)

            rootData = QCoreApplication.translate("BrowserModel", "Name")
            self.rootItem = BrowserItem(None, rootData)

            self.__populateModel()

    def columnCount(self, parent=None):
        """
        Public method to get the number of columns.

        @param parent index of parent item
        @type QModelIndex
        @return number of columns
        @rtype int
        """
        if parent is None:
            parent = QModelIndex()

        item = parent.internalPointer() if parent.isValid() else self.rootItem

        return item.columnCount()

    def data(self, index, role):
        """
        Public method to get data of an item.

        @param index index of the data to retrieve
        @type QModelIndex
        @param role role of data
        @type Qt.ItemDataRole
        @return requested data
        @rtype Any
        """
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            item = index.internalPointer()
            if index.column() < item.columnCount():
                return item.data(index.column())
            elif (
                index.column() == item.columnCount()
                and index.column() < self.columnCount(self.parent(index))
            ):
                # This is for the case where an item under a multi-column
                # parent doesn't have a value for all the columns
                return ""
        elif role == Qt.ItemDataRole.DecorationRole:
            if index.column() == 0:
                return index.internalPointer().getIcon()
        elif role == Qt.ItemDataRole.FontRole:
            item = index.internalPointer()
            if item.isSymlink():
                font = QFont(QApplication.font("QTreeView"))
                font.setItalic(True)
                return font
            elif item.isRemote():
                font = QFont(QApplication.font("QTreeView"))
                font.setUnderline(True)
                return font
        elif role == Qt.ItemDataRole.ToolTipRole:
            return index.internalPointer().getRemoteInfo()

        return None

    def flags(self, index):
        """
        Public method to get the item flags.

        @param index index of the data to retrieve
        @type QModelIndex
        @return requested flags
        @rtype Qt.ItemFlags
        """
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get the header data.

        @param section number of section to get data for
        @type int
        @param orientation header orientation
        @type Qt.Orientation
        @param role role of data
        @type Qt.ItemDataRole
        @return requested header data
        @rtype Any
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            if section >= self.rootItem.columnCount():
                return ""
            else:
                return self.rootItem.data(section)

        return None

    def index(self, row, column, parent=None):
        """
        Public method to create an index.

        @param row row number of the new index
        @type int
        @param column column number of the new index
        @type int
        @param parent index of parent item
        @type QModelIndex
        @return index object
        @rtype QModelIndex
        """
        if parent is None:
            parent = QModelIndex()

        # The model/view framework considers negative values out-of-bounds,
        # however in python they work when indexing into lists. So make sure
        # we return an invalid index for out-of-bounds row/col
        if (
            row < 0
            or column < 0
            or row >= self.rowCount(parent)
            or column >= self.columnCount(parent)
        ):
            return QModelIndex()

        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem

        try:
            if not parentItem.isPopulated():
                self.populateItem(parentItem)
            childItem = parentItem.child(row)
        except IndexError:
            childItem = None
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        """
        Public method to get the index of the parent object.

        @param index index of the item
        @type QModelIndex
        @return index of parent item
        @rtype QModelIndex
        """
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem is None or parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=None):
        """
        Public method to get the number of rows.

        @param parent index of parent item
        @type QModelIndex
        @return number of rows
        @rtype int
        """
        if parent is None:
            parent = QModelIndex()

        # Only the first column should have children
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
            if not parentItem.isPopulated():  # lazy population
                self.populateItem(parentItem)

        return parentItem.childCount()

    def hasChildren(self, parent=None):
        """
        Public method to check for the presence of child items.

        We always return True for normal items in order to do lazy
        population of the tree.

        @param parent index of parent item
        @type QModelIndex
        @return flag indicating the presence of child items
        @rtype bool
        """
        if parent is None:
            parent = QModelIndex()

        # Only the first column should have children
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return self.rootItem.childCount() > 0

        if parent.internalPointer().isLazyPopulated():
            return True
        else:
            return parent.internalPointer().childCount() > 0

    def clear(self):
        """
        Public method to clear the model.
        """
        self.beginResetModel()
        self.rootItem.removeChildren()
        self.endResetModel()

    def item(self, index):
        """
        Public method to get a reference to an item.

        @param index index of the data to retrieve
        @type QModelIndex
        @return requested item reference
        @rtype BrowserItem
        """
        if not index.isValid():
            return None

        return index.internalPointer()

    def _addWatchedItem(self, itm):
        """
        Protected method to watch an item.

        @param itm item to be watched
        @type BrowserDirectoryItem
        """
        if isinstance(itm, BrowserDirectoryItem):
            dirName = itm.dirName()
            if (
                dirName != ""
                and not FileSystemUtilities.isRemoteFileName(dirName)
                and not dirName.startswith(("//", "\\\\"))
            ):
                EricFileSystemWatcher.instance().addPath(dirName)
                if dirName in self.watchedDirItems:
                    if itm not in self.watchedDirItems[dirName]:
                        self.watchedDirItems[dirName].append(itm)
                else:
                    self.watchedDirItems[dirName] = [itm]

    def _removeWatchedItem(self, itm):
        """
        Protected method to remove a watched item.

        @param itm item to be removed
        @type BrowserDirectoryItem
        """
        if isinstance(itm, BrowserDirectoryItem):
            dirName = itm.dirName()
            with contextlib.suppress(KeyError):
                with contextlib.suppress(ValueError):
                    self.watchedDirItems[dirName].remove(itm)
                if len(self.watchedDirItems[dirName]) == 0:
                    del self.watchedDirItems[dirName]
                    EricFileSystemWatcher.instance().removePath(dirName)

    def entryCreated(self, path, isDir=False):
        """
        Public method to handle the creation of a file or directory.

        @param path path of the created file or directory
        @type str
        @param isDir flag indicating a created directory (defaults to False)
        @type bool (optional)
        """
        parentPath = os.path.dirname(path)
        if parentPath not in self.watchedDirItems:
            # just ignore the situation we don't have a reference to the item
            return

        for itm in self.watchedDirItems[parentPath]:
            cnt = itm.childCount()
            self.beginInsertRows(self.createIndex(itm.row(), 0, itm), cnt, cnt)
            node = (
                BrowserDirectoryItem(
                    itm,
                    FileSystemUtilities.toNativeSeparators(path),
                    False,
                )
                if isDir
                else BrowserFileItem(
                    itm,
                    FileSystemUtilities.toNativeSeparators(path),
                )
            )
            self._addItem(node, itm)
            self.endInsertRows()

    def entryDeleted(self, path, isDir=False):  # noqa: U100
        """
        Public method to handle the deletion of a file or directory.

        @param path path of the deleted file or directory
        @type str
        @param isDir flag indicating a deleted directory (defaults to False) (unused)
        @type bool (optional)
        @return flag indicating a deletion
        @rtype bool
        """
        parentPath = os.path.dirname(path)
        if parentPath not in self.watchedDirItems:
            # just ignore the situation we don't have a reference to the item
            return False

        for itm in self.watchedDirItems[parentPath]:
            for row in range(itm.childCount() - 1, -1, -1):
                child = itm.child(row)
                if child.name() == path:
                    self._removeWatchedItem(child)
                    self.beginRemoveRows(self.createIndex(itm.row(), 0, itm), row, row)
                    itm.removeChild(child)
                    self.endRemoveRows()
                    return True

        return False

    def refreshDirectory(self, index):
        """
        Public method to refresh the directory with the given index.

        @param index index of the directory item
        @type QModelIndex
        """
        item = self.item(index)
        self.beginRemoveRows(index, 0, item.childCount() - 1)
        item.removeChildren()
        item._populated = False
        self.endRemoveRows()
        self.populateItem(item, repopulate=True)

    def __populateModel(self):
        """
        Private method to populate the browser model.
        """
        self.toplevelDirs = []
        tdp = Preferences.getSettings().value("BrowserModel/ToplevelDirs")
        if tdp:
            self.toplevelDirs = tdp
        else:
            self.toplevelDirs.append(
                FileSystemUtilities.toNativeSeparators(QDir.homePath())
            )
            for d in QDir.drives():
                self.toplevelDirs.append(
                    FileSystemUtilities.toNativeSeparators(d.absoluteFilePath())
                )

        for d in self.toplevelDirs:
            itm = BrowserDirectoryItem(
                self.rootItem, d, fsInterface=self.__remotefsInterface
            )
            self._addItem(itm, self.rootItem)

    def interpreterChanged(self, interpreter):
        """
        Public method to handle a change of the debug client's interpreter.

        @param interpreter interpreter of the debug client
        @type str
        """
        if interpreter and "python" in interpreter.lower():
            if interpreter.endswith("w.exe"):
                interpreter = interpreter.replace("w.exe", ".exe")
            if self.__sysPathInterpreter != interpreter:
                self.__sysPathInterpreter = interpreter
                # step 1: remove sys.path entry
                if self.__sysPathItem is not None:
                    self.beginRemoveRows(
                        QModelIndex(),
                        self.__sysPathItem.row(),
                        self.__sysPathItem.row(),
                    )
                    self.rootItem.removeChild(self.__sysPathItem)
                    self.endRemoveRows()
                    self.__sysPathItem = None

                if self.__sysPathInterpreter:
                    # step 2: add a new one
                    self.__sysPathItem = BrowserSysPathItem(self.rootItem)
                    self.addItem(self.__sysPathItem)
        else:
            # remove sys.path entry
            if self.__sysPathItem is not None:
                self.beginRemoveRows(
                    QModelIndex(), self.__sysPathItem.row(), self.__sysPathItem.row()
                )
                self.rootItem.removeChild(self.__sysPathItem)
                self.endRemoveRows()
                self.__sysPathItem = None
            self.__sysPathInterpreter = ""

    def programChange(self, dirname):
        """
        Public method to change the entry for the directory of file being
        debugged.

        @param dirname name of the directory containing the file
        @type str
        """
        if self.progDir:
            if dirname == self.progDir.dirName():
                return

            # remove old entry
            self._removeWatchedItem(self.progDir)
            self.beginRemoveRows(QModelIndex(), self.progDir.row(), self.progDir.row())
            self.rootItem.removeChild(self.progDir)
            self.endRemoveRows()
            self.progDir = None

        itm = BrowserDirectoryItem(
            self.rootItem, dirname, fsInterface=self.__remotefsInterface
        )
        self.addItem(itm)
        self.progDir = itm

    def addTopLevelDir(self, dirname):
        """
        Public method to add a new toplevel directory.

        If the directory does not contain a host connection info but is a remote
        directory, this info is added.

        @param dirname name of the new toplevel directory
        @type str
        """
        if FileSystemUtilities.isRemoteFileName(dirname) and "@@" not in dirname:
            dirname = (
                f"{dirname}@@{self.__remotefsInterface.serverInterface().getHost()}"
            )
        if dirname not in self.toplevelDirs:
            itm = BrowserDirectoryItem(
                self.rootItem, dirname, fsInterface=self.__remotefsInterface
            )
            self.addItem(itm)
            self.toplevelDirs.append(dirname)

    def removeToplevelDir(self, index):
        """
        Public method to remove a toplevel directory.

        @param index index of the toplevel directory to be removed
        @type QModelIndex
        """
        if not index.isValid():
            return

        item = index.internalPointer()
        self.beginRemoveRows(index.parent(), index.row(), index.row())
        self.rootItem.removeChild(item)
        self.endRemoveRows()

        with contextlib.suppress(ValueError):
            self.toplevelDirs.remove(item.dirName())
        self._removeWatchedItem(item)

    def saveToplevelDirs(self):
        """
        Public slot to save the toplevel directories.
        """
        Preferences.getSettings().setValue(
            "BrowserModel/ToplevelDirs", self.toplevelDirs
        )

    def _addItem(self, itm, parentItem):
        """
        Protected slot to add an item.

        @param itm reference to item to add
        @type BrowserItem
        @param parentItem reference to item to add to
        @type BrowserItem
        """
        parentItem.appendChild(itm)

    def addItem(self, itm, parent=None):
        """
        Public slot to add an item.

        @param itm item to add
        @type BrowserItem
        @param parent index of parent item
        @type QModelIndex
        """
        if parent is None:
            parent = QModelIndex()

        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem

        cnt = parentItem.childCount()
        self.beginInsertRows(parent, cnt, cnt)
        self._addItem(itm, parentItem)
        self.endInsertRows()

    def populateItem(self, parentItem, repopulate=False):
        """
        Public method to populate an item's subtree.

        @param parentItem reference to the item to be populated
        @type BrowserItem
        @param repopulate flag indicating a repopulation
        @type bool
        """
        if parentItem.type() == BrowserItemType.Directory:
            self.populateDirectoryItem(parentItem, repopulate)
        elif parentItem.type() == BrowserItemType.SysPath:
            self.populateSysPathItem(parentItem, repopulate)
        elif parentItem.type() == BrowserItemType.File:
            self.populateFileItem(parentItem, repopulate)
        elif parentItem.type() == BrowserItemType.Class:
            self.populateClassItem(parentItem, repopulate)
        elif parentItem.type() == BrowserItemType.Method:
            self.populateMethodItem(parentItem, repopulate)
        elif parentItem.type() == BrowserItemType.Attributes:
            self.populateClassAttributesItem(parentItem, repopulate)

    def populateDirectoryItem(self, parentItem, repopulate=False):
        """
        Public method to populate a directory item's subtree.

        @param parentItem reference to the directory item to be populated
        @type BrowserDirectoryItem
        @param repopulate flag indicating a repopulation
        @type bool
        """
        self._addWatchedItem(parentItem)

        dirName = parentItem.dirName()
        if FileSystemUtilities.isPlainFileName(dirName):
            qdir = QDir(dirName)

            dirFilter = (
                QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.Hidden
            )
            entryInfoList = qdir.entryInfoList(dirFilter)
            if len(entryInfoList) > 0:
                if repopulate:
                    self.beginInsertRows(
                        self.createIndex(parentItem.row(), 0, parentItem),
                        0,
                        len(entryInfoList) - 1,
                    )
                for f in entryInfoList:
                    if f.isDir():
                        node = BrowserDirectoryItem(
                            parentItem,
                            FileSystemUtilities.toNativeSeparators(
                                f.absoluteFilePath()
                            ),
                            False,
                        )
                    else:
                        fileFilters = Preferences.getUI("BrowsersFileFilters").split(
                            ";"
                        )
                        if fileFilters:
                            fn = f.fileName()
                            if any(
                                fnmatch.fnmatch(fn, ff.strip()) for ff in fileFilters
                            ):
                                continue
                        node = BrowserFileItem(
                            parentItem,
                            FileSystemUtilities.toNativeSeparators(
                                f.absoluteFilePath()
                            ),
                        )
                    self._addItem(node, parentItem)
                if repopulate:
                    self.endInsertRows()

        elif FileSystemUtilities.isRemoteFileName(dirName):
            entriesList = self.__remotefsInterface.listdir(dirName)[2]
            if len(entriesList) > 0:
                if repopulate:
                    self.beginInsertRows(
                        self.createIndex(parentItem.row(), 0, parentItem),
                        0,
                        len(entriesList) - 1,
                    )
                for entry in entriesList:
                    if entry["is_dir"]:
                        node = BrowserDirectoryItem(
                            parentItem,
                            entry["path"],
                            False,
                            fsInterface=self.__remotefsInterface,
                        )
                    else:
                        fileFilters = Preferences.getUI("BrowsersFileFilters").split(
                            ";"
                        )
                        if fileFilters:
                            fn = entry["name"]
                            if any(
                                fnmatch.fnmatch(fn, ff.strip()) for ff in fileFilters
                            ):
                                continue
                        node = BrowserFileItem(
                            parentItem,
                            entry["path"],
                            fsInterface=self.__remotefsInterface,
                        )
                    self._addItem(node, parentItem)
                if repopulate:
                    self.endInsertRows()

    def populateSysPathItem(self, parentItem, repopulate=False):
        """
        Public method to populate a sys.path item's subtree.

        @param parentItem reference to the sys.path item to be populated
        @type BrowserSysPathItem
        @param repopulate flag indicating a repopulation
        @type bool
        """
        if self.__sysPathInterpreter:
            script = "import sys, json; print(json.dumps(sys.path))"
            proc = QProcess()
            proc.start(self.__sysPathInterpreter, ["-c", script])
            finished = proc.waitForFinished(3000)
            if finished:
                procOutput = str(
                    proc.readAllStandardOutput(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )
                syspath = [p for p in json.loads(procOutput) if p]
                if len(syspath) > 0:
                    if repopulate:
                        self.beginInsertRows(
                            self.createIndex(parentItem.row(), 0, parentItem),
                            0,
                            len(syspath) - 1,
                        )
                    for p in syspath:
                        node = (
                            BrowserDirectoryItem(parentItem, p)
                            if os.path.isdir(p)
                            else BrowserFileItem(parentItem, p)
                        )
                        self._addItem(node, parentItem)
                    if repopulate:
                        self.endInsertRows()
            else:
                proc.kill()

    def populateFileItem(self, parentItem, repopulate=False):
        """
        Public method to populate a file item's subtree.

        @param parentItem reference to the file item to be populated
        @type BrowserFileItem
        @param repopulate flag indicating a repopulation
        @type bool
        """
        from eric7.Utilities import ClassBrowsers

        moduleName = parentItem.moduleName()
        fileName = parentItem.fileName()
        try:
            dictionary = ClassBrowsers.readmodule(
                moduleName,
                [parentItem.dirName()],
                parentItem.isPython3File() or parentItem.isCythonFile(),
            )
        except ImportError:
            return

        if bool(dictionary):
            if repopulate:
                last = len(dictionary) - 1
                if "@@Coding@@" in dictionary and not Preferences.getUI(
                    "BrowserShowCoding"
                ):
                    last -= 1
                self.beginInsertRows(
                    self.createIndex(parentItem.row(), 0, parentItem), 0, last
                )

            for key in dictionary:
                if key.startswith("@@"):
                    # special treatment done later
                    continue
                cl = dictionary[key]
                with contextlib.suppress(AttributeError):
                    if cl.module == moduleName:
                        if isinstance(
                            cl, (ClbrBaseClasses.Class, ClbrBaseClasses.Module)
                        ):
                            node = BrowserClassItem(
                                parentItem, cl, fileName, modelType=self._modelType
                            )
                        elif isinstance(cl, ClbrBaseClasses.Function):
                            node = BrowserMethodItem(
                                parentItem, cl, fileName, modelType=self._modelType
                            )
                        else:
                            node = None
                        if node:
                            self._addItem(node, parentItem)
            if "@@Coding@@" in dictionary and Preferences.getUI("BrowserShowCoding"):
                node = BrowserCodingItem(
                    parentItem,
                    QCoreApplication.translate("BrowserModel", "Coding: {0}").format(
                        dictionary["@@Coding@@"].coding
                    ),
                    dictionary["@@Coding@@"].linenumber,
                )
                self._addItem(node, parentItem)
            if "@@Globals@@" in dictionary:
                node = BrowserGlobalsItem(
                    parentItem,
                    dictionary["@@Globals@@"].globals,
                    QCoreApplication.translate("BrowserModel", "Globals"),
                )
                self._addItem(node, parentItem)
            if "@@Import@@" in dictionary or "@@ImportFrom@@" in dictionary:
                node = BrowserImportsItem(
                    parentItem, QCoreApplication.translate("BrowserModel", "Imports")
                )
                self._addItem(node, parentItem)
                if "@@Import@@" in dictionary:
                    for importedModule in (
                        dictionary["@@Import@@"].getImports().values()
                    ):
                        m_node = BrowserImportItem(
                            node,
                            importedModule.importedModuleName,
                            importedModule.file,
                            importedModule.linenos,
                            modelType=self._modelType,
                        )
                        self._addItem(m_node, node)
                        for (
                            importedName,
                            linenos,
                        ) in importedModule.importedNames.items():
                            mn_node = BrowserImportItem(
                                m_node,
                                importedName,
                                importedModule.file,
                                linenos,
                                isModule=False,
                                modelType=self._modelType,
                            )
                            self._addItem(mn_node, m_node)

            if repopulate:
                self.endInsertRows()

        parentItem._populated = True
        if (
            parentItem.type_ == BrowserItemType.File
            and fileName not in self.watchedFileItems
        ):
            # watch the file only in the file browser not the project viewer
            watcher = EricFileSystemWatcher.instance()
            watcher.addPath(fileName)
            self.watchedFileItems[fileName] = parentItem

    def repopulateFileItem(self, itm):
        """
        Public method to repopulate a file item.

        @param itm reference to the item to be repopulated
        @type BrowserFileItem
        """
        if isinstance(itm, BrowserFileItem) and itm.isLazyPopulated():
            if not itm.isPopulated():
                # item is not populated yet, nothing to do
                return

            if itm.childCount():
                index = self.createIndex(itm.row(), 0, itm)
                self.beginRemoveRows(index, 0, itm.childCount() - 1)
                itm.removeChildren()
                self.endRemoveRows()

            self.populateFileItem(itm, True)

    def fileChanged(self, fileName):
        """
        Public method to react upon file changes.

        @param fileName path of the changed file
        @type str
        """
        if fileName in self.watchedFileItems:
            if os.path.exists(fileName):
                # the file was changed
                self.repopulateFileItem(self.watchedFileItems[fileName])
            else:
                # the file does not exist anymore
                watcher = EricFileSystemWatcher.instance()
                watcher.removePath(fileName)
                del self.watchedFileItems[fileName]

    def populateClassItem(self, parentItem, repopulate=False):
        """
        Public method to populate a class item's subtree.

        @param parentItem reference to the class item to be populated
        @type BrowserClassItem
        @param repopulate flag indicating a repopulation
        @type bool
        """
        cl = parentItem.classObject()
        file_ = parentItem.fileName()

        if cl is None:
            return

        # build sorted list of names
        keys = []
        for name in cl.classes:
            keys.append((name, "c"))
        for name in cl.methods:
            keys.append((name, "m"))

        if len(cl.attributes):
            node = BrowserClassAttributesItem(
                parentItem,
                cl.attributes,
                QCoreApplication.translate("BrowserModel", "Attributes"),
            )
            if repopulate:
                self.addItem(node, self.createIndex(parentItem.row(), 0, parentItem))
            else:
                self._addItem(node, parentItem)

        if len(cl.globals):
            node = BrowserClassAttributesItem(
                parentItem,
                cl.globals,
                QCoreApplication.translate("BrowserModel", "Class Attributes"),
                True,
            )
            if repopulate:
                self.addItem(node, self.createIndex(parentItem.row(), 0, parentItem))
            else:
                self._addItem(node, parentItem)

        if len(keys) > 0:
            if repopulate:
                self.beginInsertRows(
                    self.createIndex(parentItem.row(), 0, parentItem), 0, len(keys) - 1
                )
            for key, kind in keys:
                if kind == "c":
                    node = BrowserClassItem(
                        parentItem, cl.classes[key], file_, modelType=self._modelType
                    )
                elif kind == "m":
                    node = BrowserMethodItem(
                        parentItem, cl.methods[key], file_, modelType=self._modelType
                    )
                self._addItem(node, parentItem)
            if repopulate:
                self.endInsertRows()

    def populateMethodItem(self, parentItem, repopulate=False):
        """
        Public method to populate a method item's subtree.

        @param parentItem reference to the method item to be populated
        @type BrowserItem
        @param repopulate flag indicating a repopulation
        @type bool
        """
        fn = parentItem.functionObject()
        file_ = parentItem.fileName()

        if fn is None:
            return

        # build sorted list of names
        keys = []
        for name in fn.classes:
            keys.append((name, "c"))
        for name in fn.methods:
            keys.append((name, "m"))
        for name in fn.attributes:
            keys.append((name, "a"))

        if len(keys) > 0:
            if repopulate:
                self.beginInsertRows(
                    self.createIndex(parentItem.row(), 0, parentItem), 0, len(keys) - 1
                )
            for key, kind in keys:
                if kind == "c":
                    node = BrowserClassItem(
                        parentItem, fn.classes[key], file_, modelType=self._modelType
                    )
                elif kind == "m":
                    node = BrowserMethodItem(
                        parentItem, fn.methods[key], file_, modelType=self._modelType
                    )
                elif kind == "a":
                    node = BrowserClassAttributeItem(
                        parentItem, fn.attributes[key], modelType=self._modelType
                    )
                self._addItem(node, parentItem)
            if repopulate:
                self.endInsertRows()

    def populateClassAttributesItem(self, parentItem, repopulate=False):
        """
        Public method to populate a class attributes item's subtree.

        @param parentItem reference to the class attributes item to be
            populated
        @type BrowserClassAttributesItem
        @param repopulate flag indicating a repopulation
        @type bool
        """
        classAttributes = parentItem.isClassAttributes()
        attributes = parentItem.attributes()
        if not attributes:
            return

        keys = list(attributes)
        if len(keys) > 0:
            if repopulate:
                self.beginInsertRows(
                    self.createIndex(parentItem.row(), 0, parentItem), 0, len(keys) - 1
                )
            for key in keys:
                node = BrowserClassAttributeItem(
                    parentItem,
                    attributes[key],
                    classAttributes,
                    modelType=self._modelType,
                )
                self._addItem(node, parentItem)
            if repopulate:
                self.endInsertRows()


class BrowserItem:
    """
    Class implementing the data structure for browser items.
    """

    def __init__(self, parent, data):
        """
        Constructor

        @param parent reference to the parent item
        @type BrowserItem
        @param data single data of the item
        @type Any
        """
        self.childItems = []

        self.parentItem = parent
        self.itemData = [data]
        self.type_ = BrowserItemType.Root
        self.icon = EricPixmapCache.getIcon("empty")
        self._populated = True
        self._lazyPopulation = False
        self.symlink = False
        self.remote = False
        self.remoteInfo = ""

    def appendChild(self, child):
        """
        Public method to add a child to this item.

        @param child reference to the child item to add
        @type BrowserItem
        """
        self.childItems.append(child)
        self._populated = True

    def removeChild(self, child):
        """
        Public method to remove a child.

        @param child reference to the child to remove
        @type BrowserItem
        """
        self.childItems.remove(child)

    def removeChildren(self):
        """
        Public method to remove all children.
        """
        self.childItems = []

    def child(self, row):
        """
        Public method to get a child id.

        @param row number of child to get the id of
        @type int
        @return reference to the child item
        @rtype BrowserItem
        """
        return self.childItems[row]

    def children(self):
        """
        Public method to get the ids of all child items.

        @return references to all child items
        @rtype list of BrowserItem
        """
        return self.childItems[:]

    def childCount(self):
        """
        Public method to get the number of available child items.

        @return number of child items
        @rtype int
        """
        return len(self.childItems)

    def columnCount(self):
        """
        Public method to get the number of available data items.

        @return number of data items
        @rtype int
        """
        return len(self.itemData)

    def data(self, column):
        """
        Public method to get a specific data item.

        @param column number of the requested data item
        @type int
        @return stored data item
        @rtype Any
        """
        try:
            return self.itemData[column]
        except IndexError:
            return ""

    def parent(self):
        """
        Public method to get the reference to the parent item.

        @return reference to the parent item
        @rtype BrowserItem
        """
        return self.parentItem

    def row(self):
        """
        Public method to get the row number of this item.

        @return row number
        @rtype int
        """
        try:
            return self.parentItem.childItems.index(self)
        except ValueError:
            return 0

    def type(self):
        """
        Public method to get the item type.

        @return type of the item
        @rtype BrowserItemType
        """
        return self.type_

    def isPublic(self):
        """
        Public method returning the public visibility status.

        @return flag indicating public visibility
        @rtype bool
        """
        return True

    def getIcon(self):
        """
        Public method to get the items icon.

        @return the icon
        @rtype QIcon
        """
        return self.icon

    def isPopulated(self):
        """
        Public method to chek, if this item is populated.

        @return population status
        @rtype bool
        """
        return self._populated

    def isLazyPopulated(self):
        """
        Public method to check, if this item should be populated lazyly.

        @return lazy population flag
        @rtype bool
        """
        return self._lazyPopulation

    def lessThan(self, other, column, _order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param _order sort order (for special sorting) (unused)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        try:
            return self.itemData[column] < other.itemData[column]
        except IndexError:
            return False

    def isSymlink(self):
        """
        Public method to check, if the item is a symbolic link.

        @return flag indicating a symbolic link
        @rtype bool
        """
        return self.symlink

    def isRemote(self):
        """
        Public method to check, if the item is a remote path item.

        @return flag indicating a remote path item
        @rtype bool
        """
        return self.remote

    def getRemoteInfo(self):
        """
        Public method to get data about the remote connection.

        @return string describing the remote connection
        @rtype str
        """
        return self.remoteInfo

    def lineno(self):
        """
        Public method to return the line number of the item.

        @return line number defining the object
        @rtype int
        """
        return 0  # just a placeholder implementation

    def colOffset(self):
        """
        Public method to return the column offset of the item definition.

        @return column offset defining the object
        @rtype int
        """
        return 0  # default value


class BrowserSimpleDirectoryItem(BrowserItem):
    """
    Class implementing the data structure for browser simple directory items.
    """

    def __init__(self, parent, text, path="", fsInterface=None):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param text text to be displayed
        @type str
        @param path path of the directory
        @type str
        @param fsInterface reference to the 'eric-ide' server file system interface
            (defaults to None)
        @type EricServerFileSystemInterface (optional)
        """
        super().__init__(parent, text)

        self.__fsInterface = fsInterface

        self.type_ = BrowserItemType.SimpleDirectory

        self._dirName = path
        if FileSystemUtilities.isRemoteFileName(self._dirName):
            if not self.__fsInterface.isdir(self._dirName):
                self._dirName = self.__fsInterface.dirname(self._dirName)
        else:
            if not os.path.isdir(self._dirName):
                self._dirName = os.path.dirname(self._dirName)

        if (
            FileSystemUtilities.isPlainFileName(self._dirName)
            and os.path.lexists(self._dirName)
            and os.path.islink(self._dirName)
        ):
            self.symlink = True
            self.icon = EricPixmapCache.getSymlinkIcon("dirClosed")
        else:
            self.icon = EricPixmapCache.getIcon("dirClosed")

    def setName(self, dinfo, full=True):  # noqa: U100
        """
        Public method to set the directory name.

        @param dinfo dinfo is the string for the directory
        @type str
        @param full flag indicating full path name should be displayed (unused)
        @type bool
        """
        if FileSystemUtilities.isRemoteFileName(dinfo):
            self._dirName = dinfo
            self.itemData[0] = self.__fsInterface.basename(self._dirName)
        else:
            self._dirName = os.path.abspath(dinfo)
            self.itemData[0] = os.path.basename(self._dirName)

    def dirName(self):
        """
        Public method returning the directory name.

        @return directory name
        @rtype str
        """
        return self._dirName

    def name(self):
        """
        Public method to return the name of the item.

        @return name of the item
        @rtype str
        """
        return self._dirName

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if issubclass(other.__class__, BrowserFileItem) and Preferences.getUI(
            "BrowsersListFoldersFirst"
        ):
            return order == Qt.SortOrder.AscendingOrder

        return super().lessThan(other, column, order)


class BrowserDirectoryItem(BrowserItem):
    """
    Class implementing the data structure for browser directory items.
    """

    def __init__(self, parent, dinfo, full=True, fsInterface=None):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param dinfo string containing the directory info
        @type str
        @param full flag indicating full pathname should be displayed (defaults to True)
        @type bool (optional)
        @param fsInterface reference to the 'eric-ide' server file system interface
            (defaults to None)
        @type EricServerFileSystemInterface (optional)
        """
        self.__fsInterface = fsInterface

        dn, isRemote, host = self.__prepareInfo(dinfo, full=full)
        super().__init__(parent, dn)

        self.type_ = BrowserItemType.Directory
        if (
            FileSystemUtilities.isPlainFileName(self._dirName)
            and not FileSystemUtilities.isDrive(self._dirName)
            and os.path.lexists(self._dirName)
            and os.path.islink(self._dirName)
        ):
            self.symlink = True
            self.icon = EricPixmapCache.getSymlinkIcon("dirClosed")
        elif FileSystemUtilities.isRemoteFileName(self._dirName):
            self.icon = EricPixmapCache.getIcon("open-remote")
        else:
            self.icon = EricPixmapCache.getIcon("dirClosed")
        self.remote = isRemote
        self.remoteInfo = host
        self._populated = False
        self._lazyPopulation = True

    def setName(self, dinfo, full=True):
        """
        Public method to set the directory name.

        @param dinfo string containing the directory info
        @type str
        @param full flag indicating full pathname should be displayed (defaults to True)
        @type bool (optional)
        """
        dn, isRemote, host = self.__prepareInfo(dinfo, full=full)
        self.itemData[0] = dn
        self.remoteInfo = host

    def __prepareInfo(self, dinfo, full=True):
        """
        Private method to prepare the information to be stored.

        @param dinfo string containing the directory info
        @type str
        @param full flag indicating full pathname should be displayed (defaults to True)
        @type bool (optional)
        @return tuple containing the path name to be shown, a flag indicating a
            remote (eric-ide server) path and a string with the connection info
        @rtype tuple of (str, bool)
        """
        if FileSystemUtilities.isRemoteFileName(dinfo):
            if "@@" in dinfo:
                dinfo, host = dinfo.split("@@")
            else:
                host = ""

            self._dirName = dinfo
            return (
                self._dirName if full else self.__fsInterface.basename(self._dirName),
                True,
                host,
            )
        else:
            self._dirName = os.path.abspath(dinfo)
            return (
                self._dirName if full else os.path.basename(self._dirName),
                False,
                "",
            )

    def dirName(self):
        """
        Public method returning the directory name.

        @return directory name
        @rtype str
        """
        return self._dirName

    def name(self):
        """
        Public method to return the name of the item.

        @return name of the item
        @rtype str
        """
        return self._dirName

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if issubclass(other.__class__, BrowserFileItem) and Preferences.getUI(
            "BrowsersListFoldersFirst"
        ):
            return order == Qt.SortOrder.AscendingOrder

        return super().lessThan(other, column, order)


class BrowserSysPathItem(BrowserItem):
    """
    Class implementing the data structure for browser sys.path items.
    """

    def __init__(self, parent):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        """
        super().__init__(parent, "sys.path")

        self.type_ = BrowserItemType.SysPath
        self.icon = EricPixmapCache.getIcon("filePython")
        self._populated = False
        self._lazyPopulation = True

    def name(self):
        """
        Public method to return the name of the item.

        @return name of the item
        @rtype str
        """
        return "sys.path"


class BrowserFileItem(BrowserItem):
    """
    Class implementing the data structure for browser file items.
    """

    def __init__(self, parent, finfo, full=True, sourceLanguage="", fsInterface=None):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param finfo the string for the file
        @type str
        @param full flag indicating full pathname should be displayed (defaults to True)
        @type bool (optional)
        @param sourceLanguage source code language of the project (defaults to "")
        @type str (optional)
        @param fsInterface reference to the 'eric-ide' server file system interface
            (defaults to None)
        @type EricServerFileSystemInterface (optional)
        """
        self.__fsInterface = fsInterface

        if FileSystemUtilities.isRemoteFileName(finfo):
            dirname, basename = self.__fsInterface.split(finfo)
            self.fileext = self.__fsInterface.splitext(finfo)[1].lower()
            self._filename = finfo
        else:
            dirname, basename = os.path.split(finfo)
            self.fileext = os.path.splitext(finfo)[1].lower()
            self._filename = os.path.abspath(finfo)

        super().__init__(parent, basename)

        self._dirName = dirname
        self.type_ = BrowserItemType.File
        self.sourceLanguage = sourceLanguage

        self._moduleName = ""

        pixName = ""
        if self.isPython3File():
            pixName = "filePython"
            self._populated = False
            self._lazyPopulation = True
            self._moduleName = basename
        elif self.isCythonFile():
            pixName = "lexerCython"
            self._populated = False
            self._lazyPopulation = True
            self._moduleName = basename
        elif self.isRubyFile():
            pixName = "fileRuby"
            self._populated = False
            self._lazyPopulation = True
            self._moduleName = basename
        elif self.isDesignerFile():
            pixName = "fileDesigner"
        elif self.isLinguistFile():
            if self.fileext == ".ts":
                pixName = "fileLinguist"
            else:
                pixName = "fileLinguist2"
        elif self.isResourcesFile():
            pixName = "fileResource"
        elif self.isProjectFile():
            pixName = "fileProject"
        elif self.isMultiProjectFile():
            pixName = "fileMultiProject"
        elif self.isSvgFile():
            pixName = "fileSvg"
        elif self.isPixmapFile():
            pixName = "filePixmap"
        elif self.isDFile():
            pixName = "fileD"
        elif self.isJavaScriptFile():
            pixName = "fileJavascript"
            self._populated = False
            self._lazyPopulation = True
            self._moduleName = basename
        elif self.isEricGraphicsFile():
            pixName = "fileUML"
        elif self.isParsableFile():
            pixName = ClassBrowsers.getIcon(self._filename)
            self._populated = False
            self._lazyPopulation = True
            self._moduleName = basename
        else:
            pixName = "fileMisc"

        if (
            FileSystemUtilities.isPlainFileName(self._filename)
            and os.path.lexists(self._filename)
            and os.path.islink(self._filename)
        ):
            self.symlink = True
            self.icon = EricPixmapCache.getSymlinkIcon(pixName)
        else:
            self.icon = EricPixmapCache.getIcon(pixName)

    def setName(self, finfo, full=True):  # noqa: U100
        """
        Public method to set the directory name.

        @param finfo the string for the file
        @type str
        @param full flag indicating full path name should be displayed (unused)
        @type bool
        """
        if FileSystemUtilities.isRemoteFileName(finfo):
            dirname, basename = self.__fsInterface.split(finfo)
            self.fileext = self.__fsInterface.splitext(finfo)[1].lower()
            self._filename = finfo
        else:
            dirname, basename = os.path.split(finfo)
            self.fileext = os.path.splitext(finfo)[1].lower()
            self._filename = os.path.abspath(finfo)

        self.itemData[0] = basename
        if (
            self.isPython3File()
            or self.isCythonFile()
            or self.isRubyFile()
            or self.isJavaScriptFile()
            or self.isParsableFile()
        ):
            self._dirName = dirname
            self._moduleName = basename

    def fileName(self):
        """
        Public method returning the filename.

        @return filename
        @rtype str
        """
        return self._filename

    def name(self):
        """
        Public method to return the name of the item.

        @return name of the item
        @rtype str
        """
        return self._filename

    def fileExt(self):
        """
        Public method returning the file extension.

        @return file extension
        @rtype str
        """
        return self.fileext

    def dirName(self):
        """
        Public method returning the directory name.

        @return directory name
        @rtype str
        """
        return self._dirName

    def moduleName(self):
        """
        Public method returning the module name.

        @return module name
        @rtype str
        """
        return self._moduleName

    def isPython3File(self):
        """
        Public method to check, if this file is a Python3 script.

        @return flag indicating a Python3 file
        @rtype bool
        """
        return (
            self.fileext in Preferences.getPython("Python3Extensions")
            or (self.fileext == "" and self.sourceLanguage == "Python3")
            or (
                not Preferences.getPython("Python3Extensions")
                and self.fileext in (".py", ".pyw")
            )
        )

    def isCythonFile(self):
        """
        Public method to check, if this file is a Cython file.

        @return flag indicating a Cython file
        @rtype bool
        """
        return self.fileext in (".pyx", ".pxd", ".pxi") or (
            self.fileext == "" and self.sourceLanguage == "Cython"
        )

    def isRubyFile(self):
        """
        Public method to check, if this file is a Ruby script.

        @return flag indicating a Ruby file
        @rtype bool
        """
        return self.fileext == ".rb" or (
            self.fileext == "" and self.sourceLanguage == "Ruby"
        )

    def isDesignerFile(self):
        """
        Public method to check, if this file is a Qt-Designer file.

        @return flag indicating a Qt-Designer file
        @rtype bool
        """
        return self.fileext == ".ui"

    def isLinguistFile(self):
        """
        Public method to check, if this file is a Qt-Linguist file.

        @return flag indicating a Qt-Linguist file
        @rtype bool
        """
        return self.fileext in [".ts", ".qm"]

    def isResourcesFile(self):
        """
        Public method to check, if this file is a Qt-Resources file.

        @return flag indicating a Qt-Resources file
        @rtype bool
        """
        return self.fileext == ".qrc"

    def isProjectFile(self):
        """
        Public method to check, if this file is an eric project file.

        @return flag indicating an eric project file
        @rtype bool
        """
        return self.fileext in (".epj",)

    def isMultiProjectFile(self):
        """
        Public method to check, if this file is an eric multi project file.

        @return flag indicating an eric project file
        @rtype bool
        """
        return self.fileext in (".emj",)

    def isJavaScriptFile(self):
        """
        Public method to check, if this file is a JavaScript file.

        @return flag indicating a JavaScript file
        @rtype bool
        """
        return self.fileext == ".js"

    def isPixmapFile(self):
        """
        Public method to check, if this file is a pixmap file.

        @return flag indicating a pixmap file
        @rtype bool
        """
        return self.fileext[1:] in QImageReader.supportedImageFormats()

    def isSvgFile(self):
        """
        Public method to check, if this file is a SVG file.

        @return flag indicating a SVG file
        @rtype bool
        """
        return self.fileext == ".svg"

    def isPdfFile(self):
        """
        Public method to check, if this file is a PDF file.

        @return flag indicating a PDF file
        @rtype bool
        """
        return self.fileext == ".pdf"

    def isDFile(self):
        """
        Public method to check, if this file is a D file.

        @return flag indicating a D file
        @rtype bool
        """
        return self.fileext in [".d", ".di"] or (
            self.fileext == "" and self.sourceLanguage == "D"
        )

    def isEricGraphicsFile(self):
        """
        Public method to check, if this is an eric graphics file.

        @return flag indicating an eric graphics file
        @rtype bool
        """
        return self.fileext in (".egj",)

    def isParsableFile(self):
        """
        Public method to check, if the file is supported by class browsers.

        @return flag indicating a supported file
        @rtype bool
        """
        return ClassBrowsers.isSupportedType(self.fileext)

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if not issubclass(other.__class__, BrowserFileItem) and Preferences.getUI(
            "BrowsersListFoldersFirst"
        ):
            return order == Qt.SortOrder.DescendingOrder

        if issubclass(other.__class__, BrowserFileItem):
            if FileSystemUtilities.isRemoteFileName(self._filename):
                basename = self.__fsInterface.basename(self._filename)
            else:
                basename = os.path.basename(self._filename)
            sinit = basename.startswith("__init__.py")

            if FileSystemUtilities.isRemoteFileName(other.fileName()):
                basename = self.__fsInterface.basename(other.fileName())
            else:
                basename = os.path.basename(other.fileName())
            oinit = basename.startswith("__init__.py")

            if sinit and not oinit:
                return order == Qt.SortOrder.AscendingOrder
            if not sinit and oinit:
                return order == Qt.SortOrder.DescendingOrder

        return super().lessThan(other, column, order)


class BrowserClassItem(BrowserItem):
    """
    Class implementing the data structure for browser class items.
    """

    def __init__(self, parent, cl, filename, modelType=BrowserModelType.Generic):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param cl Class object to be shown
        @type Class
        @param filename file name of the file defining this class
        @type str
        @param modelType type of the browser model (defaults to
            BrowserModelType.Generic)
        @type BrowserModelType (optional)
        """
        name = cl.name
        if hasattr(cl, "super") and cl.super:
            supers = []
            for sup in cl.super:
                try:
                    sname = sup.name
                    if sup.module != cl.module:
                        sname = "{0}.{1}".format(sup.module, sname)
                except AttributeError:
                    sname = sup
                supers.append(sname)
            name += "({0})".format(", ".join(supers))

        super().__init__(parent, name)

        self._modelType = modelType
        self.type_ = BrowserItemType.Class
        self._name = name
        self._classObject = cl
        self._filename = filename

        self.isfunction = isinstance(self._classObject, ClbrBaseClasses.Function)
        self.ismodule = isinstance(self._classObject, ClbrBaseClasses.Module)
        self.isenum = isinstance(self._classObject, ClbrBaseClasses.Enum)
        if self.isfunction:
            if cl.isPrivate():
                self.icon = EricPixmapCache.getIcon("method_private")
            elif cl.isProtected():
                self.icon = EricPixmapCache.getIcon("method_protected")
            else:
                self.icon = EricPixmapCache.getIcon("method")
            self.itemData[0] = "{0}({1})".format(
                name, ", ".join(self._classObject.parameters)
            )
            if self._classObject.annotation:
                self.itemData[0] = "{0} {1}".format(
                    self.itemData[0], self._classObject.annotation
                )
            # - if no defaults are wanted
            # - ....format(name,
            # -            ", ".join([e.split('=')[0].strip()
            # -                       for e in self._classObject.parameters]))
        elif self.ismodule:
            self.icon = EricPixmapCache.getIcon("module")
        elif self.isenum:
            self.icon = EricPixmapCache.getIcon("attribute")
        else:
            if cl.isPrivate():
                self.icon = EricPixmapCache.getIcon("class_private")
            elif cl.isProtected():
                self.icon = EricPixmapCache.getIcon("class_protected")
            else:
                self.icon = EricPixmapCache.getIcon("class")
        if self._classObject and (
            self._classObject.methods
            or self._classObject.classes
            or self._classObject.attributes
            or self._classObject.globals
        ):
            self._populated = False
            self._lazyPopulation = True

    def name(self):
        """
        Public method to return the name of the item.

        @return name of the item
        @rtype str
        """
        return "{0}@@{1}".format(self._filename, self.lineno())

    def fileName(self):
        """
        Public method returning the filename.

        @return filename
        @rtype str
        """
        return self._filename

    def classObject(self):
        """
        Public method returning the class object.

        @return reference to the class object
        @rtype Class
        """
        return self._classObject

    def lineno(self):
        """
        Public method returning the line number defining this object.

        @return line number defining the object
        @rtype int
        """
        return self._classObject.lineno

    def boundaries(self):
        """
        Public method returning the boundaries of the method definition.

        @return tuple with start end end line number
        @rtype tuple of (int, int)
        """
        return (self._classObject.lineno, self._classObject.endlineno)

    def colOffset(self):
        """
        Public method to return the column offset of the item definition.

        @return column offset defining the object
        @rtype int
        """
        return self._classObject.coloffset

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if issubclass(other.__class__, (BrowserCodingItem, BrowserClassAttributesItem)):
            return order == Qt.SortOrder.DescendingOrder

        if column == 0 and (
            (
                self._modelType == BrowserModelType.EditorOutline
                and Preferences.getEditor("SourceOutlineListContentsByOccurrence")
            )
            or (
                self._modelType != BrowserModelType.EditorOutline
                and Preferences.getUI("BrowsersListContentsByOccurrence")
            )
        ):
            if order == Qt.SortOrder.AscendingOrder:
                return self.lineno() < other.lineno()
            else:
                return self.lineno() > other.lineno()

        return super().lessThan(other, column, order)

    def isPublic(self):
        """
        Public method returning the public visibility status.

        @return flag indicating public visibility
        @rtype bool
        """
        return self._classObject.isPublic()


class BrowserMethodItem(BrowserItem):
    """
    Class implementing the data structure for browser method items.
    """

    def __init__(self, parent, fn, filename, modelType=BrowserModelType.Generic):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param fn Function object to be shown
        @type Function
        @param filename filename of the file defining this class
        @type str
        @param modelType type of the browser model (defaults to
            BrowserModelType.Generic)
        @type BrowserModelType (optional)
        """
        name = fn.name
        super().__init__(parent, name)

        self._modelType = modelType
        self.type_ = BrowserItemType.Method
        self._name = name
        self._functionObject = fn
        self._filename = filename
        if self._functionObject.modifier == ClbrBaseClasses.Function.Static:
            self.icon = EricPixmapCache.getIcon("method_static")
        elif self._functionObject.modifier == ClbrBaseClasses.Function.Class:
            self.icon = EricPixmapCache.getIcon("method_class")
        elif self._functionObject.isPrivate():
            self.icon = EricPixmapCache.getIcon("method_private")
        elif self._functionObject.isProtected():
            self.icon = EricPixmapCache.getIcon("method_protected")
        else:
            self.icon = EricPixmapCache.getIcon("method")
        self.itemData[0] = "{0}({1})".format(
            name, ", ".join(self._functionObject.parameters)
        )
        if self._functionObject.annotation:
            self.itemData[0] = "{0} {1}".format(
                self.itemData[0], self._functionObject.annotation
            )
        # if no defaults are wanted
        # ....format(name,
        #            ", ".join([e.split('=')[0].strip()
        #                       for e in self._functionObject.parameters]))
        if self._functionObject and (
            self._functionObject.methods
            or self._functionObject.classes
            or self._functionObject.attributes
        ):
            self._populated = False
            self._lazyPopulation = True

    def name(self):
        """
        Public method to return the name of the item.

        @return name of the item
        @rtype str
        """
        return "{0}@@{1}".format(self._filename, self.lineno())

    def fileName(self):
        """
        Public method returning the filename.

        @return filename
        @rtype str
        """
        return self._filename

    def functionObject(self):
        """
        Public method returning the function object.

        @return reference to the function object
        @rtype Function
        """
        return self._functionObject

    def lineno(self):
        """
        Public method returning the line number defining this object.

        @return line number defining the object
        @rtype int
        """
        return self._functionObject.lineno

    def boundaries(self):
        """
        Public method returning the boundaries of the method definition.

        @return tuple with start end end line number
        @rtype tuple of (int, int)
        """
        return (self._functionObject.lineno, self._functionObject.endlineno)

    def colOffset(self):
        """
        Public method to return the column offset of the item definition.

        @return column offset defining the object
        @rtype int
        """
        return self._functionObject.coloffset

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if issubclass(other.__class__, BrowserMethodItem):
            if self._name.startswith("__init__"):
                return order == Qt.SortOrder.AscendingOrder
            if other._name.startswith("__init__"):
                return order == Qt.SortOrder.DescendingOrder
        elif issubclass(other.__class__, BrowserClassAttributesItem):
            return order == Qt.SortOrder.DescendingOrder

        if column == 0 and (
            (
                self._modelType == BrowserModelType.EditorOutline
                and Preferences.getEditor("SourceOutlineListContentsByOccurrence")
            )
            or (
                self._modelType != BrowserModelType.EditorOutline
                and Preferences.getUI("BrowsersListContentsByOccurrence")
            )
        ):
            if order == Qt.SortOrder.AscendingOrder:
                return self.lineno() < other.lineno()
            else:
                return self.lineno() > other.lineno()

        return super().lessThan(other, column, order)

    def isPublic(self):
        """
        Public method returning the public visibility status.

        @return flag indicating public visibility
        @rtype bool
        """
        return self._functionObject.isPublic()


class BrowserClassAttributesItem(BrowserItem):
    """
    Class implementing the data structure for browser class attributes items.
    """

    def __init__(self, parent, attributes, text, isClass=False):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param attributes list of attributes
        @type list of Attribute
        @param text text to be shown by this item
        @type str
        @param isClass flag indicating class attributes
        @type bool
        """
        super().__init__(parent, text)

        self.type_ = BrowserItemType.Attributes
        self._attributes = attributes.copy()
        self._populated = False
        self._lazyPopulation = True
        if isClass:
            self.icon = EricPixmapCache.getIcon("attributes_class")
        else:
            self.icon = EricPixmapCache.getIcon("attributes")
        self.__isClass = isClass

    def name(self):
        """
        Public method to return the name of the item.

        @return name of the item
        @rtype str
        """
        return "{0}@@{1}".format(self.parentItem.name(), self.data(0))

    def attributes(self):
        """
        Public method returning the attribute list.

        @return reference to the list of attributes
        @rtype list of Attribute
        """
        return self._attributes

    def isClassAttributes(self):
        """
        Public method returning the attributes type.

        @return flag indicating class attributes
        @rtype bool
        """
        return self.__isClass

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if issubclass(other.__class__, BrowserCodingItem):
            return order == Qt.SortOrder.DescendingOrder
        elif issubclass(other.__class__, (BrowserClassItem, BrowserMethodItem)):
            return order == Qt.SortOrder.AscendingOrder

        return super().lessThan(other, column, order)


class BrowserClassAttributeItem(BrowserItem):
    """
    Class implementing the data structure for browser class attribute items.
    """

    def __init__(
        self, parent, attribute, isClass=False, modelType=BrowserModelType.Generic
    ):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param attribute reference to the attribute object
        @type Attribute
        @param isClass flag indicating a class attribute (defaults to False)
        @type bool (optional)
        @param modelType type of the browser model (defaults to
            BrowserModelType.Generic)
        @type BrowserModelType (optional)
        """
        super().__init__(parent, attribute.name)

        self._modelType = modelType
        self.type_ = BrowserItemType.Attribute
        self._attributeObject = attribute
        self.__public = attribute.isPublic()
        if isClass:
            self.icon = EricPixmapCache.getIcon("attribute_class")
        elif attribute.isPrivate():
            self.icon = EricPixmapCache.getIcon("attribute_private")
        elif attribute.isProtected():
            self.icon = EricPixmapCache.getIcon("attribute_protected")
        else:
            self.icon = EricPixmapCache.getIcon("attribute")

    def isPublic(self):
        """
        Public method returning the public visibility status.

        @return flag indicating public visibility
        @rtype bool
        """
        return self.__public

    def attributeObject(self):
        """
        Public method returning the class object.

        @return reference to the class object
        @rtype Class
        """
        return self._attributeObject

    def fileName(self):
        """
        Public method returning the filename.

        @return filename
        @rtype str
        """
        return self._attributeObject.file

    def lineno(self):
        """
        Public method returning the line number defining this object.

        @return line number defining the object
        @rtype int
        """
        return self._attributeObject.lineno

    def linenos(self):
        """
        Public method returning the line numbers this object is assigned to.

        @return line number the object is assigned to
        @rtype list of int
        """
        return self._attributeObject.linenos[:]

    def colOffset(self):
        """
        Public method to return the column offset of the item definition.

        @return column offset defining the object
        @rtype int
        """
        return self._attributeObject.coloffset

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if column == 0 and (
            (
                self._modelType == BrowserModelType.EditorOutline
                and Preferences.getEditor("SourceOutlineListContentsByOccurrence")
            )
            or (
                self._modelType != BrowserModelType.EditorOutline
                and Preferences.getUI("BrowsersListContentsByOccurrence")
            )
        ):
            if order == Qt.SortOrder.AscendingOrder:
                return self.lineno() < other.lineno()
            else:
                return self.lineno() > other.lineno()

        return super().lessThan(other, column, order)


class BrowserGlobalsItem(BrowserClassAttributesItem):
    """
    Class implementing the data structure for browser globals items.
    """

    def __init__(self, parent, attributes, text):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param attributes list of attributes
        @type list of Attribute
        @param text text to be shown by this item
        @type str
        """
        BrowserClassAttributesItem.__init__(self, parent, attributes, text)


class BrowserCodingItem(BrowserItem):
    """
    Class implementing the data structure for browser coding items.
    """

    def __init__(self, parent, text, linenumber):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param text text to be shown by this item
        @type str
        @param linenumber line number of the coding line
        @type int
        """
        super().__init__(parent, text)

        self.type_ = BrowserItemType.Coding
        self.icon = EricPixmapCache.getIcon("textencoding")

        self.__lineno = linenumber

    def lineno(self):
        """
        Public method returning the line number of the coding line.

        @return line number defining the coding line
        @rtype int
        """
        return self.__lineno

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if issubclass(
            other.__class__,
            (BrowserClassItem, BrowserClassAttributesItem, BrowserImportItem),
        ):
            return order == Qt.SortOrder.AscendingOrder

        return super().lessThan(other, column, order)


class BrowserImportsItem(BrowserItem):
    """
    Class implementing the data structure for browser import items.
    """

    def __init__(self, parent, text):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param text text to be shown by this item
        @type str
        """
        super().__init__(parent, text)

        self.type_ = BrowserItemType.Imports
        self.icon = EricPixmapCache.getIcon("imports")

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if issubclass(other.__class__, (BrowserClassItem, BrowserClassAttributesItem)):
            return order == Qt.SortOrder.AscendingOrder

        return super().lessThan(other, column, order)


class BrowserImportItem(BrowserItem):
    """
    Class implementing the data structure for browser imported module and
    imported names items.
    """

    def __init__(
        self,
        parent,
        text,
        filename,
        lineNumbers,
        isModule=True,
        modelType=BrowserModelType.Generic,
    ):
        """
        Constructor

        @param parent parent item
        @type BrowserItem
        @param text text to be shown by this item
        @type str
        @param filename name of the file
        @type str
        @param lineNumbers list of line numbers of the import statement
        @type list of int
        @param isModule flag indicating a module item entry (defaults to True)
        @type bool (optional)
        @param modelType type of the browser model (defaults to
            BrowserModelType.Generic)
        @type BrowserModelType (optional)
        """
        super().__init__(parent, text)

        self.__filename = filename
        self.__linenos = lineNumbers[:]

        self._modelType = modelType
        self.type_ = BrowserItemType.Import
        if isModule:
            self.icon = EricPixmapCache.getIcon("importedModule")
        else:
            self.icon = EricPixmapCache.getIcon("importedName")

    def fileName(self):
        """
        Public method returning the filename.

        @return filename
        @rtype str
        """
        return self.__filename

    def lineno(self):
        """
        Public method returning the line number of the first import.

        @return line number of the first import
        @rtype int
        """
        return self.__linenos[0]

    def linenos(self):
        """
        Public method returning the line numbers of all imports.

        @return line numbers of all imports
        @rtype list of int
        """
        return self.__linenos[:]

    def lessThan(self, other, column, order):
        """
        Public method to check, if the item is less than the other one.

        @param other reference to item to compare against
        @type BrowserItem
        @param column column number to use for the comparison
        @type int
        @param order sort order (for special sorting)
        @type Qt.SortOrder
        @return true, if this item is less than other
        @rtype bool
        """
        if column == 0 and (
            (
                self._modelType == BrowserModelType.EditorOutline
                and Preferences.getEditor("SourceOutlineListContentsByOccurrence")
            )
            or (
                self._modelType != BrowserModelType.EditorOutline
                and Preferences.getUI("BrowsersListContentsByOccurrence")
            )
        ):
            if order == Qt.SortOrder.AscendingOrder:
                return self.lineno() < other.lineno()
            else:
                return self.lineno() > other.lineno()

        return super().lessThan(other, column, order)
