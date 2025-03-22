# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to store task data.
"""

import contextlib
import enum
import os
import time

from PyQt6.QtCore import Qt, QUuid
from PyQt6.QtWidgets import QTreeWidgetItem

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache


class TaskType(enum.IntEnum):
    """
    Class defining the task types.
    """

    NONE = 255
    FIXME = 0
    TODO = 1
    WARNING = 2
    NOTE = 3
    TEST = 4
    DOCU = 5


class TaskPriority(enum.IntEnum):
    """
    Class defining the task priorities.
    """

    HIGH = 0
    NORMAL = 1
    LOW = 2


class Task(QTreeWidgetItem):
    """
    Class implementing the task data structure.
    """

    TaskType2IconName = {
        TaskType.FIXME: "taskFixme",  # __NO-TASK__
        TaskType.TODO: "taskTodo",  # __NO-TASK__
        TaskType.WARNING: "taskWarning",  # __NO-TASK__
        TaskType.NOTE: "taskNote",  # __NO-TASK__
        TaskType.TEST: "taskTest",  # __NO-TASK__
        TaskType.DOCU: "taskDocu",  # __NO-TASK__
    }
    TaskType2ColorName = {
        TaskType.FIXME: "TasksFixmeColor",  # __NO-TASK__
        TaskType.TODO: "TasksTodoColor",  # __NO-TASK__
        TaskType.WARNING: "TasksWarningColor",  # __NO-TASK__
        TaskType.NOTE: "TasksNoteColor",  # __NO-TASK__
        TaskType.TEST: "TasksTestColor",  # __NO-TASK__
        TaskType.DOCU: "TasksDocuColor",  # __NO-TASK__
    }
    TaskType2MarkersName = {
        TaskType.FIXME: "TasksFixmeMarkers",  # __NO-TASK__
        TaskType.TODO: "TasksTodoMarkers",  # __NO-TASK__
        TaskType.WARNING: "TasksWarningMarkers",  # __NO-TASK__
        TaskType.NOTE: "TasksNoteMarkers",  # __NO-TASK__
        TaskType.TEST: "TasksTestMarkers",  # __NO-TASK__
        TaskType.DOCU: "TasksDocuMarkers",  # __NO-TASK__
    }

    def __init__(
        self,
        summary,
        priority=TaskPriority.NORMAL,
        filename="",
        lineno=0,
        completed=False,
        _time=0,
        isProjectTask=False,
        taskType=TaskType.TODO,
        project=None,
        description="",
        uid="",
        parentUid="",
    ):
        """
        Constructor

        @param summary summary text of the task
        @type str
        @param priority priority of the task
        @type TaskPriority
        @param filename filename containing the task
        @type str
        @param lineno line number containing the task
        @type int
        @param completed flag indicating completion status
        @type bool
        @param _time creation time of the task (if 0 use current time)
        @type float
        @param isProjectTask flag indicating a task related to the current
            project
        @type bool
        @param taskType type of the task
        @type TaskType
        @param project reference to the project object
        @type Project
        @param description explanatory text of the task
        @type str
        @param uid unique id of the task
        @type str
        @param parentUid unique id of the parent task
        @type str
        """
        super().__init__()

        self.summary = summary
        self.description = description
        self.filename = filename
        self.lineno = lineno
        self.completed = completed
        self.created = _time and _time or time.time()
        self._isProjectTask = isProjectTask
        self.project = project
        if uid:
            self.uid = uid
        else:
            self.uid = QUuid.createUuid().toString()
        self.parentUid = parentUid

        if isProjectTask:
            self.filename = self.project.getRelativePath(self.filename)

        self.setData(0, Qt.ItemDataRole.DisplayRole, "")
        self.setData(1, Qt.ItemDataRole.DisplayRole, "")
        self.setData(2, Qt.ItemDataRole.DisplayRole, self.summary)
        self.setData(3, Qt.ItemDataRole.DisplayRole, self.filename)
        self.setData(4, Qt.ItemDataRole.DisplayRole, self.lineno or "")

        if self.completed:
            self.setIcon(0, EricPixmapCache.getIcon("taskCompleted"))
            strikeOut = True
        else:
            self.setIcon(0, EricPixmapCache.getIcon("empty"))
            strikeOut = False
        for column in range(2, 5):
            f = self.font(column)
            f.setStrikeOut(strikeOut)
            self.setFont(column, f)

        self.setPriority(priority)

        self.setTaskType(taskType)
        self.setTextAlignment(4, Qt.AlignmentFlag.AlignRight)

    def colorizeTask(self):
        """
        Public slot to set the colors of the task item.
        """
        boldFont = self.font(0)
        boldFont.setBold(True)
        nonBoldFont = self.font(0)
        nonBoldFont.setBold(False)
        for col in range(5):
            with contextlib.suppress(KeyError):
                self.setBackground(
                    col, Preferences.getTasks(Task.TaskType2ColorName[self.taskType])
                )

            if self._isProjectTask:
                self.setFont(col, boldFont)
            else:
                self.setFont(col, nonBoldFont)

    def setSummary(self, summary):
        """
        Public slot to update the description.

        @param summary summary text of the task
        @type str
        """
        self.summary = summary
        self.setText(2, self.summary)

    def setDescription(self, description):
        """
        Public slot to update the description field.

        @param description descriptive text of the task
        @type str
        """
        self.description = description

    def setPriority(self, priority):
        """
        Public slot to update the priority.

        @param priority priority of the task
        @type TaskPriority
        """
        self.priority = priority

        if self.priority == TaskPriority.NORMAL:
            self.setIcon(1, EricPixmapCache.getIcon("empty"))
        elif self.priority == TaskPriority.HIGH:
            self.setIcon(1, EricPixmapCache.getIcon("taskPrioHigh"))
        elif self.priority == TaskPriority.LOW:
            self.setIcon(1, EricPixmapCache.getIcon("taskPrioLow"))
        else:
            self.setIcon(1, EricPixmapCache.getIcon("empty"))

    def setTaskType(self, taskType):
        """
        Public method to update the task type.

        @param taskType type of the task
        @type TaskType
        """
        self.taskType = taskType

        try:
            self.setIcon(
                2, EricPixmapCache.getIcon(Task.TaskType2IconName[self.taskType])
            )
        except KeyError:
            self.setIcon(2, EricPixmapCache.getIcon("empty"))

        self.colorizeTask()

    def setCompleted(self, completed):
        """
        Public slot to update the completed flag.

        @param completed flag indicating completion status
        @type bool
        """
        self.completed = completed
        if self.completed:
            self.setIcon(0, EricPixmapCache.getIcon("taskCompleted"))
            strikeOut = True
        else:
            self.setIcon(0, EricPixmapCache.getIcon("empty"))
            strikeOut = False
        for column in range(2, 5):
            f = self.font(column)
            f.setStrikeOut(strikeOut)
            self.setFont(column, f)

        # set the completion status for all children
        for index in range(self.childCount()):
            self.child(index).setCompleted(completed)

    def isCompleted(self):
        """
        Public slot to return the completion status.

        @return flag indicating the completion status
        @rtype bool
        """
        return self.completed

    def getFilename(self):
        """
        Public method to retrieve the task's filename.

        @return filename
        @rtype str
        """
        if self._isProjectTask and self.filename:
            return os.path.join(self.project.getProjectPath(), self.filename)
        else:
            return self.filename

    def isFileTask(self):
        """
        Public slot to get an indication, if this task is related to a file.

        @return flag indicating a file task
        @rtype bool
        """
        return self.filename != ""

    def getLineno(self):
        """
        Public method to retrieve the task's linenumber.

        @return linenumber
        @rtype int
        """
        return self.lineno

    def getUuid(self):
        """
        Public method to get the task's uid.

        @return uid
        @rtype str
        """
        return self.uid

    def getParentUuid(self):
        """
        Public method to get the parent task's uid.

        @return parent uid
        @rtype str
        """
        return self.parentUid

    def setProjectTask(self, pt):
        """
        Public method to set the project relation flag.

        @param pt flag indicating a project task
        @type bool
        """
        self._isProjectTask = pt
        self.colorizeTask()

    def isProjectTask(self):
        """
        Public slot to return the project relation status.

        @return flag indicating the project relation status
        @rtype bool
        """
        return self._isProjectTask

    def isProjectFileTask(self):
        """
        Public slot to get an indication, if this task is related to a
        project file.

        @return flag indicating a project file task
        @rtype bool
        """
        return self._isProjectTask and self.filename != ""

    def toDict(self):
        """
        Public method to convert the task data to a dictionary.

        @return dictionary containing the task data
        @rtype dict
        """
        return {
            "summary": self.summary.strip(),
            "description": self.description.strip(),
            "priority": self.priority.value,
            "lineno": self.lineno,
            "completed": self.completed,
            "created": self.created,
            "type": self.taskType.value,
            "uid": self.uid,
            "parent_uid": self.parentUid,
            "expanded": self.isExpanded(),
            "filename": self.getFilename(),
        }
