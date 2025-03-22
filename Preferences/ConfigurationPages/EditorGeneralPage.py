# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor General configuration page.
"""

from PyQt6.Qsci import QsciScintillaBase
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QHeaderView, QTreeWidgetItem

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.QScintilla.DocstringGenerator import getSupportedDocstringTypes

from .ConfigurationPageBase import ConfigurationPageBase
from .EditorLanguageTabIndentOverrideDialog import EditorLanguageTabIndentOverrideDialog
from .Ui_EditorGeneralPage import Ui_EditorGeneralPage


class EditorGeneralPage(ConfigurationPageBase, Ui_EditorGeneralPage):
    """
    Class implementing the Editor General configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorGeneralPage")

        self.addButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.deleteButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.editButton.setIcon(EricPixmapCache.getIcon("edit"))

        for docstringType, docstringStyle in sorted(getSupportedDocstringTypes()):
            self.docstringStyleComboBox.addItem(docstringStyle, docstringType)

        # set initial values
        self.tabwidthSlider.setValue(Preferences.getEditor("TabWidth"))
        self.indentwidthSlider.setValue(Preferences.getEditor("IndentWidth"))
        self.tabforindentationCheckBox.setChecked(
            Preferences.getEditor("TabForIndentation")
        )
        self.tabindentsCheckBox.setChecked(Preferences.getEditor("TabIndents"))
        self.converttabsCheckBox.setChecked(Preferences.getEditor("ConvertTabsOnLoad"))
        self.autoindentCheckBox.setChecked(Preferences.getEditor("AutoIndentation"))
        self.comment0CheckBox.setChecked(Preferences.getEditor("CommentColumn0"))

        self.sourceNavigationGroupBox.setChecked(
            Preferences.getEditor("ShowSourceNavigator")
        )
        self.sourceOutlineGroupBox.setChecked(
            Preferences.getEditor("ShowSourceOutline")
        )
        self.sourceOutlineWidthSpinBox.setValue(
            Preferences.getEditor("SourceOutlineWidth")
        )
        self.sourceOutlineSortByOccurrenceCheckBox.setChecked(
            Preferences.getEditor("SourceOutlineListContentsByOccurrence")
        )
        self.sourceOutlineShowCodingCheckBox.setChecked(
            Preferences.getEditor("SourceOutlineShowCoding")
        )

        index = self.docstringStyleComboBox.findData(
            Preferences.getEditor("DocstringType")
        )
        self.docstringStyleComboBox.setCurrentIndex(index)
        self.docstringCompletionCheckBox.setChecked(
            Preferences.getEditor("DocstringAutoGenerate")
        )

        self.mouseHoverHelpGroupBox.setChecked(Preferences.getEditor("MouseHoverHelp"))
        self.mouseDwellTimeSpinBox.setValue(Preferences.getEditor("MouseHoverTimeout"))

        rectangularSelectionModifier = Preferences.getEditor(
            "RectangularSelectionModifier"
        )
        if rectangularSelectionModifier == Qt.KeyboardModifier.ControlModifier:
            self.rectangularSelectionCtrlButton.setChecked(True)
        elif rectangularSelectionModifier == Qt.KeyboardModifier.AltModifier:
            self.rectangularSelectionAltButton.setChecked(True)
        elif rectangularSelectionModifier == Qt.KeyboardModifier.MetaModifier:
            self.rectangularSelectionMetaButton.setChecked(True)
        else:
            self.rectangularSelectionCtrlButton.setChecked(True)  # default

        virtualSpaceOptions = Preferences.getEditor("VirtualSpaceOptions")
        self.vsSelectionCheckBox.setChecked(
            virtualSpaceOptions & QsciScintillaBase.SCVS_RECTANGULARSELECTION
        )
        self.vsUserCheckBox.setChecked(
            virtualSpaceOptions & QsciScintillaBase.SCVS_USERACCESSIBLE
        )

        self.__populateLanguageOverrideWidget()

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        from ..ConfigurationDialog import ConfigurationMode

        if displayMode in (ConfigurationMode.SHELLMODE,):
            self.sourceNavigationGroupBox.hide()
            self.commentsGroupBox.hide()
            self.docstringGroupBox.hide()
            self.mouseHoverHelpGroupBox.hide()
            self.virtualSpaceGroupBox.hide()

    def save(self):
        """
        Public slot to save the Editor General configuration.
        """
        Preferences.setEditor("TabWidth", self.tabwidthSlider.value())
        Preferences.setEditor("IndentWidth", self.indentwidthSlider.value())
        Preferences.setEditor(
            "TabForIndentation", self.tabforindentationCheckBox.isChecked()
        )
        Preferences.setEditor("TabIndents", self.tabindentsCheckBox.isChecked())
        Preferences.setEditor("ConvertTabsOnLoad", self.converttabsCheckBox.isChecked())
        Preferences.setEditor("AutoIndentation", self.autoindentCheckBox.isChecked())
        Preferences.setEditor("CommentColumn0", self.comment0CheckBox.isChecked())

        Preferences.setEditor(
            "ShowSourceNavigator", self.sourceNavigationGroupBox.isChecked()
        )
        Preferences.setEditor(
            "ShowSourceOutline", self.sourceOutlineGroupBox.isChecked()
        )
        Preferences.setEditor(
            "SourceOutlineWidth", self.sourceOutlineWidthSpinBox.value()
        )
        Preferences.setEditor(
            "SourceOutlineListContentsByOccurrence",
            self.sourceOutlineSortByOccurrenceCheckBox.isChecked(),
        )
        Preferences.setEditor(
            "SourceOutlineShowCoding", self.sourceOutlineShowCodingCheckBox.isChecked()
        )

        Preferences.setEditor(
            "DocstringType", self.docstringStyleComboBox.currentData()
        )
        Preferences.setEditor(
            "DocstringAutoGenerate", self.docstringCompletionCheckBox.isChecked()
        )

        Preferences.setEditor("MouseHoverHelp", self.mouseHoverHelpGroupBox.isChecked())
        Preferences.setEditor("MouseHoverTimeout", self.mouseDwellTimeSpinBox.value())

        rectangularSelectionModifier = Qt.KeyboardModifier.ControlModifier  # default
        if self.rectangularSelectionCtrlButton.isChecked():
            pass  # already set as default value
        elif self.rectangularSelectionAltButton.isChecked():
            rectangularSelectionModifier = Qt.KeyboardModifier.AltModifier
        elif self.rectangularSelectionMetaButton.isChecked():
            rectangularSelectionModifier = Qt.KeyboardModifier.MetaModifier
        Preferences.setEditor(
            "RectangularSelectionModifier", rectangularSelectionModifier
        )

        virtualSpaceOptions = QsciScintillaBase.SCVS_NONE
        if self.vsSelectionCheckBox.isChecked():
            virtualSpaceOptions |= QsciScintillaBase.SCVS_RECTANGULARSELECTION
        if self.vsUserCheckBox.isChecked():
            virtualSpaceOptions |= QsciScintillaBase.SCVS_USERACCESSIBLE
        Preferences.setEditor("VirtualSpaceOptions", virtualSpaceOptions)

        self.__saveLanguageOverrides()

    def on_tabforindentationCheckBox_toggled(self, checked):
        """
        Private slot used to set the tab conversion check box.

        @param checked flag received from the signal
        @type bool
        """
        if checked and self.converttabsCheckBox.isChecked():
            self.converttabsCheckBox.setChecked(not checked)
        self.converttabsCheckBox.setEnabled(not checked)

    def __populateLanguageOverrideWidget(self):
        """
        Private method to populate the language specific indentation and tab
        width override widget.
        """
        overrides = Preferences.getEditor("TabIndentOverride")
        for language, (tabWidth, indentWidth) in overrides.items():
            self.__createOverrideItem(language, tabWidth, indentWidth)
        self.languageOverrideWidget.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.__resizeOverrideColumns()
        self.on_languageOverrideWidget_itemSelectionChanged()

    def __createOverrideItem(self, language, tabWidth, indentWidth):
        """
        Private method to create an entry for a language override.

        @param language name of the language
        @type str
        @param tabWidth tabulator width
        @type int
        @param indentWidth indentation width
        @type int
        """
        itm = QTreeWidgetItem(
            self.languageOverrideWidget,
            [language, "{0:2d}".format(tabWidth), "{0:2d}".format(indentWidth)],
        )
        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignHCenter)

    def __resizeOverrideColumns(self):
        """
        Private method to resize the list columns.
        """
        self.languageOverrideWidget.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.languageOverrideWidget.header().setStretchLastSection(True)

    def __saveLanguageOverrides(self):
        """
        Private method to save the language specific indentation and tab width
        overrides.
        """
        overrides = {}
        for row in range(self.languageOverrideWidget.topLevelItemCount()):
            itm = self.languageOverrideWidget.topLevelItem(row)
            language = itm.text(0)
            overrides[language] = [
                int(itm.text(1)),
                int(itm.text(2)),
            ]

        Preferences.setEditor("TabIndentOverride", overrides)

    @pyqtSlot()
    def on_languageOverrideWidget_itemSelectionChanged(self):
        """
        Private slot handling a change of the override selection.
        """
        self.deleteButton.setEnabled(
            len(self.languageOverrideWidget.selectedItems()) > 0
        )
        self.editButton.setEnabled(
            len(self.languageOverrideWidget.selectedItems()) == 1
        )

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a new override entry.
        """
        languages = []
        for row in range(self.languageOverrideWidget.topLevelItemCount()):
            itm = self.languageOverrideWidget.topLevelItem(row)
            languages.append(itm.text(0))
        dlg = EditorLanguageTabIndentOverrideDialog(
            editMode=False,
            languages=languages,
            tabWidth=self.tabwidthSlider.value(),
            indentWidth=self.indentwidthSlider.value(),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            language, tabWidth, indentWidth = dlg.getData()
            self.__createOverrideItem(language, tabWidth, indentWidth)
            self.languageOverrideWidget.sortItems(0, Qt.SortOrder.AscendingOrder)
            self.__resizeOverrideColumns()

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the selected override entries.
        """
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Tab and Indent Override"),
            self.tr("""Shall the selected entries really be removed?"""),
        )
        if ok:
            for itm in self.languageOverrideWidget.selectedItems():
                index = self.languageOverrideWidget.indexOfTopLevelItem(itm)
                self.languageOverrideWidget.takeTopLevelItem(index)
                del itm

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to edit the selected override entry.
        """
        itm = self.languageOverrideWidget.selectedItems()[0]
        dlg = EditorLanguageTabIndentOverrideDialog(
            editMode=True,
            languages=[itm.text(0)],
            tabWidth=int(itm.text(1)),
            indentWidth=int(itm.text(2)),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            language, tabWidth, indentWidth = dlg.getData()
            itm.setText(1, "{0:2d}".format(tabWidth))
            itm.setText(2, "{0:2d}".format(indentWidth))


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorGeneralPage()
    return page
