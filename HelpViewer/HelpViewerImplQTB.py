# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the QTextBrowser based help viewer class.
"""

import contextlib
import functools

from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QEvent,
    QPoint,
    Qt,
    QUrl,
    pyqtSlot,
)
from PyQt6.QtGui import QClipboard, QDesktopServices, QGuiApplication, QImage
from PyQt6.QtWidgets import QMenu, QTextBrowser

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricTextEditSearchWidget import EricTextEditType

from .HelpViewerImpl import HelpViewerImpl

AboutBlank = QCoreApplication.translate(
    "HelpViewer",
    "<html><head><title>about:blank</title></head><body></body></html>",
)

PageNotFound = QCoreApplication.translate(
    "HelpViewer",
    """<html>"""
    """<head><title>Error 404...</title></head>"""
    """<body><div align="center"><br><br>"""
    """<h1>The page could not be found</h1><br>"""
    """<h3>'{0}'</h3></div></body>"""
    """</html>""",
)


class HelpViewerImplQTB(HelpViewerImpl, QTextBrowser):
    """
    Class implementing the QTextBrowser based help viewer class.
    """

    def __init__(self, engine, parent=None):
        """
        Constructor

        @param engine reference to the help engine
        @type QHelpEngine
        @param parent reference to the parent widget
        @type QWidget
        """
        QTextBrowser.__init__(self, parent=parent)
        HelpViewerImpl.__init__(self, engine, EricTextEditType.QTEXTBROWSER)

        self.__helpViewerWidget = parent

        self.__zoomCount = 0

        self.__menu = QMenu(self)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)

        self.sourceChanged.connect(self.titleChanged)

        self.grabGesture(Qt.GestureType.PinchGesture)

    def setLink(self, url):
        """
        Public method to set the URL of the document to be shown.

        @param url source of the document
        @type QUrl
        """
        if url.toString() == "about:blank":
            self.setHtml(self.__helpViewerWidget.emptyDocument())
        else:
            self.setSource(url)

    def link(self):
        """
        Public method to get the URL of the shown document.

        @return URL of the document
        @rtype QUrl
        """
        return self.source()

    def doSetSource(self, url, type_):
        """
        Public method to load the data and show it.

        @param url URL of resource to load
        @type QUrl
        @param type_ type of the resource to load
        @type QTextDocument.ResourceType
        """
        if not self.__canLoadResource(url):
            QDesktopServices.openUrl(url)
            return

        super().doSetSource(url, type_)

        self.sourceChanged.emit(url)
        self.loadFinished.emit(True)

    def loadResource(self, type_, name):
        """
        Public method to load data of the specified type from the resource with
        the given name.

        @param type_ resource type
        @type int
        @param name resource name
        @type QUrl
        @return byte array containing the loaded data
        @rtype QByteArray
        """
        ba = QByteArray()
        scheme = name.scheme()

        if type_ < 4:  # QTextDocument.ResourceType.MarkdownResource
            if scheme == "about":
                if name.toString() == "about:blank":
                    return QByteArray(AboutBlank.encode("utf-8"))
            elif scheme in ("file", ""):
                filePath = name.toLocalFile()
                with contextlib.suppress(OSError), open(filePath, "rb") as f:
                    ba = QByteArray(f.read())
            elif scheme == "qthelp":
                url = self._engine.findFile(name)
                if url.isValid():
                    ba = self._engine.fileData(url)

            if name.toString().lower().endswith(".svg"):
                image = QImage()
                image.loadFromData(ba, "svg")
                if not image.isNull():
                    return image

            if ba.isEmpty():
                ba = QByteArray(PageNotFound.format(name.toString()).encode("utf-8"))

        return ba

    def __canLoadResource(self, url):
        """
        Private method to check, if the given resource can be loaded.

        @param url URL of resource to be loaded
        @type QUrl
        @return flag indicating, that the given URL can be handled
        @rtype bool
        """
        scheme = url.scheme()
        return scheme in ("about", "qthelp", "file", "")

    def pageTitle(self):
        """
        Public method get the page title.

        @return page title
        @rtype str
        """
        titleStr = self.documentTitle()
        if not titleStr:
            url = self.link()

            titleStr = url.host()
            if not titleStr:
                titleStr = url.toString(QUrl.UrlFormattingOption.RemoveFragment)

        if not titleStr or titleStr == "about:blank":
            titleStr = self.tr("Empty Page")

        return titleStr

    def isEmptyPage(self):
        """
        Public method to check, if the current page is the empty page.

        @return flag indicating an empty page is loaded
        @rtype bool
        """
        return self.pageTitle() == self.tr("Empty Page")

    def mousePressEvent(self, evt):
        """
        Protected method called by a mouse press event.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.XButton1:
            self.backward()
            evt.accept()
        elif evt.button() == Qt.MouseButton.XButton2:
            self.forward()
            evt.accept()
        else:
            super().mousePressEvent(evt)

    def mouseReleaseEvent(self, evt):
        """
        Protected method called by a mouse release event.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        hasModifier = evt.modifiers() != Qt.KeyboardModifier.NoModifier
        if evt.button() == Qt.MouseButton.LeftButton and hasModifier:
            anchor = self.anchorAt(evt.pos())
            if anchor:
                url = self.link().resolved(QUrl(anchor))
                if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.__helpViewerWidget.openUrlNewBackgroundPage(url)
                else:
                    self.__helpViewerWidget.openUrlNewPage(url)
                evt.accept()
        else:
            super().mousePressEvent(evt)

    def gotoHistory(self, index):
        """
        Public method to step through the history.

        @param index history index (<0 backward, >0 forward)
        @type int
        """
        if index < 0:
            # backward
            for _ind in range(-index):
                self.backward()
        else:
            # forward
            for _ind in range(index):
                self.forward()

    def isBackwardAvailable(self):
        """
        Public method to check, if stepping backward through the history is
        available.

        @return flag indicating backward stepping is available
        @rtype bool
        """
        return QTextBrowser.isBackwardAvailable(self)

    def isForwardAvailable(self):
        """
        Public method to check, if stepping forward through the history is
        available.

        @return flag indicating forward stepping is available
        @rtype bool
        """
        return QTextBrowser.isForwardAvailable(self)

    def scaleUp(self):
        """
        Public method to zoom in.
        """
        if self.__zoomCount < 10:
            self.__zoomCount += 1
            self.zoomIn()
            self.zoomChanged.emit()

    def scaleDown(self):
        """
        Public method to zoom out.
        """
        if self.__zoomCount > -5:
            self.__zoomCount -= 1
            self.zoomOut()
            self.zoomChanged.emit()

    def setScale(self, scale):
        """
        Public method to set the zoom level.

        @param scale zoom level to set
        @type int
        """
        if -5 <= scale <= 10:
            self.zoomOut(scale)
            self.__zoomCount = scale
            self.zoomChanged.emit()

    def resetScale(self):
        """
        Public method to reset the zoom level.
        """
        if self.__zoomCount != 0:
            self.zoomOut(self.__zoomCount)
            self.zoomChanged.emit()
        self.__zoomCount = 0

    def scale(self):
        """
        Public method to get the zoom level.

        @return current zoom level
        @rtype int
        """
        return self.__zoomCount

    def isScaleUpAvailable(self):
        """
        Public method to check, if the max. zoom level is reached.

        @return flag indicating scale up is available
        @rtype bool
        """
        return self.__zoomCount < 10

    def isScaleDownAvailable(self):
        """
        Public method to check, if the min. zoom level is reached.

        @return flag indicating scale down is available
        @rtype bool
        """
        return self.__zoomCount > -5

    def wheelEvent(self, evt):
        """
        Protected method to handle wheel event to zoom.

        @param evt reference to the event object
        @type QWheelEvent
        """
        delta = evt.angleDelta().y()
        if evt.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if delta > 0:
                self.scaleUp()
            else:
                self.scaleDown()
            evt.accept()

        elif evt.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if delta < 0:
                self.backward()
            elif delta > 0:
                self.forward()
            evt.accept()

        else:
            QTextBrowser.wheelEvent(self, evt)

    def keyPressEvent(self, evt):
        """
        Protected method to handle key press events.

        @param evt reference to the key event
        @type QKeyEvent
        """
        key = evt.key()
        isControlModifier = evt.modifiers() == Qt.KeyboardModifier.ControlModifier

        if key == Qt.Key.Key_ZoomIn or (key == Qt.Key.Key_Plus and isControlModifier):
            self.scaleUp()
            evt.accept()
        elif key == Qt.Key.Key_ZoomOut or (
            key == Qt.Key.Key_Minus and isControlModifier
        ):
            self.scaleDown()
            evt.accept()
        elif key == Qt.Key.Key_0 and isControlModifier:
            self.resetScale()
            evt.accept()
        elif key == Qt.Key.Key_Backspace or (
            key == Qt.Key.Key_Left and isControlModifier
        ):
            self.backward()
            evt.accept()
        elif key == Qt.Key.Key_Right and isControlModifier:
            self.forward()
            evt.accept()
        elif key == Qt.Key.Key_F and isControlModifier:
            self.__helpViewerWidget.showHideSearch(True)
            evt.accept()
        elif key == Qt.Key.Key_F3 and evt.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.__helpViewerWidget.searchNext()
            evt.accept()
        elif (
            key == Qt.Key.Key_F3
            and evt.modifiers() == Qt.KeyboardModifier.ShiftModifier
        ):
            self.__helpViewerWidget.searchPrev()
            evt.accept()
        else:
            super().keyPressEvent(evt)

    def event(self, evt):
        """
        Public method handling events.

        @param evt reference to the event
        @type QEvent
        @return flag indicating the event was handled
        @rtype bool
        """
        if evt.type() == QEvent.Type.Gesture:
            self.gestureEvent(evt)
            return True

        return super().event(evt)

    def gestureEvent(self, evt):
        """
        Protected method handling gesture events.

        @param evt reference to the gesture event
        @type QGestureEvent
        """
        pinch = evt.gesture(Qt.GestureType.PinchGesture)
        if pinch:
            if pinch.state() == Qt.GestureState.GestureStarted:
                zoom = (self.getZoom() + 6) / 10.0
                pinch.setTotalScaleFactor(zoom)
            elif pinch.state() == Qt.GestureState.GestureUpdated:
                zoom = int(pinch.totalScaleFactor() * 10) - 6
                if zoom <= -5:
                    zoom = -5
                    pinch.setTotalScaleFactor(0.1)
                elif zoom >= 10:
                    zoom = 10
                    pinch.setTotalScaleFactor(1.6)
                self.setScale(zoom)
            evt.accept()

    #######################################################################
    ## Context menu related methods below
    #######################################################################

    @pyqtSlot(QPoint)
    def __showContextMenu(self, pos):
        """
        Private slot to show the context menu.

        @param pos position to show the context menu at
        @type QPoint
        """
        self.__menu.clear()
        anchor = self.anchorAt(pos)
        linkUrl = self.link().resolved(QUrl(anchor)) if anchor else QUrl()
        selectedText = self.textCursor().selectedText()

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("back"), self.tr("Backward"), self.backward
        )
        act.setEnabled(self.isBackwardAvailable())

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("forward"), self.tr("Forward"), self.forward
        )
        act.setEnabled(self.isForwardAvailable())

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("reload"), self.tr("Reload"), self.reload
        )

        if not linkUrl.isEmpty() and linkUrl.scheme() != "javascript":
            self.__createLinkContextMenu(self.__menu, linkUrl)

        self.__menu.addSeparator()

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy Page URL to Clipboard")
        )
        act.setData(self.link())
        act.triggered.connect(functools.partial(self.__copyLink, act))

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("bookmark22"), self.tr("Bookmark Page")
        )
        act.setData({"title": self.pageTitle(), "url": self.link()})
        act.triggered.connect(functools.partial(self.__bookmarkPage, act))

        self.__menu.addSeparator()

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("zoomIn"), self.tr("Zoom in"), self.scaleUp
        )
        act.setEnabled(self.isScaleUpAvailable())

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("zoomOut"), self.tr("Zoom out"), self.scaleDown
        )
        act.setEnabled(self.isScaleDownAvailable())

        self.__menu.addAction(
            EricPixmapCache.getIcon("zoomReset"), self.tr("Zoom reset"), self.resetScale
        )

        self.__menu.addSeparator()

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy"), self.copy
        )
        act.setEnabled(bool(selectedText))

        self.__menu.addAction(
            EricPixmapCache.getIcon("editSelectAll"),
            self.tr("Select All"),
            self.selectAll,
        )

        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("tabClose"), self.tr("Close"), self.__closePage
        )

        act = self.__menu.addAction(
            EricPixmapCache.getIcon("tabCloseOther"),
            self.tr("Close Others"),
            self.__closeOtherPages,
        )
        act.setEnabled(self.__helpViewerWidget.openPagesCount() > 1)

        self.__menu.popup(self.mapToGlobal(pos))

    def __createLinkContextMenu(self, menu, linkUrl):
        """
        Private method to populate the context menu for URLs.

        @param menu reference to the menu to be populated
        @type QMenu
        @param linkUrl URL to create the menu part for
        @type QUrl
        """
        if not menu.isEmpty():
            menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("openNewTab"), self.tr("Open Link in New Page")
        )
        act.setData(linkUrl)
        act.triggered.connect(functools.partial(self.__openLinkInNewPage, act))

        act = menu.addAction(
            EricPixmapCache.getIcon("newWindow"),
            self.tr("Open Link in Background Page"),
        )
        act.setData(linkUrl)
        act.triggered.connect(functools.partial(self.__openLinkInBackgroundPage, act))

        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy URL to Clipboard")
        )
        act.setData(linkUrl)
        act.triggered.connect(functools.partial(self.__copyLink, act))

    def __openLinkInNewPage(self, act):
        """
        Private method called by the context menu to open a link in a new page.

        @param act reference to the action that triggered
        @type QAction
        """
        url = act.data()
        if url.isEmpty():
            return

        self.__helpViewerWidget.openUrlNewPage(url)

    def __openLinkInBackgroundPage(self, act):
        """
        Private method called by the context menu to open a link in a
        background page.

        @param act reference to the action that triggered
        @type QAction
        """
        url = act.data()
        if url.isEmpty():
            return

        self.__helpViewerWidget.openUrlNewBackgroundPage(url)

    def __bookmarkPage(self, act):
        """
        Private method called by the context menu to bookmark the page.

        @param act reference to the action that triggered
        @type QAction
        """
        data = act.data()
        if data:
            with contextlib.suppress(KeyError):
                url = data["url"]
                title = data["title"]

                self.__helpViewerWidget.bookmarkPage(title, url)

    def __copyLink(self, act):
        """
        Private method called by the context menu to copy a link to the
        clipboard.

        @param act reference to the action that triggered
        @type QAction
        """
        data = act.data()
        if isinstance(data, QUrl) and data.isEmpty():
            return

        if isinstance(data, QUrl):
            data = data.toString()

        # copy the URL to both clipboard areas
        QGuiApplication.clipboard().setText(data, QClipboard.Mode.Clipboard)
        QGuiApplication.clipboard().setText(data, QClipboard.Mode.Selection)

    def __closePage(self):
        """
        Private method called by the context menu to close the current page.
        """
        self.__helpViewerWidget.closeCurrentPage()

    def __closeOtherPages(self):
        """
        Private method called by the context menu to close all other pages.
        """
        self.__helpViewerWidget.closeOtherPages()
