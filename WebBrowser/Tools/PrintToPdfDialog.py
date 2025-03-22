# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for printing a web page to PDF.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QPageLayout
from PyQt6.QtPrintSupport import QPageSetupDialog
from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_PrintToPdfDialog import Ui_PrintToPdfDialog


class PrintToPdfDialog(QDialog, Ui_PrintToPdfDialog):
    """
    Class implementing a dialog to enter the data for printing a web page to
    PDF.
    """

    def __init__(self, printer, parent=None):
        """
        Constructor

        @param printer reference to an initialized QPrinter object
        @type QPrinter
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__printer = printer

        self.pdfFilePicker.setMode(EricPathPickerModes.SAVE_FILE_OVERWRITE_MODE)
        self.pdfFilePicker.setFilters(self.tr("PDF Files (*.pdf);;All Files (*)"))
        self.pdfFilePicker.setText(self.__printer.outputFileName(), toNative=True)

        self.__updatePageLayoutLabel()

    @pyqtSlot()
    def on_pageLayoutButton_clicked(self):
        """
        Private slot to define the page layout.
        """
        dlg = QPageSetupDialog(self.__printer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.__updatePageLayoutLabel()

    def __updatePageLayoutLabel(self):
        """
        Private method to update the page layout label.
        """
        orientation = (
            self.tr("Portrait")
            if (
                self.__printer.pageLayout().orientation()
                == QPageLayout.Orientation.Portrait
            )
            else self.tr("Landscape")
        )
        self.pageLayoutLabel.setText(
            self.tr("{0}, {1}", "page size, page orientation").format(
                self.__printer.pageLayout().pageSize().name(), orientation
            )
        )

    def getData(self):
        """
        Public method to get the dialog data.

        @return tuple containing the file path and the page layout
        @rtype tuple of str and QPageLayout
        """
        return (
            self.pdfFilePicker.text(toNative=True),
            self.__printer.pageLayout(),
        )
