# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/ShellPage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_ShellPage(object):
    def setupUi(self, ShellPage):
        ShellPage.setObjectName("ShellPage")
        ShellPage.resize(573, 677)
        self.verticalLayout = QtWidgets.QVBoxLayout(ShellPage)
        self.verticalLayout.setObjectName("verticalLayout")
        self.headerLabel = QtWidgets.QLabel(parent=ShellPage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout.addWidget(self.headerLabel)
        self.line14 = QtWidgets.QFrame(parent=ShellPage)
        self.line14.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line14.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line14.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line14.setObjectName("line14")
        self.verticalLayout.addWidget(self.line14)
        self.gridlayout = QtWidgets.QGridLayout()
        self.gridlayout.setObjectName("gridlayout")
        self.shellLinenoCheckBox = QtWidgets.QCheckBox(parent=ShellPage)
        self.shellLinenoCheckBox.setObjectName("shellLinenoCheckBox")
        self.gridlayout.addWidget(self.shellLinenoCheckBox, 0, 0, 1, 1)
        self.shellCTEnabledCheckBox = QtWidgets.QCheckBox(parent=ShellPage)
        self.shellCTEnabledCheckBox.setObjectName("shellCTEnabledCheckBox")
        self.gridlayout.addWidget(self.shellCTEnabledCheckBox, 1, 1, 1, 1)
        self.shellWordWrapCheckBox = QtWidgets.QCheckBox(parent=ShellPage)
        self.shellWordWrapCheckBox.setObjectName("shellWordWrapCheckBox")
        self.gridlayout.addWidget(self.shellWordWrapCheckBox, 0, 1, 1, 1)
        self.shellACEnabledCheckBox = QtWidgets.QCheckBox(parent=ShellPage)
        self.shellACEnabledCheckBox.setObjectName("shellACEnabledCheckBox")
        self.gridlayout.addWidget(self.shellACEnabledCheckBox, 1, 0, 1, 1)
        self.shellSyntaxHighlightingCheckBox = QtWidgets.QCheckBox(parent=ShellPage)
        self.shellSyntaxHighlightingCheckBox.setObjectName("shellSyntaxHighlightingCheckBox")
        self.gridlayout.addWidget(self.shellSyntaxHighlightingCheckBox, 2, 0, 1, 1)
        self.rememberCheckBox = QtWidgets.QCheckBox(parent=ShellPage)
        self.rememberCheckBox.setObjectName("rememberCheckBox")
        self.gridlayout.addWidget(self.rememberCheckBox, 2, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridlayout)
        self.groupBox = QtWidgets.QGroupBox(parent=ShellPage)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.textLabel1_20 = QtWidgets.QLabel(parent=self.groupBox)
        self.textLabel1_20.setObjectName("textLabel1_20")
        self.gridLayout.addWidget(self.textLabel1_20, 0, 0, 1, 1)
        self.shellHistorySpinBox = QtWidgets.QSpinBox(parent=self.groupBox)
        self.shellHistorySpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.shellHistorySpinBox.setAccelerated(True)
        self.shellHistorySpinBox.setMinimum(10)
        self.shellHistorySpinBox.setMaximum(1000)
        self.shellHistorySpinBox.setSingleStep(10)
        self.shellHistorySpinBox.setProperty("value", 100)
        self.shellHistorySpinBox.setObjectName("shellHistorySpinBox")
        self.gridLayout.addWidget(self.shellHistorySpinBox, 0, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(343, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout.addItem(spacerItem, 0, 2, 1, 1)
        self.label = QtWidgets.QLabel(parent=self.groupBox)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.shellHistoryStyleComboBox = QtWidgets.QComboBox(parent=self.groupBox)
        self.shellHistoryStyleComboBox.setObjectName("shellHistoryStyleComboBox")
        self.gridLayout.addWidget(self.shellHistoryStyleComboBox, 1, 1, 1, 2)
        self.shellHistoryWrapCheckBox = QtWidgets.QCheckBox(parent=self.groupBox)
        self.shellHistoryWrapCheckBox.setObjectName("shellHistoryWrapCheckBox")
        self.gridLayout.addWidget(self.shellHistoryWrapCheckBox, 2, 0, 1, 3)
        self.shellHistoryCursorKeysCheckBox = QtWidgets.QCheckBox(parent=self.groupBox)
        self.shellHistoryCursorKeysCheckBox.setObjectName("shellHistoryCursorKeysCheckBox")
        self.gridLayout.addWidget(self.shellHistoryCursorKeysCheckBox, 3, 0, 1, 3)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_5 = QtWidgets.QGroupBox(parent=ShellPage)
        self.groupBox_5.setObjectName("groupBox_5")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_5)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.monospacedFontButton = QtWidgets.QPushButton(parent=self.groupBox_5)
        self.monospacedFontButton.setObjectName("monospacedFontButton")
        self.gridLayout_2.addWidget(self.monospacedFontButton, 0, 0, 1, 1)
        self.monospacedFontSample = QtWidgets.QLineEdit(parent=self.groupBox_5)
        self.monospacedFontSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.monospacedFontSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.monospacedFontSample.setReadOnly(True)
        self.monospacedFontSample.setObjectName("monospacedFontSample")
        self.gridLayout_2.addWidget(self.monospacedFontSample, 0, 1, 1, 1)
        self.monospacedCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_5)
        self.monospacedCheckBox.setObjectName("monospacedCheckBox")
        self.gridLayout_2.addWidget(self.monospacedCheckBox, 0, 2, 1, 1)
        self.linenumbersFontButton = QtWidgets.QPushButton(parent=self.groupBox_5)
        self.linenumbersFontButton.setObjectName("linenumbersFontButton")
        self.gridLayout_2.addWidget(self.linenumbersFontButton, 1, 0, 1, 1)
        self.marginsFontSample = QtWidgets.QLineEdit(parent=self.groupBox_5)
        self.marginsFontSample.setMinimumSize(QtCore.QSize(200, 0))
        self.marginsFontSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.marginsFontSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.marginsFontSample.setReadOnly(True)
        self.marginsFontSample.setObjectName("marginsFontSample")
        self.gridLayout_2.addWidget(self.marginsFontSample, 1, 1, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_5)
        self.groupBox_2 = QtWidgets.QGroupBox(parent=ShellPage)
        self.groupBox_2.setObjectName("groupBox_2")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.groupBox_2)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtWidgets.QLabel(parent=self.groupBox_2)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.timeoutSpinBox = QtWidgets.QSpinBox(parent=self.groupBox_2)
        self.timeoutSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.timeoutSpinBox.setAccelerated(True)
        self.timeoutSpinBox.setMinimum(5)
        self.timeoutSpinBox.setMaximum(600)
        self.timeoutSpinBox.setObjectName("timeoutSpinBox")
        self.horizontalLayout.addWidget(self.timeoutSpinBox)
        spacerItem1 = QtWidgets.QSpacerItem(289, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.stdOutErrCheckBox = QtWidgets.QCheckBox(parent=ShellPage)
        self.stdOutErrCheckBox.setObjectName("stdOutErrCheckBox")
        self.verticalLayout.addWidget(self.stdOutErrCheckBox)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(spacerItem2)

        self.retranslateUi(ShellPage)
        self.shellSyntaxHighlightingCheckBox.toggled['bool'].connect(self.monospacedFontButton.setDisabled) # type: ignore
        self.shellSyntaxHighlightingCheckBox.toggled['bool'].connect(self.monospacedFontSample.setDisabled) # type: ignore
        self.shellSyntaxHighlightingCheckBox.toggled['bool'].connect(self.monospacedCheckBox.setDisabled) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(ShellPage)
        ShellPage.setTabOrder(self.shellLinenoCheckBox, self.shellWordWrapCheckBox)
        ShellPage.setTabOrder(self.shellWordWrapCheckBox, self.shellACEnabledCheckBox)
        ShellPage.setTabOrder(self.shellACEnabledCheckBox, self.shellCTEnabledCheckBox)
        ShellPage.setTabOrder(self.shellCTEnabledCheckBox, self.shellSyntaxHighlightingCheckBox)
        ShellPage.setTabOrder(self.shellSyntaxHighlightingCheckBox, self.rememberCheckBox)
        ShellPage.setTabOrder(self.rememberCheckBox, self.shellHistorySpinBox)
        ShellPage.setTabOrder(self.shellHistorySpinBox, self.shellHistoryStyleComboBox)
        ShellPage.setTabOrder(self.shellHistoryStyleComboBox, self.shellHistoryWrapCheckBox)
        ShellPage.setTabOrder(self.shellHistoryWrapCheckBox, self.shellHistoryCursorKeysCheckBox)
        ShellPage.setTabOrder(self.shellHistoryCursorKeysCheckBox, self.monospacedFontButton)
        ShellPage.setTabOrder(self.monospacedFontButton, self.monospacedCheckBox)
        ShellPage.setTabOrder(self.monospacedCheckBox, self.linenumbersFontButton)
        ShellPage.setTabOrder(self.linenumbersFontButton, self.timeoutSpinBox)
        ShellPage.setTabOrder(self.timeoutSpinBox, self.stdOutErrCheckBox)

    def retranslateUi(self, ShellPage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("ShellPage", "<b>Configure Shell</b>"))
        self.shellLinenoCheckBox.setToolTip(_translate("ShellPage", "Select whether line numbers margin should be shown."))
        self.shellLinenoCheckBox.setText(_translate("ShellPage", "Show Line Numbers Margin"))
        self.shellCTEnabledCheckBox.setToolTip(_translate("ShellPage", "Select this to enable calltips"))
        self.shellCTEnabledCheckBox.setText(_translate("ShellPage", "Calltips Enabled"))
        self.shellWordWrapCheckBox.setToolTip(_translate("ShellPage", "Select to enable wrapping at word boundaries"))
        self.shellWordWrapCheckBox.setText(_translate("ShellPage", "Word Wrap Enabled"))
        self.shellACEnabledCheckBox.setToolTip(_translate("ShellPage", "Select this to enable autocompletion"))
        self.shellACEnabledCheckBox.setText(_translate("ShellPage", "Autocompletion Enabled"))
        self.shellSyntaxHighlightingCheckBox.setToolTip(_translate("ShellPage", "Select to enable syntax highlighting"))
        self.shellSyntaxHighlightingCheckBox.setText(_translate("ShellPage", "Syntax Highlighting Enabled"))
        self.rememberCheckBox.setToolTip(_translate("ShellPage", "Select to start with the most recently used virtual environment"))
        self.rememberCheckBox.setText(_translate("ShellPage", "Start with most recently used virtual environment"))
        self.groupBox.setTitle(_translate("ShellPage", "History"))
        self.textLabel1_20.setText(_translate("ShellPage", "max. History Entries:"))
        self.shellHistorySpinBox.setToolTip(_translate("ShellPage", "Enter the number of history entries allowed"))
        self.label.setText(_translate("ShellPage", "Navigation Style:"))
        self.shellHistoryStyleComboBox.setToolTip(_translate("ShellPage", "Select the history style"))
        self.shellHistoryWrapCheckBox.setToolTip(_translate("ShellPage", "Select to wrap around while navigating through the history"))
        self.shellHistoryWrapCheckBox.setText(_translate("ShellPage", "Wrap around while navigating"))
        self.shellHistoryCursorKeysCheckBox.setToolTip(_translate("ShellPage", "Select to make Up- and Down-keys move in history"))
        self.shellHistoryCursorKeysCheckBox.setWhatsThis(_translate("ShellPage", "<b>Up/Down keys navigate in history<b>\n"
"<p>Select this entry to make Up- and Down-keys navigate in history. If unselected history navigation may be performed by Ctrl-Up or Ctrl-Down.</p>"))
        self.shellHistoryCursorKeysCheckBox.setText(_translate("ShellPage", "Up/Down keys navigate in history"))
        self.groupBox_5.setTitle(_translate("ShellPage", "Font"))
        self.monospacedFontButton.setToolTip(_translate("ShellPage", "Press to select the font to be used as the monospaced font"))
        self.monospacedFontButton.setText(_translate("ShellPage", "Monospaced Font"))
        self.monospacedFontSample.setText(_translate("ShellPage", "Monospaced Text"))
        self.monospacedCheckBox.setToolTip(_translate("ShellPage", "Select, whether the monospaced font should be used as default"))
        self.monospacedCheckBox.setText(_translate("ShellPage", "Use monospaced as default"))
        self.linenumbersFontButton.setToolTip(_translate("ShellPage", "Press to select the font for the line numbers"))
        self.linenumbersFontButton.setText(_translate("ShellPage", "Line Numbers Font"))
        self.marginsFontSample.setText(_translate("ShellPage", "2345"))
        self.groupBox_2.setTitle(_translate("ShellPage", "Interpreter"))
        self.label_2.setText(_translate("ShellPage", "Statement Execution Timeout:"))
        self.timeoutSpinBox.setToolTip(_translate("ShellPage", "Enter the timeout in seconds after which the shell will not wait for the result of the current statement execution."))
        self.timeoutSpinBox.setSuffix(_translate("ShellPage", " s"))
        self.stdOutErrCheckBox.setToolTip(_translate("ShellPage", "Select to show debugger stdout and stderr"))
        self.stdOutErrCheckBox.setText(_translate("ShellPage", "Show stdout and stderr of debugger"))
