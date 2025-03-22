# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the .desktop wizard plug-in.
"""

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog

from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

# Start-of-Header
__header__ = {
    "name": ".desktop Wizard Plug-in",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "DotDesktopWizard",
    "packageName": "__core__",
    "shortDescription": "Wizard for the creation of a .desktop file.",
    "longDescription": (
        """This plug-in implements a wizard to generate code for a .desktop file."""
    ),
    "needsRestart": False,
    "pyqtApi": 2,
}
# End-of-Header

error = ""  # noqa: U200


class DotDesktopWizard(QObject):
    """
    Class implementing the .desktop wizard plug-in.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        super().__init__(ui)
        self.__ui = ui
        self.__action = None

    def __initialize(self):
        """
        Private slot to (re)initialize the plug-in.
        """
        self.__act = None

    def activate(self):
        """
        Public method to activate this plug-in.

        @return tuple of None and activation status
        @rtype bool
        """
        self.__initAction()
        self.__initMenu()

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plug-in.
        """
        menu = self.__ui.getMenu("wizards")
        if menu:
            menu.removeAction(self.__action)
        self.__ui.removeEricActions([self.__action], "wizards")

    def __initAction(self):
        """
        Private method to initialize the action.
        """
        self.__action = EricAction(
            self.tr(".desktop Wizard"),
            self.tr(".desktop Wizard..."),
            0,
            0,
            self,
            "wizards_dotdesktop",
        )
        self.__action.setStatusTip(self.tr(".desktop Wizard"))
        self.__action.setWhatsThis(
            self.tr(
                """<b>.desktop Wizard</b>"""
                """<p>This wizard opens a dialog for entering all the parameters"""
                """ needed to create the contents of a .desktop file. The"""
                """ generated code replaces the text of the current editor."""
                """ Alternatively a new editor is opened.</p>"""
            )
        )
        self.__action.triggered.connect(self.__handle)

        self.__ui.addEricActions([self.__action], "wizards")

    def __initMenu(self):
        """
        Private method to add the actions to the right menu.
        """
        menu = self.__ui.getMenu("wizards")
        if menu:
            menu.addAction(self.__action)

    def __handle(self):
        """
        Private method to handle the wizards action.
        """
        from eric7.Plugins.WizardPlugins.DotDesktopWizard import DotDesktopWizardDialog

        editor = ericApp().getObject("ViewManager").activeWindow()

        if editor is None:
            EricMessageBox.critical(
                self.__ui,
                self.tr("No current editor"),
                self.tr("Please open or create a file first."),
            )
        else:
            if editor.text():
                ok = EricMessageBox.yesNo(
                    self.__ui,
                    self.tr(".desktop Wizard"),
                    self.tr(
                        """The current editor contains text."""
                        """ Shall this be replaced?"""
                    ),
                    icon=EricMessageBox.Critical,
                )
                if not ok:
                    ericApp().getObject("ViewManager").newEditor()
                    editor = ericApp().getObject("ViewManager").activeWindow()

            dlg = DotDesktopWizardDialog.DotDesktopWizardDialog(parent=self.__ui)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                code = dlg.getCode()
                if code:
                    editor.selectAll()
                    # It should be done on this way to allow undo
                    editor.beginUndoAction()
                    editor.replaceSelectedText(code)
                    editor.endUndoAction()

                    editor.setLanguage("dummy.desktop")


#
# eflag: noqa = M801
