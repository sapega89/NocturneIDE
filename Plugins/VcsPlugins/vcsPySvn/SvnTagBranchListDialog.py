# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show a list of tags or branches.
"""

import os
import re

import pysvn

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QTreeWidgetItem,
)

from eric7.EricUtilities.EricMutexLocker import EricMutexLocker
from eric7.EricWidgets import EricMessageBox

from .SvnDialogMixin import SvnDialogMixin
from .SvnUtilities import formatTime
from .Ui_SvnTagBranchListDialog import Ui_SvnTagBranchListDialog


class SvnTagBranchListDialog(QDialog, SvnDialogMixin, Ui_SvnTagBranchListDialog):
    """
    Class implementing a dialog to show a list of tags or branches.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Subversion
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        SvnDialogMixin.__init__(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.vcs = vcs

        self.tagList.headerItem().setText(self.tagList.columnCount(), "")
        self.tagList.header().setSortIndicator(3, Qt.SortOrder.AscendingOrder)

        self.client = self.vcs.getClient()
        self.client.callback_cancel = self._clientCancelCallback
        self.client.callback_get_login = self._clientLoginCallback
        self.client.callback_ssl_server_trust_prompt = (
            self._clientSslServerTrustPromptCallback
        )

    def start(self, path, tags=True):
        """
        Public slot to start the svn status command.

        @param path name of directory to be listed
        @type str
        @param tags flag indicating a list of tags is requested
            (False = branches, True = tags)
        @type bool
        @return flag indicating success
        @rtype bool
        """
        self.errorGroup.hide()

        self.tagList.clear()

        if not tags:
            self.setWindowTitle(self.tr("Subversion Branches List"))
        self.activateWindow()
        QApplication.processEvents()

        dname, _fname = self.vcs.splitPath(path)

        reposURL = self.vcs.svnGetReposName(dname)
        if reposURL is None:
            EricMessageBox.critical(
                self,
                self.tr("Subversion Error"),
                self.tr(
                    """The URL of the project repository could not be"""
                    """ retrieved from the working copy. The list operation"""
                    """ will be aborted"""
                ),
            )
            self.close()
            return False

        if self.vcs.otherData["standardLayout"]:
            # determine the base path of the project in the repository
            rx_base = re.compile("(.+)/(trunk|tags|branches).*")
            match = rx_base.fullmatch(reposURL)
            if match is None:
                EricMessageBox.critical(
                    self,
                    self.tr("Subversion Error"),
                    self.tr(
                        """The URL of the project repository has an"""
                        """ invalid format. The list operation will"""
                        """ be aborted"""
                    ),
                )
                return False

            reposRoot = match.group(1)

            if tags:
                path = "{0}/tags".format(reposRoot)
            else:
                path = "{0}/branches".format(reposRoot)
        else:
            reposPath, ok = QInputDialog.getText(
                self,
                self.tr("Subversion List"),
                self.tr("Enter the repository URL containing the tags or branches"),
                QLineEdit.EchoMode.Normal,
                self.vcs.svnNormalizeURL(reposURL),
            )
            if not ok:
                self.close()
                return False
            if not reposPath:
                EricMessageBox.critical(
                    self,
                    self.tr("Subversion List"),
                    self.tr("""The repository URL is empty. Aborting..."""),
                )
                self.close()
                return False
            path = reposPath

        self.tagsList = []
        cwd = os.getcwd()
        os.chdir(dname)
        try:
            with EricMutexLocker(self.vcs.vcsExecutionMutex):
                entries = self.client.list(path, recurse=False)
            for dirent, _lock in entries:
                if dirent["path"] != path:
                    name = dirent["path"].replace(path + "/", "")
                    self.__generateItem(
                        dirent["created_rev"].number,
                        dirent["last_author"],
                        formatTime(dirent["time"]),
                        name,
                    )
                    if self.vcs.otherData["standardLayout"]:
                        self.tagsList.append(name)
                    else:
                        self.tagsList.append(path + "/" + name)
                    if self._clientCancelCallback():
                        break
            res = True
        except pysvn.ClientError as e:
            self.__showError(e.args[0])
            res = False
        except AttributeError:
            self.__showError(
                self.tr("The installed version of PySvn should be 1.4.0 or better.")
            )
            res = False
        self.__finish()
        os.chdir(cwd)
        return res

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed the
        button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.__resizeColumns()
        self.__resort()

        self._cancel()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__finish()

    def __showError(self, msg):
        """
        Private slot to show an error message.

        @param msg error message to show
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(msg)
        self.errors.ensureCursorVisible()

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.tagList.sortItems(
            self.tagList.sortColumn(), self.tagList.header().sortIndicatorOrder()
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.tagList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.tagList.header().setStretchLastSection(True)

    def __generateItem(self, revision, author, date, name):
        """
        Private method to generate a tag item in the taglist.

        @param revision revision number
        @type int
        @param author author of the tag
        @type str
        @param date date of the tag
        @type str
        @param name name (path) of the tag
        @type str
        """
        itm = QTreeWidgetItem(self.tagList)
        itm.setData(0, Qt.ItemDataRole.DisplayRole, revision)
        itm.setData(1, Qt.ItemDataRole.DisplayRole, author)
        itm.setData(2, Qt.ItemDataRole.DisplayRole, date)
        itm.setData(3, Qt.ItemDataRole.DisplayRole, name)
        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)

    def getTagList(self):
        """
        Public method to get the taglist of the last run.

        @return list of tags
        @rtype list of str
        """
        return self.tagsList
