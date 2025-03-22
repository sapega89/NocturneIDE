# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an editor for binary data.
"""

import math

from PyQt6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QRect,
    Qt,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QFont, QKeySequence, QPainter, QPalette
from PyQt6.QtWidgets import QAbstractScrollArea, QApplication

from eric7 import EricUtilities
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import OSUtilities

from .HexEditChunks import HexEditChunks
from .HexEditUndoStack import HexEditUndoStack


class HexEditWidget(QAbstractScrollArea):
    """
    Class implementing an editor for binary data.

    @signal currentAddressChanged(address) emitted to indicate the new
        cursor position
    @signal currentSizeChanged(size) emitted to indicate the new size of
        the data
    @signal dataChanged(modified) emitted to indicate a change of the data
    @signal overwriteModeChanged(state) emitted to indicate a change of
        the overwrite mode
    @signal readOnlyChanged(state) emitted to indicate a change of the
        read only state
    @signal canRedoChanged(bool) emitted after the redo status has changed
    @signal canUndoChanged(bool) emitted after the undo status has changed
    @signal selectionAvailable(bool) emitted to signal a change of the
        selection
    """

    currentAddressChanged = pyqtSignal(int)
    currentSizeChanged = pyqtSignal(int)
    dataChanged = pyqtSignal(bool)
    overwriteModeChanged = pyqtSignal(bool)
    readOnlyChanged = pyqtSignal(bool)
    canRedoChanged = pyqtSignal(bool)
    canUndoChanged = pyqtSignal(bool)
    selectionAvailable = pyqtSignal(bool)

    HEXCHARS_PER_LINE = 47
    BYTES_PER_LINE = 16

    def __init__(self, parent=None):
        """
        Constructor

        @param parent refernce to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        # Properties
        self.__addressArea = True
        # switch the address area on/off
        self.__addressOffset = 0
        # offset into the shown address range
        self.__addressWidth = 4
        # address area width in characters
        self.__asciiArea = True
        # switch the ASCII area on/off
        self.__data = bytearray()
        # contents of the hex editor
        self.__highlighting = True
        # switch the highlighting feature on/off
        self.__overwriteMode = True
        # set overwrite mode on/off
        self.__readOnly = False
        # set read only mode on/off
        self.__cursorPosition = 0
        # absolute position of cursor, 1 Byte == 2 tics

        self.__addrDigits = 0
        self.__addrSeparators = 0
        self.__blink = True
        self.__bData = QBuffer()
        self.__cursorRect = QRect()
        self.__cursorRectAscii = QRect()
        self.__dataShown = bytearray()
        self.__hexDataShown = bytearray()
        self.__lastEventSize = 0
        self.__markedShown = bytearray()
        self.__modified = False
        self.__rowsShown = 0

        # pixel related attributes (starting with __px)
        self.__pxCharWidth = 0
        self.__pxCharHeight = 0
        self.__pxPosHexX = 0
        self.__pxPosAdrX = 0
        self.__pxPosAsciiX = 0
        self.__pxGapAdr = 0
        self.__pxGapAdrHex = 0
        self.__pxGapHexAscii = 0
        self.__pxSelectionSub = 0
        self.__pxCursorWidth = 0
        self.__pxCursorX = 0
        self.__pxCursorY = 0

        # absolute byte position related attributes (starting with __b)
        self.__bSelectionBegin = 0
        self.__bSelectionEnd = 0
        self.__bSelectionInit = 0
        self.__bPosFirst = 0
        self.__bPosLast = 0
        self.__bPosCurrent = 0

        self.__chunks = HexEditChunks()
        self.__undoStack = HexEditUndoStack(self.__chunks, self)
        if OSUtilities.isWindowsPlatform():
            self.setFont(QFont(["Courier"], 10))
        else:
            self.setFont(QFont(["Monospace"], 10))

        self.__cursorTimer = QTimer()
        self.__cursorTimer.timeout.connect(self.__updateCursor)

        self.verticalScrollBar().valueChanged.connect(self.__adjust)

        self.__undoStack.indexChanged.connect(self.__dataChangedPrivate)
        self.__undoStack.canRedoChanged.connect(self.__canRedoChanged)
        self.__undoStack.canUndoChanged.connect(self.__canUndoChanged)

        self.readOnlyChanged.connect(self.__canRedoChanged)
        self.readOnlyChanged.connect(self.__canUndoChanged)

        self.__cursorTimer.setInterval(500)
        self.__cursorTimer.start()

        self.setAddressWidth(4)
        self.setAddressArea(True)
        self.setAsciiArea(True)
        self.setOverwriteMode(True)
        self.setHighlighting(True)
        self.setReadOnly(False)

        self.__initialize()

    def undoStack(self):
        """
        Public method to get a reference to the undo stack.

        @return reference to the undo stack
        @rtype HexEditUndoStack
        """
        return self.__undoStack

    @pyqtSlot()
    def __canRedoChanged(self):
        """
        Private slot handling changes of the Redo state.
        """
        self.canRedoChanged.emit(self.__undoStack.canRedo() and not self.__readOnly)

    @pyqtSlot()
    def __canUndoChanged(self):
        """
        Private slot handling changes of the Undo state.
        """
        self.canUndoChanged.emit(self.__undoStack.canUndo() and not self.__readOnly)

    def addressArea(self):
        """
        Public method to get the address area visibility.

        @return flag indicating the address area visibility
        @rtype bool
        """
        return self.__addressArea

    def setAddressArea(self, on):
        """
        Public method to set the address area visibility.

        @param on flag indicating the address area visibility
        @type bool
        """
        self.__addressArea = on
        self.__adjust()
        self.setCursorPosition(self.__cursorPosition)
        self.viewport().update()

    def addressOffset(self):
        """
        Public method to get the address offset.

        @return address offset
        @rtype int
        """
        return self.__addressOffset

    def setAddressOffset(self, offset):
        """
        Public method to set the address offset.

        @param offset address offset
        @type int
        """
        self.__addressOffset = offset
        self.__adjust()
        self.setCursorPosition(self.__cursorPosition)
        self.viewport().update()

    def addressWidth(self):
        """
        Public method to get the width of the address area in
        characters.

        Note: The address area width is always a multiple of four.

        @return minimum width of the address area
        @rtype int
        """
        size = self.__chunks.size()
        n = 1
        if size > 0x100000000:
            n += 8
            size //= 0x100000000
        if size > 0x10000:
            n += 4
            size //= 0x10000
        if size > 0x100:
            n += 2
            size //= 0x100
        if size > 0x10:
            n += 1
            size //= 0x10
        n = int(math.ceil(n / 4)) * 4

        if n > self.__addressWidth:
            return n
        else:
            return self.__addressWidth

    def setAddressWidth(self, width):
        """
        Public method to set the width of the address area.

        Note: The address area width is always a multiple of four.
        The given value will be adjusted as required.

        @param width width of the address area in characters
        @type int
        """
        self.__addressWidth = int(math.ceil(width / 4)) * 4
        self.__adjust()
        self.setCursorPosition(self.__cursorPosition)
        self.viewport().update()

    def asciiArea(self):
        """
        Public method to get the visibility of the ASCII area.

        @return visibility of the ASCII area
        @rtype bool
        """
        return self.__asciiArea

    def setAsciiArea(self, on):
        """
        Public method to set the visibility of the ASCII area.

        @param on flag indicating the visibility of the ASCII area
        @type bool
        """
        self.__asciiArea = on
        self.viewport().update()

    def cursorPosition(self):
        """
        Public method to get the cursor position.

        @return cursor position
        @rtype int
        """
        return self.__cursorPosition

    def setCursorPosition(self, pos):
        """
        Public method to set the cursor position.

        @param pos cursor position
        @type int
        """
        # step 1: delete old cursor
        self.__blink = False
        self.viewport().update(self.__cursorRect)
        if self.__asciiArea:
            self.viewport().update(self.__cursorRectAscii)

        # step 2: check, if cursor is in range
        if self.__overwriteMode and pos > (self.__chunks.size() * 2 - 1):
            pos = self.__chunks.size() * 2 - 1
        if (not self.__overwriteMode) and pos > (self.__chunks.size() * 2):
            pos = self.__chunks.size() * 2
        if pos < 0:
            pos = 0

        # step 3: calculate new position of cursor
        self.__cursorPosition = pos
        self.__bPosCurrent = pos // 2
        self.__pxCursorY = (
            (pos // 2 - self.__bPosFirst) // self.BYTES_PER_LINE + 1
        ) * self.__pxCharHeight
        x = pos % (2 * self.BYTES_PER_LINE)
        self.__pxCursorX = (
            ((x // 2) * 3) + (x % 2)
        ) * self.__pxCharWidth + self.__pxPosHexX

        self.__setHexCursorRect()

        # step 4: calculate position of ASCII cursor
        x = self.__bPosCurrent % self.BYTES_PER_LINE
        self.__cursorRectAscii = QRect(
            self.__pxPosAsciiX + x * self.__pxCharWidth - 1,
            self.__pxCursorY - self.__pxCharHeight + 4,
            self.__pxCharWidth + 1,
            self.__pxCharHeight + 1,
        )

        # step 5: draw new cursors
        self.__blink = True
        self.viewport().update(self.__cursorRect)
        if self.__asciiArea:
            self.viewport().update(self.__cursorRectAscii)
        self.currentAddressChanged.emit(self.__bPosCurrent)

    def __setHexCursorRect(self):
        """
        Private method to set the cursor.
        """
        if self.__overwriteMode:
            self.__cursorRect = QRect(
                self.__pxCursorX,
                self.__pxCursorY + self.__pxCursorWidth,
                self.__pxCharWidth,
                self.__pxCursorWidth,
            )
        else:
            self.__cursorRect = QRect(
                self.__pxCursorX,
                self.__pxCursorY - self.__pxCharHeight + 4,
                self.__pxCursorWidth,
                self.__pxCharHeight,
            )

    def cursorBytePosition(self):
        """
        Public method to get the cursor position in bytes.

        @return cursor position in bytes
        @rtype int
        """
        return self.__bPosCurrent

    def setCursorBytePosition(self, pos):
        """
        Public method to set the cursor position in bytes.

        @param pos cursor position in bytes
        @type int
        """
        self.setCursorPosition(pos * 2)

    def goto(self, offset, fromCursor=False, backwards=False, extendSelection=False):
        """
        Public method to move the cursor.

        @param offset offset to move to
        @type int
        @param fromCursor flag indicating a move relative to the current cursor
        @type bool
        @param backwards flag indicating a backwards move
        @type bool
        @param extendSelection flag indicating to extend the selection
        @type bool
        """
        if fromCursor:
            if backwards:
                newPos = self.cursorBytePosition() - offset
            else:
                newPos = self.cursorBytePosition() + offset
        else:
            if backwards:
                newPos = self.__chunks.size() - offset
            else:
                newPos = offset

        self.setCursorBytePosition(newPos)
        if extendSelection:
            self.__setSelection(self.__cursorPosition)
        else:
            self.__resetSelection(self.__cursorPosition)

        self.__refresh()

    def data(self):
        """
        Public method to get the binary data.

        @return binary data
        @rtype bytearray
        """
        return self.__chunks.data(0, -1)

    def setData(self, dataOrDevice):
        """
        Public method to set the data to show.

        @param dataOrDevice byte array or device containing the data
        @type bytes, bytearray, QByteArray or QIODevice
        @return flag indicating success
        @rtype bool
        @exception TypeError raised to indicate a wrong parameter type
        """
        if not isinstance(dataOrDevice, (bytes, bytearray, QByteArray, QIODevice)):
            raise TypeError(
                "setData: parameter must be bytes, bytearray, "
                "QByteArray or QIODevice"
            )

        if isinstance(dataOrDevice, (bytes, bytearray, QByteArray)):
            self.__data = bytearray(dataOrDevice)
            self.__bData.setData(self.__data)
            return self.__setData(self.__bData)
        else:
            return self.__setData(dataOrDevice)

    def __setData(self, ioDevice):
        """
        Private method to set the data to show.

        @param ioDevice device containing the data
        @type QIODevice
        @return flag indicating success
        @rtype bool
        """
        ok = self.__chunks.setIODevice(ioDevice)
        self.__initialize()
        self.__dataChangedPrivate()
        return ok

    def highlighting(self):
        """
        Public method to get the highlighting state.

        @return highlighting state
        @rtype bool
        """
        return self.__highlighting

    def setHighlighting(self, on):
        """
        Public method to set the highlighting state.

        @param on new highlighting state
        @type bool
        """
        self.__highlighting = on
        self.viewport().update()

    def overwriteMode(self):
        """
        Public method to get the overwrite mode.

        @return overwrite mode
        @rtype bool
        """
        return self.__overwriteMode

    def setOverwriteMode(self, on):
        """
        Public method to set the overwrite mode.

        @param on flag indicating the new overwrite mode
        @type bool
        """
        self.__overwriteMode = on
        self.overwriteModeChanged.emit(self.__overwriteMode)

        # step 1: delete old cursor
        self.__blink = False
        self.viewport().update(self.__cursorRect)
        # step 2: change the cursor rectangle
        self.__setHexCursorRect()
        # step 3: draw new cursors
        self.__blink = True
        self.viewport().update(self.__cursorRect)

    def isReadOnly(self):
        """
        Public method to test the read only state.

        @return flag indicating the read only state
        @rtype bool
        """
        return self.__readOnly

    def setReadOnly(self, on):
        """
        Public method to set the read only state.

        @param on new read only state
        @type bool
        """
        self.__readOnly = on
        self.readOnlyChanged.emit(self.__readOnly)

    def font(self):
        """
        Public method to get the font used to show the data.

        @return font used to show the data
        @rtype QFont
        """
        return super().font()

    def setFont(self, font):
        """
        Public method to set the font used to show the data.

        @param font font used to show the data
        @type QFont
        """
        super().setFont(font)
        self.__pxCharWidth = self.fontMetrics().horizontalAdvance("2")
        self.__pxCharHeight = self.fontMetrics().height()
        self.__pxGapAdr = self.__pxCharWidth // 2
        self.__pxGapAdrHex = self.__pxCharWidth
        self.__pxGapHexAscii = 2 * self.__pxCharWidth
        self.__pxCursorWidth = self.__pxCharHeight // 7
        self.__pxSelectionSub = self.fontMetrics().descent()
        self.__adjust()
        self.viewport().update()

    def dataAt(self, pos, count=-1):
        """
        Public method to get data from a given position.

        @param pos position to get data from
        @type int
        @param count amount of bytes to get
        @type int
        @return requested data
        @rtype bytearray
        """
        return bytearray(self.__chunks.data(pos, count))

    def write(self, device, pos=0, count=-1):
        """
        Public method to write data from a given position to a device.

        @param device device to write to
        @type QIODevice
        @param pos position to start the write at
        @type int
        @param count amount of bytes to write
        @type int
        @return flag indicating success
        @rtype bool
        """
        return self.__chunks.write(device, pos, count)

    def insert(self, pos, ch):
        """
        Public method to insert a byte.

        @param pos position to insert the byte at
        @type int
        @param ch byte to insert
        @type int in the range 0x00 to 0xff
        """
        if ch in range(0, 256):
            self.__undoStack.insert(pos, ch)
            self.__refresh()

    def remove(self, pos, length=1):
        """
        Public method to remove bytes.

        @param pos position to remove bytes from
        @type int
        @param length amount of bytes to remove
        @type int
        """
        self.__undoStack.removeAt(pos, length)
        self.__refresh()

    def replace(self, pos, ch):
        """
        Public method to replace a byte.

        @param pos position to replace the byte at
        @type int
        @param ch byte to replace with
        @type int in the range 0x00 to 0xff
        """
        if ch in range(0, 256):
            self.__undoStack.overwrite(pos, ch)
            self.__refresh()

    def insertByteArray(self, pos, byteArray):
        """
        Public method to insert bytes.

        @param pos position to insert the bytes at
        @type int
        @param byteArray bytes to be insert
        @type bytearray or QByteArray
        """
        self.__undoStack.insertByteArray(pos, bytearray(byteArray))
        self.__refresh()

    def replaceByteArray(self, pos, length, byteArray):
        """
        Public method to replace bytes.

        @param pos position to replace the bytes at
        @type int
        @param length amount of bytes to replace
        @type int
        @param byteArray bytes to replace with
        @type bytearray or QByteArray
        """
        self.__undoStack.overwriteByteArray(pos, length, bytearray(byteArray))
        self.__refresh()

    def cursorPositionFromPoint(self, point):
        """
        Public method to calculate a cursor position from a graphics position.

        @param point graphics position
        @type QPoint
        @return cursor position
        @rtype int
        """
        result = -1
        if (point.x() >= self.__pxPosHexX) and (
            point.x()
            < (self.__pxPosHexX + (1 + self.HEXCHARS_PER_LINE) * self.__pxCharWidth)
        ):
            x = (
                point.x() - self.__pxPosHexX - self.__pxCharWidth // 2
            ) // self.__pxCharWidth
            x = (x // 3) * 2 + x % 3
            y = ((point.y() - 3) // self.__pxCharHeight) * 2 * self.BYTES_PER_LINE
            result = self.__bPosFirst * 2 + x + y
        return result

    def ensureVisible(self):
        """
        Public method to ensure, that the cursor is visible.
        """
        if self.__cursorPosition < 2 * self.__bPosFirst:
            self.verticalScrollBar().setValue(
                self.__cursorPosition // 2 // self.BYTES_PER_LINE
            )
        if self.__cursorPosition > (
            (self.__bPosFirst + (self.__rowsShown - 1) * self.BYTES_PER_LINE) * 2
        ):
            self.verticalScrollBar().setValue(
                self.__cursorPosition // 2 // self.BYTES_PER_LINE - self.__rowsShown + 1
            )
        self.viewport().update()

    def indexOf(self, byteArray, start):
        """
        Public method to find the first occurrence of a byte array in our data.

        @param byteArray data to search for
        @type bytearray or QByteArray
        @param start start position of the search
        @type int
        @return position of match (or -1 if not found)
        @rtype int
        """
        byteArray = bytearray(byteArray)
        pos = self.__chunks.indexOf(byteArray, start)
        if pos > -1:
            curPos = pos * 2
            self.setCursorPosition(curPos + len(byteArray) * 2)
            self.__resetSelection(curPos)
            self.__setSelection(curPos + len(byteArray) * 2)
            self.ensureVisible()
        return pos

    def lastIndexOf(self, byteArray, start):
        """
        Public method to find the last occurrence of a byte array in our data.

        @param byteArray data to search for
        @type bytearray or QByteArray
        @param start start position of the search
        @type int
        @return position of match (or -1 if not found)
        @rtype int
        """
        byteArray = bytearray(byteArray)
        pos = self.__chunks.lastIndexOf(byteArray, start)
        if pos > -1:
            curPos = pos * 2
            self.setCursorPosition(curPos - 1)
            self.__resetSelection(curPos)
            self.__setSelection(curPos + len(byteArray) * 2)
            self.ensureVisible()
        return pos

    def isModified(self):
        """
        Public method to check for any modification.

        @return flag indicating a modified state
        @rtype bool
        """
        return self.__modified

    def setModified(self, modified, setCleanState=False):
        """
        Public slot to set the modified flag.

        @param modified flag indicating the new modification status
        @type bool
        @param setCleanState flag indicating to set the undo stack to clean
        @type bool
        """
        self.__modified = modified
        self.dataChanged.emit(modified)

        if not modified and setCleanState:
            self.__undoStack.setClean()

    def selectionToHexString(self):
        """
        Public method to get a hexadecimal representation of the selection.

        @return hexadecimal representation of the selection
        @rtype str
        """
        byteArray = self.__chunks.data(
            self.getSelectionBegin(), self.getSelectionLength()
        )
        return self.__toHex(byteArray).decode(encoding="ascii")

    def selectionToReadableString(self):
        """
        Public method to get a formatted representation of the selection.

        @return formatted representation of the selection
        @rtype str
        """
        byteArray = self.__chunks.data(
            self.getSelectionBegin(), self.getSelectionLength()
        )
        return self.__toReadable(byteArray)

    def toReadableString(self):
        """
        Public method to get a formatted representation of our data.

        @return formatted representation of our data
        @rtype str
        """
        byteArray = self.__chunks.data()
        return self.__toReadable(byteArray)

    @pyqtSlot()
    def redo(self):
        """
        Public slot to redo the last operation.
        """
        self.__undoStack.redo()
        self.setCursorPosition(self.__chunks.pos() * 2)
        self.__refresh()

    @pyqtSlot()
    def undo(self):
        """
        Public slot to undo the last operation.
        """
        self.__undoStack.undo()
        self.setCursorPosition(self.__chunks.pos() * 2)
        self.__refresh()

    @pyqtSlot()
    def revertToUnmodified(self):
        """
        Public slot to revert all changes.
        """
        cleanIndex = self.__undoStack.cleanIndex()
        if cleanIndex >= 0:
            self.__undoStack.setIndex(cleanIndex)
        self.setCursorPosition(self.__chunks.pos() * 2)
        self.__refresh()

    ####################################################
    ## Cursor movement commands
    ####################################################

    def moveCursorToNextChar(self):
        """
        Public method to move the cursor to the next byte.
        """
        self.setCursorPosition(self.__cursorPosition + 1)
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToPreviousChar(self):
        """
        Public method to move the cursor to the previous byte.
        """
        self.setCursorPosition(self.__cursorPosition - 1)
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToEndOfLine(self):
        """
        Public method to move the cursor to the end of the current line.
        """
        self.setCursorPosition(self.__cursorPosition | (2 * self.BYTES_PER_LINE - 1))
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToStartOfLine(self):
        """
        Public method to move the cursor to the beginning of the current line.
        """
        self.setCursorPosition(
            self.__cursorPosition - (self.__cursorPosition % (2 * self.BYTES_PER_LINE))
        )
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToPreviousLine(self):
        """
        Public method to move the cursor to the previous line.
        """
        self.setCursorPosition(self.__cursorPosition - 2 * self.BYTES_PER_LINE)
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToNextLine(self):
        """
        Public method to move the cursor to the next line.
        """
        self.setCursorPosition(self.__cursorPosition + 2 * self.BYTES_PER_LINE)
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToNextPage(self):
        """
        Public method to move the cursor to the next page.
        """
        self.setCursorPosition(
            self.__cursorPosition + (self.__rowsShown - 1) * 2 * self.BYTES_PER_LINE
        )
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToPreviousPage(self):
        """
        Public method to move the cursor to the previous page.
        """
        self.setCursorPosition(
            self.__cursorPosition - (self.__rowsShown - 1) * 2 * self.BYTES_PER_LINE
        )
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToEndOfDocument(self):
        """
        Public method to move the cursor to the end of the data.
        """
        self.setCursorPosition(self.__chunks.size() * 2)
        self.__resetSelection(self.__cursorPosition)

    def moveCursorToStartOfDocument(self):
        """
        Public method to move the cursor to the start of the data.
        """
        self.setCursorPosition(0)
        self.__resetSelection(self.__cursorPosition)

    ####################################################
    ## Selection commands
    ####################################################

    def deselectAll(self):
        """
        Public method to deselect all data.
        """
        self.__resetSelection(0)
        self.__refresh()

    def selectAll(self):
        """
        Public method to select all data.
        """
        self.__resetSelection(0)
        self.__setSelection(2 * self.__chunks.size() + 1)
        self.__refresh()

    def selectNextChar(self):
        """
        Public method to extend the selection by one byte right.
        """
        pos = self.__cursorPosition + 1
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectPreviousChar(self):
        """
        Public method to extend the selection by one byte left.
        """
        pos = self.__cursorPosition - 1
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectToEndOfLine(self):
        """
        Public method to extend the selection to the end of line.
        """
        pos = (
            self.__cursorPosition
            - (self.__cursorPosition % (2 * self.BYTES_PER_LINE))
            + 2 * self.BYTES_PER_LINE
        )
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectToStartOfLine(self):
        """
        Public method to extend the selection to the start of line.
        """
        pos = self.__cursorPosition - (
            self.__cursorPosition % (2 * self.BYTES_PER_LINE)
        )
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectPreviousLine(self):
        """
        Public method to extend the selection one line up.
        """
        pos = self.__cursorPosition - 2 * self.BYTES_PER_LINE
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectNextLine(self):
        """
        Public method to extend the selection one line down.
        """
        pos = self.__cursorPosition + 2 * self.BYTES_PER_LINE
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectNextPage(self):
        """
        Public method to extend the selection one page down.
        """
        pos = (
            self.__cursorPosition
            + ((self.viewport().height() // self.__pxCharHeight) - 1)
            * 2
            * self.BYTES_PER_LINE
        )
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectPreviousPage(self):
        """
        Public method to extend the selection one page up.
        """
        pos = (
            self.__cursorPosition
            - ((self.viewport().height() // self.__pxCharHeight) - 1)
            * 2
            * self.BYTES_PER_LINE
        )
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectEndOfDocument(self):
        """
        Public method to extend the selection to the end of the data.
        """
        pos = self.__chunks.size() * 2
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    def selectStartOfDocument(self):
        """
        Public method to extend the selection to the start of the data.
        """
        pos = 0
        self.setCursorPosition(pos)
        self.__setSelection(pos)

    ####################################################
    ## Edit commands
    ####################################################

    def cut(self):
        """
        Public method to cut the selected bytes and move them to the clipboard.
        """
        if not self.__readOnly:
            byteArray = self.__toHex(
                self.__chunks.data(self.getSelectionBegin(), self.getSelectionLength())
            )
            idx = 32
            while idx < len(byteArray):
                byteArray.insert(idx, "\n")
                idx += 33
            cb = QApplication.clipboard()
            cb.setText(byteArray.decode(encoding="latin1"))
            if self.__overwriteMode:
                length = self.getSelectionLength()
                self.replaceByteArray(
                    self.getSelectionBegin(), length, bytearray(length)
                )
            else:
                self.remove(self.getSelectionBegin(), self.getSelectionLength())
            self.setCursorPosition(2 * self.getSelectionBegin())
            self.__resetSelection(2 * self.getSelectionBegin())

    def copy(self):
        """
        Public method to copy the selected bytes to the clipboard.
        """
        byteArray = self.__toHex(
            self.__chunks.data(self.getSelectionBegin(), self.getSelectionLength())
        )
        idx = 32
        while idx < len(byteArray):
            byteArray.insert(idx, "\n")
            idx += 33
        cb = QApplication.clipboard()
        cb.setText(byteArray.decode(encoding="latin1"))

    def paste(self):
        """
        Public method to paste bytes from the clipboard.
        """
        if not self.__readOnly:
            cb = QApplication.clipboard()
            byteArray = self.__fromHex(cb.text().encode(encoding="latin1"))
            if self.__overwriteMode:
                self.replaceByteArray(self.__bPosCurrent, len(byteArray), byteArray)
            else:
                self.insertByteArray(self.__bPosCurrent, byteArray)
            self.setCursorPosition(self.__cursorPosition + 2 * len(byteArray))
            self.__resetSelection(2 * self.getSelectionBegin())

    def deleteByte(self):
        """
        Public method to delete the current byte.
        """
        if not self.__readOnly:
            if self.hasSelection():
                self.__bPosCurrent = self.getSelectionBegin()
                if self.__overwriteMode:
                    byteArray = bytearray(self.getSelectionLength())
                    self.replaceByteArray(self.__bPosCurrent, len(byteArray), byteArray)
                else:
                    self.remove(self.__bPosCurrent, self.getSelectionLength())
            else:
                if self.__overwriteMode:
                    self.replace(self.__bPosCurrent, 0)
                else:
                    self.remove(self.__bPosCurrent, 1)
            self.setCursorPosition(2 * self.__bPosCurrent)
            self.__resetSelection(2 * self.__bPosCurrent)

    def deleteByteBack(self):
        """
        Public method to delete the previous byte.
        """
        if not self.__readOnly:
            if self.hasSelection():
                self.__bPosCurrent = self.getSelectionBegin()
                self.setCursorPosition(2 * self.__bPosCurrent)
                if self.__overwriteMode:
                    byteArray = bytearray(self.getSelectionLength())
                    self.replaceByteArray(self.__bPosCurrent, len(byteArray), byteArray)
                else:
                    self.remove(self.__bPosCurrent, self.getSelectionLength())
            else:
                self.__bPosCurrent -= 1
                if self.__overwriteMode:
                    self.replace(self.__bPosCurrent, 0)
                else:
                    self.remove(self.__bPosCurrent, 1)
                self.setCursorPosition(2 * self.__bPosCurrent)
            self.__resetSelection(2 * self.__bPosCurrent)

    ####################################################
    ## Event handling methods
    ####################################################

    def keyPressEvent(self, evt):
        """
        Protected method to handle key press events.

        @param evt reference to the key event
        @type QKeyEvent
        """
        # Cursor movements
        if evt.matches(QKeySequence.StandardKey.MoveToNextChar):
            self.moveCursorToNextChar()
        elif evt.matches(QKeySequence.StandardKey.MoveToPreviousChar):
            self.moveCursorToPreviousChar()
        elif evt.matches(QKeySequence.StandardKey.MoveToEndOfLine):
            self.moveCursorToEndOfLine()
        elif evt.matches(QKeySequence.StandardKey.MoveToStartOfLine):
            self.moveCursorToStartOfLine()
        elif evt.matches(QKeySequence.StandardKey.MoveToPreviousLine):
            self.moveCursorToPreviousLine()
        elif evt.matches(QKeySequence.StandardKey.MoveToNextLine):
            self.moveCursorToNextLine()
        elif evt.matches(QKeySequence.StandardKey.MoveToNextPage):
            self.moveCursorToNextPage()
        elif evt.matches(QKeySequence.StandardKey.MoveToPreviousPage):
            self.moveCursorToPreviousPage()
        elif evt.matches(QKeySequence.StandardKey.MoveToEndOfDocument):
            self.moveCursorToEndOfDocument()
        elif evt.matches(QKeySequence.StandardKey.MoveToStartOfDocument):
            self.moveCursorToStartOfDocument()

        # Selection commands
        elif evt.matches(QKeySequence.StandardKey.SelectAll):
            self.selectAll()
        elif evt.matches(QKeySequence.StandardKey.SelectNextChar):
            self.selectNextChar()
        elif evt.matches(QKeySequence.StandardKey.SelectPreviousChar):
            self.selectPreviousChar()
        elif evt.matches(QKeySequence.StandardKey.SelectEndOfLine):
            self.selectToEndOfLine()
        elif evt.matches(QKeySequence.StandardKey.SelectStartOfLine):
            self.selectToStartOfLine()
        elif evt.matches(QKeySequence.StandardKey.SelectPreviousLine):
            self.selectPreviousLine()
        elif evt.matches(QKeySequence.StandardKey.SelectNextLine):
            self.selectNextLine()
        elif evt.matches(QKeySequence.StandardKey.SelectNextPage):
            self.selectNextPage()
        elif evt.matches(QKeySequence.StandardKey.SelectPreviousPage):
            self.selectPreviousPage()
        elif evt.matches(QKeySequence.StandardKey.SelectEndOfDocument):
            self.selectEndOfDocument()
        elif evt.matches(QKeySequence.StandardKey.SelectStartOfDocument):
            self.selectStartOfDocument()

        # Edit commands
        elif evt.matches(QKeySequence.StandardKey.Copy):
            self.copy()
        elif (
            evt.key() == Qt.Key.Key_Insert
            and evt.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            self.setOverwriteMode(not self.overwriteMode())
            self.setCursorPosition(self.__cursorPosition)

        elif not self.__readOnly:
            if evt.matches(QKeySequence.StandardKey.Cut):
                self.cut()
            elif evt.matches(QKeySequence.StandardKey.Paste):
                self.paste()
            elif evt.matches(QKeySequence.StandardKey.Delete):
                self.deleteByte()
            elif (
                evt.key() == Qt.Key.Key_Backspace
                and evt.modifiers() == Qt.KeyboardModifier.NoModifier
            ):
                self.deleteByteBack()
            elif evt.matches(QKeySequence.StandardKey.Undo):
                self.undo()
            elif evt.matches(QKeySequence.StandardKey.Redo):
                self.redo()

            elif QApplication.keyboardModifiers() in [
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.KeypadModifier,
            ]:
                # some hex input
                key = evt.text()
                if key and key in "0123456789abcdef":
                    if self.hasSelection():
                        if self.__overwriteMode:
                            length = self.getSelectionLength()
                            self.replaceByteArray(
                                self.getSelectionBegin(), length, bytearray(length)
                            )
                        else:
                            self.remove(
                                self.getSelectionBegin(), self.getSelectionLength()
                            )
                            self.__bPosCurrent = self.getSelectionBegin()
                        self.setCursorPosition(2 * self.__bPosCurrent)
                        self.__resetSelection(2 * self.__bPosCurrent)

                    # if in insert mode, insert a byte
                    if not self.__overwriteMode and (self.__cursorPosition % 2) == 0:
                        self.insert(self.__bPosCurrent, 0)

                    # change content
                    if self.__chunks.size() > 0:
                        hexValue = self.__toHex(
                            self.__chunks.data(self.__bPosCurrent, 1)
                        )
                        if (self.__cursorPosition % 2) == 0:
                            hexValue[0] = ord(key)
                        else:
                            hexValue[1] = ord(key)
                        self.replace(self.__bPosCurrent, self.__fromHex(hexValue)[0])

                        self.setCursorPosition(self.__cursorPosition + 1)
                        self.__resetSelection(self.__cursorPosition)
                    else:
                        return
                else:
                    return
            else:
                return
        else:
            return

        self.__refresh()

    def mouseMoveEvent(self, evt):
        """
        Protected method to handle mouse moves.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        self.__blink = False
        self.viewport().update()
        actPos = self.cursorPositionFromPoint(evt.position().toPoint())
        if actPos >= 0:
            self.setCursorPosition(actPos)
            self.__setSelection(actPos)

    def mousePressEvent(self, evt):
        """
        Protected method to handle mouse button presses.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        self.__blink = False
        self.viewport().update()
        cPos = self.cursorPositionFromPoint(evt.position().toPoint())
        if cPos >= 0:
            if evt.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                self.__setSelection(cPos)
            else:
                self.__resetSelection(cPos)
            self.setCursorPosition(cPos)

    def paintEvent(self, evt):
        """
        Protected method to handle paint events.

        @param evt reference to the paint event
        @type QPaintEvent
        """
        painter = QPainter(self.viewport())

        # initialize colors
        if ericApp().usesDarkPalette():
            addressAreaForeground = self.palette().color(QPalette.ColorRole.Text)
            addressAreaBackground = (
                self.palette().color(QPalette.ColorRole.Base).lighter(200)
            )
            highlightingForeground = (
                self.palette().color(QPalette.ColorRole.HighlightedText).darker(200)
            )
            highlightingBackground = (
                self.palette().color(QPalette.ColorRole.Highlight).lighter()
            )
        else:
            addressAreaForeground = self.palette().color(QPalette.ColorRole.Text)
            addressAreaBackground = (
                self.palette().color(QPalette.ColorRole.Base).darker()
            )
            highlightingForeground = (
                self.palette().color(QPalette.ColorRole.HighlightedText).lighter()
            )
            highlightingBackground = (
                self.palette().color(QPalette.ColorRole.Highlight).darker()
            )
        selectionForeground = self.palette().color(QPalette.ColorRole.HighlightedText)
        selectionBackground = self.palette().color(QPalette.ColorRole.Highlight)
        standardBackground = self.viewport().palette().color(QPalette.ColorRole.Base)
        standardForeground = self.viewport().palette().color(QPalette.ColorRole.Text)

        if evt.rect() != self.__cursorRect and evt.rect() != self.__cursorRectAscii:
            pxOfsX = self.horizontalScrollBar().value()
            pxPosStartY = self.__pxCharHeight

            # draw some patterns if needed
            painter.fillRect(evt.rect(), standardBackground)
            if self.__addressArea:
                painter.fillRect(
                    QRect(
                        -pxOfsX,
                        evt.rect().top(),
                        self.__pxPosHexX - self.__pxGapAdrHex // 2 - pxOfsX,
                        self.height(),
                    ),
                    addressAreaBackground,
                )
            if self.__asciiArea:
                linePos = self.__pxPosAsciiX - (self.__pxGapHexAscii // 2)
                painter.setPen(Qt.GlobalColor.gray)
                painter.drawLine(
                    linePos - pxOfsX, evt.rect().top(), linePos - pxOfsX, self.height()
                )

            # paint the address area
            if self.__addressArea:
                painter.setPen(addressAreaForeground)
                address = ""
                row = 0
                pxPosY = self.__pxCharHeight
                while row <= len(self.__dataShown) // self.BYTES_PER_LINE:
                    address = "{0:0{1}x}".format(
                        self.__bPosFirst + row * self.BYTES_PER_LINE, self.__addrDigits
                    )
                    address = EricUtilities.strGroup(address, ":", 4)
                    painter.drawText(self.__pxPosAdrX - pxOfsX, pxPosY, address)
                    # increment loop variables
                    row += 1
                    pxPosY += self.__pxCharHeight

            # paint hex and ascii area
            painter.setBackgroundMode(Qt.BGMode.TransparentMode)

            row = 0
            pxPosY = pxPosStartY
            while row <= self.__rowsShown:
                pxPosX = self.__pxPosHexX - pxOfsX
                pxPosAsciiX2 = self.__pxPosAsciiX - pxOfsX
                bPosLine = row * self.BYTES_PER_LINE

                colIdx = 0
                while (
                    bPosLine + colIdx < len(self.__dataShown)
                    and colIdx < self.BYTES_PER_LINE
                ):
                    background = standardBackground
                    painter.setPen(standardForeground)

                    posBa = self.__bPosFirst + bPosLine + colIdx
                    if (
                        self.getSelectionBegin() <= posBa
                        and self.getSelectionEnd() > posBa
                    ):
                        background = selectionBackground
                        painter.setPen(selectionForeground)
                    elif (
                        self.__highlighting
                        and self.__markedShown
                        and self.__markedShown[posBa - self.__bPosFirst]
                    ):
                        background = highlightingBackground
                        painter.setPen(highlightingForeground)

                    # render hex value
                    rect = QRect()
                    if colIdx == 0:
                        rect.setRect(
                            pxPosX,
                            pxPosY - self.__pxCharHeight + self.__pxSelectionSub,
                            2 * self.__pxCharWidth,
                            self.__pxCharHeight,
                        )
                    else:
                        rect.setRect(
                            pxPosX - self.__pxCharWidth,
                            pxPosY - self.__pxCharHeight + self.__pxSelectionSub,
                            3 * self.__pxCharWidth,
                            self.__pxCharHeight,
                        )
                    painter.fillRect(rect, background)
                    hexStr = chr(self.__hexDataShown[(bPosLine + colIdx) * 2]) + chr(
                        self.__hexDataShown[(bPosLine + colIdx) * 2 + 1]
                    )
                    painter.drawText(pxPosX, pxPosY, hexStr)
                    pxPosX += 3 * self.__pxCharWidth

                    # render ascii value
                    if self.__asciiArea:
                        by = self.__dataShown[bPosLine + colIdx]
                        if by < 0x20 or (by > 0x7E and by < 0xA0):
                            ch = "."
                        else:
                            ch = chr(by)
                        rect.setRect(
                            pxPosAsciiX2,
                            pxPosY - self.__pxCharHeight + self.__pxSelectionSub,
                            self.__pxCharWidth,
                            self.__pxCharHeight,
                        )
                        painter.fillRect(rect, background)
                        painter.drawText(pxPosAsciiX2, pxPosY, ch)
                        pxPosAsciiX2 += self.__pxCharWidth

                    # increment loop variable
                    colIdx += 1

                # increment loop variables
                row += 1
                pxPosY += self.__pxCharHeight

        painter.setBackgroundMode(Qt.BGMode.TransparentMode)
        painter.setPen(standardForeground)

        # paint cursor
        if self.__blink and not self.__readOnly and self.isActiveWindow():
            painter.fillRect(self.__cursorRect, standardForeground)
        else:
            if self.__hexDataShown:
                try:
                    c = chr(
                        self.__hexDataShown[
                            self.__cursorPosition - self.__bPosFirst * 2
                        ]
                    )
                except IndexError:
                    c = ""
            else:
                c = ""
            painter.drawText(self.__pxCursorX, self.__pxCursorY, c)

        if self.__asciiArea:
            painter.drawRect(self.__cursorRectAscii)

        # emit event, if size has changed
        if self.__lastEventSize != self.__chunks.size():
            self.__lastEventSize = self.__chunks.size()
            self.currentSizeChanged.emit(self.__lastEventSize)

    def resizeEvent(self, evt):
        """
        Protected method to handle resize events.

        @param evt reference to the resize event
        @type QResizeEvent
        """
        self.__adjust()

    def __resetSelection(self, pos=None):
        """
        Private method to reset the selection.

        @param pos position to set selection start and end to
            (if this is None, selection end is set to selection start)
        @type int or None
        """
        if pos is None:
            self.__bSelectionBegin = self.__bSelectionInit
            self.__bSelectionEnd = self.__bSelectionInit
        else:
            if pos < 0:
                pos = 0
            pos //= 2
            self.__bSelectionInit = pos
            self.__bSelectionBegin = pos
            self.__bSelectionEnd = pos

        self.selectionAvailable.emit(False)

    def __setSelection(self, pos):
        """
        Private method to set the selection.

        @param pos position
        @type int
        """
        if pos < 0:
            pos = 0
        pos //= 2
        if pos >= self.__bSelectionInit:
            self.__bSelectionEnd = pos
            self.__bSelectionBegin = self.__bSelectionInit
        else:
            self.__bSelectionBegin = pos
            self.__bSelectionEnd = self.__bSelectionInit

        self.selectionAvailable.emit(True)

    def getSelectionBegin(self):
        """
        Public method to get the start of the selection.

        @return selection start
        @rtype int
        """
        return self.__bSelectionBegin

    def getSelectionEnd(self):
        """
        Public method to get the end of the selection.

        @return selection end
        @rtype int
        """
        return self.__bSelectionEnd

    def getSelectionLength(self):
        """
        Public method to get the length of the selection.

        @return selection length
        @rtype int
        """
        return self.__bSelectionEnd - self.__bSelectionBegin

    def hasSelection(self):
        """
        Public method to test for a selection.

        @return flag indicating the presence of a selection
        @rtype bool
        """
        return self.__bSelectionBegin != self.__bSelectionEnd

    def __initialize(self):
        """
        Private method to do some initialization.
        """
        self.__undoStack.clear()
        self.setAddressOffset(0)
        self.__resetSelection(0)
        self.setCursorPosition(0)
        self.verticalScrollBar().setValue(0)
        self.__modified = False

    def __readBuffers(self):
        """
        Private method to read the buffers.
        """
        self.__dataShown = self.__chunks.data(
            self.__bPosFirst,
            self.__bPosLast - self.__bPosFirst + self.BYTES_PER_LINE + 1,
            self.__markedShown,
        )
        self.__hexDataShown = self.__toHex(self.__dataShown)

    def __toHex(self, byteArray):
        """
        Private method to convert the data of a Python bytearray to hex.

        @param byteArray byte array to be converted
        @type bytearray
        @return converted data
        @rtype bytearray
        """
        return bytearray(QByteArray(byteArray).toHex())

    def __fromHex(self, byteArray):
        """
        Private method to convert data of a Python bytearray from hex.

        @param byteArray byte array to be converted
        @type bytearray
        @return converted data
        @rtype bytearray
        """
        return bytearray(QByteArray.fromHex(byteArray))

    def __toReadable(self, byteArray):
        """
        Private method to convert some data into a readable format.

        @param byteArray data to be converted
        @type bytearray or QByteArray
        @return readable data
        @rtype str
        """
        byteArray = bytearray(byteArray)
        result = ""
        for i in range(0, len(byteArray), 16):
            addrStr = "{0:0{1}x}".format(self.__addressOffset + i, self.addressWidth())
            hexStr = ""
            ascStr = ""
            for j in range(16):
                if (i + j) < len(byteArray):
                    hexStr += " {0:02x}".format(byteArray[i + j])
                    by = byteArray[i + j]
                    if by < 0x20 or (by > 0x7E and by < 0xA0):
                        ch = "."
                    else:
                        ch = chr(by)
                    ascStr += ch
            result += "{0} {1:<48} {2:<17}\n".format(addrStr, hexStr, ascStr)
        return result

    @pyqtSlot()
    def __adjust(self):
        """
        Private slot to recalculate pixel positions.
        """
        # recalculate graphics
        if self.__addressArea:
            self.__addrDigits = self.addressWidth()
            self.__addrSeparators = self.__addrDigits // 4 - 1
            self.__pxPosHexX = (
                self.__pxGapAdr
                + (self.__addrDigits + self.__addrSeparators) * self.__pxCharWidth
                + self.__pxGapAdrHex
            )
        else:
            self.__pxPosHexX = self.__pxGapAdrHex
        self.__pxPosAdrX = self.__pxGapAdr
        self.__pxPosAsciiX = (
            self.__pxPosHexX
            + self.HEXCHARS_PER_LINE * self.__pxCharWidth
            + self.__pxGapHexAscii
        )

        # set horizontal scrollbar
        pxWidth = self.__pxPosAsciiX
        if self.__asciiArea:
            pxWidth += self.BYTES_PER_LINE * self.__pxCharWidth
        self.horizontalScrollBar().setRange(0, pxWidth - self.viewport().width())
        self.horizontalScrollBar().setPageStep(self.viewport().width())

        # set vertical scrollbar
        self.__rowsShown = (self.viewport().height() - 4) // self.__pxCharHeight
        lineCount = (self.__chunks.size() // self.BYTES_PER_LINE) + 1
        self.verticalScrollBar().setRange(0, lineCount - self.__rowsShown)
        self.verticalScrollBar().setPageStep(self.__rowsShown)

        # do the rest
        value = self.verticalScrollBar().value()
        self.__bPosFirst = value * self.BYTES_PER_LINE
        self.__bPosLast = self.__bPosFirst + self.__rowsShown * self.BYTES_PER_LINE - 1
        if self.__bPosLast >= self.__chunks.size():
            self.__bPosLast = self.__chunks.size() - 1
        self.__readBuffers()
        self.setCursorPosition(self.__cursorPosition)

    @pyqtSlot(int)
    def __dataChangedPrivate(self, idx=0):
        """
        Private slot to handle data changes.

        @param idx index
        @type int
        """
        self.__modified = (
            self.__undoStack.cleanIndex() == -1
            or self.__undoStack.index() != self.__undoStack.cleanIndex()
        )
        self.__adjust()
        self.dataChanged.emit(self.__modified)

    @pyqtSlot()
    def __refresh(self):
        """
        Private slot to refresh the display.
        """
        self.ensureVisible()
        self.__readBuffers()

    @pyqtSlot()
    def __updateCursor(self):
        """
        Private slot to update the blinking cursor.
        """
        self.__blink = not self.__blink
        self.viewport().update(self.__cursorRect)
