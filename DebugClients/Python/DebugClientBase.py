# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a debug client base class.
"""

import atexit
import codecs
import codeop
import contextlib
import fnmatch
import importlib.util
import json
import os
import re
import runpy
import select
import signal
import socket
import sys
import sysconfig
import traceback
import types

# modify sys.path to get access to the 'coverage' package
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# site-packages is three levels up

import DebugClientCapabilities
import DebugVariables

from AsyncFile import AsyncFile, AsyncPendingWrite
from BreakpointWatch import Breakpoint, Watch
from DebugBase import printerr, setRecursionLimit
from DebugConfig import NonExpandableTypes, SpecialAttributes
from DebugUtilities import formatargvalues, getargvalues, prepareJsonCommand
from FlexCompleter import Completer
from MultiProcessDebugExtension import patchNewProcessFunctions

DebugClientInstance = None

###############################################################################


def DebugClientInput(prompt="", echo=True):
    """
    Replacement for the standard input() builtin.

    This function works with the split debugger.

    @param prompt prompt to be shown
    @type str
    @param echo flag indicating echoing of the input
    @type bool
    @return result of the input() call
    @rtype str
    """
    if DebugClientInstance is None or not DebugClientInstance.redirect:
        return DebugClientOrigInput(prompt)
    else:
        return DebugClientInstance.input(prompt, echo=echo)


# Use our own input().
try:
    DebugClientOrigInput = __builtins__.__dict__["input"]
    __builtins__.__dict__["input"] = DebugClientInput
except (AttributeError, KeyError):
    import __main__

    DebugClientOrigInput = __main__.__builtins__.__dict__["input"]
    __main__.__builtins__.__dict__["input"] = DebugClientInput

###############################################################################


def DebugClientClose(fd):
    """
    Replacement for the standard os.close(fd).

    @param fd open file descriptor to be closed
    @type int
    """
    if DebugClientInstance is None:
        DebugClientOrigClose(fd)
    else:
        DebugClientInstance.close(fd)


# use our own close().
if "close" in dir(os):
    DebugClientOrigClose = os.close
    os.close = DebugClientClose

###############################################################################


def DebugClientSetRecursionLimit(limit):
    """
    Replacement for the standard sys.setrecursionlimit(limit).

    @param limit recursion limit
    @type int
    """
    rl = max(limit, 64)
    setRecursionLimit(rl)
    DebugClientOrigSetRecursionLimit(rl + 64)


# use our own setrecursionlimit().
if "setrecursionlimit" in dir(sys):
    DebugClientOrigSetRecursionLimit = sys.setrecursionlimit
    sys.setrecursionlimit = DebugClientSetRecursionLimit
    DebugClientSetRecursionLimit(sys.getrecursionlimit())

###############################################################################


class DebugClientBase:
    """
    Class implementing the client side of the debugger.

    It provides access to the Python interpeter from a debugger running in
    another process.

    The protocol between the debugger and the client is based on JSONRPC 2.0
    PDUs. Each one is sent on a single line, i.e. commands or responses are
    separated by a linefeed character.

    If the debugger closes the session there is no response from the client.
    The client may close the session at any time as a result of the script
    being debugged closing or crashing.

    <b>Note</b>: This class is meant to be subclassed by individual
    DebugClient classes. Do not instantiate it directly.
    """

    clientCapabilities = DebugClientCapabilities.HasAll

    Type2Indicators = {
        # Python types
        "list": "[]",
        "tuple": "()",
        "dict": "{:}",  # __IGNORE_WARNING_M613__
        "set": "{}",  # __IGNORE_WARNING_M613__
        "frozenset": "{}",  # __IGNORE_WARNING_M613__
        "numpy.ndarray": "[ndarray]",  # __IGNORE_WARNING_M613__
        "collections.abc.ItemsView": "[]",
        "collections.abc.KeysView": "[]",
        "collections.abc.ValuesView": "[]",
    }

    def __init__(self):
        """
        Constructor
        """
        self.breakpoints = {}
        self.redirect = True

        # special objects representing the main scripts thread and frame
        self.mainThread = self
        self.framenr = 0

        # The context to run the debugged program in.
        self.debugMod = types.ModuleType("__main__")
        self.debugMod.__dict__["__builtins__"] = __builtins__

        # The list of complete lines to execute.
        self.buffer = ""

        # The precompiled regexp to filter variables against
        self.globalsFilterObjects = (None, False)  # filter regexp, show flag
        self.localsFilterObjects = (None, False)  # filter regexp, show flag

        self._fncache = {}
        self.dircache = []
        self.passive = False  # used to indicate the passive mode
        self.running = None
        self.test = None
        self.debugging = False
        self.multiprocessSupport = False
        self.reportAllExceptions = False
        self.noDebugList = []

        self.readstream = None
        self.writestream = None
        self.errorstream = None
        self.pollingDisabled = False

        self.__debuggerId = ""

        self.callTraceEnabled = None

        self.compile_command = codeop.CommandCompiler()

        self.coding_re = re.compile(r"coding[:=]\s*([-\w_.]+)")
        self.defaultCoding = "utf-8"
        self.__coding = self.defaultCoding
        self.noencoding = False

        self.startOptions = None

        self.callTraceOptimization = False

        self.__debugeeExceptHook = None

    def getCoding(self):
        """
        Public method to return the current coding.

        @return codec name
        @rtype str
        """
        return self.__coding

    def __setCoding(self, filename):
        """
        Private method to set the coding used by a python file.

        @param filename name of the file to inspect
        @type str
        """
        if self.noencoding:
            self.__coding = sys.getdefaultencoding()
        else:
            default = "utf-8"
            try:
                with open(filename, "rb") as f:
                    # read the first and second line
                    text = f.readline()
                    text = "{0}{1}".format(text, f.readline())
            except OSError:
                self.__coding = default
                return

            for line in text.splitlines():
                m = self.coding_re.search(line)
                if m:
                    self.__coding = m.group(1)
                    return
            self.__coding = default

    def input(self, prompt, echo=True):
        """
        Public method to implement input() using the event loop.

        @param prompt prompt to be shown
        @type str
        @param echo flag indicating echoing of the input
        @type bool
        @return the entered string
        @rtype str
        """
        self.sendJsonCommand(
            "RequestRaw",
            {
                "prompt": prompt,
                "echo": echo,
            },
        )
        self.eventLoop(True)
        return self.rawLine

    def sessionClose(self, terminate=True):
        """
        Public method to close the session with the debugger and optionally
        terminate.

        @param terminate flag indicating to terminate
        @type bool
        """
        with contextlib.suppress(Exception):  # secok
            self.set_quit()

        self.debugging = False
        self.multiprocessSupport = False
        self.reportAllExceptions = False
        self.noDebugList = []

        # make sure we close down our end of the socket
        # might be overkill as normally stdin, stdout and stderr
        # SHOULD be closed on exit, but it does not hurt to do it here
        self.readstream.close(True)
        self.writestream.close(True)
        self.errorstream.close(True)

        if terminate:
            # Ok, go away.
            sys.exit()

    def __compileFileSource(self, filename, mode="exec"):
        """
        Private method to compile source code read from a file.

        @param filename name of the source file
        @type str
        @param mode kind of code to be generated (exec or eval)
        @type str
        @return compiled code object (None in case of errors)
        @rtype Code
        """
        with codecs.open(filename, encoding=self.__coding) as fp:
            statement = fp.read()

        return self.__compileCommand(statement, filename=filename, mode=mode)

    def __compileCommand(self, statement, filename="<string>", mode="exec"):
        """
        Private method to compile source code.

        @param statement source code string to be compiled
        @type str
        @param filename name of the source file
        @type str
        @param mode kind of code to be generated (exec or eval)
        @type str
        @return compiled code object (None in case of errors)
        @rtype Code
        """
        try:
            code = compile(statement + "\n", filename, mode)
        except SyntaxError:
            exctype, excval, exctb = sys.exc_info()
            try:
                message = str(excval)
                filename = excval.filename
                lineno = excval.lineno
                charno = excval.offset
                if charno is None:
                    charno = 0

            except (AttributeError, ValueError):
                message = ""
                filename = ""
                lineno = 0
                charno = 0

            self.sendSyntaxError(message, filename, lineno, charno, self.name)
            return None

        return code

    def handleJsonCommand(self, jsonStr):
        """
        Public method to handle a command serialized as a JSON string.

        @param jsonStr string containing the command received from the IDE
        @type str
        """
        ##        printerr(jsonStr)          ## debug       # noqa: M891

        try:
            commandDict = json.loads(jsonStr.strip())
        except (TypeError, ValueError) as err:
            printerr("Error handling command: " + jsonStr)
            printerr(str(err))
            return

        method = commandDict["method"]
        params = commandDict["params"]

        if method == "RequestVariables":
            self.__dumpVariables(
                params["frameNumber"], params["scope"], params["filters"]
            )

        elif method == "RequestVariable":
            self.__dumpVariable(
                params["variable"],
                params["frameNumber"],
                params["scope"],
                params["filters"],
            )

        elif method == "RequestStack":
            stack = self.mainThread.getStack()
            self.sendResponseLine(stack, self.mainThread.name)

        elif method == "RequestThreadList":
            self.dumpThreadList()

        elif method == "RequestThreadSet":
            if params["threadID"] == -1:
                # -1 is indication for the main thread
                threadId = -1
                for thread in self.threads.values():
                    if thread.name == "MainThread":
                        threadId = thread.id
            else:
                threadId = params["threadID"]
            if threadId in self.threads:
                self.setCurrentThread(threadId)
                self.sendJsonCommand("ResponseThreadSet", {})
                stack = self.currentThread.getStack()
                self.sendJsonCommand(
                    "ResponseStack",
                    {
                        "stack": stack,
                        "threadName": self.currentThread.name,
                    },
                )

        elif method == "RequestDisassembly":
            if self.disassembly is not None:
                self.sendJsonCommand(
                    "ResponseDisassembly", {"disassembly": self.disassembly}
                )
            else:
                self.sendJsonCommand("ResponseDisassembly", {"disassembly": {}})

        elif method == "RequestCapabilities":
            clientType = "Python3"
            self.sendJsonCommand(
                "ResponseCapabilities",
                {"capabilities": self.__clientCapabilities(), "clientType": clientType},
            )

        elif method == "RequestBanner":
            self.sendJsonCommand(
                "ResponseBanner",
                {
                    "version": "Python {0}".format(sys.version),
                    "platform": socket.gethostname(),
                },
            )

        elif method == "RequestSetFilter":
            self.__generateFilterObjects(params["scope"], params["filter"])

        elif method == "RequestCallTrace":
            if params["enable"]:
                callTraceEnabled = self.profile
            else:
                callTraceEnabled = None

            if self.debugging:
                sys.setprofile(callTraceEnabled)
            else:
                # remember for later
                self.callTraceEnabled = callTraceEnabled

        elif method == "RequestEnvironment":
            for key, value in params["environment"].items():
                if key.endswith("+"):
                    # append to the key
                    key = key[:-1]
                    if key in os.environ:
                        os.environ[key] += value
                    else:
                        os.environ[key] = value
                elif key.endswith("-"):
                    # delete the key if it exists
                    key = key[:-1]
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = value

        elif method == "RequestLoad":
            self._fncache = {}
            self.dircache = []
            self.disassembly = None
            sys.argv = []
            if params["argv"] and params["argv"][0].startswith("--plugin="):
                # we are debugging an eric IDE plug-in
                ide = os.path.join(
                    sysconfig.get_path("platlib"), "eric7", "eric7_ide.py"
                )
                params["filename"] = ide
            self.__setCoding(params["filename"])
            sys.argv.append(params["filename"])
            sys.argv.extend(params["argv"])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params["workdir"] == "":
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])

            self.running = sys.argv[0]
            self.debugging = True
            self.multiprocessSupport = params["multiprocess"]
            self.reportAllExceptions = params["reportAllExceptions"]

            self.threads.clear()
            self.attachThread(mainThread=True)

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()

            # clear all old breakpoints, they'll get set after we have
            # started
            Breakpoint.clear_all_breaks()
            Watch.clear_all_watches()

            self.mainThread.tracePythonLibs(params["traceInterpreter"])

            # This will eventually enter a local event loop.
            self.debugMod.__dict__["__file__"] = self.running
            sys.modules["__main__"] = self.debugMod
            code = self.__compileFileSource(self.running)
            if code:
                sys.setprofile(self.callTraceEnabled)
                self.mainThread.run(
                    code, self.debugMod.__dict__, debug=True, closeSession=False
                )

        elif method == "RequestRun":
            self.disassembly = None
            sys.argv = []
            if params["argv"] and params["argv"][0].startswith("--plugin="):
                # we are executing an eric IDE plug-in
                ide = os.path.join(
                    sysconfig.get_path("platlib"), "eric7", "eric7_ide.py"
                )
                params["filename"] = ide
            self.__setCoding(params["filename"])
            sys.argv.append(params["filename"])
            sys.argv.extend(params["argv"])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params["workdir"] == "":
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])

            self.running = sys.argv[0]
            self.botframe = None

            self.threads.clear()
            self.attachThread(mainThread=True)

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()

            self.mainThread.tracePythonLibs(False)

            self.debugMod.__dict__["__file__"] = sys.argv[0]
            sys.modules["__main__"] = self.debugMod
            res = 0
            code = self.__compileFileSource(self.running)
            if code:
                self.mainThread.run(
                    code, self.debugMod.__dict__, debug=False, closeSession=False
                )

        elif method == "RequestCoverage":
            from coverage import Coverage  # __IGNORE_WARNING_I10__

            self.disassembly = None
            sys.argv = []
            if params["argv"] and params["argv"][0].startswith("--plugin="):
                # we are coverage testing an eric IDE plug-in
                ide = os.path.join(
                    sysconfig.get_path("platlib"), "eric7", "eric7_ide.py"
                )
                params["filename"] = ide
            self.__setCoding(params["filename"])
            sys.argv.append(params["filename"])
            sys.argv.extend(params["argv"])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params["workdir"] == "":
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()

            # generate a coverage object
            self.cover = Coverage(
                auto_data=True,
                data_file="{0}.coverage".format(os.path.splitext(sys.argv[0])[0]),
            )

            if params["erase"]:
                self.cover.erase()
            sys.modules["__main__"] = self.debugMod
            self.debugMod.__dict__["__file__"] = sys.argv[0]
            code = self.__compileFileSource(sys.argv[0])
            if code:
                self.running = sys.argv[0]
                self.cover.start()
                self.mainThread.run(
                    code, self.debugMod.__dict__, debug=False, closeSession=False
                )
                self.cover.stop()
                self.cover.save()

        elif method == "RequestProfile":
            sys.setprofile(None)
            import PyProfile  # __IGNORE_WARNING_I10__

            self.disassembly = None
            sys.argv = []
            if params["argv"] and params["argv"][0].startswith("--plugin="):
                # we are profiling an eric IDE plug-in
                ide = os.path.join(
                    sysconfig.get_path("platlib"), "eric7", "eric7_ide.py"
                )
                params["filename"] = ide
            self.__setCoding(params["filename"])
            sys.argv.append(params["filename"])
            sys.argv.extend(params["argv"])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if params["workdir"] == "":
                os.chdir(sys.path[1])
            else:
                os.chdir(params["workdir"])

            # set the system exception handling function to ensure, that
            # we report on all unhandled exceptions
            sys.excepthook = self.__unhandled_exception
            self.__interceptSignals()

            # generate a profile object
            self.prof = PyProfile.PyProfile(sys.argv[0])

            if params["erase"]:
                self.prof.erase()
            self.debugMod.__dict__["__file__"] = sys.argv[0]
            sys.modules["__main__"] = self.debugMod
            script = ""
            with codecs.open(sys.argv[0], encoding=self.__coding) as fp:
                script = fp.read()
            if script and not script.endswith("\n"):
                script += "\n"

            if script:
                self.running = sys.argv[0]
                res = 0
                try:
                    self.prof.run(script)
                    atexit._run_exitfuncs()
                except SystemExit as exc:
                    res = exc.code
                    atexit._run_exitfuncs()
                except Exception:
                    excinfo = sys.exc_info()
                    self.__unhandled_exception(*excinfo)

                self.prof.save()
                self.progTerminated(res, closeSession=False)

        elif method == "ExecuteStatement":
            if self.buffer:
                self.buffer = self.buffer + "\n" + params["statement"]
            else:
                self.buffer = params["statement"]

            try:
                code = self.compile_command(self.buffer, self.readstream.name)
            except (OverflowError, SyntaxError, ValueError):
                # Report the exception
                sys.last_type, sys.last_value, sys.last_traceback = sys.exc_info()
                self.sendJsonCommand(
                    "ClientOutput",
                    {
                        "text": "".join(
                            traceback.format_exception_only(
                                sys.last_type, sys.last_value
                            )
                        )
                    },
                )
                self.buffer = ""
            else:
                if code is None:
                    self.sendJsonCommand("ResponseContinue", {})
                    return
                else:
                    self.buffer = ""

                    try:
                        if self.running is None:
                            exec(code, self.debugMod.__dict__)  # secok
                        else:
                            if self.currentThread is None:
                                # program has terminated
                                self.running = None
                                _globals = self.debugMod.__dict__
                                _locals = _globals
                            else:
                                cf = self.currentThread.getFrame()
                                # program has terminated
                                if cf is None:
                                    self.running = None
                                    _globals = self.debugMod.__dict__
                                    _locals = _globals
                                else:
                                    cf = self.currentThread.getFrame(self.framenr)
                                    _globals = cf.f_globals
                                    _locals = self.currentThread.getFrameLocals(
                                        self.framenr
                                    )
                            # transfer all locals into a new globals
                            # to emulate Python scoping rules
                            _updatedGlobals = {}
                            _updatedGlobals.update(_globals)
                            _updatedGlobals.update(_locals)
                            # - reset sys.stdout to our redirector
                            # - (unconditionally)
                            if "sys" in _globals:
                                __stdout = _updatedGlobals["sys"].stdout
                                _updatedGlobals["sys"].stdout = self.writestream
                                exec(code, _updatedGlobals, _locals)  # secok
                                _updatedGlobals["sys"].stdout = __stdout
                            elif "sys" in _locals:
                                __stdout = _locals["sys"].stdout
                                _locals["sys"].stdout = self.writestream
                                exec(code, _updatedGlobals, _locals)  # secok
                                _locals["sys"].stdout = __stdout
                            else:
                                exec(code, _updatedGlobals, _locals)  # secok

                            self.currentThread.storeFrameLocals(self.framenr)
                    except SystemExit as exc:
                        self.progTerminated(exc.code)
                    except Exception:
                        # Report the exception and the traceback
                        tlist = []
                        try:
                            exc_type, exc_value, exc_tb = sys.exc_info()
                            sys.last_type = exc_type
                            sys.last_value = exc_value
                            sys.last_traceback = exc_tb
                            tblist = traceback.extract_tb(exc_tb)
                            del tblist[:1]
                            tlist = traceback.format_list(tblist)
                            if tlist:
                                tlist.insert(0, "Traceback (innermost last):\n")
                                tlist.extend(
                                    traceback.format_exception_only(exc_type, exc_value)
                                )
                        finally:
                            tblist = exc_tb = None

                        self.sendJsonCommand("ClientOutput", {"text": "".join(tlist)})

            self.sendJsonCommand("ResponseOK", {})

        elif method == "RequestStep":
            self.currentThreadExec.step(True)
            self.eventExit = True

        elif method == "RequestStepOver":
            self.currentThreadExec.step(False)
            self.eventExit = True

        elif method == "RequestStepOut":
            self.currentThreadExec.stepOut()
            self.eventExit = True

        elif method == "RequestStepQuit":
            if self.passive:
                self.progTerminated(42)
            else:
                self.set_quit()
                self.eventExit = True

        elif method == "RequestMoveIP":
            newLine = params["newLine"]
            self.currentThreadExec.move_instruction_pointer(newLine)

        elif method == "RequestContinue":
            self.currentThreadExec.go(params["special"])
            self.eventExit = True

        elif method == "RequestContinueUntil":
            newLine = params["newLine"]
            self.currentThreadExec.set_until(lineno=newLine)
            self.eventExit = True

        elif method == "RawInput":
            # If we are handling raw mode input then break out of the current
            # event loop.
            self.rawLine = params["input"]
            self.eventExit = True

        elif method == "RequestBreakpoint":
            if params["setBreakpoint"]:
                if params["condition"] in ["None", ""]:
                    cond = None
                elif params["condition"] is not None:
                    try:
                        cond = compile(params["condition"], "<string>", "eval")
                    except SyntaxError:
                        self.sendJsonCommand(
                            "ResponseBPConditionError",
                            {
                                "filename": params["filename"],
                                "line": params["line"],
                            },
                        )
                        return
                else:
                    cond = None

                Breakpoint(
                    params["filename"], params["line"], params["temporary"], cond
                )
            else:
                Breakpoint.clear_break(params["filename"], params["line"])

        elif method == "RequestBreakpointEnable":
            bp = Breakpoint.get_break(params["filename"], params["line"])
            if bp is not None:
                if params["enable"]:
                    bp.enable()
                else:
                    bp.disable()

        elif method == "RequestBreakpointIgnore":
            bp = Breakpoint.get_break(params["filename"], params["line"])
            if bp is not None:
                bp.ignore = params["count"]

        elif method == "RequestWatch":
            if params["setWatch"]:
                if params["condition"].endswith(("??created??", "??changed??")):
                    compiledCond, flag = params["condition"].split()
                else:
                    compiledCond = params["condition"]
                    flag = ""

                try:
                    compiledCond = compile(compiledCond, "<string>", "eval")
                except SyntaxError:
                    self.sendJsonCommand(
                        "ResponseWatchConditionError",
                        {
                            "condition": params["condition"],
                        },
                    )
                    return
                Watch(params["condition"], compiledCond, flag, params["temporary"])
            else:
                Watch.clear_watch(params["condition"])

        elif method == "RequestWatchEnable":
            wp = Watch.get_watch(params["condition"])
            if wp is not None:
                if params["enable"]:
                    wp.enable()
                else:
                    wp.disable()

        elif method == "RequestWatchIgnore":
            wp = Watch.get_watch(params["condition"])
            if wp is not None:
                wp.ignore = params["count"]

        elif method == "RequestShutdown":
            self.sessionClose()

        elif method == "RequestSetNoDebugList":
            self.noDebugList = params["noDebug"][:]

        elif method == "RequestCompletion":
            self.__completionList(params["text"])

    def setDisassembly(self, disassembly):
        """
        Public method to store a disassembly of the code object raising an
        exception.

        @param disassembly dictionary containing the disassembly information
        @type dict
        """
        self.disassembly = disassembly

    def sendJsonCommand(self, method, params):
        """
        Public method to send a single command or response to the IDE.

        @param method command or response command name to be sent
        @type str
        @param params dictionary of named parameters for the command or
            response
        @type dict
        """
        # send debugger ID with all responses
        if "debuggerId" not in params:
            params["debuggerId"] = self.__debuggerId

        jsonCommand = prepareJsonCommand(method, params)

        self.writestream.write_p(jsonCommand)
        self.writestream.flush()

    def sendClearTemporaryBreakpoint(self, filename, lineno):
        """
        Public method to signal the deletion of a temporary breakpoint.

        @param filename name of the file the bp belongs to
        @type str
        @param lineno line number of the bp
        @type int
        """
        self.sendJsonCommand(
            "ResponseClearBreakpoint", {"filename": filename, "line": lineno}
        )

    def sendClearTemporaryWatch(self, condition):
        """
        Public method to signal the deletion of a temporary watch expression.

        @param condition condition of the watch expression to be cleared
        @type str
        """
        self.sendJsonCommand(
            "ResponseClearWatch",
            {
                "condition": condition,
            },
        )

    def sendResponseLine(self, stack, threadName):
        """
        Public method to send the current call stack.

        @param stack call stack
        @type list
        @param threadName name of the thread sending the event
        @type str
        """
        self.sendJsonCommand(
            "ResponseLine",
            {
                "stack": stack,
                "threadName": threadName,
            },
        )

    def sendCallTrace(self, event, fromInfo, toInfo):
        """
        Public method to send a call trace entry.

        @param event trace event (call or return)
        @type str
        @param fromInfo dictionary containing the origin info
        @type dict with 'filename', 'linenumber' and 'codename'
            as keys
        @param toInfo dictionary containing the target info
        @type dict with 'filename', 'linenumber' and 'codename'
            as keys
        """
        self.sendJsonCommand(
            "CallTrace",
            {
                "event": event[0],
                "from": fromInfo,
                "to": toInfo,
            },
        )

    def sendException(self, exceptionType, exceptionMessage, stack, threadName):
        """
        Public method to send information for an exception.

        @param exceptionType type of exception raised
        @type str
        @param exceptionMessage message of the exception
        @type str
        @param stack stack trace information
        @type list
        @param threadName name of the thread sending the event
        @type str
        """
        self.sendJsonCommand(
            "ResponseException",
            {
                "type": exceptionType,
                "message": exceptionMessage,
                "stack": stack,
                "threadName": threadName,
            },
        )

    def sendSyntaxError(self, message, filename, lineno, charno, threadName):
        """
        Public method to send information for a syntax error.

        @param message syntax error message
        @type str
        @param filename name of the faulty file
        @type str
        @param lineno line number info
        @type int
        @param charno character number info
        @type int
        @param threadName name of the thread sending the event
        @type str
        """
        self.sendJsonCommand(
            "ResponseSyntax",
            {
                "message": message,
                "filename": filename,
                "linenumber": lineno,
                "characternumber": charno,
                "threadName": threadName,
            },
        )

    def sendPassiveStartup(self, filename, reportAllExceptions):
        """
        Public method to send the passive start information.

        @param filename name of the script
        @type str
        @param reportAllExceptions flag to enable reporting of all exceptions
        @type bool
        """
        self.sendJsonCommand(
            "PassiveStartup",
            {
                "filename": filename,
                "reportAllExceptions": reportAllExceptions,
            },
        )

    def sendDebuggerId(self):
        """
        Public method to send the debug client id.
        """
        # debugger ID is added automatically by sendJsonCommand
        self.sendJsonCommand("DebuggerId", {})

    def __clientCapabilities(self):
        """
        Private method to determine the clients capabilities.

        @return client capabilities
        @rtype int
        """
        if importlib.util.find_spec("PyProfile") is None:
            return self.clientCapabilities & ~DebugClientCapabilities.HasProfiler
        else:
            return self.clientCapabilities

    def readReady(self, stream):
        """
        Public method called when there is data ready to be read.

        @param stream file like object that has data to be read
        @type file like
        @return flag indicating an error condition
        @rtype bool
        """
        error = False

        self.lockClient()
        try:
            command = stream.readCommand()
        except Exception:
            error = True
            command = ""
        self.unlockClient()

        if error or len(command) == 0:
            self.sessionClose()
        else:
            self.handleJsonCommand(command)

        return error

    def writeReady(self, stream):
        """
        Public method called when we are ready to write data.

        @param stream file like object that has data to be written
        @type file like
        """
        stream.write_p("")
        stream.flush()

    def __interact(self):
        """
        Private method to interact with the debugger.
        """
        global DebugClientInstance

        DebugClientInstance = self
        self.__receiveBuffer = ""

        if not self.passive:
            # At this point simulate an event loop.
            self.eventLoop()

    def eventLoop(self, disablePolling=False):
        """
        Public method implementing our event loop.

        @param disablePolling flag indicating to enter an event loop with
            polling disabled
        @type bool
        """
        self.eventExit = False
        self.pollingDisabled = disablePolling
        selectErrors = 0
        self.rawLine = ""

        while not self.eventExit:
            wrdy = []

            if self.writestream.nWriteErrors > self.writestream.MAX_TRIES:
                break

            if AsyncPendingWrite(self.writestream):
                wrdy.append(self.writestream)

            if AsyncPendingWrite(self.errorstream):
                wrdy.append(self.errorstream)

            try:
                rrdy, wrdy, xrdy = select.select([self.readstream], wrdy, [])
            except (KeyboardInterrupt, OSError):
                selectErrors += 1
                if selectErrors <= 10:  # arbitrarily selected
                    # just carry on
                    continue
                else:
                    # give up for too many errors
                    break
            except ValueError:
                # the client socket might already be closed, i.e. its fd is -1
                break

            # reset the select error counter
            selectErrors = 0

            if self.readstream in rrdy:
                error = self.readReady(self.readstream)
                if error:
                    break

            if self.writestream in wrdy:
                self.writeReady(self.writestream)

            if self.errorstream in wrdy:
                self.writeReady(self.errorstream)

        self.eventExit = False
        self.pollingDisabled = False

    def eventPoll(self):
        """
        Public method to poll for events like 'set break point'.
        """
        if self.pollingDisabled:
            return

        wrdy = []
        if AsyncPendingWrite(self.writestream):
            wrdy.append(self.writestream)

        if AsyncPendingWrite(self.errorstream):
            wrdy.append(self.errorstream)

        # immediate return if nothing is ready.
        try:
            rrdy, wrdy, _xrdy = select.select([self.readstream], wrdy, [], 0)
        except (KeyboardInterrupt, OSError):
            return

        if self.readstream in rrdy:
            self.readReady(self.readstream)

        if self.writestream in wrdy:
            self.writeReady(self.writestream)

        if self.errorstream in wrdy:
            self.writeReady(self.errorstream)

    def connectDebugger(self, port, remoteAddress=None, redirect=True, name=""):
        """
        Public method to establish a session with the debugger.

        It opens a network connection to the debugger, connects it to stdin,
        stdout and stderr and saves these file objects in case the application
        being debugged redirects them itself.

        @param port the port number to connect to
        @type int
        @param remoteAddress the network address of the debug server host
        @type str
        @param redirect flag indicating redirection of stdin, stdout and
            stderr
        @type bool
        @param name name to be attached to the debugger ID
        @type str
        """
        if remoteAddress is None:
            remoteAddress = "127.0.0.1"
        elif "@@i" in remoteAddress:
            remoteAddress = remoteAddress.split("@@i")[0]
        sock = socket.create_connection((remoteAddress, port))

        stdinName = sys.stdin.name
        # Special case if in a multiprocessing.Process
        if isinstance(stdinName, int):
            stdinName = "<stdin>"

        self.readstream = AsyncFile(sock, sys.stdin.mode, stdinName)
        self.writestream = AsyncFile(sock, sys.stdout.mode, sys.stdout.name)
        self.errorstream = AsyncFile(sock, sys.stderr.mode, sys.stderr.name)

        if redirect:
            sys.stdin = self.readstream
            sys.stdout = self.writestream
            sys.stderr = self.errorstream
        self.redirect = redirect

        # attach to the main thread here
        self.attachThread(mainThread=True)

        if not name:
            name = "main"
        self.__debuggerId = "{0}/{1}/{2}".format(
            socket.gethostname(), os.getpid(), name
        )

        self.sendDebuggerId()

    def __unhandled_exception(self, exctype, excval, exctb):
        """
        Private method called to report an uncaught exception.

        @param exctype class of the exception
        @type type
        @param excval exception instance
        @type Exception
        @param exctb traceback for the exception
        @type traceback
        """
        self.mainThread.user_exception((exctype, excval, exctb), True)

        if self.__debugeeExceptHook is not None:
            # call the exception hook of the program being debugged
            self.__debugeeExceptHook(exctype, excval, exctb)

    def checkExceptionHook(self):
        """
        Public method to check, that 'sys.excepthook' is still our hook.

        If the exception hook has been changed by the program being debugger, save
        that hook and set it to ours again. The program's hook is called in our
        '__unhandled_exception()' method.
        """
        if sys.excepthook != self.__unhandled_exception:
            self.__debugeeExceptHook = sys.excepthook
            sys.excepthook = self.__unhandled_exception

    def __interceptSignals(self):
        """
        Private method to intercept common signals.
        """
        for signum in [
            signal.SIGABRT,  # abnormal termination
            signal.SIGFPE,  # floating point exception
            signal.SIGILL,  # illegal instruction
            signal.SIGSEGV,  # segmentation violation
        ]:
            signal.signal(signum, self.__signalHandler)

    def __signalHandler(self, signalNumber, stackFrame):
        """
        Private method to handle signals.

        @param signalNumber number of the signal to be handled
        @type int
        @param stackFrame current stack frame
        @type frame object
        """
        if signalNumber == signal.SIGABRT:
            message = "Abnormal Termination"
        elif signalNumber == signal.SIGFPE:
            message = "Floating Point Exception"
        elif signalNumber == signal.SIGILL:
            message = "Illegal Instruction"
        elif signalNumber == signal.SIGSEGV:
            message = "Segmentation Violation"
        else:
            message = "Unknown Signal '{0}'".format(signalNumber)

        filename = self.absPath(stackFrame)

        linenr = stackFrame.f_lineno
        ffunc = stackFrame.f_code.co_name

        if ffunc == "?":
            ffunc = ""

        if ffunc and not ffunc.startswith("<"):
            argInfo = getargvalues(stackFrame)
            try:
                fargs = formatargvalues(
                    argInfo.args, argInfo.varargs, argInfo.keywords, argInfo.locals
                )
            except Exception:
                fargs = ""
        else:
            fargs = ""

        self.sendJsonCommand(
            "ResponseSignal",
            {
                "message": message,
                "filename": filename,
                "linenumber": linenr,
                "function": ffunc,
                "arguments": fargs,
            },
        )

    def absPath(self, fn):
        """
        Public method to convert a filename to an absolute name.

        sys.path is used as a set of possible prefixes. The name stays
        relative if a file could not be found.

        @param fn filename
        @type str
        @return the converted filename
        @rtype str
        """
        if os.path.isabs(fn):
            return fn

        # Check the cache.
        if fn in self._fncache:
            return self._fncache[fn]

        # Search sys.path.
        for p in sys.path:
            afn = os.path.abspath(os.path.join(p, fn))
            nafn = os.path.normcase(afn)

            if os.path.exists(nafn):
                self._fncache[fn] = afn
                d = os.path.dirname(afn)
                if (d not in sys.path) and (d not in self.dircache):
                    self.dircache.append(d)
                return afn

        # Search the additional directory cache
        for p in self.dircache:
            afn = os.path.abspath(os.path.join(p, fn))
            nafn = os.path.normcase(afn)

            if os.path.exists(nafn):
                self._fncache[fn] = afn
                return afn

        # Nothing found.
        return fn

    def getRunning(self):
        """
        Public method to return the main script we are currently running.

        @return flag indicating a running debug session
        @rtype bool
        """
        return self.running

    def progTerminated(self, status, message="", closeSession=True):
        """
        Public method to tell the debugger that the program has terminated.

        @param status return status
        @type int
        @param message status message
        @type str
        @param closeSession flag indicating to close the debugger session
        @type bool
        """
        if status is None:
            status = 0
        elif not isinstance(status, int):
            message = str(status)
            status = 1
        if message is None:
            message = ""

        if self.running:
            self.set_quit()
            program = self.running
            self.running = None
            self.sendJsonCommand(
                "ResponseExit",
                {
                    "status": status,
                    "message": message,
                    "program": program,
                },
            )

        # reset coding
        self.__coding = self.defaultCoding

        if closeSession:
            self.sessionClose(False)

    def __dumpVariables(self, frmnr, scope, filterList):
        """
        Private method to return the variables of a frame to the debug server.

        @param frmnr distance of frame reported on. 0 is the current frame
        @type int
        @param scope 1 to report global variables, 0 for local variables
        @type int
        @param filterList list of variable types to be filtered
        @type list of str
        """
        if self.currentThread is None:
            return

        self.resolverCache = [{}, {}]
        frmnr += self.currentThread.skipFrames
        if scope == 0:
            self.framenr = frmnr

        f = self.currentThread.getFrame(frmnr)

        if f is None:
            if scope == 1:
                varDict = self.debugMod.__dict__
            else:
                scope = -2
        elif scope == 1:
            varDict = dict(f.f_globals)
        elif f.f_globals == f.f_locals:
            scope = -1
        else:
            varDict = dict(f.f_locals)

        # Update known types list
        DebugVariables.updateTypeMap()

        varlist = (
            []
            if scope < 0
            else self.__formatVariablesList(varDict.items(), scope, filterList)
        )

        self.sendJsonCommand(
            "ResponseVariables",
            {
                "scope": scope,
                "variables": varlist,
            },
        )

    def __dumpVariable(self, var, frmnr, scope, filterList):
        """
        Private method to return the variables of a frame to the debug server.

        @param var list encoded name of the requested variable
        @type list of str and int
        @param frmnr distance of frame reported on. 0 is the current frame
        @type int
        @param scope 1 to report global variables, 0 for local variables
        @type int
        @param filterList list of variable types to be filtered
        @type list of int
        """
        if self.currentThread is None:
            return

        frmnr += self.currentThread.skipFrames
        f = self.currentThread.getFrame(frmnr)

        if f is None:
            if scope == 1:
                varDict = self.debugMod.__dict__
            else:
                scope = -1
        elif scope == 1:
            varDict = dict(f.f_globals)
        elif f.f_globals == f.f_locals:
            scope = -1
        else:
            varDict = dict(f.f_locals)

        varlist = []

        # fast path if variable was looked up before (see elif)
        if scope != -1 and str(var) in self.resolverCache[scope]:
            varGen = self.resolverCache[scope][str(var)]
            idx, varDict = next(varGen)
            if idx != -2:  # more elements available
                var.insert(0, idx)
                varlist = self.__formatVariablesList(
                    varDict, scope, filterList, var[1:]
                )
        elif scope != -1:
            variable = varDict
            # Lookup the wanted attribute
            for attribute in var:
                resolver = DebugVariables.getResolver(variable)
                if resolver:
                    variable = resolver.resolve(variable, attribute)
                    if variable is None:
                        break

                else:
                    break

            idx = -3  # Requested variable doesn't exist anymore
            # If found, get the details of attribute
            if variable is not None:
                resolver = DebugVariables.getResolver(variable)
                if resolver:
                    varGen = resolver.getVariableList(variable)
                    # cache for next lookup
                    self.resolverCache[scope][str(var)] = varGen

                    idx, varDict = next(varGen)
                    if idx != -2:  # more elements available
                        varlist = self.__formatVariablesList(
                            varDict, scope, filterList, var
                        )

            var.insert(0, idx)

        self.sendJsonCommand(
            "ResponseVariable",
            {
                "scope": scope,
                "variable": var,
                "variables": varlist,
            },
        )

    def __formatVariablesList(self, variables, scope, filterList=None, var=None):
        """
        Private method to produce a formated variables list.

        The dictionary passed in to it is scanned. Variables are
        only added to the list, if their type is not contained
        in the filter list and their name doesn't match any of the filter
        expressions. The formated variables list (a list of tuples of 3
        values) is returned.

        @param variables variables list to be processed
        @type list of tuple of (str, Any) or (str, str, Any)
        @param scope 1 to filter using the globals filter, 0 using the locals
            filter.
            Variables are only added to the list, if their access path does not match
            any of the filter expressions and the 'show/no show' indication.
        @type int
        @param filterList list of variable types to be filtered.
            Variables are only added to the list, if their type is not
            contained in the filter list. (defaults to None)
        @type list of str (optional)
        @param var list encoded name of the requested variable (access path) (defaults
            to None)
        @type list of str and int (optional)
        @return A tuple consisting of a list of formatted variables. Each
            variable entry is a tuple of three elements, the variable name,
            its type and value.
        @rtype list of tuple of (str, str, str)
        """
        filterList = set(filterList or [])

        varlist = []
        patternFilterObjects, showFlag = (
            self.globalsFilterObjects if scope else self.localsFilterObjects
        )

        if var:
            var = ".".join(str(v) for v in var)

        for variabel in variables:
            valtype = None
            rvalue = None
            try:
                key, value = variabel
            except ValueError:
                # Special case for some Qt variables, where the real type is
                # overwritten
                key, valtype, rvalue = variabel

            # filter based on the filter pattern
            keyPath = "{0}.{1}".format(var, key) if var else key
            if patternFilterObjects and (
                (not showFlag and patternFilterObjects.match(str(keyPath)))
                or (showFlag and not patternFilterObjects.match(str(keyPath)))
            ):
                continue

            # filter hidden attributes (filter #0)
            if "__" in filterList and str(key)[:2] == "__":
                continue

            hasChildren = False
            # special handling for '__builtins__' (it's way too big)
            if key == "__builtins__":
                rvalue = "<module builtins (built-in)>"
                valtype = "module"
                if valtype in filterList:
                    continue
            elif (key in SpecialAttributes and "special_attributes" in filterList) or (
                key == "__hash__" and "builtin_function_or_method" in filterList
            ):
                continue
            elif valtype is None:
                # valtypestr, e.g. class 'PyQt6.QtCore.QPoint'
                valtypestr = str(type(value))
                _, valtype = valtypestr.split(" ", 1)
                # valtype is the real type, e.g. PyQt6.QtCore.QPoint
                # valtype_filter is used for filtering, where the base class is
                # also important
                valtype = valtype_filter = valtype[1:-2]
                # Strip 'instance' to be equal with Python 3
                if valtype == "instancemethod":
                    valtype = valtype_filter = "method"
                elif isinstance(value, type):
                    valtype_filter = "class"
                    if valtype == "type":
                        valtype = "class"
                elif valtype == "method-wrapper":
                    valtype = valtype_filter = "builtin_function_or_method"

                # Don't process variables which types are on filter list
                if (
                    valtype_filter in filterList
                    or (
                        valtype_filter in ("sip.enumtype", "sip.wrappertype")
                        and "class" in filterList
                    )
                    or (
                        valtype_filter in ("sip.methoddescriptor", "method_descriptor")
                        and "method" in filterList
                    )
                    or (
                        valtype_filter in ("numpy.ndarray", "array.array")
                        and "list" in filterList
                    )
                    or (
                        valtype_filter == "django.MultiValueDict"
                        and "dict" in filterList
                    )
                    or "instance" in filterList
                ):
                    continue

            length = -2
            indicator = ""

            if valtype == "str":
                rvalue = repr(value)
                length = len(rvalue)
            elif valtype in NonExpandableTypes:
                rvalue = repr(value)

            if rvalue is not None:
                varlist.append((key, indicator, valtype, hasChildren, length, rvalue))
                continue

            try:
                for dtype in DebugVariables._ArrayTypes:
                    if isinstance(value, dtype):
                        try:
                            length = len(value)
                        except TypeError:
                            length = -1  # Uninitialized array

                        dtype = str(dtype)[8:-2]
                        # Standard array type indicators
                        indicator = self.Type2Indicators.get(dtype, "")

                        # Special handling of some array types
                        if valtype == "array.array":
                            indicator = "[<{0}>]".format(value.typecode)
                        elif valtype == "collections.defaultdict":
                            if value.default_factory is None:
                                def_factory = "None"
                            else:
                                def_factory = value.default_factory.__name__
                            indicator = "{{:<{0}>}}".format(def_factory)
                        elif valtype == "numpy.ndarray" and length > -1:
                            length = "x".join(str(x) for x in value.shape)
                        elif valtype.endswith(".MultiValueDict"):
                            indicator = "{:}"  # __IGNORE_WARNING__
                            valtype = "django.MultiValueDict"  # shortened type
                        break
                else:
                    rvalue = repr(value)

                hasChildren = True
            except Exception:
                rvalue = ""

            varlist.append((key, indicator, valtype, hasChildren, length, rvalue))

        return varlist

    def __generateFilterObjects(self, scope, filterString):
        """
        Private slot to convert a filter string to a list of filter objects.

        @param scope 1 to generate filter for global variables, 0 for local
            variables
        @type int
        @param filterString string of filter patterns separated by ';'
        @type str
        """
        patternFilterObjects = None
        filterString = filterString.strip()
        if filterString:
            if filterString[0] == "~":
                showFlag = False
                filterString = filterString[1:].strip()
            else:
                showFlag = True
            if filterString:
                filterList = filterString.split(";")
                pattern = "|".join(f.strip() for f in filterList)
                with contextlib.suppress(re.error):
                    patternFilterObjects = re.compile(pattern)
        else:
            showFlag = False

        if scope:
            self.globalsFilterObjects = (patternFilterObjects, showFlag)
        else:
            self.localsFilterObjects = (patternFilterObjects, showFlag)

    def __completionList(self, text):
        """
        Private slot to handle the request for a commandline completion list.

        @param text the text to be completed
        @type str
        """
        completerDelims = " \t\n`~!@#$%^&*()-=+[{]}\\|;:'\",<>/?"

        completions = set()
        # find position of last delim character
        pos = -1
        while pos >= -len(text):
            if text[pos] in completerDelims:
                if pos == -1:
                    text = ""
                else:
                    text = text[pos + 1 :]
                break
            pos -= 1

        # Get local and global completions
        with contextlib.suppress(AttributeError):
            localdict = self.currentThread.getFrameLocals(self.framenr)
            localCompleter = Completer(localdict).complete
            self.__getCompletionList(text, localCompleter, completions)

        cf = self.currentThread.getFrame(self.framenr)
        globaldict = self.debugMod.__dict__ if cf is None else cf.f_globals
        globalCompleter = Completer(globaldict).complete
        self.__getCompletionList(text, globalCompleter, completions)

        self.sendJsonCommand(
            "ResponseCompletion",
            {
                "completions": list(completions),
                "text": text,
            },
        )

    def __getCompletionList(self, text, completer, completions):
        """
        Private method to create a completions list.

        @param text text to complete
        @type str
        @param completer completer method
        @type function
        @param completions set where to add new completions strings
        @type set
        """
        state = 0
        try:
            comp = completer(text, state)
        except Exception:
            comp = None
        while comp is not None:
            completions.add(comp)
            state += 1
            try:
                comp = completer(text, state)
            except Exception:
                comp = None

    def startDebugger(
        self,
        filename=None,
        host=None,
        port=None,
        enableTrace=True,
        reportAllExceptions=False,
        tracePython=False,
        redirect=True,
        passive=True,
        multiprocessSupport=False,  # noqa: U100
    ):
        """
        Public method used to start the remote debugger.

        @param filename the program to be debugged
        @type str
        @param host hostname of the debug server
        @type str
        @param port portnumber of the debug server
        @type int
        @param enableTrace flag to enable the tracing function
        @type bool
        @param reportAllExceptions flag indicating to report all exceptions
            instead of unhandled exceptions only
        @type bool
        @param tracePython flag to enable tracing into the Python library
        @type bool
        @param redirect flag indicating redirection of stdin, stdout and
            stderr
        @type bool
        @param passive flag indicating a passive debugging session
        @type bool
        @param multiprocessSupport flag indicating to enable multiprocess
            debugging support (unused)
        @type bool
        """
        if host is None:
            host = os.getenv("ERICHOST", "localhost")
        if port is None:
            port = os.getenv("ERICPORT", 42424)

        remoteAddress = self.__resolveHost(host)
        name = os.path.basename(filename) if filename is not None else ""
        self.connectDebugger(port, remoteAddress, redirect, name=name)
        if filename is not None:
            self.running = os.path.abspath(filename)
        else:
            try:
                self.running = os.path.abspath(sys.argv[0])
            except IndexError:
                self.running = None
        if self.running:
            self.__setCoding(self.running)
        self.passive = passive
        self.__interact()

        # setup the debugger variables
        self._fncache = {}
        self.dircache = []
        self.debugging = True

        # all exceptions reporting
        self.reportAllExceptions = reportAllExceptions

        self.attachThread(mainThread=True)
        self.mainThread.tracePythonLibs(tracePython)

        # set the system exception handling function to ensure, that
        # we report on all unhandled exceptions
        sys.excepthook = self.__unhandled_exception
        self.__interceptSignals()

        # now start debugging
        if enableTrace:
            self.mainThread.set_trace()

    def startProgInDebugger(
        self,
        progargs,
        wd="",
        host=None,
        port=None,
        tracePython=False,
        redirect=True,
        passive=True,
        multiprocessSupport=False,
        reportAllExceptions=False,
        callTraceOptimization=False,
        codeStr="",
        scriptModule="",
    ):
        """
        Public method used to start the remote debugger.

        @param progargs commandline for the program to be debugged
        @type list of str
        @param wd working directory for the program execution
        @type str
        @param host hostname of the debug server
        @type str
        @param port portnumber of the debug server
        @type int
        @param tracePython flag to enable tracing into the Python library
        @type bool
        @param redirect flag indicating redirection of stdin, stdout and
            stderr
        @type bool
        @param passive flag indicating a passive debugging session
        @type bool
        @param multiprocessSupport flag indicating to enable multiprocess
            debugging support
        @type bool
        @param reportAllExceptions flag indicating to report all exceptions instead
            of unhandled exceptions only
        @type bool
        @param callTraceOptimization flag indicating to speed up function/method
            call tracing
        @type bool
        @param codeStr string containing Python code to execute
        @type str
        @param scriptModule name of a module to be executed as a script
        @type str
        @return exit code of the debugged program
        @rtype int
        """
        if host is None:
            host = os.getenv("ERICHOST", "localhost")
        if port is None:
            port = os.getenv("ERICPORT", 42424)

        remoteAddress = self.__resolveHost(host)
        if progargs:
            if not progargs[0].startswith("-"):
                name = os.path.basename(progargs[0])
            elif progargs[0] == "--multiprocessing-fork":
                name = "debug_client_mp-fork"
            else:
                name = "debug_client_code"
        else:
            name = "debug_client_code"
        self.connectDebugger(port, remoteAddress, redirect, name=name)

        self._fncache = {}
        self.dircache = []
        if codeStr:
            self.running = "<string>"
            sys.argv = ["<string>"] + progargs[:]
        else:
            sys.argv = progargs[:]
            sys.argv[0] = os.path.abspath(sys.argv[0])
            sys.path = self.__getSysPath(os.path.dirname(sys.argv[0]))
            if wd == "":
                os.chdir(sys.path[1])
            else:
                os.chdir(wd)
            self.running = sys.argv[0]
            self.__setCoding(self.running)
        self.debugging = True
        self.multiprocessSupport = multiprocessSupport
        self.reportAllExceptions = reportAllExceptions
        self.callTraceOptimization = callTraceOptimization

        self.passive = passive
        if passive:
            self.sendPassiveStartup(self.running, reportAllExceptions)

        self.attachThread(mainThread=True)
        self.mainThread.tracePythonLibs(tracePython)

        # set the system exception handling function to ensure, that
        # we report on all unhandled exceptions
        sys.excepthook = self.__unhandled_exception
        self.__interceptSignals()

        # This will eventually enter a local event loop.
        self.debugMod.__dict__["__file__"] = self.running
        sys.modules["__main__"] = self.debugMod
        if codeStr:
            code = self.__compileCommand(codeStr)
        elif scriptModule:
            modName, modSpec, code = runpy._get_module_details(scriptModule)
            self.running = code.co_filename
            self.debugMod.__dict__.clear()
            self.debugMod.__dict__.update(
                {
                    "__name__": "__main__",
                    "__file__": self.running,
                    "__package__": modSpec.parent,
                    "__loader__": modSpec.loader,
                    "__spec__": modSpec,
                    "__builtins__": __builtins__,
                }
            )
        else:
            code = self.__compileFileSource(self.running)
        res = (
            self.mainThread.run(code, self.debugMod.__dict__, debug=True)
            if code
            else 42  # should not happen
        )
        return res

    def run_call(self, scriptname, func, *args):
        """
        Public method used to start the remote debugger and call a function.

        @param scriptname name of the script to be debugged
        @type str
        @param func function to be called
        @type function
        @param *args arguments being passed to func
        @type list
        @return result of the function call
        @rtype Any
        """
        self.startDebugger(scriptname, enableTrace=False)
        res = self.mainThread.runcall(func, *args)
        self.progTerminated(res, closeSession=False)
        return res

    def __resolveHost(self, host):
        """
        Private method to resolve a hostname to an IP address.

        @param host hostname of the debug server
        @type str
        @return IP address
        @rtype str
        """
        try:
            host, version = host.split("@@")
        except ValueError:
            version = "v4"

        family = (
            0
            if version.startswith("i")
            else (socket.AF_INET if version == "v4" else socket.AF_INET6)
        )

        try:
            addrinfo = socket.getaddrinfo(host, None, family, socket.SOCK_STREAM)
            return addrinfo[0][4][0]
        except OSError:
            # Did not resolve via this method. Return the host name and let Python3
            # try when connecting.
            return host

        return None

    def main(self):
        """
        Public method implementing the main method.
        """
        if "--" in sys.argv:
            args = sys.argv[1:]
            host = None
            port = None
            wd = ""
            tracePython = False
            redirect = True
            passive = True
            multiprocess = False
            reportAllExceptions = False
            callTraceOptimization = False
            codeStr = ""
            scriptModule = ""
            while args[0]:
                if args[0] == "-h":
                    host = args[1]
                    del args[:2]
                elif args[0] == "-p":
                    port = int(args[1])
                    del args[:2]
                elif args[0] == "-w":
                    wd = args[1]
                    del args[:2]
                elif args[0] == "-t":
                    tracePython = True
                    del args[0]
                elif args[0] == "-n":
                    redirect = False
                    del args[0]
                elif args[0] == "--no-encoding":
                    self.noencoding = True
                    del args[0]
                elif args[0] == "--no-passive":
                    passive = False
                    del args[0]
                elif args[0] == "--multiprocess":
                    multiprocess = True
                    del args[0]
                elif args[0] == "--report-exceptions":
                    reportAllExceptions = True
                    del args[0]
                elif args[0] == "--call-trace-optimization":
                    callTraceOptimization = True
                    del args[0]
                elif args[0] in ("-c", "--code"):
                    codeStr = args[1]
                    del args[:2]
                elif args[0] in ("-m", "--module"):
                    scriptModule = args[1]
                    del args[:2]
                elif args[0] == "--":
                    del args[0]
                    break
                else:  # unknown option
                    del args[0]
            if not args:
                print("No program given. Aborting!")
                # __IGNORE_WARNING_M801__
            elif "-m" in args:
                print("Running module as a script is not supported. Aborting!")
                # __IGNORE_WARNING_M801__
            else:
                # Store options in case a new Python process is created
                self.startOptions = (
                    wd,
                    host,
                    port,
                    reportAllExceptions,
                    tracePython,
                    redirect,
                    self.noencoding,
                )
                if not self.noencoding:
                    self.__coding = self.defaultCoding
                patchNewProcessFunctions(multiprocess, self)
                res = self.startProgInDebugger(
                    args,
                    wd,
                    host,
                    port,
                    tracePython=tracePython,
                    redirect=redirect,
                    passive=passive,
                    multiprocessSupport=multiprocess,
                    reportAllExceptions=reportAllExceptions,
                    callTraceOptimization=callTraceOptimization,
                    codeStr=codeStr,
                    scriptModule=scriptModule,
                )
                sys.exit(res)
        else:
            if sys.argv[1] == "--no-encoding":
                self.noencoding = True
                del sys.argv[1]

            if sys.argv[1] == "--multiprocess":
                self.multiprocessSupport = True
                del sys.argv[1]

            if sys.argv[1] == "--call-trace-optimization":
                self.callTraceOptimization = True
                del sys.argv[1]

            if sys.argv[1] == "":
                del sys.argv[1]

            try:
                port = int(sys.argv[1])
            except (IndexError, ValueError):
                port = -1

            if sys.argv[2] == "True":
                redirect = True
            elif sys.argv[2] == "False":
                redirect = False
            else:
                try:
                    redirect = int(sys.argv[2])
                except (IndexError, ValueError):
                    redirect = True

            ipOrHost = sys.argv[3]
            if ":" in ipOrHost or ipOrHost[0] in "0123456789":
                # IPv6 address or IPv4 address
                remoteAddress = ipOrHost
            else:
                remoteAddress = self.__resolveHost(ipOrHost)
            if remoteAddress is None:
                print(f"Remote host '{ipOrHost}' could not be resolved.")  # noqa: M801
                sys.exit(1)

            sys.argv = [""]
            if "" not in sys.path:
                sys.path.insert(0, "")

            if port >= 0:
                # Store options in case a new Python process is created
                self.startOptions = (
                    "",
                    remoteAddress,
                    port,
                    False,
                    False,
                    redirect,
                    self.noencoding,
                )
                if not self.noencoding:
                    self.__coding = self.defaultCoding
                patchNewProcessFunctions(self.multiprocessSupport, self)
                self.connectDebugger(port, remoteAddress, redirect)
                self.__interact()
            else:
                print("No network port given. Aborting...")  # noqa: M801
                sys.exit(2)

    def close(self, fd):
        """
        Public method implementing a close method as a replacement for
        os.close().

        It prevents the debugger connections from being closed.

        @param fd file descriptor to be closed
        @type int
        """
        if fd in [
            self.readstream.fileno(),
            self.writestream.fileno(),
            self.errorstream.fileno(),
        ]:
            return

        DebugClientOrigClose(fd)

    def __getSysPath(self, firstEntry):
        """
        Private slot to calculate a path list including the PYTHONPATH
        environment variable.

        @param firstEntry entry to be put first in sys.path
        @type str
        @return path list for use as sys.path
        @rtype list of str
        """
        sysPath = [
            path
            for path in os.environ.get("PYTHONPATH", "").split(os.pathsep)
            if path not in sys.path
        ] + sys.path[:]
        if "" in sysPath:
            sysPath.remove("")
        sysPath.insert(0, firstEntry)
        sysPath.insert(0, "")
        return sysPath

    def skipMultiProcessDebugging(self, scriptName):
        """
        Public method to check, if the given script is eligible for debugging.

        @param scriptName name of the script to check
        @type str
        @return flag indicating eligibility
        @rtype bool
        """
        return any(fnmatch.fnmatch(scriptName, pattern) for pattern in self.noDebugList)
