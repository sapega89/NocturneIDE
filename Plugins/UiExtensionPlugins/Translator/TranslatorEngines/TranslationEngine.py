# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the translation engine base class.
"""

import contextlib

from PyQt6.QtCore import QObject, pyqtSignal


class TranslationEngine(QObject):
    """
    Class implementing the translation engine base class containing
    default methods.

    @signal availableTranslationsLoaded() emitted to indicate the availability
        of the list of supported translation languages
    """

    availableTranslationsLoaded = pyqtSignal()

    def __init__(self, plugin, parent=None):
        """
        Constructor

        @param plugin reference to the plugin object
        @type TranslatorPlugin
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.plugin = plugin

    def engineName(self):
        """
        Public method to get the name of the engine.

        @return engine name
        @rtype str
        """
        return ""

    def supportedLanguages(self):
        """
        Public method to get the supported languages.

        @return list of supported language codes
        @rtype list of str
        """
        return []

    def supportedTargetLanguages(self, original):
        """
        Public method to get a list of supported target languages for an
        original language.

        Note: The default implementation return the list of supported languages
        (i.e. the same as those for the source) with the given original
        removed.

        @param original original language
        @type str
        @return list of supported target languages for the given original
        @rtype list of str
        """
        targetLanguages = self.supportedLanguages()[:]
        with contextlib.suppress(ValueError):
            targetLanguages.remove(original)

        return targetLanguages

    def hasTTS(self):
        """
        Public method indicating the Text-to-Speech capability.

        @return flag indicating the Text-to-Speech capability
        @rtype bool
        """
        return False

    def getTextToSpeechData(self, requestObject, text, language):  # noqa: U100
        """
        Public method to pronounce the given text.

        @param requestObject reference to the request object (unused)
        @type TranslatorRequest
        @param text text to be pronounced (unused)
        @type str
        @param language language code of the text (unused)
        @type str
        @return tuple with pronounce data or an error string and a success flag
        @rtype tuple of (QByteArray or str, bool)
        """
        return self.tr("No pronounce data available"), False

    def getTranslation(
        self, requestObject, text, originalLanguage, translationLanguage  # noqa: U100
    ):
        """
        Public method to translate the given text.

        @param requestObject reference to the request object (unused)
        @type TranslatorRequest
        @param text text to be translated (unused)
        @type str
        @param originalLanguage language code of the original (unused)
        @type str
        @param translationLanguage language code of the translation (unused)
        @type str
        @return tuple of translated text and flag indicating success (unused)
        @rtype tuple of (str, bool)
        """
        return self.tr("No translation available"), False
