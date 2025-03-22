# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a QProcess derived class with a timeout and convenience signals.
"""

from PyQt6.QtCore import QProcess, QTimer, pyqtSignal, pyqtSlot


class EricProcess(QProcess):
    """
    Class implementing a QProcess derived class with a timeout and convenience signals
    succeeded and failed.

    @signal failed() emitted to indicate a process failure
    @signal succeeded() emitted to indicate that the process finished successfully
    @signal timeout() emitted to indicate the expiry of the configured timeout value
    """

    failed = pyqtSignal()
    succeeded = pyqtSignal()
    timeout = pyqtSignal()

    def __init__(self, timeout=30000, parent=None):
        """
        Constructor

        @param timeout timeout value in milliseconds. If the process does not finish
            within this interval, it is killed. (defaults to 30000)
        @type int (optional)
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent=parent)

        self.started.connect(self.__started)
        self.finished.connect(self.__finished)

        self.__timeoutTimer = QTimer(self)
        self.__timeoutTimer.setInterval(timeout)
        self.__timeoutTimer.timeout.connect(self.__timeout)

        self.__timedOut = False

    def timedOut(self):
        """
        Public method to test, if the process timed out.

        @return flag indicating a timeout
        @rtype bool
        """
        return self.__timedOut

    def timeoutInterval(self):
        """
        Public method to get the process timeout interval.

        @return process timeout interval in milliseconds
        @rtype int
        """
        return self.__timeoutTimer.interval()

    @pyqtSlot()
    def __timeout(self):
        """
        Private slot to handle the timer interval exoiration.
        """
        self.__timeoutTimer.stop()
        self.__timedOut = True
        self.kill()

        self.timeout.emit()

    @pyqtSlot()
    def __started(self):
        """
        Private slot handling the process start.
        """
        self.__timedOut = False
        self.__timeoutTimer.start()

    @pyqtSlot(int, QProcess.ExitStatus)
    def __finished(self, exitCode, exitStatus):
        """
        Private slot handling the end of the process.

        @param exitCode exit code of the process (0 = success)
        @type int
        @param exitStatus exit status of the process
        @type QProcess.ExitStatus
        """
        self.__timeoutTimer.stop()

        if exitStatus == QProcess.ExitStatus.CrashExit or exitCode != 0:
            self.failed.emit()
        else:
            self.succeeded.emit()
