#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from jasper import JasperReport

__all__ = ['SequenceReport']


class SequenceReport(JasperReport):
    __name__ = 'jasper_reports.sequence'

SequenceReport()
