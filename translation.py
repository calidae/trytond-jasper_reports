#This file is part jasper_reports module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from xml import dom
import copy
import os
import re
import polib
import contextlib

from trytond.model import ModelView, ModelSQL
from trytond.wizard import Wizard
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.tools import file_open
from difflib import SequenceMatcher

__all__ = [
    'Translation',
    'ReportTranslationSet',
    'TranslationUpdate',
    'TranslationClean',
    ]


class Translation(ModelSQL, ModelView):
    __name__ = 'ir.translation'

    @classmethod
    def __setup__(cls):
        super(Translation, cls).__setup__()
        new_type = ('jasper', 'Jasper Report')
        if new_type not in cls.type.selection:
            cls.type = copy.copy(cls.type)
            cls.type.selection = copy.copy(cls.type.selection)
            cls.type.selection.append(new_type)

    @classmethod
    def translation_import(cls, lang, module, po_path):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        models_data = ModelData.search([
                ('module', '=', module),
                ])
        fs_id2model_data = {}
        for model_data in models_data:
            fs_id2model_data.setdefault(model_data.model, {})
            fs_id2model_data[model_data.model][model_data.fs_id] = model_data

        translations = set()
        to_create = []
        pofile = polib.pofile(po_path)

        id2translation = {}
        key2ids = {}
        module_translations = cls.search([
            ('lang', '=', lang),
            ('module', '=', module),
            ])
        for translation in module_translations:
            if translation.type in ('odt', 'view', 'wizard_button',
                    'selection', 'error', 'jasper'):
                key = (translation.name, translation.res_id, translation.type,
                        translation.src)
            elif translation.type in ('field', 'model', 'help'):
                key = (translation.name, translation.res_id, translation.type)
            else:
                raise Exception('Unknow translation type: %s'
                    % translation.type)
            key2ids.setdefault(key, []).append(translation.id)
            id2translation[translation.id] = translation

        for entry in pofile:
            ttype, name, res_id = entry.msgctxt.split(':')
            src = entry.msgid
            value = entry.msgstr
            fuzzy = 'fuzzy' in entry.flags
            noupdate = False

            model = name.split(',')[0]
            if model in fs_id2model_data and res_id in fs_id2model_data[model]:
                model_data = fs_id2model_data[model][res_id]
                res_id = model_data.db_id
                noupdate = model_data.noupdate

            if res_id:
                try:
                    res_id = int(res_id)
                except ValueError:
                    continue
            if not res_id:
                res_id = None

            if ttype in ('odt', 'view', 'wizard_button', 'selection', 'error',
                    'jasper'):
                key = (name, res_id, ttype, src)
            elif ttype in('field', 'model', 'help'):
                key = (name, res_id, ttype)
            else:
                raise Exception('Unknow translation type: %s' % ttype)
            ids = key2ids.get(key, [])

            with contextlib.nested(Transaction().set_user(0),
                    Transaction().set_context(module=module)):
                if not ids:
                    to_create.append({
                        'name': name,
                        'res_id': res_id,
                        'lang': lang,
                        'type': ttype,
                        'src': src,
                        'value': value,
                        'fuzzy': fuzzy,
                        'module': module,
                        })
                else:
                    translations2 = []
                    for translation_id in ids:
                        translation = id2translation[translation_id]
                        if translation.value != value \
                                or translation.fuzzy != fuzzy:
                            translations2.append(translation)
                    if translations2 and not noupdate:
                        cls.write(translations2, {
                            'value': value,
                            'fuzzy': fuzzy,
                            })
                    translations |= set(cls.browse(ids))

        if to_create:
            translations |= set(cls.create(to_create))

        if translations:
            all_translations = set(cls.search([
                        ('module', '=', module),
                        ('lang', '=', lang),
                        ]))
            translations_to_delete = all_translations - translations
            cls.delete(list(translations_to_delete))
        return len(translations)


