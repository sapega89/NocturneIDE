# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS status monitor thread class for Git.
"""

from PyQt6.QtCore import QProcess

from eric7 import Preferences
from eric7.VCS.StatusMonitorThread import VcsStatusMonitorThread


class GitStatusMonitorThread(VcsStatusMonitorThread):
    """
    Class implementing the VCS status monitor thread class for Git.
    """

    ConflictStates = ["AA", "AU", "DD", "DU", "UA", "UD", "UU"]

    def __init__(self, interval, project, vcs, parent=None):
        """
        Constructor

        @param interval new interval in seconds
        @type int
        @param project reference to the project object
        @type Project
        @param vcs reference to the version control object
        @type Git
        @param parent reference to the parent object
        @type QObject
        """
        VcsStatusMonitorThread.__init__(self, interval, project, vcs, parent)

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        self.__client = None
        self.__useCommandLine = False

    def _performMonitor(self):
        """
        Protected method implementing the monitoring action.

        This method populates the statusList member variable
        with a list of strings giving the status in the first column and the
        path relative to the project directory starting with the third column.
        The allowed status flags are:
        <ul>
            <li>"A" path was added but not yet committed</li>
            <li>"M" path has local changes</li>
            <li>"O" path was removed</li>
            <li>"R" path was deleted and then re-added</li>
            <li>"U" path needs an update</li>
            <li>"Z" path contains a conflict</li>
            <li>"?" path is not tracked</li>
            <li>"!" path is missing</li>
            <li>" " path is back at normal</li>
        </ul>

        @return tuple of flag indicating successful operation and a status message
            in case of non successful operation
        @rtype tuple of (bool, str)
        """
        self.shouldUpdate = False

        # step 1: get overall status
        args = self.vcs.initCommand("status")
        args.append("--porcelain")

        output = ""
        error = ""
        process = QProcess()
        process.setWorkingDirectory(self.projectDir)
        process.start("git", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(300000)
            if finished and process.exitCode() == 0:
                output = str(
                    process.readAllStandardOutput(), self.__ioEncoding, "replace"
                )
            else:
                process.kill()
                process.waitForFinished()
                error = str(
                    process.readAllStandardError(), self.__ioEncoding, "replace"
                )
        else:
            process.kill()
            process.waitForFinished()
            error = self.tr("Could not start the Git process.")

        if error:
            return False, error

        states = {}
        for line in output.splitlines():
            flags = line[:2]
            name = line[3:].split(" -> ")[-1]
            if flags in self.ConflictStates:
                states[name] = "Z"
            if flags[0] in "AMDR":
                if flags[0] == "D":
                    status = "O"
                elif flags[0] == "R":
                    status = "A"
                else:
                    status = flags[0]
                states[name] = status
            elif flags[1] in "MD":
                if flags[1] == "D":
                    status = "O"
                else:
                    status = flags[1]
                states[name] = status
            elif flags == "??":
                states[name] = "?"

        # step 2: collect the status to be reported back
        for name in states:
            try:
                if self.reportedStates[name] != states[name]:
                    self.statusList.append("{0} {1}".format(states[name], name))
            except KeyError:
                self.statusList.append("{0} {1}".format(states[name], name))
        for name in self.reportedStates:
            if name not in states:
                self.statusList.append("  {0}".format(name))
        self.reportedStates = states

        return (True, self.tr("Git status checked successfully"))

    def _getInfo(self):
        """
        Protected method implementing the real info action.

        This method should be overridden and create a short info message to be
        shown in the main window status bar right next to the status indicator.

        @return short info message
        @rtype str
        """
        args = self.vcs.initCommand("show")
        args.append("--abbrev-commit")
        args.append("--format=%h %D")
        args.append("--no-patch")

        output = ""
        process = QProcess()
        process.setWorkingDirectory(self.projectDir)
        process.start("git", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(
                    process.readAllStandardOutput(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )

        if output:
            commitId, refs = output.splitlines()[0].strip().split(None, 1)
            ref = refs.split(",", 1)[0]
            if "->" in ref:
                branch = ref.split("->", 1)[1].strip()
            else:
                branch = self.tr("<detached>")

            return self.tr("{0} / {1}", "branch, commit").format(branch, commitId)
        else:
            return ""

    def _shutdown(self):
        """
        Protected method performing shutdown actions.
        """
        if self.__client:
            self.__client.stopServer()
