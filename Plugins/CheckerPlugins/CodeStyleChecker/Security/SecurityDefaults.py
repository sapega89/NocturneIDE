# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the default values for some check modules.
"""

SecurityDefaults = {
    # generalHardcodedTmp.py
    "hardcoded_tmp_directories": ["/tmp", "/var/tmp", "/dev/shm", "~/tmp"],
    # secok
    # insecureHashlibNew.py
    "insecure_hashes": ["md4", "md5", "sha", "sha1"],
    # injectionShell.py
    # injectionWildcard.py
    "shell_injection_subprocess": [
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.run",
    ],
    # injectionShell.py
    # injectionWildcard.py
    "shell_injection_shell": [
        "os.system",
        "os.popen",
        "os.popen2",
        "os.popen3",
        "os.popen4",
        "popen2.popen2",
        "popen2.popen3",
        "popen2.popen4",
        "popen2.Popen3",
        "popen2.Popen4",
        "commands.getoutput",
        "commands.getstatusoutput",
        "subprocess.getoutput",
        "subprocess.getstatusoutput",
    ],
    # injectionShell.py
    "shell_injection_noshell": [
        "os.execl",
        "os.execle",
        "os.execlp",
        "os.execlpe",
        "os.execv",
        "os.execve",
        "os.execvp",
        "os.execvpe",
        "os.spawnl",
        "os.spawnle",
        "os.spawnlp",
        "os.spawnlpe",
        "os.spawnv",
        "os.spawnve",
        "os.spawnvp",
        "os.spawnvpe",
        "os.startfile",
    ],
    # insecureSslTls.py
    "insecure_ssl_protocol_versions": [
        "PROTOCOL_SSLv2",
        "SSLv2_METHOD",
        "SSLv23_METHOD",
        "PROTOCOL_SSLv3",
        "PROTOCOL_TLSv1",
        "PROTOCOL_TLSv1_1",
        "SSLv3_METHOD",
        "TLSv1_METHOD",
        "TLSv1_1_METHOD",
    ],
    # tryExcept.py
    "check_typed_exception": False,
    # weakCryptographicKey.py
    "weak_key_size_dsa_high": 1024,
    "weak_key_size_dsa_medium": 2048,
    "weak_key_size_rsa_high": 1024,
    "weak_key_size_rsa_medium": 2048,
    "weak_key_size_ec_high": 160,
    "weak_key_size_ec_medium": 224,
}
