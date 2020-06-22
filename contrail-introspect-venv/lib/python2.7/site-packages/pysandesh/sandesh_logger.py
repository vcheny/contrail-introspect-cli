#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Sandesh Logger
#

import logging
import logging.config
import logging.handlers

from gen_py.sandesh.ttypes import SandeshLevel

import sandesh_base_logger
import util


def create_logger(generator, logger_class, logger_config_file=None):
    l_class = util.import_class(logger_class)
    return l_class(generator, logger_config_file=logger_config_file)


class SandeshConfigLogger(sandesh_base_logger.SandeshBaseLogger):

    """Sandesh Config Logger Implementation.

    This class sets the log config file to the python logging module.
    The user should define the log config file as per format defined in [1].

    [1] https://docs.python.org/2/library/logging.config.html
    """

    def __init__(self, logger_name, logger_config_file=None):
        super(SandeshConfigLogger, self).__init__(logger_name)
        logging.config.fileConfig(logger_config_file)
        self._logger = logging.getLogger(logger_name)


class SandeshLogger(sandesh_base_logger.SandeshBaseLogger):

    """Sandesh Logger Implementation."""
    _DEFAULT_LOG_FILE = '<stdout>'
    _DEFAULT_SYSLOG_FACILITY = 'LOG_LOCAL0'

    def __init__(self, logger_name, logger_config_file=None):
        assert logger_name, 'SandeshLogger init requires logger name'

        super(SandeshLogger, self).__init__(logger_name)

        self._logger_name = logger_name

        self._logger = logging.getLogger(self._logger_name)
        self._logger.setLevel(
            sandesh_base_logger.SandeshBaseLogger.get_py_logger_level(
                SandeshLevel.SYS_INFO))
        if not len(self._logger.handlers):
            # add the handler only once
            self._logging_file_handler = logging.StreamHandler()
            log_format = logging.Formatter(
                '%(asctime)s [%(name)s] [%(levelname)s]: %(message)s',
                datefmt='%m/%d/%Y %I:%M:%S %p')
            self._logging_file_handler.setFormatter(log_format)
            self._logger.addHandler(self._logging_file_handler)
        else:
            self._logging_file_handler = self._logger.handlers[0]

    # end __init__

    @staticmethod
    def _get_sandesh_and_logging_levels(level):
        if isinstance(level, unicode):
            level = level.encode('utf-8')
        if isinstance(level, str):
            if level in SandeshLevel._NAMES_TO_VALUES:
                level = SandeshLevel._NAMES_TO_VALUES[level]
            else:
                level = SandeshLevel.SYS_INFO
        # get logging level corresponding to sandesh level
        try:
            logger_level = sandesh_base_logger.SandeshBaseLogger.\
                   get_py_logger_level(level)
        except KeyError:
            logger_level = logging.INFO
            level = SandeshLevel.SYS_INFO
        return (level, logger_level)
    # end _get_sandesh_and_logging_levels

    def set_logging_params(self, enable_local_log=False, category='',
                           level=SandeshLevel.SYS_INFO, file=_DEFAULT_LOG_FILE,
                           enable_syslog=False, syslog_facility='LOG_LOCAL0',
                           enable_trace_print=False, enable_flow_log=False,
                           maxBytes=5000000, backupCount=10):
        self.set_local_logging(enable_local_log)
        self.set_logging_category(category)
        self.set_logging_level(level)
        self.set_logging_file(file, maxBytes, backupCount)
        self.set_logging_syslog(enable_syslog, syslog_facility)
        self.set_trace_print(enable_trace_print)
        self.set_flow_logging(enable_flow_log)
    # end set_logging_params

    @staticmethod
    def set_logger_params(logger, enable_local_log, level, file,
                          enable_syslog, syslog_facility,
                          maxBytes=5000000, backupCount=10):
        (_, logger_level) = \
                SandeshLogger._get_sandesh_and_logging_levels(level)
        logger.setLevel(logger_level)
        if enable_local_log:
            if file == SandeshLogger._DEFAULT_LOG_FILE:
                logging_file_handler = logging.StreamHandler()
            else:
                logging_file_handler = (
                    logging.handlers.RotatingFileHandler(
                        filename=file, maxBytes=maxBytes,
                        backupCount=backupCount))
            log_format = logging.Formatter(
                '%(asctime)s [%(name)s] [%(levelname)s]: %(message)s',
                datefmt='%m/%d/%Y %I:%M:%S %p')
            logging_file_handler.setFormatter(log_format)
            logger.addHandler(logging_file_handler)
        if enable_syslog:
            logging_syslog_handler = logging.handlers.SysLogHandler(
                address="/dev/log",
                facility=getattr(logging.handlers.SysLogHandler,
                                 syslog_facility,
                                 logging.handlers.SysLogHandler.LOG_LOCAL0)
            )
            log_format = logging.Formatter(
                '%(name)s[%(process)d]: %(message)s')
            logging_syslog_handler.setFormatter(log_format)
            logger.addHandler(logging_syslog_handler)
    # end set_logger_params

    def set_trace_print(self, enable_trace_print):
        if self.is_trace_print_enabled() != enable_trace_print:
            self._logger.info('SANDESH: Trace: PRINT: [%s] -> [%s]',
                              self.is_trace_print_enabled(),
                              enable_trace_print)
            super(SandeshLogger, self).set_trace_print(enable_trace_print)
    # end set_trace_print

    def set_flow_logging(self, enable_flow_log):
        if self.is_flow_logging_enabled() != enable_flow_log:
            self._logger.info('SANDESH: Flow Logging: [%s] -> [%s]',
                              self.is_flow_logging_enabled(),
                              enable_flow_log)
            super(SandeshLogger, self).set_flow_logging(enable_flow_log)
    # end set_flow_logging

    def set_logging_level(self, level):
        (level, logger_level) = \
            SandeshLogger._get_sandesh_and_logging_levels(level)
        self._logger.info('SANDESH: Logging: LEVEL: [%s] -> [%s]',
                          SandeshLevel._VALUES_TO_NAMES[self.logging_level()],
                          SandeshLevel._VALUES_TO_NAMES[level])
        self._logger.setLevel(logger_level)
        super(SandeshLogger, self).set_logging_level(level)
    # end set_logging_level

    def set_logging_file(self, file, maxBytes=5000000, backupCount=10):
        if self.logging_file() != file:
            self._logger.info('SANDESH: Logging: FILE: [%s] -> [%s]',
                              self.logging_file(), file)
            self._logger.removeHandler(self._logging_file_handler)
            if file == self._DEFAULT_LOG_FILE:
                self._logging_file_handler = logging.StreamHandler()
            else:
                self._logging_file_handler = (
                    logging.handlers.RotatingFileHandler(
                        filename=file, maxBytes=maxBytes,
                        backupCount=backupCount))
            log_format = logging.Formatter(
                '%(asctime)s [%(name)s] [%(levelname)s]: %(message)s',
                datefmt='%m/%d/%Y %I:%M:%S %p')
            self._logging_file_handler.setFormatter(log_format)
            self._logger.addHandler(self._logging_file_handler)
            super(SandeshLogger, self).set_logging_file(file)
    # end set_logging_file

    def set_logging_syslog(self, enable_syslog, syslog_facility):
        if (self.is_syslog_logging_enabled() == enable_syslog and
           self.logging_syslog_facility() == syslog_facility):
            return

        if self.logging_syslog_facility() != syslog_facility:
            self._logger.info('SANDESH: Logging: SYSLOG: [%s] -> [%s]',
                              self.logging_syslog_facility(), syslog_facility)

        if self.is_syslog_logging_enabled():
            self._logger.removeHandler(self._logging_syslog_handler)

        if enable_syslog:
            self._logging_syslog_handler = logging.handlers.SysLogHandler(
                address="/dev/log",
                facility=getattr(logging.handlers.SysLogHandler,
                                 syslog_facility,
                                 logging.handlers.SysLogHandler.LOG_LOCAL0)
            )
            log_format = logging.Formatter(
                '%(name)s[%(process)d]: %(message)s')
            self._logging_syslog_handler.setFormatter(log_format)
            self._logger.addHandler(self._logging_syslog_handler)

        super(SandeshLogger, self).set_logging_syslog(enable_syslog,
                                                      syslog_facility)
    # end set_logging_syslog
# end class SandeshLogger
