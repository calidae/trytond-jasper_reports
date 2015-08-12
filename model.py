# -*- coding: utf-8 -*-
#This file is part jasper_reports module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from xml.dom.minidom import getDOMImplementation
import unicodedata

__all__ = ['Model']
__metaclass__ = PoolMeta

src_chars = """ '"()/*-+?Â¿!&$[]{}@#`'^:;<>=~%,\\"""
src_chars = unicode(src_chars, 'iso-8859-1')
dst_chars = """________________________________"""
dst_chars = unicode(dst_chars, 'iso-8859-1')


class Model:
    "Model"
    __name__ = 'ir.model'

    @staticmethod
    def normalize(text):
        if isinstance(text, unicode):
            text = text.encode('utf-8')
        return text

    @staticmethod
    def unaccent(text):
        if isinstance(text, str):
            text = unicode(text, 'utf-8')
        output = text
        for c in xrange(len(src_chars)):
            if c >= len(dst_chars):
                break
            output = output.replace(src_chars[c], dst_chars[c])
        output = unicodedata.normalize('NFKD', output).encode('ASCII',
            'ignore')
        return output.strip('_').encode('utf-8')

    @staticmethod
    def generate_jreport_xml(model, depth=1):
        """
        Generate XML from ir.model
        @param model: object
        @param depth: str
        :return file
        """
        IrModel = Pool().get('ir.model')
        document = getDOMImplementation().createDocument(None, 'data', None)
        topNode = document.documentElement
        recordNode = document.createElement('record')
        topNode.appendChild(recordNode)
        IrModel.get_jreport_xml(model, recordNode, document, depth)
        file_data = topNode.toxml()
        return bytes(file_data)

    @staticmethod
    def get_jreport_xml(model, parentNode, document, depth=1, first_call=True):
        """Get data fields XML
        @param model: str
        @param parentNode: object
        @param document: object
        @param depth: str
        @param first_call: boolean
        """
        pool = Pool()
        IrModel = pool.get('ir.model')

        model = IrModel.search([('model', '=', model)])[0]

        fieldNode = document.createElement('id')
        parentNode.appendChild(fieldNode)
        valueNode = document.createTextNode('1')
        fieldNode.appendChild(valueNode)

        for field in model.fields:
            if field.name == 'id':
                continue

            name = IrModel.unaccent(field.name)
            name = '%s-%s' % (name, name)
            fieldNode = document.createElement(name)
            parentNode.appendChild(fieldNode)

            fieldType = field.ttype
            if fieldType in ('many2one', 'one2many', 'many2many'):
                if depth <= 1:
                    continue
                newName = field.relation
                IrModel.get_jreport_xml(newName, fieldNode, document,
                    depth - 1, False)
                continue

        # TODO
        #~ if depth > 1 and modelName != 'Attachments':
            #~ # Create relation with attachments
            #~ fieldNode = document.createElement( '%s-Attachments' % _('Attachments') )
            #~ parentNode.appendChild( fieldNode )
            #~ self.generate_xml(cr, uid, context, pool, 'ir.attachment', fieldNode, document, depth-1, False)

        if first_call:
            # Create relation with user
            fieldNode = document.createElement('user-user')
            parentNode.appendChild(fieldNode)
            IrModel.get_jreport_xml('res.user', fieldNode, document,
                depth - 1, False)
