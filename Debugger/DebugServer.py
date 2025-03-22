# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the debug server.
"""

import contextlib
import importlib
import os
import shlex

from PyQt6.QtCore import QModelIndex, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QHostAddress, QHostInfo, QNetworkInterface, QTcpServer

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities

from . import DebugClientCapabilities
from .BreakPointModel import BreakPointModel
from .WatchPointModel import WatchPointModel

DebuggerInterfaces = {
    "Python": "DebuggerInterfacePython",
    "None": "DebuggerInterfaceNone",
}

NetworkInterfaceMapping = {
    "all": QHostAddress.SpecialAddress.Any,
    "allv4": QHostAddress.SpecialAddress.AnyIPv4,
    "allv6": QHostAddress.SpecialAddress.AnyIPv6,
    "localv4": QHostAddress.SpecialAddress.LocalHost,
    "localv6": QHostAddress.SpecialAddress.LocalHostIPv6,
}


class DebugServer(QTcpServer):
    """
    Class implementing the debug server embedded within the IDE.

    @signal clientProcessStdout(str) emitted after the client has sent some
        output via stdout
    @signal clientProcessStderr(str) emitted after the client has sent some
        output via stderr
    @signal clientOutput(str) emitted after the client has sent some output
    @signal clientRawInputSent(debuggerId) emitted after the data was sent
        to the indicated debug client
    @signal clientLine(filename, lineno, debuggerId, threadName, forStack)
        emitted after the debug client has executed a line of code
    @signal clientStack(stack, debuggerId, threadName) emitted after the
        debug client has executed a line of code
    @signal clientThreadList(currentId, threadList, debuggerId) emitted after
        a thread list has been received
    @signal clientThreadSet(debuggerId) emitted after the client has
        acknowledged the change of the current thread
    @signal clientVariables(scope, variables, debuggerId) emitted after a
        variables dump has been received
    @signal clientVariable(scope, variables, debuggerId) emitted after a dump
        for one class variable has been received
    @signal clientStatement(continue, debuggerId) emitted after an interactive
        command has been executed. The parameter is False to indicate that the
        command is complete and True if it needs more input.
    @signal clientDisassembly(disassembly, debuggerId) emitted after the client
        has sent a disassembly of the code raising an exception
    @signal clientException(exceptionType, exceptionMessage, stackTrace,
        debuggerId, threadName) emitted after an exception occured on the
        client side
    @signal clientSyntaxError(message, filename, linenumber, characternumber,
        debuggerId, threadName) emitted after a syntax error has been detected
        on the client side
    @signal clientSignal(message, filename, linenumber, function name,
        function arguments, debuggerId) emitted after a signal has been
        generated on the client side
    @signal clientDisconnected(str) emitted after a debug client has
        disconnected (i.e. closed the network socket)
    @signal clientExit(str, int, str, bool, str) emitted after the client has
        exited giving the program name, the exit status, an exit message, an
        indication to be quiet and the ID of the exited client
    @signal mainClientExit() emitted to indicate that the main client process
        has exited
    @signal lastClientExited() emitted to indicate that the last connected
        debug client has terminated
    @signal clientClearBreak(filename, lineno, debuggerId) emitted after the
        debug client has decided to clear a temporary breakpoint
    @signal clientBreakConditionError(fn, lineno, debuggerId) emitted after the
        client has signaled a syntax error in a breakpoint condition
    @signal clientClearWatch(condition, debuggerId) emitted after the debug
        client has decided to clear a temporary watch expression
    @signal clientWatchConditionError(condition, debuggerId) emitted after the
        client has signaled a syntax error in a watch expression
    @signal clientRawInput(prompt, echo, debuggerId) emitted after a raw input
        request was received
    @signal clientBanner(version, platform, venvname) emitted after
        the client banner data was received
    @signal clientCapabilities(capabilities, cltype, venvname) emitted after
        the clients capabilities were received
    @signal clientCompletionList(completionList, text) emitted after the
        commandline completion list and the reworked search string was
        received from the client
    @signal passiveDebugStarted(str, bool) emitted after the debug client has
        connected in passive debug mode
    @signal clientGone(bool) emitted if the client went away (planned or
        unplanned)
    @signal clientInterpreterChanged(str) emitted to signal a change of the
        client interpreter
    @signal callTraceInfo emitted after the client reported the call trace
        data (isCall, fromFile, fromLine, fromFunction, toFile, toLine,
        toFunction, debuggerId)
    @signal appendStdout(msg) emitted when a passive debug connection is
        established or lost
    @signal clientDebuggerId(debuggerId) emitted to indicate a newly connected
        debugger backend
    """

    clientClearBreak = pyqtSignal(str, int, str)
    clientClearWatch = pyqtSignal(str, str)
    clientGone = pyqtSignal(bool)
    clientProcessStdout = pyqtSignal(str)
    clientProcessStderr = pyqtSignal(str)
    clientRawInputSent = pyqtSignal(str)
    clientOutput = pyqtSignal(str)
    clientLine = pyqtSignal(str, int, str, str, bool)
    clientStack = pyqtSignal(list, str, str)
    clientThreadList = pyqtSignal("PyQt_PyObject", list, str)
    clientThreadSet = pyqtSignal(str)
    clientVariables = pyqtSignal(int, list, str)
    clientVariable = pyqtSignal(int, list, str)
    clientStatement = pyqtSignal(bool, str)
    clientDisassembly = pyqtSignal(dict, str)
    clientException = pyqtSignal(str, str, list, str, str)
    clientSyntaxError = pyqtSignal(str, str, int, int, str, str)
    clientSignal = pyqtSignal(str, str, int, str, str, str)
    clientDisconnected = pyqtSignal(str)
    clientExit = pyqtSignal(str, int, str, bool, str)
    mainClientExit = pyqtSignal()
    lastClientExited = pyqtSignal()
    clientBreakConditionError = pyqtSignal(str, int, str)
    clientWatchConditionError = pyqtSignal(str, str)
    clientRawInput = pyqtSignal(str, bool, str)
    clientBanner = pyqtSignal(str, str, str)
    clientCapabilities = pyqtSignal(int, str, str)
    clientCompletionList = pyqtSignal(list, str)
    clientInterpreterChanged = pyqtSignal(str)
    clientDebuggerId = pyqtSignal(str)
    passiveDebugStarted = pyqtSignal(str, bool)
    callTraceInfo = pyqtSignal(bool, str, str, str, str, str, str, str)
    appendStdout = pyqtSignal(str)

    def __init__(
        self,
        originalPathString,
        preventPassiveDebugging=False,
        project=None,
        parent=None,
    ):
        """
        Constructor

        @param originalPathString original PATH environment variable
        @type str
        @param preventPassiveDebugging flag overriding the PassiveDbgEnabled
            setting (defaults to False)
        @type bool (optional)
        @param project reference to the project object (defaults to None)
        @type Project (optional)
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__originalPathString = originalPathString

        self.__debuggerInterfaces = {}
        # the interface name is the key, a function to get the
        # registration data is the value
        self.__debuggerInterfaceRegistry = {}
        # the client language is the key, a list containing the client
        # capabilities, a list of associated file extensions, a
        # function reference to create the debugger interface (see
        # __createDebuggerInterface() below) and the interface name is
        # the value

        # create our models
        self.breakpointModel = BreakPointModel(project, self)
        self.watchpointModel = WatchPointModel(self)
        self.watchSpecialCreated = self.tr(
            "created", "must be same as in EditWatchpointDialog"
        )
        self.watchSpecialChanged = self.tr(
            "changed", "must be same as in EditWatchpointDialog"
        )

        # arrays to track already reported issues
        self.__reportedBreakpointIssues = []
        self.__reportedWatchpointIssues = []

        self.networkInterface = Preferences.getDebugger("NetworkInterface")
        hostAddress = (
            QHostAddress(NetworkInterfaceMapping[self.networkInterface])
            if self.networkInterface in NetworkInterfaceMapping
            else QHostAddress(self.networkInterface)
        )
        (
            self.networkInterfaceName,
            self.networkInterfaceIndex,
        ) = self.__getNetworkInterfaceAndIndex(self.networkInterface)

        if not preventPassiveDebugging and Preferences.getDebugger("PassiveDbgEnabled"):
            port = Preferences.getDebugger("PassiveDbgPort")  # default: 42424
            self.listen(hostAddress, port)
            self.passive = True
            self.passiveClientExited = False
        else:
            if hostAddress.toString().lower().startswith("fe80"):
                hostAddress.setScopeId(self.networkInterfaceName)
            if Preferences.getDebugger("NetworkPortFixed"):
                port = Preferences.getDebugger("NetworkPort")
                res = self.listen(hostAddress, port)
                if not res and Preferences.getDebugger("NetworkPortIncrement"):
                    maxPort = port + 100  # try a maximum of 100 ports
                    while not res and port < maxPort:
                        port += 1
                        res = self.listen(hostAddress, port)
            else:
                self.listen(hostAddress)
            self.passive = False

        self.debuggerInterface = None
        self.debugging = False
        self.running = False
        self.clientProcess = None
        self.clientInterpreter = ""
        self.clientType = Preferences.getSettings().value("DebugClient/Type")
        if self.clientType is None:
            self.clientType = "Python3"

        self.lastClientType = ""
        self.__autoClearShell = False
        self.__forProject = False

        self.__ericServerDebugging = False

        self.clientClearBreak.connect(self.__clientClearBreakPoint)
        self.clientClearWatch.connect(self.__clientClearWatchPoint)
        self.newConnection.connect(self.__newConnection)

        self.breakpointModel.rowsAboutToBeRemoved.connect(self.__deleteBreakPoints)
        self.breakpointModel.dataAboutToBeChanged.connect(
            self.__breakPointDataAboutToBeChanged
        )
        self.breakpointModel.dataChanged.connect(self.__changeBreakPoints)
        self.breakpointModel.rowsInserted.connect(self.__addBreakPoints)

        self.watchpointModel.rowsAboutToBeRemoved.connect(self.__deleteWatchPoints)
        self.watchpointModel.dataAboutToBeChanged.connect(
            self.__watchPointDataAboutToBeChanged
        )
        self.watchpointModel.dataChanged.connect(self.__changeWatchPoints)
        self.watchpointModel.rowsInserted.connect(self.__addWatchPoints)

        self.__maxVariableSize = Preferences.getDebugger("MaxVariableSize")

        self.__multiprocessNoDebugList = []

        self.__registerDebuggerInterfaces()

    def getHostAddress(self, localhost):
        """
        Public method to get the IP address or hostname the debug server is
        listening.

        @param localhost flag indicating to return the address for localhost
        @type bool
        @return IP address or hostname
        @rtype str
        """
        if self.networkInterface in ("allv4", "localv4"):
            if localhost or self.networkInterface == "localv4":
                return "127.0.0.1"
            else:
                return "{0}@@v4".format(QHostInfo.localHostName())
        elif self.networkInterface in ("all", "allv6", "localv6"):
            if localhost or self.networkInterface == "localv6":
                return "::1"
            else:
                return "{0}@@v6".format(QHostInfo.localHostName())
        else:
            return "{0}@@i{1}".format(self.networkInterface, self.networkInterfaceIndex)

    def __getNetworkInterfaceAndIndex(self, address):
        """
        Private method to determine the network interface and the interface
        index.

        @param address address to determine the info for
        @type str
        @return tuple of network interface name and index
        @rtype tuple of (str, int)
        """
        if address not in ["all", "allv6"]:
            for networkInterface in QNetworkInterface.allInterfaces():
                addressEntries = networkInterface.addressEntries()
                if len(addressEntries) > 0:
                    for addressEntry in addressEntries:
                        if addressEntry.ip().toString().lower() == address.lower():
                            return (
                                networkInterface.humanReadableName(),
                                networkInterface.index(),
                            )

        return "", 0

    def preferencesChanged(self):
        """
        Public slot to handle the preferencesChanged signal.
        """
        registeredInterfaces = {}
        for interfaceName in self.__debuggerInterfaces:
            registeredInterfaces[interfaceName] = self.__debuggerInterfaces[
                interfaceName
            ]

        self.__debuggerInterfaceRegistry = {}
        for interfaceName, getRegistryData in registeredInterfaces.items():
            self.registerDebuggerInterface(
                interfaceName, getRegistryData, reregister=True
            )

        self.__maxVariableSize = Preferences.getDebugger("MaxVariableSize")

    def registerDebuggerInterface(
        self, interfaceName, getRegistryData, reregister=False
    ):
        """
        Public method to register a debugger interface.

        @param interfaceName name of the debugger interface
        @type str
        @param getRegistryData reference to a function to be called
            to get the debugger interface details. This method shall
            return the client language, the client capabilities, the
            list of associated file extensions and a function reference
            to create the debugger interface (see __createDebuggerInterface())
        @type function
        @param reregister flag indicating to re-register the interface
        @type bool
        """
        if interfaceName in self.__debuggerInterfaces and not reregister:
            EricMessageBox.warning(
                None,
                self.tr("Register Debugger Interface"),
                self.tr(
                    """<p>The debugger interface <b>{0}</b> has already"""
                    """ been registered. Ignoring this request.</p>"""
                ),
            )
            return

        if not reregister:
            self.__debuggerInterfaces[interfaceName] = getRegistryData
        registryDataList = getRegistryData()
        if registryDataList:
            for (
                clientLanguage,
                clientCapabilities,
                clientExtensions,
                interfaceCreator,
            ) in registryDataList:
                self.__debuggerInterfaceRegistry[clientLanguage] = [
                    clientCapabilities,
                    clientExtensions,
                    interfaceCreator,
                    interfaceName,
                ]

    def unregisterDebuggerInterface(self, interfaceName):
        """
        Public method to unregister a debugger interface.

        @param interfaceName interfaceName of the debugger interface
        @type str
        """
        if interfaceName in self.__debuggerInterfaces:
            clientLanguages = []
            for (
                clientLanguage,
                registryData,
            ) in self.__debuggerInterfaceRegistry.items():
                if interfaceName == registryData[-1]:
                    clientLanguages.append(clientLanguage)
            for clientLanguage in clientLanguages:
                del self.__debuggerInterfaceRegistry[clientLanguage]
            del self.__debuggerInterfaces[interfaceName]

    def __findLanguageForExtension(self, ext):
        """
        Private method to get the language associated with a file extension.

        @param ext file extension
        @type str
        @return associated language
        @rtype str
        """
        for language in self.__debuggerInterfaceRegistry:
            if ext in self.__debuggerInterfaceRegistry[language][1]:
                return language

        return ""

    def __registerDebuggerInterfaces(self):
        """
        Private method to register the available internal debugger interfaces.
        """
        for name, interface in DebuggerInterfaces.items():
            mod = importlib.import_module(".{0}".format(interface), __package__)
            self.registerDebuggerInterface(name, mod.getRegistryData)

    def getSupportedLanguages(self, shellOnly=False):
        """
        Public slot to return the supported programming languages.

        @param shellOnly flag indicating only languages supporting an
            interactive shell should be returned
        @type bool
        @return list of supported languages
        @rtype list of str
        """
        languages = list(self.__debuggerInterfaceRegistry)
        with contextlib.suppress(ValueError):
            languages.remove("None")

        if shellOnly:
            languages = [
                lang
                for lang in languages
                if self.__debuggerInterfaceRegistry[lang][0]
                & DebugClientCapabilities.HasShell
            ]

        return languages[:]

    def getExtensions(self, language):
        """
        Public slot to get the extensions associated with the given language.

        @param language language to get extensions for
        @type str
        @return tuple of extensions associated with the language
        @rtype tuple of str
        """
        if language in self.__debuggerInterfaceRegistry:
            return tuple(self.__debuggerInterfaceRegistry[language][1])
        else:
            return ()

    def __createDebuggerInterface(self, clientType=None):
        """
        Private slot to create the debugger interface object.

        @param clientType type of the client interface to be created
        @type str
        """
        if self.lastClientType != self.clientType or clientType is not None:
            if clientType is None:
                clientType = self.clientType
            if clientType in self.__debuggerInterfaceRegistry:
                self.debuggerInterface = self.__debuggerInterfaceRegistry[clientType][
                    2
                ](self, self.passive)
            else:
                self.debuggerInterface = self.__debuggerInterfaceRegistry["None"][2](
                    self, self.passive
                )
                self.clientType = "None"

    def __setClientType(self, clType):
        """
        Private method to set the client type.

        @param clType type of client to be started
        @type str
        """
        if clType is not None and clType in self.getSupportedLanguages():
            self.clientType = clType
            Preferences.getSettings().setValue("DebugClient/Type", self.clientType)

    def startClient(
        self,
        unplanned=True,
        clType=None,
        forProject=False,
        runInConsole=False,
        venvName="",
        workingDir="",
        configOverride=None,
        startViaServer=None,
    ):
        """
        Public method to start a debug client.

        @param unplanned flag indicating that the client has died (defaults to True)
        @type bool (optional)
        @param clType type of client to be started (defaults to None)
        @type str (optional)
        @param forProject flag indicating a project related action (defaults to False)
        @type bool (optional)
        @param runInConsole flag indicating to start the debugger in a
            console window (defaults to False)
        @type bool (optional)
        @param venvName name of the virtual environment to be used (defaults to "")
        @type str (optional)
        @param workingDir directory to start the debugger client in (defaults to "")
        @type str (optional)
        @param configOverride dictionary containing the global config override data
            (defaults to None)
        @type dict (optional)
        @param startViaServer flag indicating to start the client via an eric-ide server
            (defaults to None)
        @type bool (optional)
        """
        self.running = False

        if (
            (not self.passive or not self.passiveClientExited)
            and self.debuggerInterface
            and self.debuggerInterface.isConnected()
        ):
            self.shutdownServer()
            self.debugging = False
            self.clientGone.emit(unplanned and self.debugging)

        if clType:
            if clType not in self.getSupportedLanguages():
                # a not supported client language was requested
                return

            self.__setClientType(clType)

        # only start the client, if we are not in passive mode
        if not self.passive:
            if self.clientProcess:
                with contextlib.suppress(RuntimeError):
                    # Workaround: The wrapped C/C++ object of type QProcess
                    # gets deleted prematurely sometimes.
                    self.clientProcess.kill()
                    self.clientProcess.waitForFinished(1000)
                    self.clientProcess.deleteLater()
                self.clientProcess = None

            self.__forProject = forProject
            self.__createDebuggerInterface()
            if forProject:
                project = ericApp().getObject("Project")
                if project.isDebugPropertiesLoaded():
                    (
                        self.clientProcess,
                        _isNetworked,
                        clientInterpreter,
                    ) = self.debuggerInterface.startRemoteForProject(
                        self.serverPort(),
                        runInConsole,
                        venvName,
                        self.__originalPathString,
                        workingDir=workingDir,
                        configOverride=configOverride,
                        startViaServer=startViaServer,
                    )
                else:
                    if not venvName and project.getProjectData(dataKey="EMBEDDED_VENV"):
                        venvName = self.getProjectEnvironmentString()

                    (
                        self.clientProcess,
                        _isNetworked,
                        clientInterpreter,
                    ) = self.debuggerInterface.startRemote(
                        self.serverPort(),
                        runInConsole,
                        venvName,
                        self.__originalPathString,
                        workingDir=workingDir,
                        configOverride=configOverride,
                        startViaServer=startViaServer,
                    )
            else:
                (
                    self.clientProcess,
                    _isNetworked,
                    clientInterpreter,
                ) = self.debuggerInterface.startRemote(
                    self.serverPort(),
                    runInConsole,
                    venvName,
                    self.__originalPathString,
                    workingDir=workingDir,
                    configOverride=configOverride,
                    startViaServer=startViaServer,
                )

            if self.clientProcess:
                self.clientProcess.readyReadStandardError.connect(
                    self.__clientProcessError
                )
                self.clientProcess.readyReadStandardOutput.connect(
                    self.__clientProcessOutput
                )

                # Perform actions necessary, if client type has changed
                if self.lastClientType != self.clientType:
                    self.lastClientType = self.clientType
                    self.remoteBanner()
                elif self.__autoClearShell:
                    self.__autoClearShell = False
                    self.remoteBanner()
            elif startViaServer:
                self.__ericServerDebugging = True
                if self.lastClientType != self.clientType:
                    self.lastClientType = self.clientType
                    self.remoteBanner()
                elif self.__autoClearShell:
                    self.__autoClearShell = False
                    self.remoteBanner()
            else:
                if clType and self.lastClientType:
                    self.__setClientType(self.lastClientType)
        else:
            self.__createDebuggerInterface("None")
            clientInterpreter = ""

        if clientInterpreter != self.clientInterpreter:
            self.clientInterpreter = clientInterpreter
            self.clientInterpreterChanged.emit(clientInterpreter)

    def __clientProcessOutput(self):
        """
        Private slot to process client output received via stdout.
        """
        output = str(
            self.clientProcess.readAllStandardOutput(),
            Preferences.getSystem("IOEncoding"),
            "replace",
        )
        self.clientProcessStdout.emit(output)

    def __clientProcessError(self):
        """
        Private slot to process client output received via stderr.
        """
        error = str(
            self.clientProcess.readAllStandardError(),
            Preferences.getSystem("IOEncoding"),
            "replace",
        )
        self.clientProcessStderr.emit(error)

    @pyqtSlot(str, int)
    def __clientClearBreakPoint(self, fn, lineno):
        """
        Private slot to handle the clientClearBreak signal.

        @param fn filename of breakpoint to clear
        @type str
        @param lineno line number of breakpoint to clear
        @type int
        """
        if self.debugging:
            index = self.breakpointModel.getBreakPointIndex(fn, lineno)
            self.breakpointModel.deleteBreakPointByIndex(index)
            if (fn, lineno) in self.__reportedBreakpointIssues:
                self.__reportedBreakpointIssues.remove((fn, lineno))

    def __deleteBreakPoints(self, parentIndex, start, end):
        """
        Private slot to delete breakpoints.

        @param parentIndex index of parent item
        @type QModelIndex
        @param start start row
        @type int
        @param end end row
        @type int
        """
        if self.debugging:
            for row in range(start, end + 1):
                index = self.breakpointModel.index(row, 0, parentIndex)
                fn, lineno = self.breakpointModel.getBreakPointByIndex(index)[0:2]
                # delete the breakpoints of all connected backends
                self.remoteBreakpoint("", fn, lineno, False)
                if (fn, lineno) in self.__reportedBreakpointIssues:
                    self.__reportedBreakpointIssues.remove((fn, lineno))

    def __changeBreakPoints(self, startIndex, endIndex):
        """
        Private slot to set changed breakpoints.

        @param startIndex starting index of the change breakpoins
        @type QModelIndex
        @param endIndex ending index of the change breakpoins
        @type QModelIndex
        """
        if self.debugging:
            self.__addBreakPoints(QModelIndex(), startIndex.row(), endIndex.row())

    def __breakPointDataAboutToBeChanged(self, startIndex, endIndex):
        """
        Private slot to handle the dataAboutToBeChanged signal of the
        breakpoint model.

        @param startIndex start index of the rows to be changed
        @type QModelIndex
        @param endIndex end index of the rows to be changed
        @type QModelIndex
        """
        if self.debugging:
            self.__deleteBreakPoints(QModelIndex(), startIndex.row(), endIndex.row())

    def __addBreakPoints(self, parentIndex, start, end, debuggerId=""):
        """
        Private slot to add breakpoints.

        @param parentIndex index of parent item
        @type QModelIndex
        @param start start row
        @type int
        @param end end row
        @type int
        @param debuggerId ID of the debugger backend to send to. If this is
            empty, they will be broadcast to all connected backends.
        @type str
        """
        if self.debugging:
            for row in range(start, end + 1):
                index = self.breakpointModel.index(row, 0, parentIndex)
                (
                    fn,
                    lineno,
                    cond,
                    temp,
                    enabled,
                    ignorecount,
                ) = self.breakpointModel.getBreakPointByIndex(index)[:6]

                if (fn, lineno) in self.__reportedBreakpointIssues:
                    self.__reportedBreakpointIssues.remove((fn, lineno))

                if (
                    self.__ericServerDebugging
                    and FileSystemUtilities.isRemoteFileName(fn)
                ) or (
                    not self.__ericServerDebugging
                    and FileSystemUtilities.isPlainFileName(fn)
                ):
                    self.remoteBreakpoint(debuggerId, fn, lineno, True, cond, temp)
                    if not enabled:
                        self.__remoteBreakpointEnable(debuggerId, fn, lineno, False)
                    if ignorecount:
                        self.__remoteBreakpointIgnore(
                            debuggerId, fn, lineno, ignorecount
                        )

    def __makeWatchCondition(self, cond, special):
        """
        Private method to construct the condition string.

        @param cond condition
        @type str
        @param special special condition
        @type str
        @return condition string
        @rtype str
        """
        if special == "":
            _cond = cond
        else:
            if special == self.watchSpecialCreated:
                _cond = "{0} ??created??".format(cond)
            elif special == self.watchSpecialChanged:
                _cond = "{0} ??changed??".format(cond)
        return _cond

    def __splitWatchCondition(self, cond):
        """
        Private method to split a remote watch expression.

        @param cond remote expression
        @type str
        @return tuple of local expression (string) and special condition
        @rtype str
        """
        if cond.endswith(" ??created??"):
            cond, special = cond.split()
            special = self.watchSpecialCreated
        elif cond.endswith(" ??changed??"):
            cond, special = cond.split()
            special = self.watchSpecialChanged
        else:
            special = ""

        return cond, special

    @pyqtSlot(str)
    def __clientClearWatchPoint(self, condition):
        """
        Private slot to handle the clientClearWatch signal.

        @param condition expression of watch expression to clear
        @type str
        """
        if self.debugging:
            cond, special = self.__splitWatchCondition(condition)
            index = self.watchpointModel.getWatchPointIndex(cond, special)
            self.watchpointModel.deleteWatchPointByIndex(index)
            if condition in self.__reportedWatchpointIssues:
                self.__reportedWatchpointIssues.remove(condition)

    def __deleteWatchPoints(self, parentIndex, start, end):
        """
        Private slot to delete watch expressions.

        @param parentIndex index of parent item
        @type QModelIndex
        @param start start row
        @type int
        @param end end row
        @type int
        """
        if self.debugging:
            for row in range(start, end + 1):
                index = self.watchpointModel.index(row, 0, parentIndex)
                cond, special = self.watchpointModel.getWatchPointByIndex(index)[0:2]
                cond = self.__makeWatchCondition(cond, special)
                self.__remoteWatchpoint("", cond, False)
                if cond in self.__reportedWatchpointIssues:
                    self.__reportedWatchpointIssues.remove(cond)

    def __watchPointDataAboutToBeChanged(self, startIndex, endIndex):
        """
        Private slot to handle the dataAboutToBeChanged signal of the
        watch expression model.

        @param startIndex start index of the rows to be changed
        @type QModelIndex
        @param endIndex end index of the rows to be changed
        @type QModelIndex
        """
        if self.debugging:
            self.__deleteWatchPoints(QModelIndex(), startIndex.row(), endIndex.row())

    def __addWatchPoints(self, parentIndex, start, end, debuggerId=""):
        """
        Private slot to set a watch expression.

        @param parentIndex index of parent item
        @type QModelIndex
        @param start start row
        @type int
        @param end end row
        @type int
        @param debuggerId ID of the debugger backend to send to. If this is
            empty, they will be broadcast to all connected backends.
        @type str
        """
        if self.debugging:
            for row in range(start, end + 1):
                index = self.watchpointModel.index(row, 0, parentIndex)
                (
                    cond,
                    special,
                    temp,
                    enabled,
                    ignorecount,
                ) = self.watchpointModel.getWatchPointByIndex(index)[:5]
                cond = self.__makeWatchCondition(cond, special)

                if cond in self.__reportedWatchpointIssues:
                    self.__reportedWatchpointIssues.remove(cond)

                self.__remoteWatchpoint(debuggerId, cond, True, temp)
                if not enabled:
                    self.__remoteWatchpointEnable(debuggerId, cond, False)
                if ignorecount:
                    self.__remoteWatchpointIgnore(debuggerId, cond, ignorecount)

    def __changeWatchPoints(self, startIndex, endIndex):
        """
        Private slot to set changed watch expressions.

        @param startIndex start index of the rows to be changed
        @type QModelIndex
        @param endIndex end index of the rows to be changed
        @type QModelIndex
        """
        if self.debugging:
            self.__addWatchPoints(QModelIndex(), startIndex.row(), endIndex.row())

    def getClientCapabilities(self, clientType):
        """
        Public method to retrieve the debug clients capabilities.

        @param clientType debug client type
        @type str
        @return debug client capabilities
        @rtype int
        """
        try:
            return self.__debuggerInterfaceRegistry[clientType][0]
        except KeyError:
            return 0  # no capabilities

    def getClientInterpreter(self):
        """
        Public method to get the interpreter of the debug client.

        @return interpreter of the debug client
        @rtype str
        """
        return self.clientInterpreter

    def getClientType(self):
        """
        Public method to get the currently running debug client type.

        @return debug client type
        @rtype str
        """
        return self.clientType

    def isClientProcessUp(self):
        """
        Public method to check, if the debug client process is up or we are
        doing debugging via the eric-ide server.

        @return flag indicating a running debug client process
        @rtype bool
        """
        return self.clientProcess is not None or self.__ericServerDebugging

    def __newConnection(self):
        """
        Private slot to handle a new connection.
        """
        sock = self.nextPendingConnection()
        peerAddress = sock.peerAddress().toString()
        if peerAddress not in Preferences.getDebugger("AllowedHosts"):
            # the peer is not allowed to connect
            res = EricMessageBox.yesNo(
                None,
                self.tr("Connection from unknown host"),
                self.tr(
                    """<p>A connection was attempted by the unknown host"""
                    """ <b>{0}</b>. Accept this connection?</p>"""
                ).format(peerAddress),
                icon=EricMessageBox.Warning,
            )
            if not res:
                sock.abort()
                return
            else:
                allowedHosts = Preferences.getDebugger("AllowedHosts")
                allowedHosts.append(peerAddress)
                Preferences.setDebugger("AllowedHosts", allowedHosts)

        if self.passive:
            self.__createDebuggerInterface(Preferences.getDebugger("PassiveDbgType"))
            self.debuggerInterface.setAutoContinue(
                Preferences.getDebugger("PassivAutoContinue")
            )

        self.debuggerInterface.newConnection(sock)

    def mainClientConnected(self):
        """
        Public method to perform actions after the main client has finally
        established the connection.
        """
        # Perform actions necessary, if client type has changed
        if self.lastClientType != self.clientType:
            self.lastClientType = self.clientType
            self.remoteBanner()
        elif self.__autoClearShell:
            self.__autoClearShell = False
            self.remoteBanner()
        elif self.passive:
            self.remoteBanner()

    def shutdownServer(self):
        """
        Public method to cleanly shut down.

        It closes our socket and shuts down
        the debug client. (Needed on Win OS)
        """
        if self.debuggerInterface is not None:
            self.debuggerInterface.shutdown()

        if self.clientProcess is not None:
            self.clientProcess.terminate()
            if not self.clientProcess.waitForFinished(10000):
                self.clientProcess.kill()

    def remoteEnvironment(self, env):
        """
        Public method to set the environment for a program to debug, run, ...

        @param env environment settings
        @type str or dict
        @exception TypeError taised to indicate an unsupported parameter type
        """
        if not isinstance(env, (dict, str)):
            raise TypeError("'env' must be of type str or list of str")
        elif isinstance(env, str):
            envlist = shlex.split(env)
            envdict = {}
            for el in envlist:
                if "=" in el:
                    key, value = el.split("=", 1)
                    envdict[key] = value
                else:
                    envdict[el] = ""
        else:
            envdict = env
        self.debuggerInterface.remoteEnvironment(envdict)

    def remoteLoad(
        self,
        venvName,
        fn,
        argv,
        wd,
        env,
        autoClearShell=True,
        tracePython=False,
        autoContinue=True,
        forProject=False,
        runInConsole=False,
        clientType="",
        enableCallTrace=False,
        enableMultiprocess=False,
        multiprocessNoDebug="",
        configOverride=None,
        reportAllExceptions=False,
    ):
        """
        Public method to load a new program to debug.

        @param venvName name of the virtual environment to be used
        @type str
        @param fn filename to debug
        @type str
        @param argv list of command line arguments to pass to the program
        @type list of str
        @param wd working directory for the program
        @type str
        @param env environment parameter settings
        @type str or dict
        @param autoClearShell flag indicating, that the interpreter window
            should be cleared
        @type bool
        @param tracePython flag indicating if the Python library should be
            traced as well
        @type bool
        @param autoContinue flag indicating, that the debugger should not
            stop at the first executable line
        @type bool
        @param forProject flag indicating a project related action
        @type bool
        @param runInConsole flag indicating to start the debugger in a
            console window
        @type bool
        @param clientType client type to be used
        @type str
        @param enableCallTrace flag indicating to enable the call trace
            function
        @type bool
        @param enableMultiprocess flag indicating to perform multiprocess
            debugging
        @type bool
        @param multiprocessNoDebug space separated list of programs not to be
            debugged
        @type str
        @param configOverride dictionary containing the global config override
            data
        @type dict
        @param reportAllExceptions flag indicating to report all exceptions
            instead of unhandled exceptions only
        @type bool
        """
        self.__autoClearShell = autoClearShell
        self.__multiprocessNoDebugList = [
            s.strip() for s in multiprocessNoDebug.split(os.pathsep)
        ]

        if clientType not in self.getSupportedLanguages():
            # a not supported client language was requested
            EricMessageBox.critical(
                None,
                self.tr("Start Debugger"),
                self.tr(
                    """<p>The debugger type <b>{0}</b> is not supported"""
                    """ or not configured.</p>"""
                ).format(clientType),
            )
            return

        # Restart the client
        try:
            if clientType:
                self.__setClientType(clientType)
            else:
                self.__setClientType(
                    self.__findLanguageForExtension(os.path.splitext(fn)[1])
                )
        except KeyError:
            self.__setClientType("Python3")  # assume it is a Python3 file
        self.startClient(
            False,
            forProject=forProject,
            runInConsole=runInConsole,
            venvName=venvName,
            configOverride=configOverride,
            startViaServer=FileSystemUtilities.isRemoteFileName(fn),
        )

        self.setCallTraceEnabled("", enableCallTrace)
        self.remoteEnvironment(env)

        self.debuggerInterface.remoteLoad(
            fn,
            argv,
            wd,
            tracePython,
            autoContinue,
            enableMultiprocess=enableMultiprocess,
            reportAllExceptions=reportAllExceptions,
        )
        self.debugging = True
        self.running = True
        self.__restoreBreakpoints()
        self.__restoreWatchpoints()
        self.__restoreNoDebugList()

    def remoteRun(
        self,
        venvName,
        fn,
        argv,
        wd,
        env,
        autoClearShell=True,
        forProject=False,
        runInConsole=False,
        clientType="",
        configOverride=None,
    ):
        """
        Public method to load a new program to run.

        @param venvName name of the virtual environment to be used
        @type str
        @param fn filename to debug
        @type str
        @param argv list of command line arguments to pass to the program
        @type list str
        @param wd  working directory for the program
        @type str
        @param env environment parameter settings
        @type str or dict
        @param autoClearShell flag indicating, that the interpreter window
            should be cleared
        @type bool
        @param forProject flag indicating a project related action
        @type bool
        @param runInConsole flag indicating to start the debugger in a
            console window
        @type bool
        @param clientType client type to be used
        @type str
        @param configOverride dictionary containing the global config override
            data
        @type dict
        """
        self.__autoClearShell = autoClearShell

        if clientType not in self.getSupportedLanguages():
            EricMessageBox.critical(
                None,
                self.tr("Start Debugger"),
                self.tr(
                    """<p>The debugger type <b>{0}</b> is not supported"""
                    """ or not configured.</p>"""
                ).format(clientType),
            )
            # a not supported client language was requested
            return

        # Restart the client
        try:
            if clientType:
                self.__setClientType(clientType)
            else:
                self.__setClientType(
                    self.__findLanguageForExtension(os.path.splitext(fn)[1])
                )
        except KeyError:
            self.__setClientType("Python3")  # assume it is a Python3 file
        self.startClient(
            False,
            forProject=forProject,
            runInConsole=runInConsole,
            venvName=venvName,
            configOverride=configOverride,
            startViaServer=FileSystemUtilities.isRemoteFileName(fn),
        )

        self.remoteEnvironment(env)

        self.debuggerInterface.remoteRun(fn, argv, wd)
        self.debugging = False
        self.running = True

    def remoteCoverage(
        self,
        venvName,
        fn,
        argv,
        wd,
        env,
        autoClearShell=True,
        erase=False,
        forProject=False,
        runInConsole=False,
        clientType="",
        configOverride=None,
    ):
        """
        Public method to load a new program to collect coverage data.

        @param venvName name of the virtual environment to be used
        @type str
        @param fn filename to debug
        @type str
        @param argv list of command line arguments to pass to the program
        @type list of str
        @param wd working directory for the program
        @type str
        @param env environment parameter settings
        @type str or dict
        @param autoClearShell flag indicating, that the interpreter window
            should be cleared
        @type bool
        @param erase flag indicating that coverage info should be
            cleared first
        @type bool
        @param forProject flag indicating a project related action
        @type bool
        @param runInConsole flag indicating to start the debugger in a
            console window
        @type bool
        @param clientType client type to be used
        @type str
        @param configOverride dictionary containing the global config override
            data
        @type dict
        """
        self.__autoClearShell = autoClearShell

        if clientType not in self.getSupportedLanguages():
            # a not supported client language was requested
            EricMessageBox.critical(
                None,
                self.tr("Start Debugger"),
                self.tr(
                    """<p>The debugger type <b>{0}</b> is not supported"""
                    """ or not configured.</p>"""
                ).format(clientType),
            )
            return

        # Restart the client
        try:
            if clientType:
                self.__setClientType(clientType)
            else:
                self.__setClientType(
                    self.__findLanguageForExtension(os.path.splitext(fn)[1])
                )
        except KeyError:
            self.__setClientType("Python3")  # assume it is a Python3 file
        self.startClient(
            False,
            forProject=forProject,
            runInConsole=runInConsole,
            venvName=venvName,
            configOverride=configOverride,
            startViaServer=FileSystemUtilities.isRemoteFileName(fn),
        )

        self.remoteEnvironment(env)

        self.debuggerInterface.remoteCoverage(fn, argv, wd, erase)
        self.debugging = False
        self.running = True

    def remoteProfile(
        self,
        venvName,
        fn,
        argv,
        wd,
        env,
        autoClearShell=True,
        erase=False,
        forProject=False,
        runInConsole=False,
        clientType="",
        configOverride=None,
    ):
        """
        Public method to load a new program to collect profiling data.

        @param venvName name of the virtual environment to be used
        @type str
        @param fn filename to debug
        @type str
        @param argv list of command line arguments to pass to the program
        @type list of str
        @param wd working directory for the program
        @type str
        @param env environment parameter settings
        @type str or dict
        @param autoClearShell flag indicating, that the interpreter window
            should be cleared
        @type bool
        @param erase flag indicating that coverage info should be
            cleared first
        @type bool
        @param forProject flag indicating a project related action
        @type bool
        @param runInConsole flag indicating to start the debugger in a
            console window
        @type bool
        @param clientType client type to be used
        @type str
        @param configOverride dictionary containing the global config override
            data
        @type dict
        """
        self.__autoClearShell = autoClearShell

        if clientType not in self.getSupportedLanguages():
            # a not supported client language was requested
            EricMessageBox.critical(
                None,
                self.tr("Start Debugger"),
                self.tr(
                    """<p>The debugger type <b>{0}</b> is not supported"""
                    """ or not configured.</p>"""
                ).format(clientType),
            )
            return

        # Restart the client
        try:
            if clientType:
                self.__setClientType(clientType)
            else:
                self.__setClientType(
                    self.__findLanguageForExtension(os.path.splitext(fn)[1])
                )
        except KeyError:
            self.__setClientType("Python3")  # assume it is a Python3 file
        self.startClient(
            False,
            forProject=forProject,
            runInConsole=runInConsole,
            venvName=venvName,
            configOverride=configOverride,
            startViaServer=FileSystemUtilities.isRemoteFileName(fn),
        )

        self.remoteEnvironment(env)

        self.debuggerInterface.remoteProfile(fn, argv, wd, erase)
        self.debugging = False
        self.running = True

    def remoteStatement(self, debuggerId, stmt):
        """
        Public method to execute a Python statement.

        @param debuggerId ID of the debugger backend
        @type str
        @param stmt Python statement to execute.
        @type str
        """
        self.debuggerInterface.remoteStatement(debuggerId, stmt.rstrip())

    def remoteStep(self, debuggerId):
        """
        Public method to single step the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.debuggerInterface.remoteStep(debuggerId)

    def remoteStepOver(self, debuggerId):
        """
        Public method to step over the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.debuggerInterface.remoteStepOver(debuggerId)

    def remoteStepOut(self, debuggerId):
        """
        Public method to step out the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.debuggerInterface.remoteStepOut(debuggerId)

    def remoteStepQuit(self, debuggerId):
        """
        Public method to stop the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.debuggerInterface.remoteStepQuit(debuggerId)

    def remoteContinue(self, debuggerId, special=False):
        """
        Public method to continue the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        @param special flag indicating a special continue operation
        @type bool
        """
        self.debuggerInterface.remoteContinue(debuggerId, special)

    def remoteContinueUntil(self, debuggerId, line):
        """
        Public method to continue the debugged program to the given line
        or until returning from the current frame.

        @param debuggerId ID of the debugger backend
        @type str
        @param line new line, where execution should be continued to
        @type int
        """
        self.debuggerInterface.remoteContinueUntil(debuggerId, line)

    def remoteMoveIP(self, debuggerId, line):
        """
        Public method to move the instruction pointer to a different line.

        @param debuggerId ID of the debugger backend
        @type str
        @param line new line, where execution should be continued
        @type int
        """
        self.debuggerInterface.remoteMoveIP(debuggerId, line)

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
        self.debuggerInterface.remoteBreakpoint(
            debuggerId, fn, line, setBreakpoint, cond, temp
        )

    def __remoteBreakpointEnable(self, debuggerId, fn, line, enable):
        """
        Private method to enable or disable a breakpoint.

        @param debuggerId ID of the debugger backend
        @type str
        @param fn filename the breakpoint belongs to
        @type str
        @param line line number of the breakpoint
        @type int
        @param enable flag indicating enabling or disabling a breakpoint
        @type bool
        """
        self.debuggerInterface.remoteBreakpointEnable(debuggerId, fn, line, enable)

    def __remoteBreakpointIgnore(self, debuggerId, fn, line, count):
        """
        Private method to ignore a breakpoint the next couple of occurrences.

        @param debuggerId ID of the debugger backend
        @type str
        @param fn filename the breakpoint belongs to
        @type str
        @param line line number of the breakpoint
        @type int
        @param count number of occurrences to ignore
        @type int
        """
        self.debuggerInterface.remoteBreakpointIgnore(debuggerId, fn, line, count)

    def __remoteWatchpoint(self, debuggerId, cond, setWatch, temp=False):
        """
        Private method to set or clear a watch expression.

        @param debuggerId ID of the debugger backend
        @type str
        @param cond expression of the watch expression
        @type str
        @param setWatch flag indicating setting or resetting a watch expression
        @type bool
        @param temp flag indicating a temporary watch expression
        @type bool
        """
        # cond is combination of cond and special (s. watch expression viewer)
        self.debuggerInterface.remoteWatchpoint(debuggerId, cond, setWatch, temp)

    def __remoteWatchpointEnable(self, debuggerId, cond, enable):
        """
        Private method to enable or disable a watch expression.

        @param debuggerId ID of the debugger backend
        @type str
        @param cond expression of the watch expression
        @type str
        @param enable flag indicating enabling or disabling a watch expression
        @type bool
        """
        # cond is combination of cond and special (s. watch expression viewer)
        self.debuggerInterface.remoteWatchpointEnable(debuggerId, cond, enable)

    def __remoteWatchpointIgnore(self, debuggerId, cond, count):
        """
        Private method to ignore a watch expression the next couple of
        occurrences.

        @param debuggerId ID of the debugger backend
        @type str
        @param cond expression of the watch expression
        @type str
        @param count number of occurrences to ignore
        @type int
        """
        # cond is combination of cond and special (s. watch expression viewer)
        self.debuggerInterface.remoteWatchpointIgnore(debuggerId, cond, count)

    def remoteRawInput(self, debuggerId, inputString):
        """
        Public method to send the raw input to the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        @param inputString raw input
        @type str
        """
        self.debuggerInterface.remoteRawInput(debuggerId, inputString)
        self.clientRawInputSent.emit(debuggerId)

    def remoteThreadList(self, debuggerId):
        """
        Public method to request the list of threads from the client.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.debuggerInterface.remoteThreadList(debuggerId)

    def remoteSetThread(self, debuggerId, tid):
        """
        Public method to request to set the given thread as current thread.

        @param debuggerId ID of the debugger backend
        @type str
        @param tid id of the thread
        @type int
        """
        self.debuggerInterface.remoteSetThread(debuggerId, tid)

    def remoteClientStack(self, debuggerId):
        """
        Public method to request the stack of the main thread.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.debuggerInterface.remoteClientStack(debuggerId)

    def remoteClientVariables(self, debuggerId, scope, filterList, framenr=0):
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
        """
        self.debuggerInterface.remoteClientVariables(
            debuggerId, scope, filterList, framenr, self.__maxVariableSize
        )

    def remoteClientVariable(
        self, debuggerId, scope, filterList, var, framenr=0, maxSize=0  # noqa: U100
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
            be given (@@TOO_BIG_TO_SHOW@@). (unused)
        @type int
        """
        self.debuggerInterface.remoteClientVariable(
            debuggerId, scope, filterList, var, framenr, self.__maxVariableSize
        )

    def remoteClientDisassembly(self, debuggerId):
        """
        Public method to ask the client for the latest traceback disassembly.

        @param debuggerId ID of the debugger backend
        @type str
        """
        with contextlib.suppress(AttributeError):
            self.debuggerInterface.remoteClientDisassembly(debuggerId)

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
        self.debuggerInterface.remoteClientSetFilter(debuggerId, scope, filterStr)

    def setCallTraceEnabled(self, debuggerId, on):
        """
        Public method to set the call trace state.

        @param debuggerId ID of the debugger backend
        @type str
        @param on flag indicating to enable the call trace function
        @type bool
        """
        self.debuggerInterface.setCallTraceEnabled(debuggerId, on)

    def remoteBanner(self):
        """
        Public slot to get the banner info of the remote client.
        """
        self.debuggerInterface.remoteBanner()

    def remoteCapabilities(self):
        """
        Public slot to get the debug clients capabilities.
        """
        self.debuggerInterface.remoteCapabilities()

    def remoteCompletion(self, debuggerId, text):
        """
        Public slot to get the a list of possible commandline completions
        from the remote client.

        @param debuggerId ID of the debugger backend
        @type str
        @param text text to be completed
        @type str
        """
        self.debuggerInterface.remoteCompletion(debuggerId, text)

    def signalClientOutput(self, line, debuggerId):
        """
        Public method to process a line of client output.

        @param line client output
        @type str
        @param debuggerId ID of the debugger backend
        @type str
        """
        if debuggerId:
            self.clientOutput.emit("{0}: {1}".format(debuggerId, line))
        else:
            self.clientOutput.emit(line)

    def signalClientLine(
        self, filename, lineno, debuggerId, forStack=False, threadName=""
    ):
        """
        Public method to process client position feedback.

        @param filename name of the file currently being executed
        @type str
        @param lineno line of code currently being executed
        @type int
        @param debuggerId ID of the debugger backend
        @type str
        @param forStack flag indicating this is for a stack dump
        @type bool
        @param threadName name of the thread signaling the event
        @type str
        """
        self.clientLine.emit(filename, lineno, debuggerId, threadName, forStack)

    def signalClientStack(self, stack, debuggerId, threadName=""):
        """
        Public method to process a client's stack information.

        @param stack list of stack entries. Each entry is a tuple of three
            values giving the filename, linenumber and method
        @type list of lists of (string, integer, string)
        @param debuggerId ID of the debugger backend
        @type str
        @param threadName name of the thread signaling the event
        @type str
        """
        self.clientStack.emit(stack, debuggerId, threadName)

    def signalClientThreadList(self, currentId, threadList, debuggerId):
        """
        Public method to process the client thread list info.

        @param currentId id of the current thread
        @type int
        @param threadList list of dictionaries containing the thread data
        @type list of dict
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientThreadList.emit(currentId, threadList, debuggerId)

    def signalClientThreadSet(self, debuggerId):
        """
        Public method to handle the change of the client thread.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientThreadSet.emit(debuggerId)

    def signalClientVariables(self, scope, variables, debuggerId):
        """
        Public method to process the client variables info.

        @param scope scope of the variables
            (-2 = no frame found, -1 = empty locals, 1 = global, 0 = local)
        @type int
        @param variables the list of variables from the client
        @type list
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientVariables.emit(scope, variables, debuggerId)

    def signalClientVariable(self, scope, variables, debuggerId):
        """
        Public method to process the client variable info.

        @param scope scope of the variables (-1 = empty global, 1 = global,
            0 = local)
        @type int
        @param variables the list of members of a classvariable from the client
        @type list
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientVariable.emit(scope, variables, debuggerId)

    def signalClientStatement(self, more, debuggerId):
        """
        Public method to process the input response from the client.

        @param more flag indicating that more user input is required
        @type bool
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientStatement.emit(more, debuggerId)

    def signalClientDisassembly(self, disassembly, debuggerId):
        """
        Public method to process the disassembly info from the client.

        @param disassembly dictionary containing the disassembly information
        @type dict
        @param debuggerId ID of the debugger backend
        @type str
        """
        if self.running:
            self.clientDisassembly.emit(disassembly, debuggerId)

    def signalClientException(
        self, exceptionType, exceptionMessage, stackTrace, debuggerId, threadName=""
    ):
        """
        Public method to process the exception info from the client.

        @param exceptionType type of exception raised
        @type str
        @param exceptionMessage message given by the exception
        @type str
        @param stackTrace list of stack entries with the exception position
            first. Each stack entry is a list giving the filename and the
            linenumber.
        @type list
        @param debuggerId ID of the debugger backend
        @type str
        @param threadName name of the thread signaling the event
        @type str
        """
        if self.running:
            self.clientException.emit(
                exceptionType, exceptionMessage, stackTrace, debuggerId, threadName
            )

    def signalClientSyntaxError(
        self, message, filename, lineNo, characterNo, debuggerId, threadName=""
    ):
        """
        Public method to process a syntax error info from the client.

        @param message message of the syntax error
        @type str
        @param filename translated filename of the syntax error position
        @type str
        @param lineNo line number of the syntax error position
        @type int
        @param characterNo character number of the syntax error position
        @type int
        @param debuggerId ID of the debugger backend
        @type str
        @param threadName name of the thread signaling the event
        @type str
        """
        if self.running:
            self.clientSyntaxError.emit(
                message, filename, lineNo, characterNo, debuggerId, threadName
            )

    def signalClientSignal(
        self, message, filename, lineNo, funcName, funcArgs, debuggerId
    ):
        """
        Public method to process a signal generated on the client side.

        @param message message of the syntax error
        @type str
        @param filename translated filename of the syntax error position
        @type str
        @param lineNo line number of the syntax error position
        @type int
        @param funcName name of the function causing the signal
        @type str
        @param funcArgs function arguments
        @type str
        @param debuggerId ID of the debugger backend
        @type str
        """
        if self.running:
            self.clientSignal.emit(
                message, filename, lineNo, funcName, funcArgs, debuggerId
            )

    def signalClientDisconnected(self, debuggerId):
        """
        Public method to send a signal when a debug client has closed its
        connection.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientDisconnected.emit(debuggerId)

    def signalClientExit(self, program, status, message, debuggerId):
        """
        Public method to process the client exit status.

        @param program name of the exited program
        @type str
        @param status exit code
        @type int
        @param message message sent with the exit
        @type str
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientExit.emit(program, int(status), message, False, debuggerId)

    def signalMainClientExit(self):
        """
        Public method to process the main client exiting.
        """
        self.mainClientExit.emit()

    def signalLastClientExited(self):
        """
        Public method to process the last client exit event.
        """
        if self.passive:
            self.__passiveShutDown()
        self.lastClientExited.emit()
        if Preferences.getDebugger("AutomaticReset") or (
            self.running and not self.debugging
        ):
            self.debugging = False
            self.startClient(False, forProject=self.__forProject)
        if self.passive:
            self.__createDebuggerInterface("None")
            self.signalClientOutput(self.tr("\nNot connected\n"), "")
            self.signalClientStatement(False, "")
        self.running = False
        self.__ericServerDebugging = False

    def signalClientClearBreak(self, filename, lineno, debuggerId):
        """
        Public method to process the client clear breakpoint command.

        @param filename filename of the breakpoint
        @type str
        @param lineno line umber of the breakpoint
        @type int
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientClearBreak.emit(filename, lineno, debuggerId)

    def signalClientBreakConditionError(self, filename, lineno, debuggerId):
        """
        Public method to process the client breakpoint condition error info.

        @param filename filename of the breakpoint
        @type str
        @param lineno line umber of the breakpoint
        @type int
        @param debuggerId ID of the debugger backend
        @type str
        """
        if (filename, lineno) not in self.__reportedBreakpointIssues:
            self.__reportedBreakpointIssues.append((filename, lineno))
            self.clientBreakConditionError.emit(filename, lineno, debuggerId)

    def signalClientClearWatch(self, condition, debuggerId):
        """
        Public slot to handle the clientClearWatch signal.

        @param condition expression of watch expression to clear
        @type str
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientClearWatch.emit(condition, debuggerId)

    def signalClientWatchConditionError(self, condition, debuggerId):
        """
        Public method to process the client watch expression error info.

        @param condition expression of watch expression to clear
        @type str
        @param debuggerId ID of the debugger backend
        @type str
        """
        if condition not in self.__reportedWatchpointIssues:
            self.__reportedWatchpointIssues.append(condition)
            self.clientWatchConditionError.emit(condition, debuggerId)

    def signalClientRawInput(self, prompt, echo, debuggerId):
        """
        Public method to process the client raw input command.

        @param prompt the input prompt
        @type str
        @param echo flag indicating an echoing of the input
        @type bool
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.clientRawInput.emit(prompt, echo, debuggerId)

    def signalClientBanner(self, version, platform, venvName):
        """
        Public method to process the client banner info.

        @param version interpreter version info
        @type str
        @param platform hostname of the client
        @type str
        @param venvName name of the virtual environment
        @type str
        """
        self.clientBanner.emit(version, platform, venvName)

    def signalClientCapabilities(self, capabilities, clientType, venvName):
        """
        Public method to process the client capabilities info.

        @param capabilities bitmaks with the client capabilities
        @type int
        @param clientType type of the debug client
        @type str
        @param venvName name of the virtual environment
        @type str
        """
        with contextlib.suppress(KeyError):
            self.__debuggerInterfaceRegistry[clientType][0] = capabilities
            self.clientCapabilities.emit(capabilities, clientType, venvName)

    def signalClientCompletionList(self, completionList, text, _debuggerId):
        """
        Public method to process the client auto completion info.

        @param completionList list of possible completions
        @type list of str
        @param text the text to be completed
        @type str
        @param _debuggerId ID of the debugger backend (unused)
        @type str
        """
        self.clientCompletionList.emit(completionList, text)

    def signalClientCallTrace(
        self,
        isCall,
        fromFile,
        fromLine,
        fromFunction,
        toFile,
        toLine,
        toFunction,
        debuggerId,
    ):
        """
        Public method to process the client call trace data.

        @param isCall flag indicating a 'call'
        @type bool
        @param fromFile name of the originating file
        @type str
        @param fromLine line number in the originating file
        @type str
        @param fromFunction name of the originating function
        @type str
        @param toFile name of the target file
        @type str
        @param toLine line number in the target file
        @type str
        @param toFunction name of the target function
        @type str
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.callTraceInfo.emit(
            isCall,
            fromFile,
            fromLine,
            fromFunction,
            toFile,
            toLine,
            toFunction,
            debuggerId,
        )

    def passiveStartUp(self, fn, reportAllExceptions, debuggerId):
        """
        Public method to handle a passive debug connection.

        @param fn filename of the debugged script
        @type str
        @param reportAllExceptions flag to enable reporting of all exceptions
        @type bool
        @param debuggerId ID of the debugger backend
        @type str
        """
        if self.passive:
            self.appendStdout.emit(self.tr("Passive debug connection received\n"))
            self.passiveClientExited = False
            self.debugging = True
            self.running = True
            self.__restoreBreakpoints(debuggerId)
            self.__restoreWatchpoints(debuggerId)
            self.passiveDebugStarted.emit(fn, reportAllExceptions)
        else:
            self.appendStdout.emit(
                self.tr(
                    "Passive debug connection received while not in passive mode.\n"
                )
            )
            EricMessageBox.critical(
                None,
                self.tr("Debug Client Connection"),
                self.tr(
                    "Passive debug client connection received while not in passive"
                    " mode. Enable this mode on the 'Debugger General' configuration"
                    " page. The connection will be rejected."
                ),
            )
            self.shutdownServer()
            self.startClient(False, forProject=self.__forProject)

    def __passiveShutDown(self):
        """
        Private method to shut down a passive debug connection.
        """
        self.passiveClientExited = True
        self.shutdownServer()
        self.appendStdout.emit(self.tr("Passive debug connection closed\n"))

    def __restoreBreakpoints(self, debuggerId=""):
        """
        Private method to restore the breakpoints after a restart.

        @param debuggerId ID of the debugger backend to send to. If this is
            empty, they will be broadcast to all connected backends.
        @type str
        """
        if self.debugging:
            self.__addBreakPoints(
                QModelIndex(), 0, self.breakpointModel.rowCount() - 1, debuggerId
            )

    def __restoreWatchpoints(self, debuggerId=""):
        """
        Private method to restore the watch expressions after a restart.

        @param debuggerId ID of the debugger backend to send to. If this is
            empty, they will be broadcast to all connected backends.
        @type str
        """
        if self.debugging:
            self.__addWatchPoints(
                QModelIndex(), 0, self.watchpointModel.rowCount() - 1, debuggerId
            )

    def getBreakPointModel(self):
        """
        Public slot to get a reference to the breakpoint model object.

        @return reference to the breakpoint model object
        @rtype BreakPointModel
        """
        return self.breakpointModel

    def getWatchPointModel(self):
        """
        Public slot to get a reference to the watch expression model object.

        @return reference to the watch expression model object
        @rtype WatchPointModel
        """
        return self.watchpointModel

    def isConnected(self):
        """
        Public method to test, if the debug server is connected to a backend.

        @return flag indicating a connection
        @rtype bool
        """
        return self.debuggerInterface and self.debuggerInterface.isConnected()

    def isDebugging(self):
        """
        Public method to test, if the debug server is debugging.

        @return flag indicating the debugging state
        @rtype bool
        """
        return self.debugging

    def setDebugging(self, on):
        """
        Public method to set the debugging state.

        @param on flag indicating the new debugging state
        @type bool
        """
        self.debugging = on

    def signalClientDebuggerId(self, debuggerId):
        """
        Public method to signal the receipt of a new debugger ID.

        This signal indicates, that a new debugger backend has connected.

        @param debuggerId ID of the newly connected debugger backend
        @type str
        """
        self.clientDebuggerId.emit(debuggerId)

    def getDebuggerIds(self):
        """
        Public method to return the IDs of the connected debugger backends.

        @return list of connected debugger backend IDs
        @rtype list of str
        """
        if self.debuggerInterface:
            return self.debuggerInterface.getDebuggerIds()
        else:
            return []

    def initializeClient(self, debuggerId):
        """
        Public method to initialize a freshly connected debug client.

        @param debuggerId ID of the connected debugger
        @type str
        """
        self.__restoreBreakpoints(debuggerId)
        self.__restoreWatchpoints(debuggerId)
        self.__restoreNoDebugList(debuggerId)

    def __restoreNoDebugList(self, debuggerId=""):
        """
        Private method to restore the list of scripts not to be debugged after
        a restart.

        @param debuggerId ID of the debugger backend to send to. If this is
            empty, they will be broadcast to all connected backends.
        @type str
        """
        if self.debugging:
            self.debuggerInterface.remoteNoDebugList(
                debuggerId, self.__multiprocessNoDebugList
            )

    def getProjectEnvironmentString(self):
        """
        Public method to get the string for the project environment.

        @return string for the project environment
        @rtype str
        """
        try:
            project = ericApp().getObject("Project")
            if project.isOpen() and project.getProjectVenv(resolveDebugger=False):
                return self.tr("<project>")
            else:
                return ""
        except KeyError:
            # The project object is not present
            return ""

    def getEricServerEnvironmentString(self):
        """
        Public method to get the string for an eric-ide server environment.

        @return string for the eric-ide server environment
        @rtype str
        """
        return "eric-ide Server"
