# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to generate the output of the git diff command
process.
"""

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal, pyqtSlot

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursorProcess


class GitDiffGenerator(QObject):
    """
    Class implementing the generation of output of the git diff command.

    @signal finished() emitted when all processes have finished
    """

    finished = pyqtSignal()

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Git
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.vcs = vcs

        self.__process = EricOverrideCursorProcess()
        self.__process.finished.connect(self.__procFinished)
        self.__process.readyReadStandardOutput.connect(
            lambda: self.__readStdout(self.__process)
        )
        self.__process.readyReadStandardError.connect(
            lambda: self.__readStderr(self.__process)
        )

        self.__process2 = EricOverrideCursorProcess()
        self.__process2.finished.connect(self.__procFinished)
        self.__process2.readyReadStandardOutput.connect(
            lambda: self.__readStdout(self.__process2)
        )
        self.__process2.readyReadStandardError.connect(
            lambda: self.__readStderr(self.__process2)
        )

    def stopProcesses(self):
        """
        Public slot to stop the diff processes.
        """
        for process in [self.__process, self.__process2]:
            if (
                process is not None
                and process.state() != QProcess.ProcessState.NotRunning
            ):
                process.terminate()
                QTimer.singleShot(2000, process.kill)
                process.waitForFinished(3000)

    def start(self, fn, versions=None, diffMode="work2repo", stashName=""):
        """
        Public slot to start the git diff command.

        @param fn filename to be diffed
        @type str
        @param versions list of versions to be diffed
        @type list of up to 2 str or None
        @param diffMode indication for the type of diff to be performed (
            'work2repo' compares the working tree with the HEAD commit,
            'work2stage' compares the working tree with the staging area,
            'stage2repo' compares the staging area with the HEAD commit,
            'work2stage2repo' compares the working tree with the staging area
                and the staging area with the HEAD commit,
            'stash' shows the diff for a stash)
        @type str
        @param stashName name of the stash to show a diff for
        @type str
        @return flag indicating the start status
        @rtype bool
        @exception ValueError raised to indicate a bad value for the 'diffMode'
            parameter.
        """
        if diffMode not in [
            "work2repo",
            "work2stage",
            "stage2repo",
            "work2stage2repo",
            "stash",
        ]:
            raise ValueError("Bad value for 'diffMode' parameter.")

        self.__output1 = []
        self.__output2 = []
        self.__errors = []
        self.__fileSeparators = []
        args2 = []

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        if diffMode in ["work2repo", "work2stage", "stage2repo", "work2stage2repo"]:
            args = self.vcs.initCommand("diff")
            args.append("--patch")
            args.append("--find-copies-harder")

            if versions is not None:
                for version in versions:
                    if version:
                        args.append(version)
            else:
                if diffMode == "work2stage2repo":
                    args2 = args[:]
                    args2.append("--cached")
                    args2.append("--")
                elif diffMode == "stage2repo":
                    args.append("--cached")
                elif diffMode == "work2repo":
                    args.append("HEAD")

            args.append("--")
            if isinstance(fn, list):
                dname, _fnames = self.vcs.splitPathList(fn)
                self.vcs.addArguments(args, fn)
                if args2:
                    self.vcs.addArguments(args2, fn)
            else:
                dname, _fname = self.vcs.splitPath(fn)
                args.append(fn)
                if args2:
                    args2.append(fn)
        elif diffMode == "stash":
            dname, _fname = self.vcs.splitPath(fn)
            args = self.vcs.initCommand("stash")
            args.append("show")
            args.append("--patch")
            if stashName:
                args.append(stashName)

        # find the root of the repo
        repodir = self.vcs.findRepoRoot(dname)
        if not repodir:
            return False

        self.__process.kill()
        self.__process.setWorkingDirectory(repodir)
        self.__process.start("git", args)
        procStarted = self.__process.waitForStarted(5000)
        if not procStarted:
            return False

        if diffMode == "work2stage2repo":
            self.__process2.kill()
            self.__process2.setWorkingDirectory(repodir)
            self.__process2.start("git", args2)
            procStarted = self.__process2.waitForStarted(5000)
            if not procStarted:
                return False

        return True

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        if (
            self.__process.state() == QProcess.ProcessState.NotRunning
            and self.__process2.state() == QProcess.ProcessState.NotRunning
        ):
            self.finished.emit()

    def getResult(self):
        """
        Public method to return the result data.

        @return tuple of lists of string containing lines of the diff, the diff
            between stage and repo for 'work2stage2repo' mode (empty
            otherwise), the list of errors and a list of tuples of filenames
            and the line into the diff output.
        @rtype tuple of (list of str, list of str, list of str, list of (str, int))
        """
        return (self.__output1, self.__output2, self.__errors, self.__fileSeparators)

    def __processFileLine(self, line, isTopDiff):
        """
        Private slot to process a line giving the old/new file.

        @param line line to be processed
        @type str
        @param isTopDiff flag indicating to show the output in the top
            output widget
        @type bool
        """
        _prefix, filenames = line.split(" a/", 1)
        oldFile, newFile = filenames.split(" b/", 1)
        if isTopDiff:
            self.__fileSeparators.append(
                (oldFile.strip(), newFile.strip(), len(self.__output1), -2)
            )
        else:
            self.__fileSeparators.append(
                (oldFile.strip(), newFile.strip(), -2, len(self.__output2))
            )

    def __processLine(self, line, isTopDiff):
        """
        Private method to process one line of output.

        @param line output line to process
        @type str
        @param isTopDiff flag indicating to show the output in the top
            output widget
        @type bool
        """
        if line.startswith("diff --git"):
            self.__processFileLine(line, isTopDiff)

        if isTopDiff:
            self.__output1.append(line)
        else:
            self.__output2.append(line)

    def __readStdout(self, process):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.

        @param process reference to the process providing output
        @type QProcess
        """
        process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        isTopDiff = process == self.__process

        while process.canReadLine():
            line = str(process.readLine(), self.__ioEncoding, "replace")
            self.__processLine(line, isTopDiff)

    def __readStderr(self, process):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.

        @param process reference to the process providing error output
        @type QProcess
        """
        s = str(process.readAllStandardError(), self.__ioEncoding, "replace")
        self.__errors.append(s)
