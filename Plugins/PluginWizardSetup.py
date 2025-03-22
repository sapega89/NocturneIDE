# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the setup.py wizard plug-in.
"""

import functools

from PyQt6.QtCore import QObject

from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

# Start-of-Header
__header__ = {
    "name": "setup.py Wizard Plug-in",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "SetupWizard",
    "packageName": "__core__",
    "shortDescription": "Wizard for the creation of a setup.py file.",
    "longDescription": (
        """This plug-in implements a wizard to generate code for"""
        """ a setup.py file. It supports the 'setuptools' variant."""
    ),
    "needsRestart": False,
    "pyqtApi": 2,
}
# End-of-Header

error = ""  # noqa: U200


class SetupWizard(QObject):
    """
    Class implementing the setup.py wizard plug-in.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UI.UserInterface
        """
        super().__init__(ui)
        self.__ui = ui
        self.__actions = []

    def activate(self):
        """
        Public method to activate this plug-in.

        @return tuple of None and activation status
        @rtype tuple of (None, boolean)
        """
        self.__initActions()
        self.__initMenu()

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plug-in.
        """
        menu = self.__ui.getMenu("wizards")
        if menu:
            for act in self.__actions:
                menu.removeAction(act)
        self.__ui.removeEricActions(self.__actions, "wizards")

    def __initActions(self):
        """
        Private method to initialize the actions.
        """
        # 1. action for 'setup.py' creation
        act = EricAction(
            self.tr("setup.py Wizard"),
            self.tr("setup.py Wizard..."),
            0,
            0,
            self,
            "wizards_setup_py",
        )
        act.setStatusTip(self.tr("setup.py Wizard"))
        act.setWhatsThis(
            self.tr(
                """<b>setup.py Wizard</b>"""
                """<p>This wizard opens a dialog for entering all the parameters"""
                """ needed to create the basic contents of a setup.py file. The"""
                """ generated code is inserted at the current cursor position."""
                """</p>"""
            )
        )
        act.triggered.connect(functools.partial(self.__handle, "setup.py"))
        self.__actions.append(act)

        # 2. action for 'setup.cfg' creation
        act = EricAction(
            self.tr("setup.cfg Wizard"),
            self.tr("setup.cfg Wizard..."),
            0,
            0,
            self,
            "wizards_setup_cfg",
        )
        act.setStatusTip(self.tr("setup.cfg Wizard"))
        act.setWhatsThis(
            self.tr(
                """<b>setup.cfg Wizard</b>"""
                """<p>This wizard opens a dialog for entering all the parameters"""
                """ needed to create the basic contents of a setup.cfg file. The"""
                """ generated code is inserted at the current cursor position."""
                """</p>"""
            )
        )
        act.triggered.connect(functools.partial(self.__handle, "setup.cfg"))
        self.__actions.append(act)

        # 3. action for 'pyproject.toml' creation
        act = EricAction(
            self.tr("pyproject.toml Wizard"),
            self.tr("pyproject.toml Wizard..."),
            0,
            0,
            self,
            "wizards_pyproject_toml",
        )
        act.setStatusTip(self.tr("pyproject.toml Wizard"))
        act.setWhatsThis(
            self.tr(
                """<b>pyproject.toml Wizard</b>"""
                """<p>This wizard opens a dialog for entering all the parameters"""
                """ needed to create the basic contents of a pyproject.toml file. The"""
                """ generated code is inserted at the current cursor position."""
                """</p>"""
            )
        )
        act.triggered.connect(functools.partial(self.__handle, "pyproject.toml"))
        self.__actions.append(act)

        self.__ui.addEricActions(self.__actions, "wizards")

    def __initMenu(self):
        """
        Private method to add the actions to the right menu.
        """
        menu = self.__ui.getMenu("wizards")
        if menu:
            menu.addActions(self.__actions)

    def __handle(self, category):
        """
        Private method to handle the wizards action.

        @param category category of setup file to create
        @type str
        """
        from eric7.Plugins.WizardPlugins.SetupWizard.SetupWizardDialog import (
            SetupWizardDialog,
        )

        editor = ericApp().getObject("ViewManager").activeWindow()

        if editor is None:
            EricMessageBox.critical(
                self.__ui,
                self.tr("No current editor"),
                self.tr("Please open or create a file first."),
            )
        else:
            dlg = SetupWizardDialog(category, editor, self.__ui)
            dlg.show()


#
# eflag: noqa = M801
