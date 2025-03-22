# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to show some source code information provided by
plug-ins.
"""

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QTextBrowser,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricTextEditSearchWidget import (
    EricTextEditSearchWidget,
    EricTextEditType,
)

from .CodeDocumentationViewerTemplate import (
    prepareDocumentationViewerHtmlDocument,
    prepareDocumentationViewerHtmlDocWarningDocument,
    prepareDocumentationViewerHtmlWarningDocument,
)


class DocumentationViewerWidget(QWidget):
    """
    Class implementing a rich text documentation viewer.
    """

    EmpytDocument_Light = (
        """<!DOCTYPE html>\n"""
        """<html lang="EN">\n"""
        """<head>\n"""
        """<style type="text/css">\n"""
        """html {background-color: #ffffff;}\n"""
        """body {background-color: #ffffff;\n"""
        """      color: #000000;\n"""
        """      margin: 0px 10px 10px 10px;\n"""
        """}\n"""
        """</style"""
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
        """      margin: 0px 10px 10px 10px;\n"""
        """}\n"""
        """</style"""
        """</head>\n"""
        """<body>\n"""
        """</body>\n"""
        """</html>"""
    )

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setObjectName("DocumentationViewerWidget")

        self.__verticalLayout = QVBoxLayout(self)
        self.__verticalLayout.setObjectName("verticalLayout")
        self.__verticalLayout.setContentsMargins(0, 0, 0, 0)

        try:
            from PyQt6.QtWebEngineCore import (  # __IGNORE_WARNING_I10__
                QWebEngineSettings,
            )
            from PyQt6.QtWebEngineWidgets import (  # __IGNORE_WARNING_I10__
                QWebEngineView,
            )

            self.__contents = QWebEngineView(self)
            self.__contents.page().linkHovered.connect(self.__showLink)
            self.__contents.settings().setAttribute(
                QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, False
            )
            self.__viewerType = EricTextEditType.QWEBENGINEVIEW
        except ImportError:
            self.__contents = QTextBrowser(self)
            self.__contents.setOpenExternalLinks(True)
            self.__viewerType = EricTextEditType.QTEXTBROWSER

        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.__contents.sizePolicy().hasHeightForWidth())
        self.__contents.setSizePolicy(sizePolicy)
        self.__contents.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        if self.__viewerType != EricTextEditType.QTEXTBROWSER:
            self.__contents.setUrl(QUrl("about:blank"))
        self.__verticalLayout.addWidget(self.__contents)

        self.__searchWidget = EricTextEditSearchWidget(self, False)
        self.__searchWidget.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.__searchWidget.setObjectName("searchWidget")
        self.__verticalLayout.addWidget(self.__searchWidget)

        self.__searchWidget.attachTextEdit(self.__contents, editType=self.__viewerType)

    @pyqtSlot(str)
    def __showLink(self, urlStr):
        """
        Private slot to show the hovered link in a tooltip.

        @param urlStr hovered URL
        @type str
        """
        QToolTip.showText(QCursor.pos(), urlStr, self.__contents)

    def setHtml(self, html):
        """
        Public method to set the HTML text of the widget.

        @param html HTML text to be shown
        @type str
        """
        self.__contents.setEnabled(False)
        self.__contents.setHtml(html)
        self.__contents.setEnabled(True)

    def clear(self):
        """
        Public method to clear the shown contents.
        """
        if self.__viewerType == EricTextEditType.QTEXTBROWSER:
            self.__contents.clear()
        else:
            if ericApp().usesDarkPalette():
                self.__contents.setHtml(self.EmpytDocument_Dark)
            else:
                self.__contents.setHtml(self.EmpytDocument_Light)


