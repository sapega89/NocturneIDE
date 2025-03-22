# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the standard debug client.
"""

from DebugBase import DebugBase
from DebugClientBase import DebugClientBase
from ModuleLoader import ModuleLoader
from ThreadExtension import ThreadExtension


class DebugClient(DebugClientBase, DebugBase, ThreadExtension):
    """
    Class implementing the client side of the debugger.
    """

    def __init__(self):
        """
        Constructor
        """
        DebugClientBase.__init__(self)

        DebugBase.__init__(self, self)

        ThreadExtension.__init__(self)

        self.__moduleLoader = ModuleLoader(self)


# We are normally called by the debugger to execute directly.

if __name__ == "__main__":
    debugClient = DebugClient()
    debugClient.main()
