# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Mercurial Options Dialog for a new project from the
repository.
"""

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from .Config import ConfigHgSchemes
from .Ui_HgNewProjectOptionsDialog import Ui_HgNewProjectOptionsDialog


class HgNewProjectOptionsDialog(QDialog, Ui_HgNewProjectOptionsDialog):
    """
    Class implementing the Options Dialog for a new project from the
    repository.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the version control object
        @type Hg
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.vcsProjectDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        self.__vcs = vcs

        vcsUrlHistory = self.__vcs.getPlugin().getPreferences("RepositoryUrlHistory")
        self.vcsUrlPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.vcsUrlPicker.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.vcsUrlPicker.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.vcsUrlPicker.setPathsList(vcsUrlHistory)
        self.vcsUrlClearHistoryButton.setIcon(EricPixmapCache.getIcon("editDelete"))
        self.vcsUrlPicker.setText("")

        ipath = Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir()
        self.__initPaths = [
            FileSystemUtilities.fromNativeSeparators(ipath),
            FileSystemUtilities.fromNativeSeparators(ipath) + "/",
        ]
        self.vcsProjectDirPicker.setText(self.__initPaths[0])

        self.lfNoteLabel.setVisible(self.__vcs.isExtensionActive("largefiles"))
        self.largeCheckBox.setVisible(self.__vcs.isExtensionActive("largefiles"))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_vcsProjectDirPicker_textChanged(self, txt):
        """
        Private slot to handle a change of the project directory.

        @param txt name of the project directory
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(txt)
            and FileSystemUtilities.fromNativeSeparators(txt) not in self.__initPaths
        )

    @pyqtSlot(str)
    def on_vcsUrlPicker_textChanged(self, txt):
        """
        Private slot to handle changes of the URL.

        @param txt current text of the line edit
        @type str
        """
        url = QUrl.fromUserInput(txt)
        enable = url.isValid() and url.scheme() in ConfigHgSchemes
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

        self.vcsUrlPicker.setPickerEnabled(url.scheme() == "file" or len(txt) == 0)

    @pyqtSlot()
    def on_vcsUrlClearHistoryButton_clicked(self):
        """
        Private slot to clear the history of entered repository URLs.
        """
        currentVcsUrl = self.vcsUrlPicker.text()
        self.vcsUrlPicker.clear()
        self.vcsUrlPicker.setText(currentVcsUrl)

        self.__saveHistory()

    def getData(self):
        """
        Public slot to retrieve the data entered into the dialog and to
        save the history of entered repository URLs.

        @return tuple containing the project directory and a dictionary
            containing the data entered
        @rtype tuple of (str, dict)
        """
        self.__saveHistory()

        url = QUrl.fromUserInput(self.vcsUrlPicker.text().replace("\\", "/"))
        vcsdatadict = {
            "url": url.toString(QUrl.UrlFormattingOption.None_),
            "revision": self.vcsRevisionEdit.text(),
            "largefiles": self.largeCheckBox.isChecked(),
        }
        return (self.vcsProjectDirPicker.text(), vcsdatadict)

    def __saveHistory(self):
        """
        Private method to save the repository URL history.
        """
        url = self.vcsUrlPicker.text()
        vcsUrlHistory = self.vcsUrlPicker.getPathItems()
        if url not in vcsUrlHistory:
            vcsUrlHistory.insert(0, url)

        # max. list sizes is hard coded to 20 entries
        newVcsUrlHistory = [url for url in vcsUrlHistory if url]
        if len(newVcsUrlHistory) > 20:
            newVcsUrlHistory = newVcsUrlHistory[:20]

        self.__vcs.getPlugin().setPreferences("RepositoryUrlHistory", newVcsUrlHistory)
