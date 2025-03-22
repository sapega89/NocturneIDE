# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Git Options Dialog for a new project from the
repository.
"""

from PyQt6.QtCore import Qt, QUrl, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog
from eric7.EricWidgets.EricCompleters import EricDirCompleter
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from .Config import ConfigGitSchemes
from .Ui_GitNewProjectOptionsDialog import Ui_GitNewProjectOptionsDialog


class GitNewProjectOptionsDialog(QDialog, Ui_GitNewProjectOptionsDialog):
    """
    Class implementing the Options Dialog for a new project from the
    repository.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the version control object
        @type Git
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__vcs = vcs

        self.projectDirButton.setIcon(EricPixmapCache.getIcon("open"))
        self.vcsUrlButton.setIcon(EricPixmapCache.getIcon("open"))
        self.vcsUrlClearHistoryButton.setIcon(EricPixmapCache.getIcon("editDelete"))

        vcsUrlHistory = self.__vcs.getPlugin().getPreferences("RepositoryUrlHistory")
        self.vcsUrlCombo.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive
        )
        self.vcsUrlCombo.addItems(vcsUrlHistory)
        self.vcsUrlCombo.setEditText("")

        self.vcsDirectoryCompleter = EricDirCompleter(self.vcsUrlCombo)
        self.vcsProjectDirCompleter = EricDirCompleter(self.vcsProjectDirEdit)

        ipath = Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir()
        self.__initPaths = [
            FileSystemUtilities.fromNativeSeparators(ipath),
            FileSystemUtilities.fromNativeSeparators(ipath) + "/",
        ]
        self.vcsProjectDirEdit.setText(
            FileSystemUtilities.toNativeSeparators(self.__initPaths[0])
        )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_vcsProjectDirEdit_textChanged(self, txt):
        """
        Private slot to handle a change of the project directory.

        @param txt name of the project directory
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(txt)
            and FileSystemUtilities.fromNativeSeparators(txt) not in self.__initPaths
        )

    @pyqtSlot()
    def on_vcsUrlButton_clicked(self):
        """
        Private slot to display a selection dialog.
        """
        directory = EricFileDialog.getExistingDirectory(
            self,
            self.tr("Select Repository-Directory"),
            self.vcsUrlCombo.currentText(),
            EricFileDialog.ShowDirsOnly,
        )

        if directory:
            self.vcsUrlCombo.setEditText(
                FileSystemUtilities.toNativeSeparators(directory)
            )

    @pyqtSlot()
    def on_projectDirButton_clicked(self):
        """
        Private slot to display a directory selection dialog.
        """
        directory = EricFileDialog.getExistingDirectory(
            self,
            self.tr("Select Project Directory"),
            self.vcsProjectDirEdit.text(),
            EricFileDialog.ShowDirsOnly,
        )

        if directory:
            self.vcsProjectDirEdit.setText(
                FileSystemUtilities.toNativeSeparators(directory)
            )

    @pyqtSlot(str)
    def on_vcsUrlCombo_editTextChanged(self, txt):
        """
        Private slot to handle changes of the URL.

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
        self.vcsUrlButton.setEnabled(vcsUrlEnable)

    @pyqtSlot()
    def on_vcsUrlClearHistoryButton_clicked(self):
        """
        Private slot to clear the history of entered repository URLs.
        """
        currentVcsUrl = self.vcsUrlCombo.currentText()
        self.vcsUrlCombo.clear()
        self.vcsUrlCombo.setEditText(currentVcsUrl)

        self.__saveHistory()

    def getData(self):
        """
        Public slot to retrieve the data entered into the dialog.

        @return a tuple of a string (project directory) and a dictionary
            containing the data entered
        @rtype tuple of (str, Any)
        """
        self.__saveHistory()

        vcsdatadict = {
            "url": self.vcsUrlCombo.currentText().replace("\\", "/"),
        }
        return (self.vcsProjectDirEdit.text(), vcsdatadict)

    def __saveHistory(self):
        """
        Private method to save the repository URL history.
        """
        url = self.vcsUrlCombo.currentText()
        vcsUrlHistory = []
        for index in range(self.vcsUrlCombo.count()):
            vcsUrlHistory.append(self.vcsUrlCombo.itemText(index))
        if url not in vcsUrlHistory:
            vcsUrlHistory.insert(0, url)

        # max. list sizes is hard coded to 20 entries
        newVcsUrlHistory = [url for url in vcsUrlHistory if url]
        if len(newVcsUrlHistory) > 20:
            newVcsUrlHistory = newVcsUrlHistory[:20]

        self.__vcs.getPlugin().setPreferences("RepositoryUrlHistory", newVcsUrlHistory)
