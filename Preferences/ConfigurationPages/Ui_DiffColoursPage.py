# Form implementation generated from reading ui file 'src/eric7/Preferences/ConfigurationPages/DiffColoursPage.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_DiffColoursPage(object):
    def setupUi(self, DiffColoursPage):
        DiffColoursPage.setObjectName("DiffColoursPage")
        DiffColoursPage.resize(400, 286)
        self.verticalLayout = QtWidgets.QVBoxLayout(DiffColoursPage)
        self.verticalLayout.setObjectName("verticalLayout")
        self.headerLabel = QtWidgets.QLabel(parent=DiffColoursPage)
        self.headerLabel.setObjectName("headerLabel")
        self.verticalLayout.addWidget(self.headerLabel)
        self.line1 = QtWidgets.QFrame(parent=DiffColoursPage)
        self.line1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line1.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line1.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line1.setObjectName("line1")
        self.verticalLayout.addWidget(self.line1)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.headerButton = QtWidgets.QPushButton(parent=DiffColoursPage)
        self.headerButton.setObjectName("headerButton")
        self.gridLayout.addWidget(self.headerButton, 5, 0, 1, 1)
        self.headerSample = QtWidgets.QLineEdit(parent=DiffColoursPage)
        self.headerSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.headerSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.headerSample.setReadOnly(True)
        self.headerSample.setObjectName("headerSample")
        self.gridLayout.addWidget(self.headerSample, 5, 1, 1, 1)
        self.whitespaceButton = QtWidgets.QPushButton(parent=DiffColoursPage)
        self.whitespaceButton.setObjectName("whitespaceButton")
        self.gridLayout.addWidget(self.whitespaceButton, 6, 0, 1, 1)
        self.whitespaceSample = QtWidgets.QLineEdit(parent=DiffColoursPage)
        self.whitespaceSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.whitespaceSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.whitespaceSample.setReadOnly(True)
        self.whitespaceSample.setObjectName("whitespaceSample")
        self.gridLayout.addWidget(self.whitespaceSample, 6, 1, 1, 1)
        self.textButton = QtWidgets.QPushButton(parent=DiffColoursPage)
        self.textButton.setObjectName("textButton")
        self.gridLayout.addWidget(self.textButton, 0, 0, 1, 1)
        self.textSample = QtWidgets.QLineEdit(parent=DiffColoursPage)
        self.textSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.textSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.textSample.setReadOnly(True)
        self.textSample.setObjectName("textSample")
        self.gridLayout.addWidget(self.textSample, 0, 1, 1, 1)
        self.addedButton = QtWidgets.QPushButton(parent=DiffColoursPage)
        self.addedButton.setObjectName("addedButton")
        self.gridLayout.addWidget(self.addedButton, 1, 0, 1, 1)
        self.addedSample = QtWidgets.QLineEdit(parent=DiffColoursPage)
        self.addedSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.addedSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.addedSample.setReadOnly(True)
        self.addedSample.setObjectName("addedSample")
        self.gridLayout.addWidget(self.addedSample, 1, 1, 1, 1)
        self.removedButton = QtWidgets.QPushButton(parent=DiffColoursPage)
        self.removedButton.setObjectName("removedButton")
        self.gridLayout.addWidget(self.removedButton, 2, 0, 1, 1)
        self.removedSample = QtWidgets.QLineEdit(parent=DiffColoursPage)
        self.removedSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.removedSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.removedSample.setReadOnly(True)
        self.removedSample.setObjectName("removedSample")
        self.gridLayout.addWidget(self.removedSample, 2, 1, 1, 1)
        self.replacedButton = QtWidgets.QPushButton(parent=DiffColoursPage)
        self.replacedButton.setObjectName("replacedButton")
        self.gridLayout.addWidget(self.replacedButton, 3, 0, 1, 1)
        self.replacedSample = QtWidgets.QLineEdit(parent=DiffColoursPage)
        self.replacedSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.replacedSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.replacedSample.setReadOnly(True)
        self.replacedSample.setObjectName("replacedSample")
        self.gridLayout.addWidget(self.replacedSample, 3, 1, 1, 1)
        self.contextButton = QtWidgets.QPushButton(parent=DiffColoursPage)
        self.contextButton.setObjectName("contextButton")
        self.gridLayout.addWidget(self.contextButton, 4, 0, 1, 1)
        self.contextSample = QtWidgets.QLineEdit(parent=DiffColoursPage)
        self.contextSample.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.contextSample.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.contextSample.setReadOnly(True)
        self.contextSample.setObjectName("contextSample")
        self.gridLayout.addWidget(self.contextSample, 4, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        spacerItem = QtWidgets.QSpacerItem(20, 46, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(DiffColoursPage)
        QtCore.QMetaObject.connectSlotsByName(DiffColoursPage)

    def retranslateUi(self, DiffColoursPage):
        _translate = QtCore.QCoreApplication.translate
        self.headerLabel.setText(_translate("DiffColoursPage", "<b>Configure Diff colors</b>"))
        self.headerButton.setToolTip(_translate("DiffColoursPage", "Select the background color for header lines"))
        self.headerButton.setText(_translate("DiffColoursPage", "Header Color"))
        self.headerSample.setText(_translate("DiffColoursPage", "Header Line"))
        self.whitespaceButton.setToolTip(_translate("DiffColoursPage", "Select the background color for bad whitespace"))
        self.whitespaceButton.setText(_translate("DiffColoursPage", "Whitespace Color"))
        self.textButton.setToolTip(_translate("DiffColoursPage", "Select the text foreground color"))
        self.textButton.setText(_translate("DiffColoursPage", "Text Color"))
        self.textSample.setText(_translate("DiffColoursPage", "Normal Text"))
        self.addedButton.setToolTip(_translate("DiffColoursPage", "Select the background color for additions"))
        self.addedButton.setText(_translate("DiffColoursPage", "Added Color"))
        self.addedSample.setText(_translate("DiffColoursPage", "Added Text"))
        self.removedButton.setToolTip(_translate("DiffColoursPage", "Select the background color for removed text"))
        self.removedButton.setText(_translate("DiffColoursPage", "Removed Color"))
        self.removedSample.setText(_translate("DiffColoursPage", "Removed Text"))
        self.replacedButton.setToolTip(_translate("DiffColoursPage", "Select the background color for replaced text"))
        self.replacedButton.setText(_translate("DiffColoursPage", "Replaced Color"))
        self.replacedSample.setText(_translate("DiffColoursPage", "Replaced Text"))
        self.contextButton.setToolTip(_translate("DiffColoursPage", "Select the background color for context lines"))
        self.contextButton.setText(_translate("DiffColoursPage", "Context Color"))
        self.contextSample.setText(_translate("DiffColoursPage", "Context Line"))
