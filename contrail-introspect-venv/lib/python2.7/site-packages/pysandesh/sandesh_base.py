#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Sandesh
#

import importlib
import os
import sys
import pkgutil
import gevent
import json
import base64
import time
import copy
try:
    from collections import OrderedDict
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict

import sandesh_logger as sand_logger
import trace
import util
import platform

from gen_py.sandesh.ttypes import SandeshType, SandeshLevel, \
     SandeshTxDropReason
from gen_py.sandesh.constants import *
from sandesh_http import SandeshHttp
from sandesh_trace import SandeshTraceRequestRunner
from sandesh_client import SandeshClient
from sandesh_uve import SandeshUVETypeMaps, SandeshUVEPerTypeMap
from work_queue import WorkQueue

class SandeshConfig(object):

    def __init__(self, http_server_ip=None, keyfile=None, certfile=None, ca_cert=None,
                 sandesh_ssl_enable=False, introspect_ssl_enable=False,
                 dscp_value=0, disable_object_logs=False,
                 system_logs_rate_limit=DEFAULT_SANDESH_SEND_RATELIMIT,
                 stats_collector=None, tcp_keepalive_enable=True,
                 tcp_keepalive_idle_time=7200, tcp_keepalive_interval=75,
                 tcp_keepalive_probes=9):
        self.http_server_ip = http_server_ip
        self.keyfile = keyfile
        self.certfile = certfile
        self.ca_cert = ca_cert
        self.sandesh_ssl_enable = sandesh_ssl_enable
        self.introspect_ssl_enable = introspect_ssl_enable
        self.dscp_value = dscp_value
        self.disable_object_logs = disable_object_logs
        self.system_logs_rate_limit = system_logs_rate_limit
        self.stats_collector = stats_collector
        self.tcp_keepalive_enable = tcp_keepalive_enable
        self.tcp_keepalive_idle_time = tcp_keepalive_idle_time
        self.tcp_keepalive_interval = tcp_keepalive_interval
        self.tcp_keepalive_probes= tcp_keepalive_probes
    # end __init__

    @staticmethod
    def get_default_options(sections=['SANDESH']):
        sandeshopts = {}
        for section in sections:
            if section == 'SANDESH':
                sandeshopts.update({
                    'sandesh_keyfile': \
                        '/etc/contrail/ssl/private/server-privkey.pem',
                    'sandesh_certfile': \
                        '/etc/contrail/ssl/certs/server.pem',
                    'sandesh_ca_cert': \
                        '/etc/contrail/ssl/certs/ca-cert.pem',
                    'sandesh_ssl_enable': False,
                    'introspect_ssl_enable': False,
                    'sandesh_dscp_value': 0,
                    'disable_object_logs': False,
                    'tcp_keepalive_enable': True,
                    'tcp_keepalive_idle_time': 7200,
                    'tcp_keepalive_interval': 75,
                    'tcp_keepalive_probes': 9,
                    })
            if section == 'DEFAULTS':
                sandeshopts.update({'sandesh_send_rate_limit': \
                    DEFAULT_SANDESH_SEND_RATELIMIT,
                    'http_server_ip': '0.0.0.0'})
            if section == 'STATS':
                sandeshopts.update({'stats_collector': None})
        return sandeshopts
    # end get_default_options

    @classmethod
    def from_parser_arguments(cls, parser_args=None):
        default_opts = SandeshConfig.get_default_options(
                sections=['SANDESH', 'DEFAULTS', 'STATS'])
        sandesh_config = cls(
            http_server_ip = parser_args.http_server_ip if parser_args and \
                parser_args.http_server_ip else \
                default_opts['http_server_ip'],
            keyfile = parser_args.sandesh_keyfile if parser_args and \
                parser_args.sandesh_keyfile else \
                default_opts['sandesh_keyfile'],
            certfile = parser_args.sandesh_certfile if parser_args and \
                parser_args.sandesh_certfile else \
                default_opts['sandesh_certfile'],
            ca_cert = parser_args.sandesh_ca_cert if parser_args and \
                parser_args.sandesh_ca_cert else \
                default_opts['sandesh_ca_cert'],
            sandesh_ssl_enable = \
                parser_args.sandesh_ssl_enable if parser_args and \
                parser_args.sandesh_ssl_enable is not None else \
                default_opts['sandesh_ssl_enable'],
            introspect_ssl_enable = \
                parser_args.introspect_ssl_enable if parser_args and \
                parser_args.introspect_ssl_enable is not None else \
                default_opts['introspect_ssl_enable'],
            dscp_value = parser_args.sandesh_dscp_value if parser_args and \
                parser_args.sandesh_dscp_value is not None else \
                default_opts['sandesh_dscp_value'],
            disable_object_logs =
                parser_args.disable_object_logs if parser_args and \
                parser_args.disable_object_logs is not None else \
                default_opts['disable_object_logs'],
            system_logs_rate_limit =
                parser_args.sandesh_send_rate_limit if parser_args and \
                parser_args.sandesh_send_rate_limit is not None else \
                default_opts['sandesh_send_rate_limit'],
            stats_collector =
                parser_args.stats_collector if parser_args and \
                hasattr(parser_args, 'stats_collector') and \
                parser_args.stats_collector is not None else \
                default_opts['stats_collector'],
            tcp_keepalive_enable =
                parser_args.tcp_keepalive_enable if parser_args and \
                parser_args.tcp_keepalive_enable is not None else \
                default_opts['tcp_keepalive_enable'],
            tcp_keepalive_idle_time =
                parser_args.tcp_keepalive_idle_time if parser_args and \
                parser_args.tcp_keepalive_idle_time is not None else \
                default_opts['tcp_keepalive_idle_time'],
            tcp_keepalive_interval =
                parser_args.tcp_keepalive_interval if parser_args and \
                parser_args.tcp_keepalive_interval is not None else \
                default_opts['tcp_keepalive_interval'],
            tcp_keepalive_probes =
                parser_args.tcp_keepalive_probes if parser_args and \
                parser_args.tcp_keepalive_probes is not None else \
                default_opts['tcp_keepalive_probes'])

        return sandesh_config
    # end get_sandesh_config

    @staticmethod
    def add_parser_arguments(parser, add_dscp=False):
        parser.add_argument("--sandesh_keyfile",
            help="Sandesh SSL private key")
        parser.add_argument("--sandesh_certfile",
            help="Sandesh SSL certificate")
        parser.add_argument("--sandesh_ca_cert",
            help="Sandesh CA SSL certificate")
        parser.add_argument("--sandesh_ssl_enable", action="store_true",
            help="Enable SSL for sandesh connection")
        parser.add_argument("--introspect_ssl_enable", action="store_true",
            help="Enable SSL for introspect connection")
        if add_dscp:
            parser.add_argument("--sandesh_dscp_value", type=int,
                help="DSCP bits for IP header of Sandesh messages")
        parser.add_argument("--disable_object_logs", action="store_true",
            help="Disable sending of object logs to the oollector")
        parser.add_argument("--sandesh_send_rate_limit", type=int,
            help="System logs send rate limit in messages per second per message type")
        parser.add_argument("--stats_collector",
            help="External Stats Collector")
        parser.add_argument("--tcp_keepalive_enable", action="store_true",
            help="Enable keepalive for tcp connection")
        parser.add_argument("--tcp_keepalive_idle_time", type=int,
            help="set the keepalive timer in seconds")
        parser.add_argument("--tcp_keepalive_interval", type=int,
            help="specify the tcp keepalive interval time")
        parser.add_argument("--tcp_keepalive_probes", type=int,
            help="specify the tcp keepalive probes")
    # end add_parser_arguments

    @staticmethod
    def update_options(sandeshopts, config):
        if 'SANDESH' in config.sections():
            sandeshopts.update(dict(config.items('SANDESH')))
            if 'sandesh_ssl_enable' in config.options('SANDESH'):
                sandeshopts['sandesh_ssl_enable'] = config.getboolean(
                    'SANDESH', 'sandesh_ssl_enable')
            if 'introspect_ssl_enable' in config.options('SANDESH'):
                sandeshopts['introspect_ssl_enable'] = config.getboolean(
                    'SANDESH', 'introspect_ssl_enable')
            if 'disable_object_logs' in config.options('SANDESH'):
                sandeshopts['disable_object_logs'] = config.getboolean(
                    'SANDESH', 'disable_object_logs')
            if 'sandesh_dscp_value' in config.options('SANDESH'):
                try:
                    sandeshopts['sandesh_dscp_value'] = config.getint(
                        'SANDESH', 'sandesh_dscp_value')
                except:
                    pass

            if 'tcp_keepalive_enable' in config.options('SANDESH'):
                sandeshopts['tcp_keepalive_enable'] = config.getboolean(
                      'SANDESH', 'tcp_keepalive_enable')
            if 'tcp_keepalive_idle_time' in config.options('SANDESH'):
                sandeshopts['tcp_keepalive_idle_time'] = config.getint(
                      'SANDESH', 'tcp_keepalive_idle_time')
            if 'tcp_keepalive_interval' in config.options('SANDESH'):
                sandeshopts['tcp_keepalive_interval'] = config.getint(
                      'SANDESH', 'tcp_keepalive_interval')
            if 'tcp_keepalive_probes' in config.options('SANDESH'):
                sandeshopts['tcp_keepalive_probes'] = config.getint(
                      'SANDESH', 'tcp_keepalive_probes')

        if 'STATS' in config.sections():
            sandeshopts.update(dict(config.items('STATS')))
            if 'stats_collector' in config.options('STATS'):
                sandeshopts['stats_collector'] = config.get('STATS',
                    'stats_collector')
    # end update_options

