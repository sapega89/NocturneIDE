# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the AdBlock configuration dialog.
"""

from PyQt6.QtCore import QCoreApplication, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QDialog, QMenu, QToolButton

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .Ui_AdBlockDialog import Ui_AdBlockDialog


class AdBlockDialog(QDialog, Ui_AdBlockDialog):
    """
    Class implementing the AdBlock configuration dialog.
    """

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the AdBlock manager
        @type AdBlockManager
        @param parent reference to the parent object
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__manager = manager

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("adBlockPlus48"))

        self.updateSpinBox.setValue(Preferences.getWebBrowser("AdBlockUpdatePeriod"))

        self.useLimitedEasyListCheckBox.setChecked(
            Preferences.getWebBrowser("AdBlockUseLimitedEasyList")
        )

        self.adBlockGroup.setChecked(self.__manager.isEnabled())
        self.__manager.requiredSubscriptionLoaded.connect(self.addSubscription)
        self.__manager.enabledChanged.connect(self.__managerEnabledChanged)

        self.__currentTreeWidget = None
        self.__currentSubscription = None
        self.__loaded = False

        menu = QMenu(self)
        menu.aboutToShow.connect(self.__aboutToShowActionMenu)
        self.actionButton.setMenu(menu)
        self.actionButton.setIcon(EricPixmapCache.getIcon("adBlockAction"))
        self.actionButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.__load()

        self.buttonBox.setFocus()

    def __loadSubscriptions(self):
        """
        Private slot to load the AdBlock subscription rules.
        """
        for index in range(self.subscriptionsTabWidget.count()):
            tree = self.subscriptionsTabWidget.widget(index)
            tree.refresh()

    def __load(self):
        """
        Private slot to populate the tab widget with subscriptions.
        """
        from .AdBlockTreeWidget import AdBlockTreeWidget

        if self.__loaded or not self.adBlockGroup.isChecked():
            return

        for subscription in self.__manager.subscriptions():
            tree = AdBlockTreeWidget(subscription, self.subscriptionsTabWidget)
            icon = (
                EricPixmapCache.getIcon("adBlockPlus")
                if subscription.isEnabled()
                else EricPixmapCache.getIcon("adBlockPlusDisabled")
            )
            self.subscriptionsTabWidget.addTab(tree, icon, subscription.title())

        self.__loaded = True
        QCoreApplication.processEvents()

        QTimer.singleShot(50, self.__loadSubscriptions)

    def addSubscription(self, subscription, refresh=True):
        """
        Public slot adding a subscription to the list.

        @param subscription reference to the subscription to be
            added
        @type AdBlockSubscription
        @param refresh flag indicating to refresh the tree
        @type bool
        """
        from .AdBlockTreeWidget import AdBlockTreeWidget

        tree = AdBlockTreeWidget(subscription, self.subscriptionsTabWidget)
        index = self.subscriptionsTabWidget.insertTab(
            self.subscriptionsTabWidget.count() - 1, tree, subscription.title()
        )
        self.subscriptionsTabWidget.setCurrentIndex(index)
        QCoreApplication.processEvents()
        if refresh:
            tree.refresh()
        self.__setSubscriptionEnabled(subscription, True)

    def __aboutToShowActionMenu(self):
        """
        Private slot to show the actions menu.
        """
        subscriptionEditable = (
            self.__currentSubscription and self.__currentSubscription.canEditRules()
        )
        subscriptionRemovable = (
            self.__currentSubscription and self.__currentSubscription.canBeRemoved()
        )
        subscriptionEnabled = (
            self.__currentSubscription and self.__currentSubscription.isEnabled()
        )

        menu = self.actionButton.menu()
        menu.clear()

        menu.addAction(self.tr("Add Rule"), self.__addCustomRule).setEnabled(
            subscriptionEditable
        )
        menu.addAction(self.tr("Remove Rule"), self.__removeCustomRule).setEnabled(
            subscriptionEditable
        )
        menu.addSeparator()
        menu.addAction(self.tr("Browse Subscriptions..."), self.__browseSubscriptions)
        menu.addAction(
            self.tr("Remove Subscription"), self.__removeSubscription
        ).setEnabled(subscriptionRemovable)
        if self.__currentSubscription:
            menu.addSeparator()
            if subscriptionEnabled:
                txt = self.tr("Disable Subscription")
            else:
                txt = self.tr("Enable Subscription")
            menu.addAction(txt, self.__switchSubscriptionEnabled)
        menu.addSeparator()
        menu.addAction(
            self.tr("Update Subscription"), self.__updateSubscription
        ).setEnabled(not subscriptionEditable)
        menu.addAction(
            self.tr("Update All Subscriptions"), self.__updateAllSubscriptions
        )
        menu.addSeparator()
        menu.addAction(
            self.tr("Learn more about writing rules..."),
            self.__learnAboutWritingFilters,
        )

    def addCustomRule(self, filterRule):
        """
        Public slot to add a custom AdBlock rule.

        @param filterRule filter to be added
        @type string
        """
        self.subscriptionsTabWidget.setCurrentIndex(
            self.subscriptionsTabWidget.count() - 1
        )
        self.__currentTreeWidget.addRule(filterRule)

    def __addCustomRule(self):
        """
        Private slot to add a custom AdBlock rule.
        """
        self.__currentTreeWidget.addRule()

    def __removeCustomRule(self):
        """
        Private slot to remove a custom AdBlock rule.
        """
        self.__currentTreeWidget.removeRule()

    def __updateSubscription(self):
        """
        Private slot to update the selected subscription.
        """
        self.__currentSubscription.updateNow()

    def __updateAllSubscriptions(self):
        """
        Private slot to update all subscriptions.
        """
        self.__manager.updateAllSubscriptions()

    def __browseSubscriptions(self):
        """
        Private slot to browse the list of available AdBlock subscriptions.
        """
        mw = WebBrowserWindow.mainWindow()
        mw.newTab("http://adblockplus.org/en/subscriptions")
        mw.raise_()

    def __learnAboutWritingFilters(self):
        """
        Private slot to show the web page about how to write filters.
        """
        mw = WebBrowserWindow.mainWindow()
        mw.newTab("http://adblockplus.org/en/filters")
        mw.raise_()

    def __removeSubscription(self):
        """
        Private slot to remove the selected subscription.
        """
        requiresTitles = []
        requiresSubscriptions = self.__manager.getRequiresSubscriptions(
            self.__currentSubscription
        )
        for subscription in requiresSubscriptions:
            requiresTitles.append(subscription.title())
        message = (
            self.tr(
                "<p>Do you really want to remove subscription"
                " <b>{0}</b> and all subscriptions requiring it?</p>"
                "<ul><li>{1}</li></ul>"
            ).format(
                self.__currentSubscription.title(), "</li><li>".join(requiresTitles)
            )
            if requiresTitles
            else self.tr(
                "<p>Do you really want to remove subscription <b>{0}</b>?</p>"
            ).format(self.__currentSubscription.title())
        )
        res = EricMessageBox.yesNo(self, self.tr("Remove Subscription"), message)

        if res:
            removeSubscription = self.__currentSubscription
            removeTrees = [self.__currentTreeWidget]
            for index in range(self.subscriptionsTabWidget.count()):
                tree = self.subscriptionsTabWidget.widget(index)
                if tree.subscription() in requiresSubscriptions:
                    removeTrees.append(tree)
            for tree in removeTrees:
                self.subscriptionsTabWidget.removeTab(
                    self.subscriptionsTabWidget.indexOf(tree)
                )
            self.__manager.removeSubscription(removeSubscription)

    def __switchSubscriptionEnabled(self):
        """
        Private slot to switch the enabled state of the selected subscription.
        """
        newState = not self.__currentSubscription.isEnabled()
        self.__setSubscriptionEnabled(self.__currentSubscription, newState)

    def __setSubscriptionEnabled(self, subscription, enable):
        """
        Private slot to set the enabled state of a subscription.

        @param subscription subscription to set the state for
        @type AdBlockSubscription
        @param enable state to set to
        @type bool
        """
        if enable:
            # enable required one as well
            sub = self.__manager.subscription(subscription.requiresLocation())
            requiresSubscriptions = [] if sub is None else [sub]
            icon = EricPixmapCache.getIcon("adBlockPlus")
        else:
            # disable dependent ones as well
            requiresSubscriptions = self.__manager.getRequiresSubscriptions(
                subscription
            )
            icon = EricPixmapCache.getIcon("adBlockPlusDisabled")
        requiresSubscriptions.append(subscription)
        for sub in requiresSubscriptions:
            sub.setEnabled(enable)

        for index in range(self.subscriptionsTabWidget.count()):
            tree = self.subscriptionsTabWidget.widget(index)
            if tree.subscription() in requiresSubscriptions:
                self.subscriptionsTabWidget.setTabIcon(
                    self.subscriptionsTabWidget.indexOf(tree), icon
                )

    @pyqtSlot(int)
    def on_updateSpinBox_valueChanged(self, value):
        """
        Private slot to handle changes of the update period.

        @param value update period
        @type int
        """
        if value != Preferences.getWebBrowser("AdBlockUpdatePeriod"):
            Preferences.setWebBrowser("AdBlockUpdatePeriod", value)

            manager = WebBrowserWindow.adBlockManager()
            for subscription in manager.subscriptions():
                subscription.checkForUpdate()

    @pyqtSlot(int)
    def on_subscriptionsTabWidget_currentChanged(self, index):
        """
        Private slot handling the selection of another tab.

        @param index index of the new current tab
        @type int
        """
        if index != -1:
            self.__currentTreeWidget = self.subscriptionsTabWidget.widget(index)
            self.__currentSubscription = self.__currentTreeWidget.subscription()

            isEasyList = (
                self.__currentSubscription.url()
                .toString()
                .startswith(self.__manager.getDefaultSubscriptionUrl())
            )
            self.useLimitedEasyListCheckBox.setVisible(isEasyList)

    @pyqtSlot(str)
    def on_searchEdit_textChanged(self, filterRule):
        """
        Private slot to set a new filter on the current widget.

        @param filterRule filter to be set
        @type str
        """
        if self.__currentTreeWidget and self.adBlockGroup.isChecked():
            self.__currentTreeWidget.filterString(filterRule)

    @pyqtSlot(bool)
    def on_adBlockGroup_toggled(self, state):
        """
        Private slot handling the enabling/disabling of AdBlock.

        @param state state of the toggle
        @type bool
        """
        self.__manager.setEnabled(state)

        if state:
            self.__load()

    @pyqtSlot(bool)
    def on_useLimitedEasyListCheckBox_clicked(self, _checked):
        """
        Private slot handling the selection of the limited EasyList.

        @param _checked flag indicating the state of the check box (unused)
        @type bool
        """
        self.__manager.setUseLimitedEasyList(
            self.useLimitedEasyListCheckBox.isChecked()
        )

    @pyqtSlot(bool)
    def __managerEnabledChanged(self, enabled):
        """
        Private slot handling a change of the AdBlock manager enabled state.

        @param enabled flag indicating the enabled state
        @type bool
        """
        self.adBlockGroup.setChecked(enabled)
