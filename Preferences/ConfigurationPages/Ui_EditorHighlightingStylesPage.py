# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/EditorHighlightingStylesPage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_EditorHighlightingStylesPage(object):
    def setupUi(self, EditorHighlightingStylesPage):
        EditorHighlightingStylesPage.setObjectName("EditorHighlightingStylesPage")
        EditorHighlightingStylesPage.resize(550, 624)
        self.verticalLayout = QtWidgets.QVBoxLayout(EditorHighlightingStylesPage)
        self.verticalLayout.setObjectName("verticalLayout")
        self.headerLabel = QtWidgets.QLabel(parent=EditorHighlightingStylesPage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout.addWidget(self.headerLabel)
        self.line1 = QtWidgets.QFrame(parent=EditorHighlightingStylesPage)
        self.line1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line1.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line1.setObjectName("line1")
        self.verticalLayout.addWidget(self.line1)
        self.hboxlayout = QtWidgets.QHBoxLayout()
        self.hboxlayout.setObjectName("hboxlayout")
        self.TextLabel1_3 = QtWidgets.QLabel(parent=EditorHighlightingStylesPage)
        self.TextLabel1_3.setToolTip("")
        self.TextLabel1_3.setObjectName("TextLabel1_3")
        self.hboxlayout.addWidget(self.TextLabel1_3)
        self.lexerLanguageComboBox = QtWidgets.QComboBox(parent=EditorHighlightingStylesPage)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lexerLanguageComboBox.sizePolicy().hasHeightForWidth())
        self.lexerLanguageComboBox.setSizePolicy(sizePolicy)
        self.lexerLanguageComboBox.setObjectName("lexerLanguageComboBox")
        self.hboxlayout.addWidget(self.lexerLanguageComboBox)
        self.verticalLayout.addLayout(self.hboxlayout)
        self.styleGroup = QtWidgets.QGroupBox(parent=EditorHighlightingStylesPage)
        self.styleGroup.setObjectName("styleGroup")
        self.gridLayout = QtWidgets.QGridLayout(self.styleGroup)
        self.gridLayout.setObjectName("gridLayout")
        self.styleElementList = QtWidgets.QTreeWidget(parent=self.styleGroup)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.styleElementList.sizePolicy().hasHeightForWidth())
        self.styleElementList.setSizePolicy(sizePolicy)
        self.styleElementList.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.styleElementList.setRootIsDecorated(False)
        self.styleElementList.setItemsExpandable(False)
        self.styleElementList.setHeaderHidden(True)
        self.styleElementList.setObjectName("styleElementList")
        self.styleElementList.headerItem().setText(0, "1")
        self.gridLayout.addWidget(self.styleElementList, 0, 0, 1, 1)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem = QtWidgets.QSpacerItem(13, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.defaultSubstylesButton = QtWidgets.QToolButton(parent=self.styleGroup)
        self.defaultSubstylesButton.setObjectName("defaultSubstylesButton")
        self.horizontalLayout_2.addWidget(self.defaultSubstylesButton)
        self.addSubstyleButton = QtWidgets.QToolButton(parent=self.styleGroup)
        self.addSubstyleButton.setObjectName("addSubstyleButton")
        self.horizontalLayout_2.addWidget(self.addSubstyleButton)
        self.deleteSubstyleButton = QtWidgets.QToolButton(parent=self.styleGroup)
        self.deleteSubstyleButton.setObjectName("deleteSubstyleButton")
        self.horizontalLayout_2.addWidget(self.deleteSubstyleButton)
        self.editSubstyleButton = QtWidgets.QToolButton(parent=self.styleGroup)
        self.editSubstyleButton.setObjectName("editSubstyleButton")
        self.horizontalLayout_2.addWidget(self.editSubstyleButton)
        self.copySubstyleButton = QtWidgets.QToolButton(parent=self.styleGroup)
        self.copySubstyleButton.setObjectName("copySubstyleButton")
        self.horizontalLayout_2.addWidget(self.copySubstyleButton)
        spacerItem1 = QtWidgets.QSpacerItem(13, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.line_3 = QtWidgets.QFrame(parent=self.styleGroup)
        self.line_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_3.setObjectName("line_3")
        self.verticalLayout_2.addWidget(self.line_3)
        self.foregroundButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.foregroundButton.setObjectName("foregroundButton")
        self.verticalLayout_2.addWidget(self.foregroundButton)
        self.backgroundButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.backgroundButton.setObjectName("backgroundButton")
        self.verticalLayout_2.addWidget(self.backgroundButton)
        self.fontButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.fontButton.setObjectName("fontButton")
        self.verticalLayout_2.addWidget(self.fontButton)
        self.eolfillCheckBox = QtWidgets.QCheckBox(parent=self.styleGroup)
        self.eolfillCheckBox.setObjectName("eolfillCheckBox")
        self.verticalLayout_2.addWidget(self.eolfillCheckBox)
        self.line = QtWidgets.QFrame(parent=self.styleGroup)
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout_2.addWidget(self.line)
        self.defaultButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.defaultButton.setObjectName("defaultButton")
        self.verticalLayout_2.addWidget(self.defaultButton)
        spacerItem2 = QtWidgets.QSpacerItem(20, 43, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_2.addItem(spacerItem2)
        self.monospacedButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.monospacedButton.setCheckable(True)
        self.monospacedButton.setChecked(True)
        self.monospacedButton.setObjectName("monospacedButton")
        self.verticalLayout_2.addWidget(self.monospacedButton)
        spacerItem3 = QtWidgets.QSpacerItem(20, 38, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_2.addItem(spacerItem3)
        self.allBackgroundColoursButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.allBackgroundColoursButton.setObjectName("allBackgroundColoursButton")
        self.verticalLayout_2.addWidget(self.allBackgroundColoursButton)
        self.allFontsButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.allFontsButton.setObjectName("allFontsButton")
        self.verticalLayout_2.addWidget(self.allFontsButton)
        self.allEolFillButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.allEolFillButton.setObjectName("allEolFillButton")
        self.verticalLayout_2.addWidget(self.allEolFillButton)
        self.line_2 = QtWidgets.QFrame(parent=self.styleGroup)
        self.line_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_2.setObjectName("line_2")
        self.verticalLayout_2.addWidget(self.line_2)
        self.allDefaultButton = QtWidgets.QPushButton(parent=self.styleGroup)
        self.allDefaultButton.setObjectName("allDefaultButton")
        self.verticalLayout_2.addWidget(self.allDefaultButton)
        self.gridLayout.addLayout(self.verticalLayout_2, 0, 1, 1, 1)
        self.sampleText = QtWidgets.QLineEdit(parent=self.styleGroup)
        self.sampleText.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.sampleText.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.sampleText.setReadOnly(True)
        self.sampleText.setObjectName("sampleText")
        self.gridLayout.addWidget(self.sampleText, 1, 0, 1, 2)
        self.label = QtWidgets.QLabel(parent=self.styleGroup)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 2, 0, 1, 2)
        self.verticalLayout.addWidget(self.styleGroup)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.importButton = QtWidgets.QPushButton(parent=EditorHighlightingStylesPage)
        self.importButton.setObjectName("importButton")
        self.horizontalLayout.addWidget(self.importButton)
        self.exportButton = QtWidgets.QPushButton(parent=EditorHighlightingStylesPage)
        self.exportButton.setObjectName("exportButton")
        self.horizontalLayout.addWidget(self.exportButton)
        self.importAllButton = QtWidgets.QPushButton(parent=EditorHighlightingStylesPage)
        self.importAllButton.setObjectName("importAllButton")
        self.horizontalLayout.addWidget(self.importAllButton)
        self.exportAllButton = QtWidgets.QPushButton(parent=EditorHighlightingStylesPage)
        self.exportAllButton.setObjectName("exportAllButton")
        self.horizontalLayout.addWidget(self.exportAllButton)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(EditorHighlightingStylesPage)
        QtCore.QMetaObject.connectSlotsByName(EditorHighlightingStylesPage)
        EditorHighlightingStylesPage.setTabOrder(self.lexerLanguageComboBox, self.styleElementList)
        EditorHighlightingStylesPage.setTabOrder(self.styleElementList, self.defaultSubstylesButton)
        EditorHighlightingStylesPage.setTabOrder(self.defaultSubstylesButton, self.addSubstyleButton)
        EditorHighlightingStylesPage.setTabOrder(self.addSubstyleButton, self.deleteSubstyleButton)
        EditorHighlightingStylesPage.setTabOrder(self.deleteSubstyleButton, self.editSubstyleButton)
        EditorHighlightingStylesPage.setTabOrder(self.editSubstyleButton, self.copySubstyleButton)
        EditorHighlightingStylesPage.setTabOrder(self.copySubstyleButton, self.foregroundButton)
        EditorHighlightingStylesPage.setTabOrder(self.foregroundButton, self.backgroundButton)
        EditorHighlightingStylesPage.setTabOrder(self.backgroundButton, self.fontButton)
        EditorHighlightingStylesPage.setTabOrder(self.fontButton, self.eolfillCheckBox)
        EditorHighlightingStylesPage.setTabOrder(self.eolfillCheckBox, self.defaultButton)
        EditorHighlightingStylesPage.setTabOrder(self.defaultButton, self.monospacedButton)
        EditorHighlightingStylesPage.setTabOrder(self.monospacedButton, self.allBackgroundColoursButton)
        EditorHighlightingStylesPage.setTabOrder(self.allBackgroundColoursButton, self.allFontsButton)
        EditorHighlightingStylesPage.setTabOrder(self.allFontsButton, self.allEolFillButton)
        EditorHighlightingStylesPage.setTabOrder(self.allEolFillButton, self.allDefaultButton)
        EditorHighlightingStylesPage.setTabOrder(self.allDefaultButton, self.importButton)
        EditorHighlightingStylesPage.setTabOrder(self.importButton, self.exportButton)
        EditorHighlightingStylesPage.setTabOrder(self.exportButton, self.importAllButton)
        EditorHighlightingStylesPage.setTabOrder(self.importAllButton, self.exportAllButton)

    def retranslateUi(self, EditorHighlightingStylesPage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("EditorHighlightingStylesPage", "<b>Configure syntax highlighting</b>"))
        self.TextLabel1_3.setText(_translate("EditorHighlightingStylesPage", "Lexer Language:"))
        self.lexerLanguageComboBox.setToolTip(_translate("EditorHighlightingStylesPage", "Select the lexer language to be configured."))
        self.styleGroup.setTitle(_translate("EditorHighlightingStylesPage", "Style Element"))
        self.defaultSubstylesButton.setToolTip(_translate("EditorHighlightingStylesPage", "Press to set all sub-styles to default values"))
        self.addSubstyleButton.setToolTip(_translate("EditorHighlightingStylesPage", "Press to add a sub-style to the selected style"))
        self.deleteSubstyleButton.setToolTip(_translate("EditorHighlightingStylesPage", "Press to to delete the selected sub-style"))
        self.editSubstyleButton.setToolTip(_translate("EditorHighlightingStylesPage", "Press to edit the selected sub-style"))
        self.copySubstyleButton.setToolTip(_translate("EditorHighlightingStylesPage", "Press to copy the selected sub-style"))
        self.foregroundButton.setToolTip(_translate("EditorHighlightingStylesPage", "Select the foreground color."))
        self.foregroundButton.setText(_translate("EditorHighlightingStylesPage", "Foreground Color"))
        self.backgroundButton.setToolTip(_translate("EditorHighlightingStylesPage", "Select the background color."))
        self.backgroundButton.setText(_translate("EditorHighlightingStylesPage", "Background Color"))
        self.fontButton.setToolTip(_translate("EditorHighlightingStylesPage", "Select the font."))
        self.fontButton.setText(_translate("EditorHighlightingStylesPage", "Font"))
        self.eolfillCheckBox.setToolTip(_translate("EditorHighlightingStylesPage", "Select end of line fill."))
        self.eolfillCheckBox.setText(_translate("EditorHighlightingStylesPage", "Fill to end of line"))
        self.defaultButton.setToolTip(_translate("EditorHighlightingStylesPage", "Press to set the current style to its default values"))
        self.defaultButton.setText(_translate("EditorHighlightingStylesPage", "to Default"))
        self.monospacedButton.setToolTip(_translate("EditorHighlightingStylesPage", "Press to show only monospaced fonts"))
        self.monospacedButton.setText(_translate("EditorHighlightingStylesPage", "Monospaced Fonts Only"))
        self.allBackgroundColoursButton.setToolTip(_translate("EditorHighlightingStylesPage", "Select the background color for all styles"))
        self.allBackgroundColoursButton.setText(_translate("EditorHighlightingStylesPage", "All Background Colors"))
        self.allFontsButton.setToolTip(_translate("EditorHighlightingStylesPage", "Select the font for all styles."))
        self.allFontsButton.setText(_translate("EditorHighlightingStylesPage", "All Fonts"))
        self.allEolFillButton.setToolTip(_translate("EditorHighlightingStylesPage", "Select the eol fill for all styles"))
        self.allEolFillButton.setText(_translate("EditorHighlightingStylesPage", "All Fill to end of line"))
        self.allDefaultButton.setToolTip(_translate("EditorHighlightingStylesPage", "Press to set all styles to their default values"))
        self.allDefaultButton.setText(_translate("EditorHighlightingStylesPage", "All to Default"))
        self.sampleText.setText(_translate("EditorHighlightingStylesPage", "Sample Text"))
        self.label.setText(_translate("EditorHighlightingStylesPage", "<b>Note:</b> The tick in the list above indicates the entrie\'s \'fill to end of line\' setting."))
        self.importButton.setToolTip(_translate("EditorHighlightingStylesPage", "Imports all styles of languages to be selected"))
        self.importButton.setText(_translate("EditorHighlightingStylesPage", "Import styles"))
        self.exportButton.setToolTip(_translate("EditorHighlightingStylesPage", "Exports all styles of languages to be selected"))
        self.exportButton.setText(_translate("EditorHighlightingStylesPage", "Export styles"))
        self.importAllButton.setToolTip(_translate("EditorHighlightingStylesPage", "Imports all styles of all languages"))
        self.importAllButton.setText(_translate("EditorHighlightingStylesPage", "Import all styles"))
        self.exportAllButton.setToolTip(_translate("EditorHighlightingStylesPage", "Exports all styles of all languages"))
        self.exportAllButton.setText(_translate("EditorHighlightingStylesPage", "Export all styles"))