# end class SandeshConfig

class Sandesh(object):
    _DEFAULT_LOG_FILE = sand_logger.SandeshLogger._DEFAULT_LOG_FILE
    _DEFAULT_SYSLOG_FACILITY = (
        sand_logger.SandeshLogger._DEFAULT_SYSLOG_FACILITY)

    class SandeshRole:
        INVALID = 0
        GENERATOR = 1
        COLLECTOR = 2
    # end class SandeshRole

    def __init__(self):
        self._context = ''
        self._scope = ''
        self._module = ''
        self._source = ''
        self._node_type = ''
        self._instance_id = ''
        self._timestamp = 0
        self._versionsig = 0
        self._type = 0
        self._hints = 0
        self._client_context = ''
        self._client = None
        self._role = self.SandeshRole.INVALID
        self._logger = None
        self._level = SandeshLevel.INVALID
        self._category = ''
        self._send_queue_enabled = True
        self._http_server = None
        self._connect_to_collector = True
        self._disable_sending_object_logs = False
        self._disable_sending_all_messages = False
    # end __init__

    # Public functions

    def init_generator(self, module, source, node_type, instance_id,
                       collectors, client_context,
                       http_port, sandesh_req_uve_pkg_list=None,
                       connect_to_collector=True,
                       logger_class=None, logger_config_file=None,
                       host_ip='127.0.0.1', alarm_ack_callback=None,
                       config=None):
        self._role = self.SandeshRole.GENERATOR
        self._module = module
        self._source = source
        self._node_type = node_type
        self._instance_id = instance_id
        self._sandesh_req_uve_pkg_list = sandesh_req_uve_pkg_list or []
        self._host_ip = host_ip
        self._client_context = client_context
        self._connect_to_collector = connect_to_collector
        self._rcv_queue = WorkQueue(self._process_rx_sandesh)
        self._init_logger(self._module, logger_class=logger_class,
                          logger_config_file=logger_config_file)
        self._logger.info('SANDESH: CONNECT TO COLLECTOR: %s',
                          connect_to_collector)
        from sandesh_stats import SandeshMessageStatistics
        self._msg_stats = SandeshMessageStatistics()
        self._trace = trace.Trace()
        self._sandesh_request_map = {}
        self._alarm_ack_callback = alarm_ack_callback
        self._config = config or SandeshConfig.from_parser_arguments()
        self._uve_type_maps = SandeshUVETypeMaps(self._logger)
        # Initialize the request handling
        # Import here to break the cyclic import dependency
        import sandesh_req_impl
        sandesh_req_impl = sandesh_req_impl.SandeshReqImpl(self)
        self._sandesh_req_uve_pkg_list.append('pysandesh.gen_py')
        for pkg_name in self._sandesh_req_uve_pkg_list:
            self._create_sandesh_request_and_uve_lists(pkg_name)
        if self._config.disable_object_logs is not None:
            self.disable_sending_object_logs(self._config.disable_object_logs)
        if self._config.system_logs_rate_limit is not None:
            SandeshSystem.set_sandesh_send_rate_limit(
                self._config.system_logs_rate_limit)
        self._gev_httpd = None
        if http_port != -1:
            self.run_introspect_server(http_port)
        if self._connect_to_collector:
            self._client = SandeshClient(self)
            self._client.initiate(collectors)
    # end init_generator

    def run_introspect_server(self, http_port):
        self._logger.info('SANDESH: INTROSPECT IS ON: %s:%s',
                    self._config.http_server_ip, http_port)
        self._http_server = SandeshHttp(
            self, self._module, http_port,
            self._sandesh_req_uve_pkg_list, self._config,
            self._config.http_server_ip)
        self._gev_httpd = gevent.spawn(self._http_server.start_http_server)
    # end run_introspect_server

    def uninit(self):
        self.kill_httpd()

    def kill_httpd(self):
        if self._gev_httpd:
            try:
                self._http_server.stop_http_server()
                self._http_server = None
                gevent.sleep(0)
                self._gev_httpd.kill()
            except Exception as e:
                self._logger.debug(str(e))

    def record_port(self, name, port):
        if platform.system() != 'Windows':
            pipe_name = '/tmp/%s.%d.%s_port' % (self._module, os.getppid(), name)
            try:
                pipeout = os.open(pipe_name, os.O_WRONLY)
            except Exception:
                self._logger.error('Cannot write %s_port %d to %s'
                                   % (name, port, pipe_name))
            else:
                self._logger.error('Writing %s_port %d to %s'
                                   % (name, port, pipe_name))
                os.write(pipeout, '%d\n' % port)
                os.close(pipeout)

    def logger(self):
        return self._logger
    # end logger

    def sandesh_logger(self):
        return self._sandesh_logger
    # end sandesh_logger

    def set_logging_params(self, enable_local_log=False, category='',
                           level=SandeshLevel.SYS_INFO,
                           file=sand_logger.SandeshLogger._DEFAULT_LOG_FILE,
                           enable_syslog=False,
                           syslog_facility=_DEFAULT_SYSLOG_FACILITY,
                           enable_trace_print=False,
                           enable_flow_log=False):
        self._sandesh_logger.set_logging_params(
            enable_local_log=enable_local_log, category=category,
            level=level, file=file, enable_syslog=enable_syslog,
            syslog_facility=syslog_facility,
            enable_trace_print=enable_trace_print,
            enable_flow_log=enable_flow_log)
    # end set_logging_params

    def set_trace_print(self, enable_trace_print):
        self._sandesh_logger.set_trace_print(enable_trace_print)
    # end set_trace_print

    def set_flow_logging(self, enable_flow_log):
        self._sandesh_logger.set_flow_logging(enable_flow_log)
    # end set_flow_logging

    def set_local_logging(self, enable_local_log):
        self._sandesh_logger.set_local_logging(enable_local_log)
    # end set_local_logging

    def set_logging_level(self, level):
        self._sandesh_logger.set_logging_level(level)
    # end set_logging_level

    def set_logging_category(self, category):
        self._sandesh_logger.set_logging_category(category)
    # end set_logging_category

    def set_logging_file(self, file):
        self._sandesh_logger.set_logging_file(file)
    # end set_logging_file

    def is_logging_dropped_allowed(self, sandesh):
        if sandesh.type() == SandeshType.FLOW or \
           sandesh.type() == SandeshType.SESSION:
            return self.is_flow_logging_enabled()
        else:
            if hasattr(sandesh, 'do_rate_limit_drop_log'):
                return sandesh.do_rate_limit_drop_log
            return True
    # end is_logging_dropped_allowed

    def is_send_queue_enabled(self):
        return self._send_queue_enabled
    # end is_send_queue_enabled

    def is_connect_to_collector_enabled(self):
        return self._connect_to_collector
    # end is_connect_to_collector_enabled

    def is_sending_object_logs_disabled(self):
        return self._disable_sending_object_logs
    # end is_sending_object_logs_disabled

    def disable_sending_object_logs(self, disable):
        if self._disable_sending_object_logs != disable:
            self._logger.info("SANDESH: Disable Sending Object "
                "Logs: %s -> %s", self._disable_sending_object_logs,
                disable)
            self._disable_sending_object_logs = disable
    # end disable_sending_object_logs

    def is_sending_all_messages_disabled(self):
        return self._disable_sending_all_messages
    # end is_sending_all_messages_disabled

    def disable_sending_all_messages(self, disable):
        if self._disable_sending_all_messages != disable:
            self._logger.info("SANDESH: Disable Sending ALL Messages: "
                "%s -> %s", self._disable_sending_all_messages, disable)
            self._disable_sending_all_messagess = disable
    # end disable_sending_all_messages

    def set_send_queue(self, enable):
        if self._send_queue_enabled != enable:
            self._logger.info("SANDESH: CLIENT: SEND QUEUE: %s -> %s",
                              self._send_queue_enabled, enable)
            self._send_queue_enabled = enable
            if enable:
                connection = self._client.connection()
                if connection and connection.session():
                    connection.session().send_queue().may_be_start_runner()
    # end set_send_queue

    def send_level(self):
       session = self._get_client_session()
       if session:
           return session.send_level()
       return SandeshLevel.INVALID
    # end send_level

    def init_collector(self):
        pass
    # end init_collector

    def msg_stats(self):
        return self._msg_stats
    # end msg_stats

    def reconfig_collectors(self, collectors):
        self._client.set_collectors(collectors)
    # end reconfig_collectors

    @classmethod
    def next_seqnum(cls):
        if not hasattr(cls, '_lseqnum'):
            cls._lseqnum = 1
        else:
            cls._lseqnum += 1
        return cls._lseqnum
    # end next_seqnum

    @classmethod
    def lseqnum(cls):
        if not hasattr(cls, '_lseqnum'):
            cls._lseqnum = 0
        return cls._lseqnum
    # end lseqnum

    def module(self):
        return self._module
    # end module

    def source_id(self):
        return self._source
    # end source_id

    def node_type(self):
        return self._node_type
    # end node_type

    def instance_id(self):
        return self._instance_id
    # end instance_id

    def host_ip(self):
        return self._host_ip
    # end host_ip

    def scope(self):
        return self._scope
    # end scope

    def context(self):
        return self._context
    # end context

    def seqnum(self):
        return self._seqnum
    # end seqnum

    def timestamp(self):
        return self._timestamp
    # end timestamp

    def versionsig(self):
        return self._versionsig
    # end versionsig

    def type(self):
        return self._type
    # end type

    def hints(self):
        return self._hints
    # end hints

    def client(self):
        return self._client
    # end client

    def level(self):
        return self._level
    # end level

    def category(self):
        return self._category
    # end category

    def validate(self):
        return
    # end validate

    def alarm_ack_callback(self):
        return self._alarm_ack_callback
    # end alarm_ack_callback

    def config(self):
        return self._config
    # end config

    def is_send_queue_empty(self):
        return self._client.connection().statemachine().session().\
            send_queue().is_queue_empty()

    def is_flow_logging_enabled(self):
        return self._sandesh_logger.is_flow_logging_enabled()
    # end is_flow_logging_enabled

    def is_trace_print_enabled(self):
        return self._sandesh_logger.is_trace_print_enabled()
    # end is_trace_print_enabled

    def is_local_logging_enabled(self):
        return self._sandesh_logger.is_local_logging_enabled()
    # end is_local_logging_enabled

    def logging_level(self):
        return self._sandesh_logger.logging_level()
    # end logging_level

    def logging_category(self):
        return self._sandesh_logger.logging_category()
    # end logging_category

    def is_syslog_logging_enabled(self):
        return self._sandesh_logger.is_syslog_logging_enabled()
    # end is_syslog_logging_enabled

    def logging_syslog_facility(self):
        return self._sandesh_logger.logging_syslog_facility()
    # end logging_syslog_facility

    def is_unit_test(self):
        return self._role == self.SandeshRole.INVALID
    # end is_unit_test

    def handle_test(self, sandesh_init):
        if sandesh_init.is_unit_test() or self._is_level_ut():
            if self.is_logging_allowed(sandesh_init):
                sandesh_init._logger.debug(self.log())
            return True
        return False

    def is_logging_allowed(self, sandesh_init):
        if self._type == SandeshType.FLOW or \
           self._type == SandeshType.SESSION:
            return sandesh_init.is_flow_logging_enabled()

        if not sandesh_init.is_local_logging_enabled():
            return False

        logging_level = sandesh_init.logging_level()
        # Do not log UVEs unless explicitly configured
        # to do so via setting log_level to INVALID. This
        # is to avoid flooding the log files with UVEs
        level = self._level
        if self._type == SandeshType.UVE:
            level = SandeshLevel.INVALID
        level_allowed = logging_level >= level

        logging_category = sandesh_init.logging_category()
        if logging_category is None or len(logging_category) == 0:
            category_allowed = True
        else:
            category_allowed = logging_category == self._category

        return level_allowed and category_allowed
    # end is_logging_allowed

    def enqueue_sandesh_request(self, sandesh):
        self._rcv_queue.enqueue(sandesh)
    # end enqueue_sandesh_request

    def send_sandesh(self, tx_sandesh):
        if self._client:
            self._client.send_sandesh(tx_sandesh)
        else:
            if self._connect_to_collector:
                self.drop_tx_sandesh(tx_sandesh, SandeshTxDropReason.NoClient)
            else:
                self.drop_tx_sandesh(tx_sandesh, SandeshTxDropReason.NoClient,
                    tx_sandesh.level())
    # end send_sandesh

    def drop_tx_sandesh(self, tx_sandesh, drop_reason, level=None):
        self._msg_stats.update_tx_stats(tx_sandesh.__class__.__name__,
            sys.getsizeof(tx_sandesh), drop_reason)
        if self.is_logging_dropped_allowed(tx_sandesh):
            if level is not None:
                self._logger.log(
                    sand_logger.SandeshLogger.get_py_logger_level(level),
                    tx_sandesh.log())
            else:
                self._logger.error('SANDESH: [DROP: %s] %s' % \
                    (SandeshTxDropReason._VALUES_TO_NAMES[drop_reason],
                     tx_sandesh.log()))
    # end drop_tx_sandesh

    def send_generator_info(self):
        from gen_py.sandesh_uve.ttypes import SandeshClientInfo, \
            ModuleClientState, SandeshModuleClientTrace
        if not self._client or not self._client.connection():
            return
        client_info = SandeshClientInfo()
        try:
            client_start_time = self._start_time
        except Exception:
            self._start_time = util.UTCTimestampUsec()
        finally:
            client_info.start_time = self._start_time
            client_info.pid = os.getpid()
            if self._http_server is not None:
                client_info.http_port = self._http_server.get_port()
            client_info.collector_name = \
                self._client.connection().collector_name() or ''
            client_info.collector_ip = \
                self._client.connection().collector() or ''
            client_info.collector_list = self._client.connection().collectors()
            client_info.status = self._client.connection().state()
            client_info.successful_connections = (
                self._client.connection().statemachine().connect_count())
            module_state = ModuleClientState(name=self._source + ':' +
                                             self._node_type + ':' +
                                             self._module + ':' +
                                             self._instance_id,
                                             client_info=client_info,
                                             sm_queue_count=self._client.\
                connection().statemachine()._event_queue.size(),
                                             max_sm_queue_count=self._client.\
                connection().statemachine()._event_queue.max_qlen())
            generator_info = SandeshModuleClientTrace(
                data=module_state, sandesh=self)
            generator_info.send(sandesh=self)
    # end send_generator_info

    def get_sandesh_request_object(self, request):
        try:
            req_type = self._sandesh_request_map[request]
        except KeyError:
            self._logger.error('Invalid Sandesh Request "%s"' % (request))
            return None
        else:
            return req_type()
    # end get_sandesh_request_object

    def trace_enable(self):
        self._trace.TraceOn()
    # end trace_enable

    def trace_disable(self):
        self._trace.TraceOff()
    # end trace_disable

    def is_trace_enabled(self):
        return self._trace.IsTraceOn()
    # end is_trace_enabled

    def trace_buffer_create(self, name, size, enable=True):
        self._trace.TraceBufAdd(name, size, enable)
    # end trace_buffer_create

    def trace_buffer_delete(self, name):
        self._trace.TraceBufDelete(name)
    # end trace_buffer_delete

    def trace_buffer_enable(self, name):
        self._trace.TraceBufOn(name)
    # end trace_buffer_enable

    def trace_buffer_disable(self, name):
        self._trace.TraceBufOff(name)
    # end trace_buffer_disable

    def is_trace_buffer_enabled(self, name):
        return self._trace.IsTraceBufOn(name)
    # end is_trace_buffer_enabled

    def trace_buffer_list_get(self):
        return self._trace.TraceBufListGet()
    # end trace_buffer_list_get

    def trace_buffer_size_get(self, name):
        return self._trace.TraceBufSizeGet(name)
    # end trace_buffer_size_get

    def trace_buffer_read(self, name, read_context, count, read_cb):
        self._trace.TraceRead(name, read_context, count, read_cb)
    # end trace_buffer_read

    def trace_buffer_read_done(self, name, context):
        self._trace.TraceReadDone(name, context)
    # end trace_buffer_read_done

    # API to send the trace buffer to the Collector.
    # If trace count is not specified/or zero, then the entire trace buffer
    # is sent to the Collector.
    # [Note] No duplicate trace message sent to the Collector. i.e., If there
    # is no trace message added between two consequent calls to this API, then
    # no trace message is sent to the Collector.
    def send_sandesh_trace_buffer(self, trace_buf, count=0):
        trace_req_runner = SandeshTraceRequestRunner(
            sandesh=self, request_buffer_name=trace_buf, request_context='',
            read_context='Collector', request_count=count)
        trace_req_runner.Run()
    # end send_sandesh_trace_buffer

    # Private functions

    def _get_client_session(self):
        if self._client and self._client.connection():
            return self._client.connection().session()
        return None
    # end _get_client_session

    def _is_level_ut(self):
        return (self._level >= SandeshLevel.UT_START and
                self._level <= SandeshLevel.UT_END)
    # end _is_level_ut

    def _create_task(self):
        return gevent.spawn(self._runner.run_for_ever)
    # end _create_task

    def _process_rx_sandesh(self, rx_sandesh):
        handle_request_fn = getattr(rx_sandesh, "handle_request", None)
        if callable(handle_request_fn):
            handle_request_fn(rx_sandesh)
        else:
            self._logger.error('Sandesh Request "%s" not implemented' %
                               (rx_sandesh.__class__.__name__))
    # end _process_rx_sandesh

    def _create_sandesh_request_and_uve_lists(self, package):
        try:
            imp_pkg = __import__(package)
        except ImportError:
            self._logger.error('Failed to import package "%s"' % (package))
        else:
            try:
                pkg_path = imp_pkg.__path__
            except AttributeError:
                self._logger.error(
                    'Failed to get package [%s] path' % (package))
                return
            for importer, mod, ispkg in (
                pkgutil.walk_packages(path=pkg_path,
                                      prefix=imp_pkg.__name__ + '.')):
                if not ispkg:
                    module = mod.rsplit('.', 1)[-1]
                    if 'ttypes' == module:
                        self._logger.debug(
                            'Add Sandesh requests in module "%s"' % (mod))
                        self._add_sandesh_request(mod)
                        self._logger.debug(
                            'Add Sandesh UVEs in module "%s"' % (mod))
                        self._add_sandesh_uve(mod)
                        self._logger.debug(
                            'Add Sandesh Alarms in module "%s"' % (mod))
                        self._add_sandesh_alarm(mod)
    # end _create_sandesh_request_and_uve_lists

    def _add_sandesh_request(self, mod):
        try:
            imp_module = importlib.import_module(mod)
        except ImportError:
            self._logger.error('Failed to import Module "%s"' % (mod))
        else:
            try:
                sandesh_req_list = getattr(imp_module, '_SANDESH_REQUEST_LIST')
            except AttributeError:
                self._logger.error(
                    '"%s" module does not have sandesh request list' % (mod))
            else:
                # Add sandesh requests to the dictionary.
                for req in sandesh_req_list:
                    self._sandesh_request_map[req.__name__] = req
    # end _add_sandesh_request

    def _get_sandesh_uve_list(self, imp_module):
        try:
            sandesh_uve_list = getattr(imp_module, '_SANDESH_UVE_LIST')
        except AttributeError:
            self._logger.error(
                '"%s" module does not have sandesh UVE list' %
                (imp_module.__name__))
            return None
        else:
            return sandesh_uve_list
    # end _get_sandesh_uve_list

    def _add_sandesh_uve(self, mod):
        try:
            imp_module = importlib.import_module(mod)
        except ImportError:
            self._logger.error('Failed to import Module "%s"' % (mod))
        else:
            sandesh_uve_list = self._get_sandesh_uve_list(imp_module)
            if not sandesh_uve_list:
                return
            # Register sandesh UVEs
            for uve_type, uve_data_type in sandesh_uve_list:
                SandeshUVEPerTypeMap(self, SandeshType.UVE,
                    uve_type, uve_data_type)
    # end _add_sandesh_uve

    def _get_sandesh_alarm_list(self, imp_module):
        try:
            sandesh_alarm_list = getattr(imp_module, '_SANDESH_ALARM_LIST')
        except AttributeError:
            self._logger.error(
                '"%s" module does not have sandesh Alarm list' %
                (imp_module.__name__))
            return None
        else:
            return sandesh_alarm_list
    # end _get_sandesh_alarm_list

    def _add_sandesh_alarm(self, mod):
        try:
            imp_module = importlib.import_module(mod)
        except ImportError:
            self._logger.error('Failed to import Module "%s"' % (mod))
        else:
            sandesh_alarm_list = self._get_sandesh_alarm_list(imp_module)
            if not sandesh_alarm_list:
                return
            # Register sandesh Alarms
            for alarm_type, alarm_data_type in sandesh_alarm_list:
                SandeshUVEPerTypeMap(self, SandeshType.ALARM, alarm_type,
                    alarm_data_type)
    # end _add_sandesh_alarm

    def _init_logger(self, module, logger_class=None,
                     logger_config_file=None):
        if not module:
            module = 'sandesh'

        if logger_class:
            self._sandesh_logger = (sand_logger.create_logger(
                module, logger_class,
                logger_config_file=logger_config_file))
        else:
            self._sandesh_logger = sand_logger.SandeshLogger(
                module, logger_config_file=logger_config_file)
        self._logger = self._sandesh_logger.logger()
    # end _init_logger

