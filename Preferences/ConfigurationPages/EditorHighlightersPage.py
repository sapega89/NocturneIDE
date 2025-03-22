# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Highlighter Associations configuration page.
"""

import os

from pygments.lexers import get_all_lexers
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QHeaderView, QTreeWidgetItem

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.QScintilla import Lexers

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorHighlightersPage import Ui_EditorHighlightersPage


class EditorHighlightersPage(ConfigurationPageBase, Ui_EditorHighlightersPage):
    """
    Class implementing the Editor Highlighter Associations configuration page.
    """

    def __init__(self, lexers):
        """
        Constructor

        @param lexers reference to the lexers dictionary
        @type dict
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorHighlightersPage")

        self.editorLexerList.headerItem().setText(
            self.editorLexerList.columnCount(), ""
        )
        header = self.editorLexerList.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        try:
            self.extsep = os.extsep
        except AttributeError:
            self.extsep = "."

        self.extras = ["-----------", self.tr("Alternative")]
        self.editorLexerCombo.addItem("")
        self.editorLexerCombo.addItem(EricPixmapCache.getIcon("fileText"), "Text")
        for lang in sorted(lexers):
            self.editorLexerCombo.addItem(Lexers.getLanguageIcon(lang, False), lang)
        self.editorLexerCombo.addItems(self.extras)

        pygmentsLexers = [""] + sorted(lex[0] for lex in get_all_lexers())
        self.pygmentsLexerCombo.addItems(pygmentsLexers)

        # set initial values
        lexerAssocs = Preferences.getEditorLexerAssocs()
        for ext in lexerAssocs:
            QTreeWidgetItem(self.editorLexerList, [ext, lexerAssocs[ext]])
        self.editorLexerList.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    def save(self):
        """
        Public slot to save the Editor Highlighter Associations configuration.
        """
        lexerAssocs = {}
        for index in range(self.editorLexerList.topLevelItemCount()):
            itm = self.editorLexerList.topLevelItem(index)
            lexerAssocs[itm.text(0)] = itm.text(1)
        Preferences.setEditorLexerAssocs(lexerAssocs)

    @pyqtSlot()
    def on_addLexerButton_clicked(self):
        """
        Private slot to add the lexer association displayed to the list.
        """
        ext = self.editorFileExtEdit.text()
        if ext.startswith(self.extsep):
            ext.replace(self.extsep, "")
        lexer = self.editorLexerCombo.currentText()
        if lexer in self.extras:
            pygmentsLexer = self.pygmentsLexerCombo.currentText()
            if not pygmentsLexer:
                lexer = pygmentsLexer
            else:
                lexer = "Pygments|{0}".format(pygmentsLexer)
        if ext and lexer:
            itmList = self.editorLexerList.findItems(ext, Qt.MatchFlag.MatchExactly, 0)
            if itmList:
                index = self.editorLexerList.indexOfTopLevelItem(itmList[0])
                itm = self.editorLexerList.takeTopLevelItem(index)
                # __IGNORE_WARNING__
                del itm
            QTreeWidgetItem(self.editorLexerList, [ext, lexer])
            self.editorFileExtEdit.clear()
            self.editorLexerCombo.setCurrentIndex(0)
            self.pygmentsLexerCombo.setCurrentIndex(0)
            self.editorLexerList.sortItems(
                self.editorLexerList.sortColumn(),
                self.editorLexerList.header().sortIndicatorOrder(),
            )

    @pyqtSlot()
    def on_deleteLexerButton_clicked(self):
        """
        Private slot to delete the currently selected lexer association of the
        list.
        """
        itmList = self.editorLexerList.selectedItems()
        if itmList:
            index = self.editorLexerList.indexOfTopLevelItem(itmList[0])
            itm = self.editorLexerList.takeTopLevelItem(index)
            # __IGNORE_WARNING__
            del itm

            self.editorLexerList.clearSelection()
            self.editorFileExtEdit.clear()
            self.editorLexerCombo.setCurrentIndex(0)

    @pyqtSlot(QTreeWidgetItem, int)
    def on_editorLexerList_itemClicked(self, itm, column):
        """
        Private slot to handle the clicked signal of the lexer association
        list.

        @param itm reference to the selected item
        @type QTreeWidgetItem
        @param column column the item was clicked or activated (ignored)
        @type int
        """
        if itm is None:
            self.editorFileExtEdit.clear()
            self.editorLexerCombo.setCurrentIndex(0)
            self.pygmentsLexerCombo.setCurrentIndex(0)
        else:
            self.editorFileExtEdit.setText(itm.text(0))
            lexer = itm.text(1)
            if lexer.startswith("Pygments|"):
                pygmentsLexer = lexer.split("|")[1]
                pygmentsIndex = self.pygmentsLexerCombo.findText(pygmentsLexer)
                lexer = self.tr("Alternative")
            else:
                pygmentsIndex = 0
            index = self.editorLexerCombo.findText(lexer)
            self.editorLexerCombo.setCurrentIndex(index)
            self.pygmentsLexerCombo.setCurrentIndex(pygmentsIndex)

    def on_editorLexerList_itemActivated(self, itm, column):
        """
        Private slot to handle the activated signal of the lexer association
        list.

        @param itm reference to the selecte item
        @type QTreeWidgetItem
        @param column column the item was clicked or activated
        @type int
        """
        self.on_editorLexerList_itemClicked(itm, column)

    @pyqtSlot(int)
    def on_editorLexerCombo_currentIndexChanged(self, index):
        """
        Private slot to handle the selection of a lexer.

        @param index index of the current item
        @type int
        """
        text = self.editorLexerCombo.itemText(index)
        if text in self.extras:
            self.pygmentsLexerCombo.setEnabled(True)
            self.pygmentsLabel.setEnabled(True)
        else:
            self.pygmentsLexerCombo.setEnabled(False)
            self.pygmentsLabel.setEnabled(False)


def create(dlg):
    """
    Module function to create the configuration page.

    @param dlg reference to the configuration dialog
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorHighlightersPage(dlg.getLexers())
    return page
