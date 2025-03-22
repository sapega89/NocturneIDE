# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a package item.
"""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGraphicsSimpleTextItem, QStyle

from eric7 import EricUtilities

from .UMLItem import UMLItem, UMLModel


class PackageModel(UMLModel):
    """
    Class implementing the package model.
    """

    def __init__(self, name, moduleslist=None):
        """
        Constructor

        @param name package name
        @type str
        @param moduleslist list of module names
        @type list of str
        """
        super().__init__(name)

        self.moduleslist = [] if moduleslist is None else moduleslist[:]

    def addModule(self, modulename):
        """
        Public method to add a module to the package model.

        @param modulename module name to be added
        @type str
        """
        self.moduleslist.append(modulename)

    def getModules(self):
        """
        Public method to retrieve the modules of the package.

        @return list of module names
        @rtype list of str
        """
        return self.moduleslist[:]


class PackageItem(UMLItem):
    """
    Class implementing a package item.
    """

    ItemType = "package"

    def __init__(
        self,
        model=None,
        x=0,
        y=0,
        rounded=False,
        noModules=False,
        colors=None,
        parent=None,
        scene=None,
    ):
        """
        Constructor

        @param model package model containing the package data
        @type PackageModel
        @param x x-coordinate
        @type int
        @param y y-coordinate
        @type int
        @param rounded flag indicating a rounded corner
        @type bool
        @param noModules flag indicating, that no module names should be
            shown
        @type bool
        @param colors tuple containing the foreground and background colors
        @type tuple of (QColor, QColor)
        @param parent reference to the parent object
        @type QGraphicsItem
        @param scene reference to the scene object
        @type QGraphicsScene
        """
        UMLItem.__init__(self, model, x, y, rounded, colors, parent)
        self.noModules = noModules

        if scene:
            scene.addItem(self)

        if self.model:
            self.__createTexts()
            self.__calculateSize()

    def __createTexts(self):
        """
        Private method to create the text items of the class item.
        """
        if self.model is None:
            return

        boldFont = QFont(self.font)
        boldFont.setBold(True)

        modules = self.model.getModules()

        x = self.margin + int(self.rect().x())
        y = self.margin + int(self.rect().y())
        self.header = QGraphicsSimpleTextItem(self)
        self.header.setBrush(self._colors[0])
        self.header.setFont(boldFont)
        self.header.setText(self.model.getName())
        self.header.setPos(x, y)
        y += int(self.header.boundingRect().height()) + self.margin

        if not self.noModules:
            if modules:
                txt = "\n".join(modules)
            else:
                txt = " "
            self.modules = QGraphicsSimpleTextItem(self)
            self.modules.setBrush(self._colors[0])
            self.modules.setFont(self.font)
            self.modules.setText(txt)
            self.modules.setPos(x, y)
        else:
            self.modules = None

    def __calculateSize(self):
        """
        Private method to calculate the size of the package widget.
        """
        if self.model is None:
            return

        width = int(self.header.boundingRect().width())
        height = int(self.header.boundingRect().height())
        if self.modules:
            width = max(width, int(self.modules.boundingRect().width()))
            height += int(self.modules.boundingRect().height())
        latchW = width / 3.0
        latchH = min(15.0, latchW)
        self.setSize(width + 2 * self.margin, height + latchH + 2 * self.margin)

        x = self.margin + int(self.rect().x())
        y = self.margin + int(self.rect().y()) + latchH
        self.header.setPos(x, y)
        y += int(self.header.boundingRect().height()) + self.margin
        if self.modules:
            self.modules.setPos(x, y)

    def setModel(self, model):
        """
        Public method to set the package model.

        @param model package model containing the package data
        @type PackageModel
        """
        self.scene().removeItem(self.header)
        self.header = None
        if self.modules:
            self.scene().removeItem(self.modules)
            self.modules = None
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

        offsetX = int(self.rect().x())
        offsetY = int(self.rect().y())
        w = int(self.rect().width())
        latchW = w / 3.0
        latchH = min(15.0, latchW)
        h = int(self.rect().height() - latchH + 1)

        painter.setPen(pen)
        painter.setBrush(self.brush())
        painter.setFont(self.font)

        painter.drawRect(offsetX, offsetY, int(latchW), int(latchH))
        painter.drawRect(offsetX, offsetY + int(latchH), w, h)
        y = int(self.margin + self.header.boundingRect().height() + latchH)
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
        if len(parts) < 2:
            return False

        name = ""
        modules = []

        for part in parts:
            key, value = part.split("=", 1)
            if key == "no_modules":
                self.external = EricUtilities.toBool(value.strip())
            elif key == "name":
                name = value.strip()
            elif key == "modules":
                modules = value.strip().split("||")
            else:
                return False

        self.model = PackageModel(name, modules)
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
            "no_nodules": self.noModules,
            "modules": self.model.getModules(),
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
            model = PackageModel(data["model_name"], data["modules"])
            itm = cls(model, x=0, y=0, noModules=data["no_nodules"], colors=colors)
            itm.setPos(data["x"], data["y"])
            itm.setId(data["id"])
            return itm
        except KeyError:
            return None
