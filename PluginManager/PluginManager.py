# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Plugin Manager.
"""

import contextlib
import datetime
import importlib
import importlib.util
import itertools
import logging
import os
import pathlib
import sys
import types
import zipfile

from PyQt6.QtCore import QFile, QIODevice, QObject, QUrl, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricNetwork.EricNetworkProxyFactory import proxyAuthenticationRequired
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import getConfig
from eric7.SystemUtilities import FileSystemUtilities, PythonUtilities

try:
    from eric7.EricNetwork.EricSslErrorHandler import (
        EricSslErrorHandler,
        EricSslErrorState,
    )

    SSL_AVAILABLE = True
except ImportError:
    SSL_AVAILABLE = False

from .PluginExceptions import (
    PluginActivationError,
    PluginClassFormatError,
    PluginLoadError,
    PluginModuleFormatError,
    PluginModulesError,
    PluginPathError,
)
from .PluginRepositoryReader import PluginRepositoryReader
from .PluginUtilities import getPluginHeaderEntry, hasPluginHeaderEntry


class PluginManager(QObject):
    """
    Class implementing the Plugin Manager.

    @signal shutdown() emitted at shutdown of the IDE
    @signal pluginAboutToBeActivated(modulName, pluginObject) emitted just
        before a plugin is activated
    @signal pluginActivated(moduleName, pluginObject) emitted just after
        a plugin was activated
    @signal allPlugginsActivated() emitted at startup after all plugins have
        been activated
    @signal pluginAboutToBeDeactivated(moduleName, pluginObject) emitted just
        before a plugin is deactivated
    @signal pluginDeactivated(moduleName, pluginObject) emitted just after
        a plugin was deactivated
    @signal pluginRepositoryFileDownloaded() emitted to indicate a completed
        download of the plugin repository file
    """

    shutdown = pyqtSignal()
    pluginAboutToBeActivated = pyqtSignal(str, object)
    pluginActivated = pyqtSignal(str, object)
    allPlugginsActivated = pyqtSignal()
    pluginAboutToBeDeactivated = pyqtSignal(str, object)
    pluginDeactivated = pyqtSignal(str, object)
    pluginRepositoryFileDownloaded = pyqtSignal()

    def __init__(
        self, parent=None, disabledPlugins=None, doLoadPlugins=True, develPlugin=None
    ):
        """
        Constructor

        The Plugin Manager deals with three different plugin directories.
        The first is the one, that is part of eric7 (eric7/Plugins). The
        second one is the global plugin directory called 'eric7plugins',
        which is located inside the site-packages directory. The last one
        is the user plugin directory located inside the .eric7 directory
        of the users home directory.

        @param parent reference to the parent object
        @type QObject
        @param disabledPlugins list of plug-ins that have been disabled via
            the command line parameters '--disable-plugin='
        @type list of str
        @param doLoadPlugins flag indicating, that plug-ins should
            be loaded
        @type bool
        @param develPlugin filename of a plug-in to be loaded for
            development
        @type str
        @exception PluginPathError raised to indicate an invalid plug-in path
        @exception PluginModulesError raised to indicate the absence of
            plug-in modules
        """
        super().__init__(parent)

        self.__ui = parent
        self.__develPluginFile = develPlugin
        self.__develPluginName = None
        if disabledPlugins is not None:
            self.__disabledPlugins = disabledPlugins[:]
        else:
            self.__disabledPlugins = []

        self.__inactivePluginsKey = "PluginManager/InactivePlugins"

        self.pluginDirs = {
            "eric7": os.path.join(getConfig("ericDir"), "Plugins"),
            "global": os.path.join(
                PythonUtilities.getPythonLibraryDirectory(), "eric7plugins"
            ),
            "user": os.path.join(EricUtilities.getConfigDir(), "eric7plugins"),
        }
        self.__priorityOrder = ["eric7", "global", "user"]

        self.__defaultDownloadDir = os.path.join(
            EricUtilities.getConfigDir(), "Downloads"
        )

        self.__activePlugins = {}
        self.__inactivePlugins = {}
        self.__onDemandActivePlugins = {}
        self.__onDemandInactivePlugins = {}
        self.__activeModules = {}
        self.__inactiveModules = {}
        self.__onDemandActiveModules = {}
        self.__onDemandInactiveModules = {}
        self.__failedModules = {}

        self.__foundCoreModules = []
        self.__foundGlobalModules = []
        self.__foundUserModules = []

        self.__modulesCount = 0

        pdirsExist, msg = self.__pluginDirectoriesExist()
        if not pdirsExist:
            raise PluginPathError(msg)

        if doLoadPlugins:
            if not self.__pluginModulesExist():
                raise PluginModulesError

            self.__insertPluginsPaths()

            self.__loadPlugins()

        self.__checkPluginsDownloadDirectory()

        self.pluginRepositoryFile = os.path.join(
            EricUtilities.getConfigDir(), "PluginRepository"
        )

        # attributes for the network objects
        self.__networkManager = QNetworkAccessManager(self)
        self.__networkManager.proxyAuthenticationRequired.connect(
            proxyAuthenticationRequired
        )
        if SSL_AVAILABLE:
            self.__sslErrorHandler = EricSslErrorHandler(
                Preferences.getSettings(), self
            )
            self.__networkManager.sslErrors.connect(self.__sslErrors)
        self.__replies = []

    def finalizeSetup(self):
        """
        Public method to finalize the setup of the plugin manager.
        """
        for module in itertools.chain(
            self.__onDemandInactiveModules.values(),
            self.__onDemandActiveModules.values(),
        ):
            if hasattr(module, "moduleSetup"):
                module.moduleSetup()

    def getPluginDir(self, key):
        """
        Public method to get the path of a plugin directory.

        @param key key of the plug-in directory
        @type str
        @return path of the requested plugin directory
        @rtype str
        """
        if key not in ["global", "user"]:
            return None
        else:
            try:
                return self.pluginDirs[key]
            except KeyError:
                return None

    def __pluginDirectoriesExist(self):
        """
        Private method to check, if the plugin folders exist.

        If the plugin folders don't exist, they are created (if possible).

        @return tuple of a flag indicating existence of any of the plugin
            directories and a message
        @rtype tuple of (bool, str)
        """
        if self.__develPluginFile:
            path = FileSystemUtilities.splitPath(self.__develPluginFile)[0]
            fname = os.path.join(path, "__init__.py")
            if not os.path.exists(fname):
                try:
                    with open(fname, "w"):
                        pass
                except OSError:
                    return (
                        False,
                        self.tr("Could not create a package for {0}.").format(
                            self.__develPluginFile
                        ),
                    )

        fname = os.path.join(self.pluginDirs["user"], "__init__.py")
        if not os.path.exists(fname):
            if not os.path.exists(self.pluginDirs["user"]):
                os.mkdir(self.pluginDirs["user"], 0o755)
            try:
                with open(fname, "w"):
                    pass
            except OSError:
                del self.pluginDirs["user"]

        if not os.path.exists(self.pluginDirs["global"]):
            try:
                # create the global plugins directory
                os.mkdir(self.pluginDirs["global"], 0o755)
                fname = os.path.join(self.pluginDirs["global"], "__init__.py")
                with open(fname, "w", encoding="utf-8") as f:
                    f.write("# -*- coding: utf-8 -*-\n")
                    f.write("\n")
                    f.write('"""\n')
                    f.write("Package containing the global plugins.\n")
                    f.write('"""\n')
            except OSError:
                del self.pluginDirs["global"]

        if not os.path.exists(self.pluginDirs["eric7"]):
            return (
                False,
                self.tr(
                    "The internal plugin directory <b>{0}</b> does not exits."
                ).format(self.pluginDirs["eric7"]),
            )

        return (True, "")

    def __pluginModulesExist(self):
        """
        Private method to check, if there are plugins available.

        @return flag indicating the availability of plugins
        @rtype bool
        """
        if self.__develPluginFile and not os.path.exists(self.__develPluginFile):
            return False

        self.__foundCoreModules = self.getPluginModules(self.pluginDirs["eric7"])
        if Preferences.getPluginManager("ActivateExternal"):
            if "global" in self.pluginDirs:
                self.__foundGlobalModules = self.getPluginModules(
                    self.pluginDirs["global"]
                )
            if "user" in self.pluginDirs:
                self.__foundUserModules = self.getPluginModules(self.pluginDirs["user"])

        return (
            len(
                self.__foundCoreModules
                + self.__foundGlobalModules
                + self.__foundUserModules
            )
            > 0
        )

    def getPluginModules(self, pluginPath):
        """
        Public method to get a list of plugin modules.

        @param pluginPath name of the path to search
        @type str
        @return list of plugin module names
        @rtype list of str
        """
        pluginFiles = [
            f[:-3] for f in os.listdir(pluginPath) if self.isValidPluginName(f)
        ]
        return pluginFiles[:]

    def isValidPluginName(self, pluginName):
        """
        Public method to check, if a file name is a valid plugin name.

        Plugin modules must start with "Plugin" and have the extension ".py".

        @param pluginName name of the file to be checked
        @type str
        @return flag indicating a valid plugin name
        @rtype bool
        """
        return pluginName.startswith("Plugin") and pluginName.endswith(".py")

    def __insertPluginsPaths(self):
        """
        Private method to insert the valid plugin paths into the search path.
        """
        for key in self.__priorityOrder:
            if key in self.pluginDirs:
                if self.pluginDirs[key] not in sys.path:
                    sys.path.insert(2, self.pluginDirs[key])
                EricPixmapCache.addSearchPath(self.pluginDirs[key])

        if self.__develPluginFile:
            path = FileSystemUtilities.splitPath(self.__develPluginFile)[0]
            if path not in sys.path:
                sys.path.insert(2, path)
            EricPixmapCache.addSearchPath(path)

    def __loadPlugins(self):
        """
        Private method to load the plugins found.
        """
        develPluginName = ""
        if self.__develPluginFile:
            develPluginPath, develPluginName = FileSystemUtilities.splitPath(
                self.__develPluginFile
            )
            if self.isValidPluginName(develPluginName):
                develPluginName = develPluginName[:-3]

        for pluginName in self.__foundGlobalModules:
            # user and core plug-ins have priority
            if (
                pluginName not in self.__foundUserModules
                and pluginName not in self.__foundCoreModules
                and pluginName != develPluginName
            ):
                self.loadPlugin(pluginName, self.pluginDirs["global"])

        for pluginName in self.__foundUserModules:
            # core plug-ins have priority
            if (
                pluginName not in self.__foundCoreModules
                and pluginName != develPluginName
            ):
                self.loadPlugin(pluginName, self.pluginDirs["user"])

        for pluginName in self.__foundCoreModules:
            # plug-in under development has priority
            if pluginName != develPluginName:
                self.loadPlugin(pluginName, self.pluginDirs["eric7"])

        if develPluginName:
            self.loadPlugin(develPluginName, develPluginPath)
            self.__develPluginName = develPluginName

    def loadDocumentationSetPlugins(self):
        """
        Public method to load just the documentation sets plugins.

        @exception PluginModulesError raised to indicate the absence of
            plug-in modules
        """
        if not self.__pluginModulesExist():
            raise PluginModulesError

        self.__insertPluginsPaths()

        for pluginName in self.__foundGlobalModules:
            # user and core plug-ins have priority
            if (
                pluginName not in self.__foundUserModules
                and pluginName not in self.__foundCoreModules
                and pluginName.startswith("PluginDocumentationSets")
            ):
                self.loadPlugin(pluginName, self.pluginDirs["global"])

        for pluginName in self.__foundUserModules:
            # core plug-ins have priority
            if pluginName not in self.__foundCoreModules and pluginName.startswith(
                "PluginDocumentationSets"
            ):
                self.loadPlugin(pluginName, self.pluginDirs["user"])

        for pluginName in self.__foundCoreModules:
            # plug-in under development has priority
            if pluginName.startswith("PluginDocumentationSets"):
                self.loadPlugin(pluginName, self.pluginDirs["eric7"])

    def loadPlugin(self, name, directory, reload_=False, install=False):
        """
        Public method to load a plugin module.

        Initially all modules are inactive. Modules that are requested on
        demand are sorted out and are added to the on demand list. Some
        basic validity checks are performed as well. Modules failing these
        checks are added to the failed modules list.

        @param name name of the module to be loaded
        @type str
        @param directory name of the plugin directory
        @type str
        @param reload_ flag indicating to reload the module
        @type bool
        @param install flag indicating a load operation as part of an
            installation process
        @type bool
        @exception PluginLoadError raised to indicate an issue loading
            the plug-in
        """
        try:
            fname = "{0}.py".format(os.path.join(directory, name))
            spec = importlib.util.spec_from_file_location(name, fname)
            module = importlib.util.module_from_spec(spec)
            sys.modules[module.__name__] = module
            spec.loader.exec_module(module)
            if not hasPluginHeaderEntry(module, "autoactivate"):
                module.error = self.tr(
                    "Module is missing the 'autoactivate' attribute."
                )
                self.__failedModules[name] = module
                raise PluginLoadError(name)
            if getPluginHeaderEntry(module, "autoactivate", False):
                self.__inactiveModules[name] = module
            else:
                if not hasPluginHeaderEntry(
                    module, "pluginType"
                ) or not hasPluginHeaderEntry(module, "pluginTypename"):
                    module.error = self.tr(
                        "Module is missing the 'pluginType' "
                        "and/or 'pluginTypename' attributes."
                    )
                    self.__failedModules[name] = module
                    raise PluginLoadError(name)
                else:
                    self.__onDemandInactiveModules[name] = module
            module.eric7PluginModuleName = name
            module.eric7PluginModuleFilename = fname
            if (
                install or Preferences.getPluginManager("AutoInstallDependencies")
            ) and hasattr(module, "installDependencies"):
                # ask the module to install its dependencies
                module.installDependencies(self.pipInstall)
            self.__modulesCount += 1
            if reload_:
                importlib.reload(module)
                self.initOnDemandPlugin(name)
                with contextlib.suppress(KeyError, AttributeError):
                    pluginObject = self.__onDemandInactivePlugins[name]
                    pluginObject.initToolbar(
                        self.__ui, ericApp().getObject("ToolbarManager")
                    )
        except PluginLoadError:
            print("Error loading plug-in module:", name)
        except Exception as err:
            module = types.ModuleType(name)
            module.error = self.tr("Module failed to load. Error: {0}").format(str(err))
            self.__failedModules[name] = module
            print("Error loading plug-in module:", name)
            print(str(err))

    def unloadPlugin(self, name):
        """
        Public method to unload a plugin module.

        @param name name of the module to be unloaded
        @type str
        @return flag indicating success
        @rtype bool
        """
        if name in self.__onDemandActiveModules:
            # cannot unload an ondemand plugin, that is in use
            return False

        if name in self.__activeModules:
            self.deactivatePlugin(name)

        if name in self.__inactiveModules:
            with contextlib.suppress(KeyError):
                pluginObject = self.__inactivePlugins[name]
                with contextlib.suppress(AttributeError):
                    pluginObject.prepareUnload()
                del self.__inactivePlugins[name]
            del self.__inactiveModules[name]
        elif name in self.__onDemandInactiveModules:
            with contextlib.suppress(KeyError):
                pluginObject = self.__onDemandInactivePlugins[name]
                with contextlib.suppress(AttributeError):
                    pluginObject.prepareUnload()
                del self.__onDemandInactivePlugins[name]
            del self.__onDemandInactiveModules[name]
        elif name in self.__failedModules:
            del self.__failedModules[name]

        self.__modulesCount -= 1
        return True

    def removePluginFromSysModules(self, pluginName, package, internalPackages):
        """
        Public method to remove a plugin and all related modules from
        sys.modules.

        @param pluginName name of the plugin module
        @type str
        @param package name of the plugin package
        @type str
        @param internalPackages list of intenal packages
        @type list of str
        @return flag indicating the plugin module was found in sys.modules
        @rtype bool
        """
        packages = [package] + internalPackages
        found = False
        if not package:
            package = "__None__"
        for moduleName in list(sys.modules):
            if moduleName == pluginName or moduleName.split(".")[0] in packages:
                found = True
                del sys.modules[moduleName]
        return found

    def initOnDemandPlugins(self):
        """
        Public method to create plugin objects for all on demand plugins.

        Note: The plugins are not activated.
        """
        names = sorted(self.__onDemandInactiveModules)
        for name in names:
            self.initOnDemandPlugin(name)

    def initOnDemandPlugin(self, name):
        """
        Public method to create a plugin object for the named on demand plugin.

        Note: The plug-in is not activated.

        @param name name of the plug-in
        @type str
        @exception PluginActivationError raised to indicate an issue during the
            plug-in activation
        """
        try:
            try:
                module = self.__onDemandInactiveModules[name]
            except KeyError:
                return

            if not self.__canActivatePlugin(module):
                raise PluginActivationError(module.eric7PluginModuleName)
            version = getPluginHeaderEntry(module, "version", "0.0.0")
            className = getPluginHeaderEntry(module, "className", "")
            pluginClass = getattr(module, className)
            pluginObject = None
            if name not in self.__onDemandInactivePlugins:
                pluginObject = pluginClass(self.__ui)
                pluginObject.eric7PluginModule = module
                pluginObject.eric7PluginName = className
                pluginObject.eric7PluginVersion = version
                self.__onDemandInactivePlugins[name] = pluginObject
        except PluginActivationError:
            return

    def initPluginToolbars(self, toolbarManager):
        """
        Public method to initialize plug-in toolbars.

        @param toolbarManager reference to the toolbar manager object
        @type EricToolBarManager
        """
        self.initOnDemandPlugins()
        for pluginObject in self.__onDemandInactivePlugins.values():
            with contextlib.suppress(AttributeError):
                pluginObject.initToolbar(self.__ui, toolbarManager)

    def activatePlugins(self):
        """
        Public method to activate all plugins having the "autoactivate"
        attribute set to True.
        """
        savedInactiveList = Preferences.getSettings().value(self.__inactivePluginsKey)
        inactiveList = self.__disabledPlugins[:]
        if savedInactiveList is not None:
            inactiveList += [
                p for p in savedInactiveList if p not in self.__disabledPlugins
            ]
        if (
            self.__develPluginName is not None
            and self.__develPluginName in inactiveList
        ):
            inactiveList.remove(self.__develPluginName)
        names = sorted(self.__inactiveModules)
        for name in names:
            if name not in inactiveList:
                self.activatePlugin(name)
        self.allPlugginsActivated.emit()

    def activatePlugin(self, name, onDemand=False):
        """
        Public method to activate a plugin.

        @param name name of the module to be activated
        @type str
        @param onDemand flag indicating activation of an
            on demand plugin
        @type bool
        @return reference to the initialized plugin object and an error string
        @rtype tuple of (QObject, str)
        @exception PluginActivationError raised to indicate an issue during the
            plug-in activation
        """
        try:
            logging.getLogger(__name__).debug(f"Activating Plugin '{name}'...")
            try:
                module = (
                    self.__onDemandInactiveModules[name]
                    if onDemand
                    else self.__inactiveModules[name]
                )
            except KeyError:
                logging.getLogger(__name__).debug(f"No such plugin module: '{name}'")
                return None, f"no such plugin module: {name}"

            if not self.__canActivatePlugin(module):
                raise PluginActivationError(module.eric7PluginModuleName)
            version = getPluginHeaderEntry(module, "version", "0.0.0")
            className = getPluginHeaderEntry(module, "className", "")
            pluginClass = getattr(module, className)
            pluginObject = None
            if onDemand and name in self.__onDemandInactivePlugins:
                pluginObject = self.__onDemandInactivePlugins[name]
            elif not onDemand and name in self.__inactivePlugins:
                pluginObject = self.__inactivePlugins[name]
            else:
                pluginObject = pluginClass(self.__ui)
            self.pluginAboutToBeActivated.emit(name, pluginObject)
            try:
                obj, ok = pluginObject.activate()
            except TypeError:
                module.error = self.tr("Incompatible plugin activation method.")
                obj = None
                ok = True
            except Exception as err:
                module.error = str(err)
                obj = None
                ok = False
            if not ok:
                logging.getLogger(__name__).debug(
                    f"Error activating plugin '{name}': {module.error}"
                )
                return None, module.error

            self.pluginActivated.emit(name, pluginObject)
            pluginObject.eric7PluginModule = module
            pluginObject.eric7PluginName = className
            pluginObject.eric7PluginVersion = version

            if onDemand:
                self.__onDemandInactiveModules.pop(name)
                with contextlib.suppress(KeyError):
                    self.__onDemandInactivePlugins.pop(name)
                self.__onDemandActivePlugins[name] = pluginObject
                self.__onDemandActiveModules[name] = module
            else:
                self.__inactiveModules.pop(name)
                with contextlib.suppress(KeyError):
                    self.__inactivePlugins.pop(name)
                self.__activePlugins[name] = pluginObject
                self.__activeModules[name] = module
            return obj, ""
        except PluginActivationError as err:
            logging.getLogger(__name__).debug(
                f"Error activating plugin '{name}': {str(err)}"
            )
            return None, str(err)

    def __canActivatePlugin(self, module):
        """
        Private method to check, if a plugin can be activated.

        @param module reference to the module to be activated
        @type Module
        @return flag indicating, if the module satisfies all requirements
            for being activated
        @rtype bool
        @exception PluginModuleFormatError raised to indicate an invalid
            plug-in module format
        @exception PluginClassFormatError raised to indicate an invalid
            plug-in class format
        """
        try:
            if not hasPluginHeaderEntry(module, "version"):
                raise PluginModuleFormatError(module.eric7PluginModuleName, "version")
            if not hasPluginHeaderEntry(module, "className"):
                raise PluginModuleFormatError(module.eric7PluginModuleName, "className")
            className = getPluginHeaderEntry(module, "className", "")
            if not className or not hasattr(module, className):
                raise PluginModuleFormatError(module.eric7PluginModuleName, className)
            pluginClass = getattr(module, className)
            if not hasattr(pluginClass, "__init__"):
                raise PluginClassFormatError(
                    module.eric7PluginModuleName, className, "__init__"
                )
            if not hasattr(pluginClass, "activate"):
                raise PluginClassFormatError(
                    module.eric7PluginModuleName, className, "activate"
                )
            if not hasattr(pluginClass, "deactivate"):
                raise PluginClassFormatError(
                    module.eric7PluginModuleName, className, "deactivate"
                )
            return True
        except PluginModuleFormatError as e:
            print(repr(e))
            return False
        except PluginClassFormatError as e:
            print(repr(e))
            return False

    def deactivatePlugin(self, name, onDemand=False):
        """
        Public method to deactivate a plugin.

        @param name name of the module to be deactivated
        @type str
        @param onDemand flag indicating deactivation of an
            on demand plugin
        @type bool
        """
        try:
            module = (
                self.__onDemandActiveModules[name]
                if onDemand
                else self.__activeModules[name]
            )
        except KeyError:
            return

        if self.__canDeactivatePlugin(module):
            pluginObject = None
            if onDemand and name in self.__onDemandActivePlugins:
                pluginObject = self.__onDemandActivePlugins[name]
            elif not onDemand and name in self.__activePlugins:
                pluginObject = self.__activePlugins[name]
            if pluginObject:
                self.pluginAboutToBeDeactivated.emit(name, pluginObject)
                pluginObject.deactivate()
                self.pluginDeactivated.emit(name, pluginObject)

                if onDemand:
                    self.__onDemandActiveModules.pop(name)
                    self.__onDemandActivePlugins.pop(name)
                    self.__onDemandInactivePlugins[name] = pluginObject
                    self.__onDemandInactiveModules[name] = module
                else:
                    self.__activeModules.pop(name)
                    with contextlib.suppress(KeyError):
                        self.__activePlugins.pop(name)
                    self.__inactivePlugins[name] = pluginObject
                    self.__inactiveModules[name] = module

    def __canDeactivatePlugin(self, module):
        """
        Private method to check, if a plugin can be deactivated.

        @param module reference to the module to be deactivated
        @type Module
        @return flag indicating, if the module satisfies all requirements
            for being deactivated
        @rtype bool
        """
        return getPluginHeaderEntry(module, "deactivateable", True)

    def getPluginObject(self, type_, typename, maybeActive=False):
        """
        Public method to activate an on-demand plugin given by type and
        type name.

        @param type_ type of the plugin to be activated
        @type str
        @param typename name of the plugin within the type category
        @type str
        @param maybeActive flag indicating, that the plugin may be active
            already
        @type bool
        @return reference to the initialized plugin object and an error string
        @rtype tuple of (QObject, str)
        """
        for name, module in self.__onDemandInactiveModules.items():
            if (
                getPluginHeaderEntry(module, "pluginType", "") == type_
                and getPluginHeaderEntry(module, "pluginTypename", "") == typename
            ):
                return self.activatePlugin(name, onDemand=True)

        if maybeActive:
            for name, module in self.__onDemandActiveModules.items():
                if (
                    getPluginHeaderEntry(module, "pluginType", "") == type_
                    and getPluginHeaderEntry(module, "pluginTypename", "") == typename
                ):
                    self.deactivatePlugin(name, onDemand=True)
                    return self.activatePlugin(name, onDemand=True)

        return None, f"no plugin module of type {type_}: {typename}"

    def getPluginInfos(self):
        """
        Public method to get infos about all loaded plug-ins.

        @return list of dictionaries with keys "module_name", "plugin_name",
            "version", "auto_activate", "active", "short_desc", "error"
        @rtype list of dict ("module_name": str, "plugin_name": str,
            "version": str, "auto_activate": bool, "active": bool,
            "short_desc": str, "error": bool)
        """
        infos = []

        # 1. active, non-on-demand modules
        for name in self.__activeModules:
            info = self.__getShortInfo(self.__activeModules[name])
            info.update(
                {
                    "module_name": name,
                    "auto_activate": True,
                    "active": True,
                }
            )
            infos.append(info)

        # 2. inactive, non-on-demand modules
        for name in self.__inactiveModules:
            info = self.__getShortInfo(self.__inactiveModules[name])
            info.update(
                {
                    "module_name": name,
                    "auto_activate": True,
                    "active": False,
                }
            )
            infos.append(info)

        # 3. active, on-demand modules
        for name in self.__onDemandActiveModules:
            info = self.__getShortInfo(self.__onDemandActiveModules[name])
            info.update(
                {
                    "module_name": name,
                    "auto_activate": False,
                    "active": True,
                }
            )
            infos.append(info)

        # 4. inactive, non-on-demand modules
        for name in self.__onDemandInactiveModules:
            info = self.__getShortInfo(self.__onDemandInactiveModules[name])
            info.update(
                {
                    "module_name": name,
                    "auto_activate": False,
                    "active": False,
                }
            )
            infos.append(info)

        # 5. failed modules
        for name in self.__failedModules:
            info = self.__getShortInfo(self.__failedModules[name])
            info.update(
                {
                    "module_name": name,
                    "auto_activate": False,
                    "active": False,
                }
            )
            infos.append(info)

        return infos

    def __getShortInfo(self, module):
        """
        Private method to extract the short info from a module.

        @param module module to extract short info from
        @type Module
        @return dictionary containing plug-in data
        @rtype dict ("plugin_name": str, "version": str, "short_desc": str,
            "error": bool)
        """
        return {
            "plugin_name": getPluginHeaderEntry(module, "name", ""),
            "version": getPluginHeaderEntry(module, "version", ""),
            "short_desc": getPluginHeaderEntry(module, "shortDescription", ""),
            "error": bool(getPluginHeaderEntry(module, "error", "")),
        }

    def getPluginDetails(self, name):
        """
        Public method to get detailed information about a plugin.

        @param name name of the module to get detailed infos about
        @type str
        @return details of the plugin as a dictionary
        @rtype dict
        """
        details = {}

        autoactivate = True
        active = True

        if name in self.__activeModules:
            module = self.__activeModules[name]
        elif name in self.__inactiveModules:
            module = self.__inactiveModules[name]
            active = False
        elif name in self.__onDemandActiveModules:
            module = self.__onDemandActiveModules[name]
            autoactivate = False
        elif name in self.__onDemandInactiveModules:
            module = self.__onDemandInactiveModules[name]
            autoactivate = False
            active = False
        elif name in self.__failedModules:
            module = self.__failedModules[name]
            autoactivate = False
            active = False
        elif "_" in name:
            # try stripping of a postfix
            return self.getPluginDetails(name.rsplit("_", 1)[0])
        else:
            # should not happen
            return None

        details["moduleName"] = name
        details["moduleFileName"] = getPluginHeaderEntry(
            module, "eric7PluginModuleFilename", ""
        )
        details["pluginName"] = getPluginHeaderEntry(module, "name", "")
        details["version"] = getPluginHeaderEntry(module, "version", "")
        details["author"] = getPluginHeaderEntry(module, "author", "")
        details["description"] = getPluginHeaderEntry(module, "longDescription", "")
        details["autoactivate"] = autoactivate
        details["active"] = active
        details["error"] = getPluginHeaderEntry(module, "error", "")

        return details

    def doShutdown(self):
        """
        Public method called to perform actions upon shutdown of the IDE.
        """
        names = []
        for name in self.__inactiveModules:
            names.append(name)
        Preferences.getSettings().setValue(self.__inactivePluginsKey, names)

        self.shutdown.emit()

    def getPluginDisplayStrings(self, type_):
        """
        Public method to get the display strings of all plugins of a specific
        type.

        @param type_ type of the plugins
        @type str
        @return dictionary with name as key and display string as value
        @rtype dict
        """
        pluginDict = {}

        for module in itertools.chain(
            self.__onDemandActiveModules.values(),
            self.__onDemandInactiveModules.values(),
        ):
            if (
                getPluginHeaderEntry(module, "pluginType", "") == type_
                and getPluginHeaderEntry(module, "error", "") == ""
            ):
                plugin_name = getPluginHeaderEntry(module, "pluginTypename", "")
                if plugin_name:
                    pluginDict[plugin_name] = getPluginHeaderEntry(
                        module, "displayString", plugin_name
                    )

        return pluginDict

    def getPluginPreviewPixmap(self, type_, name):
        """
        Public method to get a preview pixmap of a plugin of a specific type.

        @param type_ type of the plugin
        @type str
        @param name name of the plugin type
        @type str
        @return preview pixmap
        @rtype QPixmap
        """
        for module in itertools.chain(
            self.__onDemandActiveModules.values(),
            self.__onDemandInactiveModules.values(),
        ):
            if (
                getPluginHeaderEntry(module, "pluginType", "") == type_
                and getPluginHeaderEntry(module, "pluginTypename", "") == name
            ):
                if hasattr(module, "previewPix"):
                    return module.previewPix()
                else:
                    return QPixmap()

        return QPixmap()

    def getPluginApiFiles(self, language):
        """
        Public method to get the list of API files installed by a plugin.

        @param language language of the requested API files
        @type str
        @return list of API filenames
        @rtype list of str
        """
        apis = []

        for module in itertools.chain(
            self.__activeModules.values(),
            self.__onDemandActiveModules.values(),
        ):
            if hasattr(module, "apiFiles"):
                apis.extend(module.apiFiles(language))

        return apis

    def getPluginQtHelpFiles(self):
        """
        Public method to get the list of QtHelp documentation files provided
        by a plug-in.

        @return dictionary with documentation type as key and list of files
            as value
        @rtype dict (key: str, value: list of str)
        """
        helpFiles = {}
        for module in itertools.chain(
            self.__activeModules.values(),
            self.__onDemandActiveModules.values(),
        ):
            if hasattr(module, "helpFiles"):
                helpFiles.update(module.helpFiles())

        return helpFiles

    def getPluginExeDisplayData(self):
        """
        Public method to get data to display information about a plugins
        external tool.

        @return list of dictionaries containing the data. Each dictionary must
            either contain data for the determination or the data to be
            displayed.<br />
            A dictionary of the first form must have the following entries:
            <ul>
                <li>programEntry - indicator for this dictionary form
                   (boolean), always True</li>
                <li>header - string to be diplayed as a header (string)</li>
                <li>exe - the executable (string)</li>
                <li>versionCommand - commandline parameter for the exe
                    (string)</li>
                <li>versionStartsWith - indicator for the output line
                    containing the version (string)</li>
                <li>versionPosition - number of element containing the
                    version (integer)</li>
                <li>version - version to be used as default (string)</li>
                <li>versionCleanup - tuple of two integers giving string
                    positions start and stop for the version string
                    (tuple of integers)</li>
            </ul>
            A dictionary of the second form must have the following entries:
            <ul>
                <li>programEntry - indicator for this dictionary form
                    (boolean), always False</li>
                <li>header - string to be diplayed as a header (string)</li>
                <li>text - entry text to be shown (string)</li>
                <li>version - version text to be shown (string)</li>
            </ul>
        @rtype list of dict
        """
        infos = []

        for module in itertools.chain(
            self.__activeModules.values(),
            self.__inactiveModules.values(),
            self.__onDemandActiveModules.values(),
            self.__onDemandInactiveModules.values(),
        ):
            if hasattr(module, "exeDisplayDataList"):
                infos.extend(module.exeDisplayDataList())
            elif hasattr(module, "exeDisplayData"):
                infos.append(module.exeDisplayData())

        return infos

    def getPluginConfigData(self):
        """
        Public method to get the config data of all active, non on-demand
        plugins used by the configuration dialog.

        Plugins supporting this functionality must provide the plugin module
        function 'getConfigData' returning a dictionary with unique keys
        of lists with the following list contents:
        <dl>
          <dt>display string</dt>
          <dd>string shown in the selection area of the configuration page.
              This should be a localized string</dd>
          <dt>pixmap name</dt>
          <dd>filename of the pixmap to be shown next to the display
              string</dd>
          <dt>page creation function</dt>
          <dd>plugin module function to be called to create the configuration
              page. The page must be subclasses from
              Preferences.ConfigurationPages.ConfigurationPageBase and must
              implement a method called 'save' to save the settings. A parent
              entry will be created in the selection list, if this value is
              None.</dd>
          <dt>parent key</dt>
          <dd>dictionary key of the parent entry or None, if this defines a
              toplevel entry.</dd>
          <dt>reference to configuration page</dt>
          <dd>This will be used by the configuration dialog and must always
              be None</dd>
        </dl>

        @return plug-in configuration data
        @rtype dict
        """
        configData = {}
        for module in itertools.chain(
            self.__activeModules.values(),
            self.__onDemandActiveModules.values(),
            self.__onDemandInactiveModules.values(),
        ):
            if hasattr(module, "getConfigData"):
                configData.update(module.getConfigData())
        return configData

    def isPluginLoaded(self, pluginName):
        """
        Public method to check, if a certain plugin is loaded.

        @param pluginName name of the plugin to check for
        @type str
        @return flag indicating, if the plugin is loaded
        @rtype bool
        """
        return (
            pluginName in self.__activeModules
            or pluginName in self.__inactiveModules
            or pluginName in self.__onDemandActiveModules
            or pluginName in self.__onDemandInactiveModules
        )

    def isPluginActive(self, pluginName):
        """
        Public method to check, if a certain plugin is active.

        @param pluginName name of the plugin to check for
        @type str
        @return flag indicating, if the plugin is active
        @rtype bool
        """
        return (
            pluginName in self.__activeModules
            or pluginName in self.__onDemandActiveModules
        )

    ###########################################################################
    ## Specialized plug-in module handling methods below
    ###########################################################################

    ###########################################################################
    ## VCS related methods below
    ###########################################################################

    def getVcsSystemIndicators(self):
        """
        Public method to get the Vcs System indicators.

        Plugins supporting this functionality must support the module function
        getVcsSystemIndicator returning a dictionary with indicator as key and
        a tuple with the vcs name (string) and vcs display string (string).

        @return dictionary with indicator as key and a list of tuples as
            values. Each tuple contains the vcs name (str) and vcs display
            string (str).
        @rtype dict
        """
        vcsDict = {}

        for module in itertools.chain(
            self.__onDemandActiveModules.values(),
            self.__onDemandInactiveModules.values(),
        ):
            if getPluginHeaderEntry(
                module, "pluginType", ""
            ) == "version_control" and hasattr(module, "getVcsSystemIndicator"):
                res = module.getVcsSystemIndicator()
                for indicator, vcsData in res.items():
                    if indicator in vcsDict:
                        vcsDict[indicator].append(vcsData)
                    else:
                        vcsDict[indicator] = [vcsData]

        return vcsDict

    def deactivateVcsPlugins(self):
        """
        Public method to deactivated all activated VCS plugins.
        """
        for name, module in list(self.__onDemandActiveModules.items()):
            if getPluginHeaderEntry(module, "pluginType", "") == "version_control":
                self.deactivatePlugin(name, True)

    ########################################################################
    ## Methods for the creation of the plug-ins download directory
    ########################################################################

    def __checkPluginsDownloadDirectory(self):
        """
        Private slot to check for the existence of the plugins download
        directory.
        """
        downloadDir = Preferences.getPluginManager("DownloadPath")
        if not downloadDir:
            downloadDir = self.__defaultDownloadDir

        if not os.path.exists(downloadDir):
            try:
                os.mkdir(downloadDir, 0o755)
            except OSError:
                # try again with (possibly) new default
                downloadDir = self.__defaultDownloadDir
                if not os.path.exists(downloadDir):
                    try:
                        os.mkdir(downloadDir, 0o755)
                    except OSError as err:
                        EricMessageBox.critical(
                            self.__ui,
                            self.tr("Plugin Manager Error"),
                            self.tr(
                                """<p>The plugin download directory"""
                                """ <b>{0}</b> could not be created. Please"""
                                """ configure it via the configuration"""
                                """ dialog.</p><p>Reason: {1}</p>"""
                            ).format(downloadDir, str(err)),
                        )
                        downloadDir = ""

        Preferences.setPluginManager("DownloadPath", downloadDir)

    def preferencesChanged(self):
        """
        Public slot to react to changes in configuration.
        """
        self.__checkPluginsDownloadDirectory()

    ########################################################################
    ## Methods for automatic plug-in update check below
    ########################################################################

    def checkPluginUpdatesAvailable(self):
        """
        Public method to check the availability of updates of plug-ins.
        """
        period = Preferences.getPluginManager("UpdatesCheckInterval")
        # 0 = off
        # 1 = daily
        # 2 = weekly
        # 3 = monthly
        # 4 = always

        if period == 0 or (self.__ui is not None and not self.__ui.isOnline()):
            return

        elif period in [1, 2, 3] and pathlib.Path(self.pluginRepositoryFile).exists():
            lastModified = datetime.datetime.fromtimestamp(
                pathlib.Path(self.pluginRepositoryFile).stat().st_mtime,
                tz=datetime.timezone.utc,
            )
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            delta = now - lastModified
            if (
                (period == 1 and delta.days < 1)
                or (period == 2 and delta.days < 7)
                or (period == 3 and delta.days < 30)
            ):
                # daily, weekly, monthly
                return

        self.downLoadRepositoryFile()

    def downLoadRepositoryFile(self, url=None):
        """
        Public method to download the plugin repository file.

        @param url URL to get the plugin repository file from
            (defaults to None)
        @type QUrl or str (optional)
        """
        self.__updateAvailable = False

        if url is None:
            url = Preferences.getUI("PluginRepositoryUrl7")
            if Preferences.getPluginManager("ForceHttpPluginDownload"):
                url = url.replace("https://", "http://")
        request = QNetworkRequest(QUrl(url))
        request.setAttribute(
            QNetworkRequest.Attribute.CacheLoadControlAttribute,
            QNetworkRequest.CacheLoadControl.AlwaysNetwork,
        )
        reply = self.__networkManager.get(request)
        reply.finished.connect(lambda: self.__downloadRepositoryFileDone(reply))
        self.__replies.append(reply)

    def __downloadRepositoryFileDone(self, reply):
        """
        Private method called after the repository file was downloaded.

        @param reply reference to the reply object of the download
        @type QNetworkReply
        """
        if reply in self.__replies:
            self.__replies.remove(reply)

        if reply.error() != QNetworkReply.NetworkError.NoError:
            EricMessageBox.warning(
                None,
                self.tr("Error downloading file"),
                self.tr(
                    """<p>Could not download the requested file"""
                    """ from {0}.</p><p>Error: {1}</p>"""
                ).format(
                    Preferences.getUI("PluginRepositoryUrl7"), reply.errorString()
                ),
            )
            reply.deleteLater()
            return

        ioDevice = QFile(self.pluginRepositoryFile + ".tmp")
        ioDevice.open(QIODevice.OpenModeFlag.WriteOnly)
        ioDevice.write(reply.readAll())
        ioDevice.close()
        if QFile.exists(self.pluginRepositoryFile):
            QFile.remove(self.pluginRepositoryFile)
        ioDevice.rename(self.pluginRepositoryFile)
        reply.deleteLater()

        if os.path.exists(self.pluginRepositoryFile):
            f = QFile(self.pluginRepositoryFile)
            if f.open(QIODevice.OpenModeFlag.ReadOnly):
                # save current URL
                url = Preferences.getUI("PluginRepositoryUrl7")

                # read the repository file
                reader = PluginRepositoryReader(f, self.checkPluginEntry)
                reader.readXML()
                if url != Preferences.getUI("PluginRepositoryUrl7"):
                    # redo if it is a redirect
                    self.checkPluginUpdatesAvailable()
                    return

                if self.__updateAvailable:
                    self.__ui and self.__ui.activatePluginRepositoryViewer()
                else:
                    self.pluginRepositoryFileDownloaded.emit()

    def checkPluginEntry(
        self,
        _name,
        _short,
        _description,
        url,
        _author,
        version,
        filename,
        _status,
        _category,
    ):
        """
        Public method to check a plug-in's data for an update.

        @param _name data for the name field (unused)
        @type str
        @param _short data for the short field (unused)
        @type str
        @param _description data for the description field (unused)
        @type list of str
        @param url data for the url field
        @type str
        @param _author data for the author field (unused)
        @type str
        @param version data for the version field
        @type str
        @param filename data for the filename field
        @type str
        @param _status status of the plugin (one of stable, unstable, unknown) (unused)
        @type str
        @param _category category designation of the plugin (unused)
        @type str
        """
        # ignore hidden plug-ins
        pluginName = os.path.splitext(url.rsplit("/", 1)[1])[0]
        if pluginName in Preferences.getPluginManager("HiddenPlugins"):
            return

        archive = os.path.join(Preferences.getPluginManager("DownloadPath"), filename)

        # Check against installed/loaded plug-ins
        pluginDetails = self.getPluginDetails(pluginName)
        if pluginDetails is None:
            if not Preferences.getPluginManager("CheckInstalledOnly"):
                self.__updateAvailable = True
            return

        versionTuple = EricUtilities.versionToTuple(version)[:3]
        pluginVersionTuple = EricUtilities.versionToTuple(pluginDetails["version"])[:3]

        if pluginVersionTuple < versionTuple:
            self.__updateAvailable = True
            return

        if not Preferences.getPluginManager("CheckInstalledOnly"):
            # Check against downloaded plugin archives
            # 1. Check, if the archive file exists
            if not os.path.exists(archive):
                if pluginDetails["moduleName"] != pluginName:
                    self.__updateAvailable = True
                return

            # 2. Check, if the archive is a valid zip file
            if not zipfile.is_zipfile(archive):
                self.__updateAvailable = True
                return

            # 3. Check the version of the archive file
            zipFile = zipfile.ZipFile(archive, "r")
            try:
                aversion = zipFile.read("VERSION").decode("utf-8")
            except KeyError:
                aversion = "0.0.0"
            zipFile.close()

            aversionTuple = EricUtilities.versionToTuple(aversion)[:3]
            if aversionTuple != versionTuple:
                self.__updateAvailable = True

    def __sslErrors(self, reply, errors):
        """
        Private slot to handle SSL errors.

        @param reply reference to the reply object
        @type QNetworkReply
        @param errors list of SSL errors
        @type list of QSslError
        """
        ignored = self.__sslErrorHandler.sslErrorsReply(reply, errors)[0]
        if ignored == EricSslErrorState.NOT_IGNORED:
            self.__downloadCancelled = True

    ########################################################################
    ## Methods to clear private data of plug-ins below
    ########################################################################

    def clearPluginsPrivateData(self, type_):
        """
        Public method to clear the private data of plug-ins of a specified
        type.

        Plugins supporting this functionality must support the module function
        'clearPrivateData()' (and may have the module level attribute 'pluginType').

        @param type_ type of the plugin to clear private data for
        @type str
        """
        for module in itertools.chain(
            self.__onDemandActiveModules.values(),
            self.__onDemandInactiveModules.values(),
            self.__activeModules.values(),
            self.__inactiveModules.values(),
        ):
            if getPluginHeaderEntry(module, "pluginType", "") == type_ and hasattr(
                module, "clearPrivateData"
            ):
                module.clearPrivateData()

    ########################################################################
    ## Methods to install a plug-in module dependency via pip
    ########################################################################

    def pipInstall(self, packages):
        """
        Public method to install the given package via pip.

        @param packages list of packages to install
        @type list of str
        """
        try:
            pip = ericApp().getObject("Pip")
        except KeyError:
            # Installation is performed via the plug-in installation script.
            from eric7.PipInterface.Pip import Pip  # __IGNORE_WARNING_I101__

            pip = Pip(self)
        pip.installPackages(packages, interpreter=PythonUtilities.getPythonExecutable())


#
# eflag: noqa = M801
