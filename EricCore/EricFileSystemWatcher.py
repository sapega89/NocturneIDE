# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a QFileSystemWatcher replacement based on the 'watchdog' package.
"""

import os
import sys

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from watchdog.events import EVENT_TYPE_CLOSED, EVENT_TYPE_OPENED, FileSystemEventHandler

if sys.platform == "darwin":
    from watchdog.observers.kqueue import KqueueObserver as Observer
else:
    from watchdog.observers import Observer


class _EricFileSystemEventHandler(QObject, FileSystemEventHandler):
    """
    Class implementing a QObject based file system event handler for watchdog.

    @signal directoryChanged(path: str) emitted when the directory at a given path is
        modified or removed from disk
    @signal directoryCreated(path: str) emitted when a directory is created
    @signal directoryDeleted(path: str) emitted when a directory is removed from disk
    @signal directoryModified(path: str) emitted when a directory is modified
    @signal directoryMoved(srcPath: str, dstPath: str) emitted when the directory at a
        given source path is renamed or moved to destination path
    @signal fileChanged(path: str) emitted when the file at a given path is modified
        or removed from disk
    @signal fileCreated(path: str) emitted when a file is created
    @signal fileDeleted(path: str) emitted when a file is removed from disk
    @signal fileModified(path: str) emitted when a file is modified
    @signal fileMoved(srcPath: str, dstPath: str) emitted when the file at a
        given source path is renamed or moved to destination path
    """

    directoryChanged = pyqtSignal(str)  # compatibility with QFileSystemWatcher
    directoryCreated = pyqtSignal(str)
    directoryDeleted = pyqtSignal(str)
    directoryModified = pyqtSignal(str)
    directoryMoved = pyqtSignal(str, str)

    fileChanged = pyqtSignal(str)  # compatibility with QFileSystemWatcher
    fileCreated = pyqtSignal(str)
    fileDeleted = pyqtSignal(str)
    fileModified = pyqtSignal(str)
    fileMoved = pyqtSignal(str, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent=parent)

    def on_any_event(self, event):
        """
        Private method handling any file system event.

        @param event event to be handled
        @type watchdog.events.FileSystemEvent
        """
        super().on_any_event(event)

        if event.event_type not in (EVENT_TYPE_CLOSED, EVENT_TYPE_OPENED):
            if event.is_directory:
                self.directoryChanged.emit(event.src_path)
            else:
                self.fileChanged.emit(event.src_path)

    def on_created(self, event):
        """
        Private method to handle a creation event.

        @param event event to be handled
        @type watchdog.events.FileCreatedEvent or watchdog.event.DirCreatedEvent
        """
        super().on_created(event)

        if event.is_directory:
            self.directoryCreated.emit(event.src_path)
        else:
            self.fileCreated.emit(event.src_path)

    def on_deleted(self, event):
        """
        Private method to handle a deletion event.

        @param event event to be handled
        @type watchdog.events.FileDeletedEvent or watchdog.event.DirDeletedEvent
        """
        super().on_deleted(event)

        if event.is_directory:
            self.directoryDeleted.emit(event.src_path)
        else:
            self.fileDeleted.emit(event.src_path)

    def on_modified(self, event):
        """
        Private method to handle a modification event.

        @param event event to be handled
        @type watchdog.events.FileModifiedEvent or watchdog.event.DirModifiedEvent
        """
        super().on_modified(event)

        if event.is_directory:
            self.directoryModified.emit(event.src_path)
        else:
            self.fileModified.emit(event.src_path)

    def on_moved(self, event):
        """
        Private method to handle a move or rename event.

        @param event event to be handled
        @type watchdog.events.FileMovedEvent or watchdog.event.DirMovedEvent
        """
        super().on_moved(event)

        if event.is_directory:
            self.directoryMoved.emit(event.src_path, event.dest_path)
        else:
            self.fileMoved.emit(event.src_path, event.dest_path)


class EricFileSystemWatcher(QObject):
    """
    Class implementing a file system monitor based on the 'watchdog' package as a
    replacement for 'QFileSystemWatcher'.

    This class has more fine grained signaling capability compared to
    QFileSystemWatcher. The 'directoryChanged' and 'fileChanged' signals are emitted
    to keep the API compatible with QFileSystemWatcher.

    @signal directoryChanged(path: str) emitted when the directory at a given path is
        modified or removed from disk
    @signal directoryCreated(path: str) emitted when a directory is created
    @signal directoryDeleted(path: str) emitted when a directory is removed from disk
    @signal directoryModified(path: str) emitted when a directory is modified
    @signal directoryMoved(srcPath: str, dstPath: str) emitted when the directory at a
        given source path is renamed or moved to destination path
    @signal fileChanged(path: str) emitted when the file at a given path is modified
        or removed from disk
    @signal fileCreated(path: str) emitted when a file is created
    @signal fileDeleted(path: str) emitted when a file is removed from disk
    @signal fileModified(path: str) emitted when a file is modified
    @signal fileMoved(srcPath: str, dstPath: str) emitted when the file at a
        given source path is renamed or moved to destination path
    @signal error(errno: int, errmsg: str) emitted to indicate an OS error
    """

    directoryChanged = pyqtSignal(str)  # compatibility with QFileSystemWatcher
    directoryCreated = pyqtSignal(str)
    directoryDeleted = pyqtSignal(str)
    directoryModified = pyqtSignal(str)
    directoryMoved = pyqtSignal(str, str)

    fileChanged = pyqtSignal(str)  # compatibility with QFileSystemWatcher
    fileCreated = pyqtSignal(str)
    fileDeleted = pyqtSignal(str)
    fileModified = pyqtSignal(str)
    fileMoved = pyqtSignal(str, str)

    error = pyqtSignal(int, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent=parent)

        self.__paths = {}
        # key: file/directory path, value: tuple with created watch and monitor count

        self.__eventHandler = _EricFileSystemEventHandler(parent=self)
        self.__eventHandler.directoryChanged.connect(self.__directoryChanged)
        self.__eventHandler.directoryCreated.connect(self.directoryCreated)
        self.__eventHandler.directoryDeleted.connect(self.directoryDeleted)
        self.__eventHandler.directoryModified.connect(self.directoryModified)
        self.__eventHandler.directoryMoved.connect(self.directoryMoved)
        self.__eventHandler.fileChanged.connect(self.__fileChanged)
        self.__eventHandler.fileCreated.connect(self.fileCreated)
        self.__eventHandler.fileDeleted.connect(self.fileDeleted)
        self.__eventHandler.fileModified.connect(self.fileModified)
        self.__eventHandler.fileMoved.connect(self.fileMoved)

        self.__observer = Observer()
        self.__observer.start()

    def __del__(self):
        """
        Special method called when an instance object is about to be destroyed.
        """
        self.shutdown()

    @pyqtSlot(str)
    def __directoryChanged(self, path):
        """
        Private slot handling any change of a directory at a given path.

        It emits the signal 'directoryChanged', if the path is in the list of
        watched paths. This behavior is compatible with the QFileSystemWatcher signal
        of identical name.

        @param path path name of the changed directory
        @type str
        """
        if path in self.__paths:
            self.directoryChanged.emit(path)

    @pyqtSlot(str)
    def __fileChanged(self, path):
        """
        Private slot handling any change of a file at a given path.

        It emits the signal 'fileChanged', if the path is in the list of
        watched paths. This behavior is compatible with the QFileSystemWatcher signal
        of identical name.

        @param path path name of the changed file
        @type str
        """
        if path in self.__paths:
            self.fileChanged.emit(path)

    def addPath(self, path, recursive=False):
        """
        Public method to add the given path to the list of watched paths.

        If the given path is a directory, a recursive watch may be requested.
        Otherwise only the given directory is watched for changes but none of its
        subdirectories.

        The path is not added, if it does not exist or if it is already being monitored
        by the file system watcher.

        @param path file or directory path to be added to the watched paths
        @type str
        @param recursive flag indicating a watch for the complete tree rooted at the
            given path (for directory paths only) (defaults to False)
        @type bool (optional)
        @return flag indicating a successful creation of a watch for the given path
        @rtype bool
        """
        if os.path.exists(path) and self.__observer is not None:
            try:
                self.__paths[path][1] += 1
                return True
            except KeyError:
                try:
                    watch = self.__observer.schedule(
                        self.__eventHandler,
                        path,
                        recursive=recursive and os.path.isdir(path),
                    )
                    if watch is not None:
                        self.__paths[watch.path] = [watch, 1]
                        return True
                except OSError as err:
                    self.error.emit(err.errno, err.strerror)

        return False

    def addPaths(self, paths, recursive=False):
        """
        Public method to add each path of the given list to the file system watched.

        If a path of the given paths list is a directory, a recursive watch may be
        requested. Otherwise only the given directory is watched for changes but none
        of its subdirectories. This applies to all directory paths of the given list.

        A path of the list is not added, if it does not exist or if it is already being
        monitored by the file system watcher.

        @param paths list of file or directory paths to be added to the watched paths
        @type list of str
        @param recursive flag indicating a watch for the complete tree rooted at the
            given path (for directory paths only) (defaults to False)
        @type bool (optional)
        @return list of paths that could not be added to the list of monitored paths
        @rtype list of str
        """
        failedPaths = []

        for path in paths:
            ok = self.addPath(path, recursive=recursive)
            if not ok:
                failedPaths.append(path)

        return failedPaths

    def removePath(self, path):
        """
        Public method to remove a given path from the list of monitored paths.

        @param path directory or file path to be removed
        @type str
        @return flag indicating a successful removal. The only reason for a failure is,
            if the given path is not currently being monitored.
        @rtype bool
        """
        try:
            self.__paths[path][1] -= 1
            if self.__paths[path][1] == 0:
                watch, _ = self.__paths.pop(path)
                if self.__observer is not None:
                    self.__observer.unschedule(watch)
            return True
        except KeyError:
            return False

    def removePaths(self, paths):
        """
        Public method to remove the specified paths from the list of monitored paths.

        @param paths list of directory or file paths to be removed
        @type list of str
        @return list of paths that could not be removed from the list of monitored paths
        @rtype list of str
        """
        failedPaths = []

        for path in paths:
            ok = self.removePath(path)
            if not ok:
                failedPaths.append(path)

        return failedPaths

    def directories(self):
        """
        Public method to return a list of paths to directories that are being watched.

        @return list of watched directory paths
        @rtype list of str
        """
        return [p for p in self.__paths if os.path.isdir(p)]

    def files(self):
        """
        Public method to return a list of paths to files that are being watched.

        @return list of watched file paths
        @rtype list of str
        """
        return [p for p in self.__paths if os.path.isfile(p)]

    def paths(self):
        """
        Public method to return a list of paths that are being watched.

        @return list of all watched paths
        @rtype list of str
        """
        return list(self.__paths.keys())

    def shutdown(self):
        """
        Public method to shut down the file system watcher instance.

        This needs to be done in order to stop the monitoring threads doing their
        work in the background. If this method was not called explicitly when the
        instance is about to be destroyed, the special method '__del__' will do that.
        """
        if self.__observer is not None:
            self.__observer.stop()
            self.__observer.join()
            self.__observer = None


_GlobalFileSystemWatcher = None


def instance():
    """
    Function to get a reference to the global file system monitor object.

    If the global file system monitor does not exist yet, it will be created
    automatically.

    @return reference to the global file system monitor object
    @rtype EricFileSystemWatcher
    """
    global _GlobalFileSystemWatcher

    if _GlobalFileSystemWatcher is None:
        _GlobalFileSystemWatcher = EricFileSystemWatcher()

    return _GlobalFileSystemWatcher
