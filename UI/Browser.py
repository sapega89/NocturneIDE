# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a browser with class browsing capabilities.
"""

import os
import shutil

from PyQt6.QtCore import (
    QCoreApplication,
    QElapsedTimer,
    QItemSelectionModel,
    Qt,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeView,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Project.ProjectBrowserModel import ProjectBrowserSimpleDirectoryItem
from eric7.RemoteServerInterface import EricServerFileDialog
from eric7.SystemUtilities import FileSystemUtilities
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog
from eric7.Utilities import MimeTypes

from .BrowserModel import (
    BrowserClassAttributeItem,
    BrowserClassItem,
    BrowserDirectoryItem,
    BrowserFileItem,
    BrowserGlobalsItem,
    BrowserImportItem,
    BrowserImportsItem,
    BrowserItemType,
    BrowserMethodItem,
    BrowserModel,
    BrowserSimpleDirectoryItem,
    BrowserSysPathItem,
)
from .BrowserSortFilterProxyModel import BrowserSortFilterProxyModel


class Browser(QTreeView):
    """
    Class used to display a file system tree.

    Via the context menu that
    is displayed by a right click the user can select various actions on
    the selected file.

    @signal sourceFile(filename) emitted to open a Python file at the first line (str)
    @signal sourceFile(filename, lineno) emitted to open a Python file at a
        line (str, int)
    @signal sourceFile(filename, lineno, type) emitted to open a Python file
        at a line giving an explicit file type (str, int, str)
    @signal sourceFile(filename, linenos) emitted to open a Python file giving
        a list of lines(str, list)
    @signal sourceFile(filename, lineno, col_offset) emitted to open a Python file at a
        line and column (str, int, int)
    @signal designerFile(filename) emitted to open a Qt-Designer file (str)
    @signal linguistFile(filename) emitted to open a Qt-Linguist (*.ts)
        file (str)
    @signal trpreview(filenames) emitted to preview Qt-Linguist (*.qm)
        files (list of str)
    @signal trpreview(filenames, ignore) emitted to preview Qt-Linguist (*.qm)
        files indicating whether non-existent files shall be ignored
        (list of str, bool)
    @signal projectFile(filename) emitted to open an eric project file (str)
    @signal multiProjectFile(filename) emitted to open an eric multi project
        file (str)
    @signal pixmapFile(filename) emitted to open a pixmap file (str)
    @signal pixmapEditFile(filename) emitted to edit a pixmap file (str)
    @signal svgFile(filename) emitted to open a SVG file (str)
    @signal umlFile(filename) emitted to open an eric UML file (str)
    @signal binaryFile(filename) emitted to open a file as binary (str)
    @signal testFile(filename) emitted to open a Python file for a
        unit test (str)
    @signal pdfFile(filename) emitted to open a PDF file (str)
    """

    sourceFile = pyqtSignal(
        (str,), (str, int), (str, int, int), (str, list), (str, int, str)
    )
    designerFile = pyqtSignal(str)
    linguistFile = pyqtSignal(str)
    trpreview = pyqtSignal((list,), (list, bool))
    projectFile = pyqtSignal(str)
    multiProjectFile = pyqtSignal(str)
    pixmapFile = pyqtSignal(str)
    pixmapEditFile = pyqtSignal(str)
    svgFile = pyqtSignal(str)
    umlFile = pyqtSignal(str)
    binaryFile = pyqtSignal(str)
    pdfFile = pyqtSignal(str)
    testFile = pyqtSignal(str)

    def __init__(self, serverInterface, parent=None):
        """
        Constructor

        @param serverInterface reference to the 'eric-ide' server interface object
        @type EricServerInterface
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setWindowTitle(QCoreApplication.translate("Browser", "File-Browser"))
        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

        self.__ericServerInterface = serverInterface
        self.__remotefsInterface = serverInterface.getServiceInterface("FileSystem")

        self.__model = BrowserModel(fsInterface=self.__remotefsInterface)
        self.__sortModel = BrowserSortFilterProxyModel(remoteServer=serverInterface)
        self.__sortModel.setSourceModel(self.__model)
        self.setModel(self.__sortModel)

        self.selectedItemsFilter = [BrowserFileItem]

        self._activating = False

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenuRequested)
        self.activated.connect(self._openItem)
        self.expanded.connect(self._resizeColumns)
        self.collapsed.connect(self._resizeColumns)

        self.setWhatsThis(
            QCoreApplication.translate(
                "Browser",
                """<b>The Browser Window</b>"""
                """<p>This allows you to easily navigate the hierarchy of"""
                """ directories and files on your system, identify the Python"""
                """ programs and open them up in a Source Viewer window. The"""
                """ window displays several separate hierarchies.</p>"""
                """<p>The first hierarchy is only shown if you have opened a"""
                """ program for debugging and its root is the directory"""
                """ containing that program. Usually all of the separate files"""
                """ that make up a Python application are held in the same"""
                """ directory, so this hierarchy gives you easy access to most"""
                """ of what you will need.</p>"""
                """<p>The next hierarchy is used to easily navigate the"""
                """ directories that are specified in the Python"""
                """ <tt>sys.path</tt> variable.</p>"""
                """<p>The remaining hierarchies allow you navigate your system"""
                """ as a whole. On a UNIX system there will be a hierarchy with"""
                """ <tt>/</tt> at its root and another with the user home"""
                """ directory. On a Windows system there will be a hierarchy for"""
                """ each drive on the"""
                """ system.</p>"""
                """<p>Python programs (i.e. those with a <tt>.py</tt> file name"""
                """ suffix) are identified in the hierarchies with a Python"""
                """ icon. The right mouse button will popup a menu which lets"""
                """ you open the file in a Source Viewer window, open the file"""
                """ for debugging or use it for a test run.</p>"""
                """<p>The context menu of a class, function or method allows you"""
                """ to open the file defining this class, function or method and"""
                """ will ensure, that the correct source line is visible.</p>"""
                """<p>Qt-Designer files (i.e. those with a <tt>.ui</tt> file"""
                """ name suffix) are shown with a Designer icon. The context"""
                """ menu of these files allows you to start Qt-Designer with"""
                """ that file.</p>"""
                """<p>Qt-Linguist files (i.e. those with a <tt>.ts</tt> file"""
                """ name suffix) are shown with a Linguist icon. The context"""
                """ menu of these files allows you to start Qt-Linguist with"""
                """ that file.</p>""",
            )
        )

        self.__createPopupMenus()

        self._init()  # perform common initialization tasks

        self._keyboardSearchString = ""
        self._keyboardSearchTimer = QElapsedTimer()
        self._keyboardSearchTimer.invalidate()

    def _init(self):
        """
        Protected method to perform initialization tasks common to this
        base class and all derived classes.
        """
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)

        header = self.header()
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)

        self.setSortingEnabled(True)

        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.layoutDisplay()

    def layoutDisplay(self):
        """
        Public slot to perform a layout operation.
        """
        self._resizeColumns()
        self._resort()

    @pyqtSlot()
    def _resizeColumns(self):
        """
        Protected slot to resize the view when items get expanded or collapsed.
        """
        self.resizeColumnToContents(0)

    @pyqtSlot()
    def _resort(self):
        """
        Protected slot to resort the tree.
        """
        self.model().sort(
            self.header().sortIndicatorSection(), self.header().sortIndicatorOrder()
        )

    def __createPopupMenus(self):
        """
        Private method to generate the various popup menus.
        """
        self.showHiddenFilesAct = QAction(
            QCoreApplication.translate("Browser", "Show Hidden Files")
        )
        self.showHiddenFilesAct.setCheckable(True)
        self.showHiddenFilesAct.toggled.connect(self._showHidden)
        self.showHiddenFilesAct.setChecked(Preferences.getUI("BrowsersListHiddenFiles"))

        self.__newMenu = QMenu(QCoreApplication.translate("Browser", "New"), self)
        self.__newMenu.addAction(
            QCoreApplication.translate("Browser", "Directory"), self._newDirectory
        )
        self.__newMenu.addAction(
            QCoreApplication.translate("Browser", "File"), self._newFile
        )

        # create the popup menu for source files
        self.sourceMenu = QMenu(self)
        self.sourceMenu.addAction(
            QCoreApplication.translate("Browser", "Open"), self._openItem
        )
        self.testingAct = self.sourceMenu.addAction(
            QCoreApplication.translate("Browser", "Run Test..."), self.handleTesting
        )
        self.sourceMenu.addSeparator()
        self.mimeTypeAct = self.sourceMenu.addAction(
            QCoreApplication.translate("Browser", "Show Mime-Type"), self.__showMimeType
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(
            QCoreApplication.translate("Browser", "Refresh Source File"),
            self.__refreshSource,
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(
            QCoreApplication.translate("Browser", "Show in File Manager"),
            self._showInFileManager,
        )
        self.sourceMenu.addAction(
            QCoreApplication.translate("Browser", "Copy Path to Clipboard"),
            self._copyToClipboard,
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(self.showHiddenFilesAct)
        self.sourceMenu.addSeparator()
        self.sourceMenu.addMenu(self.__newMenu)
        self.sourceMenu.addAction(
            QCoreApplication.translate("Browser", "Delete"), self._deleteFileOrDirectory
        )

        # create the popup menu for general use
        self.menu = QMenu(self)
        self.menu.addAction(
            QCoreApplication.translate("Browser", "Open"), self._openItem
        )
        self.menu.addAction(
            QCoreApplication.translate("Browser", "Open in Hex Editor"),
            self._openHexEditor,
        )
        self.editPixmapAct = self.menu.addAction(
            QCoreApplication.translate("Browser", "Open in Icon Editor"),
            self._editPixmap,
        )
        self.openInEditorAct = self.menu.addAction(
            QCoreApplication.translate("Browser", "Open in Editor"),
            self._openFileInEditor,
        )
        self.openInPdfViewerAct = self.menu.addAction(
            QCoreApplication.translate("Browser", "Open in PDF Viewer"),
            self._openPdfViewer,
        )
        self.menu.addSeparator()
        self.mimeTypeAct = self.menu.addAction(
            QCoreApplication.translate("Browser", "Show Mime-Type"), self.__showMimeType
        )
        self.menu.addSeparator()
        self.menu.addAction(
            QCoreApplication.translate("Browser", "Show in File Manager"),
            self._showInFileManager,
        )
        self.menu.addAction(
            QCoreApplication.translate("Browser", "Copy Path to Clipboard"),
            self._copyToClipboard,
        )
        self.menu.addSeparator()
        self.menu.addAction(self.showHiddenFilesAct)
        self.menu.addSeparator()
        self.menu.addMenu(self.__newMenu)
        self.menu.addAction(
            QCoreApplication.translate("Browser", "Delete"), self._deleteFileOrDirectory
        )

        # create the menu for multiple selected files
        self.multiMenu = QMenu(self)
        self.multiMenu.addAction(
            QCoreApplication.translate("Browser", "Open"), self._openItem
        )
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.showHiddenFilesAct)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(
            QCoreApplication.translate("Browser", "Delete"), self.__deleteMultiple
        )

        # create the directory menu
        self.dirMenu = QMenu(self)
        self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "New Top Level Directory..."),
            self.__newTopLevelDir,
        )
        self.__dmRemoteTopLevelAct = self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "New Remote Top Level Directory..."),
            self.__newRemoteTopLevelDir,
        )
        self.addAsTopLevelAct = self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "Add as top level directory"),
            self.__addAsToplevelDir,
        )
        self.removeFromToplevelAct = self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "Remove from top level"),
            self.__removeToplevel,
        )
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "Refresh directory"),
            self.__refreshDirectory,
        )
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "Find in this directory"),
            self.__findInDirectory,
        )
        self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "Find && Replace in this directory"),
            self.__replaceInDirectory,
        )
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "Show in File Manager"),
            self._showInFileManager,
        )
        self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "Copy Path to Clipboard"),
            self._copyToClipboard,
        )
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.showHiddenFilesAct)
        self.dirMenu.addSeparator()
        self.dirMenu.addMenu(self.__newMenu)
        self.dirMenu.addAction(
            QCoreApplication.translate("Browser", "Delete"), self._deleteFileOrDirectory
        )

        # create the attribute menu
        self.gotoMenu = QMenu(QCoreApplication.translate("Browser", "Goto"), self)
        self.gotoMenu.aboutToShow.connect(self._showGotoMenu)
        self.gotoMenu.triggered.connect(self._gotoAttribute)

        self.attributeMenu = QMenu(self)
        self.attributeMenu.addAction(
            QCoreApplication.translate("Browser", "New Top Level Directory..."),
            self.__newTopLevelDir,
        )
        self.__amRemoteTopLevelAct = self.attributeMenu.addAction(
            QCoreApplication.translate("Browser", "New Remote Top Level Directory..."),
            self.__newRemoteTopLevelDir,
        )
        self.attributeMenu.addSeparator()
        self.attributeMenu.addMenu(self.gotoMenu)

        # create the background menu
        self.backMenu = QMenu(self)
        self.backMenu.addAction(
            QCoreApplication.translate("Browser", "New Top Level Directory..."),
            self.__newTopLevelDir,
        )
        self.__bmRemoteTopLevelAct = self.backMenu.addAction(
            QCoreApplication.translate("Browser", "New Remote Top Level Directory..."),
            self.__newRemoteTopLevelDir,
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.showHiddenFilesAct)

    def mouseDoubleClickEvent(self, mouseEvent):
        """
        Protected method of QAbstractItemView.

        Reimplemented to disable expanding/collapsing of items when
        double-clicking. Instead the double-clicked entry is opened.

        @param mouseEvent the mouse event
        @type QMouseEvent
        """
        index = self.indexAt(mouseEvent.position().toPoint())
        if index.isValid():
            itm = self.model().item(index)
            if isinstance(
                itm,
                (
                    BrowserDirectoryItem,
                    BrowserImportsItem,
                    ProjectBrowserSimpleDirectoryItem,
                    BrowserSysPathItem,
                    BrowserGlobalsItem,
                ),
            ):
                self.setExpanded(index, not self.isExpanded(index))
            else:
                self._openItem()

    def _contextMenuRequested(self, coord):
        """
        Protected slot to show the context menu of the list view.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        categories = self.getSelectedItemsCountCategorized(
            [BrowserDirectoryItem, BrowserFileItem, BrowserClassItem, BrowserMethodItem]
        )
        cnt = categories["sum"]
        bfcnt = categories[str(BrowserFileItem)]
        if cnt > 1 and cnt == bfcnt:
            self.multiMenu.popup(self.mapToGlobal(coord))
        else:
            index = self.indexAt(coord)

            if index.isValid():
                self.setCurrentIndex(index)
                flags = (
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QItemSelectionModel.SelectionFlag.Rows
                )
                self.selectionModel().select(index, flags)

                itm = self.model().item(index)
                coord = self.mapToGlobal(coord)
                if isinstance(itm, BrowserFileItem):
                    if itm.isPython3File():
                        if itm.fileName().endswith(".py"):
                            self.testingAct.setEnabled(True)
                        else:
                            self.testingAct.setEnabled(False)
                        self.sourceMenu.popup(coord)
                    else:
                        self.editPixmapAct.setVisible(itm.isPixmapFile())
                        self.openInEditorAct.setVisible(itm.isSvgFile())
                        self.openInPdfViewerAct.setVisible(itm.isPdfFile())
                        self.menu.popup(coord)
                elif isinstance(
                    itm, (BrowserClassItem, BrowserMethodItem, BrowserImportItem)
                ):
                    self.editPixmapAct.setVisible(False)
                    self.openInPdfViewerAct.setVisible(False)
                    self.menu.popup(coord)
                elif isinstance(itm, BrowserClassAttributeItem):
                    self.__amRemoteTopLevelAct.setEnabled(
                        self.__ericServerInterface.isServerConnected()
                    )
                    self.attributeMenu.popup(coord)
                elif isinstance(itm, BrowserDirectoryItem):
                    if not index.parent().isValid():
                        self.removeFromToplevelAct.setEnabled(True)
                        self.addAsTopLevelAct.setEnabled(False)
                    else:
                        self.removeFromToplevelAct.setEnabled(False)
                        self.addAsTopLevelAct.setEnabled(True)
                    self.__dmRemoteTopLevelAct.setEnabled(
                        self.__ericServerInterface.isServerConnected()
                    )
                    self.dirMenu.popup(coord)
                else:
                    self.__bmRemoteTopLevelAct.setEnabled(
                        self.__ericServerInterface.isServerConnected()
                    )
                    self.backMenu.popup(coord)
            else:
                self.__bmRemoteTopLevelAct.setEnabled(
                    self.__ericServerInterface.isServerConnected()
                )
                self.backMenu.popup(self.mapToGlobal(coord))

    def _showGotoMenu(self):
        """
        Protected slot to prepare the goto submenu of the attribute menu.
        """
        self.gotoMenu.clear()

        itm = self.model().item(self.currentIndex())
        linenos = itm.linenos()
        fileName = itm.fileName()

        for lineno in sorted(linenos):
            act = self.gotoMenu.addAction(
                QCoreApplication.translate("Browser", "Line {0}").format(lineno)
            )
            act.setData([fileName, lineno])

    def _gotoAttribute(self, act):
        """
        Protected slot to handle the selection of the goto menu.

        @param act reference to the action
        @type EricAction
        """
        fileName, lineno = act.data()
        self.sourceFile[str, int].emit(fileName, lineno)

    def handlePreferencesChanged(self):
        """
        Public slot used to handle the preferencesChanged signal.
        """
        self.model().preferencesChanged()
        self.layoutDisplay()

    def _openItem(self):
        """
        Protected slot to handle the open popup menu entry.
        """
        itmList = self.getSelectedItems(
            [
                BrowserFileItem,
                BrowserClassItem,
                BrowserMethodItem,
                BrowserClassAttributeItem,
                BrowserImportItem,
            ]
        )

        if not self._activating:
            self._activating = True
            for itm in itmList:
                if isinstance(itm, BrowserFileItem):
                    if (
                        itm.isPython3File()
                        or itm.isResourcesFile()
                        or itm.isParsableFile()
                    ):
                        self.sourceFile[str].emit(itm.fileName())
                    elif itm.isRubyFile():
                        self.sourceFile[str, int, str].emit(itm.fileName(), -1, "Ruby")
                    elif itm.isDFile():
                        self.sourceFile[str, int, str].emit(itm.fileName(), -1, "D")
                    elif itm.isDesignerFile():
                        self.designerFile.emit(itm.fileName())
                    elif itm.isLinguistFile():
                        if itm.fileExt() == ".ts":
                            self.linguistFile.emit(itm.fileName())
                        else:
                            self.trpreview.emit([itm.fileName()])
                    elif itm.isProjectFile():
                        self.projectFile.emit(itm.fileName())
                    elif itm.isMultiProjectFile():
                        self.multiProjectFile.emit(itm.fileName())
                    elif itm.isSvgFile():
                        self.svgFile.emit(itm.fileName())
                    elif itm.isPixmapFile():
                        self.pixmapFile.emit(itm.fileName())
                    elif itm.isEricGraphicsFile():
                        self.umlFile.emit(itm.fileName())
                    else:
                        if MimeTypes.isTextFile(itm.fileName()):
                            self.sourceFile[str].emit(itm.fileName())
                        else:
                            QDesktopServices.openUrl(QUrl(itm.fileName()))
                elif isinstance(itm, BrowserClassItem):
                    self.sourceFile[str, int, int].emit(
                        itm.fileName(), itm.lineno(), itm.colOffset()
                    )
                elif isinstance(itm, BrowserMethodItem):
                    self.sourceFile[str, int, int].emit(
                        itm.fileName(), itm.lineno(), itm.colOffset()
                    )
                elif isinstance(itm, BrowserClassAttributeItem):
                    self.sourceFile[str, int, int].emit(
                        itm.fileName(), itm.lineno(), itm.colOffset()
                    )
                elif isinstance(itm, BrowserImportItem):
                    self.sourceFile[str, list].emit(itm.fileName(), itm.linenos())
            self._activating = False

    def _showInFileManager(self):
        """
        Protected method to show the selected items path in a file manager application.
        """
        itmList = self.getSelectedItems(
            [
                BrowserFileItem,
                BrowserClassItem,
                BrowserMethodItem,
                BrowserClassAttributeItem,
                BrowserImportItem,
                BrowserDirectoryItem,
                BrowserSimpleDirectoryItem,
            ]
        )
        for itm in itmList:
            directory = (
                itm.dirName()
                if isinstance(itm, (BrowserDirectoryItem, BrowserSimpleDirectoryItem))
                else os.path.dirname(itm.fileName())
            )
            if FileSystemUtilities.isRemoteFileName(directory):
                EricMessageBox.critical(
                    self,
                    self.tr("Show in File Manager"),
                    self.tr(
                        "Directories accessed through an eric-ide server cannot be"
                        " opened in a file manager application. Aborting..."
                    ),
                )
                return

            ok = FileSystemUtilities.startfile(directory)

            if not ok:
                EricMessageBox.warning(
                    self,
                    self.tr("Show in File Manager"),
                    self.tr(
                        "<p>The directory of the selected item (<b>{0}</b>) cannot be"
                        " shown in a file manager application.</p>"
                    ).format(directory),
                )

    def __showMimeType(self):
        """
        Private slot to show the mime type of the selected entry.
        """
        itmList = self.getSelectedItems(
            [
                BrowserFileItem,
                BrowserClassItem,
                BrowserMethodItem,
                BrowserClassAttributeItem,
                BrowserImportItem,
            ]
        )
        if itmList:
            mimetype = MimeTypes.mimeType(itmList[0].fileName())
            if mimetype is None:
                EricMessageBox.warning(
                    self,
                    QCoreApplication.translate("Browser", "Show Mime-Type"),
                    QCoreApplication.translate(
                        "Browser",
                        """The mime type of the file could not be determined.""",
                    ),
                )
            elif mimetype.split("/")[0] == "text":
                EricMessageBox.information(
                    self,
                    QCoreApplication.translate("Browser", "Show Mime-Type"),
                    QCoreApplication.translate(
                        "Browser", """The file has the mime type <b>{0}</b>."""
                    ).format(mimetype),
                )
            else:
                textMimeTypesList = Preferences.getUI("TextMimeTypes")
                if mimetype in textMimeTypesList:
                    EricMessageBox.information(
                        self,
                        QCoreApplication.translate("Browser", "Show Mime-Type"),
                        QCoreApplication.translate(
                            "Browser", """The file has the mime type <b>{0}</b>."""
                        ).format(mimetype),
                    )
                else:
                    ok = EricMessageBox.yesNo(
                        self,
                        QCoreApplication.translate("Browser", "Show Mime-Type"),
                        QCoreApplication.translate(
                            "Browser",
                            """The file has the mime type <b>{0}</b>."""
                            """<br/> Shall it be added to the list of"""
                            """ text mime types?""",
                        ).format(mimetype),
                    )
                    if ok:
                        textMimeTypesList.append(mimetype)
                        Preferences.setUI("TextMimeTypes", textMimeTypesList)

    def __refreshSource(self):
        """
        Private slot to refresh the structure of a source file.
        """
        itmList = self.getSelectedItems([BrowserFileItem])
        if itmList:
            self.__model.repopulateFileItem(itmList[0])

    def _editPixmap(self):
        """
        Protected slot to handle the open in icon editor popup menu entry.
        """
        itmList = self.getSelectedItems([BrowserFileItem])

        for itm in itmList:
            if isinstance(itm, BrowserFileItem) and itm.isPixmapFile():
                self.pixmapEditFile.emit(itm.fileName())

    def _openHexEditor(self):
        """
        Protected slot to handle the open in hex editor popup menu entry.
        """
        itmList = self.getSelectedItems([BrowserFileItem])

        for itm in itmList:
            if isinstance(itm, BrowserFileItem):
                self.binaryFile.emit(itm.fileName())

    def _openPdfViewer(self):
        """
        Protected slot to handle the open in PDF viewer popup menu entry.
        """
        itmList = self.getSelectedItems([BrowserFileItem])

        for itm in itmList:
            if isinstance(itm, BrowserFileItem):
                self.pdfFile.emit(itm.fileName())

    def _openFileInEditor(self):
        """
        Protected slot to handle the Open in Editor menu action.
        """
        itmList = self.getSelectedItems([BrowserFileItem])

        for itm in itmList:
            if MimeTypes.isTextFile(itm.fileName()):
                self.sourceFile.emit(itm.fileName())

    def _copyToClipboard(self):
        """
        Protected method to copy the text shown for an entry to the clipboard.
        """
        itm = self.model().item(self.currentIndex())
        try:
            fn = itm.fileName()
        except AttributeError:
            try:
                fn = itm.dirName()
            except AttributeError:
                fn = ""

        if fn:
            cb = QApplication.clipboard()
            cb.setText(fn)

    @pyqtSlot(bool)
    def _showHidden(self, checked):
        """
        Protected slot to show or hide hidden files.

        @param checked flag indicating the state of the action
        @type bool
        """
        self.__sortModel.setShowHiddenFiles(checked)
        # remember the current state
        Preferences.setUI("BrowsersListHiddenFiles", checked)

    @pyqtSlot()
    def handleTesting(self):
        """
        Public slot to handle the testing popup menu entry.
        """
        try:
            index = self.currentIndex()
            itm = self.model().item(index)
            pyfn = itm.fileName()
        except AttributeError:
            pyfn = None

        if pyfn is not None:
            self.testFile.emit(pyfn)

    @pyqtSlot()
    def __newTopLevelDir(self):
        """
        Private slot to handle the New Top Level Directory popup menu entry.
        """
        dname = EricFileDialog.getExistingDirectory(
            None,
            QCoreApplication.translate("Browser", "New Top Level Directory"),
            "",
            EricFileDialog.ShowDirsOnly,
        )
        if dname:
            dname = os.path.abspath(FileSystemUtilities.toNativeSeparators(dname))
            self.__model.addTopLevelDir(dname)

    @pyqtSlot()
    def __newRemoteTopLevelDir(self):
        """
        Private slot to handle the New Remote Top Level Directory popup menu entry.
        """
        dname = EricServerFileDialog.getExistingDirectory(
            None,
            QCoreApplication.translate("Browser", "New Remote Top Level Directory"),
            "",
            dirsOnly=True,
        )
        if dname:
            self.__model.addTopLevelDir(dname)

    @pyqtSlot()
    def __removeToplevel(self):
        """
        Private slot to handle the Remove from top level popup menu entry.
        """
        index = self.currentIndex()
        sindex = self.model().mapToSource(index)
        self.__model.removeToplevelDir(sindex)

    @pyqtSlot()
    def __addAsToplevelDir(self):
        """
        Private slot to handle the Add as top level directory popup menu entry.
        """
        index = self.currentIndex()
        dname = self.model().item(index).dirName()
        self.__model.addTopLevelDir(dname)

    @pyqtSlot()
    def __refreshDirectory(self):
        """
        Private slot to refresh a directory entry.
        """
        index = self.currentIndex()
        self.__model.refreshDirectory(self.model().mapToSource(index))

    @pyqtSlot()
    def __findInDirectory(self):
        """
        Private slot to handle the Find in directory popup menu entry.
        """
        index = self.currentIndex()
        searchDir = self.model().item(index).dirName()

        ericApp().getObject("UserInterface").showFindFilesWidget(searchDir=searchDir)

    @pyqtSlot()
    def __replaceInDirectory(self):
        """
        Private slot to handle the Find&Replace in directory popup menu entry.
        """
        index = self.currentIndex()
        searchDir = self.model().item(index).dirName()

        ericApp().getObject("UserInterface").showReplaceFilesWidget(searchDir=searchDir)

    @pyqtSlot(str)
    def handleProgramChange(self, fn):
        """
        Public slot to handle the programChange signal.

        @param fn file name
        @type str
        """
        self.__model.programChange(os.path.dirname(fn))

    @pyqtSlot(str)
    def handleInterpreterChanged(self, interpreter):
        """
        Public slot to handle a change of the debug client's interpreter.

        @param interpreter interpreter of the debug client
        @type str
        """
        self.__model.interpreterChanged(interpreter)

    def wantedItem(self, itm, filterList=None):
        """
        Public method to check type of an item.

        @param itm the item to check
        @type BrowserItem
        @param filterList list of classes to check against
        @type list of Class
        @return flag indicating item is a valid type
        @rtype bool
        """
        if filterList is None:
            filterList = self.selectedItemsFilter

        return any(isinstance(itm, typ) for typ in filterList)

    def getSelectedItems(self, filterList=None):
        """
        Public method to get the selected items.

        @param filterList list of classes to check against
        @type list of Class
        @return list of selected items
        @rtype list of BrowserItem
        """
        selectedItems = []
        indexes = self.selectedIndexes()
        for index in indexes:
            if index.column() == 0:
                itm = self.model().item(index)
                if self.wantedItem(itm, filterList):
                    selectedItems.append(itm)
        return selectedItems

    def getSelectedItemsCount(self, filterList=None):
        """
        Public method to get the count of items selected.

        @param filterList list of classes to check against
        @type list of Class
        @return count of items selected
        @rtype int
        """
        count = 0
        indexes = self.selectedIndexes()
        for index in indexes:
            if index.column() == 0:
                itm = self.model().item(index)
                if self.wantedItem(itm, filterList):
                    count += 1
        return count

    def getSelectedItemsCountCategorized(self, filterList=None):
        """
        Public method to get a categorized count of selected items.

        @param filterList list of classes to check against
        @type list of Class
        @return a dictionary containing the counts of items belonging
            to the individual filter classes. The keys of the dictionary
            are the string representation of the classes given in the
            filter (i.e. str(filterClass)). The dictionary contains
            an additional entry with key "sum", that stores the sum of
            all selected entries fulfilling the filter criteria.
        @rtype dict
        """
        if filterList is None:
            filterList = self.selectedItemsFilter
        categories = {"sum": 0}
        for typ in filterList:
            categories[str(typ)] = 0

        indexes = self.selectedIndexes()
        for index in indexes:
            if index.column() == 0:
                itm = self.model().item(index)
                for typ in filterList:
                    if isinstance(itm, typ):
                        categories["sum"] += 1
                        categories[str(typ)] += 1

        return categories

    def saveToplevelDirs(self):
        """
        Public slot to save the toplevel directories.
        """
        self.__model.saveToplevelDirs()

    def keyboardSearch(self, search):
        """
        Public function to search the tree via the keyboard.

        @param search the character entered via the keyboard
        @type str
        """
        if self.model().rowCount() == 0:
            return

        startIndex = (
            self.currentIndex()
            if self.currentIndex().isValid()
            else self.model().index(0, 0)
        )

        keyboardSearchTimeWasValid = self._keyboardSearchTimer.isValid()
        keyboardSearchTimeElapsed = self._keyboardSearchTimer.restart()
        if (
            not search
            or not keyboardSearchTimeWasValid
            or keyboardSearchTimeElapsed > QApplication.keyboardInputInterval()
        ):
            self._keyboardSearchString = search.lower()
        else:
            self._keyboardSearchString += search.lower()

        index = startIndex
        found = False
        while True:
            name = self.model().data(index)
            if name.lower().startswith(
                self._keyboardSearchString
            ) and self._keyboardSearchType(self.model().item(index)):
                found = True
                break

            index = self.indexBelow(index)
            if not index.isValid():
                index = self.model().index(0, 0)
            if index == startIndex:
                break

        if found:
            self.setCurrentIndex(index)

    def _keyboardSearchType(self, item):
        """
        Protected method to check, if the item is of the correct type.

        @param item reference to the item
        @type BrowserItem
        @return flag indicating a correct type
        @rtype bool
        """
        return isinstance(
            item, (BrowserDirectoryItem, BrowserFileItem, BrowserSysPathItem)
        )

    @pyqtSlot()
    def _newDirectory(self):
        """
        Protected slot to create a new directory.
        """
        index = self.currentIndex()
        if index.isValid():
            dname = self.model().item(index).dirName()
            newName, ok = QInputDialog.getText(
                self,
                self.tr("New Directory"),
                self.tr("Name for new directory:"),
                QLineEdit.EchoMode.Normal,
            )
            if ok and bool(newName):
                if FileSystemUtilities.isRemoteFileName(dname):
                    dirpath = self.__remotefsInterface.join(dname, newName)
                    dirExists = self.__remotefsInterface.exists(dirpath)
                else:
                    dirpath = os.path.join(dname, newName)
                    dirExists = os.path.exists(dirpath)
                if dirExists:
                    EricMessageBox.warning(
                        self,
                        self.tr("New Directory"),
                        self.tr(
                            "A file or directory named <b>{0}</b> exists"
                            " already. Aborting..."
                        ).format(newName),
                    )
                else:
                    try:
                        if FileSystemUtilities.isRemoteFileName(dirpath):
                            self.__remotefsInterface.mkdir(dirpath, mode=0o751)
                        else:
                            os.mkdir(dirpath, mode=0o751)
                    except OSError as err:
                        EricMessageBox.critical(
                            self,
                            self.tr("New Directory"),
                            self.tr(
                                "<p>The directory <b>{0}</b> could not be"
                                " created.</p><p>Reason: {1}</p>"
                            ).format(newName, str(err)),
                        )

    @pyqtSlot()
    def _newFile(self):
        """
        Protected slot to create a new file.
        """
        index = self.currentIndex()
        if index.isValid():
            dname = self.model().item(index).dirName()
            fname, ok = QInputDialog.getText(
                self,
                self.tr("New File"),
                self.tr("Name for new file:"),
                QLineEdit.EchoMode.Normal,
            )
            if ok and bool(fname):
                if FileSystemUtilities.isRemoteFileName(dname):
                    filepath = self.__remotefsInterface.join(dname, fname)
                    fileExists = self.__remotefsInterface.exists(filepath)
                else:
                    filepath = os.path.join(dname, fname)
                    fileExists = os.path.exists(filepath)
                if fileExists:
                    EricMessageBox.warning(
                        self,
                        self.tr("New File"),
                        self.tr(
                            "A file or directory named <b>{0}</b> exists"
                            " already. Aborting..."
                        ).format(fname),
                    )
                else:
                    try:
                        if FileSystemUtilities.isRemoteFileName(filepath):
                            self.__remotefsInterface.writeFile(filepath, b"")
                        else:
                            with open(filepath, "w"):
                                pass
                    except OSError as err:
                        EricMessageBox.critical(
                            self,
                            self.tr("New File"),
                            self.tr(
                                "<p>The file <b>{0}</b> could not be"
                                " created.</p><p>Reason: {1}</p>"
                            ).format(fname, str(err)),
                        )

    @pyqtSlot()
    def _deleteFileOrDirectory(self):
        """
        Protected slot to delete a directory or file.
        """
        index = self.currentIndex()
        if index.isValid():
            itm = self.model().item(index)
            if itm.type() == BrowserItemType.Directory:
                self.__deleteDirectory(itm.dirName())
            else:
                self.__deleteFile(itm.fileName())

    def __deleteFile(self, fn):
        """
        Private method to delete a file.

        @param fn filename to be deleted
        @type str
        """
        dlg = DeleteFilesConfirmationDialog(
            self.parent(),
            self.tr("Delete File"),
            self.tr("Do you really want to delete this file?"),
            [fn],
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                if FileSystemUtilities.isRemoteFileName(fn):
                    self.__remotefsInterface.remove(fn)
                else:
                    os.remove(fn)
            except OSError as err:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Delete File"),
                    self.tr(
                        "<p>The selected file <b>{0}</b> could not be"
                        " deleted.</p><p>Reason: {1}</p>"
                    ).format(fn, str(err)),
                )

    def __deleteDirectory(self, dn):
        """
        Private method to delete a directory.

        @param dn directory name to be removed from the project
        @type str
        """
        dlg = DeleteFilesConfirmationDialog(
            self.parent(),
            self.tr("Delete Directory"),
            self.tr("Do you really want to delete this directory?"),
            [dn],
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                if FileSystemUtilities.isRemoteFileName(dn):
                    self.__remotefsInterface.shutilRmtree(dn, ignore_errors=True)
                else:
                    shutil.rmtree(dn, ignore_errors=True)
            except OSError as err:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Delete Directory"),
                    self.tr(
                        "<p>The selected directory <b>{0}</b> could not be"
                        " deleted.</p><p>Reason: {1}</p>"
                    ).format(dn, str(err)),
                )

    @pyqtSlot()
    def __deleteMultiple(self):
        """
        Private slot to delete multiple files.

        Note: The context menu for multi selection is only shown for file
        items.
        """
        fileNames = []
        for itm in self.getSelectedItems():
            fileNames.append(itm.fileName())

        dlg = DeleteFilesConfirmationDialog(
            self.parent(),
            self.tr("Delete Files"),
            self.tr("Do you really want to delete these files?"),
            sorted(fileNames),
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            for fn in fileNames:
                try:
                    if FileSystemUtilities.isRemoteFileName(fn):
                        self.__remotefsInterface.remove(fn)
                    else:
                        os.remove(fn)
                except OSError as err:
                    EricMessageBox.critical(
                        self.ui,
                        self.tr("Delete File"),
                        self.tr(
                            "<p>The selected file <b>{0}</b> could not be"
                            " deleted.</p><p>Reason: {1}</p>"
                        ).format(fn, str(err)),
                    )
