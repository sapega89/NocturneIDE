# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to write speed dial data files.
"""

from PyQt6.QtCore import QFile, QIODevice, QXmlStreamWriter


class SpeedDialWriter(QXmlStreamWriter):
    """
    Class implementing a writer object to generate speed dial data files.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.setAutoFormatting(True)

    def write(self, fileNameOrDevice, pages, pagesPerRow, speedDialSize):
        """
        Public method to write a speed dial data file.

        @param fileNameOrDevice name of the file to write or device to write to
        @type str or QIODevice
        @param pages list of speed dial pages
        @type list of Page
        @param pagesPerRow number of pages per row
        @type int
        @param speedDialSize size of the speed dial pages
        @type int
        @return flag indicating success
        @rtype bool
        """
        if isinstance(fileNameOrDevice, QIODevice):
            f = fileNameOrDevice
        else:
            f = QFile(fileNameOrDevice)
            if not f.open(QIODevice.OpenModeFlag.WriteOnly):
                return False

        self.setDevice(f)
        return self.__write(pages, pagesPerRow, speedDialSize)

    def __write(self, pages, pagesPerRow, speedDialSize):
        """
        Private method to write a speed dial file.

        @param pages list of speed dial pages
        @type list of Page
        @param pagesPerRow number of pages per row
        @type int
        @param speedDialSize size of the speed dial pages
        @type int
        @return flag indicating success
        @rtype bool
        """
        self.writeStartDocument()
        self.writeDTD("<!DOCTYPE speeddial>")
        self.writeStartElement("SpeedDial")
        self.writeAttribute("version", "1.0")

        self.writeStartElement("Pages")
        self.writeAttribute("row", str(pagesPerRow))
        self.writeAttribute("size", str(speedDialSize))

        for page in pages:
            self.writeEmptyElement("Page")
            self.writeAttribute("url", page.url)
            self.writeAttribute("title", page.title)

        self.writeEndDocument()
        return True
