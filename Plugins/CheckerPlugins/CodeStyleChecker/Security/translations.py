# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing message translations for the code style plugin messages
(security part).
"""

from PyQt6.QtCore import QCoreApplication

_securityMessages = {
    # assert used
    "S101": QCoreApplication.translate(
        "Security",
        "Use of 'assert' detected. The enclosed code will be removed when"
        " compiling to optimised byte code.",
    ),
    # exec used
    "S102": QCoreApplication.translate("Security", "Use of 'exec' detected."),
    # bad file permissions
    "S103": QCoreApplication.translate(
        "Security", "'chmod' setting a permissive mask {0} on file ({1})."
    ),
    # bind to all interfaces
    "S104": QCoreApplication.translate(
        "Security", "Possible binding to all interfaces."
    ),
    # hardcoded passwords
    "S105": QCoreApplication.translate(
        "Security", "Possible hardcoded password: '{0}'"
    ),
    "S106": QCoreApplication.translate(
        "Security", "Possible hardcoded password: '{0}'"
    ),
    "S107": QCoreApplication.translate(
        "Security", "Possible hardcoded password: '{0}'"
    ),
    # hardcoded tmp directory
    "S108": QCoreApplication.translate(
        "Security", "Probable insecure usage of temp file/directory."
    ),
    # try-except and contextlib.suppress
    "S110": QCoreApplication.translate("Security", "Try, Except, Pass detected."),
    "S112": QCoreApplication.translate("Security", "Try, Except, Continue detected."),
    "S113": QCoreApplication.translate("Security", "'contextlib.suppress()' detected."),
    # request without timeout
    "S114.1": QCoreApplication.translate("Security", "Call to {0} without timeout."),
    "S114.2": QCoreApplication.translate(
        "Security",
        "Call to {0} with timeout set to None.",
    ),
    # flask app
    "S201": QCoreApplication.translate(
        "Security",
        "A Flask app appears to be run with debug=True, which exposes the"
        " Werkzeug debugger and allows the execution of arbitrary code.",
    ),
    # tarfile.extractall
    "S202.1": QCoreApplication.translate(
        "Security",
        "Usage of 'tarfile.extractall(members=function(tarfile))'. "
        "Make sure your function properly discards dangerous members ({0}).",
    ),
    "S202.2": QCoreApplication.translate(
        "Security",
        "Found 'tarfile.extractall(members=?)' but couldn't identify the type of"
        " members. Check if the members were properly validated ({0}).",
    ),
    "S202.3": QCoreApplication.translate(
        "Security",
        "'tarfile.extractall()' used without any validation. Please check and"
        " discard dangerous members.",
    ),
    # prohibited calls
    "S301": QCoreApplication.translate(
        "Security",
        "Pickle and modules that wrap it can be unsafe when used to "
        "deserialize untrusted data, possible security issue.",
    ),
    "S302": QCoreApplication.translate(
        "Security", "Deserialization with the marshal module is possibly dangerous."
    ),
    "S303": QCoreApplication.translate(
        "Security", "Use of insecure MD2, MD4, MD5, or SHA1 hash function."
    ),
    "S304": QCoreApplication.translate(
        "Security",
        "Use of insecure cipher '{0}'. Replace with a known secure cipher"
        " such as AES.",
    ),
    "S305": QCoreApplication.translate(
        "Security", "Use of insecure cipher mode '{0}'."
    ),
    "S306": QCoreApplication.translate(
        "Security", "Use of insecure and deprecated function (mktemp)."
    ),
    "S307": QCoreApplication.translate(
        "Security",
        "Use of possibly insecure function - consider using safer ast.literal_eval.",
    ),
    "S308": QCoreApplication.translate(
        "Security",
        "Use of mark_safe() may expose cross-site scripting vulnerabilities"
        " and should be reviewed.",
    ),
    "S310": QCoreApplication.translate(
        "Security",
        "Audit url open for permitted schemes. Allowing use of file:/ or"
        " custom schemes is often unexpected.",
    ),
    "S311": QCoreApplication.translate(
        "Security",
        "Standard pseudo-random generators are not suitable for"
        " security/cryptographic purposes.",
    ),
    "S312": QCoreApplication.translate(
        "Security",
        "Telnet-related functions are being called. Telnet is considered"
        " insecure. Use SSH or some other encrypted protocol.",
    ),
    "S313": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable to"
        " XML attacks. Replace '{0}' with its defusedxml equivalent function"
        " or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S314": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable to"
        " XML attacks. Replace '{0}' with its defusedxml equivalent function"
        " or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S315": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable to"
        " XML attacks. Replace '{0}' with its defusedxml equivalent function"
        " or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S316": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable to"
        " XML attacks. Replace '{0}' with its defusedxml equivalent function"
        " or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S317": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable to"
        " XML attacks. Replace '{0}' with its defusedxml equivalent function"
        " or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S318": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable to"
        " XML attacks. Replace '{0}' with its defusedxml equivalent function"
        " or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S319": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable to"
        " XML attacks. Replace '{0}' with its defusedxml equivalent function"
        " or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S320": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable to"
        " XML attacks. Replace '{0}' with its defusedxml equivalent"
        " function.",
    ),
    "S321": QCoreApplication.translate(
        "Security",
        "FTP-related functions are being called. FTP is considered insecure."
        " Use SSH/SFTP/SCP or some other encrypted protocol.",
    ),
    "S322": QCoreApplication.translate(
        "Security",
        "The input method in Python 2 will read from standard input, evaluate"
        " and run the resulting string as Python source code. This is"
        " similar, though in many ways worse, than using eval. On Python 2,"
        " use raw_input instead, input is safe in Python 3.",
    ),
    "S323": QCoreApplication.translate(
        "Security",
        "By default, Python will create a secure, verified SSL context for"
        " use in such classes as HTTPSConnection. However, it still allows"
        " using an insecure context via the _create_unverified_context that"
        " reverts to the previous behavior that does not validate"
        " certificates or perform hostname checks.",
    ),
    # hashlib.new
    "S331": QCoreApplication.translate(
        "Security", "Use of insecure {0} hash function."
    ),
    "S332": QCoreApplication.translate(
        "Security",
        "Use of insecure {0} hash for security. Consider 'usedforsecurity=False'.",
    ),
    # prohibited imports
    "S401": QCoreApplication.translate(
        "Security",
        "A telnet-related module is being imported.  Telnet is considered"
        " insecure. Use SSH or some other encrypted protocol.",
    ),
    "S402": QCoreApplication.translate(
        "Security",
        "A FTP-related module is being imported.  FTP is considered"
        " insecure. Use SSH/SFTP/SCP or some other encrypted protocol.",
    ),
    "S403": QCoreApplication.translate(
        "Security",
        "Consider possible security implications associated with the '{0}' module.",
    ),
    "S404": QCoreApplication.translate(
        "Security",
        "Consider possible security implications associated with the '{0}' module.",
    ),
    "S405": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable"
        " to XML attacks. Replace '{0}' with the equivalent defusedxml"
        " package, or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S406": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable"
        " to XML attacks. Replace '{0}' with the equivalent defusedxml"
        " package, or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S407": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable"
        " to XML attacks. Replace '{0}' with the equivalent defusedxml"
        " package, or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S408": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable"
        " to XML attacks. Replace '{0}' with the equivalent defusedxml"
        " package, or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S409": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable"
        " to XML attacks. Replace '{0}' with the equivalent defusedxml"
        " package, or make sure defusedxml.defuse_stdlib() is called.",
    ),
    "S410": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable"
        " to XML attacks. Replace '{0}' with the equivalent defusedxml"
        " package.",
    ),
    "S411": QCoreApplication.translate(
        "Security",
        "Using '{0}' to parse untrusted XML data is known to be vulnerable"
        " to XML attacks. Use defusedxml.xmlrpc.monkey_patch() function to"
        " monkey-patch xmlrpclib and mitigate XML vulnerabilities.",
    ),
    "S412": QCoreApplication.translate(
        "Security",
        "Consider possible security implications associated with '{0}' module.",
    ),
    "S413": QCoreApplication.translate(
        "Security",
        "The pyCrypto library and its module '{0}' are no longer actively"
        " maintained and have been deprecated. Consider using"
        " pyca/cryptography library.",
    ),
    "S414": QCoreApplication.translate(
        "Security",
        "An IPMI-related module is being imported. IPMI is considered "
        "insecure. Use an encrypted protocol.",
    ),
    # insecure certificate usage
    "S501": QCoreApplication.translate(
        "Security",
        "'requests' call with verify=False disabling SSL certificate checks,"
        " security issue.",
    ),
    # insecure SSL/TLS protocol version
    "S502.1": QCoreApplication.translate(
        "Security",
        "'ssl.wrap_socket' call with insecure SSL/TLS protocol version"
        " identified, security issue.",
    ),
    "S502.2": QCoreApplication.translate(
        "Security",
        "'SSL.Context' call with insecure SSL/TLS protocol version identified,"
        " security issue.",
    ),
    "S502.3": QCoreApplication.translate(
        "Security",
        "Function call with insecure SSL/TLS protocol version identified,"
        " security issue.",
    ),
    "S503": QCoreApplication.translate(
        "Security",
        "Function definition identified with insecure SSL/TLS protocol"
        " version by default, possible security issue.",
    ),
    "S504": QCoreApplication.translate(
        "Security",
        "'ssl.wrap_socket' call with no SSL/TLS protocol version specified,"
        " the default 'SSLv23' could be insecure, possible security issue.",
    ),
    # weak cryptographic keys
    "S505": QCoreApplication.translate(
        "Security", "{0} key sizes below {1:d} bits are considered breakable."
    ),
    # YAML load
    "S506": QCoreApplication.translate(
        "Security",
        "Use of unsafe 'yaml.load()'. Allows instantiation of arbitrary"
        " objects. Consider 'yaml.safe_load()'.",
    ),
    # SSH host key verification
    "S507": QCoreApplication.translate(
        "Security",
        "Paramiko call with policy set to automatically trust the unknown host key.",
    ),
    # insecure SNMP
    "S508": QCoreApplication.translate(
        "Security",
        "The use of SNMPv1 and SNMPv2 is insecure. You should use SNMPv3 if possible.",
    ),
    "S509": QCoreApplication.translate(
        "Security",
        "You should not use SNMPv3 without encryption. noAuthNoPriv & authNoPriv is"
        " insecure.",
    ),
    # Shell injection
    "S601": QCoreApplication.translate(
        "Security",
        "Possible shell injection via 'Paramiko' call, check inputs are"
        " properly sanitized.",
    ),
    "S602.L": QCoreApplication.translate(
        "Security",
        "'subprocess' call with shell=True seems safe, but may be changed"
        " in the future, consider rewriting without shell",
    ),
    "S602.H": QCoreApplication.translate(
        "Security", "'subprocess' call with shell=True identified, security issue."
    ),
    "S603": QCoreApplication.translate(
        "Security", "'subprocess' call - check for execution of untrusted input."
    ),
    "S604": QCoreApplication.translate(
        "Security",
        "Function call with shell=True parameter identified, possible"
        " security issue.",
    ),
    "S605.L": QCoreApplication.translate(
        "Security",
        "Starting a process with a shell: Seems safe, but may be changed in"
        " the future, consider rewriting without shell",
    ),
    "S605.H": QCoreApplication.translate(
        "Security",
        "Starting a process with a shell, possible injection detected,"
        " security issue.",
    ),
    "S606": QCoreApplication.translate(
        "Security", "Starting a process without a shell."
    ),
    "S607": QCoreApplication.translate(
        "Security", "Starting a process with a partial executable path."
    ),
    # SQL injection
    "S608": QCoreApplication.translate(
        "Security",
        "Possible SQL injection vector through string-based query construction.",
    ),
    # Wildcard injection
    "S609": QCoreApplication.translate(
        "Security", "Possible wildcard injection in call: {0}"
    ),
    # Django SQL injection
    "S610": QCoreApplication.translate(
        "Security", "Use of 'extra()' opens a potential SQL attack vector."
    ),
    "S611": QCoreApplication.translate(
        "Security", "Use of 'RawSQL()' opens a potential SQL attack vector."
    ),
    # insecure logging.config.listen()
    "S612": QCoreApplication.translate(
        "Security",
        "Use of insecure logging.config.listen() detected.",
    ),
    # Trojan Source
    "S613": QCoreApplication.translate(
        "Security",
        "The Python source file contains bidirectional control characters ({0}).",
    ),
    # PyTorch unsafe load or save
    "S614": QCoreApplication.translate(
        "Security", "Use of unsafe PyTorch load or save."
    ),
    # Jinja2 templates
    "S701.1": QCoreApplication.translate(
        "Security",
        "Using jinja2 templates with 'autoescape=False' is dangerous and can"
        " lead to XSS. Use 'autoescape=True' or use the 'select_autoescape'"
        " function to mitigate XSS vulnerabilities.",
    ),
    "S701.2": QCoreApplication.translate(
        "Security",
        "By default, jinja2 sets 'autoescape' to False. Consider using"
        " 'autoescape=True' or use the 'select_autoescape' function to"
        " mitigate XSS vulnerabilities.",
    ),
    # Mako templates
    "S702": QCoreApplication.translate(
        "Security",
        "Mako templates allow HTML/JS rendering by default and are inherently"
        " open to XSS attacks. Ensure variables in all templates are properly"
        " sanitized via the 'n', 'h' or 'x' flags (depending on context). For"
        " example, to HTML escape the variable 'data' do ${{ data |h }}.",
    ),
    # Django XSS vulnerability
    "S703": QCoreApplication.translate(
        "Security", "Potential XSS on 'mark_safe()' function."
    ),
    # hardcoded AWS passwords
    "S801": QCoreApplication.translate(
        "Security", "Possible hardcoded AWS access key ID: {0}"
    ),
    "S802": QCoreApplication.translate(
        "Security", "Possible hardcoded AWS secret access key: {0}"
    ),
}

_securityMessagesSampleArgs = {
    "S103": ["0o777", "testfile.txt"],
    "S105": ["password"],
    "S106": ["password"],
    "S107": ["password"],
    "S114.1": ["requests"],
    "S114.2": ["httpx"],
    "S202.1": ["members_filter(tar)"],
    "S202.2": ["tar"],
    "S304": ["Crypto.Cipher.DES"],
    "S305": ["cryptography.hazmat.primitives.ciphers.modes.ECB"],
    "S313": ["xml.etree.cElementTree.parse"],
    "S314": ["xml.etree.ElementTree.parse"],
    "S315": ["xml.sax.expatreader.create_parser"],
    "S316": ["xml.dom.expatbuilder.parse"],
    "S317": ["xml.sax.parse"],
    "S318": ["xml.dom.minidom.parse"],
    "S319": ["xml.dom.pulldom.parse"],
    "S320": ["lxml.etree.parse"],
    "S331": ["MD5"],
    "S403": ["pickle"],
    "S404": ["subprocess"],
    "S405": ["xml.etree.ElementTree"],
    "S406": ["xml.sax"],
    "S407": ["xml.dom.expatbuilder"],
    "S408": ["xml.dom.minidom"],
    "S409": ["xml.dom.pulldom"],
    "S410": ["lxml"],
    "S411": ["xmlrpclib"],
    "S412": ["wsgiref.handlers.CGIHandler"],
    "S413": ["Crypto.Cipher"],
    "S505": ["RSA", 2048],
    "S609": ["os.system"],
    "S613": [repr("\u202e")],
    "S801": ["A1B2C3D4E5F6G7H8I9J0"],  # secok
    "S802": ["aA1bB2cC3dD4/eE5fF6gG7+hH8iI9jJ0=kKlLM+="],  # secok
}
