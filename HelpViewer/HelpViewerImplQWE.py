# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the help viewer base class.
"""

import contextlib
import functools

from PyQt6.QtCore import QEvent, QPoint, Qt, QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtWebEngineCore import QWebEngineNewWindowRequest, QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricTextEditSearchWidget import EricTextEditType

from .HelpViewerImpl import HelpViewerImpl
from .HelpViewerWidget import HelpViewerWidget


class HelpViewerImplQWE(HelpViewerImpl, QWebEngineView):
    """
    Class implementing the QTextBrowser based help viewer class.
    """

    ZoomLevels = [
        30,
        40,
        50,
        67,
        80,
        90,
        100,
        110,
        120,
        133,
        150,
        170,
        200,
        220,
        233,
        250,
        270,
        285,
        300,
    ]
    ZoomLevelDefault = 100

    def __init__(self, engine, parent=None):
        """
        Constructor

        @param engine reference to the help engine
        @type QHelpEngine
        @param parent reference to the parent widget
        @type QWidget
        """
        QWebEngineView.__init__(self, parent=parent)
        HelpViewerImpl.__init__(self, engine, EricTextEditType.QWEBENGINEVIEW)

        self.__helpViewerWidget = parent

        self.__rwhvqt = None
        self.installEventFilter(self)

        self.__page = None
        self.__createNewPage()

        self.__currentScale = 100

        self.__menu = QMenu(self)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)

    def __createNewPage(self):
        """
        Private method to create a new page object.
        """
        self.__page = QWebEnginePage(self.__helpViewerWidget.webProfile())
        self.setPage(self.__page)

        self.__page.titleChanged.connect(self.__titleChanged)
        self.__page.urlChanged.connect(self.__titleChanged)
        self.__page.newWindowRequested.connect(self.__newWindowRequested)

    def __newWindowRequested(self, request):
        """
        Private slot handling new window requests of the web page.

        @param request reference to the new window request
        @type QWebEngineNewWindowRequest
        """
        background = (
            request.destination()
            == QWebEngineNewWindowRequest.DestinationType.InNewBackgroundTab
        )
        newViewer = self.__helpViewerWidget.addPage(background=background)
        request.openIn(newViewer.page())

    def __setRwhvqt(self):
        """
        Private slot to set widget that receives input events.
        """
        self.grabGesture(Qt.GestureType.PinchGesture)
        self.__rwhvqt = self.focusProxy()
        if self.__rwhvqt:
            self.__rwhvqt.grabGesture(Qt.GestureType.PinchGesture)
            self.__rwhvqt.installEventFilter(self)
        else:
            print("Focus proxy is null!")  # __IGNORE_WARNING_M801__

    def setLink(self, url):
        """
        Public method to set the URL of the document to be shown.

        @param url URL of the document
        @type QUrl
        """
        if url.toString() == "about:blank":
            self.setHtml(self.__helpViewerWidget.emptyDocument())
        else:
            super().setUrl(url)

    def link(self):
        """
        Public method to get the URL of the shown document.

        @return url URL of the document
        @rtype QUrl
        """
        return super().url()

    @pyqtSlot()
    def __titleChanged(self):
        """
        Private method to handle a change of the web page title.
        """
        super().titleChanged.emit()

    def pageTitle(self):
        """
        Public method get the page title.

        @return page title
        @rtype str
        """
        titleStr = super().title()
        if not titleStr:
            if self.link().isEmpty():
                url = self.__page.requestedUrl()
            else:
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

    #######################################################################
    ## History related methods below
    #######################################################################

    def isBackwardAvailable(self):
        """
        Public method to check, if stepping backward through the history is
        available.

        @return flag indicating backward stepping is available
        @rtype bool
        """
        return self.history().canGoBack()

    def isForwardAvailable(self):
        """
        Public method to check, if stepping forward through the history is
        available.

        @return flag indicating forward stepping is available
        @rtype bool
        """
        return self.history().canGoForward()

    def backward(self):
        """
        Public slot to move backwards in history.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Back)

    def forward(self):
        """
        Public slot to move forward in history.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Forward)

    def reload(self):
        """
        Public slot to reload the current page.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Reload)

    def backwardHistoryCount(self):
        """
        Public method to get the number of available back history items.

        Note: For performance reasons this is limited to the maximum number of
        history items the help viewer is interested in.

        @return count of available back history items
        @rtype int
        """
        history = self.history()
        return len(history.backItems(HelpViewerWidget.MaxHistoryItems))

    def forwardHistoryCount(self):
        """
        Public method to get the number of available forward history items.

        Note: For performance reasons this is limited to the maximum number of
        history items the help viewer is interested in.

        @return count of available forward history items
        @rtype int
        """
        history = self.history()
        return len(history.forwardItems(HelpViewerWidget.MaxHistoryItems))

    def historyTitle(self, offset):
        """
        Public method to get the title of a history item.

        @param offset offset of the item with respect to the current page
        @type int
        @return title of the requeted item in history
        @rtype str
        """
        history = self.history()
        currentIndex = history.currentItemIndex()
        itm = self.history().itemAt(currentIndex + offset)
        return itm.title()

    def gotoHistory(self, offset):
        """
        Public method to go to a history item.

        @param offset offset of the item with respect to the current page
        @type int
        """
        history = self.history()
        currentIndex = history.currentItemIndex()
        itm = self.history().itemAt(currentIndex + offset)
        history.goToItem(itm)

    def clearHistory(self):
        """
        Public method to clear the history.
        """
        self.history().clear()

    #######################################################################
    ## Zoom related methods below
    #######################################################################

    def __levelForScale(self, scale):
        """
        Private method determining the zoom level index given a zoom factor.

        @param scale zoom factor
        @type int
        @return index of zoom factor
        @rtype int
        """
        try:
            index = self.ZoomLevels.index(scale)
        except ValueError:
            for _index in range(len(self.ZoomLevels)):
                if scale <= self.ZoomLevels[scale]:
                    break
        return index

    def scaleUp(self):
        """
        Public method to zoom in.
        """
        index = self.__levelForScale(self.__currentScale)
        if index < len(self.ZoomLevels) - 1:
            self.setScale(self.ZoomLevels[index + 1])

    def scaleDown(self):
        """
        Public method to zoom out.
        """
        index = self.__levelForScale(self.__currentScale)
        if index > 0:
            self.setScale(self.ZoomLevels[index - 1])

    def setScale(self, scale):
        """
        Public method to set the zoom level.

        @param scale zoom level to set
        @type int
        """
        if scale != self.__currentScale:
            self.setZoomFactor(scale / 100.0)
            self.__currentScale = scale
            self.zoomChanged.emit()

    def resetScale(self):
        """
        Public method to reset the zoom level.
        """
        index = self.__levelForScale(self.ZoomLevelDefault)
        self.setScale(self.ZoomLevels[index])

    def scale(self):
        """
        Public method to get the zoom level.

        @return current zoom level
        @rtype int
        """
        return self.__currentScale

    def isScaleUpAvailable(self):
        """
        Public method to check, if the max. zoom level is reached.

        @return flag indicating scale up is available
        @rtype bool
        """
        index = self.__levelForScale(self.__currentScale)
        return index < len(self.ZoomLevels) - 1

    def isScaleDownAvailable(self):
        """
        Public method to check, if the min. zoom level is reached.

        @return flag indicating scale down is available
        @rtype bool
        """
        index = self.__levelForScale(self.__currentScale)
        return index > 0

    #######################################################################
    ## Event handlers below
    #######################################################################

    def eventFilter(self, obj, evt):
        """
        Public method to process event for other objects.

        @param obj reference to object to process events for
        @type QObject
        @param evt reference to event to be processed
        @type QEvent
        @return flag indicating that the event should be filtered out
        @rtype bool
        """
        if (
            obj is self
            and evt.type() == QEvent.Type.ParentChange
            and self.parentWidget() is not None
        ):
            self.parentWidget().installEventFilter(self)

        # find the render widget receiving events for the web page
        if obj is self and evt.type() == QEvent.Type.ChildAdded:
            QTimer.singleShot(0, self.__setRwhvqt)

        # forward events to WebBrowserView
        if obj is self.__rwhvqt and evt.type() in [
            QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.Wheel,
            QEvent.Type.Gesture,
        ]:
            wasAccepted = evt.isAccepted()
            evt.setAccepted(False)
            if evt.type() == QEvent.Type.KeyPress:
                self._keyPressEvent(evt)
            elif evt.type() == QEvent.Type.MouseButtonRelease:
                self._mouseReleaseEvent(evt)
            elif evt.type() == QEvent.Type.Wheel:
                self._wheelEvent(evt)
            elif evt.type() == QEvent.Type.Gesture:
                self._gestureEvent(evt)
            ret = evt.isAccepted()
            evt.setAccepted(wasAccepted)
            return ret

        if obj is self.parentWidget() and evt.type() in [
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
        ]:
            wasAccepted = evt.isAccepted()
            evt.setAccepted(False)
            if evt.type() == QEvent.Type.KeyPress:
                self._keyPressEvent(evt)
            ret = evt.isAccepted()
            evt.setAccepted(wasAccepted)
            return ret

        # block already handled events
        if obj is self and evt.type() in [
            QEvent.Type.KeyPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.Wheel,
            QEvent.Type.Gesture,
        ]:
            return True

        return super().eventFilter(obj, evt)

    def _keyPressEvent(self, evt):
        """
        Protected method called by a key press.

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
        elif key == Qt.Key.Key_Escape:
            self.findText("")

    def _mouseReleaseEvent(self, evt):
        """
        Protected method called by a mouse release event.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        accepted = evt.isAccepted()
        self.__page.event(evt)
        if not evt.isAccepted() and evt.button() == Qt.MouseButton.MiddleButton:
            url = QUrl(QGuiApplication.clipboard().text(QClipboard.Mode.Selection))
            if not url.isEmpty() and url.isValid() and url.scheme() != "":
                self.setLink(url)
                accepted = True
        evt.setAccepted(accepted)

    def _wheelEvent(self, evt):
        """
        Protected method to handle wheel events.

        @param evt reference to the wheel event
        @type QWheelEvent
        """
        delta = evt.angleDelta().y()
        if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if delta < 0:
                self.scaleDown()
            elif delta > 0:
                self.scaleUp()
            evt.accept()

        elif evt.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if delta < 0:
                self.backward()
            elif delta > 0:
                self.forward()
            evt.accept()

    def _gestureEvent(self, evt):
        """
        Protected method handling gesture events.

        @param evt reference to the gesture event
        @type QGestureEvent
        """
        pinch = evt.gesture(Qt.GestureType.PinchGesture)
        if pinch:
            if pinch.state() == Qt.GestureState.GestureStarted:
                pinch.setTotalScaleFactor(self.__currentScale / 100.0)
            elif pinch.state() == Qt.GestureState.GestureUpdated:
                scaleFactor = pinch.totalScaleFactor()
                self.setScale(int(scaleFactor * 100))
            evt.accept()

    def event(self, evt):
        """
        Public method handling events.

        @param evt reference to the event
        @type QEvent
        @return flag indicating, if the event was handled
        @rtype bool
        """
        if evt.type() == QEvent.Type.Gesture:
            self._gestureEvent(evt)
            return True

        return super().event(evt)

    #######################################################################
    ## Context menu related methods below
    #######################################################################

    @pyqtSlot(QPoint)
    def __showContextMenu(self, pos):
        """
        Private slot to show a context menu.

        @param pos position for the context menu
        @type QPoint
        """
        self.__menu.clear()

        self.__createContextMenu(self.__menu)

        if not self.__menu.isEmpty():
            self.__menu.popup(self.mapToGlobal(pos))

    def __createContextMenu(self, menu):
        """
        Private method to populate the context menu.

        @param menu reference to the menu to be populated
        @type QMenu
        """
        contextMenuData = self.lastContextMenuRequest()

        act = menu.addAction(
            EricPixmapCache.getIcon("back"), self.tr("Backward"), self.backward
        )
        act.setEnabled(self.isBackwardAvailable())

        act = menu.addAction(
            EricPixmapCache.getIcon("forward"), self.tr("Forward"), self.forward
        )
        act.setEnabled(self.isForwardAvailable())

        act = menu.addAction(
            EricPixmapCache.getIcon("reload"), self.tr("Reload"), self.reload
        )

        if (
            not contextMenuData.linkUrl().isEmpty()
            and contextMenuData.linkUrl().scheme() != "javascript"
        ):
            self.__createLinkContextMenu(menu, contextMenuData)

        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy Page URL to Clipboard")
        )
        act.setData(self.link())
        act.triggered.connect(functools.partial(self.__copyLink, act))

        act = menu.addAction(
            EricPixmapCache.getIcon("bookmark22"), self.tr("Bookmark Page")
        )
        act.setData({"title": self.pageTitle(), "url": self.link()})
        act.triggered.connect(functools.partial(self.__bookmarkPage, act))

        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("zoomIn"), self.tr("Zoom in"), self.scaleUp
        )
        act.setEnabled(self.isScaleUpAvailable())

        act = menu.addAction(
            EricPixmapCache.getIcon("zoomOut"), self.tr("Zoom out"), self.scaleDown
        )
        act.setEnabled(self.isScaleDownAvailable())

        menu.addAction(
            EricPixmapCache.getIcon("zoomReset"), self.tr("Zoom reset"), self.resetScale
        )

        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy"), self.__copyText
        )
        act.setEnabled(bool(contextMenuData.selectedText()))

        menu.addAction(
            EricPixmapCache.getIcon("editSelectAll"),
            self.tr("Select All"),
            self.__selectAll,
        )

        menu.addSeparator()

        menu.addAction(
            EricPixmapCache.getIcon("tabClose"), self.tr("Close"), self.__closePage
        )

        act = menu.addAction(
            EricPixmapCache.getIcon("tabCloseOther"),
            self.tr("Close Others"),
            self.__closeOtherPages,
        )
        act.setEnabled(self.__helpViewerWidget.openPagesCount() > 1)

    def __createLinkContextMenu(self, menu, contextMenuData):
        """
        Private method to populate the context menu for URLs.

        @param menu reference to the menu to be populated
        @type QMenu
        @param contextMenuData data of the last context menu request
        @type QWebEngineContextMenuRequest
        """
        if not menu.isEmpty():
            menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("openNewTab"), self.tr("Open Link in New Page")
        )
        act.setData(contextMenuData.linkUrl())
        act.triggered.connect(functools.partial(self.__openLinkInNewPage, act))

        act = menu.addAction(
            EricPixmapCache.getIcon("newWindow"),
            self.tr("Open Link in Background Page"),
        )
        act.setData(contextMenuData.linkUrl())
        act.triggered.connect(functools.partial(self.__openLinkInBackgroundPage, act))

        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy URL to Clipboard")
        )
        act.setData(contextMenuData.linkUrl())
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

    def __copyText(self):
        """
        Private method called by the context menu to copy selected text to the
        clipboard.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Copy)

    def __selectAll(self):
        """
        Private method called by the context menu to select all text.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.SelectAll)

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
