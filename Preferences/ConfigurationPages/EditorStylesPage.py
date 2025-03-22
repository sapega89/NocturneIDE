# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Styles configuration page.
"""

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog, QFontDialog

from eric7 import Preferences
from eric7.QScintilla.QsciScintillaCompat import QsciScintillaCompat

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorStylesPage import Ui_EditorStylesPage


class EditorStylesPage(ConfigurationPageBase, Ui_EditorStylesPage):
    """
    Class implementing the Editor Styles configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorStylesPage")

        self.foldStyles = [
            QsciScintilla.FoldStyle.PlainFoldStyle.value,
            QsciScintilla.FoldStyle.CircledFoldStyle.value,
            QsciScintilla.FoldStyle.BoxedFoldStyle.value,
            QsciScintilla.FoldStyle.CircledTreeFoldStyle.value,
            QsciScintilla.FoldStyle.BoxedTreeFoldStyle.value,
            # the below ones are not (yet) defined in QsciScintilla
            QsciScintillaCompat.ArrowFoldStyle,
            QsciScintillaCompat.ArrowTreeFoldStyle,
        ]

        self.edgeModes = [
            QsciScintilla.EdgeMode.EdgeNone,
            QsciScintilla.EdgeMode.EdgeLine,
            QsciScintilla.EdgeMode.EdgeBackground,
        ]

        self.wrapModeComboBox.addItem(
            self.tr("Disabled"), QsciScintilla.WrapMode.WrapNone
        )
        self.wrapModeComboBox.addItem(
            self.tr("Word Boundary"), QsciScintilla.WrapMode.WrapWord
        )
        self.wrapModeComboBox.addItem(
            self.tr("Character Boundary"), QsciScintilla.WrapMode.WrapCharacter
        )
        self.wrapVisualComboBox.addItem(
            self.tr("No Indicator"), QsciScintilla.WrapVisualFlag.WrapFlagNone
        )
        self.wrapVisualComboBox.addItem(
            self.tr("Indicator by Text"), QsciScintilla.WrapVisualFlag.WrapFlagByText
        )
        self.wrapVisualComboBox.addItem(
            self.tr("Indicator by Margin"),
            QsciScintilla.WrapVisualFlag.WrapFlagByBorder,
        )
        self.wrapVisualComboBox.addItem(
            self.tr("Indicator in Line Number Margin"),
            QsciScintilla.WrapVisualFlag.WrapFlagInMargin,
        )

        self.wrapIndentComboBox.addItem(
            self.tr("Fixed"), QsciScintilla.WrapIndentMode.WrapIndentFixed
        )
        self.wrapIndentComboBox.addItem(
            self.tr("Aligned"), QsciScintilla.WrapIndentMode.WrapIndentSame
        )
        self.wrapIndentComboBox.addItem(
            self.tr("Aligned plus One"), QsciScintilla.WrapIndentMode.WrapIndentIndented
        )
        self.wrapIndentComboBox.addItem(
            self.tr("Aligned plus Two"),
            QsciScintilla.WrapIndentMode.WrapIndentDeeplyIndented,
        )

        # set initial values
        try:
            self.foldingStyleComboBox.setCurrentIndex(
                self.foldStyles.index(Preferences.getEditor("FoldingStyle"))
            )
        except ValueError:
            self.foldingStyleComboBox.setCurrentIndex(0)
        self.marginsFont = Preferences.getEditorOtherFonts("MarginsFont")
        self.marginsFontSample.setFont(self.marginsFont)
        self.defaultFont = Preferences.getEditorOtherFonts("DefaultFont")
        self.defaultFontSample.setFont(self.defaultFont)
        self.monospacedFont = Preferences.getEditorOtherFonts("MonospacedFont")
        self.monospacedFontSample.setFont(self.monospacedFont)
        self.monospacedCheckBox.setChecked(Preferences.getEditor("UseMonospacedFont"))
        self.linenoCheckBox.setChecked(Preferences.getEditor("LinenoMargin"))
        self.foldingCheckBox.setChecked(Preferences.getEditor("FoldingMargin"))

        self.caretlineVisibleCheckBox.setChecked(
            Preferences.getEditor("CaretLineVisible")
        )
        self.caretlineAlwaysVisibleCheckBox.setChecked(
            Preferences.getEditor("CaretLineAlwaysVisible")
        )
        self.caretWidthSpinBox.setValue(Preferences.getEditor("CaretWidth"))
        self.caretlineFrameWidthSpinBox.setValue(
            Preferences.getEditor("CaretLineFrameWidth")
        )
        self.colourizeSelTextCheckBox.setChecked(
            Preferences.getEditor("ColourizeSelText")
        )
        self.customSelColourCheckBox.setChecked(
            Preferences.getEditor("CustomSelectionColours")
        )
        self.extentSelEolCheckBox.setChecked(
            Preferences.getEditor("ExtendSelectionToEol")
        )
        self.debugMarkerBackgroundCheckBox.setChecked(
            Preferences.getEditor("LineMarkersBackground")
        )

        self.initColour(
            "CaretForeground", self.caretForegroundButton, Preferences.getEditorColour
        )
        self.initColour(
            "CaretLineBackground",
            self.caretlineBackgroundButton,
            Preferences.getEditorColour,
            hasAlpha=True,
        )
        self.initColour(
            "SelectionForeground",
            self.selectionForegroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "SelectionBackground",
            self.selectionBackgroundButton,
            Preferences.getEditorColour,
            hasAlpha=True,
        )
        self.initColour(
            "CurrentMarker",
            self.currentLineMarkerButton,
            Preferences.getEditorColour,
            hasAlpha=True,
        )
        self.initColour(
            "ErrorMarker",
            self.errorMarkerButton,
            Preferences.getEditorColour,
            hasAlpha=True,
        )
        self.initColour(
            "MarginsForeground",
            self.marginsForegroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "MarginsBackground",
            self.marginsBackgroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "FoldmarginBackground",
            self.foldmarginBackgroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "FoldMarkersForeground",
            self.foldmarkersForegroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "FoldMarkersBackground",
            self.foldmarkersBackgroundButton,
            Preferences.getEditorColour,
        )

        self.editorColours = {}
        self.editorColours["AnnotationsWarningForeground"] = QColor(
            Preferences.getEditorColour("AnnotationsWarningForeground")
        )
        self.editorColours["AnnotationsWarningBackground"] = QColor(
            Preferences.getEditorColour("AnnotationsWarningBackground")
        )
        self.editorColours["AnnotationsErrorForeground"] = QColor(
            Preferences.getEditorColour("AnnotationsErrorForeground")
        )
        self.editorColours["AnnotationsErrorBackground"] = QColor(
            Preferences.getEditorColour("AnnotationsErrorBackground")
        )
        self.editorColours["AnnotationsStyleForeground"] = QColor(
            Preferences.getEditorColour("AnnotationsStyleForeground")
        )
        self.editorColours["AnnotationsStyleBackground"] = QColor(
            Preferences.getEditorColour("AnnotationsStyleBackground")
        )
        self.editorColours["AnnotationsInfoForeground"] = QColor(
            Preferences.getEditorColour("AnnotationsInfoForeground")
        )
        self.editorColours["AnnotationsInfoBackground"] = QColor(
            Preferences.getEditorColour("AnnotationsInfoBackground")
        )

        self.eolCheckBox.setChecked(Preferences.getEditor("ShowEOL"))
        self.wrapModeComboBox.setCurrentIndex(
            self.wrapModeComboBox.findData(Preferences.getEditor("WrapLongLinesMode"))
        )
        self.wrapVisualComboBox.setCurrentIndex(
            self.wrapVisualComboBox.findData(Preferences.getEditor("WrapVisualFlag"))
        )
        self.wrapIndentComboBox.setCurrentIndex(
            self.wrapIndentComboBox.findData(Preferences.getEditor("WrapIndentMode"))
        )
        self.wrapStartIndentSpinBox.setValue(Preferences.getEditor("WrapStartIndent"))

        self.edgeModeCombo.setCurrentIndex(
            self.edgeModes.index(Preferences.getEditor("EdgeMode"))
        )
        self.edgeLineColumnSlider.setValue(Preferences.getEditor("EdgeColumn"))
        self.initColour(
            "Edge", self.edgeBackgroundColorButton, Preferences.getEditorColour
        )

        self.bracehighlightingCheckBox.setChecked(
            Preferences.getEditor("BraceHighlighting")
        )
        self.initColour(
            "MatchingBrace", self.matchingBracesButton, Preferences.getEditorColour
        )
        self.initColour(
            "MatchingBraceBack",
            self.matchingBracesBackButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "NonmatchingBrace",
            self.nonmatchingBracesButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "NonmatchingBraceBack",
            self.nonmatchingBracesBackButton,
            Preferences.getEditorColour,
        )

        self.zoomfactorSlider.setValue(Preferences.getEditor("ZoomFactor"))

        self.whitespaceCheckBox.setChecked(Preferences.getEditor("ShowWhitespace"))
        self.whitespaceSizeSpinBox.setValue(Preferences.getEditor("WhitespaceSize"))
        self.initColour(
            "WhitespaceForeground",
            self.whitespaceForegroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "WhitespaceBackground",
            self.whitespaceBackgroundButton,
            Preferences.getEditorColour,
        )
        if not hasattr(QsciScintilla, "setWhitespaceForegroundColor"):
            self.whitespaceSizeSpinBox.setEnabled(False)
            self.whitespaceForegroundButton.setEnabled(False)
            self.whitespaceBackgroundButton.setEnabled(False)

        self.miniMenuCheckBox.setChecked(Preferences.getEditor("MiniContextMenu"))
        self.hideFormatButtonsCheckBox.setChecked(
            Preferences.getEditor("HideFormatButtons")
        )

        self.enableAnnotationsCheckBox.setChecked(
            Preferences.getEditor("AnnotationsEnabled")
        )

        self.editAreaOverrideCheckBox.setChecked(
            Preferences.getEditor("OverrideEditAreaColours")
        )
        self.initColour(
            "EditAreaForeground",
            self.editAreaForegroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "EditAreaBackground",
            self.editAreaBackgroundButton,
            Preferences.getEditorColour,
        )

        self.enableChangeTraceCheckBox.setChecked(
            Preferences.getEditor("OnlineChangeTrace")
        )
        self.changeTraceTimeoutSpinBox.setValue(
            Preferences.getEditor("OnlineChangeTraceInterval")
        )
        self.initColour(
            "OnlineChangeTraceMarkerUnsaved",
            self.changeMarkerUnsavedColorButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "OnlineChangeTraceMarkerSaved",
            self.changeMarkerSavedColorButton,
            Preferences.getEditorColour,
        )

        self.markerMapRightCheckBox.setChecked(
            Preferences.getEditor("ShowMarkerMapOnRight")
        )
        self.initColour(
            "BookmarksMap", self.bookmarksMapButton, Preferences.getEditorColour
        )
        self.initColour("ErrorsMap", self.errorsMapButton, Preferences.getEditorColour)
        self.initColour(
            "WarningsMap", self.warningsMapButton, Preferences.getEditorColour
        )
        self.initColour(
            "BreakpointsMap", self.breakpointsMapButton, Preferences.getEditorColour
        )
        self.initColour("TasksMap", self.tasksMapButton, Preferences.getEditorColour)
        self.initColour(
            "CoverageMap", self.coverageMapButton, Preferences.getEditorColour
        )
        self.initColour(
            "ChangesMap", self.changesMapButton, Preferences.getEditorColour
        )
        self.initColour(
            "CurrentMap", self.currentMapButton, Preferences.getEditorColour
        )
        self.initColour(
            "SearchMarkersMap", self.searchMarkerMapButton, Preferences.getEditorColour
        )
        self.initColour(
            "VcsConflictMarkersMap",
            self.conflictMarkerMapButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "MarkerMapBackground",
            self.markerMapBackgroundButton,
            Preferences.getEditorColour,
        )
        self.changesMarkerCheckBox.setChecked(
            Preferences.getEditor("ShowMarkerChanges")
        )
        self.coverageMarkerCheckBox.setChecked(
            Preferences.getEditor("ShowMarkerCoverage")
        )
        self.searchMarkerCheckBox.setChecked(Preferences.getEditor("ShowMarkerSearch"))

        self.indentguidesCheckBox.setChecked(Preferences.getEditor("IndentationGuides"))
        self.initColour(
            "IndentationGuidesBackground",
            self.indentationGuidesBackgroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "IndentationGuidesForeground",
            self.indentationGuidesForegroundButton,
            Preferences.getEditorColour,
        )

        self.initColour(
            "HighlightMarker",
            self.highlightingBackgroundButton,
            Preferences.getEditorColour,
            hasAlpha=True,
        )

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        from ..ConfigurationDialog import ConfigurationMode

        if displayMode in (ConfigurationMode.SHELLMODE,):
            self.foldMarginGroup.hide()
            self.caretLineGroup.hide()
            self.debuggingGroup.hide()
            self.wrapLongLinesGroup.hide()
            self.edgeModeGroup.hide()
            self.zoomGroup.hide()
            self.annotationsGroup.hide()
            self.changeTracingGroup.hide()
            self.indentationsGroup.hide()
            self.markerMapGroup.hide()
            self.variousGroup.hide()
            self.fontsGroup.hide()
            self.lineNumbersGroup.hide()

    def save(self):
        """
        Public slot to save the Editor Styles configuration.
        """
        Preferences.setEditor(
            "FoldingStyle", self.foldStyles[self.foldingStyleComboBox.currentIndex()]
        )
        Preferences.setEditorOtherFonts("MarginsFont", self.marginsFont)
        Preferences.setEditorOtherFonts("DefaultFont", self.defaultFont)
        Preferences.setEditorOtherFonts("MonospacedFont", self.monospacedFont)
        Preferences.setEditor("UseMonospacedFont", self.monospacedCheckBox.isChecked())

        Preferences.setEditor("LinenoMargin", self.linenoCheckBox.isChecked())
        Preferences.setEditor("FoldingMargin", self.foldingCheckBox.isChecked())

        Preferences.setEditor(
            "CaretLineVisible", self.caretlineVisibleCheckBox.isChecked()
        )
        Preferences.setEditor(
            "CaretLineAlwaysVisible", self.caretlineAlwaysVisibleCheckBox.isChecked()
        )
        Preferences.setEditor(
            "ColourizeSelText", self.colourizeSelTextCheckBox.isChecked()
        )
        Preferences.setEditor(
            "CustomSelectionColours", self.customSelColourCheckBox.isChecked()
        )
        Preferences.setEditor(
            "ExtendSelectionToEol", self.extentSelEolCheckBox.isChecked()
        )
        Preferences.setEditor(
            "LineMarkersBackground", self.debugMarkerBackgroundCheckBox.isChecked()
        )

        Preferences.setEditor("CaretWidth", self.caretWidthSpinBox.value())
        Preferences.setEditor(
            "CaretLineFrameWidth", self.caretlineFrameWidthSpinBox.value()
        )

        Preferences.setEditor("ShowEOL", self.eolCheckBox.isChecked())
        Preferences.setEditor(
            "WrapLongLinesMode",
            self.wrapModeComboBox.itemData(self.wrapModeComboBox.currentIndex()),
        )
        Preferences.setEditor(
            "WrapVisualFlag",
            self.wrapVisualComboBox.itemData(self.wrapVisualComboBox.currentIndex()),
        )
        Preferences.setEditor(
            "WrapIndentMode",
            self.wrapIndentComboBox.itemData(self.wrapIndentComboBox.currentIndex()),
        )
        Preferences.setEditor("WrapStartIndent", self.wrapStartIndentSpinBox.value())
        Preferences.setEditor(
            "EdgeMode", self.edgeModes[self.edgeModeCombo.currentIndex()]
        )
        Preferences.setEditor("EdgeColumn", self.edgeLineColumnSlider.value())

        Preferences.setEditor(
            "BraceHighlighting", self.bracehighlightingCheckBox.isChecked()
        )

        Preferences.setEditor("ZoomFactor", self.zoomfactorSlider.value())

        Preferences.setEditor("ShowWhitespace", self.whitespaceCheckBox.isChecked())
        Preferences.setEditor("WhitespaceSize", self.whitespaceSizeSpinBox.value())

        Preferences.setEditor("MiniContextMenu", self.miniMenuCheckBox.isChecked())
        Preferences.setEditor(
            "HideFormatButtons", self.hideFormatButtonsCheckBox.isChecked()
        )

        Preferences.setEditor(
            "AnnotationsEnabled", self.enableAnnotationsCheckBox.isChecked()
        )

        Preferences.setEditor(
            "OverrideEditAreaColours", self.editAreaOverrideCheckBox.isChecked()
        )

        Preferences.setEditor(
            "OnlineChangeTrace", self.enableChangeTraceCheckBox.isChecked()
        )
        Preferences.setEditor(
            "OnlineChangeTraceInterval", self.changeTraceTimeoutSpinBox.value()
        )

        Preferences.setEditor(
            "IndentationGuides", self.indentguidesCheckBox.isChecked()
        )

        Preferences.setEditor(
            "ShowMarkerMapOnRight", self.markerMapRightCheckBox.isChecked()
        )
        Preferences.setEditor(
            "ShowMarkerChanges", self.changesMarkerCheckBox.isChecked()
        )
        Preferences.setEditor(
            "ShowMarkerCoverage", self.coverageMarkerCheckBox.isChecked()
        )
        Preferences.setEditor("ShowMarkerSearch", self.searchMarkerCheckBox.isChecked())

        self.saveColours(Preferences.setEditorColour)
        for color in self.editorColours:
            Preferences.setEditorColour(color, self.editorColours[color])

    @pyqtSlot()
    def on_linenumbersFontButton_clicked(self):
        """
        Private method used to select the font for the editor margins.
        """
        self.marginsFont = self.selectFont(
            self.marginsFontSample,
            self.marginsFont,
            options=QFontDialog.FontDialogOption.MonospacedFonts,
        )

    @pyqtSlot()
    def on_defaultFontButton_clicked(self):
        """
        Private method used to select the default font for the editor.
        """
        self.defaultFont = self.selectFont(self.defaultFontSample, self.defaultFont)

    @pyqtSlot()
    def on_monospacedFontButton_clicked(self):
        """
        Private method used to select the font to be used as the monospaced
        font.
        """
        self.monospacedFont = self.selectFont(
            self.monospacedFontSample,
            self.monospacedFont,
            options=QFontDialog.FontDialogOption.MonospacedFonts,
        )

    def __setSampleStyleSheet(self, sampleLineEdit, color, background):
        """
        Private method to colorize a sample with given foreground and
        background colors.

        @param sampleLineEdit line edit element to be colorized
        @type QLineEdit
        @param color text color to be shown
        @type QColor
        @param background background color to be shown
        @type QColor
        """
        sampleLineEdit.setStyleSheet(
            "QLineEdit {{ color: {0}; background-color: {1}; }}".format(
                color.name(), background.name()
            )
        )

    def polishPage(self):
        """
        Public slot to perform some polishing actions.
        """
        self.marginsFontSample.setFont(self.marginsFont)
        self.defaultFontSample.setFont(self.defaultFont)
        self.monospacedFontSample.setFont(self.monospacedFont)

        self.__setSampleStyleSheet(
            self.annotationsWarningSample,
            self.editorColours["AnnotationsWarningForeground"],
            self.editorColours["AnnotationsWarningBackground"],
        )

        self.__setSampleStyleSheet(
            self.annotationsErrorSample,
            self.editorColours["AnnotationsErrorForeground"],
            self.editorColours["AnnotationsErrorBackground"],
        )

        self.__setSampleStyleSheet(
            self.annotationsStyleWarningSample,
            self.editorColours["AnnotationsStyleForeground"],
            self.editorColours["AnnotationsStyleBackground"],
        )

        self.__setSampleStyleSheet(
            self.annotationsInformationSample,
            self.editorColours["AnnotationsInfoForeground"],
            self.editorColours["AnnotationsInfoBackground"],
        )

    def __selectAnnotationColor(self, annotationType, isBackground, annotationSample):
        """
        Private method to select an annotation color and update the sample.

        @param annotationType type of the annotation
        @type str
        @param isBackground flag indicating the background color
        @type bool
        @param annotationSample reference to the annotation sample widget
        @type QLineEdit
        """
        bgColorStr = f"Annotations{annotationType}Background"
        fgColorStr = f"Annotations{annotationType}Foreground"

        color = QColorDialog.getColor(
            self.editorColours[bgColorStr]
            if isBackground
            else self.editorColours[fgColorStr]
        )
        if color.isValid():
            self.__setSampleStyleSheet(
                annotationSample,
                self.editorColours[fgColorStr] if isBackground else color,
                color if isBackground else self.editorColours[bgColorStr],
            )
            self.editorColours[bgColorStr if isBackground else fgColorStr] = color

    @pyqtSlot()
    def on_annotationsWarningFgButton_clicked(self):
        """
        Private slot to set the foreground colour of the warning annotations.
        """
        self.__selectAnnotationColor("Warning", False, self.annotationsWarningSample)

    @pyqtSlot()
    def on_annotationsWarningBgButton_clicked(self):
        """
        Private slot to set the background colour of the warning annotations.
        """
        self.__selectAnnotationColor("Warning", True, self.annotationsWarningSample)

    @pyqtSlot()
    def on_annotationsErrorFgButton_clicked(self):
        """
        Private slot to set the foreground colour of the error annotations.
        """
        self.__selectAnnotationColor("Error", False, self.annotationsErrorSample)

    @pyqtSlot()
    def on_annotationsErrorBgButton_clicked(self):
        """
        Private slot to set the background colour of the error annotations.
        """
        self.__selectAnnotationColor("Error", True, self.annotationsErrorSample)

    @pyqtSlot()
    def on_annotationsStyleWarningFgButton_clicked(self):
        """
        Private slot to set the foreground colour of the style annotations.
        """
        self.__selectAnnotationColor("Style", False, self.annotationsStyleWarningSample)

    @pyqtSlot()
    def on_annotationsStyleWarningBgButton_clicked(self):
        """
        Private slot to set the background colour of the style annotations.
        """
        self.__selectAnnotationColor("Style", True, self.annotationsStyleWarningSample)

    @pyqtSlot()
    def on_annotationsInformationFgButton_clicked(self):
        """
        Private slot to set the foreground colour of the information annotations.
        """
        self.__selectAnnotationColor("Info", False, self.annotationsInformationSample)

    @pyqtSlot()
    def on_annotationsInformationBgButton_clicked(self):
        """
        Private slot to set the background colour of the information annotations.
        """
        self.__selectAnnotationColor("Info", True, self.annotationsInformationSample)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorStylesPage()
    return page
