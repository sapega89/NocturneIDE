# Form implementation generated from reading ui file 'src/eric7/WebBrowser/UrlBar/BookmarkInfoDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_BookmarkInfoDialog(object):
    def setupUi(self, BookmarkInfoDialog):
        BookmarkInfoDialog.setObjectName("BookmarkInfoDialog")
        BookmarkInfoDialog.resize(350, 135)
        BookmarkInfoDialog.setSizeGripEnabled(True)
        self.gridLayout = QtWidgets.QGridLayout(BookmarkInfoDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.icon = QtWidgets.QLabel(parent=BookmarkInfoDialog)
        self.icon.setText("")
        self.icon.setObjectName("icon")
        self.horizontalLayout.addWidget(self.icon)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.title = QtWidgets.QLabel(parent=BookmarkInfoDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.title.sizePolicy().hasHeightForWidth())
        self.title.setSizePolicy(sizePolicy)
        self.title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title.setObjectName("title")
        self.verticalLayout.addWidget(self.title)
        self.removeButton = QtWidgets.QPushButton(parent=BookmarkInfoDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.removeButton.sizePolicy().hasHeightForWidth())
        self.removeButton.setSizePolicy(sizePolicy)
        self.removeButton.setObjectName("removeButton")
        self.verticalLayout.addWidget(self.removeButton)
        self.horizontalLayout.addLayout(self.verticalLayout)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 1, 1, 1)
        self.label = QtWidgets.QLabel(parent=BookmarkInfoDialog)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.titleEdit = QtWidgets.QLineEdit(parent=BookmarkInfoDialog)
        self.titleEdit.setObjectName("titleEdit")
        self.gridLayout.addWidget(self.titleEdit, 1, 1, 1, 1)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=BookmarkInfoDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel|QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 2)

        self.retranslateUi(BookmarkInfoDialog)
        self.buttonBox.accepted.connect(BookmarkInfoDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(BookmarkInfoDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(BookmarkInfoDialog)
        BookmarkInfoDialog.setTabOrder(self.removeButton, self.titleEdit)
        BookmarkInfoDialog.setTabOrder(self.titleEdit, self.buttonBox)

    def retranslateUi(self, BookmarkInfoDialog):
        _translate = QtCore.QCoreApplication.translate
        BookmarkInfoDialog.setWindowTitle(_translate("BookmarkInfoDialog", "Edit Bookmark"))
        self.title.setText(_translate("BookmarkInfoDialog", "Edit this Bookmark"))
        self.removeButton.setToolTip(_translate("BookmarkInfoDialog", "Press to remove this bookmark"))
        self.removeButton.setText(_translate("BookmarkInfoDialog", "Remove this Bookmark"))
        self.label.setText(_translate("BookmarkInfoDialog", "Title:"))
