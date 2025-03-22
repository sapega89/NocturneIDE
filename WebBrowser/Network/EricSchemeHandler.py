# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a scheme handler for the eric: scheme.
"""

from PyQt6.QtCore import QBuffer, QIODevice, QMutex, QUrlQuery, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineUrlSchemeHandler

from eric7.EricUtilities.EricMutexLocker import EricMutexLocker
from eric7.EricWidgets.EricApplication import ericApp
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from ..Tools.WebBrowserTools import getHtmlPage, getJquery, pixmapFileToDataUrl

_SupportedPages = [
    "adblock",  # error page for URLs blocked by AdBlock
    "home",
    "start",
    "startpage",  # eric home page
    "speeddial",  # eric speeddial
]


class EricSchemeHandler(QWebEngineUrlSchemeHandler):
    """
    Class implementing a scheme handler for the eric: scheme.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__replies = []

    def requestStarted(self, job):
        """
        Public method handling the URL request.

        @param job URL request job
        @type QWebEngineUrlRequestJob
        """
        reply = EricSchemeReply(job)
        reply.closed.connect(lambda: self.__replyClosed(reply))
        self.__replies.append(reply)
        job.reply(b"text/html", reply)

    def __replyClosed(self, reply):
        """
        Private slot handling the closed signal of a reply.

        @param reply reference to the network reply
        @type EricSchemeReply
        """
        if reply in self.__replies:
            self.__replies.remove(reply)


