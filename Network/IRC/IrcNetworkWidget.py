# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the network part of the IRC widget.
"""

import pathlib

from PyQt6.QtCore import QPoint, QThread, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QMenu, QWidget

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import OSUtilities

from .IrcUtilities import ircFilter, ircTimestamp
from .Ui_IrcNetworkWidget import Ui_IrcNetworkWidget


class IrcNetworkWidget(QWidget, Ui_IrcNetworkWidget):
    """
    Class implementing the network part of the IRC widget.

    @signal connectNetwork(str,bool,bool) emitted to connect or disconnect from
        a network
    @signal editNetwork(str) emitted to edit a network configuration
    @signal joinChannel(str) emitted to join a channel
    @signal nickChanged(str) emitted to change the nick name
    @signal sendData(str) emitted to send a message to the channel
    @signal away(bool) emitted to indicate the away status
    @signal autoConnected() emitted after an automatic connection was initiated
    """

    connectNetwork = pyqtSignal(str, bool, bool)
    editNetwork = pyqtSignal(str)
    joinChannel = pyqtSignal(str)
    nickChanged = pyqtSignal(str)
    sendData = pyqtSignal(str)
    away = pyqtSignal(bool)
    autoConnected = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.connectButton.setIcon(EricPixmapCache.getIcon("ircConnect"))
        self.editButton.setIcon(EricPixmapCache.getIcon("ircConfigure"))
        self.joinButton.setIcon(EricPixmapCache.getIcon("ircJoinChannel"))
        self.awayButton.setIcon(EricPixmapCache.getIcon("ircUserPresent"))

        self.joinButton.setEnabled(False)
        self.nickCombo.setEnabled(False)
        self.awayButton.setEnabled(False)

        self.channelCombo.lineEdit().returnPressed.connect(self.on_joinButton_clicked)
        self.nickCombo.lineEdit().returnPressed.connect(
            self.on_nickCombo_currentIndexChanged
        )

        self.setConnected(False)

        self.__initMessagesMenu()

        self.__manager = None
        self.__connected = False
        self.__registered = False
        self.__away = False

    def initialize(self, manager):
        """
        Public method to initialize the widget.

        @param manager reference to the network manager
        @type IrcNetworkManager
        """
        self.__manager = manager

        self.networkCombo.addItems(self.__manager.getNetworkNames())

        self.__manager.networksChanged.connect(self.__refreshNetworks)
        self.__manager.identitiesChanged.connect(self.__refreshNetworks)

    def autoConnect(self):
        """
        Public method to perform the IRC auto connection.
        """
        userInterface = ericApp().getObject("UserInterface")
        online = userInterface.isOnline()
        self.connectButton.setEnabled(online)
        userInterface.onlineStateChanged.connect(self.__onlineStateChanged)
        if online:
            self.__autoConnect()

    def __autoConnect(self):
        """
        Private method to perform the IRC auto connection.
        """
        for networkName in self.__manager.getNetworkNames():
            if self.__manager.getNetwork(networkName).autoConnect():
                row = self.networkCombo.findText(networkName)
                self.networkCombo.setCurrentIndex(row)
                self.on_connectButton_clicked()
                self.autoConnected.emit()
                break

    @pyqtSlot(bool)
    def __onlineStateChanged(self, online):
        """
        Private slot handling online state changes.

        @param online online state
        @type bool
        """
        self.connectButton.setEnabled(online)
        if online:
            # delay a bit because the signal seems to be sent before the
            # network interface is fully up
            QThread.msleep(200)
            self.__autoConnect()
        else:
            network = self.networkCombo.currentText()
            self.connectNetwork.emit(network, online, True)

    @pyqtSlot()
    def __refreshNetworks(self):
        """
        Private slot to refresh all network related widgets.
        """
        currentNetwork = self.networkCombo.currentText()
        currentNick = self.nickCombo.currentText()
        currentChannel = self.channelCombo.currentText()
        blocked = self.networkCombo.blockSignals(True)
        self.networkCombo.clear()
        self.networkCombo.addItems(self.__manager.getNetworkNames())
        self.networkCombo.blockSignals(blocked)
        row = self.networkCombo.findText(currentNetwork)
        if row == -1:
            row = 0
        blocked = self.nickCombo.blockSignals(True)
        self.networkCombo.setCurrentIndex(row)
        self.nickCombo.setEditText(currentNick)
        self.nickCombo.blockSignals(blocked)
        self.channelCombo.setEditText(currentChannel)

    @pyqtSlot()
    def on_connectButton_clicked(self):
        """
        Private slot to connect to a network.
        """
        network = self.networkCombo.currentText()
        self.connectNetwork.emit(network, not self.__connected, False)

    @pyqtSlot()
    def on_awayButton_clicked(self):
        """
        Private slot to toggle the away status.
        """
        if self.__away:
            self.handleAwayCommand("")
        else:
            networkName = self.networkCombo.currentText()
            identityName = self.__manager.getNetwork(networkName).getIdentityName()
            identity = self.__manager.getIdentity(identityName)
            if identity:
                awayMessage = identity.getAwayMessage()
            else:
                awayMessage = ""
            self.handleAwayCommand(awayMessage)

    @pyqtSlot(str)
    def handleAwayCommand(self, awayMessage):
        """
        Public slot to process an away command.

        @param awayMessage message to be set for being away
        @type str
        """
        if awayMessage and not self.__away:
            # set being away
            # don't send away, if the status is already set
            self.sendData.emit("AWAY :" + awayMessage)
            self.awayButton.setIcon(EricPixmapCache.getIcon("ircUserAway"))
            self.__away = True
            self.away.emit(self.__away)
        elif not awayMessage and self.__away:
            # cancel being away
            self.sendData.emit("AWAY")
            self.awayButton.setIcon(EricPixmapCache.getIcon("ircUserPresent"))
            self.__away = False
            self.away.emit(self.__away)

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to edit a network.
        """
        network = self.networkCombo.currentText()
        self.editNetwork.emit(network)

    @pyqtSlot(str)
    def on_channelCombo_editTextChanged(self, txt):
        """
        Private slot to react upon changes of the channel.

        @param txt current text of the channel combo
        @type str
        """
        on = bool(txt) and self.__registered
        self.joinButton.setEnabled(on)

    @pyqtSlot()
    def on_joinButton_clicked(self):
        """
        Private slot to join a channel.
        """
        channel = self.channelCombo.currentText()
        self.joinChannel.emit(channel)

    @pyqtSlot(int)
    def on_networkCombo_currentIndexChanged(self, index):
        """
        Private slot to handle selections of a network.

        @param index index of the selected entry
        @type int
        """
        networkName = self.networkCombo.itemText(index)
        network = self.__manager.getNetwork(networkName)
        self.nickCombo.clear()
        self.channelCombo.clear()
        if network:
            channels = network.getChannelNames()
            self.channelCombo.addItems(channels)
            self.channelCombo.setEnabled(True)
            identity = self.__manager.getIdentity(network.getIdentityName())
            if identity:
                self.nickCombo.addItems(identity.getNickNames())
        else:
            self.channelCombo.setEnabled(False)

    def getNetworkChannels(self):
        """
        Public method to get the list of channels associated with the
        selected network.

        @return associated channels
        @rtype list of IrcChannel
        """
        networkName = self.networkCombo.currentText()
        network = self.__manager.getNetwork(networkName)
        return network.getChannels()

    @pyqtSlot(int)
    @pyqtSlot()
    def on_nickCombo_currentIndexChanged(self, nick=0):
        """
        Private slot to use another nick name.

        @param nick index of the selected nick name (unused)
        @type int
        """
        if self.__connected:
            self.nickChanged.emit(self.nickCombo.currentText())

    def getNickname(self):
        """
        Public method to get the currently selected nick name.

        @return selected nick name
        @rtype str
        """
        return self.nickCombo.currentText()

    def setNickName(self, nick):
        """
        Public slot to set the nick name in use.

        @param nick nick name in use
        @type str
        """
        self.nickCombo.blockSignals(True)
        self.nickCombo.setEditText(nick)
        self.nickCombo.blockSignals(False)

    def addMessage(self, msg):
        """
        Public method to add a message.

        @param msg message to be added
        @type str
        """
        s = '<font color="{0}">{1} {2}</font>'.format(
            Preferences.getIrc("NetworkMessageColour"), ircTimestamp(), msg
        )
        self.messages.append(s)

    def addServerMessage(self, msgType, msg, filterMsg=True):
        """
        Public method to add a server message.

        @param msgType txpe of the message
        @type str
        @param msg message to be added
        @type str
        @param filterMsg flag indicating to filter the message
        @type bool
        """
        if filterMsg:
            msg = ircFilter(msg)
        s = '<font color="{0}">{1} <b>[</b>{2}<b>]</b> {3}</font>'.format(
            Preferences.getIrc("ServerMessageColour"), ircTimestamp(), msgType, msg
        )
        self.messages.append(s)

    def addErrorMessage(self, msgType, msg):
        """
        Public method to add an error message.

        @param msgType txpe of the message
        @type str
        @param msg message to be added
        @type str
        """
        s = '<font color="{0}">{1} <b>[</b>{2}<b>]</b> {3}</font>'.format(
            Preferences.getIrc("ErrorMessageColour"), ircTimestamp(), msgType, msg
        )
        self.messages.append(s)

    def setConnected(self, connected):
        """
        Public slot to set the connection state.

        @param connected flag indicating the connection state
        @type bool
        """
        self.__connected = connected
        if self.__connected:
            self.connectButton.setIcon(EricPixmapCache.getIcon("ircDisconnect"))
            self.connectButton.setToolTip(
                self.tr("Press to disconnect from the network")
            )
        else:
            self.connectButton.setIcon(EricPixmapCache.getIcon("ircConnect"))
            self.connectButton.setToolTip(
                self.tr("Press to connect to the selected network")
            )

    def isConnected(self):
        """
        Public method to check, if the network is connected.

        @return flag indicating a connected network
        @rtype bool
        """
        return self.__connected

    def setRegistered(self, registered):
        """
        Public slot to set the registered state.

        @param registered flag indicating the registration state
        @type bool
        """
        self.__registered = registered
        on = bool(self.channelCombo.currentText()) and self.__registered
        self.joinButton.setEnabled(on)
        self.nickCombo.setEnabled(registered)
        self.awayButton.setEnabled(registered)
        if registered:
            self.awayButton.setIcon(EricPixmapCache.getIcon("ircUserPresent"))
            self.__away = False

    def __clearMessages(self):
        """
        Private slot to clear the contents of the messages display.
        """
        self.messages.clear()

    def __copyMessages(self):
        """
        Private slot to copy the selection of the messages display to
        the clipboard.
        """
        self.messages.copy()

    def __copyAllMessages(self):
        """
        Private slot to copy the contents of the messages display to
        the clipboard.
        """
        txt = self.messages.toPlainText()
        if txt:
            cb = QApplication.clipboard()
            cb.setText(txt)

    def __cutAllMessages(self):
        """
        Private slot to cut the contents of the messages display to
        the clipboard.
        """
        txt = self.messages.toPlainText()
        if txt:
            cb = QApplication.clipboard()
            cb.setText(txt)
        self.messages.clear()

    def __saveMessages(self):
        """
        Private slot to save the contents of the messages display.
        """
        hasText = not self.messages.document().isEmpty()
        if hasText:
            if OSUtilities.isWindowsPlatform():
                htmlExtension = "htm"
            else:
                htmlExtension = "html"
            fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
                self,
                self.tr("Save Messages"),
                "",
                self.tr("HTML Files (*.{0});;Text Files (*.txt);;All Files (*)").format(
                    htmlExtension
                ),
                None,
                EricFileDialog.DontConfirmOverwrite,
            )
            if fname:
                fpath = pathlib.Path(fname)
                if not fpath.suffix:
                    ex = selectedFilter.split("(*")[1].split(")")[0]
                    if ex:
                        fpath = fpath.with_suffix(ex)
                if fpath.exists():
                    res = EricMessageBox.yesNo(
                        self,
                        self.tr("Save Messages"),
                        self.tr(
                            "<p>The file <b>{0}</b> already exists."
                            " Overwrite it?</p>"
                        ).format(fpath),
                        icon=EricMessageBox.Warning,
                    )
                    if not res:
                        return

                try:
                    txt = (
                        self.messages.toHtml()
                        if fpath.suffix.lower() in [".htm", ".html"]
                        else self.messages.toPlainText()
                    )
                    with fpath.open("w", encoding="utf-8") as f:
                        f.write(txt)
                except OSError as err:
                    EricMessageBox.critical(
                        self,
                        self.tr("Error saving Messages"),
                        self.tr(
                            """<p>The messages contents could not be written"""
                            """ to <b>{0}</b></p><p>Reason: {1}</p>"""
                        ).format(fpath, str(err)),
                    )

    def __initMessagesMenu(self):
        """
        Private slot to initialize the context menu of the messages pane.
        """
        self.__messagesMenu = QMenu(self)
        self.__copyMessagesAct = self.__messagesMenu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy"), self.__copyMessages
        )
        self.__messagesMenu.addSeparator()
        self.__cutAllMessagesAct = self.__messagesMenu.addAction(
            EricPixmapCache.getIcon("editCut"),
            self.tr("Cut all"),
            self.__cutAllMessages,
        )
        self.__copyAllMessagesAct = self.__messagesMenu.addAction(
            EricPixmapCache.getIcon("editCopy"),
            self.tr("Copy all"),
            self.__copyAllMessages,
        )
        self.__messagesMenu.addSeparator()
        self.__clearMessagesAct = self.__messagesMenu.addAction(
            EricPixmapCache.getIcon("editDelete"),
            self.tr("Clear"),
            self.__clearMessages,
        )
        self.__messagesMenu.addSeparator()
        self.__saveMessagesAct = self.__messagesMenu.addAction(
            EricPixmapCache.getIcon("fileSave"), self.tr("Save"), self.__saveMessages
        )

        self.on_messages_copyAvailable(False)

    @pyqtSlot(bool)
    def on_messages_copyAvailable(self, yes):
        """
        Private slot to react to text selection/deselection of the
        messages edit.

        @param yes flag signaling the availability of selected text
        @type bool
        """
        self.__copyMessagesAct.setEnabled(yes)

    @pyqtSlot(QPoint)
    def on_messages_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu of the messages pane.

        @param pos position the menu should be opened at
        @type QPoint
        """
        enable = not self.messages.document().isEmpty()
        self.__cutAllMessagesAct.setEnabled(enable)
        self.__copyAllMessagesAct.setEnabled(enable)
        self.__saveMessagesAct.setEnabled(enable)
        self.__messagesMenu.popup(self.messages.mapToGlobal(pos))

    @pyqtSlot(QUrl)
    def on_messages_anchorClicked(self, url):
        """
        Private slot to open links in the default browser.

        @param url URL to be opened
        @type QUrl
        """
        QDesktopServices.openUrl(url)
