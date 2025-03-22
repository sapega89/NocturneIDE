# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an UML like class item.
"""

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QGraphicsSimpleTextItem, QStyle

from eric7 import EricUtilities

from .UMLItem import UMLItem, UMLModel


class ClassModel(UMLModel):
    """
    Class implementing the class model.
    """

    def __init__(
        self, name, methods=None, instanceAttributes=None, classAttributes=None
    ):
        """
        Constructor

        @param name the class name
        @type str
        @param methods list of method names of the class
        @type list of str
        @param instanceAttributes list of instance attribute names of the class
        @type list of str
        @param classAttributes list of class attribute names of the class
        @type list of str
        """
        super().__init__(name)

        self.methods = [] if methods is None else methods[:]
        self.instanceAttributes = (
            [] if instanceAttributes is None else instanceAttributes[:]
        )
        self.classAttributes = [] if classAttributes is None else classAttributes[:]

    def addMethod(self, method):
        """
        Public method to add a method to the class model.

        @param method method name to be added
        @type str
        """
        self.methods.append(method)

    def addInstanceAttribute(self, attribute):
        """
        Public method to add an instance attribute to the class model.

        @param attribute instance attribute name to be added
        @type str
        """
        self.instanceAttributes.append(attribute)

    def addClassAttribute(self, attribute):
        """
        Public method to add a class attribute to the class model.

        @param attribute class attribute name to be added
        @type str
        """
        self.classAttributes.append(attribute)

    def getMethods(self):
        """
        Public method to retrieve the methods of the class.

        @return list of class methods
        @rtype list of str
        """
        return self.methods[:]

    def getInstanceAttributes(self):
        """
        Public method to retrieve the attributes of the class.

        @return list of instance attributes
        @rtype list of str
        """
        return self.instanceAttributes[:]

    def getClassAttributes(self):
        """
        Public method to retrieve the global attributes of the class.

        @return list of class attributes
        @rtype list of str
        """
        return self.classAttributes[:]


class ClassItem(UMLItem):
    """
    Class implementing an UML like class item.
    """

    ItemType = "class"

    def __init__(
        self,
        model=None,
        external=False,
        x=0,
        y=0,
        rounded=False,
        noAttrs=False,
        colors=None,
        parent=None,
        scene=None,
    ):
        """
        Constructor

        @param model class model containing the class data
        @type ClassModel
        @param external flag indicating a class defined outside our scope
        @type boolean
        @param x x-coordinate
        @type int
        @param y y-coordinate
        @type int
        @param rounded flag indicating a rounded corner
        @type bool
        @param noAttrs flag indicating, that no attributes should be shown
        @type bool
        @param colors tuple containing the foreground and background colors
        @type tuple of (QColor, QColor)
        @param parent reference to the parent object
        @type QGraphicsItem
        @param scene reference to the scene object
        @type QGraphicsScene
        """
        UMLItem.__init__(self, model, x, y, rounded, colors, parent)

        self.external = external
        self.noAttrs = noAttrs

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
        boldFont.setUnderline(True)

        classAttributes = self.model.getClassAttributes()
        attrs = self.model.getInstanceAttributes()
        meths = self.model.getMethods()

        x = self.margin + int(self.rect().x())
        y = self.margin + int(self.rect().y())
        self.header = QGraphicsSimpleTextItem(self)
        self.header.setBrush(self._colors[0])
        self.header.setFont(boldFont)
        self.header.setText(self.model.getName())
        self.header.setPos(x, y)
        y += int(self.header.boundingRect().height()) + self.margin

        if self.external:
            self.classAttributes = None
        else:
            txt = QCoreApplication.translate("ClassItem", "Class Attributes:\n  ")
            txt += (
                "\n  ".join(classAttributes)
                if globals
                else "  " + QCoreApplication.translate("ClassItem", "none")
            )
            self.classAttributes = QGraphicsSimpleTextItem(self)
            self.classAttributes.setBrush(self._colors[0])
            self.classAttributes.setFont(self.font)
            self.classAttributes.setText(txt)
            self.classAttributes.setPos(x, y)
            y += int(self.classAttributes.boundingRect().height()) + self.margin

        if not self.noAttrs and not self.external:
            txt = QCoreApplication.translate("ClassItem", "Instance Attributes:\n  ")
            txt += (
                "\n  ".join(attrs)
                if attrs
                else "  " + QCoreApplication.translate("ClassItem", "none")
            )
            self.attrs = QGraphicsSimpleTextItem(self)
            self.attrs.setBrush(self._colors[0])
            self.attrs.setFont(self.font)
            self.attrs.setText(txt)
            self.attrs.setPos(x, y)
            y += int(self.attrs.boundingRect().height()) + self.margin
        else:
            self.attrs = None

        if self.external:
            txt = " "
        else:
            txt = QCoreApplication.translate("ClassItem", "Methods:\n  ")
            txt += (
                "\n  ".join(meths)
                if meths
                else "  " + QCoreApplication.translate("ClassItem", "none")
            )
        self.meths = QGraphicsSimpleTextItem(self)
        self.meths.setBrush(self._colors[0])
        self.meths.setFont(self.font)
        self.meths.setText(txt)
        self.meths.setPos(x, y)

    def __calculateSize(self):
        """
        Private method to calculate the size of the class item.
        """
        if self.model is None:
            return

        width = int(self.header.boundingRect().width())
        height = int(self.header.boundingRect().height())
        if self.classAttributes:
            width = max(width, int(self.classAttributes.boundingRect().width()))
            height += int(self.classAttributes.boundingRect().height()) + self.margin
        if self.attrs:
            width = max(width, int(self.attrs.boundingRect().width()))
            height = height + int(self.attrs.boundingRect().height()) + self.margin
        if self.meths:
            width = max(width, int(self.meths.boundingRect().width()))
            height += int(self.meths.boundingRect().height())

        self.setSize(width + 2 * self.margin, height + 2 * self.margin)

    def setModel(self, model):
        """
        Public method to set the class model.

        @param model class model containing the class data
        @type ClassModel
        """
        self.scene().removeItem(self.header)
        self.header = None
        if self.classAttributes:
            self.scene().removeItem(self.classAttributes)
            self.classAttributes = None
        if self.attrs:
            self.scene().removeItem(self.attrs)
            self.attrs = None
        if self.meths:
            self.scene().removeItem(self.meths)
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
        if self.classAttributes:
            y += self.margin + int(self.classAttributes.boundingRect().height())
            painter.drawLine(offsetX, offsetY + y, offsetX + w - 1, offsetY + y)
        if self.attrs:
            y += self.margin + int(self.attrs.boundingRect().height())
            painter.drawLine(offsetX, offsetY + y, offsetX + w - 1, offsetY + y)

        self.adjustAssociations()

    def isExternal(self):
        """
        Public method returning the external state.

        @return external state
        @rtype bool
        """
        return self.external

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
        if len(parts) < 3:
            return False

        name = ""
        instanceAttributes = []
        methods = []
        classAttributes = []

        for part in parts:
            key, value = part.split("=", 1)
            if key == "is_external":
                self.external = EricUtilities.toBool(value.strip())
            elif key == "no_attributes":
                self.noAttrs = EricUtilities.toBool(value.strip())
            elif key == "name":
                name = value.strip()
            elif key == "attributes":
                instanceAttributes = value.strip().split("||")
            elif key == "methods":
                methods = value.strip().split("||")
            elif key == "class_attributes":
                classAttributes = value.strip().split("||")
            else:
                return False

        self.model = ClassModel(name, methods, instanceAttributes, classAttributes)
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
            "is_external": self.external,
            "no_attributes": self.noAttrs,
            "model_name": self.model.getName(),
            "attributes": self.model.getInstanceAttributes(),
            "methods": self.model.getMethods(),
            "class_attributes": self.model.getClassAttributes(),
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
            model = ClassModel(
                data["model_name"],
                data["methods"],
                data["attributes"],
                data["class_attributes"],
            )
            itm = cls(
                model=model,
                external=data["is_external"],
                x=0,
                y=0,
                noAttrs=data["no_attributes"],
                colors=colors,
            )
            itm.setPos(data["x"], data["y"])
            itm.setId(data["id"])
            return itm
        except KeyError:
            return None
