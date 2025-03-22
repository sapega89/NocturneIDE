# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a toolbar manager class.
"""

import contextlib

from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QDataStream,
    QIODevice,
    QObject,
    QSize,
)
from PyQt6.QtWidgets import QStyle, QToolBar

from eric7 import EricUtilities


class EricToolBarManager(QObject):
    """
    Class implementing a toolbar manager.
    """

    VersionMarker = 0xFFFF
    ToolBarMarker = 0xFEFE
    CustomToolBarMarker = 0xFDFD

    IconSizes = {
        # tuples with (icon size, translated size string)
        "": (
            0,
            QCoreApplication.translate(
                "EricToolBarManager", "default (style dependent)"
            ),
        ),
        "xs": (
            16,
            QCoreApplication.translate("EricToolBarManager", "extra small (16 px)"),
        ),
        "sm": (22, QCoreApplication.translate("EricToolBarManager", "small (22 px)")),
        "md": (32, QCoreApplication.translate("EricToolBarManager", "medium (32 px)")),
        "lg": (48, QCoreApplication.translate("EricToolBarManager", "large (48 px)")),
        "xl": (
            64,
            QCoreApplication.translate("EricToolBarManager", "extra large (64 px)"),
        ),
    }

    def __init__(self, ui=None, iconSize="", parent=None):
        """
        Constructor

        @param ui reference to the user interface object (defaults to None)
        @type UI.UserInterface (optional)
        @param iconSize string giving the icon size (one of the sizes defined by the
            IconSizes dictionary) (defaults to "")
        @type str (optional)
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__mainWindow = None
        self.__ui = ui
        self.__iconSizeStr = iconSize

        self.__toolBars = {}
        # maps toolbar IDs to actions
        self.__toolBarsWithSeparators = {}
        # maps toolbar IDs to actions incl. separators
        self.__defaultToolBars = {}
        # maps default toolbar IDs to actions
        self.__customToolBars = []
        # list of custom toolbars
        self.__allToolBars = {}
        # maps toolbar IDs to toolbars

        self.__categoryToActions = {}
        # maps categories to actions
        self.__actionToCategory = {}
        # maps action IDs to categories
        self.__allActions = {}
        # maps action IDs to actions
        self.__actionToToolBars = {}
        # maps action IDs to toolbars

        self.__widgetActions = {}
        # maps widget action IDs to toolbars
        self.__allWidgetActions = {}
        # maps widget action IDs to widget actions

    ######################################################
    ## Private methods
    ######################################################

    def __toolBarByName(self, name):
        """
        Private slot to get a toolbar by its object name.

        @param name object name of the toolbar
        @type str
        @return reference to the toolbar
        @rtype QToolBar
        """
        for toolBar in self.__allToolBars.values():
            if toolBar.objectName() == name:
                return toolBar
        return None

    def __findAction(self, name):
        """
        Private method to find an action by name.

        @param name name of the action to search for
        @type str
        @return reference to the action
        @rtype QAction
        """
        # check objectName() first
        for action in self.__allActions.values():
            if action.objectName() == name:
                return action

        # check text() next
        for action in self.__allActions.values():
            if action.text() == name:
                return action

        return None

    def __findDefaultToolBar(self, name):
        """
        Private method to find a default toolbar by name.

        @param name name of the default toolbar to search for
        @type str
        @return reference to the default toolbar
        @rtype QToolBar
        """
        # check objectName() first
        for tbID in self.__defaultToolBars:
            tb = self.__allToolBars[tbID]
            if tb.objectName() == name:
                return tb

        # check windowTitle() next
        for tbID in self.__defaultToolBars:
            tb = self.__allToolBars[tbID]
            if tb.windowTitle() == name:
                return tb

        return None

    ######################################################
    ## Public methods
    ######################################################

    def setMainWindow(self, mainWindow):
        """
        Public method to set the reference to the main window.

        @param mainWindow reference to the main window
        @type QMainWindow
        """
        self.__mainWindow = mainWindow

    def mainWindow(self):
        """
        Public method to get the reference to the main window.

        @return reference to the main window
        @rtype QMainWindow
        """
        return self.__mainWindow

    def addToolBar(self, toolBar, category):
        """
        Public method to add a toolbar to be managed.

        @param toolBar reference to the toolbar to be managed
        @type QToolBar
        @param category category for the toolbar
        @type str
        """
        if toolBar is None:
            return

        if self.__iconSizeStr:
            with contextlib.suppress(KeyError):
                iconSize = EricToolBarManager.IconSizes[self.__iconSizeStr][0]
                toolBar.setIconSize(QSize(iconSize, iconSize))

        newActions = []
        newActionsWithSeparators = []
        actions = toolBar.actions()
        for action in actions:
            actID = id(action)
            self.addAction(action, category)
            if actID in self.__widgetActions:
                self.__widgetActions[actID] = toolBar
            newActionsWithSeparators.append(action)
            if action.isSeparator():
                action = None
            else:
                if toolBar not in self.__actionToToolBars[actID]:
                    self.__actionToToolBars[actID].append(toolBar)
            newActions.append(action)
        tbID = id(toolBar)
        self.__defaultToolBars[tbID] = newActions
        self.__toolBars[tbID] = newActions
        self.__toolBarsWithSeparators[tbID] = newActionsWithSeparators
        self.__allToolBars[tbID] = toolBar

    def removeToolBar(self, toolBar):
        """
        Public method to remove a toolbar added with addToolBar().

        @param toolBar reference to the toolbar to be removed
        @type QToolBar
        """
        if toolBar is None:
            return

        tbID = id(toolBar)

        if tbID not in self.__defaultToolBars:
            return

        defaultActions = self.__defaultToolBars[tbID][:]
        self.setToolBar(toolBar, [])
        for action in defaultActions:
            self.removeAction(action)

        del self.__defaultToolBars[tbID]
        del self.__toolBars[tbID]
        del self.__toolBarsWithSeparators[tbID]
        del self.__allToolBars[tbID]

        for action in defaultActions:
            if action is None:
                toolBar.addSeparator()
            else:
                toolBar.addAction(action)

    def setToolBars(self, toolBars):
        """
        Public method to set the actions of several toolbars.

        @param toolBars dictionary with toolbar id as key and
            a list of actions as value
        @type dict
        """
        for key, actions in toolBars.items():
            tb = self.__allToolBars[key]
            self.setToolBar(tb, actions)

    def setToolBar(self, toolBar, actions):
        """
        Public method to set the actions of a toolbar.

        @param toolBar reference to the toolbar to configure
        @type QToolBar
        @param actions list of actions to be set
        @type list of QAction
        """
        if toolBar is None:
            return

        tbID = id(toolBar)
        if tbID not in self.__toolBars:
            return
        if self.__toolBars[tbID] == actions:
            return

        # step 1: check list of actions
        toRemove = {}
        newActions = []
        for action in actions:
            if action is None or (
                action not in newActions and id(action) in self.__allActions
            ):
                newActions.append(action)
            oldTB = self.toolBarWidgetAction(action)
            if oldTB is not None and oldTB != toolBar:
                if id(oldTB) not in toRemove:
                    toRemove[id(oldTB)] = []
                toRemove[id(oldTB)].append(action)
        self.removeWidgetActions(toRemove)

        # step 2: remove all toolbar actions
        for action in self.__toolBarsWithSeparators[tbID]:
            if self.toolBarWidgetAction(action) == tbID:
                self.__widgetActions[id(action)] = None
            toolBar.removeAction(action)
            if action.isSeparator():
                del action
            else:
                self.__actionToToolBars[id(action)].remove(toolBar)

        # step 3: set the actions as requested
        newActionsWithSeparators = []
        for action in newActions:
            newAction = None
            if action is None:
                newAction = toolBar.addSeparator()
            elif id(action) in self.__allActions:
                toolBar.addAction(action)
                newAction = action
                self.__actionToToolBars[id(action)].append(toolBar)
                if id(action) in self.__widgetActions:
                    self.__widgetActions[id(action)] = toolBar
            else:
                continue
            newActionsWithSeparators.append(newAction)

        if toolBar.isVisible():
            toolBar.hide()
            toolBar.show()
        self.__toolBars[tbID] = newActions
        self.__toolBarsWithSeparators[tbID] = newActionsWithSeparators

    def resetToolBar(self, toolBar):
        """
        Public method to reset a toolbar to its default state.

        @param toolBar reference to the toolbar to configure
        @type QToolBar
        """
        if not self.isDefaultToolBar():
            return
        self.setToolBar(toolBar, self.__defaultToolBars[id(toolBar)])

    def resetAllToolBars(self):
        """
        Public method to reset all toolbars to their default state.
        """
        self.setToolBars(self.__defaultToolBars)
        for toolBar in self.__customToolBars[:]:
            self.deleteToolBar(toolBar)

    def defaultToolBars(self):
        """
        Public method to get all toolbars added with addToolBar().

        @return list of all default toolbars
        @rtype list of QToolBar
        """
        return list(self.__defaultToolBars.values())

    def isDefaultToolBar(self, toolBar):
        """
        Public method to check, if a toolbar was added with addToolBar().

        @param toolBar reference to the toolbar to be checked
        @type QToolBar
        @return flag indicating an added toolbar
        @rtype bool
        """
        return toolBar is not None and id(toolBar) in self.__defaultToolBars

    def createToolBar(self, title, name=""):
        """
        Public method to create a custom toolbar.

        @param title title to be used for the toolbar
        @type str
        @param name optional name for the new toolbar
        @type str
        @return reference to the created toolbar
        @rtype QToolBar
        """
        if self.__mainWindow is None:
            return None

        toolBar = QToolBar(title, self.__mainWindow)
        toolBar.setToolTip(title)
        if not name:
            index = 1
            customPrefix = "__CustomPrefix__"
            name = "{0}{1:d}".format(customPrefix, index)
            while self.__toolBarByName(name) is not None:
                index += 1
                name = "{0}{1:d}".format(customPrefix, index)
        toolBar.setObjectName(name)
        self.__mainWindow.addToolBar(toolBar)

        tbID = id(toolBar)
        self.__customToolBars.append(toolBar)
        self.__allToolBars[tbID] = toolBar
        self.__toolBars[tbID] = []
        self.__toolBarsWithSeparators[tbID] = []

        if self.__ui is not None:
            self.__ui.registerToolbar(name, title, toolBar)

        return toolBar

    def deleteToolBar(self, toolBar):
        """
        Public method to remove a custom toolbar created with createToolBar().

        @param toolBar reference to the toolbar to be managed
        @type QToolBar
        """
        if toolBar is None:
            return

        tbID = id(toolBar)
        if tbID not in self.__toolBars:
            return
        if tbID in self.__defaultToolBars:
            return

        if self.__ui is not None:
            self.__ui.unregisterToolbar(toolBar.objectName())

        self.setToolBar(toolBar, [])

        del self.__allToolBars[tbID]
        del self.__toolBars[tbID]
        del self.__toolBarsWithSeparators[tbID]
        self.__customToolBars.remove(toolBar)
        self.__mainWindow.removeToolBar(toolBar)
        del toolBar

    def renameToolBar(self, toolBar, title):
        """
        Public method to give a toolbar a new title.

        @param toolBar reference to the toolbar to be managed
        @type QToolBar
        @param title title to be used for the toolbar
        @type str
        """
        if toolBar is None:
            return

        toolBar.setWindowTitle(title)

        if self.__ui is not None:
            self.__ui.reregisterToolbar(toolBar.objectName(), title)

    def toolBars(self):
        """
        Public method to get all toolbars.

        @return list of all toolbars
        @rtype list of QToolBar
        """
        return list(self.__allToolBars.values())

    def addAction(self, action, category):
        """
        Public method to add an action to be managed.

        @param action reference to the action to be managed
        @type QAction
        @param category category for the toolbar
        @type str
        """
        if action is None:
            return
        if action.isSeparator():
            return
        if id(action) in self.__allActions:
            return

        if action.metaObject().className() == "QWidgetAction":
            self.__widgetActions[id(action)] = None
            self.__allWidgetActions[id(action)] = action
        self.__allActions[id(action)] = action
        if category not in self.__categoryToActions:
            self.__categoryToActions[category] = []
        self.__categoryToActions[category].append(action)
        self.__actionToCategory[id(action)] = category
        self.__actionToToolBars[id(action)] = []

    def addActions(self, actions, category):
        """
        Public method to add actions to be managed.

        @param actions list of actions to be managed
        @type list of QAction
        @param category category for the toolbar
        @type str
        """
        for action in actions:
            self.addAction(action, category)

    def removeAction(self, action):
        """
        Public method to remove an action from the manager.

        @param action reference to the action to be removed
        @type QAction
        """
        aID = id(action)

        if aID not in self.__allActions:
            return

        toolBars = self.__actionToToolBars[aID]
        for toolBar in toolBars:
            tbID = id(toolBar)
            self.__toolBars[tbID].remove(action)
            self.__toolBarsWithSeparators[tbID].remove(action)
            toolBar.removeAction(action)
            if toolBar.isVisible():
                toolBar.hide()
                toolBar.show()

        for tbID in self.__defaultToolBars:
            if action in self.__defaultToolBars[tbID]:
                self.__defaultToolBars[tbID].remove(action)

        del self.__allActions[aID]
        if aID in self.__widgetActions:
            del self.__widgetActions[aID]
            del self.__allWidgetActions[aID]
        del self.__actionToCategory[aID]
        del self.__actionToToolBars[aID]

        for category in self.__categoryToActions:
            if action in self.__categoryToActions[category]:
                self.__categoryToActions[category].remove(action)

    def removeCategoryActions(self, category):
        """
        Public method to remove the actions belonging to a category.

        @param category category for the actions
        @type str
        """
        for action in self.categoryActions(category):
            self.removeAction(action)

    def saveState(self, version=0):
        """
        Public method to save the state of the toolbar manager.

        @param version version number stored with the data
        @type int
        @return saved state as a byte array
        @rtype QByteArray
        """
        data = QByteArray()
        stream = QDataStream(data, QIODevice.OpenModeFlag.WriteOnly)
        stream.setVersion(QDataStream.Version.Qt_4_6)
        stream.writeUInt16(EricToolBarManager.VersionMarker)
        stream.writeUInt16(version)

        # save default toolbars
        stream.writeUInt16(EricToolBarManager.ToolBarMarker)
        stream.writeUInt16(len(self.__defaultToolBars))
        for tbID in self.__defaultToolBars:
            tb = self.__allToolBars[tbID]
            if tb.objectName():
                stream.writeString(tb.objectName().encode("utf-8"))
            else:
                stream.writeString(tb.windowTitle().encode("utf-8"))
            stream.writeUInt16(len(self.__toolBars[tbID]))
            for action in self.__toolBars[tbID]:
                if action is not None:
                    if action.objectName():
                        stream.writeString(action.objectName().encode("utf-8"))
                    else:
                        stream.writeString(action.text().encode("utf-8"))
                else:
                    stream.writeString("".encode("utf-8"))

        # save the custom toolbars
        stream.writeUInt16(EricToolBarManager.CustomToolBarMarker)
        stream.writeUInt16(len(self.__toolBars) - len(self.__defaultToolBars))
        for tbID in self.__toolBars:
            if tbID not in self.__defaultToolBars:
                tb = self.__allToolBars[tbID]
                stream.writeString(tb.objectName().encode("utf-8"))
                stream.writeString(tb.windowTitle().encode("utf-8"))
                stream.writeUInt16(len(self.__toolBars[tbID]))
                for action in self.__toolBars[tbID]:
                    if action is not None:
                        if action.objectName():
                            stream.writeString(action.objectName().encode("utf-8"))
                        else:
                            stream.writeString(action.text().encode("utf-8"))
                    else:
                        stream.writeString("".encode("utf-8"))

        return data

    def restoreState(self, state, version=0):
        """
        Public method to restore the state of the toolbar manager.

        @param state byte array containing the saved state
        @type QByteArray
        @param version version number stored with the data
        @type int
        @return flag indicating success
        @rtype bool
        """
        if state.isEmpty():
            return False

        data = QByteArray(state)
        stream = QDataStream(data, QIODevice.OpenModeFlag.ReadOnly)
        stream.setVersion(QDataStream.Version.Qt_4_6)
        marker = stream.readUInt16()
        vers = stream.readUInt16()
        if marker != EricToolBarManager.VersionMarker or vers != version:
            return False

        tmarker = stream.readUInt16()
        if tmarker != EricToolBarManager.ToolBarMarker:
            return False

        toolBarCount = stream.readUInt16()
        for _i in range(toolBarCount):
            objectName = EricUtilities.readStringFromStream(stream)
            actionCount = stream.readUInt16()
            actions = []
            for _j in range(actionCount):
                actionName = EricUtilities.readStringFromStream(stream)
                if actionName:
                    action = self.__findAction(actionName)
                    if action is not None:
                        actions.append(action)
                else:
                    actions.append(None)
            toolBar = self.__findDefaultToolBar(objectName)
            if toolBar is not None:
                self.setToolBar(toolBar, actions)

        cmarker = stream.readUInt16()
        if cmarker != EricToolBarManager.CustomToolBarMarker:
            return False

        oldCustomToolBars = self.__customToolBars[:]

        toolBarCount = stream.readUInt16()
        for _i in range(toolBarCount):
            objectName = EricUtilities.readStringFromStream(stream)
            toolBarTitle = EricUtilities.readStringFromStream(stream)
            actionCount = stream.readUInt16()
            actions = []
            for _j in range(actionCount):
                actionName = EricUtilities.readStringFromStream(stream)
                if actionName:
                    action = self.__findAction(actionName)
                    if action is not None:
                        actions.append(action)
                else:
                    actions.append(None)
            toolBar = self.__toolBarByName(objectName)
            if toolBar is not None:
                toolBar.setWindowTitle(toolBarTitle)
                oldCustomToolBars.remove(toolBar)
            else:
                toolBar = self.createToolBar(toolBarTitle, objectName)
            if toolBar is not None:
                toolBar.setObjectName(objectName)
                self.setToolBar(toolBar, actions)

        for tb in oldCustomToolBars:
            self.deleteToolBar(tb)

        return True

    def toolBarWidgetAction(self, action):
        """
        Public method to get the toolbar for a widget action.

        @param action widget action to check for
        @type QAction
        @return reference to the toolbar containing action
        @rtype QToolBar
        """
        aID = id(action)
        if aID in self.__widgetActions:
            return self.__widgetActions[aID]
        return None

    def removeWidgetActions(self, actions):
        """
        Public method to remove widget actions.

        @param actions dictionary with toolbar id as key and
            a list of widget actions as value
        @type dict
        """
        for tbID in list(actions):
            toolBar = self.__allToolBars[tbID]
            newActions = self.__toolBars[tbID][:]
            newActionsWithSeparators = self.__toolBarsWithSeparators[tbID][:]

            removedActions = []
            for action in actions[tbID]:
                if action in newActions and self.toolBarWidgetAction(action) == toolBar:
                    newActions.remove(action)
                    newActionsWithSeparators.remove(action)
                    removedActions.append(action)

            self.__toolBars[tbID] = newActions
            self.__toolBarsWithSeparators[tbID] = newActionsWithSeparators

            for action in removedActions:
                self.__widgetActions[id(action)] = None
                self.__actionToToolBars[id(action)].remove(toolBar)
                toolBar.removeAction(action)

    def isWidgetAction(self, action):
        """
        Public method to check, if action is a widget action.

        @param action reference to the action to be checked
        @type QAction
        @return flag indicating a widget action
        @rtype bool
        """
        return id(action) in self.__allWidgetActions

    def categories(self):
        """
        Public method to get the list of categories.

        @return list of categories
        @rtype list of str
        """
        return list(self.__categoryToActions)

    def categoryActions(self, category):
        """
        Public method to get the actions belonging to a category.

        @param category category for the actions
        @type str
        @return list of actions
        @rtype list of QAction
        """
        if category not in self.__categoryToActions:
            return []

        return self.__categoryToActions[category][:]

    def actionById(self, aID):
        """
        Public method to get an action given its id.

        @param aID id of the action object
        @type int
        @return reference to the action
        @rtype QAction
        """
        if aID not in self.__allActions:
            return None
        return self.__allActions[aID]

    def toolBarById(self, tbID):
        """
        Public method to get a toolbar given its id.

        @param tbID id of the toolbar object
        @type int
        @return reference to the toolbar
        @rtype QToolBar
        """
        if tbID not in self.__allToolBars:
            return None
        return self.__allToolBars[tbID]

    def toolBarActions(self, tbID):
        """
        Public method to get a toolbar's actions given its id.

        @param tbID id of the toolbar object
        @type int
        @return list of actions
        @rtype list of QAction
        """
        if tbID not in self.__toolBars:
            return []
        return self.__toolBars[tbID][:]

    def toolBarsActions(self):
        """
        Public method to get all toolbars and their actions.

        @return reference to dictionary of toolbar IDs as key and list
            of actions as values
        @rtype dict
        """
        return self.__toolBars

    def defaultToolBarActions(self, tbID):
        """
        Public method to get a default toolbar's actions given its id.

        @param tbID id of the default toolbar object
        @type int
        @return list of actions
        @rtype list of QAction
        """
        if tbID not in self.__defaultToolBars:
            return []
        return self.__defaultToolBars[tbID][:]

    def setIconSize(self, iconSize):
        """
        Public method to set the icon size.

        @param iconSize string giving the icon size (one of the sizes defined by the
            IconSizes dictionary)
        @type str
        """
        self.__iconSizeStr = iconSize
        if self.__iconSizeStr:
            try:
                iconSize = EricToolBarManager.IconSizes[self.__iconSizeStr][0]
            except KeyError:
                # determine icon size through the style
                iconSize = (
                    list(self.__allToolBars.items()[0])
                    .style()
                    .pixelMetric(QStyle.PixelMetric.PM_ToolBarIconSize)
                )
        else:
            # determine icon size through the style
            iconSize = (
                list(self.__allToolBars.values())[0]
                .style()
                .pixelMetric(QStyle.PixelMetric.PM_ToolBarIconSize)
            )

        for tbID in self.__allToolBars:
            self.__allToolBars[tbID].setIconSize(QSize(iconSize, iconSize))