# end class Sandesh

sandesh_global = Sandesh()



class SandeshAsync(Sandesh):

    def __init__(self):
        Sandesh.__init__(self)
    # end __init__

    def send(self, sandesh=sandesh_global):
        try:
            self.validate()
        except e:
            sandesh.drop_tx_sandesh(self, SandeshTxDropReason.ValidationFailed)
            return -1
        if self.handle_test(sandesh):
            return 0
        # Check if sending is disabled
        if sandesh.is_sending_all_messages_disabled():
            sandesh.drop_tx_sandesh(self,
                SandeshTxDropReason.SendingDisabled, self.level())
            return -1
        # For objectlog message, check if sending message is disabled
        if self._type == SandeshType.OBJECT and \
                sandesh.is_sending_object_logs_disabled():
            sandesh.drop_tx_sandesh(self,
                SandeshTxDropReason.SendingDisabled, self.level())
            return -1
        # For systemlog message, first check if sending message is disabled,
        # then check rate limit
        if self._type == SandeshType.SYSTEM:
            if SandeshSystem.get_sandesh_send_rate_limit() == 0:
                sandesh.drop_tx_sandesh(self,
                    SandeshTxDropReason.SendingDisabled, self.level())
                return -1
            if (not self.is_rate_limit_pass(sandesh)):
                sandesh.drop_tx_sandesh(self,
                    SandeshTxDropReason.RatelimitDrop)
                return -1
        if self._level >= sandesh.send_level():
            sandesh.drop_tx_sandesh(self, SandeshTxDropReason.QueueLevel)
            return -1
        self._seqnum = self.next_seqnum()
        sandesh.send_sandesh(self)
        return 0

    def is_rate_limit_pass(self,sandesh):
        #Check if buffer resize is reqd
        if (self.__class__.rate_limit_buffer.maxlen != \
                SandeshSystem.get_sandesh_send_rate_limit()):
            temp_buffer = copy.deepcopy(self.__class__.rate_limit_buffer)
            self.__class__.rate_limit_buffer = util.deque(temp_buffer, \
                maxlen=SandeshSystem.get_sandesh_send_rate_limit())
            del temp_buffer
        #If buffer size 0 return
        if self.__class__.rate_limit_buffer.maxlen == 0:
            return False
        cur_time=int(time.time())
        #Check if circular buffer is full
        if len(self.__class__.rate_limit_buffer) == \
            self.__class__.rate_limit_buffer.maxlen :
            # Read the element in buffer and compare with cur_time
            if(self.__class__.rate_limit_buffer[0] == cur_time):
                #Sender generating more messages/sec than the
                #buffer_threshold size
                if self.__class__.do_rate_limit_drop_log:
                    sandesh._logger.error('SANDESH: Ratelimit Drop ' \
                        '(%d messages/sec): for %s' % \
                        (self.__class__.rate_limit_buffer.maxlen, \
                         self.__class__.__name__))
                    #Disable logging
                    self.__class__.do_rate_limit_drop_log = False
                return False
        #If logging is disabled enable it
        self.__class__.do_rate_limit_drop_log = True
        self.__class__.rate_limit_buffer.append(cur_time)
        return True

    # end send