class CodeDocumentationViewer(QWidget):
    """
    Class implementing a widget to show some source code information provided
    by plug-ins.

    @signal providerAdded() emitted to indicate the availability of a new
        provider
    @signal providerRemoved() emitted to indicate the removal of a provider
    """

    providerAdded = pyqtSignal()
    providerRemoved = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.__setupUi()

        self.__ui = parent

        self.__providers = {}
        self.__selectedProvider = ""
        self.__disabledProvider = "disabled"

        self.__shuttingDown = False
        self.__startingUp = True

        self.__lastDocumentation = None
        self.__requestingEditor = None

        self.__unregisterTimer = QTimer(self)
        self.__unregisterTimer.setInterval(30000)  # 30 seconds
        self.__unregisterTimer.setSingleShot(True)
        self.__unregisterTimer.timeout.connect(self.__unregisterTimerTimeout)
        self.__mostRecentlyUnregisteredProvider = None

    def __setupUi(self):
        """
        Private method to generate the UI layout.
        """
        self.setObjectName("CodeDocumentationViewer")

        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(3, 3, 3, 3)

        # top row 1 of widgets
        self.horizontalLayout1 = QHBoxLayout()
        self.horizontalLayout1.setObjectName("horizontalLayout1")

        self.label = QLabel(self)
        self.label.setObjectName("label")
        self.label.setText(self.tr("Code Info Provider:"))
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.horizontalLayout1.addWidget(self.label)

        self.providerComboBox = QComboBox(self)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.providerComboBox.sizePolicy().hasHeightForWidth()
        )
        self.providerComboBox.setSizePolicy(sizePolicy)
        self.providerComboBox.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.providerComboBox.setObjectName("providerComboBox")
        self.providerComboBox.setToolTip(self.tr("Select the code info provider"))
        self.providerComboBox.addItem(self.tr("<disabled>"), "disabled")
        self.horizontalLayout1.addWidget(self.providerComboBox)

        # top row 2 of widgets
        self.objectLineEdit = QLineEdit(self)
        self.objectLineEdit.setReadOnly(True)
        self.objectLineEdit.setObjectName("objectLineEdit")

        self.verticalLayout.addLayout(self.horizontalLayout1)
        self.verticalLayout.addWidget(self.objectLineEdit)

        # Rich Text (Web) Documentation Viewer
        self.__viewerWidget = DocumentationViewerWidget(self)
        self.__viewerWidget.setObjectName("__viewerWidget")
        self.verticalLayout.addWidget(self.__viewerWidget)

        self.providerComboBox.currentIndexChanged[int].connect(
            self.on_providerComboBox_currentIndexChanged
        )

    def finalizeSetup(self):
        """
        Public method to finalize the setup of the documentation viewer.
        """
        self.__startingUp = False
        provider = Preferences.getDocuViewer("Provider")
        if provider in self.__providers:
            index = self.providerComboBox.findData(provider)
        else:
            index = 0
            provider = self.__disabledProvider
        self.providerComboBox.setCurrentIndex(index)
        self.__selectedProvider = provider
        if index == 0:
            self.__showDisabledMessage()

    def registerProvider(self, providerName, providerDisplay, provider, supported):
        """
        Public method register a source docu provider.

        @param providerName name of the provider (must be unique)
        @type str
        @param providerDisplay visible name of the provider
        @type str
        @param provider function to be called to determine source docu
        @type function(editor)
        @param supported function to be called to determine, if a language is
            supported
        @type function(language)
        @exception KeyError raised if a provider with the given name was
            already registered
        """
        if providerName in self.__providers:
            raise KeyError("Provider '{0}' already registered.".format(providerName))

        self.__providers[providerName] = (provider, supported)
        self.providerComboBox.addItem(providerDisplay, providerName)

        self.providerAdded.emit()

        if (
            self.__unregisterTimer.isActive()
            and providerName == self.__mostRecentlyUnregisteredProvider
        ):
            # this is assumed to be a plug-in reload
            self.__unregisterTimer.stop()
            self.__mostRecentlyUnregisteredProvider = None
            self.__selectProvider(providerName)

    def unregisterProvider(self, providerName):
        """
        Public method register a source docu provider.

        @param providerName name of the provider (must be unique)
        @type str
        """
        if providerName in self.__providers:
            if providerName == self.__selectedProvider:
                self.providerComboBox.setCurrentIndex(0)

                # in case this is just a temporary unregistration (< 30s)
                # e.g. when the plug-in is re-installed or updated
                self.__mostRecentlyUnregisteredProvider = providerName
                self.__unregisterTimer.start()

            del self.__providers[providerName]
            index = self.providerComboBox.findData(providerName)
            self.providerComboBox.removeItem(index)

            self.providerRemoved.emit()

    @pyqtSlot()
    def __unregisterTimerTimeout(self):
        """
        Private slot handling the timeout signal of the unregister timer.
        """
        self.__mostRecentlyUnregisteredProvider = None

    def isSupportedLanguage(self, language):
        """
        Public method to check, if the given language is supported by the
        selected provider.

        @param language editor programming language to check
        @type str
        @return flag indicating the support status
        @rtype bool
        """
        supported = False

        if self.__selectedProvider != self.__disabledProvider:
            supported = self.__providers[self.__selectedProvider][1](language)

        return supported

    def getProviders(self):
        """
        Public method to get a list of providers and their visible strings.

        @return list containing the providers and their visible strings
        @rtype list of tuple of (str,str)
        """
        providers = []
        for index in range(1, self.providerComboBox.count()):
            provider = self.providerComboBox.itemData(index)
            text = self.providerComboBox.itemText(index)
            providers.append((provider, text))

        return providers

    def showInfo(self, editor):
        """
        Public method to request code documentation data from a provider.

        @param editor reference to the editor to request code docu for
        @type Editor
        """
        line, index = editor.getCursorPosition()
        word = editor.getWord(line, index)
        if not word:
            # try again one index before
            word = editor.getWord(line, index - 1)
        self.objectLineEdit.setText(word)

        if self.__selectedProvider != self.__disabledProvider:
            self.__viewerWidget.clear()
            self.__providers[self.__selectedProvider][0](editor)

    def documentationReady(
        self, documentationInfo, isWarning=False, isDocWarning=False
    ):
        """
        Public method to provide the documentation info to the viewer.

        If documentationInfo is a dictionary, it should contain these
        (optional) keys and data:

        name: the name of the inspected object
        argspec: its arguments specification
        note: A phrase describing the type of object (function or method) and
            the module it belongs to.
        docstring: its documentation string
        typ: its type information

        @param documentationInfo dictionary containing the source docu data
        @type dict or str
        @param isWarning flag indicating a warning page
        @type bool
        @param isDocWarning flag indicating a documentation warning page
        @type bool
        """
        self.__ui.activateCodeDocumentationViewer(switchFocus=False)

        if not isWarning and not isDocWarning:
            self.__lastDocumentation = documentationInfo

        if not documentationInfo:
            if self.__selectedProvider == self.__disabledProvider:
                self.__showDisabledMessage()
            else:
                self.documentationReady(
                    self.tr("No documentation available"), isDocWarning=True
                )
        else:
            if isWarning:
                html = prepareDocumentationViewerHtmlWarningDocument(documentationInfo)
            elif isDocWarning:
                html = prepareDocumentationViewerHtmlDocWarningDocument(
                    documentationInfo
                )
            elif isinstance(documentationInfo, dict):
                html = prepareDocumentationViewerHtmlDocument(documentationInfo)
            else:
                html = documentationInfo
            self.__viewerWidget.setHtml(html)

    def __showDisabledMessage(self):
        """
        Private method to show a message giving the reason for being disabled.
        """
        if len(self.__providers) == 0:
            self.documentationReady(
                self.tr(
                    "No source code documentation provider has been"
                    " registered. This function has been disabled."
                ),
                isWarning=True,
            )
        else:
            self.documentationReady(
                self.tr("This function has been disabled."), isWarning=True
            )

    @pyqtSlot(int)
    def on_providerComboBox_currentIndexChanged(self, index):
        """
        Private slot to handle the selection of a provider.

        @param index index of the selected provider
        @type int
        """
        if not self.__shuttingDown and not self.__startingUp:
            self.__viewerWidget.clear()
            self.objectLineEdit.clear()

            provider = self.providerComboBox.itemData(index)
            if provider == self.__disabledProvider:
                self.__showDisabledMessage()
            else:
                self.__lastDocumentation = None

            Preferences.setDocuViewer("Provider", provider)
            self.__selectedProvider = provider

    def shutdown(self):
        """
        Public method to perform shutdown actions.
        """
        self.__shuttingDown = True
        Preferences.setDocuViewer("Provider", self.__selectedProvider)

    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        provider = Preferences.getDocuViewer("Provider")
        self.__selectProvider(provider)

    def __selectProvider(self, provider):
        """
        Private method to select a provider programmatically.

        @param provider name of the provider to be selected
        @type str
        """
        if provider != self.__selectedProvider:
            index = self.providerComboBox.findData(provider)
            if index < 0:
                index = 0
            self.providerComboBox.setCurrentIndex(index)

    def isEnabled(self):
        """
        Public method to check, if the code documentation viewer is enabled.

        @return flag indicating the enabled state
        @rtype bool
        """
        provider = self.providerComboBox.currentData()
        return provider != self.__disabledProvider
