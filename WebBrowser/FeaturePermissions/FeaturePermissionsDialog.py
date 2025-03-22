# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the feature permission dialog.
"""

import contextlib

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QAbstractItemView, QDialog, QTreeWidget, QTreeWidgetItem

try:
    # Qt 6.8+
    from PyQt6.QtWebEngineCore import QWebEnginePermission
except ImportError:
    # Qt <6.8
    from PyQt6.QtWebEngineCore import QWebEnginePage

from eric7.EricGui import EricPixmapCache
from eric7.SystemUtilities import QtUtilities

from .Ui_FeaturePermissionsDialog import Ui_FeaturePermissionsDialog


class FeaturePermissionsDialog(QDialog, Ui_FeaturePermissionsDialog):
    """
    Class implementing the feature permission dialog.
    """

    def __init__(self, featurePermissions, parent=None):
        """
        Constructor

        @param featurePermissions dictionary with remembered feature
            permissions (Qt <6.8) or a list of permission objects (Qt 6.8+)
        @type dict of dict of list or list of QWebEnginePermission
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        # add the various lists

        self.notifList = QTreeWidget()
        self.notifList.setAlternatingRowColors(True)
        self.notifList.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.notifList.setRootIsDecorated(False)
        self.notifList.setItemsExpandable(False)
        self.notifList.setAllColumnsShowFocus(True)
        self.notifList.setObjectName("notifList")
        self.notifList.setSortingEnabled(True)
        self.notifList.headerItem().setText(0, self.tr("Host"))
        self.notifList.headerItem().setText(1, self.tr("Permission"))
        self.tabWidget.addTab(
            self.notifList,
            EricPixmapCache.getIcon("notification"),
            self.tr("Notifications"),
        )

        self.geoList = QTreeWidget()
        self.geoList.setAlternatingRowColors(True)
        self.geoList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.geoList.setRootIsDecorated(False)
        self.geoList.setItemsExpandable(False)
        self.geoList.setAllColumnsShowFocus(True)
        self.geoList.setObjectName("geoList")
        self.geoList.setSortingEnabled(True)
        self.geoList.headerItem().setText(0, self.tr("Host"))
        self.geoList.headerItem().setText(1, self.tr("Permission"))
        self.tabWidget.addTab(
            self.geoList, EricPixmapCache.getIcon("geolocation"), self.tr("Geolocation")
        )

        self.micList = QTreeWidget()
        self.micList.setAlternatingRowColors(True)
        self.micList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.micList.setRootIsDecorated(False)
        self.micList.setItemsExpandable(False)
        self.micList.setAllColumnsShowFocus(True)
        self.micList.setObjectName("micList")
        self.micList.setSortingEnabled(True)
        self.micList.headerItem().setText(0, self.tr("Host"))
        self.micList.headerItem().setText(1, self.tr("Permission"))
        self.tabWidget.addTab(
            self.micList, EricPixmapCache.getIcon("audiocapture"), self.tr("Microphone")
        )

        self.camList = QTreeWidget()
        self.camList.setAlternatingRowColors(True)
        self.camList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.camList.setRootIsDecorated(False)
        self.camList.setItemsExpandable(False)
        self.camList.setAllColumnsShowFocus(True)
        self.camList.setObjectName("camList")
        self.camList.setSortingEnabled(True)
        self.camList.headerItem().setText(0, self.tr("Host"))
        self.camList.headerItem().setText(1, self.tr("Permission"))
        self.tabWidget.addTab(
            self.camList, EricPixmapCache.getIcon("camera"), self.tr("Camera")
        )

        self.micCamList = QTreeWidget()
        self.micCamList.setAlternatingRowColors(True)
        self.micCamList.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.micCamList.setRootIsDecorated(False)
        self.micCamList.setItemsExpandable(False)
        self.micCamList.setAllColumnsShowFocus(True)
        self.micCamList.setObjectName("micCamList")
        self.micCamList.setSortingEnabled(True)
        self.micCamList.headerItem().setText(0, self.tr("Host"))
        self.micCamList.headerItem().setText(1, self.tr("Permission"))
        self.tabWidget.addTab(
            self.micCamList,
            EricPixmapCache.getIcon("audio-video"),
            self.tr("Microphone && Camera"),
        )

        self.mouseLockList = QTreeWidget()
        self.mouseLockList.setAlternatingRowColors(True)
        self.mouseLockList.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.mouseLockList.setRootIsDecorated(False)
        self.mouseLockList.setItemsExpandable(False)
        self.mouseLockList.setAllColumnsShowFocus(True)
        self.mouseLockList.setObjectName("mouseLockList")
        self.mouseLockList.setSortingEnabled(True)
        self.mouseLockList.headerItem().setText(0, self.tr("Host"))
        self.mouseLockList.headerItem().setText(1, self.tr("Permission"))
        self.tabWidget.addTab(
            self.mouseLockList, EricPixmapCache.getIcon("mouse"), self.tr("Mouse Lock")
        )

        self.deskVidList = QTreeWidget()
        self.deskVidList.setAlternatingRowColors(True)
        self.deskVidList.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.deskVidList.setRootIsDecorated(False)
        self.deskVidList.setItemsExpandable(False)
        self.deskVidList.setAllColumnsShowFocus(True)
        self.deskVidList.setObjectName("deskVidList")
        self.deskVidList.setSortingEnabled(True)
        self.deskVidList.headerItem().setText(0, self.tr("Host"))
        self.deskVidList.headerItem().setText(1, self.tr("Permission"))
        self.tabWidget.addTab(
            self.deskVidList,
            EricPixmapCache.getIcon("desktopVideoCapture"),
            self.tr("Desktop Video"),
        )

        self.deskAudVidList = QTreeWidget()
        self.deskAudVidList.setAlternatingRowColors(True)
        self.deskAudVidList.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.deskAudVidList.setRootIsDecorated(False)
        self.deskAudVidList.setItemsExpandable(False)
        self.deskAudVidList.setAllColumnsShowFocus(True)
        self.deskAudVidList.setObjectName("deskAudVidList")
        self.deskAudVidList.setSortingEnabled(True)
        self.deskAudVidList.headerItem().setText(0, self.tr("Host"))
        self.deskAudVidList.headerItem().setText(1, self.tr("Permission"))
        self.tabWidget.addTab(
            self.deskAudVidList,
            EricPixmapCache.getIcon("desktopAudioVideoCapture"),
            self.tr("Desktop Audio && Video"),
        )

        if QtUtilities.qVersionTuple() >= (6, 8, 0):
            # Qt 6.8+
            self.clipboardList = QTreeWidget()
            self.clipboardList.setAlternatingRowColors(True)
            self.clipboardList.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
            self.clipboardList.setRootIsDecorated(False)
            self.clipboardList.setItemsExpandable(False)
            self.clipboardList.setAllColumnsShowFocus(True)
            self.clipboardList.setObjectName("camList")
            self.clipboardList.setSortingEnabled(True)
            self.clipboardList.headerItem().setText(0, self.tr("Host"))
            self.clipboardList.headerItem().setText(1, self.tr("Permission"))
            self.tabWidget.addTab(
                self.clipboardList,
                EricPixmapCache.getIcon("clipboard"),
                self.tr("Clipboard"),
            )

            self.localFontsList = QTreeWidget()
            self.localFontsList.setAlternatingRowColors(True)
            self.localFontsList.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
            )
            self.localFontsList.setRootIsDecorated(False)
            self.localFontsList.setItemsExpandable(False)
            self.localFontsList.setAllColumnsShowFocus(True)
            self.localFontsList.setObjectName("camList")
            self.localFontsList.setSortingEnabled(True)
            self.localFontsList.headerItem().setText(0, self.tr("Host"))
            self.localFontsList.headerItem().setText(1, self.tr("Permission"))
            self.tabWidget.addTab(
                self.localFontsList,
                EricPixmapCache.getIcon("font"),
                self.tr("Local Fonts"),
            )

        self.setTabOrder(self.tabWidget, self.notifList)
        self.setTabOrder(self.notifList, self.geoList)
        self.setTabOrder(self.geoList, self.micList)
        self.setTabOrder(self.micList, self.camList)
        self.setTabOrder(self.camList, self.micCamList)
        self.setTabOrder(self.micCamList, self.mouseLockList)
        self.setTabOrder(self.mouseLockList, self.deskVidList)
        self.setTabOrder(self.deskVidList, self.deskAudVidList)
        if QtUtilities.qVersionTuple() >= (6, 8, 0):
            # Qt 6.8+
            self.setTabOrder(self.deskAudVidList, self.clipboardList)
            self.setTabOrder(self.clipboardList, self.localFontsList)
            self.setTabOrder(self.localFontsList, self.removeButton)
        else:
            self.setTabOrder(self.deskAudVidList, self.removeButton)
        self.setTabOrder(self.removeButton, self.removeAllButton)

        if QtUtilities.qVersionTuple() >= (6, 8, 0):
            # Qt 6.8+
            self.__initializePermissionsList_qt68(featurePermissions)
        else:
            # Qt <6.8
            self.__initializePermissionsList_qt67(featurePermissions)

        self.__removedPermissions = []
        self.__previousCurrent = -1
        self.tabWidget.currentChanged.connect(self.__currentTabChanged)
        self.tabWidget.setCurrentIndex(0)

    def __initializePermissionsList_qt68(self, permissions):
        """
        Private method to initialize the permission lists for Qt 6.8+.

        @param permissions list of permission objects
        @type list of QWebEnginePermission
        """
        self.__permissionStrings = {
            QWebEnginePermission.State.Granted: self.tr("Allow"),
            QWebEnginePermission.State.Denied: self.tr("Deny"),
            QWebEnginePermission.State.Ask: self.tr("Always Ask"),
            QWebEnginePermission.State.Invalid: self.tr("Invalid"),
        }

        self.__permissionsLists = {
            QWebEnginePermission.PermissionType.Geolocation: self.geoList,
            QWebEnginePermission.PermissionType.MediaAudioCapture: self.micList,
            QWebEnginePermission.PermissionType.MediaVideoCapture: self.camList,
            QWebEnginePermission.PermissionType.MediaAudioVideoCapture: self.micCamList,
            QWebEnginePermission.PermissionType.MouseLock: self.mouseLockList,
            QWebEnginePermission.PermissionType.DesktopVideoCapture: self.deskVidList,
            QWebEnginePermission.PermissionType.DesktopAudioVideoCapture: (
                self.deskAudVidList
            ),
            QWebEnginePermission.PermissionType.Notifications: self.notifList,
            QWebEnginePermission.PermissionType.ClipboardReadWrite: self.clipboardList,
            QWebEnginePermission.PermissionType.LocalFontsAccess: self.localFontsList,
        }

        for permission in permissions:
            with contextlib.suppress(KeyError):
                permissionsList = self.__permissionsLists[permission.permissionType()]
                itm = QTreeWidgetItem(
                    permissionsList,
                    [
                        permission.origin().toString(),
                        self.__permissionStrings[permission.state()],
                    ],
                )
                itm.setData(0, Qt.ItemDataRole.UserRole, permission)
        for permissionsList in self.__permissionsLists.values():
            permissionsList.resizeColumnToContents(0)

    def __initializePermissionsList_qt67(self, permissions):
        """
        Private method to initialize the permission lists for Qt <6.8.

        @param permissions dictionary with remembered feature permissions
        @type dict of dict of list
        """
        self.__permissionStrings = {
            QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: self.tr("Allow"),
            QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: self.tr("Deny"),
        }

        self.__permissionsLists = {
            QWebEnginePage.Feature.Geolocation: self.geoList,
            QWebEnginePage.Feature.MediaAudioCapture: self.micList,
            QWebEnginePage.Feature.MediaVideoCapture: self.camList,
            QWebEnginePage.Feature.MediaAudioVideoCapture: self.micCamList,
            QWebEnginePage.Feature.MouseLock: self.mouseLockList,
            QWebEnginePage.Feature.DesktopVideoCapture: self.deskVidList,
            QWebEnginePage.Feature.DesktopAudioVideoCapture: self.deskAudVidList,
            QWebEnginePage.Feature.Notifications: self.notifList,
        }

        for feature, permissionsList in self.__permissionsLists.items():
            for permission in permissions[feature]:
                for host in permissions[feature][permission]:
                    itm = QTreeWidgetItem(
                        permissionsList,
                        [host, self.__permissionStrings[permission]],
                    )
                    itm.setData(0, Qt.ItemDataRole.UserRole, permission)
            permissionsList.resizeColumnToContents(0)

    @pyqtSlot(int)
    def __currentTabChanged(self, index):
        """
        Private slot handling changes of the selected tab.

        @param index index of the current tab
        @type int
        """
        if self.__previousCurrent >= 0:
            previousList = self.tabWidget.widget(self.__previousCurrent)
            previousList.itemSelectionChanged.disconnect(self.__itemSelectionChanged)

        self.__updateButtons()

        currentList = self.tabWidget.currentWidget()
        currentList.itemSelectionChanged.connect(self.__itemSelectionChanged)
        self.__previousCurrent = index

    def __updateButtons(self):
        """
        Private method to update the buttons.
        """
        currentList = self.tabWidget.currentWidget()
        self.removeAllButton.setEnabled(currentList.topLevelItemCount() > 0)
        self.removeButton.setEnabled(len(currentList.selectedItems()) > 0)

    @pyqtSlot()
    def __itemSelectionChanged(self):
        """
        Private slot handling changes in the current list of selected items.
        """
        self.__updateButtons()

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove selected entries.
        """
        currentList = self.tabWidget.currentWidget()
        for itm in currentList.selectedItems():
            row = currentList.indexOfTopLevelItem(itm)
            itm = currentList.takeTopLevelItem(row)
            self.__removedPermissions.append(itm.data(0, Qt.ItemDataRole.UserRole))
            del itm
        self.__updateButtons()

    @pyqtSlot()
    def on_removeAllButton_clicked(self):
        """
        Private slot to remove all entries.
        """
        currentList = self.tabWidget.currentWidget()
        while currentList.topLevelItemCount() > 0:
            itm = currentList.takeTopLevelItem(0)  # __IGNORE_WARNING__
            self.__removedPermissions.append(itm.data(0, Qt.ItemDataRole.UserRole))
            del itm
        self.__updateButtons()

    def getData(self):
        """
        Public method to retrieve the dialog contents.

        @return new feature permission settings
        @rtype dict of dict of list
        """
        # Qt <6.8
        featurePermissions = {}
        for feature, permissionsList in self.__permissionsLists.items():
            featurePermissions[feature] = {
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser: [],
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser: [],
            }
            for row in range(permissionsList.topLevelItemCount()):
                itm = permissionsList.topLevelItem(row)
                host = itm.text(0)
                permission = itm.data(0, Qt.ItemDataRole.UserRole)
                featurePermissions[feature][permission].append(host)

        return featurePermissions

    def persistChanges(self):
        """
        Public method to persist the removed permissions.
        """
        # Qt 6.8+
        for permission in self.__removedPermissions:
            permission.reset()
