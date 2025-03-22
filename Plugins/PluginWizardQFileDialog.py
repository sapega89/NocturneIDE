# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the QFileDialog wizard plugin.
"""

import re

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog

from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

# Start-Of-Header
__header__ = {
    "name": "QFileDialog Wizard Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "FileDialogWizard",
    "packageName": "__core__",
    "shortDescription": "Show the QFileDialog wizard.",
    "longDescription": """This plugin shows the QFileDialog wizard.""",
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


class FileDialogWizard(QObject):
    """
    Class implementing the QFileDialog wizard plugin.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        super().__init__(ui)
        self.__ui = ui

        # PyQt5/PyQt6
        self.__pyqtRe = re.compile(r"(?:import|from)\s+PyQt([56])")

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of None and activation status
        @rtype bool
        """
        self.__initActions()
        self.__initMenu()

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        menu = self.__ui.getMenu("wizards")
        if menu:
            menu.removeAction(self.qFileDialogAction)
            menu.removeAction(self.ericFileDialogAction)
        self.__ui.removeEricActions(
            [self.qFileDialogAction, self.ericFileDialogAction], "wizards"
        )

    def __initActions(self):
        """
        Private method to initialize the actions.
        """
        self.qFileDialogAction = EricAction(
            self.tr("QFileDialog Wizard"),
            self.tr("QFileDialog Wizard..."),
            0,
            0,
            self,
            "wizards_qfiledialog",
        )
        self.qFileDialogAction.setStatusTip(self.tr("QFileDialog Wizard"))
        self.qFileDialogAction.setWhatsThis(
            self.tr(
                """<b>QFileDialog Wizard</b>"""
                """<p>This wizard opens a dialog for entering all the parameters"""
                """ needed to create a QFileDialog. The generated code is"""
                """ inserted at the current cursor position.</p>"""
            )
        )
        self.qFileDialogAction.triggered.connect(lambda: self.__handle("QFileDialog"))

        self.ericFileDialogAction = EricAction(
            self.tr("EricFileDialog Wizard"),
            self.tr("EricFileDialog Wizard..."),
            0,
            0,
            self,
            "wizards_e5filedialog",
        )
        self.ericFileDialogAction.setStatusTip(self.tr("EricFileDialog Wizard"))
        self.ericFileDialogAction.setWhatsThis(
            self.tr(
                """<b>EricFileDialog Wizard</b>"""
                """<p>This wizard opens a dialog for entering all the parameters"""
                """ needed to create an EricFileDialog. The generated code is"""
                """ inserted at the current cursor position.</p>"""
            )
        )
        self.ericFileDialogAction.triggered.connect(
            lambda: self.__handle("EricFileDialog")
        )

        self.__ui.addEricActions(
            [self.qFileDialogAction, self.ericFileDialogAction], "wizards"
        )

    def __initMenu(self):
        """
        Private method to add the actions to the right menu.
        """
        menu = self.__ui.getMenu("wizards")
        if menu:
            menu.addAction(self.ericFileDialogAction)
            menu.addAction(self.qFileDialogAction)

    def __callForm(self, editor, variant):
        """
        Private method to display a dialog and get the code.

        @param editor reference to the current editor
        @type Editor
        @param variant variant of code to be generated
            (-1 = EricFileDialog, 0 = unknown, 5 = PyQt5, 6 = PyQt6)
        @type int
        @return the generated code
        @rtype str
        """
        from eric7.Plugins.WizardPlugins.FileDialogWizard import FileDialogWizardDialog

        dlg = FileDialogWizardDialog.FileDialogWizardDialog(variant, parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            line, index = editor.getCursorPosition()
            indLevel = editor.indentation(line) // editor.indentationWidth()
            if editor.indentationsUseTabs():
                indString = "\t"
            else:
                indString = editor.indentationWidth() * " "
            return (dlg.getCode(indLevel, indString), 1)
        else:
            return (None, 0)

    def __handle(self, variant):
        """
        Private method to handle the wizards action.

        @param variant dialog variant to be generated
            (EricFileDialog or QFileDialog)
        @type str
        @exception ValueError raised to indicate an illegal file dialog variant
        """
        editor = ericApp().getObject("ViewManager").activeWindow()

        if editor is None:
            EricMessageBox.critical(
                self.__ui,
                self.tr("No current editor"),
                self.tr("Please open or create a file first."),
            )
        else:
            if variant not in ("QFileDialog", "EricFileDialog"):
                raise ValueError("Illegal dialog variant given")

            if variant == "QFileDialog":
                match = self.__pyqtRe.search(editor.text())
                if match is None:
                    # unknown
                    dialogVariant = 0
                else:
                    # PyQt5/PyQt6
                    dialogVariant = int(match.group(1))
            else:
                # EricFileDialog
                dialogVariant = -1

            code, ok = self.__callForm(editor, dialogVariant)
            if ok:
                line, index = editor.getCursorPosition()
                # It should be done on this way to allow undo
                editor.beginUndoAction()
                editor.insertAt(code, line, index)
                editor.endUndoAction()
