# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/WebBrowserAppearancePage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_WebBrowserAppearancePage(object):
    def setupUi(self, WebBrowserAppearancePage):
        WebBrowserAppearancePage.setObjectName("WebBrowserAppearancePage")
        WebBrowserAppearancePage.resize(499, 1049)
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(WebBrowserAppearancePage)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.headerLabel = QtWidgets.QLabel(parent=WebBrowserAppearancePage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout_6.addWidget(self.headerLabel)
        self.line17 = QtWidgets.QFrame(parent=WebBrowserAppearancePage)
        self.line17.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line17.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line17.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line17.setObjectName("line17")
        self.verticalLayout_6.addWidget(self.line17)
        self.groupBox_4 = QtWidgets.QGroupBox(parent=WebBrowserAppearancePage)
        self.groupBox_4.setObjectName("groupBox_4")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox_4)
        self.gridLayout.setObjectName("gridLayout")
        self.label_5 = QtWidgets.QLabel(parent=self.groupBox_4)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 3, 0, 1, 1)
        self.cursiveFontCombo = QtWidgets.QFontComboBox(parent=self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cursiveFontCombo.sizePolicy().hasHeightForWidth())
        self.cursiveFontCombo.setSizePolicy(sizePolicy)
        self.cursiveFontCombo.setObjectName("cursiveFontCombo")
        self.gridLayout.addWidget(self.cursiveFontCombo, 4, 1, 1, 1)
        self.fantasyFontCombo = QtWidgets.QFontComboBox(parent=self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fantasyFontCombo.sizePolicy().hasHeightForWidth())
        self.fantasyFontCombo.setSizePolicy(sizePolicy)
        self.fantasyFontCombo.setObjectName("fantasyFontCombo")
        self.gridLayout.addWidget(self.fantasyFontCombo, 5, 1, 1, 1)
        self.fixedFontCombo = QtWidgets.QFontComboBox(parent=self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.fixedFontCombo.sizePolicy().hasHeightForWidth())
        self.fixedFontCombo.setSizePolicy(sizePolicy)
        self.fixedFontCombo.setFontFilters(QtWidgets.QFontComboBox.FontFilter.MonospacedFonts)
        self.fixedFontCombo.setObjectName("fixedFontCombo")
        self.gridLayout.addWidget(self.fixedFontCombo, 1, 1, 1, 1)
        self.serifFontCombo = QtWidgets.QFontComboBox(parent=self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.serifFontCombo.sizePolicy().hasHeightForWidth())
        self.serifFontCombo.setSizePolicy(sizePolicy)
        self.serifFontCombo.setObjectName("serifFontCombo")
        self.gridLayout.addWidget(self.serifFontCombo, 2, 1, 1, 1)
        self.sansSerifFontCombo = QtWidgets.QFontComboBox(parent=self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sansSerifFontCombo.sizePolicy().hasHeightForWidth())
        self.sansSerifFontCombo.setSizePolicy(sizePolicy)
        self.sansSerifFontCombo.setObjectName("sansSerifFontCombo")
        self.gridLayout.addWidget(self.sansSerifFontCombo, 3, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=self.groupBox_4)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=self.groupBox_4)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.label_6 = QtWidgets.QLabel(parent=self.groupBox_4)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 4, 0, 1, 1)
        self.label_4 = QtWidgets.QLabel(parent=self.groupBox_4)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 2, 0, 1, 1)
        self.standardFontCombo = QtWidgets.QFontComboBox(parent=self.groupBox_4)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.standardFontCombo.sizePolicy().hasHeightForWidth())
        self.standardFontCombo.setSizePolicy(sizePolicy)
        self.standardFontCombo.setObjectName("standardFontCombo")
        self.gridLayout.addWidget(self.standardFontCombo, 0, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(parent=self.groupBox_4)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 5, 0, 1, 1)
        self.verticalLayout_6.addWidget(self.groupBox_4)
        self.groupBox_6 = QtWidgets.QGroupBox(parent=WebBrowserAppearancePage)
        self.groupBox_6.setObjectName("groupBox_6")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.groupBox_6)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.label_8 = QtWidgets.QLabel(parent=self.groupBox_6)
        self.label_8.setObjectName("label_8")
        self.gridLayout_4.addWidget(self.label_8, 0, 0, 1, 1)
        self.defaultSizeSpinBox = QtWidgets.QSpinBox(parent=self.groupBox_6)
        self.defaultSizeSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.defaultSizeSpinBox.setMinimum(1)
        self.defaultSizeSpinBox.setObjectName("defaultSizeSpinBox")
        self.gridLayout_4.addWidget(self.defaultSizeSpinBox, 0, 1, 1, 1)
        self.label_9 = QtWidgets.QLabel(parent=self.groupBox_6)
        self.label_9.setObjectName("label_9")
        self.gridLayout_4.addWidget(self.label_9, 1, 0, 1, 1)
        self.fixedSizeSpinBox = QtWidgets.QSpinBox(parent=self.groupBox_6)
        self.fixedSizeSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.fixedSizeSpinBox.setMinimum(1)
        self.fixedSizeSpinBox.setObjectName("fixedSizeSpinBox")
        self.gridLayout_4.addWidget(self.fixedSizeSpinBox, 1, 1, 1, 1)
        self.label_10 = QtWidgets.QLabel(parent=self.groupBox_6)
        self.label_10.setObjectName("label_10")
        self.gridLayout_4.addWidget(self.label_10, 2, 0, 1, 1)
        self.minSizeSpinBox = QtWidgets.QSpinBox(parent=self.groupBox_6)
        self.minSizeSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.minSizeSpinBox.setMinimum(1)
        self.minSizeSpinBox.setObjectName("minSizeSpinBox")
        self.gridLayout_4.addWidget(self.minSizeSpinBox, 2, 1, 1, 1)
        self.label_11 = QtWidgets.QLabel(parent=self.groupBox_6)
        self.label_11.setObjectName("label_11")
        self.gridLayout_4.addWidget(self.label_11, 3, 0, 1, 1)
        self.minLogicalSizeSpinBox = QtWidgets.QSpinBox(parent=self.groupBox_6)
        self.minLogicalSizeSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.minLogicalSizeSpinBox.setMinimum(1)
        self.minLogicalSizeSpinBox.setObjectName("minLogicalSizeSpinBox")
        self.gridLayout_4.addWidget(self.minLogicalSizeSpinBox, 3, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(230, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_4.addItem(spacerItem, 3, 2, 1, 1)
        self.verticalLayout_6.addWidget(self.groupBox_6)
        self.groupBox_3 = QtWidgets.QGroupBox(parent=WebBrowserAppearancePage)
        self.groupBox_3.setObjectName("groupBox_3")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.groupBox_3)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.groupBox_8 = QtWidgets.QGroupBox(parent=self.groupBox_3)
        self.groupBox_8.setObjectName("groupBox_8")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_8)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.textLabel1_3 = QtWidgets.QLabel(parent=self.groupBox_8)
        self.textLabel1_3.setObjectName("textLabel1_3")
        self.gridLayout_2.addWidget(self.textLabel1_3, 0, 0, 1, 1)
        self.secureURLsColourButton = QtWidgets.QPushButton(parent=self.groupBox_8)
        self.secureURLsColourButton.setMinimumSize(QtCore.QSize(100, 0))
        self.secureURLsColourButton.setText("")
        self.secureURLsColourButton.setObjectName("secureURLsColourButton")
        self.gridLayout_2.addWidget(self.secureURLsColourButton, 0, 1, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(223, 17, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 0, 2, 1, 1)
        self.textLabel1_4 = QtWidgets.QLabel(parent=self.groupBox_8)
        self.textLabel1_4.setObjectName("textLabel1_4")
        self.gridLayout_2.addWidget(self.textLabel1_4, 1, 0, 1, 1)
        self.insecureURLsColourButton = QtWidgets.QPushButton(parent=self.groupBox_8)
        self.insecureURLsColourButton.setMinimumSize(QtCore.QSize(100, 0))
        self.insecureURLsColourButton.setText("")
        self.insecureURLsColourButton.setObjectName("insecureURLsColourButton")
        self.gridLayout_2.addWidget(self.insecureURLsColourButton, 1, 1, 1, 1)
        self.textLabel1_5 = QtWidgets.QLabel(parent=self.groupBox_8)
        self.textLabel1_5.setObjectName("textLabel1_5")
        self.gridLayout_2.addWidget(self.textLabel1_5, 2, 0, 1, 1)
        self.maliciousURLsColourButton = QtWidgets.QPushButton(parent=self.groupBox_8)
        self.maliciousURLsColourButton.setMinimumSize(QtCore.QSize(100, 0))
        self.maliciousURLsColourButton.setText("")
        self.maliciousURLsColourButton.setObjectName("maliciousURLsColourButton")
        self.gridLayout_2.addWidget(self.maliciousURLsColourButton, 2, 1, 1, 1)
        self.label_12 = QtWidgets.QLabel(parent=self.groupBox_8)
        self.label_12.setObjectName("label_12")
        self.gridLayout_2.addWidget(self.label_12, 3, 0, 1, 1)
        self.privateModeURLsColourButton = QtWidgets.QPushButton(parent=self.groupBox_8)
        self.privateModeURLsColourButton.setMinimumSize(QtCore.QSize(100, 0))
        self.privateModeURLsColourButton.setText("")
        self.privateModeURLsColourButton.setObjectName("privateModeURLsColourButton")
        self.gridLayout_2.addWidget(self.privateModeURLsColourButton, 3, 1, 1, 1)
        self.verticalLayout_5.addWidget(self.groupBox_8)
        self.verticalLayout_6.addWidget(self.groupBox_3)
        self.groupBox = QtWidgets.QGroupBox(parent=WebBrowserAppearancePage)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.autoLoadImagesCheckBox = QtWidgets.QCheckBox(parent=self.groupBox)
        self.autoLoadImagesCheckBox.setObjectName("autoLoadImagesCheckBox")
        self.verticalLayout.addWidget(self.autoLoadImagesCheckBox)
        self.verticalLayout_6.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(parent=WebBrowserAppearancePage)
        self.groupBox_2.setObjectName("groupBox_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(parent=self.groupBox_2)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.styleSheetPicker = EricPathPicker(parent=self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.styleSheetPicker.sizePolicy().hasHeightForWidth())
        self.styleSheetPicker.setSizePolicy(sizePolicy)
        self.styleSheetPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.styleSheetPicker.setObjectName("styleSheetPicker")
        self.horizontalLayout.addWidget(self.styleSheetPicker)
        self.verticalLayout_6.addWidget(self.groupBox_2)
        self.tabsGroupBox = QtWidgets.QGroupBox(parent=WebBrowserAppearancePage)
        self.tabsGroupBox.setObjectName("tabsGroupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.tabsGroupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.warnOnMultipleCloseCheckBox = QtWidgets.QCheckBox(parent=self.tabsGroupBox)
        self.warnOnMultipleCloseCheckBox.setObjectName("warnOnMultipleCloseCheckBox")
        self.verticalLayout_2.addWidget(self.warnOnMultipleCloseCheckBox)
        self.verticalLayout_6.addWidget(self.tabsGroupBox)
        self.groupBox_7 = QtWidgets.QGroupBox(parent=WebBrowserAppearancePage)
        self.groupBox_7.setObjectName("groupBox_7")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBox_7)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.scrollbarsCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_7)
        self.scrollbarsCheckBox.setObjectName("scrollbarsCheckBox")
        self.verticalLayout_4.addWidget(self.scrollbarsCheckBox)
        self.verticalLayout_6.addWidget(self.groupBox_7)
        self.line9_2 = QtWidgets.QFrame(parent=WebBrowserAppearancePage)
        self.line9_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line9_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_2.setObjectName("line9_2")
        self.verticalLayout_6.addWidget(self.line9_2)
        self.TextLabel1_2_2_2 = QtWidgets.QLabel(parent=WebBrowserAppearancePage)
        self.TextLabel1_2_2_2.setObjectName("TextLabel1_2_2_2")
        self.verticalLayout_6.addWidget(self.TextLabel1_2_2_2)
        self.groupBox_5 = QtWidgets.QGroupBox(parent=WebBrowserAppearancePage)
        self.groupBox_5.setObjectName("groupBox_5")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.groupBox_5)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.toolbarsCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_5)
        self.toolbarsCheckBox.setObjectName("toolbarsCheckBox")
        self.verticalLayout_3.addWidget(self.toolbarsCheckBox)
        self.verticalLayout_6.addWidget(self.groupBox_5)

        self.retranslateUi(WebBrowserAppearancePage)
        QtCore.QMetaObject.connectSlotsByName(WebBrowserAppearancePage)
        WebBrowserAppearancePage.setTabOrder(self.standardFontCombo, self.fixedFontCombo)
        WebBrowserAppearancePage.setTabOrder(self.fixedFontCombo, self.serifFontCombo)
        WebBrowserAppearancePage.setTabOrder(self.serifFontCombo, self.sansSerifFontCombo)
        WebBrowserAppearancePage.setTabOrder(self.sansSerifFontCombo, self.cursiveFontCombo)
        WebBrowserAppearancePage.setTabOrder(self.cursiveFontCombo, self.fantasyFontCombo)
        WebBrowserAppearancePage.setTabOrder(self.fantasyFontCombo, self.defaultSizeSpinBox)
        WebBrowserAppearancePage.setTabOrder(self.defaultSizeSpinBox, self.fixedSizeSpinBox)
        WebBrowserAppearancePage.setTabOrder(self.fixedSizeSpinBox, self.minSizeSpinBox)
        WebBrowserAppearancePage.setTabOrder(self.minSizeSpinBox, self.minLogicalSizeSpinBox)
        WebBrowserAppearancePage.setTabOrder(self.minLogicalSizeSpinBox, self.secureURLsColourButton)
        WebBrowserAppearancePage.setTabOrder(self.secureURLsColourButton, self.insecureURLsColourButton)
        WebBrowserAppearancePage.setTabOrder(self.insecureURLsColourButton, self.maliciousURLsColourButton)
        WebBrowserAppearancePage.setTabOrder(self.maliciousURLsColourButton, self.privateModeURLsColourButton)
        WebBrowserAppearancePage.setTabOrder(self.privateModeURLsColourButton, self.autoLoadImagesCheckBox)
        WebBrowserAppearancePage.setTabOrder(self.autoLoadImagesCheckBox, self.styleSheetPicker)
        WebBrowserAppearancePage.setTabOrder(self.styleSheetPicker, self.warnOnMultipleCloseCheckBox)
        WebBrowserAppearancePage.setTabOrder(self.warnOnMultipleCloseCheckBox, self.scrollbarsCheckBox)
        WebBrowserAppearancePage.setTabOrder(self.scrollbarsCheckBox, self.toolbarsCheckBox)

    def retranslateUi(self, WebBrowserAppearancePage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("WebBrowserAppearancePage", "<b>Configure Web Browser appearance</b>"))
        self.groupBox_4.setTitle(_translate("WebBrowserAppearancePage", "Fonts"))
        self.label_5.setText(_translate("WebBrowserAppearancePage", "Sans Serif Font:"))
        self.cursiveFontCombo.setToolTip(_translate("WebBrowserAppearancePage", "Select the cursive font"))
        self.fantasyFontCombo.setToolTip(_translate("WebBrowserAppearancePage", "Select the fantasy font"))
        self.fixedFontCombo.setToolTip(_translate("WebBrowserAppearancePage", "Select the fixed width font"))
        self.serifFontCombo.setToolTip(_translate("WebBrowserAppearancePage", "Select the serif font"))
        self.sansSerifFontCombo.setToolTip(_translate("WebBrowserAppearancePage", "Select the sans serif font"))
        self.label_2.setText(_translate("WebBrowserAppearancePage", "Standard Font:"))
        self.label_3.setText(_translate("WebBrowserAppearancePage", "Fixed Width Font:"))
        self.label_6.setText(_translate("WebBrowserAppearancePage", "Cursive Font:"))
        self.label_4.setText(_translate("WebBrowserAppearancePage", "Serif Font:"))
        self.standardFontCombo.setToolTip(_translate("WebBrowserAppearancePage", "Select the standard font"))
        self.label_7.setText(_translate("WebBrowserAppearancePage", "Fantasy Font:"))
        self.groupBox_6.setTitle(_translate("WebBrowserAppearancePage", "Font Sizes"))
        self.label_8.setText(_translate("WebBrowserAppearancePage", "Default Font Size:"))
        self.label_9.setText(_translate("WebBrowserAppearancePage", "Fixed Font Size:"))
        self.label_10.setText(_translate("WebBrowserAppearancePage", "Minimum Font Size:"))
        self.label_11.setText(_translate("WebBrowserAppearancePage", "Minimum Logical Font Size:"))
        self.groupBox_3.setTitle(_translate("WebBrowserAppearancePage", "Colors"))
        self.groupBox_8.setTitle(_translate("WebBrowserAppearancePage", "URL Entry Background"))
        self.textLabel1_3.setText(_translate("WebBrowserAppearancePage", "Secure URLs:"))
        self.secureURLsColourButton.setToolTip(_translate("WebBrowserAppearancePage", "Select the background color for secure URLs."))
        self.textLabel1_4.setText(_translate("WebBrowserAppearancePage", "Insecure URLs:"))
        self.insecureURLsColourButton.setToolTip(_translate("WebBrowserAppearancePage", "Select the background color for insecure URLs."))
        self.textLabel1_5.setText(_translate("WebBrowserAppearancePage", "Malicious URLs:"))
        self.maliciousURLsColourButton.setToolTip(_translate("WebBrowserAppearancePage", "Select the background color for malicious URLs."))
        self.label_12.setText(_translate("WebBrowserAppearancePage", "Private Mode:"))
        self.privateModeURLsColourButton.setToolTip(_translate("WebBrowserAppearancePage", "Select the background color for URLs in private mode."))
        self.groupBox.setTitle(_translate("WebBrowserAppearancePage", "Images"))
        self.autoLoadImagesCheckBox.setToolTip(_translate("WebBrowserAppearancePage", "Select to load images"))
        self.autoLoadImagesCheckBox.setText(_translate("WebBrowserAppearancePage", "Load images"))
        self.groupBox_2.setTitle(_translate("WebBrowserAppearancePage", "Style Sheet"))
        self.label.setText(_translate("WebBrowserAppearancePage", "User Style Sheet:"))
        self.styleSheetPicker.setToolTip(_translate("WebBrowserAppearancePage", "Enter the file name of a user style sheet"))
        self.tabsGroupBox.setTitle(_translate("WebBrowserAppearancePage", "Tabs"))
        self.warnOnMultipleCloseCheckBox.setToolTip(_translate("WebBrowserAppearancePage", "Select to issue a warning, if multiple tabs are about to be closed"))
        self.warnOnMultipleCloseCheckBox.setText(_translate("WebBrowserAppearancePage", "Warn, if multiple tabs are about to be closed"))
        self.groupBox_7.setTitle(_translate("WebBrowserAppearancePage", "Scrollbars"))
        self.scrollbarsCheckBox.setToolTip(_translate("WebBrowserAppearancePage", "Select to show scrollbars. Note: Scrolling is possible even without them."))
        self.scrollbarsCheckBox.setText(_translate("WebBrowserAppearancePage", "Show Scrollbars"))
        self.TextLabel1_2_2_2.setText(_translate("WebBrowserAppearancePage", "<font color=\"#FF0000\"><b>Note:</b> All settings below are activated at the next startup of the application.</font>"))
        self.groupBox_5.setTitle(_translate("WebBrowserAppearancePage", "Toolbars"))
        self.toolbarsCheckBox.setToolTip(_translate("WebBrowserAppearancePage", "Select to show toolbars"))
        self.toolbarsCheckBox.setText(_translate("WebBrowserAppearancePage", "Show Toolbars"))
from eric7.EricWidgets.EricPathPicker import EricPathPicker
