# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the EricMessageBox wizard plugin.
"""

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog

from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

# Start-Of-Header
__header__ = {
    "name": "EricMessageBox Wizard Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "EricMessageBoxWizard",
    "packageName": "__core__",
    "shortDescription": "Show the EricMessageBox wizard.",
    "longDescription": """This plugin shows the EricMessageBox wizard.""",
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


class EricMessageBoxWizard(QObject):
    """
    Class implementing the EricMessageBox wizard plugin.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        super().__init__(ui)
        self.__ui = ui

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of None and activation status
        @rtype bool
        """
        self.__initAction()
        self.__initMenu()

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        menu = self.__ui.getMenu("wizards")
        if menu:
            menu.removeAction(self.action)
        self.__ui.removeEricActions([self.action], "wizards")

    def __initAction(self):
        """
        Private method to initialize the action.
        """
        self.action = EricAction(
            self.tr("EricMessageBox Wizard"),
            self.tr("EricMessageBox Wizard..."),
            0,
            0,
            self,
            "wizards_e5messagebox",
        )
        self.action.setStatusTip(self.tr("EricMessageBox Wizard"))
        self.action.setWhatsThis(
            self.tr(
                """<b>EricMessageBox Wizard</b>"""
                """<p>This wizard opens a dialog for entering all the parameters"""
                """ needed to create an EricMessageBox. The generated code is"""
                """ inserted at the current cursor position.</p>"""
            )
        )
        self.action.triggered.connect(self.__handle)

        self.__ui.addEricActions([self.action], "wizards")

    def __initMenu(self):
        """
        Private method to add the actions to the right menu.
        """
        menu = self.__ui.getMenu("wizards")
        if menu:
            menu.addAction(self.action)

    def __callForm(self, editor):
        """
        Private method to display a dialog and get the code.

        @param editor reference to the current editor
        @type Editor
        @return the generated code
        @rtype str
        """
        from eric7.Plugins.WizardPlugins.EricMessageBoxWizard import (
            EricMessageBoxWizardDialog,
        )

        dlg = EricMessageBoxWizardDialog.EricMessageBoxWizardDialog(parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            line, index = editor.getCursorPosition()
            indLevel = editor.indentation(line) // editor.indentationWidth()
            if editor.indentationsUseTabs():
                indString = "\t"
            else:
                indString = editor.indentationWidth() * " "
            return (dlg.getCode(indLevel, indString), True)
        else:
            return (None, False)

    def __handle(self):
        """
        Private method to handle the wizards action.
        """
        editor = ericApp().getObject("ViewManager").activeWindow()

        if editor is None:
            EricMessageBox.critical(
                self.__ui,
                self.tr("No current editor"),
                self.tr("Please open or create a file first."),
            )
        else:
            code, ok = self.__callForm(editor)
            if ok:
                line, index = editor.getCursorPosition()
                # It should be done on this way to allow undo
                editor.beginUndoAction()
                editor.insertAt(code, line, index)
                editor.endUndoAction()


#
# eflag: noqa = M841
