# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a debugger stub for remote debugging.
"""

import os
import sys

from eric7.Globals import getConfig

debugger = None
__scriptname = None

ericpath = os.getenv("ERICDIR", getConfig("ericDir"))

if ericpath not in sys.path:
    sys.path.insert(-1, ericpath)


def initDebugger(kind="standard"):
    """
    Module function to initialize a debugger for remote debugging.

    @param kind type of debugger ("standard" or "threads")
    @type str
    @return flag indicating success
    @rtype bool
    @exception ValueError raised to indicate a wrong debugger kind
    """
    global debugger

    res = True
    try:
        if kind == "standard":
            import DebugClient  # __IGNORE_WARNING_I10__

            debugger = DebugClient.DebugClient()
        else:
            raise ValueError
    except ImportError:
        debugger = None
        res = False

    return res


def runcall(func, *args):
    """
    Module function mimicing the Pdb interface.

    @param func function to be called
    @type function
    @param *args arguments being passed to func
    @type list of Any
    @return the function result
    @rtype Any
    """
    global debugger, __scriptname
    return debugger.run_call(__scriptname, func, *args)


def setScriptname(name):
    """
    Module function to set the script name to be reported back to the IDE.

    @param name absolute path name of the script
    @type str
    """
    global __scriptname
    __scriptname = name


def startDebugger(enableTrace=True, exceptions=True, tracePython=False, redirect=True):
    """
    Module function used to start the remote debugger.

    @param enableTrace flag to enable the tracing function
    @type bool
    @param exceptions flag to enable exception reporting of the IDE
    @type bool
    @param tracePython flag to enable tracing into the Python library
    @type bool
    @param redirect flag indicating redirection of stdin, stdout and stderr
    @type bool
    """
    global debugger
    if debugger:
        debugger.startDebugger(
            enableTrace=enableTrace,
            exceptions=exceptions,
            tracePython=tracePython,
            redirect=redirect,
        )
