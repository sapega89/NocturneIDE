# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Syntax Checker plugin.
"""

import contextlib
import os

from PyQt6.QtCore import QObject

from eric7 import Preferences
from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import getConfig
from eric7.Project.ProjectBrowserModel import ProjectBrowserFileItem

# Start-Of-Header
__header__ = {
    "name": "Syntax Checker Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "SyntaxCheckerPlugin",
    "packageName": "__core__",
    "shortDescription": "Show the Syntax Checker dialog.",
    "longDescription": (
        """This plugin implements the Syntax Checker dialog. Syntax Checker is used"""
        """ to check Python, JavaScript, JSON, TOML and YAML files for correct"""
        """ syntax."""
    ),
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


class SyntaxCheckerPlugin(QObject):
    """
    Class implementing the Syntax Checker plugin.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UI.UserInterface
        """
        from eric7.Plugins.CheckerPlugins.SyntaxChecker.SyntaxCheckService import (
            SyntaxCheckService,
        )

        super().__init__(ui)
        self.__ui = ui
        self.__initialize()

        self.syntaxCheckService = SyntaxCheckService()
        ericApp().registerObject("SyntaxCheckService", self.syntaxCheckService)

        ericPath = getConfig("ericDir")
        path = os.path.join(ericPath, "Plugins", "CheckerPlugins", "SyntaxChecker")

        # Python 3 syntax and pyflakes check
        self.syntaxCheckService.addLanguage(
            "Python3",
            "Python3",
            path,
            "pyCheckSyntax",
            self.__getPythonOptions,
            lambda: Preferences.getPython("Python3Extensions"),
            self.__translateSyntaxCheck,
            self.syntaxCheckService.serviceErrorPy3,
        )

        # YAML syntax check via Python3
        self.syntaxCheckService.addLanguage(
            "YAML",
            "Python3",
            path,
            "yamlCheckSyntax",
            lambda: [],  # No options
            lambda: [".yml", ".yaml"],
            lambda fn, problems: self.syntaxCheckService.syntaxChecked.emit(
                fn, problems
            ),
            self.syntaxCheckService.serviceErrorYAML,
        )

        # JSON syntax check via Python3
        self.syntaxCheckService.addLanguage(
            "JSON",
            "Python3",
            path,
            "jsonCheckSyntax",
            lambda: [],  # No options
            lambda: [".json"],
            lambda fn, problems: self.syntaxCheckService.syntaxChecked.emit(
                fn, problems
            ),
            self.syntaxCheckService.serviceErrorJSON,
        )

        # TOML syntax check via Python3
        self.syntaxCheckService.addLanguage(
            "TOML",
            "Python3",
            path,
            "tomlCheckSyntax",
            lambda: [],  # No options
            lambda: [".toml"],
            lambda fn, problems: self.syntaxCheckService.syntaxChecked.emit(
                fn, problems
            ),
            self.syntaxCheckService.serviceErrorTOML,
        )

        # JavaScript syntax check via Python3
        self.syntaxCheckService.addLanguage(
            "JavaScript",
            "Python3",
            path,
            "jsCheckSyntax",
            lambda: [],  # No options
            lambda: [".js"],
            lambda fn, problems: self.syntaxCheckService.syntaxChecked.emit(
                fn, problems
            ),
            self.syntaxCheckService.serviceErrorJavaScript,
        )

    def __initialize(self):
        """
        Private slot to (re)initialize the plugin.
        """
        self.__projectAct = None
        self.__projectSyntaxCheckerDialog = None

        self.__projectBrowserAct = None
        self.__projectBrowserMenu = None
        self.__projectBrowserSyntaxCheckerDialog = None

        self.__editors = []
        self.__editorAct = None
        self.__editorSyntaxCheckerDialog = None

    def __getPythonOptions(self):
        """
        Private method to determine the syntax check options.

        @return tuple containing a flag indicating to perform a pyflakes check and
            a flag indicating to ignore star import warnings
        @rtype tuple of (bool, bool)
        """
        checkFlakes = Preferences.getFlakes("IncludeInSyntaxCheck")
        ignoreStarImportWarnings = Preferences.getFlakes("IgnoreStarImportWarnings")
        return checkFlakes, ignoreStarImportWarnings

    def __translateSyntaxCheck(self, fn, problems):
        """
        Private slot to translate the resulting messages.

        If checkFlakes is True, warnings contains a list of strings containing
        the warnings (marker, file name, line number, message)
        The values are only valid, if nok is False.

        @param fn filename of the checked file
        @type str
        @param problems list of dictionaries with the keys 'error', 'py_warnings' and
            'warnings' which contain a tuple with details about the syntax error or a
            list of tuples with details about Python warnings and PyFlakes warnings.
            Each tuple contains the file name, line number, column, code string (only
            for syntax errors), the message and an optional list with arguments for
            the message.
        @type list of dict
        """
        from eric7.Plugins.CheckerPlugins.SyntaxChecker.pyflakes.translations import (
            getTranslatedFlakesMessage,
        )

        warnings = problems.get("warnings", [])
        for warning in warnings:
            # Translate messages
            msg_args = warning.pop()
            warning[4] = getTranslatedFlakesMessage(warning[4], msg_args)

        problems["warnings"] = warnings
        self.syntaxCheckService.syntaxChecked.emit(fn, problems)

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of None and activation status
        @rtype bool
        """
        menu = ericApp().getObject("Project").getMenu("Checks")
        if menu:
            self.__projectAct = EricAction(
                self.tr("Check Syntax"),
                self.tr("&Syntax..."),
                0,
                0,
                self,
                "project_check_syntax",
            )
            self.__projectAct.setStatusTip(self.tr("Check syntax."))
            self.__projectAct.setWhatsThis(
                self.tr(
                    """<b>Check Syntax...</b>"""
                    """<p>This checks Python files for syntax errors.</p>"""
                )
            )
            self.__projectAct.triggered.connect(self.__projectSyntaxCheck)
            ericApp().getObject("Project").addEricActions([self.__projectAct])
            menu.addAction(self.__projectAct)

        self.__editorAct = EricAction(
            self.tr("Check Syntax"), self.tr("&Syntax..."), 0, 0, self, ""
        )
        self.__editorAct.setWhatsThis(
            self.tr(
                """<b>Check Syntax...</b>"""
                """<p>This checks Python files for syntax errors.</p>"""
            )
        )
        self.__editorAct.triggered.connect(self.__editorSyntaxCheck)

        ericApp().getObject("Project").showMenu.connect(self.__projectShowMenu)
        ericApp().getObject("ProjectBrowser").getProjectBrowser(
            "sources"
        ).showMenu.connect(self.__projectBrowserShowMenu)
        ericApp().getObject("ViewManager").editorOpenedEd.connect(self.__editorOpened)
        ericApp().getObject("ViewManager").editorClosedEd.connect(self.__editorClosed)

        for editor in ericApp().getObject("ViewManager").getOpenEditors():
            self.__editorOpened(editor)

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        ericApp().getObject("Project").showMenu.disconnect(self.__projectShowMenu)
        ericApp().getObject("ProjectBrowser").getProjectBrowser(
            "sources"
        ).showMenu.disconnect(self.__projectBrowserShowMenu)
        ericApp().getObject("ViewManager").editorOpenedEd.disconnect(
            self.__editorOpened
        )
        ericApp().getObject("ViewManager").editorClosedEd.disconnect(
            self.__editorClosed
        )

        menu = ericApp().getObject("Project").getMenu("Checks")
        if menu:
            menu.removeAction(self.__projectAct)

        if self.__projectBrowserMenu and self.__projectBrowserAct:
            self.__projectBrowserMenu.removeAction(self.__projectBrowserAct)

        for editor in self.__editors:
            editor.showMenu.disconnect(self.__editorShowMenu)
            menu = editor.getMenu("Checks")
            if menu is not None:
                menu.removeAction(self.__editorAct)

        self.__initialize()

    def __projectShowMenu(self, menuName, _menu):
        """
        Private slot called, when the the project menu or a submenu is
        about to be shown.

        @param menuName name of the menu to be shown
        @type str
        @param _menu reference to the menu (unused)
        @type QMenu
        """
        if menuName == "Checks" and self.__projectAct is not None:
            self.__projectAct.setEnabled(
                ericApp().getObject("Project").getProjectLanguage()
                in self.syntaxCheckService.getLanguages()
            )

    def __projectBrowserShowMenu(self, menuName, menu):
        """
        Private slot called, when the the project browser menu or a submenu is
        about to be shown.

        @param menuName name of the menu to be shown
        @type str
        @param menu reference to the menu
        @type QMenu
        """
        if (
            menuName == "Checks"
            and ericApp().getObject("Project").getProjectLanguage()
            in self.syntaxCheckService.getLanguages()
        ):
            self.__projectBrowserMenu = menu
            if self.__projectBrowserAct is None:
                self.__projectBrowserAct = EricAction(
                    self.tr("Check Syntax"), self.tr("&Syntax..."), 0, 0, self, ""
                )
                self.__projectBrowserAct.setWhatsThis(
                    self.tr(
                        """<b>Check Syntax...</b>"""
                        """<p>This checks Python files for syntax errors.</p>"""
                    )
                )
                self.__projectBrowserAct.triggered.connect(
                    self.__projectBrowserSyntaxCheck
                )
            if self.__projectBrowserAct not in menu.actions():
                menu.addAction(self.__projectBrowserAct)

    def __projectSyntaxCheck(self):
        """
        Private slot used to check the project files for syntax errors.
        """
        from eric7.Plugins.CheckerPlugins.SyntaxChecker.SyntaxCheckerDialog import (
            SyntaxCheckerDialog,
        )

        project = ericApp().getObject("Project")
        project.saveAllScripts()
        ppath = project.getProjectPath()
        extensions = tuple(self.syntaxCheckService.getExtensions())
        files = [
            os.path.join(ppath, file)
            for file in project.getProjectData(dataKey="SOURCES")
            if file.endswith(extensions)
        ]

        self.__projectSyntaxCheckerDialog = SyntaxCheckerDialog()
        self.__projectSyntaxCheckerDialog.show()
        self.__projectSyntaxCheckerDialog.prepare(files, project)

    def __projectBrowserSyntaxCheck(self):
        """
        Private method to handle the syntax check context menu action of the
        project sources browser.
        """
        from eric7.Plugins.CheckerPlugins.SyntaxChecker.SyntaxCheckerDialog import (
            SyntaxCheckerDialog,
        )

        browser = ericApp().getObject("ProjectBrowser").getProjectBrowser("sources")
        if browser.getSelectedItemsCount([ProjectBrowserFileItem]) > 1:
            fn = [
                itm.fileName()
                for itm in browser.getSelectedItems([ProjectBrowserFileItem])
            ]
        else:
            itm = browser.model().item(browser.currentIndex())
            try:
                fn = itm.fileName()
            except AttributeError:
                fn = itm.dirName()

        self.__projectBrowserSyntaxCheckerDialog = SyntaxCheckerDialog()
        self.__projectBrowserSyntaxCheckerDialog.show()
        self.__projectBrowserSyntaxCheckerDialog.startForBrowser(fn)

    def __editorOpened(self, editor):
        """
        Private slot called, when a new editor was opened.

        @param editor reference to the new editor
        @type QScintilla.Editor
        """
        menu = editor.getMenu("Checks")
        if menu is not None:
            menu.addAction(self.__editorAct)
            editor.showMenu.connect(self.__editorShowMenu)
            self.__editors.append(editor)

    def __editorClosed(self, editor):
        """
        Private slot called, when an editor was closed.

        @param editor reference to the editor
        @type QScintilla.Editor
        """
        with contextlib.suppress(ValueError):
            self.__editors.remove(editor)

    def __editorShowMenu(self, menuName, menu, editor):
        """
        Private slot called, when the the editor context menu or a submenu is
        about to be shown.

        @param menuName name of the menu to be shown
        @type str
        @param menu reference to the menu
        @type QMenu
        @param editor reference to the editor
        @type QScintilla.Editor
        """
        if menuName == "Checks":
            if self.__editorAct not in menu.actions():
                menu.addAction(self.__editorAct)
            self.__editorAct.setEnabled(
                editor.getLanguage() in self.syntaxCheckService.getLanguages()
            )

    def __editorSyntaxCheck(self):
        """
        Private slot to handle the syntax check context menu action of the
        editors.
        """
        from eric7.Plugins.CheckerPlugins.SyntaxChecker.SyntaxCheckerDialog import (
            SyntaxCheckerDialog,
        )

        project = ericApp().getObject("Project")
        editor = ericApp().getObject("ViewManager").activeWindow()
        if editor is not None:
            self.__editorSyntaxCheckerDialog = SyntaxCheckerDialog()
            if editor.isPy3File():
                self.__editorSyntaxCheckerDialog.setArguments(
                    (
                        project.getData("CHECKERSPARMS", "SyntaxChecker", {}).get(
                            "AdditionalBuiltins", []
                        ),
                    )
                    if editor.isProjectFile()
                    else (Preferences.getFlakes("AdditionalBuiltins"),)
                )
            self.__editorSyntaxCheckerDialog.show()
            if editor.isJavascriptFile():
                unnamed = "Unnamed.js"
            else:
                unnamed = "Unnamed.py"
            self.__editorSyntaxCheckerDialog.start(
                editor.getFileName() or unnamed, editor.text()
            )
