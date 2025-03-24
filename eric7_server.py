#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
eric-ide Server.

This is the main Python script of the eric-ide server. This is a server to perform
remote development (e.g. code hosted on another computer or through a docker
container).
"""

import argparse
import socket
import sys

from __version__ import Version
from RemoteServer.EricServer import EricServer


def createArgumentParser():
    """
    Function to create an argument parser.

    @return created argument parser object
    @rtype argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description=(
            "Start the eric-ide server component. This will listen for connections"
            " from the eric IDE in order to perform remote development."
        ),
        epilog="Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>.",
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=42024,
        help="Listen on the given port for connections from an eric IDE (default"
        " 42024).",
    )
    parser.add_argument(
        "-6",
        "--with-ipv6",
        action="store_true",
        help="Listen on IPv6 interfaces as well if the system supports the creation"
        " of TCP sockets which can handle both IPv4 and IPv6. {0}".format(
            "This system supports this feature."
            if socket.has_dualstack_ipv6()
            else "This system does not support this feature. The option will be"
            " ignored."
        ),
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {0}".format(Version),
        help="Show version information and exit.",
    )
    parser.add_argument(
        "client_id",
        nargs="?",
        default="",
        help="ID string to check, if received messages have been sent by a"
        " valid eric IDE (default empty)",
    )

    return parser


def main():
    """
    Main entry point into the application.
    """
    parser = createArgumentParser()
    args = parser.parse_args()

    if not args.client_id:
        print(
            "You should consider to add a client ID string in order to allow\n"
            "the eric-ide server to check, if received messages have been sent\n"
            "by a valid eric IDE.\n"
        )

    server = EricServer(port=args.port, useIPv6=args.with_ipv6, clientId=args.client_id)
    ok = server.run()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

#
# eflag: noqa = M801
