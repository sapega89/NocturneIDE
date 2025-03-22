# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS status monitor thread class for Subversion.
"""

import re

from PyQt6.QtCore import QProcess

from eric7 import Preferences
from eric7.VCS.StatusMonitorThread import VcsStatusMonitorThread


class SvnStatusMonitorThread(VcsStatusMonitorThread):
    """
    Class implementing the VCS status monitor thread class for Subversion.
    """

    def __init__(self, interval, project, vcs, parent=None):
        """
        Constructor

        @param interval new interval in seconds
        @type int
        @param project reference to the project object
        @type Project
        @param vcs reference to the version control object
        @type Subversion
        @param parent reference to the parent object
        @type QObject
        """
        VcsStatusMonitorThread.__init__(self, interval, project, vcs, parent)

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        self.rx_status1 = re.compile("(.{8,9})\\s+([0-9-]+)\\s+(.+)\\s*")
        self.rx_status2 = re.compile(
            "(.{8,9})\\s+([0-9-]+)\\s+([0-9?]+)\\s+(\\S+)\\s+(.+)\\s*"
        )

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

        process = QProcess()
        args = []
        args.append("status")
        if not Preferences.getVCS("MonitorLocalStatus"):
            args.append("--show-updates")
        args.append("--non-interactive")
        args.append(".")
        process.setWorkingDirectory(self.projectDir)
        process.start("svn", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(300000)
            if finished and process.exitCode() == 0:
                output = str(
                    process.readAllStandardOutput(), self.__ioEncoding, "replace"
                )
                states = {}
                for line in output.splitlines():
                    match = self.rx_status1.fullmatch(
                        line
                    ) or self.rx_status2.fullmatch(line)
                    if match is None:
                        continue
                    elif match.re is self.rx_status1:
                        flags = match.group(1)
                        path = match.group(3).strip()
                    elif match.re is self.rx_status2:
                        flags = match.group(1)
                        path = match.group(5).strip()
                    if (
                        flags[0] in "ACDMR?!"
                        or (flags[0] == " " and flags[-1] == "*")
                        or flags[1] in "CM"
                    ):
                        if flags[-1] == "*":
                            status = "U"
                        else:
                            status = flags[0]
                        if status == "C" or flags[1] == "C":
                            status = "Z"  # give it highest priority
                        elif status == "D":
                            status = "O"
                        if status == "U":
                            self.shouldUpdate = True
                        if status == " " and flags[1] == "M":
                            status = "M"
                        name = path
                        states[name] = status
                        try:
                            if self.reportedStates[name] != status:
                                self.statusList.append("{0} {1}".format(status, name))
                        except KeyError:
                            self.statusList.append("{0} {1}".format(status, name))
                for name in self.reportedStates:
                    if name not in states:
                        self.statusList.append("  {0}".format(name))
                self.reportedStates = states
                return True, self.tr(
                    "Subversion status checked successfully (using svn)"
                )
            else:
                process.kill()
                process.waitForFinished()
                return (
                    False,
                    str(
                        process.readAllStandardError(),
                        Preferences.getSystem("IOEncoding"),
                        "replace",
                    ),
                )
        else:
            process.kill()
            process.waitForFinished()
            return False, self.tr("Could not start the Subversion process.")
