# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an embedded viewer for QtHelp and local HTML files.
"""

import os

from PyQt6.QtCore import QByteArray, Qt, QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import QAction, QFont, QFontMetrics
from PyQt6.QtHelp import QHelpEngine
from PyQt6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings

    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricTextEditSearchWidget import EricTextEditSearchWidget
from eric7.EricWidgets.EricToolButton import EricToolButton
from eric7.QtHelpInterface.HelpIndexWidget import HelpIndexWidget
from eric7.QtHelpInterface.HelpSearchWidget import HelpSearchWidget
from eric7.QtHelpInterface.HelpTocWidget import HelpTocWidget
from eric7.SystemUtilities import QtUtilities

from .HelpBookmarksWidget import HelpBookmarksWidget
from .OpenPagesWidget import OpenPagesWidget


class HelpViewerWidget(QWidget):
    """
    Class implementing an embedded viewer for QtHelp and local HTML files.
    """

    MaxHistoryItems = 20  # max. number of history items to be shown

    EmpytDocument_Light = (
        """<!DOCTYPE html>\n"""
        """<html lang="EN">\n"""
        """<head>\n"""
        """<style type="text/css">\n"""
        """html {background-color: #ffffff;}\n"""
        """body {background-color: #ffffff;\n"""
        """      color: #000000;\n"""
        """      margin: 10px 10px 10px 10px;\n"""
        """}\n"""
        """</style>\n"""
        """</head>\n"""
        """<body>\n"""
        """</body>\n"""
        """</html>"""
    )
    EmpytDocument_Dark = (
        """<!DOCTYPE html>\n"""
        """<html lang="EN">\n"""
        """<head>\n"""
        """<style type="text/css">\n"""
        """html {background-color: #262626;}\n"""
        """body {background-color: #262626;\n"""
        """      color: #ffffff;\n"""
        """      margin: 10px 10px 10px 10px;\n"""
        """}\n"""
        """</style>\n"""
        """</head>\n"""
        """<body>\n"""
        """</body>\n"""
        """</html>"""
    )

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setObjectName("HelpViewerWidget")

        self.__ui = parent

        self.__initHelpEngine()

        self.__layout = QVBoxLayout()
        self.__layout.setObjectName("MainLayout")
        self.__layout.setContentsMargins(0, 3, 0, 0)

        ###################################################################
        ## Help Topic Selector
        ###################################################################

        self.__selectorLayout = QHBoxLayout()

        self.__helpSelector = QComboBox(self)
        self.__helpSelector.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.__selectorLayout.addWidget(self.__helpSelector)
        self.__populateHelpSelector()
        self.__helpSelector.activated.connect(self.__helpTopicSelected)

        self.__openButton = QToolButton(self)
        self.__openButton.setIcon(EricPixmapCache.getIcon("open"))
        self.__openButton.setToolTip(self.tr("Open a local file"))
        self.__openButton.clicked.connect(self.__openFile)
        self.__selectorLayout.addWidget(self.__openButton)

        self.__actionsButton = EricToolButton(self)
        self.__actionsButton.setIcon(EricPixmapCache.getIcon("actionsToolButton"))
        self.__actionsButton.setToolTip(self.tr("Select action from menu"))
        self.__actionsButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.__actionsButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.__actionsButton.setShowMenuInside(True)
        self.__selectorLayout.addWidget(self.__actionsButton)

        self.__layout.addLayout(self.__selectorLayout)

        ###################################################################
        ## Navigation Buttons
        ###################################################################

        self.__navButtonsLayout = QHBoxLayout()

        self.__navButtonsLayout.addStretch()

        self.__backwardButton = QToolButton(self)
        self.__backwardButton.setIcon(EricPixmapCache.getIcon("back"))
        self.__backwardButton.setToolTip(self.tr("Move one page backward"))
        self.__backwardButton.clicked.connect(self.__backward)

        self.__forwardButton = QToolButton(self)
        self.__forwardButton.setIcon(EricPixmapCache.getIcon("forward"))
        self.__forwardButton.setToolTip(self.tr("Move one page forward"))
        self.__forwardButton.clicked.connect(self.__forward)

        self.__backForButtonLayout = QHBoxLayout()
        self.__backForButtonLayout.setContentsMargins(0, 0, 0, 0)
        self.__backForButtonLayout.setSpacing(0)
        self.__backForButtonLayout.addWidget(self.__backwardButton)
        self.__backForButtonLayout.addWidget(self.__forwardButton)
        self.__navButtonsLayout.addLayout(self.__backForButtonLayout)

        self.__reloadButton = QToolButton(self)
        self.__reloadButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.__reloadButton.setToolTip(self.tr("Reload the current page"))
        self.__reloadButton.clicked.connect(self.__reload)
        self.__navButtonsLayout.addWidget(self.__reloadButton)

        self.__buttonLine1 = QFrame(self)
        self.__buttonLine1.setFrameShape(QFrame.Shape.VLine)
        self.__buttonLine1.setFrameShadow(QFrame.Shadow.Sunken)
        self.__navButtonsLayout.addWidget(self.__buttonLine1)

        self.__zoomInButton = QToolButton(self)
        self.__zoomInButton.setIcon(EricPixmapCache.getIcon("zoomIn"))
        self.__zoomInButton.setToolTip(self.tr("Zoom in on the current page"))
        self.__zoomInButton.clicked.connect(self.__zoomIn)
        self.__navButtonsLayout.addWidget(self.__zoomInButton)

        self.__zoomOutButton = QToolButton(self)
        self.__zoomOutButton.setIcon(EricPixmapCache.getIcon("zoomOut"))
        self.__zoomOutButton.setToolTip(self.tr("Zoom out on the current page"))
        self.__zoomOutButton.clicked.connect(self.__zoomOut)
        self.__navButtonsLayout.addWidget(self.__zoomOutButton)

        self.__zoomResetButton = QToolButton(self)
        self.__zoomResetButton.setIcon(EricPixmapCache.getIcon("zoomReset"))
        self.__zoomResetButton.setToolTip(
            self.tr("Reset the zoom level of the current page")
        )
        self.__zoomResetButton.clicked.connect(self.__zoomReset)
        self.__navButtonsLayout.addWidget(self.__zoomResetButton)

        self.__buttonLine2 = QFrame(self)
        self.__buttonLine2.setFrameShape(QFrame.Shape.VLine)
        self.__buttonLine2.setFrameShadow(QFrame.Shadow.Sunken)
        self.__navButtonsLayout.addWidget(self.__buttonLine2)

        self.__addPageButton = QToolButton(self)
        self.__addPageButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.__addPageButton.setToolTip(self.tr("Add a new empty page"))
        self.__addPageButton.clicked.connect(self.__addNewPage)
        self.__navButtonsLayout.addWidget(self.__addPageButton)

        self.__closePageButton = QToolButton(self)
        self.__closePageButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.__closePageButton.setToolTip(self.tr("Close the current page"))
        self.__closePageButton.clicked.connect(self.closeCurrentPage)
        self.__navButtonsLayout.addWidget(self.__closePageButton)

        self.__buttonLine3 = QFrame(self)
        self.__buttonLine3.setFrameShape(QFrame.Shape.VLine)
        self.__buttonLine3.setFrameShadow(QFrame.Shadow.Sunken)
        self.__navButtonsLayout.addWidget(self.__buttonLine3)

        self.__searchButton = QToolButton(self)
        self.__searchButton.setIcon(EricPixmapCache.getIcon("find"))
        self.__searchButton.setToolTip(self.tr("Show or hide the search pane"))
        self.__searchButton.setCheckable(True)
        self.__searchButton.setChecked(False)
        self.__searchButton.clicked.connect(self.showHideSearch)
        self.__navButtonsLayout.addWidget(self.__searchButton)

        self.__navButtonsLayout.addStretch()

        self.__layout.addLayout(self.__navButtonsLayout)

        self.__backMenu = QMenu(self)
        self.__backMenu.triggered.connect(self.__navigationMenuActionTriggered)
        self.__backwardButton.setMenu(self.__backMenu)
        self.__backMenu.aboutToShow.connect(self.__showBackMenu)

        self.__forwardMenu = QMenu(self)
        self.__forwardMenu.triggered.connect(self.__navigationMenuActionTriggered)
        self.__forwardButton.setMenu(self.__forwardMenu)
        self.__forwardMenu.aboutToShow.connect(self.__showForwardMenu)

        ###################################################################
        ## Center widget with help pages, search widget and navigation
        ## widgets
        ###################################################################

        self.__centerSplitter = QSplitter(Qt.Orientation.Vertical, self)
        self.__centerSplitter.setChildrenCollapsible(False)
        self.__layout.addWidget(self.__centerSplitter)

        self.__helpCenterWidget = QWidget(self)
        self.__helpCenterLayout = QVBoxLayout()
        self.__helpCenterLayout.setContentsMargins(0, 0, 0, 0)
        self.__helpCenterWidget.setLayout(self.__helpCenterLayout)

        ###################################################################

        self.__helpStack = QStackedWidget(self)
        self.__helpStack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.__helpCenterLayout.addWidget(self.__helpStack)

        ###################################################################

        self.__searchWidget = EricTextEditSearchWidget(
            self, widthForHeight=False, enableClose=True
        )
        self.__helpCenterLayout.addWidget(self.__searchWidget)
        self.__searchWidget.closePressed.connect(self.__searchWidgetClosed)
        self.__searchWidget.hide()

        self.__centerSplitter.addWidget(self.__helpCenterWidget)

        ###################################################################

        self.__helpNavigationStack = QStackedWidget(self)
        self.__helpNavigationStack.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.__helpNavigationStack.setMinimumHeight(100)
        self.__centerSplitter.addWidget(self.__helpNavigationStack)
        self.__populateNavigationStack()

        ###################################################################
        ## Bottom buttons
        ###################################################################

        self.__buttonLayout = QHBoxLayout()

        self.__buttonGroup = QButtonGroup(self)
        self.__buttonGroup.setExclusive(True)
        self.__buttonGroup.buttonClicked.connect(self.__selectNavigationWidget)

        self.__buttonLayout.addStretch()

        self.__openPagesButton = self.__addNavigationButton(
            "fileMisc", self.tr("Show list of open pages")
        )
        self.__helpTocButton = self.__addNavigationButton(
            "tableOfContents", self.tr("Show the table of contents")
        )
        self.__helpIndexButton = self.__addNavigationButton(
            "helpIndex", self.tr("Show the help document index")
        )
        self.__helpSearchButton = self.__addNavigationButton(
            "documentFind", self.tr("Show the help search window")
        )
        self.__bookmarksButton = self.__addNavigationButton(
            "bookmark22", self.tr("Show list of bookmarks")
        )

        self.__buttonLayout.addStretch()

        self.__helpFilterWidget = self.__initFilterWidget()
        self.__buttonLayout.addWidget(self.__helpFilterWidget)

        self.__layout.addLayout(self.__buttonLayout)

        self.__indexingProgressWidget = self.__initIndexingProgress()
        self.__layout.addWidget(self.__indexingProgressWidget)
        self.__indexingProgressWidget.hide()

        ###################################################################

        self.setLayout(self.__layout)

        self.__openPagesButton.setChecked(True)

        self.__ui.preferencesChanged.connect(self.__populateHelpSelector)

        self.__initActionsMenu()

        self.__useQTextBrowser = not WEBENGINE_AVAILABLE or Preferences.getHelp(
            "ForceQTextBrowser"
        )
        if not self.__useQTextBrowser:
            self.__initQWebEngine()
            self.__ui.preferencesChanged.connect(self.__initQWebEngineSettings)

        self.addPage()
        self.__checkActionButtons()

        self.__centerSplitter.setSizes([900, 150])

        self.__helpInstaller = None

        if Preferences.getHelp("QtHelpSearchNewOnStart"):
            QTimer.singleShot(50, self.__lookForNewDocumentation)

    def __addNavigationButton(self, iconName, toolTip):
        """
        Private method to create and add a navigation button.

        @param iconName name of the icon
        @type str
        @param toolTip tooltip to be shown
        @type str
        @return reference to the created button
        @rtype QToolButton
        """
        button = QToolButton(self)
        button.setIcon(EricPixmapCache.getIcon(iconName))
        button.setToolTip(toolTip)
        button.setCheckable(True)
        self.__buttonGroup.addButton(button)
        self.__buttonLayout.addWidget(button)

        return button

    def __populateNavigationStack(self):
        """
        Private method to populate the stack of navigation widgets.
        """
        # Open Pages
        self.__openPagesList = OpenPagesWidget(self.__helpStack, self)
        self.__openPagesList.currentPageChanged.connect(self.__currentPageChanged)
        self.__helpNavigationStack.addWidget(self.__openPagesList)

        # QtHelp TOC widget
        self.__helpTocWidget = HelpTocWidget(self.__helpEngine, internal=True)
        self.__helpTocWidget.escapePressed.connect(self.__activateCurrentPage)
        self.__helpTocWidget.openUrl.connect(self.openUrl)
        self.__helpTocWidget.newTab.connect(self.openUrlNewPage)
        self.__helpTocWidget.newBackgroundTab.connect(self.openUrlNewBackgroundPage)
        self.__helpNavigationStack.addWidget(self.__helpTocWidget)

        # QtHelp Index widget
        self.__helpIndexWidget = HelpIndexWidget(self.__helpEngine, internal=True)
        self.__helpIndexWidget.escapePressed.connect(self.__activateCurrentPage)
        self.__helpIndexWidget.openUrl.connect(self.openUrl)
        self.__helpIndexWidget.newTab.connect(self.openUrlNewPage)
        self.__helpIndexWidget.newBackgroundTab.connect(self.openUrlNewBackgroundPage)
        self.__helpNavigationStack.addWidget(self.__helpIndexWidget)

        # QtHelp Search widget
        self.__indexing = False
        self.__indexingProgress = None
        self.__helpSearchEngine = self.__helpEngine.searchEngine()
        self.__helpSearchEngine.indexingStarted.connect(self.__indexingStarted)
        self.__helpSearchEngine.indexingFinished.connect(self.__indexingFinished)

        self.__helpSearchWidget = HelpSearchWidget(
            self.__helpSearchEngine, internal=True
        )
        self.__helpSearchWidget.escapePressed.connect(self.__activateCurrentPage)
        self.__helpSearchWidget.openUrl.connect(self.openUrl)
        self.__helpSearchWidget.newTab.connect(self.openUrlNewPage)
        self.__helpSearchWidget.newBackgroundTab.connect(self.openUrlNewBackgroundPage)
        self.__helpNavigationStack.addWidget(self.__helpSearchWidget)

        # Bookmarks widget
        self.__bookmarksList = HelpBookmarksWidget(self)
        self.__bookmarksList.escapePressed.connect(self.__activateCurrentPage)
        self.__bookmarksList.openUrl.connect(self.openUrl)
        self.__bookmarksList.newTab.connect(self.openUrlNewPage)
        self.__bookmarksList.newBackgroundTab.connect(self.openUrlNewBackgroundPage)
        self.__helpNavigationStack.addWidget(self.__bookmarksList)

    @pyqtSlot(QAbstractButton)
    def __selectNavigationWidget(self, button):
        """
        Private slot to select the navigation widget.

        @param button reference to the clicked button
        @type QAbstractButton
        """
        if button == self.__openPagesButton:
            self.__helpNavigationStack.setCurrentWidget(self.__openPagesList)
        elif button == self.__helpTocButton:
            self.__helpNavigationStack.setCurrentWidget(self.__helpTocWidget)
        elif button == self.__helpIndexButton:
            self.__helpNavigationStack.setCurrentWidget(self.__helpIndexWidget)
        elif button == self.__helpSearchButton:
            self.__helpNavigationStack.setCurrentWidget(self.__helpSearchWidget)
        elif button == self.__bookmarksButton:
            self.__helpNavigationStack.setCurrentWidget(self.__bookmarksList)

    def __populateHelpSelector(self):
        """
        Private method to populate the help selection combo box.
        """
        self.__helpSelector.clear()

        self.__helpSelector.addItem("", "")

        for key, topic in [
            ("EricDocDir", self.tr("eric API Documentation")),
            ("PythonDocDir", self.tr("Python 3 Documentation")),
            ("Qt5DocDir", self.tr("Qt5 Documentation")),
            ("Qt6DocDir", self.tr("Qt6 Documentation")),
            ("PyQt5DocDir", self.tr("PyQt5 Documentation")),
            ("PyQt6DocDir", self.tr("PyQt6 Documentation")),
            ("PySide2DocDir", self.tr("PySide2 Documentation")),
            ("PySide6DocDir", self.tr("PySide6 Documentation")),
        ]:
            urlStr = Preferences.getHelp(key)
            if urlStr:
                self.__helpSelector.addItem(topic, urlStr)

    @pyqtSlot()
    def __helpTopicSelected(self):
        """
        Private slot handling the selection of a new help topic.
        """
        urlStr = self.__helpSelector.currentData()
        if urlStr:
            url = QUrl(urlStr)
            self.openUrl(url)
        else:
            self.openUrl(QUrl("about:blank"))

    def activate(self, searchWord=None, url=None):
        """
        Public method to activate the widget and search for a given word.

        @param searchWord word to search for (defaults to None)
        @type str (optional)
        @param url URL to show in a new page
        @type QUrl
        """
        if url is not None:
            cv = self.currentViewer()
            if cv and cv.isEmptyPage():
                self.openUrl(url)
            else:
                self.openUrlNewPage(url)
        else:
            cv = self.currentViewer()
            if cv:
                cv.setFocus(Qt.FocusReason.OtherFocusReason)

            if searchWord:
                self.searchQtHelp(searchWord)

    def shutdown(self):
        """
        Public method to perform shut down actions.
        """
        self.__helpSearchEngine.cancelIndexing()
        self.__helpSearchEngine.cancelSearching()

        self.__helpInstaller and self.__helpInstaller.stop()

    @pyqtSlot()
    def __openFile(self):
        """
        Private slot to open a local help file (*.html).
        """
        htmlFile = EricFileDialog.getOpenFileName(
            self,
            self.tr("Open HTML File"),
            "",
            self.tr("HTML Files (*.htm *.html);;All Files (*)"),
        )
        if htmlFile:
            self.currentViewer().setLink(QUrl.fromLocalFile(htmlFile))

    @pyqtSlot()
    def __addNewPage(self):
        """
        Private slot to add a new empty page.
        """
        urlStr = self.__helpSelector.currentData()
        url = QUrl(urlStr) if bool(urlStr) else None
        self.addPage(url=url)

    def addPage(self, url=None, background=False):
        """
        Public method to add a new help page with the given URL.

        @param url requested URL (defaults to QUrl("about:blank"))
        @type QUrl (optional)
        @param background flag indicating to open the page in the background
            (defaults to False)
        @type bool (optional)
        @return reference to the created page
        @rtype HelpViewerImpl
        """
        if url is None:
            url = QUrl("about:blank")

        viewer, viewerType = self.__newViewer()
        viewer.setLink(url)

        cv = self.currentViewer()
        if background and bool(cv):
            index = self.__helpStack.indexOf(cv) + 1
            self.__helpStack.insertWidget(index, viewer)
            self.__openPagesList.insertPage(index, viewer, background=background)
            cv.setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            self.__helpStack.addWidget(viewer)
            self.__openPagesList.addPage(viewer, background=background)
            viewer.setFocus(Qt.FocusReason.OtherFocusReason)
            self.__searchWidget.attachTextEdit(viewer, editType=viewerType)

        return viewer

    @pyqtSlot(QUrl)
    def openUrl(self, url):
        """
        Public slot to load a URL in the current page.

        @param url URL to be opened
        @type QUrl
        """
        cv = self.currentViewer()
        if cv:
            cv.setLink(url)
            cv.setFocus(Qt.FocusReason.OtherFocusReason)

    @pyqtSlot(QUrl)
    def openUrlNewPage(self, url):
        """
        Public slot to load a URL in a new page.

        @param url URL to be opened
        @type QUrl
        """
        self.addPage(url=url)

    @pyqtSlot(QUrl)
    def openUrlNewBackgroundPage(self, url):
        """
        Public slot to load a URL in a new background page.

        @param url URL to be opened
        @type QUrl
        """
        self.addPage(url=url, background=True)

    @pyqtSlot()
    def closeCurrentPage(self):
        """
        Public slot to close the current page.
        """
        self.__openPagesList.closeCurrentPage()

    @pyqtSlot()
    def closeOtherPages(self):
        """
        Public slot to close all other pages.
        """
        self.__openPagesList.closeOtherPages()

    @pyqtSlot()
    def closeAllPages(self):
        """
        Public slot to close all pages.
        """
        self.__openPagesList.closeAllPages()

    @pyqtSlot()
    def __activateCurrentPage(self):
        """
        Private slot to activate the current page.
        """
        cv = self.currentViewer()
        if cv:
            cv.setFocus()

    def __newViewer(self):
        """
        Private method to create a new help viewer.

        @return tuple containing the reference to the created help viewer
            object and its type
        @rtype tuple of (HelpViewerImpl, EricTextEditType)
        """
        if self.__useQTextBrowser:
            from .HelpViewerImplQTB import HelpViewerImplQTB  # __IGNORE_WARNING_I101__

            viewer = HelpViewerImplQTB(self.__helpEngine, self)
        else:
            from .HelpViewerImplQWE import HelpViewerImplQWE  # __IGNORE_WARNING_I101__

            viewer = HelpViewerImplQWE(self.__helpEngine, self)

        viewer.zoomChanged.connect(self.__checkActionButtons)

        return viewer, viewer.viewerType()

    def currentViewer(self):
        """
        Public method to get the active viewer.

        @return reference to the active help viewer
        @rtype HelpViewerImpl
        """
        return self.__helpStack.currentWidget()

    def bookmarkPage(self, title, url):
        """
        Public method to bookmark a page with the given data.

        @param title title of the page
        @type str
        @param url URL of the page
        @type QUrl
        """
        self.__bookmarksList.addBookmark(title, url)

    #######################################################################
    ## QtHelp related code below
    #######################################################################

    def __initHelpEngine(self):
        """
        Private method to initialize the QtHelp related stuff.
        """
        self.__helpEngine = QHelpEngine(self.__getQtHelpCollectionFileName(), self)
        self.__helpEngine.setReadOnly(False)
        self.__helpEngine.setUsesFilterEngine(True)

        self.__helpEngine.warning.connect(self.__warning)

        self.__helpEngine.setupData()
        self.__removeOldDocumentation()

    def __getQtHelpCollectionFileName(self):
        """
        Private method to determine the name of the QtHelp collection file.

        @return path of the QtHelp collection file
        @rtype str
        """
        qthelpDir = os.path.join(EricUtilities.getConfigDir(), "qthelp")
        if not os.path.exists(qthelpDir):
            os.makedirs(qthelpDir, exist_ok=True)
        return os.path.join(qthelpDir, "eric7help.qhc")

    @pyqtSlot(str)
    def __warning(self, msg):
        """
        Private slot handling warnings of the help engine.

        @param msg message sent by the help  engine
        @type str
        """
        EricMessageBox.warning(self, self.tr("Help Engine"), msg)

    @pyqtSlot()
    def __removeOldDocumentation(self):
        """
        Private slot to remove non-existing documentation from the help engine.
        """
        for namespace in self.__helpEngine.registeredDocumentations():
            docFile = self.__helpEngine.documentationFileName(namespace)
            if not os.path.exists(docFile):
                self.__helpEngine.unregisterDocumentation(namespace)

    @pyqtSlot()
    def __lookForNewDocumentation(self):
        """
        Private slot to look for new documentation to be loaded into the
        help database.
        """
        from eric7.QtHelpInterface.HelpDocsInstaller import HelpDocsInstaller

        self.__helpInstaller = HelpDocsInstaller(self.__helpEngine.collectionFile())
        self.__helpInstaller.errorMessage.connect(self.__showInstallationError)
        self.__helpInstaller.docsInstalled.connect(self.__docsInstalled)

        self.__ui.statusBar().showMessage(self.tr("Looking for Documentation..."))
        self.__helpInstaller.installDocs()

    @pyqtSlot(str)
    def __showInstallationError(self, message):
        """
        Private slot to show installation errors.

        @param message message to be shown
        @type str
        """
        EricMessageBox.warning(self, self.tr("eric Help Viewer"), message)

    @pyqtSlot(bool)
    def __docsInstalled(self, _installed):
        """
        Private slot handling the end of documentation installation.

        @param _installed flag indicating that documents were installed (unused)
        @type bool
        """
        self.__ui.statusBar().clearMessage()
        self.__helpEngine.setupData()

    #######################################################################
    ## Actions Menu related methods
    #######################################################################

    def __initActionsMenu(self):
        """
        Private method to initialize the actions menu.
        """
        self.__actionsMenu = QMenu()
        self.__actionsMenu.setToolTipsVisible(True)

        self.__actionsMenu.addAction(
            self.tr("Manage QtHelp Documents"), self.__manageQtHelpDocuments
        )
        self.__actionsMenu.addAction(
            self.tr("Reindex Documentation"),
            self.__helpSearchEngine.reindexDocumentation,
        )
        self.__actionsMenu.addSeparator()
        self.__actionsMenu.addAction(
            self.tr("Configure Help Documentation"), self.__configureHelpDocumentation
        )

        self.__actionsButton.setMenu(self.__actionsMenu)

    @pyqtSlot()
    def __manageQtHelpDocuments(self):
        """
        Private slot to manage the QtHelp documentation database.
        """
        from eric7.QtHelpInterface.QtHelpDocumentationConfigurationDialog import (
            QtHelpDocumentationConfigurationDialog,
        )

        dlg = QtHelpDocumentationConfigurationDialog(self.__helpEngine, parent=self)
        dlg.exec()

    @pyqtSlot()
    def __configureHelpDocumentation(self):
        """
        Private slot to open the Help Documentation configuration page.
        """
        self.__ui.showPreferences("helpDocumentationPage")

    #######################################################################
    ## Navigation related methods below
    #######################################################################

    @pyqtSlot()
    def __backward(self):
        """
        Private slot to move one page backward.
        """
        cv = self.currentViewer()
        if cv:
            cv.backward()

    @pyqtSlot()
    def __forward(self):
        """
        Private slot to move one page foreward.
        """
        cv = self.currentViewer()
        if cv:
            cv.forward()

    @pyqtSlot()
    def __reload(self):
        """
        Private slot to reload the current page.
        """
        cv = self.currentViewer()
        if cv:
            cv.reload()

    def __showBackMenu(self):
        """
        Private slot showing the backward navigation menu.
        """
        cv = self.currentViewer()
        if cv:
            self.__backMenu.clear()
            backwardHistoryCount = min(
                cv.backwardHistoryCount(), HelpViewerWidget.MaxHistoryItems
            )

            for index in range(1, backwardHistoryCount + 1):
                act = QAction(self)
                act.setData(-index)
                act.setText(cv.historyTitle(-index))
                self.__backMenu.addAction(act)

            self.__backMenu.addSeparator()
            self.__backMenu.addAction(self.tr("Clear History"), self.__clearHistory)

    def __showForwardMenu(self):
        """
        Private slot showing the forward navigation menu.
        """
        cv = self.currentViewer()
        if cv:
            self.__forwardMenu.clear()
            forwardHistoryCount = min(
                cv.forwardHistoryCount(), HelpViewerWidget.MaxHistoryItems
            )

            for index in range(1, forwardHistoryCount + 1):
                act = QAction(self)
                act.setData(index)
                act.setText(cv.historyTitle(index))
                self.__forwardMenu.addAction(act)

            self.__forwardMenu.addSeparator()
            self.__forwardMenu.addAction(self.tr("Clear History"), self.__clearHistory)

    def __navigationMenuActionTriggered(self, act):
        """
        Private slot to go to the selected page.

        @param act reference to the action selected in the navigation menu
        @type QAction
        """
        cv = self.currentViewer()
        if cv:
            index = act.data()
            if index is not None:
                cv.gotoHistory(index)

    def __clearHistory(self):
        """
        Private slot to clear the history of the current viewer.
        """
        cv = self.currentViewer()
        if cv:
            cv.clearHistory()
            self.__checkActionButtons()

    #######################################################################
    ## Page navigation related methods below
    #######################################################################

    @pyqtSlot()
    def __checkActionButtons(self):
        """
        Private slot to set the enabled state of the action buttons.
        """
        cv = self.currentViewer()
        if cv:
            self.__backwardButton.setEnabled(cv.isBackwardAvailable())
            self.__forwardButton.setEnabled(cv.isForwardAvailable())
            self.__zoomInButton.setEnabled(cv.isScaleUpAvailable())
            self.__zoomOutButton.setEnabled(cv.isScaleDownAvailable())
        else:
            self.__backwardButton.setEnabled(False)
            self.__forwardButton.setEnabled(False)
            self.__zoomInButton.setEnabled(False)
            self.__zoomOutButton.setEnabled(False)

    @pyqtSlot()
    def __currentPageChanged(self):
        """
        Private slot handling the selection of another page.
        """
        self.__checkActionButtons()
        cv = self.currentViewer()
        if cv:
            self.__searchWidget.attachTextEdit(cv, editType=cv.viewerType())
            self.__searchWidget.deactivate()
            cv.setFocus(Qt.FocusReason.OtherFocusReason)

    #######################################################################
    ## Zoom related methods below
    #######################################################################

    @pyqtSlot()
    def __zoomIn(self):
        """
        Private slot to zoom in.
        """
        cv = self.currentViewer()
        if cv:
            cv.scaleUp()

    @pyqtSlot()
    def __zoomOut(self):
        """
        Private slot to zoom out.
        """
        cv = self.currentViewer()
        if cv:
            cv.scaleDown()

    @pyqtSlot()
    def __zoomReset(self):
        """
        Private slot to reset the zoom level.
        """
        cv = self.currentViewer()
        if cv:
            cv.resetScale()

    #######################################################################
    ## QtHelp Search related methods below
    #######################################################################

    def __initIndexingProgress(self):
        """
        Private method to initialize the help documents indexing progress
        widget.

        @return reference to the generated widget
        @rtype QWidget
        """
        progressWidget = QWidget(self)
        layout = QHBoxLayout(progressWidget)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(self.tr("Updating search index"))
        layout.addWidget(label)

        progressBar = QProgressBar()
        progressBar.setRange(0, 0)
        progressBar.setTextVisible(False)
        progressBar.setFixedHeight(16)
        layout.addWidget(progressBar)

        return progressWidget

    @pyqtSlot()
    def __indexingStarted(self):
        """
        Private slot handling the start of the indexing process.
        """
        self.__indexing = True
        self.__indexingProgressWidget.show()

    @pyqtSlot()
    def __indexingFinished(self):
        """
        Private slot handling the end of the indexing process.
        """
        self.__indexingProgressWidget.hide()
        self.__indexing = False

    @pyqtSlot(str)
    def searchQtHelp(self, searchExpression):
        """
        Public slot to search for a given search expression.

        @param searchExpression expression to search for
        @type str
        """
        if searchExpression:
            if self.__indexing:
                # Try again a second later
                QTimer.singleShot(1000, lambda: self.searchQtHelp(searchExpression))
            else:
                self.__helpSearchButton.setChecked(True)
                self.__helpSearchEngine.search(searchExpression)

    #######################################################################
    ## QtHelp filter related methods below
    #######################################################################

    def __initFilterWidget(self):
        """
        Private method to initialize the filter selection widget.

        @return reference to the generated widget
        @rtype QWidget
        """
        filterWidget = QWidget()
        layout = QHBoxLayout(filterWidget)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(self.tr("Filtered by: "))
        layout.addWidget(label)

        self.__helpFilterCombo = QComboBox()
        comboWidth = QFontMetrics(QFont()).horizontalAdvance("ComboBoxWithEnoughWidth")
        self.__helpFilterCombo.setMinimumWidth(comboWidth)
        layout.addWidget(self.__helpFilterCombo)

        self.__helpEngine.setupFinished.connect(
            self.__setupFilterCombo, Qt.ConnectionType.QueuedConnection
        )
        self.__helpFilterCombo.currentIndexChanged.connect(
            self.__filterQtHelpDocumentation
        )
        self.__helpEngine.filterEngine().filterActivated.connect(
            self.__currentFilterChanged
        )

        self.__setupFilterCombo()

        return filterWidget

    @pyqtSlot()
    def __setupFilterCombo(self):
        """
        Private slot to setup the filter combo box.
        """
        activeFilter = self.__helpFilterCombo.currentText()
        if not activeFilter:
            activeFilter = self.__helpEngine.filterEngine().activeFilter()
        if not activeFilter:
            activeFilter = self.tr("Unfiltered")
        allFilters = self.__helpEngine.filterEngine().filters()

        blocked = self.__helpFilterCombo.blockSignals(True)
        self.__helpFilterCombo.clear()
        self.__helpFilterCombo.addItem(self.tr("Unfiltered"))
        if allFilters:
            self.__helpFilterCombo.insertSeparator(1)
            for helpFilter in sorted(allFilters):
                self.__helpFilterCombo.addItem(helpFilter, helpFilter)
        self.__helpFilterCombo.blockSignals(blocked)

        self.__helpFilterCombo.setCurrentText(activeFilter)

    @pyqtSlot(int)
    def __filterQtHelpDocumentation(self, index):
        """
        Private slot to filter the QtHelp documentation.

        @param index index of the selected QtHelp documentation filter
        @type int
        """
        if self.__helpEngine:
            helpFilter = self.__helpFilterCombo.itemData(index)
            self.__helpEngine.filterEngine().setActiveFilter(helpFilter)

    @pyqtSlot(str)
    def __currentFilterChanged(self, filter_):
        """
        Private slot handling a change of the active QtHelp filter.

        @param filter_ filter name
        @type str
        """
        index = self.__helpFilterCombo.findData(filter_)
        if index < 0:
            index = 0
        self.__helpFilterCombo.setCurrentIndex(index)

    #######################################################################
    ## QWebEngine related code below
    #######################################################################

    def __initQWebEngine(self):
        """
        Private method to initialize global QWebEngine related objects.
        """
        from eric7.QtHelpInterface.QtHelpSchemeHandler import QtHelpSchemeHandler

        self.__webProfile = QWebEngineProfile("eric7")
        self.__webProfile.setHttpCacheType(
            QWebEngineProfile.HttpCacheType.MemoryHttpCache
        )
        self.__webProfile.setHttpCacheMaximumSize(0)

        self.__initQWebEngineSettings()

        self.__qtHelpSchemeHandler = QtHelpSchemeHandler(self.__helpEngine)
        self.__webProfile.installUrlSchemeHandler(
            QByteArray(b"qthelp"), self.__qtHelpSchemeHandler
        )

    def webProfile(self):
        """
        Public method to get a reference to the global web profile object.

        @return reference to the global web profile object
        @rtype QWebEngineProfile
        """
        return self.__webProfile

    def webSettings(self):
        """
        Public method to get the web settings of the current profile.

        @return web settings of the current profile
        @rtype QWebEngineSettings
        """
        return self.webProfile().settings()

    def __initQWebEngineSettings(self):
        """
        Private method to set the global web settings.
        """
        settings = self.webSettings()

        settings.setFontFamily(
            QWebEngineSettings.FontFamily.StandardFont,
            Preferences.getWebBrowser("StandardFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.FixedFont,
            Preferences.getWebBrowser("FixedFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.SerifFont,
            Preferences.getWebBrowser("SerifFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.SansSerifFont,
            Preferences.getWebBrowser("SansSerifFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.CursiveFont,
            Preferences.getWebBrowser("CursiveFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.FantasyFont,
            Preferences.getWebBrowser("FantasyFontFamily"),
        )

        settings.setFontSize(
            QWebEngineSettings.FontSize.DefaultFontSize,
            Preferences.getWebBrowser("DefaultFontSize"),
        )
        settings.setFontSize(
            QWebEngineSettings.FontSize.DefaultFixedFontSize,
            Preferences.getWebBrowser("DefaultFixedFontSize"),
        )
        settings.setFontSize(
            QWebEngineSettings.FontSize.MinimumFontSize,
            Preferences.getWebBrowser("MinimumFontSize"),
        )
        settings.setFontSize(
            QWebEngineSettings.FontSize.MinimumLogicalFontSize,
            Preferences.getWebBrowser("MinimumLogicalFontSize"),
        )

        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages,
            Preferences.getWebBrowser("AutoLoadImages"),
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        # JavaScript is needed for the web browser functionality
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            Preferences.getWebBrowser("JavaScriptCanOpenWindows"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard,
            Preferences.getWebBrowser("JavaScriptCanAccessClipboard"),
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)

        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled, False
        )
        settings.setDefaultTextEncoding(
            Preferences.getWebBrowser("DefaultTextEncoding")
        )

        settings.setAttribute(
            QWebEngineSettings.WebAttribute.SpatialNavigationEnabled,
            Preferences.getWebBrowser("SpatialNavigationEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LinksIncludedInFocusChain,
            Preferences.getWebBrowser("LinksIncludedInFocusChain"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            Preferences.getWebBrowser("LocalContentCanAccessRemoteUrls"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            Preferences.getWebBrowser("LocalContentCanAccessFileUrls"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.XSSAuditingEnabled,
            Preferences.getWebBrowser("XSSAuditingEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled,
            Preferences.getWebBrowser("ScrollAnimatorEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ErrorPageEnabled,
            Preferences.getWebBrowser("ErrorPageEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, False
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScreenCaptureEnabled,
            Preferences.getWebBrowser("ScreenCaptureEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebGLEnabled,
            Preferences.getWebBrowser("WebGLEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled,
            Preferences.getWebBrowser("FocusOnNavigationEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PrintElementBackgrounds,
            Preferences.getWebBrowser("PrintElementBackgrounds"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent,
            Preferences.getWebBrowser("AllowRunningInsecureContent"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins,
            Preferences.getWebBrowser("AllowGeolocationOnInsecureOrigins"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript,
            Preferences.getWebBrowser("AllowWindowActivationFromJavaScript"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ShowScrollBars,
            Preferences.getWebBrowser("ShowScrollBars"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,
            Preferences.getWebBrowser("PlaybackRequiresUserGesture"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanPaste,
            Preferences.getWebBrowser("JavaScriptCanPaste"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly, False
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, False)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PdfViewerEnabled,
            Preferences.getWebBrowser("PdfViewerEnabled"),
        )

        if QtUtilities.qVersionTuple() >= (6, 6, 0):
            # Qt 6.6+
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.ReadingFromCanvasEnabled, False
            )

        if QtUtilities.qVersionTuple() >= (6, 7, 0):
            # Qt 6.7+
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.ForceDarkMode,
                Preferences.getWebBrowser("ForceDarkMode"),
            )

    #######################################################################
    ## Search widget related methods below
    #######################################################################

    @pyqtSlot()
    def __searchWidgetClosed(self):
        """
        Private slot to handle the closing of the search widget.
        """
        self.__searchButton.setChecked(False)

    @pyqtSlot(bool)
    def showHideSearch(self, visible):
        """
        Public slot to show or hide the search widget.

        @param visible flag indicating to show or hide the search widget
        @type bool
        """
        self.__searchButton.setChecked(visible)

        self.__searchWidget.setVisible(visible)
        if visible:
            self.__searchWidget.activate()
        else:
            self.__searchWidget.deactivate()

    @pyqtSlot()
    def searchPrev(self):
        """
        Public slot to find the previous occurrence of the current search term.
        """
        self.showHideSearch(True)
        self.__searchWidget.findPrev()

    @pyqtSlot()
    def searchNext(self):
        """
        Public slot to find the next occurrence of the current search term.
        """
        self.showHideSearch(True)
        self.__searchWidget.findNext()

    #######################################################################
    ## Utility methods below
    #######################################################################

    def openPagesCount(self):
        """
        Public method to get the count of open pages.

        @return count of open pages
        @rtype int
        """
        return self.__helpStack.count()

    @classmethod
    def emptyDocument(cls):
        """
        Class method to get the HTML code for an empty page.

        @return HTML code for an empty page.
        @rtype str
        """
        if ericApp().usesDarkPalette():
            return cls.EmpytDocument_Dark
        else:
            return cls.EmpytDocument_Light
