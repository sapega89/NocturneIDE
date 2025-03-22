# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the pip packages management widget.
"""

import contextlib
import enum
import os

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from PyQt6.QtCore import Qt, QUrl, QUrlQuery, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QHeaderView,
    QMenu,
    QToolButton,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .PipVulnerabilityChecker import Package, VulnerabilityCheckError
from .Ui_PipPackagesWidget import Ui_PipPackagesWidget


class PipPackageInformationMode(enum.Enum):
    """
    Class defining the show information process modes.
    """

    General = 0
    Classifiers = 1
    EntryPoints = 2
    FilesList = 3
    UrlsList = 4


class PipPackagesWidget(QWidget, Ui_PipPackagesWidget):
    """
    Class implementing the pip packages management widget.
    """

    SearchVersionRole = Qt.ItemDataRole.UserRole + 1
    VulnerabilityRole = Qt.ItemDataRole.UserRole + 2

    PackageColumn = 0
    InstalledVersionColumn = 1
    AvailableVersionColumn = 2
    VulnerabilityColumn = 3

    DepPackageColumn = 0
    DepInstalledVersionColumn = 1
    DepRequiredVersionColumn = 2

    def __init__(self, pip, parent=None):
        """
        Constructor

        @param pip reference to the global pip interface
        @type Pip
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.layout().setContentsMargins(0, 3, 0, 0)

        self.viewToggleButton.setIcon(EricPixmapCache.getIcon("viewListTree"))

        self.pipMenuButton.setObjectName("pip_supermenu_button")
        self.pipMenuButton.setIcon(EricPixmapCache.getIcon("superMenu"))
        self.pipMenuButton.setToolTip(self.tr("pip Menu"))
        self.pipMenuButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.pipMenuButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.pipMenuButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pipMenuButton.setShowMenuInside(True)

        self.refreshButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.installButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.upgradeButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.upgradeAllButton.setIcon(EricPixmapCache.getIcon("2uparrow"))
        self.uninstallButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.showPackageDetailsButton.setIcon(EricPixmapCache.getIcon("info"))
        self.searchButton.setIcon(EricPixmapCache.getIcon("find"))
        self.cleanupButton.setIcon(EricPixmapCache.getIcon("clear"))

        self.refreshDependenciesButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.showDepPackageDetailsButton.setIcon(EricPixmapCache.getIcon("info"))
        self.dependencyRepairButton.setIcon(EricPixmapCache.getIcon("repair"))
        self.dependencyRepairAllButton.setIcon(EricPixmapCache.getIcon("repairAll"))

        self.__pip = pip

        self.packagesList.header().setSortIndicator(
            PipPackagesWidget.PackageColumn, Qt.SortOrder.AscendingOrder
        )
        self.dependenciesList.header().setSortIndicator(
            PipPackagesWidget.DepPackageColumn, Qt.SortOrder.AscendingOrder
        )

        self.__infoLabels = {
            "author": self.tr("Author:"),
            "author-email": self.tr("Author Email:"),
            "classifiers": self.tr("Classifiers:"),
            "entry-points": self.tr("Entry Points:"),
            "files": self.tr("Files:"),
            "home-page": self.tr("Homepage:"),
            "installer": self.tr("Installer:"),
            "license": self.tr("License:"),
            "location": self.tr("Location:"),
            "metadata-version": self.tr("Metadata Version:"),
            "name": self.tr("Name:"),
            "project-urls": self.tr("Project URLs:"),
            "requires": self.tr("Requires:"),
            "required-by": self.tr("Required By:"),
            "summary": self.tr("Summary:"),
            "version": self.tr("Version:"),
        }
        self.packageInfoWidget.setHeaderLabels(["Key", "Value"])
        self.dependencyInfoWidget.setHeaderLabels(["Key", "Value"])

        venvManager = ericApp().getObject("VirtualEnvManager")
        venvManager.virtualEnvironmentAdded.connect(self.on_refreshButton_clicked)
        venvManager.virtualEnvironmentRemoved.connect(self.on_refreshButton_clicked)
        self.__selectedEnvironment = None

        with contextlib.suppress(KeyError):
            project = ericApp().getObject("Project")
            project.projectOpened.connect(self.__projectOpened)
            project.projectClosed.connect(self.__projectClosed)

        self.__packageDetailsDialog = None

        self.installButton.clicked.connect(self.__installPackages)

        self.__initPipMenu()
        self.__populateEnvironments()
        self.__updateActionButtons()
        self.__updateDepActionButtons()

        self.statusLabel.hide()
        self.__lastSearchPage = 0

        self.__queryName = []
        self.__querySummary = []

        self.__replies = []

        self.viewsStackWidget.setCurrentWidget(self.packagesPage)
        self.on_packagesList_itemSelectionChanged()

        self.preferencesChanged()  # perform preferences dependent configuration

    @pyqtSlot()
    def __projectOpened(self):
        """
        Private slot to handle the projectOpened signal.
        """
        projectVenv = self.__pip.getProjectEnvironmentString()
        if projectVenv:
            self.environmentsComboBox.insertItem(1, projectVenv)

    @pyqtSlot(bool)
    def __projectClosed(self, shutdown):
        """
        Private slot to handle the projectClosed signal.

        @param shutdown flag indicating the IDE shutdown
        @type bool
        """
        if not shutdown:
            # the project entry is always at index 1
            if self.environmentsComboBox.currentIndex() == 1:
                self.environmentsComboBox.setCurrentIndex(0)

            self.environmentsComboBox.removeItem(1)

    def __populateEnvironments(self):
        """
        Private method to get a list of environments and populate the selector.
        """
        self.environmentsComboBox.addItem("")
        projectVenv = self.__pip.getProjectEnvironmentString()
        if projectVenv:
            self.environmentsComboBox.addItem(projectVenv)
        self.environmentsComboBox.addItems(
            self.__pip.getVirtualenvNames(
                noRemote=True,
                noConda=Preferences.getPip("ExcludeCondaEnvironments"),
                noGlobals=Preferences.getPip("ExcludeGlobalEnvironments"),
                noServer=True,
            )
        )

    def __isPipAvailable(self):
        """
        Private method to check, if the pip package is available for the
        selected environment.

        @return flag indicating availability
        @rtype bool
        """
        available = False

        venvName = self.environmentsComboBox.currentText()
        if venvName:
            available = (
                len(
                    self.packagesList.findItems(
                        "pip",
                        Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive,
                    )
                )
                == 1
            )

        return available

    def __availablePipVersion(self):
        """
        Private method to get the pip version of the selected environment.

        @return tuple containing the version number or tuple with all zeros
            in case pip is not available
        @rtype tuple of int
        """
        pipVersionTuple = (0, 0, 0)
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            pipList = self.packagesList.findItems(
                "pip", Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive
            )
            if len(pipList) > 0:
                pipVersionTuple = EricUtilities.versionToTuple(
                    pipList[0].text(PipPackagesWidget.InstalledVersionColumn)
                )

        return pipVersionTuple

    def getPip(self):
        """
        Public method to get a reference to the pip interface object.

        @return reference to the pip interface object
        @rtype Pip
        """
        return self.__pip

    #######################################################################
    ## Slots handling widget signals below
    #######################################################################

    def __selectedUpdateableItems(self):
        """
        Private method to get a list of selected items that can be updated.

        @return list of selected items that can be updated
        @rtype list of QTreeWidgetItem
        """
        return [
            itm
            for itm in self.packagesList.selectedItems()
            if bool(itm.text(PipPackagesWidget.AvailableVersionColumn))
        ]

    def __allPackageNames(self):
        """
        Private method to get a list of all package names.

        @return list of all package names
        @rtype list of str
        """
        packages = []
        for index in range(self.packagesList.topLevelItemCount()):
            packages.append(self.packagesList.topLevelItem(index).text(0))
        return packages

    def __allUpdateableItems(self):
        """
        Private method to get a list of all items that can be updated.

        @return list of all items that can be updated
        @rtype list of QTreeWidgetItem
        """
        updateableItems = []
        for index in range(self.packagesList.topLevelItemCount()):
            itm = self.packagesList.topLevelItem(index)
            if itm.text(PipPackagesWidget.AvailableVersionColumn):
                updateableItems.append(itm)

        return updateableItems

    def __updateActionButtons(self):
        """
        Private method to set the state of the action buttons.
        """
        if self.__isPipAvailable():
            self.installButton.setEnabled(True)
            self.upgradeButton.setEnabled(bool(self.__selectedUpdateableItems()))
            self.uninstallButton.setEnabled(bool(self.packagesList.selectedItems()))
            self.upgradeAllButton.setEnabled(bool(self.__allUpdateableItems()))
            self.showPackageDetailsButton.setEnabled(
                len(self.packagesList.selectedItems()) == 1
            )
            self.cleanupButton.setEnabled(True)
        else:
            self.installButton.setEnabled(False)
            self.upgradeButton.setEnabled(False)
            self.uninstallButton.setEnabled(False)
            self.upgradeAllButton.setEnabled(False)
            self.showPackageDetailsButton.setEnabled(False)
            self.cleanupButton.setEnabled(False)

    def __refreshPackagesList(self):
        """
        Private method to refresh the packages list.
        """
        self.packagesList.clear()
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            interpreter = self.__pip.getVirtualenvInterpreter(venvName)
            if interpreter:
                self.statusLabel.show()
                self.statusLabel.setText(self.tr("Getting installed packages..."))

                with EricOverrideCursor():
                    # 1. populate with installed packages
                    installedPackages = self.__pip.getInstalledPackages(
                        venvName,
                        localPackages=self.localCheckBox.isChecked(),
                        notRequired=self.notRequiredCheckBox.isChecked(),
                        usersite=self.userCheckBox.isChecked(),
                    )
                    for package, version in installedPackages:
                        QTreeWidgetItem(self.packagesList, [package, version, "", ""])
                    self.packagesList.sortItems(
                        PipPackagesWidget.PackageColumn, Qt.SortOrder.AscendingOrder
                    )
                    self.packagesList.resizeColumnToContents(
                        PipPackagesWidget.PackageColumn
                    )
                    self.packagesList.resizeColumnToContents(
                        PipPackagesWidget.InstalledVersionColumn
                    )

                    # 2. update with vulnerability information
                    if self.vulnerabilityCheckBox.isChecked():
                        self.__updateVulnerabilityData()
                        self.packagesList.resizeColumnToContents(
                            PipPackagesWidget.VulnerabilityColumn
                        )
                    self.statusLabel.setText(self.tr("Getting outdated packages..."))

                    # 3. update with update information
                    self.__pip.getOutdatedPackages(
                        venvName,
                        localPackages=self.localCheckBox.isChecked(),
                        notRequired=self.notRequiredCheckBox.isChecked(),
                        usersite=self.userCheckBox.isChecked(),
                        callback=self.__updateOutdatedInfo,
                    )

        else:
            self.__updateActionButtons()

    def __updateOutdatedInfo(self, outdatedPackages):
        """
        Private method to process the list of outdated packages.

        @param outdatedPackages dictionary with the package name as key and
            a tuple containing the installed and available version as the value
        @type dict of [str: (str, str)]
        """
        for row in range(self.packagesList.topLevelItemCount()):
            item = self.packagesList.topLevelItem(row)
            with contextlib.suppress(KeyError):
                item.setText(
                    PipPackagesWidget.AvailableVersionColumn,
                    outdatedPackages[item.text(0)][1],
                )
        self.packagesList.resizeColumnToContents(
            PipPackagesWidget.AvailableVersionColumn
        )

        self.__updateActionButtons()

        self.statusLabel.hide()

    @pyqtSlot(str)
    def on_environmentsComboBox_currentTextChanged(self, name):
        """
        Private slot handling the selection of a Python environment.

        @param name name of the selected Python environment
        @type str
        """
        if name != self.__selectedEnvironment:
            if name:
                self.environmentPathLabel.setPath(
                    self.__pip.getVirtualenvInterpreter(name)
                )
            else:
                self.environmentPathLabel.setPath("")
                if self.__packageDetailsDialog is not None:
                    self.__packageDetailsDialog.close()

            if self.viewToggleButton.isChecked():
                self.__refreshDependencyTree()
            else:
                self.__refreshPackagesList()
            self.__selectedEnvironment = name

            self.__updateActionButtons()

    @pyqtSlot()
    def on_localCheckBox_clicked(self):
        """
        Private slot handling the switching of the local mode.
        """
        self.__refreshPackagesList()

    @pyqtSlot()
    def on_notRequiredCheckBox_clicked(self):
        """
        Private slot handling the switching of the 'not required' mode.
        """
        self.__refreshPackagesList()

    @pyqtSlot()
    def on_userCheckBox_clicked(self):
        """
        Private slot handling the switching of the 'user-site' mode.
        """
        self.__refreshPackagesList()

    def __showPackageInformation(self, packageName, infoWidget):
        """
        Private method to show information for a package.

        @param packageName name of the package
        @type str
        @param infoWidget reference to the widget to contain the information
        @type QTreeWidget
        """
        environment = self.environmentsComboBox.currentText()
        interpreter = self.__pip.getVirtualenvInterpreter(environment)
        if not interpreter:
            return

        args = ["-m", "pip", "show"]
        if self.verboseCheckBox.isChecked():
            args.append("--verbose")
        if self.installedFilesCheckBox.isChecked():
            args.append("--files")
        args.append(packageName)

        with EricOverrideCursor():
            success, output = self.__pip.runProcess(args, interpreter)

            if success and output:
                mode = PipPackageInformationMode.General
                for line in output.splitlines():
                    line = line.rstrip()
                    if line and line != "---":
                        if mode != PipPackageInformationMode.General:
                            if line[0] == " ":
                                QTreeWidgetItem(infoWidget, [" ", line.strip()])
                            else:
                                mode = PipPackageInformationMode.General
                        if mode == PipPackageInformationMode.General:
                            try:
                                label, info = line.split(": ", 1)
                            except ValueError:
                                label = line[:-1]
                                info = ""
                            label = label.lower()
                            if label in self.__infoLabels:
                                QTreeWidgetItem(
                                    infoWidget, [self.__infoLabels[label], info]
                                )
                            if label == "files":
                                mode = PipPackageInformationMode.FilesList
                            elif label == "classifiers":
                                mode = PipPackageInformationMode.Classifiers
                            elif label == "entry-points":
                                mode = PipPackageInformationMode.EntryPoints
                            elif label == "project-urls":
                                mode = PipPackageInformationMode.UrlsList
                infoWidget.scrollToTop()

            header = infoWidget.header()
            header.setStretchLastSection(False)
            header.resizeSections(QHeaderView.ResizeMode.ResizeToContents)
            if header.sectionSize(0) + header.sectionSize(1) < header.width():
                header.setStretchLastSection(True)

    @pyqtSlot()
    def on_packagesList_itemSelectionChanged(self):
        """
        Private slot reacting on a change of selected items.
        """
        self.packageInfoWidget.clear()
        self.vulnerabilitiesInfoWidget.clear()

        if len(self.packagesList.selectedItems()) == 1:
            # one item was selected, show info for that item
            curr = self.packagesList.selectedItems()[0]
            self.__showPackageInformation(
                curr.text(PipPackagesWidget.PackageColumn), self.packageInfoWidget
            )
            if bool(curr.text(PipPackagesWidget.VulnerabilityColumn)):
                self.__showVulnerabilityInformation(
                    curr.text(PipPackagesWidget.PackageColumn),
                    curr.text(PipPackagesWidget.InstalledVersionColumn),
                    curr.data(
                        PipPackagesWidget.VulnerabilityColumn,
                        PipPackagesWidget.VulnerabilityRole,
                    ),
                )
                self.infoWidget.tabBar().show()
            else:
                self.infoWidget.tabBar().hide()
            self.infoWidget.setCurrentIndex(0)
        else:
            # multiple items or none were selected
            self.infoWidget.tabBar().hide()

        self.__updateActionButtons()

    @pyqtSlot(QTreeWidgetItem, int)
    def on_packagesList_itemActivated(self, item, column):
        """
        Private slot reacting on a package item being activated.

        @param item reference to the activated item
        @type QTreeWidgetItem
        @param column activated column
        @type int
        """
        packageName = item.text(PipPackagesWidget.PackageColumn)
        upgradable = bool(item.text(PipPackagesWidget.AvailableVersionColumn))
        if column == PipPackagesWidget.InstalledVersionColumn:
            # show details for installed version
            packageVersion = item.text(PipPackagesWidget.InstalledVersionColumn)
        else:
            # show details for available version or installed one
            if item.text(PipPackagesWidget.AvailableVersionColumn):
                packageVersion = item.text(PipPackagesWidget.AvailableVersionColumn)
            else:
                packageVersion = item.text(PipPackagesWidget.InstalledVersionColumn)

        vulnerabilities = (
            item.data(
                PipPackagesWidget.VulnerabilityColumn,
                PipPackagesWidget.VulnerabilityRole,
            )
            if bool(item.text(PipPackagesWidget.VulnerabilityColumn))
            else []
        )

        self.__showPackageDetails(
            packageName,
            packageVersion,
            vulnerabilities=vulnerabilities,
            upgradable=upgradable,
        )

    @pyqtSlot(bool)
    def on_verboseCheckBox_clicked(self, checked):
        """
        Private slot to handle a change of the verbose package information
        checkbox.

        @param checked state of the checkbox
        @type bool
        """
        self.on_packagesList_itemSelectionChanged()

    @pyqtSlot(bool)
    def on_installedFilesCheckBox_clicked(self, checked):
        """
        Private slot to handle a change of the installed files information
        checkbox.

        @param checked state of the checkbox
        @type bool
        """
        self.on_packagesList_itemSelectionChanged()

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
        packages = [
            itm.text(PipPackagesWidget.PackageColumn)
            for itm in self.__selectedUpdateableItems()
        ]
        if packages:
            self.executeUpgradePackages(packages)

    @pyqtSlot()
    def on_upgradeAllButton_clicked(self):
        """
        Private slot to upgrade all packages of the selected environment.
        """
        packages = [
            itm.text(PipPackagesWidget.PackageColumn)
            for itm in self.__allUpdateableItems()
        ]
        if packages:
            self.executeUpgradePackages(packages)

    @pyqtSlot()
    def on_uninstallButton_clicked(self):
        """
        Private slot to remove selected packages of the selected environment.
        """
        packages = [
            itm.text(PipPackagesWidget.PackageColumn)
            for itm in self.packagesList.selectedItems()
        ]
        self.executeUninstallPackages(packages)

    def executeUninstallPackages(self, packages):
        """
        Public method to uninstall the given list of packages.

        @param packages list of package names to be uninstalled
        @type list of str
        """
        if packages:
            ok = self.__pip.uninstallPackages(
                packages, venvName=self.environmentsComboBox.currentText()
            )
            if ok:
                self.on_refreshButton_clicked()

    def executeUpgradePackages(self, packages):
        """
        Public method to execute the pip upgrade command.

        @param packages list of package names to be upgraded
        @type list of str
        """
        ok = self.__pip.upgradePackages(
            packages,
            venvName=self.environmentsComboBox.currentText(),
            userSite=self.userCheckBox.isChecked(),
        )
        if ok:
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_showPackageDetailsButton_clicked(self):
        """
        Private slot to show information for the selected package.
        """
        item = self.packagesList.selectedItems()[0]
        if item:
            packageName = item.text(PipPackagesWidget.PackageColumn)
            upgradable = bool(item.text(PipPackagesWidget.AvailableVersionColumn))
            # show details for available version or installed one
            if item.text(PipPackagesWidget.AvailableVersionColumn):
                packageVersion = item.text(PipPackagesWidget.AvailableVersionColumn)
            else:
                packageVersion = item.text(PipPackagesWidget.InstalledVersionColumn)

            vulnerabilities = (
                item.data(
                    PipPackagesWidget.VulnerabilityColumn,
                    PipPackagesWidget.VulnerabilityRole,
                )
                if bool(item.text(PipPackagesWidget.VulnerabilityColumn))
                else []
            )

            self.__showPackageDetails(
                packageName,
                packageVersion,
                vulnerabilities=vulnerabilities,
                upgradable=upgradable,
            )

    @pyqtSlot()
    def on_cleanupButton_clicked(self):
        """
        Private slot to cleanup the site-packages directory of the selected
        environment.
        """
        envName = self.environmentsComboBox.currentText()
        if envName:
            ok = self.__pip.runCleanup(envName=envName)
            if ok:
                EricMessageBox.information(
                    self,
                    self.tr("Cleanup Environment"),
                    self.tr("The environment cleanup was successful."),
                )
            else:
                EricMessageBox.warning(
                    self,
                    self.tr("Cleanup Environment"),
                    self.tr(
                        "Some leftover package directories could not been removed."
                        " Delete them manually."
                    ),
                )

    @pyqtSlot()
    def on_searchButton_clicked(self):
        """
        Private slot to open a web browser for package searching.
        """
        url = QUrl(self.__pip.getIndexUrlSearch())

        searchTerm = self.searchEdit.text().strip()
        if searchTerm:
            searchTerm = bytes(QUrl.toPercentEncoding(searchTerm)).decode()
            urlQuery = QUrlQuery()
            urlQuery.addQueryItem("q", searchTerm)
            url.setQuery(urlQuery)

        QDesktopServices.openUrl(url)

    @pyqtSlot()
    def on_searchEdit_returnPressed(self):
        """
        Private slot to handle the press of the Return key in the search line edit.
        """
        self.on_searchButton_clicked()

    def executeInstallPackages(self, packages, userSite=False):
        """
        Public method to install the given list of packages.

        @param packages list of package names to be installed
        @type list of str
        @param userSite flag indicating to install to the user directory
        @type bool
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName and packages:
            self.__pip.installPackages(packages, venvName=venvName, userSite=userSite)
            self.on_refreshButton_clicked()

    def __showPackageDetails(
        self,
        packageName,
        packageVersion,
        vulnerabilities=None,
        upgradable=False,
        installable=False,
    ):
        """
        Private method to populate the package details dialog.

        @param packageName name of the package to show details for
        @type str
        @param packageVersion version of the package
        @type str
        @param vulnerabilities list of known vulnerabilities (defaults to None)
        @type list (optional)
        @param upgradable flag indicating that the package may be upgraded
            (defaults to False)
        @type bool (optional)
        @param installable flag indicating that the package may be installed
            (defaults to False)
        @type bool (optional)
        """
        from .PipPackageDetailsDialog import PipPackageDetailsDialog

        with EricOverrideCursor():
            packageData = self.__pip.getPackageDetails(packageName, packageVersion)

        if packageData:
            if installable:
                buttonsMode = PipPackageDetailsDialog.ButtonInstall
            elif upgradable:
                buttonsMode = (
                    PipPackageDetailsDialog.ButtonRemove
                    | PipPackageDetailsDialog.ButtonUpgrade
                )
            else:
                buttonsMode = PipPackageDetailsDialog.ButtonRemove

            if self.__packageDetailsDialog is not None:
                self.__packageDetailsDialog.close()

            self.__packageDetailsDialog = PipPackageDetailsDialog(
                packageData,
                vulnerabilities=vulnerabilities,
                buttonsMode=buttonsMode,
                parent=self,
            )
            self.__packageDetailsDialog.show()
        else:
            EricMessageBox.warning(
                self,
                self.tr("Search PyPI"),
                self.tr(
                    """<p>No package details info for <b>{0}</b>"""
                    """ available.</p>"""
                ).format(packageName),
            )

    #######################################################################
    ## Menu related methods below
    #######################################################################

    def __initPipMenu(self):
        """
        Private method to create the super menu and attach it to the super
        menu button.
        """
        ###################################################################
        ## Menu with pip related actions
        ###################################################################

        self.__pipSubmenu = QMenu(self.tr("Pip"))
        self.__installPipAct = self.__pipSubmenu.addAction(
            self.tr("Install Pip"), self.__installPip
        )
        self.__installPipUserAct = self.__pipSubmenu.addAction(
            self.tr("Install Pip to User-Site"), self.__installPipUser
        )
        self.__repairPipAct = self.__pipSubmenu.addAction(
            self.tr("Repair Pip"), self.__repairPip
        )

        ###################################################################
        ## Menu with install related actions
        ###################################################################

        self.__installSubmenu = QMenu(self.tr("Install"))
        self.__installPackagesAct = self.__installSubmenu.addAction(
            self.tr("Install Packages"), self.__installPackages
        )
        self.__installLocalPackageAct = self.__installSubmenu.addAction(
            self.tr("Install Local Package"), self.__installLocalPackage
        )
        self.__reinstallPackagesAct = self.__installSubmenu.addAction(
            self.tr("Re-Install Selected Packages"), self.__reinstallPackages
        )

        ###################################################################
        ## Menu for requirements and constraints management
        ###################################################################

        self.__requirementsSubenu = QMenu(self.tr("Requirements/Constraints"))
        self.__installRequirementsAct = self.__requirementsSubenu.addAction(
            self.tr("Install Requirements"), self.__installRequirements
        )
        self.__uninstallRequirementsAct = self.__requirementsSubenu.addAction(
            self.tr("Uninstall Requirements"), self.__uninstallRequirements
        )
        self.__generateRequirementsAct = self.__requirementsSubenu.addAction(
            self.tr("Generate Requirements..."), self.__generateRequirements
        )
        self.__requirementsSubenu.addSeparator()
        self.__installPyprojectAct = self.__requirementsSubenu.addAction(
            self.tr("Install from 'pyproject.toml'"),
            self.__installPyprojectDependencies,
        )
        self.__uninstallPyprojectAct = self.__requirementsSubenu.addAction(
            self.tr("Uninstall from 'pyproject.toml'"),
            self.__uninstallPyprojectDependencies,
        )
        self.__requirementsSubenu.addSeparator()
        self.__generateConstraintsAct = self.__requirementsSubenu.addAction(
            self.tr("Generate Constraints..."), self.__generateConstraints
        )

        ###################################################################
        ## Menu for requirements and constraints management
        ###################################################################

        self.__cacheSubmenu = QMenu(self.tr("Cache"))
        self.__cacheInfoAct = self.__cacheSubmenu.addAction(
            self.tr("Show Cache Info..."), self.__showCacheInfo
        )
        self.__cacheShowListAct = self.__cacheSubmenu.addAction(
            self.tr("Show Cached Files..."), self.__showCacheList
        )
        self.__cacheRemoveAct = self.__cacheSubmenu.addAction(
            self.tr("Remove Cached Files..."), self.__removeCachedFiles
        )
        self.__cachePurgeAct = self.__cacheSubmenu.addAction(
            self.tr("Purge Cache..."), self.__purgeCache
        )

        ###################################################################
        ## Main menu
        ###################################################################

        self.__pipMenu = QMenu()
        self.__pipSubmenuAct = self.__pipMenu.addMenu(self.__pipSubmenu)
        self.__pipMenu.addSeparator()
        self.__installSubmenuAct = self.__pipMenu.addMenu(self.__installSubmenu)
        self.__pipMenu.addSeparator()
        self.__requirementsSubmenuAct = self.__pipMenu.addMenu(
            self.__requirementsSubenu
        )
        self.__pipMenu.addSeparator()
        self.__showLicensesDialogAct = self.__pipMenu.addAction(
            self.tr("Show Licenses..."), self.__showLicensesDialog
        )
        self.__pipMenu.addSeparator()
        self.__checkVulnerabilityAct = self.__pipMenu.addAction(
            self.tr("Check Vulnerabilities"), self.__checkVulnerability
        )
        # updateVulnerabilityDbAct
        self.__updateVulnerabilitiesAct = self.__pipMenu.addAction(
            self.tr("Update Vulnerability Database"), self.__updateVulnerabilityDbCache
        )
        self.__pipMenu.addSeparator()
        self.__cyclonedxAct = self.__pipMenu.addAction(
            self.tr("Create SBOM file"), self.__createSBOMFile
        )
        self.__pipMenu.addSeparator()
        self.__cacheSubmenuAct = self.__pipMenu.addMenu(self.__cacheSubmenu)
        self.__pipMenu.addSeparator()
        # editUserConfigAct
        self.__pipMenu.addAction(
            self.tr("Edit User Configuration..."), self.__editUserConfiguration
        )
        self.__editVirtualenvConfigAct = self.__pipMenu.addAction(
            self.tr("Edit Environment Configuration..."),
            self.__editVirtualenvConfiguration,
        )
        self.__pipMenu.addSeparator()
        # pipConfigAct
        self.__pipMenu.addAction(self.tr("Configure..."), self.__pipConfigure)

        self.__pipMenu.aboutToShow.connect(self.__aboutToShowPipMenu)

        self.pipMenuButton.setMenu(self.__pipMenu)

    def __aboutToShowPipMenu(self):
        """
        Private slot to set the action enabled status.
        """
        enable = bool(self.environmentsComboBox.currentText())
        enablePip = self.__isPipAvailable()
        enablePipCache = self.__availablePipVersion() >= (20, 1, 0)

        self.__pipSubmenuAct.setEnabled(enable)
        self.__installPipAct.setEnabled(not enablePip)
        self.__installPipUserAct.setEnabled(not enablePip)
        self.__repairPipAct.setEnabled(enablePip)

        self.__installSubmenu.setEnabled(enablePip)

        self.__requirementsSubmenuAct.setEnabled(enablePip)

        self.__cacheSubmenuAct.setEnabled(enablePipCache)

        self.__editVirtualenvConfigAct.setEnabled(enable)

        self.__checkVulnerabilityAct.setEnabled(
            enable
            and self.vulnerabilityCheckBox.isEnabled()
            and Preferences.getPip("VulnerabilityCheckEnabled")
        )
        self.__updateVulnerabilitiesAct.setEnabled(
            enable and Preferences.getPip("VulnerabilityCheckEnabled")
        )

        self.__cyclonedxAct.setEnabled(enable)

        self.__showLicensesDialogAct.setEnabled(enable)

    @pyqtSlot()
    def __installPip(self):
        """
        Private slot to install pip into the selected environment.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.installPip(venvName)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __installPipUser(self):
        """
        Private slot to install pip into the user site for the selected
        environment.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.installPip(venvName, userSite=True)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __repairPip(self):
        """
        Private slot to repair the pip installation of the selected
        environment.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.repairPip(venvName)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __installPackages(self):
        """
        Private slot to install packages to be given by the user.
        """
        from .PipPackagesInputDialog import PipPackagesInputDialog

        venvName = self.environmentsComboBox.currentText()
        if venvName:
            dlg = PipPackagesInputDialog(self.tr("Install Packages"), parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                packages, user = dlg.getData()
                self.executeInstallPackages(packages, userSite=user)

    @pyqtSlot()
    def __installLocalPackage(self):
        """
        Private slot to install a package available on local storage.
        """
        from .PipFileSelectionDialog import PipFileSelectionDialog

        venvName = self.environmentsComboBox.currentText()
        if venvName:
            dlg = PipFileSelectionDialog("package", parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                package, user = dlg.getData()
                if package and os.path.exists(package):
                    self.executeInstallPackages([package], userSite=user)

    @pyqtSlot()
    def __reinstallPackages(self):
        """
        Private slot to force a re-installation of the selected packages.
        """
        packages = [
            itm.text(PipPackagesWidget.PackageColumn)
            for itm in self.packagesList.selectedItems()
        ]
        venvName = self.environmentsComboBox.currentText()
        if venvName and packages:
            self.__pip.installPackages(packages, venvName=venvName, forceReinstall=True)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __installRequirements(self):
        """
        Private slot to install packages as given in a requirements file.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.installRequirements(venvName)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __uninstallRequirements(self):
        """
        Private slot to uninstall packages as given in a requirements file.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.uninstallRequirements(venvName)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __generateRequirements(self):
        """
        Private slot to generate the contents for a requirements file.
        """
        from .PipFreezeDialog import PipFreezeDialog, PipFreezeDialogModes

        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__freezeDialog = PipFreezeDialog(
                self.__pip, mode=PipFreezeDialogModes.Requirements, parent=self
            )
            self.__freezeDialog.show()
            self.__freezeDialog.start(venvName)

    @pyqtSlot()
    def __generateConstraints(self):
        """
        Private slot to generate the contents for a constraints file.
        """
        from .PipFreezeDialog import PipFreezeDialog, PipFreezeDialogModes

        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__freezeDialog = PipFreezeDialog(
                self.__pip, mode=PipFreezeDialogModes.Constraints, parent=self
            )
            self.__freezeDialog.show()
            self.__freezeDialog.start(venvName)

    @pyqtSlot()
    def __installPyprojectDependencies(self):
        """
        Private slot to install packages as given in a 'pyproject.toml' file.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.installPyprojectDependencies(venvName)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __uninstallPyprojectDependencies(self):
        """
        Private slot to uninstall packages as given in a 'pyproject.toml' file.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.uninstallPyprojectDependencies(venvName)
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def __editUserConfiguration(self):
        """
        Private slot to edit the user configuration.
        """
        self.__editConfiguration()

    @pyqtSlot()
    def __editVirtualenvConfiguration(self):
        """
        Private slot to edit the configuration of the selected environment.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__editConfiguration(venvName=venvName)

    def __editConfiguration(self, venvName=""):
        """
        Private method to edit a configuration.

        @param venvName name of the environment to act upon
        @type str
        """
        from eric7.QScintilla.MiniEditor import MiniEditor

        if venvName:
            cfgFile = self.__pip.getVirtualenvConfig(venvName)
            if not cfgFile:
                return
        else:
            cfgFile = self.__pip.getUserConfig()
        cfgDir = os.path.dirname(cfgFile)
        if not cfgDir:
            EricMessageBox.critical(
                None,
                self.tr("Edit Configuration"),
                self.tr("""No valid configuration path determined. Aborting"""),
            )
            return

        try:
            if not os.path.isdir(cfgDir):
                os.makedirs(cfgDir)
        except OSError:
            EricMessageBox.critical(
                None,
                self.tr("Edit Configuration"),
                self.tr("""No valid configuration path determined. Aborting"""),
            )
            return

        if not os.path.exists(cfgFile):
            with contextlib.suppress(OSError), open(cfgFile, "w") as f:
                f.write("[global]\n")

        # check, if the destination is writeable
        if not os.access(cfgFile, os.W_OK):
            EricMessageBox.critical(
                None,
                self.tr("Edit Configuration"),
                self.tr("""No valid configuration path determined. Aborting"""),
            )
            return

        self.__editor = MiniEditor(cfgFile, "Properties")
        self.__editor.show()

    def __pipConfigure(self):
        """
        Private slot to open the configuration page.
        """
        try:
            ericApp().getObject("UserInterface").showPreferences("pipPage")
        except KeyError:
            # we were called from outside the eric IDE
            from eric7.Preferences.ConfigurationDialog import (  # noqa: I101
                ConfigurationDialog,
                ConfigurationMode,
            )

            dlg = ConfigurationDialog(
                parent=self,
                name="Configuration",
                modal=True,
                fromEric=False,
                displayMode=ConfigurationMode.PIPMANAGERMODE,
            )
            dlg.show()
            dlg.showConfigurationPageByName("pipPage")
            dlg.exec()
            if dlg.result() == QDialog.DialogCode.Accepted:
                dlg.setPreferences()
                Preferences.syncPreferences()
                self.preferencesChanged()

    @pyqtSlot()
    def __showCacheInfo(self):
        """
        Private slot to show information about the cache.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.showCacheInfo(venvName)

    @pyqtSlot()
    def __showCacheList(self):
        """
        Private slot to show a list of cached files.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.cacheList(venvName)

    @pyqtSlot()
    def __removeCachedFiles(self):
        """
        Private slot to remove files from the pip cache.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.cacheRemove(venvName)

    @pyqtSlot()
    def __purgeCache(self):
        """
        Private slot to empty the pip cache.
        """
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            self.__pip.cachePurge(venvName)

    ##################################################################
    ## Interface to the vulnerability checks below
    ##################################################################

    @pyqtSlot(bool)
    def setVulnerabilityEnabled(self, enable):
        """
        Public slot to set the enabled state of the vulnerability checks.

        @param enable vulnerability checks enabled state
        @type bool
        """
        self.vulnerabilityCheckBox.setChecked(enable)
        self.vulnerabilityCheckBox.setEnabled(enable)
        self.packagesList.setColumnHidden(
            PipPackagesWidget.VulnerabilityColumn, not enable
        )
        if not enable:
            self.__clearVulnerabilityInfo()

    @pyqtSlot(bool)
    def on_vulnerabilityCheckBox_clicked(self, checked):
        """
        Private slot handling a change of the automatic vulnerability checks.

        @param checked flag indicating the state of the check box
        @type bool
        """
        if checked:
            self.__updateVulnerabilityData(clearFirst=True)
        else:
            self.__clearVulnerabilityInfo()

        self.packagesList.header().setSectionHidden(
            PipPackagesWidget.VulnerabilityColumn, not checked
        )

    @pyqtSlot()
    def __checkVulnerability(self):
        """
        Private slot to update and show the vulnerability data (called from the menu).
        """
        self.vulnerabilityCheckBox.setChecked(True)
        self.on_vulnerabilityCheckBox_clicked(True)

    @pyqtSlot()
    def __clearVulnerabilityInfo(self):
        """
        Private slot to clear the vulnerability info.
        """
        for row in range(self.packagesList.topLevelItemCount()):
            itm = self.packagesList.topLevelItem(row)
            itm.setText(PipPackagesWidget.VulnerabilityColumn, "")
            itm.setToolTip(PipPackagesWidget.VulnerabilityColumn, "")
            itm.setIcon(PipPackagesWidget.VulnerabilityColumn, QIcon())
            itm.setData(
                PipPackagesWidget.VulnerabilityColumn,
                PipPackagesWidget.VulnerabilityRole,
                None,
            )

    @pyqtSlot()
    def __updateVulnerabilityData(self, clearFirst=True):
        """
        Private slot to update the shown vulnerability info.

        @param clearFirst flag indicating to clear the vulnerability info first
            (defaults to True)
        @type bool (optional)
        """
        if clearFirst:
            self.__clearVulnerabilityInfo()

        packages = []
        for row in range(self.packagesList.topLevelItemCount()):
            itm = self.packagesList.topLevelItem(row)
            packages.append(
                Package(
                    name=itm.text(PipPackagesWidget.PackageColumn),
                    version=itm.text(PipPackagesWidget.InstalledVersionColumn),
                )
            )

        if packages:
            error, vulnerabilities = self.__pip.getVulnerabilityChecker().check(
                packages
            )
            if error == VulnerabilityCheckError.OK:
                for package in vulnerabilities:
                    items = self.packagesList.findItems(
                        package,
                        Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive,
                    )
                    if items:
                        itm = items[0]
                        itm.setData(
                            PipPackagesWidget.VulnerabilityColumn,
                            PipPackagesWidget.VulnerabilityRole,
                            vulnerabilities[package],
                        )
                        affected = {v.spec for v in vulnerabilities[package]}
                        itm.setText(
                            PipPackagesWidget.VulnerabilityColumn, ", ".join(affected)
                        )
                        itm.setIcon(
                            PipPackagesWidget.VulnerabilityColumn,
                            EricPixmapCache.getIcon("securityLow"),
                        )

            elif error in (
                VulnerabilityCheckError.FullDbUnavailable,
                VulnerabilityCheckError.SummaryDbUnavailable,
            ):
                self.setVulnerabilityEnabled(False)

    @pyqtSlot()
    def __updateVulnerabilityDbCache(self):
        """
        Private slot to initiate an update of the local cache of the
        vulnerability database.
        """
        with EricOverrideCursor():
            self.__pip.getVulnerabilityChecker().updateVulnerabilityDb()

    def __showVulnerabilityInformation(
        self, packageName, packageVersion, vulnerabilities
    ):
        """
        Private method to show the detected vulnerability data.

        @param packageName name of the package
        @type str
        @param packageVersion installed version number
        @type str
        @param vulnerabilities list of vulnerabilities
        @type list of Vulnerability
        """
        if vulnerabilities:
            header = self.tr("{0} {1}", "package name, package version").format(
                packageName, packageVersion
            )
            topItem = QTreeWidgetItem(self.vulnerabilitiesInfoWidget, [header])
            topItem.setFirstColumnSpanned(True)
            topItem.setExpanded(True)
            font = topItem.font(0)
            font.setBold(True)
            topItem.setFont(0, font)

            for vulnerability in vulnerabilities:
                title = (
                    vulnerability.cve
                    if vulnerability.cve
                    else vulnerability.vulnerabilityId
                )
                titleItem = QTreeWidgetItem(topItem, [title])
                titleItem.setFirstColumnSpanned(True)
                titleItem.setExpanded(True)

                QTreeWidgetItem(
                    titleItem, [self.tr("Affected Version:"), vulnerability.spec]
                )
                itm = QTreeWidgetItem(
                    titleItem, [self.tr("Advisory:"), vulnerability.advisory]
                )
                itm.setToolTip(
                    1,
                    "<p>{0}</p>".format(
                        vulnerability.advisory.replace("\r\n", "<br/>")
                    ),
                )

            self.vulnerabilitiesInfoWidget.scrollToTop()
            self.vulnerabilitiesInfoWidget.resizeColumnToContents(0)

            header = self.vulnerabilitiesInfoWidget.header()
            header.setStretchLastSection(True)
        else:
            self.vulnerabilitiesInfoWidget.clear()

    #######################################################################
    ## Dependency tree related methods below
    #######################################################################

    @pyqtSlot(bool)
    def on_viewToggleButton_toggled(self, checked):
        """
        Private slot handling the view selection.

        @param checked state of the toggle button
        @type bool
        """
        if checked:
            self.viewsStackWidget.setCurrentWidget(self.dependenciesPage)
            self.__refreshDependencyTree()
        else:
            self.viewsStackWidget.setCurrentWidget(self.packagesPage)
            self.__refreshPackagesList()

    @pyqtSlot(bool)
    def on_requiresButton_toggled(self, checked):
        """
        Private slot handling the selection of the view type.

        @param checked state of the radio button (unused)
        @type bool
        """
        self.__refreshDependencyTree()

    @pyqtSlot()
    def on_localDepCheckBox_clicked(self):
        """
        Private slot handling the switching of the local mode.
        """
        self.__refreshDependencyTree()

    @pyqtSlot()
    def on_userDepCheckBox_clicked(self):
        """
        Private slot handling the switching of the 'user-site' mode.
        """
        self.__refreshDependencyTree()

    def __refreshDependencyTree(self):
        """
        Private method to refresh the dependency tree.
        """
        self.dependenciesList.clear()
        venvName = self.environmentsComboBox.currentText()
        if venvName:
            interpreter = self.__pip.getVirtualenvInterpreter(venvName)
            if interpreter:
                with EricOverrideCursor():
                    dependencies = self.__pip.getDependencyTree(
                        venvName,
                        localPackages=self.localDepCheckBox.isChecked(),
                        usersite=self.userDepCheckBox.isChecked(),
                        reverse=self.requiredByButton.isChecked(),
                    )

                    self.dependenciesList.setUpdatesEnabled(False)
                    for dependency in dependencies:
                        self.__addDependency(dependency, self.dependenciesList)

                    self.dependenciesList.sortItems(
                        PipPackagesWidget.DepPackageColumn, Qt.SortOrder.AscendingOrder
                    )
                    for col in range(self.dependenciesList.columnCount()):
                        self.dependenciesList.resizeColumnToContents(col)
                    self.dependenciesList.setUpdatesEnabled(True)

        self.__updateDepActionButtons()

    def __addDependency(self, dependency, parent):
        """
        Private method to add a dependency branch to a given parent.

        @param dependency dependency to be added
        @type dict
        @param parent reference to the parent item
        @type QTreeWidget or QTreeWidgetItem
        """
        itm = QTreeWidgetItem(
            parent,
            [
                dependency["package_name"],
                dependency["installed_version"],
                dependency["required_version"],
            ],
        )
        itm.setExpanded(True)

        if dependency["installed_version"] == "?":
            itm.setText(PipPackagesWidget.DepInstalledVersionColumn, self.tr("unknown"))

        if dependency["required_version"].lower() not in ("any", "?"):
            spec = (
                "=={0}".format(dependency["required_version"])
                if dependency["required_version"][0] in "0123456789"
                else dependency["required_version"]
            )
            try:
                specifierSet = SpecifierSet(specifiers=spec)
                if not specifierSet.contains(dependency["installed_version"]):
                    itm.setIcon(
                        PipPackagesWidget.DepRequiredVersionColumn,
                        EricPixmapCache.getIcon("warning"),
                    )
            except InvalidSpecifier:
                itm.setText(
                    PipPackagesWidget.DepRequiredVersionColumn,
                    dependency["required_version"],
                )

        elif dependency["required_version"].lower() == "any":
            itm.setText(PipPackagesWidget.DepRequiredVersionColumn, self.tr("any"))

        elif dependency["required_version"] == "?":
            itm.setText(PipPackagesWidget.DepRequiredVersionColumn, self.tr("unknown"))

        # recursively add sub-dependencies
        for dep in dependency["dependencies"]:
            self.__addDependency(dep, itm)

    @pyqtSlot(QTreeWidgetItem, int)
    def on_dependenciesList_itemActivated(self, item, column):
        """
        Private slot reacting on a package item of the dependency tree being
        activated.

        @param item reference to the activated item
        @type QTreeWidgetItem
        @param column activated column
        @type int
        """
        packageName = item.text(PipPackagesWidget.DepPackageColumn)
        packageVersion = item.text(PipPackagesWidget.DepInstalledVersionColumn)

        self.__showPackageDetails(packageName, packageVersion)

    @pyqtSlot()
    def on_dependenciesList_itemSelectionChanged(self):
        """
        Private slot reacting on a change of selected items of the dependency
        tree.
        """
        if len(self.dependenciesList.selectedItems()) == 0:
            self.dependencyInfoWidget.clear()

        self.__updateDepActionButtons()

    @pyqtSlot(QTreeWidgetItem, int)
    def on_dependenciesList_itemPressed(self, item, column):
        """
        Private slot reacting on a package item of the dependency tree being
        pressed.

        @param item reference to the pressed item
        @type QTreeWidgetItem
        @param column pressed column
        @type int
        """
        self.dependencyInfoWidget.clear()

        if item is not None:
            self.__showPackageInformation(
                item.text(PipPackagesWidget.DepPackageColumn), self.dependencyInfoWidget
            )

        self.__updateDepActionButtons()

    @pyqtSlot()
    def on_refreshDependenciesButton_clicked(self):
        """
        Private slot to refresh the dependency tree.
        """
        currentEnvironment = self.environmentsComboBox.currentText()
        self.environmentsComboBox.clear()
        self.dependenciesList.clear()

        with EricOverrideCursor():
            self.__populateEnvironments()

            index = self.environmentsComboBox.findText(
                currentEnvironment,
                Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive,
            )
            if index != -1:
                self.environmentsComboBox.setCurrentIndex(index)

        self.__updateDepActionButtons()

    @pyqtSlot()
    def on_showDepPackageDetailsButton_clicked(self):
        """
        Private slot to show information for the selected package of the
        dependency tree.
        """
        item = self.dependenciesList.selectedItems()[0]
        if item:
            packageName = item.text(PipPackagesWidget.DepPackageColumn)
            packageVersion = item.text(PipPackagesWidget.DepInstalledVersionColumn)

            self.__showPackageDetails(packageName, packageVersion)

    def __updateDepActionButtons(self):
        """
        Private method to set the state of the dependency page action buttons.
        """
        self.showDepPackageDetailsButton.setEnabled(
            len(self.dependenciesList.selectedItems()) == 1
        )

        self.dependencyRepairButton.setEnabled(
            any(
                not itm.icon(PipPackagesWidget.DepRequiredVersionColumn).isNull()
                for itm in self.dependenciesList.selectedItems()
            )
        )

        itm = self.dependenciesList.topLevelItem(0)
        while itm:
            if not itm.icon(PipPackagesWidget.DepRequiredVersionColumn).isNull():
                self.dependencyRepairAllButton.setEnabled(True)
                break
            itm = self.dependenciesList.itemBelow(itm)
        else:
            self.dependencyRepairAllButton.setEnabled(False)

    @pyqtSlot()
    def on_dependencyRepairButton_clicked(self):
        """
        Private slot to repair all selected dependencies.
        """
        packages = set()
        for itm in self.dependenciesList.selectedItems():
            if not itm.icon(PipPackagesWidget.DepRequiredVersionColumn).isNull():
                packages.add(
                    "{0}{1}".format(
                        itm.text(PipPackagesWidget.DepPackageColumn),
                        itm.text(PipPackagesWidget.DepRequiredVersionColumn),
                    )
                )

        venvName = self.environmentsComboBox.currentText()
        if venvName and packages:
            self.__pip.installPackages(
                list(packages),
                venvName=venvName,
                userSite=self.userDepCheckBox.isChecked(),
            )
            self.on_refreshDependenciesButton_clicked()

    @pyqtSlot()
    def on_dependencyRepairAllButton_clicked(self):
        """
        Private slot to repair all dependencies.
        """
        packages = set()
        itm = self.dependenciesList.topLevelItem(0)
        while itm:
            if not itm.icon(PipPackagesWidget.DepRequiredVersionColumn).isNull():
                packages.add(
                    "{0}{1}".format(
                        itm.text(PipPackagesWidget.DepPackageColumn),
                        itm.text(PipPackagesWidget.DepRequiredVersionColumn),
                    )
                )
            itm = self.dependenciesList.itemBelow(itm)

        venvName = self.environmentsComboBox.currentText()
        if venvName and packages:
            self.__pip.installPackages(
                list(packages),
                venvName=venvName,
                userSite=self.userDepCheckBox.isChecked(),
            )
            self.on_refreshDependenciesButton_clicked()

    ##################################################################
    ## Interface to show the licenses dialog below
    ##################################################################

    @pyqtSlot()
    def __showLicensesDialog(self):
        """
        Private slot to show a dialog with the licenses of the selected
        environment.
        """
        from .PipLicensesDialog import PipLicensesDialog

        environment = self.environmentsComboBox.currentText()
        dlg = PipLicensesDialog(
            self.__pip,
            environment,
            packages=self.__allPackageNames(),
            parent=self,
        )
        dlg.exec()

    ##################################################################
    ## Interface to create a SBOM file using CycloneDX
    ##################################################################

    @pyqtSlot()
    def __createSBOMFile(self):
        """
        Private slot to create a "Software Bill Of Material" file.
        """
        import CycloneDXInterface  # __IGNORE_WARNING_I102__

        venvName = self.environmentsComboBox.currentText()
        if venvName == self.__pip.getProjectEnvironmentString():
            venvName = "<project>"
        CycloneDXInterface.createCycloneDXFile(venvName, parent=self)

    ##################################################################
    ## Interface to preferences
    ##################################################################

    @pyqtSlot()
    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        enable = self.setVulnerabilityEnabled(
            Preferences.getPip("VulnerabilityCheckEnabled")
        )
        if enable != self.vulnerabilityCheckBox.isEnabled():
            # only if status changes because it is an expensive operation
            if self.vulnerabilityCheckBox.isChecked():
                self.__updateVulnerabilityData(clearFirst=True)
            else:
                self.__clearVulnerabilityInfo()
