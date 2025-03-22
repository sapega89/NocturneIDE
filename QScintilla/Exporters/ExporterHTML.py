# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an exporter for HTML.
"""

# This code is a port of the C++ code found in SciTE 1.74
# Original code: Copyright 1998-2006 by Neil Hodgson <neilh@scintilla.org>

import importlib.util
import io
import os
import sys

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QFontInfo
from PyQt6.QtWidgets import QInputDialog

from eric7 import EricUtilities, Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.UI.Previewers import MarkdownExtensions, PreviewerHTMLStyles

from .ExporterBase import ExporterBase


class HTMLGenerator:
    """
    Class implementing an HTML generator for exporting source code.
    """

    def __init__(self, editor):
        """
        Constructor

        @param editor reference to the editor object
        @type QScintilla.Editor.Editor
        """
        self.editor = editor

    def generate(
        self,
        tabSize=4,
        useTabs=False,
        wysiwyg=True,
        folding=False,
        onlyStylesUsed=False,
        titleFullPath=False,
    ):
        """
        Public method to generate HTML for the source editor.

        @param tabSize size of tabs
        @type int
        @param useTabs flag indicating the use of tab characters
        @type bool
        @param wysiwyg flag indicating colorization
        @type bool
        @param folding flag indicating usage of fold markers
        @type bool
        @param onlyStylesUsed flag indicating to include only style
            definitions for styles used in the source
        @type bool
        @param titleFullPath flag indicating to include the full file path
            in the title tag
        @type bool
        @return generated HTML text
        @rtype str
        """
        self.editor.recolor(0, -1)

        lengthDoc = self.editor.length()
        styleIsUsed = {}
        if onlyStylesUsed:
            for index in range(QsciScintilla.STYLE_MAX + 1):
                styleIsUsed[index] = False
            # check the used styles
            pos = 0
            while pos < lengthDoc:
                styleIsUsed[self.editor.styleAt(pos) & 0x7F] = True
                pos += 1
        else:
            for index in range(QsciScintilla.STYLE_MAX + 1):
                styleIsUsed[index] = True
        styleIsUsed[QsciScintilla.STYLE_DEFAULT] = True

        html = (
            """<!DOCTYPE html PUBLIC "-//W3C//DTD"""
            """ XHTML 1.0 Transitional//EN"\n"""
            """ "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">"""
            """\n"""
            """<html xmlns="http://www.w3.org/1999/xhtml">\n"""
            """<head>\n"""
        )
        if titleFullPath:
            html += """<title>{0}</title>\n""".format(self.editor.getFileName())
        else:
            html += """<title>{0}</title>\n""".format(
                os.path.basename(self.editor.getFileName())
            )
        html += (
            """<meta name="Generator" content="eric" />\n"""
            """<meta http-equiv="Content-Type" """
            """content="text/html; charset=utf-8" />\n"""
        )
        if folding:
            html += (
                """<script language="JavaScript" type="text/javascript">\n"""
                """<!--\n"""
                """function symbol(id, sym) {\n"""
                """  if (id.textContent == undefined) {\n"""
                """    id.innerText = sym;\n"""
                """  } else {\n"""
                """    id.textContent = sym;\n"""
                """  }\n"""
                """}\n"""
                """function toggle(id) {\n"""
                """  var thislayer = document.getElementById('ln' + id);\n"""
                """  id -= 1;\n"""
                """  var togline = document.getElementById('hd' + id);\n"""
                """  var togsym = document.getElementById('bt' + id);\n"""
                """  if (thislayer.style.display == 'none') {\n"""
                """    thislayer.style.display = 'block';\n"""
                """    togline.style.textDecoration = 'none';\n"""
                """    symbol(togsym, '- ');\n"""
                """  } else {\n"""
                """    thislayer.style.display = 'none';\n"""
                """    togline.style.textDecoration = 'underline';\n"""
                """    symbol(togsym, '+ ');\n"""
                """  }\n"""
                """}\n"""
                """//-->\n"""
                """</script>\n"""
            )

        lex = self.editor.getLexer()
        bgColour = (
            lex.paper(QsciScintilla.STYLE_DEFAULT).name()
            if lex
            else self.editor.paper().name()
        )

        html += """<style type="text/css">\n"""
        if lex:
            istyle = 0
            while istyle <= QsciScintilla.STYLE_MAX:
                if (
                    istyle <= QsciScintilla.STYLE_DEFAULT
                    or istyle > QsciScintilla.STYLE_LASTPREDEFINED
                ) and styleIsUsed[istyle]:
                    if lex.description(istyle) or istyle == QsciScintilla.STYLE_DEFAULT:
                        font = lex.font(istyle)
                        colour = lex.color(istyle)
                        paper = lex.paper(istyle)
                        if istyle == QsciScintilla.STYLE_DEFAULT:
                            html += """span {\n"""
                        else:
                            html += """.S{0:d} {{\n""".format(istyle)
                        if font.italic():
                            html += """    font-style: italic;\n"""
                        if font.bold():
                            html += """    font-weight: bold;\n"""
                        if wysiwyg:
                            html += """    font-family: '{0}';\n""".format(
                                font.family()
                            )
                        html += """    color: {0};\n""".format(colour.name())
                        if (
                            istyle != QsciScintilla.STYLE_DEFAULT
                            and bgColour != paper.name()
                        ):
                            html += """    background: {0};\n""".format(paper.name())
                            html += """    text-decoration: inherit;\n"""
                        if wysiwyg:
                            html += """    font-size: {0:d}pt;\n""".format(
                                QFontInfo(font).pointSize()
                            )
                        html += """}\n"""

                        # get substyles
                        subs_start, subs_count = self.editor.getSubStyleRange(istyle)
                        for subs_idx in range(subs_count):
                            styleIsUsed[subs_idx - subs_start] = True
                            font = lex.font(subs_start + subs_idx)
                            colour = lex.color(subs_start + subs_idx)
                            paper = lex.paper(subs_start + subs_idx)
                            html += ".S{0:d} {{\n".format(subs_idx - subs_start)
                            if font.italic():
                                html += "    font-style: italic;\n"
                            if font.bold():
                                html += "    font-weight: bold;\n"
                            if wysiwyg:
                                html += "    font-family: '{0}';\n".format(
                                    font.family()
                                )
                            html += "    color: {0};\n".format(colour.name())
                            if wysiwyg:
                                html += "    font-size: {0:d}pt;\n".format(
                                    QFontInfo(font).pointSize()
                                )
                            html += "}\n"
                    else:
                        styleIsUsed[istyle] = False
                istyle += 1
        else:
            colour = self.editor.color()
            paper = self.editor.paper()
            font = Preferences.getEditorOtherFonts("DefaultFont")
            html += """.S0 {\n"""
            if font.italic():
                html += """    font-style: italic;\n"""
            if font.bold():
                html += """    font-weight: bold;\n"""
            if wysiwyg:
                html += """    font-family: '{0}';\n""".format(font.family())
            html += """    color: {0};\n""".format(colour.name())
            if bgColour != paper.name():
                html += """    background: {0};\n""".format(paper.name())
                html += """    text-decoration: inherit;\n"""
            if wysiwyg:
                html += """    font-size: {0:d}pt;\n""".format(
                    QFontInfo(font).pointSize()
                )
            html += """}\n"""
        html += """</style>\n"""
        html += """</head>\n"""

        html += """<body bgcolor="{0}">\n""".format(bgColour)
        line = self.editor.lineAt(0)
        level = self.editor.foldLevelAt(line) - QsciScintilla.SC_FOLDLEVELBASE
        levelStack = [level]
        styleCurrent = self.editor.styleAt(0)
        inStyleSpan = False
        inFoldSpan = False
        # Global span for default attributes
        if wysiwyg:
            html += """<span>"""
        else:
            html += """<pre>"""

        if folding:
            if self.editor.foldFlagsAt(line) & QsciScintilla.SC_FOLDLEVELHEADERFLAG:
                html += ("""<span id="hd{0:d}" onclick="toggle('{1:d}')">""").format(
                    line, line + 1
                )
                html += """<span id="bt{0:d}">- </span>""".format(line)
                inFoldSpan = True
            else:
                html += """&nbsp; """

        if styleIsUsed[styleCurrent]:
            html += """<span class="S{0:0d}">""".format(styleCurrent)
            inStyleSpan = True

        column = 0
        pos = 0
        utf8 = self.editor.isUtf8()
        utf8Ch = b""
        utf8Len = 0

        while pos < lengthDoc:
            ch = self.editor.byteAt(pos)
            style = self.editor.styleAt(pos)
            if style != styleCurrent:
                if inStyleSpan:
                    html += """</span>"""
                    inStyleSpan = False
                if ch not in [b"\r", b"\n"]:  # no need of a span for the EOL
                    if styleIsUsed[style]:
                        html += """<span class="S{0:d}">""".format(style)
                        inStyleSpan = True
                    styleCurrent = style

            if ch == b" ":
                if wysiwyg:
                    prevCh = b""
                    if column == 0:
                        # at start of line, must put a &nbsp;
                        # because regular space will be collapsed
                        prevCh = b" "
                    while pos < lengthDoc and self.editor.byteAt(pos) == b" ":
                        if prevCh != b" ":
                            html += " "
                        else:
                            html += """&nbsp;"""
                        prevCh = self.editor.byteAt(pos)
                        pos += 1
                        column += 1
                    pos -= 1
                    # the last incrementation will be done by the outer loop
                else:
                    html += " "
                    column += 1
            elif ch == b"\t":
                ts = tabSize - (column % tabSize)
                if wysiwyg:
                    html += """&nbsp;""" * ts
                    column += ts
                else:
                    if useTabs:
                        html += "\t"
                        column += 1
                    else:
                        html += " " * ts
                        column += ts
            elif ch in [b"\r", b"\n"]:
                if inStyleSpan:
                    html += """</span>"""
                    inStyleSpan = False
                if inFoldSpan:
                    html += """</span>"""
                    inFoldSpan = False
                if ch == b"\r" and self.editor.byteAt(pos + 1) == b"\n":
                    pos += 1  # CR+LF line ending, skip the "extra" EOL char
                column = 0
                if wysiwyg:
                    html += """<br />"""

                styleCurrent = self.editor.styleAt(pos + 1)
                if folding:
                    line = self.editor.lineAt(pos + 1)
                    newLevel = self.editor.foldLevelAt(line)

                    if newLevel < level:
                        while levelStack[-1] > newLevel:
                            html += """</span>"""
                            levelStack.pop()
                    html += "\n"  # here to get clean code
                    if newLevel > level:
                        html += """<span id="ln{0:d}">""".format(line)
                        levelStack.append(newLevel)
                    if (
                        self.editor.foldFlagsAt(line)
                        & QsciScintilla.SC_FOLDLEVELHEADERFLAG
                    ):
                        html += (
                            """<span id="hd{0:d}" onclick="toggle('{1:d}')">"""
                        ).format(line, line + 1)
                        html += """<span id="bt{0:d}">- </span>""".format(line)
                        inFoldSpan = True
                    else:
                        html += """&nbsp; """
                    level = newLevel
                else:
                    html += "\n"

                if styleIsUsed[styleCurrent] and self.editor.byteAt(pos + 1) not in [
                    b"\r",
                    b"\n",
                ]:
                    # We know it's the correct next style,
                    # but no (empty) span for an empty line
                    html += """<span class="S{0:0d}">""".format(styleCurrent)
                    inStyleSpan = True
            else:
                if ch == b"<":
                    html += """&lt;"""
                elif ch == b">":
                    html += """&gt"""
                elif ch == b"&":
                    html += """&amp;"""
                else:
                    if ord(ch) > 127 and utf8:
                        utf8Ch += ch
                        if utf8Len == 0:
                            if (utf8Ch[0] & 0xF0) == 0xF0:
                                utf8Len = 4
                            elif (utf8Ch[0] & 0xE0) == 0xE0:
                                utf8Len = 3
                            elif (utf8Ch[0] & 0xC0) == 0xC0:
                                utf8Len = 2
                            column -= 1  # will be incremented again later
                        elif len(utf8Ch) == utf8Len:
                            ch = utf8Ch.decode("utf8")
                            html += EricUtilities.html_encode(ch)
                            utf8Ch = b""
                            utf8Len = 0
                        else:
                            column -= 1  # will be incremented again later
                    else:
                        html += ch.decode()
                column += 1

            pos += 1

        if inStyleSpan:
            html += """</span>"""

        if folding:
            while levelStack:
                html += """</span>"""
                levelStack.pop()

        if wysiwyg:
            html += """</span>"""
        else:
            html += """</pre>"""

        html += """</body>\n</html>\n"""

        return html


