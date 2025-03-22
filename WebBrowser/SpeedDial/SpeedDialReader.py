# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing a class to read speed dial data files.
"""

from PyQt6.QtCore import QCoreApplication, QFile, QIODevice, QXmlStreamReader

from .Page import Page


class SpeedDialReader(QXmlStreamReader):
    """
    Class implementing a reader object for speed dial data files.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

    def read(self, fileNameOrDevice):
        """
        Public method to read a user agent file.

        @param fileNameOrDevice name of the file to read or reference to
            the device to read
        @type str or QIODevice
        @return list of speed dial pages, number of pages per row and
            size of the speed dial pages
        @rtype tuple of (list of Page, int, int)
        """
        self.__pages = []
        self.__pagesPerRow = 0
        self.__sdSize = 0

        if isinstance(fileNameOrDevice, QIODevice):
            self.setDevice(fileNameOrDevice)
        else:
            f = QFile(fileNameOrDevice)
            if not f.exists():
                return self.__pages, self.__pagesPerRow, self.__sdSize
            opened = f.open(QIODevice.OpenModeFlag.ReadOnly)
            if not opened:
                self.raiseError(
                    QCoreApplication.translate(
                        "SpeedDialReader",
                        "The file {0} could not be opened. Error: {1}",
                    ).format(fileNameOrDevice, f.errorString())
                )
                return self.__pages, self.__pagesPerRow, self.__sdSize
            self.setDevice(f)

        while not self.atEnd():
            self.readNext()
            if self.isStartElement():
                version = self.attributes().value("version")
                if self.name() == "SpeedDial" and (not version or version == "1.0"):
                    self.__readSpeedDial()
                else:
                    self.raiseError(
                        QCoreApplication.translate(
                            "SpeedDialReader",
                            "The file is not a SpeedDial version 1.0 file.",
                        )
                    )

        return self.__pages, self.__pagesPerRow, self.__sdSize

    def __readSpeedDial(self):
        """
        Private method to read the speed dial data.
        """
        if not self.isStartElement() and self.name() != "SpeedDial":
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                if self.name() in ["Pages", "Page"]:
                    continue
                else:
                    break

            if self.isStartElement():
                if self.name() == "Pages":
                    attributes = self.attributes()
                    pagesPerRow = attributes.value("row")
                    if pagesPerRow.isdigit():
                        self.__pagesPerRow = int(pagesPerRow)
                    sdSize = attributes.value("size")
                    if sdSize.isdigit():
                        self.__sdSize = int(sdSize)
                elif self.name() == "Page":
                    attributes = self.attributes()
                    url = attributes.value("url")
                    title = attributes.value("title")
                    if url:
                        if not title:
                            title = url
                        page = Page(url, title)
                        self.__pages.append(page)
                else:
                    self.__skipUnknownElement()

    def __skipUnknownElement(self):
        """
        Private method to skip over all unknown elements.
        """
        if not self.isStartElement():
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break

            if self.isStartElement():
                self.__skipUnknownElement()