# end class SandeshAsync


class SandeshSystem(SandeshAsync):

    _DEFAULT_SEND_RATELIMIT = DEFAULT_SANDESH_SEND_RATELIMIT

    @classmethod
    def set_sandesh_send_rate_limit(cls, sandesh_send_rate_limit_val):
        if (sandesh_send_rate_limit_val >= 0):
            cls._DEFAULT_SEND_RATELIMIT = sandesh_send_rate_limit_val
    # end set_sandesh_send_rate_limit

    @classmethod
    def get_sandesh_send_rate_limit(cls):
        return cls._DEFAULT_SEND_RATELIMIT
    # end get_sandesh_send_rate_limit

    def __init__(self):
        SandeshAsync.__init__(self)
        self._type = SandeshType.SYSTEM
    # end __init__

# end class SandeshSystem


class SandeshObject(SandeshAsync):

    def __init__(self):
        SandeshAsync.__init__(self)
        self._type = SandeshType.OBJECT
    # end __init__

# end class SandeshObject


class SandeshFlow(SandeshAsync):

    def __init__(self):
        SandeshAsync.__init__(self)
        self._type = SandeshType.FLOW
    # end __init__

# end class SandeshFlow


class SandeshFlowSession(SandeshAsync):

    def __init__(self):
        SandeshAsync.__init__(self)
        self._type = SandeshType.SESSION
    # end __init__

