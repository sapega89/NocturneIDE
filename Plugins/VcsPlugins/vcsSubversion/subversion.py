# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the version control systems interface to Subversion.
"""

import os
import re
import shutil

from urllib.parse import quote

from PyQt6.QtCore import QCoreApplication, QProcess, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog, QInputDialog, QLineEdit

from eric7 import Preferences, Utilities
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog
from eric7.VCS.VersionControl import VersionControl, VersionControlState

from .SvnDialog import SvnDialog
from .SvnUtilities import amendConfig, createDefaultConfig, getConfigPath


class Subversion(VersionControl):
    """
    Class implementing the version control systems interface to Subversion.

    @signal committed() emitted after the commit action has completed
    """

    committed = pyqtSignal()

    def __init__(self, plugin, parent=None, name=None):
        """
        Constructor

        @param plugin reference to the plugin object
        @type VcsSubversionPlugin
        @param parent parent widget
        @type QWidget
        @param name name of this object
        @type str
        """
        VersionControl.__init__(self, parent, name)
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
        self.interestingDataKeys = [
            "standardLayout",
        ]

        self.__plugin = plugin
        self.__ui = parent

        self.options = self.defaultOptions
        self.otherData["standardLayout"] = True
        self.tagsList = []
        self.branchesList = []
        self.allTagsBranchesList = []
        self.mergeList = [[], [], []]
        self.showedTags = False
        self.showedBranches = False

        self.tagTypeList = [
            "tags",
            "branches",
        ]

        self.commandHistory = []
        self.wdHistory = []

        if "SVN_ASP_DOT_NET_HACK" in os.environ:
            self.adminDir = "_svn"
        else:
            self.adminDir = ".svn"

        self.log = None
        self.diff = None
        self.sbsDiff = None
        self.status = None
        self.propList = None
        self.tagbranchList = None
        self.blame = None
        self.repoBrowser = None
        self.logBrowser = None

        # regular expression object for evaluation of the status output
        self.rx_status1 = re.compile(
            "(.{8})\\s+([0-9-]+)\\s+([0-9?]+)\\s+(\\S+)\\s+(.+)"
        )
        self.rx_status2 = re.compile("(.{8})\\s+(.+)\\s*")
        self.statusCache = {}

        self.__commitData = {}
        self.__commitDialog = None

        self.__wcng = True
        # assume new generation working copy metadata format

    def getPlugin(self):
        """
        Public method to get a reference to the plugin object.

        @return reference to the plugin object
        @rtype VcsSubversionPlugin
        """
        return self.__plugin

    def vcsShutdown(self):
        """
        Public method used to shutdown the Subversion interface.
        """
        if self.log is not None:
            self.log.close()
        if self.diff is not None:
            self.diff.close()
        if self.sbsDiff is not None:
            self.sbsDiff.close()
        if self.status is not None:
            self.status.close()
        if self.propList is not None:
            self.propList.close()
        if self.tagbranchList is not None:
            self.tagbranchList.close()
        if self.blame is not None:
            self.blame.close()
        if self.repoBrowser is not None:
            self.repoBrowser.close()
        if self.logBrowser is not None:
            self.logBrowser.close()

    def vcsExists(self):
        """
        Public method used to test for the presence of the svn executable.

        @return flag indicating the existence and an error message
        @rtype tuple of (bool, str)
        """
        self.versionStr = ""
        errMsg = ""
        ioEncoding = Preferences.getSystem("IOEncoding")

        process = QProcess()
        process.start("svn", ["--version"])
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(process.readAllStandardOutput(), ioEncoding, "replace")
                self.versionStr = output.split()[2]
                v = list(
                    re.match(r".*?(\d+)\.(\d+)\.?(\d+)?", self.versionStr).groups()
                )
                for i in range(3):
                    try:
                        v[i] = int(v[i])
                    except TypeError:
                        v[i] = 0
                    except IndexError:
                        v.append(0)
                self.version = tuple(v)
                return True, errMsg
            else:
                if finished:
                    errMsg = self.tr(
                        "The svn process finished with the exit code {0}"
                    ).format(process.exitCode())
                else:
                    errMsg = self.tr("The svn process did not finish within 30s.")
        else:
            errMsg = self.tr("Could not start the svn executable.")

        return False, errMsg

    def vcsInit(self, vcsDir, noDialog=False):  # noqa: U100
        """
        Public method used to initialize the subversion repository.

        The subversion repository has to be initialized from outside eric
        because the respective command always works locally. Therefore we
        always return TRUE without doing anything.

        @param vcsDir name of the VCS directory (unused)
        @type str
        @param noDialog flag indicating quiet operations (unused)
        @type bool
        @return always True
        @rtype bool
        """
        return True

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
        """
        success = self.vcsImport(vcsDataDict, project.ppath, addAll=addAll)[0]
        if not success:
            EricMessageBox.critical(
                self.__ui,
                self.tr("Create project in repository"),
                self.tr(
                    """The project could not be created in the repository."""
                    """ Maybe the given repository doesn't exist or the"""
                    """ repository server is down."""
                ),
            )
        else:
            cwdIsPpath = False
            if os.getcwd() == project.ppath:
                os.chdir(os.path.dirname(project.ppath))
                cwdIsPpath = True
            tmpProjectDir = "{0}_tmp".format(project.ppath)
            shutil.rmtree(tmpProjectDir, ignore_errors=True)
            os.rename(project.ppath, tmpProjectDir)
            os.makedirs(project.ppath)
            self.vcsCheckout(vcsDataDict, project.ppath)
            if cwdIsPpath:
                os.chdir(project.ppath)
            self.vcsCommit(project.ppath, vcsDataDict["message"], True)
            pfn = project.pfile
            if not os.path.isfile(pfn):
                pfn += "z"
            if not os.path.isfile(pfn):
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("New project"),
                    self.tr(
                        """The project could not be checked out of the"""
                        """ repository.<br />"""
                        """Restoring the original contents."""
                    ),
                )
                if os.getcwd() == project.ppath:
                    os.chdir(os.path.dirname(project.ppath))
                    cwdIsPpath = True
                else:
                    cwdIsPpath = False
                shutil.rmtree(project.ppath, ignore_errors=True)
                os.rename(tmpProjectDir, project.ppath)
                project.setProjectData("None", dataKey="VCS")
                project.vcs = None
                project.setDirty(True)
                project.saveProject()
                project.closeProject()
                return
            shutil.rmtree(tmpProjectDir, ignore_errors=True)
            project.closeProject(noSave=True)
            project.openProject(pfn)

    def vcsImport(
        self, vcsDataDict, projectDir, noDialog=False, addAll=True  # noqa: U100
    ):
        """
        Public method used to import the project into the Subversion
        repository.

        @param vcsDataDict dictionary of data required for the import
        @type dict
        @param projectDir project directory
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        @param addAll flag indicating to add all files to the repository (unused)
        @type bool
        @return tuple containing a flag indicating an execution without errors
            and a flag indicating the version controll status
        @rtype tuple of (bool, bool)
        """
        noDialog = False
        msg = vcsDataDict["message"]
        if not msg:
            msg = "***"

        vcsDir = self.svnNormalizeURL(vcsDataDict["url"])
        if vcsDir.startswith("/"):
            vcsDir = "file://{0}".format(vcsDir)
        elif vcsDir[1] in ["|", ":"]:
            vcsDir = "file:///{0}".format(vcsDir)

        project = vcsDir[vcsDir.rfind("/") + 1 :]

        # create the dir structure to be imported into the repository
        tmpDir = "{0}_tmp".format(projectDir)
        try:
            os.makedirs(tmpDir)
            if self.otherData["standardLayout"]:
                os.mkdir(os.path.join(tmpDir, project))
                os.mkdir(os.path.join(tmpDir, project, "branches"))
                os.mkdir(os.path.join(tmpDir, project, "tags"))
                shutil.copytree(projectDir, os.path.join(tmpDir, project, "trunk"))
            else:
                shutil.copytree(projectDir, os.path.join(tmpDir, project))
        except OSError:
            if os.path.isdir(tmpDir):
                shutil.rmtree(tmpDir, ignore_errors=True)
            return False, False

        args = []
        args.append("import")
        self.addArguments(args, self.options["global"])
        args.append("-m")
        args.append(msg)
        args.append(self.__svnURL(vcsDir))

        if noDialog:
            status = self.startSynchronizedProcess(
                QProcess(), "svn", args, os.path.join(tmpDir, project)
            )
        else:
            dia = SvnDialog(
                self.tr("Importing project into Subversion repository"),
                parent=self.__ui,
            )
            res = dia.startProcess(args, os.path.join(tmpDir, project))
            if res:
                dia.exec()
            status = dia.normalExit()

        shutil.rmtree(tmpDir, ignore_errors=True)
        return status, False

    def vcsCheckout(self, vcsDataDict, projectDir, noDialog=False):
        """
        Public method used to check the project out of the Subversion
        repository.

        @param vcsDataDict dictionary of data required for the checkout
        @type dict
        @param projectDir project directory to create
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating an execution without errors
        @rtype bool
        """
        noDialog = False
        try:
            tag = vcsDataDict["tag"]
        except KeyError:
            tag = None
        vcsDir = self.svnNormalizeURL(vcsDataDict["url"])
        if vcsDir.startswith("/"):
            vcsDir = "file://{0}".format(vcsDir)
        elif vcsDir[1] in ["|", ":"]:
            vcsDir = "file:///{0}".format(vcsDir)

        if self.otherData["standardLayout"]:
            if tag is None or tag == "":
                svnUrl = "{0}/trunk".format(vcsDir)
            else:
                if not tag.startswith("tags") and not tag.startswith("branches"):
                    tagType, ok = QInputDialog.getItem(
                        None,
                        self.tr("Subversion Checkout"),
                        self.tr(
                            "The tag must be a normal tag (tags) or"
                            " a branch tag (branches)."
                            " Please select from the list."
                        ),
                        self.tagTypeList,
                        0,
                        False,
                    )
                    if not ok:
                        return False
                    tag = "{0}/{1}".format(tagType, tag)
                svnUrl = "{0}/{1}".format(vcsDir, tag)
        else:
            svnUrl = vcsDir

        args = []
        args.append("checkout")
        self.addArguments(args, self.options["global"])
        self.addArguments(args, self.options["checkout"])
        args.append(self.__svnURL(svnUrl))
        args.append(projectDir)

        if noDialog:
            return self.startSynchronizedProcess(QProcess(), "svn", args)
        else:
            dia = SvnDialog(
                self.tr("Checking project out of Subversion repository"),
                parent=self.__ui,
            )
            res = dia.startProcess(args)
            if res:
                dia.exec()
            return dia.normalExit()

    def vcsExport(self, vcsDataDict, projectDir):
        """
        Public method used to export a directory from the Subversion
        repository.

        @param vcsDataDict dictionary of data required for the checkout
        @type dict
        @param projectDir project directory to create
        @type str
        @return flag indicating an execution without errors
        @rtype bool
        """
        try:
            tag = vcsDataDict["tag"]
        except KeyError:
            tag = None
        vcsDir = self.svnNormalizeURL(vcsDataDict["url"])
        if vcsDir.startswith("/") or vcsDir[1] == "|":
            vcsDir = "file://{0}".format(vcsDir)

        if self.otherData["standardLayout"]:
            if tag is None or tag == "":
                svnUrl = "{0}/trunk".format(vcsDir)
            else:
                if not tag.startswith("tags") and not tag.startswith("branches"):
                    tagType, ok = QInputDialog.getItem(
                        None,
                        self.tr("Subversion Export"),
                        self.tr(
                            "The tag must be a normal tag (tags) or"
                            " a branch tag (branches)."
                            " Please select from the list."
                        ),
                        self.tagTypeList,
                        0,
                        False,
                    )
                    if not ok:
                        return False
                    tag = "{0}/{1}".format(tagType, tag)
                svnUrl = "{0}/{1}".format(vcsDir, tag)
        else:
            svnUrl = vcsDir

        args = []
        args.append("export")
        self.addArguments(args, self.options["global"])
        args.append("--force")
        args.append(self.__svnURL(svnUrl))
        args.append(projectDir)

        dia = SvnDialog(
            self.tr("Exporting project from Subversion repository"),
            parent=self.__ui,
        )
        res = dia.startProcess(args)
        if res:
            dia.exec()
        return dia.normalExit()

    def vcsCommit(self, name, message, noDialog=False):
        """
        Public method used to make the change of a file/directory permanent
        in the Subversion repository.

        @param name file/directory name to be committed
        @type str or list of str
        @param message message for this operation
        @type str
        @param noDialog flag indicating quiet operations
        @type bool
        """
        from .SvnCommitDialog import SvnCommitDialog

        msg = message

        if not noDialog and not msg:
            # call CommitDialog and get message from there
            if self.__commitDialog is None:
                self.__commitDialog = SvnCommitDialog(self, self.__ui)
                self.__commitDialog.accepted.connect(self.__vcsCommit_Step2)
            self.__commitDialog.show()
            self.__commitDialog.raise_()
            self.__commitDialog.activateWindow()

        self.__commitData["name"] = name
        self.__commitData["msg"] = msg
        self.__commitData["noDialog"] = noDialog

        if noDialog:
            self.__vcsCommit_Step2()

    def __vcsCommit_Step2(self):
        """
        Private slot performing the second step of the commit action.
        """
        name = self.__commitData["name"]
        msg = self.__commitData["msg"]
        noDialog = self.__commitData["noDialog"]

        if not noDialog:
            # check, if there are unsaved changes, that should be committed
            if isinstance(name, list):
                nameList = name
            else:
                nameList = [name]
            ok = True
            for nam in nameList:
                # check for commit of the project
                if os.path.isdir(nam):
                    project = ericApp().getObject("Project")
                    if nam == project.getProjectPath():
                        ok &= (
                            project.checkAllScriptsDirty(reportSyntaxErrors=True)
                            and project.checkDirty()
                        )
                        continue
                elif os.path.isfile(nam):
                    editor = ericApp().getObject("ViewManager").getOpenEditor(nam)
                    if editor:
                        ok &= editor.checkDirty()
                if not ok:
                    break

            if not ok:
                res = EricMessageBox.yesNo(
                    self.__ui,
                    self.tr("Commit Changes"),
                    self.tr(
                        """The commit affects files, that have unsaved"""
                        """ changes. Shall the commit be continued?"""
                    ),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return

        if self.__commitDialog is not None:
            msg = self.__commitDialog.logMessage()
            if self.__commitDialog.hasChangelists():
                changelists, keepChangelists = self.__commitDialog.changelistsData()
            else:
                changelists, keepChangelists = [], False
            self.__commitDialog.deleteLater()
            self.__commitDialog = None
        else:
            changelists, keepChangelists = [], False

        if not msg:
            msg = "***"

        args = []
        args.append("commit")
        self.addArguments(args, self.options["global"])
        self.addArguments(args, self.options["commit"])
        if keepChangelists:
            args.append("--keep-changelists")
        for changelist in changelists:
            args.append("--changelist")
            args.append(changelist)
        args.append("-m")
        args.append(msg)
        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
            self.addArguments(args, fnames)
        else:
            dname, fname = self.splitPath(name)
            args.append(fname)

        if self.svnGetReposName(dname).startswith("http") or self.svnGetReposName(
            dname
        ).startswith("svn"):
            noDialog = False

        if noDialog:
            self.startSynchronizedProcess(QProcess(), "svn", args, dname)
        else:
            dia = SvnDialog(
                self.tr("Commiting changes to Subversion repository"),
                parent=self.__ui,
            )
            res = dia.startProcess(args, dname)
            if res:
                dia.exec()
        self.committed.emit()
        self.checkVCSStatus()

    def vcsCommitMessages(self):
        """
        Public method to get the list of saved commit messages.

        @return list of saved commit messages
        @rtype list of str
        """
        # try per project commit history first
        messages = self._vcsProjectCommitMessages()
        if not messages:
            # empty list returned, try the vcs specific one
            messages = self.getPlugin().getPreferences("Commits")

        return messages

    def vcsAddCommitMessage(self, message):
        """
        Public method to add a commit message to the list of saved messages.

        @param message message to be added
        @type str
        """
        if not self._vcsAddProjectCommitMessage(message):
            commitMessages = self.vcsCommitMessages()
            if message in commitMessages:
                commitMessages.remove(message)
            commitMessages.insert(0, message)
            no = Preferences.getVCS("CommitMessages")
            del commitMessages[no:]
            self.getPlugin().setPreferences("Commits", commitMessages)

    def vcsClearCommitMessages(self):
        """
        Public method to clear the list of saved messages.
        """
        if not self._vcsClearProjectCommitMessages():
            self.getPlugin().setPreferences("Commits", [])

    def vcsUpdate(self, name, noDialog=False):
        """
        Public method used to update a file/directory with the Subversion
        repository.

        @param name file/directory name to be updated
        @type str or list of str
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating, that the update contained an add or delete
        @rtype bool
        """
        args = []
        args.append("update")
        self.addArguments(args, self.options["global"])
        self.addArguments(args, self.options["update"])
        if self.version >= (1, 5, 0):
            args.append("--accept")
            args.append("postpone")
        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
            self.addArguments(args, fnames)
        else:
            dname, fname = self.splitPath(name)
            args.append(fname)

        if noDialog:
            self.startSynchronizedProcess(QProcess(), "svn", args, dname)
            res = False
        else:
            dia = SvnDialog(
                self.tr("Synchronizing with the Subversion repository"),
                parent=self.__ui,
            )
            res = dia.startProcess(args, dname, True)
            if res:
                dia.exec()
                res = dia.hasAddOrDelete()
        self.checkVCSStatus()
        return res

    def vcsAdd(self, name, isDir=False, noDialog=False):
        """
        Public method used to add a file/directory to the Subversion
        repository.

        @param name file/directory name to be added
        @type str
        @param isDir flag indicating name is a directory
        @type bool
        @param noDialog flag indicating quiet operations
        @type bool
        """
        args = []
        args.append("add")
        self.addArguments(args, self.options["global"])
        self.addArguments(args, self.options["add"])
        args.append("--non-recursive")
        if noDialog and "--force" not in args:
            args.append("--force")

        if isinstance(name, list):
            if isDir:
                dname, fname = os.path.split(name[0])
            else:
                dname, fnames = self.splitPathList(name)
        else:
            if isDir:
                dname, fname = os.path.split(name)
            else:
                dname, fname = self.splitPath(name)
        tree = []
        wdir = dname
        if self.__wcng:
            repodir = dname
            while not os.path.isdir(os.path.join(repodir, self.adminDir)):
                repodir = os.path.dirname(repodir)
                if os.path.splitdrive(repodir)[1] == os.sep:
                    return  # oops, project is not version controlled
            while os.path.normcase(dname) != os.path.normcase(repodir) and (
                os.path.normcase(dname) not in self.statusCache
                or self.statusCache[os.path.normcase(dname)]
                == VersionControlState.Uncontrolled
            ):
                # add directories recursively, if they aren't in the
                # repository already
                tree.insert(-1, dname)
                dname = os.path.dirname(dname)
                wdir = dname
        else:
            while not os.path.exists(os.path.join(dname, self.adminDir)):
                # add directories recursively, if they aren't in the
                # repository already
                tree.insert(-1, dname)
                dname = os.path.dirname(dname)
                wdir = dname
        self.addArguments(args, tree)

        if isinstance(name, list):
            tree2 = []
            for n in name:
                d = os.path.dirname(n)
                if self.__wcng:
                    repodir = d
                    while not os.path.isdir(os.path.join(repodir, self.adminDir)):
                        repodir = os.path.dirname(repodir)
                        if os.path.splitdrive(repodir)[1] == os.sep:
                            return  # oops, project is not version controlled
                    while (
                        os.path.normcase(d) != os.path.normcase(repodir)
                        and (d not in tree2 + tree)
                        and (
                            os.path.normcase(d) not in self.statusCache
                            or self.statusCache[os.path.normcase(d)]
                            == VersionControlState.Uncontrolled
                        )
                    ):
                        tree2.append(d)
                        d = os.path.dirname(d)
                else:
                    while not os.path.exists(os.path.join(d, self.adminDir)):
                        if d in tree2 + tree:
                            break
                        tree2.append(d)
                        d = os.path.dirname(d)
            tree2.reverse()
            self.addArguments(args, tree2)
            self.addArguments(args, name)
        else:
            args.append(name)

        if noDialog:
            self.startSynchronizedProcess(QProcess(), "svn", args, wdir)
        else:
            dia = SvnDialog(
                self.tr("Adding files/directories to the Subversion repository"),
                parent=self.__ui,
            )
            res = dia.startProcess(args, wdir)
            if res:
                dia.exec()

    def vcsAddBinary(self, name, isDir=False):
        """
        Public method used to add a file/directory in binary mode to the
        Subversion repository.

        @param name file/directory name to be added
        @type str
        @param isDir flag indicating name is a directory
        @type bool
        """
        self.vcsAdd(name, isDir)

    def vcsAddTree(self, path):
        """
        Public method to add a directory tree rooted at path to the Subversion
        repository.

        @param path root directory of the tree to be added
        @type str or list of str
        """
        args = []
        args.append("add")
        self.addArguments(args, self.options["global"])
        self.addArguments(args, self.options["add"])

        tree = []
        if isinstance(path, list):
            dname, fnames = self.splitPathList(path)
            for n in path:
                d = os.path.dirname(n)
                if self.__wcng:
                    repodir = d
                    while not os.path.isdir(os.path.join(repodir, self.adminDir)):
                        repodir = os.path.dirname(repodir)
                        if os.path.splitdrive(repodir)[1] == os.sep:
                            return  # oops, project is not version controlled
                    while (
                        os.path.normcase(d) != os.path.normcase(repodir)
                        and (d not in tree)
                        and (
                            os.path.normcase(d) not in self.statusCache
                            or self.statusCache[os.path.normcase(d)]
                            == VersionControlState.Uncontrolled
                        )
                    ):
                        tree.append(d)
                        d = os.path.dirname(d)
                else:
                    while not os.path.exists(os.path.join(d, self.adminDir)):
                        # add directories recursively,
                        # if they aren't in the repository already
                        if d in tree:
                            break
                        tree.append(d)
                        d = os.path.dirname(d)
            tree.reverse()
        else:
            dname, fname = os.path.split(path)
            if self.__wcng:
                repodir = dname
                while not os.path.isdir(os.path.join(repodir, self.adminDir)):
                    repodir = os.path.dirname(repodir)
                    if os.path.splitdrive(repodir)[1] == os.sep:
                        return  # oops, project is not version controlled
                while os.path.normcase(dname) != os.path.normcase(repodir) and (
                    os.path.normcase(dname) not in self.statusCache
                    or self.statusCache[os.path.normcase(dname)]
                    == VersionControlState.Uncontrolled
                ):
                    # add directories recursively, if they aren't in the
                    # repository already
                    tree.insert(-1, dname)
                    dname = os.path.dirname(dname)
            else:
                while not os.path.exists(os.path.join(dname, self.adminDir)):
                    # add directories recursively,
                    # if they aren't in the repository already
                    tree.insert(-1, dname)
                    dname = os.path.dirname(dname)
        if tree:
            self.vcsAdd(tree, True)

        if isinstance(path, list):
            self.addArguments(args, path)
        else:
            args.append(path)

        dia = SvnDialog(
            self.tr("Adding directory trees to the Subversion repository"),
            parent=self.__ui,
        )
        res = dia.startProcess(args, dname)
        if res:
            dia.exec()

    def vcsRemove(self, name, project=False, noDialog=False):  # noqa: U100
        """
        Public method used to remove a file/directory from the Subversion
        repository.

        The default operation is to remove the local copy as well.

        @param name file/directory name to be removed
        @type str or list of str
        @param project flag indicating deletion of a project tree (unused)
        @type bool
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating successfull operation
        @rtype bool
        """
        args = []
        args.append("delete")
        self.addArguments(args, self.options["global"])
        self.addArguments(args, self.options["remove"])
        if noDialog and "--force" not in args:
            args.append("--force")

        if isinstance(name, list):
            self.addArguments(args, name)
        else:
            args.append(name)

        if noDialog:
            res = self.startSynchronizedProcess(QProcess(), "svn", args)
        else:
            dia = SvnDialog(
                self.tr("Removing files/directories from the Subversion repository"),
                parent=self.__ui,
            )
            res = dia.startProcess(args)
            if res:
                dia.exec()
                res = dia.normalExit()

        return res

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
        """
        from .SvnCopyDialog import SvnCopyDialog

        rx_prot = re.compile("(file:|svn:|svn+ssh:|http:|https:).+")
        opts = self.options["global"][:]
        force = "--force" in opts
        if force:
            del opts[opts.index("--force")]

        res = False
        if noDialog:
            if target is None:
                return False
            force = True
            accepted = True
        else:
            dlg = SvnCopyDialog(name, parent=self.__ui, move=True, force=force)
            accepted = dlg.exec() == QDialog.DialogCode.Accepted
            if accepted:
                target, force = dlg.getData()
            if not target:
                return False

        isDir = os.path.isdir(name) if rx_prot.fullmatch(target) is None else False

        if accepted:
            args = []
            args.append("move")
            self.addArguments(args, opts)
            if force:
                args.append("--force")
            if rx_prot.fullmatch(target) is not None:
                args.append("--message")
                args.append("Moving {0} to {1}".format(name, target))
                target = self.__svnURL(target)
            args.append(name)
            args.append(target)

            if noDialog:
                res = self.startSynchronizedProcess(QProcess(), "svn", args)
            else:
                dia = SvnDialog(self.tr("Moving {0}").format(name), parent=self.__ui)
                res = dia.startProcess(args)
                if res:
                    dia.exec()
                    res = dia.normalExit()
            if res and rx_prot.fullmatch(target) is None:
                if target.startswith(project.getProjectPath()):
                    if isDir:
                        project.moveDirectory(name, target)
                    else:
                        project.renameFileInPdata(name, target)
                else:
                    if isDir:
                        project.removeDirectory(name)
                    else:
                        project.removeFile(name)
        return res

    def vcsDiff(self, name):
        """
        Public method used to view the difference of a file/directory to the
        Subversion repository.

        If name is a directory and is the project directory, all project files
        are saved first. If name is a file (or list of files), which is/are
        being edited and has unsaved modification, they can be saved or the
        operation may be aborted.

        @param name file/directory name to be diffed
        @type str
        """
        from .SvnDiffDialog import SvnDiffDialog

        names = name[:] if isinstance(name, list) else [name]
        for nam in names:
            if os.path.isfile(nam):
                editor = ericApp().getObject("ViewManager").getOpenEditor(nam)
                if editor and not editor.checkDirty():
                    return
            else:
                project = ericApp().getObject("Project")
                if nam == project.ppath and not project.saveAllScripts():
                    return
        if self.diff is None:
            self.diff = SvnDiffDialog(self)
        self.diff.show()
        self.diff.raise_()
        QApplication.processEvents()
        self.diff.start(name, refreshable=True)

    def vcsStatus(self, name):
        """
        Public method used to view the status of files/directories in the
        Subversion repository.

        @param name file/directory name(s) to show the status of
        @type str or list of str
        """
        from .SvnStatusDialog import SvnStatusDialog

        if self.status is None:
            self.status = SvnStatusDialog(self)
        self.status.show()
        self.status.raise_()
        self.status.start(name)

    def vcsTag(self, name):
        """
        Public method used to set the tag of a file/directory in the
        Subversion repository.

        @param name file/directory name to be tagged
        @type str
        """
        from .SvnTagDialog import SvnTagDialog

        dname, fname = self.splitPath(name)

        reposURL = self.svnGetReposName(dname)
        if reposURL is None:
            EricMessageBox.critical(
                self.__ui,
                self.tr("Subversion Error"),
                self.tr(
                    """The URL of the project repository could not be"""
                    """ retrieved from the working copy. The tag operation"""
                    """ will be aborted"""
                ),
            )
            return

        url = (
            None if self.otherData["standardLayout"] else self.svnNormalizeURL(reposURL)
        )
        dlg = SvnTagDialog(
            self.allTagsBranchesList,
            url,
            self.otherData["standardLayout"],
            parent=self.__ui,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tag, tagOp = dlg.getParameters()
            if tag in self.allTagsBranchesList:
                self.allTagsBranchesList.remove(tag)
            self.allTagsBranchesList.insert(0, tag)
        else:
            return

        if self.otherData["standardLayout"]:
            rx_base = re.compile("(.+)/(trunk|tags|branches).*")
            match = rx_base.fullmatch(reposURL)
            if match is None:
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("Subversion Error"),
                    self.tr(
                        """The URL of the project repository has an"""
                        """ invalid format. The tag operation will"""
                        """ be aborted"""
                    ),
                )
                return

            reposRoot = match.group(1)
            if tagOp in [1, 4]:
                url = "{0}/tags/{1}".format(reposRoot, quote(tag))
            elif tagOp in [2, 8]:
                url = "{0}/branches/{1}".format(reposRoot, quote(tag))
        else:
            url = self.__svnURL(tag)

        args = []
        if tagOp in [1, 2]:
            args.append("copy")
            self.addArguments(args, self.options["global"])
            self.addArguments(args, self.options["tag"])
            args.append("--message")
            args.append("Created tag <{0}>".format(tag))
            args.append(reposURL)
            args.append(url)
        else:
            args.append("delete")
            self.addArguments(args, self.options["global"])
            self.addArguments(args, self.options["tag"])
            args.append("--message")
            args.append("Deleted tag <{0}>".format(tag))
            args.append(url)

        dia = SvnDialog(
            self.tr("Tagging {0} in the Subversion repository").format(name),
            parent=self.__ui,
        )
        res = dia.startProcess(args)
        if res:
            dia.exec()

    def vcsRevert(self, name):
        """
        Public method used to revert changes made to a file/directory.

        @param name file/directory name to be reverted
        @type str
        @return flag indicating, that the update contained an add
            or delete
        @rtype bool
        """
        args = []
        args.append("revert")
        self.addArguments(args, self.options["global"])
        if isinstance(name, list):
            self.addArguments(args, name)
            names = name[:]
        else:
            if os.path.isdir(name):
                args.append("--recursive")
            args.append(name)
            names = [name]

        project = ericApp().getObject("Project")
        names = [project.getRelativePath(nam) for nam in names]
        if names[0]:
            dlg = DeleteFilesConfirmationDialog(
                self.parent(),
                self.tr("Revert changes"),
                self.tr(
                    "Do you really want to revert all changes to"
                    " these files or directories?"
                ),
                names,
            )
            yes = dlg.exec() == QDialog.DialogCode.Accepted
        else:
            yes = EricMessageBox.yesNo(
                None,
                self.tr("Revert changes"),
                self.tr(
                    """Do you really want to revert all changes of"""
                    """ the project?"""
                ),
            )
        if yes:
            dia = SvnDialog(self.tr("Reverting changes"), parent=self.__ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()
            self.checkVCSStatus()

        return False

    def vcsForget(self, name):
        """
        Public method used to remove a file from the repository.

        Note: svn does not support this operation. The method is implemented
        as a NoOp.

        @param name file/directory name to be removed
        @type str or list of str
        """
        pass

    def vcsSwitch(self, name):
        """
        Public method used to switch a directory to a different tag/branch.

        @param name directory name to be switched
        @type str
        @return flag indicating added or changed files
        @rtype bool
        """
        from .SvnSwitchDialog import SvnSwitchDialog

        dname, fname = self.splitPath(name)

        reposURL = self.svnGetReposName(dname)
        if reposURL is None:
            EricMessageBox.critical(
                self.__ui,
                self.tr("Subversion Error"),
                self.tr(
                    """The URL of the project repository could not be"""
                    """ retrieved from the working copy. The switch"""
                    """ operation will be aborted"""
                ),
            )
            return False

        url = (
            None if self.otherData["standardLayout"] else self.svnNormalizeURL(reposURL)
        )
        dlg = SvnSwitchDialog(
            self.allTagsBranchesList,
            url,
            self.otherData["standardLayout"],
            parent=self.__ui,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            tag, tagType = dlg.getParameters()
            if tag in self.allTagsBranchesList:
                self.allTagsBranchesList.remove(tag)
            self.allTagsBranchesList.insert(0, tag)
        else:
            return False

        if self.otherData["standardLayout"]:
            rx_base = re.compile("(.+)/(trunk|tags|branches).*")
            match = rx_base.fullmatch(reposURL)
            if match is None:
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("Subversion Error"),
                    self.tr(
                        """The URL of the project repository has an"""
                        """ invalid format. The switch operation will"""
                        """ be aborted"""
                    ),
                )
                return False

            reposRoot = match.group(1)
            tn = tag
            if tagType == 1:
                url = "{0}/tags/{1}".format(reposRoot, quote(tag))
            elif tagType == 2:
                url = "{0}/branches/{1}".format(reposRoot, quote(tag))
            elif tagType == 4:
                url = "{0}/trunk".format(reposRoot)
                tn = "HEAD"
        else:
            url = self.__svnURL(tag)
            tn = url

        args = []
        args.append("switch")
        if self.version >= (1, 5, 0):
            args.append("--accept")
            args.append("postpone")
        args.append(url)
        args.append(name)

        dia = SvnDialog(self.tr("Switching to {0}").format(tn), parent=self.__ui)
        res = dia.startProcess(args, setLanguage=True)
        if res:
            dia.exec()
            res = dia.hasAddOrDelete()
        self.checkVCSStatus()
        return res

    def vcsMerge(self, name):
        """
        Public method used to merge a URL/revision into the local project.

        @param name file/directory name to be merged
        @type str
        """
        from .SvnMergeDialog import SvnMergeDialog

        dname, fname = self.splitPath(name)

        opts = self.options["global"][:]
        force = "--force" in opts
        if force:
            del opts[opts.index("--force")]

        dlg = SvnMergeDialog(
            self.mergeList[0],
            self.mergeList[1],
            self.mergeList[2],
            force=force,
            parent=self.__ui,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            urlrev1, urlrev2, target, force = dlg.getParameters()
        else:
            return

        # remember URL or revision
        if urlrev1 in self.mergeList[0]:
            self.mergeList[0].remove(urlrev1)
        self.mergeList[0].insert(0, urlrev1)
        if urlrev2 in self.mergeList[1]:
            self.mergeList[1].remove(urlrev2)
        self.mergeList[1].insert(0, urlrev2)

        rx_rev = re.compile("\\d+|HEAD")

        args = []
        args.append("merge")
        self.addArguments(args, opts)
        if self.version >= (1, 5, 0):
            args.append("--accept")
            args.append("postpone")
        if force:
            args.append("--force")
        if rx_rev.fullmatch(urlrev1) is not None:
            args.append("-r")
            args.append("{0}:{1}".format(urlrev1, urlrev2))
            if not target:
                args.append(name)
            else:
                args.append(target)

            # remember target
            if target in self.mergeList[2]:
                self.mergeList[2].remove(target)
            self.mergeList[2].insert(0, target)
        else:
            args.append(self.__svnURL(urlrev1))
            args.append(self.__svnURL(urlrev2))
        args.append(fname)

        dia = SvnDialog(self.tr("Merging {0}").format(name), parent=self.__ui)
        res = dia.startProcess(args, dname)
        if res:
            dia.exec()

    def vcsRegisteredState(self, name):
        """
        Public method used to get the registered state of a file in the vcs.

        @param name filename to check
        @type str
        @return registered state
        @rtype VersionControlState
        """
        if self.__wcng:
            return self.__vcsRegisteredState_wcng(name)
        else:
            return self.__vcsRegisteredState_wc(name)

    def __vcsRegisteredState_wcng(self, name):
        """
        Private method used to get the registered state of a file in the vcs.

        This is the variant for subversion installations using the new
        working copy meta-data format.

        @param name filename to check
        @type str
        @return registered state
        @rtype VersionControlState
        """
        if name.endswith(os.sep):
            name = name[:-1]
        name = os.path.normcase(name)
        dname, fname = self.splitPath(name)

        if fname == "." and os.path.isdir(os.path.join(dname, self.adminDir)):
            return VersionControlState.Controlled

        if name in self.statusCache:
            return self.statusCache[name]

        name = os.path.normcase(name)
        states = {name: 0}
        states = self.vcsAllRegisteredStates(states, dname, False)
        if states[name] == VersionControlState.Controlled:
            return VersionControlState.Controlled
        else:
            return VersionControlState.Uncontrolled

    def __vcsRegisteredState_wc(self, name):
        """
        Private method used to get the registered state of a file in the VCS.

        This is the variant for subversion installations using the old working
        copy meta-data format.

        @param name filename to check
        @type str
        @return registered state
        @rtype VersionControlState
        """
        dname, fname = self.splitPath(name)

        if fname == ".":
            if os.path.isdir(os.path.join(dname, self.adminDir)):
                return VersionControlState.Controlled
            else:
                return VersionControlState.Uncontrolled

        name = os.path.normcase(name)
        states = {name: 0}
        states = self.vcsAllRegisteredStates(states, dname, False)
        if states[name] == VersionControlState.Controlled:
            return VersionControlState.Controlled
        else:
            return VersionControlState.Uncontrolled

    def vcsAllRegisteredStates(self, names, dname, shortcut=True):
        """
        Public method used to get the registered states of a number of files
        in the VCS.

        <b>Note:</b> If a shortcut is to be taken, the code will only check,
        if the named directory has been scanned already. If so, it is assumed,
        that the states for all files have been populated by the previous run.

        @param names dictionary with all filenames to be checked as keys
        @type dict
        @param dname directory to check in
        @type str
        @param shortcut flag indicating a shortcut should be taken
        @type bool
        @return the received dictionary completed with the VCS state or None in
            order to signal an error
        @rtype dict
        """
        if self.__wcng:
            return self.__vcsAllRegisteredStates_wcng(names, dname)
        else:
            return self.__vcsAllRegisteredStates_wc(names, dname, shortcut)

    def __vcsAllRegisteredStates_wcng(self, names, dname):
        """
        Private method used to get the registered states of a number of files
        in the VCS.

        This is the variant for subversion installations using the new working
        copy meta-data format.

        <b>Note:</b> If a shortcut is to be taken, the code will only check,
        if the named directory has been scanned already. If so, it is assumed,
        that the states for all files has been populated by the previous run.

        @param names dictionary with all filenames to be checked as keys
        @type dict
        @param dname directory to check in
        @type str
        @return the received dictionary completed with the VCS state or None in
            order to signal an error
        @rtype dict
        """
        if dname.endswith(os.sep):
            dname = dname[:-1]
        dname = os.path.normcase(dname)

        found = False
        for name in self.statusCache:
            if name in names:
                found = True
                names[name] = self.statusCache[name]

        if not found:
            # find the root of the repo
            repodir = dname
            while not os.path.isdir(os.path.join(repodir, self.adminDir)):
                repodir = os.path.dirname(repodir)
                if os.path.splitdrive(repodir)[1] == os.sep:
                    return names

            ioEncoding = str(Preferences.getSystem("IOEncoding"))
            process = QProcess()
            args = []
            args.append("status")
            args.append("--verbose")
            args.append("--non-interactive")
            args.append(dname)
            process.start("svn", args)
            procStarted = process.waitForStarted(5000)
            if procStarted:
                finished = process.waitForFinished(30000)
                if finished and process.exitCode() == 0:
                    output = str(process.readAllStandardOutput(), ioEncoding, "replace")
                    for line in output.splitlines():
                        match = self.rx_status1.fullmatch(line)
                        if match is not None:
                            flags = match.group(1)
                            path = match.group(5).strip()
                        else:
                            match = self.rx_status2.fullmatch(line)
                            if match is not None:
                                flags = match.group(1)
                                path = match.group(2).strip()
                            else:
                                continue
                        name = os.path.normcase(path)
                        if flags[0] not in "?I":
                            if name in names:
                                names[name] = VersionControlState.Controlled
                            self.statusCache[name] = VersionControlState.Controlled
                        else:
                            self.statusCache[name] = VersionControlState.Uncontrolled

        return names

    def __vcsAllRegisteredStates_wc(self, names, dname, shortcut=True):
        """
        Private method used to get the registered states of a number of files
        in the VCS.

        This is the variant for subversion installations using the old working
        copy meta-data format.

        <b>Note:</b> If a shortcut is to be taken, the code will only check,
        if the named directory has been scanned already. If so, it is assumed,
        that the states for all files has been populated by the previous run.

        @param names dictionary with all filenames to be checked as keys
        @type dict
        @param dname directory to check in
        @type str
        @param shortcut flag indicating a shortcut should be taken
        @type bool
        @return the received dictionary completed with the VCS state or None in
            order to signal an error
        @rtype dict
        """
        if not os.path.isdir(os.path.join(dname, self.adminDir)):
            # not under version control -> do nothing
            return names

        found = False
        for name in self.statusCache:
            if os.path.dirname(name) == dname:
                if shortcut:
                    found = True
                    break
                if name in names:
                    found = True
                    names[name] = self.statusCache[name]

        if not found:
            ioEncoding = Preferences.getSystem("IOEncoding")
            process = QProcess()
            args = []
            args.append("status")
            args.append("--verbose")
            args.append("--non-interactive")
            args.append(dname)
            process.start("svn", args)
            procStarted = process.waitForStarted(5000)
            if procStarted:
                finished = process.waitForFinished(30000)
                if finished and process.exitCode() == 0:
                    output = str(process.readAllStandardOutput(), ioEncoding, "replace")
                    for line in output.splitlines():
                        match = self.rx_status1.fullmatch(line)
                        if match is not None:
                            flags = match.group(1)
                            path = match.group(5).strip()
                        else:
                            match = self.rx_status2.fullmatch(line)
                            if match is not None:
                                flags = match.group(1)
                                path = match.group(2).strip()
                            else:
                                continue
                        name = os.path.normcase(path)
                        if flags[0] not in "?I":
                            if name in names:
                                names[name] = VersionControlState.Controlled
                            self.statusCache[name] = VersionControlState.Controlled
                        else:
                            self.statusCache[name] = VersionControlState.Uncontrolled

        return names

    def clearStatusCache(self):
        """
        Public method to clear the status cache.
        """
        self.statusCache = {}

    def vcsInitConfig(self, _project):
        """
        Public method to initialize the VCS configuration.

        This method ensures, that an ignore file exists.

        @param _project reference to the project (unused)
        @type Project
        """
        configPath = getConfigPath()
        if os.path.exists(configPath):
            amendConfig()
        else:
            createDefaultConfig()

    def vcsName(self):
        """
        Public method returning the name of the vcs.

        @return always 'Subversion'
        @rtype str
        """
        return "Subversion"

    def vcsCleanup(self, name):
        """
        Public method used to cleanup the working copy.

        @param name directory name to be cleaned up
        @type str
        """
        args = []
        args.append("cleanup")
        self.addArguments(args, self.options["global"])
        args.append(name)

        dia = SvnDialog(self.tr("Cleaning up {0}").format(name), parent=self.__ui)
        res = dia.startProcess(args)
        if res:
            dia.exec()

    def vcsCommandLine(self, name):
        """
        Public method used to execute arbitrary subversion commands.

        @param name directory name of the working directory
        @type str
        """
        from .SvnCommandDialog import SvnCommandDialog

        dlg = SvnCommandDialog(
            self.commandHistory, self.wdHistory, name, parent=self.__ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            command, wd = dlg.getData()
            commandList = Utilities.parseOptionString(command)

            # This moves any previous occurrence of these arguments to the head
            # of the list.
            if command in self.commandHistory:
                self.commandHistory.remove(command)
            self.commandHistory.insert(0, command)
            if wd in self.wdHistory:
                self.wdHistory.remove(wd)
            self.wdHistory.insert(0, wd)

            args = []
            self.addArguments(args, commandList)

            dia = SvnDialog(self.tr("Subversion command"), parent=self.__ui)
            res = dia.startProcess(args, wd)
            if res:
                dia.exec()

    def vcsOptionsDialog(
        self, project, _archive, editable=False, parent=None  # noqa: U100
    ):
        """
        Public method to get a dialog to enter repository info.

        @param project reference to the project object
        @type Project
        @param _archive name of the project in the repository (unused)
        @type str
        @param editable flag indicating that the project name is editable (unused)
        @type bool
        @param parent parent widget
        @type QWidget
        @return reference to the instantiated options dialog
        @rtype SvnOptionsDialog
        """
        from .SvnOptionsDialog import SvnOptionsDialog

        return SvnOptionsDialog(self, project, parent)

    def vcsNewProjectOptionsDialog(self, parent=None):
        """
        Public method to get a dialog to enter repository info for getting
        a new project.

        @param parent parent widget
        @type QWidget
        @return reference to the instantiated options dialog
        @rtype SvnNewProjectOptionsDialog
        """
        from .SvnNewProjectOptionsDialog import SvnNewProjectOptionsDialog

        return SvnNewProjectOptionsDialog(self, parent)

    def vcsRepositoryInfos(self, ppath):
        """
        Public method to retrieve information about the repository.

        @param ppath local path to get the repository infos
        @type str
        @return string with ready formated info for display
        @rtype str
        """
        info = {
            "committed-rev": "",
            "committed-date": "",
            "committed-time": "",
            "url": "",
            "last-author": "",
            "revision": "",
        }

        ioEncoding = Preferences.getSystem("IOEncoding")

        process = QProcess()
        args = []
        args.append("info")
        args.append("--non-interactive")
        args.append("--xml")
        args.append(ppath)
        process.start("svn", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(process.readAllStandardOutput(), ioEncoding, "replace")
                entryFound = False
                commitFound = False
                for line in output.splitlines():
                    line = line.strip()
                    if line.startswith("<entry"):
                        entryFound = True
                    elif line.startswith("<commit"):
                        commitFound = True
                    elif line.startswith("</commit>"):
                        commitFound = False
                    elif line.startswith("revision="):
                        rev = line[line.find('"') + 1 : line.rfind('"')]
                        if entryFound:
                            info["revision"] = rev
                            entryFound = False
                        elif commitFound:
                            info["committed-rev"] = rev
                    elif line.startswith("<url>"):
                        info["url"] = line.replace("<url>", "").replace("</url>", "")
                    elif line.startswith("<author>"):
                        info["last-author"] = line.replace("<author>", "").replace(
                            "</author>", ""
                        )
                    elif line.startswith("<date>"):
                        value = line.replace("<date>", "").replace("</date>", "")
                        date, time = value.split("T")
                        info["committed-date"] = date
                        info["committed-time"] = "{0}{1}".format(
                            time.split(".")[0], time[-1]
                        )

        return QCoreApplication.translate(
            "subversion",
            """<h3>Repository information</h3>"""
            """<table>"""
            """<tr><td><b>Subversion V.</b></td><td>{0}</td></tr>"""
            """<tr><td><b>URL</b></td><td>{1}</td></tr>"""
            """<tr><td><b>Current revision</b></td><td>{2}</td></tr>"""
            """<tr><td><b>Committed revision</b></td><td>{3}</td></tr>"""
            """<tr><td><b>Committed date</b></td><td>{4}</td></tr>"""
            """<tr><td><b>Comitted time</b></td><td>{5}</td></tr>"""
            """<tr><td><b>Last author</b></td><td>{6}</td></tr>"""
            """</table>""",
        ).format(
            self.versionStr,
            info["url"],
            info["revision"],
            info["committed-rev"],
            info["committed-date"],
            info["committed-time"],
            info["last-author"],
        )

    ###########################################################################
    ## Public Subversion specific methods are below.
    ###########################################################################

    def svnGetReposName(self, path):
        """
        Public method used to retrieve the URL of the subversion repository
        path.

        @param path local path to get the svn repository path for
        @type str
        @return string with the repository path URL
        @rtype str
        """
        ioEncoding = Preferences.getSystem("IOEncoding")

        process = QProcess()
        args = []
        args.append("info")
        args.append("--xml")
        args.append("--non-interactive")
        args.append(path)
        process.start("svn", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(process.readAllStandardOutput(), ioEncoding, "replace")
                for line in output.splitlines():
                    line = line.strip()
                    if line.startswith("<url>"):
                        reposURL = line.replace("<url>", "").replace("</url>", "")
                        return reposURL

        return ""

    def vcsResolved(self, name):
        """
        Public method used to resolve conflicts of a file/directory.

        @param name file/directory name to be resolved
        @type str
        """
        args = []
        if self.version >= (1, 5, 0):
            args.append("resolve")
            args.append("--accept")
            args.append("working")
        else:
            args.append("resolved")
        self.addArguments(args, self.options["global"])
        if isinstance(name, list):
            self.addArguments(args, name)
        else:
            if os.path.isdir(name):
                args.append("--recursive")
            args.append(name)

        dia = SvnDialog(self.tr("Resolving conficts"), parent=self.__ui)
        res = dia.startProcess(args)
        if res:
            dia.exec()
        self.checkVCSStatus()

    def svnCopy(self, name, project):
        """
        Public method used to copy a file/directory.

        @param name file/directory name to be copied
        @type str
        @param project reference to the project object
        @type Project
        @return flag indicating successfull operation
        @rtype bool
        """
        from .SvnCopyDialog import SvnCopyDialog

        rx_prot = re.compile("(file:|svn:|svn+ssh:|http:|https:).+")
        dlg = SvnCopyDialog(name, parent=self.__ui)
        res = False
        if dlg.exec() == QDialog.DialogCode.Accepted:
            target, force = dlg.getData()

            args = []
            args.append("copy")
            self.addArguments(args, self.options["global"])
            match = rx_prot.fullmatch(target)
            if match is not None:
                args.append("--message")
                args.append("Copying {0} to {1}".format(name, target))
                target = self.__svnURL(target)
            args.append(name)
            args.append(target)

            dia = SvnDialog(self.tr("Copying {0}").format(name), parent=self.__ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()
                res = dia.normalExit()
                if (
                    res
                    and match is None
                    and target.startswith(project.getProjectPath())
                ):
                    if os.path.isdir(name):
                        project.copyDirectory(name, target)
                    else:
                        project.appendFile(target)
        return res

    def svnListProps(self, name, recursive=False):
        """
        Public method used to list the properties of a file/directory.

        @param name file/directory name
        @type str or list of str
        @param recursive flag indicating a recursive list is requested
        @type bool
        """
        from .SvnPropListDialog import SvnPropListDialog

        if self.propList is None:
            self.propList = SvnPropListDialog(self)
        self.propList.show()
        self.propList.raise_()
        self.propList.start(name, recursive)

    def svnSetProp(self, name, recursive=False):
        """
        Public method used to add a property to a file/directory.

        @param name file/directory name
        @type str or list of str
        @param recursive flag indicating a recursive list is requested
        @type bool
        """
        from .SvnPropSetDialog import SvnPropSetDialog

        dlg = SvnPropSetDialog(parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            propName, fileFlag, propValue = dlg.getData()
            if not propName:
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("Subversion Set Property"),
                    self.tr("""You have to supply a property name. Aborting."""),
                )
                return

            args = []
            args.append("propset")
            self.addArguments(args, self.options["global"])
            if recursive:
                args.append("--recursive")
            args.append(propName)
            if fileFlag:
                args.append("--file")
            args.append(propValue)
            if isinstance(name, list):
                dname, fnames = self.splitPathList(name)
                self.addArguments(args, fnames)
            else:
                dname, fname = self.splitPath(name)
                args.append(fname)

            dia = SvnDialog(self.tr("Subversion Set Property"), parent=self.__ui)
            res = dia.startProcess(args, dname)
            if res:
                dia.exec()

    def svnDelProp(self, name, recursive=False):
        """
        Public method used to delete a property of a file/directory.

        @param name file/directory name
        @type str or list of str
        @param recursive flag indicating a recursive list is requested
        @type bool
        """
        propName, ok = QInputDialog.getText(
            None,
            self.tr("Subversion Delete Property"),
            self.tr("Enter property name"),
            QLineEdit.EchoMode.Normal,
        )

        if not ok:
            return

        if not propName:
            EricMessageBox.critical(
                self.__ui,
                self.tr("Subversion Delete Property"),
                self.tr("""You have to supply a property name. Aborting."""),
            )
            return

        args = []
        args.append("propdel")
        self.addArguments(args, self.options["global"])
        if recursive:
            args.append("--recursive")
        args.append(propName)
        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
            self.addArguments(args, fnames)
        else:
            dname, fname = self.splitPath(name)
            args.append(fname)

        dia = SvnDialog(self.tr("Subversion Delete Property"), parent=self.__ui)
        res = dia.startProcess(args, dname)
        if res:
            dia.exec()

    def svnListTagBranch(self, path, tags=True):
        """
        Public method used to list the available tags or branches.

        @param path directory name of the project
        @type str
        @param tags flag indicating listing of branches or tags
            (False = branches, True = tags)
        @type bool
        """
        from .SvnTagBranchListDialog import SvnTagBranchListDialog

        if self.tagbranchList is None:
            self.tagbranchList = SvnTagBranchListDialog(self)
        self.tagbranchList.show()
        self.tagbranchList.raise_()
        if tags:
            if not self.showedTags:
                self.showedTags = True
                allTagsBranchesList = self.allTagsBranchesList
            else:
                self.tagsList = []
                allTagsBranchesList = None
            self.tagbranchList.start(path, tags, self.tagsList, allTagsBranchesList)
        elif not tags:
            if not self.showedBranches:
                self.showedBranches = True
                allTagsBranchesList = self.allTagsBranchesList
            else:
                self.branchesList = []
                allTagsBranchesList = None
            self.tagbranchList.start(
                path, tags, self.branchesList, self.allTagsBranchesList
            )

    def svnBlame(self, name):
        """
        Public method to show the output of the svn blame command.

        @param name file name to show the blame for
        @type str
        """
        from .SvnBlameDialog import SvnBlameDialog

        if self.blame is None:
            self.blame = SvnBlameDialog(self)
        self.blame.show()
        self.blame.raise_()
        self.blame.start(name)

    def svnExtendedDiff(self, name):
        """
        Public method used to view the difference of a file/directory to the
        Subversion repository.

        If name is a directory and is the project directory, all project files
        are saved first. If name is a file (or list of files), which is/are
        being edited and has unsaved modification, they can be saved or the
        operation may be aborted.

        This method gives the chance to enter the revisions to be compared.

        @param name file/directory name to be diffed
        @type str
        """
        from .SvnDiffDialog import SvnDiffDialog
        from .SvnRevisionSelectionDialog import SvnRevisionSelectionDialog

        names = name[:] if isinstance(name, list) else [name]
        for nam in names:
            if os.path.isfile(nam):
                editor = ericApp().getObject("ViewManager").getOpenEditor(nam)
                if editor and not editor.checkDirty():
                    return
            else:
                project = ericApp().getObject("Project")
                if nam == project.ppath and not project.saveAllScripts():
                    return
        dlg = SvnRevisionSelectionDialog(parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            revisions = dlg.getRevisions()
            self.diff = SvnDiffDialog(self)
            self.diff.show()
            self.diff.start(name, revisions)

    def svnUrlDiff(self, name):
        """
        Public method used to view the difference of a file/directory of two
        repository URLs.

        If name is a directory and is the project directory, all project files
        are saved first. If name is a file (or list of files), which is/are
        being edited and has unsaved modification, they can be saved or the
        operation may be aborted.

        This method gives the chance to enter the revisions to be compared.

        @param name file/directory name to be diffed
        @type str
        """
        from .SvnDiffDialog import SvnDiffDialog
        from .SvnUrlSelectionDialog import SvnUrlSelectionDialog

        names = name[:] if isinstance(name, list) else [name]
        for nam in names:
            if os.path.isfile(nam):
                editor = ericApp().getObject("ViewManager").getOpenEditor(nam)
                if editor and not editor.checkDirty():
                    return
            else:
                project = ericApp().getObject("Project")
                if nam == project.ppath and not project.saveAllScripts():
                    return

        dname = self.splitPath(names[0])[0]

        dlg = SvnUrlSelectionDialog(
            self, self.tagsList, self.branchesList, dname, parent=self.__ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            urls, summary = dlg.getURLs()
            self.diff = SvnDiffDialog(self)
            self.diff.show()
            QApplication.processEvents()
            self.diff.start(name, urls=urls, summary=summary)

    def __svnGetFileForRevision(self, name, rev=""):
        """
        Private method to get a file for a specific revision from the
        repository.

        @param name file name to get from the repository
        @type str
        @param rev revision to retrieve
        @type int or str
        @return contents of the file (string) and an error message
        @rtype str
        """
        args = []
        args.append("cat")
        if rev:
            args.append("--revision")
            args.append(str(rev))
        args.append(name)

        output = ""
        error = ""

        process = QProcess()
        process.start("svn", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished:
                if process.exitCode() == 0:
                    output = str(
                        process.readAllStandardOutput(),
                        Preferences.getSystem("IOEncoding"),
                        "replace",
                    )
                else:
                    error = str(
                        process.readAllStandardError(),
                        Preferences.getSystem("IOEncoding"),
                        "replace",
                    )
            else:
                error = self.tr("The svn process did not finish within 30s.")
        else:
            error = self.tr(
                "The process {0} could not be started. "
                "Ensure, that it is in the search path."
            ).format("svn")

        return output, error

    def vcsSbsDiff(self, name, extended=False, revisions=None):
        """
        Public method used to view the difference of a file to the Mercurial
        repository side-by-side.

        @param name file name to be diffed
        @type str
        @param extended flag indicating the extended variant
        @type bool
        @param revisions tuple of two revisions
        @type tuple of (str, str)
        @exception ValueError raised to indicate an illegal name parameter type
        """
        from eric7.UI.CompareDialog import CompareDialog

        from .SvnRevisionSelectionDialog import SvnRevisionSelectionDialog

        if isinstance(name, list):
            raise ValueError("Wrong parameter type")

        if extended:
            dlg = SvnRevisionSelectionDialog(parent=self.__ui)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                rev1, rev2 = dlg.getRevisions()
                if rev1 == "WORKING":
                    rev1 = ""
                if rev2 == "WORKING":
                    rev2 = ""
            else:
                return
        elif revisions:
            rev1, rev2 = revisions[0], revisions[1]
        else:
            rev1, rev2 = "", ""

        output1, error = self.__svnGetFileForRevision(name, rev=rev1)
        if error:
            EricMessageBox.critical(
                self.__ui, self.tr("Subversion Side-by-Side Difference"), error
            )
            return
        name1 = "{0} (rev. {1})".format(name, rev1 and rev1 or ".")

        if rev2:
            output2, error = self.__svnGetFileForRevision(name, rev=rev2)
            if error:
                EricMessageBox.critical(
                    self.__ui, self.tr("Subversion Side-by-Side Difference"), error
                )
                return
            name2 = "{0} (rev. {1})".format(name, rev2)
        else:
            try:
                with open(name, "r", encoding="utf-8") as f1:
                    output2 = f1.read()
                name2 = name
            except OSError:
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("Subversion Side-by-Side Difference"),
                    self.tr("""<p>The file <b>{0}</b> could not be read.</p>""").format(
                        name
                    ),
                )
                return

        if self.sbsDiff is None:
            self.sbsDiff = CompareDialog()
        self.sbsDiff.show()
        self.sbsDiff.raise_()
        self.sbsDiff.compare(output1, output2, name1, name2)

    def vcsLogBrowser(self, name, isFile=False):
        """
        Public method used to browse the log of a file/directory from the
        Subversion repository.

        @param name file/directory name to show the log of
        @type str
        @param isFile flag indicating log for a file is to be shown
        @type bool
        """
        from .SvnLogBrowserDialog import SvnLogBrowserDialog

        if self.logBrowser is None:
            self.logBrowser = SvnLogBrowserDialog(self)
        self.logBrowser.show()
        self.logBrowser.raise_()
        self.logBrowser.start(name, isFile=isFile)

    def svnLock(self, name, stealIt=False, parent=None):
        """
        Public method used to lock a file in the Subversion repository.

        @param name file/directory name to be locked
        @type str or list of str
        @param stealIt flag indicating a forced operation
        @type bool
        @param parent reference to the parent object of the subversion dialog
        @type QWidget
        """
        args = []
        args.append("lock")
        self.addArguments(args, self.options["global"])
        if stealIt:
            args.append("--force")
        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
            self.addArguments(args, fnames)
        else:
            dname, fname = self.splitPath(name)
            args.append(fname)

        dia = SvnDialog(self.tr("Locking in the Subversion repository"), parent=parent)
        res = dia.startProcess(args, dname)
        if res:
            dia.exec()

    def svnUnlock(self, name, breakIt=False, parent=None):
        """
        Public method used to unlock a file in the Subversion repository.

        @param name file/directory name to be unlocked
        @type str or list of str
        @param breakIt flag indicating a forced operation
        @type bool
        @param parent reference to the parent object of the subversion dialog
        @type QWidget
        """
        args = []
        args.append("unlock")
        self.addArguments(args, self.options["global"])
        if breakIt:
            args.append("--force")
        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
            self.addArguments(args, fnames)
        else:
            dname, fname = self.splitPath(name)
            args.append(fname)

        dia = SvnDialog(
            self.tr("Unlocking in the Subversion repository"), parent=parent
        )
        res = dia.startProcess(args, dname)
        if res:
            dia.exec()

    def svnRelocate(self, projectPath):
        """
        Public method to relocate the working copy to a new repository URL.

        @param projectPath path name of the project
        @type str
        """
        from .SvnRelocateDialog import SvnRelocateDialog

        currUrl = self.svnGetReposName(projectPath)
        dlg = SvnRelocateDialog(currUrl, parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            newUrl, inside = dlg.getData()
            args = []
            args.append("switch")
            if not inside:
                args.append("--relocate")
                args.append(currUrl)
            args.append(newUrl)
            args.append(projectPath)

            dia = SvnDialog(self.tr("Relocating"), parent=self.__ui)
            res = dia.startProcess(args)
            if res:
                dia.exec()

    def svnRepoBrowser(self, projectPath=None):
        """
        Public method to open the repository browser.

        @param projectPath path name of the project
        @type str
        """
        from .SvnRepoBrowserDialog import SvnRepoBrowserDialog

        url = self.svnGetReposName(projectPath) if projectPath else None

        if url is None:
            url, ok = QInputDialog.getText(
                None,
                self.tr("Repository Browser"),
                self.tr("Enter the repository URL."),
                QLineEdit.EchoMode.Normal,
            )
            if not ok or not url:
                return

        if self.repoBrowser is None:
            self.repoBrowser = SvnRepoBrowserDialog(self)
        self.repoBrowser.show()
        self.repoBrowser.raise_()
        self.repoBrowser.start(url)

    def svnRemoveFromChangelist(self, names):
        """
        Public method to remove a file or directory from its changelist.

        Note: Directories will be removed recursively.

        @param names name or list of names of file or directory to remove
        @type str or list of str
        """
        args = []
        args.append("changelist")
        self.addArguments(args, self.options["global"])
        args.append("--remove")
        args.append("--recursive")
        if isinstance(names, list):
            dname, fnames = self.splitPathList(names)
            self.addArguments(args, fnames)
        else:
            dname, fname = self.splitPath(names)
            args.append(fname)

        dia = SvnDialog(self.tr("Remove from changelist"), parent=self.__ui)
        res = dia.startProcess(args, dname)
        if res:
            dia.exec()

    def svnAddToChangelist(self, names):
        """
        Public method to add a file or directory to a changelist.

        Note: Directories will be added recursively.

        @param names name or list of names of file or directory to add
        @type str or list of str
        """
        clname, ok = QInputDialog.getItem(
            None,
            self.tr("Add to changelist"),
            self.tr("Enter name of the changelist:"),
            sorted(self.svnGetChangelists()),
            0,
            True,
        )
        if not ok or not clname:
            return

        args = []
        args.append("changelist")
        self.addArguments(args, self.options["global"])
        args.append("--recursive")
        args.append(clname)
        if isinstance(names, list):
            dname, fnames = self.splitPathList(names)
            self.addArguments(args, fnames)
        else:
            dname, fname = self.splitPath(names)
            args.append(fname)

        dia = SvnDialog(self.tr("Remove from changelist"), parent=self.__ui)
        res = dia.startProcess(args, dname)
        if res:
            dia.exec()

    def svnShowChangelists(self, path):
        """
        Public method used to inspect the change lists defined for the project.

        @param path directory name to show change lists for
        @type str
        """
        from .SvnChangeListsDialog import SvnChangeListsDialog

        self.changeLists = SvnChangeListsDialog(self)
        self.changeLists.show()
        QApplication.processEvents()
        self.changeLists.start(path)

    def svnGetChangelists(self):
        """
        Public method to get a list of all defined change lists.

        @return list of defined change list names
        @rtype list of str
        """
        changelists = []
        rx_changelist = re.compile("--- \\S+ .([\\w\\s]+).:\\s*")
        # three dashes, Changelist (translated), quote,
        # changelist name, quote, :

        args = []
        args.append("status")
        args.append("--non-interactive")
        args.append(".")

        ppath = ericApp().getObject("Project").getProjectPath()
        process = QProcess()
        process.setWorkingDirectory(ppath)
        process.start("svn", args)
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
                    for line in output.splitlines():
                        match = rx_changelist.fullmatch(line)
                        if match is not None:
                            changelist = match.group(1)
                            if changelist not in changelists:
                                changelists.append(changelist)

        return changelists

    def svnUpgrade(self, path):
        """
        Public method to upgrade the working copy format.

        @param path directory name to show change lists for
        @type str
        """
        args = []
        args.append("upgrade")
        args.append(".")

        dia = SvnDialog(self.tr("Upgrade"), parent=self.__ui)
        res = dia.startProcess(args, path)
        if res:
            dia.exec()

    ###########################################################################
    ## Private Subversion specific methods are below.
    ###########################################################################

    def __svnURL(self, url):
        """
        Private method to format a url for subversion.

        @param url unformatted url string
        @type str
        @return properly formated url for subversion
        @rtype str
        """
        url = self.svnNormalizeURL(url)
        url = url.split(":", 2)
        if len(url) == 3:
            scheme = url[0]
            host = url[1]
            port, path = url[2].split("/", 1)
            return "{0}:{1}:{2}/{3}".format(scheme, host, port, quote(path))
        else:
            scheme = url[0]
            if scheme == "file":
                return "{0}:{1}".format(scheme, quote(url[1]))
            else:
                try:
                    host, path = url[1][2:].split("/", 1)
                except ValueError:
                    host = url[1][2:]
                    path = ""
                return "{0}://{1}/{2}".format(scheme, host, quote(path))

    def svnNormalizeURL(self, url):
        """
        Public method to normalize a url for subversion.

        @param url url string
        @type str
        @return properly normalized url for subversion
        @rtype str
        """
        protocol, url = url.split("://", 1)
        if url.startswith("\\\\"):
            url = url[2:]
        if protocol == "file":
            url = os.path.normcase(url)
        url = url.replace("\\", "/")
        if url.endswith("/"):
            url = url[:-1]
        if not url.startswith("/") and url[1] in [":", "|"]:
            url = "/{0}".format(url)
        return "{0}://{1}".format(protocol, url)

    ###########################################################################
    ## Methods to get the helper objects are below.
    ###########################################################################

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
        @rtype SvnProjectBrowserHelper
        """
        from .ProjectBrowserHelper import SvnProjectBrowserHelper

        return SvnProjectBrowserHelper(self, browser, project, isTranslationsBrowser)

    def vcsGetProjectHelper(self, project):
        """
        Public method to instanciate a helper object for the project.

        @param project reference to the project object
        @type Project
        @return the project helper object
        @rtype SvnProjectHelper
        """
        helper = self.__plugin.getProjectHelper()
        helper.setObjects(self, project)
        self.__wcng = (
            os.path.exists(os.path.join(project.getProjectPath(), ".svn", "format"))
            or os.path.exists(os.path.join(project.getProjectPath(), "_svn", "format"))
            or os.path.exists(os.path.join(project.getProjectPath(), ".svn", "wc.db"))
            or os.path.exists(os.path.join(project.getProjectPath(), "_svn", "wc.db"))
        )
        return helper

    ###########################################################################
    ##  Status Monitor Thread methods
    ###########################################################################

    def _createStatusMonitorThread(self, interval, project):
        """
        Protected method to create an instance of the VCS status monitor
        thread.

        @param interval check interval for the monitor thread in seconds
        @type int
        @param project reference to the project object
        @type Project
        @return reference to the monitor thread
        @rtype SvnStatusMonitorThread
        """
        from .SvnStatusMonitorThread import SvnStatusMonitorThread

        return SvnStatusMonitorThread(interval, project, self)
