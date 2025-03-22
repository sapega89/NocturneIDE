# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the version control systems interface to Subversion.
"""

import contextlib
import os
import re
import shutil
import time

from urllib.parse import quote

import pysvn

from PyQt6.QtCore import QCoreApplication, QDateTime, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog, QInputDialog, QLineEdit

from eric7 import Preferences, Utilities
from eric7.EricUtilities.EricMutexLocker import EricMutexLocker
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

        self.tagTypeList = ["tags", "branches"]

        self.commandHistory = []
        self.wdHistory = []

        if pysvn.version >= (1, 4, 3, 0) and "SVN_ASP_DOT_NET_HACK" in os.environ:
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

        self.statusCache = {}

        self.__commitData = {}
        self.__commitDialog = None

        self.__wcng = True
        # assume new generation working copy metadata format

    def getPlugin(self):
        """
        Public method to get a reference to the plugin object.

        @return reference to the plugin object
        @rtype VcsPySvnPlugin
        """
        return self.__plugin

    def getClient(self):
        """
        Public method to create and initialize the pysvn client object.

        @return the pysvn client object
        @rtype pysvn.Client
        """
        configDir = ""
        authCache = True
        for arg in self.options["global"]:
            if arg.startswith("--config-dir"):
                configDir = arg.split("=", 1)[1]
            if arg.startswith("--no-auth-cache"):
                authCache = False

        client = pysvn.Client(configDir)
        client.exception_style = 1
        client.set_auth_cache(authCache)

        return client

    ###########################################################################
    ## Methods of the VCS interface
    ###########################################################################

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

        @return flag indicating the existance and an error message
        @rtype tuple of (bool, str)
        """
        self.versionStr = ".".join([str(v) for v in pysvn.svn_version[:-1]])
        self.version = pysvn.svn_version[:-1]
        return True, ""

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

        cwd = os.getcwd()
        os.chdir(os.path.join(tmpDir, project))
        opts = self.options["global"]
        recurse = "--non-recursive" not in opts
        url = self.__svnURL(vcsDir)
        client = self.getClient()
        if not noDialog:
            dlg = SvnDialog(
                self.tr("Importing project into Subversion repository"),
                "import{0} --message {1} .".format(
                    (not recurse) and " --non-recursive" or "", msg
                ),
                client,
                parent=self.__ui,
            )
            QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                rev = client.import_(".", url, msg, recurse, ignore=True)
            status = True
        except pysvn.ClientError as e:
            status = False
            rev = None
            if not noDialog:
                dlg.showError(e.args[0])
        if not noDialog:
            rev and dlg.showMessage(
                self.tr("Imported revision {0}.\n").format(rev.number)
            )
            dlg.finish()
            dlg.exec()
        os.chdir(cwd)

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
                    type_, ok = QInputDialog.getItem(
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
                    tag = "{0}/{1}".format(type_, tag)
                svnUrl = "{0}/{1}".format(vcsDir, tag)
        else:
            svnUrl = vcsDir

        opts = self.options["global"] + self.options["checkout"]
        recurse = "--non-recursive" not in opts
        url = self.__svnURL(svnUrl)
        client = self.getClient()
        if not noDialog:
            dlg = SvnDialog(
                self.tr("Checking project out of Subversion repository"),
                "checkout{0} {1} {2}".format(
                    (not recurse) and " --non-recursive" or "", url, projectDir
                ),
                client,
                parent=self.__ui,
            )
            QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.checkout(url, projectDir, recurse)
            status = True
        except pysvn.ClientError as e:
            status = False
            if not noDialog:
                dlg.showError(e.args[0])
        if not noDialog:
            dlg.finish()
            dlg.exec()
        return status

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
                    type_, ok = QInputDialog.getItem(
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
                    tag = "{0}/{1}".format(type_, tag)
                svnUrl = "{0}/{1}".format(vcsDir, tag)
        else:
            svnUrl = vcsDir

        opts = self.options["global"]
        recurse = "--non-recursive" not in opts
        url = self.__svnURL(svnUrl)
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Exporting project from Subversion repository"),
            "export --force{0} {1} {2}".format(
                (not recurse) and " --non-recursive" or "", url, projectDir
            ),
            client,
            parent=self.__ui,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.export(url, projectDir, force=True, recurse=recurse)
            status = True
        except pysvn.ClientError as e:
            status = False
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()
        return status

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

        if not noDialog and not message:
            # call CommitDialog and get message from there
            if self.__commitDialog is None:
                self.__commitDialog = SvnCommitDialog(self, self.__ui)
                self.__commitDialog.accepted.connect(self.__vcsCommit_Step2)
            self.__commitDialog.show()
            self.__commitDialog.raise_()
            self.__commitDialog.activateWindow()

        self.__commitData["name"] = name
        self.__commitData["msg"] = message
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

        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
        else:
            dname, fname = self.splitPath(name)
            fnames = [fname]

        if self.svnGetReposName(dname).startswith("http") or self.svnGetReposName(
            dname
        ).startswith("svn"):
            noDialog = False

        cwd = os.getcwd()
        os.chdir(dname)
        opts = self.options["global"] + self.options["commit"]
        recurse = "--non-recursive" not in opts
        keeplocks = "--keep-locks" in opts
        client = self.getClient()
        if not noDialog:
            dlg = SvnDialog(
                self.tr("Commiting changes to Subversion repository"),
                "commit{0}{1}{2}{3} --message {4} {5}".format(
                    (not recurse) and " --non-recursive" or "",
                    keeplocks and " --keep-locks" or "",
                    keepChangelists and " --keep-changelists" or "",
                    changelists and " --changelist ".join([""] + changelists) or "",
                    msg,
                    " ".join(fnames),
                ),
                client,
                parent=self.__ui,
            )
            QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                rev = (
                    client.checkin(
                        fnames,
                        msg,
                        recurse=recurse,
                        keep_locks=keeplocks,
                        keep_changelist=keepChangelists,
                        changelists=changelists,
                    )
                    if changelists
                    else client.checkin(
                        fnames, msg, recurse=recurse, keep_locks=keeplocks
                    )
                )
        except pysvn.ClientError as e:
            rev = None
            if not noDialog:
                dlg.showError(e.args[0])
        if not noDialog:
            rev and dlg.showMessage(
                self.tr("Committed revision {0}.").format(rev.number)
            )
            dlg.finish()
            dlg.exec()
        os.chdir(cwd)
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
        @type  (str or list of str
        @param noDialog flag indicating quiet operations
        @type bool
        @return flag indicating, that the update contained an add or delete
        @rtype bool
        """
        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
        else:
            dname, fname = self.splitPath(name)
            fnames = [fname]

        cwd = os.getcwd()
        os.chdir(dname)
        opts = self.options["global"] + self.options["update"]
        recurse = "--non-recursive" not in opts
        client = self.getClient()
        if not noDialog:
            dlg = SvnDialog(
                self.tr("Synchronizing with the Subversion repository"),
                "update{0} {1}".format(
                    (not recurse) and " --non-recursive" or "", " ".join(fnames)
                ),
                client,
                parent=self.__ui,
            )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.update(fnames, recurse)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        if not noDialog:
            dlg.finish()
            dlg.exec()
            res = dlg.hasAddOrDelete()
        else:
            res = False
        os.chdir(cwd)
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
        names = []
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
        names.extend(tree)

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
                        (os.path.normcase(d) != os.path.normcase(repodir))
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
            names.extend(tree2)
            names.extend(name)
        else:
            names.append(name)

        cwd = os.getcwd()
        os.chdir(wdir)
        opts = self.options["global"] + self.options["add"]
        recurse = False
        force = "--force" in opts or noDialog
        noignore = "--no-ignore" in opts
        client = self.getClient()
        if not noDialog:
            dlg = SvnDialog(
                self.tr("Adding files/directories to the Subversion repository"),
                "add --non-recursive{0}{1} {2}".format(
                    force and " --force" or "",
                    noignore and " --no-ignore" or "",
                    " ".join(names),
                ),
                client,
                parent=self.__ui,
            )
            QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.add(names, recurse=recurse, force=force, ignore=not noignore)
        except pysvn.ClientError as e:
            if not noDialog:
                dlg.showError(e.args[0])
        if not noDialog:
            dlg.finish()
            dlg.exec()
        os.chdir(cwd)

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
                        (os.path.normcase(d) != os.path.normcase(repodir))
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
                while (os.path.normcase(dname) != os.path.normcase(repodir)) and (
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

        names = []
        if isinstance(path, list):
            names.extend(path)
        else:
            names.append(path)

        cwd = os.getcwd()
        os.chdir(dname)
        opts = self.options["global"] + self.options["add"]
        recurse = True
        force = "--force" in opts
        ignore = "--ignore" in opts
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Adding directory trees to the Subversion repository"),
            "add{0}{1} {2}".format(
                force and " --force" or "",
                ignore and " --ignore" or "",
                " ".join(names),
            ),
            client,
            parent=self.__ui,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.add(names, recurse=recurse, force=force, ignore=ignore)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()
        os.chdir(cwd)

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
        if not isinstance(name, list):
            name = [name]
        opts = self.options["global"] + self.options["remove"]
        force = "--force" in opts or noDialog
        client = self.getClient()
        if not noDialog:
            dlg = SvnDialog(
                self.tr("Removing files/directories from the Subversion repository"),
                "remove{0} {1}".format(force and " --force" or "", " ".join(name)),
                client,
                parent=self.__ui,
            )
            QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.remove(name, force=force)
            res = True
        except pysvn.ClientError as e:
            res = False
            if not noDialog:
                dlg.showError(e.args[0])
        if not noDialog:
            dlg.finish()
            dlg.exec()

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
        opts = self.options["global"]
        res = False

        if noDialog:
            if target is None:
                return False
            force = True
            accepted = True
        else:
            dlg = SvnCopyDialog(
                name, parent=self.__ui, move=True, force="--force" in opts
            )
            accepted = dlg.exec() == QDialog.DialogCode.Accepted
            if accepted:
                target, force = dlg.getData()
            if not target:
                return False

        isDir = os.path.isdir(name) if rx_prot.fullmatch(target) is None else False

        if accepted:
            client = self.getClient()
            if rx_prot.fullmatch(target) is not None:
                target = self.__svnURL(target)
                log = "Moving {0} to {1}".format(name, target)
            else:
                log = ""
            if not noDialog:
                dlg = SvnDialog(
                    self.tr("Moving {0}").format(name),
                    "move{0}{1} {2} {3}".format(
                        force and " --force" or "",
                        log and (" --message {0}".format(log)) or "",
                        name,
                        target,
                    ),
                    client,
                    parent=self.__ui,
                    log=log,
                )
                QApplication.processEvents()
            try:
                with EricMutexLocker(self.vcsExecutionMutex):
                    client.move(name, target, force=force)
                res = True
            except pysvn.ClientError as e:
                res = False
                if not noDialog:
                    dlg.showError(e.args[0])
            if not noDialog:
                dlg.finish()
                dlg.exec()
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
        QApplication.processEvents()
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

        self.tagName = tag
        client = self.getClient()
        rev = None
        if tagOp in [1, 2]:
            log = "Created tag <{0}>".format(self.tagName)
            dlg = SvnDialog(
                self.tr("Tagging {0} in the Subversion repository").format(name),
                "copy --message {0} {1} {2}".format(log, reposURL, url),
                client,
                parent=self.__ui,
                log=log,
            )
            QApplication.processEvents()
            try:
                with EricMutexLocker(self.vcsExecutionMutex):
                    rev = client.copy(reposURL, url)
            except pysvn.ClientError as e:
                dlg.showError(e.args[0])
        else:
            log = "Deleted tag <{0}>".format(self.tagName)
            dlg = SvnDialog(
                self.tr("Tagging {0} in the Subversion repository").format(name),
                "remove --message {0} {1}".format(log, url),
                client,
                parent=self.__ui,
                log=log,
            )
            QApplication.processEvents()
            try:
                with EricMutexLocker(self.vcsExecutionMutex):
                    rev = client.remove(url)
            except pysvn.ClientError as e:
                dlg.showError(e.args[0])
        rev and dlg.showMessage(self.tr("Revision {0}.\n").format(rev.number))
        dlg.finish()
        dlg.exec()

    def vcsRevert(self, name):
        """
        Public method used to revert changes made to a file/directory.

        @param name file/directory name to be reverted
        @type str
        @return flag indicating, that the update contained an add
            or delete
        @rtype bool
        """
        recurse = False
        if not isinstance(name, list):
            name = [name]
            if os.path.isdir(name[0]):
                recurse = True

        project = ericApp().getObject("Project")
        names = [project.getRelativePath(nam) for nam in name]
        if names[0]:
            dia = DeleteFilesConfirmationDialog(
                self.parent(),
                self.tr("Revert changes"),
                self.tr(
                    "Do you really want to revert all changes to these files"
                    " or directories?"
                ),
                name,
            )
            yes = dia.exec() == QDialog.DialogCode.Accepted
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
            client = self.getClient()
            dlg = SvnDialog(
                self.tr("Reverting changes"),
                "revert {0} {1}".format(
                    (not recurse) and " --non-recursive" or "", " ".join(name)
                ),
                client,
                parent=self.__ui,
            )
            QApplication.processEvents()
            try:
                with EricMutexLocker(self.vcsExecutionMutex):
                    client.revert(name, recurse)
            except pysvn.ClientError as e:
                dlg.showError(e.args[0])
            dlg.finish()
            dlg.exec()
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
        @return flag indicating, that the switch contained an add or delete
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

        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Switching to {0}").format(tn),
            "switch {0} {1}".format(url, name),
            client,
            parent=self.__ui,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                rev = client.switch(name, url)
            dlg.showMessage(self.tr("Revision {0}.\n").format(rev.number))
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()
        res = dlg.hasAddOrDelete()
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

        opts = self.options["global"]
        dlg = SvnMergeDialog(
            self.mergeList[0],
            self.mergeList[1],
            self.mergeList[2],
            "--force" in opts,
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

        rx_rev = re.compile("\\d+|HEAD|head")

        cwd = os.getcwd()
        os.chdir(dname)
        recurse = "--non-recursive" not in opts
        if bool(rx_rev.fullmatch(urlrev1)):
            if urlrev1 in ["HEAD", "head"]:
                revision1 = pysvn.Revision(pysvn.opt_revision_kind.head)
                rev1 = "HEAD"
            else:
                revision1 = pysvn.Revision(pysvn.opt_revision_kind.number, int(urlrev1))
                rev1 = urlrev1
            if urlrev2 in ["HEAD", "head"]:
                revision2 = pysvn.Revision(pysvn.opt_revision_kind.head)
                rev2 = "HEAD"
            else:
                revision2 = pysvn.Revision(pysvn.opt_revision_kind.number, int(urlrev2))
                rev2 = urlrev2
            if not target:
                url1 = name
                url2 = name
            else:
                url1 = target
                url2 = target

            # remember target
            if target in self.mergeList[2]:
                self.mergeList[2].remove(target)
            self.mergeList[2].insert(0, target)
        else:
            if "@" in urlrev1:
                url1, rev = urlrev1.split("@")
                if rev in ["HEAD", "head"]:
                    revision1 = pysvn.Revision(pysvn.opt_revision_kind.head)
                    rev1 = "HEAD"
                else:
                    revision1 = pysvn.Revision(pysvn.opt_revision_kind.number, int(rev))
                    rev1 = rev
            else:
                url1 = urlrev1
                revision1 = pysvn.Revision(pysvn.opt_revision_kind.unspecified)
                rev1 = ""
            if "@" in urlrev2:
                url2, rev = urlrev2.split("@")
                if rev in ["HEAD", "head"]:
                    revision2 = pysvn.Revision(pysvn.opt_revision_kind.head)
                    rev2 = "HEAD"
                else:
                    revision2 = pysvn.Revision(pysvn.opt_revision_kind.number, int(rev))
                    rev2 = rev
            else:
                url2 = urlrev2
                revision2 = pysvn.Revision(pysvn.opt_revision_kind.unspecified)
                rev2 = ""
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Merging {0}").format(name),
            "merge{0}{1} {2} {3} {4}".format(
                (not recurse) and " --non-recursive" or "",
                force and " --force" or "",
                "{0}{1}".format(url1, rev1 and ("@" + rev1) or ""),
                "{0}{1}".format(url2, rev2 and ("@" + rev2) or ""),
                fname,
            ),
            client,
            parent=self.__ui,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.merge(
                    url1,
                    revision1,
                    url2,
                    revision2,
                    fname,
                    recurse=recurse,
                    force=force,
                )
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()
        os.chdir(cwd)

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
        Private method used to get the registered state of a file in the vcs.

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
        in the vcs.

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
        if self.__wcng:
            return self.__vcsAllRegisteredStates_wcng(names, dname, shortcut)
        else:
            return self.__vcsAllRegisteredStates_wc(names, dname, shortcut)

    def __vcsAllRegisteredStates_wcng(self, names, dname, shortcut=True):  # noqa: U100
        """
        Private method used to get the registered states of a number of files
        in the vcs.

        This is the variant for subversion installations using the new working
        copy meta-data format.

        <b>Note:</b> If a shortcut is to be taken, the code will only check,
        if the named directory has been scanned already. If so, it is assumed,
        that the states for all files has been populated by the previous run.

        @param names dictionary with all filenames to be checked as keys
        @type dict
        @param dname directory to check in
        @type str
        @param shortcut flag indicating a shortcut should be taken (unused)
        @type bool
        @return the received dictionary completed with the VCS state or None in
            order to signal an error
        @rtype dict
        """
        from .SvnDialogMixin import SvnDialogMixin

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

            mixin = SvnDialogMixin()
            client = self.getClient()
            client.callback_get_login = mixin._clientLoginCallback
            client.callback_ssl_server_trust_prompt = (
                mixin._clientSslServerTrustPromptCallback
            )

            with contextlib.suppress(pysvn.ClientError):
                with EricMutexLocker(self.vcsExecutionMutex):
                    allFiles = client.status(
                        dname, recurse=True, get_all=True, ignore=True, update=False
                    )
                dirs = [x for x in names if os.path.isdir(x)]
                for file in allFiles:
                    name = os.path.normcase(file.path)
                    if self.__isVersioned(file):
                        if name in names:
                            names[name] = VersionControlState.Controlled
                            dn = name
                            while os.path.splitdrive(dn)[1] != os.sep and dn != repodir:
                                dn = os.path.dirname(dn)
                                if (
                                    dn in self.statusCache
                                    and self.statusCache[dn]
                                    == VersionControlState.Controlled
                                ):
                                    break
                                self.statusCache[dn] = VersionControlState.Controlled
                        self.statusCache[name] = VersionControlState.Controlled
                        if dirs:
                            for d in dirs[:]:
                                if name.startswith(d):
                                    names[d] = VersionControlState.Controlled
                                    self.statusCache[d] = VersionControlState.Controlled
                                    dirs.remove(d)
                                    break
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
        from .SvnDialogMixin import SvnDialogMixin

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
            mixin = SvnDialogMixin()
            client = self.getClient()
            client.callback_get_login = mixin._clientLoginCallback
            client.callback_ssl_server_trust_prompt = (
                mixin._clientSslServerTrustPromptCallback
            )

            with contextlib.suppress(pysvn.ClientError):
                with EricMutexLocker(self.vcsExecutionMutex):
                    allFiles = client.status(
                        dname, recurse=True, get_all=True, ignore=True, update=False
                    )
                for file in allFiles:
                    name = os.path.normcase(file.path)
                    if self.__isVersioned(file):
                        if name in names:
                            names[name] = VersionControlState.Controlled
                        self.statusCache[name] = VersionControlState.Controlled
                    else:
                        self.statusCache[name] = VersionControlState.Uncontrolled

        return names

    def __isVersioned(self, status):
        """
        Private method to check, if the given status indicates a
        versioned state.

        @param status status object to check
        @type pysvn.PysvnStatus
        @return flag indicating a versioned state
        @rtype bool
        """
        return status["text_status"] in [
            pysvn.wc_status_kind.normal,
            pysvn.wc_status_kind.added,
            pysvn.wc_status_kind.missing,
            pysvn.wc_status_kind.deleted,
            pysvn.wc_status_kind.replaced,
            pysvn.wc_status_kind.modified,
            pysvn.wc_status_kind.merged,
            pysvn.wc_status_kind.conflicted,
        ]

    def clearStatusCache(self):
        """
        Public method to clear the status cache.
        """
        self.statusCache = {}

    def vcsInitConfig(self, _project):
        """
        Public method to initialize the VCS configuration.

        This method ensures, that eric specific files and directories are
        ignored.

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
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Cleaning up {0}").format(name),
            "cleanup {0}".format(name),
            client,
            parent=self.__ui,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.cleanup(name)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()

    def vcsCommandLine(self, name):
        """
        Public method used to execute arbitrary subversion commands.

        @param name directory name of the working directory
        @type str
        """
        from eric7.Plugins.VcsPlugins.vcsSubversion.SvnDialog import (
            SvnDialog as SvnProcessDialog,
        )

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

            dia = SvnProcessDialog(self.tr("Subversion command"), parent=self.__ui)
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
        Public method to get a dialog to enter repository info for getting a
        new project.

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
        try:
            entry = self.getClient().info(ppath)
        except pysvn.ClientError as e:
            return e.args[0]

        apiVersion = (
            "{0} {1}".format(
                ".".join([str(v) for v in pysvn.svn_api_version[:3]]),
                pysvn.svn_api_version[3],
            )
            if hasattr(pysvn, "svn_api_version")
            else QCoreApplication.translate("subversion", "unknown")
        )

        hmsz = time.strftime("%H:%M:%S %Z", time.localtime(entry.commit_time))
        return QCoreApplication.translate(
            "subversion",
            """<h3>Repository information</h3>"""
            """<table>"""
            """<tr><td><b>PySvn V.</b></td><td>{0}</td></tr>"""
            """<tr><td><b>Subversion V.</b></td><td>{1}</td></tr>"""
            """<tr><td><b>Subversion API V.</b></td><td>{2}</td></tr>"""
            """<tr><td><b>URL</b></td><td>{3}</td></tr>"""
            """<tr><td><b>Current revision</b></td><td>{4}</td></tr>"""
            """<tr><td><b>Committed revision</b></td><td>{5}</td></tr>"""
            """<tr><td><b>Committed date</b></td><td>{6}</td></tr>"""
            """<tr><td><b>Comitted time</b></td><td>{7}</td></tr>"""
            """<tr><td><b>Last author</b></td><td>{8}</td></tr>"""
            """</table>""",
        ).format(
            ".".join([str(v) for v in pysvn.version]),
            ".".join([str(v) for v in pysvn.svn_version[:3]]),
            apiVersion,
            entry.url,
            entry.revision.number,
            entry.commit_revision.number,
            time.strftime("%Y-%m-%d", time.localtime(entry.commit_time)),
            hmsz,
            entry.commit_author,
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
        client = pysvn.Client()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                entry = client.info(path)
            url = entry.url
        except pysvn.ClientError:
            url = ""
        return url

    def vcsResolved(self, name):
        """
        Public method used to resolve conflicts of a file/directory.

        @param name file/directory name to be resolved
        @type str
        """
        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
        else:
            dname, fname = self.splitPath(name)
            fnames = [fname]

        cwd = os.getcwd()
        os.chdir(dname)
        opts = self.options["global"]
        recurse = "--non-recursive" not in opts
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Resolving conficts"),
            "resolved{0} {1}".format(
                (not recurse) and " --non-recursive" or "", " ".join(fnames)
            ),
            client,
            parent=self.__ui,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                for name in fnames:
                    client.resolved(name, recurse=recurse)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()
        os.chdir(cwd)
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

            client = self.getClient()
            if bool(rx_prot.fullmatch(target)):
                target = self.__svnURL(target)
                log = "Copying {0} to {1}".format(name, target)
            else:
                log = ""
            dlg = SvnDialog(
                self.tr("Copying {0}").format(name),
                "copy{0} {1} {2}".format(
                    log and (" --message {0}".format(log)) or "", name, target
                ),
                client,
                parent=self.__ui,
                log=log,
            )
            QApplication.processEvents()
            try:
                with EricMutexLocker(self.vcsExecutionMutex):
                    client.copy(name, target)
                res = True
            except pysvn.ClientError as e:
                res = False
                dlg.showError(e.args[0])
            dlg.finish()
            dlg.exec()
            if (
                res
                and not bool(rx_prot.fullmatch(target))
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
        QApplication.processEvents()
        self.propList.start(name, recursive)

    def svnSetProp(self, name, recursive=False):
        """
        Public method used to add a property to a file/directory.

        @param name file/directory name
        @type str or list of str
        @param recursive flag indicating a recursive set is requested
        @type bool
        """
        from .SvnPropSetDialog import SvnPropSetDialog

        dlg = SvnPropSetDialog(recursive, parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            propName, propValue, recurse = dlg.getData()
            if not propName:
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("Subversion Set Property"),
                    self.tr("""You have to supply a property name. Aborting."""),
                )
                return

            if isinstance(name, list):
                dname, fnames = self.splitPathList(name)
            else:
                dname, fname = self.splitPath(name)
                fnames = [fname]

            cwd = os.getcwd()
            os.chdir(dname)
            opts = self.options["global"]
            skipchecks = "--skip-checks" in opts
            client = self.getClient()
            dlg = SvnDialog(
                self.tr("Subversion Set Property"),
                "propset{0}{1} {2} {3} {4}".format(
                    recurse and " --recurse" or "",
                    skipchecks and " --skip-checks" or "",
                    propName,
                    propValue,
                    " ".join(fnames),
                ),
                client,
                parent=self.__ui,
            )
            QApplication.processEvents()
            try:
                with EricMutexLocker(self.vcsExecutionMutex):
                    for name in fnames:
                        client.propset(
                            propName,
                            propValue,
                            name,
                            recurse=recurse,
                            skip_checks=skipchecks,
                        )
            except pysvn.ClientError as e:
                dlg.showError(e.args[0])
            dlg.showMessage(self.tr("Property set."))
            dlg.finish()
            dlg.exec()
            os.chdir(cwd)

    def svnDelProp(self, name, recursive=False):
        """
        Public method used to delete a property of a file/directory.

        @param name file/directory name
        @type str or list of str
        @param recursive flag indicating a recursive list is requested
        @type bool
        """
        from .SvnPropDelDialog import SvnPropDelDialog

        dlg = SvnPropDelDialog(recursive, parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            propName, recurse = dlg.getData()

            if not propName:
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("Subversion Delete Property"),
                    self.tr("""You have to supply a property name. Aborting."""),
                )
                return

            if isinstance(name, list):
                dname, fnames = self.splitPathList(name)
            else:
                dname, fname = self.splitPath(name)
                fnames = [fname]

            cwd = os.getcwd()
            os.chdir(dname)
            opts = self.options["global"]
            skipchecks = "--skip-checks" in opts
            client = self.getClient()
            dlg = SvnDialog(
                self.tr("Subversion Delete Property"),
                "propdel{0}{1} {2} {3}".format(
                    recurse and " --recurse" or "",
                    skipchecks and " --skip-checks" or "",
                    propName,
                    " ".join(fnames),
                ),
                client,
                parent=self.__ui,
            )
            QApplication.processEvents()
            try:
                with EricMutexLocker(self.vcsExecutionMutex):
                    for name in fnames:
                        client.propdel(
                            propName, name, recurse=recurse, skip_checks=skipchecks
                        )
            except pysvn.ClientError as e:
                dlg.showError(e.args[0])
            dlg.showMessage(self.tr("Property deleted."))
            dlg.finish()
            dlg.exec()
            os.chdir(cwd)

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
        QApplication.processEvents()
        res = self.tagbranchList.start(path, tags)
        if res:
            if tags:
                self.tagsList = self.tagbranchList.getTagList()
                if not self.showedTags:
                    self.allTagsBranchesList = self.allTagsBranchesList + self.tagsList
                    self.showedTags = True
            elif not tags:
                self.branchesList = self.tagbranchList.getTagList()
                if not self.showedBranches:
                    self.allTagsBranchesList = (
                        self.allTagsBranchesList + self.branchesList
                    )
                    self.showedBranches = True

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
        QApplication.processEvents()
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
            if self.diff is None:
                self.diff = SvnDiffDialog(self)
            self.diff.show()
            self.diff.raise_()
            QApplication.processEvents()
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
            if self.diff is None:
                self.diff = SvnDiffDialog(self)
            self.diff.show()
            self.diff.raise_()
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
        output = ""
        error = ""

        client = self.getClient()
        try:
            if rev:
                if isinstance(rev, int) or rev.isdecimal():
                    rev = pysvn.Revision(pysvn.opt_revision_kind.number, int(rev))
                elif rev.startswith("{"):
                    dateStr = rev[1:-1]
                    secs = QDateTime.fromString(
                        dateStr, Qt.DateFormat.ISODate
                    ).toTime_t()
                    rev = pysvn.Revision(pysvn.opt_revision_kind.date, secs)
                elif rev == "HEAD":
                    rev = pysvn.Revision(pysvn.opt_revision_kind.head)
                elif rev == "COMMITTED":
                    rev = pysvn.Revision(pysvn.opt_revision_kind.committed)
                elif rev == "BASE":
                    rev = pysvn.Revision(pysvn.opt_revision_kind.base)
                elif rev == "WORKING":
                    rev = pysvn.Revision(pysvn.opt_revision_kind.working)
                elif rev == "PREV":
                    rev = pysvn.Revision(pysvn.opt_revision_kind.previous)
                else:
                    rev = pysvn.Revision(pysvn.opt_revision_kind.unspecified)
                output = client.cat(name, revision=rev)
            else:
                output = client.cat(name)
            output = output.decode("utf-8")
        except pysvn.ClientError as e:
            error = str(e)

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
        @exception ValueError raised to indicate an invalid name parameter type
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
        QApplication.processEvents()
        self.logBrowser.start(name, isFile=isFile)

    def svnLock(self, name, stealIt=False, parent=None):
        """
        Public method used to lock a file in the Subversion repository.

        @param name file/directory name to be locked
        @type str or list of str
        @param stealIt flag indicating a forced operation
        @type bool
        @param parent reference to the parent widget of the subversion dialog
        @type QWidget
        """
        comment, ok = QInputDialog.getText(
            None,
            self.tr("Subversion Lock"),
            self.tr("Enter lock comment"),
            QLineEdit.EchoMode.Normal,
        )

        if not ok:
            return

        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
        else:
            dname, fname = self.splitPath(name)
            fnames = [fname]

        cwd = os.getcwd()
        os.chdir(dname)
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Locking in the Subversion repository"),
            "lock{0}{1} {2}".format(
                stealIt and " --force" or "",
                comment and (" --message {0}".format(comment)) or "",
                " ".join(fnames),
            ),
            client,
            parent=parent,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.lock(fnames, comment, force=stealIt)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        except AttributeError as e:
            dlg.showError(str(e))
        dlg.finish()
        dlg.exec()
        os.chdir(cwd)

    def svnUnlock(self, name, breakIt=False, parent=None):
        """
        Public method used to unlock a file in the Subversion repository.

        @param name file/directory name to be unlocked
        @type str or list of str
        @param breakIt flag indicating a forced operation
        @type bool
        @param parent reference to the parent widget of the subversion dialog
        @type QWidget
        """
        if isinstance(name, list):
            dname, fnames = self.splitPathList(name)
        else:
            dname, fname = self.splitPath(name)
            fnames = [fname]

        cwd = os.getcwd()
        os.chdir(dname)
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Unlocking in the Subversion repository"),
            "unlock{0} {1}".format(breakIt and " --force" or "", " ".join(fnames)),
            client,
            parent=parent,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.unlock(fnames, force=breakIt)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        except AttributeError as e:
            dlg.showError(str(e))
        dlg.finish()
        dlg.exec()
        os.chdir(cwd)

    def svnInfo(self, projectPath, name):
        """
        Public method to show repository information about a file or directory.

        @param projectPath path name of the project
        @type str
        @param name file/directory name relative to the project
        @type str
        """
        from .SvnInfoDialog import SvnInfoDialog

        dlg = SvnInfoDialog(self, parent=self.__ui)
        dlg.start(projectPath, name)
        dlg.exec()

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
            if inside:
                msg = "switch {0} {1}".format(newUrl, projectPath)
            else:
                msg = "relocate {0} {1} {2}".format(currUrl, newUrl, projectPath)
            client = self.getClient()
            dlg = SvnDialog(self.tr("Relocating"), msg, client, parent=self.__ui)
            QApplication.processEvents()
            try:
                with EricMutexLocker(self.vcsExecutionMutex):
                    if inside:
                        client.switch(projectPath, newUrl)
                    else:
                        client.relocate(currUrl, newUrl, projectPath, recurse=True)
            except pysvn.ClientError as e:
                dlg.showError(e.args[0])
            dlg.finish()
            dlg.exec()

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
        self.repoBrowser.start(url)
        self.repoBrowser.show()
        self.repoBrowser.raise_()

    def svnRemoveFromChangelist(self, names):
        """
        Public method to remove a file or directory from its changelist.

        Note: Directories will be removed recursively.

        @param names name or list of names of file or directory to remove
        @type str or list of str
        """
        if not isinstance(names, list):
            names = [names]
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Remove from changelist"),
            "changelist --remove {0}".format(" ".join(names)),
            client,
            parent=self.__ui,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                for name in names:
                    client.remove_from_changelists(name)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()

    def svnAddToChangelist(self, names):
        """
        Public method to add a file or directory to a changelist.

        Note: Directories will be added recursively.

        @param names name or list of names of file or directory to add
        @type str or list of str
        """
        if not isinstance(names, list):
            names = [names]

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

        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Add to changelist"),
            "changelist {0}".format(" ".join(names)),
            client,
            parent=self.__ui,
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                for name in names:
                    client.add_to_changelist(name, clname, depth=pysvn.depth.infinity)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()

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
        client = self.getClient()
        if hasattr(client, "get_changelist"):
            ppath = ericApp().getObject("Project").getProjectPath()
            with contextlib.suppress(pysvn.ClientError):
                with EricMutexLocker(self.vcsExecutionMutex):
                    entries = client.get_changelist(ppath, depth=pysvn.depth.infinity)
                for entry in entries:
                    changelist = entry[1]
                    if changelist not in changelists:
                        changelists.append(changelist)

        return changelists

    def svnUpgrade(self, path):
        """
        Public method to upgrade the working copy format.

        @param path directory name to show change lists for
        @type str
        """
        client = self.getClient()
        dlg = SvnDialog(
            self.tr("Upgrade"), "upgrade {0}".format(path), client, parent=self.__ui
        )
        QApplication.processEvents()
        try:
            with EricMutexLocker(self.vcsExecutionMutex):
                client.upgrade(path)
        except pysvn.ClientError as e:
            dlg.showError(e.args[0])
        dlg.finish()
        dlg.exec()

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
            if url[1] == ":":
                url = url.replace(":", "|", 1)
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
        @rtype PySvnProjectHelper
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
