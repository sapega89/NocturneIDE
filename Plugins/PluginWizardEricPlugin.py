# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the eric plug-in wizard plug-in.
"""

import os

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QDialog

from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

# Start-of-Header
__header__ = {
    "name": "eric plug-in Wizard Plug-in",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "WizardEricPluginWizard",
    "packageName": "__core__",
    "shortDescription": "Wizard for the creation of an eric plug-in file.",
    "longDescription": (
        """This plug-in implements a wizard to generate code for"""
        """ an eric plug-in main script file."""
    ),
    "needsRestart": False,
    "pyqtApi": 2,
}
# End-of-Header

error = ""  # noqa: U200


class WizardEricPluginWizard(QObject):
    """
    Class implementing the eric plug-in wizard plug-in.
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
            self.tr("eric Plug-in Wizard"),
            self.tr("eric Plug-in Wizard..."),
            0,
            0,
            self,
            "wizards_eric_plugin",
        )
        self.__action.setStatusTip(self.tr("eric Plug-in Wizard"))
        self.__action.setWhatsThis(
            self.tr(
                """<b>eric Plug-in Wizard</b>"""
                """<p>This wizard opens a dialog for entering all the parameters"""
                """ needed to create the basic contents of an eric plug-in file."""
                """ The generated code is inserted at the current cursor"""
                """ position.</p>"""
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

    def __callForm(self):
        """
        Private method to display a dialog and get the code.

        @return generated code, the plug-in package name and a flag indicating success
        @rtype tuple of (str, str, bool)
        """
        from eric7.Plugins.WizardPlugins.EricPluginWizard.PluginWizardDialog import (
            PluginWizardDialog,
        )

        dlg = PluginWizardDialog(parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return (dlg.getCode(), dlg.packageName(), True)
        else:
            return (None, "", False)

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
            code, packageName, ok = self.__callForm()
            if ok:
                line, index = editor.getCursorPosition()
                # It should be done on this way to allow undo
                editor.beginUndoAction()
                editor.insertAt(code, line, index)
                editor.endUndoAction()
                if not editor.getFileName():
                    editor.setLanguage("dummy.py")

                if packageName:
                    project = ericApp().getObject("Project")
                    packagePath = os.path.join(project.getProjectPath(), packageName)
                    if not os.path.exists(packagePath):
                        try:
                            os.mkdir(packagePath)
                        except OSError as err:
                            EricMessageBox.critical(
                                self,
                                self.tr("Create Package"),
                                self.tr(
                                    """<p>The package directory <b>{0}</b>"""
                                    """ could not be created. Aborting..."""
                                    """</p><p>Reason: {1}</p>"""
                                ).format(packagePath, str(err)),
                            )
                            return
                    packageFile = os.path.join(packagePath, "__init__.py")
                    if not os.path.exists(packageFile):
                        try:
                            with open(packageFile, "w", encoding="utf-8"):
                                pass
                        except OSError as err:
                            EricMessageBox.critical(
                                self,
                                self.tr("Create Package"),
                                self.tr(
                                    """<p>The package file <b>{0}</b> could"""
                                    """ not be created. Aborting...</p>"""
                                    """<p>Reason: {1}</p>"""
                                ).format(packageFile, str(err)),
                            )
                            return
                    project.appendFile(packageFile)
                    project.saveProject()
                    ericApp().getObject("ViewManager").openSourceFile(packageFile)


#
# eflag: noqa = M801
