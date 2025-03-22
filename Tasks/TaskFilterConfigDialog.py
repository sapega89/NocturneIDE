# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the task filter configuration dialog.
"""

from PyQt6.QtWidgets import QDialog

from .Task import TaskPriority, TaskType
from .Ui_TaskFilterConfigDialog import Ui_TaskFilterConfigDialog


class TaskFilterConfigDialog(QDialog, Ui_TaskFilterConfigDialog):
    """
    Class implementing the task filter configuration dialog.
    """

    def __init__(self, taskFilter, parent=None):
        """
        Constructor

        @param taskFilter the task filter object to be configured
        @type TaskFilter
        @param parent the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.typeCombo.addItem("", TaskType.NONE)
        self.typeCombo.addItem(self.tr("Bugfix"), TaskType.FIXME)
        self.typeCombo.addItem(self.tr("Warning"), TaskType.WARNING)
        self.typeCombo.addItem(self.tr("ToDo"), TaskType.TODO)
        self.typeCombo.addItem(self.tr("Note"), TaskType.NOTE)
        self.typeCombo.addItem(self.tr("Test"), TaskType.TEST)
        self.typeCombo.addItem(self.tr("Documentation"), TaskType.DOCU)

        if taskFilter.summaryFilter is None or not taskFilter.summaryFilter.pattern:
            self.summaryGroup.setChecked(False)
            self.summaryEdit.clear()
        else:
            self.summaryGroup.setChecked(True)
            self.summaryEdit.setText(taskFilter.summaryFilter.pattern)

        if not taskFilter.filenameFilter:
            self.filenameGroup.setChecked(False)
            self.filenameEdit.clear()
        else:
            self.filenameGroup.setChecked(True)
            self.filenameEdit.setText(taskFilter.filenameFilter)

        if taskFilter.typeFilter == TaskType.NONE:
            self.typeGroup.setChecked(False)
            self.typeCombo.setCurrentIndex(0)
        else:
            self.typeGroup.setChecked(True)
            self.typeCombo.setCurrentIndex(
                self.typeCombo.findData(taskFilter.typeFilter)
            )

        if taskFilter.scopeFilter is None:
            self.scopeGroup.setChecked(False)
            self.globalRadioButton.setChecked(True)
        else:
            self.scopeGroup.setChecked(True)
            if taskFilter.scopeFilter:
                self.projectRadioButton.setChecked(True)
            else:
                self.globalRadioButton.setChecked(True)

        if taskFilter.statusFilter is None:
            self.statusGroup.setChecked(False)
            self.uncompletedRadioButton.setChecked(True)
        else:
            self.statusGroup.setChecked(True)
            if taskFilter.statusFilter:
                self.completedRadioButton.setChecked(True)
            else:
                self.uncompletedRadioButton.setChecked(True)

        if taskFilter.prioritiesFilter is None:
            self.priorityGroup.setChecked(False)
            self.priorityHighCheckBox.setChecked(False)
            self.priorityNormalCheckBox.setChecked(False)
            self.priorityLowCheckBox.setChecked(False)
        else:
            self.priorityGroup.setChecked(True)
            self.priorityHighCheckBox.setChecked(
                TaskPriority.HIGH in taskFilter.prioritiesFilter
            )
            self.priorityNormalCheckBox.setChecked(
                TaskPriority.NORMAL in taskFilter.prioritiesFilter
            )
            self.priorityLowCheckBox.setChecked(
                TaskPriority.LOW in taskFilter.prioritiesFilter
            )

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def configureTaskFilter(self, taskFilter):
        """
        Public method to set the parameters of the task filter object.

        @param taskFilter task filter object to be configured
        @type TaskFilter
        """
        if self.summaryGroup.isChecked():
            taskFilter.setSummaryFilter(self.summaryEdit.text())
        else:
            taskFilter.setSummaryFilter(None)

        if self.filenameGroup.isChecked():
            taskFilter.setFileNameFilter(self.filenameEdit.text())
        else:
            taskFilter.setFileNameFilter("")

        if self.typeGroup.isChecked():
            taskFilter.setTypeFilter(
                TaskType(self.typeCombo.itemData(self.typeCombo.currentIndex()))
            )
        else:
            taskFilter.setTypeFilter(TaskType.NONE)

        if self.scopeGroup.isChecked():
            if self.projectRadioButton.isChecked():
                taskFilter.setScopeFilter(True)
            else:
                taskFilter.setScopeFilter(False)
        else:
            taskFilter.setScopeFilter(None)

        if self.statusGroup.isChecked():
            if self.completedRadioButton.isChecked():
                taskFilter.setStatusFilter(True)
            else:
                taskFilter.setStatusFilter(False)
        else:
            taskFilter.setStatusFilter(None)

        if self.priorityGroup.isChecked():
            priorities = []
            if self.priorityHighCheckBox.isChecked():
                priorities.append(TaskPriority.HIGH)
            if self.priorityNormalCheckBox.isChecked():
                priorities.append(TaskPriority.NORMAL)
            if self.priorityLowCheckBox.isChecked():
                priorities.append(TaskPriority.LOW)
            taskFilter.setPrioritiesFilter(priorities)
        else:
            taskFilter.setPrioritiesFilter(None)
