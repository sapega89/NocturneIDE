# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to compare two files.
"""

import contextlib
import os
import pathlib
import time

from difflib import context_diff, unified_diff

from PyQt6.QtCore import QEvent, QTimer, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QWidget

from eric7 import Preferences
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .DiffHighlighter import DiffHighlighter
from .Ui_DiffDialog import Ui_DiffDialog


class DiffDialog(QWidget, Ui_DiffDialog):
    """
    Class implementing a dialog to compare two files.
    """

    def __init__(self, files=None, parent=None):
        """
        Constructor

        @param files list of two file names to be diffed
        @type list of [str, str]
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.file1Picker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.file2Picker.setMode(EricPathPickerModes.OPEN_FILE_MODE)

        self.diffButton = self.buttonBox.addButton(
            self.tr("Compare"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.diffButton.setToolTip(
            self.tr("Press to perform the comparison of the two files")
        )
        self.saveButton = self.buttonBox.addButton(
            self.tr("Save"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.saveButton.setToolTip(self.tr("Save the output to a patch file"))
        self.diffButton.setEnabled(False)
        self.saveButton.setEnabled(False)
        self.diffButton.setDefault(True)

        self.searchWidget.attachTextEdit(self.contents)

        self.filename1 = ""
        self.filename2 = ""

        self.updateInterval = 20  # update every 20 lines

        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.contents.document().setDefaultFont(font)

        self.highlighter = DiffHighlighter(self.contents.document())

        # connect some of our widgets explicitly
        self.file1Picker.textChanged.connect(self.__fileChanged)
        self.file2Picker.textChanged.connect(self.__fileChanged)

        if bool(files) and len(files) == 2:
            self.file1Picker.setText(files[0])
            self.file2Picker.setText(files[1])
            QTimer.singleShot(0, self.on_diffButton_clicked)

    def show(self, filename=None):
        """
        Public slot to show the dialog.

        @param filename name of a file to use as the first file
        @type str
        """
        if filename:
            self.file1Picker.setText(filename)
        super().show()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.diffButton:
            self.on_diffButton_clicked()
        elif button == self.saveButton:
            self.on_saveButton_clicked()

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot to handle the Save button press.

        It saves the diff shown in the dialog to a file in the local
        filesystem.
        """
        dname, fname = FileSystemUtilities.splitPath(self.filename2)
        fname = "{0}.diff".format(self.filename2) if fname != "." else dname

        fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Save Diff"),
            fname,
            self.tr("Patch Files (*.diff)"),
            None,
            EricFileDialog.DontConfirmOverwrite,
        )

        if not fname:
            return

        fpath = pathlib.Path(fname)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)
        if fpath.exists():
            res = EricMessageBox.yesNo(
                self,
                self.tr("Save Diff"),
                self.tr(
                    "<p>The patch file <b>{0}</b> already exists. Overwrite it?</p>"
                ).format(fpath),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return

        txt = self.contents.toPlainText()
        try:
            with fpath.open("w", encoding="utf-8") as f, contextlib.suppress(
                UnicodeError
            ):
                f.write(txt)
        except OSError as why:
            EricMessageBox.critical(
                self,
                self.tr("Save Diff"),
                self.tr(
                    "<p>The patch file <b>{0}</b> could not be saved.<br />"
                    "Reason: {1}</p>"
                ).format(fpath, str(why)),
            )

    @pyqtSlot()
    def on_diffButton_clicked(self):
        """
        Private slot to handle the Compare button press.
        """
        self.filename1 = FileSystemUtilities.toNativeSeparators(self.file1Picker.text())
        try:
            filemtime1 = time.ctime(os.stat(self.filename1).st_mtime)
        except OSError:
            filemtime1 = ""
        try:
            with open(self.filename1, "r", encoding="utf-8") as f1:
                lines1 = f1.readlines()
        except OSError:
            EricMessageBox.critical(
                self,
                self.tr("Compare Files"),
                self.tr("""<p>The file <b>{0}</b> could not be read.</p>""").format(
                    self.filename1
                ),
            )
            return

        self.filename2 = FileSystemUtilities.toNativeSeparators(self.file2Picker.text())
        try:
            filemtime2 = time.ctime(os.stat(self.filename2).st_mtime)
        except OSError:
            filemtime2 = ""
        try:
            with open(self.filename2, "r", encoding="utf-8") as f2:
                lines2 = f2.readlines()
        except OSError:
            EricMessageBox.critical(
                self,
                self.tr("Compare Files"),
                self.tr("""<p>The file <b>{0}</b> could not be read.</p>""").format(
                    self.filename2
                ),
            )
            return

        self.highlighter.regenerateRules(
            {
                "text": Preferences.getDiffColour("TextColor"),
                "added": Preferences.getDiffColour("AddedColor"),
                "removed": Preferences.getDiffColour("RemovedColor"),
                "replaced": Preferences.getDiffColour("ReplacedColor"),
                "context": Preferences.getDiffColour("ContextColor"),
                "header": Preferences.getDiffColour("HeaderColor"),
                "whitespace": Preferences.getDiffColour("BadWhitespaceColor"),
            },
            Preferences.getEditorOtherFonts("MonospacedFont"),
        )

        self.contents.clear()
        self.saveButton.setEnabled(False)

        if self.unifiedRadioButton.isChecked():
            self.__generateUnifiedDiff(
                lines1, lines2, self.filename1, self.filename2, filemtime1, filemtime2
            )
        else:
            self.__generateContextDiff(
                lines1, lines2, self.filename1, self.filename2, filemtime1, filemtime2
            )

        tc = self.contents.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Start)
        self.contents.setTextCursor(tc)
        self.contents.ensureCursorVisible()

        self.saveButton.setEnabled(True)

    def __appendText(self, txt):
        """
        Private method to append text to the end of the contents pane.

        @param txt text to insert
        @type str
        """
        tc = self.contents.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.End)
        self.contents.setTextCursor(tc)
        self.contents.insertPlainText(txt)

    def __generateUnifiedDiff(self, a, b, fromfile, tofile, fromfiledate, tofiledate):
        """
        Private slot to generate a unified diff output.

        @param a first sequence of lines
        @type list of str
        @param b second sequence of lines
        @type list of str
        @param fromfile filename of the first file
        @type str
        @param tofile filename of the second file
        @type str
        @param fromfiledate modification time of the first file
        @type str
        @param tofiledate modification time of the second file
        @type str
        """
        for paras, line in enumerate(
            unified_diff(a, b, fromfile, tofile, fromfiledate, tofiledate)
        ):
            self.__appendText(line)
            if not (paras % self.updateInterval):
                QApplication.processEvents()

        if self.contents.toPlainText().strip() == "":
            self.__appendText(self.tr("There is no difference."))

    def __generateContextDiff(self, a, b, fromfile, tofile, fromfiledate, tofiledate):
        """
        Private slot to generate a context diff output.

        @param a first sequence of lines
        @type list of str
        @param b second sequence of lines
        @type list of str
        @param fromfile filename of the first file
        @type str
        @param tofile filename of the second file
        @type str
        @param fromfiledate modification time of the first file
        @type str
        @param tofiledate modification time of the second file
        @type str
        """
        for paras, line in enumerate(
            context_diff(a, b, fromfile, tofile, fromfiledate, tofiledate)
        ):
            self.__appendText(line)
            if not (paras % self.updateInterval):
                QApplication.processEvents()

        if self.contents.toPlainText().strip() == "":
            self.__appendText(self.tr("There is no difference."))

    def __fileChanged(self):
        """
        Private slot to enable/disable the Compare button.
        """
        if not self.file1Picker.text() or not self.file2Picker.text():
            self.diffButton.setEnabled(False)
        else:
            self.diffButton.setEnabled(True)


class DiffWindow(EricMainWindow):
    """
    Main window class for the standalone dialog.
    """

    def __init__(self, files=None, parent=None):
        """
        Constructor

        @param files list of two file names to be diffed
        @type list of [str, str]
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.cw = DiffDialog(files=files, parent=self)
        self.cw.installEventFilter(self)
        size = self.cw.size()
        self.setCentralWidget(self.cw)
        self.resize(size)

    def eventFilter(self, _obj, event):
        """
        Public method to filter events.

        @param _obj reference to the object the event is meant for (unused)
        @type QObject
        @param event reference to the event object
        @type QEvent
        @return flag indicating, whether the event was handled
        @rtype bool
        """
        if event.type() == QEvent.Type.Close:
            QApplication.exit()
            return True

        return False
