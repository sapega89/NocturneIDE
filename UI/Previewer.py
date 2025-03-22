# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a previewer widget for HTML, Markdown and ReST files.
"""

import os

from PyQt6.QtCore import QTimer, pyqtSlot
from PyQt6.QtWidgets import QStackedWidget

from eric7 import Preferences


class Previewer(QStackedWidget):
    """
    Class implementing a previewer widget containing a stack of
    specialized previewers.
    """

    def __init__(self, viewmanager, parent=None):
        """
        Constructor

        @param viewmanager reference to the viewmanager object
        @type ViewManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__vm = viewmanager

        self.__firstShow = True

        self.__htmlPreviewer = None
        self.__qssPreviewer = None

        # Don't update too often because the UI might become sluggish
        self.__typingTimer = QTimer()
        self.__typingTimer.setInterval(
            Preferences.getEditor("PreviewRefreshWaitTimer")
        )  # default 500ms
        self.__typingTimer.timeout.connect(self.__processEditor)

        self.__vm.editorChangedEd.connect(self.__editorChanged)
        self.__vm.editorLanguageChanged.connect(self.__editorLanguageChanged)
        self.__vm.editorTextChanged.connect(self.__editorTextChanged)

        self.__vm.previewStateChanged.connect(self.__previewStateChanged)

        self.hide()

    def setSplitter(self, splitter):
        """
        Public method to set the splitter.

        @param splitter reference to the embedding splitter
        @type QSplitter
        """
        self.__splitter = splitter
        self.__splitter.splitterMoved.connect(self.__splitterMoved)

    @pyqtSlot()
    def preferencesChanged(self):
        """
        Public slot handling a change of preferences.
        """
        self.__typingTimer.setInterval(Preferences.getEditor("PreviewRefreshWaitTimer"))

    def show(self):
        """
        Public method to show the preview widget.
        """
        super().show()
        if self.__firstShow:
            self.__splitter.restoreState(Preferences.getUI("PreviewSplitterState"))
            self.__firstShow = False
        self.__typingTimer.start()

    def hide(self):
        """
        Public method to hide the preview widget.
        """
        super().hide()
        self.__typingTimer.stop()

    def shutdown(self):
        """
        Public method to perform shutdown actions.
        """
        self.__typingTimer.stop()
        self.__htmlPreviewer and self.__htmlPreviewer.shutdown()

    def __splitterMoved(self):
        """
        Private slot to handle the movement of the embedding splitter's handle.
        """
        state = self.__splitter.saveState()
        Preferences.setUI("PreviewSplitterState", state)

    def __editorChanged(self, editor):
        """
        Private slot to handle a change of the current editor.

        @param editor reference to the editor
        @type Editor
        """
        if editor is None:
            self.hide()
            return

        if Preferences.getUI("ShowFilePreview") and self.__isPreviewable(editor):
            self.show()
            self.__processEditor()
        else:
            self.hide()

    def __editorLanguageChanged(self, editor):
        """
        Private slot to handle a change of the current editor's language.

        @param editor reference to the editor
        @type Editor
        """
        self.__editorChanged(editor)

    def __editorTextChanged(self, _editor):
        """
        Private slot to handle changes of an editor's text.

        @param _editor reference to the editor (unused)
        @type Editor
        """
        if self.isVisible():
            self.__typingTimer.stop()
            self.__typingTimer.start()

    def __previewStateChanged(self, on):
        """
        Private slot to toggle the display of the preview.

        @param on flag indicating to show a preview
        @type bool
        """
        editor = self.__vm.activeWindow()
        if on and editor and self.__isPreviewable(editor):
            self.show()
        else:
            self.hide()

    def __isPreviewable(self, editor):
        """
        Private method to check, if a preview can be shown for the given
        editor.

        @param editor reference to an editor
        @type Editor
        @return flag indicating if a preview can be shown
        @rtype bool
        """
        if editor:
            if bool(editor.getFileName()):
                extension = os.path.normcase(
                    os.path.splitext(editor.getFileName())[1][1:]
                )
                return extension in (
                    Preferences.getEditor("PreviewHtmlFileNameExtensions")
                    + Preferences.getEditor("PreviewMarkdownFileNameExtensions")
                    + Preferences.getEditor("PreviewRestFileNameExtensions")
                    + Preferences.getEditor("PreviewQssFileNameExtensions")
                )
            elif editor.getLanguage().lower() in [
                "html",
                "markdown",
                "restructuredtext",
                "qss",
            ]:
                return True

        return False

    def __processEditor(self):
        """
        Private slot to schedule the processing of the current editor's text.
        """
        self.__typingTimer.stop()

        editor = self.__vm.activeWindow()
        if editor is not None:
            fn = editor.getFileName()

            if fn:
                extension = os.path.normcase(os.path.splitext(fn)[1][1:])
            else:
                extension = ""
            if (
                extension in Preferences.getEditor("PreviewHtmlFileNameExtensions")
                or editor.getLanguage().lower() == "html"
            ):
                language = "HTML"
            elif (
                extension in Preferences.getEditor("PreviewMarkdownFileNameExtensions")
                or editor.getLanguage().lower() == "markdown"
            ):
                language = "Markdown"
            elif (
                extension in Preferences.getEditor("PreviewRestFileNameExtensions")
                or editor.getLanguage().lower() == "restructuredtext"
            ):
                language = "ReST"
            elif (
                extension in Preferences.getEditor("PreviewQssFileNameExtensions")
                or editor.getLanguage().lower() == "qss"
            ):
                language = "QSS"
            else:
                language = ""

            if language in ["HTML", "Markdown", "ReST"]:
                if self.__htmlPreviewer is None:
                    from .Previewers.PreviewerHTML import (  # __IGNORE_WARNING_I101__
                        PreviewerHTML,
                    )

                    self.__htmlPreviewer = PreviewerHTML()
                    self.addWidget(self.__htmlPreviewer)
                self.setCurrentWidget(self.__htmlPreviewer)
                self.__htmlPreviewer.processEditor(editor)
            elif language == "QSS":
                if self.__qssPreviewer is None:
                    from .Previewers.PreviewerQSS import (  # __IGNORE_WARNING_I101__
                        PreviewerQSS,
                    )

                    self.__qssPreviewer = PreviewerQSS()
                    self.addWidget(self.__qssPreviewer)
                self.setCurrentWidget(self.__qssPreviewer)
                self.__qssPreviewer.processEditor(editor)
