# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the status of the submodules of the
project.
"""

from PyQt6.QtCore import QProcess, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidgetItem,
)

from eric7 import Preferences

from .Ui_GitSubmodulesStatusDialog import Ui_GitSubmodulesStatusDialog


class GitSubmodulesStatusDialog(QDialog, Ui_GitSubmodulesStatusDialog):
    """
    Class implementing a dialog to show the status of the submodules of the
    project.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Git
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__statusCodes = {
            " ": self.tr("up-to-date"),
            "-": self.tr("not initialized"),
            "+": self.tr("different to index"),
            "U": self.tr("merge conflicts"),
        }

        self.__vcs = vcs
        self.__repodir = None

        self.refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the status display"))

    def start(self, projectDir):
        """
        Public method to populate the status list.

        @param projectDir name of the project directory
        @type str
        """
        # find the root of the repo
        self.__repodir = self.__vcs.findRepoRoot(projectDir)
        if not self.__repodir:
            return

        self.errorGroup.hide()
        self.errors.clear()
        self.statusList.clear()
        self.buttonBox.setEnabled(False)

        args = self.__vcs.initCommand("submodule")
        args.append("status")
        if self.recursiveCheckBox.isChecked():
            args.append("--recursive")
        if self.indexCheckBox.isChecked():
            args.append("--cached")

        process = QProcess()
        process.setWorkingDirectory(self.__repodir)
        process.start("git", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                ioEncoding = Preferences.getSystem("IOEncoding")
                output = str(process.readAllStandardOutput(), ioEncoding, "replace")
                error = str(process.readAllStandardError(), ioEncoding, "replace")
                if error:
                    self.errors.setText(error)
                    self.errorGroup.show()
                self.__processOutput(output)
            else:
                if not finished:
                    self.errors.setText(
                        self.tr(
                            "The process {0} did not finish within 30 seconds."
                        ).format("git")
                    )
                else:
                    self.errors.setText(
                        self.tr(
                            "The process {0} finished with an error.\nError: {1}"
                        ).format("git", process.errorString())
                    )
                self.errorGroup.show()
        else:
            self.errors.setText(
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("git")
            )
            self.errorGroup.show()

        self.buttonBox.setEnabled(True)
        self.buttonBox.setFocus()

    def __processOutput(self, output):
        """
        Private method to process the output and populate the list.

        @param output output of the submodule status command
        @type str
        """
        for line in output.splitlines():
            try:
                status = self.__statusCodes[line[0]]
            except KeyError:
                status = self.tr("unknown")
            lineParts = line[1:].split(None, 2)
            if len(lineParts) == 3 and lineParts[2][0] == "(":
                # get rid of leading and trailing brackets
                lineParts[2] = lineParts[2][1:-1]
            QTreeWidgetItem(
                self.statusList,
                [
                    lineParts[1],  # submodule name
                    status,  # submodule status
                    lineParts[0],  # commit ID
                    lineParts[2],  # additional info
                ],
            )

        self.statusList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)

        self.statusList.setSortingEnabled(True)
        self.statusList.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.statusList.setSortingEnabled(False)

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the status display.
        """
        self.start(self.__repodir)

    @pyqtSlot(bool)
    def on_indexCheckBox_toggled(self, _checked):
        """
        Private slot handling a change of the index check box.

        @param _checked check state of the check box (unused)
        @type bool
        """
        self.on_refreshButton_clicked()

    @pyqtSlot(bool)
    def on_recursiveCheckBox_toggled(self, _checked):
        """
        Private slot handling a change of the recursive check box.

        @param _checked check state of the check box (unused)
        @type bool
        """
        self.on_refreshButton_clicked()