# end class SandeshFlowSession


class SandeshRequest(Sandesh):

    def __init__(self):
        Sandesh.__init__(self)
        self._type = SandeshType.REQUEST
    # end __init__

    def request(self, context='', sandesh=sandesh_global):
        try:
            self.validate()
        except e:
            sandesh.drop_tx_sandesh(self, SandeshTxDropReason.ValidationFailed)
            return -1
        if context == 'ctrl':
            self._hints |= SANDESH_CONTROL_HINT
        self._context = context
        self._seqnum = self.next_seqnum()
        if self.handle_test(sandesh):
            return 0
        sandesh.send_sandesh(self)
        return 0
    # end request

# end class SandeshRequest


class SandeshResponse(Sandesh):

    def __init__(self):
        Sandesh.__init__(self)
        self._type = SandeshType.RESPONSE
        self._more = False
    # end __init__

    def response(self, context='', more=False, sandesh=sandesh_global):
        try:
            self.validate()
        except e:
            sandesh.drop_tx_sandesh(self, SandeshTxDropReason.ValidationFailed)
            return -1
        self._context = context
        self._more = more
        self._seqnum = self.next_seqnum()
        if self._context.find('http://') == 0 or \
                self._context.find('https://') == 0:
            SandeshHttp.create_http_response(self, sandesh)
        else:
            if self.handle_test(sandesh):
                return 0
            sandesh.send_sandesh(self)
        return 0
    # end response

