# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Jedi assistant plug-in.
"""

import contextlib

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMenu

from eric7 import Preferences
from eric7.SystemUtilities import FileSystemUtilities

from .JediServer import JediServer


class AssistantJedi(QObject):
    """
    Class implementing the Jedi assistant interface.
    """

    def __init__(self, ui, viewManager, project):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        @param viewManager reference to the viewmanager object
        @type ViewManager
        @param project reference to the project object
        @type Project
        """
        super().__init__(ui)
        self.__ui = ui
        self.__vm = viewManager

        self.__jediServer = None
        self.__editors = []
        self.__menuActions = {}

        self.__jediServer = JediServer(self.__vm, project, self.__ui)
        self.__jediServer.activate()

        self.__ui.preferencesChanged.connect(self.__preferencesChanged)

        self.__initRefactoringMenu()

        self.__vm.editorOpenedEd.connect(self.__editorOpened)
        self.__vm.editorClosedEd.connect(self.__editorClosed)

    @pyqtSlot()
    def __preferencesChanged(self):
        """
        Private slot handling changes of the Disassembly viewer settings.
        """
        for editor in self.__editors:
            self.__disconnectMouseClickHandler(editor)
            if not FileSystemUtilities.isRemoteFileName(editor.getFileName()):
                self.__connectMouseClickHandler(editor)

    def __determineLanguage(self):
        """
        Private method to determine the valid language strings.

        @return list of valid language strings
        @rtype list of str
        """
        return [
            "Python3",
            "MicroPython",
            "Pygments|Python",
            "Pygments|Python 2.x",
            "Cython",
            "Pygments|Cython",
        ]

    def __editorOpened(self, editor):
        """
        Private slot called, when a new editor was opened.

        @param editor reference to the new editor
        @type Editor
        """
        if not FileSystemUtilities.isRemoteFileName(editor.getFileName()):
            languages = self.__determineLanguage()

            if editor.getLanguage() in languages:
                self.__connectEditor(editor)

            editor.languageChanged.connect(self.__editorLanguageChanged)
            self.__editors.append(editor)

    def __editorClosed(self, editor):
        """
        Private slot called, when an editor was closed.

        @param editor reference to the editor
        @type Editor
        """
        if editor in self.__editors:
            editor.languageChanged.disconnect(self.__editorLanguageChanged)
            self.__disconnectEditor(editor)
            self.__editors.remove(editor)

    def __editorLanguageChanged(self, language):
        """
        Private slot to handle the language change of an editor.

        @param language programming language of the editor
        @type str
        """
        editor = self.sender()
        languages = self.__determineLanguage()

        self.__disconnectEditor(editor)
        if language in languages:
            self.__connectEditor(editor)

    def __connectEditor(self, editor):
        """
        Private method to connect an editor.

        @param editor reference to the editor
        @type Editor
        """
        if not FileSystemUtilities.isRemoteFileName(editor.getFileName()):
            self.__setAutoCompletionHook(editor)
            self.__setCalltipsHook(editor)

            self.__connectMouseClickHandler(editor)

            editor.registerMouseHoverHelpFunction(self.__jediServer.hoverHelp)

            menu = editor.getMenu("Main")
            if menu is not None:
                checkAction = editor.getMenu("Checks").menuAction()
                act = menu.insertMenu(checkAction, self.__menu)
                self.__menuActions[editor] = [act]
            editor.showMenu.connect(self.__editorShowMenu)

    def __disconnectEditor(self, editor):
        """
        Private method to disconnect an editor.

        @param editor reference to the editor
        @type Editor
        """
        self.__unsetAutoCompletionHook(editor)
        self.__unsetCalltipsHook(editor)

        self.__disconnectMouseClickHandler(editor)

        editor.unregisterMouseHoverHelpFunction(self.__jediServer.hoverHelp)
        self.__jediServer.forgetEditor(editor)

        with contextlib.suppress(TypeError):
            editor.showMenu.disconnect(self.__editorShowMenu)
        menu = editor.getMenu("Main")
        if menu is not None and editor in self.__menuActions:
            for act in self.__menuActions[editor]:
                with contextlib.suppress(RuntimeError):
                    menu.removeAction(act)
            del self.__menuActions[editor]

    def __connectMouseClickHandler(self, editor):
        """
        Private method to connect the mouse click handler to an editor.

        @param editor reference to the editor
        @type Editor
        """
        if Preferences.getJedi(
            "MouseClickGotoButton"
        ) and not FileSystemUtilities.isRemoteFileName(editor.getFileName()):
            editor.setMouseClickHandler(
                "jedi",
                Preferences.getJedi("MouseClickGotoModifiers"),
                Preferences.getJedi("MouseClickGotoButton"),
                self.__jediServer.gotoDefinition,
            )

    def __disconnectMouseClickHandler(self, editor):
        """
        Private method to disconnect the mouse click handler from an editor.

        @param editor reference to the editor
        @type Editor
        """
        editor.removeMouseClickHandlers("jedi")

    def __setAutoCompletionHook(self, editor):
        """
        Private method to set the autocompletion hook.

        @param editor reference to the editor
        @type Editor
        """
        editor.addCompletionListHook("jedi", self.__jediServer.requestCompletions, True)

    def __unsetAutoCompletionHook(self, editor):
        """
        Private method to unset the autocompletion hook.

        @param editor reference to the editor
        @type Editor
        """
        editor.removeCompletionListHook("jedi")

    def __setCalltipsHook(self, editor):
        """
        Private method to set the calltip hook.

        @param editor reference to the editor
        @type Editor
        """
        editor.addCallTipHook("jedi", self.__jediServer.getCallTips)

    def __unsetCalltipsHook(self, editor):
        """
        Private method to unset the calltip hook.

        @param editor reference to the editor
        @type Editor
        """
        editor.removeCallTipHook("jedi")

    def __initRefactoringMenu(self):
        """
        Private method to initialize the Refactoring menu.
        """
        self.__menu = QMenu(self.tr("Refactoring"))
        self.__menu.addAction(
            self.tr("Rename Variable"), self.__jediServer.refactoringRenameVariable
        )
        self.__menu.addAction(
            self.tr("Extract Variable"), self.__jediServer.refactoringExtractNewVariable
        )
        self.__menu.addAction(
            self.tr("Inline Variable"), self.__jediServer.refactoringInlineVariable
        )
        self.__menu.addSeparator()
        self.__menu.addAction(
            self.tr("Extract Function"), self.__jediServer.refactoringExtractFunction
        )

    def __editorShowMenu(self, menuName, _menu, editor):
        """
        Private slot called, when the the editor context menu or a submenu is
        about to be shown.

        @param menuName name of the menu to be shown
        @type str
        @param _menu reference to the menu (unused)
        @type QMenu
        @param editor reference to the editor
        @type Editor
        """
        if menuName == "Main":
            self.__menu.setEnabled(
                not FileSystemUtilities.isRemoteFileName(editor.getFileName())
                and editor.hasSelectedText()
            )
