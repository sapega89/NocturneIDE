# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing a UML like class diagram.
"""

import os

from itertools import zip_longest

from PyQt6.QtWidgets import QGraphicsTextItem

from eric7 import EricUtilities, Preferences
from eric7.SystemUtilities import FileSystemUtilities

from .UMLDiagramBuilder import UMLDiagramBuilder


class UMLClassDiagramBuilder(UMLDiagramBuilder):
    """
    Class implementing a builder for UML like class diagrams.
    """

    def __init__(self, dialog, view, project, file, noAttrs=False):
        """
        Constructor

        @param dialog reference to the UML dialog
        @type UMLDialog
        @param view reference to the view object
        @type UMLGraphicsView
        @param project reference to the project object
        @type Project
        @param file file name of a python module to be shown
        @type str
        @param noAttrs flag indicating, that no attributes should be shown
        @type bool
        """
        super().__init__(dialog, view, project)
        self.setObjectName("UMLClassDiagramBuilder")

        self.file = file
        self.noAttrs = noAttrs

        self.__relFile = (
            self.project.getRelativePath(self.file)
            if self.project.isProjectCategory(self.file, "SOURCES")
            else ""
        )

    def initialize(self):
        """
        Public method to initialize the object.
        """
        pname = self.project.getProjectName()
        name = (
            self.tr("Class Diagram {0}: {1}").format(
                pname, self.project.getRelativePath(self.file)
            )
            if pname and self.project.isProjectCategory(self.file, "SOURCES")
            else self.tr("Class Diagram: {0}").format(self.file)
        )
        self.umlView.setDiagramName(name)

    def __getCurrentShape(self, name):
        """
        Private method to get the named shape.

        @param name name of the shape
        @type str
        @return shape
        @rtype QGraphicsItem
        """
        return self.allClasses.get(name)

    def buildDiagram(self):
        """
        Public method to build the class shapes of the class diagram.

        The algorithm is borrowed from Boa Constructor.
        """
        from eric7.Utilities import ModuleParser

        self.allClasses = {}
        self.allModules = {}

        try:
            extensions = Preferences.getPython("Python3Extensions") + [".rb"]
            module = ModuleParser.readModule(
                self.file, extensions=extensions, caching=False
            )
        except ImportError:
            ct = QGraphicsTextItem(None)
            ct.setHtml(
                self.buildErrorMessage(
                    self.tr("The module <b>'{0}'</b> could not be found.").format(
                        self.file
                    )
                )
            )
            self.scene.addItem(ct)
            return

        if self.file not in self.allModules:
            self.allModules[self.file] = []

        routes = []
        nodes = []
        todo = [module.createHierarchy()]
        classesFound = False
        while todo:
            hierarchy = todo[0]
            for className in hierarchy:
                classesFound = True
                cw = self.__getCurrentShape(className)
                if not cw and className.find(".") >= 0:
                    cw = self.__getCurrentShape(className.split(".")[-1])
                    if cw:
                        self.allClasses[className] = cw
                        if className not in self.allModules[self.file]:
                            self.allModules[self.file].append(className)
                if cw and cw.noAttrs != self.noAttrs:
                    cw = None
                if cw and not (
                    cw.external
                    and (className in module.classes or className in module.modules)
                ):
                    if cw.scene() != self.scene:
                        self.scene.addItem(cw)
                        cw.setPos(10, 10)
                        if className not in nodes:
                            nodes.append(className)
                else:
                    if className in module.classes:
                        # this is a local class (defined in this module)
                        self.__addLocalClass(className, module.classes[className], 0, 0)
                    elif className in module.modules:
                        # this is a local module (defined in this module)
                        self.__addLocalClass(
                            className, module.modules[className], 0, 0, True
                        )
                    else:
                        self.__addExternalClass(className, 0, 0)
                    nodes.append(className)

                if hierarchy.get(className):
                    todo.append(hierarchy.get(className))
                    for child in hierarchy.get(className, []):
                        if (className, child) not in routes:
                            routes.append((className, child))

            del todo[0]

        if classesFound:
            self.__arrangeClasses(nodes, routes[:])
            self.__createAssociations(routes)
            self.umlView.autoAdjustSceneSize(limit=True)
        else:
            ct = QGraphicsTextItem(None)
            ct.setHtml(
                self.buildErrorMessage(
                    self.tr(
                        "The module <b>'{0}'</b> does not contain any classes."
                    ).format(self.file)
                )
            )
            self.scene.addItem(ct)

    def __arrangeClasses(self, nodes, routes, whiteSpaceFactor=1.2):
        """
        Private method to arrange the shapes on the canvas.

        The algorithm is borrowed from Boa Constructor.

        @param nodes list of nodes to arrange
        @type list of str
        @param routes list of routes
        @type list of tuple of (str, str)
        @param whiteSpaceFactor factor to increase whitespace between
            items
        @type float
        """
        from . import GraphicsUtilities

        generations = GraphicsUtilities.sort(nodes, routes)

        # calculate width and height of all elements
        sizes = []
        for generation in generations:
            sizes.append([])
            for child in generation:
                sizes[-1].append(self.__getCurrentShape(child).sceneBoundingRect())

        # calculate total width and total height
        width = 0
        height = 0
        widths = []
        heights = []
        for generation in sizes:
            currentWidth = 0
            currentHeight = 0

            for rect in generation:
                if rect.bottom() > currentHeight:
                    currentHeight = rect.bottom()
                currentWidth += rect.right()

            # update totals
            if currentWidth > width:
                width = currentWidth
            height += currentHeight

            # store generation info
            widths.append(currentWidth)
            heights.append(currentHeight)

        # add in some whitespace
        width *= whiteSpaceFactor
        height = height * whiteSpaceFactor - 20
        verticalWhiteSpace = 40.0

        sceneRect = self.umlView.sceneRect()
        width += 50.0
        height += 50.0
        swidth = sceneRect.width() if width < sceneRect.width() else width
        sheight = sceneRect.height() if height < sceneRect.height() else height
        self.umlView.setSceneSize(swidth, sheight)

        # distribute each generation across the width and the
        # generations across height
        y = 10.0
        for currentWidth, currentHeight, generation in zip_longest(
            widths, heights, generations
        ):
            x = 10.0
            # whiteSpace is the space between any two elements
            whiteSpace = (width - currentWidth - 20) / (len(generation) - 1.0 or 2.0)
            for className in generation:
                cw = self.__getCurrentShape(className)
                cw.setPos(x, y)
                rect = cw.sceneBoundingRect()
                x = x + rect.width() + whiteSpace
            y = y + currentHeight + verticalWhiteSpace

    def __addLocalClass(self, className, _class, x, y, isRbModule=False):
        """
        Private method to add a class defined in the module.

        @param className name of the class to be as a dictionary key
        @type str
        @param _class class to be shown
        @type ModuleParser.Class
        @param x x-coordinate
        @type float
        @param y y-coordinate
        @type float
        @param isRbModule flag indicating a Ruby module
        @type bool
        """
        from .ClassItem import ClassItem, ClassModel

        name = _class.name
        if isRbModule:
            name = "{0} (Module)".format(name)
        cl = ClassModel(
            name,
            sorted(_class.methods),
            sorted(_class.attributes),
            sorted(_class.globals),
        )
        cw = ClassItem(
            cl,
            False,
            x,
            y,
            noAttrs=self.noAttrs,
            scene=self.scene,
            colors=self.umlView.getDrawingColors(),
        )
        cw.setId(self.umlView.getItemId())
        self.allClasses[className] = cw
        if _class.name not in self.allModules[self.file]:
            self.allModules[self.file].append(_class.name)

    def __addExternalClass(self, _class, x, y):
        """
        Private method to add a class defined outside the module.

        If the canvas is too small to take the shape, it
        is enlarged.

        @param _class class to be shown
        @type ModuleParser.Class
        @param x x-coordinate
        @type float
        @param y y-coordinate
        @type float
        """
        from .ClassItem import ClassItem, ClassModel

        cl = ClassModel(_class)
        cw = ClassItem(
            cl,
            True,
            x,
            y,
            noAttrs=self.noAttrs,
            scene=self.scene,
            colors=self.umlView.getDrawingColors(),
        )
        cw.setId(self.umlView.getItemId())
        self.allClasses[_class] = cw
        if _class not in self.allModules[self.file]:
            self.allModules[self.file].append(_class)

    def __createAssociations(self, routes):
        """
        Private method to generate the associations between the class shapes.

        @param routes list of relationsships
        @type list of tuple of (str, str)
        """
        from .AssociationItem import AssociationItem, AssociationType

        for route in routes:
            if len(route) > 1:
                assoc = AssociationItem(
                    self.__getCurrentShape(route[1]),
                    self.__getCurrentShape(route[0]),
                    AssociationType.GENERALISATION,
                    topToBottom=True,
                    colors=self.umlView.getDrawingColors(),
                )
                self.scene.addItem(assoc)

    def parsePersistenceData(self, _version, data):
        """
        Public method to parse persisted data.

        @param _version version of the data (unused)
        @type str
        @param data persisted data to be parsed
        @type str
        @return flag indicating success
        @rtype bool
        """
        parts = data.split(", ")
        if (
            len(parts) != 2
            or not parts[0].startswith("file=")
            or not parts[1].startswith("no_attributes=")
        ):
            return False

        self.file = parts[0].split("=", 1)[1].strip()
        self.noAttrs = EricUtilities.toBool(parts[1].split("=", 1)[1].strip())

        self.initialize()

        return True

    def toDict(self):
        """
        Public method to collect data to be persisted.

        @return dictionary containing data to be persisted
        @rtype dict
        """
        data = {
            "project_name": self.project.getProjectName(),
            "no_attributes": self.noAttrs,
            "file": (
                FileSystemUtilities.fromNativeSeparators(self.__relFile)
                if self.__relFile
                else FileSystemUtilities.fromNativeSeparators(self.file)
            ),
        }

        return data

    def fromDict(self, _version, data):
        """
        Public method to populate the class with data persisted by 'toDict()'.

        @param _version version of the data (unused)
        @type str
        @param data dictionary containing the persisted data
        @type dict
        @return tuple containing a flag indicating success and an info
            message in case the diagram belongs to a different project
        @rtype tuple of (bool, str)
        """
        try:
            self.noAttrs = data["no_attributes"]

            file = FileSystemUtilities.toNativeSeparators(data["file"])
            if os.path.isabs(file):
                self.file = file
                self.__relFile = ""
            else:
                # relative file paths indicate a project file
                if data["project_name"] != self.project.getProjectName():
                    msg = self.tr(
                        "<p>The diagram belongs to project <b>{0}</b>."
                        " Please open it and try again.</p>"
                    ).format(data["project_name"])
                    return False, msg

                self.__relFile = file
                self.file = self.project.getAbsolutePath(file)
        except KeyError:
            return False, ""

        self.initialize()

        return True, ""
