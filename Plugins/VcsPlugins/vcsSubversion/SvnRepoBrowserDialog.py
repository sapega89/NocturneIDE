# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the subversion repository browser dialog.
"""

import os
import re

from PyQt6.QtCore import QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QTreeWidgetItem,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursorProcess
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_SvnRepoBrowserDialog import Ui_SvnRepoBrowserDialog


class SvnRepoBrowserDialog(QDialog, Ui_SvnRepoBrowserDialog):
    """
    Class implementing the subversion repository browser dialog.
    """

    def __init__(self, vcs, mode="browse", parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Subversion
        @param mode mode of the dialog ("browse" or "select")
        @type str
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.repoTree.headerItem().setText(self.repoTree.columnCount(), "")
        self.repoTree.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.vcs = vcs
        self.mode = mode

        self.__process = EricOverrideCursorProcess()
        self.__process.finished.connect(self.__procFinished)
        self.__process.readyReadStandardOutput.connect(self.__readStdout)
        self.__process.readyReadStandardError.connect(self.__readStderr)

        if self.mode == "select":
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).hide()
        else:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).hide()
            self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).hide()

        self.__dirIcon = EricPixmapCache.getIcon("dirClosed")
        self.__fileIcon = EricPixmapCache.getIcon("fileMisc")

        self.__urlRole = Qt.ItemDataRole.UserRole
        self.__ignoreExpand = False
        self.intercept = False

        self.__rx_dir = re.compile(
            r"""\s*([0-9]+)\s+(\w+)\s+"""
            r"""((?:\w+\s+\d+|[0-9.]+\s+\w+)\s+[0-9:]+)\s+(.+)\s*"""
        )
        self.__rx_file = re.compile(
            r"""\s*([0-9]+)\s+(\w+)\s+([0-9]+)\s"""
            r"""((?:\w+\s+\d+|[0-9.]+\s+\w+)\s+[0-9:]+)\s+(.+)\s*"""
        )

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        e.accept()

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.repoTree.sortItems(
            self.repoTree.sortColumn(), self.repoTree.header().sortIndicatorOrder()
        )

    def __resizeColumns(self):
        """
        Private method to resize the tree columns.
        """
        self.repoTree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.repoTree.header().setStretchLastSection(True)

    def __generateItem(self, repopath, revision, author, size, date, nodekind, url):
        """
        Private method to generate a tree item in the repository tree.

        @param repopath path of the item
        @type str
        @param revision revision info
        @type str
        @param author author info
        @type str
        @param size size info
        @type str
        @param date date info
        @type str
        @param nodekind node kind info ("dir" or "file")
        @type str
        @param url url of the entry
        @type str
        @return reference to the generated item
        @rtype QTreeWidgetItem
        """
        rev = "" if revision == "" else int(revision)
        sz = "" if size == "" else int(size)

        itm = QTreeWidgetItem(self.parentItem)
        itm.setData(0, Qt.ItemDataRole.DisplayRole, repopath)
        itm.setData(1, Qt.ItemDataRole.DisplayRole, rev)
        itm.setData(2, Qt.ItemDataRole.DisplayRole, author)
        itm.setData(3, Qt.ItemDataRole.DisplayRole, sz)
        itm.setData(4, Qt.ItemDataRole.DisplayRole, date)

        if nodekind == "dir":
            itm.setIcon(0, self.__dirIcon)
            itm.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
            )
        elif nodekind == "file":
            itm.setIcon(0, self.__fileIcon)

        itm.setData(0, self.__urlRole, url)

        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignLeft)
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignLeft)
        itm.setTextAlignment(3, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(4, Qt.AlignmentFlag.AlignLeft)

        return itm

    def __repoRoot(self, url):
        """
        Private method to get the repository root using the svn info command.

        @param url the repository URL to browser
        @type str
        @return repository root
        @rtype str
        """
        ioEncoding = Preferences.getSystem("IOEncoding")
        repoRoot = None

        process = QProcess()

        args = []
        args.append("info")
        self.vcs.addArguments(args, self.vcs.options["global"])
        args.append("--xml")
        args.append(url)

        process.start("svn", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished:
                if process.exitCode() == 0:
                    output = str(process.readAllStandardOutput(), ioEncoding, "replace")
                    for line in output.splitlines():
                        line = line.strip()
                        if line.startswith("<root>"):
                            repoRoot = line.replace("<root>", "").replace("</root>", "")
                            break
                else:
                    error = str(
                        process.readAllStandardError(),
                        Preferences.getSystem("IOEncoding"),
                        "replace",
                    )
                    self.errors.insertPlainText(error)
                    self.errors.ensureCursorVisible()
        else:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("svn"),
            )
        return repoRoot

    def __listRepo(self, url, parent=None):
        """
        Private method to perform the svn list command.

        @param url the repository URL to browse
        @type str
        @param parent reference to the item, the data should be appended to
        @type QTreeWidget or QTreeWidgetItem
        """
        self.errorGroup.hide()

        self.repoUrl = url

        if parent is None:
            self.parentItem = self.repoTree
        else:
            self.parentItem = parent

        if self.parentItem == self.repoTree:
            repoRoot = self.__repoRoot(url)
            if repoRoot is None:
                self.__finish()
                return
            self.__ignoreExpand = True
            itm = self.__generateItem(repoRoot, "", "", "", "", "dir", repoRoot)
            itm.setExpanded(True)
            self.parentItem = itm
            urlPart = repoRoot
            for element in url.replace(repoRoot, "").split("/"):
                if element:
                    urlPart = "{0}/{1}".format(urlPart, element)
                    itm = self.__generateItem(element, "", "", "", "", "dir", urlPart)
                    itm.setExpanded(True)
                    self.parentItem = itm
            itm.setExpanded(False)
            self.__ignoreExpand = False
            self.__finish()
            return

        self.intercept = False

        self.__process.kill()

        args = []
        args.append("list")
        self.vcs.addArguments(args, self.vcs.options["global"])
        if "--verbose" not in self.vcs.options["global"]:
            args.append("--verbose")
        args.append(url)

        self.__process.start("svn", args)
        procStarted = self.__process.waitForStarted(5000)
        if not procStarted:
            self.__finish()
            self.inputGroup.setEnabled(False)
            self.inputGroup.hide()
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("svn"),
            )
        else:
            self.inputGroup.setEnabled(True)
            self.inputGroup.show()

    def __normalizeUrl(self, url):
        """
        Private method to normalite the url.

        @param url the url to normalize
        @type str
        @return normalized URL
        @rtype str
        """
        if url.endswith("/"):
            return url[:-1]
        return url

    def start(self, url):
        """
        Public slot to start the svn info command.

        @param url the repository URL to browser
        @type str
        """
        self.repoTree.clear()

        self.url = ""

        url = self.__normalizeUrl(url)
        if self.urlCombo.findText(url) == -1:
            self.urlCombo.addItem(url)

    @pyqtSlot(int)
    def on_urlCombo_currentIndexChanged(self, index):
        """
        Private slot called, when a new repository URL is entered or selected.

        @param index index of the current item
        @type int
        """
        text = self.urlCombo.itemText(index)
        url = self.__normalizeUrl(text)
        if url != self.url:
            self.url = url
            self.repoTree.clear()
            self.__listRepo(url)

    @pyqtSlot(QTreeWidgetItem)
    def on_repoTree_itemExpanded(self, item):
        """
        Private slot called when an item is expanded.

        @param item reference to the item to be expanded
        @type QTreeWidgetItem
        """
        if not self.__ignoreExpand:
            url = item.data(0, self.__urlRole)
            self.__listRepo(url, item)

    @pyqtSlot(QTreeWidgetItem)
    def on_repoTree_itemCollapsed(self, item):
        """
        Private slot called when an item is collapsed.

        @param item reference to the item to be collapsed
        @type QTreeWidgetItem
        """
        for child in item.takeChildren():
            del child

    @pyqtSlot()
    def on_repoTree_itemSelectionChanged(self):
        """
        Private slot called when the selection changes.
        """
        if self.mode == "select":
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)

    def accept(self):
        """
        Public slot called when the dialog is accepted.
        """
        if self.focusWidget() == self.urlCombo:
            return

        super().accept()

    def getSelectedUrl(self):
        """
        Public method to retrieve the selected repository URL.

        @return the selected repository URL
        @rtype str
        """
        items = self.repoTree.selectedItems()
        if len(items) == 1:
            return items[0].data(0, self.__urlRole)
        else:
            return ""

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed the
        button.
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()

        self.__resizeColumns()
        self.__resort()

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        self.__finish()

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        if self.__process is not None:
            self.__process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

            while self.__process.canReadLine():
                s = str(
                    self.__process.readLine(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )
                match = self.__rx_dir.fullmatch(s) or self.__rx_file.fullmatch(s)
                if match is None:
                    continue
                elif match.re is self.__rx_dir:
                    revision = match.group(1)
                    author = match.group(2)
                    date = match.group(3)
                    name = match.group(4).strip()
                    if name.endswith("/"):
                        name = name[:-1]
                    size = ""
                    nodekind = "dir"
                    if name == ".":
                        continue
                elif match.re is self.__rx_file:
                    revision = match.group(1)
                    author = match.group(2)
                    size = match.group(3)
                    date = match.group(4)
                    name = match.group(5).strip()
                    nodekind = "file"

                url = "{0}/{1}".format(self.repoUrl, name)
                self.__generateItem(name, revision, author, size, date, nodekind, url)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.__process is not None:
            s = str(
                self.__process.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.errors.insertPlainText(s)
            self.errors.ensureCursorVisible()
            self.errorGroup.show()

    def on_passwordCheckBox_toggled(self, isOn):
        """
        Private slot to handle the password checkbox toggled.

        @param isOn flag indicating the status of the check box
        @type bool
        """
        if isOn:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)

    @pyqtSlot()
    def on_sendButton_clicked(self):
        """
        Private slot to send the input to the subversion process.
        """
        inputTxt = self.input.text()
        inputTxt += os.linesep

        if self.passwordCheckBox.isChecked():
            self.errors.insertPlainText(os.linesep)
            self.errors.ensureCursorVisible()
        else:
            self.errors.insertPlainText(inputTxt)
            self.errors.ensureCursorVisible()

        self.__process.write(strToQByteArray(inputTxt))

        self.passwordCheckBox.setChecked(False)
        self.input.clear()

    def on_input_returnPressed(self):
        """
        Private slot to handle the press of the return key in the input field.
        """
        self.intercept = True
        self.on_sendButton_clicked()

    def keyPressEvent(self, evt):
        """
        Protected slot to handle a key press event.

        @param evt the key press event
        @type QKeyEvent
        """
        if self.intercept:
            self.intercept = False
            evt.accept()
            return
        super().keyPressEvent(evt)
