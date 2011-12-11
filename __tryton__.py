#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
{
    'name': 'Jasper Reports',
    'version': '2.3.0',
    'author': 'NaN·tic',
    'email': 'info@nan-tic.com',
    'website': 'http://www.nan-tic.com/',
    'description': '''
Adds support for using JasperReports-based reports.

Note that the module creates a Java process which listents on localhost
for XML-RPC calls to avoid the overhead of loading the java virtual machine
each time a report is called.

Given that filenames are given tot the Java process, this could be a security
issue if you cannot rely on the users who can stablish TCP/IP connections
to localhost.
''',
    'depends': [
        'ir',
    ],
    'xml': [
        'sequence.xml',
    ],
    'translation': [
    ],
}
