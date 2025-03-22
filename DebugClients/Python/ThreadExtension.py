# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an import hook patching thread modules to get debugged too.
"""

import _thread
import contextlib
import os
import sys
import threading

from DebugBase import DebugBase

_qtThreadNumber = 1


class ThreadExtension:
    """
    Class implementing the thread support for the debugger.

    Provides methods for intercepting thread creation, retrieving the running
    threads and their name and state.
    """

    def __init__(self):
        """
        Constructor
        """
        self.threadNumber = 1
        self._original_start_new_thread = None

        self.clientLock = threading.RLock()

        # dictionary of all threads running {id: DebugBase}
        self.threads = {_thread.get_ident(): self}

        # the "current" thread, basically for variables view
        self.currentThread = self
        # the thread we are at a breakpoint continuing at next command
        self.currentThreadExec = self

        # special objects representing the main scripts thread and frame
        self.mainThread = self

    def attachThread(self, target=None, args=None, kwargs=None, mainThread=False):
        """
        Public method to setup a standard thread for DebugClient to debug.

        If mainThread is True, then we are attaching to the already
        started mainthread of the app and the rest of the args are ignored.

        @param target start function of the target thread (i.e. the user
            code)
        @type function
        @param args arguments to pass to target
        @type list of Any
        @param kwargs keyword arguments to pass to target
        @type dict of Any
        @param mainThread True, if we are attaching to the already started
            mainthread of the app
        @type bool
        @return identifier of the created thread
        @rtype int
        """
        if kwargs is None:
            kwargs = {}

        if mainThread:
            ident = _thread.get_ident()
            name = "MainThread"
            newThread = self.mainThread
            newThread.isMainThread = True
            if self.debugging:
                sys.setprofile(newThread.profile)

        else:
            newThread = DebugBase(self)
            ident = self._original_start_new_thread(
                newThread.bootstrap, (target, args, kwargs)
            )
            name = "Thread-{0}".format(self.threadNumber)
            self.threadNumber += 1

        newThread.id = ident
        newThread.name = name

        self.threads[ident] = newThread

        return ident

    def threadTerminated(self, threadId):
        """
        Public method called when a DebugThread has exited.

        @param threadId id of the DebugThread that has exited
        @type int
        """
        self.lockClient()
        try:
            with contextlib.suppress(KeyError):
                del self.threads[threadId]
        finally:
            self.unlockClient()

    def lockClient(self, blocking=True):
        """
        Public method to acquire the lock for this client.

        @param blocking flag to indicating a blocking lock
        @type bool
        @return flag indicating successful locking
        @rtype bool
        """
        return self.clientLock.acquire(blocking)

    def unlockClient(self):
        """
        Public method to release the lock for this client.
        """
        with contextlib.suppress(RuntimeError):
            self.clientLock.release()

    def setCurrentThread(self, threadId):
        """
        Public method to set the current thread.

        @param threadId the id the current thread should be set to.
        @type int
        """
        try:
            self.lockClient()
            if threadId is None:
                self.currentThread = None
            else:
                self.currentThread = self.threads.get(threadId)
        finally:
            self.unlockClient()

    def dumpThreadList(self):
        """
        Public method to send the list of threads.
        """
        self.updateThreadList()

        threadList = []
        currentId = _thread.get_ident()
        # update thread names set by user (threading.setName)
        threadNames = {t.ident: t.name for t in threading.enumerate()}

        for threadId, thd in self.threads.items():
            d = {"id": threadId}
            try:
                d["name"] = threadNames.get(threadId, thd.name)
                d["broken"] = thd.isBroken
                d["except"] = thd.isException
            except Exception:
                d["name"] = "UnknownThread"
                d["broken"] = False
                d["except"] = False

            threadList.append(d)

        self.sendJsonCommand(
            "ResponseThreadList",
            {
                "currentID": currentId,
                "threadList": threadList,
            },
        )

    def getExecutedFrame(self, frame):
        """
        Public method to return the currently executed frame.

        @param frame the current frame
        @type frame object
        @return the frame which is excecuted (without debugger frames)
        @rtype frame object
        """
        # to get the currently executed frame, skip all frames belonging to the
        # debugger
        while frame is not None:
            baseName = os.path.basename(frame.f_code.co_filename)
            if not baseName.startswith(
                (
                    "DebugClientBase.py",
                    "DebugBase.py",
                    "AsyncFile.py",
                    "ThreadExtension.py",
                )
            ):
                break
            frame = frame.f_back

        return frame

    def updateThreadList(self):
        """
        Public method to update the list of running threads.
        """
        frames = sys._current_frames()
        for threadId, frame in frames.items():
            # skip our own timer thread
            if frame.f_code.co_name == "__eventPollTimer":
                continue

            # Unknown thread
            if threadId not in self.threads:
                newThread = DebugBase(self)
                name = "Thread-{0}".format(self.threadNumber)
                self.threadNumber += 1

                newThread.id = threadId
                newThread.name = name
                self.threads[threadId] = newThread

            # adjust current frame
            if "__pypy__" not in sys.builtin_module_names:
                # Don't update with None
                currentFrame = self.getExecutedFrame(frame)
                if (
                    currentFrame is not None
                    and self.threads[threadId].isBroken is False
                ):
                    self.threads[threadId].currentFrame = currentFrame

        # Clean up obsolet because terminated threads
        self.threads = {
            id_: thrd for id_, thrd in self.threads.items() if id_ in frames
        }

    #######################################################################
    ## Methods below deal with patching various modules to support
    ## debugging of threads.
    #######################################################################

    def patchPyThread(self, module):
        """
        Public method to patch Python _thread module.

        @param module reference to the imported module to be patched
        @type module
        """
        # make thread hooks available to system
        self._original_start_new_thread = module.start_new_thread
        module.start_new_thread = self.attachThread

    def patchGreenlet(self, module):
        """
        Public method to patch the 'greenlet' module.

        @param module reference to the imported module to be patched
        @type module
        @return flag indicating that the module was processed
        @rtype bool
        """
        # Check for greenlet.settrace
        if hasattr(module, "settrace"):
            DebugBase.pollTimerEnabled = False
            return True
        return False

    def patchPyThreading(self, module):
        """
        Public method to patch the Python threading module.

        @param module reference to the imported module to be patched
        @type module
        """
        # _debugClient as a class attribute can't be accessed in following
        # class. Therefore we need a global variable.
        _debugClient = self

        def _bootstrap(self, run):
            """
            Bootstrap for threading, which reports exceptions correctly.

            @param run the run method of threading.Thread
            @type method pointer
            """
            newThread = DebugBase(_debugClient)
            newThread.name = self.name

            _debugClient.threads[self.ident] = newThread
            _debugClient.dumpThreadList()

            # see DebugBase.bootstrap
            sys.settrace(newThread.trace_dispatch)
            try:
                run()
            except Exception:
                excinfo = sys.exc_info()
                newThread.user_exception(excinfo, True)
            finally:
                sys.settrace(None)
                _debugClient.dumpThreadList()

        class ThreadWrapper(module.Thread):
            """
            Wrapper class for threading.Thread.
            """

            def __init__(self, *args, **kwargs):
                """
                Constructor
                """
                # Overwrite the provided run method with our own, to
                # intercept the thread creation by threading.Thread
                self.run = lambda s=self, run=self.run: _bootstrap(s, run)

                super().__init__(*args, **kwargs)

        module.Thread = ThreadWrapper

        # Special handling of threading.(_)Timer
        timer = module.Timer

        class TimerWrapper(timer, ThreadWrapper):
            """
            Wrapper class for threading.(_)Timer.
            """

            def __init__(self, interval, function, *args, **kwargs):
                """
                Constructor
                """
                super().__init__(interval, function, *args, **kwargs)

        module.Timer = TimerWrapper

        # Special handling of threading._DummyThread
        class DummyThreadWrapper(module._DummyThread, ThreadWrapper):
            """
            Wrapper class for threading._DummyThread.
            """

            def __init__(self, *args, **kwargs):
                """
                Constructor
                """
                super().__init__(*args, **kwargs)

        module._DummyThread = DummyThreadWrapper

    def patchQThread(self, module):
        """
        Public method to patch the QtCore module's QThread.

        @param module reference to the imported module to be patched
        @type module
        """
        # _debugClient as a class attribute can't be accessed in following
        # class. Therefore we need a global variable.
        _debugClient = self

        def _bootstrapQThread(self, run):
            """
            Bootstrap for QThread, which reports exceptions correctly.

            @param run the run method of *.QThread
            @type method pointer
            """
            global _qtThreadNumber

            newThread = DebugBase(_debugClient)
            ident = _thread.get_ident()
            name = "QtThread-{0}".format(_qtThreadNumber)

            _qtThreadNumber += 1

            newThread.id = ident
            newThread.name = name

            _debugClient.threads[ident] = newThread
            _debugClient.dumpThreadList()

            # see DebugBase.bootstrap
            sys.settrace(newThread.trace_dispatch)
            try:
                run()
            except SystemExit:
                # *.QThreads doesn't like SystemExit
                pass
            except Exception:
                excinfo = sys.exc_info()
                newThread.user_exception(excinfo, True)
            finally:
                sys.settrace(None)
                _debugClient.dumpThreadList()

        class QThreadWrapper(module.QThread):
            """
            Wrapper class for *.QThread.
            """

            def __init__(self, *args, **kwargs):
                """
                Constructor
                """
                # Overwrite the provided run method with our own, to
                # intercept the thread creation by Qt
                self.run = lambda s=self, run=self.run: (_bootstrapQThread(s, run))

                super().__init__(*args, **kwargs)

        class QRunnableWrapper(module.QRunnable):
            """
            Wrapper class for *.QRunnable.
            """

            def __init__(self, *args, **kwargs):
                """
                Constructor
                """
                # Overwrite the provided run method with our own, to
                # intercept the thread creation by Qt
                self.run = lambda s=self, run=self.run: (_bootstrapQThread(s, run))

                super().__init__(*args, **kwargs)

        module.QThread = QThreadWrapper
        module.QRunnable = QRunnableWrapper