class ReportTranslationSet(Wizard):
    __name__ = "ir.translation.set_report"

    def _translate_jasper_report(self, node):
        strings = []
        if node.nodeType in (node.CDATA_SECTION_NODE, node.TEXT_NODE):
            if not (node.parentNode and
                    node.parentNode.tagName.endswith('Expression')):
                return []
            if node.nodeValue:
                #re.findall('tr *\([^\(]*,"([^"]*)"\)', 'tr($V{L},"hola manola") + tr($V{L},"adeu andreu")')
                node_strings = re.findall('tr *\([^\(]*,"([^"]*)"\)',
                node.nodeValue)
                strings += [x for x in node_strings if x]

        for child in [x for x in node.childNodes]:
            strings.extend(self._translate_jasper_report(child))
        return strings

    def _store_report_strings(self, report, strings, type_):
        Translation = Pool().get('ir.translation')
        cursor = Transaction().cursor

        cursor.execute('SELECT id, name, src FROM ir_translation '
            'WHERE lang = %s '
                'AND type = %s '
                'AND name = %s '
                'AND module = %s',
            ('en_US', type_, report.report_name, report.module or ''))
        trans_reports = {}
        for trans in cursor.dictfetchall():
            trans_reports[trans['src']] = trans
        for string in {}.fromkeys(strings).keys():
            src_md5 = Translation.get_src_md5(string)
            done = False
            if string in trans_reports:
                del trans_reports[string]
                continue
            for string_trans in trans_reports:
                if string_trans in strings:
                    continue
                seqmatch = SequenceMatcher(lambda x: x == ' ',
                        string, string_trans)
                if seqmatch.ratio() == 1.0:
                    del trans_reports[report.report_name][string_trans]
                    done = True
                    break
                if seqmatch.ratio() > 0.6:
                    cursor.execute('UPDATE ir_translation '
                            'SET src = %s, '
                                'fuzzy = %s, '
                                'src_md5 = %s '
                            'WHERE name = %s '
                                'AND type = %s '
                                'AND src = %s '
                                'AND module = %s',
                            (string, True, src_md5, report.report_name,
                                type_, string_trans, report.module))
                    del trans_reports[string_trans]
                    done = True
                    break
            if not done:
                cursor.execute('INSERT INTO ir_translation '
                        '(name, lang, type, src, value, module, fuzzy, '
                         'src_md5)'
                        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                        (report.report_name, 'en_US', type_, string, '',
                            report.module, False, src_md5))
        if strings:
            cursor.execute('DELETE FROM ir_translation '
                    'WHERE name = %s '
                        'AND type = %s '
                        'AND module = %s '
                        'AND src NOT IN '
                            '(' + ','.join(('%s',) * len(strings)) + ')', (
                                report.report_name,
                                type_,
                                report.module
                                ) + tuple(strings))

    def transition_set_report(self):
        pool = Pool()
        Report = pool.get('ir.action.report')

        result = super(ReportTranslationSet, self).transition_set_report()

        with Transaction().set_context(active_test=False):
            reports = Report.search([('report', 'ilike', '%.jrxml')])

        if not reports:
            return {}

        for report in reports:
            strings = []

            # odt_content = ''
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


class TranslationUpdate(Wizard):
    __name__ = "ir.translation.update"

    def do_update(self, action):
        pool = Pool()
        Translation = pool.get('ir.translation')

        cursor = Transaction().cursor
        lang = self.start.language.code
        cursor.execute("SELECT name, res_id, type, src, module "
            "FROM ir_translation "
            "WHERE lang = 'en_US' "
                "AND type = 'jasper' "
            "EXCEPT SELECT name, res_id, type, src, module "
            "FROM ir_translation "
            "WHERE lang=%s "
                "AND type = 'jasper'",
            (lang,))
        for row in cursor.dictfetchall():
            with Transaction().set_user(0):
                Translation.create([{
                    'name': row['name'],
                    'res_id': row['res_id'],
                    'lang': lang,
                    'type': row['type'],
                    'src': row['src'],
                    'module': row['module'],
                    }])
        return super(TranslationUpdate, self).do_update(action)


class TranslationClean(Wizard):
    "Clean translation"
    __name__ = 'ir.translation.clean'

    @staticmethod
    def _clean_jasper(translation):
        pool = Pool()
        Report = pool.get('ir.action.report')
        with Transaction().set_context(active_test=False):
            if not Report.search([
                        ('report_name', '=', translation.name),
                        ]):
                return True
