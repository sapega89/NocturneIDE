# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing the safe browsing functionality.
"""


def SafeBrowsingHelp():
    """
    Module function to get some help about how to enable the Google Mail
    OAuth2 service.

    @return help text
    @rtype str
    """
    return (
        "<h2>Steps to get a Google Safe Browsing API key</h2>"
        "<p>In order to use Google Safe Browsing you need a Google Account,"
        " a Google Developer Console project, and an API key. You also need"
        " to activate the Safe Browsing APIs for use with your project.</p>"
        "<ol>"
        "<li>Google Account<br/>You need a Google Account in order to create"
        " a project. If you don't already have an account, sign up at"
        " <a href='https://accounts.google.com/SignUp'>Create your Google"
        " Account</a>.</li>"
        "<li>Developer Console Project<br/>You need a Google Developer Console"
        " project in order to create an API key. If you don't already have a"
        " project, see"
        " <a href='https://support.google.com/cloud/answer/6251787?hl=en'>"
        "Create, shut down, and restore projects</a>.</li>"
        "<li>API Key<br/>You need an API key to access the Safe Browsing APIs."
        " An API key authenticates you as an API user and allows you to"
        " interact with the APIs. To set up an API key, see "
        "<a href='https://support.google.com/cloud/answer/6158862"
        "?hl=en&ref_topic=6262490'>Setting up API keys</a>. Your new API key"
        " appears in a table. Copy and paste this key into the line edit above"
        " the button used to show this help.</li>"
        "<li>Activate the API<br/>Finally, you need to activate the Safe"
        " Browsing API for use with your project. To learn how to do this, see"
        " <a href='https://support.google.com/cloud/answer/6158841?hl=en'>"
        "Activate and deactivate APIs</a>. The API to enable is referred to as"
        " &quot;Google Safe Browsing API&quot;.</li>"
        "</ol>"
    )
