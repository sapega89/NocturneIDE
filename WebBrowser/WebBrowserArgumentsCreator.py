# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a function to create an argparse.Namespace object for the web
browser.
"""

import argparse
import sys


def createArgparseNamespace(argv=None):
    """
    Function to create an argparse.Namespace object.

    @param argv list of command line arguments to be parsed
    @type list of str
    @return created argument parser object
    @rtype argparse.ArgumentParser
    """
    from eric7.__version__ import Version

    # 1. create the argument parser
    parser = argparse.ArgumentParser(
        description="Web Browser application of the eric tool suite.",
        epilog="Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>.",
    )

    # 2. add the arguments
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {0}".format(Version),
        help="show version information and exit",
    )
    parser.add_argument(
        "--config",
        metavar="config_dir",
        help="use the given directory as the one containing the config files",
    )
    parser.add_argument(
        "--settings",
        metavar="settings_dir",
        help="use the given directory to store the settings files",
    )
    parser.add_argument(
        "--name",
        metavar="browser name",
        default="",
        help="name to be used for the browser instance",
    )
    parser.add_argument(
        "--new-tab",
        metavar="URL",
        action="append",
        help="open a new tab for the given URL",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="start the browser in private browsing mode",
    )
    parser.add_argument(
        "--qthelp",
        action="store_true",
        help="start the browser with support for QtHelp",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="don't show any startup error messages",
    )
    parser.add_argument(
        "--search",
        metavar="searchword",
        help="search for the given word",
    )
    parser.add_argument(
        "--shutdown",
        action="store_true",
        help="shut down the browser instance",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="start the browser as a single application",
    )
    parser.add_argument(
        "home",
        nargs="?",
        default="",
        metavar="file | URL",
        help="open a file or URL",
    )

    # 3. create the Namespace object by parsing the command line
    if argv is None:
        argv = sys.argv[1:]
    args = parser.parse_args(argv)
    return args
