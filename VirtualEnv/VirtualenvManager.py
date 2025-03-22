# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to manage Python virtual environments.
"""

import contextlib
import copy
import json
import os
import shutil
import sys

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities, PythonUtilities
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

from .VirtualenvMeta import VirtualenvMetaData


class VirtualenvManager(QObject):
    """
    Class implementing an object to manage Python virtual environments.

    @signal virtualEnvironmentAdded() emitted to indicate the addition of
        a virtual environment
    @signal virtualEnvironmentRemoved() emitted to indicate the removal and
        deletion of a virtual environment
    @signal virtualEnvironmentChanged(name) emitted to indicate a change of
        a virtual environment
    @signal virtualEnvironmentsListChanged() emitted to indicate a change of
        the list of virtual environments (may be used to refresh the list)
    """

    DefaultKey = "<default>"
    SystemKey = "<system>"

    virtualEnvironmentAdded = pyqtSignal()
    virtualEnvironmentRemoved = pyqtSignal()
    virtualEnvironmentChanged = pyqtSignal(str)

    virtualEnvironmentsListChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QWidget
        """
        super().__init__(parent)

        self.__ui = parent

        self.__loadSettings()

    def __loadSettings(self):
        """
        Private slot to load the virtual environments.
        """
        self.__virtualEnvironmentsBaseDir = Preferences.getSettings().value(
            "PyVenv/VirtualEnvironmentsBaseDir", ""
        )

        venvString = Preferences.getSettings().value(
            "PyVenv/VirtualEnvironments", "{}"  # __IGNORE_WARNING_M613__
        )
        environments = json.loads(venvString)

        self.__virtualEnvironments = {}
        # each environment entry is a dictionary:
        #   path:           the directory of the virtual environment
        #                   (empty for a global environment)
        #   interpreter:    the path of the Python interpreter
        #   variant:        Python variant (always 3)
        #   is_global:      a flag indicating a global environment
        #   is_conda:       a flag indicating an Anaconda environment
        #   is_remote:      a flag indicating a remotely accessed environment
        #   is_eric_server  a flag indicating an eric-ide server environment
        #   eric_server     a string giving the server name in case of an
        #                   eric-ide server environment
        #   exec_path:      a string to be prefixed to the PATH environment
        #                   setting
        #   description     a description of the environment
        #
        for venvName in environments:
            environment = environments[venvName]
            environment["name"] = venvName
            if (
                environment["is_remote"]
                or os.access(environment["interpreter"], os.X_OK)
            ) and "is_global" not in environment:
                environment["is_global"] = environment["path"] == ""

            self.__virtualEnvironments[venvName] = VirtualenvMetaData.from_dict(
                environment
            )

        # check, if the interpreter used to run eric is in the environments
        defaultPy = PythonUtilities.getPythonExecutable()
        if "{0}.venv{0}".format(os.sep) not in defaultPy:
            # only check for a non-embedded environment
            found = False
            for venvName in self.__virtualEnvironments:
                interpreter = self.__virtualEnvironments[venvName].interpreter
                with contextlib.suppress(OSError):
                    if not FileSystemUtilities.isRemoteFileName(
                        interpreter
                    ) and os.path.samefile(defaultPy, interpreter):
                        found = True
                        break
            if not found:
                # add an environment entry for the default interpreter
                self.__virtualEnvironments[VirtualenvManager.DefaultKey] = (
                    VirtualenvMetaData(
                        name=VirtualenvManager.DefaultKey,
                        interpreter=defaultPy,
                        is_global=True,
                    )
                )

        self.__cleanEnvironments()

        self.__saveSettings()

    def __saveSettings(self):
        """
        Private slot to save the virtual environments.
        """
        Preferences.getSettings().setValue(
            "PyVenv/VirtualEnvironmentsBaseDir", self.__virtualEnvironmentsBaseDir
        )

        Preferences.getSettings().setValue(
            "PyVenv/VirtualEnvironments",
            json.dumps(
                {env.name: env.as_dict() for env in self.__virtualEnvironments.values()}
            ),
        )
        Preferences.syncPreferences()

    @pyqtSlot()
    def reloadSettings(self):
        """
        Public slot to reload the virtual environments.
        """
        Preferences.syncPreferences()
        self.__loadSettings()

    def __cleanEnvironments(self):
        """
        Private method to delete all non-existent local or eric-ide server environments.
        """
        removed = False

        for venvName in list(self.__virtualEnvironments):
            venvItem = self.__virtualEnvironments[venvName]
            if not venvItem.is_remote:
                venvPath = venvItem.path
                if venvPath:
                    if venvItem.is_eric_server:
                        with contextlib.suppress(KeyError):
                            # It is an eric-ide server environment; check it is
                            # still valid.
                            ericServer = ericApp().getObject("EricServer")
                            if (
                                ericServer.isServerConnected()
                                and ericServer.getHost() == venvItem.eric_server
                                and not ericServer.getServiceInterface(
                                    "FileSystem"
                                ).exists(venvPath)
                            ):
                                del self.__virtualEnvironments[venvName]
                                removed = True
                    else:
                        # It is a local environment; check it is still valid.
                        if not os.path.exists(venvPath):
                            del self.__virtualEnvironments[venvName]
                            removed = True
        if removed:
            self.__saveSettings()
            self.virtualEnvironmentRemoved.emit()
            self.virtualEnvironmentsListChanged.emit()

    def getDefaultEnvironment(self):
        """
        Public method to get the default virtual environment.

        Default is an environment with the key '<default>' or the first one
        having an interpreter matching sys.executable (i.e. the one used to
        execute eric with)

        @return tuple containing the environment name and a copy of the metadata
            of the default virtual environment
        @rtype tuple of (str, VirtualenvMetaData)
        """
        if VirtualenvManager.DefaultKey in self.__virtualEnvironments:
            return (
                VirtualenvManager.DefaultKey,
                copy.copy(self.__virtualEnvironments[VirtualenvManager.DefaultKey]),
            )

        else:
            return self.environmentForInterpreter(sys.executable)

    def environmentForInterpreter(self, interpreter):
        """
        Public method to get the environment a given interpreter belongs to.

        @param interpreter path of the interpreter
        @type str
        @return tuple containing the environment name and a copy of the metadata
            of the virtual environment the interpreter belongs to
        @rtype tuple of (str, VirtualenvMetaData)
        """
        py = FileSystemUtilities.normcaseabspath(interpreter.replace("w.exe", ".exe"))
        for venvName in self.__virtualEnvironments:
            if py == FileSystemUtilities.normcaseabspath(
                self.__virtualEnvironments[venvName].interpreter
            ):
                return (venvName, copy.copy(self.__virtualEnvironments[venvName]))

        if os.path.samefile(interpreter, sys.executable):
            return (VirtualenvManager.SystemKey, {})

        return ("", {})

    @pyqtSlot()
    def createVirtualEnv(self, baseDir=""):
        """
        Public slot to create a new virtual environment.

        @param baseDir base directory for the virtual environments
        @type str
        """
        from .VirtualenvConfigurationDialog import VirtualenvConfigurationDialog
        from .VirtualenvExecDialog import VirtualenvExecDialog

        if not baseDir:
            baseDir = self.__virtualEnvironmentsBaseDir

        dlg = VirtualenvConfigurationDialog(baseDir=baseDir, parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            resultDict = dlg.getData()

            if resultDict["envType"] == "conda":
                # create the conda environment
                conda = ericApp().getObject("Conda")
                ok, prefix, interpreter = conda.createCondaEnvironment(
                    resultDict["arguments"]
                )
                if ok and "--dry-run" not in resultDict["arguments"]:
                    self.addVirtualEnv(
                        VirtualenvMetaData(
                            name=resultDict["logicalName"],
                            path=prefix,
                            interpreter=interpreter,
                            is_conda=True,
                        )
                    )
            else:
                # now do the call
                dia = VirtualenvExecDialog(resultDict, self, parent=self.__ui)
                dia.show()
                dia.start(resultDict["arguments"])
                dia.exec()

    @pyqtSlot()
    def upgradeVirtualEnv(self, venvName):
        """
        Public slot to upgrade a virtual environment.

        @param venvName name of the virtual environment
        @type str
        """
        from .VirtualenvUpgradeConfigurationDialog import (
            VirtualenvUpgradeConfigurationDialog,
        )
        from .VirtualenvUpgradeExecDialog import VirtualenvUpgradeExecDialog

        venvDirectory = self.getVirtualenvDirectory(venvName)
        if not os.path.exists(os.path.join(venvDirectory, "pyvenv.cfg")):
            # The environment was not created by the 'venv' module.
            return

        dlg = VirtualenvUpgradeConfigurationDialog(
            venvName, venvDirectory, parent=self.__ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pythonExe, args, createLog = dlg.getData()

            dia = VirtualenvUpgradeExecDialog(
                venvName, pythonExe, createLog, self, parent=self.__ui
            )
            dia.show()
            dia.start(args)
            dia.exec()

    def addVirtualEnv(self, metadata):
        """
        Public method to add a virtual environment.

        @param metadata object containing the metadata of the virtual environment
        @type VirtualenvMetaData
        """
        from .VirtualenvInterpreterSelectionDialog import (
            VirtualenvInterpreterSelectionDialog,
        )
        from .VirtualenvNameDialog import VirtualenvNameDialog

        if metadata.name in self.__virtualEnvironments:
            ok = EricMessageBox.yesNo(
                None,
                self.tr("Add Virtual Environment"),
                self.tr(
                    """A virtual environment named <b>{0}</b> exists"""
                    """ already. Shall it be replaced?"""
                ).format(metadata.name),
                icon=EricMessageBox.Warning,
            )
            if not ok:
                dlg = VirtualenvNameDialog(
                    list(self.__virtualEnvironments), metadata.name, parent=self.__ui
                )
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    return

                metadata.name = dlg.getName()

        if not metadata.interpreter:
            dlg = VirtualenvInterpreterSelectionDialog(
                metadata.name, metadata.path, parent=self.__ui
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                metadata.interpreter = dlg.getData()

        if metadata.interpreter:
            self.__virtualEnvironments[metadata.name] = metadata
            self.__saveSettings()

            self.virtualEnvironmentAdded.emit()
            self.virtualEnvironmentsListChanged.emit()

    def setVirtualEnv(self, metadata):
        """
        Public method to change a virtual environment.

        @param metadata object containing the metadata of the virtual environment
        @type VirtualenvMetaData
        """
        if metadata.name not in self.__virtualEnvironments:
            EricMessageBox.yesNo(
                None,
                self.tr("Change Virtual Environment"),
                self.tr(
                    """A virtual environment named <b>{0}</b> does not"""
                    """ exist. Aborting!"""
                ).format(metadata.name),
                icon=EricMessageBox.Warning,
            )
            return

        self.__virtualEnvironments[metadata.name] = metadata
        self.__saveSettings()

        self.virtualEnvironmentChanged.emit(metadata.name)
        self.virtualEnvironmentsListChanged.emit()

    def renameVirtualEnv(
        self,
        oldVenvName,
        metadata,
    ):
        """
        Public method to substitute a virtual environment entry with a new
        name.

        @param oldVenvName old name of the virtual environment
        @type str
        @param metadata object containing the metadata of the virtual environment
        @type VirtualenvMetaData
        """
        if oldVenvName not in self.__virtualEnvironments:
            EricMessageBox.yesNo(
                None,
                self.tr("Rename Virtual Environment"),
                self.tr(
                    """A virtual environment named <b>{0}</b> does not"""
                    """ exist. Aborting!"""
                ).format(oldVenvName),
                icon=EricMessageBox.Warning,
            )
            return

        del self.__virtualEnvironments[oldVenvName]
        self.addVirtualEnv(metadata)

    def deleteVirtualEnvs(self, venvNames):
        """
        Public method to delete virtual environments from the list and disk.

        @param venvNames list of logical names for the virtual environments
        @type list of str
        """
        venvMessages = []
        for venvName in venvNames:
            if venvName in self.__virtualEnvironments and bool(
                self.__virtualEnvironments[venvName].path
            ):
                venvMessages.append(
                    self.tr("{0} - {1}").format(
                        venvName, self.__virtualEnvironments[venvName].path
                    )
                )
        if venvMessages:
            dlg = DeleteFilesConfirmationDialog(
                self.__ui,
                self.tr("Delete Virtual Environments"),
                self.tr(
                    """Do you really want to delete these virtual"""
                    """ environments?"""
                ),
                venvMessages,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for venvName in venvNames:
                    if self.__isEnvironmentDeleteable(venvName):
                        if self.isCondaEnvironment(venvName):
                            conda = ericApp().getObject("Conda")
                            path = self.__virtualEnvironments[venvName].path
                            res = conda.removeCondaEnvironment(prefix=path)
                            if res:
                                del self.__virtualEnvironments[venvName]
                        else:
                            shutil.rmtree(
                                self.__virtualEnvironments[venvName].path,
                                ignore_errors=True,
                            )
                            del self.__virtualEnvironments[venvName]

                self.__saveSettings()

                self.virtualEnvironmentRemoved.emit()
                self.virtualEnvironmentsListChanged.emit()

    def __isEnvironmentDeleteable(self, venvName):
        """
        Private method to check, if a virtual environment can be deleted from
        disk.

        @param venvName name of the virtual environment
        @type str
        @return flag indicating it can be deleted
        @rtype bool
        """
        ok = False
        if venvName in self.__virtualEnvironments:
            ok = True
            ok &= bool(self.__virtualEnvironments[venvName].path)
            ok &= not self.__virtualEnvironments[venvName].is_global
            ok &= not self.__virtualEnvironments[venvName].is_remote
            ok &= not self.__virtualEnvironments[venvName].is_eric_server
            ok &= os.access(self.__virtualEnvironments[venvName].path, os.W_OK)

        return ok

    def removeVirtualEnvs(self, venvNames):
        """
        Public method to delete virtual environment from the list.

        @param venvNames list of logical names for the virtual environments
        @type list of str
        """
        venvMessages = []
        for venvName in venvNames:
            if venvName in self.__virtualEnvironments:
                venvMessages.append(
                    self.tr("{0} - {1}").format(
                        venvName, self.__virtualEnvironments[venvName].path
                    )
                )
        if venvMessages:
            dlg = DeleteFilesConfirmationDialog(
                self.__ui,
                self.tr("Remove Virtual Environments"),
                self.tr(
                    """Do you really want to remove these virtual"""
                    """ environments?"""
                ),
                venvMessages,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for venvName in venvNames:
                    if venvName in self.__virtualEnvironments:
                        del self.__virtualEnvironments[venvName]

                self.__saveSettings()

                self.virtualEnvironmentRemoved.emit()
                self.virtualEnvironmentsListChanged.emit()

    def searchUnregisteredInterpreters(self):
        """
        Public method to search for unregistered Python interpreters.

        @return list of unregistered interpreters
        @rtype list of str
        """
        interpreters = []
        baseDir = self.getVirtualEnvironmentsBaseDir()
        if not baseDir:
            # search in home directory, if no environments base directory is defined
            baseDir = OSUtilities.getHomeDir()
        environments = [
            os.path.join(baseDir, d)
            for d in os.listdir(baseDir)
            if os.path.isdir(os.path.join(baseDir, d))
        ]

        interpreters = PythonUtilities.searchInterpreters()
        if environments:
            interpreters += PythonUtilities.searchInterpreters(environments)

        interpreters = {
            i for i in interpreters if not self.environmentForInterpreter(i)[0]
        }  # filter the list into a set to make the remaining ones unique
        return list(interpreters)

    def getEnvironmentEntries(self):
        """
        Public method to get a list of the defined virtual environment entries.

        @return list containing a copy of the defined virtual environments
        @rtype list
        """
        return [copy.copy(env) for env in self.__virtualEnvironments.values()]

    @pyqtSlot()
    def showVirtualenvManagerDialog(self, modal=False):
        """
        Public slot to show the virtual environment manager dialog.

        @param modal flag indicating that the dialog should be shown in
            a blocking mode
        @type bool
        """
        from .VirtualenvManagerWidgets import VirtualenvManagerDialog

        if modal:
            virtualenvManagerDialog = VirtualenvManagerDialog(self, parent=self.__ui)
            virtualenvManagerDialog.exec()
            self.virtualEnvironmentsListChanged.emit()
        else:
            self.__ui.activateVirtualenvManager()

    def isUnique(self, venvName):
        """
        Public method to check, if the give logical name is unique.

        @param venvName logical name for the virtual environment
        @type str
        @return flag indicating uniqueness
        @rtype bool
        """
        return venvName not in self.__virtualEnvironments

    def getVirtualenvInterpreter(self, venvName):
        """
        Public method to get the interpreter for a virtual environment.

        @param venvName logical name for the virtual environment
        @type str
        @return interpreter path
        @rtype str
        """
        if venvName in self.__virtualEnvironments:
            return self.__virtualEnvironments[venvName].interpreter.replace(
                "w.exe", ".exe"
            )
        elif venvName == VirtualenvManager.SystemKey:
            return sys.executable.replace("w.exe", ".exe")
        else:
            return ""

    def setVirtualEnvInterpreter(self, venvName, venvInterpreter):
        """
        Public method to change the interpreter for a virtual environment.

        @param venvName logical name for the virtual environment
        @type str
        @param venvInterpreter interpreter path to be set
        @type str
        """
        if venvName in self.__virtualEnvironments:
            self.__virtualEnvironments[venvName].interpreter = venvInterpreter
            self.__saveSettings()

            self.virtualEnvironmentChanged.emit(venvName)
            self.virtualEnvironmentsListChanged.emit()

    def getVirtualenvDirectory(self, venvName):
        """
        Public method to get the directory of a virtual environment.

        @param venvName logical name for the virtual environment
        @type str
        @return directory path
        @rtype str
        """
        if venvName in self.__virtualEnvironments:
            return self.__virtualEnvironments[venvName].path
        else:
            return ""

    def getVirtualenvNames(
        self, noRemote=False, noConda=False, noGlobals=False, noServer=False
    ):
        """
        Public method to get a list of defined virtual environments.

        @param noRemote flag indicating to exclude environments for remote
            debugging (defaults to False)
        @type bool (optional)
        @param noConda flag indicating to exclude Conda environments (defaults to False)
        @type bool (optional)
        @param noGlobals flag indicating to exclude global environments
            (defaults to False)
        @type bool (optional)
        @param noServer flag indicating to exclude eric-ide server environments
            (defaults to False)
        @type bool (optional)
        @return list of defined virtual environments
        @rtype list of str
        """
        environments = list(self.__virtualEnvironments)
        if noRemote:
            environments = [
                name for name in environments if not self.isRemoteEnvironment(name)
            ]
        if noConda:
            environments = [
                name for name in environments if not self.isCondaEnvironment(name)
            ]
        if noGlobals:
            environments = [
                name for name in environments if not self.isGlobalEnvironment(name)
            ]
        if noServer:
            environments = [
                name for name in environments if not self.isEricServerEnvironment(name)
            ]

        return environments

    def isGlobalEnvironment(self, venvName):
        """
        Public method to test, if a given environment is a global one.

        @param venvName logical name of the virtual environment
        @type str
        @return flag indicating a global environment
        @rtype bool
        """
        try:
            return self.__virtualEnvironments[venvName].is_global
        except KeyError:
            return False

    def isCondaEnvironment(self, venvName):
        """
        Public method to test, if a given environment is an Anaconda
        environment.

        @param venvName logical name of the virtual environment
        @type str
        @return flag indicating an Anaconda environment
        @rtype bool
        """
        try:
            return self.__virtualEnvironments[venvName].is_conda
        except KeyError:
            return False

    def isRemoteEnvironment(self, venvName):
        """
        Public method to test, if a given environment is a remotely accessed
        environment.

        @param venvName logical name of the virtual environment
        @type str
        @return flag indicating a remotely accessed environment
        @rtype bool
        """
        try:
            return self.__virtualEnvironments[venvName].is_remote
        except KeyError:
            return False

    def getVirtualenvExecPath(self, venvName):
        """
        Public method to get the search path prefix of a virtual environment.

        @param venvName logical name for the virtual environment
        @type str
        @return search path prefix
        @rtype str
        """
        try:
            return self.__virtualEnvironments[venvName].exec_path
        except KeyError:
            return ""

    def setVirtualEnvironmentsBaseDir(self, baseDir):
        """
        Public method to set the base directory for the virtual environments.

        @param baseDir base directory for the virtual environments
        @type str
        """
        self.__virtualEnvironmentsBaseDir = baseDir
        self.__saveSettings()

    def getVirtualEnvironmentsBaseDir(self):
        """
        Public method to set the base directory for the virtual environments.

        @return base directory for the virtual environments
        @rtype str
        """
        return self.__virtualEnvironmentsBaseDir

    def isEricServerEnvironment(self, venvName, host=""):
        """
        Public method to test, if a given environment is an environment accessed
        through an eric-ide server.

        @param venvName logical name of the virtual environment
        @type str
        @param host name of the host to check for or empty string to just check for
            an eric-ide server environment (defaults to "")
        @type str (optional)
        @return flag indicating an eric-ide server environment
        @rtype bool
        """
        try:
            if host:
                return self.__virtualEnvironments[
                    venvName
                ].is_eric_server and self.__virtualEnvironments[
                    venvName
                ].eric_server.startswith(
                    f"{host}:"
                )
            else:
                return self.__virtualEnvironments[venvName].is_eric_server
        except KeyError:
            return False

    def getEricServerEnvironmentNames(self, host=""):
        """
        Public method to get a list of defined eric-ide server environments.

        @param host host name to get environment names for (defaults to "")
        @type str (optional)
        @return list of defined eric-ide server environments
        @rtype list of str
        """
        environments = [
            name
            for name in self.__virtualEnvironments
            if self.isEricServerEnvironment(name, host=host)
        ]

        return environments
