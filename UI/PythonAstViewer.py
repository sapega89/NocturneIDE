# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to visualize the Python AST for some Python
sources.
"""

import ast

from asttokens import ASTTokens
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QBrush
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor


class PythonAstViewer(QWidget):
    """
    Class implementing a widget to visualize the Python AST for some Python
    sources.
    """

    StartLineRole = Qt.ItemDataRole.UserRole
    StartIndexRole = Qt.ItemDataRole.UserRole + 1
    EndLineRole = Qt.ItemDataRole.UserRole + 2
    EndIndexRole = Qt.ItemDataRole.UserRole + 3

    def __init__(self, viewmanager, parent=None):
        """
        Constructor

        @param viewmanager reference to the viewmanager object
        @type ViewManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__layout = QVBoxLayout(self)
        self.setLayout(self.__layout)
        self.__astWidget = QTreeWidget(self)
        self.__layout.addWidget(self.__astWidget)
        self.__layout.setContentsMargins(0, 0, 0, 0)

        self.__vm = viewmanager
        self.__vmConnected = False

        self.__editor = None
        self.__source = ""

        self.__astWidget.setHeaderLabels([self.tr("Node"), self.tr("Code Range")])
        self.__astWidget.setSortingEnabled(False)
        self.__astWidget.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.__astWidget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.__astWidget.setAlternatingRowColors(True)
        self.__astWidget.setExpandsOnDoubleClick(False)

        self.__errorColor = QBrush(Preferences.getPython("ASTViewerErrorColor"))

        self.__astWidget.itemClicked.connect(self.__astItemClicked)

        self.__vm.astViewerStateChanged.connect(self.__astViewerStateChanged)

        self.hide()

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
                self.__loadAST()

    def __editorSaved(self, editor):
        """
        Private slot to reload the AST after the connected editor was saved.

        @param editor reference to the editor that performed a save action
        @type Editor
        """
        if editor and editor is self.__editor:
            self.__loadAST()

    def __editorDoubleClicked(self, editor, _pos, buttons):
        """
        Private slot to handle a mouse button double click in the editor.

        @param editor reference to the editor, that emitted the signal
        @type Editor
        @param _pos position of the double click (unused)
        @type QPoint
        @param buttons mouse buttons that were double clicked
        @type Qt.MouseButton
        """
        if editor is self.__editor and buttons == Qt.MouseButton.LeftButton:
            if editor.isModified():
                # reload the source
                QTimer.singleShot(0, self.__loadAST)

            # highlight the corresponding entry
            QTimer.singleShot(0, self.__selectItemForEditorSelection)
            QTimer.singleShot(0, self.__grabFocus)

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
        Public slot to show the AST viewer.
        """
        super().show()

        if not self.__vmConnected:
            self.__vm.editorChangedEd.connect(self.__editorChanged)
            self.__vm.editorSavedEd.connect(self.__editorSaved)
            self.__vm.editorDoubleClickedEd.connect(self.__editorDoubleClicked)
            self.__vm.editorLanguageChanged.connect(self.__editorLanguageChanged)
            self.__vmConnected = True

    def hide(self):
        """
        Public slot to hide the AST viewer.
        """
        super().hide()

        if self.__editor:
            self.__editor.clearAllHighlights()

        if self.__vmConnected:
            self.__vm.editorChangedEd.disconnect(self.__editorChanged)
            self.__vm.editorSavedEd.disconnect(self.__editorSaved)
            self.__vm.editorDoubleClickedEd.disconnect(self.__editorDoubleClicked)
            self.__vm.editorLanguageChanged.disconnect(self.__editorLanguageChanged)
            self.__vmConnected = False

    def shutdown(self):
        """
        Public method to perform shutdown actions.
        """
        self.__editor = None

    def __astViewerStateChanged(self, on):
        """
        Private slot to toggle the display of the AST viewer.

        @param on flag indicating to show the AST
        @type bool
        """
        editor = self.__vm.activeWindow()
        if on:
            if editor is not self.__editor:
                self.__editor = editor
            self.show()
            self.__loadAST()
        else:
            self.hide()
            self.__editor = None

    def __createErrorItem(self, error):
        """
        Private method to create a top level error item.

        @param error error message
        @type str
        @return generated item
        @rtype QTreeWidgetItem
        """
        itm = QTreeWidgetItem(self.__astWidget, [error])
        itm.setFirstColumnSpanned(True)
        itm.setForeground(0, self.__errorColor)
        return itm

    def __loadAST(self):
        """
        Private method to generate the AST from the source of the current
        editor and visualize it.
        """
        if not self.__editor:
            self.__createErrorItem(self.tr("No editor has been opened."))
            return

        self.__astWidget.clear()
        self.__editor.clearAllHighlights()

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

        with EricOverrideCursor():
            try:
                # generate the AST
                root = ast.parse(source, self.__editor.getFileName(), "exec")
                self.__markTextRanges(root, source)
                astValid = True
            except Exception as exc:
                self.__createErrorItem(str(exc))
                astValid = False

            if astValid:
                self.setUpdatesEnabled(False)

                # populate the AST tree
                self.__populateNode(self.tr("Module"), root, self.__astWidget)
                self.__selectItemForEditorSelection()
                QTimer.singleShot(0, self.__resizeColumns)

                self.setUpdatesEnabled(True)

        self.__grabFocus()

    def __populateNode(self, name, nodeOrFields, parent):
        """
        Private method to populate the tree view with a node.

        @param name name of the node
        @type str
        @param nodeOrFields reference to the node or a list node fields
        @type ast.AST or list
        @param parent reference to the parent item
        @type QTreeWidget or QTreeWidgetItem
        """
        if isinstance(nodeOrFields, ast.AST):
            fields = [(key, val) for key, val in ast.iter_fields(nodeOrFields)]
            value = nodeOrFields.__class__.__name__
        elif isinstance(nodeOrFields, list):
            fields = list(enumerate(nodeOrFields))
            if len(nodeOrFields) == 0:
                value = "[]"
            else:
                value = "[...]"
        else:
            fields = []
            value = repr(nodeOrFields)

        text = self.tr("{0}: {1}").format(name, value)
        itm = QTreeWidgetItem(parent, [text])
        itm.setExpanded(True)

        if hasattr(nodeOrFields, "lineno") and hasattr(nodeOrFields, "col_offset"):
            itm.setData(0, self.StartLineRole, nodeOrFields.lineno)
            itm.setData(0, self.StartIndexRole, nodeOrFields.col_offset)
            startStr = self.tr("{0},{1}").format(
                nodeOrFields.lineno, nodeOrFields.col_offset
            )
            endStr = ""

            if hasattr(nodeOrFields, "end_lineno") and hasattr(
                nodeOrFields, "end_col_offset"
            ):
                itm.setData(0, self.EndLineRole, nodeOrFields.end_lineno)
                itm.setData(0, self.EndIndexRole, nodeOrFields.end_col_offset)
                endStr = self.tr("{0},{1}").format(
                    nodeOrFields.end_lineno, nodeOrFields.end_col_offset
                )
            else:
                itm.setData(0, self.EndLineRole, nodeOrFields.lineno)
                itm.setData(0, self.EndIndexRole, nodeOrFields.col_offset + 1)
            if endStr:
                rangeStr = self.tr("{0}  -  {1}").format(startStr, endStr)
            else:
                rangeStr = startStr

            itm.setText(1, rangeStr)

        for fieldName, fieldValue in fields:
            self.__populateNode(fieldName, fieldValue, itm)

    def __markTextRanges(self, tree, source):
        """
        Private method to modify the AST nodes with end_lineno and
        end_col_offset information.

        Note: The modifications are only done for nodes containing lineno and
        col_offset attributes.

        @param tree reference to the AST to be modified
        @type ast.AST
        @param source source code the AST was created from
        @type str
        """
        ASTTokens(source, tree=tree)
        for child in ast.walk(tree):
            if hasattr(child, "last_token"):
                child.end_lineno, child.end_col_offset = child.last_token.end
                if hasattr(child, "lineno"):
                    # Fixes problems with some nodes like binop
                    child.lineno, child.col_offset = child.first_token.start

    def __findClosestContainingNode(self, node, textRange):
        """
        Private method to search for the AST node that contains a range
        closest.

        @param node AST node to start searching at
        @type ast.AST
        @param textRange tuple giving the start and end positions
        @type tuple of (int, int, int, int)
        @return best matching node
        @rtype ast.AST
        """
        if textRange in [(-1, -1, -1, -1), (0, -1, 0, -1)]:
            # no valid range, i.e. no selection
            return None

        # first look among children
        for child in ast.iter_child_nodes(node):
            result = self.__findClosestContainingNode(child, textRange)
            if result is not None:
                return result

        # no suitable child was found
        if hasattr(node, "lineno") and self.__rangeContainsSmaller(
            (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset),
            textRange,
        ):
            return node
        else:
            # nope
            return None

    def __findClosestContainingItem(self, itm, textRange):
        """
        Private method to search for the tree item that contains a range
        closest.

        @param itm tree item to start searching at
        @type QTreeWidgetItem
        @param textRange tuple giving the start and end positions
        @type tuple of (int, int, int, int)
        @return best matching tree item
        @rtype QTreeWidgetItem
        """
        if textRange in [(-1, -1, -1, -1), (0, -1, 0, -1)]:
            # no valid range, i.e. no selection
            return None

        lineno = itm.data(0, self.StartLineRole)
        if lineno is not None and not self.__rangeContainsSmallerOrEqual(
            (
                itm.data(0, self.StartLineRole),
                itm.data(0, self.StartIndexRole),
                itm.data(0, self.EndLineRole),
                itm.data(0, self.EndIndexRole),
            ),
            textRange,
        ):
            return None

        # first look among children
        for index in range(itm.childCount()):
            child = itm.child(index)
            result = self.__findClosestContainingItem(child, textRange)
            if result is not None:
                return result

        # no suitable child was found
        lineno = itm.data(0, self.StartLineRole)
        if lineno is not None and self.__rangeContainsSmallerOrEqual(
            (
                itm.data(0, self.StartLineRole),
                itm.data(0, self.StartIndexRole),
                itm.data(0, self.EndLineRole),
                itm.data(0, self.EndIndexRole),
            ),
            textRange,
        ):
            return itm
        else:
            # nope
            return None

    def __resizeColumns(self):
        """
        Private method to resize the columns to suitable values.
        """
        for col in range(self.__astWidget.columnCount()):
            self.__astWidget.resizeColumnToContents(col)

        rangeSize = self.__astWidget.columnWidth(1) + 10
        # 10 px extra for the range
        nodeSize = max(400, self.__astWidget.viewport().width() - rangeSize)
        self.__astWidget.setColumnWidth(0, nodeSize)
        self.__astWidget.setColumnWidth(1, rangeSize)

    def resizeEvent(self, _evt):
        """
        Protected method to handle resize events.

        @param _evt resize event (unused)
        @type QResizeEvent
        """
        # just adjust the sizes of the columns
        self.__resizeColumns()

    def __rangeContainsSmaller(self, first, second):
        """
        Private method to check, if second is contained in first.

        @param first text range to check against
        @type tuple of (int, int, int, int)
        @param second text range to check for
        @type tuple of (int, int, int, int)
        @return flag indicating second is contained in first
        @rtype bool
        """
        firstStart = first[:2]
        firstEnd = first[2:]
        secondStart = second[:2]
        secondEnd = second[2:]

        return (
            (firstStart < secondStart and firstEnd > secondEnd)
            or (firstStart == secondStart and firstEnd > secondEnd)
            or (firstStart < secondStart and firstEnd == secondEnd)
        )

    def __rangeContainsSmallerOrEqual(self, first, second):
        """
        Private method to check, if second is contained in or equal to first.

        @param first text range to check against
        @type tuple of (int, int, int, int)
        @param second text range to check for
        @type tuple of (int, int, int, int)
        @return flag indicating second is contained in or equal to first
        @rtype bool
        """
        return first == second or self.__rangeContainsSmaller(first, second)

    def __clearSelection(self):
        """
        Private method to clear all selected items.
        """
        for itm in self.__astWidget.selectedItems():
            itm.setSelected(False)

    def __selectItemForEditorSelection(self):
        """
        Private slot to select the item corresponding to an editor selection.
        """
        # step 1: clear all selected items
        self.__clearSelection()

        # step 2: retrieve the editor selection
        selection = self.__editor.getSelection()
        # make the line numbers 1-based
        selection = (selection[0] + 1, selection[1], selection[2] + 1, selection[3])

        # step 3: search the corresponding item, scroll to it and select it
        itm = self.__findClosestContainingItem(
            self.__astWidget.topLevelItem(0), selection
        )
        if itm:
            self.__astWidget.scrollToItem(
                itm, QAbstractItemView.ScrollHint.PositionAtCenter
            )
            itm.setSelected(True)

    def __grabFocus(self):
        """
        Private method to grab the input focus.
        """
        self.__astWidget.setFocus(Qt.FocusReason.OtherFocusReason)

    @pyqtSlot(QTreeWidgetItem, int)
    def __astItemClicked(self, itm, _column):
        """
        Private slot handling a user click on an AST node item.

        @param itm reference to the clicked item
        @type QTreeWidgetItem
        @param _column column number of the click (unused)
        @type int
        """
        self.__editor.clearAllHighlights()

        if itm is not None:
            startLine = itm.data(0, self.StartLineRole)
            if startLine is not None:
                startIndex = itm.data(0, self.StartIndexRole)
                endLine = itm.data(0, self.EndLineRole)
                endIndex = itm.data(0, self.EndIndexRole)

                self.__editor.gotoLine(startLine, firstVisible=True, expand=True)
                self.__editor.setHighlight(
                    startLine - 1, startIndex, endLine - 1, endIndex
                )

    @pyqtSlot()
    def preferencesChanged(self):
        """
        Public slot handling changes of the AST viewer settings.
        """
        self.__errorColor = QBrush(Preferences.getPython("ASTViewerErrorColor"))
