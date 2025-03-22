# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the task properties dialog.
"""

import time

from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets.EricCompleters import EricFileCompleter

from .Task import TaskPriority, TaskType
from .Ui_TaskPropertiesDialog import Ui_TaskPropertiesDialog


class TaskPropertiesDialog(QDialog, Ui_TaskPropertiesDialog):
    """
    Class implementing the task properties dialog.
    """

    def __init__(self, task=None, parent=None, projectOpen=False):
        """
        Constructor

        @param task the task object to be shown
        @type Task
        @param parent the parent widget
        @type QWidget
        @param projectOpen flag indicating status of the project
        @type bool
        """
        super().__init__(parent)
        self.setupUi(self)

        self.filenameCompleter = EricFileCompleter(self.filenameEdit)

        self.typeCombo.addItem(self.tr("Bugfix"), TaskType.FIXME)
        self.typeCombo.addItem(self.tr("Warning"), TaskType.WARNING)
        self.typeCombo.addItem(self.tr("ToDo"), TaskType.TODO)
        self.typeCombo.addItem(self.tr("Note"), TaskType.NOTE)
        self.typeCombo.addItem(self.tr("Test"), TaskType.TEST)
        self.typeCombo.addItem(self.tr("Documentation"), TaskType.DOCU)

        if task is not None:
            self.summaryEdit.setText(task.summary)
            self.descriptionEdit.setText(task.description)
            self.creationLabel.setText(
                time.strftime("%Y-%m-%d, %H:%M:%S", time.localtime(task.created))
            )
            self.priorityCombo.setCurrentIndex(task.priority.value)
            self.projectCheckBox.setChecked(task._isProjectTask)
            self.completedCheckBox.setChecked(task.completed)
            self.filenameEdit.setText(task.filename)
            if task.lineno:
                self.linenoEdit.setText(str(task.lineno))
            index = self.typeCombo.findData(task.taskType)
            self.typeCombo.setCurrentIndex(index)
            self.__setMode(bool(task.filename), projectOpen)
        else:
            self.projectCheckBox.setChecked(projectOpen)
            self.typeCombo.setCurrentIndex(2)  # TaskType.TODO
            self.__setMode(False, projectOpen)

    def __setMode(self, isFileTask, projectOpen):
        """
        Private method to show or hide dialog elements depending on the task
        kind.

        @param isFileTask flag indicating a file task (i.e. extracted task)
        @type bool
        @param projectOpen flag indicating status of the project
        @type bool
        """
        self.__isFileTaskMode = isFileTask
        if self.__isFileTaskMode:
            self.descriptionEdit.hide()
            self.descriptionLabel.hide()
            self.manualTaskFrame.hide()

            msh = self.minimumSizeHint()
            self.resize(max(self.width(), msh.width()), msh.height())
        else:
            self.fileTaskFrame.hide()

        self.summaryEdit.setReadOnly(isFileTask)
        self.projectCheckBox.setEnabled(projectOpen and not isFileTask)

    def isManualTaskMode(self):
        """
        Public method to check, if the dialog is in manual task mode.

        @return flag indicating manual task mode
        @rtype bool
        """
        return not self.__isFileTaskMode

    def setSubTaskMode(self, projectTask):
        """
        Public slot to set the sub-task mode.

        @param projectTask flag indicating a project related task
        @type bool
        """
        self.projectCheckBox.setChecked(projectTask)
        self.projectCheckBox.setEnabled(False)

    def getData(self):
        """
        Public method to retrieve the dialogs data.

        @return tuple of description, priority, type, completion flag,
                project flag and long text
        @rtype tuple of (str, TaskPriority, TaskType, bool, bool, str)
        """
        return (
            self.summaryEdit.text(),
            TaskPriority(self.priorityCombo.currentIndex()),
            TaskType(self.typeCombo.currentData()),
            self.completedCheckBox.isChecked(),
            self.projectCheckBox.isChecked(),
            self.descriptionEdit.toPlainText(),
        )
