# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dummy debugger interface for the debug server.
"""

from PyQt6.QtCore import QObject

ClientDefaultCapabilities = 0

ClientTypeAssociations = []


class DebuggerInterfaceNone(QObject):
    """
    Class implementing a dummy debugger interface for the debug server.
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

        self.debugServer = debugServer
        self.passive = passive

        self.qsock = None
        self.__commandQueue = []
        # set default values for capabilities of clients
        self.clientCapabilities = ClientDefaultCapabilities

    def startRemote(
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
        return None, True, ""

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
        return None, True, ""

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
        return False

    def getDebuggerIds(self):
        """
        Public method to return the IDs of the connected debugger backends.

        @return list of connected debugger backend IDs
        @rtype list of str
        """
        return []

    def shutdown(self):
        """
        Public method to cleanly shut down.

        It closes our socket and shuts down the debug client.
        (Needed on Win OS)
        """
        self.qsock = None
        self.__commandQueue.clear()

    def isConnected(self):
        """
        Public method to test, if a debug client has connected.

        @return flag indicating the connection status
        @rtype bool
        """
        return self.qsock is not None

    def remoteEnvironment(self, env):
        """
        Public method to set the environment for a program to debug, run, ...

        @param env environment settings
        @type dict
        """
        return

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
        return

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
        return

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
        return

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
        return

    def remoteStatement(self, debuggerId, stmt):
        """
        Public method to execute a Python statement.

        @param debuggerId ID of the debugger backend
        @type str
        @param stmt Python statement to execute.
        @type str
        """
        self.debugServer.signalClientStatement(False, "")
        return

    def remoteStep(self, debuggerId):
        """
        Public method to single step the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        return

    def remoteStepOver(self, debuggerId):
        """
        Public method to step over the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        return

    def remoteStepOut(self, debuggerId):
        """
        Public method to step out the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        return

    def remoteStepQuit(self, debuggerId):
        """
        Public method to stop the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        """
        return

    def remoteContinue(self, debuggerId, special=False):
        """
        Public method to continue the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        @param special flag indicating a special continue operation
        @type bool
        """
        return

    def remoteContinueUntil(self, debuggerId, line):
        """
        Public method to continue the debugged program to the given line
        or until returning from the current frame.

        @param debuggerId ID of the debugger backend
        @type str
        @param line new line, where execution should be continued to
        @type int
        """
        return

    def remoteMoveIP(self, debuggerId, line):
        """
        Public method to move the instruction pointer to a different line.

        @param debuggerId ID of the debugger backend
        @type str
        @param line new line, where execution should be continued
        @type int
        """
        return

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
        return

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
        return

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
        return

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
        return

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
        return

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
        return

    def remoteRawInput(self, debuggerId, inputString):
        """
        Public method to send the raw input to the debugged program.

        @param debuggerId ID of the debugger backend
        @type str
        @param inputString raw input
        @type str
        """
        return

    def remoteThreadList(self, debuggerId):
        """
        Public method to request the list of threads from the client.

        @param debuggerId ID of the debugger backend
        @type str
        """
        return

    def remoteSetThread(self, debuggerId, tid):
        """
        Public method to request to set the given thread as current thread.

        @param debuggerId ID of the debugger backend
        @type str
        @param tid id of the thread
        @type int
        """
        return

    def remoteClientStack(self, debuggerId):
        """
        Public method to request the stack of the main thread.

        @param debuggerId ID of the debugger backend
        @type str
        """
        return

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
        return

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
        return

    def remoteClientDisassembly(self, debuggerId):
        """
        Public method to ask the client for the latest traceback disassembly.

        @param debuggerId ID of the debugger backend
        @type str
        """
        return

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
        return

    def setCallTraceEnabled(self, debuggerId, on):
        """
        Public method to set the call trace state.

        @param debuggerId ID of the debugger backend
        @type str
        @param on flag indicating to enable the call trace function
        @type bool
        """
        return

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
        return

    def remoteBanner(self):
        """
        Public slot to get the banner info of the remote client.
        """
        return

    def remoteCapabilities(self, debuggerId):
        """
        Public slot to get the debug clients capabilities.

        @param debuggerId ID of the debugger backend
        @type str
        """
        return

    def remoteCompletion(self, debuggerId, text):
        """
        Public slot to get the a list of possible commandline completions
        from the remote client.

        @param debuggerId ID of the debugger backend
        @type str
        @param text text to be completed
        @type str
        """
        return

    def setAutoContinue(self, autoContinue):
        """
        Public method to set the automatic continue flag of the interface.

        If this is set to True, the debugger will tell the debug client to continue
        when it stops at the first line of the script to be debugged.

        @param autoContinue flag indicating the auto continue state
        @type bool
        """
        return


def createDebuggerInterfaceNone(debugServer, passive):
    """
    Module function to create a debugger interface instance.


    @param debugServer reference to the debug server
    @type DebugServer
    @param passive flag indicating passive connection mode
    @type bool
    @return instantiated debugger interface
    @rtype DebuggerInterfaceNone
    """
    return DebuggerInterfaceNone(debugServer, passive)


def getRegistryData():
    """
    Module function to get characterizing data for the debugger interface.

    @return list of tuples containing the client type, the client capabilities,
        the client file type associations and a reference to the creation
        function
    @rtype list of tuple of (str, int, list of str, function)
    """
    return [
        (
            "None",
            ClientDefaultCapabilities,
            ClientTypeAssociations,
            createDebuggerInterfaceNone,
        )
    ]


#
# eflag: noqa = U100
