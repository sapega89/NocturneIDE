# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a tool bar populated from a QAbstractItemModel.
"""

from PyQt6.QtCore import QEvent, QModelIndex, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QIcon
from PyQt6.QtWidgets import QApplication, QToolBar, QToolButton


class EricModelToolBar(QToolBar):
    """
    Class implementing a tool bar populated from a QAbstractItemModel.

    @signal activated(QModelIndex) emitted when an action has been triggered
    """

    activated = pyqtSignal(QModelIndex)

    def __init__(self, title=None, parent=None):
        """
        Constructor

        @param title title for the tool bar
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        if title is not None:
            super().__init__(title, parent)
        else:
            super().__init__(parent)

        self.__model = None

        self.__root = QModelIndex()
        self.__dragStartPosition = QPoint()

        if self.isVisible():
            self._build()

        self.setAcceptDrops(True)

        self._mouseButton = Qt.MouseButton.NoButton
        self._keyboardModifiers = Qt.KeyboardModifier.NoModifier
        self.__dropRow = -1
        self.__dropIndex = None

    def setModel(self, model):
        """
        Public method to set the model for the tool bar.

        @param model reference to the model
        @type QAbstractItemModel
        """
        if self.__model is not None:
            self.__model.modelReset.disconnect(self._build)
            self.__model.rowsInserted[QModelIndex, int, int].disconnect(self._build)
            self.__model.rowsRemoved[QModelIndex, int, int].disconnect(self._build)
            self.__model.dataChanged.disconnect(self._build)

        self.__model = model

        if self.__model is not None:
            self.__model.modelReset.connect(self._build)
            self.__model.rowsInserted[QModelIndex, int, int].connect(self._build)
            self.__model.rowsRemoved[QModelIndex, int, int].connect(self._build)
            self.__model.dataChanged.connect(self._build)

    def model(self):
        """
        Public method to get a reference to the model.

        @return reference to the model
        @rtype QAbstractItemModel
        """
        return self.__model

    def setRootIndex(self, idx):
        """
        Public method to set the root index.

        @param idx index to be set as the root index
        @type QModelIndex
        """
        self.__root = idx

    def rootIndex(self):
        """
        Public method to get the root index.

        @return root index
        @rtype QModelIndex
        """
        return self.__root

    def _build(self):
        """
        Protected slot to build the tool bar.
        """
        if self.__model is None:
            return

        self.clear()

        for i in range(self.__model.rowCount(self.__root)):
            idx = self.__model.index(i, 0, self.__root)

            title = idx.data(Qt.ItemDataRole.DisplayRole)
            icon = idx.data(Qt.ItemDataRole.DecorationRole)
            if icon == NotImplemented or icon is None:
                icon = QIcon()
            folder = self.__model.hasChildren(idx)

            act = self.addAction(icon, title)
            act.setData(idx)

            button = self.widgetForAction(act)
            button.installEventFilter(self)

            if folder:
                menu = self._createMenu()
                menu.setModel(self.__model)
                menu.setRootIndex(idx)
                button.setMenu(menu)
                button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
                button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

    def index(self, action):
        """
        Public method to get the index of an action.

        @param action reference to the action to get the index for
        @type QAction
        @return index of the action
        @rtype QModelIndex
        """
        if action is None:
            return QModelIndex()

        idx = action.data()
        if idx is None:
            return QModelIndex()

        if not isinstance(idx, QModelIndex):
            return QModelIndex()

        return idx

    def _createMenu(self):
        """
        Protected method to create the menu for a tool bar action.

        @return menu for a tool bar action
        @rtype EricModelMenu
        """
        from .EricModelMenu import EricModelMenu

        return EricModelMenu(self)

    def eventFilter(self, obj, evt):
        """
        Public method to handle event for other objects.

        @param obj reference to the object
        @type QObject
        @param evt reference to the event
        @type QEvent
        @return flag indicating that the event should be filtered out
        @rtype bool
        """
        if evt.type() == QEvent.Type.MouseButtonRelease:
            self._mouseButton = evt.button()
            self._keyboardModifiers = evt.modifiers()
            act = obj.defaultAction()
            idx = self.index(act)
            if idx.isValid():
                self.activated[QModelIndex].emit(idx)
        elif (
            evt.type() == QEvent.Type.MouseButtonPress
            and evt.buttons() & Qt.MouseButton.LeftButton
        ):
            self.__dragStartPosition = self.mapFromGlobal(
                evt.globalPosition().toPoint()
            )

        return False

    def dragEnterEvent(self, evt):
        """
        Protected method to handle drag enter events.

        @param evt reference to the event
        @type QDragEnterEvent
        """
        if self.__model is not None:
            mimeTypes = self.__model.mimeTypes()
            for mimeType in mimeTypes:
                if evt.mimeData().hasFormat(mimeType):
                    evt.acceptProposedAction()

        super().dragEnterEvent(evt)

    def dropEvent(self, evt):
        """
        Protected method to handle drop events.

        @param evt reference to the event
        @type QDropEvent
        @exception RuntimeError raised to indicate an invalid model index
        """
        if self.__model is not None:
            act = self.actionAt(evt.position().toPoint())
            parentIndex = self.__root
            if act is None:
                row = self.__model.rowCount(self.__root)
            else:
                idx = self.index(act)
                if not idx.isValid():
                    raise RuntimeError("invalid index")
                row = idx.row()
                if self.__model.hasChildren(idx):
                    parentIndex = idx
                    row = self.__model.rowCount(idx)

            self.__dropRow = row
            self.__dropIndex = parentIndex
            evt.acceptProposedAction()
            self.__model.dropMimeData(
                evt.mimeData(), evt.dropAction(), row, 0, parentIndex
            )

        super().dropEvent(evt)

    def mouseMoveEvent(self, evt):
        """
        Protected method to handle mouse move events.

        @param evt reference to the event
        @type QMouseEvent
        @exception RuntimeError raised to indicate an invalid model index
        """
        if self.__model is None:
            super().mouseMoveEvent(evt)
            return

        if not (evt.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(evt)
            return

        manhattanLength = (
            evt.position().toPoint() - self.__dragStartPosition
        ).manhattanLength()
        if manhattanLength <= QApplication.startDragDistance():
            super().mouseMoveEvent(evt)
            return

        act = self.actionAt(self.__dragStartPosition)
        if act is None:
            super().mouseMoveEvent(evt)
            return

        idx = self.index(act)
        if not idx.isValid():
            raise RuntimeError("invalid index")

        drag = QDrag(self)
        drag.setMimeData(self.__model.mimeData([idx]))
        actionRect = self.actionGeometry(act)
        drag.setPixmap(self.grab(actionRect))

        if drag.exec() == Qt.DropAction.MoveAction:
            row = idx.row()
            if self.__dropIndex == idx.parent() and self.__dropRow <= row:
                row += 1
            self.__model.removeRow(row, self.__root)

    def hideEvent(self, evt):
        """
        Protected method to handle hide events.

        @param evt reference to the hide event
        @type QHideEvent
        """
        self.clear()
        super().hideEvent(evt)

    def showEvent(self, evt):
        """
        Protected method to handle show events.

        @param evt reference to the hide event
        @type QHideEvent
        """
        if len(self.actions()) == 0:
            self._build()
        super().showEvent(evt)

    def resetFlags(self):
        """
        Public method to reset the saved internal state.
        """
        self._mouseButton = Qt.MouseButton.NoButton
        self._keyboardModifiers = Qt.KeyboardModifier.NoModifier
