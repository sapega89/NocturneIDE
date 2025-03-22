# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the MicroPython REPL widget.
"""

import re

from PyQt6.QtCore import QPoint, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import (
    QBrush,
    QClipboard,
    QColor,
    QGuiApplication,
    QKeySequence,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricZoomWidget import EricZoomWidget
from eric7.SystemUtilities import OSUtilities

AnsiColorSchemes = {
    "Windows 7": {
        0: QBrush(QColor(0, 0, 0)),
        1: QBrush(QColor(128, 0, 0)),
        2: QBrush(QColor(0, 128, 0)),
        3: QBrush(QColor(128, 128, 0)),
        4: QBrush(QColor(0, 0, 128)),
        5: QBrush(QColor(128, 0, 128)),
        6: QBrush(QColor(0, 128, 128)),
        7: QBrush(QColor(192, 192, 192)),
        10: QBrush(QColor(128, 128, 128)),
        11: QBrush(QColor(255, 0, 0)),
        12: QBrush(QColor(0, 255, 0)),
        13: QBrush(QColor(255, 255, 0)),
        14: QBrush(QColor(0, 0, 255)),
        15: QBrush(QColor(255, 0, 255)),
        16: QBrush(QColor(0, 255, 255)),
        17: QBrush(QColor(255, 255, 255)),
    },
    "Windows 10": {
        0: QBrush(QColor(12, 12, 12)),
        1: QBrush(QColor(197, 15, 31)),
        2: QBrush(QColor(19, 161, 14)),
        3: QBrush(QColor(193, 156, 0)),
        4: QBrush(QColor(0, 55, 218)),
        5: QBrush(QColor(136, 23, 152)),
        6: QBrush(QColor(58, 150, 221)),
        7: QBrush(QColor(204, 204, 204)),
        10: QBrush(QColor(118, 118, 118)),
        11: QBrush(QColor(231, 72, 86)),
        12: QBrush(QColor(22, 198, 12)),
        13: QBrush(QColor(249, 241, 165)),
        14: QBrush(QColor(59, 12, 255)),
        15: QBrush(QColor(180, 0, 158)),
        16: QBrush(QColor(97, 214, 214)),
        17: QBrush(QColor(242, 242, 242)),
    },
    "PuTTY": {
        0: QBrush(QColor(0, 0, 0)),
        1: QBrush(QColor(187, 0, 0)),
        2: QBrush(QColor(0, 187, 0)),
        3: QBrush(QColor(187, 187, 0)),
        4: QBrush(QColor(0, 0, 187)),
        5: QBrush(QColor(187, 0, 187)),
        6: QBrush(QColor(0, 187, 187)),
        7: QBrush(QColor(187, 187, 187)),
        10: QBrush(QColor(85, 85, 85)),
        11: QBrush(QColor(255, 85, 85)),
        12: QBrush(QColor(85, 255, 85)),
        13: QBrush(QColor(255, 255, 85)),
        14: QBrush(QColor(85, 85, 255)),
        15: QBrush(QColor(255, 85, 255)),
        16: QBrush(QColor(85, 255, 255)),
        17: QBrush(QColor(255, 255, 255)),
    },
    "xterm": {
        0: QBrush(QColor(0, 0, 0)),
        1: QBrush(QColor(205, 0, 0)),
        2: QBrush(QColor(0, 205, 0)),
        3: QBrush(QColor(205, 205, 0)),
        4: QBrush(QColor(0, 0, 238)),
        5: QBrush(QColor(205, 0, 205)),
        6: QBrush(QColor(0, 205, 205)),
        7: QBrush(QColor(229, 229, 229)),
        10: QBrush(QColor(127, 127, 127)),
        11: QBrush(QColor(255, 0, 0)),
        12: QBrush(QColor(0, 255, 0)),
        13: QBrush(QColor(255, 255, 0)),
        14: QBrush(QColor(0, 0, 255)),
        15: QBrush(QColor(255, 0, 255)),
        16: QBrush(QColor(0, 255, 255)),
        17: QBrush(QColor(255, 255, 255)),
    },
    "Ubuntu": {
        0: QBrush(QColor(1, 1, 1)),
        1: QBrush(QColor(222, 56, 43)),
        2: QBrush(QColor(57, 181, 74)),
        3: QBrush(QColor(255, 199, 6)),
        4: QBrush(QColor(0, 11, 184)),
        5: QBrush(QColor(118, 38, 113)),
        6: QBrush(QColor(44, 181, 233)),
        7: QBrush(QColor(204, 204, 204)),
        10: QBrush(QColor(128, 128, 128)),
        11: QBrush(QColor(255, 0, 0)),
        12: QBrush(QColor(0, 255, 0)),
        13: QBrush(QColor(255, 255, 0)),
        14: QBrush(QColor(0, 0, 255)),
        15: QBrush(QColor(255, 0, 255)),
        16: QBrush(QColor(0, 255, 255)),
        17: QBrush(QColor(255, 255, 255)),
    },
    "Ubuntu (dark)": {
        0: QBrush(QColor(96, 96, 96)),
        1: QBrush(QColor(235, 58, 45)),
        2: QBrush(QColor(57, 181, 74)),
        3: QBrush(QColor(255, 199, 29)),
        4: QBrush(QColor(25, 56, 230)),
        5: QBrush(QColor(200, 64, 193)),
        6: QBrush(QColor(48, 200, 255)),
        7: QBrush(QColor(204, 204, 204)),
        10: QBrush(QColor(128, 128, 128)),
        11: QBrush(QColor(255, 0, 0)),
        12: QBrush(QColor(0, 255, 0)),
        13: QBrush(QColor(255, 255, 0)),
        14: QBrush(QColor(0, 0, 255)),
        15: QBrush(QColor(255, 0, 255)),
        16: QBrush(QColor(0, 255, 255)),
        17: QBrush(QColor(255, 255, 255)),
    },
    "Breeze (dark)": {
        0: QBrush(QColor(35, 38, 39)),
        1: QBrush(QColor(237, 21, 21)),
        2: QBrush(QColor(17, 209, 22)),
        3: QBrush(QColor(246, 116, 0)),
        4: QBrush(QColor(29, 153, 243)),
        5: QBrush(QColor(155, 89, 182)),
        6: QBrush(QColor(26, 188, 156)),
        7: QBrush(QColor(252, 252, 252)),
        10: QBrush(QColor(127, 140, 141)),
        11: QBrush(QColor(192, 57, 43)),
        12: QBrush(QColor(28, 220, 154)),
        13: QBrush(QColor(253, 188, 75)),
        14: QBrush(QColor(61, 174, 233)),
        15: QBrush(QColor(142, 68, 173)),
        16: QBrush(QColor(22, 160, 133)),
        17: QBrush(QColor(255, 255, 255)),
    },
}


class MicroPythonReplWidget(QWidget):
    """
    Class implementing the MicroPython REPL widget.
    """

    ZoomMin = -10
    ZoomMax = 20

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent=parent)

        self.__layout = QVBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)

        self.__zoomLayout = QHBoxLayout()
        self.__osdLabel = QLabel()
        self.__osdLabel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.__zoomLayout.addWidget(self.__osdLabel)

        self.__zoomWidget = EricZoomWidget(
            EricPixmapCache.getPixmap("zoomOut"),
            EricPixmapCache.getPixmap("zoomIn"),
            EricPixmapCache.getPixmap("zoomReset"),
            self,
        )
        self.__zoomWidget.setMinimum(self.ZoomMin)
        self.__zoomWidget.setMaximum(self.ZoomMax)
        self.__zoomLayout.addWidget(self.__zoomWidget)
        self.__layout.addLayout(self.__zoomLayout)

        self.__replEdit = MicroPythonReplEdit(self)
        self.__layout.addWidget(self.__replEdit)

        self.setLayout(self.__layout)

        self.__zoomWidget.valueChanged.connect(self.__replEdit.doZoom)
        self.__replEdit.osdInfo.connect(self.setOSDInfo)

    @pyqtSlot(str)
    def setOSDInfo(self, infoStr):
        """
        Public slot to set the OSD information.

        @param infoStr string to be shown
        @type str
        """
        self.__osdLabel.setText(infoStr)

    @pyqtSlot()
    def clearOSD(self):
        """
        Public slot to clear the OSD info.
        """
        self.__osdLabel.clear()

    def replEdit(self):
        """
        Public method to get a reference to the REPL edit.

        @return reference to the REPL edit
        @rtype MicroPythonReplEdit
        """
        return self.__replEdit


class MicroPythonReplEdit(QTextEdit):
    """
    Class implementing the REPL edit pane.

    @signal osdInfo(str) emitted when some OSD data was received from the device
    """

    osdInfo = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent=parent)

        self.setAcceptRichText(False)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.__currentZoom = 0

        self.__replBuffer = b""

        self.__vt100Re = re.compile(
            r"(?P<count>\d*)(?P<color>(?:;?\d*)*)(?P<action>[ABCDKm])"
        )

        self.customContextMenuRequested.connect(self.__showContextMenu)

        charFormat = self.currentCharFormat()
        self.DefaultForeground = charFormat.foreground()
        self.DefaultBackground = charFormat.background()

        self.__interface = None

    def setInterface(self, deviceInterface):
        """
        Public method to set the reference to the device interface object.

        @param deviceInterface reference to the device interface object
        @type MicroPythonDeviceInterface
        """
        self.__interface = deviceInterface

    @pyqtSlot(int)
    def doZoom(self, value):
        """
        Public slot to zoom in or out.

        @param value zoom value
        @type int
        """
        if value < self.__currentZoom:
            self.zoomOut(self.__currentZoom - value)
        elif value > self.__currentZoom:
            self.zoomIn(value - self.__currentZoom)
        self.__currentZoom = value

    @pyqtSlot(QPoint)
    def __showContextMenu(self, pos):
        """
        Private slot to show the REPL context menu.

        @param pos position to show the menu at
        @type QPoint
        """
        connected = bool(self.__interface) and self.__interface.isConnected()

        if OSUtilities.isMacPlatform():
            copyKeys = QKeySequence("Ctrl+C")
            pasteKeys = QKeySequence("Ctrl+V")
            selectAllKeys = QKeySequence("Ctrl+A")
        else:
            copyKeys = QKeySequence("Ctrl+Shift+C")
            pasteKeys = QKeySequence("Ctrl+Shift+V")
            selectAllKeys = QKeySequence("Ctrl+Shift+A")

        menu = QMenu(self)
        menu.addAction(
            EricPixmapCache.getIcon("editDelete"), self.tr("Clear"), self.__clear
        ).setEnabled(bool(self.toPlainText()))
        menu.addSeparator()
        menu.addAction(
            EricPixmapCache.getIcon("editCopy"),
            self.tr("Copy"),
            copyKeys,
            self.copy,
        ).setEnabled(self.textCursor().hasSelection())
        menu.addAction(
            EricPixmapCache.getIcon("editPaste"),
            self.tr("Paste"),
            pasteKeys,
            self.__paste,
        ).setEnabled(self.canPaste() and connected)
        menu.addSeparator()
        menu.addAction(
            EricPixmapCache.getIcon("editSelectAll"),
            self.tr("Select All"),
            selectAllKeys,
            self.selectAll,
        ).setEnabled(bool(self.toPlainText()))

        menu.exec(self.mapToGlobal(pos))

    @pyqtSlot()
    def handlePreferencesChanged(self):
        """
        Public slot to handle a change in preferences.
        """
        self.__colorScheme = Preferences.getMicroPython("ColorScheme")

        self.__font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.setFontFamily(self.__font.family())
        self.setFontPointSize(self.__font.pointSize())

        if Preferences.getMicroPython("ReplLineWrap"):
            self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

    @pyqtSlot()
    def __clear(self):
        """
        Private slot to clear the REPL pane.
        """
        self.clear()
        if bool(self.__interface) and self.__interface.isConnected():
            self.__interface.write(b"\r")

    @pyqtSlot()
    def __paste(self, mode=QClipboard.Mode.Clipboard):
        """
        Private slot to perform a paste operation.

        @param mode paste mode (defaults to QClipboard.Mode.Clipboard)
        @type QClipboard.Mode (optional)
        """
        # add support for paste by mouse middle button
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            pasteText = clipboard.text(mode=mode)
            if pasteText:
                pasteText = pasteText.replace("\n\r", "\r")
                pasteText = pasteText.replace("\n", "\r")
                if bool(self.__interface) and self.__interface.isConnected():
                    self.__interface.write(b"\x05")
                    self.__interface.write(pasteText.encode("utf-8"))
                    self.__interface.write(b"\x04")

    def keyPressEvent(self, evt):
        """
        Protected method to handle key press events.

        @param evt reference to the key press event
        @type QKeyEvent
        """
        key = evt.key()
        msg = bytes(evt.text(), "utf8")
        if key == Qt.Key.Key_Backspace:
            msg = b"\b"
        elif key == Qt.Key.Key_Delete:
            msg = b"\x1b[\x33\x7e"
        elif key == Qt.Key.Key_Up:
            msg = b"\x1b[A"
        elif key == Qt.Key.Key_Down:
            msg = b"\x1b[B"
        elif key == Qt.Key.Key_Right:
            msg = b"\x1b[C"
        elif key == Qt.Key.Key_Left:
            msg = b"\x1b[D"
        elif key == Qt.Key.Key_Home:
            msg = b"\x1b[H"
        elif key == Qt.Key.Key_End:
            msg = b"\x1b[F"
        elif (
            OSUtilities.isMacPlatform()
            and evt.modifiers() == Qt.KeyboardModifier.MetaModifier
        ) or (
            not OSUtilities.isMacPlatform()
            and evt.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
                # devices treat an input of \x01 as Ctrl+A, etc.
                msg = bytes([1 + key - Qt.Key.Key_A])
        elif evt.modifiers() == (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        ) or (
            OSUtilities.isMacPlatform()
            and evt.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            if key == Qt.Key.Key_C:
                self.copy()
                msg = b""
            elif key == Qt.Key.Key_V:
                self.__paste()
                msg = b""
            elif key == Qt.Key.Key_A:
                self.selectAll()
                msg = b""
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            tc = self.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.EndOfLine)
            self.setTextCursor(tc)
        if bool(self.__interface) and self.__interface.isConnected():
            self.__interface.write(msg)

        evt.accept()

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle mouse release events.

        @param evt reference to the event object
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.MiddleButton:
            self.__paste(mode=QClipboard.Mode.Selection)
            msg = b""
            if bool(self.__interface) and self.__interface.isConnected():
                self.__interface.write(msg)
            evt.accept()
        else:
            super().mouseReleaseEvent(evt)

    @pyqtSlot(bytes)
    def processData(self, data):
        """
        Public slot to process the data received from the device.

        @param data data received from the device
        @type bytes
        """
        tc = self.textCursor()
        # the text cursor must be on the last line
        while tc.movePosition(QTextCursor.MoveOperation.Down):
            pass

        # reset the font
        self.__setCharFormat(None, tc)

        # add received data to the buffered one
        data = self.__replBuffer + data

        index = 0
        while index < len(data):
            if data[index] == 8:  # \b
                tc.movePosition(QTextCursor.MoveOperation.Left)
                self.setTextCursor(tc)
            elif data[index] in (4, 13):  # EOT, \r
                pass
            elif len(data) > index + 1 and data[index] == 27 and data[index + 1] == 91:
                # VT100 cursor command detected: <Esc>[
                index += 2  # move index to after the [
                match = self.__vt100Re.search(
                    data[index:].decode("utf-8", errors="replace")
                )
                if match:
                    # move to last position in control sequence
                    # ++ will be done at end of loop
                    index += match.end() - 1

                    action = match.group("action")
                    if action in "ABCD":
                        if match.group("count") == "":
                            count = 1
                        else:
                            count = int(match.group("count"))

                        if action == "A":  # up
                            tc.movePosition(QTextCursor.MoveOperation.Up, n=count)
                            self.setTextCursor(tc)
                        elif action == "B":  # down
                            tc.movePosition(QTextCursor.MoveOperation.Down, n=count)
                            self.setTextCursor(tc)
                        elif action == "C":  # right
                            tc.movePosition(QTextCursor.MoveOperation.Right, n=count)
                            self.setTextCursor(tc)
                        elif action == "D":  # left
                            tc.movePosition(QTextCursor.MoveOperation.Left, n=count)
                            self.setTextCursor(tc)
                    elif action == "K":  # delete things
                        if match.group("count") in ("", "0"):
                            # delete to end of line
                            tc.movePosition(
                                QTextCursor.MoveOperation.EndOfLine,
                                mode=QTextCursor.MoveMode.KeepAnchor,
                            )
                            tc.removeSelectedText()
                            self.setTextCursor(tc)
                        elif match.group("count") == "1":
                            # delete to beginning of line
                            tc.movePosition(
                                QTextCursor.MoveOperation.StartOfLine,
                                mode=QTextCursor.MoveMode.KeepAnchor,
                            )
                            tc.removeSelectedText()
                            self.setTextCursor(tc)
                        elif match.group("count") == "2":
                            # delete whole line
                            tc.movePosition(QTextCursor.MoveOperation.EndOfLine)
                            tc.movePosition(
                                QTextCursor.MoveOperation.StartOfLine,
                                mode=QTextCursor.MoveMode.KeepAnchor,
                            )
                            tc.removeSelectedText()
                            self.setTextCursor(tc)
                    elif action == "m":
                        self.__setCharFormat(match.group(0)[:-1].split(";"), tc)
            elif (
                len(data) > index + 1
                and data[index] == 27
                and data[index + 1 : index + 4] == b"]0;"
            ):
                if b"\x1b\\" in data[index + 4 :]:
                    # 'set window title' command detected: <Esc>]0;...<Esc>\
                    # __IGNORE_WARNING_M891__
                    titleData = data[index + 4 :].split(b"\x1b\\")[0]
                    title = titleData.decode("utf-8")
                    index += len(titleData) + 5  # one more is done at the end
                    self.osdInfo.emit(title)
                else:
                    # data is incomplete; buffer and stop processing
                    self.__replBuffer = data[index:]
                    return
            else:
                tc.deleteChar()
                self.setTextCursor(tc)
                # unicode handling
                if data[index] & 0b11110000 == 0b11110000:
                    length = 4
                elif data[index] & 0b11100000 == 0b11100000:
                    length = 3
                elif data[index] & 0b11000000 == 0b11000000:
                    length = 2
                else:
                    length = 1
                try:
                    txt = data[index : index + length].decode("utf8")
                except UnicodeDecodeError:
                    txt = data[index : index + length].decode("iso8859-1")
                index += length - 1  # one more is done at the end
                self.insertPlainText(txt)

            index += 1

        self.ensureCursorVisible()
        self.__replBuffer = b""

    def __setCharFormat(self, formatCodes, textCursor):
        """
        Private method setting the current text format of the REPL pane based
        on the passed ANSI codes.

        Following codes are used:
        <ul>
        <li>0: Reset</li>
        <li>1: Bold font (weight 75)</li>
        <li>2: Light font (weight 25)</li>
        <li>3: Italic font</li>
        <li>4: Underlined font</li>
        <li>9: Strikeout font</li>
        <li>21: Bold off (weight 50)</li>
        <li>22: Light off (weight 50)</li>
        <li>23: Italic off</li>
        <li>24: Underline off</li>
        <li>29: Strikeout off</li>
        <li>30: foreground Black</li>
        <li>31: foreground Dark Red</li>
        <li>32: foreground Dark Green</li>
        <li>33: foreground Dark Yellow</li>
        <li>34: foreground Dark Blue</li>
        <li>35: foreground Dark Magenta</li>
        <li>36: foreground Dark Cyan</li>
        <li>37: foreground Light Gray</li>
        <li>39: reset foreground to default</li>
        <li>40: background Black</li>
        <li>41: background Dark Red</li>
        <li>42: background Dark Green</li>
        <li>43: background Dark Yellow</li>
        <li>44: background Dark Blue</li>
        <li>45: background Dark Magenta</li>
        <li>46: background Dark Cyan</li>
        <li>47: background Light Gray</li>
        <li>49: reset background to default</li>
        <li>53: Overlined font</li>
        <li>55: Overline off</li>
        <li>90: bright foreground Dark Gray</li>
        <li>91: bright foreground Red</li>
        <li>92: bright foreground Green</li>
        <li>93: bright foreground Yellow</li>
        <li>94: bright foreground Blue</li>
        <li>95: bright foreground Magenta</li>
        <li>96: bright foreground Cyan</li>
        <li>97: bright foreground White</li>
        <li>100: bright background Dark Gray</li>
        <li>101: bright background Red</li>
        <li>102: bright background Green</li>
        <li>103: bright background Yellow</li>
        <li>104: bright background Blue</li>
        <li>105: bright background Magenta</li>
        <li>106: bright background Cyan</li>
        <li>107: bright background White</li>
        </ul>

        @param formatCodes list of format codes
        @type list of str
        @param textCursor reference to the text cursor
        @type QTextCursor
        """
        if not formatCodes:
            # empty format codes list is treated as a reset
            formatCodes = ["0"]

        charFormat = textCursor.charFormat()
        charFormat.setFontFamilies([self.__font.family()])
        charFormat.setFontPointSize(self.__font.pointSize())

        for formatCode in formatCodes:
            try:
                formatCode = int(formatCode)
            except ValueError:
                # ignore non digit values
                continue

            if formatCode == 0:
                charFormat.setFontWeight(50)
                charFormat.setFontItalic(False)
                charFormat.setFontUnderline(False)
                charFormat.setFontStrikeOut(False)
                charFormat.setFontOverline(False)
                charFormat.setForeground(self.DefaultForeground)
                charFormat.setBackground(self.DefaultBackground)
            elif formatCode == 1:
                charFormat.setFontWeight(75)
            elif formatCode == 2:
                charFormat.setFontWeight(25)
            elif formatCode == 3:
                charFormat.setFontItalic(True)
            elif formatCode == 4:
                charFormat.setFontUnderline(True)
            elif formatCode == 9:
                charFormat.setFontStrikeOut(True)
            elif formatCode in (21, 22):
                charFormat.setFontWeight(50)
            elif formatCode == 23:
                charFormat.setFontItalic(False)
            elif formatCode == 24:
                charFormat.setFontUnderline(False)
            elif formatCode == 29:
                charFormat.setFontStrikeOut(False)
            elif formatCode == 53:
                charFormat.setFontOverline(True)
            elif formatCode == 55:
                charFormat.setFontOverline(False)
            elif formatCode in (30, 31, 32, 33, 34, 35, 36, 37):
                charFormat.setForeground(
                    AnsiColorSchemes[self.__colorScheme][formatCode - 30]
                )
            elif formatCode in (40, 41, 42, 43, 44, 45, 46, 47):
                charFormat.setBackground(
                    AnsiColorSchemes[self.__colorScheme][formatCode - 40]
                )
            elif formatCode in (90, 91, 92, 93, 94, 95, 96, 97):
                charFormat.setForeground(
                    AnsiColorSchemes[self.__colorScheme][formatCode - 80]
                )
            elif formatCode in (100, 101, 102, 103, 104, 105, 106, 107):
                charFormat.setBackground(
                    AnsiColorSchemes[self.__colorScheme][formatCode - 90]
                )
            elif formatCode == 39:
                charFormat.setForeground(self.DefaultForeground)
            elif formatCode == 49:
                charFormat.setBackground(self.DefaultBackground)

        textCursor.setCharFormat(charFormat)
