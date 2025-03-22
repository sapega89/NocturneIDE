# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a QWebEngineView to load the web inspector in.
"""

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

from eric7 import Preferences

_VIEWS = []


class WebInspector(QWebEngineView):
    """
    Class implementing a QWebEngineView to load the web inspector in.

    @signal inspectorClosed emitted to indicate the closing of the inspector
        window
    """

    inspectorClosed = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__view = None
        self.__inspectElement = False

        self.__reloadGeometry()

        registerView(self)

        self.page().windowCloseRequested.connect(self.close)
        self.page().loadFinished.connect(self.__loadFinished)

    def closeEvent(self, evt):
        """
        Protected method to save the geometry when closed.

        @param evt event object
        @type QCloseEvent
        """
        Preferences.setGeometry("WebInspectorGeometry", self.saveGeometry())
        super().closeEvent(evt)

        if evt.isAccepted():
            self.inspectorClosed.emit()

    def __reloadGeometry(self):
        """
        Private method to restore the geometry.
        """
        geom = Preferences.getGeometry("WebInspectorGeometry")
        if geom.isEmpty():
            s = QSize(600, 600)
            self.resize(s)
        else:
            self.restoreGeometry(geom)

    def setView(self, view, inspectElement=False):
        """
        Public method to connect a view to this inspector.

        @param view reference to the view object
        @type WebBrowserView
        @param inspectElement flag indicating to start a web inspection
        @type bool
        """
        self.__view = view
        if not self.isEnabled():
            return

        self.__inspectElement = inspectElement

        self.page().setInspectedPage(self.__view.page())

    def inspectElement(self):
        """
        Public method to inspect an element.
        """
        self.__inspectElement = True

    @classmethod
    def isEnabled(cls):
        """
        Class method to check, if the web inspector is enabled.

        @return flag indicating the enabled state
        @rtype bool
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        if not WebBrowserWindow.webSettings().testAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled
        ):
            return False

        return True

    def __loadFinished(self):
        """
        Private slot handling the finished signal.
        """
        if self.__inspectElement:
            self.__view.triggerPageAction(QWebEnginePage.WebAction.InspectElement)
            self.__inspectElement = False


def registerView(view):
    """
    Function to register a view.

    @param view reference to the view
    @type WebBrowserView
    """
    if _VIEWS is None:
        return

    _VIEWS.insert(0, view)


def unregisterView(view):
    """
    Function to unregister a view.

    @param view reference to the view
    @type WebBrowserView
    """
    if _VIEWS is None:
        return

    if view in _VIEWS:
        _VIEWS.remove(view)


def pushView(view):
    """
    Function to push a view to the front of the list.

    @param view reference to the view
    @type WebBrowserView
    """
    if _VIEWS is None:
        return

    if view in _VIEWS:
        _VIEWS.remove(view)
    _VIEWS.insert(0, view)