# end class SandeshResponse


class SandeshUVE(Sandesh):

    def __init__(self):
        Sandesh.__init__(self)
        self._type = SandeshType.UVE
        self._more = False
    # end __init__

    def send(self, isseq=False, seqno=0, context='',
             more=False, sandesh=sandesh_global,
             level=SandeshLevel.SYS_NOTICE):
        try:
            self.validate()
        except e:
            sandesh.drop_tx_sandesh(self, SandeshTxDropReason.ValidationFailed)
            return -1
        if self._type == SandeshType.UVE and \
                self._level == SandeshLevel.INVALID:
            self._level = level
        if isseq is True:
            self._seqnum = seqno
            self._hints |= SANDESH_SYNC_HINT
        else:
            uve_type_map = sandesh._uve_type_maps.get_uve_type_map(
                self.__class__.__name__)
            if uve_type_map is None:
                sandesh._logger.error('sandesh uve <%s> not registered %s'\
                    % (self.__class__.__name__, str(sandesh._uve_type_maps._uve_global_map)))
                sandesh.drop_tx_sandesh(self,
                    SandeshTxDropReason.ValidationFailed)
                return -1
            self._seqnum = self.next_seqnum()
            if not uve_type_map.update_uve(self):
                sandesh._logger.error('Failed to update sandesh in cache')
                sandesh.drop_tx_sandesh(self,
                    SandeshTxDropReason.ValidationFailed)
                return -1
        self._context = context
        self._more = more
        if self._context.find('http://') == 0 or \
                self._context.find('https://') == 0:
            SandeshHttp.create_http_response(self, sandesh)
        else:
            if self.handle_test(sandesh):
                return 0
            if sandesh._client:
                if sandesh.is_sending_all_messages_disabled():
                    sandesh.drop_tx_sandesh(self,
                        SandeshTxDropReason.SendingDisabled, self.level())
                    return -1
                # SandeshUVE has an implicit send level of SandeshLevel.SYS_UVE
                # which is irrespective of the level set by the user in the
                # send. This is needed so that the send queue does not grow
                # unbounded. Once the send queue's sending level reaches
                # SandeshLevel.SYS_UVE we will reset the connection to the
                # collector to initiate resync of the UVE cache
                if SandeshLevel.SYS_UVE >= sandesh.send_level():
                    sandesh._client.close_sm_session()
                sandesh._client.send_uve_sandesh(self)
            else:
                sandesh._logger.debug(self.log())
        return 0
    # end send

