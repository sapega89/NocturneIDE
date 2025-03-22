# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to generate a requirements file.
"""

import os

import circup

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox

from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_RequirementsDialog import Ui_RequirementsDialog


class RequirementsDialog(QDialog, Ui_RequirementsDialog):
    """
    Class implementing a dialog to generate a requirements file.
    """

    def __init__(self, devicePath, parent=None):
        """
        Constructor

        @param devicePath path to the connected board
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__title = self.tr("Generate Requirements")

        self.__refreshButton = self.buttonBox.addButton(
            self.tr("&Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )

        self.requirementsFilePicker.setMode(EricPathPickerModes.SAVE_FILE_MODE)
        self.requirementsFilePicker.setFilters(
            self.tr("Text Files (*.txt);;All Files (*)")
        )

        self.__devicePath = devicePath

        self.__requirementsEdited = False
        self.__requirementsAvailable = False

        self.__generateRequirements()

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
            self.__generateRequirements()

    def __generateRequirements(self):
        """
        Private slot to generate the requirements specifiers list.
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
            self.requirementsEdit.clear()
            self.__requirementsAvailable = False

            if not bool(self.requirementsFilePicker.text()):
                self.requirementsFilePicker.setText("requirements.txt")

            fileName = FileSystemUtilities.toNativeSeparators(
                self.requirementsFilePicker.text()
            )
            if fileName and not os.path.isabs(fileName):
                fileName = ""

            modules = circup.find_modules(self.__devicePath, circup.get_bundles_list())
            specifiers = []
            if modules:
                for module in modules:
                    specifiers.append(
                        "{0}=={1}".format(module.name, module.device_version)
                    )

            if specifiers:
                self.requirementsEdit.setPlainText("\n".join(specifiers) + "\n")
                self.__requirementsAvailable = True
            else:
                self.requirementsEdit.setPlainText(
                    self.tr("No package specifiers generated.")
                )

            self.__updateButtons()

            self.__requirementsEdited = False

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
        cb = QGuiApplication.clipboard()
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
