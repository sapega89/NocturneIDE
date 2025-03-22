# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a simple registry containing the available test framework
interfaces.
"""

import copy


class TestFrameworkRegistry:
    """
    Class implementing a simple registry of test framework interfaces.

    The test executor for a framework is responsible for running the tests,
    receiving the results and preparing them for display. It must implement
    the interface of TestExecutorBase.

    Frameworks must first be registered using '.register()'. This registry
    can then create the assoicated test executor when '.createExecutor()' is
    called.
    """

    def __init__(self):
        """
        Constructor
        """
        self.__frameworks = {}

    def register(self, executorClass):
        """
        Public method to register a test framework executor.

        @param executorClass class implementing the test framework executor
        @type TestExecutorBase
        """
        self.__frameworks[executorClass.name] = executorClass

    def createExecutor(self, framework, widget):
        """
        Public method to create a test framework executor.

        Note: The executor classes have to be registered first.

        @param framework name of the test framework
        @type str
        @param widget reference to the unit test widget
        @type TestingWidget
        @return test framework executor object
        @rtype TestExecutorBase
        """
        cls = self.__frameworks[framework]
        return cls(widget)

    def getFrameworks(self):
        """
        Public method to get a copy of the registered frameworks.

        @return  copy of the registered frameworks
        @rtype dict
        """
        return copy.copy(self.__frameworks)
