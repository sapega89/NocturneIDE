# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an abstract base class to be subclassed by all specific
VCS interfaces.
"""

import contextlib
import enum
import json
import os

from PyQt6.QtCore import (
    QCoreApplication,
    QLockFile,
    QMutex,
    QObject,
    QProcess,
    Qt,
    QThread,
    pyqtSignal,
)
from PyQt6.QtWidgets import QApplication

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp


class VersionControlState(enum.Enum):
    """
    Class defining the global VCS states of files and directories.
    """

    Controlled = 0
    Uncontrolled = 1


class VersionControl(QObject):
    """
    Class implementing an abstract base class to be subclassed by all specific
    VCS interfaces.

    It defines the vcs interface to be implemented by subclasses
    and the common methods.

    @signal committed() emitted after the commit action has completed
    @signal vcsStatusMonitorData(list of str) emitted to update the VCS status
    @signal vcsStatusMonitorAllData(dict) emitted to signal all VCS status
        (key is project relative file name, value is status)
    @signal vcsStatusMonitorStatus(str, str) emitted to signal the status of
        the monitoring thread (ok, nok, op, off) and a status message
    @signal vcsStatusMonitorInfo(str) emitted to signal some info of the
        monitoring thread
    @signal vcsStatusChanged() emitted to indicate a change of the overall
        VCS status
    """

    committed = pyqtSignal()
    vcsStatusMonitorData = pyqtSignal(list)
    vcsStatusMonitorAllData = pyqtSignal(dict)
    vcsStatusMonitorStatus = pyqtSignal(str, str)
    vcsStatusMonitorInfo = pyqtSignal(str)
    vcsStatusChanged = pyqtSignal()

    commitHistoryLock = "commitHistory.lock"
    commitHistoryData = "commitHistory.json"

    def __init__(self, parent=None, name=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        @param name name of this object
        @type str
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.defaultOptions = {
            "global": [""],
            "commit": [""],
            "checkout": [""],
            "update": [""],
            "add": [""],
            "remove": [""],
            "diff": [""],
            "log": [""],
            "history": [""],
            "status": [""],
            "tag": [""],
            "export": [""],
        }
        self.interestingDataKeys = []
        self.options = {}
        self.otherData = {}
        self.canDetectBinaries = True

        self.statusMonitorThread = None
        self.vcsExecutionMutex = QMutex()

    def vcsShutdown(self):
        """
        Public method used to shutdown the vcs interface.

        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsExists(self):
        """
        Public method used to test for the presence of the vcs.

        @return tuple of flag indicating the existence and an error message
            in case of failure
        @rtype tuple of (bool, str)
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return (False, "")

    def vcsInit(self, vcsDir, noDialog=False):
        """
        Public method used to initialize the vcs.

        @param vcsDir name of the VCS directory
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating success
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsConvertProject(self, vcsDataDict, project, addAll=True):
        """
        Public method to convert an uncontrolled project to a version
        controlled project.

        @param vcsDataDict dictionary of data required for the conversion
        @type dict
        @param project reference to the project object
        @type Project
        @param addAll flag indicating to add all files to the repository
        @type bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsImport(self, vcsDataDict, projectDir, noDialog=False, addAll=True):
        """
        Public method used to import the project into the vcs.

        @param vcsDataDict dictionary of data required for the import
        @type dict
        @param projectDir project directory
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        @param addAll flag indicating to add all files to the repository
        @type bool
        @return tuple containing a flag indicating an execution without errors
            and a flag indicating the version control status
        @rtype tuple of (bool, bool)
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return (False, False)

    def vcsCheckout(self, vcsDataDict, projectDir, noDialog=False):
        """
        Public method used to check the project out of the vcs.

        @param vcsDataDict dictionary of data required for the checkout
        @type dict
        @param projectDir project directory to create
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating an execution without errors
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsExport(self, vcsDataDict, projectDir):
        """
        Public method used to export a directory from the vcs.

        @param vcsDataDict dictionary of data required for the export
        @type dict
        @param projectDir project directory to create
        @type str
        @return flag indicating an execution without errors
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsCommit(self, name, message, noDialog=False):
        """
        Public method used to make the change of a file/directory permanent in
        the vcs.

        @param name file/directory name to be committed
        @type str
        @param message message for this operation
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating success
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsCommitMessages(self):
        """
        Public method to get the list of saved commit messages.

        @return list of saved commit messages
        @rtype list of str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return []

    def _vcsProjectCommitMessages(self):
        """
        Protected method to get the list of saved commit messages.

        @return list of saved commit messages
        @rtype list of str
        """
        messages = []
        if Preferences.getVCS("PerProjectCommitHistory"):
            projectMgmtDir = ericApp().getObject("Project").getProjectManagementDir()
            with contextlib.suppress(OSError, json.JSONDecodeError):
                with open(
                    os.path.join(projectMgmtDir, VersionControl.commitHistoryData), "r"
                ) as f:
                    jsonString = f.read()
                messages = json.loads(jsonString)

        return messages

    def vcsAddCommitMessage(self, message):
        """
        Public method to add a commit message to the list of saved messages.

        @param message message to be added
        @type str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def _vcsAddProjectCommitMessage(self, message):
        """
        Protected method to add a commit message to the list of project
        specific saved messages.

        @param message message to be added
        @type str
        @return flag indicating success
        @rtype bool
        """
        if Preferences.getVCS("PerProjectCommitHistory"):
            projectMgmtDir = ericApp().getObject("Project").getProjectManagementDir()
            lockFile = QLockFile(
                os.path.join(projectMgmtDir, VersionControl.commitHistoryLock)
            )
            if lockFile.lock():
                noMessages = Preferences.getVCS("CommitMessages")
                messages = self.vcsCommitMessages()
                if message in messages:
                    messages.remove(message)
                messages.insert(0, message)
                del messages[noMessages:]

                with contextlib.suppress(TypeError, OSError):
                    jsonString = json.dumps(messages, indent=2) + "\n"
                    with open(
                        os.path.join(projectMgmtDir, VersionControl.commitHistoryData),
                        "w",
                    ) as f:
                        f.write(jsonString)
                lockFile.unlock()
                return True

        return False

    def vcsClearCommitMessages(self):
        """
        Public method to clear the list of saved messages.

        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def _vcsClearProjectCommitMessages(self):
        """
        Protected method to clear the list of project specific saved messages.

        @return flag indicating success
        @rtype bool
        """
        if Preferences.getVCS("PerProjectCommitHistory"):
            projectMgmtDir = ericApp().getObject("Project").getProjectManagementDir()
            lockFile = QLockFile(
                os.path.join(projectMgmtDir, VersionControl.commitHistoryLock)
            )
            if lockFile.lock():
                with contextlib.suppress(TypeError, OSError):
                    jsonString = json.dumps([], indent=2) + "\n"
                    with open(
                        os.path.join(projectMgmtDir, VersionControl.commitHistoryData),
                        "w",
                    ) as f:
                        f.write(jsonString)
                lockFile.unlock()
                return True

        return False

    def vcsUpdate(self, name, noDialog=False):
        """
        Public method used to update a file/directory in the vcs.

        @param name file/directory name to be updated
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating, that the update contained an add
            or delete
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsAdd(self, name, isDir=False, noDialog=False):
        """
        Public method used to add a file/directory in the vcs.

        @param name file/directory name to be added
        @type str
        @param isDir flag indicating name is a directory
        @type bool
        @param noDialog flag indicating quiet operations
        @type bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsAddBinary(self, name, isDir=False):
        """
        Public method used to add a file/directory in binary mode in the vcs.

        @param name file/directory name to be added
        @type str
        @param isDir flag indicating name is a directory
        @type bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsAddTree(self, path):
        """
        Public method to add a directory tree rooted at path in the vcs.

        @param path root directory of the tree to be added
        @type str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsRemove(self, name, project=False, noDialog=False):
        """
        Public method used to add a file/directory in the vcs.

        @param name file/directory name to be removed
        @type str
        @param project flag indicating deletion of a project tree
        @type bool
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating success
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsMove(self, name, project, target=None, noDialog=False):
        """
        Public method used to move a file/directory.

        @param name file/directory name to be moved
        @type str
        @param project reference to the project object
        @type Project
        @param target new name of the file/directory
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating successfull operation
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsLogBrowser(self, name, isFile=False):
        """
        Public method used to view the log of a file/directory in the vcs
        with a log browser dialog.

        @param name file/directory name to show the log for
        @type str
        @param isFile flag indicating log for a file is to be shown
        @type bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsDiff(self, name):
        """
        Public method used to view the diff of a file/directory in the vcs.

        @param name file/directory name to be diffed
        @type str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsSbsDiff(self, name, extended=False, revisions=None):
        """
        Public method used to view the difference of a file to the Mercurial
        repository side-by-side.

        @param name file name to be diffed
        @type str
        @param extended flag indicating the extended variant
        @type bool
        @param revisions tuple of two revisions
        @type tuple of two str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsStatus(self, name):
        """
        Public method used to view the status of a file/directory in the vcs.

        @param name file/directory name to show the status for
        @type str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsTag(self, name):
        """
        Public method used to set the tag of a file/directory in the vcs.

        @param name file/directory name to be tagged
        @type str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsRevert(self, name):
        """
        Public method used to revert changes made to a file/directory.

        @param name file/directory name to be reverted
        @type str
        @return flag indicating, that the update contained an add
            or delete
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsForget(self, name):
        """
        Public method used to remove a file from the repository.

        @param name file/directory name to be removed
        @type str or list of str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsSwitch(self, name):
        """
        Public method used to switch a directory to a different tag/branch.

        @param name directory name to be switched
        @type str
        @return flag indicating, that the switch contained an add
            or delete
        @rtype bool
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return False

    def vcsMerge(self, name):
        """
        Public method used to merge a tag/branch into the local project.

        @param name file/directory name to be merged
        @type str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsRegisteredState(self, name):
        """
        Public method used to get the registered state of a file in the vcs.

        @param name filename to check
        @type str
        @return registered state
        @rtype VersionControlState
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return 0

    def vcsAllRegisteredStates(self, names, dname):
        """
        Public method used to get the registered states of a number of files
        in the vcs.

        @param names dictionary with all filenames to be checked as keys
        @type dict
        @param dname directory to check in
        @type str
        @return the received dictionary completed with the VCS state or None in
            order to signal an error
        @rtype dict
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return {}

    def vcsName(self):
        """
        Public method returning the name of the vcs.

        @return name of the vcs
        @rtype str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return ""

    def vcsCleanup(self, name):
        """
        Public method used to cleanup the local copy.

        @param name directory name to be cleaned up
        @type str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsCommandLine(self, name):
        """
        Public method used to execute arbitrary vcs commands.

        @param name directory name of the working directory
        @type str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsOptionsDialog(self, project, archive, editable=False, parent=None):
        """
        Public method to get a dialog to enter repository info.

        @param project reference to the project object
        @type Project
        @param archive name of the project in the repository
        @type str
        @param editable flag indicating that the project name is editable
        @type bool
        @param parent parent widget
        @type QWidget
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsNewProjectOptionsDialog(self, parent=None):
        """
        Public method to get a dialog to enter repository info for getting a
        new project.

        @param parent parent widget
        @type QWidget
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def vcsRepositoryInfos(self, ppath):
        """
        Public method to retrieve information about the repository.

        @param ppath local path to get the repository infos
        @type str
        @return string with ready formated info for display
        @rtype str
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return ""

    def vcsGetProjectBrowserHelper(self, browser, project, isTranslationsBrowser=False):
        """
        Public method to instanciate a helper object for the different
        project browsers.

        @param browser reference to the project browser object
        @type ProjectBaseBrowser
        @param project reference to the project object
        @type Project
        @param isTranslationsBrowser flag indicating, the helper is requested
            for the translations browser (this needs some special treatment)
        @type bool
        @return the project browser helper object
        @rtype VcsProjectBrowserHelper
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return None  # __IGNORE_WARNING_M831__

    def vcsGetProjectHelper(self, project):
        """
        Public method to instanciate a helper object for the project.

        @param project reference to the project object
        @type Project
        @return the project helper object
        @rtype VcsProjectHelper
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

        return None  # __IGNORE_WARNING_M831__

    #####################################################################
    ## methods above need to be implemented by a subclass
    #####################################################################

    def clearStatusCache(self):
        """
        Public method to clear the status cache.
        """
        pass

    def vcsInitConfig(self, project):
        """
        Public method to initialize the VCS configuration.

        This method could ensure, that certain files or directories are
        exclude from being version controlled.

        @param project reference to the project
        @type Project
        """
        pass

    def vcsSupportCommandOptions(self):
        """
        Public method to signal the support of user settable command options.

        @return flag indicating the support  of user settable command options
        @rtype bool
        """
        return True

    def vcsSetOptions(self, options):
        """
        Public method used to set the options for the vcs.

        @param options a dictionary of option strings with keys as
            defined by the default options
        @type dict
        """
        if self.vcsSupportCommandOptions():
            for key in options:
                with contextlib.suppress(KeyError):
                    self.options[key] = options[key]

    def vcsGetOptions(self):
        """
        Public method used to retrieve the options of the vcs.

        @return a dictionary of option strings that can be passed to
            vcsSetOptions.
        @rtype dict
        """
        if self.vcsSupportCommandOptions():
            return self.options
        else:
            return self.defaultOptions

    def vcsSetOtherData(self, data):
        """
        Public method used to set vcs specific data.

        @param data a dictionary of vcs specific data
        @type dict
        """
        for key in data:
            with contextlib.suppress(KeyError):
                self.otherData[key] = data[key]

    def vcsGetOtherData(self):
        """
        Public method used to retrieve vcs specific data.

        @return a dictionary of vcs specific data
        @rtype dict
        """
        return self.otherData

    def vcsSetData(self, key, value):
        """
        Public method used to set an entry in the otherData dictionary.

        @param key the key of the data
        @type str
        @param value the value of the data
        @type Any
        """
        if key in self.interestingDataKeys:
            self.otherData[key] = value

    def vcsSetDataFromDict(self, dictionary):
        """
        Public method used to set entries in the otherData dictionary.

        @param dictionary dictionary to pick entries from
        @type dict
        """
        for key in self.interestingDataKeys:
            if key in dictionary:
                self.otherData[key] = dictionary[key]

    def vcsResolved(self, _name):
        """
        Public method used to resolve conflicts of a file/directory.

        @param _name file/directory name to be resolved (unused)
        @type str
        """
        # default implementation just refreshes the status
        self.checkVCSStatus()

    #####################################################################
    ## below are some utility methods
    #####################################################################

    def startSynchronizedProcess(self, proc, program, arguments, workingDir=None):
        """
        Public method to start a synchroneous process.

        This method starts a process and waits
        for its end while still serving the Qt event loop.

        @param proc process to start
        @type QProcess
        @param program path of the executable to start
        @type str
        @param arguments list of arguments for the process
        @type list of str
        @param workingDir working directory for the process
        @type str
        @return flag indicating normal exit
        @rtype bool
        """
        if proc is None:
            return False

        if workingDir:
            proc.setWorkingDirectory(workingDir)
        proc.start(program, arguments)
        procStarted = proc.waitForStarted(5000)
        if not procStarted:
            EricMessageBox.critical(
                None,
                QCoreApplication.translate(
                    "VersionControl", "Process Generation Error"
                ),
                QCoreApplication.translate(
                    "VersionControl",
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path.",
                ).format(program),
            )
            return False
        else:
            while proc.state() == QProcess.ProcessState.Running:
                QThread.msleep(300)
                QApplication.processEvents()
            return (proc.exitStatus() == QProcess.ExitStatus.NormalExit) and (
                proc.exitCode() == 0
            )

    def splitPath(self, name):
        """
        Public method splitting name into a directory part and a file part.

        @param name path name
        @type str
        @return tuple containing the directory name and the file name
        @rtype tuple of (str, str)
        """
        if os.path.isdir(name):
            dn = os.path.abspath(name)
            fn = "."
        else:
            dn, fn = os.path.split(name)
        return (dn, fn)

    def splitPathList(self, names):
        """
        Public method splitting the list of names into a common directory part
        and a file list.

        @param names list of paths
        @type list of str
        @return tuple containing the directory name and the file name list
        @rtype tuple of (str, list of str)
        """
        dname = os.path.commonprefix(names)
        if dname:
            if not dname.endswith(os.sep):
                dname = os.path.dirname(dname) + os.sep
            fnames = [n.replace(dname, "") for n in names]
            dname = os.path.dirname(dname)
            return (dname, fnames)
        else:
            return ("/", names)

    def addArguments(self, args, argslist):
        """
        Public method to add an argument list to the already present
        arguments.

        @param args current arguments list
        @type list of str
        @param argslist list of arguments
        @type list of str
        """
        for arg in argslist:
            if arg != "":
                args.append(arg)

    ###########################################################################
    ## VCS status monitor thread related methods
    ###########################################################################

    def __statusMonitorStatus(self, status, statusMsg):
        """
        Private slot to receive the status monitor status.

        It simply re-emits the received status.

        @param status status of the monitoring thread
        @type str (one of ok, nok or off)
        @param statusMsg explanotory text for the signaled status
        @type str
        """
        self.vcsStatusMonitorStatus.emit(status, statusMsg)
        QCoreApplication.processEvents()

    def __statusMonitorData(self, statusList):
        """
        Private method to receive the status monitor data update.

        It simply re-emits the received status list.

        @param statusList list of status records
        @type list of str
        """
        self.vcsStatusMonitorData.emit(statusList)
        QCoreApplication.processEvents()

    def __statusMonitorAllData(self, statusDict):
        """
        Private method to receive all status monitor data.

        It simply re-emits the received status list.

        @param statusDict dictionary of status records
        @type dict
        """
        self.vcsStatusMonitorAllData.emit(statusDict)
        QCoreApplication.processEvents()

    def __statusMonitorInfo(self, info):
        """
        Private slot to receive the status monitor info message.

        It simply re-emits the received info message.

        @param info received info message
        @type str
        """
        self.vcsStatusMonitorInfo.emit(info)
        QCoreApplication.processEvents()

    def startStatusMonitor(self, project):
        """
        Public method to start the VCS status monitor thread.

        @param project reference to the project object
        @type Project
        @return reference to the monitor thread
        @rtype QThread
        """
        vcsStatusMonitorInterval = (
            project.pudata["VCSSTATUSMONITORINTERVAL"]
            if project.pudata["VCSSTATUSMONITORINTERVAL"]
            else Preferences.getVCS("StatusMonitorInterval")
        )
        if vcsStatusMonitorInterval > 0:
            self.statusMonitorThread = self._createStatusMonitorThread(
                vcsStatusMonitorInterval, project
            )
            if self.statusMonitorThread is not None:
                self.statusMonitorThread.vcsStatusMonitorData.connect(
                    self.__statusMonitorData, Qt.ConnectionType.QueuedConnection
                )
                self.statusMonitorThread.vcsStatusMonitorAllData.connect(
                    self.__statusMonitorAllData, Qt.ConnectionType.QueuedConnection
                )
                self.statusMonitorThread.vcsStatusMonitorStatus.connect(
                    self.__statusMonitorStatus, Qt.ConnectionType.QueuedConnection
                )
                self.statusMonitorThread.vcsStatusMonitorInfo.connect(
                    self.__statusMonitorInfo, Qt.ConnectionType.QueuedConnection
                )
                self.statusMonitorThread.setAutoUpdate(Preferences.getVCS("AutoUpdate"))
                self.statusMonitorThread.start()
        else:
            self.statusMonitorThread = None
        return self.statusMonitorThread

    def stopStatusMonitor(self):
        """
        Public method to stop the VCS status monitor thread.
        """
        if self.statusMonitorThread is not None:
            self.__statusMonitorData(["--RESET--"])
            self.statusMonitorThread.vcsStatusMonitorData.disconnect(
                self.__statusMonitorData
            )
            self.statusMonitorThread.vcsStatusMonitorAllData.disconnect(
                self.__statusMonitorAllData
            )
            self.statusMonitorThread.vcsStatusMonitorStatus.disconnect(
                self.__statusMonitorStatus
            )
            self.statusMonitorThread.vcsStatusMonitorInfo.disconnect(
                self.__statusMonitorInfo
            )
            self.statusMonitorThread.stop()
            self.statusMonitorThread.wait(10000)
            if not self.statusMonitorThread.isFinished():
                self.statusMonitorThread.terminate()
                self.statusMonitorThread.wait(10000)
            self.statusMonitorThread = None
            self.__statusMonitorStatus(
                "off",
                QCoreApplication.translate(
                    "VersionControl", "Repository status checking is switched off"
                ),
            )
            self.__statusMonitorInfo("")

    def restartStatusMonitor(self, project):
        """
        Public method to re-start the VCS status monitor thread.

        @param project reference to the project object
        @type Project
        @return reference to the monitor thread
        @rtype QThread
        """
        self.stopStatusMonitor()
        return self.startStatusMonitor(project)

    def setStatusMonitorInterval(self, interval, project):
        """
        Public method to change the monitor interval.

        @param interval new interval in seconds
        @type int
        @param project reference to the project object
        @type Project
        """
        if self.statusMonitorThread is not None:
            if interval == 0:
                self.stopStatusMonitor()
            else:
                self.statusMonitorThread.setInterval(interval)
        else:
            self.startStatusMonitor(project)

    def getStatusMonitorInterval(self):
        """
        Public method to get the monitor interval.

        @return interval in seconds
        @rtype int
        """
        if self.statusMonitorThread is not None:
            return self.statusMonitorThread.getInterval()
        else:
            return 0

    def setStatusMonitorAutoUpdate(self, auto):
        """
        Public method to enable the auto update function.

        @param auto status of the auto update function
        @type bool
        """
        if self.statusMonitorThread is not None:
            self.statusMonitorThread.setAutoUpdate(auto)

    def getStatusMonitorAutoUpdate(self):
        """
        Public method to retrieve the status of the auto update function.

        @return status of the auto update function
        @rtype bool
        """
        if self.statusMonitorThread is not None:
            return self.statusMonitorThread.getAutoUpdate()
        else:
            return False

    def checkVCSStatus(self):
        """
        Public method to wake up the VCS status monitor thread.
        """
        self.vcsStatusChanged.emit()

        if self.statusMonitorThread is not None:
            self.statusMonitorThread.checkStatus()

    def clearStatusMonitorCachedState(self, name):
        """
        Public method to clear the cached VCS state of a file/directory.

        @param name name of the entry to be cleared
        @type str
        """
        if self.statusMonitorThread is not None:
            self.statusMonitorThread.clearCachedState(name)

    def _createStatusMonitorThread(self, interval, project):  # noqa: U100
        """
        Protected method to create an instance of the VCS status monitor
        thread.

        Note: This method should be overwritten in subclasses in order to
        support VCS status monitoring.

        @param interval check interval for the monitor thread in seconds (unused)
        @type int
        @param project reference to the project object (unused)
        @type Project
        @return reference to the monitor thread
        @rtype QThread
        """
        return None  # __IGNORE_WARNING_M831__
