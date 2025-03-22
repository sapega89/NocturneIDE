# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an interface to the Mercurial command server.
"""

import io
import struct

from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QObject,
    QProcess,
    QThread,
    pyqtSlot,
)
from PyQt6.QtWidgets import QDialog

from .HgUtilities import getHgExecutable, prepareProcess


class HgClient(QObject):
    """
    Class implementing the Mercurial command server interface.
    """

    InputFormat = ">I"
    OutputFormat = ">cI"
    OutputFormatSize = struct.calcsize(OutputFormat)
    ReturnFormat = ">i"

    Channels = (b"I", b"L", b"o", b"e", b"r", b"d")

    def __init__(self, repoPath, encoding, vcs, parent=None):
        """
        Constructor

        @param repoPath root directory of the repository
        @type str
        @param encoding encoding to be used by the command server
        @type str
        @param vcs reference to the VCS object
        @type Hg
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__server = None
        self.__started = False
        self.__version = None
        self.__encoding = vcs.getEncoding()
        self.__cancel = False
        self.__commandRunning = False
        self.__repoPath = repoPath

        # generate command line and environment
        self.__serverArgs = vcs.initCommand("serve")
        self.__serverArgs.extend(["--cmdserver", "pipe"])
        self.__serverArgs.extend(["--config", "ui.interactive=True"])
        self.__serverArgs.extend(["--config", "progress.assume-tty=True"])
        self.__serverArgs.extend(
            ["--config", "progress.format=topic bar number estimate"]
        )
        if repoPath:
            self.__serverArgs.append("--repository")
            self.__serverArgs.append(repoPath)

        if encoding:
            self.__encoding = encoding
            if "--encoding" in self.__serverArgs:
                # use the defined encoding via the environment
                index = self.__serverArgs.index("--encoding")
                del self.__serverArgs[index : index + 2]

    def startServer(self):
        """
        Public method to start the command server.

        @return tuple of flag indicating a successful start and an error
            message in case of failure
        @rtype tuple of (bool, str)
        """
        self.__server = QProcess()
        self.__server.setWorkingDirectory(self.__repoPath)

        # connect signals
        self.__server.finished.connect(self.__serverFinished)

        prepareProcess(self.__server, self.__encoding)

        exe = getHgExecutable()
        self.__server.start(exe, self.__serverArgs)
        serverStarted = self.__server.waitForStarted(15000)
        if not serverStarted:
            return False, self.tr(
                "The process {0} could not be started. "
                "Ensure, that it is in the search path."
            ).format(exe)

        self.__server.setReadChannel(QProcess.ProcessChannel.StandardOutput)
        ok, error = self.__readHello()
        self.__started = ok
        return ok, error

    def stopServer(self):
        """
        Public method to stop the command server.
        """
        if self.__server is not None:
            self.__server.closeWriteChannel()
            res = self.__server.waitForFinished(5000)
            if not res:
                self.__server.terminate()
                res = self.__server.waitForFinished(3000)
                if not res:
                    self.__server.kill()
                    self.__server.waitForFinished(3000)

            self.__started = False
            self.__server.deleteLater()
            self.__server = None

    def restartServer(self):
        """
        Public method to restart the command server.

        @return tuple of flag indicating a successful start and an error
            message in case of failure
        @rtype tuple of (bool, str)
        """
        self.stopServer()
        return self.startServer()

    def __readHello(self):
        """
        Private method to read the hello message sent by the command server.

        @return tuple of flag indicating success and an error message in case
            of failure
        @rtype tuple of (bool, str)
        """
        ch, msg = self.__readChannel()
        if not ch:
            return False, self.tr("Did not receive the 'hello' message.")
        elif ch != "o":
            return False, self.tr("Received data on unexpected channel.")

        msg = msg.split("\n")

        if not msg[0].startswith("capabilities: "):
            return False, self.tr(
                "Bad 'hello' message, expected 'capabilities: ' but got '{0}'."
            ).format(msg[0])
        self.__capabilities = msg[0][len("capabilities: ") :]
        if not self.__capabilities:
            return False, self.tr(
                "'capabilities' message did not contain any capability."
            )

        self.__capabilities = set(self.__capabilities.split())
        if "runcommand" not in self.__capabilities:
            return False, "'capabilities' did not contain 'runcommand'."

        if not msg[1].startswith("encoding: "):
            return False, self.tr(
                "Bad 'hello' message, expected 'encoding: ' but got '{0}'."
            ).format(msg[1])
        encoding = msg[1][len("encoding: ") :]
        if not encoding:
            return False, self.tr("'encoding' message did not contain any encoding.")
        self.__encoding = encoding

        return True, ""

    @pyqtSlot(int, QProcess.ExitStatus)
    def __serverFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        self.__started = False

    def __readChannel(self):
        """
        Private method to read data from the command server.

        @return tuple of channel designator and channel data
        @rtype tuple of (str, int or str or bytes)
        """
        if self.__server.bytesAvailable() > 0 or self.__server.waitForReadyRead(10000):
            data = bytes(self.__server.peek(HgClient.OutputFormatSize))
            if not data or len(data) < HgClient.OutputFormatSize:
                return "", ""

            channel, length = struct.unpack(HgClient.OutputFormat, data)
            channel = channel.decode(self.__encoding)
            if channel in "IL":
                self.__server.read(HgClient.OutputFormatSize)
                return channel, length
            else:
                if self.__server.bytesAvailable() < HgClient.OutputFormatSize + length:
                    return "", ""
                self.__server.read(HgClient.OutputFormatSize)
                data = self.__server.read(length)
                if channel == "r":
                    return (channel, data)
                else:
                    return (channel, str(data, self.__encoding, "replace"))
        else:
            return "", ""

    def __writeDataBlock(self, data):
        """
        Private slot to write some data to the command server.

        @param data data to be sent
        @type str
        """
        if not isinstance(data, bytes):
            data = data.encode(self.__encoding)
        self.__server.write(struct.pack(HgClient.InputFormat, len(data)))
        self.__server.write(data)
        self.__server.waitForBytesWritten()

    def __runcommand(self, args, inputChannels, outputChannels):
        """
        Private method to run a command in the server (low level).

        @param args list of arguments for the command
        @type list of str
        @param inputChannels dictionary of input channels. The dictionary must
            have the keys 'I' and 'L' and each entry must be a function
            receiving the number of bytes to write.
        @type dict
        @param outputChannels dictionary of output channels. The dictionary
            must have the keys 'o' and 'e' and each entry must be a function
            receiving the data.
        @type dict
        @return result code of the command, -1 if the command server wasn't
            started or -10, if the command was canceled
        @rtype int
        @exception RuntimeError raised to indicate an unexpected command
            channel
        """
        if not self.__started:
            return -1

        self.__server.write(QByteArray(b"runcommand\n"))
        self.__writeDataBlock("\0".join(args))

        while True:
            QCoreApplication.processEvents()

            if self.__cancel:
                return -10

            if self.__server is None:
                return -1

            if self.__server.bytesAvailable() == 0:
                QThread.msleep(50)
                continue
            channel, data = self.__readChannel()

            # input channels
            if channel in inputChannels:
                if channel == "L":
                    inputData, isPassword = inputChannels[channel](data)
                    # echo the input to the output if it was a prompt
                    if not isPassword:
                        outputChannels["o"](inputData)
                else:
                    inputData = inputChannels[channel](data)
                self.__writeDataBlock(inputData)

            # output channels
            elif channel in outputChannels:
                outputChannels[channel](data)

            # result channel, command is finished
            elif channel == "r":
                return struct.unpack(HgClient.ReturnFormat, data)[0]

            # unexpected but required channel
            elif channel.isupper():
                raise RuntimeError(
                    "Unexpected but required channel '{0}'.".format(channel)
                )

            # optional channels or no channel at all
            else:
                pass

    def __prompt(self, size, message):
        """
        Private method to prompt the user for some input.

        @param size maximum length of the requested input
        @type int
        @param message message sent by the server
        @type str
        @return tuple containing data entered by the user and
            a flag indicating a password input
        @rtype tuple of (str, bool)
        """
        from .HgClientPromptDialog import HgClientPromptDialog

        inputData = ""
        isPassword = False
        dlg = HgClientPromptDialog(size, message)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            inputData = dlg.getInput() + "\n"
            isPassword = dlg.isPassword()
        return inputData, isPassword

    def runcommand(self, args, prompt=None, inputData=None, output=None, error=None):
        """
        Public method to execute a command via the command server.

        @param args list of arguments for the command
        @type list of str
        @param prompt function to reply to prompts by the server. It
            receives the max number of bytes to return and the contents
            of the output channel received so far. If an output function is
            given as well, the prompt data is passed through the output
            function. The function must return the input data and a flag
            indicating a password input.
        @type func(int, str) -> (str, bool)
        @param inputData function to reply to bulk data requests by the
            server. It receives the max number of bytes to return.
        @type func(int) -> bytes
        @param output function receiving the data from the server. If a
            prompt function is given, it is assumed, that the prompt output
            is passed via this function.
        @type func(str)
        @param error function receiving error messages from the server
        @type func(str)
        @return tuple of output and errors of the command server. In case
            output and/or error functions were given, the respective return
            value will be an empty string.
        @rtype tuple of (str, str)
        """
        if not self.__started:
            # try to start the Mercurial command server
            ok, startError = self.startServer()
            if not ok:
                return "", startError

        self.__commandRunning = True
        outputChannels = {}
        outputBuffer = None
        errorBuffer = None

        if output is None:
            outputBuffer = io.StringIO()
            outputChannels["o"] = outputBuffer.write
        else:
            outputChannels["o"] = output
        if error:
            outputChannels["e"] = error
        else:
            errorBuffer = io.StringIO()
            outputChannels["e"] = errorBuffer.write

        inputChannels = {}
        if prompt is not None:

            def func(size):
                msg = "" if outputBuffer is None else outputBuffer.getvalue()
                reply, isPassword = prompt(size, msg)
                return reply, isPassword

            inputChannels["L"] = func
        else:

            def myprompt(size):
                msg = (
                    self.tr("For message see output dialog.")
                    if outputBuffer is None
                    else outputBuffer.getvalue()
                )
                reply, isPassword = self.__prompt(size, msg)
                return reply, isPassword

            inputChannels["L"] = myprompt
        if inputData is not None:
            inputChannels["I"] = inputData

        self.__cancel = False
        self.__runcommand(args, inputChannels, outputChannels)

        out = outputBuffer.getvalue() if outputBuffer else ""
        err = errorBuffer.getvalue() if errorBuffer else ""

        self.__commandRunning = False

        return out, err

    def cancel(self):
        """
        Public method to cancel the running command.
        """
        self.__cancel = True
        self.restartServer()

    def wasCanceled(self):
        """
        Public method to check, if the last command was canceled.

        @return flag indicating the cancel state
        @rtype bool
        """
        return self.__cancel

    def isExecuting(self):
        """
        Public method to check, if the server is executing a command.

        @return flag indicating the execution of a command
        @rtype bool
        """
        return self.__commandRunning

    def getRepository(self):
        """
        Public method to get the repository path this client is serving.

        @return repository path
        @rtype str
        """
        return self.__repoPath
