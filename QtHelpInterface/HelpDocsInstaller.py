# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a thread class populating and updating the QtHelp
documentation database.
"""

import datetime
import pathlib

from PyQt6.QtCore import QLibraryInfo, QMutex, QThread, pyqtSignal
from PyQt6.QtHelp import QHelpEngineCore

from eric7.Globals import getConfig
from eric7.SystemUtilities import QtUtilities


class HelpDocsInstaller(QThread):
    """
    Class implementing the worker thread populating and updating the QtHelp
    documentation database.

    @signal errorMessage(str) emitted, if an error occurred during
        the installation of the documentation
    @signal docsInstalled(bool) emitted after the installation has finished
    """

    errorMessage = pyqtSignal(str)
    docsInstalled = pyqtSignal(bool)

    def __init__(self, collection):
        """
        Constructor

        @param collection full pathname of the collection file
        @type str
        """
        super().__init__()

        self.__abort = False
        self.__collection = collection
        self.__mutex = QMutex()

    def stop(self):
        """
        Public slot to stop the installation procedure.
        """
        if not self.isRunning():
            return

        self.__mutex.lock()
        self.__abort = True
        self.__mutex.unlock()
        self.wait()

    def installDocs(self):
        """
        Public method to start the installation procedure.
        """
        self.start(QThread.Priority.LowPriority)

    def run(self):
        """
        Public method executed by the thread.
        """
        engine = QHelpEngineCore(self.__collection)
        changes = False

        qt5Docs = [
            "activeqt",
            "qdoc",
            "qmake",
            "qt3d",
            "qt3drenderer",
            "qtandroidextras",
            "qtassistant",
            "qtbluetooth",
            "qtcanvas3d",
            "qtcharts",
            "qtcmake",
            "qtconcurrent",
            "qtcore",
            "qtdatavis3d",
            "qtdatavisualization",
            "qtdbus",
            "qtdesigner",
            "qtdistancefieldgenerator",
            "qtdoc",
            "qtenginio",
            "qtenginiooverview",
            "qtenginoqml",
            "qtgamepad",
            "qtgraphicaleffects",
            "qtgui",
            "qthelp",
            "qthttpserver",
            "qtimageformats",
            "qtlabscalendar",
            "qtlabsplatform",
            "qtlabscontrols",
            "qtlinguist",
            "qtlocation",
            "qtlottieanimation",
            "qtmacextras",
            "qtmultimedia",
            "qtmultimediawidgets",
            "qtnetwork",
            "qtnetworkauth",
            "qtnfc",
            "qtopengl",
            "qtpdf",
            "qtplatformheaders",
            "qtpositioning",
            "qtprintsupport",
            "qtpurchasing",
            "qtqml",
            "qtqmlcore",
            "qtqmlmodels",
            "qtqmltest",
            "qtqmlworkerscript",
            "qtqmlxmllistmodel",
            "qtquick",
            "qtquick3d",
            "qtquick3dphysics",
            "qtquickcontrols",
            "qtquickcontrols1",
            "qtquickdialogs",
            "qtquickextras",
            "qtquicklayouts",
            "qtquicktimeline",
            "qtremoteobjects",
            "qtscript",
            "qtscripttools",
            "qtscxml",
            "qtsensors",
            "qtserialbus",
            "qtserialport",
            "qtshadertools",
            "qtspatialaudio",
            "qtspeech",
            "qtsql",
            "qtstatemachine",
            "qtsvg",
            "qttest",
            "qttestlib",
            "qtuitools",
            "qtvirtualkeyboard",
            "qtwaylandcompositor",
            "qtwebchannel",
            "qtwebengine",
            "qtwebenginewidgets",
            "qtwebkit",
            "qtwebkitexamples",
            "qtwebsockets",
            "qtwebview",
            "qtwidgets",
            "qtwinextras",
            "qtx11extras",
            "qtxml",
            "qtxmlpatterns",
        ]
        for qtDocs, version in [(qt5Docs, 5)]:
            for doc in qtDocs:
                changes |= self.__installQtDoc(doc, version, engine)
                self.__mutex.lock()
                if self.__abort:
                    engine = None
                    self.__mutex.unlock()
                    return
                self.__mutex.unlock()

        changes |= self.__installEric7Doc(engine)
        engine = None
        del engine
        self.docsInstalled.emit(changes)

    def __installQtDoc(self, name, version, engine):
        """
        Private method to install/update a Qt help document.

        @param name name of the Qt help document
        @type str
        @param version Qt version of the help documents
        @type int
        @param engine reference to the help engine
        @type QHelpEngineCore
        @return flag indicating success
        @rtype bool
        """
        versionKey = "qt_version_{0}@@{1}".format(version, name)
        info = engine.customValue(versionKey, "")
        lst = info.split("|") if info else []

        dt = None
        if len(lst) and lst[0]:
            dt = datetime.datetime.fromisoformat(lst[0])

        qchFile = ""
        if len(lst) == 2:
            qchFile = lst[1]

        if version == 5:
            docsPath = pathlib.Path(
                QLibraryInfo.path(QLibraryInfo.LibraryPath.DocumentationPath)
            )
            if not docsPath.is_dir() or len(list(docsPath.glob("*.qch"))) == 0:
                docsPath = (
                    docsPath.parents[2]
                    / "Docs"
                    / "Qt-{0}.{1}".format(*QtUtilities.qVersionTuple())
                )
        else:
            # unsupported Qt version
            return False

        files = list(docsPath.glob("*.qch"))
        if not files:
            engine.setCustomValue(versionKey, "|")
            return False

        for f in files:
            if f.stem == name:
                namespace = QHelpEngineCore.namespaceName(str(f.resolve()))
                if not namespace:
                    continue

                if (
                    dt is not None
                    and namespace in engine.registeredDocumentations()
                    and (
                        datetime.datetime.fromtimestamp(
                            f.stat().st_mtime, tz=datetime.timezone.utc
                        )
                        == dt
                    )
                    and qchFile == str(f.resolve())
                ):
                    return False

                if namespace in engine.registeredDocumentations():
                    engine.unregisterDocumentation(namespace)

                if not engine.registerDocumentation(str(f.resolve())):
                    self.errorMessage.emit(
                        self.tr(
                            """<p>The file <b>{0}</b> could not be"""
                            """ registered. <br/>Reason: {1}</p>"""
                        ).format(f, engine.error())
                    )
                    return False

                engine.setCustomValue(
                    versionKey,
                    datetime.datetime.fromtimestamp(
                        f.stat().st_mtime, tz=datetime.timezone.utc
                    ).isoformat()
                    + "|"
                    + str(f.resolve()),
                )
                return True

        return False

    def __installEric7Doc(self, engine):
        """
        Private method to install/update the eric help documentation.

        @param engine reference to the help engine
        @type QHelpEngineCore
        @return flag indicating success
        @rtype bool
        """
        versionKey = "eric7_ide"
        info = engine.customValue(versionKey, "")
        lst = info.split("|")

        dt = None
        if len(lst) and lst[0]:
            dt = datetime.datetime.fromisoformat(lst[0])

        qchFile = ""
        if len(lst) == 2:
            qchFile = lst[1]

        docsPath = pathlib.Path(getConfig("ericDocDir")) / "Help"

        files = list(docsPath.glob("*.qch"))
        if not files:
            engine.setCustomValue(versionKey, "|")
            return False

        for f in files:
            if f.name == "source.qch":
                namespace = QHelpEngineCore.namespaceName(str(f.resolve()))
                if not namespace:
                    continue

                if (
                    dt is not None
                    and namespace in engine.registeredDocumentations()
                    and (
                        datetime.datetime.fromtimestamp(
                            f.stat().st_mtime, tz=datetime.timezone.utc
                        )
                        == dt
                    )
                    and qchFile == str(f.resolve())
                ):
                    return False

                if namespace in engine.registeredDocumentations():
                    engine.unregisterDocumentation(namespace)

                if not engine.registerDocumentation(str(f.resolve())):
                    self.errorMessage.emit(
                        self.tr(
                            """<p>The file <b>{0}</b> could not be"""
                            """ registered. <br/>Reason: {1}</p>"""
                        ).format(f, engine.error())
                    )
                    return False

                engine.setCustomValue(
                    versionKey,
                    datetime.datetime.fromtimestamp(
                        f.stat().st_mtime, tz=datetime.timezone.utc
                    ).isoformat()
                    + "|"
                    + str(f.resolve()),
                )
                return True

        return False
