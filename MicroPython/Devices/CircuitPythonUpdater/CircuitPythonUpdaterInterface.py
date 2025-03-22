# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an interface to the 'circup' package.
"""

import importlib
import logging
import os
import re
import shutil

import requests

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QDialog, QInputDialog, QLineEdit, QMenu

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricListSelectionDialog import EricListSelectionDialog
from eric7.SystemUtilities import PythonUtilities

try:
    import circup

    circup.logger.setLevel(logging.WARNING)
except ImportError:
    circup = None


class CircuitPythonUpdaterInterface(QObject):
    """
    Class implementing an interface to the 'circup' package.
    """

    def __init__(self, device, parent=None):
        """
        Constructor

        @param device reference to the CircuitPython device interface
        @type CircuitPythonDevice
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__device = device

        self.__installMenu = QMenu(self.tr("Install Modules"))
        self.__installMenu.setTearOffEnabled(True)
        self.__installMenu.addAction(
            self.tr("Select from Available Modules"), self.__installFromAvailable
        )
        self.__installMenu.addAction(
            self.tr("Install Requirements"), self.__installRequirements
        )
        self.__installMenu.addAction(
            self.tr("Install based on 'code.py'"), self.__installFromCode
        )
        self.__installMenu.addSeparator()
        self.__installPyAct = self.__installMenu.addAction(
            self.tr("Install Python Source")
        )
        self.__installPyAct.setCheckable(True)
        self.__installPyAct.setChecked(False)
        # kind of hack to make this action not hide the menu
        # Note: parent menus are hidden nevertheless
        self.__installPyAct.toggled.connect(self.__installMenu.show)

    def populateMenu(self, menu):
        """
        Public method to populate the 'circup' menu.

        @param menu reference to the menu to be populated
        @type QMenu
        """
        from .CircupFunctions import patch_circup

        patch_circup()
        isMounted = self.__device.supportsLocalFileAccess()

        act = menu.addAction(self.tr("circup"), self.__aboutCircup)
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()
        menu.addAction(
            self.tr("List Outdated Modules"), self.__listOutdatedModules
        ).setEnabled(isMounted)
        menu.addAction(self.tr("Update Modules"), self.__updateModules).setEnabled(
            isMounted
        )
        menu.addAction(
            self.tr("Update All Modules"), self.__updateAllModules
        ).setEnabled(isMounted)
        menu.addSeparator()
        menu.addAction(self.tr("Show Available Modules"), self.__showAvailableModules)
        menu.addAction(
            self.tr("Show Installed Modules"), self.__showInstalledModules
        ).setEnabled(isMounted)
        menu.addMenu(self.__installMenu).setEnabled(isMounted)
        menu.addAction(
            self.tr("Uninstall Modules"), self.__uninstallModules
        ).setEnabled(isMounted)
        menu.addSeparator()
        menu.addAction(
            self.tr("Generate Requirements ..."), self.__generateRequirements
        ).setEnabled(isMounted)
        menu.addSeparator()
        menu.addAction(self.tr("Show Bundles"), self.__showBundles)
        menu.addAction(self.tr("Show Bundles with Modules"), self.__showBundlesModules)
        menu.addSeparator()
        menu.addAction(self.tr("Add Bundle"), self.__addBundle)
        menu.addAction(self.tr("Remove Bundles"), self.__removeBundle)
        menu.addSeparator()
        menu.addAction(self.tr("Show Local Cache Path"), self.__showCachePath)

    @pyqtSlot()
    def __aboutCircup(self):
        """
        Private slot to show some info about 'circup'.
        """
        version = circup.get_circup_version()
        if version is None:
            version = self.tr("unknown")

        EricMessageBox.information(
            None,
            self.tr("About circup"),
            self.tr(
                """<p><b>circup Version {0}</b></p>"""
                """<p><i>circup</i> is a tool to manage and update libraries on a"""
                """ CircuitPython device.</p>""",
            ).format(version),
        )

    @pyqtSlot()
    def installCircup(self):
        """
        Public slot to install the 'circup' package via pip.
        """
        global circup

        pip = ericApp().getObject("Pip")
        pip.installPackages(
            ["circup>=2.0.0"], interpreter=PythonUtilities.getPythonExecutable()
        )

        circup = importlib.import_module("circup")
        circup.logger.setLevel(logging.WARNING)

    @pyqtSlot()
    def __showBundles(self, withModules=False):
        """
        Private slot to show the available bundles (default and local).

        @param withModules flag indicating to list the modules and their version
            (defaults to False)
        @type bool (optional)
        """
        from .ShowBundlesDialog import ShowBundlesDialog

        with EricOverrideCursor():
            dlg = ShowBundlesDialog(
                withModules=withModules, parent=self.__device.microPython
            )
        dlg.exec()

    @pyqtSlot()
    def __showBundlesModules(self):
        """
        Private slot to show the available bundles (default and local) with their
        modules.
        """
        self.__showBundles(withModules=True)

    @pyqtSlot()
    def __addBundle(self):
        """
        Private slot to add a bundle to the local bundles list, by "user/repo" github
        string.
        """
        bundle, ok = QInputDialog.getText(
            None,
            self.tr("Add Bundle"),
            self.tr("Enter Bundle by 'User/Repo' Github String:"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and bundle:
            bundles = circup.get_bundles_local_dict()
            modified = False

            # do some cleanup
            bundle = re.sub(r"https?://github.com/([^/]+/[^/]+)(/.*)?", r"\1", bundle)
            if bundle in bundles:
                EricMessageBox.information(
                    None,
                    self.tr("Add Bundle"),
                    self.tr(
                        """<p>The bundle <b>{0}</b> is already in the list.</p>"""
                    ).format(bundle),
                )
                return

            try:
                cBundle = circup.Bundle(bundle)
            except ValueError:
                EricMessageBox.critical(
                    None,
                    self.tr("Add Bundle"),
                    self.tr(
                        """<p>The bundle string is invalid, expecting github URL"""
                        """ or 'user/repository' string.</p>"""
                    ),
                )
                return

            result = requests.head("https://github.com/" + bundle, timeout=30)
            if result.status_code == requests.codes.NOT_FOUND:
                EricMessageBox.critical(
                    None,
                    self.tr("Add Bundle"),
                    self.tr(
                        """<p>The bundle string is invalid. The repository doesn't"""
                        """ exist (error code 404).</p>"""
                    ),
                )
                return

            if not cBundle.validate():
                EricMessageBox.critical(
                    None,
                    self.tr("Add Bundle"),
                    self.tr(
                        """<p>The bundle string is invalid. Is the repository a valid"""
                        """ circup bundle?</p>"""
                    ),
                )
                return

            # Use the bundle string as the dictionary key for uniqueness
            bundles[bundle] = bundle
            modified = True
            EricMessageBox.information(
                None,
                self.tr("Add Bundle"),
                self.tr("""<p>Added bundle <b>{0}</b> ({1}).</p>""").format(
                    bundle, cBundle.url
                ),
            )

            if modified:
                # save the bundles list
                circup.save_local_bundles(bundles)
                # update and get the new bundle for the first time
                circup.get_bundle_versions(circup.get_bundles_list())

    @pyqtSlot()
    def __removeBundle(self):
        """
        Private slot to remove one or more bundles from the local bundles list.
        """
        localBundles = circup.get_bundles_local_dict()
        dlg = EricListSelectionDialog(
            sorted(localBundles),
            title=self.tr("Remove Bundles"),
            message=self.tr("Select the bundles to be removed:"),
            checkBoxSelection=True,
            parent=self.__device.microPython,
        )
        modified = False
        if dlg.exec() == QDialog.DialogCode.Accepted:
            bundles = dlg.getSelection()
            for bundle in bundles:
                del localBundles[bundle]
                modified = True

        if modified:
            circup.save_local_bundles(localBundles)
            EricMessageBox.information(
                None,
                self.tr("Remove Bundles"),
                self.tr(
                    """<p>These bundles were removed from the local bundles list.{0}"""
                    """</p>"""
                ).format("""<ul><li>{0}</li></ul>""".format("</li><li>".join(bundles))),
            )

    @pyqtSlot()
    def __listOutdatedModules(self):
        """
        Private slot to list the outdated modules of the connected device.
        """
        from .ShowOutdatedDialog import ShowOutdatedDialog

        devicePath = self.__device.getWorkspace()

        cpyVersion, _board_id = circup.get_circuitpython_version(devicePath)
        circup.CPY_VERSION = cpyVersion

        with EricOverrideCursor():
            dlg = ShowOutdatedDialog(
                devicePath=devicePath, parent=self.__device.microPython
            )
        dlg.exec()

    @pyqtSlot()
    def __updateModules(self):
        """
        Private slot to update the modules of the connected device.
        """
        from .ShowOutdatedDialog import ShowOutdatedDialog

        devicePath = self.__device.getWorkspace()

        cpyVersion, _board_id = circup.get_circuitpython_version(devicePath)
        circup.CPY_VERSION = cpyVersion

        with EricOverrideCursor():
            dlg = ShowOutdatedDialog(
                devicePath=devicePath,
                selectionMode=True,
                parent=self.__device.microPython,
            )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            modules = dlg.getSelection()
            self.__doUpdateModules(modules)

    @pyqtSlot()
    def __updateAllModules(self):
        """
        Private slot to update all modules of the connected device.
        """
        devicePath = self.__device.getWorkspace()

        cpyVersion, _board_id = circup.get_circuitpython_version(devicePath)
        circup.CPY_VERSION = cpyVersion

        with EricOverrideCursor():
            modules = [
                m
                for m in circup.find_modules(devicePath, circup.get_bundles_list())
                if m.outofdate
            ]
        if modules:
            self.__doUpdateModules(modules)
        else:
            EricMessageBox.information(
                None,
                self.tr("Update Modules"),
                self.tr("All modules are already up-to-date."),
            )

    def __doUpdateModules(self, modules):
        """
        Private method to perform the update of a list of modules.

        @param modules list of modules to be updated
        @type circup.module.Module
        """
        backend = circup.DiskBackend(self.__device.getWorkspace(), circup.logger)

        updatedModules = []
        for module in modules:
            try:
                backend.update(module)
                updatedModules.append(module.name)
            except Exception as ex:
                EricMessageBox.critical(
                    None,
                    self.tr("Update Modules"),
                    self.tr(
                        """<p>There was an error updating <b>{0}</b>.</p>"""
                        """<p>Error: {1}</p>"""
                    ).format(module.name, str(ex)),
                )

        if updatedModules:
            EricMessageBox.information(
                None,
                self.tr("Update Modules"),
                self.tr(
                    """<p>These modules were updated on the connected device.{0}</p>"""
                ).format(
                    """<ul><li>{0}</li></ul>""".format("</li><li>".join(updatedModules))
                ),
            )
        else:
            EricMessageBox.information(
                None,
                self.tr("Update Modules"),
                self.tr("No modules could be updated."),
            )

    @pyqtSlot()
    def __showAvailableModules(self):
        """
        Private slot to show the available modules.

        These are modules which could be installed on the device.
        """
        from eric7.MicroPython.ShowModulesDialog import ShowModulesDialog

        with EricOverrideCursor():
            availableModules = circup.get_bundle_versions(circup.get_bundles_list())
            moduleNames = [m.replace(".py", "") for m in availableModules]

        dlg = ShowModulesDialog(moduleNames, parent=self.__device.microPython)
        dlg.exec()

    @pyqtSlot()
    def __showInstalledModules(self):
        """
        Private slot to show the modules installed on the connected device.
        """
        from .ShowInstalledDialog import ShowInstalledDialog

        devicePath = self.__device.getWorkspace()

        with EricOverrideCursor():
            dlg = ShowInstalledDialog(
                devicePath=devicePath, parent=self.__device.microPython
            )
        dlg.exec()

    @pyqtSlot()
    def __installFromAvailable(self):
        """
        Private slot to install modules onto the connected device.
        """
        from eric7.MicroPython.ShowModulesDialog import ShowModulesDialog

        with EricOverrideCursor():
            availableModules = circup.get_bundle_versions(circup.get_bundles_list())
            moduleNames = [m.replace(".py", "") for m in availableModules]

        dlg = ShowModulesDialog(
            moduleNames, selectionMode=True, parent=self.__device.microPython
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            modules = dlg.getSelection()
            self.__installModules(modules)

    @pyqtSlot()
    def __installRequirements(self):
        """
        Private slot to install modules determined by a requirements file.
        """
        homeDir = (
            Preferences.getMicroPython("MpyWorkspace")
            or Preferences.getMultiProject("Workspace")
            or os.path.expanduser("~")
        )
        reqFile = EricFileDialog.getOpenFileName(
            None,
            self.tr("Install Modules"),
            homeDir,
            self.tr("Text Files (*.txt);;All Files (*)"),
        )
        if reqFile:
            if os.path.exists(reqFile):
                with open(reqFile, "r") as fp:
                    requirementsText = fp.read()
                modules = circup.libraries_from_requirements(requirementsText)
                if modules:
                    self.__installModules(modules)
                else:
                    EricMessageBox.critical(
                        None,
                        self.tr("Install Modules"),
                        self.tr(
                            """<p>The given requirements file <b>{0}</b> does not"""
                            """ contain valid modules.</p>"""
                        ).format(reqFile),
                    )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Install Modules"),
                    self.tr(
                        """<p>The given requirements file <b>{0}</b> does not exist."""
                        """</p>"""
                    ).format(reqFile),
                )

    @pyqtSlot()
    def __installFromCode(self):
        """
        Private slot to install modules based on the 'code.py' file of the
        connected device.
        """
        devicePath = self.__device.getWorkspace()

        codeFile = EricFileDialog.getOpenFileName(
            None,
            self.tr("Install Modules"),
            os.path.join(devicePath, "code.py"),
            self.tr("Python Files (*.py);;All Files (*)"),
        )
        if codeFile:
            if os.path.exists(codeFile):
                with EricOverrideCursor():
                    availableModules = circup.command_utils.get_bundle_versions(
                        circup.get_bundles_list()
                    )
                    moduleNames = {}
                    for module, metadata in availableModules.items():
                        moduleNames[module.replace(".py", "")] = metadata

                modules = circup.libraries_from_code_py(codeFile, moduleNames)
                if modules:
                    self.__installModules(modules)
                else:
                    EricMessageBox.critical(
                        None,
                        self.tr("Install Modules"),
                        self.tr(
                            """<p>The given code file <b>{0}</b> does not"""
                            """ contain valid import statements or does not import"""
                            """ external modules.</p>"""
                        ).format(codeFile),
                    )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Install Modules"),
                    self.tr(
                        """<p>The given code file <b>{0}</b> does not exist.</p>"""
                    ).format(codeFile),
                )

    def __installModules(self, installs):
        """
        Private method to install the given list of modules.

        @param installs list of module names to be installed
        @type list of str
        """
        devicePath = self.__device.getWorkspace()
        backend = circup.DiskBackend(devicePath, circup.logger)

        cpyVersion, _board_id = circup.get_circuitpython_version(devicePath)
        circup.CPY_VERSION = cpyVersion

        with EricOverrideCursor():
            availableModules = circup.get_bundle_versions(circup.get_bundles_list())
            moduleNames = {}
            for module, metadata in availableModules.items():
                moduleNames[module.replace(".py", "")] = metadata
            toBeInstalled = circup.get_dependencies(installs, mod_names=moduleNames)
            deviceModules = backend.get_device_versions()
        if toBeInstalled is not None:
            dependencies = [m for m in toBeInstalled if m not in installs]
            ok = EricMessageBox.yesNo(
                None,
                self.tr("Install Modules"),
                self.tr("""<p>Ready to install these modules?{0}{1}</p>""").format(
                    """<ul><li>{0}</li></ul>""".format(
                        "</li><li>".join(sorted(installs))
                    ),
                    (
                        self.tr("Dependencies:")
                        + """<ul><li>{0}</li></ul>""".format(
                            "</li><li>".join(sorted(dependencies))
                        )
                        if dependencies
                        else ""
                    ),
                ),
                yesDefault=True,
            )
            if ok:
                installedModules = []
                with EricOverrideCursor():
                    for library in toBeInstalled:
                        success = circup.install_module(
                            devicePath,
                            deviceModules,
                            library,
                            self.__installPyAct.isChecked(),
                            moduleNames,
                        )
                        if success:
                            installedModules.append(library)

                if installedModules:
                    EricMessageBox.information(
                        None,
                        self.tr("Install Modules"),
                        self.tr(
                            "<p>Installation complete. These modules were installed"
                            " successfully.{0}</p>"
                        ).format(
                            """<ul><li>{0}</li></ul>""".format(
                                "</li><li>".join(sorted(installedModules))
                            ),
                        ),
                    )
                else:
                    EricMessageBox.information(
                        None,
                        self.tr("Install Modules"),
                        self.tr(
                            "<p>Installation complete. No modules were installed.</p>"
                        ),
                    )
        else:
            EricMessageBox.information(
                None,
                self.tr("Install Modules"),
                self.tr("<p>No modules installation is required.</p>"),
            )

    @pyqtSlot()
    def __uninstallModules(self):
        """
        Private slot to uninstall modules from the connected device.
        """
        devicePath = self.__device.getWorkspace()
        libraryPath = os.path.join(devicePath, "lib")

        with EricOverrideCursor():
            backend = circup.DiskBackend(devicePath, circup.logger)
            deviceModules = backend.get_device_versions()
        modNames = {}
        for moduleItem, metadata in deviceModules.items():
            modNames[moduleItem.replace(".py", "").lower()] = metadata

        dlg = EricListSelectionDialog(
            sorted(modNames),
            title=self.tr("Uninstall Modules"),
            message=self.tr("Select the modules/packages to be uninstalled:"),
            checkBoxSelection=True,
            parent=self.__device.microPython,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            names = dlg.getSelection()
            for name in names:
                modulePath = modNames[name]["path"]
                if os.path.isdir(modulePath):
                    target = os.path.basename(os.path.dirname(modulePath))
                    targetPath = os.path.join(libraryPath, target)
                    # Remove the package directory.
                    shutil.rmtree(targetPath)
                else:
                    target = os.path.basename(modulePath)
                    targetPath = os.path.join(libraryPath, target)
                    # Remove the module file
                    os.remove(targetPath)

            EricMessageBox.information(
                None,
                self.tr("Uninstall Modules"),
                self.tr(
                    """<p>These modules/packages were uninstalled from the connected"""
                    """ device.{0}</p>"""
                ).format("""<ul><li>{0}</li></ul>""".format("</li><li>".join(names))),
            )

    @pyqtSlot()
    def __generateRequirements(self):
        """
        Private slot to generate requirements for the connected device.
        """
        from .RequirementsDialog import RequirementsDialog

        devicePath = self.__device.getWorkspace()

        cpyVersion, _board_id = circup.get_circuitpython_version(devicePath)
        circup.CPY_VERSION = cpyVersion

        dlg = RequirementsDialog(
            devicePath=devicePath, parent=self.__device.microPython
        )
        dlg.exec()

    @pyqtSlot()
    def __showCachePath(self):
        """
        Private slot to show the path used by 'circup' to store the downloaded bundles.
        """
        EricMessageBox.information(
            None,
            self.tr("Show Local Cache Path"),
            self.tr(
                "<p><b>circup</b> stores the downloaded CircuitPython bundles in this"
                " directory.</p><p>{0}</p>"
            ).format(circup.DATA_DIR),
        )


def isCircupAvailable():
    """
    Function to check for the availability of 'circup'.

    @return flag indicating the availability of 'circup'
    @rtype bool
    """
    global circup

    return circup is not None