class EricSchemeReply(QIODevice):
    """
    Class implementing a reply for a requested eric: page.

    @signal closed emitted to signal that the web engine has read
        the data
    """

    closed = pyqtSignal()

    _speedDialPage = ""

    def __init__(self, job, parent=None):
        """
        Constructor

        @param job reference to the URL request
        @type QWebEngineUrlRequestJob
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__loaded = False
        self.__job = job
        self.__mutex = QMutex()

        self.__pageName = self.__job.requestUrl().path()
        self.__buffer = QBuffer()

        self.__loadPage()

    def __loadPage(self):
        """
        Private method to load the requested page.
        """
        if self.__loaded:
            return

        with EricMutexLocker(self.__mutex):
            if self.__pageName == "adblock":
                contents = self.__adBlockPage()
            elif self.__pageName in ["home", "start", "startpage"]:
                contents = self.__startPage()
            elif self.__pageName == "speeddial":
                contents = self.__speedDialPage()
            else:
                contents = self.__errorPage()

            self.__buffer.setData(contents.encode("utf-8"))
            self.__buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            self.open(QIODevice.OpenModeFlag.ReadOnly)

        self.readyRead.emit()

        self.__loaded = True

    def bytesAvailable(self):
        """
        Public method to get the number of available bytes.

        @return number of available bytes
        @rtype int
        """
        with EricMutexLocker(self.__mutex):
            return self.__buffer.bytesAvailable()

    def readData(self, maxlen):
        """
        Public method to retrieve data from the reply object.

        @param maxlen maximum number of bytes to read
        @type int
        @return string containing the data
        @rtype bytes
        """
        with EricMutexLocker(self.__mutex):
            return self.__buffer.read(maxlen)

    def close(self):
        """
        Public method used to cloase the reply.
        """
        super().close()
        self.closed.emit()

    def __adBlockPage(self):
        """
        Private method to build the AdBlock page.

        @return built AdBlock page
        @rtype str
        """
        query = QUrlQuery(self.__job.requestUrl())
        rule = query.queryItemValue("rule")
        subscription = query.queryItemValue("subscription")
        title = self.tr("Content blocked by AdBlock Plus")
        message = self.tr("Blocked by rule: <i>{0} ({1})</i>").format(
            rule, subscription
        )

        page = getHtmlPage("adblockPage.html")
        page = page.replace("@FAVICON@", pixmapFileToDataUrl("adBlockPlus16.png", True))
        page = page.replace("@IMAGE@", pixmapFileToDataUrl("adBlockPlus64.png", True))
        page = page.replace("@TITLE@", title)
        page = page.replace("@MESSAGE@", message)

        return page

    def __errorPage(self):
        """
        Private method to build the Error page.

        @return built Error page
        @rtype str
        """
        page = getHtmlPage("ericErrorPage.html")
        page = page.replace("@FAVICON@", pixmapFileToDataUrl("ericWeb16.png", True))
        page = page.replace("@IMAGE@", pixmapFileToDataUrl("ericWeb32.png", True))
        page = page.replace("@TITLE@", self.tr("Error accessing eric: URL"))
        page = page.replace(
            "@MESSAGE@",
            self.tr(
                "The special URL <strong>{0}</strong> is not supported."
                " Please use one of these."
            ).format(self.__job.requestUrl().toDisplayString()),
        )
        page = page.replace(
            "@ERICLIST@",
            "<br/>".join(
                [
                    '<a href="eric:{0}">{0}</a>'.format(u)
                    for u in sorted(_SupportedPages)
                ]
            ),
        )

        return page

    def __startPage(self):
        """
        Private method to build the Start page.

        @return built Start page
        @rtype str
        """
        page = getHtmlPage("startPage.html")
        page = page.replace("@FAVICON@", pixmapFileToDataUrl("ericWeb16.png", True))
        page = page.replace("@IMAGE@", pixmapFileToDataUrl("ericWeb32.png", True))
        page = page.replace("@TITLE@", self.tr("Welcome to eric Web Browser!"))
        page = page.replace("@ERIC_LINK@", self.tr("About eric"))
        page = page.replace("@HEADER_TITLE@", self.tr("eric Web Browser"))
        page = page.replace("@SUBMIT@", self.tr("Search!"))
        ltr = "LTR" if ericApp().isLeftToRight() else "RTL"
        page = page.replace("@QT_LAYOUT_DIRECTION@", ltr)

        return page

    def __speedDialPage(self):
        """
        Private method to create the Speeddial page.

        @return prepared speeddial page
        @rtype str
        """
        if not self._speedDialPage:
            page = getHtmlPage("speeddialPage.html")
            page = page.replace("@FAVICON@", pixmapFileToDataUrl("ericWeb16.png", True))
            page = page.replace("@IMG_PLUS@", pixmapFileToDataUrl("plus.png", True))
            page = page.replace("@IMG_CLOSE@", pixmapFileToDataUrl("close.png", True))
            page = page.replace("@IMG_EDIT@", pixmapFileToDataUrl("edit.png", True))
            page = page.replace("@IMG_RELOAD@", pixmapFileToDataUrl("reload.png", True))
            page = page.replace(
                "@IMG_SETTINGS@", pixmapFileToDataUrl("setting.png", True)
            )
            page = page.replace(
                "@LOADING-IMG@", pixmapFileToDataUrl("loading.gif", True)
            )
            page = page.replace(
                "@BOX-BORDER@", pixmapFileToDataUrl("box-border-small.png", True)
            )

            page = page.replace("@JQUERY@", getJquery("jquery"))
            page = page.replace("@JQUERY-UI@", getJquery("jquery-ui"))

            page = page.replace("@SITE-TITLE@", self.tr("Speed Dial"))
            page = page.replace("@URL@", self.tr("URL"))
            page = page.replace("@TITLE@", self.tr("Title"))
            page = page.replace("@APPLY@", self.tr("Apply"))
            page = page.replace("@CANCEL@", self.tr("Cancel"))
            page = page.replace("@NEW-PAGE@", self.tr("New Page"))
            page = page.replace("@TITLE-EDIT@", self.tr("Edit"))
            page = page.replace("@TITLE-REMOVE@", self.tr("Remove"))
            page = page.replace("@TITLE-RELOAD@", self.tr("Reload"))
            page = page.replace(
                "@TITLE-WARN@", self.tr("Are you sure to remove this speed dial?")
            )
            page = page.replace(
                "@TITLE-WARN-REL@",
                self.tr("Are you sure you want to reload all speed dials?"),
            )
            page = page.replace("@TITLE-FETCHTITLE@", self.tr("Load title from page"))
            page = page.replace("@SETTINGS-TITLE@", self.tr("Speed Dial Settings"))
            page = page.replace("@ADD-TITLE@", self.tr("Add New Page"))
            page = page.replace("@TXT_NRROWS@", self.tr("Maximum pages in a row:"))
            page = page.replace("@TXT_SDSIZE@", self.tr("Change size of pages:"))
            page = page.replace(
                "@JAVASCRIPT_DISABLED@",
                self.tr("SpeedDial requires enabled JavaScript."),
            )

            self._speedDialPage = page

        dial = WebBrowserWindow.speedDial()
        page = (
            self._speedDialPage.replace("@INITIAL-SCRIPT@", dial.initialScript())
            .replace("@ROW-PAGES@", str(dial.pagesInRow()))
            .replace("@SD-SIZE@", str(dial.sdSize()))
        )

        return page
