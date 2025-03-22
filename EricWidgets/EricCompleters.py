# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing various kinds of completers.
"""

import os

from PyQt6.QtCore import QDir, QStringListModel, Qt
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QCompleter

from eric7.SystemUtilities import OSUtilities


class EricFileCompleter(QCompleter):
    """
    Class implementing a completer for file names.
    """

    def __init__(
        self,
        parent=None,
        completionMode=QCompleter.CompletionMode.PopupCompletion,
        showHidden=False,
    ):
        """
        Constructor

        @param parent parent widget of the completer
        @type QWidget
        @param completionMode completion mode of the
            completer
        @type QCompleter.CompletionMode
        @param showHidden flag indicating to show hidden entries as well
        @type bool
        """
        super().__init__(parent)
        self.__model = QFileSystemModel(self)
        if showHidden:
            self.__model.setFilter(
                QDir.Filter.Dirs
                | QDir.Filter.Files
                | QDir.Filter.Drives
                | QDir.Filter.AllDirs
                | QDir.Filter.Hidden
            )
        else:
            self.__model.setFilter(
                QDir.Filter.Dirs
                | QDir.Filter.Files
                | QDir.Filter.Drives
                | QDir.Filter.AllDirs
            )
        self.__model.setRootPath("")
        self.setModel(self.__model)
        self.setCompletionMode(completionMode)
        if OSUtilities.isWindowsPlatform():
            self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        else:
            self.setCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        if parent:
            parent.setCompleter(self)

    def setRootPath(self, path):
        """
        Public method to set the root path of the model.

        @param path root path for the model
        @type str
        """
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        self.__model.setRootPath(path)

    def rootPath(self):
        """
        Public method to get the root path of the model.

        @return root path of the model
        @rtype str
        """
        return self.__model.rootPath()


class EricDirCompleter(QCompleter):
    """
    Class implementing a completer for directory names.
    """

    def __init__(
        self,
        parent=None,
        completionMode=QCompleter.CompletionMode.PopupCompletion,
        showHidden=False,
    ):
        """
        Constructor

        @param parent parent widget of the completer
        @type QWidget
        @param completionMode completion mode of the
            completer
        @type QCompleter.CompletionMode
        @param showHidden flag indicating to show hidden entries as well
        @type bool
        """
        super().__init__(parent)
        self.__model = QFileSystemModel(self)
        if showHidden:
            self.__model.setFilter(
                QDir.Filter.Drives | QDir.Filter.AllDirs | QDir.Filter.Hidden
            )
        else:
            self.__model.setFilter(QDir.Filter.Drives | QDir.Filter.AllDirs)
        self.__model.setRootPath("")
        self.setModel(self.__model)
        self.setCompletionMode(completionMode)
        if OSUtilities.isWindowsPlatform():
            self.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        else:
            self.setCaseSensitivity(Qt.CaseSensitivity.CaseSensitive)
        if parent:
            parent.setCompleter(self)

    def setRootPath(self, path):
        """
        Public method to set the root path of the model.

        @param path root path for the model
        @type str
        """
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        self.__model.setRootPath(path)

    def rootPath(self):
        """
        Public method to get the root path of the model.

        @return root path of the model
        @rtype str
        """
        return self.__model.rootPath()


class EricStringListCompleter(QCompleter):
    """
    Class implementing a completer for string lists.
    """

    def __init__(
        self,
        parent=None,
        strings=None,
        completionMode=QCompleter.CompletionMode.PopupCompletion,
    ):
        """
        Constructor

        @param parent parent widget of the completer
        @type QWidget
        @param strings list of string to load into the completer
        @type list of str
        @param completionMode completion mode of the
            completer
        @type QCompleter.CompletionMode
        """
        super().__init__(parent)
        self.__model = QStringListModel([] if strings is None else strings[:], parent)
        self.setModel(self.__model)
        self.setCompletionMode(completionMode)
        if parent:
            parent.setCompleter(self)
