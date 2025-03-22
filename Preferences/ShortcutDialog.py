# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for the configuration of a keyboard shortcut.
"""

from PyQt6.QtCore import QEvent, QKeyCombination, Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_ShortcutDialog import Ui_ShortcutDialog


class ShortcutDialog(QDialog, Ui_ShortcutDialog):
    """
    Class implementing a dialog for the configuration of a keyboard shortcut.

    @signal shortcutChanged(QKeySequence, QKeySequence, bool, string) emitted
        after the OK button was pressed
    """

    shortcutChanged = pyqtSignal(QKeySequence, QKeySequence, bool, str)

    def __init__(self, parent=None, name=None, modal=False):
        """
        Constructor

        @param parent The parent widget of this dialog.
        @type QWidget
        @param name The name of this dialog.
        @type str
        @param modal Flag indicating a modal dialog.
        @type bool
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.setModal(modal)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__clearKeys()

        self.noCheck = False
        self.objectType = ""

        self.primaryClearButton.clicked.connect(self.__clear)
        self.alternateClearButton.clicked.connect(self.__clear)
        self.primaryButton.clicked.connect(self.__typeChanged)
        self.alternateButton.clicked.connect(self.__typeChanged)

        self.shortcutsGroup.installEventFilter(self)
        self.primaryButton.installEventFilter(self)
        self.alternateButton.installEventFilter(self)
        self.primaryClearButton.installEventFilter(self)
        self.alternateClearButton.installEventFilter(self)
        self.keyEdit.installEventFilter(self)
        self.alternateKeyEdit.installEventFilter(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).installEventFilter(
            self
        )
        self.buttonBox.button(
            QDialogButtonBox.StandardButton.Cancel
        ).installEventFilter(self)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __clearKeys(self):
        """
        Private method to clear the list of recorded keys.
        """
        self.keyIndex = 0
        self.keys = [
            QKeyCombination(),
            QKeyCombination(),
            QKeyCombination(),
            QKeyCombination(),
        ]

    def setKeys(self, key, alternateKey, noCheck, objectType):
        """
        Public method to set the key to be configured.

        @param key key sequence to be changed
        @type QKeySequence
        @param alternateKey alternate key sequence to be changed
        @type QKeySequence
        @param noCheck flag indicating that no uniqueness check should
            be performed
        @type bool
        @param objectType type of the object
        @type str
        """
        self.__clearKeys()

        self.keyEdit.setText(key.toString())
        self.alternateKeyEdit.setText(alternateKey.toString())
        self.primaryButton.setChecked(True)
        self.noCheck = noCheck
        self.objectType = objectType

    def on_buttonBox_accepted(self):
        """
        Private slot to handle the OK button press.
        """
        self.hide()
        self.shortcutChanged.emit(
            QKeySequence(self.keyEdit.text()),
            QKeySequence(self.alternateKeyEdit.text()),
            self.noCheck,
            self.objectType,
        )

    def __clear(self):
        """
        Private slot to handle the Clear button press.
        """
        self.__clearKeys()
        self.__setKeyEditText("")

    def __typeChanged(self):
        """
        Private slot to handle the change of the shortcuts type.
        """
        self.__clearKeys()

    def __setKeyEditText(self, txt):
        """
        Private method to set the text of a key edit.

        @param txt text to be set
        @type str
        """
        if self.primaryButton.isChecked():
            self.keyEdit.setText(txt)
        else:
            self.alternateKeyEdit.setText(txt)

    def eventFilter(self, _watched, event):
        """
        Public method called to filter the event queue.

        @param _watched reference to the QObject being watched (unused)
        @type QObject
        @param event the event that occurred
        @type QEvent
        @return always False
        @rtype bool
        """
        if event.type() == QEvent.Type.KeyPress:
            self.keyPressEvent(event)
            return True

        return False

    def keyPressEvent(self, evt):
        """
        Protected method to handle a key press event.

        @param evt the key event
        @type QKeyEvent
        """
        if evt.key() in [
            Qt.Key.Key_Control,
            Qt.Key.Key_Meta,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Menu,
            Qt.Key.Key_Hyper_L,
            Qt.Key.Key_Hyper_R,
            Qt.Key.Key_Super_L,
            Qt.Key.Key_Super_R,
        ]:
            return

        if self.keyIndex == 4:
            self.__clearKeys()

        if (
            evt.key() == Qt.Key.Key_Backtab
            and evt.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.keys[self.keyIndex] = QKeyCombination(evt.modifiers(), Qt.Key.Key_Tab)
        else:
            self.keys[self.keyIndex] = QKeyCombination(
                evt.modifiers(), Qt.Key(evt.key())
            )

        self.keyIndex += 1

        if self.keyIndex == 1:
            ks = QKeySequence(self.keys[0])
        elif self.keyIndex == 2:
            ks = QKeySequence(self.keys[0], self.keys[1])
        elif self.keyIndex == 3:
            ks = QKeySequence(self.keys[0], self.keys[1], self.keys[2])
        elif self.keyIndex == 4:
            ks = QKeySequence(self.keys[0], self.keys[1], self.keys[2], self.keys[3])
        self.__setKeyEditText(ks.toString(QKeySequence.SequenceFormat.NativeText))
