#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.model import ModelView, ModelSQL, fields
from trytond.model.cacheable import Cacheable
from trytond.wizard import Wizard
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.tools import file_open

from difflib import SequenceMatcher
from xml import dom
import copy
import os
import re


class Translation(ModelSQL, ModelView, Cacheable):
    _name = 'ir.translation'

    def __init__(self):
    	super(Translation, self).__init__()
        new_type = ('jasper', 'Jasper Report')
        if new_type not in self.type.selection:
            self.type = copy.copy(self.type)
            self.type.selection = copy.copy(self.type.selection)
            self.type.selection.append(new_type)
            self._reset_columns()

Translation()


class ReportTranslationSet(Wizard):
    _name = "ir.translation.set_report"

    def _translate_jasper_report(self, node):
        strings = []

        if node.nodeType in (node.CDATA_SECTION_NODE, node.TEXT_NODE):
            if not (node.parentNode and
                    node.parentNode.tagName.endswith('Expression')):
                return []

            if node.nodeValue:
                #re.findall('tr *\([^\(]*,"([^"]*)"\)', 'tr($V{L},"hola manola") + tr($V{L},"adeu andreu")')
                node_strings = re.findall('tr *\([^\(]*,"([^"]*)"\)', node.nodeValue)
                strings += [x for x in node_strings if x]

        for child in [x for x in node.childNodes]:
            strings.extend(self._translate_jasper_report(child))
        return strings

    def _set_report_translation(self, data):
        result = super(ReportTranslationSet, self)._set_report_translation(data)

        pool = Pool()
        report_obj = pool.get('ir.action.report')
        translation_obj = pool.get('ir.translation')

        with Transaction().set_context(active_test=False):
            report_ids = report_obj.search([('report','ilike','%.jrxml')])

        if not report_ids:
            return {}

        reports = report_obj.browse(report_ids)
        cursor = Transaction().cursor
        for report in reports:
            strings = []

            odt_content = ''
            if report.report:
                with file_open(report.report.replace('/', os.sep),
                        mode='rb') as fp:
                    jasper_content = fp.read()
            for content in (report.report_content_custom, jasper_content):
                if not content:
                    continue
                document = dom.minidom.parseString(content)
                strings = self._translate_jasper_report(document)
            self._store_report_strings(report, strings, 'jasper')
        return result

ReportTranslationSet()

