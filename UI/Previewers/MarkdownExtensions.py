# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some Markdown extensions.
"""

import re

from markdown.extensions import Extension
from markdown.inlinepatterns import SimpleTagInlineProcessor
from markdown.preprocessors import Preprocessor

######################################################################
## Code below is an enhanced copy of the Mermaid extension
##
## Original code Copyright 2018-2020 [Olivier Ruelle]
## License: GNU GPLv3
######################################################################

MermaidRegex = re.compile(r"^(?P<mermaid_sign>[\~\`]){3}[ \t]*[Mm]ermaid[ \t]*$")
MermaidRegexFullText = re.compile(r"([\~\`]){3}[ \t]*[Mm]ermaid")  # noqa:U200


class MermaidPreprocessor(Preprocessor):
    """
    Class implementing a markdown pre-processor for Mermaid.
    """

    def run(self, lines):
        """
        Public method to do the pre-processing.

        @param lines text lines to be processed
        @type list of str
        @return processed lines
        @rtype list of str
        """
        new_lines = []
        mermaid_sign = ""
        m_start = None
        m_end = None
        in_mermaid_code = False
        is_mermaid = False
        old_line = ""
        for line in lines:
            # Wait for starting line with MermaidRegex
            # (~~~ or ``` following by [mM]ermaid )
            if not in_mermaid_code:
                m_start = MermaidRegex.match(line)
            else:
                m_end = re.match(r"^[" + mermaid_sign + "]{3}[ \t]*$", line)
                if m_end:
                    in_mermaid_code = False

            if m_start:
                in_mermaid_code = True
                mermaid_sign = m_start.group("mermaid_sign")
                if not re.match(r"^[\ \t]*$", old_line):
                    new_lines.append("")
                if not is_mermaid:
                    is_mermaid = True
                new_lines.append('<div class="mermaid">')
                m_start = None
            elif m_end:
                new_lines.append("</div>")
                new_lines.append("")
                m_end = None
            elif in_mermaid_code:
                new_lines.append(line.strip().replace("<", "&lt;").replace(">", "&gt;"))
            else:
                new_lines.append(line)

            old_line = line

        if is_mermaid:
            new_lines.append("")

        return new_lines


class MermaidExtension(Extension):
    """
    Class implementing a Markdown Extension for Mermaid.
    """

    def extendMarkdown(self, md):
        """
        Public method to register the extension.

        @param md reference to markdown
        @type Markdown
        """
        md.preprocessors.register(MermaidPreprocessor(md), "mermaid", 35)
        md.registerExtension(self)


######################################################################
## Some extension to some basic additions
######################################################################


class SimplePatternExtension(Extension):
    """
    Class implementing a Markdown extension for ~, ~~, ^, ^^ and ==.

    Note: This is a very simple pattern extension that might conflict with
    formulas set for MathJax. Use the 'pymdown-extensions' package in this
    case.
    """

    DEL_RE = r"(~~)(.+?)~~"
    SUB_RE = r"(~)(.+?)~"
    INS_RE = r"(\^\^)(.*?)\^\^"
    SUP_RE = r"(\^)(.*?)\^"
    MARK_RE = r"(==)(.*?)=="

    def extendMarkdown(self, md):
        """
        Public method to register the extension.

        @param md reference to markdown
        @type Markdown
        """
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(self.SUB_RE, "sub"), "subscript", 30
        )
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(self.DEL_RE, "del"), "deleted", 40
        )
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(self.SUP_RE, "sup"), "superscript", 30
        )
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(self.INS_RE, "ins"), "inserted", 40
        )
        md.inlinePatterns.register(
            SimpleTagInlineProcessor(self.MARK_RE, "mark"), "mark", 40
        )
