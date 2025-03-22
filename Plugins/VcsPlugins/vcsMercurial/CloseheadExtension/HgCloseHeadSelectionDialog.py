# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select the heads to be closed.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTreeWidgetItem

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_HgCloseHeadSelectionDialog import Ui_HgCloseHeadSelectionDialog


class HgCloseHeadSelectionDialog(QDialog, Ui_HgCloseHeadSelectionDialog):
    """
    Class implementing a dialog to select the heads to be closed.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the VCS object
        @type Hg
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        project = ericApp().getObject("Project")
        pwl, pel = project.getProjectDictionaries()
        language = project.getProjectSpellLanguage()
        self.logEdit.setLanguageWithPWL(language, pwl or None, pel or None)

        heads = self.__getHeads(vcs)
        for revision, branch in heads:
            QTreeWidgetItem(self.headsList, [revision, branch])

    def __getHeads(self, vcs):
        """
        Private method to get the open heads.

        @param vcs reference to the VCS object
        @type Hg
        @return list of tuples containing the revision and the corresponding
            branch name
        @rtype list of tuples of (str, str)
        """
        args = vcs.initCommand("heads")
        args.append("--template")
        args.append("{node|short}@@@{branches}\n")

        output = ""
        client = vcs.getClient()
        output, _error = client.runcommand(args)

        heads = []
        if output:
            for line in output.splitlines():
                line = line.strip()
                if line:
                    revision, branch = line.split("@@@")
                    heads.append((revision, branch))

        return heads

    @pyqtSlot()
    def on_headsList_itemSelectionChanged(self):
        """
        Private slot handling changes of the selection.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            len(self.headsList.selectedItems()) > 0
        )

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple containing a list of selected revisions and the commit
            message
        @rtype tuple of (list of str, str)
        """
        revisions = [itm.text(0) for itm in self.headsList.selectedItems()]
        message = self.logEdit.toPlainText().strip()

        return revisions, message
