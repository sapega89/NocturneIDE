# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module containing function to generate JavaScript code.
"""

#
# This code was ported from QupZilla.
# Copyright (C) David Rosca <nowrep@gmail.com>
#

from PyQt6.QtCore import QUrl, QUrlQuery

from .WebBrowserTools import getJavascript


def setupWebChannel(worldId):
    """
    Function generating  a script to setup the web channel.

    @param worldId world ID for which to setup the channel
    @type int
    @return script to setup the web channel
    @rtype str
    """
    source = """
// ==UserScript==
{0}
// ==/UserScript==

(function() {{
    {1}
    
    function registerExternal(e) {{
        window.external = e;
        if (window.external) {{
            var event = document.createEvent('Event');
            event.initEvent('_eric_external_created', true, true);
            window._eric_external = true;
            document.dispatchEvent(event);
        }}
    }}
    
    if (self !== top) {{
        if (top._eric_external)
            registerExternal(top.external);
        else
            top.document.addEventListener(
                '_eric_external_created', function() {{
                    registerExternal(top.external);
            }});
        return;
    }}

    function registerWebChannel() {{
        try {{
           new QWebChannel(qt.webChannelTransport, function(channel) {{
                var external = channel.objects.eric_object;
                external.extra = {{}};
                for (var key in channel.objects) {{
                    if (key != 'eric_object' && key.startsWith('eric_')) {{
                        external.extra[key.substr(5)] = channel.objects[key];
                    }}
                }}
                registerExternal(external);
           }});
        }} catch (e) {{
            setTimeout(registerWebChannel, 100);
        }}
    }}
    registerWebChannel();

}})()"""

    from eric7.WebBrowser.WebBrowserPage import (  # __IGNORE_WARNING_I101__
        WebBrowserPage,
    )

    match = (
        "// @exclude eric:*"
        if worldId == WebBrowserPage.SafeJsWorld
        else "// @include eric:*"
    )
    return source.format(match, getJavascript("qwebchannel.js"))


def setupWindowObject():
    """
    Function generating a script to setup window.object add-ons.

    @return generated script
    @rtype str
    """
    source = """
(function() {
    var external = {};
    external.AddSearchProvider = function(url) {
        window.location = 'eric:AddSearchProvider?url=' + url;
    };
    external.IsSearchProviderInstalled = function(url) {
        console.warn('NOT IMPLEMENTED: IsSearchProviderInstalled()');
        return false;
    };
    window.external = external;
    window.print = function() {
        window.location = 'eric:PrintPage';
    };
})()"""

    return source


def setStyleSheet(css):
    """
    Function generating a script to set a user style sheet.

    @param css style sheet to be applied
    @type str
    @return script to set a user style sheet
    @rtype str
    """
    source = """
(function() {{
    var css = document.createElement('style');
    css.setAttribute('type', 'text/css');
    css.appendChild(document.createTextNode('{0}'));
    document.getElementsByTagName('head')[0].appendChild(css);
}})()"""

    style = css.replace("'", "\\'").replace("\n", "\\n")
    return source.format(style)


def getFormData(pos):
    """
    Function generating a script to extract data for a form element.

    @param pos position to extract data at
    @type QPoint
    @return script to extract form data
    @rtype str
    """
    source = """
(function() {{
    var e = document.elementFromPoint({0}, {1});
    if (!e || e.tagName.toLowerCase() != 'input')
        return;
    var fe = e.parentElement;
    while (fe) {{
        if (fe.tagName.toLowerCase() != 'form')
            break;
        fe = fe.parentElement;
    }}
    if (!fe)
        return;
    var res = {{
        method: fe.method.toLowerCase(),
        action: fe.action,
        inputName: e.name,
        inputs: [],
    }};
    for (var i = 0; i < fe.length; ++i) {{
        var input = fe.elements[i];
        res.inputs.push([input.name, input.value]);
    }}
    return res;
}})()"""
    return source.format(pos.x(), pos.y())


def getAllImages():
    """
    Function generating a script to extract all image tags of a web page.

    @return script to extract image tags
    @rtype str
    """
    source = """
(function() {
    var out = [];
    var imgs = document.getElementsByTagName('img');
    for (var i = 0; i < imgs.length; ++i) {
        var e = imgs[i];
        out.push({
            src: e.src,
            alt: e.alt
        });
    }
    return out;
})()"""
    return source


def getAllMetaAttributes():
    """
    Function generating a script to extract all meta attributes of a web page.

    @return script to extract meta attributes
    @rtype str
    """
    source = """
(function() {
    var out = [];
    var meta = document.getElementsByTagName('meta');
    for (var i = 0; i < meta.length; ++i) {
        var e = meta[i];
        out.push({
            name: e.getAttribute('name'),
            content: e.getAttribute('content'),
            httpequiv: e.getAttribute('http-equiv'),
            charset: e.getAttribute('charset')
        });
    }
    return out;
})()"""
    return source


def getOpenSearchLinks():
    """
    Function generating a script to extract all open search links.

    @return script to extract all open serach links
    @rtype str
    """
    source = """
(function() {
    var out = [];
    var links = document.getElementsByTagName('link');
    for (var i = 0; i < links.length; ++i) {
        var e = links[i];
        if (e.type == 'application/opensearchdescription+xml') {
            out.push({
                url: e.getAttribute('href'),
                title: e.getAttribute('title')
            });
        }
    }
    return out;
})()"""
    return source


def sendPostData(url, data):
    """
    Function generating a script to send Post data.

    @param url URL to send the data to
    @type QUrl
    @param data data to be sent
    @type QByteArray
    @return script to send Post data
    @rtype str
    """
    source = """
