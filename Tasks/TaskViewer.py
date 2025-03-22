# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a task viewer and associated classes.

Tasks can be defined manually or automatically. Automatically
generated tasks are derived from a comment with a special
introductory text. This text is configurable.
"""

import fnmatch
import os
import threading
import time

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
)

from eric7 import Preferences, Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog
from eric7.Utilities.AutoSaver import AutoSaver

from .Task import Task, TaskPriority, TaskType
from .TaskFilter import TaskFilter
from .TaskPropertiesDialog import TaskPropertiesDialog


class TaskViewer(QTreeWidget):
    """
    Class implementing the task viewer.

    @signal displayFile(str, int) emitted to go to a file task
    """

    displayFile = pyqtSignal(str, int)

    def __init__(self, parent, project):
        """
        Constructor

        @param parent the parent
        @type QWidget
        @param project reference to the project object
        @type Project
        """
        super().__init__(parent)

        self.setSortingEnabled(True)
        self.setExpandsOnDoubleClick(False)

        self.__headerItem = QTreeWidgetItem(
            ["", "", self.tr("Summary"), self.tr("Filename"), self.tr("Line"), ""]
        )
        self.__headerItem.setIcon(0, EricPixmapCache.getIcon("taskCompleted"))
        self.__headerItem.setIcon(1, EricPixmapCache.getIcon("taskPriority"))
        self.setHeaderItem(self.__headerItem)

        self.header().setSortIndicator(2, Qt.SortOrder.AscendingOrder)
        self.__resizeColumns()

        self.tasks = []
        self.copyTask = None
        self.projectOpen = False
        self.project = project
        self.__projectTasksScanFilter = ""

        self.taskFilter = TaskFilter()
        self.taskFilter.setActive(False)

        self.__projectTasksSaveTimer = AutoSaver(self, self.saveProjectTasks)
        self.__projectTaskExtractionThread = ProjectTaskExtractionThread()
        self.__projectTaskExtractionThread.taskFound.connect(self.addFileTask)

        self.__projectTasksMenu = QMenu(self.tr("P&roject Tasks"), self)
        self.__projectTasksMenu.addAction(
            self.tr("&Regenerate project tasks"), self.regenerateProjectTasks
        )
        self.__projectTasksMenu.addSeparator()
        self.__projectTasksMenu.addAction(
            self.tr("&Configure scan options"), self.__configureProjectTasksScanOptions
        )

        self.__menu = QMenu(self)
        self.__menu.addAction(self.tr("&New Task..."), self.__newTask)
        self.subtaskItem = self.__menu.addAction(
            self.tr("New &Sub-Task..."), self.__newSubTask
        )
        self.__menu.addSeparator()
        self.projectTasksMenuItem = self.__menu.addMenu(self.__projectTasksMenu)
        self.__menu.addSeparator()
        self.gotoItem = self.__menu.addAction(self.tr("&Go To"), self.__goToTask)
        self.__menu.addSeparator()
        self.copyItem = self.__menu.addAction(self.tr("&Copy"), self.__copyTask)
        self.pasteItem = self.__menu.addAction(self.tr("&Paste"), self.__pasteTask)
        self.pasteMainItem = self.__menu.addAction(
            self.tr("Paste as &Main Task"), self.__pasteMainTask
        )
        self.deleteItem = self.__menu.addAction(self.tr("&Delete"), self.__deleteTask)
        self.__menu.addSeparator()
        self.markCompletedItem = self.__menu.addAction(
            self.tr("&Mark Completed"), self.__markCompleted
        )
        self.__menu.addAction(
            self.tr("Delete Completed &Tasks"), self.__deleteCompleted
        )
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("P&roperties..."), self.__editTaskProperties)
        self.__menu.addSeparator()
        self.__menuFilteredAct = self.__menu.addAction(self.tr("&Filtered display"))
        self.__menuFilteredAct.setCheckable(True)
        self.__menuFilteredAct.setChecked(False)
        self.__menuFilteredAct.triggered[bool].connect(self.__activateFilter)
        self.__menu.addAction(
            self.tr("Filter c&onfiguration..."), self.__configureFilter
        )
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("Resi&ze columns"), self.__resizeColumns)
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("Configure..."), self.__configure)

        self.__backMenu = QMenu(self)
        self.__backMenu.addAction(self.tr("&New Task..."), self.__newTask)
        self.__backMenu.addSeparator()
        self.backProjectTasksMenuItem = self.__backMenu.addMenu(self.__projectTasksMenu)
        self.__backMenu.addSeparator()
        self.backPasteItem = self.__backMenu.addAction(
            self.tr("&Paste"), self.__pasteTask
        )
        self.backPasteMainItem = self.__backMenu.addAction(
            self.tr("Paste as &Main Task"), self.__pasteMainTask
        )
        self.__backMenu.addSeparator()
        self.backDeleteCompletedItem = self.__backMenu.addAction(
            self.tr("Delete Completed &Tasks"), self.__deleteCompleted
        )
        self.__backMenu.addSeparator()
        self.__backMenuFilteredAct = self.__backMenu.addAction(
            self.tr("&Filtered display")
        )
        self.__backMenuFilteredAct.setCheckable(True)
        self.__backMenuFilteredAct.setChecked(False)
        self.__backMenuFilteredAct.triggered[bool].connect(self.__activateFilter)
        self.__backMenu.addAction(
            self.tr("Filter c&onfiguration..."), self.__configureFilter
        )
        self.__backMenu.addSeparator()
        self.__backMenu.addAction(self.tr("Resi&ze columns"), self.__resizeColumns)
        self.__backMenu.addSeparator()
        self.__backMenu.addAction(self.tr("Configure..."), self.__configure)

        self.__activating = False

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)
        self.itemActivated.connect(self.__taskItemActivated)

        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

        self.__generateTopLevelItems()

    def __generateTopLevelItems(self):
        """
        Private method to generate the 'Extracted Tasks' item.
        """
        self.__extractedItem = QTreeWidgetItem(self, [self.tr("Extracted Tasks")])
        self.__manualItem = QTreeWidgetItem(self, [self.tr("Manual Tasks")])
        for itm in [self.__extractedItem, self.__manualItem]:
            itm.setFirstColumnSpanned(True)
            itm.setExpanded(True)
            itm.setHidden(True)
            font = itm.font(0)
            font.setUnderline(True)
            itm.setFont(0, font)

    def __checkTopLevelItems(self):
        """
        Private slot to check the 'Extracted Tasks' item for children.
        """
        for itm in [self.__extractedItem, self.__manualItem]:
            visibleCount = itm.childCount()
            for index in range(itm.childCount()):
                if itm.child(index).isHidden():
                    visibleCount -= 1
            itm.setHidden(visibleCount == 0)

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.sortItems(self.sortColumn(), self.header().sortIndicatorOrder())

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.header().setStretchLastSection(True)

    def findParentTask(self, parentUid):
        """
        Public method to find a parent task by its ID.

        @param parentUid uid of the parent task
        @type str
        @return reference to the task
        @rtype Task
        """
        if not parentUid:
            return None

        parentTask = None
        for task in self.tasks:
            if task.getUuid() == parentUid:
                parentTask = task
                break

        return parentTask

    def containsTask(self, taskToTest):
        """
        Public method to test, if a task is already in the tasks list.

        @param taskToTest task to look for
        @type Task
        @return flag indicating the existence of the task
        @rtype bool
        """
        if taskToTest is None:
            # play it safe
            return False

        return any(
            (task.summary == taskToTest.summary)
            and (task.filename == taskToTest.filename)
            and (task.lineno == taskToTest.lineno)
            for task in self.tasks
        )

    def __refreshDisplay(self):
        """
        Private method to refresh the display.
        """
        for task in self.tasks:
            task.setHidden(not self.taskFilter.showTask(task))

        self.__checkTopLevelItems()
        self.__resort()
        self.__resizeColumns()

    @pyqtSlot(QTreeWidgetItem, int)
    def __taskItemActivated(self, itm, _col):
        """
        Private slot to handle the activation of an item.

        @param itm reference to the activated item
        @type QTreeWidgetItem
        @param _col column the item was activated in (unused)
        @type int
        """
        if (
            not self.__activating
            and itm is not self.__extractedItem
            and itm is not self.__manualItem
        ):
            self.__activating = True
            fn = itm.getFilename()
            if fn:
                if os.path.exists(fn):
                    self.displayFile.emit(fn, itm.getLineno())
                else:
                    if itm.isProjectTask():
                        self.__deleteTask(itm)
            else:
                self.__editTaskProperties()
            self.__activating = False

    def __showContextMenu(self, coord):
        """
        Private slot to show the context menu of the list.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        itm = self.itemAt(coord)
        coord = self.mapToGlobal(coord)
        if itm is None or itm is self.__extractedItem or itm is self.__manualItem:
            self.backProjectTasksMenuItem.setEnabled(self.projectOpen)
            if self.copyTask:
                self.backPasteItem.setEnabled(True)
                self.backPasteMainItem.setEnabled(True)
            else:
                self.backPasteItem.setEnabled(False)
                self.backPasteMainItem.setEnabled(False)
            self.backDeleteCompletedItem.setEnabled(bool(self.tasks))
            self.__backMenu.popup(coord)
        else:
            self.projectTasksMenuItem.setEnabled(self.projectOpen)
            if itm.getFilename():
                self.gotoItem.setEnabled(True)
                self.deleteItem.setEnabled(True)
                self.markCompletedItem.setEnabled(False)
                self.copyItem.setEnabled(False)
                self.subtaskItem.setEnabled(False)
            else:
                self.gotoItem.setEnabled(False)
                self.deleteItem.setEnabled(True)
                self.markCompletedItem.setEnabled(True)
                self.copyItem.setEnabled(True)
                self.subtaskItem.setEnabled(True)
            if self.copyTask:
                self.pasteItem.setEnabled(True)
                self.pasteMainItem.setEnabled(True)
            else:
                self.pasteItem.setEnabled(False)
                self.pasteMainItem.setEnabled(False)

            self.__menu.popup(coord)

    def setProjectOpen(self, o=False):
        """
        Public slot to set the project status.

        @param o flag indicating the project status
        @type bool
        """
        self.projectOpen = o

    def addTask(
        self,
        summary,
        priority=TaskPriority.NORMAL,
        filename="",
        lineno=0,
        completed=False,
        _time=0,
        isProjectTask=False,
        taskType=TaskType.TODO,
        description="",
        uid="",
        parentTask=None,
    ):
        """
        Public slot to add a task.

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
        @param description explanatory text of the task
        @type str
        @param uid unique id of the task
        @type str
        @param parentTask reference to the parent task item or the UID of the
            parent task
        @type Task or str
        @return reference to the task item
        @rtype Task
        """
        if isinstance(parentTask, str):
            # UID of parent task
            if parentTask == "":
                parentUid = ""
                parentTask = None
            else:
                parentUid = parentTask
                parentTask = self.findParentTask(parentUid)
        else:
            # parent task item
            if parentTask:
                parentUid = parentTask.getUuid()
            else:
                parentUid = ""
        task = Task(
            summary,
            priority,
            filename,
            lineno,
            completed,
            _time,
            isProjectTask,
            taskType,
            self.project,
            description,
            uid,
            parentUid,
        )
        if not self.containsTask(task):
            self.tasks.append(task)
            if parentTask:
                parentTask.addChild(task)
                parentTask.setExpanded(True)
            elif filename:
                self.__extractedItem.addChild(task)
            else:
                self.__manualItem.addChild(task)
            task.setHidden(not self.taskFilter.showTask(task))

            self.__checkTopLevelItems()
            self.__resort()
            self.__resizeColumns()

            if isProjectTask:
                self.__projectTasksSaveTimer.changeOccurred()

            return task
        else:
            return None

    def addFileTask(
        self, summary, filename, lineno, taskType=TaskType.TODO, description=""
    ):
        """
        Public slot to add a file related task.

        @param summary summary text of the task
        @type str
        @param filename filename containing the task
        @type str
        @param lineno line number containing the task
        @type int
        @param taskType type of the task
        @type TaskType
        @param description explanatory text of the task
        @type str
        """
        self.addTask(
            summary,
            filename=filename,
            lineno=lineno,
            isProjectTask=(
                self.project and self.project.isProjectCategory(filename, "SOURCES")
            ),
            taskType=TaskType(taskType),
            description=description,
        )

    def getProjectTasks(self):
        """
        Public method to retrieve all project related tasks.

        @return copy of tasks
        @rtype list of Task
        """
        tasks = [task for task in self.tasks if task.isProjectTask()]
        return tasks[:]

    def getGlobalTasks(self):
        """
        Public method to retrieve all non project related tasks.

        @return copy of tasks
        @rtype list of Task
        """
        tasks = [task for task in self.tasks if not task.isProjectTask()]
        return tasks[:]

    def clearTasks(self):
        """
        Public slot to clear all tasks from display.
        """
        self.tasks = []
        self.clear()
        self.__generateTopLevelItems()

    def clearProjectTasks(self, fileOnly=False):
        """
        Public slot to clear project related tasks.

        @param fileOnly flag indicating to clear only file related project tasks
        @type bool
        """
        for task in reversed(self.tasks[:]):
            if (fileOnly and task.isProjectFileTask()) or (
                not fileOnly and task.isProjectTask()
            ):
                if self.copyTask == task:
                    self.copyTask = None
                parent = task.parent()
                parent.removeChild(task)
                self.tasks.remove(task)
                del task

        self.__checkTopLevelItems()
        self.__resort()
        self.__resizeColumns()

    def clearFileTasks(self, filename, conditionally=False):
        """
        Public slot to clear all tasks related to a file.

        @param filename name of the file
        @type str
        @param conditionally flag indicating to clear the tasks of the file
            checking some conditions
        @type bool
        """
        if conditionally:
            if self.project and self.project.isProjectCategory(filename, "SOURCES"):
                # project related tasks will not be cleared
                return
            if not Preferences.getTasks("ClearOnFileClose"):
                return
        for task in self.tasks[:]:
            if task.getFilename() == filename:
                if self.copyTask == task:
                    self.copyTask = None
                self.__extractedItem.removeChild(task)
                self.tasks.remove(task)
                if task.isProjectTask:
                    self.__projectTasksSaveTimer.changeOccurred()
                del task

        self.__checkTopLevelItems()
        self.__resort()
        self.__resizeColumns()

    def __editTaskProperties(self):
        """
        Private slot to handle the "Properties" context menu entry.
        """
        task = self.currentItem()
        dlg = TaskPropertiesDialog(task, parent=self, projectOpen=self.projectOpen)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.isManualTaskMode():
            (
                summary,
                priority,
                taskType,
                completed,
                isProjectTask,
                description,
            ) = dlg.getData()
            task.setSummary(summary)
            task.setPriority(priority)
            task.setTaskType(taskType)
            task.setCompleted(completed)
            task.setProjectTask(isProjectTask)
            task.setDescription(description)
            self.__projectTasksSaveTimer.changeOccurred()

    def __newTask(self):
        """
        Private slot to handle the "New Task" context menu entry.
        """
        dlg = TaskPropertiesDialog(None, parent=self, projectOpen=self.projectOpen)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                summary,
                priority,
                taskType,
                completed,
                isProjectTask,
                description,
            ) = dlg.getData()
            self.addTask(
                summary,
                priority,
                completed=completed,
                isProjectTask=isProjectTask,
                taskType=taskType,
                description=description,
            )

    def __newSubTask(self):
        """
        Private slot to handle the "New Sub-Task" context menu entry.
        """
        parentTask = self.currentItem()
        projectTask = parentTask.isProjectTask()

        dlg = TaskPropertiesDialog(None, parent=self, projectOpen=self.projectOpen)
        dlg.setSubTaskMode(projectTask)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                summary,
                priority,
                taskType,
                completed,
                isProjectTask,
                description,
            ) = dlg.getData()
            self.addTask(
                summary,
                priority,
                completed=completed,
                isProjectTask=isProjectTask,
                taskType=taskType,
                description=description,
                parentTask=parentTask,
            )

    def __markCompleted(self):
        """
        Private slot to handle the "Mark Completed" context menu entry.
        """
        task = self.currentItem()
        task.setCompleted(True)

    def __deleteCompleted(self):
        """
        Private slot to handle the "Delete Completed Tasks" context menu entry.
        """
        for task in reversed(self.tasks[:]):
            if task.isCompleted():
                if self.copyTask == task:
                    self.copyTask = None
                parent = task.parent()
                parent.removeChild(task)
                self.tasks.remove(task)
                if task.isProjectTask:
                    self.__projectTasksSaveTimer.changeOccurred()
                del task

        self.__checkTopLevelItems()
        self.__resort()
        self.__resizeColumns()

        ci = self.currentItem()
        if ci:
            ind = self.indexFromItem(ci, self.currentColumn())
            self.scrollTo(ind, QAbstractItemView.ScrollHint.PositionAtCenter)

    def __copyTask(self):
        """
        Private slot to handle the "Copy" context menu entry.
        """
        task = self.currentItem()
        self.copyTask = task

    def __pasteTask(self):
        """
        Private slot to handle the "Paste" context menu entry.
        """
        if self.copyTask:
            parent = self.copyTask.parent()
            if not isinstance(parent, Task):
                parent = None

            self.addTask(
                self.copyTask.summary,
                priority=self.copyTask.priority,
                completed=self.copyTask.completed,
                description=self.copyTask.description,
                isProjectTask=self.copyTask._isProjectTask,
                parentTask=parent,
            )

    def __pasteMainTask(self):
        """
        Private slot to handle the "Paste as Main Task" context menu entry.
        """
        if self.copyTask:
            self.addTask(
                self.copyTask.summary,
                priority=self.copyTask.priority,
                completed=self.copyTask.completed,
                description=self.copyTask.description,
                isProjectTask=self.copyTask._isProjectTask,
            )

    def __deleteSubTasks(self, task):
        """
        Private method to delete all sub-tasks.

        @param task task to delete sub-tasks of
        @type Task
        """
        for subtask in task.takeChildren():
            if self.copyTask == subtask:
                self.copyTask = None
            if subtask.childCount() > 0:
                self.__deleteSubTasks(subtask)
            self.tasks.remove(subtask)

    def __deleteTask(self, task=None):
        """
        Private slot to delete a task.

        @param task task to be deleted
        @type Task
        """
        if task is None:
            # called via "Delete Task" context menu entry
            task = self.currentItem()

        if self.copyTask is task:
            self.copyTask = None
        if task.childCount() > 0:
            self.__deleteSubTasks(task)
        parent = task.parent()
        parent.removeChild(task)
        self.tasks.remove(task)
        if task.isProjectTask:
            self.__projectTasksSaveTimer.changeOccurred()
        del task

        self.__checkTopLevelItems()
        self.__resort()
        self.__resizeColumns()

        ci = self.currentItem()
        if ci:
            ind = self.indexFromItem(ci, self.currentColumn())
            self.scrollTo(ind, QAbstractItemView.ScrollHint.PositionAtCenter)

    def __goToTask(self):
        """
        Private slot to handle the "Go To" context menu entry.
        """
        task = self.currentItem()
        self.displayFile.emit(task.getFilename(), task.getLineno())

    def handlePreferencesChanged(self):
        """
        Public slot to react to changes of the preferences.
        """
        for task in self.tasks:
            task.colorizeTask()

    def __activateFilter(self, on):
        """
        Private slot to handle the "Filtered display" context menu entry.

        @param on flag indicating the filter state
        @type bool
        """
        if on and not self.taskFilter.hasActiveFilter():
            res = EricMessageBox.yesNo(
                self,
                self.tr("Activate task filter"),
                self.tr(
                    """The task filter doesn't have any active filters."""
                    """ Do you want to configure the filter settings?"""
                ),
                yesDefault=True,
            )
            if not res:
                on = False
            else:
                self.__configureFilter()
                on = self.taskFilter.hasActiveFilter()

        self.taskFilter.setActive(on)
        self.__menuFilteredAct.setChecked(on)
        self.__backMenuFilteredAct.setChecked(on)
        self.__refreshDisplay()

    def __configureFilter(self):
        """
        Private slot to handle the "Configure filter" context menu entry.
        """
        from .TaskFilterConfigDialog import TaskFilterConfigDialog

        dlg = TaskFilterConfigDialog(self.taskFilter, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.configureTaskFilter(self.taskFilter)
            self.__refreshDisplay()

    def __configureProjectTasksScanOptions(self):
        """
        Private slot to configure scan options for project tasks.
        """
        scanFilter, ok = QInputDialog.getText(
            self,
            self.tr("Scan Filter Patterns"),
            self.tr(
                "Enter filename patterns of files"
                " to be excluded separated by a comma:"
            ),
            QLineEdit.EchoMode.Normal,
            self.__projectTasksScanFilter,
        )
        if ok:
            self.__projectTasksScanFilter = scanFilter

    def regenerateProjectTasks(self, quiet=False):
        """
        Public slot to regenerate project related tasks.

        @param quiet flag indicating quiet operation
        @type bool
        """
        markers = {
            taskType: Preferences.getTasks(markersName).split()
            for taskType, markersName in Task.TaskType2MarkersName.items()
        }
        files = self.project.getProjectData(dataKey="SOURCES")

        # apply file filter
        filterList = [
            f.strip() for f in self.__projectTasksScanFilter.split(",") if f.strip()
        ]
        if filterList:
            for scanFilter in filterList:
                files = [f for f in files if not fnmatch.fnmatch(f, scanFilter)]

        # remove all project tasks
        self.clearProjectTasks(fileOnly=True)

        # now process them
        if quiet:
            ppath = self.project.getProjectPath()
            self.__projectTaskExtractionThread.scan(
                markers, [os.path.join(ppath, f) for f in files]
            )
        else:
            progress = EricProgressDialog(
                self.tr("Extracting project tasks..."),
                self.tr("Abort"),
                0,
                len(files),
                self.tr("%v/%m Files"),
                self,
            )
            progress.setMinimumDuration(0)
            progress.setWindowTitle(self.tr("Tasks"))

            ppath = self.project.getProjectPath()

            now = time.monotonic()
            for count, file in enumerate(files):
                progress.setLabelText(
                    self.tr("Extracting project tasks...\n{0}").format(file)
                )
                progress.setValue(count)
                if time.monotonic() - now > 0.01:
                    QApplication.processEvents()
                    now = time.monotonic()
                if progress.wasCanceled():
                    break

                fn = os.path.join(ppath, file)
                # read the file and split it into textlines
                try:
                    text, _encoding = Utilities.readEncodedFile(fn)
                    lines = text.splitlines()
                except (OSError, UnicodeError):
                    count += 1
                    progress.setValue(count)
                    continue

                # now search tasks and record them
                for lineIndex, line in enumerate(lines, start=1):
                    shouldBreak = False

                    if line.endswith("__NO-TASK__"):
                        # ignore potential task marker
                        continue

                    for taskType, taskMarkers in markers.items():
                        for taskMarker in taskMarkers:
                            index = line.find(taskMarker)
                            if index > -1:
                                task = line[index:]
                                self.addFileTask(task, fn, lineIndex, taskType)
                                shouldBreak = True
                                break
                        if shouldBreak:
                            break

            progress.setValue(len(files))

    def __configure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("tasksPage")

    def saveProjectTasks(self):
        """
        Public method to write the project tasks.
        """
        if self.projectOpen and Preferences.getProject("TasksProjectAutoSave"):
            self.project.writeTasks()

    def stopProjectTaskExtraction(self):
        """
        Public method to stop the project task extraction thread.
        """
        self.__projectTaskExtractionThread.requestInterrupt()
        self.__projectTaskExtractionThread.wait()

    def getTasksScanFilter(self) -> str:
        """
        Public method to get the project scan filter.

        @return project scan filter
        @rtype str
        """
        return self.__projectTasksScanFilter.strip()

    def setTasksScanFilter(self, filterStr: str):
        """
        Public method to set the project scan filter.

        @param filterStr project scan filter
        @type str
        """
        self.__projectTasksScanFilter = filterStr


class ProjectTaskExtractionThread(QThread):
    """
    Class implementing a thread to extract tasks related to a project.

    @signal taskFound(str, str, int, TaskType) emitted with the task
        description, the file name, the line number and task type to signal
        the presence of a task
    """

    taskFound = pyqtSignal(str, str, int, TaskType)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__()

        self.__lock = threading.Lock()
        self.__interrupt = False

    def requestInterrupt(self):
        """
        Public method to request iterruption of the thread.
        """
        if self.isRunning():
            self.__interrupt = True

    def scan(self, markers, files):
        """
        Public method to scan the given list of files for tasks.

        @param markers dictionary of defined task markers
        @type dict of lists of str
        @param files list of file names to be scanned
        @type list of str
        """
        with self.__lock:
            self.__interrupt = False
            self.__files = files[:]
            self.__markers = {}
            for markerType in markers:
                self.__markers[markerType] = markers[markerType][:]

            if not self.isRunning():
                self.start(QThread.Priority.LowPriority)

    def run(self):
        """
        Public thread method to scan the given files.
        """
        with self.__lock:
            files = self.__files[:]
            markers = {}
            for markerType in self.__markers:
                markers[markerType] = self.__markers[markerType][:]

        for fn in files:
            if self.__interrupt:
                break

            # read the file and split it into textlines
            try:
                text, _encoding = Utilities.readEncodedFile(fn)
                lines = text.splitlines()
            except (OSError, UnicodeError):
                continue

            # now search tasks and record them
            for lineIndex, line in enumerate(lines, start=1):
                if self.__interrupt:
                    break

                found = False

                if line.endswith("__NO-TASK__"):
                    # ignore potential task marker
                    continue

                for taskType, taskMarkers in markers.items():
                    for taskMarker in taskMarkers:
                        index = line.find(taskMarker)
                        if index > -1:
                            task = line[index:]
                            with self.__lock:
                                self.taskFound.emit(task, fn, lineIndex, taskType)
                            found = True
                            break
                    if found:
                        break
