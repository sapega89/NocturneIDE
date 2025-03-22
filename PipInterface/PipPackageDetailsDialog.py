# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show details about a package.
"""

from PyQt6.QtCore import QLocale, Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTreeWidgetItem,
)

from eric7 import EricUtilities

from .Ui_PipPackageDetailsDialog import Ui_PipPackageDetailsDialog


class PipPackageDetailsDialog(QDialog, Ui_PipPackageDetailsDialog):
    """
    Class implementing a dialog to show details about a package.
    """

    ButtonInstall = 1
    ButtonRemove = 2
    ButtonUpgrade = 4

    def __init__(self, detailsData, vulnerabilities=None, buttonsMode=0, parent=None):
        """
        Constructor

        @param detailsData package details
        @type dict
        @param vulnerabilities list of known vulnerabilities (defaults to None)
        @type list (optional)
        @param buttonsMode flags telling which convenience buttons to enable
            (defaults to 0)
        @type int (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__pipWidget = parent

        self.__installButton = self.buttonBox.addButton(
            self.tr("Install"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__removeButton = self.buttonBox.addButton(
            self.tr("Uninstall"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__upgradeButton = self.buttonBox.addButton(
            self.tr("Upgrade"), QDialogButtonBox.ButtonRole.ActionRole
        )

        self.__locale = QLocale()
        self.__packageTypeMap = {
            "sdist": self.tr("Source"),
            "bdist_wheel": self.tr("Python Wheel"),
            "bdist_egg": self.tr("Python Egg"),
            "bdist_wininst": self.tr("MS Windows Installer"),
            "bdist_msi": self.tr("MS Windows Installer"),
            "bdist_rpm": self.tr("Unix Installer"),
            "bdist_deb": self.tr("Unix Installer"),
            "bdist_dumb": self.tr("Archive"),
        }
        self.__packageName = detailsData["info"]["name"]

        self.__populateDetails(detailsData["info"])
        self.__populateDownloadUrls(detailsData["urls"])
        self.__populateProjectUrls(detailsData["info"]["project_urls"])
        self.__populateRequiresProvides(detailsData["info"])
        self.__populateVulnerabilities(vulnerabilities)

        self.__installButton.setEnabled(buttonsMode & self.ButtonInstall)
        self.__removeButton.setEnabled(buttonsMode & self.ButtonRemove)
        self.__upgradeButton.setEnabled(buttonsMode & self.ButtonUpgrade)

        if vulnerabilities:
            self.infoWidget.setCurrentWidget(self.security)
        else:
            self.infoWidget.setCurrentWidget(self.details)

    def __populateDetails(self, detailsData):
        """
        Private method to populate the details tab.

        @param detailsData package details
        @type dict
        """
        self.packageNameLabel.setText(
            "<h1>{0} {1}</h1".format(
                self.__sanitize(detailsData["name"]),
                self.__sanitize(detailsData["version"]),
            )
        )
        self.summaryLabel.setText(self.__sanitize(detailsData["summary"][:240]))
        self.descriptionEdit.setMarkdown(self.__sanitize(detailsData["description"]))
        self.authorLabel.setText(self.__sanitize(detailsData["author"]))
        self.authorEmailLabel.setText(
            '<a href="mailto:{0}">{0}</a>'.format(
                self.__sanitize(detailsData["author_email"])
            )
        )
        self.licenseLabel.setText(self.__sanitize(detailsData["license"]))
        self.platformLabel.setText(self.__sanitize(detailsData["platform"]))
        self.homePageLabel.setText(
            '<a href="{0}">{0}</a>'.format(
                self.__sanitize(
                    (
                        detailsData["project_urls"]["Homepage"]
                        if "Homepage" in detailsData["project_urls"]
                        else detailsData["home_page"]
                    ),
                    forUrl=True,
                )
            )
        )
        self.packageUrlLabel.setText(
            '<a href="{0}">{0}</a>'.format(
                self.__sanitize(detailsData["package_url"], forUrl=True)
            )
        )
        self.releaseUrlLabel.setText(
            '<a href="{0}">{0}</a>'.format(
                self.__sanitize(detailsData["release_url"], forUrl=True)
            )
        )
        self.docsUrlLabel.setText(
            '<a href="{0}">{0}</a>'.format(
                self.__sanitize(
                    (
                        detailsData["project_urls"]["Documentation"]
                        if "Documentation" in detailsData["project_urls"]
                        else detailsData["docs_url"]
                    ),
                    forUrl=True,
                )
            )
        )
        self.classifiersList.addItems(detailsData["classifiers"])

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

    def __populateDownloadUrls(self, downloadsData):
        """
        Private method to populate the download URLs tab.

        @param downloadsData downloads information
        @type dict
        """
        index = self.infoWidget.indexOf(self.urls)
        if downloadsData:
            self.infoWidget.setTabVisible(index, True)
            for download in downloadsData:
                itm = QTreeWidgetItem(
                    self.downloadUrlsList,
                    [
                        "",
                        (
                            self.__packageTypeMap[download["packagetype"]]
                            if download["packagetype"] in self.__packageTypeMap
                            else ""
                        ),
                        (
                            download["python_version"]
                            if download["python_version"] != "source"
                            else ""
                        ),
                        self.__formatUploadDate(download["upload_time"]),
                        self.__formatSize(download["size"]),
                    ],
                )
                urlLabel = QLabel(
                    '<a href="{0}#md5={2}">{1}</a>'.format(
                        download["url"],
                        download["filename"],
                        download["md5_digest"],
                    )
                )
                urlLabel.setTextInteractionFlags(
                    Qt.TextInteractionFlag.LinksAccessibleByMouse
                )
                urlLabel.setOpenExternalLinks(True)
                self.downloadUrlsList.setItemWidget(itm, 0, urlLabel)
            header = self.downloadUrlsList.header()
            header.resizeSections(QHeaderView.ResizeMode.ResizeToContents)
            header.setStretchLastSection(True)
        else:
            self.infoWidget.setTabVisible(index, False)

    def __populateProjectUrls(self, urls):
        """
        Private method to populate the 'Project URLs' tab.

        @param urls dictionary containing the defined project URLs
        @type dict
        """
        index = self.infoWidget.indexOf(self.projectUrls)
        if urls:
            self.infoWidget.setTabVisible(index, True)
            for url in urls:
                itm = QTreeWidgetItem(self.projectUrlsList, [url, ""])
                urlLabel = QLabel('<a href="{0}">{0}</a>'.format(urls[url]))
                urlLabel.setTextInteractionFlags(
                    Qt.TextInteractionFlag.LinksAccessibleByMouse
                )
                urlLabel.setOpenExternalLinks(True)
                self.projectUrlsList.setItemWidget(itm, 1, urlLabel)
            header = self.projectUrlsList.header()
            header.resizeSections(QHeaderView.ResizeMode.ResizeToContents)
            header.setStretchLastSection(True)
        else:
            self.infoWidget.setTabVisible(index, True)

    def __populateRequiresProvides(self, detailsData):
        """
        Private method to populate the requires/provides tab.

        @param detailsData package details
        @type dict
        """
        populatedItems = 0

        if "requires" in detailsData and detailsData["requires"]:
            self.requiredPackagesList.addItems(detailsData["requires"])
            populatedItems += len(detailsData["requires"])
        if "requires_dist" in detailsData and detailsData["requires_dist"]:
            self.requiredDistributionsList.addItems(detailsData["requires_dist"])
            populatedItems += len(detailsData["requires_dist"])
        if "provides" in detailsData and detailsData["provides"]:
            self.providedPackagesList.addItems(detailsData["provides"])
            populatedItems += len(detailsData["provides"])
        if "provides_dist" in detailsData and detailsData["provides_dist"]:
            self.providedDistributionsList.addItems(detailsData["provides_dist"])
            populatedItems += len(detailsData["provides_dist"])

        index = self.infoWidget.indexOf(self.requires)
        self.infoWidget.setTabVisible(index, populatedItems > 0)

    def __populateVulnerabilities(self, vulnerabilities):
        """
        Private method to populate the Security tab.

        @param vulnerabilities list of known vulnerabilities
        @type list
        """
        index = self.infoWidget.indexOf(self.security)
        if vulnerabilities:
            self.infoWidget.setTabVisible(index, True)
            for vulnerability in vulnerabilities:
                title = (
                    vulnerability.cve
                    if vulnerability.cve
                    else vulnerability.vulnerabilityId
                )
                self.vulnerabilitiesEdit.insertHtml(
                    self.tr(
                        "<h3>{0}</h3>"
                        "<table>"
                        "<tr><td>Installed Version:</td><td>{1}</td></tr>"
                        "<tr><td>Affected Version:</td><td>{2}</td></tr>"
                        "<tr><td>Advisory:</td><td>{3}</td></tr>"
                        "</table>"
                    ).format(
                        EricUtilities.html_encode(title),
                        EricUtilities.html_encode(vulnerability.version),
                        EricUtilities.html_encode(vulnerability.spec),
                        "<p>{0}</p>".format(
                            EricUtilities.html_encode(vulnerability.advisory).replace(
                                "\r\n", "<br/>"
                            )
                        ),
                    ),
                )
        else:
            self.infoWidget.setTabVisible(index, False)

    def __sanitize(self, text, forUrl=False):
        """
        Private method to clean-up the given text.

        @param text raw text
        @type str
        @param forUrl flag indicating to sanitize an URL text
        @type bool
        @return processed text
        @rtype str
        """
        if text == "UNKNOWN" or text is None:
            text = ""
        elif text == "any":
            text = self.tr("any")
        if forUrl and (
            not isinstance(text, str)
            or not text.startswith(("http://", "https://", "ftp://"))
        ):
            # ignore if the schema is not one of the listed ones
            text = ""

        return text

    def __formatUploadDate(self, datetime):
        """
        Private method to format the upload date.

        @param datetime upload date and time
        @type xmlrpc.DateTime or str
        @return formatted date string
        @rtype str
        """
        if isinstance(datetime, str):
            return datetime.split("T")[0]
        else:
            date = datetime.value.split("T")[0]
            return "{0}-{1}-{2}".format(date[:4], date[4:6], date[6:])

    def __formatSize(self, size):
        """
        Private slot to format the size.

        @param size size to be formatted
        @type int
        @return formatted size
        @rtype str
        """
        unit = ""
        if size < 1024:
            unit = self.tr("B")
        elif size < 1024 * 1024:
            size /= 1024
            unit = self.tr("KB")
        elif size < 1024 * 1024 * 1024:
            size /= 1024 * 1024
            unit = self.tr("MB")
        else:
            size /= 1024 * 1024 * 1024
            unit = self.tr("GB")
        return self.tr("{0:.1f} {1}", "value, unit").format(size, unit)

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot handling the user pressing an action button.

        @param button button activated by the user
        @type QAbstractButton
        """
        if button is self.__installButton:
            self.__pipWidget.executeInstallPackages([self.__packageName])
            self.__installButton.setEnabled(False)
            self.__removeButton.setEnabled(True)
            self.__upgradeButton.setEnabled(False)
            self.raise_()
        elif button is self.__removeButton:
            self.__pipWidget.executeUninstallPackages([self.__packageName])
            self.__installButton.setEnabled(True)
            self.__removeButton.setEnabled(False)
            self.__upgradeButton.setEnabled(False)
            self.raise_()
        elif button is self.__upgradeButton:
            self.__pipWidget.executeUpgradePackages([self.__packageName])
            self.__installButton.setEnabled(False)
            self.__removeButton.setEnabled(True)
            self.__upgradeButton.setEnabled(False)
            self.raise_()
