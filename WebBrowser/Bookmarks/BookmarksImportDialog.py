# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for importing bookmarks from other sources.
"""

import os

from PyQt6.QtCore import QSize, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QListWidgetItem

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import OSUtilities

from . import BookmarksImporters
from .Ui_BookmarksImportDialog import Ui_BookmarksImportDialog


class BookmarksImportDialog(QDialog, Ui_BookmarksImportDialog):
    """
    Class implementing a dialog for importing bookmarks from other sources.
    """

    SourcesListIdRole = Qt.ItemDataRole.UserRole

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.filePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)

        self.sourcesList.setIconSize(QSize(48, 48))
        for icon, displayText, idText in BookmarksImporters.getImporters():
            itm = QListWidgetItem(icon, displayText, self.sourcesList)
            itm.setData(self.SourcesListIdRole, idText)
        self.sourcesList.sortItems()

        self.__currentPage = 0
        self.__selectedSource = ""
        self.__topLevelBookmarkNode = None
        self.__sourceFile = ""
        self.__sourceDir = ""

        self.pagesWidget.setCurrentIndex(self.__currentPage)
        self.__enableNextButton()

    def __enableNextButton(self):
        """
        Private slot to set the enabled state of the next button.
        """
        if self.__currentPage == 0:
            self.nextButton.setEnabled(len(self.sourcesList.selectedItems()) == 1)
        elif self.__currentPage == 1:
            self.nextButton.setEnabled(self.filePicker.text() != "")

    @pyqtSlot()
    def on_sourcesList_itemSelectionChanged(self):
        """
        Private slot to handle changes of the selection of the import source.
        """
        self.__enableNextButton()

    @pyqtSlot(str)
    def on_filePicker_textChanged(self, _txt):
        """
        Private slot handling changes of the file to import bookmarks form.

        @param _txt text of the line edit (unused)
        @type str
        """
        self.__enableNextButton()

    @pyqtSlot()
    def on_nextButton_clicked(self):
        """
        Private slot to switch to the next page.
        """
        if self.sourcesList.currentItem() is None:
            return

        if self.__currentPage == 0:
            self.__selectedSource = self.sourcesList.currentItem().data(
                self.SourcesListIdRole
            )
            (
                pixmap,
                sourceName,
                self.__sourceFile,
                info,
                prompt,
                self.__sourceDir,
            ) = BookmarksImporters.getImporterInfo(self.__selectedSource)

            self.iconLabel.setPixmap(pixmap)
            self.importingFromLabel.setText(
                self.tr("<b>Importing from {0}</b>").format(sourceName)
            )
            self.fileLabel1.setText(info)
            self.fileLabel2.setText(prompt)
            self.standardDirLabel.setText("<i>{0}</i>".format(self.__sourceDir))

            self.nextButton.setText(self.tr("Finish"))

            self.__currentPage += 1
            self.pagesWidget.setCurrentIndex(self.__currentPage)
            self.__enableNextButton()

            if self.__selectedSource == "ie":
                self.filePicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
                self.filePicker.setText(self.__sourceDir)
            else:
                self.filePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
                if OSUtilities.isMacPlatform():
                    fileFilter = "*{0}".format(os.path.splitext(self.__sourceFile)[1])
                else:
                    fileFilter = self.__sourceFile
                self.filePicker.setFilters(fileFilter)
                self.filePicker.setText(
                    os.path.join(self.__sourceDir, self.__sourceFile)
                )
            self.filePicker.setDefaultDirectory(self.__sourceDir)

        elif self.__currentPage == 1:
            if self.filePicker.text() == "":
                return

            importer = BookmarksImporters.getImporter(self.__selectedSource)
            importer.setPath(self.filePicker.text())
            if importer.open():
                self.__topLevelBookmarkNode = importer.importedBookmarks()
            if importer.error():
                EricMessageBox.critical(
                    self, self.tr("Error importing bookmarks"), importer.errorString()
                )
                return

            self.accept()

    @pyqtSlot()
    def on_cancelButton_clicked(self):
        """
        Private slot documentation goes here.
        """
        self.reject()

    def getImportedBookmarks(self):
        """
        Public method to get the imported bookmarks.

        @return top level bookmark
        @rtype BookmarkNode
        """
        return self.__topLevelBookmarkNode
