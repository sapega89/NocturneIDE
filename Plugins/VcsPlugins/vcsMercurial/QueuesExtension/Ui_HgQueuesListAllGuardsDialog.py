# Form implementation generated from reading ui file 'src/eric7/Plugins/VcsPlugins/vcsMercurial/QueuesExtension/HgQueuesListAllGuardsDialog.ui'
#
# Created by: PyQt6 UI code generator 6.8.0
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_HgQueuesListAllGuardsDialog(object):
    def setupUi(self, HgQueuesListAllGuardsDialog):
        HgQueuesListAllGuardsDialog.setObjectName("HgQueuesListAllGuardsDialog")
        HgQueuesListAllGuardsDialog.resize(400, 400)
        HgQueuesListAllGuardsDialog.setSizeGripEnabled(True)
        self.verticalLayout = QtWidgets.QVBoxLayout(HgQueuesListAllGuardsDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.guardsTree = QtWidgets.QTreeWidget(parent=HgQueuesListAllGuardsDialog)
        self.guardsTree.setAlternatingRowColors(True)
        self.guardsTree.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.guardsTree.setHeaderHidden(True)
        self.guardsTree.setObjectName("guardsTree")
        self.guardsTree.headerItem().setText(0, "1")
        self.verticalLayout.addWidget(self.guardsTree)
        self.buttonBox = QtWidgets.QDialogButtonBox(parent=HgQueuesListAllGuardsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(HgQueuesListAllGuardsDialog)
        self.buttonBox.accepted.connect(HgQueuesListAllGuardsDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(HgQueuesListAllGuardsDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(HgQueuesListAllGuardsDialog)
        HgQueuesListAllGuardsDialog.setTabOrder(self.guardsTree, self.buttonBox)

    def retranslateUi(self, HgQueuesListAllGuardsDialog):
        _translate = QtCore.QCoreApplication.translate
        HgQueuesListAllGuardsDialog.setWindowTitle(_translate("HgQueuesListAllGuardsDialog", "List All Guards"))
        self.guardsTree.setToolTip(_translate("HgQueuesListAllGuardsDialog", "Show all guards of all patches"))
