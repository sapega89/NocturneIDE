# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an asynchronous file like socket interface for the
debugger.
"""

import contextlib
import socket
import struct
import threading
import zlib

from DebugUtilities import prepareJsonCommand


def AsyncPendingWrite(file):
    """
    Module function to check for data to be written.

    @param file The file object to be checked
    @type file
    @return Flag indicating if there is data waiting
    @rtype int
    """
    try:
        pending = file.pendingWrite()
    except Exception:
        pending = 0

    return pending


class AsyncFile:
    """
    Class wrapping a socket object with a file interface.
    """

    MAX_TRIES = 10

    BUFSIZE = 2**14  # 16 kBytes
    CMD_BUFSIZE = 2**12  # 4 kBytes

    def __init__(self, sock, mode, name):
        """
        Constructor

        @param sock the socket object being wrapped
        @type socket
        @param mode mode of this file
        @type str
        @param name name of this file
        @type str
        """
        # Initialise the attributes.
        self.closed = False
        self.sock = sock
        self.mode = mode
        self.name = name
        self.nWriteErrors = 0
        self.encoding = "utf-8"
        self.errors = None
        self.newlines = None
        self.line_buffering = False

        self.writeLock = threading.RLock()
        self.wpending = []

    def __checkMode(self, mode):
        """
        Private method to check the mode.

        This method checks, if an operation is permitted according to
        the mode of the file. If it is not, an OSError is raised.

        @param mode the mode to be checked
        @type string
        @exception OSError raised to indicate a bad file descriptor
        """
        if mode != self.mode:
            raise OSError((9, "[Errno 9] Bad file descriptor"))

    def pendingWrite(self):
        """
        Public method that returns the number of strings waiting to be written.

        @return the number of strings to be written
        @rtype int
        """
        return len(self.wpending)

    def close(self, closeit=False):
        """
        Public method to close the file.

        @param closeit flag to indicate a close ordered by the debugger code
        @type bool
        """
        if closeit and not self.closed:
            self.flush()
            self.sock.close()
            self.closed = True

    def flush(self):
        """
        Public method to write all pending entries.
        """
        self.writeLock.acquire()
        while self.wpending:
            try:
                data = self.wpending.pop(0)
            except IndexError:
                break

            try:
                with contextlib.suppress(UnicodeEncodeError, UnicodeDecodeError):
                    data = data.encode("utf-8", "backslashreplace")
                header = struct.pack(b"!II", len(data), zlib.adler32(data) & 0xFFFFFFFF)
                self.sock.sendall(header)
                self.sock.sendall(data)
                self.nWriteErrors = 0
            except OSError:
                self.nWriteErrors += 1
                if self.nWriteErrors > AsyncFile.MAX_TRIES:
                    self.wpending = []  # delete all output
        self.writeLock.release()

    def isatty(self):
        """
        Public method to indicate whether a tty interface is supported.

        @return always false
        @rtype bool
        """
        return False

    def fileno(self):
        """
        Public method returning the file number.

        @return file number
        @rtype int
        """
        try:
            return self.sock.fileno()
        except OSError:
            return -1

    def readable(self):
        """
        Public method to check, if the stream is readable.

        @return flag indicating a readable stream
        @rtype bool
        """
        return self.mode == "r"

    def read_p(self, size=-1):
        """
        Public method to read bytes from this file.

        @param size maximum number of bytes to be read
        @type int
        @return the bytes read
        @rtype str
        """
        self.__checkMode("r")

        if size < 0:
            size = AsyncFile.BUFSIZE

        return self.sock.recv(size).decode("utf8", "backslashreplace")

    def read(self, size=-1):
        """
        Public method to read bytes from this file.

        @param size maximum number of bytes to be read
        @type int
        @return the bytes read
        @rtype str
        """
        self.__checkMode("r")

        buf = input()  # secok
        if size >= 0:
            buf = buf[:size]
        return buf

    def readCommand(self):
        """
        Public method to read a command string prefixed by a command header.

        @return command string
        @rtype str
        """
        header = self.sock.recv(struct.calcsize(b"!II"))
        if header:
            length, datahash = struct.unpack(b"!II", header)

            length = int(length)
            data = bytearray()
            while len(data) < length:
                newData = self.sock.recv(length - len(data))
                if not newData:
                    break
                data += newData

            if data and zlib.adler32(data) & 0xFFFFFFFF == datahash:
                return data.decode("utf8", "backslashreplace")

        return ""

    def readline_p(self, size=-1):
        """
        Public method to read a line from this file.

        <b>Note</b>: This method will not block and may return
        only a part of a line if that is all that is available.

        @param size maximum number of bytes to be read
        @type int
        @return one line of text up to size bytes
        @rtype str
        """
        self.__checkMode("r")

        if size < 0:
            size = AsyncFile.BUFSIZE

        # The integration of the debugger client event loop and the connection
        # to the debugger relies on the two lines of the debugger command being
        # delivered as two separate events.  Therefore we make sure we only
        # read a line at a time.
        line = self.sock.recv(size, socket.MSG_PEEK)

        eol = line.find(b"\n")
        size = eol + 1 if eol >= 0 else len(line)

        # Now we know how big the line is, read it for real.
        return self.sock.recv(size).decode("utf8", "backslashreplace")

    def readlines(self, sizehint=-1):
        """
        Public method to read all lines from this file.

        @param sizehint hint of the numbers of bytes to be read
        @type int
        @return list of lines read
        @rtype list of str
        """
        self.__checkMode("r")

        lines = []
        room = sizehint

        line = self.readline_p(room)
        linelen = len(line)

        while linelen > 0:
            lines.append(line)

            if sizehint >= 0:
                room -= linelen

                if room <= 0:
                    break

            line = self.readline_p(room)
            linelen = len(line)

        return lines

    def readline(self, sizehint=-1):
        """
        Public method to read one line from this file.

        @param sizehint hint of the numbers of bytes to be read
        @type int
        @return one line read
        @rtype str
        """
        self.__checkMode("r")

        line = input() + "\n"  # secok
        if sizehint >= 0:
            line = line[:sizehint]
        return line

    def seekable(self):
        """
        Public method to check, if the stream is seekable.

        @return flag indicating a seekable stream
        @rtype bool
        """
        return False

    def seek(self, offset, whence=0):  # noqa: U100
        """
        Public method to move the filepointer.

        @param offset offset to move the file pointer to (unused)
        @type int
        @param whence position the offset relates to (unused)
        @type int
        @exception OSError This method is not supported and always raises an
        OSError.
        """
        raise OSError((29, "[Errno 29] Illegal seek"))

    def tell(self):
        """
        Public method to get the filepointer position.

        @exception OSError This method is not supported and always raises an
        OSError.
        """
        raise OSError((29, "[Errno 29] Illegal seek"))

    def truncate(self, size=-1):  # noqa: U100
        """
        Public method to truncate the file.

        @param size size to truncate to (unused)
        @type int
        @exception OSError This method is not supported and always raises an
        OSError.
        """
        raise OSError((29, "[Errno 29] Illegal seek"))

    def writable(self):
        """
        Public method to check, if a stream is writable.

        @return flag indicating a writable stream
        @rtype bool
        """
        return self.mode == "w"

    def write(self, s):
        """
        Public method to write a string to the file.

        @param s text to be written
        @type str, bytes or bytearray
        """
        self.__checkMode("w")

        self.writeLock.acquire()
        if isinstance(s, (bytes, bytearray)):
            # convert to string to send it
            s = repr(s)

        jsonCommand = prepareJsonCommand(
            "ClientOutput",
            {
                "text": s,
                "debuggerId": "",
            },
        )
        self.wpending.append(jsonCommand)
        self.flush()
        self.writeLock.release()

    def write_p(self, s):
        """
        Public method to write a json-rpc 2.0 coded string to the file.

        @param s text to be written
        @type str
        """
        self.__checkMode("w")

        self.wpending.append(s)
        self.flush()

    def writelines(self, lines):
        """
        Public method to write a list of strings to the file.

        @param lines list of texts to be written
        @type list of str
        """
        self.write("".join(lines))
