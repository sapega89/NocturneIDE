# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the code style checker plug-in.
"""

import contextlib
import os
import textwrap

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from eric7 import Preferences
from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Project.ProjectBrowserModel import ProjectBrowserFileItem
from eric7.SystemUtilities import PythonUtilities

# Start-Of-Header
__header__ = {
    "name": "Code Style Checker Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "CodeStyleCheckerPlugin",
    "packageName": "__core__",
    "shortDescription": "Show the Python Code Style Checker dialog.",
    "longDescription": (
        """This plugin implements the Python Code Style"""
        """ Checker dialog. A PEP-8 checker is used to check Python source"""
        """ files for compliance to the code style conventions given in PEP-8."""
        """ A PEP-257 checker is used to check Python source files for"""
        """ compliance to docstring conventions given in PEP-257 and an"""
        """ eric variant is used to check against eric conventions."""
    ),
    "pyqtApi": 2,
}
# End-Of-Header


error = ""  # noqa: U200


class CodeStyleCheckerPlugin(QObject):
    """
    Class implementing the code style checker plug-in.

    @signal styleChecked(str, dict, int, list) emitted when the style check was
        done for a file.
    @signal batchFinished() emitted when a style check batch is done
    @signal error(str, str) emitted in case of an error
    """

    styleChecked = pyqtSignal(str, dict, int, list)
    batchFinished = pyqtSignal()
    error = pyqtSignal(str, str)

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        super().__init__(ui)
        self.__ui = ui
        self.__initialize()

        self.backgroundService = ericApp().getObject("BackgroundService")

        path = os.path.join(
            os.path.dirname(__file__), "CheckerPlugins", "CodeStyleChecker"
        )
        self.backgroundService.serviceConnect(
            "style",
            "Python3",
            path,
            "CodeStyleChecker",
            self.__translateStyleCheck,
            onErrorCallback=self.serviceErrorPy3,
            onBatchDone=self.batchJobDone,
        )

        self.queuedBatches = []
        self.batchesFinished = True

        self.__wrapper = textwrap.TextWrapper(width=80)

    def __serviceError(self, fn, msg):
        """
        Private slot handling service errors.

        @param fn file name
        @type str
        @param msg message text
        @type str
        """
        self.error.emit(fn, msg)

    def serviceErrorPy3(self, fx, lang, fn, msg):
        """
        Public slot handling service errors for Python 3.

        @param fx service name
        @type str
        @param lang language
        @type str
        @param fn file name
        @type str
        @param msg message text
        @type str
        """
        if fx in ["style", "batch_style"] and lang == "Python3":
            if fx == "style":
                self.__serviceError(fn, msg)
            else:
                self.__serviceError(self.tr("Python 3 batch check"), msg)
                self.batchJobDone(fx, lang)

    def batchJobDone(self, fx, lang):
        """
        Public slot handling the completion of a batch job.

        @param fx service name
        @type str
        @param lang language
        @type str
        """
        if fx in ["style", "batch_style"]:
            if lang in self.queuedBatches:
                self.queuedBatches.remove(lang)
            # prevent sending the signal multiple times
            if len(self.queuedBatches) == 0 and not self.batchesFinished:
                self.batchFinished.emit()
                self.batchesFinished = True

    def __initialize(self):
        """
        Private slot to (re)initialize the plugin.
        """
        self.__projectAct = None
        self.__projectCodeStyleCheckerDialog = None

        self.__projectBrowserAct = None
        self.__projectBrowserMenu = None
        self.__projectBrowserCodeStyleCheckerDialog = None

        self.__editors = []
        self.__editorAct = None
        self.__editorCodeStyleCheckerDialog = None

    def styleCheck(self, lang, filename, source, args):
        """
        Public method to prepare a style check on one Python source file.

        @param lang language of the file or None to determine by internal
            algorithm
        @type str or None
        @param filename source filename
        @type str
        @param source list of code lines to be checked
        @type list of str
        @param args arguments used by the codeStyleCheck function (list of
            excludeMessages, includeMessages, repeatMessages, fixCodes,
            noFixCodes, fixIssues, maxLineLength, blankLines, hangClosing,
            docType, codeComplexityArgs, miscellaneousArgs, errors, eol,
            encoding, backup)
        @type list of (str, str, bool, str, str, bool, int, list of (int, int),
            bool, str, dict, dict, list of str, str, str, bool)
        """
        if (lang is None and PythonUtilities.isPythonSource(filename, source)) or (
            lang is not None and lang == "Python3"
        ):
            data = [source, args]
            self.backgroundService.enqueueRequest("style", "Python3", filename, data)

    def styleBatchCheck(self, argumentsList):
        """
        Public method to prepare a style check on multiple Python source files.

        @param argumentsList list of arguments tuples with each tuple
            containing filename, source and args as given in styleCheck()
            method
        @type list of tuple of (str, str, list)
        """
        data = {
            "Python3": [],
        }
        for filename, source, args in argumentsList:
            if PythonUtilities.isPythonSource(filename, source):
                data["Python3"].append((filename, source, args))

        self.queuedBatches = []
        if data["Python3"]:
            self.queuedBatches.append("Python3")
            self.backgroundService.enqueueRequest(
                "batch_style", "Python3", "", data["Python3"]
            )
            self.batchesFinished = False

    def cancelStyleBatchCheck(self):
        """
        Public method to cancel all batch jobs.
        """
        self.backgroundService.requestCancel("batch_style", "Python3")

    def __translateStyleCheck(self, fn, codeStyleCheckerStats, results):
        """
        Private slot called after performing a style check on one file.

        @param fn filename of the just checked file
        @type str
        @param codeStyleCheckerStats stats of style and name check
        @type dict
        @param results dictionary containing the check result data
            (see CodesStyleChecker.__checkCodeStyle for details)
        @type dict
        """
        from eric7.Plugins.CheckerPlugins.CodeStyleChecker.translations import (
            getTranslatedMessage,
        )

        fixes = 0
        for result in results:
            msg = getTranslatedMessage(result["code"], result["args"])

            if result["fixcode"]:
                fixes += 1
                trFixedMsg = getTranslatedMessage(result["fixcode"], result["fixargs"])

                msg += "\n" + QCoreApplication.translate(
                    "CodeStyleCheckerDialog", "Fix: {0}"
                ).format(trFixedMsg)

            result["display"] = "\n".join(self.__wrapper.wrap(msg))
        self.styleChecked.emit(fn, codeStyleCheckerStats, fixes, results)

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of None and activation status
        @rtype bool
        """
        menu = ericApp().getObject("Project").getMenu("Checks")
        if menu:
            self.__projectAct = EricAction(
                self.tr("Check Code Style"),
                self.tr("&Code Style..."),
                0,
                0,
                self,
                "project_check_pep8",
            )
            self.__projectAct.setStatusTip(self.tr("Check code style."))
            self.__projectAct.setWhatsThis(
                self.tr(
                    """<b>Check Code Style...</b>"""
                    """<p>This checks Python files for compliance to the"""
                    """ code style conventions given in various PEPs.</p>"""
                )
            )
            self.__projectAct.triggered.connect(self.__projectCodeStyleCheck)
            ericApp().getObject("Project").addEricActions([self.__projectAct])
            menu.addAction(self.__projectAct)

        self.__editorAct = EricAction(
            self.tr("Check Code Style"), self.tr("&Code Style..."), 0, 0, self, ""
        )
        self.__editorAct.setWhatsThis(
            self.tr(
                """<b>Check Code Style...</b>"""
                """<p>This checks Python files for compliance to the"""
                """ code style conventions given in various PEPs.</p>"""
            )
        )
        self.__editorAct.triggered.connect(self.__editorCodeStyleCheck)

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
                in ["Python3", "MicroPython"]
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
        if menuName == "Checks" and ericApp().getObject(
            "Project"
        ).getProjectLanguage() in ["Python3", "MicroPython"]:
            self.__projectBrowserMenu = menu
            if self.__projectBrowserAct is None:
                self.__projectBrowserAct = EricAction(
                    self.tr("Check Code Style"),
                    self.tr("&Code Style..."),
                    0,
                    0,
                    self,
                    "",
                )
                self.__projectBrowserAct.setWhatsThis(
                    self.tr(
                        """<b>Check Code Style...</b>"""
                        """<p>This checks Python files for compliance to the"""
                        """ code style conventions given in various PEPs.</p>"""
                    )
                )
                self.__projectBrowserAct.triggered.connect(
                    self.__projectBrowserCodeStyleCheck
                )
            if self.__projectBrowserAct not in menu.actions():
                menu.addAction(self.__projectBrowserAct)

    def __projectCodeStyleCheck(self):
        """
        Private slot used to check the project files for code style.
        """
        from eric7.Plugins.CheckerPlugins.CodeStyleChecker import CodeStyleCheckerDialog

        project = ericApp().getObject("Project")
        project.saveAllScripts()
        ppath = project.getProjectPath()
        files = [
            os.path.join(ppath, file)
            for file in project.getProjectData(dataKey="SOURCES")
            if file.endswith(tuple(Preferences.getPython("Python3Extensions")))
        ]

        self.__projectCodeStyleCheckerDialog = (
            CodeStyleCheckerDialog.CodeStyleCheckerDialog(self)
        )
        self.__projectCodeStyleCheckerDialog.show()
        self.__projectCodeStyleCheckerDialog.prepare(files, project)

    def __projectBrowserCodeStyleCheck(self):
        """
        Private method to handle the code style check context menu action of
        the project sources browser.
        """
        from eric7.Plugins.CheckerPlugins.CodeStyleChecker import CodeStyleCheckerDialog

        browser = ericApp().getObject("ProjectBrowser").getProjectBrowser("sources")
        if browser.getSelectedItemsCount([ProjectBrowserFileItem]) > 1:
            fn = []
            for itm in browser.getSelectedItems([ProjectBrowserFileItem]):
                fn.append(itm.fileName())
            isDir = False
        else:
            itm = browser.model().item(browser.currentIndex())
            try:
                fn = itm.fileName()
                isDir = False
            except AttributeError:
                fn = itm.dirName()
                isDir = True

        self.__projectBrowserCodeStyleCheckerDialog = (
            CodeStyleCheckerDialog.CodeStyleCheckerDialog(self)
        )
        self.__projectBrowserCodeStyleCheckerDialog.show()
        if isDir:
            self.__projectBrowserCodeStyleCheckerDialog.start(fn, save=True)
        else:
            self.__projectBrowserCodeStyleCheckerDialog.start(
                fn, save=True, repeat=True
            )

    def __editorOpened(self, editor):
        """
        Private slot called, when a new editor was opened.

        @param editor reference to the new editor
        @type Editor
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
        @type Editor
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
        @type Editor
        """
        if menuName == "Checks":
            if self.__editorAct not in menu.actions():
                menu.addAction(self.__editorAct)
            self.__editorAct.setEnabled(editor.isPyFile())

    def __editorCodeStyleCheck(self):
        """
        Private slot to handle the code style check context menu action
        of the editors.
        """
        from eric7.Plugins.CheckerPlugins.CodeStyleChecker import CodeStyleCheckerDialog

        editor = ericApp().getObject("ViewManager").activeWindow()
        if (
            editor is not None
            and editor.checkDirty()
            and editor.getFileName() is not None
        ):
            self.__editorCodeStyleCheckerDialog = (
                CodeStyleCheckerDialog.CodeStyleCheckerDialog(self)
            )
            self.__editorCodeStyleCheckerDialog.show()
            self.__editorCodeStyleCheckerDialog.start(
                editor.getFileName(), save=True, repeat=True
            )
