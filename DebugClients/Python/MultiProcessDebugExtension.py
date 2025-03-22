# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a function to patch the process creation functions to
support multiprocess debugging.
"""

import contextlib
import os
import sys

from DebugUtilities import (
    isPythonProgram,
    isWindowsPlatform,
    patchArguments,
    patchArgumentStringWindows,
)

_debugClient = None


def _shallPatch():
    """
    Function to determine, if the multiprocessing patches should be done.

    @return flag indicating patching should be performed
    @rtype bool
    """
    return _debugClient.debugging and _debugClient.multiprocessSupport


def patchModule(module, functionName, createFunction):
    """
    Function to replace a function of a module with a modified one.

    @param module reference to the module
    @type types.ModuleType
    @param functionName name of the function to be replaced
    @type str
    @param createFunction function creating the replacement
    @type types.FunctionType
    """
    if hasattr(module, functionName):
        originalName = "original_" + functionName
        if not hasattr(module, originalName):
            setattr(module, originalName, getattr(module, functionName))
            setattr(module, functionName, createFunction(originalName))


def createExecl(originalName):
    """
    Function to patch the 'execl' process creation functions.

    <ul>
        <li>os.execl(path, arg0, arg1, ...)</li>
        <li>os.execle(path, arg0, arg1, ..., env)</li>
        <li>os.execlp(file, arg0, arg1, ...)</li>
        <li>os.execlpe(file, arg0, arg1, ..., env)</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newExecl(path, *args):
        """
        Function replacing the 'execl' functions of the os module.
        """
        if _shallPatch() and isPythonProgram(args[0]):
            args = patchArguments(_debugClient, args)
            path = args[0]
        return getattr(os, originalName)(path, *args)

    return newExecl


def createExecv(originalName):
    """
    Function to patch the 'execv' process creation functions.

    <ul>
        <li>os.execv(path, args)</li>
        <li>os.execvp(file, args)</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newExecv(path, args):
        """
        Function replacing the 'execv' functions of the os module.
        """
        if _shallPatch() and isPythonProgram(args[0]):
            args = patchArguments(_debugClient, args)
            path = args[0]
        return getattr(os, originalName)(path, args)

    return newExecv


def createExecve(originalName):
    """
    Function to patch the 'execve' process creation functions.

    <ul>
        <li>os.execve(path, args, env)</li>
        <li>os.execvpe(file, args, env)</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newExecve(path, args, env):
        """
        Function replacing the 'execve' functions of the os module.
        """
        if _shallPatch() and isPythonProgram(args[0]):
            args = patchArguments(_debugClient, args)
            path = args[0]
        return getattr(os, originalName)(path, args, env)

    return newExecve


def createSpawnl(originalName):
    """
    Function to patch the 'spawnl' process creation functions.

    <ul>
        <li>os.spawnl(mode, path, arg0, arg1, ...)</li>
        <li>os.spawnlp(mode, file, arg0, arg1, ...)</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newSpawnl(mode, path, *args):
        """
        Function replacing the 'spawnl' functions of the os module.
        """
        if _shallPatch():
            args = patchArguments(_debugClient, args)
        return getattr(os, originalName)(mode, path, *args)

    return newSpawnl


def createSpawnv(originalName):
    """
    Function to patch the 'spawnv' process creation functions.

    <ul>
        <li>os.spawnv(mode, path, args)</li>
        <li>os.spawnvp(mode, file, args)</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newSpawnv(mode, path, args):
        """
        Function replacing the 'spawnv' functions of the os module.
        """
        if _shallPatch():
            args = patchArguments(_debugClient, args)
        return getattr(os, originalName)(mode, path, args)

    return newSpawnv


def createSpawnve(originalName):
    """
    Function to patch the 'spawnve' process creation functions.

    <ul>
        <li>os.spawnve(mode, path, args, env)</li>
        <li>os.spawnvpe(mode, file, args, env)</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newSpawnve(mode, path, args, env):
        """
        Function replacing the 'spawnve' functions of the os module.
        """
        if _shallPatch():
            args = patchArguments(_debugClient, args)
        return getattr(os, originalName)(mode, path, args, env)

    return newSpawnve


def createPosixSpawn(originalName):
    """
    Function to patch the 'posix_spawn' process creation functions.

    <ul>
        <li>os.posix_spawn(path, argv, env, *, file_actions=None, ...
            (6 more))</li>
        <li>os.posix_spawnp(path, argv, env, *, file_actions=None, ...
            (6 more))</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newPosixSpawn(path, argv, env, **kwargs):
        """
        Function replacing the 'posix_spawn' functions of the os module.
        """
        if _shallPatch():
            argv = patchArguments(_debugClient, argv)
        return getattr(os, originalName)(path, argv, env, **kwargs)

    return newPosixSpawn


