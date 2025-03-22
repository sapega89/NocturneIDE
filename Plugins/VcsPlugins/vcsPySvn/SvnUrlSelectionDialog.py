# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the URLs for the svn diff command.
"""

import re

import pysvn

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_SvnUrlSelectionDialog import Ui_SvnUrlSelectionDialog


class SvnUrlSelectionDialog(QDialog, Ui_SvnUrlSelectionDialog):
    """
    Class implementing a dialog to enter the URLs for the svn diff command.
    """

    def __init__(self, vcs, tagsList, branchesList, path, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Subversion
        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param path pathname to determine the repository URL from
        @type str
        @param parent parent widget of the dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if not hasattr(pysvn.Client(), "diff_summarize"):
            self.summaryCheckBox.setEnabled(False)
            self.summaryCheckBox.setChecked(False)

        self.vcs = vcs
        self.tagsList = tagsList
        self.branchesList = branchesList

        self.typeCombo1.addItems(["trunk/", "tags/", "branches/"])
        self.typeCombo2.addItems(["trunk/", "tags/", "branches/"])

        reposURL = self.vcs.svnGetReposName(path)
        if reposURL is None:
            EricMessageBox.critical(
                self,
                self.tr("Subversion Error"),
                self.tr(
                    """The URL of the project repository could not be"""
                    """ retrieved from the working copy. The operation will"""
                    """ be aborted"""
                ),
            )
            self.reject()
            return

        if self.vcs.otherData["standardLayout"]:
            # determine the base path of the project in the repository
            rx_base = re.compile("(.+/)(trunk|tags|branches).*")
            match = rx_base.fullmatch(reposURL)
            if match is None:
                EricMessageBox.critical(
                    self,
                    self.tr("Subversion Error"),
                    self.tr(
                        """The URL of the project repository has an"""
                        """ invalid format. The operation will"""
                        """ be aborted"""
                    ),
                )
                self.reject()
                return

            reposRoot = match.group(1)
            self.repoRootLabel1.setText(reposRoot)
            self.repoRootLabel2.setText(reposRoot)
        else:
            project = ericApp().getObject("Project")
            if FileSystemUtilities.normcasepath(
                path
            ) != FileSystemUtilities.normcasepath(project.getProjectPath()):
                path = project.getRelativePath(path)
                reposURL = reposURL.replace(path, "")
            self.repoRootLabel1.hide()
            self.typeCombo1.hide()
            self.labelCombo1.addItems([reposURL] + sorted(self.vcs.tagsList))
            self.labelCombo1.setEnabled(True)
            self.repoRootLabel2.hide()
            self.typeCombo2.hide()
            self.labelCombo2.addItems([reposURL] + sorted(self.vcs.tagsList))
            self.labelCombo2.setEnabled(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __changeLabelCombo(self, labelCombo, type_):
        """
        Private method used to change the label combo depending on the
        selected type.

        @param labelCombo reference to the labelCombo object
        @type QComboBox
        @param type_ type string
        @type str
        """
        if type_ == "trunk/":
            labelCombo.clear()
            labelCombo.setEditText("")
            labelCombo.setEnabled(False)
        elif type_ == "tags/":
            labelCombo.clear()
            labelCombo.clearEditText()
            labelCombo.addItems(sorted(self.tagsList))
            labelCombo.setEnabled(True)
        elif type_ == "branches/":
            labelCombo.clear()
            labelCombo.clearEditText()
            labelCombo.addItems(sorted(self.branchesList))
            labelCombo.setEnabled(True)

    @pyqtSlot(int)
    def on_typeCombo1_currentIndexChanged(self, index):
        """
        Private slot called when the selected type was changed.

        @param index index of the current item
        @type int
        """
        type_ = self.typeCombo1.itemText(index)
        self.__changeLabelCombo(self.labelCombo1, type_)

    @pyqtSlot(int)
    def on_typeCombo2_currentIndexChanged(self, index):
        """
        Private slot called when the selected type was changed.

        @param index index of the current item
        @type int
        """
        type_ = self.typeCombo2.itemText(index)
        self.__changeLabelCombo(self.labelCombo2, type_)

    def getURLs(self):
        """
        Public method to get the entered URLs.

        @return tuple of list of two URL strings and a flag indicating a diff summary
        @rtype tuple of (list of [str, str], bool)
        """
        if self.vcs.otherData["standardLayout"]:
            url1 = (
                self.repoRootLabel1.text()
                + self.typeCombo1.currentText()
                + self.labelCombo1.currentText()
            )
            url2 = (
                self.repoRootLabel2.text()
                + self.typeCombo2.currentText()
                + self.labelCombo2.currentText()
            )
        else:
            url1 = self.labelCombo1.currentText()
            url2 = self.labelCombo2.currentText()

        return [url1, url2], self.summaryCheckBox.isChecked()
