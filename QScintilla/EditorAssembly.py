# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the editor assembly widget containing the navigation
combos and the editor widget.
"""

import contextlib

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QComboBox, QGridLayout, QSplitter, QWidget

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Utilities.ModuleParser import Function

from .Editor import Editor
from .EditorButtonsWidget import EditorButtonsWidget
from .EditorOutline import EditorOutlineView


class EditorAssembly(QWidget):
    """
    Class implementing the editor assembly widget containing the navigation
    combos and the editor widget.
    """

    def __init__(self, dbs, fn="", vm=None, filetype="", editor=None, tv=None):
        """
        Constructor

        @param dbs reference to the debug server object
        @type DebugServer
        @param fn name of the file to be opened. If it is None,
            a new (empty) editor is opened.
        @type str
        @param vm reference to the view manager object
        @type ViewManager.ViewManager
        @param filetype type of the source file
        @type str
        @param editor reference to an Editor object, if this is a cloned view
        @type Editor
        @param tv reference to the task viewer object
        @type TaskViewer
        """
        super().__init__()

        self.__layout = QGridLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(1)

        self.__showNavigator = Preferences.getEditor("ShowSourceNavigator")
        self.__showOutline = Preferences.getEditor("ShowSourceOutline")
        self.__outlineSortByOccurrence = Preferences.getEditor(
            "SourceOutlineListContentsByOccurrence"
        )

        self.__editor = Editor(
            dbs=dbs,
            fn=fn,
            vm=vm,
            filetype=filetype,
            editor=editor,
            tv=tv,
            assembly=self,
        )
        self.__buttonsWidget = EditorButtonsWidget(self.__editor, self)
        self.__globalsCombo = QComboBox()
        self.__globalsCombo.setDuplicatesEnabled(True)
        self.__membersCombo = QComboBox()
        self.__membersCombo.setDuplicatesEnabled(True)
        self.__sourceOutline = EditorOutlineView(
            self.__editor, populate=self.__showOutline
        )
        self.__editorSplitter = QSplitter(Qt.Orientation.Horizontal)
        self.__editorSplitter.setChildrenCollapsible(False)
        self.__editorSplitter.addWidget(self.__editor)
        self.__editorSplitter.addWidget(self.__sourceOutline)

        self.__layout.addWidget(self.__buttonsWidget, 1, 0, -1, 1)
        self.__layout.addWidget(self.__globalsCombo, 0, 1)
        self.__layout.addWidget(self.__membersCombo, 0, 2)
        self.__layout.addWidget(self.__editorSplitter, 1, 1, 1, 2)

        self.setFocusProxy(self.__editor)

        self.__module = None

        self.__aboutToBeClosedCalled = False
        self.__parseTimer = QTimer(self)
        self.__parseTimer.setSingleShot(True)
        self.__parseTimer.setInterval(5 * 1000)
        self.__editor.textChanged.connect(self.__resetParseTimer)
        self.__editor.refreshed.connect(self.__resetParseTimer)

        self.__selectedGlobal = ""
        self.__selectedMember = ""
        self.__globalsBoundaries = {}
        self.__membersBoundaries = {}

        self.__activateOutline(self.__showNavigator and self.__showOutline)
        self.__activateCombos(self.__showNavigator and not self.__showOutline)

        ericApp().getObject("UserInterface").preferencesChanged.connect(
            self.__preferencesChanged
        )

    def finishSetup(self):
        """
        Public method to finish the setup of the assembly.
        """
        splitterWidth = self.parent().width() - self.__editorSplitter.handleWidth()
        outlineWidth = Preferences.getEditor("SourceOutlineWidth")
        self.__editorSplitter.setSizes([splitterWidth - outlineWidth, outlineWidth])

    def aboutToBeClosed(self):
        """
        Public method to stop and disconnect the timer and disconnect some signals.
        """
        self.__parseTimer.stop()
        if not self.__aboutToBeClosedCalled:
            self.__editor.textChanged.disconnect(self.__resetParseTimer)
            self.__editor.refreshed.disconnect(self.__resetParseTimer)
            ericApp().getObject("UserInterface").preferencesChanged.disconnect(
                self.__preferencesChanged
            )

            self.__aboutToBeClosedCalled = True

    def getEditor(self):
        """
        Public method to get the reference to the editor widget.

        @return reference to the editor widget
        @rtype Editor
        """
        return self.__editor

    def __preferencesChanged(self):
        """
        Private slot handling a change of preferences.
        """
        showNavigator = Preferences.getEditor("ShowSourceNavigator")
        showOutline = Preferences.getEditor("ShowSourceOutline")
        outlineSortByOccurrence = Preferences.getEditor(
            "SourceOutlineListContentsByOccurrence"
        )

        if self.__outlineSortByOccurrence != outlineSortByOccurrence:
            self.__outlineSortByOccurrence = outlineSortByOccurrence
            if self.__showOutline:
                self.__sourceOutline.repopulate()

        if showOutline != self.__showOutline or showNavigator != self.__showNavigator:
            self.__showOutline = showOutline
            self.__showNavigator = showNavigator
            self.__activateOutline(self.__showNavigator and self.__showOutline)
            self.__activateCombos(self.__showNavigator and not self.__showOutline)

        self.finishSetup()

    #######################################################################
    ## Methods dealing with the navigation combos below
    #######################################################################

    def __activateCombos(self, activate):
        """
        Private slot to activate the navigation combo boxes.

        @param activate flag indicating to activate the combo boxes
        @type bool
        """
        self.__globalsCombo.setVisible(activate)
        self.__membersCombo.setVisible(activate)
        if activate:
            self.__globalsCombo.activated[int].connect(self.__globalsActivated)
            self.__membersCombo.activated[int].connect(self.__membersActivated)
            self.__editor.cursorLineChanged.connect(self.__editorCursorLineChanged)
            self.__parseTimer.timeout.connect(self.__parseEditor)

            self.__parseEditor()

            line, _ = self.__editor.getCursorPosition()
            self.__editorCursorLineChanged(line)
        else:
            with contextlib.suppress(TypeError):
                self.__globalsCombo.activated[int].disconnect(self.__globalsActivated)
                self.__membersCombo.activated[int].disconnect(self.__membersActivated)
                self.__editor.cursorLineChanged.disconnect(
                    self.__editorCursorLineChanged
                )
            with contextlib.suppress(TypeError):
                self.__parseTimer.timeout.disconnect(self.__parseEditor)

            self.__globalsCombo.clear()
            self.__membersCombo.clear()
            self.__globalsBoundaries = {}
            self.__membersBoundaries = {}

    def __globalsActivated(self, index, moveCursor=True):
        """
        Private method to jump to the line of the selected global entry and to
        populate the members combo box.

        @param index index of the selected entry
        @type int
        @param moveCursor flag indicating to move the editor cursor
        @type bool
        """
        # step 1: go to the line of the selected entry
        lineno = self.__globalsCombo.itemData(index)
        if lineno is not None:
            if moveCursor:
                txt = self.__editor.text(lineno - 1).rstrip()
                pos = len(txt.replace(txt.strip(), ""))
                self.__editor.gotoLine(lineno, pos if pos == 0 else pos + 1, True)
                self.__editor.setFocus()

            # step 2: populate the members combo, if the entry is a class
            self.__membersCombo.clear()
            self.__membersBoundaries = {}
            self.__membersCombo.addItem("")
            memberIndex = 0
            entryName = self.__globalsCombo.itemText(index)
            if self.__module:
                if entryName in self.__module.classes:
                    entry = self.__module.classes[entryName]
                elif entryName in self.__module.modules:
                    entry = self.__module.modules[entryName]
                    # step 2.0: add module classes
                    items = []
                    for cl in entry.classes.values():
                        if cl.isPrivate():
                            icon = EricPixmapCache.getIcon("class_private")
                        elif cl.isProtected():
                            icon = EricPixmapCache.getIcon("class_protected")
                        else:
                            icon = EricPixmapCache.getIcon("class")
                        items.append((icon, cl.name, cl.lineno, cl.endlineno))
                    for itm in sorted(items, key=lambda x: (x[1], x[2])):
                        self.__membersCombo.addItem(itm[0], itm[1], itm[2])
                        memberIndex += 1
                        self.__membersBoundaries[(itm[2], itm[3])] = memberIndex
                else:
                    return

                # step 2.1: add class methods
                items = []
                for meth in entry.methods.values():
                    if meth.modifier == Function.Static:
                        icon = EricPixmapCache.getIcon("method_static")
                    elif meth.modifier == Function.Class:
                        icon = EricPixmapCache.getIcon("method_class")
                    elif meth.isPrivate():
                        icon = EricPixmapCache.getIcon("method_private")
                    elif meth.isProtected():
                        icon = EricPixmapCache.getIcon("method_protected")
                    else:
                        icon = EricPixmapCache.getIcon("method")
                    items.append((icon, meth.name, meth.lineno, meth.endlineno))
                for itm in sorted(items, key=lambda x: (x[1], x[2])):
                    self.__membersCombo.addItem(itm[0], itm[1], itm[2])
                    memberIndex += 1
                    self.__membersBoundaries[(itm[2], itm[3])] = memberIndex

                # step 2.2: add class instance attributes
                items = []
                for attr in entry.attributes.values():
                    if attr.isPrivate():
                        icon = EricPixmapCache.getIcon("attribute_private")
                    elif attr.isProtected():
                        icon = EricPixmapCache.getIcon("attribute_protected")
                    else:
                        icon = EricPixmapCache.getIcon("attribute")
                    items.append((icon, attr.name, attr.lineno))
                for itm in sorted(items, key=lambda x: (x[1], x[2])):
                    self.__membersCombo.addItem(itm[0], itm[1], itm[2])

                # step 2.3: add class attributes
                items = []
                icon = EricPixmapCache.getIcon("attribute_class")
                for globalVar in entry.globals.values():
                    items.append((icon, globalVar.name, globalVar.lineno))
                for itm in sorted(items, key=lambda x: (x[1], x[2])):
                    self.__membersCombo.addItem(itm[0], itm[1], itm[2])

    def __membersActivated(self, index, moveCursor=True):
        """
        Private method to jump to the line of the selected members entry.

        @param index index of the selected entry
        @type int
        @param moveCursor flag indicating to move the editor cursor
        @type bool
        """
        lineno = self.__membersCombo.itemData(index)
        if lineno is not None and moveCursor:
            txt = self.__editor.text(lineno - 1).rstrip()
            pos = len(txt.replace(txt.strip(), ""))
            self.__editor.gotoLine(
                lineno, pos if pos == 0 else pos + 1, firstVisible=True, expand=True
            )
            self.__editor.setFocus()

    def __resetParseTimer(self):
        """
        Private slot to reset the parse timer.
        """
        self.__parseTimer.stop()
        self.__parseTimer.start()

    def __parseEditor(self):
        """
        Private method to parse the editor source and repopulate the globals
        combo.
        """
        from eric7.Utilities.ModuleParser import Module, getTypeFromTypeName

        self.__module = None
        sourceType = getTypeFromTypeName(self.__editor.determineFileType())
        if sourceType != -1:
            src = self.__editor.text()
            if src:
                fn = self.__editor.getFileName()
                if fn is None:
                    fn = ""
                self.__module = Module("", fn, sourceType)
                self.__module.scan(src)

                # remember the current selections
                self.__selectedGlobal = self.__globalsCombo.currentText()
                self.__selectedMember = self.__membersCombo.currentText()

                self.__globalsCombo.hidePopup()
                self.__membersCombo.hidePopup()
                self.__globalsCombo.clear()
                self.__membersCombo.clear()
                self.__globalsBoundaries = {}
                self.__membersBoundaries = {}

                self.__globalsCombo.addItem("")
                index = 0  # noqa: Y113

                # step 1: add modules
                items = []
                for module in self.__module.modules.values():
                    items.append(
                        (
                            EricPixmapCache.getIcon("module"),
                            module.name,
                            module.lineno,
                            module.endlineno,
                        )
                    )
                for itm in sorted(items, key=lambda x: (x[1], x[2])):
                    self.__globalsCombo.addItem(itm[0], itm[1], itm[2])
                    index += 1
                    self.__globalsBoundaries[(itm[2], itm[3])] = index

                # step 2: add classes
                items = []
                for cl in self.__module.classes.values():
                    if cl.isPrivate():
                        icon = EricPixmapCache.getIcon("class_private")
                    elif cl.isProtected():
                        icon = EricPixmapCache.getIcon("class_protected")
                    else:
                        icon = EricPixmapCache.getIcon("class")
                    items.append((icon, cl.name, cl.lineno, cl.endlineno))
                for itm in sorted(items, key=lambda x: (x[1], x[2])):
                    self.__globalsCombo.addItem(itm[0], itm[1], itm[2])
                    index += 1
                    self.__globalsBoundaries[(itm[2], itm[3])] = index

                # step 3: add functions
                items = []
                for func in self.__module.functions.values():
                    if func.isPrivate():
                        icon = EricPixmapCache.getIcon("method_private")
                    elif func.isProtected():
                        icon = EricPixmapCache.getIcon("method_protected")
                    else:
                        icon = EricPixmapCache.getIcon("method")
                    items.append((icon, func.name, func.lineno, func.endlineno))
                for itm in sorted(items, key=lambda x: (x[1], x[2])):
                    self.__globalsCombo.addItem(itm[0], itm[1], itm[2])
                    index += 1
                    self.__globalsBoundaries[(itm[2], itm[3])] = index

                # step 4: add attributes
                items = []
                for globalValue in self.__module.globals.values():
                    if globalValue.isPrivate():
                        icon = EricPixmapCache.getIcon("attribute_private")
                    elif globalValue.isProtected():
                        icon = EricPixmapCache.getIcon("attribute_protected")
                    else:
                        icon = EricPixmapCache.getIcon("attribute")
                    items.append((icon, globalValue.name, globalValue.lineno))
                for itm in sorted(items, key=lambda x: (x[1], x[2])):
                    self.__globalsCombo.addItem(itm[0], itm[1], itm[2])

                # reset the currently selected entries without moving the
                # text cursor
                index = self.__globalsCombo.findText(self.__selectedGlobal)
                if index != -1:
                    self.__globalsCombo.setCurrentIndex(index)
                    self.__globalsActivated(index, moveCursor=False)
                index = self.__membersCombo.findText(self.__selectedMember)
                if index != -1:
                    self.__membersCombo.setCurrentIndex(index)
                    self.__membersActivated(index, moveCursor=False)
        else:
            self.__globalsCombo.hidePopup()
            self.__membersCombo.hidePopup()
            self.__globalsCombo.clear()
            self.__membersCombo.clear()
            self.__globalsBoundaries = {}
            self.__membersBoundaries = {}

    def __editorCursorLineChanged(self, lineno):
        """
        Private slot handling a line change of the cursor of the editor.

        @param lineno line number of the cursor
        @type int
        """
        lineno += 1  # cursor position is zero based, code info one based

        # step 1: search in the globals
        indexFound = 0
        for (lower, upper), index in self.__globalsBoundaries.items():
            if upper == -1:
                upper = 1000000  # it is the last line
            if lower <= lineno <= upper:
                indexFound = index
                break
        self.__globalsCombo.setCurrentIndex(indexFound)
        self.__globalsActivated(indexFound, moveCursor=False)

        # step 2: search in members
        indexFound = 0
        for (lower, upper), index in self.__membersBoundaries.items():
            if upper == -1:
                upper = 1000000  # it is the last line
            if lower <= lineno <= upper:
                indexFound = index
                break
        self.__membersCombo.setCurrentIndex(indexFound)
        self.__membersActivated(indexFound, moveCursor=False)

    #######################################################################
    ## Methods dealing with the source outline below
    #######################################################################

    def __activateOutline(self, activate):
        """
        Private slot to activate the source outline view.

        @param activate flag indicating to activate the source outline view
        @type bool
        """
        self.__sourceOutline.setActive(activate)

        if activate:
            self.__sourceOutline.setVisible(
                self.__sourceOutline.isSupportedLanguage(self.__editor.getLanguage())
            )

            self.__parseTimer.timeout.connect(self.__sourceOutline.repopulate)
            self.__editor.languageChanged.connect(self.__editorChanged)
            self.__editor.editorRenamed.connect(self.__editorChanged)
        else:
            self.__sourceOutline.hide()

            with contextlib.suppress(TypeError):
                self.__parseTimer.timeout.disconnect(self.__sourceOutline.repopulate)
                self.__editor.languageChanged.disconnect(self.__editorChanged)
                self.__editor.editorRenamed.disconnect(self.__editorChanged)

    def __editorChanged(self):
        """
        Private slot handling changes of the editor language or file name.
        """
        supported = self.__sourceOutline.isSupportedLanguage(
            self.__editor.getLanguage()
        )

        self.__sourceOutline.setVisible(supported)
