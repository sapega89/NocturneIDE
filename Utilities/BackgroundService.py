# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a background service for the various checkers and other
Python interpreter dependent functions.
"""

import contextlib
import json
import os
import struct
import sys
import time
import zlib

from PyQt6.QtCore import QProcess, QThread, QTimer, pyqtSignal
from PyQt6.QtNetwork import QHostAddress, QTcpServer
from PyQt6.QtWidgets import QApplication

import Preferences
from EricWidgets import EricMessageBox
from EricWidgets.EricApplication import ericApp
from SystemUtilities import FileSystemUtilities, PythonUtilities


class BackgroundService(QTcpServer):
    """
    Class implementing the main part of the background service.

    @signal serviceNotAvailable(function, language, filename, message)
        emitted to indicate the non-availability of a service function
        (str, str, str, str)
    @signal batchJobDone(function, language) emitted to indicate the end of
        a batch job (str, str)
    """

    serviceNotAvailable = pyqtSignal(str, str, str, str)
    batchJobDone = pyqtSignal(str, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.processes = {}
        self.connections = {}
        self.isWorking = None
        self.runningJob = [None, None, None, None]
        self.__queue = []
        self.services = {}

        networkInterface = Preferences.getDebugger("NetworkInterface")
        if networkInterface in ("allv4", "localv4") or "." in networkInterface:
            # IPv4
            self.__hostAddress = "127.0.0.1"
        elif networkInterface in ("all", "allv6", "localv6"):
            # IPv6
            self.__hostAddress = "::1"
        else:
            self.__hostAddress = networkInterface
        self.listen(QHostAddress(self.__hostAddress))

        self.newConnection.connect(self.on_newConnection)

        ## Note: Need the address and port if started external in debugger:
        port = self.serverPort()
        hostAddressStr = (
            "[{0}]".format(self.__hostAddress)
            if ":" in self.__hostAddress
            else self.__hostAddress
        )
        print("Background Service listening on: {0}:{1:d}".format(hostAddressStr, port))
        # __IGNORE_WARNING_M801__

        interpreter = self.__getPythonInterpreter()
        if interpreter:
            process = self.__startExternalClient(interpreter, port)
            if process:
                self.processes["Python3"] = process, interpreter

    def __getPythonInterpreter(self):
        """
        Private method to generate the path of the Python interpreter to be
        used to run the background client.

        @return path of the Python interpreter
        @rtype str
        """
        venvName = Preferences.getDebugger("Python3VirtualEnv")
        interpreter = (
            ericApp().getObject("VirtualEnvManager").getVirtualenvInterpreter(venvName)
        )
        if not interpreter:
            interpreter = PythonUtilities.getPythonExecutable()
        return interpreter

    def __startExternalClient(self, interpreter, port):
        """
        Private method to start the background client as external process.

        @param interpreter path and name of the executable to start
        @type str
        @param port socket port to which the interpreter should connect
        @type int
        @return the process object
        @rtype QProcess or None
        """
        if interpreter == "" or not FileSystemUtilities.isinpath(interpreter):
            return None

        backgroundClient = os.path.join(
            os.path.dirname(__file__), "BackgroundClient.py"
        )
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.ForwardedChannels)
        args = [
            backgroundClient,
            self.__hostAddress,
            str(port),
            str(Preferences.getUI("BackgroundServiceProcesses")),
            PythonUtilities.getPythonLibraryDirectory(),
        ]
        proc.start(interpreter, args)
        if not proc.waitForStarted(10000):
            proc = None
        return proc

    def __processQueue(self):
        """
        Private method to take the next service request and send it to the
        client.
        """
        if self.__queue and self.isWorking is None:
            fx, lang, fn, data = self.__queue.pop(0)
            self.isWorking = lang
            self.runningJob = fx, lang, fn, data
            self.__send(fx, lang, fn, data)

    def __send(self, fx, lang, fn, data):
        """
        Private method to send a job request to one of the clients.

        @param fx remote function name to execute
        @type str
        @param lang language to connect to
        @type str
        @param fn filename for identification
        @type str
        @param data function argument(s)
        @type any basic datatype
        """
        self.__cancelled = False
        connection = self.connections.get(lang)
        if connection is None:
            if fx != "INIT":
                # Avoid growing recursion depth which could itself result in an
                # exception
                QTimer.singleShot(
                    0,
                    lambda: self.serviceNotAvailable.emit(
                        fx, lang, fn, self.tr("{0} not configured.").format(lang)
                    ),
                )
            # Reset flag and continue processing queue
            self.isWorking = None
            self.__processQueue()
        else:
            packedData = json.dumps([fx, fn, data])
            packedData = bytes(packedData, "utf-8")
            header = struct.pack(
                b"!II", len(packedData), zlib.adler32(packedData) & 0xFFFFFFFF
            )
            connection.write(header)
            connection.write(b"JOB   ")  # 6 character message type
            connection.write(packedData)

    def __receive(self, lang):
        """
        Private method to receive the response from the clients.

        @param lang language of the incoming connection
        @type str
        @exception RuntimeError raised if hashes don't match
        """
        headerSize = struct.calcsize(b"!II")

        data = ""
        fx = ""

        connection = self.connections[lang]
        while connection and connection.bytesAvailable():
            now = time.monotonic()
            while connection.bytesAvailable() < headerSize:
                connection.waitForReadyRead(50)
                if time.monotonic() - now > 2.0:  # 2 seconds timeout
                    return
            header = connection.read(headerSize)
            length, datahash = struct.unpack(b"!II", header)

            packedData = b""
            now = time.monotonic()
            while len(packedData) < length:
                maxSize = length - len(packedData)
                if connection.bytesAvailable() < maxSize:
                    connection.waitForReadyRead(50)
                newData = connection.read(maxSize)
                if newData:
                    packedData += newData
                else:
                    if time.monotonic() - now > 2.0:  # 2 seconds timeout
                        break

            if zlib.adler32(packedData) & 0xFFFFFFFF != datahash:
                raise RuntimeError("Hashes not equal")
            packedData = packedData.decode("utf-8")
            # "check" if is's a tuple of 3 values
            fx, fn, data = json.loads(packedData)

            if fx == "INIT":
                if data != "ok":
                    EricMessageBox.critical(
                        None,
                        self.tr("Initialization of Background Service"),
                        self.tr(
                            "<p>Initialization of Background Service"
                            " <b>{0}</b> failed.</p><p>Reason: {1}</p>"
                        ).format(fn, data),
                    )
            elif fx == "EXCEPTION":
                # Remove connection because it'll close anyway
                self.connections.pop(lang, None)
                # Call sys.excepthook(type, value, traceback) to emulate the
                # exception which was caught on the client
                sys.excepthook(*data)
                res = EricMessageBox.question(
                    None,
                    self.tr("Restart background client?"),
                    self.tr(
                        "<p>The background client for <b>{0}</b> has stopped"
                        " due to an exception. It's used by various plug-ins"
                        " like the different checkers.</p>"
                        "<p>Select"
                        "<ul>"
                        "<li><b>'Yes'</b> to restart the client, but abort the"
                        " last job</li>"
                        "<li><b>'Retry'</b> to restart the client and the last"
                        " job</li>"
                        "<li><b>'No'</b> to leave the client off.</li>"
                        "</ul></p>"
                        "<p>Note: The client can be restarted by opening and"
                        " accepting the preferences dialog or reloading/"
                        "changing the project.</p>"
                    ).format(lang),
                    EricMessageBox.Yes | EricMessageBox.No | EricMessageBox.Retry,
                    EricMessageBox.Yes,
                )

                if res == EricMessageBox.Retry:
                    self.enqueueRequest(*self.runningJob)
                else:
                    fx, lng, fn, data = self.runningJob
                    with contextlib.suppress(KeyError, TypeError):
                        self.services[(fx, lng)][3](
                            fx,
                            lng,
                            fn,
                            self.tr(
                                "An error in Eric's background client stopped the"
                                " service."
                            ),
                        )
                if res != EricMessageBox.No:
                    self.isWorking = None
                    self.restartService(lang, forceKill=True)
                    return
            elif data == "Unknown service.":
                callback = self.services.get((fx, lang))
                if callback:
                    callback[3](fx, lang, fn, data)
            elif fx.startswith("batch_"):
                mfx = fx.replace("batch_", "")
                if data != "__DONE__":
                    callback = self.services.get((mfx, lang))
                    if callback:
                        if isinstance(data, (list, tuple)):
                            callback[2](fn, *data)
                        elif isinstance(data, str):
                            callback[3](mfx, lang, fn, data)
                    if data == "Unknown batch service.":
                        self.batchJobDone.emit(mfx, lang)
                        self.__cancelled = True
                else:
                    self.batchJobDone.emit(mfx, lang)
                    self.restartService(lang, forceKill=True)
            else:
                callback = self.services.get((fx, lang))
                if callback:
                    callback[2](fn, *data)

        if self.__cancelled and data != "__DONE__" and fx.startswith("batch_"):
            # If it is a canceled batch job perform the batch done logic.
            fx = fx.replace("batch_", "")
            self.batchJobDone.emit(fx, lang)
            self.restartService(lang, forceKill=True)

        self.isWorking = None
        self.__processQueue()

    def preferencesOrProjectChanged(self):
        """
        Public slot to restart the built in languages.
        """
        interpreter = self.__getPythonInterpreter()

        # Tweak the processes list to reflect the changed interpreter
        proc, _inter = self.processes.pop("Python3", [None, None])
        self.processes["Python3"] = proc, interpreter

        self.restartService("Python3")

    def restartService(self, language, forceKill=False):
        """
        Public method to restart a given language.

        @param language to restart
        @type str
        @param forceKill flag to kill a running task
        @type bool
        """
        try:
            proc, interpreter = self.processes.pop(language)
        except KeyError:
            return

        # Don't kill a process if it's still working
        if not forceKill:
            while self.isWorking is not None:
                QThread.msleep(100)
                QApplication.processEvents()

        conn = self.connections.pop(language, None)
        if conn:
            conn.blockSignals(True)
            conn.close()
        if proc:
            with contextlib.suppress(RuntimeError):
                proc.close()

        if interpreter:
            port = self.serverPort()
            process = self.__startExternalClient(interpreter, port)
            if process:
                self.processes[language] = process, interpreter

    def enqueueRequest(self, fx, lang, fn, data):
        """
        Public method implementing a queued processing of incoming events.

        Duplicate service requests update an older request to avoid overrun or
        starving of the services.

        @param fx function name of the service
        @type str
        @param lang language to connect to
        @type str
        @param fn filename for identification
        @type str
        @param data function argument(s)
        @type any basic datatype
        """
        args = [fx, lang, fn, data]
        if fx == "INIT":
            self.__queue.insert(0, args)
        else:
            for pendingArg in self.__queue:
                # Check if it's the same service request (fx, lang, fn equal)
                if pendingArg[:3] == args[:3]:
                    # Update the data
                    pendingArg[3] = args[3]
                    break
            else:
                self.__queue.append(args)
        self.__processQueue()

    def requestCancel(self, fx, lang):
        """
        Public method to ask a batch job to terminate.

        @param fx function name of the service
        @type str
        @param lang language to connect to
        @type str
        """
        entriesToRemove = []
        for pendingArg in self.__queue:
            if pendingArg[:2] == [fx, lang]:
                entriesToRemove.append(pendingArg)
        for entryToRemove in entriesToRemove:
            self.__queue.remove(entryToRemove)

        connection = self.connections.get(lang)
        if connection is None:
            return
        else:
            header = struct.pack(b"!II", 0, 0)
            connection.write(header)
            connection.write(b"CANCEL")  # 6 character message type

        self.__cancelled = True

    def serviceConnect(
        self,
        fx,
        lang,
        modulepath,
        module,
        callback,
        onErrorCallback=None,
        onBatchDone=None,
    ):
        """
        Public method to announce a new service to the background
        service/client.

        @param fx function name of the service
        @type str
        @param lang language of the new service
        @type str
        @param modulepath full path to the module
        @type str
        @param module name to import
        @type str
        @param callback function called on service response
        @type function
        @param onErrorCallback function called, if client isn't available
        @type function
        @param onBatchDone function called when a batch job is done
        @type function
        """
        self.services[(fx, lang)] = (modulepath, module, callback, onErrorCallback)
        self.enqueueRequest("INIT", lang, fx, [modulepath, module])
        if onErrorCallback:
            self.serviceNotAvailable.connect(onErrorCallback)
        if onBatchDone:
            self.batchJobDone.connect(onBatchDone)

    def serviceDisconnect(self, fx, lang):
        """
        Public method to remove the service from the service list.

        @param fx function name of the service
        @type function
        @param lang language of the service
        @type str
        """
        serviceArgs = self.services.pop((fx, lang), None)
        if serviceArgs and serviceArgs[3]:
            self.serviceNotAvailable.disconnect(serviceArgs[3])

    def on_newConnection(self):
        """
        Private slot for new incoming connections from the clients.
        """
        connection = self.nextPendingConnection()
        if not connection.waitForReadyRead(1000):
            return
        lang = connection.read(64)
        lang = lang.decode("utf-8")
        # Avoid hanging of eric on shutdown
        if self.connections.get(lang):
            self.connections[lang].close()
        if self.isWorking == lang:
            self.isWorking = None
        self.connections[lang] = connection
        connection.readyRead.connect(lambda: self.__receive(lang))
        connection.disconnected.connect(lambda: self.on_disconnectSocket(lang))

        for (fx, lng), args in self.services.items():
            if lng == lang:
                # Register service with modulepath and module
                self.enqueueRequest("INIT", lng, fx, args[:2])

        # Syntax check the open editors again
        try:
            vm = ericApp().getObject("ViewManager")
        except KeyError:
            return
        for editor in vm.getOpenEditors():
            if editor.getLanguage() == lang:
                QTimer.singleShot(0, editor.checkSyntax)

    def on_disconnectSocket(self, lang):
        """
        Private slot called when connection to a client is lost.

        @param lang client language which connection is lost
        @type str
        """
        conn = self.connections.pop(lang, None)
        if conn:
            conn.close()
            fx, lng, fn, data = self.runningJob
            if fx != "INIT" and lng == lang:
                self.services[(fx, lng)][3](
                    fx,
                    lng,
                    fn,
                    self.tr(
                        "Eric's background client disconnected because of an"
                        " unknown reason."
                    ),
                )
            self.isWorking = None

            res = EricMessageBox.yesNo(
                None,
                self.tr("Background client disconnected."),
                self.tr(
                    "The background client for <b>{0}</b> disconnected because"
                    " of an unknown reason.<br>Should it be restarted?"
                ).format(lang),
                yesDefault=True,
            )
            if res:
                self.restartService(lang)

    def shutdown(self):
        """
        Public method to cleanup the connections and processes when eric is
        shutting down.
        """
        self.close()

        for connection in self.connections.values():
            with contextlib.suppress(RuntimeError):
                connection.readyRead.disconnect()
                connection.disconnected.disconnect()
                connection.close()
                connection.deleteLater()

        for process, _interpreter in self.processes.values():
            process.close()
            if not process.waitForFinished(10000):
                process.kill()
            process = None
