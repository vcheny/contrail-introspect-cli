# Copyright (c) 2015 Cloudwatt
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
# @author: Numan Siddique, eNovance

from gen_py.sandesh.ttypes import SandeshLevel

import logging


class SandeshBaseLogger(object):
    """Sandesh Base Logger."""

    _logger = None

    _SANDESH_LEVEL_TO_LOGGER_LEVEL = {
        SandeshLevel.INVALID: logging.NOTSET,
        SandeshLevel.SYS_EMERG: logging.CRITICAL,
        SandeshLevel.SYS_ALERT: logging.CRITICAL,
        SandeshLevel.SYS_CRIT: logging.CRITICAL,
        SandeshLevel.SYS_ERR: logging.ERROR,
        SandeshLevel.SYS_WARN: logging.WARNING,
        SandeshLevel.SYS_NOTICE: logging.WARNING,
        SandeshLevel.SYS_INFO: logging.INFO,
        SandeshLevel.SYS_DEBUG: logging.DEBUG
    }

    def __init__(self, generator, logger_config_file=None):
        self._logging_params = {}

    @staticmethod
    def get_py_logger_level(sandesh_level):
        return SandeshBaseLogger._SANDESH_LEVEL_TO_LOGGER_LEVEL.get(
                sandesh_level, logging.NOTSET)
    # end get_py_logger_level

    def logger(self):
        return self._logger

    def set_logging_params(self, **kwargs):
        self._logging_params = kwargs

    def set_trace_print(self, enable_trace_print):
        self._logging_params['enable_trace_print'] = enable_trace_print

    def set_flow_logging(self, enable_flow_log):
        self._logging_params['enable_flow_log'] = enable_flow_log

    def set_local_logging(self, enable_local_log):
        self._logging_params['enable_local_log'] = enable_local_log

    def set_logging_level(self, level):
        self._logging_params['level'] = level

    def set_logging_category(self, category):
        self._logging_params['category'] = category

    def set_logging_file(self, file):
        self._logging_params['file'] = file

    def set_logging_syslog(self, enable_syslog, syslog_facility):
        self._logging_params['enable_syslog'] = enable_syslog
        self._logging_params['syslog_facility'] = syslog_facility

    def is_trace_print_enabled(self):
        return self._logging_params.get('enable_trace_print')

    def is_flow_logging_enabled(self):
        return self._logging_params.get('enable_flow_log')

    def is_local_logging_enabled(self):
        return self._logging_params.get('enable_local_log')

    def logging_level(self):
        return self._logging_params.get('level', SandeshLevel.SYS_INFO)

    def logging_category(self):
        return self._logging_params.get('category')

    def logging_file(self):
        return self._logging_params.get('file')

    def is_syslog_logging_enabled(self):
        return self._logging_params.get('enable_syslog')

    def logging_syslog_facility(self):
        return self._logging_params.get('syslog_facility')
