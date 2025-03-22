# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a module item.
"""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGraphicsSimpleTextItem, QStyle

from .UMLItem import UMLItem, UMLModel


class ModuleModel(UMLModel):
    """
    Class implementing the module model.
    """

    def __init__(self, name, classlist=None):
        """
        Constructor

        @param name the module name
        @type str
        @param classlist list of class names
        @type list of str
        """
        super().__init__(name)

        self.classlist = [] if classlist is None else classlist[:]

    def addClass(self, classname):
        """
        Public method to add a class to the module model.

        @param classname class name to be added
        @type str
        """
        self.classlist.append(classname)

    def getClasses(self):
        """
        Public method to retrieve the classes of the module.

        @return list of class names
        @rtype list of str
        """
        return self.classlist[:]


class ModuleItem(UMLItem):
    """
    Class implementing a module item.
    """

    ItemType = "module"

    def __init__(
        self, model=None, x=0, y=0, rounded=False, colors=None, parent=None, scene=None
    ):
        """
        Constructor

        @param model module model containing the module data
        @type ModuleModel
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
        @param scene reference to the scene object
        @type QGraphicsScene
        """
        UMLItem.__init__(self, model, x, y, rounded, colors, parent)

        if scene:
            scene.addItem(self)

        if self.model:
            self.__createTexts()
            self.__calculateSize()

    def __createTexts(self):
        """
        Private method to create the text items of the module item.
        """
        if self.model is None:
            return

        boldFont = QFont(self.font)
        boldFont.setBold(True)

        classes = self.model.getClasses()

        x = self.margin + int(self.rect().x())
        y = self.margin + int(self.rect().y())
        self.header = QGraphicsSimpleTextItem(self)
        self.header.setBrush(self._colors[0])
        self.header.setFont(boldFont)
        self.header.setText(self.model.getName())
        self.header.setPos(x, y)
        y += int(self.header.boundingRect().height()) + self.margin
        txt = "\n".join(classes) if classes else " "
        self.classes = QGraphicsSimpleTextItem(self)
        self.classes.setBrush(self._colors[0])
        self.classes.setFont(self.font)
        self.classes.setText(txt)
        self.classes.setPos(x, y)

    def __calculateSize(self):
        """
        Private method to calculate the size of the module item.
        """
        if self.model is None:
            return

        width = int(self.header.boundingRect().width())
        height = int(self.header.boundingRect().height())
        if self.classes:
            width = max(width, int(self.classes.boundingRect().width()))
            height += int(self.classes.boundingRect().height())
        self.setSize(width + 2 * self.margin, height + 2 * self.margin)

    def setModel(self, model):
        """
        Public method to set the module model.

        @param model module model containing the module data
        @type ModuleModel
        """
        self.scene().removeItem(self.header)
        self.header = None
        if self.classes:
            self.scene().removeItem(self.classes)
            self.meths = None
        self.model = model
        self.__createTexts()
        self.__calculateSize()

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
        painter.setFont(self.font)

        offsetX = int(self.rect().x())
        offsetY = int(self.rect().y())
        w = int(self.rect().width())
        h = int(self.rect().height())

        painter.drawRect(offsetX, offsetY, w, h)
        y = self.margin + int(self.header.boundingRect().height())
        painter.drawLine(offsetX, offsetY + y, offsetX + w - 1, offsetY + y)

        self.adjustAssociations()

    def parseItemDataString(self, _version, data):
        """
        Public method to parse the given persistence data.

        @param _version version of the data (unused)
        @type str
        @param data persisted data to be parsed
        @type str
        @return flag indicating success
        @rtype bool
        """
        parts = data.split(", ")
        if len(parts) < 1:
            return False

        name = ""
        classes = []

        for part in parts:
            key, value = part.split("=", 1)
            if key == "name":
                name = value.strip()
            elif key == "classes":
                classes = value.strip().split("||")
            else:
                return False

        self.model = ModuleModel(name, classes)
        self.__createTexts()
        self.__calculateSize()

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
            "classes": self.model.getClasses(),
        }

    @classmethod
    def fromDict(cls, data, colors=None):
        """
        Class method to create a class item from persisted data.

        @param data dictionary containing the persisted data as generated
            by toDict()
        @type dict
        @param colors tuple containing the foreground and background colors
        @type tuple of (QColor, QColor)
        @return created class item
        @rtype ClassItem
        """
        try:
            model = ModuleModel(data["model_name"], data["classes"])
            itm = cls(model, x=0, y=0, colors=colors)
            itm.setPos(data["x"], data["y"])
            itm.setId(data["id"])
            return itm
        except KeyError:
            return None
