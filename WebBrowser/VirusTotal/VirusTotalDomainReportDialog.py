# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the VirusTotal domain report.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from eric7.EricGui import EricPixmapCache

from .Ui_VirusTotalDomainReportDialog import Ui_VirusTotalDomainReportDialog


class VirusTotalDomainReportDialog(QDialog, Ui_VirusTotalDomainReportDialog):
    """
    Class implementing a dialog to show the VirusTotal domain report.
    """

    def __init__(
        self,
        domain,
        resolutions,
        urls,
        subdomains,
        categories,
        webutation,
        whois,
        parent=None,
    ):
        """
        Constructor

        @param domain domain name
        @type str
        @param resolutions list of resolved host names
        @type list of dict
        @param urls list of detected URLs
        @type list of dict
        @param subdomains list of subdomains
        @type list of str
        @param categories dictionary with various categorizations with keys
            'bitdefender', 'sophos', 'valkyrie', 'alpha', 'forcepoint'
        @type dict
        @param webutation dictionary with Webutation data with keys
            'adult', 'safety', 'verdict'
        @type dict
        @param whois whois information
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.headerLabel.setText(self.tr("<b>Report for domain {0}</b>").format(domain))
        self.headerPixmap.setPixmap(EricPixmapCache.getPixmap("virustotal"))

        for resolution in resolutions:
            QTreeWidgetItem(
                self.resolutionsList,
                [resolution["ip_address"], resolution["last_resolved"].split()[0]],
            )
        self.resolutionsList.resizeColumnToContents(0)
        self.resolutionsList.resizeColumnToContents(1)
        self.resolutionsList.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        for url in urls:
            QTreeWidgetItem(
                self.urlsList,
                [
                    url["url"],
                    self.tr("{0}/{1}", "positives / total").format(
                        url["positives"], url["total"]
                    ),
                    url["scan_date"].split()[0],
                ],
            )
        self.urlsList.resizeColumnToContents(0)
        self.urlsList.resizeColumnToContents(1)
        self.urlsList.resizeColumnToContents(2)
        self.urlsList.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        if subdomains:
            self.subdomainsList.addItems(subdomains)
            self.subdomainsList.sortItems()

        self.bdLabel.setText(categories["bitdefender"])
        self.soLabel.setText(categories["sophos"])
        self.vvLabel.setText(categories["valkyrie"])
        self.amLabel.setText(categories["alpha"])
        self.ftsLabel.setText(categories["forcepoint"])

        self.webutationAdultLabel.setText(webutation["adult"])
        self.webutationSafetyLabel.setText(str(webutation["safety"]))
        self.webutationVerdictLabel.setText(webutation["verdict"])

        self.__whois = whois
        self.__whoisDomain = domain
        self.whoisButton.setEnabled(bool(whois))

    @pyqtSlot()
    def on_whoisButton_clicked(self):
        """
        Private slot to show the whois information.
        """
        from .VirusTotalWhoisDialog import VirusTotalWhoisDialog

        dlg = VirusTotalWhoisDialog(self.__whoisDomain, self.__whois, parent=self)
        dlg.exec()