class ExporterHTML(ExporterBase):
    """
    Class implementing an exporter for HTML.
    """

    def __init__(self, editor, parent=None):
        """
        Constructor

        @param editor reference to the editor object
        @type QScintilla.Editor.Editor
        @param parent parent object of the exporter
        @type QObject
        """
        ExporterBase.__init__(self, editor, parent)

    def exportSource(self):
        """
        Public method performing the export.
        """
        filename = self._getFileName(self.tr("HTML Files (*.html)"))
        if not filename:
            return

        fn = self.editor.getFileName()
        extension = os.path.normcase(os.path.splitext(fn)[1][1:]) if fn else ""

        if (
            extension in Preferences.getEditor("PreviewMarkdownFileNameExtensions")
            or self.editor.getLanguage().lower() == "markdown"
        ):
            # export markdown to HTML
            colorSchemes = [
                self.tr("Light Background Color"),
                self.tr("Dark Background Color"),
            ]
            colorScheme, ok = QInputDialog.getItem(
                None,
                self.tr("Markdown Export"),
                self.tr("Select color scheme:"),
                colorSchemes,
                0,
                False,
            )
            if ok:
                colorSchemeIndex = colorSchemes.index(colorScheme)
            else:
                # light background as default
                colorSchemeIndex = 0
            with EricOverrideCursor():
                html = self.__generateFromMarkdown(colorSchemeIndex == 1)
        elif (
            extension in Preferences.getEditor("PreviewRestFileNameExtensions")
            or self.editor.getLanguage().lower() == "restructuredtext"
        ):
            # export ReST to HTML
            with EricOverrideCursor():
                html = self.__generateFromReSTDocutils()
        else:
            tabSize = self.editor.getEditorConfig("TabWidth")
            if tabSize == 0:
                tabSize = 4
            wysiwyg = Preferences.getEditorExporter("HTML/WYSIWYG")
            folding = Preferences.getEditorExporter("HTML/Folding")
            onlyStylesUsed = Preferences.getEditorExporter("HTML/OnlyStylesUsed")
            titleFullPath = Preferences.getEditorExporter("HTML/FullPathAsTitle")
            tabs = Preferences.getEditorExporter("HTML/UseTabs")

            with EricOverrideCursor():
                generator = HTMLGenerator(self.editor)
                html = generator.generate(
                    tabSize=tabSize,
                    useTabs=tabs,
                    wysiwyg=wysiwyg,
                    folding=folding,
                    onlyStylesUsed=onlyStylesUsed,
                    titleFullPath=titleFullPath,
                )

        if html:
            with EricOverrideCursor(), open(filename, "w", encoding="utf-8") as f:
                try:
                    f.write(html)
                except OSError as err:
                    EricMessageBox.critical(
                        self.editor,
                        self.tr("Export source"),
                        self.tr(
                            """<p>The source could not be exported to"""
                            """ <b>{0}</b>.</p><p>Reason: {1}</p>"""
                        ).format(filename, str(err)),
                    )
        else:
            EricMessageBox.critical(
                self.editor,
                self.tr("Export source"),
                self.tr(
                    """<p>The source could not be exported to"""
                    """ <b>{0}</b>.</p><p>Reason: No HTML code"""
                    """ generated.</p>"""
                ).format(filename),
            )

    def __generateFromReSTDocutils(self):
        """
        Private method to convert ReST text into HTML using 'docutils'.

        @return processed HTML
        @rtype str
        """
        if "sphinx" in sys.modules:
            # Make sure any Sphinx polution of docutils has been removed.
            unloadKeys = [
                k for k in sys.modules if k.startswith(("docutils", "sphinx"))
            ]
            for key in unloadKeys:
                sys.modules.pop(key)

        try:
            import docutils.core  # __IGNORE_EXCEPTION__ __IGNORE_WARNING_I10__
        except ImportError:
            EricMessageBox.critical(
                self.editor,
                self.tr("Export source"),
                self.tr(
                    """<p>ReStructuredText export requires the"""
                    """ <b>python-docutils</b> package.<br/>Install it with"""
                    """ your package manager, 'pip install docutils' or see"""
                    """ <a href="http://pypi.python.org/pypi/docutils">"""
                    """this page.</a></p>"""
                ),
            )
            return ""

        htmlFormat = Preferences.getEditor("PreviewRestDocutilsHTMLFormat").lower()
        # redirect sys.stderr because we are not interested in it here
        origStderr = sys.stderr
        sys.stderr = io.StringIO()
        html = docutils.core.publish_string(
            self.editor.text(), writer_name=htmlFormat
        ).decode("utf-8")
        sys.stderr = origStderr
        return html

    def __generateFromMarkdown(self, useDarkScheme):
        """
        Private method to convert Markdown text into HTML.

        @param useDarkScheme flag indicating to export using a dark color
            scheme
        @type bool
        @return processed HTML
        @rtype str
        """
        try:
            import markdown  # __IGNORE_EXCEPTION__ __IGNORE_WARNING_I10__
        except ImportError:
            EricMessageBox.critical(
                self.editor,
                self.tr("Export source"),
                self.tr(
                    """<p>Markdown export requires the <b>python-markdown"""
                    """</b> package.<br/>Install it with your package"""
                    """ manager, 'pip install docutils' or see """
                    """<a href="http://pythonhosted.org/Markdown/install"""
                    """.html"> installation instructions.</a></p>"""
                ),
            )
            return ""

        extensions = []

        text = self.editor.text()

        mermaidNeeded = False
        if Preferences.getEditor(
            "PreviewMarkdownMermaid"
        ) and MarkdownExtensions.MermaidRegexFullText.search(text):
            extensions.append(MarkdownExtensions.MermaidExtension())
            mermaidNeeded = True

        if Preferences.getEditor("PreviewMarkdownNLtoBR"):
            extensions.append("nl2br")

        pyMdown = False
        if Preferences.getEditor("PreviewMarkdownUsePyMdownExtensions") and bool(
            importlib.util.find_spec("pymdownx")
        ):
            # PyPI package is 'pymdown-extensions'
            extensions.extend(
                [
                    "toc",
                    "pymdownx.extra",
                    "pymdownx.caret",
                    "pymdownx.emoji",
                    "pymdownx.mark",
                    "pymdownx.tilde",
                    "pymdownx.keys",
                    "pymdownx.tasklist",
                    "pymdownx.smartsymbols",
                ]
            )
            pyMdown = True

        if not pyMdown:
            extensions.extend(["extra", "toc"])

            # version 2.0 supports only extension names, not instances
            if markdown.version_info[0] > 2 or (
                markdown.version_info[0] == 2 and markdown.version_info[1] > 0
            ):
                extensions.append(MarkdownExtensions.SimplePatternExtension())

        if Preferences.getEditor("PreviewMarkdownMathJax"):
            mathjax = (
                "<script type='text/javascript' id='MathJax-script' async"
                " src='https://cdn.jsdelivr.net/npm/mathjax@3/es5/"
                "tex-chtml.js'>\n"
                "</script>\n"
            )
            # prepare text for mathjax
            text = (
                text.replace(r"\(", r"\\(")
                .replace(r"\)", r"\\)")
                .replace(r"\[", r"\\[")
                .replace(r"\]", r"\\]")
            )
        else:
            mathjax = ""

        if mermaidNeeded:
            mermaid = (
                "<script type='text/javascript' id='Mermaid-script'"
                " src='https://unpkg.com/mermaid@8/dist/mermaid.min.js'>\n"
                "</script>\n"
            )
            if useDarkScheme:
                mermaid_initialize = (
                    "<script>mermaid.initialize({"
                    "theme: 'dark', "
                    "startOnLoad:true"
                    "});</script>"
                )
            else:
                mermaid_initialize = (
                    "<script>mermaid.initialize({"
                    "theme: 'default', "
                    "startOnLoad:true"
                    "});</script>"
                )
        else:
            mermaid = ""
            mermaid_initialize = ""

        htmlFormat = Preferences.getEditor("PreviewMarkdownHTMLFormat").lower()
        body = markdown.markdown(text, extensions=extensions, output_format=htmlFormat)
        style = (
            (
                PreviewerHTMLStyles.css_markdown_dark
                + PreviewerHTMLStyles.css_pygments_dark
            )
            if useDarkScheme
            else (
                PreviewerHTMLStyles.css_markdown_light
                + PreviewerHTMLStyles.css_pygments_light
            )
        )

        if htmlFormat == "xhtml1":
            head = (
                """<!DOCTYPE html PUBLIC "-//W3C//DTD"""
                """ XHTML 1.0 Transitional//EN"\n"""
                """ "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional"""
                """.dtd">\n"""
                """<html xmlns="http://www.w3.org/1999/xhtml">\n"""
            )
        elif htmlFormat == "html5":
            head = """<!DOCTYPE html>\n<html lang="EN">\n"""
        else:
            head = '<html lang="EN">\n'
        head += """<head>\n"""
        if Preferences.getEditorExporter("HTML/FullPathAsTitle"):
            head += """<title>{0}</title>\n""".format(self.editor.getFileName())
        else:
            head += """<title>{0}</title>\n""".format(
                os.path.basename(self.editor.getFileName())
            )
        head += (
            """<meta name="Generator" content="eric" />\n"""
            """<meta http-equiv="Content-Type" """
            """content="text/html; charset=utf-8" />\n"""
            """{0}"""
            """{1}"""
            """<style type="text/css">"""
            """{2}"""
            """</style>\n"""
            """</head>\n"""
            """<body>\n"""
        ).format(mathjax, mermaid, style)

        foot = """\n</body>\n</html>\n"""

        return head + body + mermaid_initialize + foot


def createExporter(editor, parent=None):
    """
    Function to instantiate an exporter object.

    @param editor reference to the editor object
    @type QScintilla.Editor.Editor
    @param parent parent object of the exporter (defaults to None)
    @type QObject (optional)
    @return exporter object
    @rtype ExporterHTML
    """
    return ExporterHTML(editor, parent=parent)
