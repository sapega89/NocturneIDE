# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS status monitor thread class for Mercurial.
"""

from eric7.VCS.StatusMonitorThread import VcsStatusMonitorThread


class HgStatusMonitorThread(VcsStatusMonitorThread):
    """
    Class implementing the VCS status monitor thread class for Mercurial.
    """

    def __init__(self, interval, project, vcs, parent=None):
        """
        Constructor

        @param interval new interval in seconds
        @type int
        @param project reference to the project object
        @type Project
        @param vcs reference to the version control object
        @type Hg
        @param parent reference to the parent object
        @type QObject
        """
        VcsStatusMonitorThread.__init__(self, interval, project, vcs, parent)

        self.__client = None

    def _performMonitor(self):
        """
        Protected method implementing the monitoring action.

        This method populates the statusList member variable with a list of
        strings giving the status in the first column and the path relative
        to the project directory starting with the third column. The allowed
        status flags are:
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

        @return tuple of flag indicating successful operation and a status
            message in case of non successful operation
        @rtype tuple of (bool, str)
        """
        self.shouldUpdate = False

        ok, err = self.__initClient()
        if not ok:
            return False, err

        # step 1: get overall status
        args = self.vcs.initCommand("status")
        args.append("--noninteractive")
        args.append("--all")
        if self.vcs.hasSubrepositories():
            args.append("--subrepos")

        output, error = self.__client.runcommand(args)

        if error:
            return False, error

        states = {}
        for line in output.splitlines():
            if not line.startswith("  "):
                flag, name = line.split(" ", 1)
                if flag in "AMR?!":
                    if flag == "R":
                        status = "O"
                    else:
                        status = flag
                    states[name] = status

        # step 2: get conflicting changes
        args = self.vcs.initCommand("resolve")
        args.append("--list")

        output, error = self.__client.runcommand(args)

        for line in output.splitlines():
            flag, name = line.split(" ", 1)
            if flag == "U":
                states[name] = "Z"  # conflict

        # step 3: collect the status to be reported back
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

        return (True, self.tr("Mercurial status checked successfully"))

    def _getInfo(self):
        """
        Protected method implementing the real info action.

        @return short info message
        @rtype str
        """
        ok, err = self.__initClient()
        if not ok:
            return ""

        args = self.vcs.initCommand("identify")
        args.append("--num")
        args.append("--id")
        args.append("--branch")

        output, error = self.__client.runcommand(args)

        if error:
            # ignore errors
            return ""

        globalRev, localRev, branch = output.splitlines()[0].split(None, 2)
        if globalRev.endswith("+"):
            globalRev = globalRev[:-1]
        if localRev.endswith("+"):
            localRev = localRev[:-1]

        return self.tr("{0} / {1}:{2}", "branch, local id, global id").format(
            branch, localRev, globalRev
        )

    def _shutdown(self):
        """
        Protected method performing shutdown actions.
        """
        if self.__client:
            self.__client.stopServer()

    def __initClient(self):
        """
        Private method to initialize the Mercurial client.

        @return tuple containing an OK flag and potentially an error message
        @rtype tuple of (bool, str)
        """
        from .HgClient import HgClient

        if self.__client is None:
            client = HgClient(self.projectDir, "utf-8", self.vcs)
            ok, err = client.startServer()
            if ok:
                self.__client = client
        else:
            ok = True
            err = ""

        return ok, err
