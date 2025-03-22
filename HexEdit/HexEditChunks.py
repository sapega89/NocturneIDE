# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the storage backend for the hex editor.
"""

import sys

from dataclasses import dataclass, field

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice


@dataclass
class HexEditChunk:
    """
    Class implementing a container for the data chunks.
    """

    data: bytearray = field(default_factory=bytearray)
    dataChanged: bytearray = field(default_factory=bytearray)
    absPos: int = 0


class HexEditChunks:
    """
    Class implementing the storage backend for the hex editor.

    When HexEditWidget loads data, HexEditChunks access them using a QIODevice
    interface. When the app uses a QByteArray or Python bytearray interface,
    QBuffer is used to provide again a QIODevice like interface. No data will
    be changed, therefore HexEditChunks opens the QIODevice in
    QIODevice.OpenModeFlag.ReadOnly mode. After every access HexEditChunks
    closes the QIODevice. That's why external applications can overwrite
    files while HexEditWidget shows them.

    When the the user starts to edit the data, HexEditChunks creates a local
    copy of a chunk of data (4 kilobytes) and notes all changes there. Parallel
    to that chunk, there is a second chunk, which keeps track of which bytes
    are changed and which are not.
    """

    BUFFER_SIZE = 0x10000
    CHUNK_SIZE = 0x1000
    READ_CHUNK_MASK = 0xFFFFFFFFFFFFF000

    def __init__(self, ioDevice=None):
        """
        Constructor

        @param ioDevice io device to get the data from
        @type QIODevice
        """
        self.__ioDevice = None
        self.__pos = 0
        self.__size = 0
        self.__chunks = []

        if ioDevice is None:
            buf = QBuffer()
            self.setIODevice(buf)
        else:
            self.setIODevice(ioDevice)

    def setIODevice(self, ioDevice):
        """
        Public method to set an io device to read the binary data from.

        @param ioDevice io device to get the data from
        @type QIODevice
        @return flag indicating successful operation
        @rtype bool
        """
        self.__ioDevice = ioDevice
        ok = self.__ioDevice.open(QIODevice.OpenModeFlag.ReadOnly)
        if ok:
            # open successfully
            self.__size = self.__ioDevice.size()
            self.__ioDevice.close()
        else:
            # fallback is an empty buffer
            self.__ioDevice = QBuffer()
            self.__size = 0

        self.__chunks = []
        self.__pos = 0

        return ok

    def data(self, pos=0, maxSize=-1, highlighted=None):
        """
        Public method to get data out of the chunks.

        @param pos position to get bytes from
        @type int
        @param maxSize maximum amount of bytes to get
        @type int
        @param highlighted reference to a byte array storing highlighting info
        @type bytearray
        @return retrieved data
        @rtype bytearray
        """
        ioDelta = 0
        chunkIdx = 0

        chunk = HexEditChunk()
        buffer = bytearray()

        if highlighted is not None:
            del highlighted[:]

        if pos >= self.__size:
            return buffer

        if maxSize < 0:
            maxSize = self.__size
        elif (pos + maxSize) > self.__size:
            maxSize = self.__size - pos

        self.__ioDevice.open(QIODevice.OpenModeFlag.ReadOnly)

        while maxSize > 0:
            chunk.absPos = sys.maxsize
            chunksLoopOngoing = True
            while chunkIdx < len(self.__chunks) and chunksLoopOngoing:
                # In this section, we track changes before our required data
                # and we take the edited data, if availible. ioDelta is a
                # difference counter to justify the read pointer to the
                # original data, if data in between was deleted or inserted.

                chunk = self.__chunks[chunkIdx]
                if chunk.absPos > pos:
                    chunksLoopOngoing = False
                else:
                    chunkIdx += 1
                    chunkOfs = pos - chunk.absPos
                    if maxSize > (len(chunk.data) - chunkOfs):
                        count = len(chunk.data) - chunkOfs
                        ioDelta += self.CHUNK_SIZE - len(chunk.data)
                    else:
                        count = maxSize
                    if count > 0:
                        buffer += chunk.data[chunkOfs : chunkOfs + count]
                        maxSize -= count
                        pos += count
                        if highlighted is not None:
                            highlighted += chunk.dataChanged[
                                chunkOfs : chunkOfs + count
                            ]

            if maxSize > 0 and pos < chunk.absPos:
                # In this section, we read data from the original source. This
                # will only happen, when no copied data is available.
                if chunk.absPos - pos > maxSize:
                    byteCount = maxSize
                else:
                    byteCount = chunk.absPos - pos

                maxSize -= byteCount
                self.__ioDevice.seek(pos + ioDelta)
                readBuffer = bytearray(self.__ioDevice.read(byteCount))
                buffer += readBuffer
                if highlighted is not None:
                    highlighted += bytearray(len(readBuffer))
                pos += len(readBuffer)

        self.__ioDevice.close()
        return buffer

    def write(self, ioDevice, pos=0, count=-1):
        """
        Public method to write data to an io device.

        @param ioDevice io device to write the data to
        @type QIODevice
        @param pos position to write bytes from
        @type int
        @param count amount of bytes to write
        @type int
        @return flag indicating success
        @rtype bool
        """
        if count == -1:
            # write all data
            count = self.__size

        ok = ioDevice.open(QIODevice.OpenModeFlag.WriteOnly)
        if ok:
            idx = pos
            while idx < count:
                data = self.data(idx, self.BUFFER_SIZE)
                ioDevice.write(QByteArray(data))

                # increment loop variable
                idx += self.BUFFER_SIZE

            ioDevice.close()

        return ok

    def setDataChanged(self, pos, dataChanged):
        """
        Public method to set highlighting info.

        @param pos position to set highlighting info for
        @type int
        @param dataChanged flag indicating changed data
        @type bool
        """
        if pos < 0 or pos >= self.__size:
            # position is out of range, do nothing
            return
        chunkIdx = self.__getChunkIndex(pos)
        posInChunk = pos - self.__chunks[chunkIdx].absPos
        self.__chunks[chunkIdx].dataChanged[posInChunk] = int(dataChanged)

    def dataChanged(self, pos):
        """
        Public method to test, if some data was changed.

        @param pos byte position to check
        @type int
        @return flag indicating the changed state
        @rtype bool
        """
        highlighted = bytearray()
        self.data(pos, 1, highlighted)
        return highlighted and bool(highlighted[0])

    def indexOf(self, byteArray, start):
        """
        Public method to search the first occurrence of some data.

        @param byteArray data to search for
        @type bytearray
        @param start position to start the search at
        @type int
        @return position the data was found at or -1 if nothing could be found
        @rtype int
        """
        ba = bytearray(byteArray)

        result = -1
        pos = start
        while pos < self.__size:
            buffer = self.data(pos, self.BUFFER_SIZE + len(ba) - 1)
            findPos = buffer.find(ba)
            if findPos >= 0:
                result = pos + findPos
                break

            # increment loop variable
            pos += self.BUFFER_SIZE

        return result

    def lastIndexOf(self, byteArray, start):
        """
        Public method to search the last occurrence of some data.

        @param byteArray data to search for
        @type bytearray
        @param start position to start the search at
        @type int
        @return position the data was found at or -1 if nothing could be found
        @rtype int
        """
        ba = bytearray(byteArray)

        result = -1
        pos = start
        while pos > 0 and result < 0:
            sPos = pos - self.BUFFER_SIZE - len(ba) + 1
            if sPos < 0:
                sPos = 0

            buffer = self.data(sPos, pos - sPos)
            findPos = buffer.rfind(ba)
            if findPos >= 0:
                result = sPos + findPos
                break

            # increment loop variable
            pos -= self.BUFFER_SIZE

        return result

    def insert(self, pos, data):
        """
        Public method to insert a byte.

        @param pos position to insert at
        @type int
        @param data byte to insert
        @type int (range 0 to 255)
        @return flag indicating success
        @rtype bool
        """
        if pos < 0 or pos > self.__size:
            # position is out of range, do nothing
            return False

        chunkIdx = (
            self.__getChunkIndex(pos - 1)
            if pos == self.__size
            else self.__getChunkIndex(pos)
        )
        chunk = self.__chunks[chunkIdx]
        posInChunk = pos - chunk.absPos
        chunk.data.insert(posInChunk, data)
        chunk.dataChanged.insert(posInChunk, 1)
        for idx in range(chunkIdx + 1, len(self.__chunks)):
            self.__chunks[idx].absPos += 1
        self.__size += 1
        self.__pos = pos
        return True

    def overwrite(self, pos, data):
        """
        Public method to overwrite a byte.

        @param pos position to overwrite
        @type int
        @param data byte to overwrite with
        @type int (range 0 to 255)
        @return flag indicating success
        @rtype bool
        """
        if pos < 0 or pos >= self.__size:
            # position is out of range, do nothing
            return False

        chunkIdx = self.__getChunkIndex(pos)
        chunk = self.__chunks[chunkIdx]
        posInChunk = pos - chunk.absPos
        chunk.data[posInChunk] = data
        chunk.dataChanged[posInChunk] = 1
        self.__pos = pos
        return True

    def removeAt(self, pos):
        """
        Public method to remove a byte.

        @param pos position to remove
        @type int
        @return flag indicating success
        @rtype bool
        """
        if pos < 0 or pos >= self.__size:
            # position is out of range, do nothing
            return False

        chunkIdx = self.__getChunkIndex(pos)
        chunk = self.__chunks[chunkIdx]
        posInChunk = pos - chunk.absPos
        chunk.data.pop(posInChunk)
        chunk.dataChanged.pop(posInChunk)
        for idx in range(chunkIdx + 1, len(self.__chunks)):
            self.__chunks[idx].absPos -= 1
        self.__size -= 1
        self.__pos = pos
        return True

    def __getitem__(self, pos):
        """
        Special method to get a byte at a position.

        Note: This realizes the [] get operator.

        @param pos position of byte to get
        @type int
        @return requested byte
        @rtype int (range 0 to 255)
        """
        if pos >= self.__size:
            return 0
        ##            raise IndexError

        return self.data(pos, 1)[0]

    def pos(self):
        """
        Public method to get the current position.

        @return current position
        @rtype int
        """
        return self.__pos

    def size(self):
        """
        Public method to get the current data size.

        @return current data size
        @rtype int
        """
        return self.__size

    def __getChunkIndex(self, absPos):
        """
        Private method to get the chunk index for a position.

        This method checks, if there is already a copied chunk available. If
        there is one, it returns its index. If there is no copied chunk
        available, original data will be copied into a new chunk.

        @param absPos absolute position of the data.
        @type int
        @return index of the chunk containing the position
        @rtype int
        """
        foundIdx = -1
        insertIdx = 0
        ioDelta = 0

        for idx in range(len(self.__chunks)):
            chunk = self.__chunks[idx]
            if absPos >= chunk.absPos and absPos < (chunk.absPos + len(chunk.data)):
                foundIdx = idx
                break

            if absPos < chunk.absPos:
                insertIdx = idx
                break

            ioDelta += len(chunk.data) - self.CHUNK_SIZE
            insertIdx = idx + 1

        if foundIdx == -1:
            newChunk = HexEditChunk()
            readAbsPos = absPos - ioDelta
            readPos = readAbsPos & self.READ_CHUNK_MASK
            self.__ioDevice.open(QIODevice.OpenModeFlag.ReadOnly)
            self.__ioDevice.seek(readPos)
            newChunk.data = bytearray(self.__ioDevice.read(self.CHUNK_SIZE))
            self.__ioDevice.close()
            newChunk.absPos = absPos - (readAbsPos - readPos)
            newChunk.dataChanged = bytearray(len(newChunk.data))
            self.__chunks.insert(insertIdx, newChunk)
            foundIdx = insertIdx

        return foundIdx
