# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/DebuggerPython3Page.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_DebuggerPython3Page(object):
    def setupUi(self, DebuggerPython3Page):
        DebuggerPython3Page.setObjectName("DebuggerPython3Page")
        DebuggerPython3Page.resize(455, 682)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(DebuggerPython3Page)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.headerLabel = QtWidgets.QLabel(parent=DebuggerPython3Page)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout_3.addWidget(self.headerLabel)
        self.line11_2 = QtWidgets.QFrame(parent=DebuggerPython3Page)
        self.line11_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line11_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line11_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line11_2.setObjectName("line11_2")
        self.verticalLayout_3.addWidget(self.line11_2)
        self.groupBox_4 = QtWidgets.QGroupBox(parent=DebuggerPython3Page)
        self.groupBox_4.setObjectName("groupBox_4")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.groupBox_4)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.venvComboBox = QtWidgets.QComboBox(parent=self.groupBox_4)
        self.venvComboBox.setObjectName("venvComboBox")
        self.horizontalLayout_2.addWidget(self.venvComboBox)
        self.venvDlgButton = QtWidgets.QToolButton(parent=self.groupBox_4)
        self.venvDlgButton.setText("")
        self.venvDlgButton.setObjectName("venvDlgButton")
        self.horizontalLayout_2.addWidget(self.venvDlgButton)
        self.venvRefreshButton = QtWidgets.QToolButton(parent=self.groupBox_4)
        self.venvRefreshButton.setText("")
        self.venvRefreshButton.setObjectName("venvRefreshButton")
        self.horizontalLayout_2.addWidget(self.venvRefreshButton)
        self.verticalLayout_3.addWidget(self.groupBox_4)
        self.groupBox_2 = QtWidgets.QGroupBox(parent=DebuggerPython3Page)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout.setObjectName("gridLayout")
        self.debugClientPicker = EricPathPicker(parent=self.groupBox_2)
        self.debugClientPicker.setEnabled(False)
        self.debugClientPicker.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.debugClientPicker.setObjectName("debugClientPicker")
        self.gridLayout.addWidget(self.debugClientPicker, 1, 0, 1, 2)
        self.standardButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.standardButton.setObjectName("standardButton")
        self.gridLayout.addWidget(self.standardButton, 0, 0, 1, 1)
        self.customButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.customButton.setObjectName("customButton")
        self.gridLayout.addWidget(self.customButton, 0, 1, 1, 1)
        self.verticalLayout_3.addWidget(self.groupBox_2)
        self.groupBox_3 = QtWidgets.QGroupBox(parent=DebuggerPython3Page)
        self.groupBox_3.setObjectName("groupBox_3")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox_3)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.sourceExtensionsEdit = QtWidgets.QLineEdit(parent=self.groupBox_3)
        self.sourceExtensionsEdit.setReadOnly(True)
        self.sourceExtensionsEdit.setObjectName("sourceExtensionsEdit")
        self.verticalLayout.addWidget(self.sourceExtensionsEdit)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.refreshButton = QtWidgets.QPushButton(parent=self.groupBox_3)
        self.refreshButton.setObjectName("refreshButton")
        self.horizontalLayout.addWidget(self.refreshButton)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout_3.addWidget(self.groupBox_3)
        self.pyRedirectCheckBox = QtWidgets.QCheckBox(parent=DebuggerPython3Page)
        self.pyRedirectCheckBox.setObjectName("pyRedirectCheckBox")
        self.verticalLayout_3.addWidget(self.pyRedirectCheckBox)
        self.pyNoEncodingCheckBox = QtWidgets.QCheckBox(parent=DebuggerPython3Page)
        self.pyNoEncodingCheckBox.setObjectName("pyNoEncodingCheckBox")
        self.verticalLayout_3.addWidget(self.pyNoEncodingCheckBox)
        self.callTraceGroupBox = QtWidgets.QGroupBox(parent=DebuggerPython3Page)
        self.callTraceGroupBox.setCheckable(False)
        self.callTraceGroupBox.setObjectName("callTraceGroupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.callTraceGroupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.callTraceCheckBox = QtWidgets.QCheckBox(parent=self.callTraceGroupBox)
        self.callTraceCheckBox.setObjectName("callTraceCheckBox")
        self.verticalLayout_2.addWidget(self.callTraceCheckBox)
        self.label_2 = QtWidgets.QLabel(parent=self.callTraceGroupBox)
        self.label_2.setWordWrap(True)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.verticalLayout_3.addWidget(self.callTraceGroupBox)
        spacerItem2 = QtWidgets.QSpacerItem(435, 21, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_3.addItem(spacerItem2)

        self.retranslateUi(DebuggerPython3Page)
        self.customButton.toggled['bool'].connect(self.debugClientPicker.setEnabled) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(DebuggerPython3Page)
        DebuggerPython3Page.setTabOrder(self.venvComboBox, self.venvDlgButton)
        DebuggerPython3Page.setTabOrder(self.venvDlgButton, self.venvRefreshButton)
        DebuggerPython3Page.setTabOrder(self.venvRefreshButton, self.standardButton)
        DebuggerPython3Page.setTabOrder(self.standardButton, self.customButton)
        DebuggerPython3Page.setTabOrder(self.customButton, self.debugClientPicker)
        DebuggerPython3Page.setTabOrder(self.debugClientPicker, self.sourceExtensionsEdit)
        DebuggerPython3Page.setTabOrder(self.sourceExtensionsEdit, self.refreshButton)
        DebuggerPython3Page.setTabOrder(self.refreshButton, self.pyRedirectCheckBox)
        DebuggerPython3Page.setTabOrder(self.pyRedirectCheckBox, self.pyNoEncodingCheckBox)

    def retranslateUi(self, DebuggerPython3Page):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("DebuggerPython3Page", "<b>Configure Python3 Debugger</b>"))
        self.groupBox_4.setTitle(_translate("DebuggerPython3Page", "Python3 Virtual Environment"))
        self.venvComboBox.setToolTip(_translate("DebuggerPython3Page", "Select the virtual environment to be used"))
        self.venvDlgButton.setToolTip(_translate("DebuggerPython3Page", "Press to open the virtual environment manager dialog"))
        self.venvRefreshButton.setToolTip(_translate("DebuggerPython3Page", "Press to refresh the list of vitual environments"))
        self.groupBox_2.setTitle(_translate("DebuggerPython3Page", "Debug Client Type"))
        self.debugClientPicker.setToolTip(_translate("DebuggerPython3Page", "Enter the path of the Debug Client to be used.  Leave empty to use the default."))
        self.standardButton.setToolTip(_translate("DebuggerPython3Page", "Select the standard debug client"))
        self.standardButton.setText(_translate("DebuggerPython3Page", "Standard"))
        self.customButton.setToolTip(_translate("DebuggerPython3Page", "Select the custom selected debug client"))
        self.customButton.setText(_translate("DebuggerPython3Page", "Custom"))
        self.groupBox_3.setTitle(_translate("DebuggerPython3Page", "Source association"))
        self.label.setText(_translate("DebuggerPython3Page", "Please configure the associated file extensions on the \'Python\' page."))
        self.refreshButton.setToolTip(_translate("DebuggerPython3Page", "Press to update the display of the source associations"))
        self.refreshButton.setText(_translate("DebuggerPython3Page", "Refresh"))
        self.pyRedirectCheckBox.setToolTip(_translate("DebuggerPython3Page", "Select, to redirect stdin, stdout and stderr of the program being debugged to the eric IDE"))
        self.pyRedirectCheckBox.setText(_translate("DebuggerPython3Page", "Redirect stdin/stdout/stderr"))
        self.pyNoEncodingCheckBox.setToolTip(_translate("DebuggerPython3Page", "Select to not set the debug client encoding"))
        self.pyNoEncodingCheckBox.setText(_translate("DebuggerPython3Page", "Don\'t set the encoding of the debug client"))
        self.callTraceGroupBox.setTitle(_translate("DebuggerPython3Page", "Call Trace Optimization"))
        self.callTraceCheckBox.setToolTip(_translate("DebuggerPython3Page", "Select to enable the call trace speed optimization."))
        self.callTraceCheckBox.setText(_translate("DebuggerPython3Page", "Enable Call Trace Speed Optimization"))
        self.label_2.setText(_translate("DebuggerPython3Page", "This option improves the speed of call tracing by tracing into functions and methods containing a breakpoint only. Please note that functions and methods must not be defined on the very first line of a module for this option to work."))
from eric7.EricWidgets.EricPathPicker import EricPathPicker
