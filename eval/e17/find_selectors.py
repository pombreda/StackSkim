#! /usr/bin/env python
# encoding: utf-8

from __future__ import unicode_literals
import logging
import os.path

import re
import ast
import cssselect
from cssselect.parser import Element, SelectorSyntaxError
from bs4 import BeautifulSoup as Soup


logging.basicConfig(level=logging.INFO, format="%(message)s")
TUTORIAL_DIR = 'tutorials'
''' We include None in this list because patterns that match all tags
    (e.g. ".klazz") yield an Element with property 'element' == None. '''
HTML_TAGS = ['a', 'abbr', 'address', 'area', 'article', 'aside', 
    'audio', 'b', 'base', 'bb', 'bdo', 'blockquote', 'body', 
    'br', 'button', 'canvas', 'caption', 'cite', 'code', 'col', 
    'colgroup', 'command', 'datagrid', 'datalist', 'dd', 'del', 
    'details', 'dfn', 'dialog', 'div', 'dl', 'dt', 'em', 'embed', 
    'fieldset', 'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 
    'h5', 'h6', 'head', 'header', 'hr', 'html', 'i', 'iframe', 'img', 
    'input', 'ins', 'kbd', 'label', 'legend', 'li', 'link', 'map', 
    'mark', 'menu', 'meta', 'meter', 'nav', 'noscript', 'object', 'ol', 
    'optgroup', 'option', 'output', 'p', 'param', 'pre', 'progress', 
    'q', 'rp', 'rt', 'ruby', 'samp', 'script', 'section', 'select', 
    'small', 'source', 'span', 'strong', 'style', 'sub', 'sup', 
    'table', 'tbody', 'td', 'textarea', 'tfoot', 'th', 'thead', 
    'time', 'title', 'tr', 'ul', 'var', 'video', None,
]
CSS_METHODS = ['CSSSelector', 'cssselect', 'select']


class CallVisitor(ast.NodeVisitor):
    ''' AST Visitor that saves all function calls. '''

    def __init__(self, *args, **kwargs):
        self.calls = []
        super(CallVisitor, self).__init__(*args, **kwargs)

    def visit_Call(self, node):
        self.calls.append(node)
        self.generic_visit(node)


class StringVisitor(ast.NodeVisitor):
    ''' AST Visitor that collects all strings in the code. '''

    def __init__(self, *args, **kwargs):
        self.strings = []
        super(StringVisitor, self).__init__(*args, **kwargs)

    def visit_Str(self, node):
        self.strings.append(node.s)


def get_descendants(x):
    ''' Get all descendants of an object. '''
    if isinstance(x, list):
        return [i for el in x for i in get_descendants(el)]
    elif hasattr(x, '__dict__'):
        return [x] + [i for child in x.__dict__.values() for i in get_descendants(child)]
    elif isinstance(x, dict):
        return [i for child in x for i in get_descendants(child)]
    else:
        return []


def is_selector(string):
    ''' Check to see if string represents valid HTML selector. '''
    try:
        ''' cssselect doesn't play well with links, so we replace them for now. '''
        string = re.sub(r"(href.=)([^\]]*)\]", r"\1fakelink]", string)
        tree = cssselect.parse(string)
        selector_parts = get_descendants(tree)
        for part in selector_parts:
            if isinstance(part, Element):
                if part.element not in HTML_TAGS:
                    return False
        return True
    except SelectorSyntaxError:
        return False


class SelectorExtractor(object):
    ''' Class with routines to extract CSS selectors. '''

    def _code_to_ast(self, code):
        success = None
        try:
            return ast.parse(code)
        except SyntaxError:
            logging.debug("Invalid code section: %s", code)
            return None

    def get_selectors_by_ast_strings(self, code):
        selectors = []
        tree = self._code_to_ast(code)
        if tree:
            visitor = StringVisitor()
            visitor.visit(tree)
            strings = visitor.strings
            selectors = [s for s in visitor.strings if is_selector(s)]
        return selectors

    def get_selectors_by_ast_functions(self, code):
        selectors = []
        tree = self._code_to_ast(code)
        if tree:
            visitor = CallVisitor()
            visitor.visit(tree)
            for call in visitor.calls:
                name = None
                if isinstance(call.func, ast.Name):
                    name = call.func.id
                elif isinstance(call.func, ast.Attribute):
                    name = call.func.attr
                if name in CSS_METHODS and len(call.args):
                    selectors.append(call.args[0].s)
        return selectors

    def get_selectors_by_regex_functions(self, code):
        selectors = []
        FUNC_REGEX = '(' + "|".join(CSS_METHODS) + ')'
        for line in code.split('\n'):
            res = re.search(FUNC_REGEX + "\(('|\")(.*?)('|\"),?", line)
            if res:
                selectors.append(res.group(3))
        return selectors


def match_strings(body):
    ''' Find and print all strings that appear to be CSS in an HTML doc. '''

    # Iterate over all code snippets
    soup = Soup(body)
    extractor = SelectorExtractor()
    for code_section in soup.select('code'):

        # Strip command prompt symbols out of example code
        code_text = re.sub('^(>>> )|(\.\.\. )', '', code_section.text)
        selectors1 = extractor.get_selectors_by_ast_functions(code_text)
        selectors2 = extractor.get_selectors_by_regex_functions(code_text)
        selectors3 = extractor.get_selectors_by_ast_strings(code_text)
        if selectors1 or selectors2 or selectors3:
            logging.info("Method 1: %s", selectors1)
            logging.info("Method 2: %s", selectors2)
            logging.info("Method 3: %s", selectors3)


def main():
    for fn in os.listdir(TUTORIAL_DIR):
        if fn.split('.')[-1] == 'html':
            with open(os.path.join(TUTORIAL_DIR, fn)) as doc:
                match_strings(doc.read())


if __name__ == '__main__':
    main()
