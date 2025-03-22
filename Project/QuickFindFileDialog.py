# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a quick search for files.

This is basically the FindFileNameDialog modified to support faster
interactions.
"""

import os

from PyQt6.QtCore import QEvent, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidgetItem,
    QWidget,
)

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_QuickFindFile import Ui_QuickFindFile


class QuickFindFileDialog(QWidget, Ui_QuickFindFile):
    """
    Class implementing the Quick Find File by Name Dialog.

    This dialog provides a slightly more streamlined behaviour
    than the standard FindFileNameDialog in that it tries to
    match any name in the project against (fragmentary) bits of
    file names.

    @signal sourceFile(str) emitted to open a file in the editor
    @signal designerFile(str) emitted to open a Qt-Designer file
    @signal linguistFile(str) emitted to open a Qt translation file
    """

    sourceFile = pyqtSignal(str)
    designerFile = pyqtSignal(str)
    linguistFile = pyqtSignal(str)

    def __init__(self, project, parent=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param parent parent widget of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.fileList.headerItem().setText(self.fileList.columnCount(), "")
        self.fileNameEdit.returnPressed.connect(self.on_fileNameEdit_returnPressed)
        self.installEventFilter(self)

        self.stopButton = self.buttonBox.addButton(
            self.tr("Stop"), QDialogButtonBox.ButtonRole.ActionRole
        )

        self.project = project
        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

    def eventFilter(self, source, event):
        """
        Public method to handle event for another object.

        @param source object to handle events for
        @type QObject
        @param event event to handle
        @type QEvent
        @return flag indicating that the event was handled
        @rtype bool
        """
        if event.type() == QEvent.Type.KeyPress:
            # Anywhere in the dialog, make hitting escape cancel it
            if event.key() == Qt.Key.Key_Escape:
                self.close()

            # Anywhere in the dialog, make hitting up/down choose next item
            # Note: This doesn't really do anything, as other than the text
            #       input there's nothing that doesn't handle up/down already.
            elif event.key() == Qt.Key.Key_Up or event.key() == Qt.Key.Key_Down:
                current = self.fileList.currentItem()
                index = self.fileList.indexOfTopLevelItem(current)
                if event.key() == Qt.Key.Key_Up:
                    if index != 0:
                        self.fileList.setCurrentItem(
                            self.fileList.topLevelItem(index - 1)
                        )
                else:
                    if index < (self.fileList.topLevelItemCount() - 1):
                        self.fileList.setCurrentItem(
                            self.fileList.topLevelItem(index + 1)
                        )
        return QWidget.eventFilter(self, source, event)

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.stopButton:
            self.shouldStop = True
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Open):
            self.__openFile()

    def __openFile(self, itm=None):
        """
        Private slot to open a file.

        It emits the signal sourceFile or designerFile depending on the
        file extension.

        @param itm item to be opened
        @type QTreeWidgetItem
        @return flag indicating a file was opened
        @rtype bool
        """
        if itm is None:
            itm = self.fileList.currentItem()
        if itm is not None:
            filePath = itm.text(1)
            fileName = itm.text(0)
            fullPath = (
                self.__remotefsInterface.join(self.project.ppath, filePath, fileName)
                if self.__isRemote
                else os.path.join(self.project.ppath, filePath, fileName)
            )

            if fullPath.endswith(".ui"):
                self.designerFile.emit(fullPath)
            elif fullPath.endswith((".ts", ".qm")):
                self.linguistFile.emit(fullPath)
            else:
                self.sourceFile.emit(fullPath)
            return True

        return False

    def __generateLocations(self):
        """
        Private method to generate a set of locations that can be searched.

        @yield set of files in our project
        @ytype str
        """
        for fileCategory in self.project.getFileCategories():
            entries = self.project.getProjectData(dataKey=fileCategory, default=[])
            yield from entries[:]

    def __sortedMatches(self, items, searchTerm):
        """
        Private method to find the subset of items which match a search term.

        @param items list of items to be scanned for the search term
        @type list of str
        @param searchTerm search term to be searched for
        @type str
        @return sorted subset of items which match searchTerm in
            relevance order (i.e. the most likely match first)
        @rtype list of tuple of bool, int and str
        """
        fragments = searchTerm.split()

        possible = [
            # matches, in_order, file name
        ]

        for entry in items:
            count = 0
            match_order = []
            for fragment in fragments:
                index = entry.find(fragment)
                if index == -1:
                    # try case-insensitive match
                    index = entry.lower().find(fragment.lower())
                if index != -1:
                    count += 1
                    match_order.append(index)
            if count:
                record = (count, match_order == sorted(match_order), entry)
                if possible and count < possible[0][0]:
                    # ignore...
                    continue
                elif possible and count > possible[0][0]:
                    # better than all previous matches, discard them and
                    # keep this
                    del possible[:]
                possible.append(record)

        ordered = []
        for _, in_order, name in possible:
            try:
                age = (
                    self.__remotefsInterface.stat(
                        self.__remotefsInterface.join(self.project.ppath, name),
                        ["st_mtime"],
                    )["st_mtime"]
                    if self.__isRemote
                    else os.stat(os.path.join(self.project.ppath, name)).st_mtime
                )
            except OSError:
                # skipping, because it doesn't appear to exist...
                continue
            ordered.append(
                (
                    in_order,  # we want closer match first
                    -age,  # then approximately "most recently edited"
                    name,
                )
            )
        ordered.sort()
        return ordered

    def __searchFile(self):
        """
        Private slot to handle the search.
        """
        fileName = self.fileNameEdit.text().strip()
        if not fileName:
            self.fileList.clear()
            return

        ordered = self.__sortedMatches(self.__generateLocations(), fileName)

        found = False
        self.fileList.clear()
        locations = {}

        for _in_order, _age, name in ordered:
            found = True
            head, tail = (
                self.__remotefsInterface.split(name)
                if self.__isRemote
                else os.path.split(name)
            )
            QTreeWidgetItem(self.fileList, [tail, head])
        QApplication.processEvents()

        del locations
        self.stopButton.setEnabled(False)
        self.fileList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.fileList.header().setStretchLastSection(True)

        if found:
            self.fileList.setCurrentItem(self.fileList.topLevelItem(0))

    @pyqtSlot(str)
    def on_fileNameEdit_textChanged(self, text):
        """
        Private slot to handle the textChanged signal of the file name edit.

        @param text (ignored)
        @type str
        """
        self.__searchFile()

    @pyqtSlot()
    def on_fileNameEdit_returnPressed(self):
        """
        Private slot to handle enter being pressed on the file name edit box.
        """
        if self.__openFile():
            self.close()

    @pyqtSlot(QTreeWidgetItem, int)
    def on_fileList_itemActivated(self, itm, _column):
        """
        Private slot to handle the double click on a file item.

        It emits the signal sourceFile or designerFile depending on the
        file extension.

        @param itm the double clicked listview item
        @type QTreeWidgetItem
        @param _column column that was double clicked (unused)
        @type int
        """
        self.__openFile(itm)

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_fileList_currentItemChanged(self, current, _previous):
        """
        Private slot handling a change of the current item.

        @param current current item
        @type QTreeWidgetItem
        @param _previous prevoius current item (unused)
        @type QTreeWidgetItem
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Open).setEnabled(
            current is not None
        )

    def show(self, isRemote):
        """
        Public method to perform actions before showing the dialog.

        @param isRemote flag indicating a remote project
        @type bool
        """
        self.__isRemote = isRemote

        self.fileNameEdit.selectAll()
        self.fileNameEdit.setFocus()

        super().show()
