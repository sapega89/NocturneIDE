# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing an imports diagram of the application.
"""

import glob
import os
import time

from PyQt6.QtWidgets import QApplication, QInputDialog

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog
from eric7.SystemUtilities import FileSystemUtilities

from .UMLDiagramBuilder import UMLDiagramBuilder


class ApplicationDiagramBuilder(UMLDiagramBuilder):
    """
    Class implementing a builder for imports diagrams of the application.
    """

    def __init__(self, dialog, view, project, noModules=False):
        """
        Constructor

        @param dialog reference to the UML dialog
        @type UMLDialog
        @param view reference to the view object
        @type UMLGraphicsView
        @param project reference to the project object
        @type Project
        @param noModules flag indicating, that no module names should be
            shown
        @type bool
        """
        super().__init__(dialog, view, project)
        self.setObjectName("ApplicationDiagram")

        self.noModules = noModules

        self.umlView.setDiagramName(
            self.tr("Application Diagram {0}").format(self.project.getProjectName())
        )

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

    def __buildModulesDict(self):
        """
        Private method to build a dictionary of modules contained in the
        application.

        @return dictionary of modules contained in the application
        @rtype dict
        """
        from eric7.Utilities import ModuleParser

        extensions = Preferences.getPython("Python3Extensions") + [".rb"]
        moduleDict = {}
        mods = self.project.getProjectData(dataKey="SOURCES")
        modules = []
        for module in mods:
            if FileSystemUtilities.isRemoteFileName(self.project.getProjectPath()):
                modules.append(
                    self.__remotefsInterface.join(self.project.getProjectPath(), module)
                )
            else:
                modules.append(
                    FileSystemUtilities.normabsjoinpath(
                        self.project.getProjectPath(), module
                    )
                )
        tot = len(modules)
        progress = EricProgressDialog(
            self.tr("Parsing modules..."),
            None,
            0,
            tot,
            self.tr("%v/%m Modules"),
            None,
        )
        progress.setWindowTitle(self.tr("Application Diagram"))
        try:
            progress.show()
            QApplication.processEvents()

            now = time.monotonic()
            for prog, module in enumerate(modules):
                progress.setValue(prog)
                if time.monotonic() - now > 0.01:
                    QApplication.processEvents()
                    now = time.monotonic()
                if module.endswith("__init__.py"):
                    continue
                try:
                    mod = ModuleParser.readModule(
                        module, extensions=extensions, caching=False
                    )
                except ImportError:
                    continue
                else:
                    name = mod.name
                    moduleDict[name] = mod
        finally:
            progress.setValue(tot)
            progress.deleteLater()
        return moduleDict

    def __findApplicationRoot(self):
        """
        Private method to find the application root path.

        @return application root path
        @rtype str
        """
        candidates = []
        ppath = self.project.getProjectPath()

        if FileSystemUtilities.isRemoteFileName(ppath):
            init = self.__remotefsInterface.join(ppath, "__init__.py")
            if self.__remotefsInterface.exists(init):
                # remote project is a package
                return ppath
            else:
                # check, if any of the top directories is a package
                for entry in self.__remotefsInterface.listdir(ppath)[2]:
                    if (
                        not entry["name"].startswith(".")
                        and entry["is_dir"]
                        and self.__remotefsInterface.exists(
                            self.__remotefsInterface.join(entry["path"], "__init__.py")
                        )
                    ):
                        candidates.append(entry["path"])

                # check, if project uses the 'src' layout
                srcPath = self.__remotefsInterface.join(ppath, "src")
                if self.__remotefsInterface.exists(srcPath):
                    for entry in self.__remotefsInterface.listdir(srcPath)[2]:
                        if (
                            not entry["name"].startswith(".")
                            and entry["is_dir"]
                            and self.__remotefsInterface.exists(
                                self.__remotefsInterface.join(
                                    entry["path"], "__init__.py"
                                )
                            )
                        ):
                            candidates.append(entry["path"])

        else:
            init = os.path.join(ppath, "__init__.py")
            if os.path.exists(init):
                # project is a package
                return ppath
            else:
                # check, if any of the top directories is a package
                with os.scandir(ppath) as dirEntriesIterator:
                    for entry in [
                        e for e in dirEntriesIterator if not e.name.startswith(".")
                    ]:
                        if entry.is_dir() and os.path.exists(
                            os.path.join(entry.path, "__init__.py")
                        ):
                            candidates.append(entry.path)

                # check, if project uses the 'src' layout
                srcPath = os.path.join(ppath, "src")
                if os.path.exists(srcPath):
                    with os.scandir(srcPath) as dirEntriesIterator:
                        for entry in [
                            e for e in dirEntriesIterator if not e.name.startswith(".")
                        ]:
                            if entry.is_dir() and os.path.exists(
                                os.path.join(entry.path, "__init__.py")
                            ):
                                candidates.append(entry.path)

        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            root, ok = QInputDialog.getItem(
                None,
                self.tr("Application Diagram"),
                self.tr("Select the application directory:"),
                sorted(candidates),
                0,
                True,
            )
            if ok:
                return root
        else:
            EricMessageBox.warning(
                None,
                self.tr("Application Diagram"),
                self.tr("""No application package could be detected. Aborting..."""),
            )
        return None

    def buildDiagram(self):
        """
        Public method to build the packages shapes of the diagram.
        """
        rpath = self.__findApplicationRoot()
        if rpath is None:
            # no root path detected
            return

        root = (
            self.__remotefsInterface.splitdrive(rpath)[1][1:].replace(
                self.__remotefsInterface.separator(), "."
            )
            if FileSystemUtilities.isRemoteFileName(rpath)
            else os.path.splitdrive(rpath)[1][1:].replace(os.sep, ".")
        )

        packages = {}
        self.__shapes = {}

        modules = self.__buildModulesDict()

        # step 1: build a dictionary of packages
        for module in sorted(modules):
            if "." in module:
                packageName, moduleName = module.rsplit(".", 1)
            else:
                packageName, moduleName = "", module
            if packageName in packages:
                packages[packageName][0].append(moduleName)
            else:
                packages[packageName] = ([moduleName], [])

        # step 2: assign modules to dictionaries and update import relationship
        for module in sorted(modules):
            package = module.rsplit(".", 1)[0]
            impLst = []
            for moduleImport in modules[module].imports:
                if moduleImport in modules:
                    impLst.append(moduleImport)
                else:
                    if moduleImport.find(".") == -1:
                        n = "{0}.{1}".format(modules[module].package, moduleImport)
                        if n in modules:
                            impLst.append(n)
                        else:
                            n = "{0}.{1}".format(root, moduleImport)
                            if n in modules:
                                impLst.append(n)
                            elif n in packages:
                                n = "{0}.<<Dummy>>".format(n)
                                impLst.append(n)
                    else:
                        n = "{0}.{1}".format(root, moduleImport)
                        if n in modules:
                            impLst.append(n)
            for moduleImport in modules[module].from_imports:
                if moduleImport.startswith("."):
                    dots = len(moduleImport) - len(moduleImport.lstrip("."))
                    if dots == 1:
                        moduleImport = moduleImport[1:]
                    elif dots > 1:
                        packagePath = os.path.dirname(modules[module].file)
                        hasInit = True
                        ppath = packagePath
                        while hasInit:
                            ppath = os.path.dirname(ppath)
                            hasInit = (
                                len(glob.glob(os.path.join(ppath, "__init__.*"))) > 0
                            )
                        shortPackage = packagePath.replace(ppath, "").replace(
                            os.sep, "."
                        )[1:]
                        packageList = shortPackage.split(".")[1:]
                        packageListLen = len(packageList)
                        moduleImport = ".".join(
                            packageList[: packageListLen - dots + 1]
                            + [moduleImport[dots:]]
                        )

                if moduleImport in modules:
                    impLst.append(moduleImport)
                else:
                    if moduleImport.find(".") == -1:
                        n = "{0}.{1}".format(modules[module].package, moduleImport)
                        if n in modules:
                            impLst.append(n)
                        else:
                            n = "{0}.{1}".format(root, moduleImport)
                            if n in modules:
                                impLst.append(n)
                            elif n in packages:
                                n = "{0}.<<Dummy>>".format(n)
                                impLst.append(n)
                    else:
                        n = "{0}.{1}".format(root, moduleImport)
                        if n in modules:
                            impLst.append(n)
            for moduleImport in impLst:
                impPackage = moduleImport.rsplit(".", 1)[0]
                try:
                    if impPackage not in packages[package][1] and impPackage != package:
                        packages[package][1].append(impPackage)
                except KeyError:
                    continue

        for package in sorted(packages):
            if package:
                relPackage = package.replace(root, "")
                if relPackage and relPackage[0] == ".":
                    relPackage = relPackage[1:]
                else:
                    relPackage = self.tr("<<Application>>")
            else:
                relPackage = self.tr("<<Others>>")
            shape = self.__addPackage(relPackage, packages[package][0], 0.0, 0.0)
            self.__shapes[package] = (shape, packages[package][1])

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
        @return reference to the package item
        @rtype PackageItem
        """
        from .PackageItem import PackageItem, PackageModel

        modules.sort()
        pm = PackageModel(name, modules)
        pw = PackageItem(
            pm,
            x,
            y,
            noModules=self.noModules,
            scene=self.scene,
            colors=self.umlView.getDrawingColors(),
        )
        pw.setId(self.umlView.getItemId())
        return pw

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
            or not parts[0].startswith("project=")
            or not parts[1].startswith("no_modules=")
        ):
            return False

        projectFile = parts[0].split("=", 1)[1].strip()
        if projectFile != self.project.getProjectFile():
            res = EricMessageBox.yesNo(
                None,
                self.tr("Load Diagram"),
                self.tr(
                    """<p>The diagram belongs to the project <b>{0}</b>."""
                    """ Shall this project be opened?</p>"""
                ).format(projectFile),
            )
            if res:
                self.project.openProject(projectFile)

        self.noModules = EricUtilities.toBool(parts[1].split("=", 1)[1].strip())

        self.initialize()

        return True

    def toDict(self):
        """
        Public method to collect data to be persisted.

        @return dictionary containing data to be persisted
        @rtype dict
        """
        return {
            "project_name": self.project.getProjectName(),
            "no_modules": self.noModules,
        }

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
            self.noModules = data["no_modules"]

            if data["project_name"] != self.project.getProjectName():
                msg = self.tr(
                    "<p>The diagram belongs to project <b>{0}</b>."
                    " Please open it and try again.</p>"
                ).format(data["project_name"])
                return False, msg
        except KeyError:
            return False, ""

        self.initialize()

        return True, ""
