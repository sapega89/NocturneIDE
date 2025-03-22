# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show some information about a site.
"""

from PyQt6.QtCore import Qt, QUrl, pyqtSlot
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPixmap
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QMenu,
    QTreeWidgetItem,
)

try:
    from PyQt6.QtNetwork import QSslCertificate  # __IGNORE_WARNING__

    SSL = True
except ImportError:
    SSL = False

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from ..Tools import Scripts, WebBrowserTools
from ..WebBrowserPage import WebBrowserPage
from .Ui_SiteInfoDialog import Ui_SiteInfoDialog


class SiteInfoDialog(QDialog, Ui_SiteInfoDialog):
    """
    Class implementing a dialog to show some information about a site.
    """

    securityStyleFormat = "QLabel {{ background-color : {0}; }}"

    def __init__(self, browser, parent=None):
        """
        Constructor

        @param browser reference to the browser window
        @type WebBrowserView
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        # put icons
        self.tabWidget.setTabIcon(0, EricPixmapCache.getIcon("siteinfo-general"))
        self.tabWidget.setTabIcon(1, EricPixmapCache.getIcon("siteinfo-media"))
        if SSL:
            self.tabWidget.setTabIcon(2, EricPixmapCache.getIcon("siteinfo-security"))

        self.__imageReply = None

        self.__baseUrl = browser.url()
        title = browser.title()
        sslInfo = browser.page().getSslCertificateChain()

        # prepare background of image preview
        self.__imagePreviewStandardBackground = self.imagePreview.backgroundBrush()
        color1 = QColor(220, 220, 220)
        color2 = QColor(160, 160, 160)
        self.__tilePixmap = QPixmap(8, 8)
        self.__tilePixmap.fill(color1)
        tilePainter = QPainter(self.__tilePixmap)
        tilePainter.fillRect(0, 0, 4, 4, color2)
        tilePainter.fillRect(4, 4, 4, 4, color2)
        tilePainter.end()

        # populate General tab
        self.heading.setText("<b>{0}</b>".format(title))
        self.siteAddressLabel.setText(self.__baseUrl.toString())
        if self.__baseUrl.scheme() in ["https"]:
            if WebBrowserWindow.networkManager().isInsecureHost(self.__baseUrl.host()):
                self.securityIconLabel.setPixmap(
                    EricPixmapCache.getPixmap("securityMedium")
                )
                self.securityLabel.setStyleSheet(
                    SiteInfoDialog.securityStyleFormat.format(
                        Preferences.getWebBrowser("InsecureUrlColor").name()
                    )
                )
                self.securityLabel.setText(
                    self.tr("<b>Connection is encrypted but may be insecure.</b>")
                )
            else:
                self.securityIconLabel.setPixmap(
                    EricPixmapCache.getPixmap("securityHigh")
                )
                self.securityLabel.setStyleSheet(
                    SiteInfoDialog.securityStyleFormat.format(
                        Preferences.getWebBrowser("SecureUrlColor").name()
                    )
                )
                self.securityLabel.setText(self.tr("<b>Connection is encrypted.</b>"))
        else:
            self.securityIconLabel.setPixmap(EricPixmapCache.getPixmap("securityLow"))
            self.securityLabel.setText(self.tr("<b>Connection is not encrypted.</b>"))
        browser.page().runJavaScript(
            "document.charset",
            WebBrowserPage.SafeJsWorld,
            lambda res: self.encodingLabel.setText(res),
        )

        # populate the Security tab
        if sslInfo and SSL:
            self.sslWidget.showCertificateChain(sslInfo)
        self.tabWidget.setTabEnabled(2, SSL and bool(sslInfo))
        self.securityDetailsButton.setEnabled(SSL and bool(sslInfo))

        # populate Meta tags
        browser.page().runJavaScript(
            Scripts.getAllMetaAttributes(),
            WebBrowserPage.SafeJsWorld,
            self.__processMetaAttributes,
        )

        # populate Media tab
        browser.page().runJavaScript(
            Scripts.getAllImages(), WebBrowserPage.SafeJsWorld, self.__processImageTags
        )

        self.tabWidget.setCurrentIndex(0)

    @pyqtSlot()
    def on_securityDetailsButton_clicked(self):
        """
        Private slot to show security details.
        """
        self.tabWidget.setCurrentIndex(self.tabWidget.indexOf(self.securityTab))

    def __processImageTags(self, res):
        """
        Private method to process the image tags.

        @param res result of the JavaScript script
        @type list of dict
        """
        for img in res:
            src = img["src"]
            alt = img["alt"]
            if not alt:
                if src.find("/") == -1:
                    alt = src
                else:
                    pos = src.rfind("/")
                    alt = src[pos + 1 :]

            if not src or not alt:
                continue

            QTreeWidgetItem(self.imagesTree, [alt, src])

        for col in range(self.imagesTree.columnCount()):
            self.imagesTree.resizeColumnToContents(col)
        if self.imagesTree.columnWidth(0) > 300:
            self.imagesTree.setColumnWidth(0, 300)
        self.imagesTree.setCurrentItem(self.imagesTree.topLevelItem(0))
        self.imagesTree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.imagesTree.customContextMenuRequested.connect(
            self.__imagesTreeContextMenuRequested
        )

    def __processMetaAttributes(self, res):
        """
        Private method to process the meta attributes.

        @param res result of the JavaScript script
        @type list of dict
        """
        for meta in res:
            content = meta["content"]
            name = meta["name"]
            if not name:
                name = meta["httpequiv"]

            if not name or not content:
                continue

            if meta["charset"]:
                self.encodingLabel.setText(meta["charset"])
            if "charset=" in content:
                self.encodingLabel.setText(content[content.index("charset=") + 8 :])

            QTreeWidgetItem(self.tagsTree, [name, content])
        for col in range(self.tagsTree.columnCount()):
            self.tagsTree.resizeColumnToContents(col)

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_imagesTree_currentItemChanged(self, current, _previous):
        """
        Private slot to show a preview of the selected image.

        @param current current image entry
        @type QTreeWidgetItem
        @param _previous old current entry (unused)
        @type QTreeWidgetItem
        """
        if current is None:
            return

        imageUrl = QUrl(current.text(1))
        if imageUrl.isRelative():
            imageUrl = self.__baseUrl.resolved(imageUrl)

        pixmap = QPixmap()
        loading = False

        if imageUrl.scheme() == "data":
            encodedUrl = current.text(1).encode("utf-8")
            imageData = encodedUrl[encodedUrl.find(b",") + 1 :]
            pixmap = WebBrowserTools.pixmapFromByteArray(imageData)
        elif imageUrl.scheme() == "file":
            pixmap = QPixmap(imageUrl.toLocalFile())
        elif imageUrl.scheme() == "qrc":
            pixmap = QPixmap(imageUrl.toString()[3:])
        else:
            if self.__imageReply is not None:
                self.__imageReply.deleteLater()
                self.__imageReply = None

            self.__imageReply = WebBrowserWindow.networkManager().get(
                QNetworkRequest(imageUrl)
            )
            self.__imageReply.finished.connect(self.__imageReplyFinished)
            loading = True
            self.__showLoadingText()

        if not loading:
            self.__showPixmap(pixmap)

    @pyqtSlot()
    def __imageReplyFinished(self):
        """
        Private slot handling the loading of an image.
        """
        if self.__imageReply.error() != QNetworkReply.NetworkError.NoError:
            return

        data = self.__imageReply.readAll()
        self.__showPixmap(QPixmap.fromImage(QImage.fromData(data)))

    def __showPixmap(self, pixmap):
        """
        Private method to show a pixmap in the preview pane.

        @param pixmap pixmap to be shown
        @type QPixmap
        """
        scene = QGraphicsScene(self.imagePreview)
        if pixmap.isNull():
            self.imagePreview.setBackgroundBrush(self.__imagePreviewStandardBackground)
            scene.addText(self.tr("Preview not available."))
        else:
            self.imagePreview.setBackgroundBrush(QBrush(self.__tilePixmap))
            scene.addPixmap(pixmap)
        self.imagePreview.setScene(scene)

    def __showLoadingText(self):
        """
        Private method to show some text while loading an image.
        """
        self.imagePreview.setBackgroundBrush(self.__imagePreviewStandardBackground)
        scene = QGraphicsScene(self.imagePreview)
        scene.addText(self.tr("Loading..."))
        self.imagePreview.setScene(scene)

    def __imagesTreeContextMenuRequested(self, pos):
        """
        Private slot to show a context menu for the images list.

        @param pos position for the menu
        @type QPoint
        """
        itm = self.imagesTree.itemAt(pos)
        if itm is None:
            return

        menu = QMenu()
        act1 = menu.addAction(self.tr("Copy Image Location to Clipboard"))
        act1.setData(itm.text(1))
        act1.triggered.connect(lambda: self.__copyAction(act1))
        act2 = menu.addAction(self.tr("Copy Image Name to Clipboard"))
        act2.setData(itm.text(0))
        act2.triggered.connect(lambda: self.__copyAction(act2))
        menu.addSeparator()
        act3 = menu.addAction(self.tr("Save Image"))
        act3.setData(self.imagesTree.indexOfTopLevelItem(itm))
        act3.triggered.connect(lambda: self.__saveImage(act3))
        menu.exec(self.imagesTree.viewport().mapToGlobal(pos))

    def __copyAction(self, act):
        """
        Private slot to copy the image URL or the image name to the clipboard.

        @param act reference to the action that triggered
        @type QAction
        """
        QApplication.clipboard().setText(act.data())

    def __saveImage(self, act):
        """
        Private slot to save the selected image to disk.

        @param act reference to the action that triggered
        @type QAction
        """
        index = act.data()
        itm = self.imagesTree.topLevelItem(index)
        if itm is None:
            return

        if not self.imagePreview.scene() or len(self.imagePreview.scene().items()) == 0:
            return

        pixmapItem = self.imagePreview.scene().items()[0]
        if not isinstance(pixmapItem, QGraphicsPixmapItem):
            return

        if pixmapItem.pixmap().isNull():
            EricMessageBox.warning(
                self,
                self.tr("Save Image"),
                self.tr("""<p>This preview is not available.</p>"""),
            )
            return

        imageFileName = WebBrowserTools.getFileNameFromUrl(QUrl(itm.text(1)))
        index = imageFileName.rfind(".")
        if index != -1:
            imageFileName = imageFileName[:index] + ".png"

        filename = EricFileDialog.getSaveFileName(
            self,
            self.tr("Save Image"),
            imageFileName,
            self.tr("All Files (*)"),
            options=EricFileDialog.DontConfirmOverwrite,
        )

        if not filename:
            return

        if not pixmapItem.pixmap().save(filename, "PNG"):
            EricMessageBox.critical(
                self,
                self.tr("Save Image"),
                self.tr("""<p>Cannot write to file <b>{0}</b>.</p>""").format(filename),
            )
            return
