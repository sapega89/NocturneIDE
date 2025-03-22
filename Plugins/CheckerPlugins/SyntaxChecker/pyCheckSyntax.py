# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the syntax check for Python 3.
"""

import ast
import builtins
import contextlib
import multiprocessing
import queue
import re
import traceback
import warnings

with contextlib.suppress(ImportError):
    from pyflakes.checker import Checker
    from pyflakes.messages import ImportStarUsage, ImportStarUsed

VcsConflictMarkerRegExpList = (
    re.compile(
        r"""^<<<<<<< .*?\|\|\|\|\|\|\| .*?=======.*?>>>>>>> .*?$""",
        re.MULTILINE | re.DOTALL,
    ),
    re.compile(r"""^<<<<<<< .*?=======.*?>>>>>>> .*?$""", re.MULTILINE | re.DOTALL),
)


def initService():
    """
    Initialize the service and return the entry point.

    @return the entry point for the background client
    @rtype function
    """
    return pySyntaxAndPyflakesCheck


def initBatchService():
    """
    Initialize the batch service and return the entry point.

    @return the entry point for the background client
    @rtype function
    """
    return pySyntaxAndPyflakesBatchCheck


def extractLineFlags(line, startComment="#", endComment="", flagsLine=False):
    """
    Function to extract flags starting and ending with '__' from a line
    comment.

    @param line line to extract flags from
    @type str
    @param startComment string identifying the start of the comment
    @type str
    @param endComment string identifying the end of a comment
    @type str
    @param flagsLine flag indicating to check for a flags only line
    @type bool
    @return list containing the extracted flags
    @rtype list of str
    """
    flags = []

    if not flagsLine or (flagsLine and line.strip().startswith(startComment)):
        pos = line.rfind(startComment)
        if pos >= 0:
            comment = line[pos + len(startComment) :].strip()
            if endComment:
                endPos = line.rfind(endComment)
                if endPos >= 0:
                    comment = comment[:endPos]
            flags = [
                f.strip()
                for f in comment.split()
                if (f.startswith("__") and f.endswith("__"))
            ]
            flags += [
                f.strip().lower() for f in comment.split() if f in ("noqa", "NOQA")
            ]
    return flags


def pySyntaxAndPyflakesCheck(
    filename,
    codestring,
    checkFlakes=True,
    ignoreStarImportWarnings=False,
    additionalBuiltins=None,
):
    """
    Function to compile one Python source file to Python bytecode
    and to perform a pyflakes check.

    @param filename source filename
    @type str
    @param codestring string containing the code to compile
    @type str
    @param checkFlakes flag indicating to do a pyflakes check
    @type bool
    @param ignoreStarImportWarnings flag indicating to ignore 'star import' warnings
    @type bool
    @param additionalBuiltins list of names pyflakes should consider as builtins
    @type list of str
    @return list of dictionaries with the keys 'error', 'py_warnings' and 'warnings'
        which contain a tuple with details about the syntax error or a list of
        tuples with details about Python warnings and PyFlakes warnings. Each tuple
        contains the file name, line number, column, code string (only for syntax
        errors), the message and an optional list with arguments for the message.
    @rtype list of dict
    """
    return __pySyntaxAndPyflakesCheck(
        filename, codestring, checkFlakes, ignoreStarImportWarnings, additionalBuiltins
    )


def pySyntaxAndPyflakesBatchCheck(argumentsList, send, fx, cancelled, maxProcesses=0):
    """
    Module function to check syntax for a batch of files.

    @param argumentsList list of arguments tuples as given for pySyntaxAndPyflakesCheck
    @type list
    @param send reference to send function
    @type function
    @param fx registered service name
    @type str
    @param cancelled reference to function checking for a cancellation
    @type function
    @param maxProcesses number of processes to be used
    @type int
    """
    if maxProcesses == 0:
        # determine based on CPU count
        try:
            NumberOfProcesses = multiprocessing.cpu_count()
            if NumberOfProcesses >= 1:
                NumberOfProcesses -= 1
        except NotImplementedError:
            NumberOfProcesses = 1
    else:
        NumberOfProcesses = maxProcesses

    # Create queues
    taskQueue = multiprocessing.Queue()
    doneQueue = multiprocessing.Queue()

    # Submit tasks (initially two times the number of processes)
    tasks = len(argumentsList)
    initialTasks = min(2 * NumberOfProcesses, tasks)
    for _ in range(initialTasks):
        taskQueue.put(argumentsList.pop(0))

    # Start worker processes
    workers = [
        multiprocessing.Process(target=workerTask, args=(taskQueue, doneQueue))
        for _ in range(NumberOfProcesses)
    ]
    for worker in workers:
        worker.start()

    # Get and send results
    for _ in range(tasks):
        resultSent = False
        wasCancelled = False

        while not resultSent:
            try:
                # get result (waiting max. 3 seconds and send it to frontend
                filename, result = doneQueue.get()
                send(fx, filename, result)
                resultSent = True
            except queue.Empty:
                # ignore empty queue, just carry on
                if cancelled():
                    wasCancelled = True
                    break

        if wasCancelled or cancelled():
            # just exit the loop ignoring the results of queued tasks
            break

        if argumentsList:
            taskQueue.put(argumentsList.pop(0))

    # Tell child processes to stop
    for _ in range(NumberOfProcesses):
        taskQueue.put("STOP")

    for worker in workers:
        worker.join()
        worker.close()

    taskQueue.close()
    doneQueue.close()


def workerTask(inputQueue, outputQueue):
    """
    Module function acting as the parallel worker for the syntax check.

    @param inputQueue input queue
    @type multiprocessing.Queue
    @param outputQueue output queue
    @type multiprocessing.Queue
    """
    for filename, args in iter(inputQueue.get, "STOP"):
        source, checkFlakes, ignoreStarImportWarnings, additionalBuiltins = args
        result = __pySyntaxAndPyflakesCheck(
            filename, source, checkFlakes, ignoreStarImportWarnings, additionalBuiltins
        )
        outputQueue.put((filename, result))


def __pySyntaxAndPyflakesCheck(
    filename,
    codestring,
    checkFlakes=True,
    ignoreStarImportWarnings=False,
    additionalBuiltins=None,
):
    """
    Function to compile one Python source file to Python bytecode
    and to perform a pyflakes check.

    @param filename source filename
    @type str
    @param codestring string containing the code to compile
    @type str
    @param checkFlakes flag indicating to do a pyflakes check
    @type bool
    @param ignoreStarImportWarnings flag indicating to
        ignore 'star import' warnings
    @type bool
    @param additionalBuiltins list of names pyflakes should consider as builtins
    @type list of str
    @return list of dictionaries with the keys 'error', 'py_warnings' and 'warnings'
        which contain a tuple with details about the syntax error or a list of
        tuples with details about Python warnings and PyFlakes warnings. Each tuple
        contains the file name, line number, column, code string (only for syntax
        errors), the message and an optional list with arguments for the message.
    @rtype list of dict
    """
    if codestring:
        errorDict = {}
        pyWarnings = []

        def showwarning(
            message,
            category,
            filename,
            lineno,
            file=None,  # noqa: U100
            line=None,  # noqa: U100
        ):
            pyWarnings.append(
                (
                    filename,
                    lineno,
                    0,
                    "",
                    "{0}: {1}".format(category.__name__, message),
                )
            )

        warnings.showwarning = showwarning
        warnings.filterwarnings("always")

        try:
            # Check for VCS conflict markers
            for conflictMarkerRe in VcsConflictMarkerRegExpList:
                conflict = conflictMarkerRe.search(codestring)
                if conflict is not None:
                    start, _i = conflict.span()
                    lineindex = 1 + codestring.count("\n", 0, start)
                    return [
                        {
                            "error": (
                                filename,
                                lineindex,
                                0,
                                "",
                                "VCS conflict marker found",
                            )
                        }
                    ]

            if filename.endswith(".ptl"):
                try:
                    import quixote.ptl_compile  # __IGNORE_WARNING_I10__
                except ImportError:
                    return [
                        {"error": (filename, 0, 0, "", "Quixote plugin not found.")}
                    ]
                template = quixote.ptl_compile.Template(codestring, filename)
                template.compile()
            else:
                module = builtins.compile(
                    codestring, filename, "exec", ast.PyCF_ONLY_AST
                )
        except SyntaxError as detail:
            index = 0
            code = ""
            error = ""
            lines = traceback.format_exception_only(SyntaxError, detail)
            match = re.match(
                r'\s*File "(.+)", line (\d+)', lines[0].replace("<string>", filename)
            )
            if match is not None:
                fn, line = match.group(1, 2)
                if lines[1].startswith("SyntaxError:"):
                    error = re.match("SyntaxError: (.+)", lines[1]).group(1)
                elif lines[1].startswith("IndentationError:"):
                    error = re.match("IndentationError: (.+)", lines[1]).group(1)
                elif lines[1].startswith("TabError:"):
                    error = re.match("TabError: (.+)", lines[1]).group(1)
                else:
                    code = re.match("(.+)", lines[1]).group(1)
                    for seLine in lines[2:]:
                        if seLine.startswith("SyntaxError:"):
                            error = re.match("SyntaxError: (.+)", seLine).group(1)
                        elif seLine.startswith("IndentationError:"):
                            error = re.match("IndentationError: (.+)", seLine).group(1)
                        elif seLine.startswith("TabError:"):
                            error = re.match("TabError: (.+)", seLine).group(1)
                        elif seLine.rstrip().endswith("^"):
                            index = len(seLine.rstrip()) - 4
            else:
                fn = detail.filename
                line = detail.lineno or 1
                error = detail.msg
            errorDict = {"error": (fn, int(line), index, code.strip(), error)}
        except ValueError as detail:
            try:
                fn = detail.filename
                line = detail.lineno
                error = detail.msg
            except AttributeError:
                fn = filename
                line = 1
                error = str(detail)
            errorDict = {"error": (fn, line, 0, "", error)}
        except Exception as detail:
            with contextlib.suppress(AttributeError):
                fn = detail.filename
                line = detail.lineno
                error = detail.msg
                errorDict = {"error": (fn, line, 0, "", error)}
        finally:
            warnings.resetwarnings()

        # return the syntax error, if one was detected
        if errorDict:
            return [errorDict]

        # pyflakes
        results = []
        if checkFlakes:
            lines = codestring.splitlines()
            try:
                flakesWarnings = Checker(
                    module, filename, builtins=additionalBuiltins, withDoctest=True
                )
                flakesWarnings.messages.sort(key=lambda a: a.lineno)
                for flakesWarning in flakesWarnings.messages:
                    if ignoreStarImportWarnings and isinstance(
                        flakesWarning, (ImportStarUsed, ImportStarUsage)
                    ):
                        continue

                    _fn, lineno, col, message, msg_args = flakesWarning.getMessageData()
                    lineFlags = extractLineFlags(lines[lineno - 1].strip())
                    with contextlib.suppress(IndexError):
                        lineFlags += extractLineFlags(
                            lines[lineno].strip(), flagsLine=True
                        )
                    if (
                        "__IGNORE_WARNING__" not in lineFlags
                        and "__IGNORE_FLAKES_WARNING__" not in lineFlags
                        and "noqa" not in lineFlags
                    ):
                        results.append((_fn, lineno, col, "", message, msg_args))
            except SyntaxError as err:
                msg = err.text.strip() if err.text.strip() else err.msg
                results.append((filename, err.lineno, 0, "FLAKES_ERROR", msg, []))

        return [{"py_warnings": pyWarnings, "warnings": results}]

    else:
        return [{}]
