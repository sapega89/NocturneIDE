# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an import hook patching modules to support debugging.
"""

import importlib
import sys

from MultiprocessingExtension import patchMultiprocessing
from QProcessExtension import patchQProcess
from SubprocessExtension import patchSubprocess


class ModuleLoader:
    """
    Class implementing an import hook patching modules to support debugging.
    """

    def __init__(self, debugClient):
        """
        Constructor

        @param debugClient reference to the debug client object
        @type DebugClient
        """
        self.__dbgClient = debugClient

        self.__enableImportHooks = set()

        # reset already imported thread module to apply hooks at next import
        for moduleName in ("thread", "_thread", "threading"):
            if moduleName in sys.modules:
                del sys.modules[moduleName]

        self.__modulesToPatch = (
            "_thread",
            "threading",
            "greenlet",
            "subprocess",
            "multiprocessing",
            "PyQt5.QtCore",
            "PyQt6.QtCore",
            "PySide2.QtCore",
            "PySide6.QtCore",
        )

        sys.meta_path.insert(0, self)

    def __loadModule(self, fullname):
        """
        Private method to load a module.

        @param fullname name of the module to be loaded
        @type str
        @return reference to the loaded module
        @rtype module
        """
        module = importlib.import_module(fullname)
        sys.modules[fullname] = module
        self.__enableImportHooks.remove(fullname)
        ## Add hook for _thread.start_new_thread
        if fullname == "_thread" and not hasattr(module, "eric7_patched"):
            module.eric7_patched = True
            self.__dbgClient.patchPyThread(module)

        ## Add hook for threading.run()
        elif fullname == "threading" and not hasattr(module, "eric7_patched"):
            module.eric7_patched = True
            self.__dbgClient.patchPyThreading(module)

        ## greenlet support
        elif fullname == "greenlet" and not hasattr(module, "eric7_patched"):
            if self.__dbgClient.patchGreenlet(module):
                module.eric7_patched = True

        ## Add hook for subprocess.Popen()
        elif fullname == "subprocess" and not hasattr(module, "eric7_patched"):
            module.eric7_patched = True
            patchSubprocess(module, self.__dbgClient)

        ## Add hook for multiprocessing.Process
        elif fullname == "multiprocessing" and not hasattr(module, "eric7_patched"):
            module.eric7_patched = True
            patchMultiprocessing(module, self.__dbgClient)

        ## Add hook for *.QThread and *.QProcess
        elif fullname in (
            "PyQt5.QtCore",
            "PyQt6.QtCore",
            "PySide2.QtCore",
            "PySide6.QtCore",
        ) and not hasattr(module, "eric7_patched"):
            module.eric7_patched = True
            self.__dbgClient.patchQThread(module)
            patchQProcess(module, self.__dbgClient)

        return module

    def find_spec(self, fullname, _path, target=None):  # noqa: U100
        """
        Public method returning the module spec.

        @param fullname name of the module to be loaded
        @type str
        @param _path path to resolve the module name (unused)
        @type str
        @param target module object to use for a more educated guess
            about what spec to return (unused)
        @type module
        @return module spec object pointing to the module loader
        @rtype ModuleSpec
        """
        if fullname in sys.modules or self.__dbgClient.debugging is False:
            return None

        if (
            fullname in self.__modulesToPatch
            and fullname not in self.__enableImportHooks
        ):
            # Disable hook to be able to import original module
            self.__enableImportHooks.add(fullname)
            return importlib.machinery.ModuleSpec(fullname, self)

        return None

    def create_module(self, spec):
        """
        Public method to create a module based on the passed in spec.

        @param spec module spec object for loading the module
        @type ModuleSpec
        @return created and patched module
        @rtype module
        """
        return self.__loadModule(spec.name)

    def exec_module(self, module):
        """
        Public method to execute the created module.

        @param module module to be executed
        @type module
        """
        pass