def createForkExec(originalName):
    """
    Function to patch the 'fork_exec' process creation functions.

    <ul>
        <li>_posixsubprocess.fork_exec(args, executable_list, close_fds,
            ... (13 more))</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newForkExec(args, *other_args):
        """
        Function replacing the 'fork_exec' functions of the _posixsubprocess
        module.
        """
        import _posixsubprocess  # __IGNORE_WARNING_I103__

        if _shallPatch():
            args = patchArguments(_debugClient, args)
        return getattr(_posixsubprocess, originalName)(args, *other_args)

    return newForkExec


def createFork(originalName):
    """
    Function to patch the 'fork' process creation functions.

    <ul>
        <li>os.fork()</li>
    </ul>

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newFork():
        """
        Function replacing the 'fork' function of the os module.
        """
        # A simple fork will result in a new python process
        isNewPythonProcess = True
        frame = sys._getframe()

        multiprocess = _shallPatch()

        isSubprocessFork = False
        isMultiprocessingPopen = False
        while frame is not None:
            if frame.f_code.co_name == "_Popen":
                # fork() was called from multiprocessing; ignore this here
                # because it is handled in 'MultiprocessingExtension.py'.
                isMultiprocessingPopen = True
                break

            elif (
                frame.f_code.co_name == "_execute_child"
                and "subprocess" in frame.f_code.co_filename
            ):
                isSubprocessFork = True
                # If we're actually in subprocess.Popen creating a child, it
                # may result in something which is not a Python process, (so,
                # we don't want to connect with it in the forked version).
                executable = frame.f_locals.get("executable")
                if executable is not None:
                    isNewPythonProcess = False
                    if isPythonProgram(executable):
                        isNewPythonProcess = True
                break

            frame = frame.f_back
        frame = None  # Just make sure we don't hold on to it.

        childProcess = getattr(os, originalName)()  # fork
        if not childProcess and not isMultiprocessingPopen and isNewPythonProcess:
            (
                wd,
                host,
                port,
                reportAllExceptions,
                tracePython,
                redirect,
                _noencoding,
            ) = _debugClient.startOptions
            _debugClient.startDebugger(
                filename=sys.argv[0],
                host=host,
                port=port,
                enableTrace=multiprocess and not isSubprocessFork,
                reportAllExceptions=reportAllExceptions,
                tracePython=tracePython,
                redirect=redirect,
                passive=False,
                multiprocessSupport=multiprocess,
            )
        return childProcess

    return newFork


def createCreateProcess(originalName):
    """
    Function to patch the 'CreateProcess' process creation function of
    Windows.

    @param originalName original name of the function to be patched
    @type str
    @return function replacing the original one
    @rtype function
    """

    def newCreateProcess(appName, cmdline, *args):
        """
        Function replacing the 'CreateProcess' function of the _subprocess
        or _winapi module.
        """
        try:
            import _subprocess  # __IGNORE_WARNING_I10__
        except ImportError:
            import _winapi as _subprocess  # __IGNORE_WARNING_I10__
        if _shallPatch():
            cmdline = patchArgumentStringWindows(_debugClient, cmdline)
        return getattr(_subprocess, originalName)(appName, cmdline, *args)

    return newCreateProcess


def patchNewProcessFunctions(multiprocessEnabled, debugClient):
    """
    Function to patch the process creation functions to support multiprocess
    debugging.

    @param multiprocessEnabled flag indicating multiprocess support
    @type bool
    @param debugClient reference to the debug client object
    @type DebugClient
    """
    global _debugClient

    if not multiprocessEnabled:
        # return without patching
        return

    # patch 'os.exec...()' functions
    # -    patchModule(os, "execl", createExecl)
    # -    patchModule(os, "execle", createExecl)
    # -    patchModule(os, "execlp", createExecl)
    # -    patchModule(os, "execlpe", createExecl)
    # -    patchModule(os, "execv", createExecv)
    # -    patchModule(os, "execve", createExecve)
    # -    patchModule(os, "execvp", createExecv)
    # -    patchModule(os, "execvpe", createExecve)
    # patch 'os.spawn...()' functions
    patchModule(os, "spawnl", createSpawnl)
    patchModule(os, "spawnle", createSpawnl)
    patchModule(os, "spawnlp", createSpawnl)
    patchModule(os, "spawnlpe", createSpawnl)
    patchModule(os, "spawnv", createSpawnv)
    patchModule(os, "spawnve", createSpawnve)
    patchModule(os, "spawnvp", createSpawnv)
    patchModule(os, "spawnvpe", createSpawnve)

    # patch 'os.posix_spawn...()' functions
    if not isWindowsPlatform():
        patchModule(os, "posix_spawn", createPosixSpawn)
        patchModule(os, "posix_spawnp", createPosixSpawn)

    if isWindowsPlatform():
        try:
            import _subprocess  # __IGNORE_WARNING_I10__
        except ImportError:
            import _winapi as _subprocess  # __IGNORE_WARNING_I10__
        patchModule(_subprocess, "CreateProcess", createCreateProcess)
    else:
        patchModule(os, "fork", createFork)
        with contextlib.suppress(ImportError):
            import _posixsubprocess  # __IGNORE_WARNING_I10__

            patchModule(_posixsubprocess, "fork_exec", createForkExec)

    _debugClient = debugClient
