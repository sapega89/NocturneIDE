# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing an UML like class diagram of a package.
"""

import glob
import os
import time

from itertools import zip_longest

from PyQt6.QtWidgets import QApplication, QGraphicsTextItem

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog
from eric7.SystemUtilities import FileSystemUtilities

from .UMLDiagramBuilder import UMLDiagramBuilder


class PackageDiagramBuilder(UMLDiagramBuilder):
    """
    Class implementing a builder for UML like class diagrams of a package.
    """

    def __init__(self, dialog, view, project, package, noAttrs=False):
        """
        Constructor

        @param dialog reference to the UML dialog
        @type UMLDialog
        @param view reference to the view object
        @type UMLGraphicsView
        @param project reference to the project object
        @type Project
        @param package name of a python package to be shown
        @type str
        @param noAttrs flag indicating, that no attributes should be shown
        @type bool
        """
        super().__init__(dialog, view, project)
        self.setObjectName("PackageDiagram")

        if FileSystemUtilities.isRemoteFileName(package):
            self.package = package
        else:
            self.package = os.path.abspath(package)
        self.noAttrs = noAttrs

        self.__relPackage = (
            self.project.getRelativePath(self.package)
            if self.project.isProjectCategory(self.package, "SOURCES")
            else ""
        )

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

    def initialize(self):
        """
        Public method to initialize the object.
        """
        pname = self.project.getProjectName()
        name = (
            self.tr("Package Diagram {0}: {1}").format(
                pname, self.project.getRelativePath(self.package)
            )
            if pname
            else self.tr("Package Diagram: {0}").format(self.package)
        )
        self.umlView.setDiagramName(name)

    def __getCurrentShape(self, name):
        """
        Private method to get the named shape.

        @param name name of the shape
        @type str
        @return shape
        @rtype QCanvasItem
        """
        return self.allClasses.get(name)

    def __buildModulesDict(self):
        """
        Private method to build a dictionary of modules contained in the
        package.

        @return dictionary of modules contained in the package
        @rtype dict
        """
        from eric7.Utilities import ModuleParser

        supportedExt = [
            "*{0}".format(ext) for ext in Preferences.getPython("Python3Extensions")
        ] + ["*.rb"]
        extensions = Preferences.getPython("Python3Extensions") + [".rb"]

        moduleDict = {}
        modules = []
        for ext in supportedExt:
            if FileSystemUtilities.isRemoteFileName(self.package):
                modules.extend(
                    self.__remotefsInterface.glob(
                        self.__remotefsInterface.join(self.package, ext)
                    )
                )
            else:
                modules.extend(
                    glob.glob(FileSystemUtilities.normjoinpath(self.package, ext))
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
        progress.setWindowTitle(self.tr("Package Diagram"))
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

    def __buildSubpackagesDict(self):
        """
        Private method to build a dictionary of sub-packages contained in this
        package.

        @return dictionary of sub-packages contained in this package
        @rtype dict
        """
        from eric7.Utilities import ModuleParser

        supportedExt = [
            "*{0}".format(ext) for ext in Preferences.getPython("Python3Extensions")
        ] + ["*.rb"]
        extensions = Preferences.getPython("Python3Extensions") + [".rb"]

        subpackagesDict = {}
        subpackagesList = []

        if FileSystemUtilities.isRemoteFileName(self.package):
            for subpackage in self.__remotefsInterface.listdir(self.package)[2]:
                if (
                    subpackage["is_dir"]
                    and subpackage["name"] != "__pycache__"
                    and len(
                        self.__remotefsInterface.glob(
                            self.__remotefsInterface.join(
                                subpackage["path"], "__init__.*"
                            )
                        )
                    )
                    != 0
                ):
                    subpackagesList.append(subpackage["path"])
        else:
            with os.scandir(self.package) as dirEntriesIterator:
                for subpackage in dirEntriesIterator:
                    if (
                        subpackage.is_dir()
                        and subpackage.name != "__pycache__"
                        and len(glob.glob(os.path.join(subpackage.path, "__init__.*")))
                        != 0
                    ):
                        subpackagesList.append(subpackage.path)

        tot = 0
        for ext in supportedExt:
            for subpackage in subpackagesList:
                if FileSystemUtilities.isRemoteFileName(subpackage):
                    tot += len(
                        self.__remotefsInterface.glob(
                            self.__remotefsInterface.join(subpackage, ext)
                        )
                    )
                else:
                    tot += len(
                        glob.glob(FileSystemUtilities.normjoinpath(subpackage, ext))
                    )
        progress = EricProgressDialog(
            self.tr("Parsing modules..."),
            None,
            0,
            tot,
            self.tr("%v/%m Modules"),
            self.parent(),
        )
        progress.setWindowTitle(self.tr("Package Diagram"))
        try:
            start = 0
            progress.show()
            QApplication.processEvents()

            now = time.monotonic()
            for subpackage in subpackagesList:
                packageName = os.path.basename(subpackage)
                subpackagesDict[packageName] = []
                modules = []
                for ext in supportedExt:
                    if FileSystemUtilities.isRemoteFileName(subpackage):
                        modules.extend(
                            self.__remotefsInterface.glob(
                                self.__remotefsInterface.join(subpackage, ext)
                            )
                        )
                    else:
                        modules.extend(
                            glob.glob(FileSystemUtilities.normjoinpath(subpackage, ext))
                        )
                for prog, module in enumerate(modules, start=start):
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
                        if "." in name:
                            name = name.rsplit(".", 1)[1]
                        subpackagesDict[packageName].append(name)
                start = prog
                subpackagesDict[packageName].sort()
                # move __init__ to the front
                if "__init__" in subpackagesDict[packageName]:
                    subpackagesDict[packageName].remove("__init__")
                    subpackagesDict[packageName].insert(0, "__init__")
        finally:
            progress.setValue(tot)
            progress.deleteLater()
        return subpackagesDict

    def buildDiagram(self):
        """
        Public method to build the class shapes of the package diagram.

        The algorithm is borrowed from Boa Constructor.
        """
        self.allClasses = {}

        globPattern = os.path.join(self.package, "__init__.*")
        initlist = (
            self.__remotefsInterface.glob(globPattern)
            if FileSystemUtilities.isRemoteFileName(self.package)
            else glob.glob(globPattern)
        )
        if len(initlist) == 0:
            ct = QGraphicsTextItem(None)
            self.scene.addItem(ct)
            ct.setHtml(
                self.tr("The directory <b>'{0}'</b> is not a package.").format(
                    self.package
                )
            )
            return

        modules = self.__buildModulesDict()
        subpackages = self.__buildSubpackagesDict()

        if not modules and not subpackages:
            ct = QGraphicsTextItem(None)
            self.scene.addItem(ct)
            ct.setHtml(
                self.buildErrorMessage(
                    self.tr(
                        "The package <b>'{0}'</b> does not contain any modules"
                        " or subpackages."
                    ).format(self.package)
                )
            )
            return

        # step 1: build all classes found in the modules
        classesFound = False

        for modName in modules:
            module = modules[modName]
            for cls in module.classes:
                classesFound = True
                self.__addLocalClass(cls, module.classes[cls], 0, 0)
        if not classesFound and not subpackages:
            ct = QGraphicsTextItem(None)
            self.scene.addItem(ct)
            ct.setHtml(
                self.buildErrorMessage(
                    self.tr(
                        "The package <b>'{0}'</b> does not contain any"
                        " classes or subpackages."
                    ).format(self.package)
                )
            )
            return

        # step 2: build the class hierarchies
        routes = []
        nodes = []

        for modName in modules:
            module = modules[modName]
            todo = [module.createHierarchy()]
            while todo:
                hierarchy = todo[0]
                for className in hierarchy:
                    cw = self.__getCurrentShape(className)
                    if not cw and className.find(".") >= 0:
                        cw = self.__getCurrentShape(className.split(".")[-1])
                        if cw:
                            self.allClasses[className] = cw
                    if cw and cw.noAttrs != self.noAttrs:
                        cw = None
                    if cw and not (
                        cw.external
                        and (className in module.classes or className in module.modules)
                    ):
                        if className not in nodes:
                            nodes.append(className)
                    else:
                        if className in module.classes:
                            # this is a local class (defined in this module)
                            self.__addLocalClass(
                                className, module.classes[className], 0, 0
                            )
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

        # step 3: build the subpackages
        for subpackage in sorted(subpackages):
            self.__addPackage(subpackage, subpackages[subpackage], 0, 0)
            nodes.append(subpackage)

        self.__arrangeClasses(nodes, routes[:])
        self.__createAssociations(routes)
        self.umlView.autoAdjustSceneSize(limit=True)

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

    def __addPackage(self, name, modules, x, y):
        """
        Private method to add a package to the diagram.

        @param name package name to be shown
        @type str
        @param modules list of module names contained in the package
        @type list of str
        @param x x-coordinate
        @type float
        @param y y-coordinate
        @type float
        """
        from .PackageItem import PackageItem, PackageModel

        pm = PackageModel(name, modules)
        pw = PackageItem(
            pm, x, y, scene=self.scene, colors=self.umlView.getDrawingColors()
        )
        pw.setId(self.umlView.getItemId())
        self.allClasses[name] = pw

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
            or not parts[0].startswith("package=")
            or not parts[1].startswith("no_attributes=")
        ):
            return False

        self.package = parts[0].split("=", 1)[1].strip()
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
            "package": (
                FileSystemUtilities.fromNativeSeparators(self.__relPackage)
                if self.__relPackage
                else FileSystemUtilities.fromNativeSeparators(self.package)
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

            package = FileSystemUtilities.toNativeSeparators(data["package"])
            if os.path.isabs(package):
                self.package = package
                self.__relPackage = ""
            else:
                # relative package paths indicate a project package
                if data["project_name"] != self.project.getProjectName():
                    msg = self.tr(
                        "<p>The diagram belongs to project <b>{0}</b>."
                        " Please open it and try again.</p>"
                    ).format(data["project_name"])
                    return False, msg

                self.__relPackage = package
                self.package = self.project.getAbsolutePath(package)
        except KeyError:
            return False, ""

        self.initialize()

        return True, ""
