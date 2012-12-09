#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.

from trytond.pool import Pool
from .sequence import *


def register():
    Pool.register(
        SequenceReport,
        module='jasper_reports', type_='report')
