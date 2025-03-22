# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2021 Detlev Offenbach <detlev@die-offenbachs.de>
# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the syntax check for JavaScript.
"""

import multiprocessing
import queue


def initService():
    """
    Initialize the service and return the entry point.

    @return the entry point for the background client
    @rtype function
    """
    return jsSyntaxCheck


def initBatchService():
    """
    Initialize the batch service and return the entry point.

    @return the entry point for the background client
    @rtype function
    """
    return jsSyntaxBatchCheck


def jsSyntaxCheck(file, codestring):
    """
    Function to check a Javascript source file for syntax errors.

    @param file source filename
    @type str
    @param codestring string containing the code to check
    @type str
    @return list of dictionaries  with the key 'error' which contain a tuple with
        details about the syntax error. Each tuple contains the file name, line
        number, column, code string and the error message.
    @rtype list of dict
    """
    return __jsSyntaxCheck(file, codestring)


def jsSyntaxBatchCheck(argumentsList, send, fx, cancelled, maxProcesses=0):
    """
    Module function to check syntax for a batch of files.

    @param argumentsList list of arguments tuples as given for jsSyntaxCheck
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

    # Submit tasks (initially two time number of processes
    tasks = len(argumentsList)
    initialTasks = 2 * NumberOfProcesses
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
        source = args[0]
        result = __jsSyntaxCheck(filename, source)
        outputQueue.put((filename, result))


def __jsSyntaxCheck(file, codestring):
    """
    Function to check a JavaScript source file for syntax errors.

    @param file source filename
    @type str
    @param codestring string containing the code to check
    @type str
    @return list of dictionaries  with the key 'error' which contain a tuple with
        details about the syntax error. Each tuple contains the file name, line
        number, column, code string and the error message.
    @rtype list of dict
    """
    if codestring:
        try:
            import esprima  # noqa: I101, I102
        except ImportError:
            error = "esprima not available. Install it via the PyPI interface."
            return [{"error": (file, 0, 0, "", error)}]

        try:
            esprima.parse(codestring, esnext=True, sourceType="module")
            # Parsing is just done to get syntax errors.
        except esprima.Error as exc:
            line = exc.lineNumber
            column = exc.column
            error = exc.message.split(":", 1)[-1].strip()

            codelines = codestring.splitlines()
            cline = min(len(codelines), line) - 1
            code = codelines[cline]

            return [{"error": (file, line, column, code, error)}]

    return [{}]
