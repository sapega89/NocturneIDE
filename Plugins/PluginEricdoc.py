# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Ericdoc plugin.
"""

import os

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7 import Preferences
from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import getConfig
from eric7.SystemUtilities import (
    FileSystemUtilities,
    OSUtilities,
    PythonUtilities,
    QtUtilities,
)

# Start-Of-Header
__header__ = {
    "name": "Ericdoc Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "EricdocPlugin",
    "packageName": "__core__",
    "shortDescription": "Show the Ericdoc dialogs.",
    "longDescription": (
        """This plugin implements the Ericdoc dialogs."""
        """ Ericdoc is used to generate a source code documentation"""
        """ for Python and Ruby projects."""
    ),
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


def exeDisplayDataList():
    """
    Public method to support the display of some executable info.

    @return dictionary containing the data to query the presence of
        the executable
    @rtype dict
    """
    dataList = []

    # 1. eric7_doc
    exe = "eric7_doc"
    if OSUtilities.isWindowsPlatform():
        for exepath in (
            getConfig("bindir"),
            PythonUtilities.getPythonScriptsDirectory(),
        ):
            found = False
            for ext in (".exe", ".cmd", ".bat"):
                exe_ = os.path.join(exepath, exe + ext)
                if os.path.exists(exe_):
                    exe = exe_
                    found = True
                    break
            if found:
                break
    else:
        for exepath in (
            getConfig("bindir"),
            PythonUtilities.getPythonScriptsDirectory(),
        ):
            exe_ = os.path.join(exepath, exe)
            if os.path.exists(exe_):
                exe = exe_
                break

    dataList.append(
        {
            "programEntry": True,
            "header": QCoreApplication.translate(
                "EricdocPlugin", "eric Documentation Generator"
            ),
            "exe": exe,
            "versionCommand": "--version",
            "versionStartsWith": "eric7_",
            "versionPosition": -3,
            "version": "",
            "versionCleanup": None,
        }
    )

    # 2. Qt Help Generator
    # 2.1 location before 6.3 (Linux and macOS) and Windows
    exe = Preferences.getQt("QHelpGenerator")

    if not exe:
        # 2.2 location before 6.3 (Linux and macOS) and Windows
        exe = os.path.join(
            QtUtilities.getQtBinariesPath(),
            QtUtilities.generateQtToolName("qhelpgenerator"),
        )
        if OSUtilities.isWindowsPlatform():
            exe += ".exe"
        if not os.path.exists(exe):
            # 2.3 location starting with 6.3.0 (Linux and macOS)
            exe = os.path.join(
                QtUtilities.getQtBinariesPath(libexec=True),
                QtUtilities.generateQtToolName("qhelpgenerator"),
            )

    if exe:
        dataList.append(
            {
                "programEntry": True,
                "header": QCoreApplication.translate("EricdocPlugin", "Qt Help Tools"),
                "exe": exe,
                "versionCommand": "-v",
                "versionStartsWith": "Qt",
                "versionPosition": -1,
                "version": "",
                "versionCleanup": (0, -1),
            }
        )

    return dataList


class EricdocPlugin(QObject):
    """
    Class implementing the Ericdoc plugin.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        super().__init__(ui)
        self.__ui = ui
        self.__initialize()

    def __initialize(self):
        """
        Private slot to (re)initialize the plugin.
        """
        self.__projectAct = None
        self.__execDialog = None

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of None and activation status
        @rtype bool
        """
        menu = ericApp().getObject("Project").getMenu("Apidoc")
        if menu:
            self.__projectAct = EricAction(
                self.tr("Generate documentation (eric7_doc)"),
                self.tr("Generate &documentation (eric7_doc)"),
                0,
                0,
                self,
                "doc_eric7_doc",
            )
            self.__projectAct.setStatusTip(
                self.tr("Generate API documentation using eric7_doc")
            )
            self.__projectAct.setWhatsThis(
                self.tr(
                    """<b>Generate documentation</b>"""
                    """<p>Generate API documentation using eric7_doc.</p>"""
                )
            )
            self.__projectAct.triggered.connect(self.__doEricdoc)
            ericApp().getObject("Project").addEricActions([self.__projectAct])
            menu.addAction(self.__projectAct)

        ericApp().getObject("Project").showMenu.connect(self.__projectShowMenu)

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        ericApp().getObject("Project").showMenu.disconnect(self.__projectShowMenu)

        menu = ericApp().getObject("Project").getMenu("Apidoc")
        if menu:
            menu.removeAction(self.__projectAct)
            ericApp().getObject("Project").removeEricActions([self.__projectAct])
        self.__initialize()

    def __projectShowMenu(self, menuName, _menu):
        """
        Private slot called, when the the project menu or a submenu is
        about to be shown.

        @param menuName name of the menu to be shown
        @type str
        @param _menu reference to the menu (unused)
        @type QMenu
        """
        if menuName == "Apidoc" and self.__projectAct is not None:
            self.__projectAct.setEnabled(
                ericApp().getObject("Project").getProjectLanguage()
                in ["Python", "Python3", "Ruby", "MicroPython"]
            )

    def __doEricdoc(self):
        """
        Private slot to perform the eric7_doc api documentation generation.
        """
        from eric7.Plugins.DocumentationPlugins.Ericdoc.EricdocConfigDialog import (
            EricdocConfigDialog,
        )
        from eric7.Plugins.DocumentationPlugins.Ericdoc.EricdocExecDialog import (
            EricdocExecDialog,
        )

        eolTranslation = {
            "\r": "cr",
            "\n": "lf",
            "\r\n": "crlf",
        }
        project = ericApp().getObject("Project")
        parms = project.getData("DOCUMENTATIONPARMS", "ERIC4DOC")
        dlg = EricdocConfigDialog(project, parms=parms, parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            args, parms, startDir = dlg.generateParameters()
            project.setData("DOCUMENTATIONPARMS", "ERIC4DOC", parms)

            if not startDir:
                startDir = project.ppath

            # add parameter for the eol setting
            if not project.useSystemEol():
                args.append("--eol={0}".format(eolTranslation[project.getEolString()]))

            # now do the call
            self.__execDialog = EricdocExecDialog("Ericdoc")
            self.__execDialog.finished.connect(self.__execDialogFinished)
            self.__execDialog.processFinished.connect(self.__ericdocProcessFinished)
            self.__execDialog.show()
            self.__execDialog.start(args, startDir)

    @pyqtSlot()
    def __ericdocProcessFinished(self):
        """
        Private slot to perform actions after the documentation was generated.
        """
        project = ericApp().getObject("Project")
        parms = project.getData("DOCUMENTATIONPARMS", "ERIC4DOC")

        outdir = FileSystemUtilities.toNativeSeparators(parms["outputDirectory"])
        if outdir == "":
            outdir = "doc"  # that is eric7_docs default output dir

        # add it to the project data, if it isn't in already
        outdir = project.getRelativePath(outdir)
        if outdir not in project.getProjectData(dataKey="OTHERS"):
            project.setProjectData(
                project.getProjectData(dataKey="OTHERS") + [outdir],
                dataKey="OTHERS",
            )
            project.setDirty(True)
            project.othersAdded(outdir)

        if parms["qtHelpEnabled"]:
            outdir = FileSystemUtilities.toNativeSeparators(
                parms["qtHelpOutputDirectory"]
            )
            if outdir == "":
                outdir = "help"
                # that is eric7_docs default QtHelp output dir

            # add it to the project data, if it isn't in already
            outdir = project.getRelativePath(outdir)
            if outdir not in project.getProjectData(dataKey="OTHERS"):
                project.setProjectData(
                    project.getProjectData(dataKey="OTHERS") + [outdir],
                    dataKey="OTHERS",
                )
                project.setDirty(True)
                project.othersAdded(outdir)

    @pyqtSlot()
    def __execDialogFinished(self):
        """
        Private slot to handle the execution dialog being closed.
        """
        self.__execDialog = None
