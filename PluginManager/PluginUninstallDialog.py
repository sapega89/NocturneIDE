# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for plugin deinstallation.
"""

import glob
import importlib.util
import os
import shutil
import sys

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialog, QListWidgetItem, QVBoxLayout, QWidget

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow

from .PluginManager import PluginManager
from .PluginUtilities import getPluginHeaderEntry, hasPluginHeaderEntry
from .Ui_PluginUninstallDialog import Ui_PluginUninstallDialog


class PluginUninstallWidget(QWidget, Ui_PluginUninstallDialog):
    """
    Class implementing a dialog for plugin deinstallation.

    @signal accepted() emitted to indicate the removal of a plug-in
    """

    accepted = pyqtSignal()

    def __init__(self, pluginManager, parent=None):
        """
        Constructor

        @param pluginManager reference to the plugin manager object
        @type PluginManager
        @param parent parent of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if pluginManager is None:
            # started as external plugin deinstaller
            self.__pluginManager = PluginManager(doLoadPlugins=False)
            self.__external = True
        else:
            self.__pluginManager = pluginManager
            self.__external = False

        self.pluginDirectoryCombo.addItem(
            self.tr("User plugins directory"), self.__pluginManager.getPluginDir("user")
        )

        globalDir = self.__pluginManager.getPluginDir("global")
        if globalDir is not None and os.access(globalDir, os.W_OK):
            self.pluginDirectoryCombo.addItem(
                self.tr("Global plugins directory"), globalDir
            )

    @pyqtSlot(int)
    def on_pluginDirectoryCombo_currentIndexChanged(self, index):
        """
        Private slot to populate the plugin name combo upon a change of the
        plugin area.

        @param index index of the selected item
        @type int
        """
        pluginDirectory = self.pluginDirectoryCombo.itemData(index)
        pluginNames = sorted(self.__pluginManager.getPluginModules(pluginDirectory))

        self.pluginsList.clear()
        for pluginName in pluginNames:
            fname = "{0}.py".format(os.path.join(pluginDirectory, pluginName))
            itm = QListWidgetItem(pluginName)
            itm.setData(Qt.ItemDataRole.UserRole, fname)
            itm.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            itm.setCheckState(Qt.CheckState.Unchecked)
            self.pluginsList.addItem(itm)

    @pyqtSlot()
    def on_buttonBox_accepted(self):
        """
        Private slot to handle the accepted signal of the button box.
        """
        if self.__uninstallPlugins():
            self.accepted.emit()

    def __getCheckedPlugins(self):
        """
        Private method to get the list of plugins to be uninstalled.

        @return list of tuples with the plugin name and plugin file name
        @rtype list of tuples of (str, str)
        """
        plugins = []
        for row in range(self.pluginsList.count()):
            itm = self.pluginsList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                plugins.append((itm.text(), itm.data(Qt.ItemDataRole.UserRole)))
        return plugins

    def __uninstallPlugins(self):
        """
        Private method to uninstall the selected plugins.

        @return flag indicating success
        @rtype bool
        """
        checkedPlugins = self.__getCheckedPlugins()
        uninstallCount = 0
        for pluginName, pluginFile in checkedPlugins:
            if self.__uninstallPlugin(pluginName, pluginFile):
                uninstallCount += 1
        return uninstallCount == len(checkedPlugins)

    def __uninstallPlugin(self, pluginName, pluginFile):
        """
        Private method to uninstall a given plugin.

        @param pluginName name of the plugin
        @type str
        @param pluginFile file name of the plugin
        @type str
        @return flag indicating success
        @rtype bool
        """
        pluginDirectory = self.pluginDirectoryCombo.itemData(
            self.pluginDirectoryCombo.currentIndex()
        )

        if not self.__pluginManager.unloadPlugin(pluginName):
            EricMessageBox.critical(
                self,
                self.tr("Plugin Uninstallation"),
                self.tr(
                    """<p>The plugin <b>{0}</b> could not be unloaded."""
                    """ Aborting...</p>"""
                ).format(pluginName),
            )
            return False

        if pluginDirectory not in sys.path:
            sys.path.insert(2, pluginDirectory)
        spec = importlib.util.spec_from_file_location(pluginName, pluginFile)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasPluginHeaderEntry(module, "packageName"):
            EricMessageBox.critical(
                self,
                self.tr("Plugin Uninstallation"),
                self.tr(
                    """<p>The plugin <b>{0}</b> has no 'packageName'"""
                    """ attribute. Aborting...</p>"""
                ).format(pluginName),
            )
            return False

        package = getPluginHeaderEntry(module, "packageName", None)
        if package is None:
            package = "None"
            packageDir = ""
        else:
            packageDir = os.path.join(pluginDirectory, package)
        if (
            hasattr(module, "prepareUninstall")
            and not self.keepConfigurationCheckBox.isChecked()
        ):
            module.prepareUninstall()
        internalPackages = []
        if hasPluginHeaderEntry(module, "internalPackages"):
            # it is a comma separated string
            internalPackages = [
                p.strip()
                for p in getPluginHeaderEntry(module, "internalPackages", "").split(",")
            ]
        del module

        # clean sys.modules
        self.__pluginManager.removePluginFromSysModules(
            pluginName, package, internalPackages
        )

        try:
            if packageDir and os.path.exists(packageDir):
                shutil.rmtree(packageDir)

            fnameo = "{0}o".format(pluginFile)
            if os.path.exists(fnameo):
                os.remove(fnameo)

            fnamec = "{0}c".format(pluginFile)
            if os.path.exists(fnamec):
                os.remove(fnamec)

            pluginDirCache = os.path.join(os.path.dirname(pluginFile), "__pycache__")
            if os.path.exists(pluginDirCache):
                pluginFileName = os.path.splitext(os.path.basename(pluginFile))[0]
                for fnameo in glob.glob(
                    os.path.join(pluginDirCache, "{0}*.pyo".format(pluginFileName))
                ):
                    os.remove(fnameo)
                for fnamec in glob.glob(
                    os.path.join(pluginDirCache, "{0}*.pyc".format(pluginFileName))
                ):
                    os.remove(fnamec)

            os.remove(pluginFile)
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Plugin Uninstallation"),
                self.tr(
                    """<p>The plugin package <b>{0}</b> could not be"""
                    """ removed. Aborting...</p>"""
                    """<p>Reason: {1}</p>"""
                ).format(packageDir, str(err)),
            )
            return False

        if not self.__external:
            ui = ericApp().getObject("UserInterface")
            ui.showNotification(
                EricPixmapCache.getPixmap("plugin48"),
                self.tr("Plugin Uninstallation"),
                self.tr(
                    """<p>The plugin <b>{0}</b> was uninstalled"""
                    """ successfully from {1}.</p>"""
                ).format(pluginName, pluginDirectory),
            )
            return True

        EricMessageBox.information(
            self,
            self.tr("Plugin Uninstallation"),
            self.tr(
                """<p>The plugin <b>{0}</b> was uninstalled successfully"""
                """ from {1}.</p>"""
            ).format(pluginName, pluginDirectory),
        )
        return True


class PluginUninstallDialog(QDialog):
    """
    Class for the dialog variant.
    """

    def __init__(self, pluginManager, parent=None):
        """
        Constructor

        @param pluginManager reference to the plugin manager object
        @type PluginManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setSizeGripEnabled(True)

        self.__layout = QVBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        self.cw = PluginUninstallWidget(pluginManager, self)
        size = self.cw.size()
        self.__layout.addWidget(self.cw)
        self.resize(size)
        self.setWindowTitle(self.cw.windowTitle())

        self.cw.buttonBox.accepted.connect(self.accept)
        self.cw.buttonBox.rejected.connect(self.reject)


class PluginUninstallWindow(EricMainWindow):
    """
    Main window class for the standalone dialog.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.cw = PluginUninstallWidget(None, self)
        size = self.cw.size()
        self.setCentralWidget(self.cw)
        self.resize(size)
        self.setWindowTitle(self.cw.windowTitle())

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.cw.buttonBox.accepted.connect(self.close)
        self.cw.buttonBox.rejected.connect(self.close)