(function() {{
    var form = document.createElement('form');
    form.setAttribute('method', 'POST');
    form.setAttribute('action', '{0}');
    var val;
    {1}
    form.submit();
}})()"""

    valueSource = """
val = document.createElement('input');
val.setAttribute('type', 'hidden');
val.setAttribute('name', '{0}');
val.setAttribute('value', '{1}');
form.appendChild(val);"""

    values = ""
    query = QUrlQuery(data)
    for name, value in query.queryItems(QUrl.ComponentFormattingOption.FullyDecoded):
        value = value.replace("'", "\\'")
        name = name.replace("'", "\\'")
        values += valueSource.format(name, value)

    return source.format(url.toString(), values)


def setupFormObserver():
    """
    Function generating a script to monitor a web form for user entries.

    @return script to monitor a web page
    @rtype str
    """
    source = """
(function() {
    function findUsername(inputs) {
        var usernameNames = ['user', 'name', 'login'];
        for (var i = 0; i < usernameNames.length; ++i) {
            for (var j = 0; j < inputs.length; ++j)
                if (inputs[j].type == 'text' &&
                    inputs[j].value.length &&
                    inputs[j].name.indexOf(usernameNames[i]) != -1)
                    return inputs[j].value;
        }
        for (var i = 0; i < inputs.length; ++i)
            if (inputs[i].type == 'text' && inputs[i].value.length)
                return inputs[i].value;
        for (var i = 0; i < inputs.length; ++i)
            if (inputs[i].type == 'email' && inputs[i].value.length)
                return inputs[i].value;
        return '';
    }
    
    function registerForm(form) {
        form.addEventListener('submit', function() {
            var form = this;
            var data = '';
            var password = '';
            var inputs = form.getElementsByTagName('input');
            for (var i = 0; i < inputs.length; ++i) {
                var input = inputs[i];
                var type = input.type.toLowerCase();
                if (type != 'text' && type != 'password' &&
                    type != 'email')
                    continue;
                if (!password && type == 'password')
                    password = input.value;
                data += encodeURIComponent(input.name);
                data += '=';
                data += encodeURIComponent(input.value);
                data += '&';
            }
            if (!password)
                return;
            data = data.substring(0, data.length - 1);
            var url = window.location.href;
            var username = findUsername(inputs);
            external.passwordManager.formSubmitted(
                url, username, password, data);
        }, true);
    }
    
    for (var i = 0; i < document.forms.length; ++i)
        registerForm(document.forms[i]);
    
    var observer = new MutationObserver(function(mutations) {
        for (var mutation of mutations)
            for (var node of mutation.addedNodes)
                if (node.tagName && node.tagName.toLowerCase() == 'form')
                    registerForm(node);
    });
    observer.observe(document.documentElement, {
        childList: true, subtree: true
    });
    
})()"""
    return source


def completeFormData(data):
    """
    Function generating a script to fill in form data.

    @param data data to be filled into the form
    @type QByteArray
    @return script to fill a form
    @rtype str
    """
    source = """
(function() {{
    var data = '{0}'.split('&');
    var inputs = document.getElementsByTagName('input');
    
    for (var i = 0; i < data.length; ++i) {{
        var pair = data[i].split('=');
        if (pair.length != 2)
            continue;
        var key = decodeURIComponent(pair[0]);
        var val = decodeURIComponent(pair[1]);
        for (var j = 0; j < inputs.length; ++j) {{
            var input = inputs[j];
            var type = input.type.toLowerCase();
            if (type != 'text' && type != 'password' &&
                type != 'email')
                continue;
            if (input.name == key) {{
                input.value = val;
                input.dispatchEvent(new Event('change'));
            }}
        }}
    }}
    
}})()"""

    data = bytes(data).decode("utf-8")
    data = data.replace("'", "\\'")
    return source.format(data)


def setCss(css):
    """
    Function generating a script to set a given CSS style sheet.

    @param css style sheet
    @type str
    @return script to set the style sheet
    @rtype str
    """
    source = """
(function() {{
    var css = document.createElement('style');
    css.setAttribute('type', 'text/css');
    css.appendChild(document.createTextNode('{0}'));
    document.getElementsByTagName('head')[0].appendChild(css);
    }})()"""
    style = css.replace("'", "\\'").replace("\n", "\\n")
    return source.format(style)


def scrollToAnchor(anchor):
    """
    Function generating script to scroll to a given anchor.

    @param anchor name of the anchor to scroll to
    @type str
    @return script to set the style sheet
    @rtype str
    """
    source = """
(function() {{
    var e = document.getElementById("{0}")
    if (!e) {{
        var els = document.querySelectorAll("[name='{0}']");
        if (els.length)
            e = els[0]
    }}
    if (e)
        e.scrollIntoView()
    }})()"""
    return source.format(anchor)


###########################################################################
## scripts below are specific for eric
###########################################################################


def getFeedLinks():
    """
    Function generating a script to extract all RSS and Atom feed links.

    @return script to extract all RSS and Atom feed links
    @rtype str
    """
    source = """
(function() {
    var out = [];
    var links = document.getElementsByTagName('link');
    for (var i = 0; i < links.length; ++i) {
        var e = links[i];
        if ((e.rel == 'alternate') &&
            ((e.type == 'application/atom+xml') ||
             (e.type == 'application/rss+xml')
            )
           ) {
            out.push({
                url: e.getAttribute('href'),
                title: e.getAttribute('title')
            });
        }
    }
    return out;
})()"""
    return source
