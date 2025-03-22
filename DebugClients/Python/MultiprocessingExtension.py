# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a function to patch multiprocessing.Process to support
debugging of the process.
"""

import sys
import traceback

_debugClient = None
_originalProcess = None
_originalBootstrap = None


def patchMultiprocessing(module, debugClient):
    """
    Function to patch the multiprocessing module.

    @param module reference to the imported module to be patched
    @type module
    @param debugClient reference to the debug client object
    @type DebugClient
    """  # __IGNORE_WARNING_D234__
    global _debugClient, _originalProcess, _originalBootstrap

    _debugClient = debugClient

    _originalProcess = module.process.BaseProcess
    _originalBootstrap = _originalProcess._bootstrap

    class ProcessWrapper(_originalProcess):
        """
        Wrapper class for multiprocessing.Process.
        """

        def _bootstrap(self, *args, **kwargs):
            """
            Wrapper around _bootstrap to start debugger.

            @param args function arguments
            @type list
            @param kwargs keyword only arguments
            @type dict
            @return exit code of the process
            @rtype int
            """
            _debugging = False
            if _debugClient.debugging and _debugClient.multiprocessSupport:
                scriptName = sys.argv[0]
                if not _debugClient.skipMultiProcessDebugging(scriptName):
                    _debugging = True
                    try:
                        (
                            _wd,
                            host,
                            port,
                            reportAllExceptions,
                            tracePython,
                            redirect,
                            _noencoding,
                        ) = _debugClient.startOptions[:7]
                        _debugClient.startDebugger(
                            sys.argv[0],
                            host=host,
                            port=port,
                            reportAllExceptions=reportAllExceptions,
                            tracePython=tracePython,
                            redirect=redirect,
                            passive=False,
                            multiprocessSupport=True,
                        )
                    except Exception:
                        print(
                            # __IGNORE_WARNING_M801__
                            "Exception during multiprocessing bootstrap init:"
                        )
                        traceback.print_exc(file=sys.stdout)
                        sys.stdout.flush()
                        raise

            exitcode = _originalBootstrap(self, *args, **kwargs)

            if _debugging:
                _debugClient.progTerminated(exitcode, "process finished")

            return exitcode

    _originalProcess._bootstrap = ProcessWrapper._bootstrap
