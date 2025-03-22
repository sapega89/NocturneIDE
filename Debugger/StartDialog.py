# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Start Program dialog.
"""

import enum
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QInputDialog

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_StartDialog import Ui_StartDialog


class StartDialogMode(enum.Enum):
    """
    Class defining the various modes of the start dialog.
    """

    Debug = 0
    Run = 1
    Coverage = 2
    Profile = 3


class StartDialog(QDialog, Ui_StartDialog):
    """
    Class implementing the Start dialog.

    It implements a dialog that is used to start an
    application for debugging. It asks the user to enter
    the commandline parameters, the working directory and
    whether exception reporting should be disabled.
    """

    def __init__(
        self,
        caption,
        lastUsedVenvName,
        argvList,
        wdList,
        envList,
        parent=None,
        dialogMode=StartDialogMode.Debug,
        modfuncList=None,
        autoClearShell=True,
        tracePython=False,
        autoContinue=True,
        reportAllExceptions=False,
        enableMultiprocess=False,
        multiprocessNoDebugHistory=None,
        configOverride=None,
        forProject=False,
        scriptName="",
        scriptsList=None,
    ):
        """
        Constructor

        @param caption caption to be displayed
        @type str
        @param lastUsedVenvName name of the most recently used virtual
            environment
        @type str
        @param argvList history list of command line arguments
        @type list of str
        @param wdList history list of working directories
        @type list of str
        @param envList history list of environment parameter settings
        @type list of str
        @param parent parent widget of this dialog
        @type QWidget
        @param dialogMode mode of the start dialog
                <ul>
                <li>StartDialogMode.Debug = start debug dialog</li>
                <li>StartDialogMode.Run = start run dialog</li>
                <li>StartDialogMode.Coverage = start coverage dialog</li>
                <li>StartDialogMode.Profile = start profile dialog</li>
                </ul>
        @type StartDialogMode
        @param modfuncList history list of module functions
        @type list of str
        @param autoClearShell flag indicating, that the interpreter window
            should be cleared automatically
        @type bool
        @param tracePython flag indicating if the Python library should
            be traced as well
        @type bool
        @param autoContinue flag indicating, that the debugger should not
            stop at the first executable line
        @type bool
        @param reportAllExceptions flag indicating to report all exceptions
        @type bool
        @param enableMultiprocess flag indicating the support for multi process
            debugging
        @type bool
        @param multiprocessNoDebugHistory list of lists with programs not to be
            debugged
        @type list of str
        @param configOverride dictionary containing the global config override
            data
        @type dict
        @param forProject flag indicating to get the parameters for a
            run/debug/... action for a project
        @type bool
        @param scriptName name of the script
        @type str
        @param scriptsList history list of script names
        @type list of str
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setModal(True)

        self.__dialogMode = dialogMode
        self.debugGroup.setVisible(self.__dialogMode == StartDialogMode.Debug)
        self.coverageGroup.setVisible(self.__dialogMode == StartDialogMode.Coverage)
        self.profileGroup.setVisible(self.__dialogMode == StartDialogMode.Profile)
        # nothing special for 'Run' mode

        self.venvComboBox.addItem("")
        projectEnvironmentString = (
            ericApp().getObject("DebugServer").getProjectEnvironmentString()
        )
        if projectEnvironmentString:
            self.venvComboBox.addItem(projectEnvironmentString)
        if ericApp().getObject("EricServer").isServerConnected():
            self.venvComboBox.addItems(
                sorted(
                    ericApp()
                    .getObject("VirtualEnvManager")
                    .getEricServerEnvironmentNames(
                        host=ericApp().getObject("EricServer").getHostName()
                    )
                )
            )
        else:
            self.venvComboBox.addItems(
                sorted(
                    ericApp()
                    .getObject("VirtualEnvManager")
                    .getVirtualenvNames(noServer=True)
                )
            )

        self.scriptnamePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.scriptnamePicker.setDefaultDirectory(
            Preferences.getMultiProject("Workspace")
        )
        self.scriptnamePicker.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.scriptnamePicker.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.scriptnamePicker.setFilters(
            self.tr(
                "Python Files (*.py *.py3);;"
                "Python GUI Files (*.pyw *.pyw3);;"
                "All Files (*)"
            )
        )
        self.scriptnamePicker.setEnabled(not forProject)

        self.workdirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.workdirPicker.setDefaultDirectory(Preferences.getMultiProject("Workspace"))
        self.workdirPicker.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.workdirPicker.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )

        self.clearButton = self.buttonBox.addButton(
            self.tr("Clear Histories"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.editButton = self.buttonBox.addButton(
            self.tr("Edit History"), QDialogButtonBox.ButtonRole.ActionRole
        )

        self.setWindowTitle(caption)
        self.cmdlineCombo.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive
        )
        self.cmdlineCombo.lineEdit().setClearButtonEnabled(True)
        self.cmdlineCombo.clear()
        self.cmdlineCombo.addItems(argvList)
        if len(argvList) > 0:
            self.cmdlineCombo.setCurrentIndex(0)

        self.workdirPicker.clear()
        self.workdirPicker.addItems(wdList)
        if len(wdList) > 0:
            self.workdirPicker.setCurrentIndex(0)

        self.environmentCombo.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive
        )
        self.environmentCombo.lineEdit().setClearButtonEnabled(True)
        self.environmentCombo.clear()
        self.environmentCombo.addItems(envList)

        self.clearShellCheckBox.setChecked(autoClearShell)
        self.consoleCheckBox.setEnabled(
            Preferences.getDebugger("ConsoleDbgCommand") != ""
        )
        self.consoleCheckBox.setChecked(False)

        venvIndex = max(0, self.venvComboBox.findText(lastUsedVenvName))
        self.venvComboBox.setCurrentIndex(venvIndex)
        self.globalOverrideGroup.setChecked(configOverride["enable"])
        self.redirectCheckBox.setChecked(configOverride["redirect"])

        self.scriptnamePicker.setRemote(
            FileSystemUtilities.isRemoteFileName(scriptName)
        )
        self.workdirPicker.setRemote(FileSystemUtilities.isRemoteFileName(scriptName))

        self.scriptnamePicker.addItems(scriptsList)
        self.scriptnamePicker.setText(scriptName)

        if dialogMode == StartDialogMode.Debug:
            enableMultiprocessGlobal = Preferences.getDebugger("MultiProcessEnabled")
            self.tracePythonCheckBox.setChecked(tracePython)
            self.tracePythonCheckBox.show()
            self.autoContinueCheckBox.setChecked(autoContinue)
            self.allExceptionsCheckBox.setChecked(reportAllExceptions)
            self.multiprocessGroup.setEnabled(enableMultiprocessGlobal)
            self.multiprocessGroup.setChecked(
                enableMultiprocess & enableMultiprocessGlobal
            )
            self.multiprocessNoDebugCombo.clear()
            self.multiprocessNoDebugCombo.setToolTip(
                self.tr(
                    "Enter the list of programs or program patterns not to be"
                    " debugged separated by '{0}'."
                ).format(os.pathsep)
            )
            self.multiprocessNoDebugCombo.lineEdit().setClearButtonEnabled(True)
            if multiprocessNoDebugHistory:
                self.multiprocessNoDebugCombo.completer().setCaseSensitivity(
                    Qt.CaseSensitivity.CaseSensitive
                )
                self.multiprocessNoDebugCombo.addItems(multiprocessNoDebugHistory)
                self.multiprocessNoDebugCombo.setCurrentIndex(0)

        if dialogMode == StartDialogMode.Coverage:
            self.eraseCoverageCheckBox.setChecked(True)

        if dialogMode == StartDialogMode.Profile:
            self.eraseProfileCheckBox.setChecked(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        self.__clearHistoryLists = False
        self.__historiesModified = False

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def on_modFuncCombo_editTextChanged(self):
        """
        Private slot to enable/disable the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setDisabled(
            self.modFuncCombo.currentText() == ""
        )

    def getData(self):
        """
        Public method to retrieve the data entered into this dialog.

        @return tuple containing the virtual environment, script name, argv, workdir,
            environment, clear interpreter flag and run in console flag
        @rtype tuple of (str, str, str, str, str, bool, bool)
        """
        cmdLine = self.cmdlineCombo.currentText()
        workdir = self.workdirPicker.currentText(toNative=False)
        environment = self.environmentCombo.currentText()
        venvName = self.venvComboBox.currentText()
        scriptName = (
            self.scriptnamePicker.currentText()
            if self.scriptnamePicker.isEnabled()
            else ""
        )

        return (
            venvName,
            scriptName,
            cmdLine,
            workdir,
            environment,
            self.clearShellCheckBox.isChecked(),
            self.consoleCheckBox.isChecked(),
        )

    def getGlobalOverrideData(self):
        """
        Public method to retrieve the global configuration override data
        entered into this dialog.

        @return dictionary containing a flag indicating to activate the global
            override and a flag indicating a redirect of stdin/stdout/stderr
        @rtype dict
        """
        return {
            "enable": self.globalOverrideGroup.isChecked(),
            "redirect": self.redirectCheckBox.isChecked(),
        }

    def getDebugData(self):
        """
        Public method to retrieve the debug related data entered into this
        dialog.

        @return tuple containing a flag indicating, if the Python library should be
            traced as well, a flag indicating, that the debugger should not
            stop at the first executable line, a flag indicating to report all
            exceptions, a flag indicating to support multi process debugging and a
            space separated list of programs not to be debugged
        @rtype tuple of (bool, bool, bool, bool, str)
        """
        if self.__dialogMode == StartDialogMode.Debug:
            return (
                self.tracePythonCheckBox.isChecked(),
                self.autoContinueCheckBox.isChecked(),
                self.allExceptionsCheckBox.isChecked(),
                self.multiprocessGroup.isChecked(),
                self.multiprocessNoDebugCombo.currentText(),
            )
        else:
            return (False, False, False, False, "")

    def getCoverageData(self):
        """
        Public method to retrieve the coverage related data entered into this
        dialog.

        @return flag indicating erasure of coverage info
        @rtype bool
        """
        if self.__dialogMode == StartDialogMode.Coverage:
            return self.eraseCoverageCheckBox.isChecked()
        else:
            return False

    def getProfilingData(self):
        """
        Public method to retrieve the profiling related data entered into this
        dialog.

        @return flag indicating erasure of profiling info
        @rtype bool
        """
        if self.__dialogMode == StartDialogMode.Profile:
            return self.eraseProfileCheckBox.isChecked()
        else:
            return False

    def __clearHistories(self):
        """
        Private slot to clear the combo boxes lists and record a flag to
        clear the lists.
        """
        self.__clearHistoryLists = True
        self.__historiesModified = False  # clear catches it all

        cmdLine = self.cmdlineCombo.currentText()
        workdir = self.workdirPicker.currentText()
        environment = self.environmentCombo.currentText()
        scriptName = self.scriptnamePicker.currentText()

        self.cmdlineCombo.clear()
        self.workdirPicker.clear()
        self.environmentCombo.clear()
        self.scriptnamePicker.clear()

        self.cmdlineCombo.addItem(cmdLine)
        self.workdirPicker.addItem(workdir)
        self.environmentCombo.addItem(environment)
        self.scriptnamePicker.addItem("")
        self.scriptnamePicker.setCurrentText(scriptName)

        if self.__dialogMode == StartDialogMode.Debug:
            noDebugList = self.multiprocessNoDebugCombo.currentText()
            self.multiprocessNoDebugCombo.clear()
            self.multiprocessNoDebugCombo.addItem(noDebugList)

    def __editHistory(self):
        """
        Private slot to edit a history list.
        """
        from .StartHistoryEditDialog import StartHistoryEditDialog

        histories = [
            "",
            self.tr("Script Name"),
            self.tr("Script Parameters"),
            self.tr("Working Directory"),
            self.tr("Environment"),
        ]
        widgets = [
            None,
            self.scriptnamePicker,
            self.cmdlineCombo,
            self.workdirPicker,
            self.environmentCombo,
        ]
        if self.__dialogMode == StartDialogMode.Debug:
            histories.append(self.tr("No Debug Programs"))
            widgets.append(self.multiprocessNoDebugCombo)
        historyKind, ok = QInputDialog.getItem(
            self,
            self.tr("Edit History"),
            self.tr("Select the history list to be edited:"),
            histories,
            0,
            False,
        )
        if ok and historyKind:
            history = []
            historiesIndex = histories.index(historyKind)
            if historiesIndex in (1, 3):
                picker = widgets[historiesIndex]
                history = picker.getPathItems()
            else:
                combo = widgets[historiesIndex]
                if combo:
                    history = [combo.itemText(idx) for idx in range(combo.count())]

            if history:
                dlg = StartHistoryEditDialog(history, parent=self)
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    history = dlg.getHistory()
                    combo = widgets[historiesIndex]
                    if combo:
                        combo.clear()
                        combo.addItems(history)

                        self.__historiesModified = True

    def historiesModified(self):
        """
        Public method to test for modified histories.

        @return flag indicating modified histories
        @rtype bool
        """
        return self.__historiesModified

    def clearHistories(self):
        """
        Public method to test, if histories shall be cleared.

        @return flag indicating histories shall be cleared
        @rtype bool
        """
        return self.__clearHistoryLists

    def getHistories(self):
        """
        Public method to get the lists of histories.

        @return tuple containing the histories of script names, command line
            arguments, working directories, environment settings and no debug
            programs lists
        @rtype tuple of five list of str
        """
        noDebugHistory = (
            [
                self.multiprocessNoDebugCombo.itemText(index)
                for index in range(self.multiprocessNoDebugCombo.count())
            ]
            if self.__dialogMode == StartDialogMode.Debug
            else None
        )
        return (
            self.scriptnamePicker.getPathItems(),
            [
                self.cmdlineCombo.itemText(index)
                for index in range(self.cmdlineCombo.count())
            ],
            self.workdirPicker.getPathItems(),
            [
                self.environmentCombo.itemText(index)
                for index in range(self.environmentCombo.count())
            ],
            noDebugHistory,
        )

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.clearButton:
            self.__clearHistories()
        elif button == self.editButton:
            self.__editHistory()
