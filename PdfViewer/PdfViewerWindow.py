# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the PDF viewer main window.
"""

import contextlib
import os
import pathlib

from PyQt6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QPointF,
    QSize,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QActionGroup, QClipboard, QGuiApplication, QKeySequence
from PyQt6.QtPdf import QPdfDocument, QPdfLink
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (
    QDialog,
    QInputDialog,
    QLineEdit,
    QMenu,
    QSplitter,
    QTabWidget,
    QToolBar,
    QWhatsThis,
)

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricStretchableSpacer import EricStretchableSpacer
from eric7.Globals import recentNamePdfFiles
from eric7.RemoteServerInterface import EricServerFileDialog
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from .PdfInfoWidget import PdfInfoWidget
from .PdfPageSelector import PdfPageSelector
from .PdfSearchWidget import PdfSearchWidget
from .PdfToCWidget import PdfToCWidget
from .PdfView import PdfView
from .PdfZoomSelector import PdfZoomSelector


class PdfViewerWindow(EricMainWindow):
    """
    Class implementing the PDF viewer main window.

    @signal viewerClosed() emitted after the window was requested to close
    """

    viewerClosed = pyqtSignal()

    windows = []

    maxMenuFilePathLen = 75

    def __init__(self, fileName="", parent=None, fromEric=False, project=None):
        """
        Constructor

        @param fileName name of a file to load on startup
        @type str
        @param parent parent widget of this window
        @type QWidget
        @param fromEric flag indicating whether it was called from within
            eric
        @type bool
        @param project reference to the project object
        @type Project
        """
        super().__init__(parent)
        self.setObjectName("eric7_pdf_viewer")

        self.__fromEric = fromEric
        self.setWindowIcon(EricPixmapCache.getIcon("ericPdf"))

        if not self.__fromEric:
            self.setStyle(
                styleName=Preferences.getUI("Style"),
                styleSheetFile=Preferences.getUI("StyleSheet"),
                itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
            )

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
            if self.__fromEric
            else None
        )

        self.__pdfDocument = QPdfDocument(self)

        self.__cw = QSplitter(Qt.Orientation.Horizontal, self)
        self.__cw.setChildrenCollapsible(False)
        self.__info = QTabWidget(self)
        self.__cw.addWidget(self.__info)
        self.__view = PdfView(self)
        self.__view.setDocument(self.__pdfDocument)
        self.__cw.addWidget(self.__view)
        self.setCentralWidget(self.__cw)

        # create the various info widgets
        self.__documentInfoWidget = PdfInfoWidget(self.__pdfDocument, self)
        index = self.__info.addTab(
            self.__documentInfoWidget, EricPixmapCache.getIcon("documentProperties"), ""
        )
        self.__info.setTabToolTip(index, self.tr("Document Properties"))

        self.__searchWidget = PdfSearchWidget(self.__pdfDocument, self)
        index = self.__info.addTab(
            self.__searchWidget, EricPixmapCache.getIcon("find"), ""
        )
        self.__info.setTabToolTip(index, self.tr("Search"))

        self.__tocWidget = PdfToCWidget(self.__pdfDocument, self)
        index = self.__info.addTab(
            self.__tocWidget, EricPixmapCache.getIcon("listSelection"), ""
        )
        self.__info.setTabToolTip(index, self.tr("Table of Contents"))

        self.__info.setCurrentWidget(self.__tocWidget)

        # create a few widgets needed in the toolbars
        self.__pageSelector = PdfPageSelector(self)
        self.__pageSelector.setDocument(self.__pdfDocument)
        self.__view.pageNavigator().currentPageChanged.connect(
            self.__pageSelector.setValue
        )
        self.__pageSelector.valueChanged.connect(self.__pageSelected)
        self.__pageSelector.gotoPage.connect(self.__gotoPage)

        self.__zoomSelector = PdfZoomSelector(self)
        self.__zoomSelector.reset()

        g = Preferences.getGeometry("PdfViewerGeometry")
        if g.isEmpty():
            s = QSize(1000, 1000)
            self.resize(s)
            self.__cw.setSizes([300, 700])
        else:
            self.restoreGeometry(g)

        self.__initActions()
        self.__initMenus()
        self.__initToolbars()
        self.__createStatusBar()

        self.__setDisplayMode()  # needs to be done after actions have been created

        self.__view.pageNavigator().backAvailableChanged.connect(
            self.backwardAct.setEnabled
        )
        self.__view.pageNavigator().forwardAvailableChanged.connect(
            self.forwardAct.setEnabled
        )

        self.__zoomSelector.zoomModeChanged.connect(self.__view.setZoomMode)
        self.__zoomSelector.zoomModeChanged.connect(self.__zoomModeChanged)
        self.__zoomSelector.zoomFactorChanged.connect(self.__view.setZoomFactor)
        self.__view.zoomFactorChanged.connect(self.__zoomSelector.setZoomFactor)
        self.__view.zoomModeChanged.connect(self.__zoomSelector.setZoomMode)
        self.__view.selectionAvailable.connect(self.copyAct.setEnabled)

        self.__tocWidget.topicActivated.connect(self.__tocActivated)

        self.__searchWidget.searchResultActivated.connect(self.__handleSearchResult)
        self.__searchWidget.searchNextAvailable.connect(self.searchNextAct.setEnabled)
        self.__searchWidget.searchPrevAvailable.connect(self.searchPrevAct.setEnabled)
        self.__searchWidget.searchCleared.connect(self.__view.clearSearchMarkers)
        self.__searchWidget.searchResult.connect(self.__view.addSearchMarker)

        PdfViewerWindow.windows.append(self)

        self.__restoreViewerState()

        self.__checkActions()

        self.__project = project
        self.__lastOpenPath = ""

        self.__recent = []
        self.__loadRecent()

        self.__setCurrentFile("")
        self.__setViewerTitle("")
        if fileName:
            self.__loadPdfFile(fileName)

    def __initActions(self):
        """
        Private method to define the user interface actions.
        """
        # list of all actions
        self.__actions = []

        self.__initFileActions()
        self.__initGotoActions()
        self.__initViewActions()
        self.__initEditActions()
        self.__initSettingsActions()
        self.__initHelpActions()

    def __initFileActions(self):
        """
        Private method to define the file related user interface actions.
        """
        self.newWindowAct = EricAction(
            self.tr("New Window"),
            EricPixmapCache.getIcon("newWindow"),
            self.tr("New &Window"),
            QKeySequence(self.tr("Ctrl+Shift+N", "File|New Window")),
            0,
            self,
            "pdfviewer_file_new_window",
        )
        self.newWindowAct.setStatusTip(
            self.tr("Open a PDF file in a new PDF Viewer window")
        )
        self.newWindowAct.setWhatsThis(
            self.tr(
                """<b>New Window</b>"""
                """<p>This opens a PDF file in a new PDF Viewer window. It pops up"""
                """ a file selection dialog.</p>"""
            )
        )
        self.newWindowAct.triggered.connect(self.__openPdfFileNewWindow)
        self.__actions.append(self.newWindowAct)

        self.openAct = EricAction(
            self.tr("Open"),
            EricPixmapCache.getIcon("documentOpen"),
            self.tr("&Open..."),
            QKeySequence(self.tr("Ctrl+O", "File|Open")),
            0,
            self,
            "pdfviewer_file_open",
        )
        self.openAct.setStatusTip(self.tr("Open a PDF file for viewing"))
        self.openAct.setWhatsThis(
            self.tr(
                """<b>Open</b>"""
                """<p>This opens a PDF file for viewing. It pops up a file"""
                """ selection dialog.</p>"""
            )
        )
        self.openAct.triggered.connect(self.__openPdfFile)
        self.__actions.append(self.openAct)

        self.reloadAct = EricAction(
            self.tr("Reload"),
            EricPixmapCache.getIcon("reload"),
            self.tr("&Reload"),
            QKeySequence("F5"),
            0,
            self,
            "pdfviewer_file_reload",
        )
        self.reloadAct.setStatusTip(self.tr("Reload the current PDF document"))
        self.reloadAct.triggered.connect(self.__reload)
        self.__actions.append(self.reloadAct)

        self.propertiesAct = EricAction(
            self.tr("Properties"),
            EricPixmapCache.getIcon("documentProperties"),
            self.tr("&Properties..."),
            QKeySequence(self.tr("Alt+Return")),
            0,
            self,
            "pdfviewer_file_properties",
        )
        self.propertiesAct.setStatusTip(self.tr("Show the document properties"))
        self.propertiesAct.setWhatsThis(
            self.tr(
                """<b>Properties</b><p>Shows the info tab of the document"""
                """ properties.</p>"""
            )
        )
        self.propertiesAct.triggered.connect(self.__showDocumentProperties)
        self.__actions.append(self.propertiesAct)

        self.closeAct = EricAction(
            self.tr("Close"),
            EricPixmapCache.getIcon("close"),
            self.tr("&Close"),
            QKeySequence(self.tr("Ctrl+W", "File|Close")),
            0,
            self,
            "pdfviewer_file_close",
        )
        self.closeAct.setStatusTip(self.tr("Close the current PDF Viewer window"))
        self.closeAct.triggered.connect(self.close)
        self.__actions.append(self.closeAct)

        self.closeAllAct = EricAction(
            self.tr("Close All"),
            self.tr("Close &All"),
            0,
            0,
            self,
            "pdfviewer_file_close_all",
        )
        self.closeAllAct.setStatusTip(self.tr("Close all PDF Viewer windows"))
        self.closeAllAct.triggered.connect(self.__closeAll)
        self.__actions.append(self.closeAllAct)

        self.closeOthersAct = EricAction(
            self.tr("Close Others"),
            self.tr("Close Others"),
            0,
            0,
            self,
            "pdfviewer_file_close_others",
        )
        self.closeOthersAct.setStatusTip(self.tr("Close all other PDF Viewer windows"))
        self.closeOthersAct.triggered.connect(self.__closeOthers)
        self.__actions.append(self.closeOthersAct)

        self.exitAct = EricAction(
            self.tr("Quit"),
            EricPixmapCache.getIcon("exit"),
            self.tr("&Quit"),
            QKeySequence(self.tr("Ctrl+Q", "File|Quit")),
            0,
            self,
            "pdfviewer_file_quit",
        )
        self.exitAct.setStatusTip(self.tr("Quit the PDF Viewer"))
        if not self.__fromEric:
            self.exitAct.triggered.connect(self.__closeAll)
        self.__actions.append(self.exitAct)

    def __initGotoActions(self):
        """
        Private method to define the navigation related user interface actions.
        """
        self.previousPageAct = EricAction(
            self.tr("Previous Page"),
            EricPixmapCache.getIcon("1leftarrow"),
            self.tr("&Previous Page"),
            0,
            0,
            self,
            "pdfviewer_goto_previous",
        )
        self.previousPageAct.setStatusTip(self.tr("Go to the previous page"))
        self.previousPageAct.triggered.connect(self.__previousPage)
        self.__actions.append(self.previousPageAct)

        self.nextPageAct = EricAction(
            self.tr("Next Page"),
            EricPixmapCache.getIcon("1rightarrow"),
            self.tr("&Next Page"),
            0,
            0,
            self,
            "pdfviewer_goto_next",
        )
        self.nextPageAct.setStatusTip(self.tr("Go to the next page"))
        self.nextPageAct.triggered.connect(self.__nextPage)
        self.__actions.append(self.nextPageAct)

        self.startDocumentAct = EricAction(
            self.tr("Start of Document"),
            EricPixmapCache.getIcon("gotoFirst"),
            self.tr("&Start of Document"),
            QKeySequence(self.tr("Ctrl+Home", "Goto|Start")),
            0,
            self,
            "pdfviewer_goto_start",
        )
        self.startDocumentAct.setStatusTip(
            self.tr("Go to the first page of the document")
        )
        self.startDocumentAct.triggered.connect(self.__startDocument)
        self.__actions.append(self.startDocumentAct)

        self.endDocumentAct = EricAction(
            self.tr("End of Document"),
            EricPixmapCache.getIcon("gotoLast"),
            self.tr("&End of Document"),
            QKeySequence(self.tr("Ctrl+End", "Goto|End")),
            0,
            self,
            "pdfviewer_goto_end",
        )
        self.endDocumentAct.setStatusTip(self.tr("Go to the last page of the document"))
        self.endDocumentAct.triggered.connect(self.__endDocument)
        self.__actions.append(self.endDocumentAct)

        self.backwardAct = EricAction(
            self.tr("Back"),
            EricPixmapCache.getIcon("back"),
            self.tr("&Back"),
            QKeySequence(self.tr("Alt+Shift+Left", "Goto|Back")),
            0,
            self,
            "pdfviewer_goto_back",
        )
        self.backwardAct.setStatusTip(self.tr("Go back in the view history"))
        self.backwardAct.triggered.connect(self.__backInHistory)
        self.__actions.append(self.backwardAct)

        self.forwardAct = EricAction(
            self.tr("Forward"),
            EricPixmapCache.getIcon("forward"),
            self.tr("&Forward"),
            QKeySequence(self.tr("Alt+Shift+Right", "Goto|Forward")),
            0,
            self,
            "pdfviewer_goto_forward",
        )
        self.forwardAct.setStatusTip(self.tr("Go forward in the view history"))
        self.forwardAct.triggered.connect(self.__forwardInHistory)
        self.__actions.append(self.forwardAct)

        self.gotoAct = EricAction(
            self.tr("Go to Page"),
            EricPixmapCache.getIcon("gotoJump"),
            self.tr("&Go to Page..."),
            QKeySequence(self.tr("Ctrl+G", "Goto|Go to Page")),
            0,
            self,
            "pdfviewer_goto_gotopage",
        )
        self.gotoAct.setStatusTip(self.tr("Jump to a page selected via a dialog"))
        self.gotoAct.triggered.connect(self.__gotoPage)
        self.__actions.append(self.gotoAct)

    def __initViewActions(self):
        """
        Private method to define the view related user interface actions.
        """
        self.fullScreenAct = EricAction(
            self.tr("Full Screen"),
            EricPixmapCache.getIcon("windowFullscreen"),
            self.tr("&Full Screen"),
            0,
            0,
            self,
            "pdfviewer_view_full_screen",
        )
        if OSUtilities.isMacPlatform():
            self.fullScreenAct.setShortcut(QKeySequence(self.tr("Meta+Ctrl+F")))
        else:
            self.fullScreenAct.setShortcut(QKeySequence(self.tr("F11")))
        self.fullScreenAct.setCheckable(True)
        self.fullScreenAct.triggered.connect(self.__toggleFullScreen)
        self.__actions.append(self.fullScreenAct)

        self.zoomInAct = EricAction(
            self.tr("Zoom in"),
            EricPixmapCache.getIcon("zoomIn"),
            self.tr("Zoom &in"),
            QKeySequence(self.tr("Ctrl++", "View|Zoom in")),
            0,
            self,
            "pdfviewer_view_zoomin",
        )
        self.zoomInAct.triggered.connect(self.__zoomIn)
        self.__actions.append(self.zoomInAct)

        self.zoomOutAct = EricAction(
            self.tr("Zoom out"),
            EricPixmapCache.getIcon("zoomOut"),
            self.tr("Zoom &out"),
            QKeySequence(self.tr("Ctrl+-", "View|Zoom out")),
            0,
            self,
            "pdfviewer_view_zoomout",
        )
        self.zoomOutAct.triggered.connect(self.__zoomOut)
        self.__actions.append(self.zoomOutAct)

        self.zoomResetAct = EricAction(
            self.tr("Zoom to 100%"),
            EricPixmapCache.getIcon("zoomReset"),
            self.tr("Zoom to &100%"),
            QKeySequence(self.tr("Ctrl+0", "View|Zoom reset")),
            0,
            self,
            "pdfviewer_view_zoomreset",
        )
        self.zoomResetAct.triggered.connect(self.__zoomReset)
        self.__actions.append(self.zoomResetAct)

        self.zoomPageWidthAct = EricAction(
            self.tr("Page Width"),
            EricPixmapCache.getIcon("zoomFitWidth"),
            self.tr("Page &Width"),
            0,
            0,
            self,
            "pdfviewer_view_zoompagewidth",
        )
        self.zoomPageWidthAct.triggered.connect(self.__zoomPageWidth)
        self.zoomPageWidthAct.setCheckable(True)
        self.__actions.append(self.zoomPageWidthAct)

        self.zoomWholePageAct = EricAction(
            self.tr("Whole Page"),
            EricPixmapCache.getIcon("zoomFitPage"),
            self.tr("Whole &Page"),
            0,
            0,
            self,
            "pdfviewer_view_zoomwholePage",
        )
        self.zoomWholePageAct.triggered.connect(self.__zoomWholePage)
        self.zoomWholePageAct.setCheckable(True)
        self.__actions.append(self.zoomWholePageAct)

    def __initEditActions(self):
        """
        Private method to create the Edit actions.
        """
        self.copyAct = EricAction(
            self.tr("Copy"),
            EricPixmapCache.getIcon("editCopy"),
            self.tr("&Copy"),
            QKeySequence(self.tr("Ctrl+C", "Edit|Copy")),
            0,
            self,
            "pdfviewer_edit_copy",
        )
        self.copyAct.triggered.connect(self.__copyText)
        self.__actions.append(self.copyAct)

        self.copyAllAct = EricAction(
            self.tr("Copy All Text"),
            self.tr("Copy &All Text"),
            QKeySequence(self.tr("Alt+Ctrl+C", "Edit|Copy All Text")),
            0,
            self,
            "pdfviewer_edit_copyall",
        )
        self.copyAllAct.triggered.connect(self.__copyAllText)
        self.__actions.append(self.copyAllAct)

        self.copyAllPageAct = EricAction(
            self.tr("Copy All Page Text"),
            self.tr("Copy All Page &Text"),
            QKeySequence(self.tr("Shift+Ctrl+C", "Edit|Copy All Page Text")),
            0,
            self,
            "pdfviewer_edit_copyallpage",
        )
        self.copyAllPageAct.triggered.connect(self.__copyAllTextOfPage)
        self.__actions.append(self.copyAllPageAct)

        self.searchAct = EricAction(
            self.tr("Search"),
            EricPixmapCache.getIcon("find"),
            self.tr("&Search..."),
            QKeySequence(self.tr("Ctrl+F", "Edit|Search")),
            0,
            self,
            "pdfviewer_edit_search",
        )
        self.searchAct.triggered.connect(self.__search)
        self.__actions.append(self.searchAct)

        self.searchNextAct = EricAction(
            self.tr("Search Next"),
            EricPixmapCache.getIcon("findNext"),
            self.tr("Search &Next"),
            QKeySequence(self.tr("F3", "Edit|Search Next")),
            0,
            self,
            "pdfviewer_edit_searchnext",
        )
        self.searchNextAct.triggered.connect(self.__searchWidget.nextResult)
        self.__actions.append(self.searchNextAct)

        self.searchPrevAct = EricAction(
            self.tr("Search Previous"),
            EricPixmapCache.getIcon("findPrev"),
            self.tr("Search &Previous"),
            QKeySequence(self.tr("Shift+F3", "Edit|Search Previous")),
            0,
            self,
            "pdfviewer_edit_searchprevious",
        )
        self.searchPrevAct.triggered.connect(self.__searchWidget.previousResult)
        self.__actions.append(self.searchPrevAct)

        self.copyAct.setEnabled(False)
        self.searchNextAct.setEnabled(False)
        self.searchPrevAct.setEnabled(False)

    def __initSettingsActions(self):
        """
        Private method to create the Settings actions.
        """
        self.prefAct = EricAction(
            self.tr("Preferences"),
            EricPixmapCache.getIcon("configure"),
            self.tr("&Preferences..."),
            0,
            0,
            self,
            "pdfviewer_settings_preferences",
        )
        self.prefAct.setStatusTip(self.tr("Set the prefered configuration"))
        self.prefAct.setWhatsThis(
            self.tr(
                """<b>Preferences</b>"""
                """<p>Set the configuration items of the application"""
                """ with your prefered values.</p>"""
            )
        )
        self.prefAct.triggered.connect(self.__showPreferences)
        self.prefAct.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.__actions.append(self.prefAct)

        self.sidebarAct = EricAction(
            self.tr("Show Sidebar"),
            EricPixmapCache.getIcon("sidebarExpandLeft"),
            self.tr("Show &Sidebar"),
            0,
            0,
            self,
            "pdfviewer_settings_sidebar",
        )
        self.sidebarAct.triggered.connect(self.__toggleSideBar)
        self.sidebarAct.setCheckable(True)
        self.__actions.append(self.sidebarAct)

        self.openRecentNewAct = EricAction(
            self.tr("Open Recent File in New Window"),
            self.tr("Open Recent File in New Window"),
            0,
            0,
            self,
            "pdfviewer_settings_openrecent new",
        )
        self.openRecentNewAct.triggered.connect(self.__toggleOpenRecentNew)
        self.openRecentNewAct.setCheckable(True)
        self.__actions.append(self.sidebarAct)

    def __initHelpActions(self):
        """
        Private method to create the Help actions.
        """
        self.aboutAct = EricAction(
            self.tr("About"), self.tr("&About"), 0, 0, self, "pdfviewer_help_about"
        )
        self.aboutAct.setStatusTip(self.tr("Display information about this software"))
        self.aboutAct.setWhatsThis(
            self.tr(
                """<b>About</b>"""
                """<p>Display some information about this software.</p>"""
            )
        )
        self.aboutAct.triggered.connect(self.__about)
        self.__actions.append(self.aboutAct)

        self.aboutQtAct = EricAction(
            self.tr("About Qt"),
            self.tr("About &Qt"),
            0,
            0,
            self,
            "pdfviewer_help_about_qt",
        )
        self.aboutQtAct.setStatusTip(
            self.tr("Display information about the Qt toolkit")
        )
        self.aboutQtAct.setWhatsThis(
            self.tr(
                """<b>About Qt</b>"""
                """<p>Display some information about the Qt toolkit.</p>"""
            )
        )
        self.aboutQtAct.triggered.connect(self.__aboutQt)
        self.__actions.append(self.aboutQtAct)

        self.whatsThisAct = EricAction(
            self.tr("What's This?"),
            EricPixmapCache.getIcon("whatsThis"),
            self.tr("&What's This?"),
            QKeySequence(self.tr("Shift+F1", "Help|What's This?'")),
            0,
            self,
            "pdfviewer_help_whats_this",
        )
        self.whatsThisAct.setStatusTip(self.tr("Context sensitive help"))
        self.whatsThisAct.setWhatsThis(
            self.tr(
                """<b>Display context sensitive help</b>"""
                """<p>In What's This? mode, the mouse cursor shows an arrow"""
                """ with a question mark, and you can click on the interface"""
                """ elements to get a short description of what they do and"""
                """ how to use them. In dialogs, this feature can be accessed"""
                """ using the context help button in the titlebar.</p>"""
            )
        )
        self.whatsThisAct.triggered.connect(self.__whatsThis)
        self.__actions.append(self.whatsThisAct)

    @pyqtSlot()
    def __checkActions(self):
        """
        Private slot to check some actions for their enable/disable status.
        """
        ready = self.__pdfDocument.status() == QPdfDocument.Status.Ready

        self.reloadAct.setEnabled(ready)
        self.propertiesAct.setEnabled(ready)

        curPage = self.__view.pageNavigator().currentPage()
        self.previousPageAct.setEnabled(curPage > 0 and ready)
        self.nextPageAct.setEnabled(
            curPage < self.__pdfDocument.pageCount() - 1 and ready
        )
        self.startDocumentAct.setEnabled(curPage != 0 and ready)
        self.endDocumentAct.setEnabled(
            curPage != self.__pdfDocument.pageCount() - 1 and ready
        )
        self.gotoAct.setEnabled(ready)

        self.backwardAct.setEnabled(self.__view.pageNavigator().backAvailable())
        self.forwardAct.setEnabled(self.__view.pageNavigator().forwardAvailable())

        self.zoomInAct.setEnabled(ready)
        self.zoomOutAct.setEnabled(ready)
        self.zoomResetAct.setEnabled(ready)
        self.__zoomSelector.setEnabled(ready)

        self.copyAllAct.setEnabled(ready)
        self.copyAllPageAct.setEnabled(ready)
        self.searchAct.setEnabled(ready)

    def __initMenus(self):
        """
        Private method to create the menus.
        """
        mb = self.menuBar()

        menu = mb.addMenu(self.tr("&File"))
        menu.setTearOffEnabled(True)
        self.__recentMenu = QMenu(self.tr("Open &Recent Files"), menu)
        menu.addAction(self.newWindowAct)
        menu.addAction(self.openAct)
        self.__menuRecentAct = menu.addMenu(self.__recentMenu)
        menu.addSeparator()
        menu.addAction(self.reloadAct)
        menu.addSeparator()
        menu.addAction(self.propertiesAct)
        menu.addSeparator()
        menu.addAction(self.closeAct)
        menu.addAction(self.closeOthersAct)
        if self.__fromEric:
            menu.addAction(self.closeAllAct)
        else:
            menu.addSeparator()
            menu.addAction(self.exitAct)
        menu.aboutToShow.connect(self.__showFileMenu)
        self.__recentMenu.aboutToShow.connect(self.__showRecentMenu)
        self.__recentMenu.triggered.connect(self.__openRecentPdfFile)

        menu = mb.addMenu(self.tr("&View"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.fullScreenAct)
        menu.addSeparator()
        menu.addAction(self.zoomInAct)
        menu.addAction(self.zoomOutAct)
        menu.addAction(self.zoomResetAct)
        menu.addAction(self.zoomPageWidthAct)
        menu.addAction(self.zoomWholePageAct)
        menu.addSeparator()
        modeMenu = menu.addMenu(self.tr("Display Mode"))
        self.__singlePageAct = modeMenu.addAction(self.tr("Single Page"))
        self.__singlePageAct.setCheckable(True)
        self.__continuousPageAct = modeMenu.addAction(self.tr("Continuous"))
        self.__continuousPageAct.setCheckable(True)
        self.__displayModeActGrp = QActionGroup(self)
        self.__displayModeActGrp.addAction(self.__singlePageAct)
        self.__displayModeActGrp.addAction(self.__continuousPageAct)
        modeMenu.triggered.connect(self.__displayModeSelected)

        menu = mb.addMenu(self.tr("&Edit"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.copyAct)
        menu.addSeparator()
        menu.addAction(self.copyAllAct)
        menu.addAction(self.copyAllPageAct)
        menu.addSeparator()
        menu.addAction(self.searchAct)
        menu.addAction(self.searchNextAct)
        menu.addAction(self.searchPrevAct)

        menu = mb.addMenu(self.tr("&Go To"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.previousPageAct)
        menu.addAction(self.nextPageAct)
        menu.addSeparator()
        menu.addAction(self.startDocumentAct)
        menu.addAction(self.endDocumentAct)
        menu.addSeparator()
        menu.addAction(self.backwardAct)
        menu.addAction(self.forwardAct)
        menu.addSeparator()
        menu.addAction(self.gotoAct)

        menu = mb.addMenu(self.tr("Se&ttings"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.prefAct)
        menu.addSeparator()
        menu.addAction(self.sidebarAct)
        menu.addSeparator()
        menu.addAction(self.openRecentNewAct)

        mb.addSeparator()

        menu = mb.addMenu(self.tr("&Help"))
        menu.addAction(self.aboutAct)
        menu.addAction(self.aboutQtAct)
        menu.addSeparator()
        menu.addAction(self.whatsThisAct)

    def __initToolbars(self):
        """
        Private method to create the toolbars.
        """
        mainToolBar = QToolBar()
        mainToolBar.setObjectName("main_toolbar")
        mainToolBar.setMovable(False)
        mainToolBar.setFloatable(False)

        # 0. Sidebar action
        mainToolBar.addAction(self.sidebarAct)
        mainToolBar.addSeparator()

        # 1. File actions
        mainToolBar.addAction(self.newWindowAct)
        mainToolBar.addAction(self.openAct)
        mainToolBar.addSeparator()
        mainToolBar.addAction(self.closeAct)
        if not self.__fromEric:
            mainToolBar.addAction(self.exitAct)
        mainToolBar.addSeparator()

        # 2. Go to actions
        mainToolBar.addWidget(EricStretchableSpacer())
        mainToolBar.addAction(self.startDocumentAct)
        mainToolBar.addWidget(self.__pageSelector)
        mainToolBar.addAction(self.endDocumentAct)
        mainToolBar.addWidget(EricStretchableSpacer())
        mainToolBar.addSeparator()

        # 3. View actions
        mainToolBar.addAction(self.zoomOutAct)
        mainToolBar.addWidget(self.__zoomSelector)
        mainToolBar.addAction(self.zoomInAct)
        mainToolBar.addAction(self.zoomResetAct)
        mainToolBar.addAction(self.zoomPageWidthAct)
        mainToolBar.addAction(self.zoomWholePageAct)

        self.addToolBar(mainToolBar)
        self.addToolBarBreak()

    def __createStatusBar(self):
        """
        Private method to initialize the status bar.
        """
        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled(True)

        # not yet implemented

    def closeEvent(self, evt):
        """
        Protected method handling the close event.

        @param evt reference to the close event
        @type QCloseEvent
        """
        Preferences.setGeometry("PdfViewerGeometry", self.saveGeometry())

        self.__saveViewerState()

        with contextlib.suppress(ValueError):
            if self.__fromEric or len(PdfViewerWindow.windows) > 1:
                PdfViewerWindow.windows.remove(self)

        self.__saveRecent()

        self.__documentInfoWidget.setDocument(None)

        evt.accept()
        self.viewerClosed.emit()

    def __saveViewerState(self):
        """
        Private method to save the PDF Viewer state data.
        """
        state = self.saveState()
        Preferences.setPdfViewer("PdfViewerState", state)
        splitterState = self.__cw.saveState()
        Preferences.setPdfViewer("PdfViewerSplitterState", splitterState)
        Preferences.setPdfViewer("PdfViewerSidebarVisible", self.sidebarAct.isChecked())
        Preferences.setPdfViewer("PdfViewerZoomFactor", self.__view.zoomFactor())
        Preferences.setPdfViewer("PdfViewerZoomMode", self.__view.zoomMode())
        Preferences.setPdfViewer(
            "PdfViewerOpenRecentInNewWindow", self.openRecentNewAct.isChecked()
        )

        if not self.__fromEric:
            Preferences.syncPreferences()

    def __restoreViewerState(self):
        """
        Private method to restore the PDF Viewer state data.
        """
        state = Preferences.getPdfViewer("PdfViewerState")
        self.restoreState(state)
        splitterState = Preferences.getPdfViewer("PdfViewerSplitterState")
        self.__cw.restoreState(splitterState)
        self.__toggleSideBar(Preferences.getPdfViewer("PdfViewerSidebarVisible"))
        self.__view.setZoomFactor(Preferences.getPdfViewer("PdfViewerZoomFactor"))
        self.__view.setZoomMode(Preferences.getPdfViewer("PdfViewerZoomMode"))
        self.openRecentNewAct.setChecked(
            Preferences.getPdfViewer("PdfViewerOpenRecentInNewWindow")
        )

    def __setViewerTitle(self, title):
        """
        Private method to set the viewer title.

        @param title title to be set
        @type str
        """
        if title:
            self.setWindowTitle(self.tr("{0} - PDF Viewer").format(title))
        else:
            self.setWindowTitle(self.tr("PDF Viewer"))

    def __getErrorString(self, err):
        """
        Private method to get an error string for the given error.

        @param err error type
        @type QPdfDocument.Error
        @return string for the given error type
        @rtype str
        """
        if err == QPdfDocument.Error.None_:
            reason = ""
        elif err == QPdfDocument.Error.DataNotYetAvailable:
            reason = self.tr("The document is still loading.")
        elif err == QPdfDocument.Error.FileNotFound:
            reason = self.tr("The file does not exist.")
        elif err == QPdfDocument.Error.InvalidFileFormat:
            reason = self.tr("The file is not a valid PDF file.")
        elif err == QPdfDocument.Error.IncorrectPassword:
            reason = self.tr("The password is not correct for this file.")
        elif err == QPdfDocument.Error.UnsupportedSecurityScheme:
            reason = self.tr("This kind of PDF file cannot be unlocked.")
        else:
            reason = self.tr("Unknown type of error.")

        return reason

    def __loadPdfFile(self, fileName):
        """
        Private method to load a PDF file.

        @param fileName path of the PDF file to load
        @type str
        """
        canceled = False
        err = QPdfDocument.Error.IncorrectPassword

        if FileSystemUtilities.isRemoteFileName(fileName):
            try:
                data = QByteArray(self.__remotefsInterface.readFile(fileName))
                buffer = QBuffer(data)
            except OSError as err:
                EricMessageBox.warning(
                    self,
                    self.tr("OpenPDF File"),
                    self.tr(
                        "<p>The PDF file <b>{0}</b> could not be read.</p>"
                        "<p>Reason: {1}</p>"
                    ).format(fileName, str(err)),
                )
                return
        else:
            buffer = None

        while not canceled and err == QPdfDocument.Error.IncorrectPassword:
            if FileSystemUtilities.isRemoteFileName(fileName):
                buffer.open(QIODevice.OpenModeFlag.ReadOnly)
                self.__pdfDocument.load(buffer)
                err = QPdfDocument.Error.None_
            else:
                err = self.__pdfDocument.load(fileName)
            if err == QPdfDocument.Error.IncorrectPassword:
                password, ok = QInputDialog.getText(
                    self,
                    self.tr("Open PDF File"),
                    self.tr("Enter password to show the document:"),
                    QLineEdit.EchoMode.Password,
                )
                if ok:
                    self.__pdfDocument.setPassword(password)
                else:
                    canceled = True
        if err != QPdfDocument.Error.None_:
            EricMessageBox.critical(
                self,
                self.tr("Open PDF File"),
                self.tr(
                    """<p>The PDF file <b>{0}</b> could not be loaded.</p>"""
                    """<p>Reason: {1}</p>"""
                ).format(fileName, self.__getErrorString(err)),
            )
            self.__documentInfoWidget.setFileName("")
            return

        self.__lastOpenPath = (
            self.__remotefsInterface.dirname(fileName)
            if FileSystemUtilities.isRemoteFileName(fileName)
            else os.path.dirname(fileName)
        )
        self.__setCurrentFile(fileName)

        documentTitle = self.__pdfDocument.metaData(QPdfDocument.MetaDataField.Title)
        self.__setViewerTitle(documentTitle)

        self.__pageSelected(0)
        self.__pageSelector.setMaximum(self.__pdfDocument.pageCount() - 1)
        self.__pageSelector.setValue(0)

        self.__documentInfoWidget.setFileName(fileName)

        self.__info.setCurrentWidget(self.__tocWidget)

    @pyqtSlot()
    def __reload(self):
        """
        Private slot to reload the current PDF document.
        """
        self.__loadPdfFile(self.__fileName)

    @pyqtSlot()
    def __openPdfFile(self):
        """
        Private slot to open a PDF file.
        """
        if (
            not self.__lastOpenPath
            and self.__project is not None
            and self.__project.isOpen()
        ):
            self.__lastOpenPath = self.__project.getProjectPath()

        fileName = (
            EricServerFileDialog.getOpenFileName(
                self,
                self.tr("Open PDF File"),
                self.__lastOpenPath,
                self.tr("PDF Files (*.pdf);;All Files (*)"),
            )
            if FileSystemUtilities.isRemoteFileName(self.__lastOpenPath)
            else EricFileDialog.getOpenFileName(
                self,
                self.tr("Open PDF File"),
                self.__lastOpenPath,
                self.tr("PDF Files (*.pdf);;All Files (*)"),
            )
        )
        if fileName:
            self.__loadPdfFile(fileName)

    @pyqtSlot()
    def __openPdfFileNewWindow(self, fileName=""):
        """
        Private slot called to open a PDF file in new viewer window.

        @param fileName name of the file to open (defaults to "")
        @type str (optional)
        """
        if (
            not self.__lastOpenPath
            and self.__project is not None
            and self.__project.isOpen()
        ):
            self.__lastOpenPath = self.__project.getProjectPath()

        if not fileName:
            fileName = (
                EricServerFileDialog.getOpenFileName(
                    self,
                    self.tr("Open PDF File"),
                    self.__lastOpenPath,
                    self.tr("PDF Files (*.pdf);;All Files (*)"),
                )
                if FileSystemUtilities.isRemoteFileName(self.__lastOpenPath)
                else EricFileDialog.getOpenFileName(
                    self,
                    self.tr("Open PDF File"),
                    self.__lastOpenPath,
                    self.tr("PDF Files (*.pdf);;All Files (*)"),
                )
            )
        if fileName:
            viewer = PdfViewerWindow(
                fileName=fileName,
                parent=self.parent(),
                fromEric=self.__fromEric,
                project=self.__project,
            )
            viewer.show()

    @pyqtSlot()
    def __closeAll(self):
        """
        Private slot to close all windows.
        """
        self.__closeOthers()
        self.close()

    @pyqtSlot()
    def __closeOthers(self):
        """
        Private slot to close all other windows.
        """
        for win in PdfViewerWindow.windows[:]:
            if win != self:
                win.close()

    @pyqtSlot(int)
    def __pageSelected(self, page):
        """
        Private slot to navigate to the given page.

        @param page index of the page to be shown
        @type int
        """
        nav = self.__view.pageNavigator()
        nav.jump(page, QPointF(), nav.currentZoom())

        self.__checkActions()

    @pyqtSlot(int, float)
    def __tocActivated(self, page, zoomFactor):
        """
        Private slot to handle the selection of a ToC topic.

        @param page page number
        @type int
        @param zoomFactor zoom factor
        @type float
        """
        nav = self.__view.pageNavigator()
        nav.jump(page, QPointF(), zoomFactor)

    @pyqtSlot(QPdfLink)
    def __handleSearchResult(self, link):
        """
        Private slot to handle the selection of a search result.

        @param link PDF link to navigate to
        @type QPdfLink
        """
        self.__view.pageNavigator().jump(link)
        self.__view.addSearchMarker(link)

    @pyqtSlot()
    def __search(self):
        """
        Private slot to initiate a search.
        """
        self.__info.setCurrentWidget(self.__searchWidget)
        self.__searchWidget.activateSearch()

    def __setCurrentFile(self, fileName):
        """
        Private method to register the file name of the current file.

        @param fileName name of the file to register
        @type str
        """
        self.__fileName = fileName
        # insert filename into list of recently opened files
        self.__addToRecentList(fileName)

    @pyqtSlot()
    def __about(self):
        """
        Private slot to show a little About message.
        """
        EricMessageBox.about(
            self,
            self.tr("About eric PDF Viewer"),
            self.tr("The eric PDF Viewer is a simple component for viewing PDF files."),
        )

    @pyqtSlot()
    def __aboutQt(self):
        """
        Private slot to handle the About Qt dialog.
        """
        EricMessageBox.aboutQt(self, "eric PDF Viewer")

    @pyqtSlot()
    def __whatsThis(self):
        """
        Private slot called in to enter Whats This mode.
        """
        QWhatsThis.enterWhatsThisMode()

    @pyqtSlot()
    def __showPreferences(self):
        """
        Private slot to set the preferences.
        """
        from eric7.Preferences.ConfigurationDialog import (
            ConfigurationDialog,
            ConfigurationMode,
        )

        dlg = ConfigurationDialog(
            parent=self,
            name="Configuration",
            modal=True,
            fromEric=False,
            displayMode=ConfigurationMode.PDFVIEWERMODE,
        )
        dlg.show()
        dlg.showConfigurationPageByName("pdfViewerPage")
        dlg.exec()
        if dlg.result() == QDialog.DialogCode.Accepted:
            dlg.setPreferences()
            Preferences.syncPreferences()

    @pyqtSlot()
    def __showFileMenu(self):
        """
        Private slot to modify the file menu before being shown.
        """
        self.__menuRecentAct.setEnabled(len(self.__recent) > 0)

    @pyqtSlot()
    def __showRecentMenu(self):
        """
        Private slot to set up the recent files menu.
        """
        self.__loadRecent()

        self.__recentMenu.clear()

        for idx, rs in enumerate(self.__recent, start=1):
            formatStr = "&{0:d}. {1}" if idx < 10 else "{0:d}. {1}"
            act = self.__recentMenu.addAction(
                formatStr.format(
                    idx,
                    FileSystemUtilities.compactPath(
                        rs, PdfViewerWindow.maxMenuFilePathLen
                    ),
                )
            )
            act.setData(rs)
            act.setEnabled(pathlib.Path(rs).exists())

        self.__recentMenu.addSeparator()
        self.__recentMenu.addAction(self.tr("&Clear"), self.__clearRecent)

    @pyqtSlot(QAction)
    def __openRecentPdfFile(self, act):
        """
        Private method to open a file from the list of recently opened files.

        @param act reference to the action that triggered
        @type QAction
        """
        fileName = act.data()
        if fileName is not None:
            if Preferences.getPdfViewer("PdfViewerOpenRecentInNewWindow"):
                self.__openPdfFileNewWindow(fileName)
            else:
                self.__loadPdfFile(fileName)

    @pyqtSlot()
    def __clearRecent(self):
        """
        Private method to clear the list of recently opened files.
        """
        self.__recent = []

    def __loadRecent(self):
        """
        Private method to load the list of recently opened files.
        """
        self.__recent = []
        Preferences.Prefs.rsettings.sync()
        rs = Preferences.Prefs.rsettings.value(recentNamePdfFiles)
        if rs is not None:
            for f in EricUtilities.toList(rs):
                if pathlib.Path(f).exists():
                    self.__recent.append(f)

    def __saveRecent(self):
        """
        Private method to save the list of recently opened files.
        """
        Preferences.Prefs.rsettings.setValue(recentNamePdfFiles, self.__recent)
        Preferences.Prefs.rsettings.sync()

    def __addToRecentList(self, fileName):
        """
        Private method to add a file name to the list of recently opened files.

        @param fileName name of the file to be added
        @type str
        """
        if fileName:
            for recent in self.__recent[:]:
                if FileSystemUtilities.samepath(fileName, recent):
                    self.__recent.remove(recent)
            self.__recent.insert(0, fileName)
            maxRecent = Preferences.getPdfViewer("RecentNumber")
            if len(self.__recent) > maxRecent:
                self.__recent = self.__recent[:maxRecent]
            self.__saveRecent()

    @pyqtSlot()
    def __showDocumentProperties(self):
        """
        Private slot to open a dialog showing the document properties.
        """
        self.__toggleSideBar(True)
        self.__info.setCurrentWidget(self.__documentInfoWidget)

    @pyqtSlot()
    def __gotoPage(self):
        """
        Private slot to show a dialog to select a page to jump to.
        """
        from .PdfGoToDialog import PdfGoToDialog

        dlg = PdfGoToDialog(
            self.__view.pageNavigator().currentPage(),
            self.__pdfDocument.pageCount(),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            page = dlg.getPage()
            self.__pageSelected(page)

    @pyqtSlot()
    def __previousPage(self):
        """
        Private slot to go to the previous page.
        """
        curPage = self.__view.pageNavigator().currentPage()
        if curPage > 0:
            self.__pageSelected(curPage - 1)

    @pyqtSlot()
    def __nextPage(self):
        """
        Private slot to go to the next page.
        """
        curPage = self.__view.pageNavigator().currentPage()
        if curPage < self.__pdfDocument.pageCount() - 1:
            self.__pageSelected(curPage + 1)

    @pyqtSlot()
    def __startDocument(self):
        """
        Private slot to go to the first page of the document.
        """
        self.__pageSelected(0)

    @pyqtSlot()
    def __endDocument(self):
        """
        Private slot to go to the last page of the document.
        """
        self.__pageSelected(self.__pdfDocument.pageCount() - 1)

    @pyqtSlot()
    def __backInHistory(self):
        """
        Private slot to go back in the view history.
        """
        self.__view.pageNavigator().back()

    @pyqtSlot()
    def __forwardInHistory(self):
        """
        Private slot to go forward in the view history.
        """
        self.__view.pageNavigator().forward()

    @pyqtSlot(bool)
    def __toggleFullScreen(self, on):
        """
        Private slot to toggle the full screen mode.

        @param on flag indicating to activate full screen mode
        @type bool
        """
        if on:
            self.showFullScreen()
        else:
            self.showNormal()

    @pyqtSlot()
    def __zoomIn(self):
        """
        Private slot to zoom into the view.
        """
        self.__view.zoomIn()

    @pyqtSlot()
    def __zoomOut(self):
        """
        Private slot to zoom out of the view.
        """
        self.__view.zoomOut()

    @pyqtSlot()
    def __zoomReset(self):
        """
        Private slot to reset the zoom factor of the view.
        """
        self.__view.zoomReset()

    @pyqtSlot(bool)
    def __zoomPageWidth(self, checked):
        """
        Private slot to fit the page width.

        @param checked flag indicating the check state
        @type bool
        """
        if checked:
            self.__view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.zoomWholePageAct.setChecked(False)

    @pyqtSlot(bool)
    def __zoomWholePage(self, checked):
        """
        Private slot to fit the page width.

        @param checked flag indicating the check state
        @type bool
        """
        if checked:
            self.__view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.zoomPageWidthAct.setChecked(False)

    @pyqtSlot(QPdfView.ZoomMode)
    def __zoomModeChanged(self, zoomMode):
        """
        Private slot to handle a change of the zoom mode.

        @param zoomMode new zoom mode
        @type QPdfView.ZoomMode
        """
        self.zoomWholePageAct.setChecked(zoomMode == QPdfView.ZoomMode.FitInView)
        self.zoomPageWidthAct.setChecked(zoomMode == QPdfView.ZoomMode.FitToWidth)

    @pyqtSlot(QAction)
    def __displayModeSelected(self, act):
        """
        Private slot to handle the selection of a display mode.

        @param act reference to the triggering action
        @type QAction
        """
        if act is self.__singlePageAct:
            Preferences.setPdfViewer("PdfViewerDisplayMode", "single")
        else:
            Preferences.setPdfViewer("PdfViewerDisplayMode", "continuous")
        self.__setDisplayMode()

    def __setDisplayMode(self):
        """
        Private method to set the display mode iaw. configuration.
        """
        if Preferences.getPdfViewer("PdfViewerDisplayMode") == "single":
            self.__view.setPageMode(QPdfView.PageMode.SinglePage)
            self.__singlePageAct.setChecked(True)
        else:
            self.__view.setPageMode(QPdfView.PageMode.MultiPage)
            self.__continuousPageAct.setChecked(True)
        return

    @pyqtSlot(bool)
    def __toggleSideBar(self, visible):
        """
        Private slot to togle the sidebar (info) widget.

        @param visible desired state of the sidebar
        @type bool
        """
        self.sidebarAct.setChecked(visible)
        self.__info.setVisible(visible)
        Preferences.setPdfViewer("PdfViewerSidebarVisible", visible)

    @pyqtSlot(bool)
    def __toggleOpenRecentNew(self, on):
        """
        Private slot to toggle the 'Open Recent File in New Window' action.

        @param on desired state of the action
        @type bool
        """
        Preferences.setPdfViewer("PdfViewerOpenRecentInNewWindow", on)

    @pyqtSlot()
    def __copyAllTextOfPage(self):
        """
        Private slot to copy all text of the current page to the system clipboard.
        """
        selection = self.__pdfDocument.getAllText(
            self.__view.pageNavigator().currentPage()
        )
        selection.copyToClipboard()

    @pyqtSlot()
    def __copyAllText(self):
        """
        Private slot to copy all text of the document to the system clipboard.
        """
        textPages = []
        for page in range(self.__pdfDocument.pageCount()):
            textPages.append(self.__pdfDocument.getAllText(page).text())
        QGuiApplication.clipboard().setText(
            "\r\n".join(textPages), QClipboard.Mode.Clipboard
        )

    @pyqtSlot()
    def __copyText(self):
        """
        Private slot to copy the selected text to the system clipboard.
        """
        selection = self.__view.getSelection()
        if selection is not None:
            selection.copyToClipboard()
