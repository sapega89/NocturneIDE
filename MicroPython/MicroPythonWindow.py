# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the standalone MicroPython window.
"""

import contextlib

from PyQt6.QtCore import QSize, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkProxyFactory
from PyQt6.QtWidgets import QDialog, QSplitter, QWidget

from eric7 import Preferences
from eric7.EricCore import EricPreferences
from eric7.EricNetwork.EricNetworkProxyFactory import (
    EricNetworkProxyFactory,
    proxyAuthenticationRequired,
)
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricSideBar import EricSideBar, EricSideBarSide
from eric7.MicroPython.MicroPythonWidget import MicroPythonWidget
from eric7.PipInterface.Pip import Pip
from eric7.QScintilla.MiniEditor import MiniEditor
from eric7.SystemUtilities import FileSystemUtilities

try:
    from eric7.EricNetwork.EricSslErrorHandler import (
        EricSslErrorHandler,
        EricSslErrorState,
    )

    SSL_AVAILABLE = True
except ImportError:
    SSL_AVAILABLE = False


class MicroPythonWindow(EricMainWindow):
    """
    Class implementing the standalone MicroPython window.

    @signal editorCountChanged(count) emitted whenever the count of open editors
        changed
    @signal preferencesChanged() emitted after the preferences were changed
    """

    editorCountChanged = pyqtSignal(int)
    preferencesChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__pip = Pip(self)

        # create the window layout
        self.__mpyWidget = MicroPythonWidget(parent=self, forMPyWindow=True)
        self.__mpyWidget.aboutToDisconnect.connect(self.__deviceDisconnect)

        self.__bottomSidebar = EricSideBar(
            EricSideBarSide.SOUTH, Preferences.getUI("IconBarSize")
        )
        self.__bottomSidebar.setIconBarColor(Preferences.getUI("IconBarColor"))

        self.__verticalSplitter = QSplitter(Qt.Orientation.Vertical)
        self.__verticalSplitter.setChildrenCollapsible(False)
        self.__verticalSplitter.addWidget(self.__mpyWidget)
        self.__verticalSplitter.addWidget(self.__bottomSidebar)
        self.setCentralWidget(self.__verticalSplitter)

        self.setWindowTitle(self.tr("MicroPython / CircuitPython Devices"))

        g = Preferences.getGeometry("MPyWindowGeometry")
        if g.isEmpty():
            s = QSize(800, 1000)
            self.resize(s)
        else:
            self.restoreGeometry(g)
        self.__verticalSplitter.setSizes(
            Preferences.getMicroPython("MPyWindowSplitterSizes")
        )

        # register the objects
        ericApp().registerObject("UserInterface", self)
        ericApp().registerObject("ViewManager", self)
        ericApp().registerObject("Pip", self.__pip)
        ericApp().registerObject("MicroPython", self.__mpyWidget)

        # attributes to manage the open editors
        self.__editors = []
        self.__activeEditor = None

        ericApp().focusChanged.connect(self.__appFocusChanged)

        # network related setup
        if EricPreferences.getNetworkProxy("UseSystemProxy"):
            QNetworkProxyFactory.setUseSystemConfiguration(True)
        else:
            self.__proxyFactory = EricNetworkProxyFactory()
            QNetworkProxyFactory.setApplicationProxyFactory(self.__proxyFactory)
            QNetworkProxyFactory.setUseSystemConfiguration(False)

        self.__networkManager = QNetworkAccessManager(self)
        self.__networkManager.proxyAuthenticationRequired.connect(
            proxyAuthenticationRequired
        )
        if SSL_AVAILABLE:
            self.__sslErrorHandler = EricSslErrorHandler(
                Preferences.getSettings(), self
            )
            self.__networkManager.sslErrors.connect(self.__sslErrors)
        self.__replies = []

        self.__bottomSidebar.setVisible(False)

    def closeEvent(self, evt):
        """
        Protected event handler for the close event.

        @param evt reference to the close event
            <br />This event is simply accepted after the history has been
            saved and all window references have been deleted.
        @type QCloseEvent
        """
        Preferences.setGeometry("MPyWindowGeometry", self.saveGeometry())
        Preferences.setMicroPython(
            "MPyWindowSplitterSizes", self.__verticalSplitter.sizes()
        )

        for editor in self.__editors[:]:
            with contextlib.suppress(RuntimeError):
                editor.close()

        evt.accept()

    def __sslErrors(self, reply, errors):
        """
        Private slot to handle SSL errors.

        @param reply reference to the reply object
        @type QNetworkReply
        @param errors list of SSL errors
        @type list of QSslError
        """
        ignored = self.__sslErrorHandler.sslErrorsReply(reply, errors)[0]
        if ignored == EricSslErrorState.NOT_IGNORED:
            self.__downloadCancelled = True

    #######################################################################
    ## Methods below implement user interface methods needed by the
    ## MicroPython widget.
    #######################################################################

    def addSideWidget(
        self,
        _side,
        widget,
        icon,
        label,
    ):
        """
        Public method to add a widget to the sides.

        @param _side side to add the widget to (unused)
        @type UserInterfaceSide
        @param widget reference to the widget to add
        @type QWidget
        @param icon icon to be used
        @type QIcon
        @param label label text to be shown
        @type str
        """
        self.__bottomSidebar.addTab(widget, icon, label)
        self.__bottomSidebar.setVisible(True)

    def showSideWidget(self, widget):
        """
        Public method to show a specific widget placed in the side widgets.

        @param widget reference to the widget to be shown
        @type QWidget
        """
        index = self.__bottomSidebar.indexOf(widget)
        if index != -1:
            self.__bottomSidebar.show()
            self.__bottomSidebar.setCurrentIndex(index)
            self.__bottomSidebar.raise_()

    def removeSideWidget(self, widget):
        """
        Public method to remove a widget added using addSideWidget().

        @param widget reference to the widget to remove
        @type QWidget
        """
        index = self.__bottomSidebar.indexOf(widget)
        if index != -1:
            self.__bottomSidebar.removeTab(index)

        self.__bottomSidebar.setVisible(self.__bottomSidebar.count() > 0)

    def networkAccessManager(self):
        """
        Public method to get a reference to the network access manager object.

        @return reference to the network access manager object
        @rtype QNetworkAccessManager
        """
        return self.__networkManager

    def launchHelpViewer(self, url):
        """
        Public slot to start the help viewer/web browser.

        @param url URL to be opened
        @type str or QUrl
        """
        started = QDesktopServices.openUrl(QUrl(url))
        if not started:
            EricMessageBox.critical(
                self, self.tr("Open Browser"), self.tr("Could not start a web browser")
            )

    @pyqtSlot()
    @pyqtSlot(str)
    def showPreferences(self, pageName=None):
        """
        Public slot to set the preferences.

        @param pageName name of the configuration page to show
        @type str
        """
        from eric7.Preferences.ConfigurationDialog import (
            ConfigurationDialog,
            ConfigurationMode,
        )

        dlg = ConfigurationDialog(
            parent=self,
            name="Configuration",
            modal=True,
            fromEric=True,
            displayMode=ConfigurationMode.MICROPYTHONMODE,
        )
        dlg.show()
        if pageName is not None:
            dlg.showConfigurationPageByName(pageName)
        else:
            dlg.showConfigurationPageByName("empty")
        dlg.exec()
        if dlg.result() == QDialog.DialogCode.Accepted:
            dlg.setPreferences()
            Preferences.syncPreferences()
            self.__preferencesChanged()

    @pyqtSlot()
    def __preferencesChanged(self):
        """
        Private slot to handle a change of the preferences.
        """
        self.__bottomSidebar.setIconBarColor(Preferences.getUI("IconBarColor"))
        self.__bottomSidebar.setIconBarSize(Preferences.getUI("IconBarSize"))

        if EricPreferences.getNetworkProxy("UseSystemProxy"):
            QNetworkProxyFactory.setUseSystemConfiguration(True)
        else:
            self.__proxyFactory = EricNetworkProxyFactory()
            QNetworkProxyFactory.setApplicationProxyFactory(self.__proxyFactory)
            QNetworkProxyFactory.setUseSystemConfiguration(False)

        self.preferencesChanged.emit()

    #######################################################################
    ## Methods below implement view manager methods needed by the
    ## MicroPython widget.
    #######################################################################

    def activeWindow(self):
        """
        Public method to get a reference to the active editor.

        @return reference to the active editor
        @rtype MiniEditor
        """
        return self.__activeEditor

    def getEditor(self, fn):
        """
        Public method to return the editor displaying the given file.

        @param fn filename to look for
        @type str
        """
        for editor in self.__editors:
            if editor.getFileName() == fn:
                editor.raise_()
                break
        else:
            editor = MiniEditor(filename=fn, parent=self)
            editor.closing.connect(lambda: self.__editorClosing(editor))
            editor.show()

            self.__editors.append(editor)
            self.editorCountChanged.emit(len(self.__editors))

    def newEditorWithText(self, text, language="", fileName=""):
        """
        Public method to generate a new editor with a given text and associated file
        name.

        @param text text for the editor
        @type str
        @param language source language (defaults to "")
        @type str (optional)
        @param fileName associated file name (defaults to "")
        @type str (optional)
        """
        editor = MiniEditor(filename=fileName, parent=self)
        editor.closing.connect(lambda: self.__editorClosing(editor))
        editor.setText(text, filetype=language)
        editor.setLanguage(fileName)
        editor.show()

        self.__editors.append(editor)
        self.editorCountChanged.emit(len(self.__editors))

    def __editorClosing(self, editor):
        """
        Private method called, when an editor is closing.

        @param editor reference to the closing editor
        @type MiniEditor
        """
        with contextlib.suppress(ValueError):
            self.__editors.remove(editor)
            del editor
            self.editorCountChanged.emit(len(self.__editors))

        if self.__editors:
            # make the last one (i.e. most recently opened one) the active editor
            self.__activeEditor = self.__editors[-1]
        else:
            self.__activeEditor = None

    def getOpenEditorsCount(self):
        """
        Public method to get the number of open editors.

        @return number of open editors
        @rtype int
        """
        return len(self.__editors)

    @pyqtSlot(QWidget, QWidget)
    def __appFocusChanged(self, _old, now):
        """
        Private slot to track the application focus.

        @param _old reference to the widget loosing focus (unused)
        @type QWidget
        @param now reference to the widget gaining focus
        @type QWidget
        """
        if now is None:
            return

        for editor in self.__editors:
            if now in editor.findChildren(QWidget):
                self.__activeEditor = editor
                break

    @pyqtSlot()
    def __deviceDisconnect(self):
        """
        Private slot handling the device being disconnected.

        This closes all editors directly connected to the device about to
        be disconnected.
        """
        for editor in self.__editors[:]:
            if FileSystemUtilities.isDeviceFileName(editor.getFileName()):
                editor.close()
