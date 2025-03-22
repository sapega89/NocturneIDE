# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show information about the installation.
"""

import json
import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Globals
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricPlainTextDialog import EricPlainTextDialog
from eric7.SystemUtilities import OSUtilities

from .Ui_InstallInfoDialog import Ui_InstallInfoDialog


class InstallInfoDialog(QDialog, Ui_InstallInfoDialog):
    """
    Class implementing a dialog to show information about the installation.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__deleteButton = self.buttonBox.addButton(
            self.tr("Delete Info"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__deleteButton.clicked.connect(self.on_deleteButton_clicked)
        self.__updateButton = self.buttonBox.addButton(
            self.tr("Upgrade Instructions"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__updateButton.clicked.connect(self.on_updateButton_clicked)

        self.__edited = False
        self.__loaded = True

        self.editButton.setIcon(EricPixmapCache.getIcon("infoEdit"))
        self.saveButton.setIcon(EricPixmapCache.getIcon("fileSave"))

        infoFileName = Globals.getInstallInfoFilePath()

        self.__deleteButton.setEnabled(os.path.exists(infoFileName))

        try:
            with open(infoFileName, "r") as infoFile:
                self.__info = json.load(infoFile)

            if OSUtilities.isWindowsPlatform():
                self.sudoLabel1.setText(self.tr("Installed as Administrator:"))
            else:
                self.sudoLabel1.setText(self.tr("Installed with sudo:"))
            self.sudoLabel2.setText(
                self.tr("Yes") if self.__info["sudo"] else self.tr("No")
            )
            self.userLabel.setText(self.__info["user"])
            self.installedFromEdit.setText(self.__info["install_cwd"])
            self.interpreteEdit.setText(self.__info["exe"])
            self.commandEdit.setText(self.__info["argv"])
            self.installPathEdit.setText(self.__info["eric"])
            self.virtenvLabel.setText(
                self.tr("Yes") if self.__info["virtualenv"] else self.tr("No")
            )
            self.remarksEdit.setPlainText(self.__info["remarks"])
            if self.__info["pip"]:
                self.pipLabel.setText(
                    self.tr("'eric-ide' was installed from PyPI using the pip command.")
                )
            else:
                self.pipLabel.hide()
            if self.__info["guessed"]:
                self.guessLabel.setText(
                    self.tr(
                        "The information shown in this dialog was guessed at"
                        " the first start of eric."
                    )
                )
            else:
                self.guessLabel.hide()
            if self.__info["edited"]:
                self.userProvidedLabel.setText(
                    self.tr("The installation information was provided by the user.")
                )
            else:
                self.userProvidedLabel.hide()
            if self.__info["installed_on"]:
                self.installDateTimeLabel.setText(
                    self.__info["installed_on"]
                    if self.__info["installed_on"]
                    else self.tr("unknown")
                )

            self.__updateButton.setEnabled(bool(self.__info["exe"]))
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Load Install Information"),
                self.tr(
                    "<p>The file containing the install information could"
                    " not be read.</p><p>Reason: {0}</p>"
                    ""
                ).format(str(err)),
            )
            self.__loaded = False
            self.__info = {}

            self.__updateButton.setEnabled(False)

    def wasLoaded(self):
        """
        Public method to check, if the install data was loaded.

        @return flag indicating the data was loaded
        @rtype bool
        """
        return self.__loaded

    @pyqtSlot(bool)
    def on_editButton_toggled(self, checked):
        """
        Private slot to switch the dialog into edit mode.

        @param checked flag giving the button check state
        @type bool
        """
        self.installedFromEdit.setReadOnly(not checked)
        self.interpreteEdit.setReadOnly(not checked)
        self.commandEdit.setReadOnly(not checked)
        self.installPathEdit.setReadOnly(not checked)
        self.remarksEdit.setReadOnly(not checked)

        if checked:
            self.__edited = True

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot handling the save button press.
        """
        if self.__edited:
            self.__saveData()

    @pyqtSlot()
    def reject(self):
        """
        Public slot handling the closing of the dialog.
        """
        if self.__edited:
            yes = EricMessageBox.yesNo(
                self,
                self.tr("Install Information"),
                self.tr(
                    """The install information was edited. Unsaved"""
                    """ changes will be lost. Save first?"""
                ),
                yesDefault=True,
            )
            if yes:
                self.__saveData()

        super().reject()

    def __saveData(self):
        """
        Private method to save the data.
        """
        if self.installedFromEdit.text() != self.__info["install_cwd"]:
            self.__info["install_cwd"] = self.installedFromEdit.text()
            self.__info["install_cwd_edited"] = True
        if self.interpreteEdit.text() != self.__info["exe"]:
            self.__info["exe"] = self.interpreteEdit.text()
            self.__info["exe_edited"] = True
        if self.commandEdit.text() != self.__info["argv"]:
            self.__info["argv"] = self.commandEdit.text()
            self.__info["argv_edited"] = True
        if self.installPathEdit.text() != self.__info["eric"]:
            self.__info["eric"] = self.installPathEdit.text()
            self.__info["eric_edited"] = True
        self.__info["remarks"] = self.remarksEdit.toPlainText()
        self.__info["edited"] = True

        infoFileName = Globals.getInstallInfoFilePath()
        try:
            with open(infoFileName, "w") as infoFile:
                json.dump(self.__info, infoFile, indent=2)
            self.__edited = False
            self.editButton.setChecked(False)
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("Save Install Information"),
                self.tr(
                    "<p>The file containing the install information could"
                    " not be written.</p><p>Reason: {0}</p>"
                    ""
                ).format(str(err)),
            )

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot deleting the install information file.
        """
        res = EricMessageBox.yesNo(
            self,
            self.tr("Delete Installation Information"),
            self.tr(
                """Do you really want to delete the installation"""
                """ information? It will be recreated at the next"""
                """ start."""
            ),
        )
        if not res:
            return

        infoFileName = Globals.getInstallInfoFilePath()
        os.remove(infoFileName)

        # local data will be deleted automatically
        self.__edited = False

        self.close()

    @pyqtSlot()
    def on_updateButton_clicked(self):
        """
        Private slot to show some upgrade instructions.
        """
        updateTextList = []
        cmdPrefix = ""

        if self.__info["sudo"]:
            if OSUtilities.isWindowsPlatform():
                updateTextList.append(
                    self.tr(
                        "Perform the following step(s) with Administrator"
                        " privileges.\n"
                    )
                )
            else:
                cmdPrefix = "sudo "

        if self.__info["pip"]:
            updateTextList.append(
                "{0}{1} -m pip install --upgrade eric-ide".format(
                    cmdPrefix,
                    self.__info["exe"],
                )
            )
        else:
            if "install_cwd" in self.__info and bool(self.__info["install_cwd"]):
                updateTextList.append("cd {0}".format(self.__info["install_cwd"]))
            updateTextList.append(
                "{0}{1} {2}".format(
                    cmdPrefix,
                    self.__info["exe"],
                    self.__info["argv"],
                )
            )

        dlg = EricPlainTextDialog(
            title=self.tr("Upgrade Instructions"),
            text="\n".join(updateTextList),
            parent=self,
        )
        dlg.exec()
