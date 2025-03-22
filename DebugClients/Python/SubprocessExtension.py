# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a function to patch subprocess.Popen to support debugging
of the process.
"""

import os
import shlex
import shutil

from DebugUtilities import (
    isPythonProgram,
    isWindowsPlatform,
    patchArguments,
    stringToArgumentsWindows,
)

_debugClient = None


def patchSubprocess(module, debugClient):
    """
    Function to patch the subprocess module.

    @param module reference to the imported module to be patched
    @type module
    @param debugClient reference to the debug client object
    @type DebugClient
    """  # __IGNORE_WARNING_D234__
    global _debugClient

    class PopenWrapper(module.Popen):
        """
        Wrapper class for subprocess.Popen.
        """

        def __init__(self, args, *popenargs, **kwargs):
            """
            Constructor

            @param args command line arguments for the new process
            @type list of str or str
            @param popenargs constructor arguments of Popen
            @type list
            @param kwargs constructor keyword only arguments of Popen
            @type dict
            """
            if (
                _debugClient.debugging
                and _debugClient.multiprocessSupport
                and isinstance(args, (str, list))
            ):
                if isinstance(args, str):
                    # convert to arguments list
                    args_list = (
                        stringToArgumentsWindows(args)
                        if isWindowsPlatform()
                        else shlex.split(args)
                    )
                else:
                    # create a copy of the arguments
                    args_list = args[:]
                isPythonProg = isPythonProgram(
                    args_list[0],
                    withPath="shell" in kwargs and kwargs["shell"] is True,
                )
                if isPythonProg:
                    scriptName = os.path.basename(args_list[0])
                    if not _debugClient.skipMultiProcessDebugging(scriptName):
                        if (
                            "shell" in kwargs
                            and kwargs["shell"] is True
                            and not os.path.isabs(args_list[0])
                        ):
                            prog = shutil.which(args_list[0])
                            if prog:
                                args_list[0] = prog
                        args = patchArguments(
                            _debugClient,
                            args_list,
                            noRedirect=True,
                            isPythonProg=isPythonProg,
                        )
                        if "shell" in kwargs and kwargs["shell"] is True:
                            args = shlex.join(args)

            super().__init__(args, *popenargs, **kwargs)

    _debugClient = debugClient
    module.Popen = PopenWrapper
