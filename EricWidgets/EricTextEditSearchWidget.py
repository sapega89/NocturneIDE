# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a horizontal search widget for QTextEdit.
"""

import enum

from PyQt6.QtCore import QMetaObject, QSize, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPalette, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from eric7.EricGui import EricPixmapCache


class EricTextEditType(enum.Enum):
    """
    Class defining the supported text edit types.
    """

    UNKNOWN = 0
    QTEXTEDIT = 1
    QTEXTBROWSER = 2
    QWEBENGINEVIEW = 3


class EricTextEditSearchWidget(QWidget):
    """
    Class implementing a horizontal search widget for QTextEdit.

    @signal closePressed() emitted to indicate the closing of the widget via
        the close button
    """

    closePressed = pyqtSignal()

    def __init__(self, parent=None, widthForHeight=True, enableClose=False):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param widthForHeight flag indicating to prefer width for height.
            If this parameter is False, some widgets are shown in a third
            line.
        @type bool
        @param enableClose flag indicating to show a close button
        @type bool
        """
        super().__init__(parent)
        self.__setupUi(widthForHeight, enableClose)

        self.__textedit = None
        self.__texteditType = EricTextEditType.UNKNOWN
        self.__findBackwards = False

        self.__defaultBaseColor = (
            self.findtextCombo.lineEdit().palette().color(QPalette.ColorRole.Base)
        )
        self.__defaultTextColor = (
            self.findtextCombo.lineEdit().palette().color(QPalette.ColorRole.Text)
        )

        self.findHistory = []

        self.findtextCombo.setCompleter(None)
        self.findtextCombo.lineEdit().returnPressed.connect(self.__findByReturnPressed)
        self.findtextCombo.lineEdit().setClearButtonEnabled(True)

        self.__setSearchButtons(False)
        self.infoLabel.hide()

        self.setFocusProxy(self.findtextCombo)

    def __setupUi(self, widthForHeight, enableClose):
        """
        Private method to generate the UI.

        @param widthForHeight flag indicating to prefer width for height
        @type bool
        @param enableClose flag indicating to show a close button
        @type bool
        """
        self.setObjectName("EricTextEditSearchWidget")

        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

        # row 1 of widgets
        self.horizontalLayout1 = QHBoxLayout()
        self.horizontalLayout1.setObjectName("horizontalLayout1")

        if enableClose:
            self.closeButton = QToolButton(self)
            self.closeButton.setIcon(EricPixmapCache.getIcon("close"))
            self.closeButton.clicked.connect(self.__closeButtonClicked)
            self.horizontalLayout1.addWidget(self.closeButton)
        else:
            self.closeButton = None

        self.label = QLabel(self)
        self.label.setObjectName("label")
        self.label.setText(self.tr("Find:"))
        self.horizontalLayout1.addWidget(self.label)

        self.findtextCombo = QComboBox(self)
        self.findtextCombo.setEditable(True)
        self.findtextCombo.lineEdit().setClearButtonEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.findtextCombo.sizePolicy().hasHeightForWidth()
        )
        self.findtextCombo.setSizePolicy(sizePolicy)
        self.findtextCombo.setMinimumSize(QSize(100, 0))
        self.findtextCombo.setEditable(True)
        self.findtextCombo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.findtextCombo.setDuplicatesEnabled(False)
        self.findtextCombo.setObjectName("findtextCombo")
        self.horizontalLayout1.addWidget(self.findtextCombo)

        # row 2 (maybe) of widgets
        self.horizontalLayout2 = QHBoxLayout()
        self.horizontalLayout2.setObjectName("horizontalLayout2")

        self.caseCheckBox = QCheckBox(self)
        self.caseCheckBox.setObjectName("caseCheckBox")
        self.caseCheckBox.setText(self.tr("Match case"))
        self.caseCheckBox.setToolTip(self.tr("Select to match case sensitive"))
        self.horizontalLayout2.addWidget(self.caseCheckBox)

        self.wordCheckBox = QCheckBox(self)
        self.wordCheckBox.setObjectName("wordCheckBox")
        self.wordCheckBox.setText(self.tr("Whole word"))
        self.wordCheckBox.setToolTip(self.tr("Select to match whole words only"))
        self.horizontalLayout2.addWidget(self.wordCheckBox)

        # layout for the navigation buttons
        self.horizontalLayout3 = QHBoxLayout()
        self.horizontalLayout3.setSpacing(0)
        self.horizontalLayout3.setObjectName("horizontalLayout3")

        self.findPrevButton = QToolButton(self)
        self.findPrevButton.setObjectName("findPrevButton")
        self.findPrevButton.setToolTip(self.tr("Press to find the previous occurrence"))
        self.findPrevButton.setIcon(EricPixmapCache.getIcon("1leftarrow"))
        self.horizontalLayout3.addWidget(self.findPrevButton)

        self.findNextButton = QToolButton(self)
        self.findNextButton.setObjectName("findNextButton")
        self.findNextButton.setToolTip(self.tr("Press to find the next occurrence"))
        self.findNextButton.setIcon(EricPixmapCache.getIcon("1rightarrow"))
        self.horizontalLayout3.addWidget(self.findNextButton)

        self.horizontalLayout2.addLayout(self.horizontalLayout3)

        # info label (in row 2 or 3)
        self.infoLabel = QLabel(self)
        self.infoLabel.setText("")
        self.infoLabel.setObjectName("infoLabel")

        # place everything together
        self.verticalLayout.addLayout(self.horizontalLayout1)
        self.__addWidthForHeightLayout(widthForHeight)
        self.verticalLayout.addWidget(self.infoLabel)

        QMetaObject.connectSlotsByName(self)

        self.setTabOrder(self.findtextCombo, self.caseCheckBox)
        self.setTabOrder(self.caseCheckBox, self.wordCheckBox)
        self.setTabOrder(self.wordCheckBox, self.findPrevButton)
        self.setTabOrder(self.findPrevButton, self.findNextButton)

        self.__isActive = False  # trace the activation state

    def setWidthForHeight(self, widthForHeight):
        """
        Public method to set the 'width for height'.

        @param widthForHeight flag indicating to prefer width
        @type bool
        """
        if self.__widthForHeight:
            self.horizontalLayout1.takeAt(self.__widthForHeightLayoutIndex)
        else:
            self.verticalLayout.takeAt(self.__widthForHeightLayoutIndex)
        self.__addWidthForHeightLayout(widthForHeight)

    def __addWidthForHeightLayout(self, widthForHeight):
        """
        Private method to set the middle part of the layout.

        @param widthForHeight flag indicating to prefer width
        @type bool
        """
        if widthForHeight:
            self.horizontalLayout1.addLayout(self.horizontalLayout2)
            self.__widthForHeightLayoutIndex = 2
        else:
            self.verticalLayout.insertLayout(1, self.horizontalLayout2)
            self.__widthForHeightLayoutIndex = 1

        self.__widthForHeight = widthForHeight

    def attachTextEdit(self, textedit, editType=EricTextEditType.QTEXTEDIT):
        """
        Public method to attach a QTextEdit or QWebEngineView widget.

        @param textedit reference to the edit widget to be attached
        @type QTextEdit, QTextBrowser or QWebEngineView
        @param editType type of the attached edit widget
        @type EricTextEditType
        """
        if self.__textedit is not None:
            self.detachTextEdit()

        self.__textedit = textedit
        self.__texteditType = editType

        self.wordCheckBox.setVisible(
            editType in (EricTextEditType.QTEXTEDIT, EricTextEditType.QTEXTBROWSER)
        )
        self.infoLabel.setVisible(editType == EricTextEditType.QWEBENGINEVIEW)

    def detachTextEdit(self):
        """
        Public method to detach the current text edit.
        """
        self.__textedit = None
        self.__texteditType = EricTextEditType.UNKNOWN

    @pyqtSlot()
    def activate(self):
        """
        Public slot to activate the widget.
        """
        self.show()
        self.findtextCombo.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.findtextCombo.lineEdit().selectAll()
        self.infoLabel.clear()

        self.__isActive = True

    @pyqtSlot()
    def deactivate(self):
        """
        Public slot to deactivate the widget.
        """
        if self.__textedit:
            self.__textedit.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
            if (
                self.__texteditType == EricTextEditType.QWEBENGINEVIEW
                and self.__isActive
            ):
                self.__textedit.findText("")
        if self.closeButton is not None:
            self.hide()
            self.closePressed.emit()

        self.__isActive = False

    @pyqtSlot()
    def __closeButtonClicked(self):
        """
        Private slot to close the widget.

        Note: The widget is just hidden.
        """
        self.deactivate()

    def keyPressEvent(self, event):
        """
        Protected slot to handle key press events.

        @param event reference to the key press event
        @type QKeyEvent
        """
        if self.__textedit:
            key = event.key()
            modifiers = event.modifiers()

            if key == Qt.Key.Key_Escape:
                self.deactivate()
                event.accept()

            elif key == Qt.Key.Key_F3:
                if modifiers == Qt.KeyboardModifier.NoModifier:
                    # search forward
                    self.on_findNextButton_clicked()
                    event.accept()
                elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                    # search backward
                    self.on_findPrevButton_clicked()
                    event.accept()

    @pyqtSlot(str)
    def on_findtextCombo_editTextChanged(self, txt):
        """
        Private slot to enable/disable the find buttons.

        @param txt text of the combobox
        @type str
        """
        self.__setSearchButtons(txt != "")

        if self.__texteditType == EricTextEditType.QWEBENGINEVIEW:
            self.infoLabel.clear()
        else:
            self.infoLabel.hide()
        self.__setFindtextComboBackground(False)

    def __setSearchButtons(self, enabled):
        """
        Private slot to set the state of the search buttons.

        @param enabled flag indicating the state
        @type bool
        """
        self.findPrevButton.setEnabled(enabled)
        self.findNextButton.setEnabled(enabled)

    def __findByReturnPressed(self):
        """
        Private slot to handle the returnPressed signal of the findtext
        combobox.
        """
        self.__find(self.__findBackwards)

    @pyqtSlot()
    def on_findPrevButton_clicked(self):
        """
        Private slot to find the previous occurrence.
        """
        self.__find(True)

    @pyqtSlot()
    def on_findNextButton_clicked(self):
        """
        Private slot to find the next occurrence.
        """
        self.__find(False)

    @pyqtSlot()
    def findPrev(self):
        """
        Public slot to find the previous occurrence of the current search term.
        """
        self.on_findPrevButton_clicked()

    @pyqtSlot()
    def findNext(self):
        """
        Public slot to find the next occurrence of the current search term.
        """
        self.on_findNextButton_clicked()

    def __find(self, backwards):
        """
        Private method to search the associated text edit.

        @param backwards flag indicating a backwards search
        @type bool
        """
        if not self.__textedit:
            return

        self.show()
        self.__isActive = True

        self.infoLabel.clear()
        if self.__texteditType != EricTextEditType.QWEBENGINEVIEW:
            self.infoLabel.hide()
        self.__setFindtextComboBackground(False)

        txt = self.findtextCombo.currentText()
        if not txt:
            return
        self.__findBackwards = backwards

        # This moves any previous occurrence of this statement to the head
        # of the list and updates the combobox
        if txt in self.findHistory:
            self.findHistory.remove(txt)
        self.findHistory.insert(0, txt)
        self.findtextCombo.clear()
        self.findtextCombo.addItems(self.findHistory)

        if self.__texteditType in (
            EricTextEditType.QTEXTBROWSER,
            EricTextEditType.QTEXTEDIT,
        ):
            self.__findPrevNextQTextEdit(backwards)
        elif self.__texteditType == EricTextEditType.QWEBENGINEVIEW:
            self.__findPrevNextQWebEngineView(backwards)

    def __findPrevNextQTextEdit(self, backwards):
        """
        Private method to to search the associated edit widget of
        type QTextEdit.

        @param backwards flag indicating a backwards search
        @type bool
        """
        flags = (
            QTextDocument.FindFlag.FindBackward
            if backwards
            else QTextDocument.FindFlag(0)
        )
        if self.caseCheckBox.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if self.wordCheckBox.isChecked():
            flags |= QTextDocument.FindFlag.FindWholeWords

        ok = self.__textedit.find(self.findtextCombo.currentText(), flags)
        if not ok:
            # wrap around once
            cursor = self.__textedit.textCursor()
            if backwards:
                moveOp = QTextCursor.MoveOperation.End
                # move to end of document
            else:
                moveOp = QTextCursor.MoveOperation.Start
                # move to start of document
            cursor.movePosition(moveOp)
            self.__textedit.setTextCursor(cursor)
            ok = self.__textedit.find(self.findtextCombo.currentText(), flags)

        if not ok:
            self.infoLabel.setText(
                self.tr("'{0}' was not found.").format(self.findtextCombo.currentText())
            )
            self.infoLabel.show()
            self.__setFindtextComboBackground(True)

    def __findPrevNextQWebEngineView(self, backwards):
        """
        Private method to to search the associated edit widget of
        type QWebEngineView.

        @param backwards flag indicating a backwards search
        @type bool
        """
        from PyQt6.QtWebEngineCore import QWebEnginePage  # noqa: I102

        if self.findtextCombo.currentText():
            findFlags = QWebEnginePage.FindFlag(0)
            if self.caseCheckBox.isChecked():
                findFlags |= QWebEnginePage.FindFlag.FindCaseSensitively
            if backwards:
                findFlags |= QWebEnginePage.FindFlag.FindBackward
            self.__textedit.findText(
                self.findtextCombo.currentText(), findFlags, self.__findTextFinished
            )

    def __setFindtextComboBackground(self, error):
        """
        Private slot to change the findtext combo background to indicate
        errors.

        @param error flag indicating an error condition
        @type bool
        """
        styleSheet = (
            "color: #000000; background-color: #ff6666"
            if error
            else f"color: {self.__defaultTextColor};"
            f" background-color: {self.__defaultBaseColor}"
        )
        self.findtextCombo.setStyleSheet(styleSheet)

    def __findTextFinished(self, result):
        """
        Private method handling the find result of the web page search.

        Note: This method is used as the callback of the 'findText()' method call.

        @param result reference to the QWebEngineFindTextResult object of the
            last search
        @type QWebEngineFindTextResult
        """
        if result.numberOfMatches() == 0:
            self.infoLabel.setText(
                self.tr("'{0}' was not found.").format(self.findtextCombo.currentText())
            )
            self.__setFindtextComboBackground(True)
        else:
            self.infoLabel.setText(
                self.tr("Match {0} of {1}").format(
                    result.activeMatch(), result.numberOfMatches()
                )
            )

    def showInfo(self, info):
        """
        Public method to show some information in the info label.

        @param info informational text to be shown
        @type str
        """
        self.infoLabel.setText(info)
        self.infoLabel.show()
