# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/ApplicationPage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_ApplicationPage(object):
    def setupUi(self, ApplicationPage):
        ApplicationPage.setObjectName("ApplicationPage")
        ApplicationPage.resize(589, 1119)
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(ApplicationPage)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.headerLabel = QtWidgets.QLabel(parent=ApplicationPage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout_5.addWidget(self.headerLabel)
        self.line9_3 = QtWidgets.QFrame(parent=ApplicationPage)
        self.line9_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_3.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line9_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_3.setObjectName("line9_3")
        self.verticalLayout_5.addWidget(self.line9_3)
        self.singleApplicationCheckBox = QtWidgets.QCheckBox(parent=ApplicationPage)
        self.singleApplicationCheckBox.setObjectName("singleApplicationCheckBox")
        self.verticalLayout_5.addWidget(self.singleApplicationCheckBox)
        self.splashScreenCheckBox = QtWidgets.QCheckBox(parent=ApplicationPage)
        self.splashScreenCheckBox.setObjectName("splashScreenCheckBox")
        self.verticalLayout_5.addWidget(self.splashScreenCheckBox)
        self.globalMenuCheckBox = QtWidgets.QCheckBox(parent=ApplicationPage)
        self.globalMenuCheckBox.setObjectName("globalMenuCheckBox")
        self.verticalLayout_5.addWidget(self.globalMenuCheckBox)
        self.groupBox_3 = QtWidgets.QGroupBox(parent=ApplicationPage)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridlayout = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridlayout.setObjectName("gridlayout")
        self.noOpenRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_3)
        self.noOpenRadioButton.setObjectName("noOpenRadioButton")
        self.gridlayout.addWidget(self.noOpenRadioButton, 0, 0, 1, 1)
        self.globalSessionRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_3)
        self.globalSessionRadioButton.setObjectName("globalSessionRadioButton")
        self.gridlayout.addWidget(self.globalSessionRadioButton, 2, 0, 1, 1)
        self.lastFileRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_3)
        self.lastFileRadioButton.setObjectName("lastFileRadioButton")
        self.gridlayout.addWidget(self.lastFileRadioButton, 0, 1, 1, 1)
        self.lastProjectRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_3)
        self.lastProjectRadioButton.setObjectName("lastProjectRadioButton")
        self.gridlayout.addWidget(self.lastProjectRadioButton, 1, 0, 1, 1)
        self.lastMultiprojectRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_3)
        self.lastMultiprojectRadioButton.setObjectName("lastMultiprojectRadioButton")
        self.gridlayout.addWidget(self.lastMultiprojectRadioButton, 1, 1, 1, 1)
        self.verticalLayout_5.addWidget(self.groupBox_3)
        self.groupBox_2 = QtWidgets.QGroupBox(parent=ApplicationPage)
        self.groupBox_2.setObjectName("groupBox_2")
        self.hboxlayout = QtWidgets.QHBoxLayout(self.groupBox_2)
        self.hboxlayout.setObjectName("hboxlayout")
        self.noCheckRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.noCheckRadioButton.setObjectName("noCheckRadioButton")
        self.hboxlayout.addWidget(self.noCheckRadioButton)
        self.alwaysCheckRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.alwaysCheckRadioButton.setObjectName("alwaysCheckRadioButton")
        self.hboxlayout.addWidget(self.alwaysCheckRadioButton)
        self.dailyCheckRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.dailyCheckRadioButton.setObjectName("dailyCheckRadioButton")
        self.hboxlayout.addWidget(self.dailyCheckRadioButton)
        self.weeklyCheckRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.weeklyCheckRadioButton.setObjectName("weeklyCheckRadioButton")
        self.hboxlayout.addWidget(self.weeklyCheckRadioButton)
        self.monthlyCheckRadioButton = QtWidgets.QRadioButton(parent=self.groupBox_2)
        self.monthlyCheckRadioButton.setObjectName("monthlyCheckRadioButton")
        self.hboxlayout.addWidget(self.monthlyCheckRadioButton)
        self.verticalLayout_5.addWidget(self.groupBox_2)
        self.groupBox_7 = QtWidgets.QGroupBox(parent=ApplicationPage)
        self.groupBox_7.setObjectName("groupBox_7")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.groupBox_7)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_3 = QtWidgets.QLabel(parent=self.groupBox_7)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_3.addWidget(self.label_3)
        self.upgraderDelaySpinBox = QtWidgets.QSpinBox(parent=self.groupBox_7)
        self.upgraderDelaySpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.upgraderDelaySpinBox.setMinimum(1)
        self.upgraderDelaySpinBox.setMaximum(30)
        self.upgraderDelaySpinBox.setObjectName("upgraderDelaySpinBox")
        self.horizontalLayout_3.addWidget(self.upgraderDelaySpinBox)
        spacerItem = QtWidgets.QSpacerItem(411, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.verticalLayout_5.addWidget(self.groupBox_7)
        self.crashSessionGroupBox = QtWidgets.QGroupBox(parent=ApplicationPage)
        self.crashSessionGroupBox.setObjectName("crashSessionGroupBox")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.crashSessionGroupBox)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.crashSessionEnabledCheckBox = QtWidgets.QCheckBox(parent=self.crashSessionGroupBox)
        self.crashSessionEnabledCheckBox.setObjectName("crashSessionEnabledCheckBox")
        self.verticalLayout_4.addWidget(self.crashSessionEnabledCheckBox)
        self.openCrashSessionCheckBox = QtWidgets.QCheckBox(parent=self.crashSessionGroupBox)
        self.openCrashSessionCheckBox.setEnabled(False)
        self.openCrashSessionCheckBox.setObjectName("openCrashSessionCheckBox")
        self.verticalLayout_4.addWidget(self.openCrashSessionCheckBox)
        self.deleteCrashSessionCheckBox = QtWidgets.QCheckBox(parent=self.crashSessionGroupBox)
        self.deleteCrashSessionCheckBox.setObjectName("deleteCrashSessionCheckBox")
        self.verticalLayout_4.addWidget(self.deleteCrashSessionCheckBox)
        self.verticalLayout_5.addWidget(self.crashSessionGroupBox)
        self.groupBox_4 = QtWidgets.QGroupBox(parent=ApplicationPage)
        self.groupBox_4.setObjectName("groupBox_4")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox_4)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.systemEmailClientCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_4)
        self.systemEmailClientCheckBox.setObjectName("systemEmailClientCheckBox")
        self.verticalLayout_2.addWidget(self.systemEmailClientCheckBox)
        self.verticalLayout_5.addWidget(self.groupBox_4)
        self.groupBox = QtWidgets.QGroupBox(parent=ApplicationPage)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName("verticalLayout")
        self.errorlogCheckBox = QtWidgets.QCheckBox(parent=self.groupBox)
        self.errorlogCheckBox.setObjectName("errorlogCheckBox")
        self.verticalLayout.addWidget(self.errorlogCheckBox)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.msgSeverityComboBox = QtWidgets.QComboBox(parent=self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.msgSeverityComboBox.sizePolicy().hasHeightForWidth())
        self.msgSeverityComboBox.setSizePolicy(sizePolicy)
        self.msgSeverityComboBox.setObjectName("msgSeverityComboBox")
        self.horizontalLayout_2.addWidget(self.msgSeverityComboBox)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout_5.addWidget(self.groupBox)
        self.groupBox_5 = QtWidgets.QGroupBox(parent=ApplicationPage)
        self.groupBox_5.setObjectName("groupBox_5")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox_5)
        self.gridLayout.setObjectName("gridLayout")
        self.intervalSpinBox = QtWidgets.QSpinBox(parent=self.groupBox_5)
        self.intervalSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.intervalSpinBox.setMaximum(2000)
        self.intervalSpinBox.setSingleStep(100)
        self.intervalSpinBox.setObjectName("intervalSpinBox")
        self.gridLayout.addWidget(self.intervalSpinBox, 0, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(453, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout.addItem(spacerItem1, 0, 1, 1, 1)
        self.verticalLayout_5.addWidget(self.groupBox_5)
        self.groupBox_6 = QtWidgets.QGroupBox(parent=ApplicationPage)
        self.groupBox_6.setObjectName("groupBox_6")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.groupBox_6)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.backgroundServicesLabel = QtWidgets.QLabel(parent=self.groupBox_6)
        self.backgroundServicesLabel.setText("")
        self.backgroundServicesLabel.setWordWrap(True)
        self.backgroundServicesLabel.setObjectName("backgroundServicesLabel")
        self.verticalLayout_3.addWidget(self.backgroundServicesLabel)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(parent=self.groupBox_6)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.backgroundServicesSpinBox = QtWidgets.QSpinBox(parent=self.groupBox_6)
        self.backgroundServicesSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.backgroundServicesSpinBox.setObjectName("backgroundServicesSpinBox")
        self.horizontalLayout.addWidget(self.backgroundServicesSpinBox)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem2)
        self.verticalLayout_3.addLayout(self.horizontalLayout)
        self.verticalLayout_5.addWidget(self.groupBox_6)
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_5.addItem(spacerItem3)

        self.retranslateUi(ApplicationPage)
        self.crashSessionEnabledCheckBox.toggled['bool'].connect(self.openCrashSessionCheckBox.setEnabled) # type: ignore
        self.crashSessionEnabledCheckBox.toggled['bool'].connect(self.openCrashSessionCheckBox.setChecked) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(ApplicationPage)
        ApplicationPage.setTabOrder(self.singleApplicationCheckBox, self.splashScreenCheckBox)
        ApplicationPage.setTabOrder(self.splashScreenCheckBox, self.globalMenuCheckBox)
        ApplicationPage.setTabOrder(self.globalMenuCheckBox, self.noOpenRadioButton)
        ApplicationPage.setTabOrder(self.noOpenRadioButton, self.lastFileRadioButton)
        ApplicationPage.setTabOrder(self.lastFileRadioButton, self.lastProjectRadioButton)
        ApplicationPage.setTabOrder(self.lastProjectRadioButton, self.lastMultiprojectRadioButton)
        ApplicationPage.setTabOrder(self.lastMultiprojectRadioButton, self.globalSessionRadioButton)
        ApplicationPage.setTabOrder(self.globalSessionRadioButton, self.noCheckRadioButton)
        ApplicationPage.setTabOrder(self.noCheckRadioButton, self.alwaysCheckRadioButton)
        ApplicationPage.setTabOrder(self.alwaysCheckRadioButton, self.dailyCheckRadioButton)
        ApplicationPage.setTabOrder(self.dailyCheckRadioButton, self.weeklyCheckRadioButton)
        ApplicationPage.setTabOrder(self.weeklyCheckRadioButton, self.monthlyCheckRadioButton)
        ApplicationPage.setTabOrder(self.monthlyCheckRadioButton, self.upgraderDelaySpinBox)
        ApplicationPage.setTabOrder(self.upgraderDelaySpinBox, self.crashSessionEnabledCheckBox)
        ApplicationPage.setTabOrder(self.crashSessionEnabledCheckBox, self.openCrashSessionCheckBox)
        ApplicationPage.setTabOrder(self.openCrashSessionCheckBox, self.deleteCrashSessionCheckBox)
        ApplicationPage.setTabOrder(self.deleteCrashSessionCheckBox, self.systemEmailClientCheckBox)
        ApplicationPage.setTabOrder(self.systemEmailClientCheckBox, self.errorlogCheckBox)
        ApplicationPage.setTabOrder(self.errorlogCheckBox, self.msgSeverityComboBox)
        ApplicationPage.setTabOrder(self.msgSeverityComboBox, self.intervalSpinBox)
        ApplicationPage.setTabOrder(self.intervalSpinBox, self.backgroundServicesSpinBox)

    def retranslateUi(self, ApplicationPage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("ApplicationPage", "<b>Configure the application</b>"))
        self.singleApplicationCheckBox.setToolTip(_translate("ApplicationPage", "Select, if only one instance of the application should be running"))
        self.singleApplicationCheckBox.setText(_translate("ApplicationPage", "Single Application Mode"))
        self.splashScreenCheckBox.setToolTip(_translate("ApplicationPage", "Select to show the startup splash screen"))
        self.splashScreenCheckBox.setText(_translate("ApplicationPage", "Show Splash Screen at startup"))
        self.globalMenuCheckBox.setToolTip(_translate("ApplicationPage", "Select to use the global application menu bar"))
        self.globalMenuCheckBox.setText(_translate("ApplicationPage", "Use Global Menu Bar"))
        self.groupBox_3.setTitle(_translate("ApplicationPage", "Open at startup"))
        self.noOpenRadioButton.setToolTip(_translate("ApplicationPage", "Select to not open anything"))
        self.noOpenRadioButton.setText(_translate("ApplicationPage", "None"))
        self.globalSessionRadioButton.setToolTip(_translate("ApplicationPage", "Select to restore the global session"))
        self.globalSessionRadioButton.setText(_translate("ApplicationPage", "Global Session"))
        self.lastFileRadioButton.setToolTip(_translate("ApplicationPage", "Select to open the most recently opened file"))
        self.lastFileRadioButton.setText(_translate("ApplicationPage", "Last File"))
        self.lastProjectRadioButton.setToolTip(_translate("ApplicationPage", "Select to open the most recently opened project"))
        self.lastProjectRadioButton.setText(_translate("ApplicationPage", "Last Project"))
        self.lastMultiprojectRadioButton.setToolTip(_translate("ApplicationPage", "Select to open the most recently opened multiproject"))
        self.lastMultiprojectRadioButton.setText(_translate("ApplicationPage", "Last Multiproject"))
        self.groupBox_2.setTitle(_translate("ApplicationPage", "Check for updates"))
        self.noCheckRadioButton.setToolTip(_translate("ApplicationPage", "Select to disable update checking"))
        self.noCheckRadioButton.setText(_translate("ApplicationPage", "Never"))
        self.alwaysCheckRadioButton.setToolTip(_translate("ApplicationPage", "Select to check for updates at every startup"))
        self.alwaysCheckRadioButton.setText(_translate("ApplicationPage", "Always"))
        self.dailyCheckRadioButton.setToolTip(_translate("ApplicationPage", "Select to check for updates once a day"))
        self.dailyCheckRadioButton.setText(_translate("ApplicationPage", "Daily"))
        self.weeklyCheckRadioButton.setToolTip(_translate("ApplicationPage", "Select to check for updates once a week"))
        self.weeklyCheckRadioButton.setText(_translate("ApplicationPage", "Weekly"))
        self.monthlyCheckRadioButton.setToolTip(_translate("ApplicationPage", "Select to check for updates once a month"))
        self.monthlyCheckRadioButton.setText(_translate("ApplicationPage", "Monthly"))
        self.groupBox_7.setTitle(_translate("ApplicationPage", "Upgrader"))
        self.label_3.setText(_translate("ApplicationPage", "Upgrader Delay:"))
        self.upgraderDelaySpinBox.setToolTip(_translate("ApplicationPage", "Enter the time the upgrader process should wait for eric to exit"))
        self.upgraderDelaySpinBox.setSuffix(_translate("ApplicationPage", " s"))
        self.crashSessionGroupBox.setToolTip(_translate("ApplicationPage", "Select to enable the generation of a crash session file"))
        self.crashSessionGroupBox.setTitle(_translate("ApplicationPage", "Crash Session"))
        self.crashSessionEnabledCheckBox.setToolTip(_translate("ApplicationPage", "Select to enable the generation of a crash session file"))
        self.crashSessionEnabledCheckBox.setText(_translate("ApplicationPage", "Enable Crash Session"))
        self.openCrashSessionCheckBox.setToolTip(_translate("ApplicationPage", "Select to check for a crash session file before opening the above configured startup item."))
        self.openCrashSessionCheckBox.setText(_translate("ApplicationPage", "Check for Crash Session at startup"))
        self.deleteCrashSessionCheckBox.setToolTip(_translate("ApplicationPage", "Select to delete a crash session file after it was loaded."))
        self.deleteCrashSessionCheckBox.setText(_translate("ApplicationPage", "Delete Crash Session after loading"))
        self.groupBox_4.setTitle(_translate("ApplicationPage", "Reporting"))
        self.systemEmailClientCheckBox.setToolTip(_translate("ApplicationPage", "Select to use the system email client to send reports"))
        self.systemEmailClientCheckBox.setText(_translate("ApplicationPage", "Use System Email Client"))
        self.groupBox.setTitle(_translate("ApplicationPage", "Error Log"))
        self.errorlogCheckBox.setToolTip(_translate("ApplicationPage", "Select to check the existence of an error log upon startup"))
        self.errorlogCheckBox.setText(_translate("ApplicationPage", "Check for Error Log at Startup"))
        self.label_2.setText(_translate("ApplicationPage", "Minimum Severity for message dialog:"))
        self.msgSeverityComboBox.setToolTip(_translate("ApplicationPage", "Select the minimum message severity shown"))
        self.groupBox_5.setTitle(_translate("ApplicationPage", "Keyboard Input Interval"))
        self.intervalSpinBox.setToolTip(_translate("ApplicationPage", "Enter the keyboard input interval, \'0\' for default"))
        self.intervalSpinBox.setSpecialValueText(_translate("ApplicationPage", "System Default"))
        self.intervalSpinBox.setSuffix(_translate("ApplicationPage", " ms"))
        self.groupBox_6.setTitle(_translate("ApplicationPage", "Background Services"))
        self.label.setText(_translate("ApplicationPage", "max. Processes:"))
        self.backgroundServicesSpinBox.setSpecialValueText(_translate("ApplicationPage", "Automatic"))
