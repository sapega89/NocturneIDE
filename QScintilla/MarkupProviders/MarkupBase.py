# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the base class for the markup providers.
"""


class MarkupBase:
    """
    Class implementing the base class for the markup providers.

    Note: Derived classes need only implement those method they provide
    functionality for. This base class implements do nothing variants for
    all methods.
    """

    def __init__(self):
        """
        Constructor
        """
        pass

    def kind(self):
        """
        Public method to get the markup kind.

        @return markup kind all lowercased
        @rtype str
        """
        return "none"

    def hasBold(self):
        """
        Public method to indicate the availability of bold markup.

        @return flag indicating the availability of bold markup
        @rtype bool
        """
        return False

    def bold(self, editor):
        """
        Public method to generate bold text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasItalic(self):
        """
        Public method to indicate the availability of italic markup.

        @return flag indicating the availability of italic markup
        @rtype bool
        """
        return False

    def italic(self, editor):
        """
        Public method to generate italic text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasStrikethrough(self):
        """
        Public method to indicate the availability of strikethrough markup.

        @return flag indicating the availability of strikethrough markup
        @rtype bool
        """
        return False

    def strikethrough(self, editor):
        """
        Public method to generate strikethrough text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasUnderline(self):
        """
        Public method to indicate the availability of underline markup.

        @return flag indicating the availability of underline markup
        @rtype bool
        """
        return False

    def underline(self, editor):
        """
        Public method to generate underline text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def headerLevels(self):
        """
        Public method to determine the available header levels.

        @return supported header levels
        @rtype int
        """
        return 0

    def header(self, editor, level):
        """
        Public method to generate a header.

        @param editor reference to the editor to work on
        @type Editor
        @param level header level
        @type int
        """
        pass

    def hasCode(self):
        """
        Public method to indicate the availability of inline code markup.

        @return flag indicating the availability of inline code markup
        @rtype bool
        """
        return False

    def code(self, editor):
        """
        Public method to generate inline code text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasCodeBlock(self):
        """
        Public method to indicate the availability of code block markup.

        @return flag indicating the availability of code block markup
        @rtype bool
        """
        return False

    def codeBlock(self, editor):
        """
        Public method to generate code block text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasHyperlink(self):
        """
        Public method to indicate the availability of hyperlink markup.

        @return flag indicating the availability of hyperlink markup
        @rtype bool
        """
        return False

    def hyperlink(self, editor):
        """
        Public method to generate hyperlink text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasLine(self):
        """
        Public method to indicate the availability of a horizontal line markup.

        @return flag indicating the availability of a horizontal line markup
        @rtype bool
        """
        return False

    def line(self, editor):
        """
        Public method to generate a horizontal line text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasQuote(self):
        """
        Public method to indicate the availability of block quote markup.

        @return flag indicating the availability of block quote markup
        @rtype bool
        """
        return False

    def quote(self, editor):
        """
        Public method to generate block quote text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasImage(self):
        """
        Public method to indicate the availability of image markup.

        @return flag indicating the availability of image markup
        @rtype bool
        """
        return False

    def image(self, editor):
        """
        Public method to generate image text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasBulletedList(self):
        """
        Public method to indicate the availability of bulleted list markup.

        @return flag indicating the availability of bulleted list markup
        @rtype bool
        """
        return False

    def bulletedList(self, editor):
        """
        Public method to generate bulleted list text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass

    def hasNumberedList(self):
        """
        Public method to indicate the availability of numbered list markup.

        @return flag indicating the availability of numbered list markup
        @rtype bool
        """
        return False

    def numberedList(self, editor):
        """
        Public method to generate numbered list text.

        @param editor reference to the editor to work on
        @type Editor
        """
        pass


def createProvider():
    """
    Function to instantiate a markup provider object.

    @return reference to the instantiated markup provider opject
    @rtype MarkupBase
    """
    return MarkupBase()
