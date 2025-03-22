# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an Action class extending QAction.

This extension is necessary in order to support alternate keyboard
shortcuts.
"""

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QAction, QActionGroup, QIcon, QKeySequence


class ArgumentsError(RuntimeError):
    """
    Class implementing an exception, which is raised, if the wrong number of
    arguments are given.
    """

    def __init__(self, error):
        """
        Constructor

        @param error error message of the exception
        @type str
        """
        self.errorMessage = str(error)

    def __repr__(self):
        """
        Special method returning a representation of the exception.

        @return string representing the error message
        @rtype str
        """
        return str(self.errorMessage)

    def __str__(self):
        """
        Special method returning a string representation of the exception.

        @return string representing the error message
        @rtype str
        """
        return str(self.errorMessage)


class EricAction(QAction):
    """
    Class implementing an Action class extending QAction.
    """

    def __init__(self, *args):
        """
        Constructor

        @param args argument list of the constructor. This list is one of
            <ul>
            <li>text, icon, menu text, accelarator, alternative accelerator, parent,
                name, toggle</li>
            <li>text, icon, menu text, accelarator, alternative accelerator, parent,
                name</li>
            <li>text, menu text, accelarator, alternative accelerator, parent, name,
                toggle</li>
            <li>text, menu text, accelarator, alternative accelerator, parent, name</li>
            </ul>
        @type list of one of the following
            <ul>
            <li>str, QIcon, str, QKeySequence, QKeySequence, QObject, str, bool</li>
            <li>str, QIcon, str, QKeySequence, QKeySequemce, QObject, str</li>
            <li>str, str, QKeySequence, QKeySequence, QObject, str, bool</li>
            <li>str, str, QKeySequence, QKeySequence, QObject, str</li>
            </ul>
        @exception ArgumentsError raised to indicate invalid arguments
        """
        if isinstance(args[1], QIcon):
            icon = args[1]
            incr = 1
        else:
            icon = None
            incr = 0
        if len(args) < 6 + incr:
            raise ArgumentsError(
                "Not enough arguments, {0:d} expected, got {1:d}".format(
                    6 + incr, len(args)
                )
            )
        elif len(args) > 7 + incr:
            raise ArgumentsError(
                "Too many arguments, max. {0:d} expected, got {1:d}".format(
                    7 + incr, len(args)
                )
            )

        parent = args[4 + incr]
        super().__init__(parent)
        name = args[5 + incr]
        if name:
            self.setObjectName(name)

        if args[1 + incr]:
            self.setText(args[1 + incr])

        if args[0]:
            self.setIconText(args[0])
        if args[2 + incr]:
            self.setShortcut(QKeySequence(args[2 + incr]))

        if args[3 + incr]:
            self.setAlternateShortcut(QKeySequence(args[3 + incr]))

        if icon:
            self.setIcon(icon)

        if len(args) == 7 + incr:
            self.setCheckable(args[6 + incr])

        self.__ammendToolTip()

    def setAlternateShortcut(self, shortcut, removeEmpty=False):
        """
        Public slot to set the alternative keyboard shortcut.

        @param shortcut the alternative accelerator
        @type QKeySequence
        @param removeEmpty flag indicating to remove the alternate shortcut,
            if it is empty
        @type bool
        """
        if not shortcut.isEmpty():
            shortcuts = self.shortcuts()
            if len(shortcuts) > 0:
                if len(shortcuts) == 1:
                    shortcuts.append(shortcut)
                else:
                    shortcuts[1] = shortcut
                self.setShortcuts(shortcuts)
        elif removeEmpty:
            shortcuts = self.shortcuts()
            if len(shortcuts) == 2:
                del shortcuts[1]
                self.setShortcuts(shortcuts)

    def alternateShortcut(self):
        """
        Public method to retrieve the alternative keyboard shortcut.

        @return the alternative accelerator
        @rtype QKeySequence
        """
        shortcuts = self.shortcuts()
        if len(shortcuts) < 2:
            return QKeySequence()
        else:
            return shortcuts[1]

    def setShortcut(self, shortcut):
        """
        Public slot to set the keyboard shortcut.

        @param shortcut the accelerator
        @type QKeySequence
        """
        super().setShortcut(shortcut)
        self.__ammendToolTip()

    def setShortcuts(self, shortcuts):
        """
        Public slot to set the list of keyboard shortcuts.

        @param shortcuts list of keyboard accelerators or key for a platform
            dependent list of accelerators
        @type list of QKeySequence or QKeySequence.StandardKey
        """
        super().setShortcuts(shortcuts)
        self.__ammendToolTip()

    def setIconText(self, text):
        """
        Public slot to set the icon text of the action.

        @param text new icon text
        @type str
        """
        super().setIconText(text)
        self.__ammendToolTip()

    def __ammendToolTip(self):
        """
        Private slot to add the primary keyboard accelerator to the tooltip.
        """
        shortcut = self.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
        if shortcut:
            if QCoreApplication.instance().isLeftToRight():
                fmt = "{0} ({1})"
            else:
                fmt = "({1}) {0}"
            self.setToolTip(fmt.format(self.iconText(), shortcut))


def addActions(target, actions):
    """
    Module function to add a list of actions to a widget.

    @param target reference to the target widget
    @type QWidget
    @param actions list of actions to be added to the target. A
        None indicates a separator
    @type list of QAction
    """
    if target is None:
        return

    for action in actions:
        if action is None:
            target.addSeparator()
        else:
            target.addAction(action)


def createActionGroup(parent, name=None, exclusive=False):
    """
    Module function to create an action group.

    @param parent parent object of the action group
    @type QObject
    @param name name of the action group object
    @type str
    @param exclusive flag indicating an exclusive action group
    @type bool
    @return reference to the created action group
    @rtype QActionGroup
    """
    actGrp = QActionGroup(parent)
    if name:
        actGrp.setObjectName(name)
    actGrp.setExclusive(exclusive)
    return actGrp
