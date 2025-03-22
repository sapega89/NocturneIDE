# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an auto saver class.
"""

from PyQt6.QtCore import QBasicTimer, QObject, QTime


class AutoSaver(QObject):
    """
    Class implementing the auto saver.
    """

    AUTOSAVE_IN = 1000 * 3
    MAXWAIT = 1000 * 15

    def __init__(self, parent, save):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        @param save slot to be called to perform the save operation
        @type function
        @exception RuntimeError raised, if no parent is given
        """
        super().__init__(parent)

        if parent is None:
            raise RuntimeError("AutoSaver: parent must not be None.")

        self.__save = save

        self.__timer = QBasicTimer()
        self.__firstChange = None

    def changeOccurred(self):
        """
        Public slot handling a change.
        """
        if self.__firstChange is None:
            self.__firstChange = QTime.currentTime()

        if self.__firstChange.msecsTo(QTime.currentTime()) > self.MAXWAIT:
            self.saveIfNeccessary()
        else:
            self.__timer.start(self.AUTOSAVE_IN, self)

    def timerEvent(self, evt):
        """
        Protected method handling timer events.

        @param evt reference to the timer event
        @type QTimerEvent
        """
        if evt.timerId() == self.__timer.timerId():
            self.saveIfNeccessary()
        else:
            super().timerEvent(evt)

    def saveIfNeccessary(self):
        """
        Public method to activate the save operation.
        """
        if not self.__timer.isActive():
            return

        self.__timer.stop()
        self.__firstChange = None
        self.__save()
