# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Tex lexer with some additional methods.
"""

import contextlib

from PyQt6.Qsci import QsciLexerTeX

from eric7 import Preferences

from .Lexer import Lexer


class LexerTeX(Lexer, QsciLexerTeX):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerTeX.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "%"

        self.keywordSetDescriptions = [
            self.tr("TeX, eTeX, pdfTeX, Omega"),
            self.tr("ConTeXt Dutch"),
            self.tr("ConTeXt English"),
            self.tr("ConTeXt German"),
            self.tr("ConTeXt Czech"),
            self.tr("ConTeXt Italian"),
            self.tr("ConTeXt Romanian"),
            self.tr("LaTeX"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        with contextlib.suppress(AttributeError):
            self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))
            self.setFoldComments(Preferences.getEditor("TexFoldComment"))
            self.setProcessComments(Preferences.getEditor("TexProcessComments"))
            self.setProcessIf(Preferences.getEditor("TexProcessIf"))

    def isCommentStyle(self, _style):
        """
        Public method to check, if a style is a comment style.

        @param _style style to check (unused)
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return False

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [QsciLexerTeX.Text]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        texKeywords = (
            "above abovedisplayshortskip abovedisplayskip "
            "abovewithdelims accent adjdemerits advance afterassignment "
            "aftergroup atop atopwithdelims badness baselineskip batchmode "
            "begingroup belowdisplayshortskip belowdisplayskip binoppenalty "
            "botmark box boxmaxdepth brokenpenalty catcode char chardef "
            "cleaders closein closeout clubpenalty copy count countdef cr "
            "crcr csname day deadcycles def defaulthyphenchar defaultskewchar "
            "delcode delimiter delimiterfactor delimeters delimitershortfall "
            "delimeters dimen dimendef discretionary displayindent "
            "displaylimits displaystyle displaywidowpenalty displaywidth "
            "divide doublehyphendemerits dp dump edef else emergencystretch "
            "end endcsname endgroup endinput endlinechar eqno errhelp "
            "errmessage errorcontextlines errorstopmode escapechar everycr "
            "everydisplay everyhbox everyjob everymath everypar everyvbox "
            "exhyphenpenalty expandafter fam fi finalhyphendemerits firstmark "
            "floatingpenalty font fontdimen fontname futurelet gdef global "
            "group globaldefs halign hangafter hangindent hbadness hbox hfil "
            "horizontal hfill horizontal hfilneg hfuzz hoffset holdinginserts "
            "hrule hsize hskip hss horizontal ht hyphenation hyphenchar "
            "hyphenpenalty hyphen if ifcase ifcat ifdim ifeof iffalse ifhbox "
            "ifhmode ifinner ifmmode ifnum ifodd iftrue ifvbox ifvmode ifvoid "
            "ifx ignorespaces immediate indent input inputlineno input insert "
            "insertpenalties interlinepenalty jobname kern language lastbox "
            "lastkern lastpenalty lastskip lccode leaders left lefthyphenmin "
            "leftskip leqno let limits linepenalty line lineskip "
            "lineskiplimit long looseness lower lowercase mag mark mathaccent "
            "mathbin mathchar mathchardef mathchoice mathclose mathcode "
            "mathinner mathop mathopen mathord mathpunct mathrel mathsurround "
            "maxdeadcycles maxdepth meaning medmuskip message mkern month "
            "moveleft moveright mskip multiply muskip muskipdef newlinechar "
            "noalign noboundary noexpand noindent nolimits nonscript "
            "scriptscript nonstopmode nulldelimiterspace nullfont number "
            "omit openin openout or outer output outputpenalty over "
            "overfullrule overline overwithdelims pagedepth pagefilllstretch "
            "pagefillstretch pagefilstretch pagegoal pageshrink pagestretch "
            "pagetotal par parfillskip parindent parshape parskip patterns "
            "pausing penalty postdisplaypenalty predisplaypenalty "
            "predisplaysize pretolerance prevdepth prevgraf radical raise "
            "read relax relpenalty right righthyphenmin rightskip "
            "romannumeral scriptfont scriptscriptfont scriptscriptstyle "
            "scriptspace scriptstyle scrollmode setbox setlanguage sfcode "
            "shipout show showbox showboxbreadth showboxdepth showlists "
            "showthe skewchar skip skipdef spacefactor spaceskip span special "
            "splitbotmark splitfirstmark splitmaxdepth splittopskip string "
            "tabskip textfont textstyle the thickmuskip thinmuskip time "
            "toks toksdef tolerance topmark topskip tracingcommands "
            "tracinglostchars tracingmacros tracingonline tracingoutput "
            "tracingpages tracingparagraphs tracingrestores tracingstats "
            "uccode uchyph underline unhbox unhcopy unkern unpenalty unskip "
            "unvbox unvcopy uppercase vadjust valign vbadness vbox vcenter "
            "vfil vfill vfilneg vfuzz voffset vrule vsize vskip vsplit vss "
            "vtop wd widowpenalty write xdef xleaders xspaceskip year"
        )
        etexKeywords = (
            "beginL beginR botmarks clubpenalties currentgrouplevel "
            "currentgrouptype currentifbranch currentiflevel currentiftype "
            "detokenize dimexpr displaywidowpenalties endL endR eTeXrevision "
            "eTeXversion everyeof firstmarks fontchardp fontcharht fontcharic "
            "fontcharwd glueexpr glueshrink glueshrinkorder gluestretch "
            "gluestretchorder gluetomu ifcsname ifdefined iffontchar "
            "interactionmode interactionmode interlinepenalties lastlinefit "
            "lastnodetype marks topmarks middle muexpr mutoglue numexpr "
            "pagediscards parshapedimen parshapeindent parshapelength "
            "predisplaydirection savinghyphcodes savingvdiscards scantokens "
            "showgroups showifs showtokens splitdiscards splitfirstmarks "
            "TeXXeTstate tracingassigns tracinggroups tracingifs "
            "tracingnesting tracingscantokens unexpanded unless widowpenalties"
        )
        pdftexKeywords = (
            "pdfadjustspacing pdfannot pdfavoidoverfull pdfcatalog "
            "pdfcompresslevel pdfdecimaldigits pdfdest pdfdestmargin "
            "pdfendlink pdfendthread pdffontattr pdffontexpand pdffontname "
            "pdffontobjnum pdffontsize pdfhorigin pdfimageresolution "
            "pdfincludechars pdfinfo pdflastannot pdflastdemerits pdflastobj "
            "pdflastvbreakpenalty pdflastxform pdflastximage "
            "pdflastximagepages pdflastxpos pdflastypos pdflinesnapx "
            "pdflinesnapy pdflinkmargin pdfliteral pdfmapfile pdfmaxpenalty "
            "pdfminpenalty pdfmovechars pdfnames pdfobj "
            "pdfoptionpdfminorversion pdfoutline pdfoutput pdfpageattr "
            "pdfpageheight pdfpageresources pdfpagesattr pdfpagewidth "
            "pdfpkresolution pdfprotrudechars pdfrefobj pdfrefxform "
            "pdfrefximage pdfsavepos pdfsnaprefpoint pdfsnapx pdfsnapy "
            "pdfstartlink pdfstartthread pdftexrevision pdftexversion "
            "pdfthread pdfthreadmargin pdfuniqueresname pdfvorigin pdfxform "
            "pdfximage"
        )
        omegaKeywords = (
            "odelimiter omathaccent omathchar oradical omathchardef omathcode "
            "odelcode leftghost rightghost charwd charht chardp charit "
            "localleftbox localrightbox localinterlinepenalty "
            "localbrokenpenalty pagedir bodydir pardir textdir mathdir boxdir "
            "nextfakemath pagewidth pageheight pagerightoffset "
            "pagebottomoffset nullocp nullocplist ocp externalocp ocplist "
            "pushocplist popocplist clearocplists ocptracelevel "
            "addbeforeocplist addafterocplist removebeforeocplist "
            "removeafterocplist OmegaVersion InputTranslation "
            "OutputTranslation DefaultInputTranslation "
            "DefaultOutputTranslation noInputTranslation noOutputTranslation "
            "InputMode OutputMode DefaultInputMode DefaultOutputMode "
            "noInputMode noOutputMode noDefaultInputMode noDefaultOutputMode"
        )
        macros = (
            "TeX bgroup egroup endgraf space empty null newcount newdimen "
            "newskip newmuskip newbox newtoks newhelp newread newwrite newfam "
            "newlanguage newinsert newif maxdimen magstephalf magstep "
            "frenchspacing nonfrenchspacing normalbaselines obeylines "
            "obeyspaces raggedright ttraggedright thinspace negthinspace "
            "enspace enskip quad qquad smallskip medskip bigskip "
            "removelastskip topglue vglue hglue break nobreak allowbreak "
            "filbreak goodbreak smallbreak medbreak bigbreak line leftline "
            "rightline centerline rlap llap underbar strutbox strut cases "
            "matrix pmatrix bordermatrix eqalign displaylines eqalignno "
            "leqalignno pageno folio tracingall showhyphens fmtname "
            "fmtversion hphantom vphantom phantom smash "
            "eTeX newmarks grouptype interactionmode nodetype iftype "
            "tracingall loggingall tracingnone"
        )
        if kwSet in (1, 2, 3, 4, 5, 6, 7):
            return (
                texKeywords
                + " "
                + etexKeywords
                + " "
                + pdftexKeywords
                + " "
                + omegaKeywords
                + " "
                + macros
            )

        if kwSet == 8:
            return texKeywords + " " + etexKeywords + " " + pdftexKeywords

        return None


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerTeX
    """
    return LexerTeX(parent=parent)
