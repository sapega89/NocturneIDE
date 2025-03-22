# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Highlighting Styles configuration page.
"""

import enum
import pathlib

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFontDialog,
    QInputDialog,
    QMenu,
    QTreeWidgetItem,
)

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.Preferences.HighlightingStylesFile import HighlightingStylesFile
from eric7.QScintilla import Lexers

from ..SubstyleDefinitionDialog import SubstyleDefinitionDialog
from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorHighlightingStylesPage import Ui_EditorHighlightingStylesPage


class FontChangeMode(enum.Enum):
    """
    Class defining the modes for font changes.
    """

    FAMILYONLY = 0
    SIZEONLY = 1
    FAMILYANDSIZE = 2
    FONT = 99


class EditorHighlightingStylesPage(
    ConfigurationPageBase, Ui_EditorHighlightingStylesPage
):
    """
    Class implementing the Editor Highlighting Styles configuration page.
    """

    StyleRole = Qt.ItemDataRole.UserRole + 1
    SubstyleRole = Qt.ItemDataRole.UserRole + 2

    def __init__(self, lexers):
        """
        Constructor

        @param lexers reference to the lexers dictionary
        @type dict
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorHighlightingStylesPage")

        self.defaultSubstylesButton.setIcon(EricPixmapCache.getIcon("editUndo"))
        self.addSubstyleButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.deleteSubstyleButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.editSubstyleButton.setIcon(EricPixmapCache.getIcon("edit"))
        self.copySubstyleButton.setIcon(EricPixmapCache.getIcon("editCopy"))

        self.__fontButtonMenu = QMenu()
        act = self.__fontButtonMenu.addAction(self.tr("Font"))
        act.setData(FontChangeMode.FONT)
        self.__fontButtonMenu.addSeparator()
        act = self.__fontButtonMenu.addAction(self.tr("Family and Size only"))
        act.setData(FontChangeMode.FAMILYANDSIZE)
        act = self.__fontButtonMenu.addAction(self.tr("Family only"))
        act.setData(FontChangeMode.FAMILYONLY)
        act = self.__fontButtonMenu.addAction(self.tr("Size only"))
        act.setData(FontChangeMode.SIZEONLY)
        self.__fontButtonMenu.triggered.connect(self.__fontButtonMenuTriggered)
        self.fontButton.setMenu(self.__fontButtonMenu)

        self.__allFontsButtonMenu = QMenu()
        act = self.__allFontsButtonMenu.addAction(self.tr("Font"))
        act.setData(FontChangeMode.FONT)
        self.__allFontsButtonMenu.addSeparator()
        act = self.__allFontsButtonMenu.addAction(self.tr("Family and Size only"))
        act.setData(FontChangeMode.FAMILYANDSIZE)
        act = self.__allFontsButtonMenu.addAction(self.tr("Family only"))
        act.setData(FontChangeMode.FAMILYONLY)
        act = self.__allFontsButtonMenu.addAction(self.tr("Size only"))
        act.setData(FontChangeMode.SIZEONLY)
        self.__allFontsButtonMenu.triggered.connect(self.__allFontsButtonMenuTriggered)
        self.allFontsButton.setMenu(self.__allFontsButtonMenu)

        self.lexer = None
        self.lexers = lexers

        # set initial values
        languages = sorted([""] + list(self.lexers))
        self.__populateLanguages(languages)

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        from ..ConfigurationDialog import ConfigurationMode

        if displayMode in (ConfigurationMode.SHELLMODE,):
            self.__populateLanguages(["Python3"])

    def save(self):
        """
        Public slot to save the Editor Highlighting Styles configuration.
        """
        for lexer in self.lexers.values():
            lexer.writeSettings()

    def __populateLanguages(self, languages):
        """
        Private method to populate the language selection box.

        @param languages list of languages to include in the language selector
        @type list of str
        """
        self.lexerLanguageComboBox.clear()
        for language in languages:
            self.lexerLanguageComboBox.addItem(
                Lexers.getLanguageIcon(language, False), language
            )
        self.on_lexerLanguageComboBox_activated(0)

    @pyqtSlot(int)
    def on_lexerLanguageComboBox_activated(self, index):
        """
        Private slot to fill the style combo of the source page.

        @param index index of the selected entry
        @type int
        """
        language = self.lexerLanguageComboBox.itemText(index)

        self.styleElementList.clear()
        self.styleGroup.setEnabled(False)
        self.lexer = None

        if not language:
            return

        try:
            self.lexer = self.lexers[language]
        except KeyError:
            return

        self.styleGroup.setEnabled(True)
        for description, styleNo, subStyleNo in self.lexer.getStyles():
            if subStyleNo >= 0:
                parent = self.styleElementList.findItems(
                    self.lexer.description(styleNo), Qt.MatchFlag.MatchExactly
                )[0]
                parent.setExpanded(True)
            else:
                parent = self.styleElementList
            itm = QTreeWidgetItem(parent, [description])
            itm.setData(0, self.StyleRole, styleNo)
            itm.setData(0, self.SubstyleRole, subStyleNo)
        self.__styleAllItems()
        self.styleElementList.setCurrentItem(self.styleElementList.topLevelItem(0))

    def __stylesForItem(self, itm):
        """
        Private method to get the style and sub-style number of the given item.

        @param itm reference to the item to extract the styles from
        @type QTreeWidgetItem
        @return tuple containing the style and sub-style numbers
        @rtype tuple of (int, int)
        """
        style = itm.data(0, self.StyleRole)
        substyle = itm.data(0, self.SubstyleRole)

        return (style, substyle)

    def __currentStyles(self):
        """
        Private method to get the styles of the current item.

        @return tuple containing the style and sub-style numbers
        @rtype tuple of (int, int)
        """
        itm = self.styleElementList.currentItem()
        # return default style, if no current item
        styles = (0, -1) if itm is None else self.__stylesForItem(itm)

        return styles

    def __styleOneItem(self, item, style, substyle):
        """
        Private method to style one item of the style element list.

        @param item reference to the item to be styled
        @type QTreeWidgetItem
        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        """
        colour = self.lexer.color(style, substyle)
        paper = self.lexer.paper(style, substyle)
        font = self.lexer.font(style, substyle)
        eolfill = self.lexer.eolFill(style, substyle)

        item.setFont(0, font)
        item.setBackground(0, paper)
        item.setForeground(0, colour)
        if eolfill:
            item.setCheckState(0, Qt.CheckState.Checked)
        else:
            item.setCheckState(0, Qt.CheckState.Unchecked)

    def __styleAllItems(self):
        """
        Private method to style all items of the style element list.
        """
        itm = self.styleElementList.topLevelItem(0)
        while itm is not None:
            style, substyle = self.__stylesForItem(itm)
            self.__styleOneItem(itm, style, substyle)
            itm = self.styleElementList.itemBelow(itm)

    def __styleSample(self, color, paper, font=None):
        """
        Private method to style the sample text.

        @param color foreground color for the sample
        @type QColor
        @param paper background color for the sample
        @type QColor
        @param font font for the sample (defaults to None)
        @type QFont (optional)
        """
        if font:
            self.sampleText.setFont(font)

        self.sampleText.setStyleSheet(
            "QLineEdit {{ color: {0}; background-color: {1}; }}".format(
                color.name(), paper.name()
            )
        )

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_styleElementList_currentItemChanged(self, current, _previous):
        """
        Private method to handle a change of the current row.

        @param current reference to the current item
        @type QTreeWidgetItem
        @param _previous reference to the previous item (unused)
        @type QTreeWidgetItem
        """
        if current is None:
            return

        style, substyle = self.__stylesForItem(current)
        colour = self.lexer.color(style, substyle)
        paper = self.lexer.paper(style, substyle)
        eolfill = self.lexer.eolFill(style, substyle)
        font = self.lexer.font(style, substyle)

        self.__styleSample(colour, paper, font=font)
        self.eolfillCheckBox.setChecked(eolfill)

        selectedOne = len(self.styleElementList.selectedItems()) == 1
        self.defaultSubstylesButton.setEnabled(
            selectedOne and substyle < 0 and self.lexer.isBaseStyle(style)
        )
        self.addSubstyleButton.setEnabled(
            selectedOne and substyle < 0 and self.lexer.isBaseStyle(style)
        )
        self.deleteSubstyleButton.setEnabled(selectedOne and substyle >= 0)
        self.editSubstyleButton.setEnabled(selectedOne and substyle >= 0)
        self.copySubstyleButton.setEnabled(selectedOne and substyle >= 0)

    @pyqtSlot()
    def on_foregroundButton_clicked(self):
        """
        Private method used to select the foreground colour of the selected
        style and lexer.
        """
        style, substyle = self.__currentStyles()
        colour = QColorDialog.getColor(self.lexer.color(style, substyle))
        if colour.isValid():
            paper = self.lexer.paper(style, substyle)
            self.__styleSample(colour, paper)
            for selItem in self.styleElementList.selectedItems():
                style, substyle = self.__stylesForItem(selItem)
                self.lexer.setColor(colour, style, substyle)
                selItem.setForeground(0, colour)

    @pyqtSlot()
    def on_backgroundButton_clicked(self):
        """
        Private method used to select the background colour of the selected
        style and lexer.
        """
        style, substyle = self.__currentStyles()
        paper = QColorDialog.getColor(self.lexer.paper(style, substyle))
        if paper.isValid():
            colour = self.lexer.color(style, substyle)
            self.__styleSample(colour, paper)
            for selItem in self.styleElementList.selectedItems():
                style, substyle = self.__stylesForItem(selItem)
                self.lexer.setPaper(paper, style, substyle)
                selItem.setBackground(0, paper)

    @pyqtSlot()
    def on_allBackgroundColoursButton_clicked(self):
        """
        Private method used to select the background colour of all styles of a
        selected lexer.
        """
        style, substyle = self.__currentStyles()
        paper = QColorDialog.getColor(self.lexer.paper(style, substyle))
        if paper.isValid():
            colour = self.lexer.color(style, substyle)
            self.__styleSample(colour, paper)

            itm = self.styleElementList.topLevelItem(0)
            while itm is not None:
                style, substyle = self.__stylesForItem(itm)
                self.lexer.setPaper(paper, style, substyle)
                itm = self.styleElementList.itemBelow(itm)
            self.__styleAllItems()

    def __changeFont(self, doAll, familyOnly, sizeOnly):
        """
        Private slot to change the highlighter font.

        @param doAll flag indicating to change the font for all styles
        @type bool
        @param familyOnly flag indicating to set the font family only
        @type bool
        @param sizeOnly flag indicating to set the font size only
        @type bool
        """

        def setFont(font, style, substyle, familyOnly, sizeOnly):
            """
            Local function to set the font.

            @param font font to be set
            @type QFont
            @param style style number
            @type int
            @param substyle sub-style number
            @type int
            @param familyOnly flag indicating to set the font family only
            @type bool
            @param sizeOnly flag indicating to set the font size only
            @type bool
            """
            if familyOnly or sizeOnly:
                newFont = QFont(self.lexer.font(style))
                if familyOnly:
                    newFont.setFamily(font.family())
                if sizeOnly:
                    newFont.setPointSize(font.pointSize())
                self.lexer.setFont(newFont, style, substyle)
            else:
                self.lexer.setFont(font, style, substyle)

        def setSampleFont(font, familyOnly, sizeOnly):
            """
            Local function to set the font of the sample text.

            @param font font to be set (QFont)
            @param familyOnly flag indicating to set the font family only
                (boolean)
            @param sizeOnly flag indicating to set the font size only (boolean
            """
            if familyOnly or sizeOnly:
                style, substyle = self.__currentStyles()
                newFont = QFont(self.lexer.font(style, substyle))
                if familyOnly:
                    newFont.setFamily(font.family())
                if sizeOnly:
                    newFont.setPointSize(font.pointSize())
                self.sampleText.setFont(newFont)
            else:
                self.sampleText.setFont(font)

        style, substyle = self.__currentStyles()
        options = (
            QFontDialog.FontDialogOption.MonospacedFonts
            if self.monospacedButton.isChecked()
            else QFontDialog.FontDialogOption(0)
        )
        font, ok = QFontDialog.getFont(
            self.lexer.font(style, substyle), self, "", options
        )
        if ok:
            setSampleFont(font, familyOnly, sizeOnly)
            if doAll:
                itm = self.styleElementList.topLevelItem(0)
                while itm is not None:
                    style, substyle = self.__stylesForItem(itm)
                    setFont(font, style, substyle, familyOnly, sizeOnly)
                    itm = self.styleElementList.itemBelow(itm)
                self.__styleAllItems()
            else:
                for selItem in self.styleElementList.selectedItems():
                    style, substyle = self.__stylesForItem(selItem)
                    setFont(font, style, substyle, familyOnly, sizeOnly)
                    itmFont = self.lexer.font(style, substyle)
                    selItem.setFont(0, itmFont)

    def __fontButtonMenuTriggered(self, act):
        """
        Private slot used to select the font of the selected style and lexer.

        @param act reference to the triggering action
        @type QAction
        """
        if act is None:
            return

        familyOnly = act.data() in (
            FontChangeMode.FAMILYANDSIZE,
            FontChangeMode.FAMILYONLY,
        )
        sizeOnly = act.data() in (FontChangeMode.FAMILYANDSIZE, FontChangeMode.SIZEONLY)
        self.__changeFont(False, familyOnly, sizeOnly)

    def __allFontsButtonMenuTriggered(self, act):
        """
        Private slot used to change the font of all styles of a selected lexer.

        @param act reference to the triggering action
        @type QAction
        """
        if act is None:
            return

        familyOnly = act.data() in (
            FontChangeMode.FAMILYANDSIZE,
            FontChangeMode.FAMILYONLY,
        )
        sizeOnly = act.data() in (FontChangeMode.FAMILYANDSIZE, FontChangeMode.SIZEONLY)
        self.__changeFont(True, familyOnly, sizeOnly)

    @pyqtSlot(bool)
    def on_eolfillCheckBox_clicked(self, on):
        """
        Private method used to set the eolfill for the selected style and
        lexer.

        @param on flag indicating enabled or disabled state
        @type bool
        """
        style, substyle = self.__currentStyles()
        checkState = Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
        for selItem in self.styleElementList.selectedItems():
            style, substyle = self.__stylesForItem(selItem)
            self.lexer.setEolFill(on, style, substyle)
            selItem.setCheckState(0, checkState)

    @pyqtSlot()
    def on_allEolFillButton_clicked(self):
        """
        Private method used to set the eolfill for all styles of a selected
        lexer.
        """
        on = self.tr("Enabled")
        off = self.tr("Disabled")
        selection, ok = QInputDialog.getItem(
            self,
            self.tr("Fill to end of line"),
            self.tr("Select fill to end of line for all styles"),
            [on, off],
            0,
            False,
        )
        if ok:
            enabled = selection == on
            self.eolfillCheckBox.setChecked(enabled)

            itm = self.styleElementList.topLevelItem(0)
            while itm is not None:
                style, substyle = self.__stylesForItem(itm)
                self.lexer.setEolFill(enabled, style, substyle)
                itm = self.styleElementList.itemBelow(itm)
            self.__styleAllItems()

    @pyqtSlot()
    def on_defaultButton_clicked(self):
        """
        Private method to set the current style to its default values.
        """
        for selItem in self.styleElementList.selectedItems():
            style, substyle = self.__stylesForItem(selItem)
            self.__setToDefault(style, substyle)
        self.on_styleElementList_currentItemChanged(
            self.styleElementList.currentItem(), None
        )
        self.__styleAllItems()

    @pyqtSlot()
    def on_allDefaultButton_clicked(self):
        """
        Private method to set all styles to their default values.
        """
        itm = self.styleElementList.topLevelItem(0)
        while itm is not None:
            style, substyle = self.__stylesForItem(itm)
            self.__setToDefault(style, substyle)
            itm = self.styleElementList.itemBelow(itm)
        self.on_styleElementList_currentItemChanged(
            self.styleElementList.currentItem(), None
        )
        self.__styleAllItems()

    def __setToDefault(self, style, substyle):
        """
        Private method to set a specific style to its default values.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        """
        self.lexer.setColor(self.lexer.defaultColor(style, substyle), style, substyle)
        self.lexer.setPaper(self.lexer.defaultPaper(style, substyle), style, substyle)
        self.lexer.setFont(self.lexer.defaultFont(style, substyle), style, substyle)
        self.lexer.setEolFill(
            self.lexer.defaultEolFill(style, substyle), style, substyle
        )

    #######################################################################
    ## Importing and exporting of styles
    #######################################################################

    @pyqtSlot()
    def on_importButton_clicked(self):
        """
        Private slot to import styles to be selected.
        """
        self.__importStyles(importAll=False)

    @pyqtSlot()
    def on_exportButton_clicked(self):
        """
        Private slot to export styles to be selected.
        """
        self.__exportStyles(exportAll=False)

    @pyqtSlot()
    def on_importAllButton_clicked(self):
        """
        Private slot to import the styles of all lexers.
        """
        self.__importStyles(importAll=True)

    @pyqtSlot()
    def on_exportAllButton_clicked(self):
        """
        Private slot to export the styles of all lexers.
        """
        self.__exportStyles(exportAll=True)

    def __exportStyles(self, exportAll=False):
        """
        Private method to export the styles of selectable lexers.

        @param exportAll flag indicating to export all styles without asking
            (defaults to False)
        @type bool (optional)
        """
        from eric7.Globals import getConfig

        from .EditorHighlightingStylesSelectionDialog import (
            EditorHighlightingStylesSelectionDialog,
        )

        stylesDir = getConfig("ericStylesDir")

        lexerNames = list(self.lexers)
        if not exportAll:
            if self.lexer:
                preselect = [self.lexer.language()]
            else:
                preselect = []
            dlg = EditorHighlightingStylesSelectionDialog(
                lexerNames, forImport=False, preselect=preselect, parent=self
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                lexerNames = dlg.getLexerNames()
            else:
                # Cancelled by user
                return

        lexers = [self.lexers[name] for name in lexerNames]

        fn, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Export Highlighting Styles"),
            stylesDir,
            self.tr("Highlighting Styles File (*.ehj)"),
            "",
            EricFileDialog.DontConfirmOverwrite,
        )

        if not fn:
            return

        fpath = pathlib.Path(fn)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)

        ok = (
            EricMessageBox.yesNo(
                self,
                self.tr("Export Highlighting Styles"),
                self.tr(
                    """<p>The highlighting styles file <b>{0}</b> exists"""
                    """ already. Overwrite it?</p>"""
                ).format(fpath),
            )
            if fpath.exists()
            else True
        )

        if ok:
            highlightingStylesFile = HighlightingStylesFile()
            highlightingStylesFile.writeFile(str(fpath), lexers)

    def __importStyles(self, importAll=False):
        """
        Private method to import the styles of lexers to be selected.

        @param importAll flag indicating to import all styles without asking
            (defaults to False)
        @type bool (optional)
        """
        from eric7.Globals import getConfig

        stylesDir = getConfig("ericStylesDir")

        fn = EricFileDialog.getOpenFileName(
            self,
            self.tr("Import Highlighting Styles"),
            stylesDir,
            self.tr("Highlighting Styles File (*.ehj)"),
        )

        if not fn:
            return

        highlightingStylesFile = HighlightingStylesFile()
        styles = highlightingStylesFile.readFile(fn)
        if not styles:
            return

        self.__applyStyles(styles, importAll=importAll)
        self.on_lexerLanguageComboBox_activated(
            self.lexerLanguageComboBox.currentIndex()
        )

    def __applyStyles(self, stylesList, importAll=False):
        """
        Private method to apply the imported styles to this dialog.

        @param stylesList list of imported lexer styles
        @type list of dict
        @param importAll flag indicating to import all styles without asking
            (defaults to False)
        @type bool (optional)
        """
        from .EditorHighlightingStylesSelectionDialog import (
            EditorHighlightingStylesSelectionDialog,
        )

        lexerNames = [d["name"] for d in stylesList if d["name"] in self.lexers]

        if not importAll:
            dlg = EditorHighlightingStylesSelectionDialog(
                lexerNames, forImport=True, parent=self
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                lexerNames = dlg.getLexerNames()
            else:
                # Cancelled by user
                return

        for lexerDict in stylesList:
            if lexerDict["name"] in lexerNames:
                lexer = self.lexers[lexerDict["name"]]
                for styleDict in lexerDict["styles"]:
                    style = styleDict["style"]
                    substyle = styleDict["substyle"]
                    lexer.setColor(QColor(styleDict["color"]), style, substyle)
                    lexer.setPaper(QColor(styleDict["paper"]), style, substyle)
                    font = QFont()
                    font.fromString(styleDict["font"])
                    lexer.setFont(font, style, substyle)
                    lexer.setEolFill(styleDict["eolfill"], style, substyle)
                    if substyle >= 0:
                        # description and words can only be set for sub-styles
                        lexer.setDescription(styleDict["description"], style, substyle)
                        lexer.setWords(styleDict["words"], style, substyle)

    #######################################################################
    ## Methods to save and restore the state
    #######################################################################

    def saveState(self):
        """
        Public method to save the current state of the widget.

        @return list containing the index of the selected lexer language
            and a tuple containing the index of the parent selected lexer
            entry and the index of the selected entry
        @rtype list of [int, tuple of (int, int)]
        """
        itm = self.styleElementList.currentItem()
        if itm:
            parent = itm.parent()
            if parent is None:
                currentData = (None, self.styleElementList.indexOfTopLevelItem(itm))
            else:
                currentData = (
                    self.styleElementList.indexOfTopLevelItem(parent),
                    parent.indexOfChild(itm),
                )

            savedState = [
                self.lexerLanguageComboBox.currentIndex(),
                currentData,
            ]
        else:
            savedState = []
        return savedState

    def setState(self, state):
        """
        Public method to set the state of the widget.

        @param state state data generated by saveState
        @type list of [int, tuple of (int, int)]
        """
        if state:
            self.lexerLanguageComboBox.setCurrentIndex(state[0])
            self.on_lexerLanguageComboBox_activated(
                self.lexerLanguageComboBox.currentIndex()
            )

            parentIndex, index = state[1]
            if parentIndex is None:
                itm = self.styleElementList.topLevelItem(index)
            else:
                parent = self.styleElementList.topLevelItem(parentIndex)
                itm = parent.child(index)
            self.styleElementList.setCurrentItem(itm)

    #######################################################################
    ## Methods to add, delete and edit sub-styles and their definitions
    #######################################################################

    @pyqtSlot()
    def on_addSubstyleButton_clicked(self):
        """
        Private slot to add a new sub-style.
        """
        style, substyle = self.__currentStyles()
        dlg = SubstyleDefinitionDialog(self.lexer, style, substyle, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            description, words = dlg.getData()
            substyle = self.lexer.addSubstyle(style)
            self.lexer.setDescription(description, style, substyle)
            self.lexer.setWords(words, style, substyle)

            parent = self.styleElementList.findItems(
                self.lexer.description(style), Qt.MatchFlag.MatchExactly
            )[0]
            parent.setExpanded(True)
            itm = QTreeWidgetItem(parent, [description])
            itm.setData(0, self.StyleRole, style)
            itm.setData(0, self.SubstyleRole, substyle)
            self.__styleOneItem(itm, style, substyle)

    @pyqtSlot()
    def on_deleteSubstyleButton_clicked(self):
        """
        Private slot to delete the selected sub-style.
        """
        style, substyle = self.__currentStyles()
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Delete Sub-Style"),
            self.tr(
                """<p>Shall the sub-style <b>{0}</b> really be deleted?</p>"""
            ).format(self.lexer.description(style, substyle)),
        )
        if ok:
            self.lexer.delSubstyle(style, substyle)

            itm = self.styleElementList.currentItem()
            parent = itm.parent()
            index = parent.indexOfChild(itm)
            parent.takeChild(index)
            del itm

    @pyqtSlot()
    def on_editSubstyleButton_clicked(self):
        """
        Private slot to edit the selected sub-style entry.
        """
        style, substyle = self.__currentStyles()
        dlg = SubstyleDefinitionDialog(self.lexer, style, substyle, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            description, words = dlg.getData()
            self.lexer.setDescription(description, style, substyle)
            self.lexer.setWords(words, style, substyle)

            itm = self.styleElementList.currentItem()
            itm.setText(0, description)

    @pyqtSlot()
    def on_copySubstyleButton_clicked(self):
        """
        Private slot to copy the selected sub-style.
        """
        style, substyle = self.__currentStyles()
        newSubstyle = self.lexer.addSubstyle(style)

        description = self.tr("{0} - Copy").format(
            self.lexer.description(style, substyle)
        )
        self.lexer.setDescription(description, style, newSubstyle)
        self.lexer.setWords(self.lexer.words(style, substyle), style, newSubstyle)
        self.lexer.setColor(self.lexer.color(style, substyle), style, newSubstyle)
        self.lexer.setPaper(self.lexer.paper(style, substyle), style, newSubstyle)
        self.lexer.setFont(self.lexer.font(style, substyle), style, newSubstyle)
        self.lexer.setEolFill(self.lexer.eolFill(style, substyle), style, newSubstyle)

        parent = self.styleElementList.findItems(
            self.lexer.description(style), Qt.MatchFlag.MatchExactly
        )[0]
        parent.setExpanded(True)
        itm = QTreeWidgetItem(parent, [description])
        itm.setData(0, self.StyleRole, style)
        itm.setData(0, self.SubstyleRole, newSubstyle)
        self.__styleOneItem(itm, style, newSubstyle)

    @pyqtSlot()
    def on_defaultSubstylesButton_clicked(self):
        """
        Private slot to reset all substyles to default values.
        """
        style, substyle = self.__currentStyles()
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Reset Sub-Styles to Default"),
            self.tr(
                "<p>Do you really want to reset all defined sub-styles of"
                " <b>{0}</b> to the default values?</p>"
                ""
            ).format(self.lexer.description(style, substyle)),
        )
        if ok:
            # 1. reset sub-styles
            self.lexer.loadDefaultSubStyles(style)

            # 2. delete all existing sub-style items
            parent = self.styleElementList.currentItem()
            while parent.childCount() > 0:
                itm = parent.takeChild(0)  # __IGNORE_WARNING__
                del itm

            # 3. create the new list of sub-style items
            for description, _, substyle in self.lexer.getSubStyles(style):
                itm = QTreeWidgetItem(parent, [description])
                itm.setData(0, self.StyleRole, style)
                itm.setData(0, self.SubstyleRole, substyle)
                self.__styleOneItem(itm, style, substyle)


def create(dlg):
    """
    Module function to create the configuration page.

    @param dlg reference to the configuration dialog
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorHighlightingStylesPage(dlg.getLexers())
    return page
