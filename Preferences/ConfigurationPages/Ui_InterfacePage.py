# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/InterfacePage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_InterfacePage(object):
    def setupUi(self, InterfacePage):
        InterfacePage.setObjectName("InterfacePage")
        InterfacePage.resize(550, 1276)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(InterfacePage)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.headerLabel = QtWidgets.QLabel(parent=InterfacePage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout_3.addWidget(self.headerLabel)
        self.line9 = QtWidgets.QFrame(parent=InterfacePage)
        self.line9.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line9.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9.setObjectName("line9")
        self.verticalLayout_3.addWidget(self.line9)
        self.groupBox_4 = QtWidgets.QGroupBox(parent=InterfacePage)
        self.groupBox_4.setObjectName("groupBox_4")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_4)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.uiBrowsersListFoldersFirstCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_4)
        self.uiBrowsersListFoldersFirstCheckBox.setObjectName("uiBrowsersListFoldersFirstCheckBox")
        self.gridLayout_2.addWidget(self.uiBrowsersListFoldersFirstCheckBox, 0, 0, 1, 1)
        self.uiBrowsersHideNonPublicCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_4)
        self.uiBrowsersHideNonPublicCheckBox.setObjectName("uiBrowsersHideNonPublicCheckBox")
        self.gridLayout_2.addWidget(self.uiBrowsersHideNonPublicCheckBox, 0, 1, 1, 1)
        self.uiBrowsersSortByOccurrenceCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_4)
        self.uiBrowsersSortByOccurrenceCheckBox.setObjectName("uiBrowsersSortByOccurrenceCheckBox")
        self.gridLayout_2.addWidget(self.uiBrowsersSortByOccurrenceCheckBox, 1, 0, 1, 1)
        self.browserShowCodingCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_4)
        self.browserShowCodingCheckBox.setObjectName("browserShowCodingCheckBox")
        self.gridLayout_2.addWidget(self.browserShowCodingCheckBox, 1, 1, 1, 1)
        self.browserShowConnectedServerOnlyCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_4)
        self.browserShowConnectedServerOnlyCheckBox.setObjectName("browserShowConnectedServerOnlyCheckBox")
        self.gridLayout_2.addWidget(self.browserShowConnectedServerOnlyCheckBox, 2, 0, 1, 2)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_4 = QtWidgets.QLabel(parent=self.groupBox_4)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_2.addWidget(self.label_4)
        self.fileFiltersEdit = QtWidgets.QLineEdit(parent=self.groupBox_4)
        self.fileFiltersEdit.setObjectName("fileFiltersEdit")
        self.horizontalLayout_2.addWidget(self.fileFiltersEdit)
        self.gridLayout_2.addLayout(self.horizontalLayout_2, 3, 0, 1, 2)
        self.verticalLayout_3.addWidget(self.groupBox_4)
        self.uiCaptionShowsFilenameGroupBox = QtWidgets.QGroupBox(parent=InterfacePage)
        self.uiCaptionShowsFilenameGroupBox.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.uiCaptionShowsFilenameGroupBox.setCheckable(True)
        self.uiCaptionShowsFilenameGroupBox.setObjectName("uiCaptionShowsFilenameGroupBox")
        self.hboxlayout = QtWidgets.QHBoxLayout(self.uiCaptionShowsFilenameGroupBox)
        self.hboxlayout.setObjectName("hboxlayout")
        self.label = QtWidgets.QLabel(parent=self.uiCaptionShowsFilenameGroupBox)
        self.label.setObjectName("label")
        self.hboxlayout.addWidget(self.label)
        self.filenameLengthSpinBox = QtWidgets.QSpinBox(parent=self.uiCaptionShowsFilenameGroupBox)
        self.filenameLengthSpinBox.setMinimum(10)
        self.filenameLengthSpinBox.setMaximum(999)
        self.filenameLengthSpinBox.setSingleStep(10)
        self.filenameLengthSpinBox.setProperty("value", 100)
        self.filenameLengthSpinBox.setObjectName("filenameLengthSpinBox")
        self.hboxlayout.addWidget(self.filenameLengthSpinBox)
        spacerItem = QtWidgets.QSpacerItem(31, 23, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.hboxlayout.addItem(spacerItem)
        self.verticalLayout_3.addWidget(self.uiCaptionShowsFilenameGroupBox)
        self.groupBox = QtWidgets.QGroupBox(parent=InterfacePage)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.label_2 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridLayout_3.addWidget(self.label_2, 0, 0, 1, 1)
        self.styleComboBox = QtWidgets.QComboBox(parent=self.groupBox)
        self.styleComboBox.setObjectName("styleComboBox")
        self.gridLayout_3.addWidget(self.styleComboBox, 0, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_3.setObjectName("label_3")
        self.gridLayout_3.addWidget(self.label_3, 1, 0, 1, 1)
        self.styleSheetPicker = EricPathPicker(parent=self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.styleSheetPicker.sizePolicy().hasHeightForWidth())
        self.styleSheetPicker.setSizePolicy(sizePolicy)
        self.styleSheetPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.styleSheetPicker.setObjectName("styleSheetPicker")
        self.gridLayout_3.addWidget(self.styleSheetPicker, 1, 1, 1, 1)
        self.label_6 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_6.setObjectName("label_6")
        self.gridLayout_3.addWidget(self.label_6, 2, 0, 1, 1)
        self.styleIconsPathPicker = EricPathPicker(parent=self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.styleIconsPathPicker.sizePolicy().hasHeightForWidth())
        self.styleIconsPathPicker.setSizePolicy(sizePolicy)
        self.styleIconsPathPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.styleIconsPathPicker.setObjectName("styleIconsPathPicker")
        self.gridLayout_3.addWidget(self.styleIconsPathPicker, 2, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_7.setObjectName("label_7")
        self.gridLayout_3.addWidget(self.label_7, 3, 0, 1, 1)
        self.itemSelectionStyleComboBox = QtWidgets.QComboBox(parent=self.groupBox)
        self.itemSelectionStyleComboBox.setObjectName("itemSelectionStyleComboBox")
        self.gridLayout_3.addWidget(self.itemSelectionStyleComboBox, 3, 1, 1, 1)
        self.label_8 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_8.setObjectName("label_8")
        self.gridLayout_3.addWidget(self.label_8, 4, 1, 1, 1)
        self.verticalLayout_3.addWidget(self.groupBox)
        self.groupBox_8 = QtWidgets.QGroupBox(parent=InterfacePage)
        self.groupBox_8.setObjectName("groupBox_8")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox_8)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.gridLayout_7 = QtWidgets.QGridLayout()
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.iconBarButton = QtWidgets.QPushButton(parent=self.groupBox_8)
        self.iconBarButton.setObjectName("iconBarButton")
        self.gridLayout_7.addWidget(self.iconBarButton, 0, 0, 1, 2)
        self.label_5 = QtWidgets.QLabel(parent=self.groupBox_8)
        self.label_5.setObjectName("label_5")
        self.gridLayout_7.addWidget(self.label_5, 1, 0, 1, 1)
        self.iconSizeComboBox = QtWidgets.QComboBox(parent=self.groupBox_8)
        self.iconSizeComboBox.setObjectName("iconSizeComboBox")
        self.gridLayout_7.addWidget(self.iconSizeComboBox, 1, 1, 1, 1)
        self.horizontalLayout.addLayout(self.gridLayout_7)
        self.sampleLabel = QtWidgets.QLabel(parent=self.groupBox_8)
        self.sampleLabel.setMinimumSize(QtCore.QSize(50, 50))
        self.sampleLabel.setText("")
        self.sampleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.sampleLabel.setObjectName("sampleLabel")
        self.horizontalLayout.addWidget(self.sampleLabel)
        self.highlightedSampleLabel = QtWidgets.QLabel(parent=self.groupBox_8)
        self.highlightedSampleLabel.setMinimumSize(QtCore.QSize(50, 50))
        self.highlightedSampleLabel.setText("")
        self.highlightedSampleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.highlightedSampleLabel.setObjectName("highlightedSampleLabel")
        self.horizontalLayout.addWidget(self.highlightedSampleLabel)
        spacerItem1 = QtWidgets.QSpacerItem(396, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.line9_3 = QtWidgets.QFrame(parent=self.groupBox_8)
        self.line9_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_3.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line9_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_3.setObjectName("line9_3")
        self.verticalLayout_2.addWidget(self.line9_3)
        self.TextLabel1_2_2_3 = QtWidgets.QLabel(parent=self.groupBox_8)
        self.TextLabel1_2_2_3.setObjectName("TextLabel1_2_2_3")
        self.verticalLayout_2.addWidget(self.TextLabel1_2_2_3)
        self.combinedLeftRightSidebarCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_8)
        self.combinedLeftRightSidebarCheckBox.setObjectName("combinedLeftRightSidebarCheckBox")
        self.verticalLayout_2.addWidget(self.combinedLeftRightSidebarCheckBox)
        self.verticalLayout_3.addWidget(self.groupBox_8)
        self.line9_2 = QtWidgets.QFrame(parent=InterfacePage)
        self.line9_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line9_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_2.setObjectName("line9_2")
        self.verticalLayout_3.addWidget(self.line9_2)
        self.TextLabel1_2_2_2 = QtWidgets.QLabel(parent=InterfacePage)
        self.TextLabel1_2_2_2.setObjectName("TextLabel1_2_2_2")
        self.verticalLayout_3.addWidget(self.TextLabel1_2_2_2)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.layoutComboBox = QtWidgets.QComboBox(parent=InterfacePage)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.layoutComboBox.sizePolicy().hasHeightForWidth())
        self.layoutComboBox.setSizePolicy(sizePolicy)
        self.layoutComboBox.setObjectName("layoutComboBox")
        self.layoutComboBox.addItem("")
        self.layoutComboBox.addItem("")
        self.gridLayout.addWidget(self.layoutComboBox, 1, 1, 1, 1)
        self.languageComboBox = QtWidgets.QComboBox(parent=InterfacePage)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.languageComboBox.sizePolicy().hasHeightForWidth())
        self.languageComboBox.setSizePolicy(sizePolicy)
        self.languageComboBox.setObjectName("languageComboBox")
        self.gridLayout.addWidget(self.languageComboBox, 0, 1, 1, 1)
        self.languageLabel = QtWidgets.QLabel(parent=InterfacePage)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.languageLabel.sizePolicy().hasHeightForWidth())
        self.languageLabel.setSizePolicy(sizePolicy)
        self.languageLabel.setObjectName("languageLabel")
        self.gridLayout.addWidget(self.languageLabel, 0, 0, 1, 1)
        self.layoutLabel = QtWidgets.QLabel(parent=InterfacePage)
        self.layoutLabel.setObjectName("layoutLabel")
        self.gridLayout.addWidget(self.layoutLabel, 1, 0, 1, 1)
        self.verticalLayout_3.addLayout(self.gridLayout)
        self.groupBox_3 = QtWidgets.QGroupBox(parent=InterfacePage)
        self.groupBox_3.setObjectName("groupBox_3")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox_3)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_10 = QtWidgets.QGroupBox(parent=self.groupBox_3)
        self.groupBox_10.setObjectName("groupBox_10")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.groupBox_10)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.symbolsCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_10)
        self.symbolsCheckBox.setObjectName("symbolsCheckBox")
        self.gridLayout_5.addWidget(self.symbolsCheckBox, 2, 0, 1, 1)
        self.templateViewerCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_10)
        self.templateViewerCheckBox.setObjectName("templateViewerCheckBox")
        self.gridLayout_5.addWidget(self.templateViewerCheckBox, 1, 0, 1, 1)
        self.fileBrowserCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_10)
        self.fileBrowserCheckBox.setObjectName("fileBrowserCheckBox")
        self.gridLayout_5.addWidget(self.fileBrowserCheckBox, 1, 1, 1, 1)
        self.findReplaceCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_10)
        self.findReplaceCheckBox.setObjectName("findReplaceCheckBox")
        self.gridLayout_5.addWidget(self.findReplaceCheckBox, 0, 0, 1, 1)
        self.findLocationCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_10)
        self.findLocationCheckBox.setObjectName("findLocationCheckBox")
        self.gridLayout_5.addWidget(self.findLocationCheckBox, 0, 1, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_10)
        self.leftRightGroupBox = QtWidgets.QGroupBox(parent=self.groupBox_3)
        self.leftRightGroupBox.setObjectName("leftRightGroupBox")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.leftRightGroupBox)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.codeDocumentationViewerCheckBox = QtWidgets.QCheckBox(parent=self.leftRightGroupBox)
        self.codeDocumentationViewerCheckBox.setObjectName("codeDocumentationViewerCheckBox")
        self.gridLayout_4.addWidget(self.codeDocumentationViewerCheckBox, 0, 0, 1, 1)
        self.helpViewerCheckBox = QtWidgets.QCheckBox(parent=self.leftRightGroupBox)
        self.helpViewerCheckBox.setObjectName("helpViewerCheckBox")
        self.gridLayout_4.addWidget(self.helpViewerCheckBox, 0, 1, 1, 1)
        self.condaCheckBox = QtWidgets.QCheckBox(parent=self.leftRightGroupBox)
        self.condaCheckBox.setObjectName("condaCheckBox")
        self.gridLayout_4.addWidget(self.condaCheckBox, 1, 0, 1, 1)
        self.pypiCheckBox = QtWidgets.QCheckBox(parent=self.leftRightGroupBox)
        self.pypiCheckBox.setObjectName("pypiCheckBox")
        self.gridLayout_4.addWidget(self.pypiCheckBox, 1, 1, 1, 1)
        self.cooperationCheckBox = QtWidgets.QCheckBox(parent=self.leftRightGroupBox)
        self.cooperationCheckBox.setObjectName("cooperationCheckBox")
        self.gridLayout_4.addWidget(self.cooperationCheckBox, 2, 0, 1, 1)
        self.ircCheckBox = QtWidgets.QCheckBox(parent=self.leftRightGroupBox)
        self.ircCheckBox.setObjectName("ircCheckBox")
        self.gridLayout_4.addWidget(self.ircCheckBox, 2, 1, 1, 1)
        self.microPythonCheckBox = QtWidgets.QCheckBox(parent=self.leftRightGroupBox)
        self.microPythonCheckBox.setObjectName("microPythonCheckBox")
        self.gridLayout_4.addWidget(self.microPythonCheckBox, 3, 0, 1, 1)
        self.verticalLayout.addWidget(self.leftRightGroupBox)
        self.groupBox_11 = QtWidgets.QGroupBox(parent=self.groupBox_3)
        self.groupBox_11.setObjectName("groupBox_11")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.groupBox_11)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.numbersCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_11)
        self.numbersCheckBox.setObjectName("numbersCheckBox")
        self.gridLayout_6.addWidget(self.numbersCheckBox, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_11)
        self.verticalLayout_3.addWidget(self.groupBox_3)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem2)
        self.resetLayoutButton = QtWidgets.QPushButton(parent=InterfacePage)
        self.resetLayoutButton.setObjectName("resetLayoutButton")
        self.horizontalLayout_3.addWidget(self.resetLayoutButton)
        spacerItem3 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem3)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)
        spacerItem4 = QtWidgets.QSpacerItem(20, 0, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_3.addItem(spacerItem4)
        self.languageLabel.setBuddy(self.languageComboBox)

        self.retranslateUi(InterfacePage)
        QtCore.QMetaObject.connectSlotsByName(InterfacePage)
        InterfacePage.setTabOrder(self.uiBrowsersListFoldersFirstCheckBox, self.uiBrowsersHideNonPublicCheckBox)
        InterfacePage.setTabOrder(self.uiBrowsersHideNonPublicCheckBox, self.uiBrowsersSortByOccurrenceCheckBox)
        InterfacePage.setTabOrder(self.uiBrowsersSortByOccurrenceCheckBox, self.browserShowCodingCheckBox)
        InterfacePage.setTabOrder(self.browserShowCodingCheckBox, self.browserShowConnectedServerOnlyCheckBox)
        InterfacePage.setTabOrder(self.browserShowConnectedServerOnlyCheckBox, self.fileFiltersEdit)
        InterfacePage.setTabOrder(self.fileFiltersEdit, self.uiCaptionShowsFilenameGroupBox)
        InterfacePage.setTabOrder(self.uiCaptionShowsFilenameGroupBox, self.filenameLengthSpinBox)
        InterfacePage.setTabOrder(self.filenameLengthSpinBox, self.styleComboBox)
        InterfacePage.setTabOrder(self.styleComboBox, self.styleSheetPicker)
        InterfacePage.setTabOrder(self.styleSheetPicker, self.styleIconsPathPicker)
        InterfacePage.setTabOrder(self.styleIconsPathPicker, self.itemSelectionStyleComboBox)
        InterfacePage.setTabOrder(self.itemSelectionStyleComboBox, self.iconBarButton)
        InterfacePage.setTabOrder(self.iconBarButton, self.iconSizeComboBox)
        InterfacePage.setTabOrder(self.iconSizeComboBox, self.combinedLeftRightSidebarCheckBox)
        InterfacePage.setTabOrder(self.combinedLeftRightSidebarCheckBox, self.languageComboBox)
        InterfacePage.setTabOrder(self.languageComboBox, self.layoutComboBox)
        InterfacePage.setTabOrder(self.layoutComboBox, self.findReplaceCheckBox)
        InterfacePage.setTabOrder(self.findReplaceCheckBox, self.findLocationCheckBox)
        InterfacePage.setTabOrder(self.findLocationCheckBox, self.templateViewerCheckBox)
        InterfacePage.setTabOrder(self.templateViewerCheckBox, self.fileBrowserCheckBox)
        InterfacePage.setTabOrder(self.fileBrowserCheckBox, self.symbolsCheckBox)
        InterfacePage.setTabOrder(self.symbolsCheckBox, self.codeDocumentationViewerCheckBox)
        InterfacePage.setTabOrder(self.codeDocumentationViewerCheckBox, self.helpViewerCheckBox)
        InterfacePage.setTabOrder(self.helpViewerCheckBox, self.condaCheckBox)
        InterfacePage.setTabOrder(self.condaCheckBox, self.pypiCheckBox)
        InterfacePage.setTabOrder(self.pypiCheckBox, self.cooperationCheckBox)
        InterfacePage.setTabOrder(self.cooperationCheckBox, self.ircCheckBox)
        InterfacePage.setTabOrder(self.ircCheckBox, self.microPythonCheckBox)
        InterfacePage.setTabOrder(self.microPythonCheckBox, self.numbersCheckBox)
        InterfacePage.setTabOrder(self.numbersCheckBox, self.resetLayoutButton)

    def retranslateUi(self, InterfacePage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("InterfacePage", "<b>Configure User Interface</b>"))
        self.groupBox_4.setTitle(_translate("InterfacePage", "Browsers"))
        self.uiBrowsersListFoldersFirstCheckBox.setToolTip(_translate("InterfacePage", "Select, if folders should be listed first in the various browsers"))
        self.uiBrowsersListFoldersFirstCheckBox.setText(_translate("InterfacePage", "List folders first in Browsers"))
        self.uiBrowsersHideNonPublicCheckBox.setToolTip(_translate("InterfacePage", "Select to hide non public classes, methods and attributes in the browsers."))
        self.uiBrowsersHideNonPublicCheckBox.setText(_translate("InterfacePage", "Hide non public members in Browsers"))
        self.uiBrowsersSortByOccurrenceCheckBox.setToolTip(_translate("InterfacePage", "Select to sort file contents by occurrence"))
        self.uiBrowsersSortByOccurrenceCheckBox.setText(_translate("InterfacePage", "Sort contents by occurrence"))
        self.browserShowCodingCheckBox.setToolTip(_translate("InterfacePage", "Select to show the source code encoding"))
        self.browserShowCodingCheckBox.setText(_translate("InterfacePage", "Show source file encoding"))
        self.browserShowConnectedServerOnlyCheckBox.setToolTip(_translate("InterfacePage", "Select to show local entries and those related to the currently connected eric-ide server."))
        self.browserShowConnectedServerOnlyCheckBox.setText(_translate("InterfacePage", "Show entries of connected server only"))
        self.label_4.setText(_translate("InterfacePage", "Filter out files:"))
        self.fileFiltersEdit.setToolTip(_translate("InterfacePage", "Enter wildcard file patterns separated by semicolon. Files matching these patterns will not be shown by the file browsers."))
        self.uiCaptionShowsFilenameGroupBox.setToolTip(_translate("InterfacePage", "Select, if the caption of the main window should show the filename of the current editor"))
        self.uiCaptionShowsFilenameGroupBox.setTitle(_translate("InterfacePage", "Caption shows filename"))
        self.label.setText(_translate("InterfacePage", "Filename Length"))
        self.filenameLengthSpinBox.setToolTip(_translate("InterfacePage", "Enter the number of characters to be shown in the main window title."))
        self.groupBox.setTitle(_translate("InterfacePage", "Style"))
        self.label_2.setText(_translate("InterfacePage", "Style:"))
        self.styleComboBox.setToolTip(_translate("InterfacePage", "Select the interface style"))
        self.label_3.setText(_translate("InterfacePage", "Style Sheet:"))
        self.styleSheetPicker.setToolTip(_translate("InterfacePage", "Enter the path of the style sheet file"))
        self.label_6.setText(_translate("InterfacePage", "Style Icons Path:"))
        self.styleIconsPathPicker.setToolTip(_translate("InterfacePage", "Enter the path to the icons used within the style sheet (empty for default)"))
        self.label_7.setText(_translate("InterfacePage", "Item Selection Style:"))
        self.itemSelectionStyleComboBox.setToolTip(_translate("InterfacePage", "Select the style for item selection (default is platform dependent)."))
        self.label_8.setText(_translate("InterfacePage", "<b>Note:</b> This may not take effect on all views."))
        self.groupBox_8.setTitle(_translate("InterfacePage", "Sidebars"))
        self.iconBarButton.setToolTip(_translate("InterfacePage", "Select the icon bar background color"))
        self.iconBarButton.setText(_translate("InterfacePage", "Icon Bar Color"))
        self.label_5.setText(_translate("InterfacePage", "Icon Size:"))
        self.iconSizeComboBox.setToolTip(_translate("InterfacePage", "Select the icon size"))
        self.TextLabel1_2_2_3.setText(_translate("InterfacePage", "<font color=\"#FF0000\"><b>Note:</b> The following setting will be activated at the next startup of the application.</font>"))
        self.combinedLeftRightSidebarCheckBox.setToolTip(_translate("InterfacePage", "Select to combine the left and right sidebar"))
        self.combinedLeftRightSidebarCheckBox.setText(_translate("InterfacePage", "Combine left and right sidebar"))
        self.TextLabel1_2_2_2.setText(_translate("InterfacePage", "<font color=\"#FF0000\"><b>Note:</b> All settings below are activated at the next startup of the application.</font>"))
        self.layoutComboBox.setToolTip(_translate("InterfacePage", "Select the layout type."))
        self.layoutComboBox.setItemText(0, _translate("InterfacePage", "Sidebars"))
        self.layoutComboBox.setItemText(1, _translate("InterfacePage", "Toolboxes"))
        self.languageComboBox.setToolTip(_translate("InterfacePage", "Select the interface language."))
        self.languageComboBox.setWhatsThis(_translate("InterfacePage", "The interface language can be selected from this list. If \"system\" is selected, the interface language is determined by the system. The selection of \"none\" means, that the default language will be used."))
        self.languageLabel.setText(_translate("InterfacePage", "Language:"))
        self.layoutLabel.setText(_translate("InterfacePage", "Layout:"))
        self.groupBox_3.setTitle(_translate("InterfacePage", "Integrated Tools Activation"))
        self.groupBox_10.setTitle(_translate("InterfacePage", "Left Side"))
        self.symbolsCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the Symbols widget"))
        self.symbolsCheckBox.setText(_translate("InterfacePage", "Symbols"))
        self.templateViewerCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the Template viewer"))
        self.templateViewerCheckBox.setText(_translate("InterfacePage", "Template-Viewer"))
        self.fileBrowserCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the File-Browser widget"))
        self.fileBrowserCheckBox.setText(_translate("InterfacePage", "File-Browser"))
        self.findReplaceCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the embedded Find/Replace In Files tool."))
        self.findReplaceCheckBox.setText(_translate("InterfacePage", "Find/Replace In Files"))
        self.findLocationCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the embedded Find File tool."))
        self.findLocationCheckBox.setText(_translate("InterfacePage", "Find File"))
        self.leftRightGroupBox.setTitle(_translate("InterfacePage", "Right Side"))
        self.codeDocumentationViewerCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the Code Documentation Viewer"))
        self.codeDocumentationViewerCheckBox.setText(_translate("InterfacePage", "Code Documentation Viewer"))
        self.helpViewerCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the Help Viewer widget"))
        self.helpViewerCheckBox.setText(_translate("InterfacePage", "Help Viewer"))
        self.condaCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the conda package manager widget"))
        self.condaCheckBox.setText(_translate("InterfacePage", "Conda Package Manager"))
        self.pypiCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the PyPI package manager widget"))
        self.pypiCheckBox.setText(_translate("InterfacePage", "PyPI Package Manager"))
        self.cooperationCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the Cooperation widget"))
        self.cooperationCheckBox.setText(_translate("InterfacePage", "Cooperation"))
        self.ircCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the IRC widget"))
        self.ircCheckBox.setText(_translate("InterfacePage", "IRC"))
        self.microPythonCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the MicroPython widget"))
        self.microPythonCheckBox.setText(_translate("InterfacePage", "MicroPython"))
        self.groupBox_11.setTitle(_translate("InterfacePage", "Bottom Side"))
        self.numbersCheckBox.setToolTip(_translate("InterfacePage", "Select to activate the Numbers widget"))
        self.numbersCheckBox.setText(_translate("InterfacePage", "Numbers"))
        self.resetLayoutButton.setText(_translate("InterfacePage", "Reset layout to factory defaults"))
from eric7.EricWidgets.EricPathPicker import EricPathPicker
