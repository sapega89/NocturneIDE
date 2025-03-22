# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to send bug reports or feature requests.
"""

import contextlib
import mimetypes
import os
import smtplib

from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextOption
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QTreeWidgetItem,
)

from eric7 import Preferences, Utilities
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricSimpleHelpDialog import EricSimpleHelpDialog

from .Info import BugAddress, FeatureAddress
from .Ui_EmailDialog import Ui_EmailDialog

############################################################
## This code is to work around a bug in the Python email  ##
## package for Image and Audio mime messages.             ##
############################################################


class EmailDialog(QDialog, Ui_EmailDialog):
    """
    Class implementing a dialog to send bug reports or feature requests.
    """

    def __init__(self, mode="bug", parent=None):
        """
        Constructor

        @param mode mode of this dialog ("bug" or "feature")
        @type str
        @param parent parent widget of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.message.setWordWrapMode(QTextOption.WrapMode.WordWrap)

        self.__mode = mode
        if self.__mode == "feature":
            self.setWindowTitle(self.tr("Send feature request"))
            self.msgLabel.setText(
                self.tr(
                    "Enter your &feature request below."
                    " Version information is added automatically."
                )
            )
            self.__toAddress = FeatureAddress
        else:
            # default is bug
            self.msgLabel.setText(
                self.tr(
                    "Enter your &bug description below."
                    " Version information is added automatically."
                )
            )
            self.__toAddress = BugAddress

        self.sendButton = self.buttonBox.addButton(
            self.tr("Send"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.sendButton.setEnabled(False)
        self.sendButton.setDefault(True)

        self.googleHelpButton = self.buttonBox.addButton(
            self.tr("Google Mail API Help"), QDialogButtonBox.ButtonRole.HelpRole
        )

        height = self.height()
        self.mainSplitter.setSizes([int(0.7 * height), int(0.3 * height)])

        self.attachments.headerItem().setText(self.attachments.columnCount(), "")
        self.attachments.header().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )

        sig = Preferences.getUser("Signature")
        if sig:
            self.message.setPlainText(sig)
            cursor = self.message.textCursor()
            cursor.setPosition(0)
            self.message.setTextCursor(cursor)
            self.message.ensureCursorVisible()

        self.__deleteFiles = []

        self.__helpDialog = None
        self.__googleMail = None

    def keyPressEvent(self, ev):
        """
        Protected method to handle the user pressing the escape key.

        @param ev key event
        @type QKeyEvent
        """
        if ev.key() == Qt.Key.Key_Escape:
            res = EricMessageBox.yesNo(
                self,
                self.tr("Close dialog"),
                self.tr("""Do you really want to close the dialog?"""),
            )
            if res:
                self.reject()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.sendButton:
            self.on_sendButton_clicked()
        elif button == self.googleHelpButton:
            self.on_googleHelpButton_clicked()

    def on_buttonBox_rejected(self):
        """
        Private slot to handle the rejected signal of the button box.
        """
        res = EricMessageBox.yesNo(
            self,
            self.tr("Close dialog"),
            self.tr("""Do you really want to close the dialog?"""),
        )
        if res:
            self.reject()

    @pyqtSlot()
    def on_googleHelpButton_clicked(self):
        """
        Private slot to show some help text "how to turn on the Gmail API".
        """
        if self.__helpDialog is None:
            try:
                from eric7.EricNetwork.EricGoogleMail import (  # noqa: I101
                    GoogleMailHelp,
                )

                helpStr = GoogleMailHelp()
            except ImportError:
                helpStr = self.tr(
                    "<p>The Google Mail Client API is not installed."
                    " Change to the Email configuration page for more.</p>"
                )

            self.__helpDialog = EricSimpleHelpDialog(
                title=self.tr("Gmail API Help"), helpStr=helpStr, parent=self
            )

        self.__helpDialog.show()

    @pyqtSlot()
    def on_sendButton_clicked(self):
        """
        Private slot to send the email message.
        """
        msg = (
            self.__createMultipartMail()
            if self.attachments.topLevelItemCount()
            else self.__createSimpleMail()
        )

        if Preferences.getUser("UseGoogleMailOAuth2"):
            self.__sendmailGoogle(msg)
        else:
            ok = self.__sendmail(msg.as_string())
            if ok:
                self.__deleteAttachedFiles()
                self.accept()

    def __deleteAttachedFiles(self):
        """
        Private method to delete attached files.
        """
        for f in self.__deleteFiles:
            with contextlib.suppress(OSError):
                os.remove(f)

    def __encodedText(self, txt):
        """
        Private method to create a MIMEText message with correct encoding.

        @param txt text to be put into the MIMEText object
        @type str
        @return MIMEText object
        @rtype email.mime.text.MIMEText
        """
        try:
            txt.encode("us-ascii")
            return MIMEText(txt)
        except UnicodeEncodeError:
            coding = Preferences.getSystem("StringEncoding")
            return MIMEText(txt.encode(coding), _charset=coding)

    def __encodedHeader(self, txt):
        """
        Private method to create a correctly encoded mail header.

        @param txt header text to encode
        @type str
        @return encoded header
        @rtype email.header.Header
        """
        try:
            txt.encode("us-ascii")
            return Header(txt)
        except UnicodeEncodeError:
            coding = Preferences.getSystem("StringEncoding")
            return Header(txt, coding)

    def __createSimpleMail(self):
        """
        Private method to create a simple mail message.

        @return prepared mail message
        @rtype email.mime.text.MIMEText
        """
        msgtext = "{0}\r\n----\r\n{1}\r\n----\r\n{2}\r\n----\r\n{3}".format(
            self.message.toPlainText(),
            Utilities.generateVersionInfo("\r\n"),
            Utilities.generatePluginsVersionInfo("\r\n"),
            Utilities.generateDistroInfo("\r\n"),
        )

        msg = self.__encodedText(msgtext)
        msg["From"] = Preferences.getUser("Email")
        msg["To"] = self.__toAddress
        subject = "[eric7] {0}".format(self.subject.text())
        msg["Subject"] = self.__encodedHeader(subject)

        return msg

    def __createMultipartMail(self):
        """
        Private method to create a multipart mail message.

        @return prepared mail message
        @rtype email.mime.text.MIMEMultipart
        """
        mpPreamble = (
            "This is a MIME-encoded message with attachments. "
            "If you see this message, your mail client is not "
            "capable of displaying the attachments."
        )

        msgtext = "{0}\r\n----\r\n{1}\r\n----\r\n{2}\r\n----\r\n{3}".format(
            self.message.toPlainText(),
            Utilities.generateVersionInfo("\r\n"),
            Utilities.generatePluginsVersionInfo("\r\n"),
            Utilities.generateDistroInfo("\r\n"),
        )

        # first part of multipart mail explains format
        msg = MIMEMultipart()
        msg["From"] = Preferences.getUser("Email")
        msg["To"] = self.__toAddress
        subject = "[eric7] {0}".format(self.subject.text())
        msg["Subject"] = self.__encodedHeader(subject)
        msg.preamble = mpPreamble
        msg.epilogue = ""

        # second part is intended to be read
        att = self.__encodedText(msgtext)
        msg.attach(att)

        # next parts contain the attachments
        for index in range(self.attachments.topLevelItemCount()):
            itm = self.attachments.topLevelItem(index)
            maintype, subtype = itm.text(1).split("/", 1)
            fname = itm.text(0)
            name = os.path.basename(fname)

            if maintype == "text":
                with open(fname, "r", encoding="utf-8") as f:
                    txt = f.read()
                try:
                    txt.encode("us-ascii")
                    att = MIMEText(txt, _subtype=subtype)
                except UnicodeEncodeError:
                    att = MIMEText(
                        txt.encode("utf-8"), _subtype=subtype, _charset="utf-8"
                    )
            elif maintype == "image":
                with open(fname, "rb") as f:
                    att = MIMEImage(f.read(), _subtype=subtype)
            elif maintype == "audio":
                with open(fname, "rb") as f:
                    att = MIMEAudio(f.read(), _subtype=subtype)
            else:
                with open(fname, "rb") as f:
                    att = MIMEApplication(f.read())
            att.add_header("Content-Disposition", "attachment", filename=name)
            msg.attach(att)

        return msg

    def __sendmail(self, msg):
        """
        Private method to actually send the message.

        @param msg the message to be sent
        @type str
        @return flag indicating success
        @rtype bool
        """
        try:
            encryption = Preferences.getUser("MailServerEncryption")
            if encryption == "SSL":
                server = smtplib.SMTP_SSL(
                    Preferences.getUser("MailServer"),
                    Preferences.getUser("MailServerPort"),
                )
            else:
                server = smtplib.SMTP(
                    Preferences.getUser("MailServer"),
                    Preferences.getUser("MailServerPort"),
                )
                if encryption == "TLS":
                    server.starttls()
            if Preferences.getUser("MailServerAuthentication"):
                # mail server needs authentication
                password = Preferences.getUser("MailServerPassword")
                if not password:
                    password, ok = QInputDialog.getText(
                        self,
                        self.tr("Mail Server Password"),
                        self.tr("Enter your mail server password"),
                        QLineEdit.EchoMode.Password,
                    )
                    if not ok:
                        # abort
                        return False
                try:
                    server.login(Preferences.getUser("MailServerUser"), password)
                except (OSError, smtplib.SMTPException) as e:
                    if isinstance(e, smtplib.SMTPResponseException):
                        errorStr = e.smtp_error.decode()
                    elif isinstance(e, OSError):
                        errorStr = e.strerror
                    elif isinstance(e, OSError):
                        errorStr = e[1]
                    else:
                        errorStr = str(e)
                    res = EricMessageBox.retryAbort(
                        self,
                        self.tr("Send Message"),
                        self.tr(
                            """<p>Authentication failed.<br>Reason: {0}</p>"""
                        ).format(errorStr),
                        EricMessageBox.Critical,
                    )
                    if res:
                        return self.__sendmail(msg)
                    else:
                        return False

            with EricOverrideCursor():
                server.sendmail(Preferences.getUser("Email"), self.__toAddress, msg)
                server.quit()
        except (OSError, smtplib.SMTPException) as e:
            if isinstance(e, smtplib.SMTPResponseException):
                errorStr = e.smtp_error.decode()
            elif isinstance(e, smtplib.SMTPException):
                errorStr = str(e)
            elif isinstance(e, OSError):
                errorStr = e.strerror
            else:
                errorStr = str(e)
            res = EricMessageBox.retryAbort(
                self,
                self.tr("Send Message"),
                self.tr("""<p>Message could not be sent.<br>Reason: {0}</p>""").format(
                    errorStr
                ),
                EricMessageBox.Critical,
            )
            if res:
                return self.__sendmail(msg)
            else:
                return False
        return True

    def __sendmailGoogle(self, msg):
        """
        Private method to actually send the message via Google Mail.

        @param msg email message to be sent
        @type email.mime.text.MIMEBase
        """
        try:
            from eric7.EricNetwork.EricGoogleMail import (  # __IGNORE_WARNING_I101__
                EricGoogleMail,
            )

            if self.__googleMail is None:
                self.__googleMail = EricGoogleMail(self)
                self.__googleMail.sendResult.connect(self.__gmailSendResult)

            self.__googleMail.sendMessage(msg)
        except ImportError:
            EricMessageBox.critical(
                self,
                self.tr("Send Message"),
                self.tr(
                    "The Google Mail Client API is not installed. The message cannot be"
                    " sent."
                ),
            )

    @pyqtSlot(bool, str)
    def __gmailSendResult(self, ok, message):
        """
        Private slot handling the send result reported by the Google Mail
        interface.

        @param ok flag indicating success
        @type bool
        @param message message from the interface
        @type str
        """
        if ok:
            self.__deleteAttachedFiles()
            self.accept()
        else:
            # we got an error
            EricMessageBox.critical(
                self,
                self.tr("Send Message via Gmail"),
                self.tr("""<p>Message could not be sent.<br>Reason: {0}</p>""").format(
                    message
                ),
            )

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to handle the Add... button.
        """
        fname = EricFileDialog.getOpenFileName(self, self.tr("Attach file"))
        if fname:
            self.attachFile(fname, False)

    def attachFile(self, fname, deleteFile):
        """
        Public method to add an attachment.

        @param fname name of the file to be attached
        @type str
        @param deleteFile flag indicating to delete the file after it has
            been sent
        @type bool
        """
        mimeType = mimetypes.guess_type(fname)[0]
        if not mimeType:
            mimeType = "application/octet-stream"
        QTreeWidgetItem(self.attachments, [fname, mimeType])
        self.attachments.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.attachments.header().setStretchLastSection(True)

        if deleteFile:
            self.__deleteFiles.append(fname)

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to handle the Delete button.
        """
        itm = self.attachments.currentItem()
        if itm is not None:
            itm = self.attachments.takeTopLevelItem(
                self.attachments.indexOfTopLevelItem(itm)
            )
            del itm

    @pyqtSlot(str)
    def on_subject_textChanged(self, txt):
        """
        Private slot to handle the textChanged signal of the subject edit.

        @param txt changed text
        @type str
        """
        self.sendButton.setEnabled(
            self.subject.text() != "" and self.message.toPlainText() != ""
        )

    def on_message_textChanged(self):
        """
        Private slot to handle the textChanged signal of the message edit.
        """
        self.sendButton.setEnabled(
            self.subject.text() != "" and self.message.toPlainText() != ""
        )
