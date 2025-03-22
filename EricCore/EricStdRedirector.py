# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a redirector for stderr and stdout to be able to send data written
to these streams via Qt signals.
"""

import locale
import os
import sys

from PyQt6.QtCore import QObject, pyqtSignal


class EricStdRedirector(QObject):
    """
    Class for replacement of stdout and stderr in order to send the data via
    Qt signals.

    @signal stderrString(str) emitted to signal data written to stderr
    @signal stdoutString(str) emitted to signal data written to stdout
    """

    stderrString = pyqtSignal(str)
    stdoutString = pyqtSignal(str)

    def __init__(self, stderr, parent=None):
        """
        Constructor

        @param stderr flag indicating stderr is being redirected
        @type bool
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.mode = "w"  # only writable stream (i.e. stdout, stderr)

        self.__isStderr = stderr
        self.__buffer = ""
        try:
            self.__encoding = locale.getencoding()
        except AttributeError:
            self.__encoding = sys.getdefaultencoding()

    def __signalData(self, n):
        """
        Private method used to signal data written to the instance object.

        @param n max number of characters to send via a Qt signal
        @type int
        """
        if n:
            line = self.__buffer[:n].replace("\n", os.linesep)
            if self.__isStderr:
                self.stderrString.emit(line)
            else:
                self.stdoutString.emit(line)
            self.__buffer = self.__buffer[n:]

    def __bufferedLength(self):
        """
        Private method returning number of characters of buffered lines.

        @return number of characters of buffered lines (complete lines only)
        @rtype int
        """
        return self.__buffer.rfind("\n") + 1

    def flush(self):
        """
        Public method used to flush all buffered data.
        """
        self.__signalData(len(self.__buffer))

    def write(self, s):
        """
        Public method used to write data.

        @param s data to be written (it must support the str-method)
        @type Any
        """
        self.__buffer += str(s).replace("\r\n", "\n").replace("\r", "\n")
        self.__signalData(self.__bufferedLength())

    def writelines(self, lines):
        """
        Public method used to write a list of strings to the file.

        @param lines list of texts to be written
        @type list of str
        """
        self.write("".join(lines))

    def isatty(self):
        """
        Public method to indicate a TTY.

        Note: This always reports 'False' because the redirector class is no TTY.

        @return flag indicating a TTY
        @rtype bool
        """
        return False

    @property
    def encoding(self):
        """
        Public method to report the used encoding.

        @return used encoding
        @rtype str
        """
        return self.__encoding

    def readable(self):
        """
        Public method to check, if the stream is readable.

        @return flag indicating a readable stream
        @rtype bool
        """
        return self.mode == "r"

    def writable(self):
        """
        Public method to check, if a stream is writable.

        @return flag indicating a writable stream
        @rtype bool
        """
        return self.mode == "w"