# end class SandeshUVE


class SandeshDynamicUVE(SandeshUVE):

    def __init__(self):
        SandeshUVE.__init__(self)
    # end __init__

    def update_uve(self, cache_data):
        if self.data.deleted is not None:
            cache_data.deleted = self.data.deleted
        if self.data.elements is not None:
            cache_data.elements = OrderedDict(sorted(
                self.data.elements.items()))
            self.data.elements = copy.deepcopy(cache_data.elements)
        return cache_data
    # end update_uve

# end class SandeshDynamicUVE


class SandeshAlarm(SandeshUVE):

    def __init__(self):
        SandeshUVE.__init__(self)
        self._type = SandeshType.ALARM
    # end __init__

    def send(self, isseq=False, seqno=0, context='',
             more=False, sandesh=sandesh_global):
        try:
            if not isseq and self.data.alarms:
                for alarm in self.data.alarms:
                    token = {'host_ip': sandesh.host_ip(),
                             'http_port': sandesh._http_server.get_port(),
                             'timestamp': alarm.timestamp}
                    alarm.token = base64.b64encode(json.dumps(token))
        except Exception as e:
            sandesh._logger.error('Failed to encode token for sandesh alarm: %s'
                                  % (str(e)))
            sandesh.drop_tx_sandesh(self, SandeshTxDropReason.ValidationFailed)
            return -1
        else:
            return super(SandeshAlarm, self).send(isseq, seqno, context,
                                                  more, sandesh)
    # end send

