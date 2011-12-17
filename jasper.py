from trytond.report import Report
from trytond.config import CONFIG
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.cache import Cache

import JasperReports

import os
import time
import tempfile
import logging

# Determines the port where the JasperServer process should listen with its XML-RPC server for incomming calls
CONFIG['jasperport'] = CONFIG.get('jasperport', 8090)

# Determines the file name where the process ID of the JasperServer process should be stored
CONFIG['jasperpid'] = CONFIG.get('jasperpid', 'openerp-jasper.pid')

# Determines if temporary files will be removed
CONFIG['jasperunlink'] = CONFIG.get('jasperunlink', True)


class JasperReport(Report):
    @Cache('jasper_report.report_file', timeout=0)
    def get_report_file(self, report):
        report_content = str(report.report_content)

        if not report_content:
            raise Exception('Error', 'Missing report file!')

        # TODO Use report.template_extension instead of hardcoded 'jrxml'
        fd, path = tempfile.mkstemp(suffix=(os.extsep + 'jrxml'), 
                prefix='trytond_')
        return path

    def execute(self, ids, datas):
        report_path = 'sequence.jrxml'
        report_path = os.path.join(self.addonsPath(), report_path)

        report_path = '/home/albert/d/tryton/master/server/jasper-reports/trytond/modules/jasper_reports/sequence.jrxml'
        print "REP: ", report_path

        report = JasperReports.JasperReport(report_path)
        logger = logging.getLogger('jasper_reports')

        pool = Pool()
        action_report_obj = pool.get('ir.action.report')
        action_report_ids = action_report_obj.search([
                ('report_name', '=', self._name)
                ])
        if not action_report_ids:
            raise Exception('Error', 'Report (%s) not find!' % self._name)
        action_report = action_report_obj.browse(action_report_ids[0])
        model = action_report.model
        output_format = action_report.extension


        # Create temporary input (XML) and output (PDF) files 
        temporary_files = []

        fd, dataFile = tempfile.mkstemp()
        os.close(fd)
        fd, outputFile = tempfile.mkstemp()
        os.close(fd)
        temporary_files.append(dataFile)
        temporary_files.append(outputFile)
        logger.info("Temporary data file: '%s'" % dataFile)

        start = time.time()

        # If the language used is xpath create the xmlFile in dataFile.
        if report.language() == 'xpath':
            if datas.get('data_source','model') == 'records':
                generator = JasperReports.CsvRecordDataGenerator(report, datas['records'])
            else:
                generator = JasperReports.CsvBrowseDataGenerator(report, model, ids)
            generator.generate( dataFile )
            temporary_files += generator.temporary_files
        
        subreportDataFiles = []
        for subreportInfo in report.subreports():
            subreport = subreportInfo['report']
            if subreport.language() == 'xpath':
                message = 'Creating CSV '
                if subreportInfo['pathPrefix']:
                    message += 'with prefix %s ' % subreportInfo['pathPrefix']
                else:
                    message += 'without prefix '
                message += 'for file %s' % subreportInfo['filename']
                logger.info(message)

                fd, subreportDataFile = tempfile.mkstemp()
                os.close(fd)
                subreportDataFiles.append({
                    'parameter': subreportInfo['parameter'],
                    'dataFile': subreportDataFile,
                    'jrxmlFile': subreportInfo['filename'],
                })
                temporary_files.append( subreportDataFile )

                if subreport.isHeader():
                    generator = JasperReports.CsvBrowseDataGenerator(subreport, 'res.users', [Transaction().user])
                elif datas.get('data_source','model') == 'records':
                    generator = JasperReports.CsvRecordDataGenerator(subreport, datas['records'])
                else:
                    generator = JasperReports.CsvBrowseDataGenerator(subreport, model, ids)
                generator.generate(subreportDataFile)


        # Start: Report execution section
        locale = Transaction().language
        
        connectionParameters = {
            'output': output_format,
            'csv': dataFile,
            'dsn': self.dsn(),
            'user': self.userName(),
            'password': self.password(),
            'subreports': subreportDataFiles,
        }
        parameters = {
            'STANDARD_DIR': report.standardDirectory(),
            'REPORT_LOCALE': locale,
            'IDS': ids,
        }
        if 'parameters' in datas:
            parameters.update( datas['parameters'] )

        # Call the external java application that will generate the PDF file in outputFile
        server = JasperReports.JasperServer( int( CONFIG['jasperport'] ) )
        server.setPidFile( CONFIG['jasperpid'] )
        pages = server.execute( connectionParameters, report_path, outputFile, parameters )
        # End: report execution section


        elapsed = (time.time() - start) / 60
        logger.info("Elapsed: %.4f seconds" % elapsed )

        # Read data from the generated file and return it
        f = open( outputFile, 'rb')
        try:
            data = f.read()
        finally:
            f.close()

        # Remove all temporary files created during the report
        if CONFIG['jasperunlink']:
            for file in temporary_files:
                try:
                    os.unlink( file )
                except os.error, e:
                    logger = netsvc.Logger()
                    logger.warning("Could not remove file '%s'." % file)


        if Transaction().context.get('return_pages'):
            return (output_format, buffer(data), action_report.direct_print,
                    action_report.name, pages)

        return (output_format, buffer(data), action_report.direct_print,
            action_report.name)

    def dsn(self):
        host = CONFIG['db_host'] or 'localhost'
        port = CONFIG['db_port'] or '5432'
        dbname = Transaction().cursor.dbname
        return 'jdbc:postgresql://%s:%s/%s' % ( host, port, dbname )

    def userName(self):
        return CONFIG['db_user'] or self.systemUserName()

    def password(self):
        return CONFIG['db_password'] or ''

    def systemUserName(self):
        if os.name == 'nt':
            import win32api
            return win32api.GetUserName()
        else:
            import pwd
            return pwd.getpwuid(os.getuid())[0]

    def path(self):
        return os.path.abspath(os.path.dirname(__file__))

    def addonsPath(self):
        return os.path.dirname( self.path() )


