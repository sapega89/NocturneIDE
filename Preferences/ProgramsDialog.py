# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Programs page.
"""

import os
import re

from PyQt6.QtCore import QProcess, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QTreeWidgetItem,
)

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import (
    FileSystemUtilities,
    OSUtilities,
    PythonUtilities,
    QtUtilities,
)

from .Ui_ProgramsDialog import Ui_ProgramsDialog


class ProgramsDialog(QDialog, Ui_ProgramsDialog):
    """
    Class implementing the Programs page.
    """

    ToolAvailableRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        """
        Constructor

        @param parent The parent widget of this dialog.
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setObjectName("ProgramsDialog")
        self.setWindowFlags(Qt.WindowType.Window)

        self.__hasSearched = False

        self.programsList.headerItem().setText(self.programsList.columnCount(), "")

        self.searchButton = self.buttonBox.addButton(
            self.tr("Search"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.searchButton.setToolTip(self.tr("Press to search for programs"))

        self.showComboBox.addItems(
            [
                self.tr("All Supported Tools"),
                self.tr("Available Tools Only"),
                self.tr("Unavailable Tools Only"),
            ]
        )

    def show(self):
        """
        Public slot to show the dialog.
        """
        QDialog.show(self)
        if not self.__hasSearched:
            self.on_programsSearchButton_clicked()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.searchButton:
            self.on_programsSearchButton_clicked()

    @pyqtSlot()
    def on_programsSearchButton_clicked(self):
        """
        Private slot to search for all supported/required programs.
        """
        self.programsList.clear()
        header = self.programsList.header()
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        header.setSortIndicatorShown(False)

        with EricOverrideCursor():
            # 1. do the Qt programs
            # 1a. Translation Converter
            exe = Preferences.getQt("Lrelease")
            if not exe:
                exe = (
                    "{0}.exe".format(QtUtilities.generateQtToolName("lrelease"))
                    if OSUtilities.isWindowsPlatform()
                    else QtUtilities.generateQtToolName("lrelease")
                )
                exe = os.path.join(QtUtilities.getQtBinariesPath(), exe)
            version = self.__createProgramEntry(
                self.tr("Translation Converter (Qt)"), exe, "-version", "lrelease", -1
            )
            # 1b. Qt Designer
            if OSUtilities.isWindowsPlatform():
                exe = os.path.join(
                    QtUtilities.getQtBinariesPath(),
                    "{0}.exe".format(QtUtilities.generateQtToolName("designer")),
                )
            elif OSUtilities.isMacPlatform():
                exe = QtUtilities.getQtMacBundle("designer")
            else:
                exe = os.path.join(
                    QtUtilities.getQtBinariesPath(),
                    QtUtilities.generateQtToolName("designer"),
                )
            self.__createProgramEntry(self.tr("Qt Designer"), exe, version=version)
            # 1c. Qt Linguist
            if OSUtilities.isWindowsPlatform():
                exe = os.path.join(
                    QtUtilities.getQtBinariesPath(),
                    "{0}.exe".format(QtUtilities.generateQtToolName("linguist")),
                )
            elif OSUtilities.isMacPlatform():
                exe = QtUtilities.getQtMacBundle("linguist")
            else:
                exe = os.path.join(
                    QtUtilities.getQtBinariesPath(),
                    QtUtilities.generateQtToolName("linguist"),
                )
            self.__createProgramEntry(self.tr("Qt Linguist"), exe, version=version)
            # 1d. Qt Assistant
            if OSUtilities.isWindowsPlatform():
                exe = os.path.join(
                    QtUtilities.getQtBinariesPath(),
                    "{0}.exe".format(QtUtilities.generateQtToolName("assistant")),
                )
            elif OSUtilities.isMacPlatform():
                exe = QtUtilities.getQtMacBundle("assistant")
            else:
                exe = os.path.join(
                    QtUtilities.getQtBinariesPath(),
                    QtUtilities.generateQtToolName("assistant"),
                )
            self.__createProgramEntry(self.tr("Qt Assistant"), exe, version=version)

            # 2. do the PyQt programs
            # 2.1 do the PyQt5 programs
            # 2.1a. Translation Extractor PyQt5
            self.__createProgramEntry(
                self.tr("Translation Extractor (Python, PyQt5)"),
                QtUtilities.generatePyQtToolPath("pylupdate5"),
                "-version",
                "pylupdate",
                -1,
            )
            # 2.1b. Forms Compiler PyQt5
            self.__createProgramEntry(
                self.tr("Forms Compiler (Python, PyQt5)"),
                QtUtilities.generatePyQtToolPath("pyuic5", ["py3uic5"]),
                "--version",
                "Python User",
                4,
            )
            # 2.1c. Resource Compiler PyQt5
            self.__createProgramEntry(
                self.tr("Resource Compiler (Python, PyQt5)"),
                QtUtilities.generatePyQtToolPath("pyrcc5"),
                "-version",
                "",
                -1,
                versionRe="Resource Compiler|pyrcc5",
            )

            # 2.2 do the PyQt6 programs
            # 2.2a. Translation Extractor PyQt6
            self.__createProgramEntry(
                self.tr("Translation Extractor (Python, PyQt6)"),
                QtUtilities.generatePyQtToolPath("pylupdate6"),
                "--version",
                versionPosition=0,
            )
            # 2.2b. Forms Compiler PyQt6
            self.__createProgramEntry(
                self.tr("Forms Compiler (Python, PyQt6)"),
                QtUtilities.generatePyQtToolPath("pyuic6"),
                "--version",
                versionPosition=0,
            )

            # 3. do the PySide programs
            # 3.1 do the PySide2 programs
            # 3.1a. Translation Extractor PySide2
            self.__createProgramEntry(
                self.tr("Translation Extractor (Python, PySide2)"),
                QtUtilities.generatePySideToolPath("pyside2-lupdate", variant=2),
                "-version",
                "",
                -1,
                versionRe="lupdate",
            )
            # 3.1b. Forms Compiler PySide2
            self.__createProgramEntry(
                self.tr("Forms Compiler (Python, PySide2)"),
                QtUtilities.generatePySideToolPath("pyside2-uic", variant=2),
                "--version",
                "",
                -1,
                versionRe="uic",
            )
            # 3.1c Resource Compiler PySide2
            self.__createProgramEntry(
                self.tr("Resource Compiler (Python, PySide2)"),
                QtUtilities.generatePySideToolPath("pyside2-rcc", variant=2),
                "-version",
                "",
                -1,
                versionRe="rcc",
            )
            # 3.2 do the PySide5 programs
            # 3.2a. Translation Extractor PySide6
            self.__createProgramEntry(
                self.tr("Translation Extractor (Python, PySide6)"),
                QtUtilities.generatePySideToolPath("pyside6-lupdate", variant=6),
                "-version",
                "",
                -1,
                versionRe="lupdate",
            )
            # 3.2b. Forms Compiler PySide6
            self.__createProgramEntry(
                self.tr("Forms Compiler (Python, PySide6)"),
                QtUtilities.generatePySideToolPath("pyside6-uic", variant=6),
                "--version",
                "",
                -1,
                versionRe="uic",
            )
            # 3.2c Resource Compiler PySide6
            self.__createProgramEntry(
                self.tr("Resource Compiler (Python, PySide6)"),
                QtUtilities.generatePySideToolPath("pyside6-rcc", variant=6),
                "--version",
                "",
                -1,
                versionRe="rcc",
            )

            # 4. do the Conda program(s)
            exe = Preferences.getConda("CondaExecutable")
            if not exe:
                exe = "conda"
                if OSUtilities.isWindowsPlatform():
                    exe += ".exe"
            self.__createProgramEntry(
                self.tr("conda Manager"), exe, "--version", "conda", -1
            )

            # 5. do the pip program(s)
            virtualenvManager = ericApp().getObject("VirtualEnvManager")
            for venvName in virtualenvManager.getVirtualenvNames(
                noRemote=True, noServer=True
            ):
                interpreter = virtualenvManager.getVirtualenvInterpreter(venvName)
                self.__createProgramEntry(
                    self.tr("PyPI Package Management"),
                    interpreter,
                    "--version",
                    "pip",
                    1,
                    exeModule=["-m", "pip"],
                )

            # 6. do the spell checking entry
            try:
                import enchant  # __IGNORE_WARNING_I10__

                try:
                    text = os.path.dirname(enchant.__file__)
                except AttributeError:
                    text = "enchant"
                try:
                    version = enchant.__version__
                except AttributeError:
                    version = self.tr("(unknown)")
            except (AttributeError, ImportError, OSError):
                text = "enchant"
                version = ""
            self.__createEntry(self.tr("Spell Checker - PyEnchant"), text, version)

            # 7. do the pygments entry
            try:
                import pygments  # __IGNORE_WARNING_I10__

                try:
                    text = os.path.dirname(pygments.__file__)
                except AttributeError:
                    text = "pygments"
                try:
                    version = pygments.__version__
                except AttributeError:
                    version = self.tr("(unknown)")
            except (AttributeError, ImportError, OSError):
                text = "pygments"
                version = ""
            self.__createEntry(self.tr("Source Highlighter - Pygments"), text, version)

            # 8. do the MicroPython related entries
            exe = Preferences.getMicroPython("MpyCrossCompiler")
            if not exe:
                exe = "mpy-cross"
            self.__createProgramEntry(
                self.tr("MicroPython - MPY Cross Compiler"),
                exe,
                "--version",
                "MicroPython",
                1,
            )
            self.__createProgramEntry(
                self.tr("MicroPython - ESP Tool"),
                PythonUtilities.getPythonExecutable(),
                "version",
                "esptool",
                -1,
                exeModule=["-m", "esptool"],
            )
            exe = Preferences.getMicroPython("DfuUtilPath")
            if not exe:
                exe = "dfu-util"
            self.__createProgramEntry(
                self.tr("MicroPython - PyBoard Flasher"),
                exe,
                "--version",
                "dfu-util",
                -1,
            )
            exe = Preferences.getMicroPython("StInfoPath")
            if not exe:
                exe = "st-info"
            self.__createProgramEntry(
                self.tr("MicroPython - STLink Info"),
                exe,
                "--version",
                "",
                -1,
            )
            exe = Preferences.getMicroPython("StFlashPath")
            if not exe:
                exe = "st-flash"
            self.__createProgramEntry(
                self.tr("MicroPython - STLink Flasher"),
                exe,
                "--version",
                "",
                -1,
            )

            # 9. do the jedi related entries
            try:
                import jedi  # __IGNORE_WARNING_I10__

                try:
                    text = os.path.dirname(jedi.__file__)
                except AttributeError:
                    text = "jedi"
                try:
                    version = jedi.__version__
                except AttributeError:
                    version = self.tr("(unknown)")
            except (AttributeError, ImportError, OSError):
                text = "jedi"
                version = ""
            self.__createEntry(self.tr("Code Assistant - Jedi"), text, version)

            # 10. do the plugin related programs
            pm = ericApp().getObject("PluginManager")
            for info in pm.getPluginExeDisplayData():
                if info["programEntry"]:
                    if "exeModule" not in info:
                        info["exeModule"] = None
                    if "versionRe" not in info:
                        info["versionRe"] = None
                    self.__createProgramEntry(
                        info["header"],
                        info["exe"],
                        versionCommand=info["versionCommand"],
                        versionStartsWith=info["versionStartsWith"],
                        versionPosition=info["versionPosition"],
                        version=info["version"],
                        versionCleanup=info["versionCleanup"],
                        versionRe=info["versionRe"],
                        exeModule=info["exeModule"],
                    )
                else:
                    self.__createEntry(info["header"], info["text"], info["version"])

            self.programsList.sortByColumn(0, Qt.SortOrder.AscendingOrder)
            self.on_showComboBox_currentIndexChanged(self.showComboBox.currentIndex())

        self.__hasSearched = True

    def __createProgramEntry(
        self,
        description,
        exe,
        versionCommand="",
        versionStartsWith="",
        versionPosition=None,
        version="",
        versionCleanup=None,
        versionRe=None,
        exeModule=None,
    ):
        """
        Private method to generate a program entry.

        @param description descriptive text
        @type str
        @param exe name of the executable program
        @type str
        @param versionCommand command line switch to get the version info.
            If this is empty, the given version will be shown.
        @type str
        @param versionStartsWith start of line identifying version info
        @type str
        @param versionPosition index of part containing the version info
        @type int
        @param version version string to show
        @type str
        @param versionCleanup tuple of two integers giving string positions
            start and stop for the version string
        @type tuple of (int, int)
        @param versionRe regexp to determine the line identifying version
            info. Takes precedence over versionStartsWith.
        @type str
        @param exeModule list of command line parameters to execute a module
            with the program given in exe (e.g. to execute a Python module)
        @type list of str
        @return version string of detected or given version
        @rtype str
        """
        itmList = self.programsList.findItems(
            description, Qt.MatchFlag.MatchCaseSensitive
        )
        itm = (
            itmList[0] if itmList else QTreeWidgetItem(self.programsList, [description])
        )
        font = itm.font(0)
        font.setBold(True)
        itm.setFont(0, font)
        rememberedExe = exe
        if not exe:
            itm.setText(1, self.tr("(not configured)"))
        else:
            if os.path.isabs(exe):
                if not FileSystemUtilities.isExecutable(exe):
                    exe = ""
            else:
                exe = FileSystemUtilities.getExecutablePath(exe)
            if exe:
                available = True
                if versionCommand and versionPosition is not None:
                    proc = QProcess()
                    proc.setProcessChannelMode(
                        QProcess.ProcessChannelMode.MergedChannels
                    )
                    if exeModule:
                        args = exeModule[:] + [versionCommand]
                    else:
                        args = [versionCommand]
                    proc.start(exe, args)
                    finished = proc.waitForFinished(10000)
                    if finished:
                        output = str(
                            proc.readAllStandardOutput(),
                            Preferences.getSystem("IOEncoding"),
                            "replace",
                        )
                        if (
                            exeModule
                            and exeModule[0] == "-m"
                            and (
                                "ImportError:" in output
                                or "ModuleNotFoundError:" in output
                                or proc.exitCode() != 0
                            )
                        ):
                            version = self.tr("(module not found)")
                            available = False
                        elif not versionStartsWith and not versionRe:
                            # assume output is just one line
                            try:
                                version = output.strip().split()[versionPosition]
                                if versionCleanup:
                                    version = version[
                                        versionCleanup[0] : versionCleanup[1]
                                    ]
                            except IndexError:
                                version = self.tr("(unknown)")
                                available = False
                        else:
                            if versionRe is None:
                                versionRe = "^{0}".format(re.escape(versionStartsWith))
                            versionRe = re.compile(versionRe, re.UNICODE)
                            for line in output.splitlines():
                                if versionRe.search(line):
                                    try:
                                        version = line.split()[versionPosition]
                                        if versionCleanup:
                                            version = version[
                                                versionCleanup[0] : versionCleanup[1]
                                            ]
                                        break
                                    except IndexError:
                                        version = self.tr("(unknown)")
                                        available = False
                            else:
                                version = self.tr("(unknown)")
                                available = False
                    else:
                        version = self.tr("(not executable)")
                        available = False
                if exeModule:
                    citm = QTreeWidgetItem(
                        itm, ["{0} {1}".format(exe, " ".join(exeModule)), version]
                    )
                else:
                    citm = QTreeWidgetItem(itm, [exe, version])
                citm.setData(0, self.ToolAvailableRole, available)
                itm.setExpanded(True)
            else:
                if itm.childCount() == 0:
                    itm.setText(1, self.tr("(not found)"))
                else:
                    citm = QTreeWidgetItem(itm, [rememberedExe, self.tr("(not found)")])
                    citm.setData(0, self.ToolAvailableRole, False)
                    itm.setExpanded(True)
        QApplication.processEvents()
        self.programsList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.programsList.header().setStretchLastSection(True)
        return version

    def __createEntry(self, description, entryText, entryVersion):
        """
        Private method to generate a program entry.

        @param description descriptive text
        @type str
        @param entryText text to show
        @type str
        @param entryVersion version string to show
        @type str
        """
        itm = QTreeWidgetItem(self.programsList, [description])
        font = itm.font(0)
        font.setBold(True)
        itm.setFont(0, font)

        if len(entryVersion):
            citm = QTreeWidgetItem(itm, [entryText, entryVersion])
            itm.setExpanded(True)
            citm.setData(0, self.ToolAvailableRole, not entryVersion.startswith("("))
            # assume version starting with '(' is an unavailability
        else:
            itm.setText(1, self.tr("(not found)"))
        QApplication.processEvents()
        self.programsList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.programsList.header().setStretchLastSection(True)

    @pyqtSlot(int)
    def on_showComboBox_currentIndexChanged(self, index):
        """
        Private slot to apply the selected show criteria.

        @param index index of the show criterium
        @type int
        """
        if index == 0:
            # All Supported Tools
            for topIndex in range(self.programsList.topLevelItemCount()):
                topItem = self.programsList.topLevelItem(topIndex)
                for childIndex in range(topItem.childCount()):
                    topItem.child(childIndex).setHidden(False)
                topItem.setHidden(False)
        else:
            # 1 = Available Tools Only
            # 2 = Unavailable Tools Only
            for topIndex in range(self.programsList.topLevelItemCount()):
                topItem = self.programsList.topLevelItem(topIndex)
                if topItem.childCount() == 0:
                    topItem.setHidden(index == 1)
                else:
                    availabilityList = []
                    for childIndex in range(topItem.childCount()):
                        childItem = topItem.child(childIndex)
                        available = childItem.data(0, self.ToolAvailableRole)
                        if index == 1:
                            childItem.setHidden(not available)
                        else:
                            childItem.setHidden(available)
                        availabilityList.append(available)
                    if index == 1:
                        topItem.setHidden(not any(availabilityList))
                    else:
                        topItem.setHidden(all(availabilityList))
