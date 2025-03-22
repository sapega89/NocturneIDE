# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing the conda GUI logic.
"""

import contextlib
import json
import os

from PyQt6.QtCore import QCoreApplication, QObject, QProcess, pyqtSignal
from PyQt6.QtWidgets import QDialog

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.SystemUtilities import OSUtilities

from . import condaVersion, rootPrefix
from .CondaExecDialog import CondaExecDialog


class Conda(QObject):
    """
    Class implementing the conda GUI logic.

    @signal condaEnvironmentCreated() emitted to indicate the creation of
        a new environment
    @signal condaEnvironmentRemoved() emitted to indicate the removal of
        an environment
    """

    condaEnvironmentCreated = pyqtSignal()
    condaEnvironmentRemoved = pyqtSignal()

    RootName = QCoreApplication.translate("Conda", "<root>")

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent
        @type QObject
        """
        super().__init__(parent)

        self.__ui = parent

    #######################################################################
    ## environment related methods below
    #######################################################################

    def createCondaEnvironment(self, arguments):
        """
        Public method to create a conda environment.

        @param arguments list of command line arguments
        @type list of str
        @return tuple containing a flag indicating success, the directory of
            the created environment (aka. prefix) and the corresponding Python
            interpreter
        @rtype tuple of (bool, str, str)
        """
        args = ["create", "--json", "--yes"] + arguments

        dlg = CondaExecDialog("create", parent=self.__ui)
        dlg.start(args)
        dlg.exec()
        ok, resultDict = dlg.getResult()

        if ok:
            if "actions" in resultDict and "PREFIX" in resultDict["actions"]:
                prefix = resultDict["actions"]["PREFIX"]
            else:
                prefix = resultDict.get("prefix", resultDict.get("dst_prefix", ""))

            # determine Python executable
            if prefix:
                pathPrefixes = [prefix, rootPrefix()]
            else:
                pathPrefixes = [rootPrefix()]
            for pathPrefix in pathPrefixes:
                python = (
                    os.path.join(pathPrefix, "python.exe")
                    if OSUtilities.isWindowsPlatform()
                    else os.path.join(pathPrefix, "bin", "python")
                )
                if os.path.exists(python):
                    break
            else:
                python = ""

            self.condaEnvironmentCreated.emit()
            return True, prefix, python
        else:
            return False, "", ""

    def removeCondaEnvironment(self, name="", prefix=""):
        """
        Public method to remove a conda environment.

        @param name name of the environment
        @type str
        @param prefix prefix of the environment
        @type str
        @return flag indicating success
        @rtype bool
        @exception RuntimeError raised to indicate an error in parameters

        Note: only one of name or prefix must be given.
        """
        if name and prefix:
            raise RuntimeError("Only one of 'name' or 'prefix' must be given.")

        if not name and not prefix:
            raise RuntimeError("One of 'name' or 'prefix' must be given.")

        args = [
            "remove",
            "--json",
            "--quiet",
            "--all",
        ]
        if name:
            args.extend(["--name", name])
        elif prefix:
            args.extend(["--prefix", prefix])

        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        proc = QProcess()
        proc.start(exe, args)
        if not proc.waitForStarted(15000):
            EricMessageBox.critical(
                self.__ui,
                self.tr("conda remove"),
                self.tr("""The conda executable could not be started."""),
            )
            return False
        else:
            proc.waitForFinished(15000)
            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            try:
                jsonDict = json.loads(output)
            except Exception:
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("conda remove"),
                    self.tr("""The conda executable returned invalid data."""),
                )
                return False

            if "error" in jsonDict:
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("conda remove"),
                    self.tr(
                        "<p>The conda executable returned an error.</p><p>{0}</p>"
                    ).format(jsonDict["message"]),
                )
                return False

            if jsonDict["success"]:
                self.condaEnvironmentRemoved.emit()

            return jsonDict["success"]

        return False

    def getCondaEnvironmentsList(self):
        """
        Public method to get a list of all Conda environments.

        @return list of tuples containing the environment name and prefix
        @rtype list of tuples of (str, str)
        """
        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        environmentsList = []

        proc = QProcess()
        proc.start(exe, ["info", "--json"])
        if proc.waitForStarted(15000) and proc.waitForFinished(15000):
            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            try:
                jsonDict = json.loads(output)
            except Exception:
                jsonDict = {}

            if "envs" in jsonDict:
                for prefix in jsonDict["envs"][:]:
                    if prefix == jsonDict["root_prefix"]:
                        if not jsonDict["root_writable"]:
                            # root prefix is listed but not writable
                            continue
                        name = self.RootName
                    else:
                        name = os.path.basename(prefix)

                    environmentsList.append((name, prefix))

        return environmentsList

    #######################################################################
    ## package related methods below
    #######################################################################

    def getInstalledPackages(self, name="", prefix=""):
        """
        Public method to get a list of installed packages of a conda
        environment.

        @param name name of the environment
        @type str
        @param prefix prefix of the environment
        @type str
        @return list of installed packages. Each entry is a tuple containing
            the package name, version and build.
        @rtype list of tuples of (str, str, str)
        @exception RuntimeError raised to indicate an error in parameters

        Note: only one of name or prefix must be given.
        """
        if name and prefix:
            raise RuntimeError("Only one of 'name' or 'prefix' must be given.")

        if not name and not prefix:
            raise RuntimeError("One of 'name' or 'prefix' must be given.")

        args = [
            "list",
            "--json",
        ]
        if name:
            args.extend(["--name", name])
        elif prefix:
            args.extend(["--prefix", prefix])

        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        packages = []

        proc = QProcess()
        proc.start(exe, args)
        if proc.waitForStarted(15000) and proc.waitForFinished(30000):
            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            try:
                jsonList = json.loads(output)
            except Exception:
                jsonList = []

            for package in jsonList:
                if isinstance(package, dict):
                    packages.append(
                        (package["name"], package["version"], package["build_string"])
                    )
                else:
                    parts = package.rsplit("-", 2)
                    while len(parts) < 3:
                        parts.append("")
                    packages.append(tuple(parts))

        return packages

    def getUpdateablePackages(self, name="", prefix=""):
        """
        Public method to get a list of updateable packages of a conda
        environment.

        @param name name of the environment
        @type str
        @param prefix prefix of the environment
        @type str
        @return list of installed packages. Each entry is a tuple containing
            the package name, version and build.
        @rtype list of tuples of (str, str, str)
        @exception RuntimeError raised to indicate an error in parameters

        Note: only one of name or prefix must be given.
        """
        if name and prefix:
            raise RuntimeError("Only one of 'name' or 'prefix' must be given.")

        if not name and not prefix:
            raise RuntimeError("One of 'name' or 'prefix' must be given.")

        args = [
            "update",
            "--json",
            "--quiet",
            "--all",
            "--dry-run",
        ]
        if name:
            args.extend(["--name", name])
        elif prefix:
            args.extend(["--prefix", prefix])

        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        packages = []

        proc = QProcess()
        proc.start(exe, args)
        if proc.waitForStarted(15000) and proc.waitForFinished(30000):
            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            try:
                jsonDict = json.loads(output)
            except Exception:
                jsonDict = {}

            if "actions" in jsonDict and "LINK" in jsonDict["actions"]:
                for linkEntry in jsonDict["actions"]["LINK"]:
                    if isinstance(linkEntry, dict):
                        packages.append(
                            (
                                linkEntry["name"],
                                linkEntry["version"],
                                linkEntry["build_string"],
                            )
                        )
                    else:
                        package = linkEntry.split()[0]
                        parts = package.rsplit("-", 2)
                        while len(parts) < 3:
                            parts.append("")
                        packages.append(tuple(parts))

        return packages

    def updatePackages(self, packages, name="", prefix=""):
        """
        Public method to update packages of a conda environment.

        @param packages list of package names to be updated
        @type list of str
        @param name name of the environment
        @type str
        @param prefix prefix of the environment
        @type str
        @return flag indicating success
        @rtype bool
        @exception RuntimeError raised to indicate an error in parameters

        Note: only one of name or prefix must be given.
        """
        if name and prefix:
            raise RuntimeError("Only one of 'name' or 'prefix' must be given.")

        if not name and not prefix:
            raise RuntimeError("One of 'name' or 'prefix' must be given.")

        if packages:
            args = [
                "update",
                "--json",
                "--yes",
            ]
            if name:
                args.extend(["--name", name])
            elif prefix:
                args.extend(["--prefix", prefix])
            args.extend(packages)

            dlg = CondaExecDialog("update", parent=self.__ui)
            dlg.start(args)
            dlg.exec()
            ok, _ = dlg.getResult()
        else:
            ok = False

        return ok

    def updateAllPackages(self, name="", prefix=""):
        """
        Public method to update all packages of a conda environment.

        @param name name of the environment
        @type str
        @param prefix prefix of the environment
        @type str
        @return flag indicating success
        @rtype bool
        @exception RuntimeError raised to indicate an error in parameters

        Note: only one of name or prefix must be given.
        """
        if name and prefix:
            raise RuntimeError("Only one of 'name' or 'prefix' must be given.")

        if not name and not prefix:
            raise RuntimeError("One of 'name' or 'prefix' must be given.")

        args = ["update", "--json", "--yes", "--all"]
        if name:
            args.extend(["--name", name])
        elif prefix:
            args.extend(["--prefix", prefix])

        dlg = CondaExecDialog("update", parent=self.__ui)
        dlg.start(args)
        dlg.exec()
        ok, _ = dlg.getResult()

        return ok

    def installPackages(self, packages, name="", prefix=""):
        """
        Public method to install packages into a conda environment.

        @param packages list of package names to be installed
        @type list of str
        @param name name of the environment
        @type str
        @param prefix prefix of the environment
        @type str
        @return flag indicating success
        @rtype bool
        @exception RuntimeError raised to indicate an error in parameters

        Note: only one of name or prefix must be given.
        """
        if name and prefix:
            raise RuntimeError("Only one of 'name' or 'prefix' must be given.")

        if not name and not prefix:
            raise RuntimeError("One of 'name' or 'prefix' must be given.")

        if packages:
            args = [
                "install",
                "--json",
                "--yes",
            ]
            if name:
                args.extend(["--name", name])
            elif prefix:
                args.extend(["--prefix", prefix])
            args.extend(packages)

            dlg = CondaExecDialog("install", parent=self.__ui)
            dlg.start(args)
            dlg.exec()
            ok, _ = dlg.getResult()
        else:
            ok = False

        return ok

    def uninstallPackages(self, packages, name="", prefix=""):
        """
        Public method to uninstall packages of a conda environment (including
        all no longer needed dependencies).

        @param packages list of package names to be uninstalled
        @type list of str
        @param name name of the environment
        @type str
        @param prefix prefix of the environment
        @type str
        @return flag indicating success
        @rtype bool
        @exception RuntimeError raised to indicate an error in parameters

        Note: only one of name or prefix must be given.
        """
        from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

        if name and prefix:
            raise RuntimeError("Only one of 'name' or 'prefix' must be given.")

        if not name and not prefix:
            raise RuntimeError("One of 'name' or 'prefix' must be given.")

        if packages:
            dlg = DeleteFilesConfirmationDialog(
                self.parent(),
                self.tr("Uninstall Packages"),
                self.tr(
                    "Do you really want to uninstall these packages and"
                    " their dependencies?"
                ),
                packages,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                args = [
                    "remove",
                    "--json",
                    "--yes",
                ]
                if condaVersion() >= (4, 4, 0):
                    args.append(
                        "--prune",
                    )
                if name:
                    args.extend(["--name", name])
                elif prefix:
                    args.extend(["--prefix", prefix])
                args.extend(packages)

                dlg = CondaExecDialog("remove", parent=self.__ui)
                dlg.start(args)
                dlg.exec()
                ok, _ = dlg.getResult()
            else:
                ok = False
        else:
            ok = False

        return ok

    def searchPackages(
        self,
        pattern,
        fullNameOnly=False,
        packageSpec=False,
        platform="",
        name="",
        prefix="",
    ):
        """
        Public method to search for a package pattern of a conda environment.

        @param pattern package search pattern
        @type str
        @param fullNameOnly flag indicating to search for full names only
        @type bool
        @param packageSpec flag indicating to search a package specification
        @type bool
        @param platform type of platform to be searched for
        @type str
        @param name name of the environment
        @type str
        @param prefix prefix of the environment
        @type str
        @return flag indicating success and a dictionary with package name as
            key and list of dictionaries containing detailed data for the found
            packages as values
        @rtype tuple of (bool, dict of list of dict)
        @exception RuntimeError raised to indicate an error in parameters

        Note: only one of name or prefix must be given.
        """
        if name and prefix:
            raise RuntimeError("Only one of 'name' or 'prefix' must be given.")

        args = [
            "search",
            "--json",
        ]
        if fullNameOnly:
            args.append("--full-name")
        if packageSpec:
            args.append("--spec")
        if platform:
            args.extend(["--platform", platform])
        if name:
            args.extend(["--name", name])
        elif prefix:
            args.extend(["--prefix", prefix])
        args.append(pattern)

        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        packages = {}
        ok = False

        proc = QProcess()
        proc.start(exe, args)
        if proc.waitForStarted(15000) and proc.waitForFinished(30000):
            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            with contextlib.suppress(json.JSONDecodeError):
                packages = json.loads(output)
                ok = "error" not in packages

        return ok, packages

    #######################################################################
    ## special methods below
    #######################################################################

    def updateConda(self):
        """
        Public method to update conda itself.

        @return flag indicating success
        @rtype bool
        """
        args = [
            "update",
            "--json",
            "--yes",
            "--name",
            "base",
            "--channel",
            "defaults",
            "conda",
        ]

        dlg = CondaExecDialog("update", parent=self.__ui)
        dlg.start(args)
        dlg.exec()
        ok, _ = dlg.getResult()

        return ok

    def writeDefaultConfiguration(self):
        """
        Public method to create a conda configuration with default values.
        """
        args = ["config", "--write-default", "--quiet"]

        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        proc = QProcess()
        proc.start(exe, args)
        proc.waitForStarted(15000)
        proc.waitForFinished(30000)

    def getCondaInformation(self):
        """
        Public method to get a dictionary containing information about conda.

        @return dictionary containing information about conda
        @rtype dict
        """
        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        infoDict = {}

        proc = QProcess()
        proc.start(exe, ["info", "--json"])
        if proc.waitForStarted(15000) and proc.waitForFinished(30000):
            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            try:
                infoDict = json.loads(output)
            except Exception:
                infoDict = {}

        return infoDict

    def runProcess(self, args):
        """
        Public method to execute the conda with the given arguments.

        The conda executable is called with the given arguments and
        waited for its end.

        @param args list of command line arguments
        @type list of str
        @return tuple containing a flag indicating success and the output
            of the process
        @rtype tuple of (bool, str)
        """
        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        process = QProcess()
        process.start(exe, args)
        procStarted = process.waitForStarted(15000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished:
                if process.exitCode() == 0:
                    output = str(
                        process.readAllStandardOutput(),
                        Preferences.getSystem("IOEncoding"),
                        "replace",
                    ).strip()
                    return True, output
                else:
                    return (
                        False,
                        self.tr("conda exited with an error ({0}).").format(
                            process.exitCode()
                        ),
                    )
            else:
                process.terminate()
                process.waitForFinished(2000)
                process.kill()
                process.waitForFinished(3000)
                return False, self.tr("conda did not finish within 3 seconds.")

        return False, self.tr("conda could not be started.")

    def cleanConda(self, cleanAction):
        """
        Public method to update conda itself.

        @param cleanAction cleaning action to be performed (must be one of
            the command line parameters without '--')
        @type str
        """
        args = [
            "clean",
            "--yes",
            "--{0}".format(cleanAction),
        ]

        dlg = CondaExecDialog("clean", parent=self.__ui)
        dlg.start(args)
        dlg.exec()
