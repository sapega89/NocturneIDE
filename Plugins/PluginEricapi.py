# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Ericapi plugin.
"""

import os

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.__version__ import VersionOnly
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import getConfig
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities, PythonUtilities

# Start-Of-Header
__header__ = {
    "name": "Ericapi Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "EricapiPlugin",
    "packageName": "__core__",
    "shortDescription": "Show the Ericapi dialogs.",
    "longDescription": (
        """This plugin implements the Ericapi dialogs."""
        """ Ericapi is used to generate a QScintilla API file for Python and"""
        """ Ruby projects."""
    ),
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


def exeDisplayData():
    """
    Public method to support the display of some executable info.

    @return dictionary containing the data to query the presence of
        the executable
    @rtype dict
    """
    exe = "eric7_api"
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

    data = {
        "programEntry": True,
        "header": QCoreApplication.translate(
            "EricapiPlugin", "eric API File Generator"
        ),
        "exe": exe,
        "versionCommand": "--version",
        "versionStartsWith": "eric7_",
        "versionPosition": -3,
        "version": "",
        "versionCleanup": None,
    }

    return data


class EricapiPlugin(QObject):
    """
    Class implementing the Ericapi plugin.
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
                self.tr("Generate API file (eric7_api)"),
                self.tr("Generate &API file (eric7_api)"),
                0,
                0,
                self,
                "doc_eric7_api",
            )
            self.__projectAct.setStatusTip(
                self.tr("Generate an API file using eric7_api")
            )
            self.__projectAct.setWhatsThis(
                self.tr(
                    """<b>Generate API file</b>"""
                    """<p>Generate an API file using eric7_api.</p>"""
                )
            )
            self.__projectAct.triggered.connect(self.__doEricapi)
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

    def __doEricapi(self):
        """
        Private slot to perform the eric7_api API generation.
        """
        from eric7.Plugins.DocumentationPlugins.Ericapi.EricapiConfigDialog import (
            EricapiConfigDialog,
        )
        from eric7.Plugins.DocumentationPlugins.Ericapi.EricapiExecDialog import (
            EricapiExecDialog,
        )

        eolTranslation = {
            "\r": "cr",
            "\n": "lf",
            "\r\n": "crlf",
        }
        project = ericApp().getObject("Project")
        parms = project.getData("DOCUMENTATIONPARMS", "ERIC4API")
        dlg = EricapiConfigDialog(project, parms=parms, parent=self.__ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            args, parms, startDir = dlg.generateParameters()
            project.setData("DOCUMENTATIONPARMS", "ERIC4API", parms)

            if not startDir:
                startDir = project.ppath

            # add parameter for the eol setting
            if not project.useSystemEol():
                args.append("--eol={0}".format(eolTranslation[project.getEolString()]))

            # now do the call
            self.__execDialog = EricapiExecDialog("Ericapi")
            self.__execDialog.finished.connect(self.__execDialogFinished)
            self.__execDialog.processFinished.connect(self.__ericapiProcessFinished)
            self.__execDialog.show()
            self.__execDialog.start(args, startDir)

    @pyqtSlot()
    def __ericapiProcessFinished(self):
        """
        Private slot to perform actions after the API data was generated.
        """
        project = ericApp().getObject("Project")
        parms = project.getData("DOCUMENTATIONPARMS", "ERIC4API")

        outputFileName = FileSystemUtilities.toNativeSeparators(parms["outputFile"])

        # add output files to the project data, if they aren't in already
        for progLanguage in parms["languages"]:
            if "%L" in outputFileName:
                outfile = outputFileName.replace("%L", progLanguage)
            else:
                if len(parms["languages"]) == 1:
                    outfile = outputFileName
                else:
                    root, ext = os.path.splitext(outputFileName)
                    outfile = "{0}-{1}{2}".format(root, progLanguage.lower(), ext)

            outfile = project.getRelativePath(outfile)
            if outfile not in project.getProjectData(dataKey="OTHERS"):
                project.appendFile(outfile)

    @pyqtSlot()
    def __execDialogFinished(self):
        """
        Private slot to handle the execution dialog being closed.
        """
        self.__execDialog = None
