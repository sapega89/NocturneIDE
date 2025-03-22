# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the syntax check for JSON.
"""

import json
import multiprocessing
import queue


def initService():
    """
    Initialize the service and return the entry point.

    @return the entry point for the background client
    @rtype function
    """
    return jsonSyntaxCheck


def initBatchService():
    """
    Initialize the batch service and return the entry point.

    @return the entry point for the background client
    @rtype function
    """
    return jsonSyntaxBatchCheck


def jsonSyntaxCheck(file, codestring):
    """
    Function to check a JSON source file for syntax errors.

    @param file source filename
    @type str
    @param codestring string containing the code to check
    @type str
    @return list of dictionaries  with the key 'error' which contain a tuple with
        details about the syntax error. Each tuple contains the file name, line
        number, column, code string and the error message.
    @rtype list of dict
    """
    return __jsonSyntaxCheck(file, codestring)


def jsonSyntaxBatchCheck(argumentsList, send, fx, cancelled, maxProcesses=0):
    """
    Module function to check syntax for a batch of files.

    @param argumentsList list of arguments tuples as given for jsonSyntaxCheck
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
        source = args[0]
        result = __jsonSyntaxCheck(filename, source)
        outputQueue.put((filename, result))


def __jsonSyntaxCheck(file, codestring):
    """
    Function to check a JSON source file for syntax errors.

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
            json.loads(codestring)
        except json.JSONDecodeError as exc:
            line = exc.lineno
            column = exc.colno
            error = exc.msg

            cline = min(len(codestring.splitlines()), int(line)) - 1
            code = codestring.splitlines()[cline]

            return [{"error": (file, line, column, code, error)}]

    return [{}]
