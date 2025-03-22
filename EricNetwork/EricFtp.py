# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an extension to the Python FTP class to support FTP
proxies.
"""

import enum
import ftplib  # secok

from socket import _GLOBAL_DEFAULT_TIMEOUT


class EricFtpProxyError(ftplib.Error):
    """
    Class to signal an error related to proxy configuration.

    The error message starts with a three digit error code followed by a
    space and the error string. Supported error codes are:
    <ul>
      <li>910: proxy error; the second number gives the category of the proxy
          error. The original response from the proxy is appended in the next
          line.</li>
      <li>930: proxy error; the second number gives the category of the proxy
          error. The original response from the proxy is appended in the next
          line.</li>
      <li>940: proxy error; the second number gives the category of the proxy
          error. The original response from the proxy is appended in the next
          line.</li>
      <li>950: proxy error; the second number gives the category of the proxy
          error. The original response from the proxy is appended in the next
          line.</li>
      <li>990: proxy usage is enabled but no proxy host given</li>
      <li>991: proxy usage is enabled but no proxy user given</li>
      <li>992: proxy usage is enabled but no proxy password given</li>
    </ul>
    """

    pass


class EricFtpProxyType(enum.Enum):
    """
    Class defining the supported FTP proxy types.
    """

    NO_PROXY = 0  # no proxy
    NON_AUTHORIZING = 1  # non authorizing proxy
    USER_SERVER = 2  # proxy login first, than user@remote.host
    SITE = 3  # proxy login first, than use SITE command
    OPEN = 4  # proxy login first, than use OPEN command
    USER_PROXYUSER_SERVER = 5  # one login for both
    PROXYUSER_SERVER = 6
    # proxy login with remote host given, than normal remote login
    AUTH_RESP = 7  # authenticate to proxy with AUTH and RESP commands
    BLUECOAT = 8  # bluecoat proxy


class EricFtp(ftplib.FTP):
    """
    Class implementing an extension to the Python FTP class to support FTP
    proxies.
    """

    def __init__(  # secok
        self,
        host="",
        user="",
        password="",
        acct="",
        proxyType=EricFtpProxyType.NO_PROXY,
        proxyHost="",
        proxyPort=ftplib.FTP_PORT,
        proxyUser="",
        proxyPassword="",
        proxyAccount="",
        timeout=_GLOBAL_DEFAULT_TIMEOUT,
    ):
        """
        Constructor

        @param host name of the FTP host
        @type str
        @param user user name for login to FTP host
        @type str
        @param password password for login to FTP host
        @type str
        @param acct account for login to FTP host
        @type str
        @param proxyType type of the FTP proxy
        @type EricFtpProxyType
        @param proxyHost name of the FTP proxy
        @type str
        @param proxyPort port of the FTP proxy
        @type int
        @param proxyUser user name for login to the proxy
        @type str
        @param proxyPassword password for login to the proxy
        @type str
        @param proxyAccount accounting info for the proxy
        @type str
        @param timeout timeout in seconds for blocking operations
        @type int
        """
        super().__init__()

        self.__timeout = timeout

        self.__proxyType = proxyType
        self.__proxyHost = proxyHost
        self.__proxyPort = proxyPort
        self.__proxyUser = proxyUser
        self.__proxyPassword = proxyPassword
        self.__proxyAccount = proxyAccount

        self.__host = host
        self.__port = ftplib.FTP_PORT

        if host:
            self.connect(host)
            if user:
                self.login(user, password, acct)

    def setProxy(
        self,
        proxyType=EricFtpProxyType.NO_PROXY,
        proxyHost="",
        proxyPort=ftplib.FTP_PORT,
        proxyUser="",
        proxyPassword="",
        proxyAccount="",
    ):
        """
        Public method to set the proxy configuration.

        @param proxyType type of the FTP proxy
        @type EricFtpProxyType
        @param proxyHost name of the FTP proxy
        @type str
        @param proxyPort port of the FTP proxy
        @type int
        @param proxyUser user name for login to the proxy
        @type str
        @param proxyPassword password  for login to the proxy
        @type str
        @param proxyAccount accounting info for the proxy
        @type str
        """
        self.__proxyType = proxyType
        self.__proxyHost = proxyHost
        self.__proxyPort = proxyPort
        self.__proxyUser = proxyUser
        self.__proxyPassword = proxyPassword
        self.__proxyAccount = proxyAccount

    def setProxyAuthentication(self, proxyUser="", proxyPassword="", proxyAccount=""):
        """
        Public method to set the proxy authentication info.

        @param proxyUser user name for login to the proxy
        @type str
        @param proxyPassword password  for login to the proxy
        @type str
        @param proxyAccount accounting info for the proxy
        @type str
        """
        self.__proxyUser = proxyUser
        self.__proxyPassword = proxyPassword
        self.__proxyAccount = proxyAccount

    def connect(self, host="", port=0, timeout=-999):
        """
        Public method to connect to the given FTP server.

        This extended method connects to the proxy instead of the given host,
        if a proxy is to be used. It throws an exception, if the proxy data
        is incomplete.

        @param host name of the FTP host
        @type str
        @param port port of the FTP host
        @type int
        @param timeout timeout in seconds for blocking operations
        @type int
        @return welcome message of the server
        @rtype str
        @exception EricFtpProxyError raised to indicate a proxy related issue
        """
        if host:
            self.__host = host
        if port:
            self.__port = port
        if timeout != -999:
            self.__timeout = timeout

        if self.__proxyType != EricFtpProxyType.NO_PROXY:
            if not self.__proxyHost:
                raise EricFtpProxyError(
                    "990 Proxy usage requested, but no proxy host given."
                )

            return super().connect(self.__proxyHost, self.__proxyPort, self.__timeout)
        else:
            return super().connect(self.__host, self.__port, self.__timeout)

    def login(self, user="", password="", acct=""):  # secok
        """
        Public method to login to the FTP server.

        This extended method respects the FTP proxy configuration. There are
        many different FTP proxy products available. But unfortunately there
        is no standard for how o traverse a FTP proxy. The lis below shows
        the sequence of commands used.

        <table>
          <tr><td>user</td><td>Username for remote host</td></tr>
          <tr><td>pass</td><td>Password for remote host</td></tr>
          <tr><td>pruser</td><td>Username for FTP proxy</td></tr>
          <tr><td>prpass</td><td>Password for FTP proxy</td></tr>
          <tr><td>remote.host</td><td>Hostname of the remote FTP server</td>
          </tr>
        </table>

        <dl>
          <dt>EricFtpProxyType.NO_PROXY:</dt>
          <dd>
            USER user<br/>
            PASS pass
          </dd>
          <dt>EricFtpProxyType.NON_AUTHORIZING:</dt>
          <dd>
            USER user@remote.host<br/>
            PASS pass
          </dd>
          <dt>EricFtpProxyType.USER_SERVER:</dt>
          <dd>
            USER pruser<br/>
            PASS prpass<br/>
            USER user@remote.host<br/>
            PASS pass
          </dd>
          <dt>EricFtpProxyType.SITE:</dt>
          <dd>
            USER pruser<br/>
            PASS prpass<br/>
            SITE remote.site<br/>
            USER user<br/>
            PASS pass
          </dd>
          <dt>EricFtpProxyType.OPEN:</dt>
          <dd>
            USER pruser<br/>
            PASS prpass<br/>
            OPEN remote.site<br/>
            USER user<br/>
            PASS pass
          </dd>
          <dt>EricFtpProxyType.USER_PROXYUSER_SERVER:</dt>
          <dd>
            USER user@pruser@remote.host<br/>
            PASS pass@prpass
          </dd>
          <dt>EricFtpProxyType.PROXYUSER_SERVER:</dt>
          <dd>
            USER pruser@remote.host<br/>
            PASS prpass<br/>
            USER user<br/>
            PASS pass
          </dd>
          <dt>EricFtpProxyType.AUTH_RESP:</dt>
          <dd>
            USER user@remote.host<br/>
            PASS pass<br/>
            AUTH pruser<br/>
            RESP prpass
          </dd>
          <dt>EricFtpProxyType.BLUECOAT:</dt>
          <dd>
            USER user@remote.host pruser<br/>
            PASS pass<br/>
            ACCT prpass
          </dd>
        </dl>

        @param user username for the remote host
        @type str
        @param password password for the remote host
        @type str
        @param acct accounting information for the remote host
        @type str
        @return response sent by the remote host
        @rtype str
        @exception EricFtpProxyError raised to indicate a proxy related issue
        @exception ftplib.error_reply raised to indicate an FTP error reply
        """
        if not user:
            user = "anonymous"
        if not password:
            # make sure it is a string
            password = ""  # secok
        if not acct:
            # make sure it is a string
            acct = ""
        if user == "anonymous" and password in {"", "-"}:
            password += "anonymous@"

        if self.__proxyType != EricFtpProxyType.NO_PROXY:
            if self.__proxyType != EricFtpProxyType.NON_AUTHORIZING:
                # check, if a valid proxy configuration is known
                if not self.__proxyUser:
                    raise EricFtpProxyError(
                        "991 Proxy usage requested, but no proxy user given"
                    )
                if not self.__proxyPassword:
                    raise EricFtpProxyError(
                        "992 Proxy usage requested, but no proxy password given"
                    )

            if self.__proxyType in [
                EricFtpProxyType.NON_AUTHORIZING,
                EricFtpProxyType.AUTH_RESP,
                EricFtpProxyType.BLUECOAT,
            ]:
                user += "@" + self.__host
                if self.__proxyType == EricFtpProxyType.BLUECOAT:
                    user += " " + self.__proxyUser
                    acct = self.__proxyPassword
            elif self.__proxyType == EricFtpProxyType.USER_PROXYUSER_SERVER:
                user = "{0}@{1}@{2}".format(user, self.__proxyUser, self.__host)
                password = "{0}@{1}".format(password, self.__proxyPassword)
            else:
                pruser = self.__proxyUser
                if self.__proxyType == EricFtpProxyType.USER_SERVER:
                    user += "@" + self.__host
                elif self.__proxyType == EricFtpProxyType.PROXYUSER_SERVER:
                    pruser += "@" + self.__host

                # authenticate to the proxy first
                presp = self.sendcmd("USER " + pruser)
                if presp[0] == "3":
                    presp = self.sendcmd("PASS " + self.__proxyPassword)
                if presp[0] == "3" and self.__proxyAccount:
                    presp = self.sendcmd("ACCT " + self.__proxyAccount)
                if presp[0] != "2":
                    raise EricFtpProxyError(
                        "9{0}0 Error authorizing at proxy\n{1}".format(presp[0], presp)
                    )

                if self.__proxyType == EricFtpProxyType.SITE:
                    # send SITE command
                    presp = self.sendcmd("SITE " + self.__host)
                    if presp[0] != "2":
                        raise EricFtpProxyError(
                            "9{0}0 Error sending SITE command\n{1}".format(
                                presp[0], presp
                            )
                        )
                elif self.__proxyType == EricFtpProxyType.OPEN:
                    # send OPEN command
                    presp = self.sendcmd("OPEN " + self.__host)
                    if presp[0] != "2":
                        raise EricFtpProxyError(
                            "9{0}0 Error sending OPEN command\n{1}".format(
                                presp[0], presp
                            )
                        )

        # authenticate to the remote host or combined to proxy and remote host
        resp = self.sendcmd("USER " + user)
        if resp[0] == "3":
            resp = self.sendcmd("PASS " + password)
        if resp[0] == "3":
            resp = self.sendcmd("ACCT " + acct)
        if resp[0] != "2":
            raise ftplib.error_reply(resp)  # secok

        if self.__proxyType == EricFtpProxyType.AUTH_RESP:
            # authorize to the FTP proxy
            presp = self.sendcmd("AUTH " + self.__proxyUser)
            if presp[0] == "3":
                presp = self.sendcmd("RESP " + self.__proxyPassword)
            if presp[0] != "2":
                raise EricFtpProxyError(
                    "9{0}0 Error authorizing at proxy\n{1}".format(presp[0], presp)
                )

        return resp
