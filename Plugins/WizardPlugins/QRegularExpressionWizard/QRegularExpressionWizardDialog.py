# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the QRegularExpression wizard dialog.
"""

import json
import os
import pathlib
import re

from PyQt6.QtCore import QByteArray, QProcess, pyqtSlot
from PyQt6.QtGui import QClipboard, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.SystemUtilities import FileSystemUtilities, PythonUtilities

from .Ui_QRegularExpressionWizardDialog import Ui_QRegularExpressionWizardDialog


class QRegularExpressionWizardWidget(QWidget, Ui_QRegularExpressionWizardDialog):
    """
    Class implementing the QRegularExpression wizard dialog.
    """

    def __init__(self, parent=None, fromEric=True):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        @param fromEric flag indicating a call from within eric
        @type bool
        """
        super().__init__(parent)
        self.setupUi(self)

        # initialize icons of the tool buttons
        self.commentButton.setIcon(EricPixmapCache.getIcon("comment"))
        self.charButton.setIcon(EricPixmapCache.getIcon("characters"))
        self.anycharButton.setIcon(EricPixmapCache.getIcon("anychar"))
        self.repeatButton.setIcon(EricPixmapCache.getIcon("repeat"))
        self.nonGroupButton.setIcon(EricPixmapCache.getIcon("nongroup"))
        self.atomicGroupButton.setIcon(EricPixmapCache.getIcon("atomicgroup"))
        self.groupButton.setIcon(EricPixmapCache.getIcon("group"))
        self.namedGroupButton.setIcon(EricPixmapCache.getIcon("namedgroup"))
        self.namedReferenceButton.setIcon(EricPixmapCache.getIcon("namedreference"))
        self.altnButton.setIcon(EricPixmapCache.getIcon("altn"))
        self.beglineButton.setIcon(EricPixmapCache.getIcon("begline"))
        self.endlineButton.setIcon(EricPixmapCache.getIcon("endline"))
        self.wordboundButton.setIcon(EricPixmapCache.getIcon("wordboundary"))
        self.nonwordboundButton.setIcon(EricPixmapCache.getIcon("nonwordboundary"))
        self.poslookaheadButton.setIcon(EricPixmapCache.getIcon("poslookahead"))
        self.neglookaheadButton.setIcon(EricPixmapCache.getIcon("neglookahead"))
        self.poslookbehindButton.setIcon(EricPixmapCache.getIcon("poslookbehind"))
        self.neglookbehindButton.setIcon(EricPixmapCache.getIcon("neglookbehind"))
        self.undoButton.setIcon(EricPixmapCache.getIcon("editUndo"))
        self.redoButton.setIcon(EricPixmapCache.getIcon("editRedo"))

        self.namedGroups = re.compile(r"""\(?P<([^>]+)>""").findall

        # start the PyQt6 server part
        self.__pyqt6Available = False
        self.__pyqt6Server = QProcess(self)
        self.__pyqt6Server.start(
            PythonUtilities.getPythonExecutable(),
            [
                os.path.join(
                    os.path.dirname(__file__), "QRegularExpressionWizardServer.py"
                )
            ],
        )
        if self.__pyqt6Server.waitForStarted(5000):
            self.__pyqt6Server.setReadChannel(QProcess.ProcessChannel.StandardOutput)
            if self.__sendCommand("available"):
                response = self.__receiveResponse()
                if response and response["available"]:
                    self.__pyqt6Available = True

        self.saveButton = self.buttonBox.addButton(
            self.tr("Save"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.saveButton.setToolTip(self.tr("Save the regular expression to a file"))
        self.loadButton = self.buttonBox.addButton(
            self.tr("Load"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.loadButton.setToolTip(self.tr("Load a regular expression from a file"))
        if self.__pyqt6Available:
            self.validateButton = self.buttonBox.addButton(
                self.tr("Validate"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.validateButton.setToolTip(self.tr("Validate the regular expression"))
            self.executeButton = self.buttonBox.addButton(
                self.tr("Execute"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.executeButton.setToolTip(self.tr("Execute the regular expression"))
            self.nextButton = self.buttonBox.addButton(
                self.tr("Next match"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.nextButton.setToolTip(
                self.tr("Show the next match of the regular expression")
            )
            self.nextButton.setEnabled(False)
        else:
            self.validateButton = None
            self.executeButton = None
            self.nextButton = None

        if fromEric:
            self.buttonBox.setStandardButtons(
                QDialogButtonBox.StandardButton.Cancel
                | QDialogButtonBox.StandardButton.Ok
            )
            self.copyButton = None
        else:
            self.copyButton = self.buttonBox.addButton(
                self.tr("Copy"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.copyButton.setToolTip(
                self.tr("Copy the regular expression to the clipboard")
            )
            self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)
            self.variableLabel.hide()
            self.variableLineEdit.hide()
            self.variableLine.hide()
            self.regexpTextEdit.setFocus()

    def __sendCommand(self, command, **kw):
        """
        Private method to send a command to the server.

        @param command dictionary with command string and related data
        @type dict
        @keyparam kw parameters for the command
        @type dict
        @return flag indicating a successful transmission
        @rtype bool
        """
        result = False
        if command:
            commandDict = {"command": command}
            commandDict.update(kw)
            commandStr = json.dumps(commandDict) + "\n"
            data = QByteArray(commandStr.encode("utf-8"))
            self.__pyqt6Server.write(data)
            result = self.__pyqt6Server.waitForBytesWritten(10000)
        return result

    def __receiveResponse(self):
        """
        Private method to receive a response from the server.

        @return response dictionary
        @rtype dict
        """
        responseDict = {}
        if self.__pyqt6Server.waitForReadyRead(10000):
            data = bytes(self.__pyqt6Server.readAllStandardOutput())
            responseStr = data.decode("utf-8")
            responseDict = json.loads(responseStr)
            if responseDict["error"]:
                EricMessageBox.critical(
                    self,
                    self.tr("Communication Error"),
                    self.tr(
                        """<p>The backend reported an error.</p><p>{0}</p>"""
                    ).format(responseDict["error"]),
                )
                responseDict = {}

        return responseDict

    def shutdown(self):
        """
        Public method to shut down the server part.
        """
        self.__sendCommand("exit")
        self.__pyqt6Server.waitForFinished(5000)

    def __insertString(self, s, steps=0):
        """
        Private method to insert a string into line edit and move cursor.

        @param s string to be inserted into the regexp line edit
        @type str
        @param steps number of characters to move the cursor. Negative steps
            move cursor back, positive steps forward.
        @type int
        """
        self.regexpTextEdit.insertPlainText(s)
        tc = self.regexpTextEdit.textCursor()
        if steps != 0:
            if steps < 0:
                act = QTextCursor.MoveOperation.Left
                steps = abs(steps)
            else:
                act = QTextCursor.MoveOperation.Right
            for _ in range(steps):
                tc.movePosition(act)
        self.regexpTextEdit.setTextCursor(tc)

    @pyqtSlot()
    def on_commentButton_clicked(self):
        """
        Private slot to handle the comment toolbutton.
        """
        self.__insertString("(?#)", -1)

    @pyqtSlot()
    def on_charButton_clicked(self):
        """
        Private slot to handle the characters toolbutton.
        """
        from .QRegularExpressionWizardCharactersDialog import (
            QRegularExpressionWizardCharactersDialog,
        )

        dlg = QRegularExpressionWizardCharactersDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.__insertString(dlg.getCharacters())

    @pyqtSlot()
    def on_anycharButton_clicked(self):
        """
        Private slot to handle the any character toolbutton.
        """
        self.__insertString(".")

    @pyqtSlot()
    def on_repeatButton_clicked(self):
        """
        Private slot to handle the repeat toolbutton.
        """
        from .QRegularExpressionWizardRepeatDialog import (
            QRegularExpressionWizardRepeatDialog,
        )

        dlg = QRegularExpressionWizardRepeatDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.__insertString(dlg.getRepeat())

    @pyqtSlot()
    def on_nonGroupButton_clicked(self):
        """
        Private slot to handle the non group toolbutton.
        """
        self.__insertString("(?:)", -1)

    @pyqtSlot()
    def on_atomicGroupButton_clicked(self):
        """
        Private slot to handle the atomic non group toolbutton.
        """
        self.__insertString("(?>)", -1)

    @pyqtSlot()
    def on_groupButton_clicked(self):
        """
        Private slot to handle the group toolbutton.
        """
        self.__insertString("()", -1)

    @pyqtSlot()
    def on_namedGroupButton_clicked(self):
        """
        Private slot to handle the named group toolbutton.
        """
        self.__insertString("(?P<>)", -2)

    @pyqtSlot()
    def on_namedReferenceButton_clicked(self):
        """
        Private slot to handle the named reference toolbutton.
        """
        # determine cursor position as length into text
        length = self.regexpTextEdit.textCursor().position()

        # only present group names that occur before the current
        # cursor position
        regex = self.regexpTextEdit.toPlainText()[:length]
        names = self.namedGroups(regex)
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Named reference"),
                self.tr("""No named groups have been defined yet."""),
            )
            return

        groupName, ok = QInputDialog.getItem(
            self,
            self.tr("Named reference"),
            self.tr("Select group name:"),
            names,
            0,
            True,
        )
        if ok and groupName:
            self.__insertString("(?P={0})".format(groupName))

    @pyqtSlot()
    def on_altnButton_clicked(self):
        """
        Private slot to handle the alternatives toolbutton.
        """
        self.__insertString("(|)", -2)

    @pyqtSlot()
    def on_beglineButton_clicked(self):
        """
        Private slot to handle the begin line toolbutton.
        """
        self.__insertString("^")

    @pyqtSlot()
    def on_endlineButton_clicked(self):
        """
        Private slot to handle the end line toolbutton.
        """
        self.__insertString("$")

    @pyqtSlot()
    def on_wordboundButton_clicked(self):
        """
        Private slot to handle the word boundary toolbutton.
        """
        self.__insertString("\\b")

    @pyqtSlot()
    def on_nonwordboundButton_clicked(self):
        """
        Private slot to handle the non word boundary toolbutton.
        """
        self.__insertString("\\B")

    @pyqtSlot()
    def on_poslookaheadButton_clicked(self):
        """
        Private slot to handle the positive lookahead toolbutton.
        """
        self.__insertString("(?=)", -1)

    @pyqtSlot()
    def on_neglookaheadButton_clicked(self):
        """
        Private slot to handle the negative lookahead toolbutton.
        """
        self.__insertString("(?!)", -1)

    @pyqtSlot()
    def on_poslookbehindButton_clicked(self):
        """
        Private slot to handle the positive lookbehind toolbutton.
        """
        self.__insertString("(?<=)", -1)

    @pyqtSlot()
    def on_neglookbehindButton_clicked(self):
        """
        Private slot to handle the negative lookbehind toolbutton.
        """
        self.__insertString("(?<!)", -1)

    @pyqtSlot()
    def on_undoButton_clicked(self):
        """
        Private slot to handle the undo action.
        """
        self.regexpTextEdit.document().undo()

    @pyqtSlot()
    def on_redoButton_clicked(self):
        """
        Private slot to handle the redo action.
        """
        self.regexpTextEdit.document().redo()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.validateButton:
            self.on_validateButton_clicked()
        elif button == self.executeButton:
            self.on_executeButton_clicked()
        elif button == self.saveButton:
            self.on_saveButton_clicked()
        elif button == self.loadButton:
            self.on_loadButton_clicked()
        elif button == self.nextButton:
            self.on_nextButton_clicked()
        elif self.copyButton and button == self.copyButton:
            self.on_copyButton_clicked()

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot to save the QRegularExpression to a file.
        """
        fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Save regular expression"),
            "",
            self.tr("RegExp Files (*.rx);;All Files (*)"),
            None,
            EricFileDialog.DontConfirmOverwrite,
        )
        if fname:
            fpath = pathlib.Path(fname)
            if not fpath.suffix:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fpath = fpath.with_suffix(ex)
            if fpath.exists():
                res = EricMessageBox.yesNo(
                    self,
                    self.tr("Save regular expression"),
                    self.tr(
                        "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                    ).format(fpath),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return

            try:
                with fpath.open("w", encoding="utf-8") as f:
                    f.write(self.regexpTextEdit.toPlainText())
            except OSError as err:
                EricMessageBox.information(
                    self,
                    self.tr("Save regular expression"),
                    self.tr(
                        """<p>The regular expression could not"""
                        """ be saved.</p><p>Reason: {0}</p>"""
                    ).format(str(err)),
                )

    @pyqtSlot()
    def on_loadButton_clicked(self):
        """
        Private slot to load a QRegularExpression from a file.
        """
        fname = EricFileDialog.getOpenFileName(
            self,
            self.tr("Load regular expression"),
            "",
            self.tr("RegExp Files (*.rx);;All Files (*)"),
        )
        if fname:
            fname = FileSystemUtilities.toNativeSeparators(fname)
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    regexp = f.read()
                self.regexpTextEdit.setPlainText(regexp)
            except OSError as err:
                EricMessageBox.information(
                    self,
                    self.tr("Save regular expression"),
                    self.tr(
                        """<p>The regular expression could not"""
                        """ be saved.</p><p>Reason: {0}</p>"""
                    ).format(str(err)),
                )

    @pyqtSlot()
    def on_copyButton_clicked(self):
        """
        Private slot to copy the QRegularExpression string into the clipboard.

        This slot is only available, if not called from within eric.
        """
        escaped = self.regexpTextEdit.toPlainText()
        if escaped:
            escaped = escaped.replace("\\", "\\\\")
            cb = QApplication.clipboard()
            cb.setText(escaped, QClipboard.Mode.Clipboard)
            if cb.supportsSelection():
                cb.setText(escaped, QClipboard.Mode.Selection)

    @pyqtSlot()
    def on_validateButton_clicked(self):
        """
        Private slot to validate the entered QRegularExpression.
        """
        if not self.__pyqt6Available:
            # only available for PyQt6
            return

        regexp = self.regexpTextEdit.toPlainText()
        if regexp:
            options = []
            if self.caseInsensitiveCheckBox.isChecked():
                options.append("CaseInsensitiveOption")
            if self.multilineCheckBox.isChecked():
                options.append("MultilineOption")
            if self.dotallCheckBox.isChecked():
                options.append("DotMatchesEverythingOption")
            if self.extendedCheckBox.isChecked():
                options.append("ExtendedPatternSyntaxOption")
            if self.greedinessCheckBox.isChecked():
                options.append("InvertedGreedinessOption")
            if self.unicodeCheckBox.isChecked():
                options.append("UseUnicodePropertiesOption")
            if self.captureCheckBox.isChecked():
                options.append("DontCaptureOption")

            if self.__sendCommand("validate", options=options, regexp=regexp):
                response = self.__receiveResponse()
                if response and "valid" in response:
                    if response["valid"]:
                        EricMessageBox.information(
                            self,
                            self.tr("Validation"),
                            self.tr("""The regular expression is valid."""),
                        )
                    else:
                        EricMessageBox.critical(
                            self,
                            self.tr("Error"),
                            self.tr("""Invalid regular expression: {0}""").format(
                                response["errorMessage"]
                            ),
                        )
                        # move cursor to error offset
                        offset = response["errorOffset"]
                        tc = self.regexpTextEdit.textCursor()
                        tc.setPosition(offset)
                        self.regexpTextEdit.setTextCursor(tc)
                        self.regexpTextEdit.setFocus()
                        return
                else:
                    EricMessageBox.critical(
                        self,
                        self.tr("Communication Error"),
                        self.tr("""Invalid response received from backend."""),
                    )
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Communication Error"),
                    self.tr("""Communication with backend failed."""),
                )
        else:
            EricMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("""A regular expression must be given."""),
            )

    @pyqtSlot()
    def on_executeButton_clicked(self, startpos=0):
        """
        Private slot to execute the entered QRegularExpression on the test
        text.

        This slot will execute the entered QRegularExpression on the entered
        test data and will display the result in the table part of the dialog.

        @param startpos starting position for the QRegularExpression matching
        @type int
        """
        if not self.__pyqt6Available:
            # only available for PyQt6
            return

        regexp = self.regexpTextEdit.toPlainText()
        text = self.textTextEdit.toPlainText()
        if regexp and text:
            options = []
            if self.caseInsensitiveCheckBox.isChecked():
                options.append("CaseInsensitiveOption")
            if self.multilineCheckBox.isChecked():
                options.append("MultilineOption")
            if self.dotallCheckBox.isChecked():
                options.append("DotMatchesEverythingOption")
            if self.extendedCheckBox.isChecked():
                options.append("ExtendedPatternSyntaxOption")
            if self.greedinessCheckBox.isChecked():
                options.append("InvertedGreedinessOption")
            if self.unicodeCheckBox.isChecked():
                options.append("UseUnicodePropertiesOption")
            if self.captureCheckBox.isChecked():
                options.append("DontCaptureOption")

            if self.__sendCommand(
                "execute", options=options, regexp=regexp, text=text, startpos=startpos
            ):
                response = self.__receiveResponse()
                if response and ("valid" in response or "matched" in response):
                    if "valid" in response:
                        EricMessageBox.critical(
                            self,
                            self.tr("Error"),
                            self.tr("""Invalid regular expression: {0}""").format(
                                response["errorMessage"]
                            ),
                        )
                        # move cursor to error offset
                        offset = response["errorOffset"]
                        tc = self.regexpTextEdit.textCursor()
                        tc.setPosition(offset)
                        self.regexpTextEdit.setTextCursor(tc)
                        self.regexpTextEdit.setFocus()
                        return
                    else:
                        row = 0
                        OFFSET = 5

                        self.resultTable.setColumnCount(0)
                        self.resultTable.setColumnCount(3)
                        self.resultTable.setRowCount(0)
                        self.resultTable.setRowCount(OFFSET)
                        self.resultTable.setItem(
                            row, 0, QTableWidgetItem(self.tr("Regexp"))
                        )
                        self.resultTable.setItem(row, 1, QTableWidgetItem(regexp))
                        if response["matched"]:
                            captures = response["captures"]
                            # index 0 is the complete match
                            offset = captures[0][1]
                            self.lastMatchEnd = captures[0][2]
                            self.nextButton.setEnabled(True)
                            row += 1
                            self.resultTable.setItem(
                                row, 0, QTableWidgetItem(self.tr("Offset"))
                            )
                            self.resultTable.setItem(
                                row, 1, QTableWidgetItem("{0:d}".format(offset))
                            )

                            row += 1
                            self.resultTable.setItem(
                                row, 0, QTableWidgetItem(self.tr("Captures"))
                            )
                            self.resultTable.setItem(
                                row,
                                1,
                                QTableWidgetItem("{0:d}".format(len(captures) - 1)),
                            )
                            row += 1
                            self.resultTable.setItem(
                                row, 1, QTableWidgetItem(self.tr("Text"))
                            )
                            self.resultTable.setItem(
                                row, 2, QTableWidgetItem(self.tr("Characters"))
                            )

                            row += 1
                            self.resultTable.setItem(
                                row, 0, QTableWidgetItem(self.tr("Match"))
                            )
                            self.resultTable.setItem(
                                row, 1, QTableWidgetItem(captures[0][0])
                            )
                            self.resultTable.setItem(
                                row, 2, QTableWidgetItem("{0:d}".format(captures[0][3]))
                            )

                            for i in range(1, len(captures)):
                                if captures[i][0]:
                                    row += 1
                                    self.resultTable.insertRow(row)
                                    self.resultTable.setItem(
                                        row,
                                        0,
                                        QTableWidgetItem(
                                            self.tr("Capture #{0}").format(i)
                                        ),
                                    )
                                    self.resultTable.setItem(
                                        row, 1, QTableWidgetItem(captures[i][0])
                                    )
                                    self.resultTable.setItem(
                                        row,
                                        2,
                                        QTableWidgetItem(
                                            "{0:d}".format(captures[i][3])
                                        ),
                                    )

                            # highlight the matched text
                            tc = self.textTextEdit.textCursor()
                            tc.setPosition(offset)
                            tc.setPosition(
                                self.lastMatchEnd, QTextCursor.MoveMode.KeepAnchor
                            )
                            self.textTextEdit.setTextCursor(tc)
                        else:
                            self.nextButton.setEnabled(False)
                            self.resultTable.setRowCount(2)
                            row += 1
                            if startpos > 0:
                                self.resultTable.setItem(
                                    row, 0, QTableWidgetItem(self.tr("No more matches"))
                                )
                            else:
                                self.resultTable.setItem(
                                    row, 0, QTableWidgetItem(self.tr("No matches"))
                                )

                            # remove the highlight
                            tc = self.textTextEdit.textCursor()
                            tc.setPosition(0)
                            self.textTextEdit.setTextCursor(tc)

                        self.resultTable.resizeColumnsToContents()
                        self.resultTable.resizeRowsToContents()
                        self.resultTable.verticalHeader().hide()
                        self.resultTable.horizontalHeader().hide()
                else:
                    EricMessageBox.critical(
                        self,
                        self.tr("Communication Error"),
                        self.tr("""Invalid response received from backend."""),
                    )
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Communication Error"),
                    self.tr("""Communication with  backend failed."""),
                )
        else:
            EricMessageBox.critical(
                self,
                self.tr("Error"),
                self.tr("""A regular expression and a text must be given."""),
            )

    @pyqtSlot()
    def on_nextButton_clicked(self):
        """
        Private slot to find the next match.
        """
        self.on_executeButton_clicked(self.lastMatchEnd)

    @pyqtSlot()
    def on_regexpTextEdit_textChanged(self):
        """
        Private slot called when the regexp changes.
        """
        if self.nextButton:
            self.nextButton.setEnabled(False)

    def getCode(self, indLevel, indString):
        """
        Public method to get the source code.

        @param indLevel indentation level
        @type int
        @param indString string used for indentation (space or tab)
        @type str
        @return generated code
        @rtype str
        """
        # calculate the indentation string
        i1string = (indLevel + 1) * indString
        estring = os.linesep + indLevel * indString

        # now generate the code
        reVar = self.variableLineEdit.text()
        if not reVar:
            reVar = "regexp"

        regexp = self.regexpTextEdit.toPlainText()

        options = []
        if self.caseInsensitiveCheckBox.isChecked():
            options.append("QRegularExpression.PatternOption.CaseInsensitiveOption")
        if self.multilineCheckBox.isChecked():
            options.append("QRegularExpression.PatternOption.MultilineOption")
        if self.dotallCheckBox.isChecked():
            options.append(
                "QRegularExpression.PatternOption.DotMatchesEverythingOption"
            )
        if self.extendedCheckBox.isChecked():
            options.append(
                "QRegularExpression.PatternOption.ExtendedPatternSyntaxOption"
            )
        if self.greedinessCheckBox.isChecked():
            options.append("QRegularExpression.PatternOption.InvertedGreedinessOption")
        if self.unicodeCheckBox.isChecked():
            options.append(
                "QRegularExpression.PatternOption.UseUnicodePropertiesOption"
            )
        if self.captureCheckBox.isChecked():
            options.append("QRegularExpression.PatternOption.DontCaptureOption")
        options = "{0}{1}| ".format(os.linesep, i1string).join(options)

        code = "{0} = QRegularExpression(".format(reVar)
        if options:
            code += '{0}{1}r"""{2}""",'.format(
                os.linesep, i1string, regexp.replace('"', '\\"')
            )
            code += "{0}{1}{2}".format(os.linesep, i1string, options)
        else:
            code += 'r"""{0}"""'.format(regexp.replace('"', '\\"'))
        code += ",{0}){0}".format(estring)
        return code


class QRegularExpressionWizardDialog(QDialog):
    """
    Class for the dialog variant.
    """

    def __init__(self, parent=None, fromEric=True):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        @param fromEric flag indicating a call from within eric
        @type bool
        """
        super().__init__(parent)
        self.setModal(fromEric)
        self.setSizeGripEnabled(True)

        self.__layout = QVBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        self.cw = QRegularExpressionWizardWidget(self, fromEric)
        size = self.cw.size()
        self.__layout.addWidget(self.cw)
        self.resize(size)
        self.setWindowTitle(self.cw.windowTitle())

        self.cw.buttonBox.accepted.connect(self.accept)
        self.cw.buttonBox.rejected.connect(self.reject)

    def getCode(self, indLevel, indString):
        """
        Public method to get the source code.

        @param indLevel indentation level
        @type int
        @param indString string used for indentation (space or tab)
        @type str
        @return generated code
        @rtype str
        """
        return self.cw.getCode(indLevel, indString)

    def accept(self):
        """
        Public slot to hide the dialog and set the result code to Accepted.
        """
        self.cw.shutdown()
        super().accept()

    def reject(self):
        """
        Public slot to hide the dialog and set the result code to Rejected.
        """
        self.cw.shutdown()
        super().reject()


class QRegularExpressionWizardWindow(EricMainWindow):
    """
    Main window class for the standalone dialog.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.cw = QRegularExpressionWizardWidget(self, fromEric=False)
        size = self.cw.size()
        self.setCentralWidget(self.cw)
        self.resize(size)
        self.setWindowTitle(self.cw.windowTitle())

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.cw.buttonBox.accepted.connect(self.close)
        self.cw.buttonBox.rejected.connect(self.close)

    def closeEvent(self, evt):
        """
        Protected method handling the close event.

        @param evt close event
        @type QCloseEvent
        """
        self.cw.shutdown()
        super().closeEvent(evt)
