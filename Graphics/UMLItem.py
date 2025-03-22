# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the UMLItem base class.
"""

from PyQt6.QtCore import QSizeF, Qt
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QStyle

from eric7 import Preferences


class UMLModel:
    """
    Class implementing the UMLModel base class.
    """

    def __init__(self, name):
        """
        Constructor

        @param name package name
        @type str
        """
        self.name = name

    def getName(self):
        """
        Public method to retrieve the model name.

        @return model name
        @rtype str
        """
        return self.name


class UMLItem(QGraphicsRectItem):
    """
    Class implementing the UMLItem base class.
    """

    ItemType = "UMLItem"

    def __init__(self, model=None, x=0, y=0, rounded=False, colors=None, parent=None):
        """
        Constructor

        @param model UML model containing the item data
        @type UMLModel
        @param x x-coordinate
        @type int
        @param y y-coordinate
        @type int
        @param rounded flag indicating a rounded corner
        @type bool
        @param colors tuple containing the foreground and background colors
        @type tuple of (QColor, QColor)
        @param parent reference to the parent object
        @type QGraphicsItem
        """
        super().__init__(parent)
        self.model = model

        if colors is None:
            self._colors = (QColor(Qt.GlobalColor.black), QColor(Qt.GlobalColor.white))
        else:
            self._colors = colors
        self.setPen(QPen(self._colors[0]))

        self.font = Preferences.getGraphics("Font")
        self.margin = 5
        self.associations = []
        self.shouldAdjustAssociations = False
        self.__id = -1

        self.setRect(x, y, 60, 30)

        if rounded:
            p = self.pen()
            p.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def getName(self):
        """
        Public method to retrieve the item name.

        @return item name
        @rtype str
        """
        if self.model:
            return self.model.name
        else:
            return ""

    def setSize(self, width, height):
        """
        Public method to set the rectangles size.

        @param width width of the rectangle
        @type float
        @param height height of the rectangle
        @type float
        """
        rect = self.rect()
        rect.setSize(QSizeF(width, height))
        self.setRect(rect)

    def addAssociation(self, assoc):
        """
        Public method to add an association to this widget.

        @param assoc association to be added
        @type AssociationWidget
        """
        if assoc and assoc not in self.associations:
            self.associations.append(assoc)

    def removeAssociation(self, assoc):
        """
        Public method to remove an association to this widget.

        @param assoc association to be removed
        @type AssociationWidget
        """
        if assoc and assoc in self.associations:
            self.associations.remove(assoc)

    def removeAssociations(self):
        """
        Public method to remove all associations of this widget.
        """
        for assoc in self.associations[:]:
            assoc.unassociate()
            assoc.hide()
            del assoc

    def adjustAssociations(self):
        """
        Public method to adjust the associations to widget movements.
        """
        if self.shouldAdjustAssociations:
            for assoc in self.associations:
                assoc.widgetMoved()
            self.shouldAdjustAssociations = False

    def moveBy(self, dx, dy):
        """
        Public overriden method to move the widget relative.

        @param dx relative movement in x-direction
        @type float
        @param dy relative movement in y-direction
        @type float
        """
        super().moveBy(dx, dy)
        self.adjustAssociations()

    def setPos(self, x, y):
        """
        Public overriden method to set the items position.

        @param x absolute x-position
        @type float
        @param y absolute y-position
        @type float
        """
        super().setPos(x, y)
        self.adjustAssociations()

    def itemChange(self, change, value):
        """
        Public method called when an items state changes.

        @param change the item's change
        @type QGraphicsItem.GraphicsItemChange
        @param value the value of the change
        @type Any
        @return adjusted values
        @rtype Any
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # 1. remember to adjust associations
            self.shouldAdjustAssociations = True

            # 2. ensure the new position is inside the scene
            scene = self.scene()
            if scene:
                rect = scene.sceneRect()
                if not rect.contains(value):
                    # keep the item inside the scene
                    value.setX(min(rect.right(), max(value.x(), rect.left())))
                    value.setY(min(rect.bottom(), max(value.y(), rect.top())))
                    return value

        return QGraphicsItem.itemChange(self, change, value)

    def paint(self, painter, option, _widget=None):
        """
        Public method to paint the item in local coordinates.

        @param painter reference to the painter object
        @type QPainter
        @param option style options
        @type QStyleOptionGraphicsItem
        @param _widget optional reference to the widget painted on (unused)
        @type QWidget
        """
        pen = self.pen()
        if (
            option.state & QStyle.StateFlag.State_Selected
        ) == QStyle.StateFlag.State_Selected:
            pen.setWidth(2)
        else:
            pen.setWidth(1)

        painter.setPen(pen)
        painter.setBrush(self.brush())
        painter.drawRect(self.rect())
        self.adjustAssociations()

    def setId(self, itemId):
        """
        Public method to assign an ID to the item.

        @param itemId assigned ID
        @type int
        """
        self.__id = itemId

    def getId(self):
        """
        Public method to get the item ID.

        @return ID of the item
        @rtype int
        """
        return self.__id

    def getItemType(self):
        """
        Public method to get the item's type.

        @return item type
        @rtype str
        """
        return self.ItemType

    def parseItemDataString(self, _version, _data):
        """
        Public method to parse the given persistence data.

        @param _version version of the data (unused)
        @type str
        @param _data persisted data to be parsed (unused)
        @type str
        @return flag indicating success
        @rtype bool
        """
        return True

    def toDict(self):
        """
        Public method to collect data to be persisted.

        @return dictionary containing data to be persisted
        @rtype dict
        """
        return {
            "id": self.getId(),
            "x": self.x(),
            "y": self.y(),
            "type": self.getItemType(),
            "model_name": self.model.getName(),
        }

    @classmethod
    def fromDict(cls, data, colors=None):
        """
        Class method to create a generic UML item from persisted data.

        @param data dictionary containing the persisted data as generated
            by toDict()
        @type dict
        @param colors tuple containing the foreground and background colors
        @type tuple of (QColor, QColor)
        @return created UML item
        @rtype UMLItem
        """
        try:
            model = UMLModel(data["model_name"])
            itm = cls(model=model, x=0, y=0, colors=colors)
            itm.setPos(data["x"], data["y"])
            itm.setId(data["id"])
            return itm
        except KeyError:
            return None
