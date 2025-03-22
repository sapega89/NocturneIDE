# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data for an image markup.
"""

import contextlib
import enum

from PyQt6.QtCore import QSize, pyqtSlot
from PyQt6.QtGui import QImage, QImageReader
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_ImageMarkupDialog import Ui_ImageMarkupDialog


class ImageMarkupMode(enum.Enum):
    """
    Class defining the image markup modes.
    """

    Html = 0
    MarkDown = 1
    Rest = 2


class ImageMarkupDialog(QDialog, Ui_ImageMarkupDialog):
    """
    Class implementing a dialog to enter data for an image markup.
    """

    def __init__(self, mode, parent=None):
        """
        Constructor

        @param mode mode of the dialog
        @type int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if mode == ImageMarkupMode.MarkDown:
            self.sizeCheckBox.setEnabled(False)
            self.aspectRatioCheckBox.setEnabled(False)
            self.widthSpinBox.setEnabled(False)
            self.heightSpinBox.setEnabled(False)
        elif mode == ImageMarkupMode.Rest:
            self.titleEdit.setEnabled(False)

        self.__mode = mode
        self.__originalImageSize = QSize()

        filters = {
            "bmp": self.tr("Windows Bitmap File (*.bmp)"),
            "cur": self.tr("Windows Cursor File (*.cur)"),
            "dds": self.tr("DirectDraw-Surface File (*.dds)"),
            "gif": self.tr("Graphic Interchange Format File (*.gif)"),
            "icns": self.tr("Apple Icon File (*.icns)"),
            "ico": self.tr("Windows Icon File (*.ico)"),
            "jp2": self.tr("JPEG2000 File (*.jp2)"),
            "jpg": self.tr("JPEG File (*.jpg)"),
            "jpeg": self.tr("JPEG File (*.jpeg)"),
            "mng": self.tr("Multiple-Image Network Graphics File (*.mng)"),
            "pbm": self.tr("Portable Bitmap File (*.pbm)"),
            "pcx": self.tr("Paintbrush Bitmap File (*.pcx)"),
            "pgm": self.tr("Portable Graymap File (*.pgm)"),
            "png": self.tr("Portable Network Graphics File (*.png)"),
            "ppm": self.tr("Portable Pixmap File (*.ppm)"),
            "sgi": self.tr("Silicon Graphics Image File (*.sgi)"),
            "svg": self.tr("Scalable Vector Graphics File (*.svg)"),
            "svgz": self.tr("Compressed Scalable Vector Graphics File (*.svgz)"),
            "tga": self.tr("Targa Graphic File (*.tga)"),
            "tif": self.tr("TIFF File (*.tif)"),
            "tiff": self.tr("TIFF File (*.tiff)"),
            "wbmp": self.tr("WAP Bitmap File (*.wbmp)"),
            "webp": self.tr("WebP Image File (*.webp)"),
            "xbm": self.tr("X11 Bitmap File (*.xbm)"),
            "xpm": self.tr("X11 Pixmap File (*.xpm)"),
        }

        inputFormats = []
        readFormats = QImageReader.supportedImageFormats()
        for readFormat in readFormats:
            with contextlib.suppress(KeyError):
                inputFormats.append(filters[bytes(readFormat).decode()])
        inputFormats.sort()
        inputFormats.append(self.tr("All Files (*)"))
        if filters["png"] in inputFormats:
            inputFormats.remove(filters["png"])
            inputFormats.insert(0, filters["png"])
        self.imagePicker.setFilters(";;".join(inputFormats))
        self.imagePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)

        self.sizeCheckBox.setChecked(True)
        self.aspectRatioCheckBox.setChecked(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

        self.__updateOkButton()

    def __updateOkButton(self):
        """
        Private slot to set the state of the OK button.
        """
        enable = bool(self.imagePicker.text())
        if self.__mode == ImageMarkupMode.MarkDown:
            enable = enable and bool(self.altTextEdit.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(str)
    def on_imagePicker_textChanged(self, address):
        """
        Private slot handling changes of the image path.

        @param address image address (URL or local path)
        @type str
        """
        if address and "://" not in address:
            image = QImage(address)
            # load the file to set the size spin boxes
            if image.isNull():
                self.widthSpinBox.setValue(0)
                self.heightSpinBox.setValue(0)
                self.__originalImageSize = QSize()
                self.__aspectRatio = 1
            else:
                self.widthSpinBox.setValue(image.width())
                self.heightSpinBox.setValue(image.height())
                self.__originalImageSize = image.size()
                self.__aspectRatio = (
                    float(self.__originalImageSize.height())
                    / self.__originalImageSize.width()
                )
        else:
            self.widthSpinBox.setValue(0)
            self.heightSpinBox.setValue(0)
            self.__originalImageSize = QSize()
            self.__aspectRatio = 1

        self.__updateOkButton()

    @pyqtSlot(str)
    def on_altTextEdit_textChanged(self, _txt):
        """
        Private slot handling changes of the alternative text.

        @param _txt alternative text (unused)
        @type str
        """
        self.__updateOkButton()

    @pyqtSlot(bool)
    def on_sizeCheckBox_toggled(self, checked):
        """
        Private slot to reset the width and height spin boxes.

        @param checked flag indicating the state of the check box
        @type bool
        """
        if checked:
            self.widthSpinBox.setValue(self.__originalImageSize.width())
            self.heightSpinBox.setValue(self.__originalImageSize.height())

    @pyqtSlot(bool)
    def on_aspectRatioCheckBox_toggled(self, checked):
        """
        Private slot to adjust the height to match the original aspect ratio.

        @param checked flag indicating the state of the check box
        @type bool
        """
        if checked and self.__originalImageSize.isValid():
            height = self.widthSpinBox.value() * self.__aspectRatio
            self.heightSpinBox.setValue(height)

    @pyqtSlot(int)
    def on_widthSpinBox_valueChanged(self, width):
        """
        Private slot to adjust the height spin box.

        @param width width for the image
        @type int
        """
        if self.aspectRatioCheckBox.isChecked() and self.widthSpinBox.hasFocus():
            height = width * self.__aspectRatio
            self.heightSpinBox.setValue(height)

    @pyqtSlot(int)
    def on_heightSpinBox_valueChanged(self, height):
        """
        Private slot to adjust the width spin box.

        @param height height for the image
        @type int
        """
        if self.aspectRatioCheckBox.isChecked() and self.heightSpinBox.hasFocus():
            width = height / self.__aspectRatio
            self.widthSpinBox.setValue(width)

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the image address, alternative text,
            title text, flag to keep the original size, width and height
        @rtype tuple of (str, str, str, bool, int, int)
        """
        return (
            self.imagePicker.text(),
            self.altTextEdit.text(),
            self.titleEdit.text(),
            self.sizeCheckBox.isChecked(),
            self.widthSpinBox.value(),
            self.heightSpinBox.value(),
        )
