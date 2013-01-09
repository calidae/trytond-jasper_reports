#This file is part jasper_reports module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from trytond.model import ModelSQL, ModelView
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['SequenceReport']


class SequenceReport(JasperReport):
    __name__ = 'jasper_reports.sequence'
