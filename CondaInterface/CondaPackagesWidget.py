# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the conda packages management widget.
"""

import os

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLineEdit,
    QMenu,
    QToolButton,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import CondaInterface
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox, EricTextInputDialog
from eric7.EricWidgets.EricApplication import ericApp
from eric7.VirtualEnv.VirtualenvMeta import VirtualenvMetaData

from .Ui_CondaPackagesWidget import Ui_CondaPackagesWidget


class CondaPackagesWidget(QWidget, Ui_CondaPackagesWidget):
    """
    Class implementing the conda packages management widget.
    """

    # Role definition of packages list
    PackageVersionRole = Qt.ItemDataRole.UserRole + 1
    PackageBuildRole = Qt.ItemDataRole.UserRole + 2

    # Role definitions of search results list
    PackageDetailedDataRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, conda, parent=None):
        """
        Constructor

        @param conda reference to the conda interface
        @type Conda
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.layout().setContentsMargins(0, 3, 0, 0)

        self.__conda = conda

        if not CondaInterface.isCondaAvailable():
            self.availableWidget.hide()
        else:
            self.notAvailableWidget.hide()

            self.__initCondaInterface()

    def __initCondaInterface(self):
        """
        Private method to initialize the conda interface elements.
        """
        self.statusLabel.hide()

        self.condaMenuButton.setObjectName("conda_supermenu_button")
        self.condaMenuButton.setIcon(EricPixmapCache.getIcon("superMenu"))
        self.condaMenuButton.setToolTip(self.tr("Conda Menu"))
        self.condaMenuButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.condaMenuButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.condaMenuButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.condaMenuButton.setShowMenuInside(True)

        self.refreshButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.upgradeButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.upgradeAllButton.setIcon(EricPixmapCache.getIcon("2uparrow"))
        self.uninstallButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.searchToggleButton_1.setIcon(EricPixmapCache.getIcon("find"))
        self.searchToggleButton_2.setIcon(EricPixmapCache.getIcon("find"))
        self.searchButton.setIcon(EricPixmapCache.getIcon("findNext"))
        self.installButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.showDetailsButton.setIcon(EricPixmapCache.getIcon("info"))

        if CondaInterface.condaVersion() >= (4, 4, 0):
            self.searchOptionsWidget.hide()
        else:
            self.platformComboBox.addItems(
                sorted(
                    [
                        "",
                        "win-32",
                        "win-64",
                        "osx-64",
                        "linux-32",
                        "linux-64",
                    ]
                )
            )

        self.__initCondaMenu()
        self.__populateEnvironments()
        self.__updateActionButtons()

        self.searchWidget.hide()

        self.__conda.condaEnvironmentCreated.connect(self.on_refreshButton_clicked)
        self.__conda.condaEnvironmentRemoved.connect(self.on_refreshButton_clicked)

    def __populateEnvironments(self):
        """
        Private method to get a list of environments and populate the selector.
        """
        environments = [("", "")] + sorted(self.__conda.getCondaEnvironmentsList())
        for environment in environments:
            self.environmentsComboBox.addItem(environment[0], environment[1])

    def __initCondaMenu(self):
        """
        Private method to create the super menu and attach it to the super
        menu button.
        """
        self.__condaMenu = QMenu(self)
        self.__envActs = []

        self.__cleanMenu = QMenu(self.tr("Clean"), self)
        self.__cleanMenu.addAction(
            self.tr("All"), lambda: self.__conda.cleanConda("all")
        )
        self.__cleanMenu.addAction(
            self.tr("Cache"), lambda: self.__conda.cleanConda("index-cache")
        )
        self.__cleanMenu.addAction(
            self.tr("Lock Files"), lambda: self.__conda.cleanConda("lock")
        )
        self.__cleanMenu.addAction(
            self.tr("Packages"), lambda: self.__conda.cleanConda("packages")
        )
        self.__cleanMenu.addAction(
            self.tr("Tarballs"), lambda: self.__conda.cleanConda("tarballs")
        )

        self.__condaMenu.addAction(self.tr("About Conda..."), self.__aboutConda)
        self.__condaMenu.addSeparator()
        self.__condaMenu.addAction(self.tr("Update Conda"), self.__conda.updateConda)
        self.__condaMenu.addSeparator()
        self.__envActs.append(
            self.__condaMenu.addAction(
                self.tr("Install Packages"), self.__installPackages
            )
        )
        self.__envActs.append(
            self.__condaMenu.addAction(
                self.tr("Install Requirements"), self.__installRequirements
            )
        )
        self.__condaMenu.addSeparator()
        self.__envActs.append(
            self.__condaMenu.addAction(
                self.tr("Generate Requirements"), self.__generateRequirements
            )
        )
        self.__condaMenu.addSeparator()
        self.__condaMenu.addAction(
            self.tr("Create Environment from Requirements"), self.__createEnvironment
        )
        self.__envActs.append(
            self.__condaMenu.addAction(
                self.tr("Clone Environment"), self.__cloneEnvironment
            )
        )
        self.__deleteEnvAct = self.__condaMenu.addAction(
            self.tr("Delete Environment"), self.__deleteEnvironment
        )
        self.__condaMenu.addSeparator()
        self.__condaMenu.addMenu(self.__cleanMenu)
        self.__condaMenu.addSeparator()
        self.__condaMenu.addAction(
            self.tr("Edit User Configuration..."), self.__editUserConfiguration
        )
        self.__condaMenu.addSeparator()
        self.__condaMenu.addAction(self.tr("Configure..."), self.__condaConfigure)

        self.condaMenuButton.setMenu(self.__condaMenu)

        self.__condaMenu.aboutToShow.connect(self.__aboutToShowCondaMenu)

    def __selectedUpdateableItems(self):
        """
        Private method to get a list of selected items that can be updated.

        @return list of selected items that can be updated
        @rtype list of QTreeWidgetItem
        """
        return [itm for itm in self.packagesList.selectedItems() if bool(itm.text(2))]

    def __allUpdateableItems(self):
        """
        Private method to get a list of all items that can be updated.

        @return list of all items that can be updated
        @rtype list of QTreeWidgetItem
        """
        updateableItems = []
        for index in range(self.packagesList.topLevelItemCount()):
            itm = self.packagesList.topLevelItem(index)
            if itm.text(2):
                updateableItems.append(itm)

        return updateableItems

    def __updateActionButtons(self):
        """
        Private method to set the state of the action buttons.
        """
        self.upgradeButton.setEnabled(bool(self.__selectedUpdateableItems()))
        self.uninstallButton.setEnabled(bool(self.packagesList.selectedItems()))
        self.upgradeAllButton.setEnabled(bool(self.__allUpdateableItems()))

    @pyqtSlot(int)
    def on_environmentsComboBox_currentIndexChanged(self, index):
        """
        Private slot handling the selection of a conda environment.

        @param index index of the selected conda environment
        @type int
        """
        self.packagesList.clear()
        prefix = self.environmentsComboBox.itemData(index)
        if prefix:
            self.statusLabel.show()
            self.statusLabel.setText(self.tr("Getting installed packages..."))

            with EricOverrideCursor():
                # 1. populate with installed packages
                self.packagesList.setUpdatesEnabled(False)
                installedPackages = self.__conda.getInstalledPackages(prefix=prefix)
                for package, version, build in installedPackages:
                    itm = QTreeWidgetItem(self.packagesList, [package, version])
                    itm.setData(1, self.PackageVersionRole, version)
                    itm.setData(1, self.PackageBuildRole, build)
                self.packagesList.setUpdatesEnabled(True)
                self.statusLabel.setText(self.tr("Getting outdated packages..."))
                QApplication.processEvents()

                # 2. update with update information
                self.packagesList.setUpdatesEnabled(False)
                updateablePackages = self.__conda.getUpdateablePackages(prefix=prefix)
                for package, version, build in updateablePackages:
                    items = self.packagesList.findItems(
                        package,
                        Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive,
                    )
                    if items:
                        itm = items[0]
                        itm.setText(2, version)
                        itm.setData(2, self.PackageVersionRole, version)
                        itm.setData(2, self.PackageBuildRole, build)
                        if itm.data(1, self.PackageVersionRole) == version:
                            # build must be different, show in version display
                            itm.setText(
                                1,
                                self.tr("{0} (Build: {1})").format(
                                    itm.data(1, self.PackageVersionRole),
                                    itm.data(1, self.PackageBuildRole),
                                ),
                            )
                            itm.setText(
                                2,
                                self.tr("{0} (Build: {1})").format(
                                    itm.data(2, self.PackageVersionRole),
                                    itm.data(2, self.PackageBuildRole),
                                ),
                            )

                self.packagesList.sortItems(0, Qt.SortOrder.AscendingOrder)
                for col in range(self.packagesList.columnCount()):
                    self.packagesList.resizeColumnToContents(col)
                self.packagesList.setUpdatesEnabled(True)
            self.statusLabel.hide()

        self.__updateActionButtons()
        self.__updateSearchActionButtons()

    @pyqtSlot()
    def on_packagesList_itemSelectionChanged(self):
        """
        Private slot to handle the selection of some items..
        """
        self.__updateActionButtons()

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the display.
        """
        currentEnvironment = self.environmentsComboBox.currentText()
        self.environmentsComboBox.clear()
        self.packagesList.clear()

        with EricOverrideCursor():
            self.__populateEnvironments()

            index = self.environmentsComboBox.findText(
                currentEnvironment,
                Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive,
            )
            if index != -1:
                self.environmentsComboBox.setCurrentIndex(index)

        self.__updateActionButtons()

    @pyqtSlot()
    def on_upgradeButton_clicked(self):
        """
        Private slot to upgrade selected packages of the selected environment.
        """
        packages = [itm.text(0) for itm in self.__selectedUpdateableItems()]
        if packages:
            prefix = self.environmentsComboBox.itemData(
                self.environmentsComboBox.currentIndex()
            )
            ok = self.__conda.updatePackages(packages, prefix=prefix)
            if ok:
                self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_upgradeAllButton_clicked(self):
        """
        Private slot to upgrade all packages of the selected environment.
        """
        prefix = self.environmentsComboBox.itemData(
            self.environmentsComboBox.currentIndex()
        )
        ok = self.__conda.updateAllPackages(prefix=prefix)
        if ok:
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_uninstallButton_clicked(self):
        """
        Private slot to remove selected packages of the selected environment.
        """
        packages = [itm.text(0) for itm in self.packagesList.selectedItems()]
        if packages:
            prefix = self.environmentsComboBox.itemData(
                self.environmentsComboBox.currentIndex()
            )
            ok = self.__conda.uninstallPackages(packages, prefix=prefix)
            if ok:
                self.on_refreshButton_clicked()

    #######################################################################
    ## Search widget related methods below
    #######################################################################

    def __updateSearchActionButtons(self):
        """
        Private method to update the action button states of the search widget.
        """
        enable = len(self.searchResultList.selectedItems()) == 1
        self.installButton.setEnabled(
            enable and self.environmentsComboBox.currentIndex() > 0
        )
        self.showDetailsButton.setEnabled(
            enable and bool(self.searchResultList.selectedItems()[0].parent())
        )

    def __doSearch(self):
        """
        Private method to search for packages.
        """
        self.searchResultList.clear()
        pattern = self.searchEdit.text()
        if pattern:
            with EricOverrideCursor():
                prefix = (
                    ""
                    if CondaInterface.condaVersion() >= (4, 4, 0)
                    else self.environmentsComboBox.itemData(
                        self.environmentsComboBox.currentIndex()
                    )
                )
                ok, result = self.__conda.searchPackages(
                    pattern,
                    fullNameOnly=self.fullNameButton.isChecked(),
                    packageSpec=self.packageSpecButton.isChecked(),
                    platform=self.platformComboBox.currentText(),
                    prefix=prefix,
                )

                if ok and result:
                    self.searchResultList.setUpdatesEnabled(False)
                    for package in result:
                        itm = QTreeWidgetItem(self.searchResultList, [package])
                        itm.setExpanded(False)
                        for detail in result[package]:
                            version = detail["version"]
                            build = detail["build"]
                            platform = detail.get("subdir", detail.get("platform", ""))
                            citm = QTreeWidgetItem(itm, ["", version, build, platform])
                            citm.setData(0, self.PackageDetailedDataRole, detail)

                    self.searchResultList.sortItems(0, Qt.SortOrder.AscendingOrder)
                    self.searchResultList.resizeColumnToContents(0)
                    self.searchResultList.setUpdatesEnabled(True)
            if not ok:
                try:
                    message = result["message"]
                except KeyError:
                    message = result["error"]
                EricMessageBox.warning(
                    self, self.tr("Conda Search Package Error"), message
                )

    def __showDetails(self, item):
        """
        Private method to show a dialog with details about a package item.

        @param item reference to the package item
        @type QTreeWidgetItem
        """
        from .CondaPackageDetailsWidget import CondaPackageDetailsDialog

        details = item.data(0, self.PackageDetailedDataRole)
        if details:
            dlg = CondaPackageDetailsDialog(details, parent=self)
            dlg.exec()

    @pyqtSlot(str)
    def on_searchEdit_textChanged(self, txt):
        """
        Private slot handling changes of the entered search specification.

        @param txt current search entry
        @type str
        """
        self.searchButton.setEnabled(bool(txt))

    @pyqtSlot()
    def on_searchEdit_returnPressed(self):
        """
        Private slot handling the user pressing the Return button in the
        search edit.
        """
        self.__doSearch()

    @pyqtSlot()
    def on_searchButton_clicked(self):
        """
        Private slot handling the press of the search button.
        """
        self.__doSearch()

    @pyqtSlot()
    def on_installButton_clicked(self):
        """
        Private slot to install a selected package.
        """
        if len(self.searchResultList.selectedItems()) == 1:
            item = self.searchResultList.selectedItems()[0]
            if item.parent() is None:
                # it is just the package item
                package = item.text(0)
            else:
                # item with version and build
                package = "{0}={1}={2}".format(
                    item.parent().text(0),
                    item.text(1),
                    item.text(2),
                )

            prefix = self.environmentsComboBox.itemData(
                self.environmentsComboBox.currentIndex()
            )
            ok = self.__conda.installPackages([package], prefix=prefix)
            if ok:
                self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_showDetailsButton_clicked(self):
        """
        Private slot handling the 'Show Details' button.
        """
        item = self.searchResultList.selectedItems()[0]
        self.__showDetails(item)

    @pyqtSlot()
    def on_searchResultList_itemSelectionChanged(self):
        """
        Private slot handling a change of selected search results.
        """
        self.__updateSearchActionButtons()

    @pyqtSlot(QTreeWidgetItem)
    def on_searchResultList_itemExpanded(self, item):
        """
        Private slot handling the expansion of an item.

        @param item reference to the expanded item
        @type QTreeWidgetItem
        """
        for col in range(1, self.searchResultList.columnCount()):
            self.searchResultList.resizeColumnToContents(col)

    @pyqtSlot(QTreeWidgetItem, int)
    def on_searchResultList_itemDoubleClicked(self, item, _column):
        """
        Private slot handling a double click of an item.

        @param item reference to the item that was double clicked
        @type QTreeWidgetItem
        @param _column column of the double click (unused)
        @type int
        """
        if item.parent() is not None:
            self.__showDetails(item)

    @pyqtSlot(bool)
    def on_searchToggleButton_1_toggled(self, checked):
        """
        Private slot to toggle the search widget.

        @param checked state of the search widget button
        @type bool
        """
        self.searchWidget.setVisible(checked)
        self.searchToggleButton_2.setChecked(checked)

        if checked:
            self.searchEdit.setFocus(Qt.FocusReason.OtherFocusReason)
            self.searchEdit.selectAll()

            self.__updateSearchActionButtons()

    @pyqtSlot(bool)
    def on_searchToggleButton_2_toggled(self, checked):
        """
        Private slot to toggle the search widget.

        @param checked state of the search widget button
        @type bool
        """
        self.searchToggleButton_1.setChecked(checked)

    #######################################################################
    ## Menu related methods below
    #######################################################################

    @pyqtSlot()
    def __aboutToShowCondaMenu(self):
        """
        Private slot to handle the conda menu about to be shown.
        """
        selectedEnvironment = self.environmentsComboBox.currentText()
        enable = selectedEnvironment not in [""]
        for act in self.__envActs:
            act.setEnabled(enable)

        self.__deleteEnvAct.setEnabled(
            selectedEnvironment not in ["", self.__conda.RootName]
        )

    @pyqtSlot()
    def __aboutConda(self):
        """
        Private slot to show some information about the conda installation.
        """
        from .CondaInfoDialog import CondaInfoDialog

        infoDict = self.__conda.getCondaInformation()

        dlg = CondaInfoDialog(infoDict, parent=self)
        dlg.exec()

    @pyqtSlot()
    def __installPackages(self):
        """
        Private slot to install packages.
        """
        prefix = self.environmentsComboBox.itemData(
            self.environmentsComboBox.currentIndex()
        )
        if prefix:
            ok, packageSpecs = EricTextInputDialog.getText(
                self,
                self.tr("Install Packages"),
                self.tr("Package Specifications (separated by whitespace):"),
                QLineEdit.EchoMode.Normal,
                minimumWidth=600,
            )
            if ok and packageSpecs.strip():
                packages = [p.strip() for p in packageSpecs.split()]
                ok = self.__conda.installPackages(packages, prefix=prefix)
                if ok:
                    self.on_refreshButton_clicked()

    @pyqtSlot()
    def __installRequirements(self):
        """
        Private slot to install packages from requirements files.
        """
        prefix = self.environmentsComboBox.itemData(
            self.environmentsComboBox.currentIndex()
        )
        if prefix:
            requirements = EricFileDialog.getOpenFileNames(
                self,
                self.tr("Install Packages"),
                "",
                self.tr("Text Files (*.txt);;All Files (*)"),
            )
            if requirements:
                args = []
                for requirement in requirements:
                    args.extend(["--file", requirement])
                ok = self.__conda.installPackages(args, prefix=prefix)
                if ok:
                    self.on_refreshButton_clicked()

    @pyqtSlot()
    def __generateRequirements(self):
        """
        Private slot to generate a requirements file.
        """
        from .CondaExportDialog import CondaExportDialog

        prefix = self.environmentsComboBox.itemData(
            self.environmentsComboBox.currentIndex()
        )
        if prefix:
            env = self.environmentsComboBox.currentText()

            self.__requirementsDialog = CondaExportDialog(self.__conda, env, prefix)
            self.__requirementsDialog.show()
            QApplication.processEvents()
            self.__requirementsDialog.start()

    @pyqtSlot()
    def __cloneEnvironment(self):
        """
        Private slot to clone a conda environment.
        """
        from .CondaNewEnvironmentDataDialog import CondaNewEnvironmentDataDialog

        prefix = self.environmentsComboBox.itemData(
            self.environmentsComboBox.currentIndex()
        )
        if prefix:
            dlg = CondaNewEnvironmentDataDialog(
                self.tr("Clone Environment"), False, parent=self
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                virtEnvName, envName, _ = dlg.getData()
                args = [
                    "--name",
                    envName.strip(),
                    "--clone",
                    prefix,
                ]
                ok, prefix, interpreter = self.__conda.createCondaEnvironment(args)
                if ok:
                    metadata = VirtualenvMetaData(
                        name=virtEnvName,
                        path=prefix,
                        interpreter=interpreter,
                        is_conda=True,
                    )
                    ericApp().getObject("VirtualEnvManager").addVirtualEnv(metadata)

    @pyqtSlot()
    def __createEnvironment(self):
        """
        Private slot to create a conda environment from a requirements file.
        """
        from .CondaNewEnvironmentDataDialog import CondaNewEnvironmentDataDialog

        dlg = CondaNewEnvironmentDataDialog(
            self.tr("Create Environment"), True, parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            virtEnvName, envName, requirements = dlg.getData()
            args = [
                "--name",
                envName.strip(),
                "--file",
                requirements,
            ]
            ok, prefix, interpreter = self.__conda.createCondaEnvironment(args)
            if ok:
                metadata = VirtualenvMetaData(
                    name=virtEnvName,
                    path=prefix,
                    interpreter=interpreter,
                    is_conda=True,
                )
                ericApp().getObject("VirtualEnvManager").addVirtualEnv(metadata)

    @pyqtSlot()
    def __deleteEnvironment(self):
        """
        Private slot to delete a conda environment.
        """
        envName = self.environmentsComboBox.currentText()
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Delete Environment"),
            self.tr(
                """<p>Shall the environment <b>{0}</b> really be deleted?</p>"""
            ).format(envName),
        )
        if ok:
            self.__conda.removeCondaEnvironment(name=envName)

    @pyqtSlot()
    def __editUserConfiguration(self):
        """
        Private slot to edit the user configuration.
        """
        from eric7.QScintilla.MiniEditor import MiniEditor

        cfgFile = CondaInterface.userConfiguration()
        if not cfgFile:
            return

        if not os.path.exists(cfgFile):
            self.__conda.writeDefaultConfiguration()

        # check, if the destination is writeable
        if not os.access(cfgFile, os.W_OK):
            EricMessageBox.critical(
                self,
                self.tr("Edit Configuration"),
                self.tr(
                    """The configuration file "{0}" does not exist"""
                    """ or is not writable."""
                ).format(cfgFile),
            )
            return

        self.__editor = MiniEditor(cfgFile, "YAML")
        self.__editor.show()

    @pyqtSlot()
    def __condaConfigure(self):
        """
        Private slot to open the configuration page.
        """
        ericApp().getObject("UserInterface").showPreferences("condaPage")

    @pyqtSlot()
    def on_recheckButton_clicked(self):
        """
        Private slot to re-check the availability of conda and adjust the
        interface if it became available.
        """
        if CondaInterface.isCondaAvailable():
            self.__initCondaInterface()

            self.notAvailableWidget.hide()
            self.baseWidget.show()
