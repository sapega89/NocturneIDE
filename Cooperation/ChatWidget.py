# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the chat dialog.
"""

import pathlib

from PyQt6.QtCore import QDateTime, QPoint, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QListWidgetItem, QMenu, QWidget

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import recentNameHosts

from .CooperationClient import CooperationClient
from .Ui_ChatWidget import Ui_ChatWidget


class ChatWidget(QWidget, Ui_ChatWidget):
    """
    Class implementing the chat dialog.

    @signal connected(connected) emitted to signal a change of the connected
            state (bool)
    @signal editorCommand(hashStr, filename, message) emitted when an editor
            command has been received (string, string, string)
    @signal shareEditor(share) emitted to signal a share is requested (bool)
    @signal startEdit() emitted to start a shared edit session
    @signal sendEdit() emitted to send a shared edit session
    @signal cancelEdit() emitted to cancel a shared edit session
    """

    connected = pyqtSignal(bool)
    editorCommand = pyqtSignal(str, str, str)

    shareEditor = pyqtSignal(bool)
    startEdit = pyqtSignal()
    sendEdit = pyqtSignal()
    cancelEdit = pyqtSignal()

    def __init__(self, ui, port=-1, parent=None):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        @param port port to be used for the cooperation server
        @type int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.shareButton.setIcon(EricPixmapCache.getIcon("sharedEditDisconnected"))
        self.startEditButton.setIcon(EricPixmapCache.getIcon("sharedEditStart"))
        self.sendEditButton.setIcon(EricPixmapCache.getIcon("sharedEditSend"))
        self.cancelEditButton.setIcon(EricPixmapCache.getIcon("sharedEditCancel"))

        self.hostEdit.lineEdit().setClearButtonEnabled(True)

        self.__ui = ui
        self.__client = CooperationClient(self)
        self.__myNickName = self.__client.nickName()

        self.__initChatMenu()
        self.__initUsersMenu()

        self.messageEdit.returnPressed.connect(self.__handleMessage)
        self.sendButton.clicked.connect(self.__handleMessage)
        self.__client.newMessage.connect(self.appendMessage)
        self.__client.newParticipant.connect(self.__newParticipant)
        self.__client.participantLeft.connect(self.__participantLeft)
        self.__client.connectionError.connect(self.__showErrorMessage)
        self.__client.cannotConnect.connect(self.__initialConnectionRefused)
        self.__client.editorCommand.connect(self.__editorCommandMessage)

        self.serverButton.setText(self.tr("Start Server"))
        self.serverLed.setColor(QColor(Qt.GlobalColor.red))
        if port == -1:
            port = Preferences.getCooperation("ServerPort")

        self.serverPortSpin.setValue(port)

        self.__setConnected(False)

        if Preferences.getCooperation("AutoStartServer"):
            self.on_serverButton_clicked()

        self.recent = []
        self.__loadHostsHistory()

    def __loadHostsHistory(self):
        """
        Private method to load the recently connected hosts.
        """
        self.__recent = []
        Preferences.Prefs.rsettings.sync()
        rh = Preferences.Prefs.rsettings.value(recentNameHosts)
        if rh is not None:
            self.__recent = rh[:20]
            self.hostEdit.clear()
            self.hostEdit.addItems(self.__recent)
            self.hostEdit.clearEditText()

    def __saveHostsHistory(self):
        """
        Private method to save the list of recently connected hosts.
        """
        Preferences.Prefs.rsettings.setValue(recentNameHosts, self.__recent)
        Preferences.Prefs.rsettings.sync()

    def __setHostsHistory(self, host):
        """
        Private method to remember the given host as the most recent entry.

        @param host host entry to remember
        @type str
        """
        if host in self.__recent:
            self.__recent.remove(host)
        self.__recent.insert(0, host)
        self.__saveHostsHistory()
        self.hostEdit.clear()
        self.hostEdit.addItems(self.__recent)

    def __clearHostsHistory(self):
        """
        Private slot to clear the hosts history.
        """
        self.__recent = []
        self.__saveHostsHistory()
        self.hostEdit.clear()
        self.hostEdit.addItems(self.__recent)

    def __handleMessage(self):
        """
        Private slot handling the Return key pressed in the message edit.
        """
        text = self.messageEdit.text()
        if text == "":
            return

        if text.startswith("/"):
            self.__showErrorMessage(
                self.tr("! Unknown command: {0}\n").format(text.split()[0])
            )
        else:
            self.__client.sendMessage(text)
            self.appendMessage(self.__myNickName, text)

        self.messageEdit.clear()

    def __newParticipant(self, nick):
        """
        Private slot handling a new participant joining.

        @param nick nick name of the new participant
        @type str
        """
        if nick == "":
            return

        color = self.chatEdit.textColor()
        self.chatEdit.setTextColor(Qt.GlobalColor.gray)
        self.chatEdit.append(
            QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss") + ":"
        )
        self.chatEdit.append(self.tr("* {0} has joined.\n").format(nick))
        self.chatEdit.setTextColor(color)

        QListWidgetItem(
            EricPixmapCache.getIcon(
                "chatUser{0}".format(1 + self.usersList.count() % 6)
            ),
            nick,
            self.usersList,
        )

        if not self.__connected:
            self.__setConnected(True)

        if not self.isVisible():
            self.__ui.showNotification(
                EricPixmapCache.getPixmap("cooperation48"),
                self.tr("New User"),
                self.tr("{0} has joined.").format(nick),
            )

    def __participantLeft(self, nick):
        """
        Private slot handling a participant leaving the session.

        @param nick nick name of the participant
        @type str
        """
        if nick == "":
            return

        items = self.usersList.findItems(nick, Qt.MatchFlag.MatchExactly)
        for item in items:
            self.usersList.takeItem(self.usersList.row(item))
            del item

            color = self.chatEdit.textColor()
            self.chatEdit.setTextColor(Qt.GlobalColor.gray)
            self.chatEdit.append(
                QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss") + ":"
            )
            self.chatEdit.append(self.tr("* {0} has left.\n").format(nick))
            self.chatEdit.setTextColor(color)

        if not self.__client.hasConnections():
            self.__setConnected(False)

        if not self.isVisible():
            self.__ui.showNotification(
                EricPixmapCache.getPixmap("cooperation48"),
                self.tr("User Left"),
                self.tr("{0} has left.").format(nick),
            )

    def appendMessage(self, from_, message):
        """
        Public slot to append a message to the display.

        @param from_ originator of the message
        @type str
        @param message message to be appended
        @type str
        """
        if from_ == "" or message == "":
            return

        self.chatEdit.append(
            QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            + " <"
            + from_
            + ">:"
        )
        self.chatEdit.append(message + "\n")
        bar = self.chatEdit.verticalScrollBar()
        bar.setValue(bar.maximum())

        if not self.isVisible():
            self.__ui.showNotification(
                EricPixmapCache.getPixmap("cooperation48"),
                self.tr("Message from <{0}>").format(from_),
                message,
            )

    @pyqtSlot(str)
    def on_hostEdit_editTextChanged(self, host):
        """
        Private slot handling the entry of a host to connect to.

        @param host host to connect to
        @type str
        """
        if not self.__connected:
            self.connectButton.setEnabled(host != "")

    def __getConnectionParameters(self):
        """
        Private method to determine the connection parameters.

        @return tuple with hostname and port
        @rtype tuple of (str, int)
        """
        hostEntry = self.hostEdit.currentText()
        if "@" in hostEntry:
            host, port = hostEntry.split("@")
            try:
                port = int(port)
            except ValueError:
                port = Preferences.getCooperation("ServerPort")
                self.hostEdit.setEditText("{0}@{1}".format(host, port))
        else:
            host = hostEntry
            port = Preferences.getCooperation("ServerPort")
            self.hostEdit.setEditText("{0}@{1}".format(host, port))
        return host, port

    @pyqtSlot()
    def on_connectButton_clicked(self):
        """
        Private slot initiating the connection.
        """
        if not self.__connected:
            host, port = self.__getConnectionParameters()
            self.__setHostsHistory(self.hostEdit.currentText())
            if not self.__client.isListening():
                self.on_serverButton_clicked()
            if self.__client.isListening():
                self.__client.connectToHost(host, port)
                self.__setConnected(True)
        else:
            self.__client.disconnectConnections()
            self.__setConnected(False)

    @pyqtSlot()
    def on_clearHostsButton_clicked(self):
        """
        Private slot to clear the hosts list.
        """
        self.__clearHostsHistory()

    @pyqtSlot()
    def on_serverButton_clicked(self):
        """
        Private slot to start the server.
        """
        if self.__client.isListening():
            self.__client.close()
            self.serverButton.setText(self.tr("Start Server"))
            self.serverPortSpin.setEnabled(True)
            if self.serverPortSpin.value() != Preferences.getCooperation("ServerPort"):
                self.serverPortSpin.setValue(Preferences.getCooperation("ServerPort"))
            self.serverLed.setColor(QColor(Qt.GlobalColor.red))
        else:
            res, port = self.__client.startListening(self.serverPortSpin.value())
            if res:
                self.serverButton.setText(self.tr("Stop Server"))
                self.serverPortSpin.setValue(port)
                self.serverPortSpin.setEnabled(False)
                self.serverLed.setColor(QColor(Qt.GlobalColor.green))
            else:
                self.__showErrorMessage(
                    self.tr("! Server Error: {0}\n").format(self.__client.errorString())
                )

    def __setConnected(self, connected):
        """
        Private slot to set the connected state.

        @param connected new connected state
        @type bool
        """
        if connected:
            self.connectButton.setText(self.tr("Disconnect"))
            self.connectButton.setEnabled(True)
            self.connectionLed.setColor(QColor(Qt.GlobalColor.green))
        else:
            self.connectButton.setText(self.tr("Connect"))
            self.connectButton.setEnabled(self.hostEdit.currentText() != "")
            self.connectionLed.setColor(QColor(Qt.GlobalColor.red))
            self.on_cancelEditButton_clicked()
            self.shareButton.setChecked(False)
            self.on_shareButton_clicked(False)
        self.__connected = connected
        self.hostEdit.setEnabled(not connected)
        self.serverButton.setEnabled(not connected)
        self.sharingGroup.setEnabled(connected)

        if connected:
            vm = ericApp().getObject("ViewManager")
            aw = vm.activeWindow()
            if aw:
                self.checkEditorActions(aw)

    def __showErrorMessage(self, message):
        """
        Private slot to show an error message.

        @param message error message to show
        @type str
        """
        color = self.chatEdit.textColor()
        self.chatEdit.setTextColor(Qt.GlobalColor.red)
        self.chatEdit.append(
            QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss") + ":"
        )
        self.chatEdit.append(message + "\n")
        self.chatEdit.setTextColor(color)

    def __initialConnectionRefused(self):
        """
        Private slot to handle the refusal of the initial connection.
        """
        self.__setConnected(False)

    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        if not self.__client.isListening():
            self.serverPortSpin.setValue(Preferences.getCooperation("ServerPort"))
            if Preferences.getCooperation("AutoStartServer"):
                self.on_serverButton_clicked()

    def getClient(self):
        """
        Public method to get a reference to the cooperation client.

        @return reference to the cooperation client
        @rtype CooperationClient
        """
        return self.__client

    def __editorCommandMessage(self, hashStr, fileName, message):
        """
        Private slot to handle editor command messages from the client.

        @param hashStr hash of the project
        @type str
        @param fileName project relative file name of the editor
        @type str
        @param message command message
        @type str
        """
        from eric7.QScintilla.Editor import Editor

        self.editorCommand.emit(hashStr, fileName, message)

        if message.startswith(
            Editor.StartEditToken + Editor.Separator
        ) or message.startswith(Editor.EndEditToken + Editor.Separator):
            vm = ericApp().getObject("ViewManager")
            aw = vm.activeWindow()
            if aw:
                self.checkEditorActions(aw)

    @pyqtSlot(bool)
    def on_shareButton_clicked(self, checked):
        """
        Private slot to share the current editor.

        @param checked flag indicating the button state
        @type bool
        """
        if checked:
            self.shareButton.setIcon(EricPixmapCache.getIcon("sharedEditConnected"))
        else:
            self.shareButton.setIcon(EricPixmapCache.getIcon("sharedEditDisconnected"))
        self.startEditButton.setEnabled(checked)

        self.shareEditor.emit(checked)

    @pyqtSlot(bool)
    def on_startEditButton_clicked(self, checked):
        """
        Private slot to start a shared edit session.

        @param checked flag indicating the button state
        @type bool
        """
        if checked:
            self.sendEditButton.setEnabled(True)
            self.cancelEditButton.setEnabled(True)
            self.shareButton.setEnabled(False)
            self.startEditButton.setEnabled(False)

            self.startEdit.emit()

    @pyqtSlot()
    def on_sendEditButton_clicked(self):
        """
        Private slot to end a shared edit session and send the changes.
        """
        self.sendEditButton.setEnabled(False)
        self.cancelEditButton.setEnabled(False)
        self.shareButton.setEnabled(True)
        self.startEditButton.setEnabled(True)
        self.startEditButton.setChecked(False)

        self.sendEdit.emit()

    @pyqtSlot()
    def on_cancelEditButton_clicked(self):
        """
        Private slot to cancel a shared edit session.
        """
        self.sendEditButton.setEnabled(False)
        self.cancelEditButton.setEnabled(False)
        self.shareButton.setEnabled(True)
        self.startEditButton.setEnabled(True)
        self.startEditButton.setChecked(False)

        self.cancelEdit.emit()

    def checkEditorActions(self, editor):
        """
        Public slot to set action according to an editor's state.

        @param editor reference to the editor
        @type Editor
        """
        shareable, sharing, editing, remoteEditing = editor.getSharingStatus()

        self.shareButton.setChecked(sharing)
        if sharing:
            self.shareButton.setIcon(EricPixmapCache.getIcon("sharedEditConnected"))
        else:
            self.shareButton.setIcon(EricPixmapCache.getIcon("sharedEditDisconnected"))
        self.startEditButton.setChecked(editing)

        self.shareButton.setEnabled(shareable and not editing)
        self.startEditButton.setEnabled(sharing and not editing and not remoteEditing)
        self.sendEditButton.setEnabled(editing)
        self.cancelEditButton.setEnabled(editing)

    def __initChatMenu(self):
        """
        Private slot to initialize the chat edit context menu.
        """
        self.__chatMenu = QMenu(self)
        self.__copyChatAct = self.__chatMenu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy"), self.__copyChat
        )
        self.__chatMenu.addSeparator()
        self.__cutAllChatAct = self.__chatMenu.addAction(
            EricPixmapCache.getIcon("editCut"), self.tr("Cut all"), self.__cutAllChat
        )
        self.__copyAllChatAct = self.__chatMenu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy all"), self.__copyAllChat
        )
        self.__chatMenu.addSeparator()
        self.__clearChatAct = self.__chatMenu.addAction(
            EricPixmapCache.getIcon("editDelete"), self.tr("Clear"), self.__clearChat
        )
        self.__chatMenu.addSeparator()
        self.__saveChatAct = self.__chatMenu.addAction(
            EricPixmapCache.getIcon("fileSave"), self.tr("Save"), self.__saveChat
        )

        self.on_chatEdit_copyAvailable(False)

    @pyqtSlot(bool)
    def on_chatEdit_copyAvailable(self, yes):
        """
        Private slot to react to text selection/deselection of the chat edit.

        @param yes flag signaling the availability of selected text
        @type bool
        """
        self.__copyChatAct.setEnabled(yes)

    @pyqtSlot(QPoint)
    def on_chatEdit_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu for the chat.

        @param pos the position of the mouse pointer
        @type QPoint
        """
        enable = self.chatEdit.toPlainText() != ""
        self.__saveChatAct.setEnabled(enable)
        self.__copyAllChatAct.setEnabled(enable)
        self.__cutAllChatAct.setEnabled(enable)
        self.__chatMenu.popup(self.chatEdit.mapToGlobal(pos))

    def __clearChat(self):
        """
        Private slot to clear the contents of the chat display.
        """
        self.chatEdit.clear()

    def __saveChat(self):
        """
        Private slot to save the contents of the chat display.
        """
        txt = self.chatEdit.toPlainText()
        if txt:
            fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
                self,
                self.tr("Save Chat"),
                "",
                self.tr("Text Files (*.txt);;All Files (*)"),
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
                        self.tr("Save Chat"),
                        self.tr(
                            "<p>The file <b>{0}</b> already exists."
                            " Overwrite it?</p>"
                        ).format(fpath),
                        icon=EricMessageBox.Warning,
                    )
                    if not res:
                        return

                try:
                    with fpath.open("w", encoding="utf-8") as f:
                        f.write(txt)
                except OSError as err:
                    EricMessageBox.critical(
                        self,
                        self.tr("Error saving Chat"),
                        self.tr(
                            """<p>The chat contents could not be"""
                            """ written to <b>{0}</b></p>"""
                            """<p>Reason: {1}</p>"""
                        ).format(fpath, str(err)),
                    )

    def __copyChat(self):
        """
        Private slot to copy the contents of the chat display to the clipboard.
        """
        self.chatEdit.copy()

    def __copyAllChat(self):
        """
        Private slot to copy the contents of the chat display to the clipboard.
        """
        txt = self.chatEdit.toPlainText()
        if txt:
            cb = QApplication.clipboard()
            cb.setText(txt)

    def __cutAllChat(self):
        """
        Private slot to cut the contents of the chat display to the clipboard.
        """
        txt = self.chatEdit.toPlainText()
        if txt:
            cb = QApplication.clipboard()
            cb.setText(txt)
        self.chatEdit.clear()

    def __initUsersMenu(self):
        """
        Private slot to initialize the users list context menu.
        """
        self.__usersMenu = QMenu(self)
        self.__kickUserAct = self.__usersMenu.addAction(
            EricPixmapCache.getIcon("chatKickUser"),
            self.tr("Kick User"),
            self.__kickUser,
        )
        self.__banUserAct = self.__usersMenu.addAction(
            EricPixmapCache.getIcon("chatBanUser"), self.tr("Ban User"), self.__banUser
        )
        self.__banKickUserAct = self.__usersMenu.addAction(
            EricPixmapCache.getIcon("chatBanKickUser"),
            self.tr("Ban and Kick User"),
            self.__banKickUser,
        )

    @pyqtSlot(QPoint)
    def on_usersList_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu for the users list.

        @param pos the position of the mouse pointer
        @type QPoint
        """
        itm = self.usersList.itemAt(pos)
        self.__kickUserAct.setEnabled(itm is not None)
        self.__banUserAct.setEnabled(itm is not None)
        self.__banKickUserAct.setEnabled(itm is not None)
        self.__usersMenu.popup(self.usersList.mapToGlobal(pos))

    def __kickUser(self):
        """
        Private slot to disconnect a user.
        """
        itm = self.usersList.currentItem()
        self.__client.kickUser(itm.text())

        color = self.chatEdit.textColor()
        self.chatEdit.setTextColor(Qt.GlobalColor.darkYellow)
        self.chatEdit.append(
            QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss") + ":"
        )
        self.chatEdit.append(
            self.tr("* {0} has been kicked.\n").format(itm.text().split("@")[0])
        )
        self.chatEdit.setTextColor(color)

    def __banUser(self):
        """
        Private slot to ban a user.
        """
        itm = self.usersList.currentItem()
        self.__client.banUser(itm.text())

        color = self.chatEdit.textColor()
        self.chatEdit.setTextColor(Qt.GlobalColor.darkYellow)
        self.chatEdit.append(
            QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss") + ":"
        )
        self.chatEdit.append(
            self.tr("* {0} has been banned.\n").format(itm.text().split("@")[0])
        )
        self.chatEdit.setTextColor(color)

    def __banKickUser(self):
        """
        Private slot to ban and kick a user.
        """
        itm = self.usersList.currentItem()
        self.__client.banKickUser(itm.text())

        color = self.chatEdit.textColor()
        self.chatEdit.setTextColor(Qt.GlobalColor.darkYellow)
        self.chatEdit.append(
            QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss") + ":"
        )
        self.chatEdit.append(
            self.tr("* {0} has been banned and kicked.\n").format(
                itm.text().split("@")[0]
            )
        )
        self.chatEdit.setTextColor(color)

    def shutdown(self):
        """
        Public method to shut down the cooperation system.
        """
        self.__client.disconnectConnections()
        self.__setConnected(False)
