# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a web search widget for the web browser.
"""

from PyQt6.QtCore import QModelIndex, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap, QStandardItem, QStandardItemModel
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWidgets import QCompleter, QMenu

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricLineEdit import EricClearableLineEdit, EricLineEditSide
from eric7.EricWidgets.EricLineEditButton import EricLineEditButton
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .WebBrowserPage import WebBrowserPage


class WebBrowserWebSearchWidget(EricClearableLineEdit):
    """
    Class implementing a web search widget for the web browser.

    @signal search(QUrl) emitted when the search should be done
    """

    search = pyqtSignal(QUrl)

    def __init__(self, mainWindow, parent=None):
        """
        Constructor

        @param mainWindow reference to the browser main window
        @type WebBrowserWindow
        @param parent reference to the parent widget
        @type QWidget
        """
        from .OpenSearch.OpenSearchManager import OpenSearchManager

        super().__init__(parent)

        self.__mw = mainWindow

        self.__openSearchManager = OpenSearchManager(self)
        self.__openSearchManager.currentEngineChanged.connect(
            self.__currentEngineChanged
        )
        self.__currentEngine = ""

        self.__enginesMenu = QMenu(self)
        self.__enginesMenu.triggered.connect(self.__handleEnginesMenuActionTriggered)

        self.__engineButton = EricLineEditButton(self)
        self.__engineButton.setMenu(self.__enginesMenu)
        self.addWidget(self.__engineButton, EricLineEditSide.LEFT)

        self.__searchButton = EricLineEditButton(self)
        self.__searchButton.setIcon(EricPixmapCache.getIcon("webSearch"))
        self.addWidget(self.__searchButton, EricLineEditSide.LEFT)

        self.__model = QStandardItemModel(self)
        self.__completer = QCompleter()
        self.__completer.setModel(self.__model)
        self.__completer.setCompletionMode(
            QCompleter.CompletionMode.UnfilteredPopupCompletion
        )
        self.__completer.setWidget(self)

        self.__searchButton.clicked.connect(self.__searchButtonClicked)
        self.textEdited.connect(self.__textEdited)
        self.returnPressed.connect(self.__searchNow)
        self.__completer.activated[QModelIndex].connect(self.__completerActivated)
        self.__completer.highlighted[QModelIndex].connect(self.__completerHighlighted)
        self.__enginesMenu.aboutToShow.connect(self.__showEnginesMenu)

        self.__suggestionsItem = None
        self.__suggestions = []
        self.__suggestTimer = None
        self.__suggestionsEnabled = Preferences.getWebBrowser("WebSearchSuggestions")

        self.__recentSearchesItem = None
        self.__recentSearches = []
        self.__maxSavedSearches = 10

        self.__engine = None
        self.__loadSearches()
        self.__setupCompleterMenu()
        self.__currentEngineChanged()

    def __searchNow(self):
        """
        Private slot to perform the web search.
        """
        searchText = self.text()
        if not searchText:
            return

        if WebBrowserWindow.isPrivate():
            return

        if searchText in self.__recentSearches:
            self.__recentSearches.remove(searchText)
        self.__recentSearches.insert(0, searchText)
        if len(self.__recentSearches) > self.__maxSavedSearches:
            self.__recentSearches = self.__recentSearches[: self.__maxSavedSearches]
        self.__setupCompleterMenu()

        self.__mw.currentBrowser().setFocus()
        self.__mw.currentBrowser().load(
            self.__openSearchManager.currentEngine().searchUrl(searchText)
        )

    def __setupCompleterMenu(self):
        """
        Private method to create the completer menu.
        """
        if not self.__suggestions or (
            self.__model.rowCount() > 0
            and self.__model.item(0) != self.__suggestionsItem
        ):
            self.__model.clear()
            self.__suggestionsItem = None
        else:
            self.__model.removeRows(1, self.__model.rowCount() - 1)

        boldFont = QFont()
        boldFont.setBold(True)

        if self.__suggestions:
            if self.__model.rowCount() == 0:
                if not self.__suggestionsItem:
                    self.__suggestionsItem = QStandardItem(self.tr("Suggestions"))
                    self.__suggestionsItem.setFont(boldFont)
                self.__model.appendRow(self.__suggestionsItem)

            for suggestion in self.__suggestions:
                self.__model.appendRow(QStandardItem(suggestion))

        if not self.__recentSearches:
            self.__recentSearchesItem = QStandardItem(self.tr("No Recent Searches"))
            self.__recentSearchesItem.setFont(boldFont)
            self.__model.appendRow(self.__recentSearchesItem)
        else:
            self.__recentSearchesItem = QStandardItem(self.tr("Recent Searches"))
            self.__recentSearchesItem.setFont(boldFont)
            self.__model.appendRow(self.__recentSearchesItem)
            for recentSearch in self.__recentSearches:
                self.__model.appendRow(QStandardItem(recentSearch))

        view = self.__completer.popup()
        view.setFixedHeight(
            view.sizeHintForRow(0) * self.__model.rowCount() + view.frameWidth() * 2
        )

        self.__searchButton.setEnabled(
            bool(self.__recentSearches or self.__suggestions)
        )

    def __completerActivated(self, index):
        """
        Private slot handling the selection of an entry from the completer.

        @param index index of the item
        @type QModelIndex
        """
        if (
            self.__suggestionsItem
            and self.__suggestionsItem.index().row() == index.row()
        ):
            return

        if (
            self.__recentSearchesItem
            and self.__recentSearchesItem.index().row() == index.row()
        ):
            return

        self.__searchNow()

    def __completerHighlighted(self, index):
        """
        Private slot handling the highlighting of an entry of the completer.

        @param index index of the item
        @type QModelIndex
        @return flah indicating a successful highlighting
        @rtype bool
        """
        if (
            self.__suggestionsItem
            and self.__suggestionsItem.index().row() == index.row()
        ):
            return False

        if (
            self.__recentSearchesItem
            and self.__recentSearchesItem.index().row() == index.row()
        ):
            return False

        self.setText(index.data())
        return True

    def __textEdited(self, txt):
        """
        Private slot to handle changes of the search text.

        @param txt search text
        @type str
        """
        if self.__suggestionsEnabled:
            if self.__suggestTimer is None:
                self.__suggestTimer = QTimer(self)
                self.__suggestTimer.setSingleShot(True)
                self.__suggestTimer.setInterval(200)
                self.__suggestTimer.timeout.connect(self.__getSuggestions)
            self.__suggestTimer.start()
        else:
            self.__completer.setCompletionPrefix(txt)
            self.__completer.complete()

    def __getSuggestions(self):
        """
        Private slot to get search suggestions from the configured search
        engine.
        """
        searchText = self.text()
        if searchText:
            self.__openSearchManager.currentEngine().requestSuggestions(searchText)

    def __newSuggestions(self, suggestions):
        """
        Private slot to receive a new list of suggestions.

        @param suggestions list of suggestions
        @type list of str
        """
        self.__suggestions = suggestions
        self.__setupCompleterMenu()
        self.__completer.complete()

    def __showEnginesMenu(self):
        """
        Private slot to handle the display of the engines menu.
        """
        from .OpenSearch.OpenSearchEngineAction import OpenSearchEngineAction
        from .Tools import Scripts

        self.__enginesMenu.clear()

        engineNames = self.__openSearchManager.allEnginesNames()
        for engineName in engineNames:
            engine = self.__openSearchManager.engine(engineName)
            action = OpenSearchEngineAction(engine, self.__enginesMenu)
            action.setData(engineName)
            self.__enginesMenu.addAction(action)

            if self.__openSearchManager.currentEngineName() == engineName:
                action.setCheckable(True)
                action.setChecked(True)

        cb = self.__mw.currentBrowser()
        script = Scripts.getOpenSearchLinks()
        cb.page().runJavaScript(
            script, WebBrowserPage.SafeJsWorld, self.__showEnginesMenuCallback
        )

    def __showEnginesMenuCallback(self, res):
        """
        Private method handling the open search links callback.

        @param res result of the JavaScript
        @type list of dict
        """
        cb = self.__mw.currentBrowser()
        if res:
            self.__enginesMenu.addSeparator()
            for entry in res:
                url = cb.url().resolved(QUrl(entry["url"]))
                title = entry["title"]
                if url.isEmpty():
                    continue
                if not title:
                    title = cb.title()

                action = self.__enginesMenu.addAction(
                    self.tr("Add '{0}'").format(title)
                )
                action.setData(url)
                action.setIcon(cb.icon())

        self.__enginesMenu.addSeparator()
        self.__enginesMenu.addAction(self.__mw.searchEnginesAction())

        if self.__recentSearches:
            act = self.__enginesMenu.addAction(self.tr("Clear Recent Searches"))
            act.setData("@@CLEAR@@")

    def __handleEnginesMenuActionTriggered(self, action):
        """
        Private slot to handle an action of the menu being triggered.

        @param action reference to the action that triggered
        @type QAction
        """
        actData = action.data()
        if isinstance(actData, QUrl):
            # add search engine
            self.__openSearchManager.addEngine(actData)
        elif isinstance(actData, str):
            # engine name or special action
            if actData == "@@CLEAR@@":
                self.clear()
            else:
                self.__openSearchManager.setCurrentEngineName(actData)

    def __searchButtonClicked(self):
        """
        Private slot to show the search menu via the search button.
        """
        self.__setupCompleterMenu()
        self.__completer.complete()

    def clear(self):
        """
        Public method to clear all private data.
        """
        self.__recentSearches = []
        self.__setupCompleterMenu()
        super().clear()
        self.clearFocus()

    def preferencesChanged(self):
        """
        Public method to handle the change of preferences.
        """
        self.__suggestionsEnabled = Preferences.getWebBrowser("WebSearchSuggestions")
        if not self.__suggestionsEnabled:
            self.__suggestions = []
            self.__setupCompleterMenu()

    def saveSearches(self):
        """
        Public method to save the recently performed web searches.
        """
        Preferences.getSettings().setValue(
            "WebBrowser/WebSearches", self.__recentSearches
        )

    def __loadSearches(self):
        """
        Private method to load the recently performed web searches.
        """
        searches = Preferences.getSettings().value("WebBrowser/WebSearches")
        if searches is not None:
            self.__recentSearches = searches

    def openSearchManager(self):
        """
        Public method to get a reference to the opensearch manager object.

        @return reference to the opensearch manager object
        @rtype OpenSearchManager
        """
        return self.__openSearchManager

    def __currentEngineChanged(self):
        """
        Private slot to track a change of the current search engine.
        """
        if self.__openSearchManager.engineExists(self.__currentEngine):
            oldEngine = self.__openSearchManager.engine(self.__currentEngine)
            oldEngine.imageChanged.disconnect(self.__engineImageChanged)
            if self.__suggestionsEnabled:
                oldEngine.suggestions.disconnect(self.__newSuggestions)

        newEngine = self.__openSearchManager.currentEngine()
        if newEngine.networkAccessManager() is None:
            newEngine.setNetworkAccessManager(self.__mw.networkManager())
        newEngine.imageChanged.connect(self.__engineImageChanged)
        if self.__suggestionsEnabled:
            newEngine.suggestions.connect(self.__newSuggestions)

        self.setPlaceholderText(self.__openSearchManager.currentEngineName())
        self.__currentEngine = self.__openSearchManager.currentEngineName()
        self.__engineButton.setIcon(
            QIcon(QPixmap.fromImage(self.__openSearchManager.currentEngine().image()))
        )
        self.__suggestions = []
        self.__setupCompleterMenu()

    def __engineImageChanged(self):
        """
        Private slot to handle a change of the current search engine icon.
        """
        self.__engineButton.setIcon(
            QIcon(QPixmap.fromImage(self.__openSearchManager.currentEngine().image()))
        )

    def mousePressEvent(self, evt):
        """
        Protected method called by a mouse press event.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.XButton1:
            self.__mw.currentBrowser().triggerPageAction(QWebEnginePage.WebAction.Back)
        elif evt.button() == Qt.MouseButton.XButton2:
            self.__mw.currentBrowser().triggerPageAction(
                QWebEnginePage.WebAction.Forward
            )
        else:
            super().mousePressEvent(evt)
