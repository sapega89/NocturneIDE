# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a previewer widget for Qt style sheet files.
"""

import os

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QHeaderView, QLabel, QListWidgetItem, QMenu, QWidget

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.Globals import getConfig
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_PreviewerQSS import Ui_PreviewerQSS


class PreviewerQSS(QWidget, Ui_PreviewerQSS):
    """
    Class implementing a previewer widget for Qt style sheet files.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        styleIconsPath = ericApp().getStyleIconsPath()
        self.styleIconsPathPicker.setMode(EricPathPickerModes.DIRECTORY_SHOW_FILES_MODE)
        self.styleIconsPathPicker.setDefaultDirectory(styleIconsPath)

        self.__lastEditor = None

        # menu for the tool buttons
        self.__toolButtonMenu_1 = QMenu(self)
        self.__toolButtonMenu_1.addAction(self.tr("Action 1.1"))
        self.__toolButtonMenu_1.addSeparator()
        self.__toolButtonMenu_1.addAction(self.tr("Action 2.1"))
        self.toolButton_1.setMenu(self.__toolButtonMenu_1)

        self.__toolButtonMenu_2 = QMenu(self)
        self.__toolButtonMenu_2.addAction(self.tr("Action 1.2"))
        self.__toolButtonMenu_2.addSeparator()
        self.__toolButtonMenu_2.addAction(self.tr("Action 2.2"))
        self.toolButton_2.setMenu(self.__toolButtonMenu_2)

        self.__toolButtonMenu_3 = QMenu(self)
        self.__toolButtonMenu_3.addAction(self.tr("Action 1.3"))
        self.__toolButtonMenu_3.addSeparator()
        self.__toolButtonMenu_3.addAction(self.tr("Action 2.3"))
        self.toolButton_3.setMenu(self.__toolButtonMenu_3)

        # combo boxes
        for combo in (self.readOnlyComboBox, self.editableComboBox):
            combo.insertSeparator(combo.count())
            combo.addItem("4")

        # a MDI window
        self.__mdi = self.mdiArea.addSubWindow(QLabel(self.tr("MDI")))
        self.__mdi.resize(160, 80)

        # tree and table widgets
        self.tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.tree.topLevelItem(0).setExpanded(True)

        # icon list widget
        for iconName, labelText in (
            ("filePython", self.tr("Python")),
            ("fileRuby", self.tr("Ruby")),
            ("fileJavascript", self.tr("JavaScript")),
        ):
            self.iconsListWidget.addItem(
                QListWidgetItem(EricPixmapCache.getIcon(iconName), labelText)
            )

    @pyqtSlot(str)
    def on_styleIconsPathPicker_textChanged(self, _txt):
        """
        Private slot handling a change of the style icons path.

        @param _txt name of the style icons directory (unused)
        @type str
        """
        self.processEditor(self.__lastEditor)

    def processEditor(self, editor=None):
        """
        Public slot to process an editor's text.

        @param editor editor to be processed
        @type Editor
        """
        self.__lastEditor = editor

        if editor is not None:
            fn = editor.getFileName()

            if fn:
                extension = os.path.normcase(os.path.splitext(fn)[1][1:])
            else:
                extension = ""
            if extension in Preferences.getEditor("PreviewQssFileNameExtensions"):
                styleSheet = editor.text()
                if styleSheet:
                    styleIconsPath = self.styleIconsPathPicker.text()
                    if not styleIconsPath:
                        styleIconsPath = Preferences.getUI("StyleIconsPath")
                        if not styleIconsPath:
                            # default ist the 'StyleIcons' subdirectory of the
                            # icons directory
                            styleIconsPath = os.path.join(
                                getConfig("ericIconDir"), "StyleIcons"
                            )

                    styleIconsPath = FileSystemUtilities.fromNativeSeparators(
                        styleIconsPath
                    )
                    styleSheet = styleSheet.replace("${path}", styleIconsPath)
                    self.scrollAreaWidgetContents.setStyleSheet(styleSheet)
                else:
                    self.scrollAreaWidgetContents.setStyleSheet("")
                self.toolButton_1.menu().setStyleSheet(
                    self.scrollAreaWidgetContents.styleSheet()
                )
                self.toolButton_2.menu().setStyleSheet(
                    self.scrollAreaWidgetContents.styleSheet()
                )
                self.toolButton_3.menu().setStyleSheet(
                    self.scrollAreaWidgetContents.styleSheet()
                )

    @pyqtSlot(int)
    def on_checkBox_stateChanged(self, state):
        """
        Private slot to synchronize the checkbox state.

        @param state state of the enabled check box
        @type int
        """
        self.disabledCheckBox.setCheckState(Qt.CheckState(state))
