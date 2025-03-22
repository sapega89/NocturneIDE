# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Python3 debugger interface for the debug server.
"""

import contextlib
import json
import logging
import os
import re
import shlex
import struct
import time
import zlib

from PyQt6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, pyqtSlot

from eric7 import EricUtilities, Preferences, Utilities
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import getConfig
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities, PythonUtilities

from . import DebugClientCapabilities

ClientDefaultCapabilities = DebugClientCapabilities.HasAll


class DebuggerInterfacePython(QObject):
    """
    Class implementing the debugger interface for the debug server for
    Python 3.
    """

    def __init__(self, debugServer, passive):
        """
        Constructor

        @param debugServer reference to the debug server
        @type DebugServer
        @param passive flag indicating passive connection mode
        @type bool
        """
        super().__init__()

        self.__isNetworked = True
        self.__autoContinue = False
        self.__autoContinued = []
        self.__isStepCommand = False

        self.__ericServerDebugging = False  # are we debugging via the eric-ide server?
        try:
            self.__ericServerDebuggerInterface = (
                ericApp().getObject("EricServer").getServiceInterface("Debugger")
            )
            self.__ericServerDebuggerInterface.debugClientResponse.connect(
                lambda jsonStr: self.handleJsonCommand(jsonStr, None)
            )
            self.__ericServerDebuggerInterface.debugClientDisconnected.connect(
                self.__handleServerDebugClientDisconnected
            )
            self.__ericServerDebuggerInterface.lastClientExited.connect(
                self.__handleServerLastClientExited
            )
        except KeyError:
            self.__ericServerDebuggerInterface = None

        self.debugServer = debugServer
        self.passive = passive
        self.process = None
        self.__startedVenv = ""

        self.__commandQueue = []
        self.__mainDebugger = None
        self.__connections = {}
        self.__pendingConnections = []
        self.__inShutdown = False

        # set default values for capabilities of clients
        self.clientCapabilities = ClientDefaultCapabilities

        # set translation function
        self.translate = self.__identityTranslation

        if passive:
            # set translation function
            if Preferences.getDebugger("PathTranslation"):
                self.translateRemote = Preferences.getDebugger("PathTranslationRemote")
                self.translateRemoteWindows = "\\" in self.translateRemote
                self.translateLocal = Preferences.getDebugger("PathTranslationLocal")
                self.translateLocalWindows = "\\" in self.translateLocal
                self.translate = self.__remoteTranslation
            else:
                self.translate = self.__identityTranslation

        # attribute to remember the name of the executed script
        self.__scriptName = ""

    def __identityTranslation(self, fn, remote2local=True):  # noqa: U100
        """
        Private method to perform the identity path translation.

        @param fn filename to be translated
        @type str
        @param remote2local flag indicating the direction of translation
            (False = local to remote, True = remote to local) (defaults to True)
            (unused)
        @type bool (optional)
        @return translated filename
        @rtype str
        """
        return fn

    def __remoteTranslation(self, fn, remote2local=True):
        """
        Private method to perform the path translation.

        @param fn filename to be translated
        @type str
        @param remote2local flag indicating the direction of translation
            (False = local to remote, True = remote to local) (defaults to True)
        @type bool (optional)
        @return translated filename
        @rtype str
        """
        if remote2local:
            path = (
                re.sub(
                    f"^{re.escape(self.translateRemote)}",
                    self.translateLocal,
                    fn,
                    flags=re.IGNORECASE,
                )
                if self.translateRemoteWindows
                else fn.replace(self.translateRemote, self.translateLocal)
            )
            if self.translateLocalWindows:
                path = path.replace("/", "\\")
        else:
            path = (
                re.sub(
                    f"^{re.escape(self.translateLocal)}",
                    self.translateRemote,
                    fn,
                    flags=re.IGNORECASE,
                )
                if self.translateLocalWindows
                else fn.replace(self.translateLocal, self.translateRemote)
            )
            if not self.translateRemoteWindows:
                path = path.replace("\\", "/")

        return path

    def __ericServerTranslation(self, fn, remote2local=True):
        """
        Private method to perform the eric-ide server path translation.

        @param fn filename to be translated
        @type str
        @param remote2local flag indicating the direction of translation
            (False = local to remote, True = remote to local) (defaults to True)
        @type bool (optional)
        @return translated filename
        @rtype str
        """
        if remote2local:
            return FileSystemUtilities.remoteFileName(fn)
        else:
            return FileSystemUtilities.plainFileName(fn)

    def __startProcess(self, program, arguments, environment=None, workingDir=""):
        """
        Private method to start the debugger client process.

        @param program name of the executable to start
        @type str
        @param arguments arguments to be passed to the program
        @type list of str
        @param environment dictionary of environment settings to pass
        @type dict of str
        @param workingDir directory to start the debugger client in
        @type str
        @return the process object
        @rtype QProcess or None
        """
        proc = QProcess(self)
        if environment is not None:
            env = QProcessEnvironment()
            for key, value in environment.items():
                env.insert(key, value)
            proc.setProcessEnvironment(env)
        args = arguments[:]
        if workingDir:
            proc.setWorkingDirectory(workingDir)
        proc.start(program, args)
        if not proc.waitForStarted(10000):
            proc = None

        return proc

    def startRemote(
        self,
        port,
        runInConsole,
        venvName,
        originalPathString,
        workingDir="",
        configOverride=None,
        startViaServer=None,
    ):
        """
        Public method to start a remote Python interpreter.

        @param port port number the debug server is listening on
        @type int
        @param runInConsole flag indicating to start the debugger in a
            console window
        @type bool
        @param venvName name of the virtual environment to be used
        @type str
        @param originalPathString original PATH environment variable
        @type str
        @param workingDir directory to start the debugger client in (defaults to "")
        @type str (optional)
        @param configOverride dictionary containing the global config override data
            (defaults to None)
        @type dict (optional)
        @param startViaServer flag indicating to start the client via an eric-ide server
            (defaults to None)
        @type bool (optional)
        @return client process object, a flag to indicate a network connection
            and the name of the interpreter in case of a local execution
        @rtype tuple of (QProcess, bool, str)
        """
        global origPathEnv

        if (
            startViaServer is True
            or (
                startViaServer is None
                and (
                    venvName == self.debugServer.getEricServerEnvironmentString()
                    or self.__ericServerDebugging
                )
            )
        ) and ericApp().getObject("EricServer").isServerConnected():
            startViaServer = True
            if venvName:
                venvManager = ericApp().getObject("VirtualEnvManager")
                interpreter = venvManager.getVirtualenvInterpreter(venvName)
            else:
                venvName = self.debugServer.getEricServerEnvironmentString()
                interpreter = ""  # use the interpreter of the server
        else:
            if not venvName:
                venvName = Preferences.getDebugger("Python3VirtualEnv")
            if venvName == self.debugServer.getProjectEnvironmentString():
                project = ericApp().getObject("Project")
                venvName = project.getProjectVenv()
                execPath = project.getProjectExecPath()
                interpreter = project.getProjectInterpreter()
            else:
                venvManager = ericApp().getObject("VirtualEnvManager")
                interpreter = venvManager.getVirtualenvInterpreter(venvName)
                execPath = venvManager.getVirtualenvExecPath(venvName)
            if interpreter == "":
                # use the interpreter used to run eric for identical variants
                interpreter = PythonUtilities.getPythonExecutable()
            if interpreter == "":
                EricMessageBox.critical(
                    None,
                    self.tr("Start Debugger"),
                    self.tr("""<p>No suitable Python3 environment configured.</p>"""),
                )
                return None, False, ""

        self.__inShutdown = False

        self.__ericServerDebugging = False

        redirect = (
            str(configOverride["redirect"])
            if configOverride and configOverride["enable"]
            else str(Preferences.getDebugger("Python3Redirect"))
        )
        noencoding = (
            "--no-encoding" if Preferences.getDebugger("Python3NoEncoding") else ""
        )
        multiprocessEnabled = (
            "--multiprocess" if Preferences.getDebugger("MultiProcessEnabled") else ""
        )
        callTraceOptimization = (
            "--call-trace-optimization"
            if Preferences.getDebugger("PythonCallTraceOptimization")
            else ""
        )

        if Preferences.getDebugger("RemoteDbgEnabled") and not startViaServer:
            # remote debugging code
            ipaddr = self.debugServer.getHostAddress(False)
            rexec = Preferences.getDebugger("RemoteExecution")
            rhost = Preferences.getDebugger("RemoteHost")
            if rhost == "":
                rhost = "localhost"
            if rexec:
                rdebugClient = Preferences.getDebugger("RemoteDebugClient")
                if not rdebugClient and rhost == "localhost":
                    # it is a remote debugging session on the same host
                    rdebugClient = self.__determineDebugClient()
                args = Utilities.parseOptionString(rexec) + [
                    rhost,
                    interpreter,
                    rdebugClient,
                ]
                if noencoding:
                    args.append(noencoding)
                if multiprocessEnabled:
                    args.append(multiprocessEnabled)
                if callTraceOptimization:
                    args.append(callTraceOptimization)
                args.extend([str(port), redirect, ipaddr])
                if OSUtilities.isWindowsPlatform():
                    if not os.path.splitext(args[0])[1]:
                        for ext in [".exe", ".com", ".cmd", ".bat"]:
                            prog = FileSystemUtilities.getExecutablePath(args[0] + ext)
                            if prog:
                                args[0] = prog
                                break
                else:
                    args[0] = FileSystemUtilities.getExecutablePath(args[0])
                process = self.__startProcess(args[0], args[1:], workingDir=workingDir)
                if process is None:
                    EricMessageBox.critical(
                        None,
                        self.tr("Start Debugger"),
                        self.tr(
                            """<p>The debugger backend could not be"""
                            """ started.</p>"""
                        ),
                    )

                # set translation function
                if Preferences.getDebugger("PathTranslation"):
                    self.translateRemote = Preferences.getDebugger(
                        "PathTranslationRemote"
                    )
                    self.translateRemoteWindows = "\\" in self.translateRemote
                    self.translateLocal = Preferences.getDebugger(
                        "PathTranslationLocal"
                    )
                    self.translate = self.__remoteTranslation
                    self.translateLocalWindows = "\\" in self.translateLocal
                else:
                    self.translate = self.__identityTranslation
                return process, self.__isNetworked, ""
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Start Debugger"),
                    self.tr(
                        "<p>Remote debugging is configured but no command for remote"
                        " login was given.</p>"
                    ),
                )
                return None, False, ""

        elif startViaServer and self.__ericServerDebuggerInterface is not None:
            # debugging via an eric-ide server
            self.translate = self.__ericServerTranslation
            self.__ericServerDebugging = True

            args = []
            if noencoding:
                args.append(noencoding)
            if multiprocessEnabled:
                args.append(multiprocessEnabled)
            if callTraceOptimization:
                args.append(callTraceOptimization)
            self.__ericServerDebuggerInterface.startClient(
                interpreter,
                originalPathString,
                args,
                workingDir=workingDir,
            )
            self.__startedVenv = venvName

            return None, self.__isNetworked, ""

        else:
            # local debugging code below
            debugClient = self.__determineDebugClient()

            # set translation function
            self.translate = self.__identityTranslation

            # setup the environment for the debugger
            if Preferences.getDebugger("DebugEnvironmentReplace"):
                clientEnv = {}
            else:
                clientEnv = os.environ.copy()
                if originalPathString:
                    clientEnv["PATH"] = originalPathString
            envlist = shlex.split(Preferences.getDebugger("DebugEnvironment"))
            for el in envlist:
                with contextlib.suppress(ValueError):
                    key, value = el.split("=", 1)
                    clientEnv[str(key)] = str(value)
            if execPath:
                if "PATH" in clientEnv:
                    clientEnv["PATH"] = os.pathsep.join([execPath, clientEnv["PATH"]])
                else:
                    clientEnv["PATH"] = execPath

            ipaddr = self.debugServer.getHostAddress(True)
            if runInConsole or Preferences.getDebugger("ConsoleDbgEnabled"):
                ccmd = Preferences.getDebugger("ConsoleDbgCommand")
                if ccmd:
                    args = Utilities.parseOptionString(ccmd) + [
                        interpreter,
                        os.path.abspath(debugClient),
                    ]
                    if noencoding:
                        args.append(noencoding)
                    if multiprocessEnabled:
                        args.append(multiprocessEnabled)
                    if callTraceOptimization:
                        args.append(callTraceOptimization)
                    args.extend([str(port), "0", ipaddr])
                    args[0] = FileSystemUtilities.getExecutablePath(args[0])
                    process = self.__startProcess(
                        args[0], args[1:], clientEnv, workingDir=workingDir
                    )
                    if process is None:
                        EricMessageBox.critical(
                            None,
                            self.tr("Start Debugger"),
                            self.tr(
                                """<p>The debugger backend could not be"""
                                """ started.</p>"""
                            ),
                        )
                    return process, self.__isNetworked, interpreter

            args = [debugClient]
            if noencoding:
                args.append(noencoding)
            if multiprocessEnabled:
                args.append(multiprocessEnabled)
            if callTraceOptimization:
                args.append(callTraceOptimization)
            args.extend([str(port), redirect, ipaddr])
            process = self.__startProcess(
                interpreter, args, clientEnv, workingDir=workingDir
            )
            if process is None:
                self.__startedVenv = ""
                EricMessageBox.critical(
                    None,
                    self.tr("Start Debugger"),
                    self.tr("""<p>The debugger backend could not be started.</p>"""),
                )
            else:
                self.__startedVenv = venvName

            return process, self.__isNetworked, interpreter

    def __determineDebugClient(self):
        """
        Private method to determine the debug client to be started.

        @return path of the debug client
        @rtype str
        """
        debugClientType = Preferences.getDebugger("DebugClientType3")
        if debugClientType == "standard":
            debugClient = os.path.join(
                getConfig("ericDir"), "DebugClients", "Python", "DebugClient.py"
            )
        else:
            debugClient = Preferences.getDebugger("DebugClient3")
            if debugClient == "":
                # use the 'standard' debug client if no custom one was configured
                debugClient = os.path.join(
                    getConfig("ericDir"), "DebugClients", "Python", "DebugClient.py"
                )

        return debugClient

    def startRemoteForProject(
        self,
        port,
        runInConsole,
        venvName,
        originalPathString,
        workingDir=None,
        configOverride=None,
        startViaServer=None,
    ):
        """
        Public method to start a remote Python interpreter for a project.

        @param port port number the debug server is listening on
        @type int
        @param runInConsole flag indicating to start the debugger in a
            console window
        @type bool
        @param venvName name of the virtual environment to be used
        @type str
        @param originalPathString original PATH environment variable
        @type str
        @param workingDir directory to start the debugger client in
        @type str
        @param configOverride dictionary containing the global config override
            data
        @type dict
        @param startViaServer flag indicating to start the client via an eric-ide server
            (defaults to None)
        @type bool (optional)
        @return client process object, a flag to indicate a network connection
            and the name of the interpreter in case of a local execution
        @rtype tuple of (QProcess, bool, str)
        """
        global origPathEnv

        project = ericApp().getObject("Project")
        if not project.isDebugPropertiesLoaded():
            return None, self.__isNetworked, ""

        # start debugger with project specific settings
        redirect = (
            str(configOverride["redirect"])
            if configOverride and configOverride["enable"]
            else str(project.getDebugProperty("REDIRECT"))
        )
        noencoding = "--no-encoding" if project.getDebugProperty("NOENCODING") else ""
        multiprocessEnabled = (
            "--multiprocess" if Preferences.getDebugger("MultiProcessEnabled") else ""
        )
        callTraceOptimization = (
            "--call-trace-optimization"
            if Preferences.getDebugger("PythonCallTraceOptimization")
            else ""
        )

        if (
            startViaServer is True
            or (
                startViaServer is None
                and (
                    venvName == self.debugServer.getEricServerEnvironmentString()
                    or self.__ericServerDebugging
                )
            )
        ) and ericApp().getObject("EricServer").isServerConnected():
            startViaServer = True
            if venvName and venvName != self.debugServer.getProjectEnvironmentString():
                venvManager = ericApp().getObject("VirtualEnvManager")
                interpreter = venvManager.getVirtualenvInterpreter(venvName)
            else:
                venvName = project.getProjectVenv()
                interpreter = project.getProjectInterpreter()
            if not venvName:
                venvName = self.debugServer.getEricServerEnvironmentString()
                interpreter = ""  # use the interpreter of the server
        else:
            if venvName and venvName != self.debugServer.getProjectEnvironmentString():
                venvManager = ericApp().getObject("VirtualEnvManager")
                interpreter = venvManager.getVirtualenvInterpreter(venvName)
                execPath = venvManager.getVirtualenvExecPath(venvName)
            else:
                venvName = project.getProjectVenv()
                execPath = project.getProjectExecPath()
                interpreter = project.getProjectInterpreter()
            if interpreter == "":
                EricMessageBox.critical(
                    None,
                    self.tr("Start Debugger"),
                    self.tr("""<p>No suitable Python3 environment configured.</p>"""),
                )
                return None, self.__isNetworked, ""

        self.__inShutdown = False

        self.__ericServerDebugging = False

        if project.getDebugProperty("REMOTEDEBUGGER") and not startViaServer:
            # remote debugging code
            ipaddr = self.debugServer.getHostAddress(False)
            rexec = project.getDebugProperty("REMOTECOMMAND")
            rhost = project.getDebugProperty("REMOTEHOST")
            if rhost == "":
                rhost = "localhost"
            if rexec:
                rdebugClient = project.getDebugProperty("REMOTEDEBUGCLIENT")
                if not rdebugClient and rhost == "localhost":
                    # it is a remote debugging session on the same host
                    rdebugClient = self.__determineDebugClient()
                args = Utilities.parseOptionString(rexec) + [
                    rhost,
                    interpreter,
                    rdebugClient,
                ]
                if noencoding:
                    args.append(noencoding)
                if multiprocessEnabled:
                    args.append(multiprocessEnabled)
                if callTraceOptimization:
                    args.append(callTraceOptimization)
                args.extend([str(port), redirect, ipaddr])
                if OSUtilities.isWindowsPlatform():
                    if not os.path.splitext(args[0])[1]:
                        for ext in [".exe", ".com", ".cmd", ".bat"]:
                            prog = FileSystemUtilities.getExecutablePath(args[0] + ext)
                            if prog:
                                args[0] = prog
                                break
                else:
                    args[0] = FileSystemUtilities.getExecutablePath(args[0])
                process = self.__startProcess(args[0], args[1:], workingDir=workingDir)
                if process is None:
                    EricMessageBox.critical(
                        None,
                        self.tr("Start Debugger"),
                        self.tr(
                            """<p>The debugger backend could not be"""
                            """ started.</p>"""
                        ),
                    )
                # set translation function
                if project.getDebugProperty("PATHTRANSLATION"):
                    self.translateRemote = project.getDebugProperty("REMOTEPATH")
                    self.translateRemoteWindows = "\\" in self.translateRemote
                    self.translateLocal = project.getDebugProperty("LOCALPATH")
                    self.translateLocalWindows = "\\" in self.translateLocal
                    self.translate = self.__remoteTranslation
                else:
                    self.translate = self.__identityTranslation

                self.__startedVenv = "" if process is None else venvName

                return process, self.__isNetworked, ""
            else:
                # remote shell command is missing
                return None, self.__isNetworked, ""

        elif startViaServer and self.__ericServerDebuggerInterface is not None:
            # debugging via an eric-ide server
            self.translate = self.__ericServerTranslation
            self.__ericServerDebugging = True

            args = []
            if noencoding:
                args.append(noencoding)
            if multiprocessEnabled:
                args.append(multiprocessEnabled)
            if callTraceOptimization:
                args.append(callTraceOptimization)
            self.__ericServerDebuggerInterface.startClient(
                interpreter,
                originalPathString,
                args,
                workingDir=workingDir,
            )
            self.__startedVenv = venvName

            return None, self.__isNetworked, ""

        else:
            # local debugging code below
            debugClient = project.getDebugProperty("DEBUGCLIENT")
            if not bool(debugClient) or not os.path.exists(debugClient):
                debugClient = self.__determineDebugClient()

            # set translation function
            self.translate = self.__identityTranslation

            # setup the environment for the debugger
            if project.getDebugProperty("ENVIRONMENTOVERRIDE"):
                clientEnv = {}
            else:
                clientEnv = os.environ.copy()
                if originalPathString:
                    clientEnv["PATH"] = originalPathString
            envlist = shlex.split(project.getDebugProperty("ENVIRONMENTSTRING"))
            for el in envlist:
                with contextlib.suppress(ValueError):
                    key, value = el.split("=", 1)
                    clientEnv[str(key)] = str(value)
            if execPath:
                if "PATH" in clientEnv:
                    clientEnv["PATH"] = os.pathsep.join([execPath, clientEnv["PATH"]])
                else:
                    clientEnv["PATH"] = execPath

            ipaddr = self.debugServer.getHostAddress(True)
            if runInConsole or project.getDebugProperty("CONSOLEDEBUGGER"):
                ccmd = project.getDebugProperty(
                    "CONSOLECOMMAND"
                ) or Preferences.getDebugger("ConsoleDbgCommand")
                if ccmd:
                    args = Utilities.parseOptionString(ccmd) + [
                        interpreter,
                        os.path.abspath(debugClient),
                    ]
                    if noencoding:
                        args.append(noencoding)
                    if multiprocessEnabled:
                        args.append(multiprocessEnabled)
                    if callTraceOptimization:
                        args.append(callTraceOptimization)
                    args.extend([str(port), "0", ipaddr])
                    args[0] = FileSystemUtilities.getExecutablePath(args[0])
                    process = self.__startProcess(
                        args[0], args[1:], clientEnv, workingDir=workingDir
                    )
                    if process is None:
                        EricMessageBox.critical(
                            None,
                            self.tr("Start Debugger"),
                            self.tr(
                                """<p>The debugger backend could not be"""
                                """ started.</p>"""
                            ),
                        )
                    return process, self.__isNetworked, interpreter

            args = [debugClient]
            if noencoding:
                args.append(noencoding)
            if multiprocessEnabled:
                args.append(multiprocessEnabled)
            if callTraceOptimization:
                args.append(callTraceOptimization)
            args.extend([str(port), redirect, ipaddr])
            process = self.__startProcess(
                interpreter, args, clientEnv, workingDir=workingDir
            )
            if process is None:
                self.__startedVenv = ""
                EricMessageBox.critical(
                    None,
                    self.tr("Start Debugger"),
                    self.tr("""<p>The debugger backend could not be started.</p>"""),
                )
            else:
                self.__startedVenv = venvName

            return process, self.__isNetworked, interpreter

    def getClientCapabilities(self):
        """
        Public method to retrieve the debug clients capabilities.

        @return debug client capabilities
        @rtype int
        """
        return self.clientCapabilities

    def newConnection(self, sock):
        """
        Public slot to handle a new connection.

        @param sock reference to the socket object
        @type QTcpSocket
        @return flag indicating success
        @rtype bool
        """
        self.__pendingConnections.append(sock)

        sock.readyRead.connect(lambda: self.__receiveJson(sock))
        sock.disconnected.connect(lambda: self.__socketDisconnected(sock))

        return True

    def __assignDebuggerId(self, sock, debuggerId):
        """
        Private method to set the debugger id for a recent debugger connection
        attempt.

        @param sock reference to the socket object
        @type QTcpSocket
        @param debuggerId id of the connected debug client
        @type str
        """
        if sock and sock in self.__pendingConnections:
            self.__connections[debuggerId] = sock
            self.__pendingConnections.remove(sock)

        if self.__mainDebugger is None:
            self.__mainDebugger = debuggerId
            # Get the remote clients capabilities
            self.remoteCapabilities(debuggerId)

        self.debugServer.signalClientDebuggerId(debuggerId)

        if debuggerId == self.__mainDebugger:
            self.__flush()
            self.debugServer.mainClientConnected()

        self.debugServer.initializeClient(debuggerId)

        # perform auto-continue except for main
        if (
            debuggerId != self.__mainDebugger
            and self.__autoContinue
            and not self.__isStepCommand
        ):
            QTimer.singleShot(0, lambda: self.remoteContinue(debuggerId))

    def __socketDisconnected(self, sock):
        """
        Private slot handling a socket disconnecting.

        @param sock reference to the disconnected socket
        @type QTcpSocket
        """
        for debuggerId in list(self.__connections):
            if self.__connections[debuggerId] is sock:
                del self.__connections[debuggerId]
                self.__handleServerDebugClientDisconnected(debuggerId)
                break
        else:
            if sock in self.__pendingConnections:
                self.__pendingConnections.remove(sock)

        if not self.__connections:
            # no active connections anymore
            self.__handleServerLastClientExited()

    @pyqtSlot(str)
    def __handleServerDebugClientDisconnected(self, debuggerId):
        """
        Private slot handling the disconnect of a debug client.

        @param debuggerId ID of the disconnected debugger
        @type str
        """
        if debuggerId == self.__mainDebugger:
            self.__mainDebugger = None
        if debuggerId in self.__autoContinued:
            self.__autoContinued.remove(debuggerId)
        if not self.__inShutdown:
            with contextlib.suppress(RuntimeError):
                # can be ignored during a shutdown
                self.debugServer.signalClientDisconnected(debuggerId)

    @pyqtSlot()
    def __handleServerLastClientExited(self):
        """
        Private slot to handle the exit of the last debug client connected.
        """
        with contextlib.suppress(RuntimeError):
            # debug server object might have been deleted already
            # ignore this
            self.__autoContinued.clear()
            if not self.__inShutdown:
                self.debugServer.signalLastClientExited()
                self.debugServer.startClient()

    def getDebuggerIds(self):
        """
        Public method to return the IDs of the connected debugger backends.

        @return list of connected debugger backend IDs
        @rtype list of str
        """
        return sorted(self.__connections)

    def __flush(self):
        """
        Private slot to flush the queue.
        """
        if self.__mainDebugger:
            # Send commands that were waiting for the connection.
            if self.__ericServerDebugging:
                for jsonStr in self.__commandQueue:
                    self.__ericServerDebuggerInterface.sendClientCommand(
                        self.__mainDebugger, jsonStr
                    )
            else:
                with contextlib.suppress(KeyError):
                    conn = self.__connections[self.__mainDebugger]
                    for jsonStr in self.__commandQueue:
                        self.__writeJsonCommandToSocket(jsonStr, conn)

        self.__commandQueue.clear()

    def shutdown(self):
        """
        Public method to cleanly shut down.

        It closes our sockets and shuts down the debug clients.
        (Needed on Win OS)
        """
        if not self.__mainDebugger:
            return

        self.__inShutdown = True

        while self.__connections:
            debuggerId, sock = self.__connections.popitem()
            self.__shutdownSocket(sock)

        while self.__pendingConnections:
            sock = self.__pendingConnections.pop()
            self.__shutdownSocket(sock)

        if self.__ericServerDebuggerInterface is not None:
            self.__ericServerDebuggerInterface.stopClient()

        # reinitialize
        self.__commandQueue.clear()

        self.__mainDebugger = None

    def __shutdownSocket(self, sock):
        """
        Private slot to shut down a socket.

        @param sock reference to the socket
        @type QTcpSocket
        """
        # do not want any slots called during shutdown
        sock.readyRead.disconnect()
        sock.disconnected.disconnect()

        # close down socket, and shut down client as well.
        self.__sendJsonCommand("RequestShutdown", {}, sock=sock)
        sock.flush()
        sock.close()

        sock.setParent(None)
        sock.deleteLater()
        del sock

    def isConnected(self):
        """
        Public method to test, if a debug client has connected.

        @return flag indicating the connection status
        @rtype bool
        """
        return bool(self.__connections) or self.__ericServerDebugging

    def remoteEnvironment(self, env):
        """
        Public method to set the environment for a program to debug, run, ...

        @param env environment settings
        @type dict
        """
        self.__sendJsonCommand(
            "RequestEnvironment", {"environment": env}, self.__mainDebugger
        )

    def remoteLoad(
        self,
        fn,
        argv,
        wd,
        traceInterpreter=False,
        autoContinue=True,
        enableMultiprocess=False,
        reportAllExceptions=False,
    ):
        """
        Public method to load a new program to debug.

        @param fn filename to debug
        @type str
        @param argv list of command line arguments to pass to the program
        @type list of str
        @param wd working directory for the program
        @type str
        @param traceInterpreter flag indicating if the interpreter library
            should be traced as well
        @type bool
        @param autoContinue flag indicating, that the debugger should not
            stop at the first executable line
        @type bool
        @param enableMultiprocess flag indicating to perform multiprocess
            debugging
        @type bool
        @param reportAllExceptions flag indicating to report all exceptions
            instead of unhandled exceptions only
        @type bool
        """
        if FileSystemUtilities.isPlainFileName(fn):
            fn = os.path.abspath(fn)

        self.__autoContinue = autoContinue
        self.__scriptName = fn
        self.__isStepCommand = False

        wd = self.translate(wd, False)
        fn = self.translate(fn, False)
        self.__sendJsonCommand(
            "RequestLoad",
            {
                "workdir": wd,
                "filename": fn,
                "argv": argv,
                "traceInterpreter": traceInterpreter,
                "multiprocess": enableMultiprocess,
                "reportAllExceptions": reportAllExceptions,
            },
            self.__mainDebugger,
        )

    def remoteRun(self, fn, argv, wd):
        """
        Public method to load a new program to run.

        @param fn filename to run
        @type str
        @param argv list of command line arguments to pass to the program
        @type list of str
        @param wd working directory for the program
        @type str
        """
        if FileSystemUtilities.isPlainFileName(fn):
            fn = os.path.abspath(fn)

        self.__scriptName = fn

        wd = self.translate(wd, False)
        fn = self.translate(fn, False)
        self.__sendJsonCommand(
            "RequestRun",
            {
                "workdir": wd,
                "filename": fn,
                "argv": argv,
            },
            self.__mainDebugger,
        )

    def remoteCoverage(self, fn, argv, wd, erase=False):
        """
        Public method to load a new program to collect coverage data.

        @param fn filename to run
        @type str
        @param argv list of command line arguments to pass to the program
        @type list of str
        @param wd working directory for the program
        @type str
        @param erase flag indicating that coverage info should be
            cleared first
        @type bool
        """
        if FileSystemUtilities.isPlainFileName(fn):
            fn = os.path.abspath(fn)

        self.__scriptName = fn

        wd = self.translate(wd, False)
        fn = self.translate(fn, False)
        self.__sendJsonCommand(
            "RequestCoverage",
            {
                "workdir": wd,
                "filename": fn,
                "argv": argv,
                "erase": erase,
            },
            self.__mainDebugger,
        )

    def remoteProfile(self, fn, argv, wd, erase=False):
        """
        Public method to load a new program to collect profiling data.

        @param fn filename to run
        @type str
        @param argv list of command line arguments to pass to the program
        @type list of str
        @param wd working directory for the program
        @type str
        @param erase flag indicating that timing info should be cleared
            first
        @type bool
        """
        if FileSystemUtilities.isPlainFileName(fn):
            fn = os.path.abspath(fn)

        self.__scriptName = fn

        wd = self.translate(wd, False)
        fn = self.translate(fn, False)
        self.__sendJsonCommand(
            "RequestProfile",
            {
                "workdir": wd,
                "filename": fn,
                "argv": argv,
                "erase": erase,
            },
            self.__mainDebugger,
        )

    def remoteStatement(self, debuggerId, stmt):
        """
        Public method to execute a Python statement.

        @param debuggerId ID of the debugger backend
        @type str
        @param stmt Python statement to execute.
        @type str
        """
        self.__sendJsonCommand(
            "ExecuteStatement",
            {
                "statement": stmt,
            },
            debuggerId,
        )

    def remoteStep(self, debuggerId):
        """
        Public method to single step the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__isStepCommand = True
        self.__sendJsonCommand("RequestStep", {}, debuggerId)

    def remoteStepOver(self, debuggerId):
        """
        Public method to step over the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__isStepCommand = True
        self.__sendJsonCommand("RequestStepOver", {}, debuggerId)

    def remoteStepOut(self, debuggerId):
        """
        Public method to step out the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__isStepCommand = True
        self.__sendJsonCommand("RequestStepOut", {}, debuggerId)

    def remoteStepQuit(self, debuggerId):
        """
        Public method to stop the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__isStepCommand = True
        self.__sendJsonCommand("RequestStepQuit", {}, debuggerId)

    def remoteContinue(self, debuggerId, special=False):
        """
        Public method to continue the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        @param special flag indicating a special continue operation
        @type bool
        """
        self.__isStepCommand = False
        self.__sendJsonCommand(
            "RequestContinue",
            {
                "special": special,
            },
            debuggerId,
        )

    def remoteContinueUntil(self, debuggerId, line):
        """
        Public method to continue the debugged program to the given line
        or until returning from the current frame.

        @param debuggerId ID of the debugger backend
        @type str
        @param line new line, where execution should be continued to
        @type int
        """
        self.__isStepCommand = False
        self.__sendJsonCommand(
            "RequestContinueUntil",
            {
                "newLine": line,
            },
            debuggerId,
        )

    def remoteMoveIP(self, debuggerId, line):
        """
        Public method to move the instruction pointer to a different line.

        @param debuggerId ID of the debugger backend
        @type str
        @param line new line, where execution should be continued
        @type int
        """
        self.__sendJsonCommand(
            "RequestMoveIP",
            {
                "newLine": line,
            },
            debuggerId,
        )

    def remoteBreakpoint(
        self, debuggerId, fn, line, setBreakpoint, cond=None, temp=False
    ):
        """
        Public method to set or clear a breakpoint.

        @param debuggerId ID of the debugger backend
        @type str
        @param fn filename the breakpoint belongs to
        @type str
        @param line line number of the breakpoint
        @type int
        @param setBreakpoint flag indicating setting or resetting a breakpoint
        @type bool
        @param cond condition of the breakpoint
        @type str
        @param temp flag indicating a temporary breakpoint
        @type bool
        """
        if debuggerId:
            debuggerList = [debuggerId]
        elif self.__ericServerDebugging:
            debuggerList = ["<<all>>"]
        else:
            debuggerList = list(self.__connections)
        for debuggerId in debuggerList:
            self.__sendJsonCommand(
                "RequestBreakpoint",
                {
                    "filename": self.translate(fn, False),
                    "line": line,
                    "temporary": temp,
                    "setBreakpoint": setBreakpoint,
                    "condition": cond,
                },
                debuggerId,
            )

    def remoteBreakpointEnable(self, debuggerId, fn, line, enable):
        """
        Public method to enable or disable a breakpoint.

        @param debuggerId ID of the debugger backend
        @type str
        @param fn filename the breakpoint belongs to
        @type str
        @param line line number of the breakpoint
        @type int
        @param enable flag indicating enabling or disabling a breakpoint
        @type bool
        """
        if debuggerId:
            debuggerList = [debuggerId]
        elif self.__ericServerDebugging:
            debuggerList = ["<<all>>"]
        else:
            debuggerList = list(self.__connections)
        for debuggerId in debuggerList:
            self.__sendJsonCommand(
                "RequestBreakpointEnable",
                {
                    "filename": self.translate(fn, False),
                    "line": line,
                    "enable": enable,
                },
                debuggerId,
            )

    def remoteBreakpointIgnore(self, debuggerId, fn, line, count):
        """
        Public method to ignore a breakpoint the next couple of occurrences.

        @param debuggerId ID of the debugger backend
        @type str
        @param fn filename the breakpoint belongs to
        @type str
        @param line line number of the breakpoint
        @type int
        @param count number of occurrences to ignore
        @type int
        """
        if debuggerId:
            debuggerList = [debuggerId]
        elif self.__ericServerDebugging:
            debuggerList = ["<<all>>"]
        else:
            debuggerList = list(self.__connections)
        for debuggerId in debuggerList:
            self.__sendJsonCommand(
                "RequestBreakpointIgnore",
                {
                    "filename": self.translate(fn, False),
                    "line": line,
                    "count": count,
                },
                debuggerId,
            )

    def remoteWatchpoint(self, debuggerId, cond, setWatch, temp=False):
        """
        Public method to set or clear a watch expression.

        @param debuggerId ID of the debugger backend
        @type str
        @param cond expression of the watch expression
        @type str
        @param setWatch flag indicating setting or resetting a watch expression
        @type bool
        @param temp flag indicating a temporary watch expression
        @type bool
        """
        if debuggerId:
            debuggerList = [debuggerId]
        elif self.__ericServerDebugging:
            debuggerList = ["<<all>>"]
        else:
            debuggerList = list(self.__connections)
        for debuggerId in debuggerList:
            # cond is combination of cond and special (s. watch expression
            # viewer)
            self.__sendJsonCommand(
                "RequestWatch",
                {
                    "temporary": temp,
                    "setWatch": setWatch,
                    "condition": cond,
                },
                debuggerId,
            )

    def remoteWatchpointEnable(self, debuggerId, cond, enable):
        """
        Public method to enable or disable a watch expression.

        @param debuggerId ID of the debugger backend
        @type str
        @param cond expression of the watch expression
        @type str
        @param enable flag indicating enabling or disabling a watch expression
        @type bool
        """
        if debuggerId:
            debuggerList = [debuggerId]
        elif self.__ericServerDebugging:
            debuggerList = ["<<all>>"]
        else:
            debuggerList = list(self.__connections)
        for debuggerId in debuggerList:
            # cond is combination of cond and special (s. watch expression
            # viewer)
            self.__sendJsonCommand(
                "RequestWatchEnable",
                {
                    "condition": cond,
                    "enable": enable,
                },
                debuggerId,
            )

    def remoteWatchpointIgnore(self, debuggerId, cond, count):
        """
        Public method to ignore a watch expression the next couple of
        occurrences.

        @param debuggerId ID of the debugger backend
        @type str
        @param cond expression of the watch expression
        @type str
        @param count number of occurrences to ignore
        @type int
        """
        if debuggerId:
            debuggerList = [debuggerId]
        elif self.__ericServerDebugging:
            debuggerList = ["<<all>>"]
        else:
            debuggerList = list(self.__connections)
        for debuggerId in debuggerList:
            # cond is combination of cond and special (s. watch expression
            # viewer)
            self.__sendJsonCommand(
                "RequestWatchIgnore",
                {
                    "condition": cond,
                    "count": count,
                },
                debuggerId,
            )

    def remoteRawInput(self, debuggerId, inputString):
        """
        Public method to send the raw input to the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        @param inputString raw input
        @type str
        """
        self.__sendJsonCommand(
            "RawInput",
            {
                "input": inputString,
            },
            debuggerId,
        )

    def remoteThreadList(self, debuggerId):
        """
        Public method to request the list of threads from the client.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__sendJsonCommand("RequestThreadList", {}, debuggerId)

    def remoteSetThread(self, debuggerId, tid):
        """
        Public method to request to set the given thread as current thread.

        @param debuggerId ID of the debugger backend
        @type str
        @param tid id of the thread
        @type int
        """
        self.__sendJsonCommand(
            "RequestThreadSet",
            {
                "threadID": tid,
            },
            debuggerId,
        )

    def remoteClientStack(self, debuggerId):
        """
        Public method to request the stack of the main thread.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__sendJsonCommand("RequestStack", {}, debuggerId)

    def remoteClientVariables(
        self, debuggerId, scope, filterList, framenr=0, maxSize=0
    ):
        """
        Public method to request the variables of the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        @param scope scope of the variables (0 = local, 1 = global)
        @type int
        @param filterList list of variable types to filter out
        @type list of str
        @param framenr framenumber of the variables to retrieve
        @type int
        @param maxSize maximum size the formatted value of a variable will
            be shown. If it is bigger than that, a 'too big' indication will
            be given (@@TOO_BIG_TO_SHOW@@).
        @type int
        """
        self.__sendJsonCommand(
            "RequestVariables",
            {
                "frameNumber": framenr,
                "scope": scope,
                "filters": filterList,
                "maxSize": maxSize,
            },
            debuggerId,
        )

    def remoteClientVariable(
        self, debuggerId, scope, filterList, var, framenr=0, maxSize=0
    ):
        """
        Public method to request the variables of the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        @param scope scope of the variables (0 = local, 1 = global)
        @type int
        @param filterList list of variable types to filter out
        @type list of str
        @param var list encoded name of variable to retrieve
        @type list of str
        @param framenr framenumber of the variables to retrieve
        @type int
        @param maxSize maximum size the formatted value of a variable will
            be shown. If it is bigger than that, a 'too big' indication will
            be given (@@TOO_BIG_TO_SHOW@@).
        @type int
        """
        self.__sendJsonCommand(
            "RequestVariable",
            {
                "variable": var,
                "frameNumber": framenr,
                "scope": scope,
                "filters": filterList,
                "maxSize": maxSize,
            },
            debuggerId,
        )

    def remoteClientDisassembly(self, debuggerId):
        """
        Public method to ask the client for the latest traceback disassembly.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__sendJsonCommand("RequestDisassembly", {}, debuggerId)

    def remoteClientSetFilter(self, debuggerId, scope, filterStr):
        """
        Public method to set a variables filter list.

        @param debuggerId ID of the debugger backend
        @type str
        @param scope scope of the variables (0 = local, 1 = global)
        @type int
        @param filterStr regexp string for variable names to filter out
        @type str
        """
        self.__sendJsonCommand(
            "RequestSetFilter",
            {
                "scope": scope,
                "filter": filterStr,
            },
            debuggerId,
        )

    def setCallTraceEnabled(self, debuggerId, on):
        """
        Public method to set the call trace state.

        @param debuggerId ID of the debugger backend
        @type str
        @param on flag indicating to enable the call trace function
        @type bool
        """
        self.__sendJsonCommand(
            "RequestCallTrace",
            {
                "enable": on,
            },
            debuggerId,
        )

    def remoteNoDebugList(self, debuggerId, noDebugList):
        """
        Public method to set a list of programs not to be debugged.

        The programs given in the list will not be run under the control
        of the multi process debugger.

        @param debuggerId ID of the debugger backend
        @type str
        @param noDebugList list of Python programs not to be debugged
        @type list of str
        """
        self.__sendJsonCommand(
            "RequestSetNoDebugList",
            {
                "noDebug": noDebugList,
            },
            debuggerId,
        )

    def remoteBanner(self):
        """
        Public slot to get the banner info of the remote client.
        """
        self.__sendJsonCommand("RequestBanner", {})

    def remoteCapabilities(self, debuggerId):
        """
        Public slot to get the debug clients capabilities.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__sendJsonCommand("RequestCapabilities", {}, debuggerId)

    def remoteCompletion(self, debuggerId, text):
        """
        Public slot to get the a list of possible commandline completions
        from the remote client.

        @param debuggerId ID of the debugger backend
        @type str
        @param text text to be completed
        @type str
        """
        self.__sendJsonCommand(
            "RequestCompletion",
            {
                "text": text,
            },
            debuggerId,
        )

    def setAutoContinue(self, autoContinue):
        """
        Public method to set the automatic continue flag of the interface.

        If this is set to True, the debugger will tell the debug client to continue
        when it stops at the first line of the script to be debugged.

        @param autoContinue flag indicating the auto continue state
        @type bool
        """
        self.__autoContinue = autoContinue

    def __receiveJson(self, sock):
        """
        Private method to handle data from the client.

        @param sock reference to the socket to read data from
        @type QTcpSocket
        """
        headerSize = struct.calcsize(b"!II")

        while sock and sock.bytesAvailable():
            now = time.monotonic()
            while sock.bytesAvailable() < headerSize:
                sock.waitForReadyRead(50)
                if time.monotonic() - now > 2.0:  # 2 seconds timeout
                    return
            header = sock.read(headerSize)
            length, datahash = struct.unpack(b"!II", header)

            data = bytearray()
            now = time.monotonic()
            while len(data) < length:
                maxSize = length - len(data)
                if sock.bytesAvailable() < maxSize:
                    sock.waitForReadyRead(50)
                newData = sock.read(maxSize)
                if newData:
                    data += newData
                else:
                    if time.monotonic() - now > 2.0:  # 2 seconds timeout
                        break

            if zlib.adler32(data) & 0xFFFFFFFF != datahash:
                # corrupted data -> discard and continue
                continue

            jsonStr = data.decode("utf-8", "backslashreplace")

            logging.getLogger(__name__).debug("<Debug-Server> %s", jsonStr)
            ##print("Server: ", jsonStr)    ## debug       # __IGNORE_WARNING_M891__

            if jsonStr:
                self.handleJsonCommand(jsonStr, sock)

    def handleJsonCommand(self, jsonStr, sock):
        """
        Public method to handle a command or response serialized as a
        JSON string.

        @param jsonStr string containing the command or response received
            from the debug backend
        @type str
        @param sock reference to the socket the data was received from
        @type QTcpSocket
        """
        try:
            commandDict = json.loads(jsonStr.strip())
        except (TypeError, ValueError) as err:
            EricMessageBox.critical(
                None,
                self.tr("Debug Protocol Error"),
                self.tr(
                    """<p>The response received from the debugger"""
                    """ backend could not be decoded. Please report"""
                    """ this issue with the received data to the"""
                    """ eric bugs email address.</p>"""
                    """<p>Error: {0}</p>"""
                    """<p>Data:<br/>{1}</p>"""
                ).format(str(err), EricUtilities.html_encode(jsonStr.strip())),
                EricMessageBox.Ok,
            )
            return

        method = commandDict["method"]
        params = commandDict["params"]

        if method == "DebuggerId":
            self.__assignDebuggerId(sock, params["debuggerId"])

        elif method == "ClientOutput":
            self.debugServer.signalClientOutput(params["text"], params["debuggerId"])

        elif method in ["ResponseLine", "ResponseStack"]:
            # Check if obsolete thread was clicked
            if params["stack"] == []:
                # Request updated list
                self.remoteThreadList(params["debuggerId"])
                return
            for s in params["stack"]:
                s[0] = self.translate(s[0], True)
            cf = params["stack"][0]
            if self.__autoContinue and params["debuggerId"] not in self.__autoContinued:
                self.__autoContinued.append(params["debuggerId"])
                QTimer.singleShot(0, lambda: self.remoteContinue(params["debuggerId"]))
            else:
                self.debugServer.signalClientLine(
                    cf[0],
                    int(cf[1]),
                    params["debuggerId"],
                    method == "ResponseStack",
                    threadName=params["threadName"],
                )
                self.debugServer.signalClientStack(
                    params["stack"],
                    params["debuggerId"],
                    threadName=params["threadName"],
                )

        elif method == "CallTrace":
            isCall = params["event"].lower() == "c"
            fromInfo = params["from"]
            toInfo = params["to"]
            self.debugServer.signalClientCallTrace(
                isCall,
                fromInfo["filename"],
                str(fromInfo["linenumber"]),
                fromInfo["codename"],
                toInfo["filename"],
                str(toInfo["linenumber"]),
                toInfo["codename"],
                params["debuggerId"],
            )

        elif method == "ResponseVariables":
            self.debugServer.signalClientVariables(
                params["scope"], params["variables"], params["debuggerId"]
            )

        elif method == "ResponseVariable":
            self.debugServer.signalClientVariable(
                params["scope"],
                [params["variable"]] + params["variables"],
                params["debuggerId"],
            )

        elif method == "ResponseThreadList":
            self.debugServer.signalClientThreadList(
                params["currentID"], params["threadList"], params["debuggerId"]
            )

        elif method == "ResponseThreadSet":
            self.debugServer.signalClientThreadSet(params["debuggerId"])

        elif method == "ResponseCapabilities":
            self.clientCapabilities = params["capabilities"]
            if params["debuggerId"] == self.__mainDebugger:
                # signal only for the main connection
                self.debugServer.signalClientCapabilities(
                    params["capabilities"],
                    params["clientType"],
                    self.__startedVenv,
                )

        elif method == "ResponseBanner":
            if params["debuggerId"] == self.__mainDebugger:
                # signal only for the main connection
                self.debugServer.signalClientBanner(
                    params["version"],
                    params["platform"],
                    self.__startedVenv,
                )

        elif method == "ResponseOK":
            self.debugServer.signalClientStatement(False, params["debuggerId"])

        elif method == "ResponseContinue":
            self.debugServer.signalClientStatement(True, params["debuggerId"])

        elif method == "RequestRaw":
            self.debugServer.signalClientRawInput(
                params["prompt"], params["echo"], params["debuggerId"]
            )
            pass

        elif method == "ResponseBPConditionError":
            fn = self.translate(params["filename"], True)
            self.debugServer.signalClientBreakConditionError(
                fn, params["line"], params["debuggerId"]
            )

        elif method == "ResponseClearBreakpoint":
            fn = self.translate(params["filename"], True)
            self.debugServer.signalClientClearBreak(
                fn, params["line"], params["debuggerId"]
            )

        elif method == "ResponseWatchConditionError":
            self.debugServer.signalClientWatchConditionError(
                params["condition"], params["debuggerId"]
            )

        elif method == "ResponseClearWatch":
            self.debugServer.signalClientClearWatch(
                params["condition"], params["debuggerId"]
            )

        elif method == "ResponseDisassembly":
            self.debugServer.signalClientDisassembly(
                params["disassembly"], params["debuggerId"]
            )

        elif method == "ResponseException":
            exctype = params["type"]
            excmessage = params["message"]
            stack = params["stack"]
            if stack:
                for stackEntry in stack:
                    stackEntry[0] = self.translate(stackEntry[0], True)
                if stack[0] and stack[0][0] == "<string>":
                    for stackEntry in stack:
                        if stackEntry[0] == "<string>":
                            stackEntry[0] = self.__scriptName
                        else:
                            break

            self.debugServer.signalClientException(
                exctype, excmessage, stack, params["debuggerId"], params["threadName"]
            )

        elif method == "ResponseSyntax":
            self.debugServer.signalClientSyntaxError(
                params["message"],
                self.translate(params["filename"], True),
                params["linenumber"],
                params["characternumber"],
                params["debuggerId"],
                params["threadName"],
            )

        elif method == "ResponseSignal":
            self.debugServer.signalClientSignal(
                params["message"],
                self.translate(params["filename"], True),
                params["linenumber"],
                params["function"],
                params["arguments"],
                params["debuggerId"],
            )

        elif method == "ResponseExit":
            self.__scriptName = ""
            self.debugServer.signalClientExit(
                self.translate(params["program"], True),
                params["status"],
                params["message"],
                params["debuggerId"],
            )
            if params["debuggerId"] == self.__mainDebugger:
                self.debugServer.signalMainClientExit()

        elif method == "PassiveStartup":
            self.debugServer.passiveStartUp(
                self.translate(params["filename"], True),
                params["reportAllExceptions"],
                params["debuggerId"],
            )

        elif method == "ResponseCompletion":
            self.debugServer.signalClientCompletionList(
                params["completions"], params["text"], params["debuggerId"]
            )

    def __sendJsonCommand(self, command, params, debuggerId="", sock=None):
        """
        Private method to send a single command to the client.

        @param command command name to be sent
        @type str
        @param params dictionary of named parameters for the command
        @type dict
        @param debuggerId id of the debug client to send the command to
        @type str
        @param sock reference to the socket object to be used (only used if
            debuggerId is not given)
        @type QTcpSocket
        """
        commandDict = {
            "jsonrpc": "2.0",
            "method": command,
            "params": params,
        }
        jsonStr = json.dumps(commandDict)

        if self.__ericServerDebugging:
            # Debugging via the eric-ide server -> pass the command on to it
            if self.__mainDebugger is None:
                # debugger has not connected yet -> queue the command
                self.__commandQueue.append(jsonStr)
            else:
                self.__ericServerDebuggerInterface.sendClientCommand(
                    debuggerId, jsonStr
                )
        else:
            # Local debugging -> send the command to the client
            if debuggerId and debuggerId in self.__connections:
                sock = self.__connections[debuggerId]
            elif sock is None and self.__mainDebugger is not None:
                with contextlib.suppress(KeyError):
                    sock = self.__connections[self.__mainDebugger]
            if sock is not None:
                self.__writeJsonCommandToSocket(jsonStr, sock)
            else:
                self.__commandQueue.append(jsonStr)

    def __writeJsonCommandToSocket(self, jsonCommand, sock):
        """
        Private method to write a JSON command to the socket.

        @param jsonCommand JSON encoded command to be sent
        @type str
        @param sock reference to the socket to write to
        @type QTcpSocket
        """
        data = jsonCommand.encode("utf8", "backslashreplace")
        header = struct.pack(b"!II", len(data), zlib.adler32(data) & 0xFFFFFFFF)
        sock.write(header)
        sock.write(data)
        sock.flush()


def createDebuggerInterfacePython3(debugServer, passive):
    """
    Module function to create a debugger interface instance.


    @param debugServer reference to the debug server
    @type DebugServer
    @param passive flag indicating passive connection mode
    @type bool
    @return instantiated debugger interface
    @rtype DebuggerInterfacePython
    """
    return DebuggerInterfacePython(debugServer, passive)


def getRegistryData():
    """
    Module function to get characterizing data for the supported debugger
    interfaces.

    @return list of tuples containing the client type, the client capabilities,
        the client file type associations and a reference to the creation
        function
    @rtype list of tuple of (str, int, list of str, function)
    """
    py3Exts = []
    for ext in Preferences.getDebugger("Python3Extensions").split():
        if ext.startswith("."):
            py3Exts.append(ext)
        else:
            py3Exts.append(".{0}".format(ext))

    registryData = []
    if py3Exts:
        registryData.append(
            (
                "Python3",
                ClientDefaultCapabilities,
                py3Exts,
                createDebuggerInterfacePython3,
            )
        )

    return registryData
