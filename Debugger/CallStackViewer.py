# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Call Stack viewer widget.
"""

import pathlib

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp


class CallStackViewer(QWidget):
    """
    Class implementing the Call Stack viewer widget.

    @signal sourceFile(str, int) emitted to show the source of a stack entry
    @signal frameSelected(int) emitted to signal the selection of a frame entry
    """

    sourceFile = pyqtSignal(str, int)
    frameSelected = pyqtSignal(int)

    FilenameRole = Qt.ItemDataRole.UserRole + 1
    LinenoRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, debugServer, parent=None):
        """
        Constructor

        @param debugServer reference to the debug server object
        @type DebugServer
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__layout = QVBoxLayout(self)
        self.setLayout(self.__layout)
        self.__debuggerLabel = QLabel(self)
        self.__layout.addWidget(self.__debuggerLabel)
        self.__callStackList = QTreeWidget(self)
        self.__layout.addWidget(self.__callStackList)

        self.__callStackList.setHeaderHidden(True)
        self.__callStackList.setAlternatingRowColors(True)
        self.__callStackList.setItemsExpandable(False)
        self.__callStackList.setRootIsDecorated(False)
        self.setWindowTitle(self.tr("Call Stack"))

        self.__menu = QMenu(self.__callStackList)
        self.__sourceAct = self.__menu.addAction(
            self.tr("Show source"), self.__openSource
        )
        self.__menu.addAction(self.tr("Clear"), self.__callStackList.clear)
        self.__menu.addSeparator()
        self.__menu.addAction(self.tr("Save"), self.__saveStackTrace)
        self.__callStackList.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.__callStackList.customContextMenuRequested.connect(self.__showContextMenu)

        self.__dbs = debugServer

        # file name, line number, function name, arguments
        self.__entryFormat = self.tr("File: {0}\nLine: {1}\n{2}{3}")
        # file name, line number
        self.__entryFormatShort = self.tr("File: {0}\nLine: {1}")

        self.__projectMode = False
        self.__project = None

        self.__dbs.clientStack.connect(self.__showCallStack)
        self.__callStackList.itemDoubleClicked.connect(self.__itemDoubleClicked)

    def setDebugger(self, debugUI):
        """
        Public method to set a reference to the Debug UI.

        @param debugUI reference to the DebugUI object
        @type DebugUI
        """
        debugUI.clientStack.connect(self.__showCallStack)

    def setProjectMode(self, enabled):
        """
        Public slot to set the call trace viewer to project mode.

        In project mode the call trace info is shown with project relative
        path names.

        @param enabled flag indicating to enable the project mode
        @type bool
        """
        self.__projectMode = enabled
        if enabled and self.__project is None:
            self.__project = ericApp().getObject("Project")

    def __showContextMenu(self, coord):
        """
        Private slot to show the context menu.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        if self.__callStackList.topLevelItemCount() > 0:
            itm = self.__callStackList.currentItem()
            self.__sourceAct.setEnabled(itm is not None)
            self.__menu.popup(self.__callStackList.mapToGlobal(coord))

    def clear(self):
        """
        Public method to clear the stack viewer data.
        """
        self.__debuggerLabel.clear()
        self.__callStackList.clear()

    def __showCallStack(self, stack, debuggerId):
        """
        Private slot to show the call stack of the program being debugged.

        @param stack list of tuples with call stack data (file name,
            line number, function name, formatted argument/values list)
        @type list of tuples of (str, str, str, str)
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__debuggerLabel.setText(debuggerId)

        self.__callStackList.clear()
        for fname, fline, ffunc, fargs in stack:
            dfname = (
                self.__project.getRelativePath(fname) if self.__projectMode else fname
            )
            itm = (
                # use normal format
                QTreeWidgetItem(
                    self.__callStackList,
                    [self.__entryFormat.format(dfname, fline, ffunc, fargs)],
                )
                if ffunc and not ffunc.startswith("<")
                else
                # use short format
                QTreeWidgetItem(
                    self.__callStackList,
                    [self.__entryFormatShort.format(dfname, fline)],
                )
            )
            itm.setData(0, self.FilenameRole, fname)
            itm.setData(0, self.LinenoRole, fline)

        self.__callStackList.resizeColumnToContents(0)

    def __itemDoubleClicked(self, itm):
        """
        Private slot to handle a double click of a stack entry.

        @param itm reference to the double clicked item
        @type QTreeWidgetItem
        """
        fname = itm.data(0, self.FilenameRole)
        fline = itm.data(0, self.LinenoRole)
        if self.__projectMode:
            fname = self.__project.getAbsolutePath(fname)
        self.sourceFile.emit(fname, fline)

        index = self.__callStackList.indexOfTopLevelItem(itm)
        self.frameSelected.emit(index)

    def __openSource(self):
        """
        Private slot to show the source for the selected stack entry.
        """
        itm = self.__callStackList.currentItem()
        if itm:
            self.__itemDoubleClicked(itm)

    def __saveStackTrace(self):
        """
        Private slot to save the stack trace info to a file.
        """
        if self.__callStackList.topLevelItemCount() > 0:
            fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
                self,
                self.tr("Save Call Stack Info"),
                "",
                self.tr("Text Files (*.txt);;All Files (*)"),
                None,
                EricFileDialog.DontConfirmOverwrite,
            )
            if fname:
                fpath = pathlib.Path(fname)
                if not fpath.suffix:
                    ex = selectedFilter.split("(*")[1].split(")")[0]
                    if ex:
                        fpath = fpath.with_suffix(ex)
                if fpath.exists():
                    res = EricMessageBox.yesNo(
                        self,
                        self.tr("Save Call Stack Info"),
                        self.tr(
                            "<p>The file <b>{0}</b> already exists."
                            " Overwrite it?</p>"
                        ).format(fpath),
                        icon=EricMessageBox.Warning,
                    )
                    if not res:
                        return

                try:
                    title = self.tr("Call Stack of '{0}'").format(
                        self.__debuggerLabel.text()
                    )
                    with fpath.open("w", encoding="utf-8") as f:
                        f.write("{0}\n".format(title))
                        f.write("{0}\n\n".format(len(title) * "="))
                        itm = self.__callStackList.topLevelItem(0)
                        while itm is not None:
                            f.write("{0}\n".format(itm.text(0)))
                            f.write("{0}\n".format(78 * "="))
                            itm = self.__callStackList.itemBelow(itm)
                except OSError as err:
                    EricMessageBox.critical(
                        self,
                        self.tr("Error saving Call Stack Info"),
                        self.tr(
                            """<p>The call stack info could not be"""
                            """ written to <b>{0}</b></p>"""
                            """<p>Reason: {1}</p>"""
                        ).format(fpath, str(err)),
                    )
