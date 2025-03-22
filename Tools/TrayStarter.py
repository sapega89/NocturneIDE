# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a starter for the system tray.
"""

import contextlib
import os
import pathlib
import sys

from PyQt6 import sip
from PyQt6.Qsci import QSCINTILLA_VERSION_STR
from PyQt6.QtCore import PYQT_VERSION_STR, QProcess, QSettings, qVersion
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QSystemTrayIcon

from eric7 import EricUtilities, Globals, Preferences
from eric7.__version__ import Version
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import DesktopUtilities, FileSystemUtilities, PythonUtilities
from eric7.UI.Info import Program


class TrayStarter(QSystemTrayIcon):
    """
    Class implementing a starter for the system tray.
    """

    def __init__(self, settingsDir):
        """
        Constructor

        @param settingsDir directory to be used for the settings files
        @type str
        """
        super().__init__(
            EricPixmapCache.getIcon(Preferences.getTrayStarter("TrayStarterIcon"))
        )

        self.settingsDir = settingsDir

        self.maxMenuFilePathLen = 75

        self.rsettings = QSettings(
            QSettings.Format.IniFormat,
            QSettings.Scope.UserScope,
            Globals.settingsNameOrganization,
            Globals.settingsNameRecent,
        )

        self.recentProjects = []
        self.__loadRecentProjects()
        self.recentMultiProjects = []
        self.__loadRecentMultiProjects()
        self.recentFiles = []
        self.__loadRecentFiles()

        self.activated.connect(self.__activated)

        self.__menu = QMenu(self.tr("eric tray starter"))

        self.recentProjectsMenu = QMenu(self.tr("Recent Projects"), self.__menu)
        self.recentProjectsMenu.aboutToShow.connect(self.__showRecentProjectsMenu)
        self.recentProjectsMenu.triggered.connect(self.__openRecent)

        self.recentMultiProjectsMenu = QMenu(
            self.tr("Recent Multiprojects"), self.__menu
        )
        self.recentMultiProjectsMenu.aboutToShow.connect(
            self.__showRecentMultiProjectsMenu
        )
        self.recentMultiProjectsMenu.triggered.connect(self.__openRecent)

        self.recentFilesMenu = QMenu(self.tr("Recent Files"), self.__menu)
        self.recentFilesMenu.aboutToShow.connect(self.__showRecentFilesMenu)
        self.recentFilesMenu.triggered.connect(self.__openRecent)

        act = self.__menu.addAction(self.tr("eric tray starter"), self.__about)
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        self.__menu.addSeparator()

        self.__menu.addAction(self.tr("Show Versions"), self.__showVersions)
        self.__menu.addSeparator()

        self.__menu.addAction(
            self.tr("QRegularExpression editor"), self.__startQRegularExpression
        )
        self.__menu.addAction(self.tr("Python re editor"), self.__startPyRe)
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("uiPreviewer"),
            self.tr("UI Previewer"),
            self.__startUIPreviewer,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("trPreviewer"),
            self.tr("Translations Previewer"),
            self.__startTRPreviewer,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("unittest"), self.tr("Testing"), self.__startTesting
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("diffFiles"),
            self.tr("Compare Files"),
            self.__startDiff,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("compareFiles"),
            self.tr("Compare Files side by side"),
            self.__startCompare,
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("sqlBrowser"),
            self.tr("SQL Browser"),
            self.__startSqlBrowser,
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("ericSnap"),
            self.tr("Snapshot"),
            self.__startSnapshot,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("iconEditor"),
            self.tr("Icon Editor"),
            self.__startIconEditor,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("ericPdf"),
            self.tr("PDF Viewer"),
            self.__startPdfViewer,
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("pluginInstall"),
            self.tr("Install Plugin"),
            self.__startPluginInstall,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("pluginUninstall"),
            self.tr("Uninstall Plugin"),
            self.__startPluginUninstall,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("pluginRepository"),
            self.tr("Plugin Repository"),
            self.__startPluginRepository,
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("virtualenv"),
            self.tr("Virtual Environments"),
            self.__startVirtualenvManager,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("pypi"),
            self.tr("PyPI Package Management"),
            self.__startPip,
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("configure"),
            self.tr("Preferences"),
            self.__startPreferences,
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("editor"),
            self.tr("eric Mini Editor"),
            self.__startMiniEditor,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("hexEditor"),
            self.tr("eric Hex Editor"),
            self.__startHexEditor,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("shell"),
            self.tr("eric Shell Window"),
            self.__startShell,
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("ericWeb"),
            self.tr("eric Web Browser"),
            self.__startWebBrowser,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("ericWeb"),
            self.tr("eric Web Browser (with QtHelp)"),
            self.__startWebBrowserQtHelp,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("ericWeb"),
            self.tr("eric Web Browser (Private Mode)"),
            self.__startWebBrowserPrivate,
        )
        self.__menu.addSeparator()

        # recent files
        self.menuRecentFilesAct = self.__menu.addMenu(self.recentFilesMenu)
        # recent multi projects
        self.menuRecentMultiProjectsAct = self.__menu.addMenu(
            self.recentMultiProjectsMenu
        )
        # recent projects
        self.menuRecentProjectsAct = self.__menu.addMenu(self.recentProjectsMenu)
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("erict"), self.tr("eric IDE"), self.__startEric
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("configure"),
            self.tr("Configure Tray Starter"),
            self.__showPreferences,
        )
        self.__menu.addSeparator()

        self.__menu.addAction(
            EricPixmapCache.getIcon("exit"), self.tr("Quit"), ericApp().quit
        )

    def __loadRecentProjects(self):
        """
        Private method to load the recently opened project filenames.
        """
        rp = self.rsettings.value(Globals.recentNameProject)
        if rp is not None:
            for f in rp:
                if pathlib.Path(f).exists():
                    self.recentProjects.append(f)

    def __loadRecentMultiProjects(self):
        """
        Private method to load the recently opened multi project filenames.
        """
        rmp = self.rsettings.value(Globals.recentNameMultiProject)
        if rmp is not None:
            for f in rmp:
                if pathlib.Path(f).exists():
                    self.recentMultiProjects.append(f)

    def __loadRecentFiles(self):
        """
        Private method to load the recently opened filenames.
        """
        rf = self.rsettings.value(Globals.recentNameFiles)
        if rf is not None:
            for f in rf:
                if pathlib.Path(f).exists():
                    self.recentFiles.append(f)

    def __activated(self, reason):
        """
        Private slot to handle the activated signal.

        @param reason reason code of the signal
        @type QSystemTrayIcon.ActivationReason
        """
        if reason in (
            QSystemTrayIcon.ActivationReason.Context,
            QSystemTrayIcon.ActivationReason.MiddleClick,
        ):
            self.__showContextMenu()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.__startEric()

    def __showContextMenu(self):
        """
        Private slot to show the context menu.
        """
        self.menuRecentProjectsAct.setEnabled(len(self.recentProjects) > 0)
        self.menuRecentMultiProjectsAct.setEnabled(len(self.recentMultiProjects) > 0)
        self.menuRecentFilesAct.setEnabled(len(self.recentFiles) > 0)

        pos = QCursor.pos()
        x = pos.x() - self.__menu.sizeHint().width()
        pos.setX(x > 0 and x or 0)
        y = pos.y() - self.__menu.sizeHint().height()
        pos.setY(y > 0 and y or 0)
        self.__menu.popup(pos)

    def __startProc(self, applName, *applArgs):
        """
        Private method to start an eric application.

        @param applName name of the eric application script
        @type str
        @param *applArgs variable list of application arguments
        @type list of str
        """
        proc = QProcess()
        applPath = os.path.join(os.path.dirname(__file__), "..", applName)

        args = []
        args.append(applPath)
        args.append("--config={0}".format(EricUtilities.getConfigDir()))
        if self.settingsDir:
            args.append("--settings={0}".format(self.settingsDir))
        for arg in applArgs:
            args.append(arg)

        if not os.path.isfile(applPath) or not proc.startDetached(
            PythonUtilities.getPythonExecutable(), args
        ):
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start the process.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(applPath),
                self.tr("OK"),
            )

    def __startMiniEditor(self):
        """
        Private slot to start the eric Mini Editor.
        """
        self.__startProc("eric7_editor.py")

    def __startEric(self):
        """
        Private slot to start the eric IDE.
        """
        self.__startProc("eric7_ide.py")

    def __startPreferences(self):
        """
        Private slot to start the eric configuration dialog.
        """
        self.__startProc("eric7_configure.py")

    def __startPluginInstall(self):
        """
        Private slot to start the eric plugin installation dialog.
        """
        self.__startProc("eric7_plugininstall.py")

    def __startPluginUninstall(self):
        """
        Private slot to start the eric plugin uninstallation dialog.
        """
        self.__startProc("eric7_pluginuninstall.py")

    def __startPluginRepository(self):
        """
        Private slot to start the eric plugin repository dialog.
        """
        self.__startProc("eric7_pluginrepository.py")

    def __startVirtualenvManager(self):
        """
        Private slot to start the eric virtual environments manager window.
        """
        self.__startProc("eric7_virtualenv.py")

    def __startPip(self):
        """
        Private slot to start the eric package manager (PyPI) window.
        """
        self.__startProc("eric7_pip.py")

    def __startWebBrowser(self):
        """
        Private slot to start the eric web browser.
        """
        variant = Globals.getWebBrowserSupport()
        if variant == "QtWebEngine":
            self.__startProc("eric7_browser.py")

    def __startWebBrowserQtHelp(self):
        """
        Private slot to start the eric web browser with QtHelp support.
        """
        variant = Globals.getWebBrowserSupport()
        if variant == "QtWebEngine":
            self.__startProc("eric7_browser.py", "--qthelp")

    def __startWebBrowserPrivate(self):
        """
        Private slot to start the eric web browser in private mode.
        """
        variant = Globals.getWebBrowserSupport()
        if variant == "QtWebEngine":
            self.__startProc("eric7_browser.py", "--private")

    def __startUIPreviewer(self):
        """
        Private slot to start the eric UI previewer.
        """
        self.__startProc("eric7_uipreviewer.py")

    def __startTRPreviewer(self):
        """
        Private slot to start the eric translations previewer.
        """
        self.__startProc("eric7_trpreviewer.py")

    def __startTesting(self):
        """
        Private slot to start the eric testing dialog.
        """
        self.__startProc("eric7_testing.py")

    def __startDiff(self):
        """
        Private slot to start the eric diff dialog.
        """
        self.__startProc("eric7_diff.py")

    def __startCompare(self):
        """
        Private slot to start the eric compare dialog.
        """
        self.__startProc("eric7_compare.py")

    def __startSqlBrowser(self):
        """
        Private slot to start the eric sql browser dialog.
        """
        self.__startProc("eric7_sqlbrowser.py")

    def __startIconEditor(self):
        """
        Private slot to start the eric icon editor dialog.
        """
        self.__startProc("eric7_iconeditor.py")

    def __startSnapshot(self):
        """
        Private slot to start the eric snapshot dialog.
        """
        self.__startProc("eric7_snap.py")

    def __startQRegularExpression(self):
        """
        Private slot to start the eric QRegularExpression editor dialog.
        """
        self.__startProc("eric7_qregularexpression.py")

    def __startPyRe(self):
        """
        Private slot to start the eric Python re editor dialog.
        """
        self.__startProc("eric7_re.py")

    def __startHexEditor(self):
        """
        Private slot to start the eric hex editor dialog.
        """
        self.__startProc("eric7_hexeditor.py")

    def __startShell(self):
        """
        Private slot to start the eric Shell window.
        """
        self.__startProc("eric7_shell.py")

    def __startPdfViewer(self):
        """
        Private slot to start the eric PDF Viewer window.
        """
        self.__startProc("eric7_pdf.py")

    def __showRecentProjectsMenu(self):
        """
        Private method to set up the recent projects menu.
        """
        self.recentProjects = []
        self.rsettings.sync()
        self.__loadRecentProjects()

        self.recentProjectsMenu.clear()

        for idx, rp in enumerate(self.recentProjects, start=1):
            formatStr = "&{0:d}. {1}" if idx < 10 else "{0:d}. {1}"
            act = self.recentProjectsMenu.addAction(
                formatStr.format(
                    idx, FileSystemUtilities.compactPath(rp, self.maxMenuFilePathLen)
                )
            )
            act.setData(rp)

    def __showRecentMultiProjectsMenu(self):
        """
        Private method to set up the recent multi projects menu.
        """
        self.recentMultiProjects = []
        self.rsettings.sync()
        self.__loadRecentMultiProjects()

        self.recentMultiProjectsMenu.clear()

        for idx, rmp in enumerate(self.recentMultiProjects, start=1):
            formatStr = "&{0:d}. {1}" if idx < 10 else "{0:d}. {1}"
            act = self.recentMultiProjectsMenu.addAction(
                formatStr.format(
                    idx, FileSystemUtilities.compactPath(rmp, self.maxMenuFilePathLen)
                )
            )
            act.setData(rmp)

    def __showRecentFilesMenu(self):
        """
        Private method to set up the recent files menu.
        """
        self.recentFiles = []
        self.rsettings.sync()
        self.__loadRecentFiles()

        self.recentFilesMenu.clear()

        for idx, rf in enumerate(self.recentFiles, start=1):
            formatStr = "&{0:d}. {1}" if idx < 10 else "{0:d}. {1}"
            act = self.recentFilesMenu.addAction(
                formatStr.format(
                    idx, FileSystemUtilities.compactPath(rf, self.maxMenuFilePathLen)
                )
            )
            act.setData(rf)

    def __openRecent(self, act):
        """
        Private method to open a project or file from the list of recently
        opened projects or files.

        @param act reference to the action that triggered
        @type QAction
        """
        filename = act.data()
        if filename:
            self.__startProc("eric7_ide.py", filename)

    def __showPreferences(self):
        """
        Private slot to set the preferences.
        """
        from eric7.Preferences.ConfigurationDialog import (
            ConfigurationDialog,
            ConfigurationMode,
        )

        dlg = ConfigurationDialog(
            None,
            "Configuration",
            True,
            fromEric=True,
            displayMode=ConfigurationMode.TRAYSTARTERMODE,
        )
        dlg.preferencesChanged.connect(self.preferencesChanged)
        dlg.show()
        dlg.showConfigurationPageByName("trayStarterPage")
        dlg.exec()
        QApplication.processEvents()
        if dlg.result() == QDialog.DialogCode.Accepted:
            dlg.setPreferences()
            Preferences.syncPreferences()
            self.preferencesChanged()

    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        self.setIcon(
            EricPixmapCache.getIcon(Preferences.getTrayStarter("TrayStarterIcon"))
        )

    def __about(self):
        """
        Private slot to handle the About dialog.
        """
        from eric7.Plugins.AboutPlugin.AboutDialog import AboutDialog

        dlg = AboutDialog()
        dlg.exec()

    def __showVersions(self):
        """
        Private slot to handle the Versions dialog.
        """
        try:
            sip_version_str = sip.SIP_VERSION_STR
        except AttributeError:
            sip_version_str = "sip version not available"

        versionText = self.tr("""<h3>Version Numbers</h3><table>""")

        # Python version
        versionText += """<tr><td><b>Python</b></td><td>{0}</td></tr>""".format(
            sys.version.split()[0]
        )

        # Qt version
        versionText += """<tr><td><b>Qt</b></td><td>{0}</td></tr>""".format(qVersion())

        # PyQt versions
        versionText += """<tr><td><b>PyQt</b></td><td>{0}</td></tr>""".format(
            PYQT_VERSION_STR
        )
        versionText += """<tr><td><b>sip</b></td><td>{0}</td></tr>""".format(
            sip_version_str
        )
        versionText += """<tr><td><b>QScintilla</b></td><td>{0}</td></tr>""".format(
            QSCINTILLA_VERSION_STR
        )

        # webengine (chromium) version
        with contextlib.suppress(ImportError):
            from eric7.WebBrowser.Tools import (  # __IGNORE_WARNING_I101__
                WebBrowserTools,
            )

            (
                chromiumVersion,
                chromiumSecurityVersion,
            ) = WebBrowserTools.getWebEngineVersions()[0:2]
            versionText += """<tr><td><b>WebEngine</b></td><td>{0}</td></tr>""".format(
                chromiumVersion
            )
            if chromiumSecurityVersion:
                versionText += self.tr(
                    """<tr><td><b>WebEngine (Security)</b></td>"""
                    """<td>{0}</td></tr>"""
                ).format(chromiumSecurityVersion)

        # eric7 version
        versionText += """<tr><td><b>{0}</b></td><td>{1}</td></tr>""".format(
            Program, Version
        )

        # desktop and session type
        desktop = DesktopUtilities.desktopName()
        session = DesktopUtilities.sessionType()
        if desktop or session:
            versionText += "<tr><td></td><td></td></tr>"
            if desktop:
                versionText += ("<tr><td><b>{0}</b></td><td>{1}</td></tr>").format(
                    self.tr("Desktop"), desktop
                )
            if session:
                versionText += ("<tr><td><b>{0}</b></td><td>{1}</td></tr>").format(
                    self.tr("Session Type"), session
                )

        versionText += self.tr("""</table>""")

        EricMessageBox.about(None, Program, versionText)
