# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Tasks configuration page.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QColor

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_TasksPage import Ui_TasksPage


class TasksPage(ConfigurationPageBase, Ui_TasksPage):
    """
    Class implementing the Tasks configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("TasksPage")

        self.colourChanged.connect(self.__colorChanged)

        # set initial values
        self.tasksMarkerFixmeEdit.setText(Preferences.getTasks("TasksFixmeMarkers"))
        self.tasksMarkerWarningEdit.setText(Preferences.getTasks("TasksWarningMarkers"))
        self.tasksMarkerTodoEdit.setText(Preferences.getTasks("TasksTodoMarkers"))
        self.tasksMarkerNoteEdit.setText(Preferences.getTasks("TasksNoteMarkers"))
        self.tasksMarkerTestEdit.setText(Preferences.getTasks("TasksTestMarkers"))
        self.tasksMarkerDocuEdit.setText(Preferences.getTasks("TasksDocuMarkers"))

        self.initColour(
            "TasksFixmeColor", self.tasksFixmeColourButton, Preferences.getTasks
        )
        self.initColour(
            "TasksWarningColor", self.tasksWarningColourButton, Preferences.getTasks
        )
        self.initColour(
            "TasksTodoColor", self.tasksTodoColourButton, Preferences.getTasks
        )
        self.initColour(
            "TasksNoteColor", self.tasksNoteColourButton, Preferences.getTasks
        )
        self.initColour(
            "TasksTestColor", self.tasksTestColourButton, Preferences.getTasks
        )
        self.initColour(
            "TasksDocuColor", self.tasksDocuColourButton, Preferences.getTasks
        )

        self.clearCheckBox.setChecked(Preferences.getTasks("ClearOnFileClose"))

    def save(self):
        """
        Public slot to save the Tasks configuration.
        """
        Preferences.setTasks("TasksFixmeMarkers", self.tasksMarkerFixmeEdit.text())
        Preferences.setTasks("TasksWarningMarkers", self.tasksMarkerWarningEdit.text())
        Preferences.setTasks("TasksTodoMarkers", self.tasksMarkerTodoEdit.text())
        Preferences.setTasks("TasksNoteMarkers", self.tasksMarkerNoteEdit.text())
        Preferences.setTasks("TasksTestMarkers", self.tasksMarkerTestEdit.text())
        Preferences.setTasks("TasksDocuMarkers", self.tasksMarkerDocuEdit.text())
        Preferences.setTasks("ClearOnFileClose", self.clearCheckBox.isChecked())

        self.saveColours(Preferences.setTasks)

    @pyqtSlot(str, QColor)
    def __colorChanged(self, colorKey, color):
        """
        Private slot handling the selection of a color.

        @param colorKey key of the color entry
        @type str
        @param color selected color
        @type QColor
        """
        if colorKey == "TasksFixmeColor":
            self.tasksMarkerFixmeEdit.setStyleSheet(f"background-color: {color.name()}")
        elif colorKey == "TasksWarningColor":
            self.tasksMarkerWarningEdit.setStyleSheet(
                f"background-color: {color.name()}"
            )
        elif colorKey == "TasksTodoColor":
            self.tasksMarkerTodoEdit.setStyleSheet(f"background-color: {color.name()}")
        elif colorKey == "TasksNoteColor":
            self.tasksMarkerNoteEdit.setStyleSheet(f"background-color: {color.name()}")
        elif colorKey == "TasksTestColor":
            self.tasksMarkerTestEdit.setStyleSheet(f"background-color: {color.name()}")
        elif colorKey == "TasksDocuColor":
            self.tasksMarkerDocuEdit.setStyleSheet(f"background-color: {color.name()}")


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = TasksPage()
    return page
