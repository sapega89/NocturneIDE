# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to generate a requirements file.
"""

import enum
import os

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QApplication, QDialog, QDialogButtonBox

from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_PipFreezeDialog import Ui_PipFreezeDialog


class PipFreezeDialogModes(enum.Enum):
    """
    Class defining the various dialog modes.
    """

    Constraints = 1
    Requirements = 2


class PipFreezeDialog(QDialog, Ui_PipFreezeDialog):
    """
    Class implementing a dialog to generate a requirements file.
    """

    def __init__(self, pip, mode=PipFreezeDialogModes.Requirements, parent=None):
        """
        Constructor

        @param pip reference to the main interface object
        @type Pip
        @param mode dialog mod (defaults to PipFreezeDialogModes.Requirements)
        @type PipFreezeDialogModes (optional)
        @param parent reference to the parent widget (defaults to None
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__dialogMode = mode
        if mode is PipFreezeDialogModes.Constraints:
            self.constraintsCheckBox.setChecked(False)
            self.constraintsCheckBox.setEnabled(False)
            self.__title = self.tr("Generate Constraints")

        elif mode is PipFreezeDialogModes.Requirements:
            self.__title = self.tr("Generate Requirements")

        self.setWindowTitle(self.__title)

        self.__refreshButton = self.buttonBox.addButton(
            self.tr("&Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )

        self.__environmentName = ""

        self.requirementsFilePicker.setMode(EricPathPickerModes.SAVE_FILE_MODE)
        self.requirementsFilePicker.setFilters(
            self.tr("Text Files (*.txt);;All Files (*)")
        )

        self.__pip = pip

        self.__requirementsEdited = False
        self.__requirementsAvailable = False

        self.__updateButtons()

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        e.accept()

    @pyqtSlot()
    def on_localCheckBox_clicked(self):
        """
        Private slot handling the switching of the local mode.
        """
        self.__refresh()

    @pyqtSlot()
    def on_userCheckBox_clicked(self):
        """
        Private slot handling the switching of the user-site mode.
        """
        self.__refresh()

    @pyqtSlot(str)
    def on_requirementsFilePicker_textChanged(self, txt):
        """
        Private slot handling a change of the requirements file name.

        @param txt name of the requirements file
        @type str
        """
        self.__updateButtons()

    @pyqtSlot()
    def on_requirementsEdit_textChanged(self):
        """
        Private slot handling changes of the requirements text.
        """
        self.__requirementsEdited = True

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.__refreshButton:
            self.__refresh()

    def __refresh(self):
        """
        Private slot to refresh the displayed list.
        """
        ok = (
            EricMessageBox.yesNo(
                self,
                self.__title,
                self.tr(
                    """The requirements were changed. Do you want"""
                    """ to overwrite these changes?"""
                ),
            )
            if self.__requirementsEdited
            else True
        )
        if ok:
            self.start(self.__environmentName)

    def start(self, venvName):
        """
        Public method to start the command.

        @param venvName name of the environment to act upon
        @type str
        """
        self.requirementsEdit.clear()
        self.__requirementsAvailable = False
        self.__environmentName = venvName

        if not bool(self.requirementsFilePicker.text()):
            self.requirementsFilePicker.setText(
                "constraints.txt"
                if self.__dialogMode is PipFreezeDialogModes.Constraints
                else "requirements.txt"
            )

        fileName = FileSystemUtilities.toNativeSeparators(
            self.requirementsFilePicker.text()
        )
        if fileName and not os.path.isabs(fileName):
            fileName = ""

        with EricOverrideCursor():
            specifiers = self.__pip.getFrozenPackages(
                venvName,
                localPackages=self.localCheckBox.isChecked(),
                usersite=self.userCheckBox.isChecked(),
                requirement=fileName,
            )

            if specifiers:
                self.requirementsEdit.setPlainText("\n".join(specifiers) + "\n")
                self.__requirementsAvailable = True
            else:
                self.requirementsEdit.setPlainText(
                    self.tr("No package specifiers generated by 'pip freeze'.")
                )

        self.__updateButtons()

        self.__requirementsEdited = False

    def __updateButtons(self):
        """
        Private method to set the state of the various buttons.
        """
        self.saveButton.setEnabled(
            self.__requirementsAvailable
            and bool(self.requirementsFilePicker.text())
            and os.path.isabs(self.requirementsFilePicker.text())
        )
        self.saveToButton.setEnabled(self.__requirementsAvailable)
        self.copyButton.setEnabled(self.__requirementsAvailable)

        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw and self.__requirementsAvailable:
            self.insertButton.setEnabled(True)
            self.replaceAllButton.setEnabled(True)
            self.replaceSelectionButton.setEnabled(aw.hasSelectedText())
        else:
            self.insertButton.setEnabled(False)
            self.replaceAllButton.setEnabled(False)
            self.replaceSelectionButton.setEnabled(False)

    def __writeToFile(self, fileName):
        """
        Private method to write the requirements text to a file.

        @param fileName name of the file to write to
        @type str
        """
        if os.path.exists(fileName):
            ok = EricMessageBox.warning(
                self,
                self.__title,
                self.tr(
                    """The file <b>{0}</b> already exists. Do you want"""
                    """ to overwrite it?"""
                ).format(fileName),
            )
            if not ok:
                return

        txt = self.requirementsEdit.toPlainText()
        if self.constraintsCheckBox.isChecked():
            txt = f"--constraint constraints.txt\n{txt}"
        try:
            with open(fileName, "w") as f:
                f.write(txt)
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.__title,
                self.tr(
                    """<p>The requirements could not be written"""
                    """ to <b>{0}</b>.</p><p>Reason: {1}</p>"""
                ).format(fileName, str(err)),
            )

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot to save the requirements text to the requirements file.
        """
        fileName = self.requirementsFilePicker.text()
        self.__writeToFile(fileName)

    @pyqtSlot()
    def on_saveToButton_clicked(self):
        """
        Private slot to write the requirements text to a new file.
        """
        fileName, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.__title,
            os.path.expanduser("~"),
            self.tr("Text Files (*.txt);;All Files (*)"),
            None,
            EricFileDialog.DontConfirmOverwrite,
        )
        if fileName:
            ext = os.path.splitext(fileName)[1]
            if not ext:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fileName += ex
            self.__writeToFile(fileName)

    @pyqtSlot()
    def on_copyButton_clicked(self):
        """
        Private slot to copy the requirements text to the clipboard.
        """
        txt = self.requirementsEdit.toPlainText()
        if self.constraintsCheckBox.isChecked():
            txt = f"--constraint constraints.txt\n{txt}"
        cb = QApplication.clipboard()
        cb.setText(txt)

    @pyqtSlot()
    def on_insertButton_clicked(self):
        """
        Private slot to insert the requirements text at the cursor position
        of the current editor.
        """
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw:
            aw.beginUndoAction()
            aw.insert(self.requirementsEdit.toPlainText())
            aw.endUndoAction()

    @pyqtSlot()
    def on_replaceSelectionButton_clicked(self):
        """
        Private slot to replace the selected text of the current editor
        with the requirements text.
        """
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw:
            aw.beginUndoAction()
            aw.replaceSelectedText(self.requirementsEdit.toPlainText())
            aw.endUndoAction()

    @pyqtSlot()
    def on_replaceAllButton_clicked(self):
        """
        Private slot to replace the text of the current editor with the
        requirements text.
        """
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw:
            aw.setText(self.requirementsEdit.toPlainText())
