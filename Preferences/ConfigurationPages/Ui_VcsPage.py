# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/VcsPage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_VcsPage(object):
    def setupUi(self, VcsPage):
        VcsPage.setObjectName("VcsPage")
        VcsPage.resize(576, 596)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(VcsPage)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.headerLabel = QtWidgets.QLabel(parent=VcsPage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout_2.addWidget(self.headerLabel)
        self.line9_3_2_2 = QtWidgets.QFrame(parent=VcsPage)
        self.line9_3_2_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_3_2_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line9_3_2_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line9_3_2_2.setObjectName("line9_3_2_2")
        self.verticalLayout_2.addWidget(self.line9_3_2_2)
        self.vcsAutoCloseCheckBox = QtWidgets.QCheckBox(parent=VcsPage)
        self.vcsAutoCloseCheckBox.setObjectName("vcsAutoCloseCheckBox")
        self.verticalLayout_2.addWidget(self.vcsAutoCloseCheckBox)
        self.groupBox = QtWidgets.QGroupBox(parent=VcsPage)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.vcsAutoSaveCheckBox = QtWidgets.QCheckBox(parent=self.groupBox)
        self.vcsAutoSaveCheckBox.setObjectName("vcsAutoSaveCheckBox")
        self.gridLayout_3.addWidget(self.vcsAutoSaveCheckBox, 0, 0, 1, 1)
        self.vcsAutoSaveProjectCheckBox = QtWidgets.QCheckBox(parent=self.groupBox)
        self.vcsAutoSaveProjectCheckBox.setObjectName("vcsAutoSaveProjectCheckBox")
        self.gridLayout_3.addWidget(self.vcsAutoSaveProjectCheckBox, 0, 1, 1, 1)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_8 = QtWidgets.QLabel(parent=self.groupBox)
        self.label_8.setObjectName("label_8")
        self.horizontalLayout.addWidget(self.label_8)
        self.commitSpinBox = QtWidgets.QSpinBox(parent=self.groupBox)
        self.commitSpinBox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.commitSpinBox.setMinimum(1)
        self.commitSpinBox.setMaximum(100)
        self.commitSpinBox.setObjectName("commitSpinBox")
        self.horizontalLayout.addWidget(self.commitSpinBox)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.gridLayout_3.addLayout(self.horizontalLayout, 1, 0, 1, 2)
        self.perProjectCommitHistoryCheckBox = QtWidgets.QCheckBox(parent=self.groupBox)
        self.perProjectCommitHistoryCheckBox.setObjectName("perProjectCommitHistoryCheckBox")
        self.gridLayout_3.addWidget(self.perProjectCommitHistoryCheckBox, 2, 0, 1, 2)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(parent=VcsPage)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.vcsStatusMonitorIntervalSpinBox = QtWidgets.QSpinBox(parent=self.groupBox_2)
        self.vcsStatusMonitorIntervalSpinBox.setMaximum(3600)
        self.vcsStatusMonitorIntervalSpinBox.setObjectName("vcsStatusMonitorIntervalSpinBox")
        self.gridLayout_2.addWidget(self.vcsStatusMonitorIntervalSpinBox, 0, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 0, 1, 1, 1)
        self.vcsMonitorLocalStatusCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_2)
        self.vcsMonitorLocalStatusCheckBox.setObjectName("vcsMonitorLocalStatusCheckBox")
        self.gridLayout_2.addWidget(self.vcsMonitorLocalStatusCheckBox, 1, 0, 1, 2)
        self.autoUpdateCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_2)
        self.autoUpdateCheckBox.setObjectName("autoUpdateCheckBox")
        self.gridLayout_2.addWidget(self.autoUpdateCheckBox, 2, 0, 1, 2)
        self.verticalLayout_2.addWidget(self.groupBox_2)
        self.groupBox_3 = QtWidgets.QGroupBox(parent=VcsPage)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout.setObjectName("gridLayout")
        self.label_4 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)
        self.pbVcsAddedButton = QtWidgets.QPushButton(parent=self.groupBox_3)
        self.pbVcsAddedButton.setMinimumSize(QtCore.QSize(100, 0))
        self.pbVcsAddedButton.setText("")
        self.pbVcsAddedButton.setObjectName("pbVcsAddedButton")
        self.gridLayout.addWidget(self.pbVcsAddedButton, 0, 1, 1, 1)
        self.label_5 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_5.setObjectName("label_5")
        self.gridLayout.addWidget(self.label_5, 0, 2, 1, 1)
        self.pbVcsConflictButton = QtWidgets.QPushButton(parent=self.groupBox_3)
        self.pbVcsConflictButton.setMinimumSize(QtCore.QSize(100, 0))
        self.pbVcsConflictButton.setText("")
        self.pbVcsConflictButton.setObjectName("pbVcsConflictButton")
        self.gridLayout.addWidget(self.pbVcsConflictButton, 0, 3, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout.addItem(spacerItem2, 0, 4, 1, 1)
        self.label_2 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.pbVcsModifiedButton = QtWidgets.QPushButton(parent=self.groupBox_3)
        self.pbVcsModifiedButton.setMinimumSize(QtCore.QSize(100, 0))
        self.pbVcsModifiedButton.setText("")
        self.pbVcsModifiedButton.setObjectName("pbVcsModifiedButton")
        self.gridLayout.addWidget(self.pbVcsModifiedButton, 1, 1, 1, 1)
        self.label_6 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_6.setObjectName("label_6")
        self.gridLayout.addWidget(self.label_6, 1, 2, 1, 1)
        self.pbVcsReplacedButton = QtWidgets.QPushButton(parent=self.groupBox_3)
        self.pbVcsReplacedButton.setMinimumSize(QtCore.QSize(100, 0))
        self.pbVcsReplacedButton.setText("")
        self.pbVcsReplacedButton.setObjectName("pbVcsReplacedButton")
        self.gridLayout.addWidget(self.pbVcsReplacedButton, 1, 3, 1, 1)
        self.label_3 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)
        self.pbVcsUpdateButton = QtWidgets.QPushButton(parent=self.groupBox_3)
        self.pbVcsUpdateButton.setMinimumSize(QtCore.QSize(100, 0))
        self.pbVcsUpdateButton.setText("")
        self.pbVcsUpdateButton.setObjectName("pbVcsUpdateButton")
        self.gridLayout.addWidget(self.pbVcsUpdateButton, 2, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(parent=self.groupBox_3)
        self.label_7.setObjectName("label_7")
        self.gridLayout.addWidget(self.label_7, 2, 2, 1, 1)
        self.pbVcsRemovedButton = QtWidgets.QPushButton(parent=self.groupBox_3)
        self.pbVcsRemovedButton.setMinimumSize(QtCore.QSize(100, 0))
        self.pbVcsRemovedButton.setText("")
        self.pbVcsRemovedButton.setObjectName("pbVcsRemovedButton")
        self.gridLayout.addWidget(self.pbVcsRemovedButton, 2, 3, 1, 1)
        self.verticalLayout_2.addWidget(self.groupBox_3)
        self.groupBox_4 = QtWidgets.QGroupBox(parent=VcsPage)
        self.groupBox_4.setObjectName("groupBox_4")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox_4)
        self.verticalLayout.setObjectName("verticalLayout")
        self.vcsToolbarCheckBox = QtWidgets.QCheckBox(parent=self.groupBox_4)
        self.vcsToolbarCheckBox.setObjectName("vcsToolbarCheckBox")
        self.verticalLayout.addWidget(self.vcsToolbarCheckBox)
        self.verticalLayout_2.addWidget(self.groupBox_4)
        spacerItem3 = QtWidgets.QSpacerItem(512, 81, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_2.addItem(spacerItem3)

        self.retranslateUi(VcsPage)
        QtCore.QMetaObject.connectSlotsByName(VcsPage)
        VcsPage.setTabOrder(self.vcsAutoCloseCheckBox, self.vcsAutoSaveCheckBox)
        VcsPage.setTabOrder(self.vcsAutoSaveCheckBox, self.vcsAutoSaveProjectCheckBox)
        VcsPage.setTabOrder(self.vcsAutoSaveProjectCheckBox, self.commitSpinBox)
        VcsPage.setTabOrder(self.commitSpinBox, self.perProjectCommitHistoryCheckBox)
        VcsPage.setTabOrder(self.perProjectCommitHistoryCheckBox, self.vcsStatusMonitorIntervalSpinBox)
        VcsPage.setTabOrder(self.vcsStatusMonitorIntervalSpinBox, self.vcsMonitorLocalStatusCheckBox)
        VcsPage.setTabOrder(self.vcsMonitorLocalStatusCheckBox, self.autoUpdateCheckBox)
        VcsPage.setTabOrder(self.autoUpdateCheckBox, self.pbVcsAddedButton)
        VcsPage.setTabOrder(self.pbVcsAddedButton, self.pbVcsConflictButton)
        VcsPage.setTabOrder(self.pbVcsConflictButton, self.pbVcsModifiedButton)
        VcsPage.setTabOrder(self.pbVcsModifiedButton, self.pbVcsReplacedButton)
        VcsPage.setTabOrder(self.pbVcsReplacedButton, self.pbVcsUpdateButton)
        VcsPage.setTabOrder(self.pbVcsUpdateButton, self.pbVcsRemovedButton)
        VcsPage.setTabOrder(self.pbVcsRemovedButton, self.vcsToolbarCheckBox)

    def retranslateUi(self, VcsPage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("VcsPage", "<b>Configure Version Control Systems</b>"))
        self.vcsAutoCloseCheckBox.setText(_translate("VcsPage", "Close VCS dialog automatically, if no error occured"))
        self.groupBox.setTitle(_translate("VcsPage", "Commit"))
        self.vcsAutoSaveCheckBox.setToolTip(_translate("VcsPage", "Select, if files should be saved before a commit"))
        self.vcsAutoSaveCheckBox.setText(_translate("VcsPage", "Save files upon commit"))
        self.vcsAutoSaveProjectCheckBox.setToolTip(_translate("VcsPage", "Select, if project should be saved before a commit"))
        self.vcsAutoSaveProjectCheckBox.setText(_translate("VcsPage", "Save project upon commit"))
        self.label_8.setText(_translate("VcsPage", "No. of commit messages to remember:"))
        self.commitSpinBox.setToolTip(_translate("VcsPage", "Enter the number of commit messages to remember"))
        self.perProjectCommitHistoryCheckBox.setToolTip(_translate("VcsPage", "Select to use one commit messages history per project"))
        self.perProjectCommitHistoryCheckBox.setText(_translate("VcsPage", "Remember commit messages per project"))
        self.groupBox_2.setTitle(_translate("VcsPage", "Status Monitor"))
        self.vcsStatusMonitorIntervalSpinBox.setToolTip(_translate("VcsPage", "Select the interval in seconds for VCS status updates (0 to disable)"))
        self.vcsStatusMonitorIntervalSpinBox.setSuffix(_translate("VcsPage", " sec"))
        self.vcsMonitorLocalStatusCheckBox.setToolTip(_translate("VcsPage", "Select to monitor local status only (if supported by VCS)"))
        self.vcsMonitorLocalStatusCheckBox.setText(_translate("VcsPage", "Monitor local status only"))
        self.autoUpdateCheckBox.setToolTip(_translate("VcsPage", "Select to enable automatic updates"))
        self.autoUpdateCheckBox.setText(_translate("VcsPage", "Automatic updates enabled"))
        self.groupBox_3.setTitle(_translate("VcsPage", "Colors"))
        self.label_4.setText(_translate("VcsPage", "VCS status \"added\":"))
        self.pbVcsAddedButton.setToolTip(_translate("VcsPage", "Select the background color for entries with VCS status \"added\"."))
        self.label_5.setText(_translate("VcsPage", "VCS status \"conflict\":"))
        self.pbVcsConflictButton.setToolTip(_translate("VcsPage", "Select the background color for entries with VCS status \"conflict\"."))
        self.label_2.setText(_translate("VcsPage", "VCS status \"modified\":"))
        self.pbVcsModifiedButton.setToolTip(_translate("VcsPage", "Select the background color for entries with VCS status \"modified\"."))
        self.label_6.setText(_translate("VcsPage", "VCS status \"replaced\":"))
        self.pbVcsReplacedButton.setToolTip(_translate("VcsPage", "Select the background color for entries with VCS status \"replaced\"."))
        self.label_3.setText(_translate("VcsPage", "VCS status \"needs update\":"))
        self.pbVcsUpdateButton.setToolTip(_translate("VcsPage", "Select the background color for entries with VCS status \"needs update\"."))
        self.label_7.setText(_translate("VcsPage", "VCS status \"removed\":"))
        self.pbVcsRemovedButton.setToolTip(_translate("VcsPage", "Select the background color for entries with VCS status \"removed\"."))
        self.groupBox_4.setTitle(_translate("VcsPage", "Toolbars"))
        self.vcsToolbarCheckBox.setToolTip(_translate("VcsPage", "Select to show VCS specific toolbars"))
        self.vcsToolbarCheckBox.setText(_translate("VcsPage", "Show VCS Toolbar"))
