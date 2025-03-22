# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to visualize the Python Disassembly for some
Python sources.
"""

import dis
import enum
import os
import sys

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QBrush
from PyQt6.QtWidgets import QAbstractItemView, QMenu, QTreeWidgetItem, QWidget

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets.EricApplication import ericApp

from .Ui_PythonDisViewer import Ui_PythonDisViewer


class PythonDisViewerModes(enum.Enum):
    """
    Class implementing the disassembly viewer operation modes.
    """

    SOURCEDISASSEMBLY = 0
    TRACEBACK = 1


class PythonDisViewer(QWidget, Ui_PythonDisViewer):
    """
    Class implementing a widget to visualize the Python Disassembly for some
    Python sources.
    """

    StartLineRole = Qt.ItemDataRole.UserRole
    EndLineRole = Qt.ItemDataRole.UserRole + 1
    CodeInfoRole = Qt.ItemDataRole.UserRole + 2

    def __init__(
        self, viewmanager, mode=PythonDisViewerModes.SOURCEDISASSEMBLY, parent=None
    ):
        """
        Constructor

        @param viewmanager reference to the viewmanager object
        @type ViewManager
        @param mode operation mode of the viewer
        @type int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowTitle(self.tr("Disassembly"))

        self.__vm = viewmanager
        self.__vmConnected = False

        self.__mode = mode

        self.__editor = None
        self.__source = ""

        self.disWidget.setHeaderLabels(
            [
                self.tr("Line"),
                self.tr("Offset"),
                self.tr("Operation"),
                self.tr("Parameters"),
                self.tr("Interpreted Parameters"),
            ]
        )
        self.codeInfoWidget.setHeaderLabels([self.tr("Key"), self.tr("Value")])

        self.__disMenu = QMenu(self.disWidget)
        if self.__mode == PythonDisViewerModes.SOURCEDISASSEMBLY:
            self.__codeInfoAct = self.__disMenu.addAction(
                self.tr("Show Code Info"), self.__showCodeInfo
            )
            self.__disMenu.addSeparator()
        self.__disMenu.addAction(self.tr("Expand All"), self.__expandAllDis)
        self.__disMenu.addAction(self.tr("Collapse All"), self.__collapseAllDis)
        self.__disMenu.addSeparator()
        self.__disMenu.addAction(self.tr("Configure..."), self.__configure)

        self.__codeInfoMenu = QMenu(self.codeInfoWidget)
        if self.__mode == PythonDisViewerModes.SOURCEDISASSEMBLY:
            self.__codeInfoMenu.addAction(self.tr("Hide"), self.codeInfoWidget.hide)
        self.__codeInfoMenu.addAction(self.tr("Expand All"), self.__expandAllCodeInfo)
        self.__codeInfoMenu.addAction(
            self.tr("Collapse All"), self.__collapseAllCodeInfo
        )
        self.__codeInfoMenu.addSeparator()
        self.__codeInfoMenu.addAction(self.tr("Configure..."), self.__configure)

        self.__errorColor = QBrush(Preferences.getPython("DisViewerErrorColor"))
        self.__currentInstructionColor = QBrush(
            Preferences.getPython("DisViewerCurrentColor")
        )
        self.__jumpTargetColor = QBrush(Preferences.getPython("DisViewerLabeledColor"))

        self.__showCodeInfoDetails = Preferences.getPython(
            "DisViewerExpandCodeInfoDetails"
        )

        if self.__mode == PythonDisViewerModes.SOURCEDISASSEMBLY:
            self.disWidget.itemClicked.connect(self.__disItemClicked)
        self.disWidget.itemCollapsed.connect(self.__resizeDisColumns)
        self.disWidget.itemExpanded.connect(self.__resizeDisColumns)
        self.disWidget.customContextMenuRequested.connect(
            self.__disContextMenuRequested
        )

        self.codeInfoWidget.itemCollapsed.connect(self.__resizeCodeInfoColumns)
        self.codeInfoWidget.itemExpanded.connect(self.__resizeCodeInfoColumns)
        self.codeInfoWidget.customContextMenuRequested.connect(
            self.__codeInfoContextMenuRequested
        )

        if self.__mode == PythonDisViewerModes.SOURCEDISASSEMBLY:
            self.__vm.disViewerStateChanged.connect(self.__disViewerStateChanged)

            self.codeInfoWidget.hide()
            self.hide()

        elif self.__mode == PythonDisViewerModes.TRACEBACK:
            self.__styleLabels()

    def __disContextMenuRequested(self, coord):
        """
        Private slot to show the context menu of the disassembly widget.

        @param coord position of the mouse pointer
        @type QPoint
        """
        if self.__mode == PythonDisViewerModes.SOURCEDISASSEMBLY:
            itm = self.disWidget.itemAt(coord)
            self.__codeInfoAct.setEnabled(bool(itm.data(0, self.CodeInfoRole)))
            self.disWidget.setCurrentItem(itm)

        if self.disWidget.topLevelItemCount() > 0:
            # don't show context menu on empty list
            coord = self.disWidget.mapToGlobal(coord)
            self.__disMenu.popup(coord)

    def __editorChanged(self, editor):
        """
        Private slot to handle a change of the current editor.

        @param editor reference to the current editor
        @type Editor
        """
        if editor is not self.__editor:
            if self.__editor:
                self.__editor.clearAllHighlights()
            self.__editor = editor
            if self.__editor:
                self.__loadDIS()

    def __editorSaved(self, editor):
        """
        Private slot to reload the Disassembly after the connected editor was
        saved.

        @param editor reference to the editor that performed a save action
        @type Editor
        """
        if editor and editor is self.__editor:
            self.__loadDIS()

    def __editorLineChanged(self, editor, _lineno):
        """
        Private slot to handle a mouse button double click in the editor.

        @param editor reference to the editor, that emitted the signal
        @type Editor
        @param _lineno line number of the editor's cursor (zero based) (unused)
        @type int
        """
        if editor is self.__editor:
            if editor.isModified():
                # reload the source
                QTimer.singleShot(0, self.__loadDIS)

            # highlight the corresponding entry
            QTimer.singleShot(0, self.__selectItemForEditorLine)

    def __editorLanguageChanged(self, editor):
        """
        Private slot to handle a change of the editor language.

        @param editor reference to the editor which changed language
        @type Editor
        """
        if editor is self.__editor:
            QTimer.singleShot(0, self.__loadDIS)

    def __lastEditorClosed(self):
        """
        Private slot to handle the last editor closed signal of the view
        manager.
        """
        self.hide()

    def show(self):
        """
        Public slot to show the DIS viewer.
        """
        super().show()

        if (
            self.__mode == PythonDisViewerModes.SOURCEDISASSEMBLY
            and not self.__vmConnected
        ):
            self.__vm.editorChangedEd.connect(self.__editorChanged)
            self.__vm.editorSavedEd.connect(self.__editorSaved)
            self.__vm.editorLineChangedEd.connect(self.__editorLineChanged)
            self.__vm.editorLanguageChanged.connect(self.__editorLanguageChanged)
            self.__vmConnected = True

        self.__styleLabels()

    def hide(self):
        """
        Public slot to hide the DIS viewer.
        """
        super().hide()

        if self.__editor:
            self.__editor.clearAllHighlights()

        if self.__mode == PythonDisViewerModes.SOURCEDISASSEMBLY and self.__vmConnected:
            self.__vm.editorChangedEd.disconnect(self.__editorChanged)
            self.__vm.editorSavedEd.disconnect(self.__editorSaved)
            self.__vm.editorLineChangedEd.disconnect(self.__editorLineChanged)
            self.__vm.editorLanguageChanged.disconnect(self.__editorLanguageChanged)
            self.__vmConnected = False

    def shutdown(self):
        """
        Public method to perform shutdown actions.
        """
        self.__editor = None

    def __disViewerStateChanged(self, on):
        """
        Private slot to toggle the display of the Disassembly viewer.

        @param on flag indicating to show the Disassembly
        @type bool
        """
        if self.__mode == PythonDisViewerModes.SOURCEDISASSEMBLY:
            editor = self.__vm.activeWindow()
            if on:
                if editor is not self.__editor:
                    self.__editor = editor
                self.show()
                self.__loadDIS()
            else:
                self.hide()
                self.__editor = None

    def __expandAllDis(self):
        """
        Private slot to expand all items of the disassembly widget.
        """
        block = self.disWidget.blockSignals(True)
        self.disWidget.expandAll()
        self.disWidget.blockSignals(block)
        self.__resizeDisColumns()

    def __collapseAllDis(self):
        """
        Private slot to collapse all items of the disassembly widget.
        """
        block = self.disWidget.blockSignals(True)
        self.disWidget.collapseAll()
        self.disWidget.blockSignals(block)
        self.__resizeDisColumns()

    def __createErrorItem(self, error):
        """
        Private method to create a top level error item.

        @param error error message
        @type str
        @return generated item
        @rtype QTreeWidgetItem
        """
        itm = QTreeWidgetItem(self.disWidget, [error])
        itm.setFirstColumnSpanned(True)
        itm.setForeground(0, self.__errorColor)
        return itm

    def __createTitleItem(self, title, line, parentItem):
        """
        Private method to create a title item.

        @param title titel string for the item
        @type str
        @param line start line of the titled disassembly
        @type int
        @param parentItem reference to the parent item
        @type QTreeWidget or QTreeWidgetItem
        @return generated item
        @rtype QTreeWidgetItem
        """
        itm = QTreeWidgetItem(parentItem, [title])
        itm.setFirstColumnSpanned(True)
        itm.setExpanded(True)

        itm.setData(0, self.StartLineRole, line)
        itm.setData(0, self.EndLineRole, line)

        return itm

    def __createInstructionItem(self, instr, parent, lasti=-1):
        """
        Private method to create an item for the given instruction.

        @param instr instruction the item should be based on
        @type dis.Instruction
        @param parent reference to the parent item
        @type QTreeWidgetItem
        @param lasti index of the instruction of a traceback
        @type int
        @return generated item
        @rtype QTreeWidgetItem
        """
        fields = []
        # Column: Source code line number (right aligned)
        if instr.starts_line:
            fields.append(
                "{0:d}".format(
                    instr.starts_line
                    if sys.version_info < (3, 13)
                    else instr.line_number
                )
            )
        else:
            fields.append("")
        # Column: Instruction offset from start of code sequence
        # (right aligned)
        fields.append("{0:d}".format(instr.offset))
        # Column: Opcode name
        fields.append(instr.opname)
        # Column: Opcode argument (right aligned)
        if instr.arg is not None:
            fields.append(repr(instr.arg))
            # Column: Opcode argument details
            if instr.argrepr:
                fields.append("(" + instr.argrepr + ")")

        itm = QTreeWidgetItem(parent, fields)
        for col in (0, 1, 3):
            itm.setTextAlignment(col, Qt.AlignmentFlag.AlignRight)
        # set font to indicate current instruction and jump target
        font = itm.font(0)
        if instr.offset == lasti:
            font.setItalic(True)
        if instr.is_jump_target:
            font.setBold(True)
        for col in range(itm.columnCount()):
            itm.setFont(col, font)
        # set color to indicate current instruction or jump target
        if instr.offset == lasti:
            foreground = self.__currentInstructionColor
        elif instr.is_jump_target:
            foreground = self.__jumpTargetColor
        else:
            foreground = None
        if foreground:
            for col in range(itm.columnCount()):
                itm.setForeground(col, foreground)

        itm.setExpanded(True)

        if instr.starts_line:
            itm.setData(0, self.StartLineRole, instr.starts_line)
            itm.setData(0, self.EndLineRole, instr.starts_line)
        elif parent is not None:
            # get line from parent (= start line)
            lineno = parent.data(0, self.StartLineRole)
            itm.setData(0, self.StartLineRole, lineno)
            itm.setData(0, self.EndLineRole, lineno)
        return itm

    def __updateItemEndLine(self, itm):
        """
        Private method to update an items end line based on its children.

        @param itm reference to the item to be updated
        @type QTreeWidgetItem
        """
        endLine = (
            max(
                itm.child(index).data(0, self.EndLineRole)
                for index in range(itm.childCount())
            )
            if itm.childCount()
            else itm.data(0, self.StartLineRole)
        )
        itm.setData(0, self.EndLineRole, endLine)

    def __createCodeInfo(self, co):
        """
        Private method to create a dictionary containing the code info data.

        @param co reference to the code object to generate the info for
        @type code
        @return dictionary containing the code info data
        @rtype dict
        """
        codeInfoDict = {
            "name": co.co_name,
            "filename": co.co_filename,
            "firstlineno": co.co_firstlineno,
            "argcount": co.co_argcount,
            "kwonlyargcount": co.co_kwonlyargcount,
            "nlocals": co.co_nlocals,
            "stacksize": co.co_stacksize,
            "flags": dis.pretty_flags(co.co_flags),
            "consts": [str(const) for const in co.co_consts],
            "names": [str(name) for name in co.co_names],
            "varnames": [str(name) for name in co.co_varnames],
            "freevars": [str(var) for var in co.co_freevars],
            "cellvars": [str(var) for var in co.co_cellvars],
        }
        try:
            codeInfoDict["posonlyargcount"] = co.co_posonlyargcount
        except AttributeError:
            # does not exist prior to 3.8.0
            codeInfoDict["posonlyargcount"] = 0

        return codeInfoDict

    def __loadDIS(self):
        """
        Private method to generate the Disassembly from the source of the
        current editor and visualize it.
        """
        if self.__mode != PythonDisViewerModes.SOURCEDISASSEMBLY:
            # wrong mode, just return
            return

        if not self.__editor:
            self.__createErrorItem(self.tr("No editor has been opened."))
            return

        self.clear()
        self.__editor.clearAllHighlights()
        self.codeInfoWidget.hide()

        source = self.__editor.text()
        if not source.strip():
            # empty editor or white space only
            self.__createErrorItem(
                self.tr("The current editor does not contain any source code.")
            )
            return

        if not self.__editor.isPyFile():
            self.__createErrorItem(
                self.tr("The current editor does not contain Python source code.")
            )
            return

        filename = self.__editor.getFileName()
        filename = os.path.basename(filename) if filename else "<dis>"

        with EricOverrideCursor():
            try:
                codeObject = tryCompile(source, filename)
            except Exception as exc:
                codeObject = None
                self.__createErrorItem(str(exc))

            if codeObject:
                self.setUpdatesEnabled(False)
                block = self.disWidget.blockSignals(True)

                self.__disassembleObject(codeObject, self.disWidget, filename)
                QTimer.singleShot(0, self.__resizeDisColumns)

                self.disWidget.blockSignals(block)
                self.setUpdatesEnabled(True)

    @pyqtSlot(dict)
    def showDisassembly(self, disassembly):
        """
        Public slot to receive a code disassembly from the debug client.

        @param disassembly dictionary containing the disassembly information
        @type dict
        """
        if (
            self.__mode == PythonDisViewerModes.TRACEBACK
            and disassembly
            and "instructions" in disassembly
            and disassembly["instructions"]
        ):
            self.disWidget.clear()

            self.setUpdatesEnabled(False)
            block = self.disWidget.blockSignals(True)

            titleItem = self.__createTitleItem(
                self.tr("Disassembly of last traceback"),
                disassembly["firstlineno"],
                self.disWidget,
            )

            lasti = disassembly["lasti"]
            lastStartItem = None
            for instrDict in disassembly["instructions"]:
                instr = (
                    dis.Instruction(
                        instrDict["opname"],
                        0,  # dummy value
                        instrDict["arg"],
                        "",  # dummy value
                        instrDict["argrepr"],
                        instrDict["offset"],
                        instrDict["lineno"],
                        instrDict["isJumpTarget"],
                    )
                    if sys.version_info < (3, 13, 0)
                    else dis.Instruction(
                        instrDict["opname"],
                        0,  # dummy value
                        instrDict["arg"],
                        "",  # dummy value
                        instrDict["argrepr"],
                        instrDict["offset"],
                        instrDict["offset"],
                        instrDict["starts_line"],
                        instrDict["lineno"],
                        instrDict["label"] if instrDict["label"] else None,
                    )
                )
                if instrDict["lineno"] > 0:
                    if lastStartItem:
                        self.__updateItemEndLine(lastStartItem)
                    lastStartItem = self.__createInstructionItem(
                        instr, titleItem, lasti=lasti
                    )
                else:
                    self.__createInstructionItem(instr, lastStartItem, lasti=lasti)
            if lastStartItem:
                self.__updateItemEndLine(lastStartItem)

            QTimer.singleShot(0, self.__resizeDisColumns)

            self.disWidget.blockSignals(block)
            self.setUpdatesEnabled(True)

            if lasti:
                lastInstructions = self.disWidget.findItems(
                    "{0:d}".format(lasti),
                    Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchRecursive,
                    1,
                )
                if lastInstructions:
                    self.disWidget.scrollToItem(
                        lastInstructions[0],
                        QAbstractItemView.ScrollHint.PositionAtCenter,
                    )

            if "codeinfo" in disassembly:
                self.__showCodeInfoData(disassembly["codeinfo"])

    def __resizeDisColumns(self):
        """
        Private method to resize the columns of the disassembly widget to
        suitable values.
        """
        for col in range(self.disWidget.columnCount()):
            self.disWidget.resizeColumnToContents(col)

    def resizeEvent(self, _evt):
        """
        Protected method to handle resize events.

        @param _evt resize event (unused)
        @type QResizeEvent
        """
        # just adjust the sizes of the columns
        self.__resizeDisColumns()
        self.__resizeCodeInfoColumns()

    def __clearSelection(self):
        """
        Private method to clear all selected items.
        """
        for itm in self.disWidget.selectedItems():
            itm.setSelected(False)

    def __selectChildren(self, itm, lineno):
        """
        Private method to select children of the given item covering the given
        line number.

        @param itm reference to the item
        @type QTreeWidgetItem
        @param lineno line number to base the selection on
        @type int
        """
        for index in range(itm.childCount()):
            child = itm.child(index)
            if (
                child.data(0, self.StartLineRole)
                <= lineno
                <= child.data(0, self.EndLineRole)
            ):
                child.setSelected(True)
                self.__selectChildren(child, lineno)

            if child.data(0, self.StartLineRole) == lineno:
                self.disWidget.scrollToItem(
                    child, QAbstractItemView.ScrollHint.PositionAtCenter
                )

    def __selectItemForEditorLine(self):
        """
        Private slot to select the items corresponding with the cursor line
        of the current editor.
        """
        # step 1: clear all selected items
        self.__clearSelection()

        # step 2: retrieve the editor cursor line
        cline, _cindex = self.__editor.getCursorPosition()
        # make the line numbers 1-based
        cline += 1

        for index in range(self.disWidget.topLevelItemCount()):
            itm = self.disWidget.topLevelItem(index)
            if (
                itm.data(0, self.StartLineRole)
                <= cline
                <= itm.data(0, self.EndLineRole)
            ):
                itm.setSelected(True)
                self.__selectChildren(itm, cline)

    @pyqtSlot(QTreeWidgetItem, int)
    def __disItemClicked(self, itm, _column):
        """
        Private slot handling a user click on a Disassembly node item.

        @param itm reference to the clicked item
        @type QTreeWidgetItem
        @param _column column number of the click (unused)
        @type int
        """
        self.__editor.clearAllHighlights()

        if itm is not None:
            startLine = itm.data(0, self.StartLineRole)
            endLine = itm.data(0, self.EndLineRole)

            self.__editor.gotoLine(startLine, firstVisible=True, expand=True)
            self.__editor.setHighlight(startLine - 1, 0, endLine, -1)

    def __disassembleObject(self, co, parentItem, parentName="", lasti=-1):
        """
        Private method to disassemble the given code object recursively.

        @param co code object to be disassembled
        @type code object
        @param parentItem reference to the parent item
        @type QTreeWidget or QTreeWidgetItem
        @param parentName name of the parent code object
        @type str
        @param lasti index of the instruction of a traceback
        @type int
        """
        if co.co_name == "<module>":
            title = os.path.basename(co.co_filename)
            name = ""
        else:
            if parentName:
                name = "{0}.{1}".format(parentName, co.co_name)
            else:
                name = co.co_name
            title = self.tr("Code Object '{0}'").format(name)
        titleItem = self.__createTitleItem(title, co.co_firstlineno, parentItem)
        codeInfo = self.__createCodeInfo(co)
        if codeInfo:
            titleItem.setData(0, self.CodeInfoRole, codeInfo)

        lastStartItem = None
        for instr in dis.get_instructions(co):
            if instr.starts_line:
                if lastStartItem:
                    self.__updateItemEndLine(lastStartItem)
                lastStartItem = self.__createInstructionItem(
                    instr, titleItem, lasti=lasti
                )
            else:
                self.__createInstructionItem(instr, lastStartItem, lasti=lasti)
        if lastStartItem:
            self.__updateItemEndLine(lastStartItem)

        for x in co.co_consts:
            if hasattr(x, "co_code"):
                self.__disassembleObject(x, titleItem, parentName=name, lasti=lasti)

        self.__updateItemEndLine(titleItem)

    @pyqtSlot()
    def preferencesChanged(self):
        """
        Public slot handling changes of the Disassembly viewer settings.
        """
        self.__errorColor = QBrush(Preferences.getPython("DisViewerErrorColor"))
        self.__currentInstructionColor = QBrush(
            Preferences.getPython("DisViewerCurrentColor")
        )
        self.__jumpTargetColor = QBrush(Preferences.getPython("DisViewerLabeledColor"))

        self.__showCodeInfoDetails = Preferences.getPython(
            "DisViewerExpandCodeInfoDetails"
        )

        if self.isVisible():
            self.__loadDIS()

        self.__styleLabels()

    def __styleLabels(self):
        """
        Private method to style the info labels iaw. selected colors.
        """
        # current instruction
        self.currentInfoLabel.setStyleSheet(
            "QLabel {{ color : {0}; }}".format(
                self.__currentInstructionColor.color().name()
            )
        )
        font = self.currentInfoLabel.font()
        font.setItalic(True)
        self.currentInfoLabel.setFont(font)

        # labeled instruction
        self.labeledInfoLabel.setStyleSheet(
            "QLabel {{ color : {0}; }}".format(self.__jumpTargetColor.color().name())
        )
        font = self.labeledInfoLabel.font()
        font.setBold(True)
        self.labeledInfoLabel.setFont(font)

    @pyqtSlot()
    def clear(self):
        """
        Public method to clear the display.
        """
        self.disWidget.clear()
        self.codeInfoWidget.clear()

    def __showCodeInfo(self):
        """
        Private slot handling the context menu action to show code info.
        """
        itm = self.disWidget.currentItem()
        codeInfo = itm.data(0, self.CodeInfoRole)
        if codeInfo:
            self.codeInfoWidget.show()
            self.__showCodeInfoData(codeInfo)

    def __showCodeInfoData(self, codeInfo):
        """
        Private method to show the passed code info data.

        @param codeInfo dictionary containing the code info data
        @type dict
        """

        def createCodeInfoItems(title, infoList):
            """
            Function to create code info items for the given list.

            @param title title string for the list
            @type str
            @param infoList list of info strings
            @type list of str
            """
            parent = QTreeWidgetItem(self.codeInfoWidget, [title, str(len(infoList))])
            parent.setExpanded(self.__showCodeInfoDetails)

            for index, value in enumerate(infoList):
                itm = QTreeWidgetItem(parent, [str(index), str(value)])
                itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)

        self.codeInfoWidget.clear()

        if codeInfo:
            QTreeWidgetItem(self.codeInfoWidget, [self.tr("Name"), codeInfo["name"]])
            QTreeWidgetItem(
                self.codeInfoWidget, [self.tr("Filename"), codeInfo["filename"]]
            )
            QTreeWidgetItem(
                self.codeInfoWidget,
                [self.tr("First Line"), str(codeInfo["firstlineno"])],
            )
            QTreeWidgetItem(
                self.codeInfoWidget,
                [self.tr("Argument Count"), str(codeInfo["argcount"])],
            )
            QTreeWidgetItem(
                self.codeInfoWidget,
                [
                    self.tr("Positional-only Arguments"),
                    str(codeInfo["posonlyargcount"]),
                ],
            )
            QTreeWidgetItem(
                self.codeInfoWidget,
                [self.tr("Keyword-only Arguments"), str(codeInfo["kwonlyargcount"])],
            )
            QTreeWidgetItem(
                self.codeInfoWidget,
                [self.tr("Number of Locals"), str(codeInfo["nlocals"])],
            )
            QTreeWidgetItem(
                self.codeInfoWidget, [self.tr("Stack Size"), str(codeInfo["stacksize"])]
            )
            QTreeWidgetItem(self.codeInfoWidget, [self.tr("Flags"), codeInfo["flags"]])
            if codeInfo["consts"]:
                createCodeInfoItems(self.tr("Constants"), codeInfo["consts"])
            if codeInfo["names"]:
                createCodeInfoItems(self.tr("Names"), codeInfo["names"])
            if codeInfo["varnames"]:
                createCodeInfoItems(self.tr("Variable Names"), codeInfo["varnames"])
            if codeInfo["freevars"]:
                createCodeInfoItems(self.tr("Free Variables"), codeInfo["freevars"])
            if codeInfo["cellvars"]:
                createCodeInfoItems(self.tr("Cell Variables"), codeInfo["cellvars"])

            QTimer.singleShot(0, self.__resizeCodeInfoColumns)

    def __resizeCodeInfoColumns(self):
        """
        Private method to resize the columns of the code info widget to
        suitable values.
        """
        for col in range(self.codeInfoWidget.columnCount()):
            self.codeInfoWidget.resizeColumnToContents(col)

    def __expandAllCodeInfo(self):
        """
        Private slot to expand all items of the code info widget.
        """
        block = self.codeInfoWidget.blockSignals(True)
        self.codeInfoWidget.expandAll()
        self.codeInfoWidget.blockSignals(block)
        self.__resizeCodeInfoColumns()

    def __collapseAllCodeInfo(self):
        """
        Private slot to collapse all items of the code info widget.
        """
        block = self.codeInfoWidget.blockSignals(True)
        self.codeInfoWidget.collapseAll()
        self.codeInfoWidget.blockSignals(block)
        self.__resizeCodeInfoColumns()

    def __codeInfoContextMenuRequested(self, coord):
        """
        Private slot to show the context menu of the code info widget.

        @param coord position of the mouse pointer
        @type QPoint
        """
        if self.disWidget.topLevelItemCount() > 0:
            # don't show context menu on empty list
            coord = self.codeInfoWidget.mapToGlobal(coord)
            self.__codeInfoMenu.popup(coord)

    def __configure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("pythonPage")


def tryCompile(source, name):
    """
    Function to attempt to compile the given source, first as an
    expression and then as a statement if the first approach fails.

    @param source source code string to be compiled
    @type str
    @param name name of the file containing the source
    @type str
    @return compiled code
    @rtype code object
    """
    try:
        c = compile(source, name, "eval")
    except SyntaxError:
        c = compile(source, name, "exec")
    return c


def linestarts(co, filename="", getall=True):
    """
    Function to get the line starts for the given code object.

    @param co reference to the compiled code object or the source code
    @type code object or str
    @param filename name of the source file (optional)
    @type str
    @param getall flag indicating to get all line starts recursively
    @type bool
    @return list of lines starting some byte code instruction block
    @rtype list of int
    """
    if isinstance(co, str):
        # try to compile the given source code first
        try:
            fn = filename if filename else "<dis>"
            co = tryCompile(co, fn)
        except SyntaxError:
            return []

    starts = [inst[1] for inst in dis.findlinestarts(co) if inst[1] is not None]
    if getall:
        for x in co.co_consts:
            if hasattr(x, "co_code"):
                starts.extend(linestarts(x))
    return sorted(starts)
