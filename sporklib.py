#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Spork
-----

A "little language" designed to facilitate the extraction and processing of
data held in XML or HTML files.

:copyright: (c) 2015 Grapeshot Ltd
:author: S Arrowsmith <sion.arrowsmith@gmail.com>
:licence: MIT, see LICENSE for more details
"""
from __future__ import print_function

import sys
import os
import json

if sys.version_info[0] > 2:
    from io import StringIO
else:
    from StringIO import StringIO
from string import Template
from collections import defaultdict
try:
    from importlib import import_module
except ImportError:
    import_module = __import__
try:
    from argparse import ArgumentParser
except ImportError:
    ArgumentParser = object

import tinycss
import cssselect
from lxml import etree

class AttributeMapping(dict):
    def __init__(self, element):
        self.element = element
        self.parent = None
    def __missing__(self, key):
        if self.element is None:
            return "''"
        value = None
        if key.startswith("_"):
            if key == '_TEXT': value = " ".join(self.element.itertext())
            elif key == '_TAG': value = self.element.tag
            elif key == '_XML': value = etree.tostring(self.element)
        else:
            value = self.element.get(key, None)
        if value is None:
            if self.parent is None:
                self.parent = AttributeMapping(self.element.getparent())
            value = self.parent[key]
        else:
            value = repr(value)
        self[key] = value
        return value

class Spork:
    """A Spork object represents one spork script"""
    class FlowControl(Exception):
        pass
    class DEFAULT(FlowControl, StopIteration):
        pass
    class PROGRAM(FlowControl):
        pass
    class ELEMENT(FlowControl):
        pass
    class SELECTOR(FlowControl):
        pass
    def __init__(self, source, warn=False, debug=False, formats=["XML", "HTML"]):
        """Initialise this object from the script given by the file-like object "source"."""
        if not source.readline().startswith("#!"):
            source.seek(0)
        self.warn = warn
        self.debug = debug
        self.translator = cssselect.GenericTranslator()
        self.namespace = globals().copy()
        self.namespace["self"] = self
        self.xmlns = dict()
        self.parse(source)
        self.formats = formats
        self.doccument = None

    def parse(self, source):
        self.rules = list()
        parsed = tinycss.make_parser().parse_stylesheet_file(source)
        if self.warn:
            if parsed.errors:
                for error in parsed.errors:
                    print(error, file=sys.stderr)
                return
        for rule in parsed.rules:
            if rule.at_keyword:
                if rule.at_keyword != '@import':
                    if self.warn:
                        print("Unknown at-rule: %s" % rule.at_keyword, file=sys.stderr)
                        return
                    continue
                self.namespace[rule.uri] = import_module(rule.uri)
            else:
                css = rule.selector.as_css()
                if css == '_':
                    xpath = None
                else:
                    xpath = self.translator.css_to_xpath(css)
            self.rules.append((xpath, rule.declarations))

    def eval(self, name, value, namespace, attribs):
        result = None
        copy = False
        if value in namespace:
            return namespace[value][:], True
        value = value.replace("[]", "[-1]")
        if name != "_":
            if name in namespace and "#" in value:
                value = "[ (%s) for __%s__ in %s ]" % (value.replace("#", "__%s__"%name), name, name)
                copy = True
            elif value.endswith("[:]"):
                copy = True
        if attribs.element is not None:
            value = Template(value).safe_substitute(attribs)
        if self.debug:
            print("++ %s <- %s" % (name, value))
        return eval(value, self.namespace, namespace), copy

    def process(self, element, declarations, namespace):
        namespace['_'] = element
        attribs = AttributeMapping(element)
        if self.debug:
            print("+expressions")
        for declaration in declarations:
            name = declaration.name
            if element is not None and name == "_":
                name = element.tag
                if name.startswith("{"):
                    name = name[name.find("}")+1:]
                name = name.replace("-", "_")
            value = declaration.value.as_css().strip(";").strip()
            result, copy = self.eval(name, value, namespace, attribs)
            if name != "_":
                if copy:
                    namespace[name] = result
                else:
                    namespace.setdefault(name, []).append(result)

    def run_element(self, document):
        namespace = {"[]": [], "__": document}
        for xpath, declarations in self.rules:
            try:
                if xpath is None:
                    self.process(None, declarations, namespace)
                else:
                    if self.debug:
                        print("+xpath\n++", xpath)
                    for element in document.xpath(xpath, namespaces=self.xmlns):
                        self.process(element, declarations, namespace)
            except Spork.SELECTOR:
                pass
        if self.debug:
            print("+namespace")
            for n in sorted(namespace):
                if not n.startswith("__"):
                    print("++ %s\t=> %s" % (n, namespace[n]))
        if "_" in namespace: del namespace["_"]
        del namespace["[]"]; del namespace["__"]
        return namespace

    def run(self, document=None):
        """Run this script over the given document root element
        If document is None, use the last document returned by get_root().
        Returns the final state of the spork variables."""
        if document is None:
            document = self.document
        try:
            return self.run_element(document)
        except Spork.FlowControl:
            pass
        return {}

    def selector(self, selector, document=None):
        """Generator to run this script over all elements in the given document identified by selector.
        If document is None, use the last document returned by get_root().
        Yields tuples of (selected_element, spork_variables)."""
        if document is None:
            document = self.document
        xpath = self.translator.css_to_xpath(selector)
        for element in document.xpath(xpath):
            try:
                yield ((element, self.run_element(element)))
            except Spork.ELEMENT:
                pass
            except Spork.PROGRAM:
                break

    def select(self, selector, document=None):
        """Convenience function to return result of selector() as a list"""
        return list(self.selector(selector, document))

    def get_root(self, document, parserargs={}):
        """Return the root element of the given document, and remember it for subsequent calls to select()."""
        for name in self.formats:
            parser = getattr(etree, name+"Parser")(**parserargs)
            try:
                root = etree.parse(document, parser).getroot()
                if root is None:
                    continue
                if name == "HTML":
                    self.translator = cssselect.HTMLTranslator()
                    self.xmlns = dict()
                else:
                    self.xmlns = root.nsmap
                self.document = root
                return root
            except etree.ParseError as e:
                document.seek(0)
                pass
        # *Theoretically* we can get here with no exception if a document parses but getroot() returns None
        raise

    def exit(self, how=DEFAULT):
        if not issubclass(how, Spork.FlowControl):
            return
        raise how()

def parse_args(args):
    """Parse arguments passed when sporklib is used as a script"""
    parser = ArgumentParser(prog="spork", description="Spork is a mark-up scanning and processing language")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-f", "--file", metavar="progfile", dest="source", type=file, help="filename of Spork program")
    source.add_argument("-e", "--source", metavar="program-text", dest="source", type=StringIO, help="text of Spork program")
    parser.add_argument("-w", "--warn", action='store_true', help="warn of program parsing errors")
    parser.add_argument("file", nargs='?', type=file, default=sys.stdin, help="document to be processed (default stdin)")
    parser.add_argument("-X", "--xml", action='store_true', help="attempt XML parsing of document")
    parser.add_argument("-H", "--html", action='store_true', help="attempt HTML parsing of document")
    parser.add_argument("-s", "--select", metavar="tag", help="process selected elements from document")
    parser.add_argument("-p", "--print", action='store_true', help="print result(s)")
    parser.add_argument("-d", "--debug", action='store_true', help="display debugging information")
    parseropts = parser.add_argument_group(title="Document parser options", description="These options only apply if -X/--xml or -H/--html are given.")
    parseropts.add_argument("--attribute-defaults", action='store_true', help="read the DTD (if referenced by the document) and add the default attributes from it")
    parseropts.add_argument("--dtd-validation", action='store_true', help="validate while parsing (if a DTD was referenced)")
    parseropts.add_argument("--allow-network", action='store_true', help="allow network access when looking up external documents")
    parseropts.add_argument("--recover", action='store_true', help="try hard to parse through broken XML")
    parseropts.add_argument("--remove-blank-text", action='store_true', help="discard blank text nodes (ignorable whitespace) between tags")
    parseropts.add_argument("--leave-cdata", action='store_true', help="don't replace CDATA sections by normal text content")
    parseropts.add_argument("--leave-entities", action='store_true', help="don't replace entities by their text value")
    parseropts.add_argument("--forget-ids", action='store_true', help="don't collect XML IDs (can speed up parsing if IDs not used)")
    parseropts.add_argument("--huge-tree", action='store_true', help="support deep trees and very long text content. WARNING: disables security restrictions")
    return parser.parse_args(args)

def get_parserargs(args):
    """Convert command line arguments to lxml parser arguments"""
    parserlist = list()
    kwargs = dict()
    va = vars(args)
    for arg in ('attribute_defaults', 'dtd_validation', 'recover', 'remove_blank_text', 'huge_tree'):
        if va[arg]:
            kwargs[arg] = True
    for (arg, kwarg) in (('allow_network', 'no_network'), ('leave_cdata', 'strip_cdata'), ('leave_entities', 'resolve_entities'), ('forget_ids', 'collect_ids')):
        if va[arg]:
            kwargs[kwarg] = False
    return kwargs

def main(args=sys.argv[1:]):
    """Entry point for using sporklib as a script"""
    args = parse_args(args)
    prog = Spork(args.source, args.warn, args.debug)
    if args.xml:
        prog.formats = ["XML"]
    if args.html:
        prog.formats = ["HTML"]
    root = prog.get_root(args.file, get_parserargs(args))
    if args.select:
        results = [ r[1] for r in prog.selector(args.select, root) ]
    else:
        results = [ prog.run(root) ]
    if args.print:
        json.dump(results, sys.stdout, indent=2)
        print()

if __name__ == '__main__':
    main()
