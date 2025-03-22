# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an info widget showing data of a PDF document.
"""

from PyQt6.QtCore import QFileInfo, Qt, pyqtSlot
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import QFormLayout, QLabel, QWidget

from eric7.Globals import dataString


class PdfInfoWidget(QWidget):
    """
    Class implementing an info widget showing data of a PDF document.
    """

    def __init__(self, document, parent=None):
        """
        Constructor

        @param document reference to the PDF document object
        @type QPdfDocument
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.__document = None

        self.__layout = QFormLayout(self)
        self.__layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.__layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        self.__layout.setFormAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.__layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.__infoLabels = {
            "filePath": QLabel(),
            "fileSize": QLabel(),
            "title": QLabel(),
            "subject": QLabel(),
            "author": QLabel(),
            "creator": QLabel(),
            "producer": QLabel(),
            "pages": QLabel(),
            "creationDate": QLabel(),
            "modificationDate": QLabel(),
            "keywords": QLabel(),
            "security": QLabel(),
        }
        for label in self.__infoLabels.values():
            label.setWordWrap(True)
        self.__layout.addRow(self.tr("File Path:"), self.__infoLabels["filePath"])
        self.__layout.addRow(self.tr("File Size:"), self.__infoLabels["fileSize"])
        self.__layout.addRow(self.tr("Title:"), self.__infoLabels["title"])
        self.__layout.addRow(self.tr("Subject:"), self.__infoLabels["subject"])
        self.__layout.addRow(self.tr("Author:"), self.__infoLabels["author"])
        self.__layout.addRow(self.tr("Created with:"), self.__infoLabels["creator"])
        self.__layout.addRow(self.tr("Creator:"), self.__infoLabels["producer"])
        self.__layout.addRow(self.tr("Pages:"), self.__infoLabels["pages"])
        self.__layout.addRow(self.tr("Created at:"), self.__infoLabels["creationDate"])
        self.__layout.addRow(
            self.tr("Last Modified at:"), self.__infoLabels["modificationDate"]
        )
        self.__layout.addRow(self.tr("Keywords:"), self.__infoLabels["keywords"])
        self.__layout.addRow(self.tr("Security:"), self.__infoLabels["security"])

        self.setLayout(self.__layout)

        self.setDocument(document)

    def setDocument(self, document):
        """
        Public method to set the reference to the PDF document.

        @param document reference to the document
        @type QPdfDocument
        """
        if self.__document is not None:
            self.__document.statusChanged.disconnect(self.__populateInfoLabels)
            self.__document.pageCountChanged.disconnect(self.__handlePageCountChanged)
            self.__document.passwordChanged.disconnect(self.__handlePasswordChanged)

        self.__document = document

        if document is not None:
            self.__document.statusChanged.connect(self.__populateInfoLabels)
            self.__document.pageCountChanged.connect(self.__handlePageCountChanged)
            self.__document.passwordChanged.connect(self.__handlePasswordChanged)

    @pyqtSlot(QPdfDocument.Status)
    def __populateInfoLabels(self, status):
        """
        Private slot to populate the info labels upon a change of the document status.

        @param status document status
        @type QPdfDocument.Status
        """
        ready = status == QPdfDocument.Status.Ready

        self.__infoLabels["title"].setText(
            self.__document.metaData(QPdfDocument.MetaDataField.Title) if ready else ""
        )
        self.__infoLabels["subject"].setText(
            self.__document.metaData(QPdfDocument.MetaDataField.Subject)
            if ready
            else ""
        )
        self.__infoLabels["author"].setText(
            self.__document.metaData(QPdfDocument.MetaDataField.Author) if ready else ""
        )
        self.__infoLabels["creator"].setText(
            self.__document.metaData(QPdfDocument.MetaDataField.Creator)
            if ready
            else ""
        )
        self.__infoLabels["producer"].setText(
            self.__document.metaData(QPdfDocument.MetaDataField.Producer)
            if ready
            else ""
        )
        self.__infoLabels["pages"].setText(
            str(self.__document.pageCount()) if ready else ""
        )
        self.__infoLabels["creationDate"].setText(
            self.__document.metaData(QPdfDocument.MetaDataField.CreationDate).toString(
                "yyyy-MM-dd hh:mm:ss t"
            )
            if ready
            else ""
        )
        self.__infoLabels["modificationDate"].setText(
            self.__document.metaData(
                QPdfDocument.MetaDataField.ModificationDate
            ).toString("yyyy-MM-dd hh:mm:ss t")
            if ready
            else ""
        )
        self.__infoLabels["keywords"].setText(
            self.__document.metaData(QPdfDocument.MetaDataField.Keywords)
            if ready
            else ""
        )

        if ready:
            self.__handlePasswordChanged()
        else:
            self.__infoLabels["security"].setText("")

    @pyqtSlot(int)
    def __handlePageCountChanged(self, pageCount):
        """
        Private slot to handle a change of the page count.

        @param pageCount changed page count
        @type int
        """
        self.__infoLabels["pages"].setText(str(pageCount))

    @pyqtSlot()
    def __handlePasswordChanged(self):
        """
        Private slot to handle a change of the password.
        """
        self.__infoLabels["security"].setText(
            self.tr("Encrypted")
            if self.__document.password()
            else self.tr("Not Encrypted")
        )

    def setFileName(self, filename):
        """
        Public method to set the file name info.

        @param filename DESCRIPTION
        @type TYPE
        """
        self.__infoLabels["filePath"].setText(filename)
        if filename:
            fi = QFileInfo(filename)
            fileSize = fi.size()
            self.__infoLabels["fileSize"].setText(dataString(fileSize))
        else:
            self.__infoLabels["fileSize"].setText("")
