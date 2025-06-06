# Form implementation generated from reading ui file 'src/eric7/WebBrowser/Bookmarks/BookmarksDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_BookmarksDialog(object):
    def setupUi(self, BookmarksDialog):
        BookmarksDialog.setObjectName("BookmarksDialog")
        BookmarksDialog.resize(750, 450)
        BookmarksDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(BookmarksDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.searchEdit = QtWidgets.QLineEdit(parent=BookmarksDialog)
        self.searchEdit.setClearButtonEnabled(True)
        self.searchEdit.setObjectName("searchEdit")
        self.horizontalLayout.addWidget(self.searchEdit)
        self.horizontalLayout_2.addLayout(self.horizontalLayout)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.bookmarksTree = EricTreeView(parent=BookmarksDialog)
        self.bookmarksTree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        self.bookmarksTree.setAlternatingRowColors(True)
        self.bookmarksTree.setTextElideMode(QtCore.Qt.TextElideMode.ElideMiddle)
        self.bookmarksTree.setUniformRowHeights(True)
        self.bookmarksTree.setObjectName("bookmarksTree")
        self.verticalLayout.addWidget(self.bookmarksTree)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.removeButton = QtWidgets.QPushButton(parent=BookmarksDialog)
        self.removeButton.setAutoDefault(False)
        self.removeButton.setObjectName("removeButton")
        self.horizontalLayout_3.addWidget(self.removeButton)
        self.addFolderButton = QtWidgets.QPushButton(parent=BookmarksDialog)
        self.addFolderButton.setAutoDefault(False)
        self.addFolderButton.setObjectName("addFolderButton")
        self.horizontalLayout_3.addWidget(self.addFolderButton)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=BookmarksDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(BookmarksDialog)
        self.buttonBox.accepted.connect(BookmarksDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(BookmarksDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(BookmarksDialog)
        BookmarksDialog.setTabOrder(self.searchEdit, self.bookmarksTree)
        BookmarksDialog.setTabOrder(self.bookmarksTree, self.removeButton)
        BookmarksDialog.setTabOrder(self.removeButton, self.addFolderButton)
        BookmarksDialog.setTabOrder(self.addFolderButton, self.buttonBox)

    def retranslateUi(self, BookmarksDialog):
        _translate = QtCore.QCoreApplication.translate
        BookmarksDialog.setWindowTitle(_translate("BookmarksDialog", "Manage Bookmarks"))
        self.searchEdit.setToolTip(_translate("BookmarksDialog", "Enter search term for bookmarks"))
        self.removeButton.setToolTip(_translate("BookmarksDialog", "Press to delete the selected entries"))
        self.removeButton.setText(_translate("BookmarksDialog", "&Delete"))
        self.addFolderButton.setToolTip(_translate("BookmarksDialog", "Press to add a new bookmarks folder"))
        self.addFolderButton.setText(_translate("BookmarksDialog", "Add &Folder"))
from eric7.EricWidgets.EricTreeView import EricTreeView
