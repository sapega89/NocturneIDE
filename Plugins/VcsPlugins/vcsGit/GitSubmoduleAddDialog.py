# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data to add a submodule.
"""

from PyQt6.QtCore import Qt, QUrl, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog
from eric7.EricWidgets.EricCompleters import EricDirCompleter
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from .Config import ConfigGitSchemes
from .Ui_GitSubmoduleAddDialog import Ui_GitSubmoduleAddDialog


class GitSubmoduleAddDialog(QDialog, Ui_GitSubmoduleAddDialog):
    """
    Class implementing a dialog to enter the data to add a submodule.
    """

    def __init__(self, vcs, repodir, parent=None):
        """
        Constructor

        @param vcs reference to the version control object
        @type Git
        @param repodir directory containing the superproject
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__vcs = vcs
        self.__repodir = repodir

        self.submoduleDirButton.setIcon(EricPixmapCache.getIcon("open"))
        self.submoduleUrlButton.setIcon(EricPixmapCache.getIcon("open"))
        self.submoduleUrlClearHistoryButton.setIcon(
            EricPixmapCache.getIcon("editDelete")
        )

        submoduleUrlHistory = self.__vcs.getPlugin().getPreferences(
            "RepositoryUrlHistory"
        )
        self.submoduleUrlCombo.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive
        )
        self.submoduleUrlCombo.addItems(submoduleUrlHistory)
        self.submoduleUrlCombo.setEditText("")

        self.submoduleUrlDirCompleter = EricDirCompleter(self.submoduleUrlCombo)
        self.submoduleDirCompleter = EricDirCompleter(self.submoduleDirEdit)

        ipath = Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir()
        self.__initPaths = [
            FileSystemUtilities.fromNativeSeparators(ipath),
            FileSystemUtilities.fromNativeSeparators(ipath) + "/",
        ]

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_submoduleUrlCombo_editTextChanged(self, txt):
        """
        Private slot to handle changes of the submodule repository URL.

        @param txt current text of the combo box
        @type str
        """
        enable = False
        vcsUrlEnable = False

        if txt:
            url = QUrl.fromUserInput(txt)
            if url.isValid():
                if url.scheme() in ConfigGitSchemes:
                    enable = True
                    vcsUrlEnable = url.scheme() == "file"
            elif ":" in txt:
                # assume scp like repository URL
                enable = True
        else:
            vcsUrlEnable = True

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)
        self.submoduleUrlButton.setEnabled(vcsUrlEnable)

    @pyqtSlot()
    def on_submoduleUrlButton_clicked(self):
        """
        Private slot to display a directory selection dialog.
        """
        directory = EricFileDialog.getExistingDirectory(
            self,
            self.tr("Select Submodule Repository Directory"),
            self.submoduleUrlCombo.currentText(),
            EricFileDialog.ShowDirsOnly,
        )

        if directory:
            self.submoduleUrlCombo.setEditText(
                FileSystemUtilities.toNativeSeparators(directory)
            )

    @pyqtSlot()
    def on_submoduleUrlClearHistoryButton_clicked(self):
        """
        Private slot to clear the history of entered repository URLs.
        """
        currentUrl = self.submoduleUrlCombo.currentText()
        self.submoduleUrlCombo.clear()
        self.submoduleUrlCombo.setEditText(currentUrl)

        self.__saveHistory()

    @pyqtSlot()
    def on_submoduleDirButton_clicked(self):
        """
        Private slot to display a directory selection dialog.
        """
        directory = EricFileDialog.getExistingDirectory(
            self,
            self.tr("Select Submodule Directory"),
            self.submoduleDirEdit.text(),
            EricFileDialog.ShowDirsOnly,
        )

        if directory:
            self.submoduleDirEdit.setText(
                FileSystemUtilities.toNativeSeparators(directory)
            )

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the repository URL, optional branch name,
            optional logical name, optional submodule path and a flag
            indicating to enforce the operation
        @rtype tuple of (str, str, str, str, bool)
        """
        self.__saveHistory()

        path = self.submoduleDirEdit.text()
        if path:
            path = self.__getRelativePath(path)

        return (
            self.submoduleUrlCombo.currentText().replace("\\", "/"),
            self.branchEdit.text(),
            self.nameEdit.text(),
            path,
            self.forceCheckBox.isChecked(),
        )

    def __saveHistory(self):
        """
        Private method to save the repository URL history.
        """
        url = self.submoduleUrlCombo.currentText()
        submoduleUrlHistory = []
        for index in range(self.submoduleUrlCombo.count()):
            submoduleUrlHistory.append(self.submoduleUrlCombo.itemText(index))
        if url not in submoduleUrlHistory:
            submoduleUrlHistory.insert(0, url)

        # max. list sizes is hard coded to 20 entries
        newSubmoduleUrlHistory = [url for url in submoduleUrlHistory if url]
        if len(newSubmoduleUrlHistory) > 20:
            newSubmoduleUrlHistory = newSubmoduleUrlHistory[:20]

        self.__vcs.getPlugin().setPreferences(
            "RepositoryUrlHistory", newSubmoduleUrlHistory
        )

    def __getRelativePath(self, path):
        """
        Private method to convert a file path to a relative path.

        @param path file or directory name to convert
        @type str
        @return relative path or unchanged path, if path doesn't
            belong to the project
        @rtype str
        """
        if path == self.__repodir:
            return ""
        elif FileSystemUtilities.normcasepath(
            FileSystemUtilities.toNativeSeparators(path)
        ).startswith(
            FileSystemUtilities.normcasepath(
                FileSystemUtilities.toNativeSeparators(self.__repodir + "/")
            )
        ):
            relpath = path[len(self.__repodir) :]
            if relpath.startswith(("/", "\\")):
                relpath = relpath[1:]
            return relpath
        else:
            return path
