# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget containing various buttons for accessing
editor actions.
"""

import contextlib

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QFrame,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache

from . import MarkupProviders


class EditorButtonsWidget(QWidget):
    """
    Class implementing a widget containing various buttons for accessing
    editor actions.
    """

    def __init__(self, editor, parent=None):
        """
        Constructor

        @param editor reference to the editor
        @type Editor
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        margin = 2
        spacing = 3

        self.__buttonsWidget = QWidget(self)

        self.__layout = QVBoxLayout(self.__buttonsWidget)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setSpacing(spacing)

        self.__provider = None

        self.__editor = editor
        self.__editor.languageChanged.connect(self.__updateButtonStates)
        self.__editor.editorSaved.connect(self.__updateButtonStates)
        self.__editor.editorRenamed.connect(self.__updateButtonStates)
        self.__editor.selectionChanged.connect(self.__editorSelectionChanged)
        self.__editor.settingsRead.connect(self.__editorSettingsRead)

        self.__createButtons()

        self.__layout.addStretch()

        self.__outerLayout = QVBoxLayout(self)
        self.__outerLayout.setContentsMargins(margin, margin, margin, margin)
        self.__outerLayout.setSpacing(spacing)
        self.__outerLayout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.__upButton = QToolButton(self)
        self.__upButton.setArrowType(Qt.ArrowType.UpArrow)
        self.__upButton.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum
        )
        self.__upButton.setAutoRepeat(True)

        self.__scroller = QScrollArea(self)
        self.__scroller.setWidget(self.__buttonsWidget)
        self.__scroller.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.__scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.__scroller.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.__scroller.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.__scroller.setWidgetResizable(False)

        self.__downButton = QToolButton(self)
        self.__downButton.setArrowType(Qt.ArrowType.DownArrow)
        self.__downButton.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum
        )
        self.__downButton.setAutoRepeat(True)

        self.__outerLayout.addWidget(self.__upButton)
        self.__outerLayout.addWidget(self.__scroller)
        self.__outerLayout.addWidget(self.__downButton)

        self.__upButton.clicked.connect(self.__slideUp)
        self.__downButton.clicked.connect(self.__slideDown)

        self.setMaximumWidth(self.__buttons["bold"].sizeHint().width() + 2 * margin)

        self.__updateButtonStates()

    #######################################################################
    ## Methods below implement some event handlers
    #######################################################################

    def show(self):
        """
        Public slot to show the widget.
        """
        super().show()
        self.__enableScrollerButtons()

    def resizeEvent(self, evt):
        """
        Protected method to handle resize events.

        @param evt reference to the resize event
        @type QResizeEvent
        """
        self.__enableScrollerButtons()
        super().resizeEvent(evt)

    #######################################################################
    ## Methods below implement scroller related functions
    #######################################################################

    def __enableScrollerButtons(self):
        """
        Private method to set the enabled state of the scroll buttons.
        """
        scrollBar = self.__scroller.verticalScrollBar()
        self.__upButton.setEnabled(scrollBar.value() > 0)
        self.__downButton.setEnabled(scrollBar.value() < scrollBar.maximum())

    def __slideUp(self):
        """
        Private slot to move the widget upwards, i.e. show contents to the
        bottom.
        """
        self.__slide(True)

    def __slideDown(self):
        """
        Private slot to move the widget downwards, i.e. show contents to
        the top.
        """
        self.__slide(False)

    def __slide(self, up):
        """
        Private method to move the sliding widget.

        @param up flag indicating to move upwards
        @type bool
        """
        scrollBar = self.__scroller.verticalScrollBar()
        stepSize = scrollBar.singleStep()
        if up:
            stepSize = -stepSize
        newValue = scrollBar.value() + stepSize
        if newValue < 0:
            newValue = 0
        elif newValue > scrollBar.maximum():
            newValue = scrollBar.maximum()
        scrollBar.setValue(newValue)
        self.__enableScrollerButtons()

    #######################################################################
    ## Methods below implement the format button functions
    #######################################################################

    def __createButtons(self):
        """
        Private slot to create the various tool buttons.
        """
        self.__buttons = {}
        self.__separators = []
        self.__headerMenu = QMenu()

        self.__addButton("bold", "formatTextBold", self.tr("Bold"))
        self.__addButton("italic", "formatTextItalic", self.tr("Italic"))
        self.__addButton(
            "strikethrough", "formatTextStrikethrough", self.tr("Strike Through")
        )
        self.__addButton("underline", "formatTextUnderline", self.tr("Underline"))
        self.__addSeparator()
        self.__addButton("header1", "formatTextHeader1", self.tr("Header 1"))
        self.__addButton("header2", "formatTextHeader2", self.tr("Header 2"))
        self.__addButton("header3", "formatTextHeader3", self.tr("Header 3"))
        button = self.__addButton("header", "formatTextHeader", self.tr("Header"))
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(self.__headerMenu)
        self.__addSeparator()
        self.__addButton("code", "formatTextInlineCode", self.tr("Inline Code"))
        self.__addButton("codeBlock", "formatTextCodeBlock", self.tr("Code Block"))
        self.__addButton("quote", "formatTextQuote", self.tr("Quote"))
        self.__addSeparator()
        self.__addButton("hyperlink", "formatTextHyperlink", self.tr("Add Hyperlink"))
        self.__addButton(
            "line", "formatTextHorizontalLine", self.tr("Add Horizontal Line")
        )
        self.__addButton("image", "formatTextImage", self.tr("Add Image"))
        self.__addSeparator()
        self.__addButton(
            "bulletedList", "formatTextBulletedList", self.tr("Add Bulleted List")
        )
        self.__addButton(
            "numberedList", "formatTextNumberedList", self.tr("Add Numbered List")
        )

        self.__headerMenu.triggered.connect(self.__headerMenuTriggered)

    def __addButton(self, formatName, iconName, toolTip):
        """
        Private method to add a format button.

        @param formatName unique name of the format
        @type str
        @param iconName name of the icon for the button
        @type str
        @param toolTip text for the tool tip
        @type str
        @return generated button
        @rtype QToolButton
        """
        button = QToolButton(self.__buttonsWidget)
        button.setIcon(EricPixmapCache.getIcon(iconName))
        button.setToolTip(toolTip)
        button.clicked.connect(lambda: self.__formatClicked(formatName))
        self.__layout.addWidget(button)
        self.__buttons[formatName] = button

        return button

    def __addSeparator(self):
        """
        Private method to add a separator line.
        """
        line = QFrame(self.__buttonsWidget)
        line.setLineWidth(2)
        if isinstance(self.__layout, QVBoxLayout):
            line.setFrameShape(QFrame.Shape.HLine)
        else:
            line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)

        self.__layout.addWidget(line)
        self.__separators.append(line)

    @pyqtSlot()
    def __updateButtonStates(self):
        """
        Private slot to change the button states.
        """
        provider = MarkupProviders.getMarkupProvider(self.__editor)
        if self.__provider is None or provider.kind() != self.__provider.kind():
            self.__provider = provider

            self.__buttons["bold"].setEnabled(self.__provider.hasBold())
            self.__buttons["italic"].setEnabled(self.__provider.hasItalic())
            self.__buttons["strikethrough"].setEnabled(
                self.__provider.hasStrikethrough()
            )
            self.__buttons["underline"].setEnabled(self.__provider.hasUnderline())

            headerLevels = self.__provider.headerLevels()
            self.__buttons["header1"].setEnabled(headerLevels >= 1)
            self.__buttons["header2"].setEnabled(headerLevels >= 2)
            self.__buttons["header3"].setEnabled(headerLevels >= 3)
            self.__buttons["header"].setEnabled(headerLevels > 3)
            self.__headerMenu.clear()
            for level in range(1, headerLevels + 1):
                act = self.__headerMenu.addAction(self.tr("Level {0}").format(level))
                act.setData("header{0}".format(level))

            self.__buttons["code"].setEnabled(self.__provider.hasCode())
            self.__buttons["codeBlock"].setEnabled(self.__provider.hasCodeBlock())

            self.__buttons["bulletedList"].setEnabled(self.__provider.hasBulletedList())
            self.__buttons["numberedList"].setEnabled(self.__provider.hasNumberedList())

            self.__editorSelectionChanged()

            if Preferences.getEditor("HideFormatButtons"):
                self.setVisible(self.__provider.kind() != "none")

    def __formatClicked(self, formatName):
        """
        Private slot to handle a format button being clicked.

        @param formatName format type of the button
        @type str
        """
        if formatName == "bold":
            self.__provider.bold(self.__editor)
        elif formatName == "italic":
            self.__provider.italic(self.__editor)
        elif formatName == "strikethrough":
            self.__provider.strikethrough(self.__editor)
        elif formatName == "underline":
            self.__provider.underline(self.__editor)
        elif formatName.startswith("header"):
            with contextlib.suppress(ValueError):
                level = int(formatName[-1])
                self.__provider.header(self.__editor, level)
        elif formatName == "code":
            self.__provider.code(self.__editor)
        elif formatName == "codeBlock":
            self.__provider.codeBlock(self.__editor)
        elif formatName == "quote":
            self.__provider.quote(self.__editor)
        elif formatName == "hyperlink":
            self.__provider.hyperlink(self.__editor)
        elif formatName == "line":
            self.__provider.line(self.__editor)
        elif formatName == "image":
            self.__provider.image(self.__editor)
        elif formatName == "bulletedList":
            self.__provider.bulletedList(self.__editor)
        elif formatName == "numberedList":
            self.__provider.numberedList(self.__editor)

    def __headerMenuTriggered(self, act):
        """
        Private method handling the selection of a header menu entry.

        @param act action of the headers menu that was triggered
        @type QAction
        """
        formatName = act.data()
        self.__formatClicked(formatName)

    def __editorSelectionChanged(self):
        """
        Private slot to handle a change of the editor's selection.
        """
        hasSelection = self.__editor.hasSelectedText()
        if self.__provider:
            self.__buttons["quote"].setEnabled(
                self.__provider.hasQuote()
                and (self.__provider.kind() == "html" or hasSelection)
            )
            self.__buttons["hyperlink"].setEnabled(
                self.__provider.hasHyperlink() and not hasSelection
            )
            self.__buttons["line"].setEnabled(
                self.__provider.hasLine() and not hasSelection
            )
            self.__buttons["image"].setEnabled(
                self.__provider.hasImage() and not hasSelection
            )

    def __editorSettingsRead(self):
        """
        Private slot to handle a change of the editor related settings.
        """
        if Preferences.getEditor("HideFormatButtons"):
            if self.__provider is not None:
                self.setVisible(self.__provider.kind() != "none")
        else:
            self.setVisible(True)