# end class SandeshAlarm


class SandeshTrace(Sandesh):

    def __init__(self, type):
        Sandesh.__init__(self)
        self._type = type
        self._more = False
        self._level = SandeshLevel.SYS_DEBUG
    # end __init__

    def send_trace(self, context='', more=False,
                   sandesh=sandesh_global):
        try:
            self.validate()
        except e:
            sandesh.drop_tx_sandesh(self, SandeshTxDropReason.ValidationFailed)
            return -1
        self._context = context
        self._more = more
        if self._context.find('http://') == 0 or \
                self._context.find('https://') == 0:
            SandeshHttp.create_http_response(self, sandesh)
        else:
            if self.handle_test(sandesh):
                return 0
            sandesh.send_sandesh(self)
        return 0
    # end send_trace

    def trace_msg(self, name, sandesh=sandesh_global):
        if sandesh._trace.IsTraceOn() and sandesh._trace.IsTraceBufOn(name):
            # store the trace buffer name in category
            self._category = name
            self._seqnum = sandesh._trace.TraceWrite(name, self)
            if sandesh.is_local_logging_enabled() and \
                    sandesh.is_trace_print_enabled():
                sandesh._logger.log(
                    sand_logger.SandeshLogger.get_py_logger_level(
                        self.level()), self.log())
    # end trace_msg

# end class SandeshTrace
