# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing utilities functions for the debug client.
"""

import json
import os
import shutil
import sys
import traceback

from collections import namedtuple
from inspect import iscode, isframe

#
# Taken from inspect.py of Python 3.4
#


# Create constants for the compiler flags in Include/code.h
# We try to get them from dis to avoid duplication, but fall
# back to hardcoding so the dependency is optional
try:
    from dis import COMPILER_FLAG_NAMES
except ImportError:
    CO_OPTIMIZED, CO_NEWLOCALS = 0x1, 0x2
    CO_VARARGS, CO_VARKEYWORDS = 0x4, 0x8
    CO_NESTED, CO_GENERATOR, CO_NOFREE = 0x10, 0x20, 0x40
else:
    mod_dict = globals()
    for k, v in COMPILER_FLAG_NAMES.items():
        mod_dict["CO_" + v] = k

ArgInfo = namedtuple("ArgInfo", "args varargs keywords locals")


def getargvalues(frame):
    """
    Function to get information about arguments passed into a
    particular frame.

    @param frame reference to a frame object to be processed
    @type frame
    @return tuple of four things, where 'args' is a list of the argument names,
        'varargs' and 'varkw' are the names of the * and ** arguments or None
        and 'locals' is the locals dictionary of the given frame.
    @rtype ArgInfo
    @exception TypeError raised if the input parameter is not a frame object
    """
    if not isframe(frame):
        raise TypeError("{0!r} is not a frame object".format(frame))

    args, varargs, kwonlyargs, varkw = _getfullargs(frame.f_code)
    return ArgInfo(args + kwonlyargs, varargs, varkw, frame.f_locals)


def _getfullargs(co):
    """
    Protected function to get information about the arguments accepted
    by a code object.

    @param co reference to a code object to be processed
    @type code
    @return tuple of four things, where 'args' and 'kwonlyargs' are lists of
        argument names, and 'varargs' and 'varkw' are the names of the
        * and ** arguments or None.
    @rtype tuple of (list of str, list of str, list of str, list of str)
    @exception TypeError raised if the input parameter is not a code object
    """
    if not iscode(co):
        raise TypeError("{0!r} is not a code object".format(co))

    nargs = co.co_argcount
    names = co.co_varnames
    nkwargs = co.co_kwonlyargcount
    args = list(names[:nargs])
    kwonlyargs = list(names[nargs : nargs + nkwargs])

    nargs += nkwargs
    varargs = None
    if co.co_flags & CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs += 1
    varkw = None
    if co.co_flags & CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]
    return args, varargs, kwonlyargs, varkw


def formatargvalues(
    args,
    varargs,
    varkw,
    localsDict,
    formatarg=str,
    formatvarargs=lambda name: "*" + name,
    formatvarkw=lambda name: "**" + name,
    formatvalue=lambda value: "=" + repr(value),
):
    """
    Function to format an argument spec from the 4 values returned
    by getargvalues.

    @param args list of argument names
    @type list of str
    @param varargs name of the variable arguments
    @type str
    @param varkw name of the keyword arguments
    @type str
    @param localsDict reference to the local variables dictionary
    @type dict
    @param formatarg argument formatting function
    @type func
    @param formatvarargs variable arguments formatting function
    @type func
    @param formatvarkw keyword arguments formatting function
    @type func
    @param formatvalue value formating functtion
    @type func
    @return formatted call signature
    @rtype str
    """
    specs = []
    for i in range(len(args)):
        name = args[i]
        specs.append(formatarg(name) + formatvalue(localsDict[name]))
    if varargs:
        specs.append(formatvarargs(varargs) + formatvalue(localsDict[varargs]))
    if varkw:
        specs.append(formatvarkw(varkw) + formatvalue(localsDict[varkw]))
    argvalues = "(" + ", ".join(specs) + ")"
    if "__return__" in localsDict:
        argvalues += " -> " + formatvalue(localsDict["__return__"])
    return argvalues


def prepareJsonCommand(method, params):
    """
    Function to prepare a single command or response for transmission to
    the IDE.

    @param method command or response name to be sent
    @type str
    @param params dictionary of named parameters for the command or response
    @type dict
    @return prepared JSON command or response string
    @rtype str
    """
    commandDict = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }
    return json.dumps(commandDict)


###########################################################################
## Things related to monkey patching below
###########################################################################


PYTHON_NAMES = ["python", "pypy"]


def isWindowsPlatform():
    """
    Function to check, if this is a Windows platform.

    @return flag indicating Windows platform
    @rtype bool
    """
    return sys.platform.startswith(("win", "cygwin"))


def isExecutable(program):
    """
    Function to check, if the given program is executable.

    @param program program path to be checked
    @type str
    @return flag indicating an executable program
    @rtype bool
    """
    return os.access(os.path.abspath(program), os.X_OK)


def startsWithShebang(program):
    """
    Function to check, if the given program start with a Shebang line.

    @param program program path to be checked
    @type str
    @return flag indicating an existing and valid shebang line
    @rtype bool
    """
    try:
        if os.path.exists(program):
            with open(program) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        return any(
                            line.startswith("#!/usr/bin/env {0}".format(name))
                            or (line.startswith("#!") and name in line)
                            for name in PYTHON_NAMES
                        )
        else:
            return False
    except UnicodeDecodeError:
        return False
    except Exception:
        traceback.print_exc()
        return False


def isPythonProgram(program, withPath=False):
    """
    Function to check, if the given program is a Python interpreter or
    program.

    @param program program to be checked
    @type str
    @param withPath flag indicating to search the program in the executable
        search path (defaults to False)
    @type bool (optional)
    @return flag indicating a Python interpreter or program
    @rtype bool
    """
    if not program:
        return False

    prog = os.path.basename(program).lower()
    if any(pyname in prog for pyname in PYTHON_NAMES):
        return True

    if withPath:
        prog = shutil.which(program)
        if prog:
            program = prog

    return (
        not isWindowsPlatform() and isExecutable(program) and startsWithShebang(program)
    )


def removeQuotesFromArgs(args):
    """
    Function to remove quotes from the arguments list.

    @param args list of arguments
    @type list of str
    @return list of unquoted strings
    @rtype list of str
    """
    if isWindowsPlatform():
        newArgs = []
        for x in args:
            if len(x) > 1 and x.startswith('"') and x.endswith('"'):
                x = x[1:-1]
            newArgs.append(x)
        return newArgs
    else:
        return args


def quoteArgs(args):
    """
    Function to quote the given list of arguments.

    @param args list of arguments to be quoted
    @type list of str
    @return list of quoted arguments
    @rtype list of str
    """
    if isWindowsPlatform():
        quotedArgs = []
        for x in args:
            if x.startswith('"') and x.endswith('"'):
                quotedArgs.append(x)
            else:
                if " " in x:
                    x = x.replace('"', '\\"')
                    quotedArgs.append('"{0}"'.format(x))
                else:
                    quotedArgs.append(x)
        return quotedArgs
    else:
        return args


def patchArguments(debugClient, arguments, noRedirect=False, isPythonProg=False):
    """
    Function to patch the arguments given to start a program in order to
    execute it in our debugger.

    @param debugClient reference to the debug client object
    @type DebugClient
    @param arguments list of program arguments
    @type list of str
    @param noRedirect flag indicating to not redirect stdin and stdout
        (defaults to False)
    @type bool (optional)
    @param isPythonProg flag indicating a Python script (defaults to False)
    @type bool (optional)
    @return modified argument list
    @rtype list of str
    """
    if not (isPythonProg or isPythonProgram(arguments[0])):
        # it is not a Python program
        return arguments

    debugClientScript = os.path.join(os.path.dirname(__file__), "DebugClient.py")
    if debugClientScript in arguments:
        # it is already patched
        return arguments

    args = list(arguments[:])  # create a copy of the arguments list
    args = removeQuotesFromArgs(args)

    # support for shebang line
    program = os.path.basename(args[0]).lower()
    for pyname in PYTHON_NAMES:
        if pyname in program:
            break
    else:
        if (not isWindowsPlatform() and startsWithShebang(args[0])) or (
            isWindowsPlatform() and args[0].lower().endswith(".py")
        ):
            # 1. insert our interpreter as first argument if not Windows
            # 2. insert our interpreter as first argument if on Windows and
            #    it is a Python script
            args.insert(0, sys.executable)

    # extract list of interpreter arguments, i.e. all arguments before the
    # first one not starting with '-'.
    interpreter = args.pop(0)
    interpreterArgs = []
    hasCode = False
    hasScriptModule = False
    while args:
        if args[0].startswith("-"):
            if args[0] in ("-W", "-X"):
                # take two elements off the list
                interpreterArgs.append(args.pop(0))
                interpreterArgs.append(args.pop(0))
            elif args[0] == "-c":
                # -c indicates code to be executed and ends the
                # arguments list
                args.pop(0)
                hasCode = True
                break
            elif args[0] == "-m":
                # -m indicates a module to be executed as a script
                # and ends the arguments list
                args.pop(0)
                hasScriptModule = True
                break
            else:
                interpreterArgs.append(args.pop(0))
        else:
            break

    (
        wd,
        host,
        port,
        reportAllExceptions,
        tracePython,
        redirect,
        noencoding,
    ) = debugClient.startOptions[:7]

    modifiedArguments = [interpreter]
    modifiedArguments.extend(interpreterArgs)
    modifiedArguments.extend(
        [
            debugClientScript,
            "-h",
            host,
            "-p",
            str(port),
            "--no-passive",
        ]
    )

    if wd:
        modifiedArguments.extend(["-w", wd])
    if tracePython:
        modifiedArguments.append("-t")
    if noRedirect or not redirect:
        modifiedArguments.append("-n")
    if noencoding:
        modifiedArguments.append("--no-encoding")
    if debugClient.multiprocessSupport:
        modifiedArguments.append("--multiprocess")
    if reportAllExceptions:
        modifiedArguments.append("--report-exceptions")
    if hasCode:
        modifiedArguments.append("--code")
        modifiedArguments.append(args.pop(0))
    if hasScriptModule:
        modifiedArguments.append("--module")
        modifiedArguments.append(args.pop(0))
    modifiedArguments.append("--")
    # end the arguments for DebugClient

    # append the arguments for the program to be debugged
    modifiedArguments.extend(args)
    modifiedArguments = quoteArgs(modifiedArguments)

    return modifiedArguments


def stringToArgumentsWindows(args):
    """
    Function to prepare a string of arguments for Windows platform.

    @param args list of command arguments
    @type str
    @return list of command arguments
    @rtype list of str
    @exception RuntimeError raised to indicate an illegal arguments parsing
        condition
    """
    # see http://msdn.microsoft.com/en-us/library/a1y7w461.aspx
    result = []

    DEFAULT = 0
    ARG = 1
    IN_DOUBLE_QUOTE = 2

    state = DEFAULT
    backslashes = 0
    buf = ""

    argsLen = len(args)
    i = 0
    while i < argsLen:
        ch = args[i]
        if ch == "\\":
            backslashes += 1
            i += 1
            continue
        elif backslashes != 0:
            if ch == '"':
                while backslashes >= 2:
                    backslashes -= 2
                    buf += "\\"
                if backslashes == 1:
                    if state == DEFAULT:
                        state = ARG

                    buf += '"'
                    backslashes = 0
                    i += 1
                    continue
            else:
                # false alarm, treat passed backslashes literally...
                if state == DEFAULT:
                    state = ARG

                while backslashes > 0:
                    backslashes -= 1
                    buf += "\\"

        if ch in (" ", "\t"):
            if state == DEFAULT:
                # skip
                i += 1
                continue
            elif state == ARG:
                state = DEFAULT
                result.append(buf)
                buf = ""
                i += 1
                continue

        if state not in (DEFAULT, ARG, IN_DOUBLE_QUOTE):
            raise RuntimeError("Illegal condition")

        if state == IN_DOUBLE_QUOTE:
            if ch == '"':
                if i + 1 < argsLen and args[i + 1] == '"':
                    # Undocumented feature in Windows:
                    # Two consecutive double quotes inside a double-quoted
                    # argument are interpreted as a single double quote.
                    buf += '"'
                    i += 1
                elif len(buf) == 0:
                    result.append('""')
                    state = DEFAULT
                else:
                    state = ARG
            else:
                buf += ch

        else:
            if ch == '"':
                state = IN_DOUBLE_QUOTE
            else:
                state = ARG
                buf += ch

        i += 1

    if len(buf) > 0 or state != DEFAULT:
        result.append(buf)

    return result


def patchArgumentStringWindows(debugClient, argStr):
    """
    Function to patch an argument string for Windows.

    @param debugClient reference to the debug client object
    @type DebugClient
    @param argStr argument string
    @type str
    @return patched argument string
    @rtype str
    """
    args = stringToArgumentsWindows(argStr)
    if not args or not isPythonProgram(args[0]):
        return argStr

    argStr = " ".join(patchArguments(debugClient, args))
    return argStr
