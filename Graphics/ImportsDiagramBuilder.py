# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing an imports diagram of a package.
"""

import glob
import os
import time

from PyQt6.QtWidgets import QApplication, QGraphicsTextItem

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog
from eric7.SystemUtilities import FileSystemUtilities

from .UMLDiagramBuilder import UMLDiagramBuilder


class ImportsDiagramBuilder(UMLDiagramBuilder):
    """
    Class implementing a builder for imports diagrams of a package.

    Note: Only package internal imports are shown in order to maintain
    some readability.
    """

    def __init__(self, dialog, view, project, package, showExternalImports=False):
        """
        Constructor

        @param dialog reference to the UML dialog
        @type UMLDialog
        @param view reference to the view object
        @type UMLGraphicsView
        @param project reference to the project object
        @type Project
        @param package name of a python package to show the import
            relationships
        @type str
        @param showExternalImports flag indicating to show exports from
            outside the package
        @type bool
        """
        super().__init__(dialog, view, project)
        self.setObjectName("ImportsDiagram")

        self.showExternalImports = showExternalImports
        if FileSystemUtilities.isRemoteFileName(package):
            self.packagePath = package
        else:
            self.packagePath = os.path.abspath(package)

        self.__relPackagePath = (
            self.project.getRelativePath(self.packagePath)
            if self.project.isProjectCategory(self.packagePath, "SOURCES")
            else ""
        )

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

    def initialize(self):
        """
        Public method to initialize the object.
        """
        hasInit = True
        ppath = self.packagePath

        if FileSystemUtilities.isRemoteFileName(self.packagePath):
            self.package = self.__remotefsInterface.splitdrive(self.packagePath)[1][
                1:
            ].replace(self.__remotefsInterface.separator(), ".")
            while hasInit:
                ppath = self.__remotefsInterface.dirname(ppath)
                globPattern = self.__remotefsInterface.join(ppath, "__init__.*")
                hasInit = len(self.__remotefsInterface.glob(globPattern)) > 0
        else:
            self.package = os.path.splitdrive(self.packagePath)[1][1:].replace(
                os.sep, "."
            )
            while hasInit:
                ppath = os.path.dirname(ppath)
                hasInit = len(glob.glob(os.path.join(ppath, "__init__.*"))) > 0

        self.shortPackage = self.packagePath.replace(ppath, "").replace(os.sep, ".")[1:]

        pname = self.project.getProjectName()
        name = (
            self.tr("Imports Diagramm {0}: {1}").format(
                pname, self.project.getRelativePath(self.packagePath)
            )
            if pname
            else self.tr("Imports Diagramm: {0}").format(self.packagePath)
        )
        self.umlView.setDiagramName(name)

    def __buildModulesDict(self):
        """
        Private method to build a dictionary of modules contained in the
        package.

        @return dictionary of modules contained in the package
        @rtype dict
        """
        from eric7.Utilities import ModuleParser

        extensions = Preferences.getPython("Python3Extensions")
        moduleDict = {}
        modules = []
        for ext in Preferences.getPython("Python3Extensions"):
            if FileSystemUtilities.isRemoteFileName(self.packagePath):
                modules.extend(
                    self.__remotefsInterface.glob(
                        self.__remotefsInterface.join(self.packagePath, f"*{ext}")
                    )
                )
            else:
                modules.extend(
                    glob.glob(
                        FileSystemUtilities.normjoinpath(self.packagePath, f"*{ext}")
                    )
                )

        tot = len(modules)
        progress = EricProgressDialog(
            self.tr("Parsing modules..."),
            None,
            0,
            tot,
            self.tr("%v/%m Modules"),
            self.parent(),
        )
        progress.setWindowTitle(self.tr("Imports Diagramm"))
        try:
            progress.show()
            QApplication.processEvents()

            now = time.monotonic()
            for prog, module in enumerate(modules):
                progress.setValue(prog)
                if time.monotonic() - now > 0.01:
                    QApplication.processEvents()
                    now = time.monotonic()
                try:
                    mod = ModuleParser.readModule(
                        module, extensions=extensions, caching=False
                    )
                except ImportError:
                    continue
                else:
                    name = mod.name
                    if name.startswith(self.package):
                        name = name[len(self.package) + 1 :]
                    moduleDict[name] = mod
        finally:
            progress.setValue(tot)
            progress.deleteLater()
        return moduleDict

    def buildDiagram(self):
        """
        Public method to build the modules shapes of the diagram.
        """
        if FileSystemUtilities.isRemoteFileName(self.packagePath):
            globPattern = self.__remotefsInterface.join(self.packagePath, "__init__.*")
            initlist = self.__remotefsInterface.glob(globPattern)
        else:
            initlist = glob.glob(os.path.join(self.packagePath, "__init__.*"))
        if len(initlist) == 0:
            ct = QGraphicsTextItem(None)
            ct.setHtml(
                self.buildErrorMessage(
                    self.tr(
                        "The directory <b>'{0}'</b> is not a Python package."
                    ).format(self.package)
                )
            )
            self.scene.addItem(ct)
            return

        self.__shapes = {}

        modules = self.__buildModulesDict()
        externalMods = []
        packageList = self.shortPackage.split(".")
        packageListLen = len(packageList)
        for module in sorted(modules):
            impLst = []
            for importName in modules[module].imports:
                n = (
                    importName[len(self.package) + 1 :]
                    if importName.startswith(self.package)
                    else importName
                )
                if importName in modules:
                    impLst.append(n)
                elif self.showExternalImports:
                    impLst.append(n)
                    if n not in externalMods:
                        externalMods.append(n)
            for importName in modules[module].from_imports:
                if importName.startswith("."):
                    dots = len(importName) - len(importName.lstrip("."))
                    if dots == 1:
                        n = importName[1:]
                        importName = n
                    else:
                        if self.showExternalImports:
                            n = ".".join(
                                packageList[: packageListLen - dots + 1]
                                + [importName[dots:]]
                            )
                        else:
                            n = importName
                elif importName.startswith(self.package):
                    n = importName[len(self.package) + 1 :]
                else:
                    n = importName
                if importName in modules:
                    impLst.append(n)
                elif self.showExternalImports:
                    impLst.append(n)
                    if n not in externalMods:
                        externalMods.append(n)

            classNames = []
            for class_ in modules[module].classes:
                className = modules[module].classes[class_].name
                if className not in classNames:
                    classNames.append(className)
            shape = self.__addModule(module, classNames, 0.0, 0.0)
            self.__shapes[module] = (shape, impLst)

        for module in externalMods:
            shape = self.__addModule(module, [], 0.0, 0.0)
            self.__shapes[module] = (shape, [])

        # build a list of routes
        nodes = []
        routes = []
        for module in self.__shapes:
            nodes.append(module)
            for rel in self.__shapes[module][1]:
                route = (module, rel)
                if route not in routes:
                    routes.append(route)

        self.__arrangeNodes(nodes, routes[:])
        self.__createAssociations(routes)
        self.umlView.autoAdjustSceneSize(limit=True)

    def __addModule(self, name, classes, x, y):
        """
        Private method to add a module to the diagram.

        @param name module name to be shown
        @type str
        @param classes list of class names contained in the module
        @type list of str
        @param x x-coordinate
        @type float
        @param y y-coordinate
        @type float
        @return reference to the imports item
        @rtype ModuleItem
        """
        from .ModuleItem import ModuleItem, ModuleModel

        classes.sort()
        impM = ModuleModel(name, classes)
        impW = ModuleItem(
            impM, x, y, scene=self.scene, colors=self.umlView.getDrawingColors()
        )
        impW.setId(self.umlView.getItemId())
        return impW

    def __arrangeNodes(self, nodes, routes, whiteSpaceFactor=1.2):
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
                sizes[-1].append(self.__shapes[child][0].sceneBoundingRect())

        # calculate total width and total height
        width = 0
        height = 0
        widths = []
        heights = []
        for generation in sizes:
            currentWidth = 0
            currentHeight = 0

            for rect in generation:
                if rect.height() > currentHeight:
                    currentHeight = rect.height()
                currentWidth += rect.width()

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
        for currentWidth, currentHeight, generation in zip(
            reversed(widths), reversed(heights), reversed(generations)
        ):
            x = 10.0
            # whiteSpace is the space between any two elements
            whiteSpace = (width - currentWidth - 20) / (len(generation) - 1.0 or 2.0)
            for name in generation:
                shape = self.__shapes[name][0]
                shape.setPos(x, y)
                rect = shape.sceneBoundingRect()
                x = x + rect.width() + whiteSpace
            y = y + currentHeight + verticalWhiteSpace

    def __createAssociations(self, routes):
        """
        Private method to generate the associations between the module shapes.

        @param routes list of associations
        @type list of tuple of (str, str)
        """
        from .AssociationItem import AssociationItem, AssociationType

        for route in routes:
            assoc = AssociationItem(
                self.__shapes[route[0]][0],
                self.__shapes[route[1]][0],
                AssociationType.IMPORTS,
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
            or not parts[0].startswith("package=")
            or not parts[1].startswith("show_external=")
        ):
            return False

        self.packagePath = parts[0].split("=", 1)[1].strip()
        self.showExternalImports = EricUtilities.toBool(
            parts[1].split("=", 1)[1].strip()
        )

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
            "show_external": self.showExternalImports,
            "package": (
                FileSystemUtilities.fromNativeSeparators(self.__relPackagePath)
                if self.__relPackagePath
                else FileSystemUtilities.fromNativeSeparators(self.packagePath)
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
            self.showExternalImports = data["show_external"]

            packagePath = FileSystemUtilities.toNativeSeparators(data["package"])
            if os.path.isabs(packagePath):
                self.packagePath = packagePath
                self.__relPackagePath = ""
            else:
                # relative package paths indicate a project package
                if data["project_name"] != self.project.getProjectName():
                    msg = self.tr(
                        "<p>The diagram belongs to project <b>{0}</b>."
                        " Please open it and try again.</p>"
                    ).format(data["project_name"])
                    return False, msg

                self.__relPackagePath = packagePath
                self.package = self.project.getAbsolutePath(packagePath)
        except KeyError:
            return False, ""

        self.initialize()

        return True, ""
