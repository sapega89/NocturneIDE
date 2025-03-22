# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a function to patch QProcess to support debugging of the
process.
"""

import os

from DebugUtilities import isPythonProgram, patchArguments, startsWithShebang

_debugClient = None


def patchQProcess(module, debugClient):
    """
    Function to patch the QtCore module's QProcess.

    @param module reference to the imported module to be patched
    @type module
    @param debugClient reference to the debug client object
    @type DebugClient
    """  # __IGNORE_WARNING_D234__
    global _debugClient

    class QProcessWrapper(module.QProcess):
        """
        Wrapper class for *.QProcess.
        """

        _origQProcessStartDetached = module.QProcess.startDetached

        def __init__(self, parent=None):
            """
            Constructor
            """
            super().__init__(parent)

        ###################################################################
        ## Handling of 'start(...)' below
        ###################################################################

        def start(self, *args, **kwargs):
            """
            Public method to start the process.

            This method patches the arguments such, that a debug client is
            started for the Python script. A Python script is assumed, if the
            program to be started contains the string 'python'.

            @param args arguments of the start call
            @type list
            @param kwargs keyword arguments of the start call
            @type dict
            """
            if (
                _debugClient.debugging
                and _debugClient.multiprocessSupport
                and (
                    (len(args) >= 2 and isinstance(args[1], list))
                    or (len(args) == 1 and not isinstance(args[0], str))
                    or len(args) == 0
                )
            ):
                if len(args) >= 2:
                    program = args[0]
                    arguments = args[1]
                    if len(args) > 2:
                        mode = args[2]
                    else:
                        mode = module.QIODevice.OpenModeFlag.ReadWrite
                else:
                    program = self.program()
                    arguments = self.arguments()
                    if len(args) == 1:
                        mode = args[0]
                    else:
                        mode = module.QIODevice.OpenModeFlag.ReadWrite
                ok = isPythonProgram(program)
                if ok:
                    if startsWithShebang(program):
                        scriptName = os.path.basename(program)
                    else:
                        scriptName = os.path.basename(arguments[0])
                    if not _debugClient.skipMultiProcessDebugging(scriptName):
                        newArgs = patchArguments(
                            _debugClient,
                            [program] + arguments,
                        )
                        super().start(newArgs[0], newArgs[1:], mode)
                        return

            super().start(*args, **kwargs)

        ###################################################################
        ## Handling of 'startDetached(...)' below
        ###################################################################

        def startDetached(self, *args, **kwargs):
            """
            Public method to start the detached process.

            This method patches the arguments such, that a debug client is
            started for the Python script. A Python script is assumed, if the
            program to be started contains the string 'python'.

            @param args arguments of the start call
            @type list
            @param kwargs keyword arguments of the start call
            @type dict
            @return flag indicating a successful start
            @rtype bool
            """
            if isinstance(self, str):
                return QProcessWrapper.startDetachedStatic(self, *args)
            else:
                return self.__startDetached(*args, **kwargs)

        def __startDetached(self, *args, **kwargs):
            """
            Private method to start the detached process.

            This method patches the arguments such, that a debug client is
            started for the Python script. A Python script is assumed, if the
            program to be started contains the string 'python'.

            @param args arguments of the start call
            @type list
            @param kwargs keyword arguments of the start call
            @type dict
            @return flag indicating a successful start
            @rtype bool
            """
            if (
                _debugClient.debugging
                and _debugClient.multiprocessSupport
                and len(args) == 0
            ):
                program = self.program()
                arguments = self.arguments()
                wd = self.workingDirectory()

                ok = isPythonProgram(program)
                if ok:
                    return QProcessWrapper.startDetachedStatic(program, arguments, wd)

            return super().startDetached(*args, **kwargs)

        @staticmethod
        def startDetachedStatic(*args, **kwargs):
            """
            Static method to start the detached process.

            This method patches the arguments such, that a debug client is
            started for the Python script. A Python script is assumed, if the
            program to be started contains the string 'python'.

            @param args arguments of the start call
            @type list
            @param kwargs keyword arguments of the start call
            @type dict
            @return flag indicating a successful start
            @rtype bool
            """
            if (
                _debugClient.debugging
                and _debugClient.multiprocessSupport
                and (len(args) >= 2 and isinstance(args[1], list))
            ):
                program = args[0]
                arguments = args[1]
                if len(args) >= 3:
                    wd = args[2]
                else:
                    wd = ""
                ok = isPythonProgram(program)
                if ok:
                    if startsWithShebang(program):
                        scriptName = os.path.basename(program)
                    else:
                        scriptName = os.path.basename(arguments[0])
                    if not _debugClient.skipMultiProcessDebugging(scriptName):
                        newArgs = patchArguments(
                            _debugClient,
                            [program] + arguments,
                        )
                        return QProcessWrapper._origQProcessStartDetached(
                            newArgs[0], newArgs[1:], wd
                        )

            return QProcessWrapper._origQProcessStartDetached(*args, **kwargs)

    _debugClient = debugClient
    module.QProcess = QProcessWrapper
