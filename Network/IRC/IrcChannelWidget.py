# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the IRC channel widget.
"""

import pathlib
import re

from itertools import zip_longest

from PyQt6.QtCore import (
    QCoreApplication,
    QDateTime,
    QPoint,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QDesktopServices, QIcon, QPainter, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QInputDialog,
    QLineEdit,
    QListWidgetItem,
    QMenu,
    QWidget,
)

from eric7 import EricUtilities, Preferences
from eric7.__version__ import Version
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import OSUtilities
from eric7.UI.Info import Copyright

from .IrcUtilities import getChannelModesDict, ircFilter, ircTimestamp
from .Ui_IrcChannelWidget import Ui_IrcChannelWidget


class IrcUserItem(QListWidgetItem):
    """
    Class implementing a list widget item containing an IRC channel user.
    """

    Normal = 0x00  # no privileges
    Operator = 0x01  # channel operator
    Voice = 0x02  # voice operator
    Admin = 0x04  # administrator
    Halfop = 0x08  # half operator
    Owner = 0x10  # channel owner
    Away = 0x80  # user away

    PrivilegeMapping = {
        "a": Away,
        "o": Operator,
        "O": Owner,
        "v": Voice,
    }

    def __init__(self, name, parent=None):
        """
        Constructor

        @param name string with user name and privilege prefix
        @type str
        @param parent reference to the parent widget
        @type QListWidget or QListWidgetItem
        """
        super().__init__(name, parent)

        self.__privilege = IrcUserItem.Normal
        self.__name = name
        self.__ignored = False

        self.__setText()
        self.__setIcon()

    def name(self):
        """
        Public method to get the user name.

        @return user name
        @rtype str
        """
        return self.__name

    def setName(self, name):
        """
        Public method to set a new nick name.

        @param name new nick name for the user
        @type str
        """
        self.__name = name
        self.__setText()

    def changePrivilege(self, privilege):
        """
        Public method to set or unset a user privilege.

        @param privilege privilege to set or unset
        @type str
        """
        oper = privilege[0]
        priv = privilege[1]
        if priv in IrcUserItem.PrivilegeMapping:
            if oper == "+":
                self.__privilege |= IrcUserItem.PrivilegeMapping[priv]
            elif oper == "-":
                self.__privilege &= ~IrcUserItem.PrivilegeMapping[priv]
        self.__setIcon()

    def clearPrivileges(self):
        """
        Public method to clear the user privileges.
        """
        self.__privilege = IrcUserItem.Normal
        self.__setIcon()

    def __setText(self):
        """
        Private method to set the user item text.
        """
        if self.__ignored:
            self.setText(
                QCoreApplication.translate("IrcUserItem", "{0} (ignored)").format(
                    self.__name
                )
            )
        else:
            self.setText(self.__name)

    def __setIcon(self):
        """
        Private method to set the icon dependent on user privileges.
        """
        # step 1: determine the icon
        if self.__privilege & IrcUserItem.Voice:
            icon = EricPixmapCache.getIcon("ircVoice")
        elif self.__privilege & IrcUserItem.Owner:
            icon = EricPixmapCache.getIcon("ircOwner")
        elif self.__privilege & IrcUserItem.Operator:
            icon = EricPixmapCache.getIcon("ircOp")
        elif self.__privilege & IrcUserItem.Halfop:
            icon = EricPixmapCache.getIcon("ircHalfop")
        elif self.__privilege & IrcUserItem.Admin:
            icon = EricPixmapCache.getIcon("ircAdmin")
        else:
            icon = EricPixmapCache.getIcon("ircNormal")
        if self.__privilege & IrcUserItem.Away:
            icon = self.__awayIcon(icon)

        # step 2: set the icon
        self.setIcon(icon)

    def __awayIcon(self, icon):
        """
        Private method to convert an icon to an away icon.

        @param icon icon to be converted
        @type QIcon
        @return away icon
        @rtype QIcon
        """
        pix1 = icon.pixmap(16, 16)
        pix2 = EricPixmapCache.getPixmap("ircAway")
        painter = QPainter(pix1)
        painter.drawPixmap(0, 0, pix2)
        painter.end()
        return QIcon(pix1)

    def parseWhoFlags(self, flags):
        """
        Public method to parse the user flags reported by a WHO command.

        @param flags user flags as reported by WHO
        @type str
        """
        # H The user is not away.
        # G The user is set away.
        # * The user is an IRC operator.
        # @ The user is a channel op in the channel listed in the first field.
        # + The user is voiced in the channel listed.
        if flags.endswith("@"):
            privilege = IrcUserItem.Operator
        elif flags.endswith("+"):
            privilege = IrcUserItem.Voice
        else:
            privilege = IrcUserItem.Normal
        if "*" in flags:
            privilege = IrcUserItem.Admin
        if flags.startswith("G"):
            privilege |= IrcUserItem.Away
        self.__privilege = privilege
        self.__setIcon()

    def canChangeTopic(self):
        """
        Public method to check, if the user is allowed to change the topic.

        @return flag indicating that the topic can be changed
        @rtype bool
        """
        return (
            bool(self.__privilege & IrcUserItem.Operator)
            or bool(self.__privilege & IrcUserItem.Admin)
            or bool(self.__privilege & IrcUserItem.Owner)
        )

    def setIgnored(self, ignored):
        """
        Public method to set the user status to ignored.

        @param ignored flag indicating the new ignored status
        @type bool
        """
        self.__ignored = ignored
        self.__setText()

    def isIgnored(self):
        """
        Public method to check, if this user is ignored.

        @return flag indicating the ignored status
        @rtype bool
        """
        return self.__ignored


class IrcChannelWidget(QWidget, Ui_IrcChannelWidget):
    """
    Class implementing the IRC channel widget.

    @signal sendData(str) emitted to send a message to the channel
    @signal sendCtcpRequest(str, str, str) emitted to send a CTCP request
    @signal sendCtcpReply(str, str) emitted to send a CTCP reply
    @signal channelClosed(str) emitted after the user has left the channel
    @signal openPrivateChat(str) emitted to open a "channel" for private
        messages
    @signal awayCommand(str) emitted to set the away status via the /away
        command
    @signal leaveChannels(list) emitted to leave a list of channels
    @signal leaveAllChannels() emitted to leave all channels
    """

    sendData = pyqtSignal(str)
    sendCtcpRequest = pyqtSignal(str, str, str)
    sendCtcpReply = pyqtSignal(str, str)
    channelClosed = pyqtSignal(str)
    openPrivateChat = pyqtSignal(str)
    awayCommand = pyqtSignal(str)
    leaveChannels = pyqtSignal(list)
    leaveAllChannels = pyqtSignal()

    UrlRe = re.compile(
        r"""((?:http|ftp|https):\/\/[\w\-_]+(?:\.[\w\-_]+)+"""
        r"""(?:[\w\-\.,@?^=%&amp;:/~\+#]*[\w\-\@?^=%&amp;/~\+#])?)"""
    )

    JoinIndicator = "--&gt;"
    LeaveIndicator = "&lt;--"
    MessageIndicator = "***"

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__ui = ericApp().getObject("UserInterface")
        self.__ircWidget = parent

        self.editTopicButton.setIcon(EricPixmapCache.getIcon("ircEditTopic"))
        self.editTopicButton.hide()

        height = self.usersList.height() + self.messages.height()
        self.splitter.setSizes([int(height * 0.3), int(height * 0.7)])

        self.__initMessagesMenu()
        self.__initUsersMenu()

        self.__name = ""
        self.__userName = ""
        self.__partMessage = ""
        self.__prefixToPrivilege = {}
        self.__private = False
        self.__privatePartner = ""
        self.__whoIsNick = ""

        self.__markerLine = ""
        self.__hidden = True

        self.__serviceNamesLower = ["nickserv", "chanserv", "memoserv"]

        self.__patterns = [
            # :foo_!n=foo@foohost.bar.net PRIVMSG #eric-ide :some long message
            # :foo_!n=foo@foohost.bar.net PRIVMSG bar_ :some long message
            (re.compile(r":([^!]+)!([^ ]+)\sPRIVMSG\s([^ ]+)\s:(.*)"), self.__message),
            # :foo_!n=foo@foohost.bar.net JOIN :#eric-ide
            (re.compile(r":([^!]+)!([^ ]+)\sJOIN\s:?([^ ]+)"), self.__userJoin),
            # :foo_!n=foo@foohost.bar.net PART #eric-ide :part message
            (re.compile(r":([^!]+).*\sPART\s([^ ]+)\s:(.*)"), self.__userPart),
            # :foo_!n=foo@foohost.bar.net PART #eric-ide
            (re.compile(r":([^!]+).*\sPART\s([^ ]+)\s*"), self.__userPart),
            # :foo_!n=foo@foohost.bar.net QUIT :quit message
            (re.compile(r":([^!]+).*\sQUIT\s:(.*)"), self.__userQuit),
            # :foo_!n=foo@foohost.bar.net QUIT
            (re.compile(r":([^!]+).*\sQUIT\s*"), self.__userQuit),
            # :foo_!n=foo@foohost.bar.net NICK :newnick
            (re.compile(r":([^!]+).*\sNICK\s:(.*)"), self.__userNickChange),
            # :foo_!n=foo@foohost.bar.net MODE #eric-ide +o foo_
            (
                re.compile(r":([^!]+).*\sMODE\s([^ ]+)\s([+-][ovO]+)\s([^ ]+).*"),
                self.__setUserPrivilege,
            ),
            # :cameron.libera.chat MODE #eric-ide +ns
            (re.compile(r":([^ ]+)\sMODE\s([^ ]+)\s(.+)"), self.__updateChannelModes),
            # :foo_!n=foo@foohost.bar.net TOPIC #eric-ide :eric - Python IDE
            (re.compile(r":.*\sTOPIC\s([^ ]+)\s:(.*)"), self.__setTopic),
            # :sturgeon.libera.chat 301 foo_ bar :Gone away for now
            (re.compile(r":.*\s301\s([^ ]+)\s([^ ]+)\s:(.+)"), self.__userAway),
            # :sturgeon.libera.chat 315 foo_ #eric-ide :End of /WHO list.
            (re.compile(r":.*\s315\s[^ ]+\s([^ ]+)\s:(.*)"), self.__whoEnd),
            # :zelazny.libera.chat 324 foo_ #eric-ide +cnt
            (re.compile(r":.*\s324\s.*\s([^ ]+)\s(.+)"), self.__channelModes),
            # :zelazny.libera.chat 328 foo_ #eric-ide :http://www.bugger.com/
            (re.compile(r":.*\s328\s.*\s([^ ]+)\s:(.+)"), self.__channelUrl),
            # :zelazny.libera.chat 329 foo_ #eric-ide 1353001005
            (re.compile(r":.*\s329\s.*\s([^ ]+)\s(.+)"), self.__channelCreated),
            # :zelazny.libera.chat 332 foo_ #eric-ide :eric support channel
            (re.compile(r":.*\s332\s.*\s([^ ]+)\s:(.*)"), self.__setTopic),
            # :zelazny.libera.chat foo_ 333 #eric-ide foo 1353089020
            (re.compile(r":.*\s333\s.*\s([^ ]+)\s([^ ]+)\s(\d+)"), self.__topicCreated),
            # :cameron.libera.chat 352 detlev_ #eric-ide ~foo foohost.bar.net
            # cameron.libera.chat foo_ H :0 Foo Bar
            (
                re.compile(
                    r":.*\s352\s[^ ]+\s([^ ]+)\s([^ ]+)\s([^ ]+)\s[^ ]+\s([^ ]+)"
                    r"\s([^ ]+)\s:\d+\s(.*)"
                ),
                self.__whoEntry,
            ),
            # :zelazny.libera.chat 353 foo_ @ #eric-ide :@user1 +user2 user3
            (re.compile(r":.*\s353\s.*\s.\s([^ ]+)\s:(.*)"), self.__userList),
            # :sturgeon.libera.chat 354 foo_ 42 ChanServ H@
            (re.compile(r":.*\s354\s[^ ]+\s42\s([^ ]+)\s(.*)"), self.__autoWhoEntry),
            # :zelazny.libera.chat 366 foo_ #eric-ide :End of /NAMES list.
            (re.compile(r":.*\s366\s.*\s([^ ]+)\s:(.*)"), self.__ignore),
            # :sturgeon.libera.chat 704 foo_ index :Help topics available:
            (re.compile(r":.*\s70[456]\s[^ ]+\s([^ ]+)\s:(.*)"), self.__help),
            # WHOIS replies
            # :sturgeon.libera.chat 311 foo_ bar ~bar barhost.foo.net * :Bar
            (
                re.compile(r":.*\s311\s[^ ]+\s([^ ]+)\s([^ ]+)\s([^ ]+)\s\*\s:(.*)"),
                self.__whoIsUser,
            ),
            # :sturgeon.libera.chat 319 foo_ bar :@#eric-ide
            (re.compile(r":.*\s319\s[^ ]+\s([^ ]+)\s:(.*)"), self.__whoIsChannels),
            # :sturgeon.libera.chat 312 foo_ bar sturgeon.libera.chat :London
            (
                re.compile(r":.*\s312\s[^ ]+\s([^ ]+)\s([^ ]+)\s:(.*)"),
                self.__whoIsServer,
            ),
            # :sturgeon.libera.chat 671 foo_ bar :is using a secure connection
            (re.compile(r":.*\s671\s[^ ]+\s([^ ]+)\s:.*"), self.__whoIsSecure),
            # :sturgeon.libera.chat 317 foo_ bar 3758 1355046912 :seconds
            # idle, signon time
            (
                re.compile(r":.*\s317\s[^ ]+\s([^ ]+)\s(\d+)\s(\d+)\s:.*"),
                self.__whoIsIdle,
            ),
            # :sturgeon.libera.chat 330 foo_ bar bar :is logged in as
            (
                re.compile(r":.*\s330\s[^ ]+\s([^ ]+)\s([^ ]+)\s:.*"),
                self.__whoIsAccount,
            ),
            # :sturgeon.libera.chat 318 foo_ bar :End of /WHOIS list.
            (re.compile(r":.*\s318\s[^ ]+\s([^ ]+)\s:(.*)"), self.__whoIsEnd),
            # :sturgeon.libera.chat 307 foo_ bar :is an identified user
            (re.compile(r":.*\s307\s[^ ]+\s([^ ]+)\s:(.*)"), self.__whoIsIdentify),
            # :sturgeon.libera.chat 320 foo_ bar :is an identified user
            (re.compile(r":.*\s320\s[^ ]+\s([^ ]+)\s:(.*)"), self.__whoIsIdentify),
            # :sturgeon.libera.chat 310 foo_ bar :is available for help
            (re.compile(r":.*\s310\s[^ ]+\s([^ ]+)\s:(.*)"), self.__whoIsHelper),
            # :sturgeon.libera.chat 338 foo_ bar real.ident@real.host
            # 12.34.56.78 :Actual user@host, Actual IP
            (
                re.compile(r":.*\s338\s[^ ]+\s([^ ]+)\s([^ ]+)\s([^ ]+)\s:.*"),
                self.__whoIsActually,
            ),
            # :sturgeon.libera.chat 313 foo_ bar :is an IRC Operator
            (re.compile(r":.*\s313\s[^ ]+\s([^ ]+)\s:(.*)"), self.__whoIsOperator),
            # :sturgeon.libera.chat 378 foo_ bar :is connecting from
            # *@mnch-4d044d5a.pool.mediaWays.net 77.4.77.90
            (
                re.compile(r":.*\s378\s[^ ]+\s([^ ]+)\s:.*\s([^ ]+)\s([^ ]+)"),
                self.__whoIsConnection,
            ),
        ]

        self.__autoWhoTemplate = "WHO {0} %tnf,42"
        self.__autoWhoTimer = QTimer()
        self.__autoWhoTimer.setSingleShot(True)
        self.__autoWhoTimer.timeout.connect(self.__sendAutoWhoCommand)
        self.__autoWhoRequested = False

    @pyqtSlot()
    def on_messageEdit_returnPressed(self):
        """
        Private slot to send a message to the channel.
        """
        msg = self.messageEdit.text()
        if msg:
            self.__processUserMessage(msg)

    def __processUserMessage(self, msg):
        """
        Private method to process a message entered by the user or via the
        user list context menu.

        @param msg message to be processed
        @type str
        """
        self.messages.append(
            '<font color="{0}">{2} <b>&lt;</b><font color="{1}">{3}</font>'
            "<b>&gt;</b> {4}</font>".format(
                Preferences.getIrc("ChannelMessageColour"),
                Preferences.getIrc("OwnNickColour"),
                ircTimestamp(),
                self.__userName,
                EricUtilities.html_encode(msg),
            )
        )

        if msg.startswith("/"):
            if self.__private:
                EricMessageBox.information(
                    self,
                    self.tr("Send Message"),
                    self.tr(
                        """Messages starting with a '/' are not allowed"""
                        """ in private chats."""
                    ),
                )
            else:
                sendData = True
                # flag set to False, if command was handled

                msgList = msg.split()
                cmd = msgList[0][1:].upper()
                if cmd in ["MSG", "QUERY"]:
                    cmd = "PRIVMSG"
                    if len(msgList) > 1:
                        if msgList[1].strip().lower() in self.__serviceNamesLower:
                            msg = (
                                "PRIVMSG "
                                + msgList[1].strip().lower()
                                + " :"
                                + " ".join(msgList[2:])
                            )
                        else:
                            msg = "PRIVMSG {0} :{1}".format(
                                msgList[1], " ".join(msgList[2:])
                            )
                    else:
                        msgList[0] = cmd
                        msg = " ".join(msgList)
                elif cmd == "NOTICE":
                    if len(msgList) > 2:
                        msg = "NOTICE {0} :{1}".format(
                            msgList[1], " ".join(msgList[2:])
                        )
                    else:
                        msg = "NOTICE {0}".format(" ".join(msgList[1:]))
                elif cmd == "PING":
                    receiver = msgList[1]
                    msg = "PING {0} "
                    self.sendCtcpRequest.emit(receiver, "PING", "")
                    sendData = False
                elif cmd == "IGNORE":
                    sendData = False
                    if len(msgList) > 1:
                        if msgList[1] == "-r":
                            ignored = False
                            userNamesList = msgList[2:]
                        else:
                            ignored = True
                            userNamesList = msgList[1:]
                    else:
                        userNamesList = []
                    userNames = ",".join(u.rstrip(",") for u in userNamesList).split(
                        ","
                    )
                    for userName in userNames:
                        itm = self.__findUser(userName)
                        if itm:
                            itm.setIgnored(ignored)
                elif cmd == "UNIGNORE":
                    sendData = False
                    if len(msgList) > 1:
                        userNamesList = msgList[1:]
                    else:
                        userNamesList = []
                    userNames = ",".join(u.rstrip(",") for u in userNamesList).split(
                        ","
                    )
                    for userName in userNames:
                        itm = self.__findUser(userName)
                        if itm:
                            itm.setIgnored(False)
                elif cmd == "AWAY":
                    sendData = False
                    if len(msgList) > 1:
                        msg = " ".join(msgList[1:])
                    else:
                        msg = ""
                    self.awayCommand.emit(msg)
                elif cmd == "JOIN":
                    sendData = False
                    if len(msgList) > 1:
                        channels = msgList[1].split(",")
                        if len(msgList) > 2:
                            keys = msgList[2].split(",")
                        else:
                            keys = []
                        for channel, key in zip_longest(channels, keys, fillvalue=""):
                            self.__ircWidget.joinChannel(channel, key)
                elif cmd == "PART":
                    sendData = False
                    if len(msgList) == 1:
                        self.leaveChannel()
                    else:
                        self.leaveChannels.emit(msgList[1:])
                elif cmd == "PARTALL":
                    sendData = False
                    self.leaveAllChannels.emit()
                else:
                    msg = msg[1:]
                if sendData:
                    self.sendData.emit(msg)
        else:
            if self.__private:
                self.sendData.emit("PRIVMSG " + self.__privatePartner + " :" + msg)
            else:
                self.sendData.emit("PRIVMSG " + self.__name + " :" + msg)

        self.messageEdit.clear()
        self.unsetMarkerLine()

    def requestLeave(self):
        """
        Public method to leave the channel.
        """
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Leave IRC channel"),
            self.tr(
                """Do you really want to leave the IRC channel <b>{0}</b>?"""
            ).format(self.__name),
        )
        if ok:
            self.leaveChannel()

    def leaveChannel(self):
        """
        Public slot to leave the channel.
        """
        if not self.__private:
            self.sendData.emit("PART " + self.__name + " :" + self.__partMessage)
        self.channelClosed.emit(self.__name)

    def name(self):
        """
        Public method to get the name of the channel.

        @return name of the channel
        @rtype str
        """
        return self.__name

    def setName(self, name):
        """
        Public method to set the name of the channel.

        @param name of the channel
        @type str
        """
        self.__name = name

    def getUsersCount(self):
        """
        Public method to get the users count of the channel.

        @return users count of the channel
        @rtype int
        """
        return self.usersList.count()

    def userName(self):
        """
        Public method to get the nick name of the user.

        @return nick name of the user
        @rtype str
        """
        return self.__userName

    def setUserName(self, name):
        """
        Public method to set the user name for the channel.

        @param name user name for the channel
        @type str
        """
        self.__userName = name

    def partMessage(self):
        """
        Public method to get the part message.

        @return part message
        @rtype str
        """
        return self.__partMessage

    def setPartMessage(self, message):
        """
        Public method to set the part message.

        @param message message to be used for PART messages
        @type str
        """
        self.__partMessage = message

    def setPrivate(self, private, partner=""):
        """
        Public method to set the private chat mode.

        @param private flag indicating private chat mode
        @type bool
        @param partner name of the partner user
        @type str
        """
        self.__private = private
        self.__privatePartner = partner
        self.editTopicButton.setEnabled(private)

    def setPrivateInfo(self, infoText):
        """
        Public method to set some info text for private chat mode.

        @param infoText info text to be shown
        @type str
        """
        if self.__private:
            self.topicLabel.setText(infoText)

    def handleMessage(self, line):
        """
        Public method to handle the message sent by the server.

        @param line server message
        @type str
        @return flag indicating, if the message was handled
        @rtype bool
        """
        for patternRe, patternFunc in self.__patterns:
            match = patternRe.match(line)
            if match is not None and patternFunc(match):
                return True

        return False

    def __message(self, match):
        """
        Private method to handle messages to the channel.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   sender user name
        # group(2)   sender user@host
        # group(3)   target nick
        # group(4)   message
        if match.group(3).lower() == self.__name.lower():
            senderName = match.group(1)
            itm = self.__findUser(senderName)
            if itm and itm.isIgnored():
                # user should be ignored
                return True

            if match.group(4).startswith("\x01"):
                return self.__handleCtcp(match)

            self.addMessage(senderName, match.group(4))
            if self.__private and not self.topicLabel.text():
                self.setPrivateInfo("{0} - {1}".format(match.group(1), match.group(2)))
            return True

        return False

    def addMessage(self, sender, msg):
        """
        Public method to add a message from external.

        @param sender nick name of the sender
        @type str
        @param msg message received from sender
        @type str
        """
        self.__appendMessage(
            '<font color="{0}">{2} <b>&lt;</b><font color="{1}">{3}</font>'
            "<b>&gt;</b> {4}</font>".format(
                Preferences.getIrc("ChannelMessageColour"),
                Preferences.getIrc("NickColour"),
                ircTimestamp(),
                sender,
                ircFilter(msg),
            )
        )
        if Preferences.getIrc("ShowNotifications"):
            if Preferences.getIrc("NotifyMessage"):
                self.__ui.showNotification(
                    EricPixmapCache.getPixmap("irc48"), self.tr("Channel Message"), msg
                )
            elif (
                Preferences.getIrc("NotifyNick")
                and self.__userName.lower() in msg.lower()
            ):
                self.__ui.showNotification(
                    EricPixmapCache.getPixmap("irc48"), self.tr("Nick mentioned"), msg
                )

    def addUsers(self, users):
        """
        Public method to add users to the channel.

        @param users list of user names to add
        @type list of str
        """
        for user in users:
            itm = self.__findUser(user)
            if itm is None:
                IrcUserItem(user, self.usersList)

    def __userJoin(self, match):
        """
        Private method to handle a user joining the channel.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(3).lower() == self.__name.lower():
            if self.__userName != match.group(1):
                IrcUserItem(match.group(1), self.usersList)
                msg = self.tr("{0} has joined the channel {1} ({2}).").format(
                    match.group(1), self.__name, match.group(2)
                )
                self.__addManagementMessage(IrcChannelWidget.JoinIndicator, msg)
            else:
                msg = self.tr("You have joined the channel {0} ({1}).").format(
                    self.__name, match.group(2)
                )
                self.__addManagementMessage(IrcChannelWidget.JoinIndicator, msg)
            if Preferences.getIrc("ShowNotifications") and Preferences.getIrc(
                "NotifyJoinPart"
            ):
                self.__ui.showNotification(
                    EricPixmapCache.getPixmap("irc48"), self.tr("Join Channel"), msg
                )
            return True

        return False

    def __userPart(self, match):
        """
        Private method to handle a user leaving the channel.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(2).lower() == self.__name.lower():
            itm = self.__findUser(match.group(1))
            self.usersList.takeItem(self.usersList.row(itm))
            del itm
            if match.lastindex == 2:
                msg = self.tr("{0} has left {1}.").format(match.group(1), self.__name)
                nmsg = msg
                self.__addManagementMessage(IrcChannelWidget.LeaveIndicator, msg)
            else:
                msg = self.tr("{0} has left {1}: {2}.").format(
                    match.group(1), self.__name, ircFilter(match.group(3))
                )
                nmsg = self.tr("{0} has left {1}: {2}.").format(
                    match.group(1), self.__name, match.group(3)
                )
                self.__addManagementMessage(IrcChannelWidget.LeaveIndicator, msg)
            if Preferences.getIrc("ShowNotifications") and Preferences.getIrc(
                "NotifyJoinPart"
            ):
                self.__ui.showNotification(
                    EricPixmapCache.getPixmap("irc48"), self.tr("Leave Channel"), nmsg
                )
            return True

        return False

    def __userQuit(self, match):
        """
        Private method to handle a user logging off the server.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        itm = self.__findUser(match.group(1))
        if itm:
            self.usersList.takeItem(self.usersList.row(itm))
            del itm
            if match.lastindex == 1:
                msg = self.tr("{0} has quit {1}.").format(match.group(1), self.__name)
                self.__addManagementMessage(IrcChannelWidget.MessageIndicator, msg)
            else:
                msg = self.tr("{0} has quit {1}: {2}.").format(
                    match.group(1), self.__name, ircFilter(match.group(2))
                )
                self.__addManagementMessage(IrcChannelWidget.MessageIndicator, msg)
            if Preferences.getIrc("ShowNotifications") and Preferences.getIrc(
                "NotifyJoinPart"
            ):
                self.__ui.showNotification(
                    EricPixmapCache.getPixmap("irc48"), self.tr("Quit"), msg
                )

        # always return False for other channels and server to process
        return False

    def __userNickChange(self, match):
        """
        Private method to handle a nickname change of a user.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        itm = self.__findUser(match.group(1))
        if itm:
            itm.setName(match.group(2))
            if match.group(1) == self.__userName:
                self.__addManagementMessage(
                    IrcChannelWidget.MessageIndicator,
                    self.tr("You are now known as {0}.").format(match.group(2)),
                )
                self.__userName = match.group(2)
            else:
                self.__addManagementMessage(
                    IrcChannelWidget.MessageIndicator,
                    self.tr("User {0} is now known as {1}.").format(
                        match.group(1), match.group(2)
                    ),
                )

        # always return False for other channels and server to process
        return False

    def __userList(self, match):
        """
        Private method to handle the receipt of a list of users of the channel.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            users = match.group(2).split()
            for user in users:
                userPrivileges, userName = self.__extractPrivilege(user)
                itm = self.__findUser(userName)
                if itm is None:
                    itm = IrcUserItem(userName, self.usersList)
                for privilege in userPrivileges:
                    itm.changePrivilege(privilege)

            self.__setEditTopicButton()
            return True

        return False

    def __userAway(self, match):
        """
        Private method to handle a topic change of the channel.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            self.__addManagementMessage(
                self.tr("Away"),
                self.tr("{0} is away: {1}").format(match.group(2), match.group(3)),
            )
            return True

        return False

    def __setTopic(self, match):
        """
        Private method to handle a topic change of the channel.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            self.topicLabel.setText(match.group(2))
            self.__addManagementMessage(
                IrcChannelWidget.MessageIndicator,
                ircFilter(
                    self.tr('The channel topic is: "{0}".').format(match.group(2))
                ),
            )
            return True

        return False

    def __topicCreated(self, match):
        """
        Private method to handle a topic created message.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            self.__addManagementMessage(
                IrcChannelWidget.MessageIndicator,
                self.tr("The topic was set by {0} on {1}.").format(
                    match.group(2),
                    QDateTime.fromSecsSinceEpoch(int(match.group(3))).toString(
                        "yyyy-MM-dd hh:mm"
                    ),
                ),
            )
            return True

        return False

    def __channelUrl(self, match):
        """
        Private method to handle a channel URL message.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            self.__addManagementMessage(
                IrcChannelWidget.MessageIndicator,
                ircFilter(self.tr("Channel URL: {0}").format(match.group(2))),
            )
            return True

        return False

    def __channelModes(self, match):
        """
        Private method to handle a message reporting the channel modes.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            modesDict = getChannelModesDict()
            modesParameters = match.group(2).split()
            modeString = modesParameters.pop(0)
            modes = []
            for modeChar in modeString:
                if modeChar == "+":
                    continue
                elif modeChar == "k":
                    parameter = modesParameters.pop(0)
                    modes.append(self.tr("password protected ({0})").format(parameter))
                elif modeChar == "l":
                    parameter = modesParameters.pop(0)
                    modes.append(self.tr("limited to %n user(s)", "", int(parameter)))
                elif modeChar in modesDict:
                    modes.append(modesDict[modeChar])
                else:
                    modes.append(modeChar)

            self.__addManagementMessage(
                IrcChannelWidget.MessageIndicator,
                self.tr("Channel modes: {0}.").format(", ".join(modes)),
            )

            return True

        return False

    def __channelCreated(self, match):
        """
        Private method to handle a channel created message.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            self.__addManagementMessage(
                IrcChannelWidget.MessageIndicator,
                self.tr("This channel was created on {0}.").format(
                    QDateTime.fromSecsSinceEpoch(int(match.group(2))).toString(
                        "yyyy-MM-dd hh:mm"
                    )
                ),
            )
            return True

        return False

    def __updateChannelModes(self, match):
        """
        Private method to handle a message reporting the channel modes.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)  user or server
        # group(2)  channel
        # group(3)  modes and parameter list
        if match.group(2).lower() == self.__name.lower():
            nick = match.group(1)
            modesParameters = match.group(3).split()
            modeString = modesParameters.pop(0)
            isPlus = True
            message = ""
            for mode in modeString:
                if mode == "+":
                    isPlus = True
                    continue
                elif mode == "-":
                    isPlus = False
                    continue
                elif mode == "a":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel mode to 'anonymous'."
                        ).format(nick)
                    else:
                        message = self.tr(
                            "{0} removes the 'anonymous' mode from the channel."
                        ).format(nick)
                elif mode == "b":
                    if isPlus:
                        message = self.tr("{0} sets a ban on {1}.").format(
                            nick, modesParameters.pop(0)
                        )
                    else:
                        message = self.tr("{0} removes the ban on {1}.").format(
                            nick, modesParameters.pop(0)
                        )
                elif mode == "c":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel mode to 'no colors allowed'."
                        ).format(nick)
                    else:
                        message = self.tr(
                            "{0} sets the channel mode to 'allow color codes'."
                        ).format(nick)
                elif mode == "e":
                    if isPlus:
                        message = self.tr("{0} sets a ban exception on {1}.").format(
                            nick, modesParameters.pop(0)
                        )
                    else:
                        message = self.tr(
                            "{0} removes the ban exception on {1}."
                        ).format(nick, modesParameters.pop(0))
                elif mode == "i":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel mode to 'invite only'."
                        ).format(nick)
                    else:
                        message = self.tr(
                            "{0} removes the 'invite only' mode from the channel."
                        ).format(nick)
                elif mode == "k":
                    if isPlus:
                        message = self.tr("{0} sets the channel key to '{1}'.").format(
                            nick, modesParameters.pop(0)
                        )
                    else:
                        message = self.tr("{0} removes the channel key.").format(nick)
                elif mode == "l":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel limit to %n nick(s).",
                            "",
                            int(modesParameters.pop(0)),
                        ).format(nick)
                    else:
                        message = self.tr("{0} removes the channel limit.").format(nick)
                elif mode == "m":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel mode to 'moderated'."
                        ).format(nick)
                    else:
                        message = self.tr(
                            "{0} sets the channel mode to 'unmoderated'."
                        ).format(nick)
                elif mode == "n":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel mode to 'no messages from"
                            " outside'."
                        ).format(nick)
                    else:
                        message = self.tr(
                            "{0} sets the channel mode to 'allow messages"
                            " from outside'."
                        ).format(nick)
                elif mode == "p":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel mode to 'private'."
                        ).format(nick)
                    else:
                        message = self.tr(
                            "{0} sets the channel mode to 'public'."
                        ).format(nick)
                elif mode == "q":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel mode to 'quiet'."
                        ).format(nick)
                    else:
                        message = self.tr(
                            "{0} removes the 'quiet' mode from the channel."
                        ).format(nick)
                elif mode == "r":
                    continue
                elif mode == "s":
                    if isPlus:
                        message = self.tr(
                            "{0} sets the channel mode to 'secret'."
                        ).format(nick)
                    else:
                        message = self.tr(
                            "{0} sets the channel mode to 'visible'."
                        ).format(nick)
                elif mode == "t":
                    if isPlus:
                        message = self.tr("{0} switches on 'topic protection'.").format(
                            nick
                        )
                    else:
                        message = self.tr(
                            "{0} switches off 'topic protection'."
                        ).format(nick)
                elif mode == "I":
                    if isPlus:
                        message = self.tr("{0} sets invitation mask {1}.").format(
                            nick, modesParameters.pop(0)
                        )
                    else:
                        message = self.tr(
                            "{0} removes the invitation mask {1}."
                        ).format(nick, modesParameters.pop(0))

                self.__addManagementMessage(self.tr("Mode"), message)

            return True

        return False

    def __setUserPrivilege(self, match):
        """
        Private method to handle a change of user privileges for the channel.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(2).lower() == self.__name.lower():
            itm = self.__findUser(match.group(4))
            if itm:
                itm.changePrivilege(match.group(3))
                self.__setEditTopicButton()
            self.__addManagementMessage(
                IrcChannelWidget.MessageIndicator,
                self.tr("{0} sets mode for {1}: {2}.").format(
                    match.group(1), match.group(4), match.group(3)
                ),
            )
            return True

        return False

    def __ignore(self, match):
        """
        Private method to handle a channel message we are not interested in.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            return True

        return False

    def __help(self, match):
        """
        Private method to handle a help message.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        self.__addManagementMessage(
            self.tr("Help"), "{0} {1}".format(match.group(1), ircFilter(match.group(2)))
        )
        return True

    def __handleCtcp(self, match):
        """
        Private method to handle a CTCP channel command.

        @param match reference to the match object
        @type re.Match
        @return flag indicating, if the message was handled
        @rtype bool
        """
        # group(1)   sender user name
        # group(2)   sender user@host
        # group(3)   target nick
        # group(4)   message
        if match.group(4).startswith("\x01"):
            ctcpCommand = match.group(4)[1:].split("\x01", 1)[0]
            if " " in ctcpCommand:
                ctcpRequest, ctcpArg = ctcpCommand.split(" ", 1)
            else:
                ctcpRequest, ctcpArg = ctcpCommand, ""
            ctcpRequest = ctcpRequest.lower()
            if ctcpRequest == "version":
                msg = "Eric IRC client {0}, {1}".format(Version, Copyright)
                self.__addManagementMessage(
                    self.tr("CTCP"),
                    self.tr("Received Version request from {0}.").format(
                        match.group(1)
                    ),
                )
                self.sendCtcpReply.emit(match.group(1), "VERSION " + msg)
            elif ctcpRequest == "ping":
                self.__addManagementMessage(
                    self.tr("CTCP"),
                    self.tr(
                        "Received CTCP-PING request from {0}, sending answer."
                    ).format(match.group(1)),
                )
                self.sendCtcpReply.emit(match.group(1), "PING {0}".format(ctcpArg))
            elif ctcpRequest == "clientinfo":
                self.__addManagementMessage(
                    self.tr("CTCP"),
                    self.tr(
                        "Received CTCP-CLIENTINFO request from {0}, sending answer."
                    ).format(match.group(1)),
                )
                self.sendCtcpReply.emit(
                    match.group(1), "CLIENTINFO CLIENTINFO PING VERSION"
                )
            else:
                self.__addManagementMessage(
                    self.tr("CTCP"),
                    self.tr("Received unknown CTCP-{0} request from {1}.").format(
                        ctcpRequest, match.group(1)
                    ),
                )
            return True

        return False

    def setUserPrivilegePrefix(self, prefixes):
        """
        Public method to set the user privilege to prefix mapping.

        @param prefixes dictionary with privilege as key and prefix as value
        @type dict
        """
        self.__prefixToPrivilege = {}
        for privilege, prefix in prefixes.items():
            if prefix:
                self.__prefixToPrivilege[prefix] = privilege

    def __findUser(self, name):
        """
        Private method to find the user in the list of users.

        @param name user name to search for
        @type str
        @return reference to the list entry
        @rtype QListWidgetItem
        """
        for row in range(self.usersList.count()):
            itm = self.usersList.item(row)
            if itm.name() == name:
                return itm

        return None

    def __extractPrivilege(self, name):
        """
        Private method to extract the user privileges out of the name.

        @param name user name and prefixes
        @type str
        @return tuple containing a list of privileges and user name
        @rtype tuple of (list of str, str)
        """
        privileges = []
        while name[0] in self.__prefixToPrivilege:
            prefix = name[0]
            privileges.append(self.__prefixToPrivilege[prefix])
            name = name[1:]
            if name[0] == ",":
                name = name[1:]

        return privileges, name

    def __addManagementMessage(self, indicator, message):
        """
        Private method to add a channel management message to the list.

        @param indicator indicator to be shown
        @type str
        @param message message to be shown
        @type str
        """
        if indicator == self.JoinIndicator:
            color = Preferences.getIrc("JoinChannelColour")
        elif indicator == self.LeaveIndicator:
            color = Preferences.getIrc("LeaveChannelColour")
        else:
            color = Preferences.getIrc("ChannelInfoColour")
        self.__appendMessage(
            '<font color="{0}">{1} <b>[</b>{2}<b>]</b> {3}</font>'.format(
                color, ircTimestamp(), indicator, message
            )
        )

    def __appendMessage(self, message):
        """
        Private slot to append a message.

        @param message message to be appended
        @type str
        """
        if (
            self.__hidden
            and self.__markerLine == ""
            and Preferences.getIrc("MarkPositionWhenHidden")
        ):
            self.setMarkerLine()
        self.messages.append(message)

    def setMarkerLine(self):
        """
        Public method to draw a line to mark the current position.
        """
        self.unsetMarkerLine()
        self.__markerLine = (
            '<span style=" color:{0}; background-color:{1};">{2}</span>'.format(
                Preferences.getIrc("MarkerLineForegroundColour"),
                Preferences.getIrc("MarkerLineBackgroundColour"),
                self.tr("--- New From Here ---"),
            )
        )
        self.messages.append(self.__markerLine)

    def unsetMarkerLine(self):
        """
        Public method to remove the marker line.
        """
        if self.__markerLine:
            txt = self.messages.toHtml()
            if txt.endswith(self.__markerLine + "</p></body></html>"):
                # remove empty last paragraph
                pos = txt.rfind("<p")
                txt = txt[:pos] + "</body></html>"
            else:
                txt = txt.replace(self.__markerLine, "")
            self.messages.setHtml(txt)
            self.__markerLine = ""
            self.messages.moveCursor(QTextCursor.MoveOperation.End)

    def __clearMessages(self):
        """
        Private slot to clear the contents of the messages display.
        """
        self.messages.clear()

    def __copyMessages(self):
        """
        Private slot to copy the selection of the messages display to the
        clipboard.
        """
        self.messages.copy()

    def __copyAllMessages(self):
        """
        Private slot to copy the contents of the messages display to the
        clipboard.
        """
        txt = self.messages.toPlainText()
        if txt:
            cb = QApplication.clipboard()
            cb.setText(txt)

    def __cutAllMessages(self):
        """
        Private slot to cut the contents of the messages display to the
        clipboard.
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
        self.__messagesMenu.addSeparator()
        self.__setMarkerMessagesAct = self.__messagesMenu.addAction(
            self.tr("Mark Current Position"), self.setMarkerLine
        )
        self.__unsetMarkerMessagesAct = self.__messagesMenu.addAction(
            self.tr("Remove Position Marker"), self.unsetMarkerLine
        )

        self.on_messages_copyAvailable(False)

    @pyqtSlot(bool)
    def on_messages_copyAvailable(self, yes):
        """
        Private slot to react to text selection/deselection of the messages
        edit.

        @param yes flag signaling the availability of selected text
        @type bool
        """
        self.__copyMessagesAct.setEnabled(yes)

    @pyqtSlot(QPoint)
    def on_messages_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu of the messages pane.

        @param pos the position of the mouse pointer
        @type QPoint
        """
        enable = not self.messages.document().isEmpty()
        self.__cutAllMessagesAct.setEnabled(enable)
        self.__copyAllMessagesAct.setEnabled(enable)
        self.__saveMessagesAct.setEnabled(enable)
        self.__setMarkerMessagesAct.setEnabled(self.__markerLine == "")
        self.__unsetMarkerMessagesAct.setEnabled(self.__markerLine != "")
        self.__messagesMenu.popup(self.messages.mapToGlobal(pos))

    def __whoIs(self):
        """
        Private slot to get information about the selected user.
        """
        self.__whoIsNick = self.usersList.selectedItems()[0].text()
        self.sendData.emit("WHOIS " + self.__whoIsNick)

    def __openPrivateChat(self):
        """
        Private slot to open a chat with the selected user.
        """
        user = self.usersList.selectedItems()[0].text()
        self.openPrivateChat.emit(user)

    def __sendUserMessage(self):
        """
        Private slot to send a private message to a specific user.
        """
        from eric7.EricWidgets import EricTextInputDialog

        user = self.usersList.selectedItems()[0].text()
        ok, message = EricTextInputDialog.getText(
            self,
            self.tr("Send Message"),
            self.tr("Enter the message to be sent:"),
            minimumWidth=400,
        )
        if ok and message:
            self.__processUserMessage("/MSG {0} {1}".format(user, message))

    def __sendUserQuery(self):
        """
        Private slot to send a query message to a specific user.
        """
        from eric7.EricWidgets import EricTextInputDialog

        user = self.usersList.selectedItems()[0].text()
        ok, message = EricTextInputDialog.getText(
            self,
            self.tr("Send Query"),
            self.tr("Enter the message to be sent:"),
            minimumWidth=400,
        )
        if ok and message:
            self.__processUserMessage("/QUERY {0} {1}".format(user, message))

    def __sendUserNotice(self):
        """
        Private slot to send a notice message to a specific user.
        """
        from eric7.EricWidgets import EricTextInputDialog

        user = self.usersList.selectedItems()[0].text()
        ok, message = EricTextInputDialog.getText(
            self,
            self.tr("Send Notice"),
            self.tr("Enter the message to be sent:"),
            minimumWidth=400,
        )
        if ok and message:
            self.__processUserMessage("/NOTICE {0} {1}".format(user, message))

    def __pingUser(self):
        """
        Private slot to send a ping to a specific user.
        """
        user = self.usersList.selectedItems()[0].text()
        self.__processUserMessage("/PING {0}".format(user))

    def __ignoreUser(self):
        """
        Private slot to ignore a specific user.
        """
        user = self.usersList.selectedItems()[0].text()
        self.__processUserMessage("/IGNORE {0}".format(user))

    def __initUsersMenu(self):
        """
        Private slot to initialize the users list context menu.
        """
        self.__usersMenu = QMenu(self)
        self.__whoIsAct = self.__usersMenu.addAction(self.tr("Who Is"), self.__whoIs)
        self.__usersMenu.addSeparator()
        self.__privateChatAct = self.__usersMenu.addAction(
            self.tr("Private Chat"), self.__openPrivateChat
        )
        self.__usersMenu.addSeparator()
        self.__sendUserMessageAct = self.__usersMenu.addAction(
            self.tr("Send Message"), self.__sendUserMessage
        )
        self.__sendUserQueryAct = self.__usersMenu.addAction(
            self.tr("Send Query"), self.__sendUserQuery
        )
        self.__sendUserNoticeAct = self.__usersMenu.addAction(
            self.tr("Send Notice"), self.__sendUserNotice
        )
        self.__usersMenu.addSeparator()
        self.__pingUserAct = self.__usersMenu.addAction(
            self.tr("Send Ping"), self.__pingUser
        )
        self.__ignoreUserAct = self.__usersMenu.addAction(
            self.tr("Ignore User"), self.__ignoreUser
        )
        self.__usersMenu.addSeparator()
        self.__usersListRefreshAct = self.__usersMenu.addAction(
            self.tr("Refresh"), self.__sendAutoWhoCommand
        )

    @pyqtSlot(QPoint)
    def on_usersList_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu of the users list.

        @param pos the position of the mouse pointer
        @type QPoint
        """
        enable = len(self.usersList.selectedItems()) > 0
        enablePrivate = enable and not self.__private
        itm = self.usersList.itemAt(pos)
        if itm and enablePrivate:
            enablePrivate = itm.text().lower() not in [
                "chanserv",
                self.__userName.lower(),
            ]
        self.__whoIsAct.setEnabled(enable)
        self.__privateChatAct.setEnabled(enablePrivate)
        self.__usersListRefreshAct.setEnabled(
            self.usersList.count() <= Preferences.getIrc("AutoUserInfoMax")
        )
        self.__usersMenu.popup(self.usersList.mapToGlobal(pos))

    def hideEvent(self, _evt):
        """
        Protected method handling hide events.

        @param _evt reference to the hide event (unused)
        @type QHideEvent
        """
        self.__hidden = True

    def showEvent(self, _evt):
        """
        Protected method handling show events.

        @param _evt reference to the show event (unused)
        @type QShowEvent
        """
        self.__hidden = False

    def initAutoWho(self):
        """
        Public method to initialize the Auto Who system.
        """
        if Preferences.getIrc("AutoUserInfoLookup"):
            self.__autoWhoTimer.setInterval(
                Preferences.getIrc("AutoUserInfoInterval") * 1000
            )
            self.__autoWhoTimer.start()

    @pyqtSlot()
    def __sendAutoWhoCommand(self):
        """
        Private slot to send the WHO command to update the users list.
        """
        if self.usersList.count() <= Preferences.getIrc("AutoUserInfoMax"):
            self.__autoWhoRequested = True
            self.sendData.emit(self.__autoWhoTemplate.format(self.__name))

    def __autoWhoEntry(self, match):
        """
        Private method to handle a WHO entry returned by the server as
        requested automatically.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)  nick
        # group(2)  user flags
        if self.__autoWhoRequested:
            itm = self.__findUser(match.group(1))
            if itm:
                itm.parseWhoFlags(match.group(2))
            return True

        return False

    def __whoEnd(self, match):
        """
        Private method to handle the end of the WHO list.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        if match.group(1).lower() == self.__name.lower():
            if self.__autoWhoRequested:
                self.__autoWhoRequested = False
                self.initAutoWho()
            else:
                self.__addManagementMessage(
                    self.tr("Who"),
                    self.tr("End of WHO list for {0}.").format(match.group(1)),
                )
            return True

        return False

    def __whoEntry(self, match):
        """
        Private method to handle a WHO entry returned by the server as
        requested manually.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)  channel
        # group(2)  user
        # group(3)  host
        # group(4)  nick
        # group(5)  user flags
        # group(6)  real name
        if match.group(1).lower() == self.__name.lower():
            away = self.tr(" (Away)") if match.group(5).startswith("G") else ""
            self.__addManagementMessage(
                self.tr("Who"),
                self.tr("{0} is {1}@{2} ({3}){4}").format(
                    match.group(4), match.group(2), match.group(3), match.group(6), away
                ),
            )
            return True

        return False

    def __whoIsUser(self, match):
        """
        Private method to handle the WHOIS user reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   user
        # group(3)   host
        # group(4)   real name
        if match.group(1) == self.__whoIsNick:
            realName = match.group(4).replace("<", "&lt;").replace(">", "&gt;")
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("{0} is {1}@{2} ({3}).").format(
                    match.group(1), match.group(2), match.group(3), realName
                ),
            )
            return True

        return False

    def __whoIsChannels(self, match):
        """
        Private method to handle the WHOIS channels reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   channels
        if match.group(1) == self.__whoIsNick:
            userChannels = []
            voiceChannels = []
            opChannels = []
            halfopChannels = []
            ownerChannels = []
            adminChannels = []

            # generate the list of channels the user is in
            channelList = match.group(2).split()
            for channel in channelList:
                if channel.startswith(("*", "&")):
                    adminChannels.append(channel[1:])
                elif channel.startswith(("!", "~")) and self.__ircWidget.isChannelName(
                    channel[1:]
                ):
                    ownerChannels.append(channel[1:])
                elif channel.startswith("@+"):
                    opChannels.append(channel[2:])
                elif channel.startswith("@"):
                    opChannels.append(channel[1:])
                elif channel.startswith("%"):
                    halfopChannels.append(channel[1:])
                elif channel.startswith("+"):
                    voiceChannels.append(channel[1:])
                else:
                    userChannels.append(channel)

            # show messages
            if userChannels:
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} is a user on channels: {1}").format(
                        match.group(1), " ".join(userChannels)
                    ),
                )
            if voiceChannels:
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} has voice on channels: {1}").format(
                        match.group(1), " ".join(voiceChannels)
                    ),
                )
            if halfopChannels:
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} is a halfop on channels: {1}").format(
                        match.group(1), " ".join(halfopChannels)
                    ),
                )
            if opChannels:
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} is an operator on channels: {1}").format(
                        match.group(1), " ".join(opChannels)
                    ),
                )
            if ownerChannels:
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} is owner of channels: {1}").format(
                        match.group(1), " ".join(ownerChannels)
                    ),
                )
            if adminChannels:
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} is admin on channels: {1}").format(
                        match.group(1), " ".join(adminChannels)
                    ),
                )
            return True

        return False

    def __whoIsServer(self, match):
        """
        Private method to handle the WHOIS server reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   server
        # group(3)   server info
        if match.group(1) == self.__whoIsNick:
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("{0} is online via {1} ({2}).").format(
                    match.group(1), match.group(2), match.group(3)
                ),
            )
            return True

        return False

    def __whoIsOperator(self, match):
        """
        Private method to handle the WHOIS operator reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   message
        if match.group(1) == self.__whoIsNick:
            if match.group(2).lower().startswith("is an irc operator"):
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} is an IRC Operator.").format(match.group(1)),
                )
            else:
                self.__addManagementMessage(
                    self.tr("Whois"), "{0} {1}".format(match.group(1), match.group(2))
                )
            return True

        return False

    def __whoIsIdle(self, match):
        """
        Private method to handle the WHOIS idle reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   idle seconds
        # group(3)   signon time
        if match.group(1) == self.__whoIsNick:
            seconds = int(match.group(2))
            minutes = seconds // 60
            hours = minutes // 60
            days = hours // 24

            signonTimestamp = int(match.group(3))
            signonTime = QDateTime()
            signonTime.setTime_t(signonTimestamp)

            if days:
                daysString = self.tr("%n day(s)", "", days)
                hoursString = self.tr("%n hour(s)", "", hours)
                minutesString = self.tr("%n minute(s)", "", minutes)
                secondsString = self.tr("%n second(s)", "", seconds)
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr(
                        "{0} has been idle for {1}, {2}, {3}, and {4}.",
                        "{0} = name of person, {1} = (x days),"
                        " {2} = (x hours), {3} = (x minutes),"
                        " {4} = (x seconds)",
                    ).format(
                        match.group(1),
                        daysString,
                        hoursString,
                        minutesString,
                        secondsString,
                    ),
                )
            elif hours:
                hoursString = self.tr("%n hour(s)", "", hours)
                minutesString = self.tr("%n minute(s)", "", minutes)
                secondsString = self.tr("%n second(s)", "", seconds)
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr(
                        "{0} has been idle for {1}, {2}, and {3}.",
                        "{0} = name of person, {1} = (x hours), "
                        "{2} = (x minutes), {3} = (x seconds)",
                    ).format(match.group(1), hoursString, minutesString, secondsString),
                )
            elif minutes:
                minutesString = self.tr("%n minute(s)", "", minutes)
                secondsString = self.tr("%n second(s)", "", seconds)
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr(
                        "{0} has been idle for {1} and {2}.",
                        "{0} = name of person, {1} = (x minutes), {3} = (x seconds)",
                    ).format(match.group(1), minutesString, secondsString),
                )
            else:
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} has been idle for %n second(s).", "", seconds).format(
                        match.group(1)
                    ),
                )

            if not signonTime.isNull():
                self.__addManagementMessage(
                    self.tr("Whois"),
                    self.tr("{0} has been online since {1}.").format(
                        match.group(1), signonTime.toString("yyyy-MM-dd, hh:mm:ss")
                    ),
                )
            return True

        return False

    def __whoIsEnd(self, match):
        """
        Private method to handle the end of WHOIS reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   end message
        if match.group(1) == self.__whoIsNick:
            self.__whoIsNick = ""
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("End of WHOIS list for {0}.").format(match.group(1)),
            )
            return True

        return False

    def __whoIsIdentify(self, match):
        """
        Private method to handle the WHOIS identify and identified replies.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   identified message
        if match.group(1) == self.__whoIsNick:
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("{0} is an identified user.").format(match.group(1)),
            )
            return True

        return False

    def __whoIsHelper(self, match):
        """
        Private method to handle the WHOIS helper reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   helper message
        if match.group(1) == self.__whoIsNick:
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("{0} is available for help.").format(match.group(1)),
            )
            return True

        return False

    def __whoIsAccount(self, match):
        """
        Private method to handle the WHOIS account reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   login name
        if match.group(1) == self.__whoIsNick:
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("{0} is logged in as {1}.").format(
                    match.group(1), match.group(2)
                ),
            )
            return True

        return False

    def __whoIsActually(self, match):
        """
        Private method to handle the WHOIS actually reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   actual user@host
        # group(3)   actual IP
        if match.group(1) == self.__whoIsNick:
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("{0} is actually using the host {1} (IP: {2}).").format(
                    match.group(1), match.group(2), match.group(3)
                ),
            )
            return True

        return False

    def __whoIsSecure(self, match):
        """
        Private method to handle the WHOIS secure reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        if match.group(1) == self.__whoIsNick:
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("{0} is using a secure connection.").format(match.group(1)),
            )
            return True

        return False

    def __whoIsConnection(self, match):
        """
        Private method to handle the WHOIS connection reply.

        @param match match object that matched the pattern
        @type re.Match
        @return flag indicating whether the message was handled
        @rtype bool
        """
        # group(1)   nick
        # group(2)   host name
        # group(3)   IP
        if match.group(1) == self.__whoIsNick:
            self.__addManagementMessage(
                self.tr("Whois"),
                self.tr("{0} is connecting from {1} (IP: {2}).").format(
                    match.group(1), match.group(2), match.group(3)
                ),
            )
            return True

        return False

    def __setEditTopicButton(self):
        """
        Private method to set the visibility of the Edit Topic button.
        """
        itm = self.__findUser(self.__userName)
        if itm:
            self.editTopicButton.setVisible(itm.canChangeTopic())

    @pyqtSlot()
    def on_editTopicButton_clicked(self):
        """
        Private slot to change the topic of the channel.
        """
        topic, ok = QInputDialog.getText(
            self,
            self.tr("Edit Channel Topic"),
            self.tr("Enter the topic for this channel:"),
            QLineEdit.EchoMode.Normal,
            self.topicLabel.text(),
        )
        if ok and topic != "":
            self.sendData.emit("TOPIC {0} :{1}".format(self.__name, topic))

    @pyqtSlot(QUrl)
    def on_messages_anchorClicked(self, url):
        """
        Private slot to open links in the default browser.

        @param url URL to be opened
        @type QUrl
        """
        QDesktopServices.openUrl(url)
