#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Sandesh Session
#

import socket
import sys
from functools import partial
from transport import TTransport
from protocol import TXMLProtocol, TJSONProtocol
from work_queue import WorkQueue, WaterMark
from ssl_session import SslSession
from sandesh_logger import SandeshLogger
from gen_py.sandesh.ttypes import SandeshLevel, SandeshType, SandeshTxDropReason

_XML_SANDESH_OPEN = '<sandesh length="0000000000">'
_XML_SANDESH_OPEN_ATTR_LEN = '<sandesh length="'
_XML_SANDESH_OPEN_END = '">'
_XML_SANDESH_CLOSE = '</sandesh>'


class StatsClient(object):

    def __init__(self, session, stats_collector):
        self._logger = session._logger
        if not ':' in stats_collector:
            self._stats_server = stats_collector
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        else:
            remote_endpoint = stats_collector.rsplit(':',1)
            if len(remote_endpoint) != 2:
                self._logger.error('INVALID STATS COLLECTOR CONFIGURATION')
            self._stats_server = (remote_endpoint[0], int(remote_endpoint[1]))
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._is_connected = False

    def initiate(self):
        try:
            self._socket.connect(self._stats_server)
            self._is_connected = True
        except Exception as e:
            self._logger.error('Error connecting to stats server: ' + str(e))

    def close(self):
        self._is_connected = False
        self._socket.close()

    def send_msg(self, sandesh):
        transport = TTransport.TMemoryBuffer()
        protocol_factory = TJSONProtocol.TJSONProtocolFactory()
        protocol = protocol_factory.getProtocol(transport)
        # write the sandesh
        if sandesh.write(protocol) < 0:
            self._logger.error('Write Json failed')
            return -1
        # get the message
        msg = transport.getvalue()
        if not msg:
            self._logger.error('Write Json failed')
            return -1
        # send the message
        self.send_buf(msg)
        return 0

    def send_buf(self, buf):
        if not self._is_connected:
            self.initiate()
            if not self._is_connected:
                return
        try:
            ret = self._socket.sendall(buf)
        except Exception as e:
            self._is_connected = False
            self._logger.error('Error Sending data to external collector: ' +
                               str(e))
        return

class SandeshReader(object):

    _READ_OK = 0
    _READ_ERR = -1

    def __init__(self, session, sandesh_msg_handler):
        self._session = session
        self._sandesh_instance = session.sandesh_instance()
        self._sandesh_msg_handler = sandesh_msg_handler
        self._read_buf = ''
        self._sandesh_len = 0
        self._logger = session._logger
    # end __init__

    # Public functions

    def read_msg(self, rcv_buf):
        self._read_buf += rcv_buf
        while True:
            (ret, sandesh) = self._extract_sandesh()
            if ret < 0:
                self._logger.error('Failed to extract sandesh')
                return self._READ_ERR
            if not sandesh:
                # read more data
                self._logger.debug(
                    'Not enough data to extract sandesh. Read more data.')
                break
            # Call sandesh message handler
            self._sandesh_msg_handler(self._session, sandesh)
            self._read_buf = self._read_buf[self._sandesh_len:]
            self._sandesh_len = 0
            if not len(self._read_buf):
                break

        return self._READ_OK
    # end read_msg

    @staticmethod
    def extract_sandesh_header(sandesh_xml):
        transport = TTransport.TMemoryBuffer(sandesh_xml)
        protocol_factory = TXMLProtocol.TXMLProtocolFactory()
        protocol = protocol_factory.getProtocol(transport)

        from gen_py.sandesh.ttypes import SandeshHeader
        hdr = SandeshHeader()
        hdr_len = hdr.read(protocol)
        if hdr_len == -1:
            return (None, 0, None)
        # Extract the sandesh name
        (length, sandesh_name) = protocol.readSandeshBegin()
        if length == -1:
            return (hdr, hdr_len, None)
        return (hdr, hdr_len, sandesh_name)
    # end extract_sandesh_header

    # Private functions

    def _extract_sandesh(self):
        if not self._sandesh_len:
            (ret, length) = self._extract_sandesh_len()
            if ret < 0:
                return (self._READ_ERR, None)
            elif not length:
                return (self._READ_OK, None)
            self._sandesh_len = length
        if len(self._read_buf) < self._sandesh_len:
            return (self._READ_OK, None)
        # Sanity check
        sandesh_close_tag = self._read_buf[
            self._sandesh_len - len(_XML_SANDESH_CLOSE):self._sandesh_len]
        if sandesh_close_tag != _XML_SANDESH_CLOSE:
            return (self._READ_ERR, None)

        # Extract sandesh
        sandesh_begin = len(_XML_SANDESH_OPEN)
        sandesh_end = self._sandesh_len - len(_XML_SANDESH_CLOSE)
        sandesh = self._read_buf[sandesh_begin:sandesh_end]
        return (self._READ_OK, sandesh)
    # end _extract_sandesh

    def _extract_sandesh_len(self):
        # Do we have enough data to extract the sandesh length?
        if len(self._read_buf) < len(_XML_SANDESH_OPEN):
            self._logger.debug('Not enough data to extract sandesh length')
            return (self._READ_OK, 0)
        # Sanity checks
        if self._read_buf[:len(_XML_SANDESH_OPEN_ATTR_LEN)] != \
                _XML_SANDESH_OPEN_ATTR_LEN:
            return (self._READ_ERR, 0)
        if self._read_buf[len(_XML_SANDESH_OPEN) - len(_XML_SANDESH_OPEN_END):
                          len(_XML_SANDESH_OPEN)] != _XML_SANDESH_OPEN_END:
            return (self._READ_ERR, 0)
        len_str = self._read_buf[len(_XML_SANDESH_OPEN_ATTR_LEN):
                                 len(_XML_SANDESH_OPEN) -
                                 len(_XML_SANDESH_OPEN_END)]
        try:
            length = int(len_str)
        except ValueError:
            self._logger.error(
                'Invalid sandesh length [%s] in the received message' %
                (len_str))
            return (self._READ_ERR, 0)

        self._logger.debug('Extracted sandesh length: %s' % (len_str))
        return (self._READ_OK, length)
    # end _extract_sandesh_len

# end class SandeshReader


class SandeshWriter(object):

    _MAX_SEND_BUF_SIZE = 4096

    def __init__(self, session):
        self._session = session
        self._sandesh_instance = session.sandesh_instance()
        self._send_buf_cache = ''
        self._logger = session._logger
    # end __init__

    # Public functions

    @staticmethod
    def encode_sandesh(sandesh, sandesh_instance=None):
        transport = TTransport.TMemoryBuffer()
        protocol_factory = TXMLProtocol.TXMLProtocolFactory()
        protocol = protocol_factory.getProtocol(transport)

        from gen_py.sandesh.ttypes import SandeshHeader

        sandesh_hdr = SandeshHeader(sandesh.scope(),
                                    sandesh.timestamp(),
                                    sandesh.module(),
                                    sandesh.source_id(),
                                    sandesh.context(),
                                    sandesh.seqnum(),
                                    sandesh.versionsig(),
                                    sandesh.type(),
                                    sandesh.hints(),
                                    sandesh.level(),
                                    sandesh.category(),
                                    sandesh.node_type(),
                                    sandesh.instance_id())
        # write the sandesh header
        if sandesh_hdr.write(protocol) < 0:
            if sandesh_instance is not None:
                sandesh_instance.drop_tx_sandesh(sandesh,
                    SandeshTxDropReason.HeaderWriteFailed)
            return None
        # write the sandesh
        if sandesh.write(protocol) < 0:
            if sandesh_instance is not None:
                sandesh_instance.drop_tx_sandesh(sandesh,
                    SandeshTxDropReason.WriteFailed)
            return None
        # get the message
        msg = transport.getvalue()
        # calculate the message length
        msg_len = len(_XML_SANDESH_OPEN) + len(msg) + len(_XML_SANDESH_CLOSE)
        len_width = len(_XML_SANDESH_OPEN) - \
            (len(_XML_SANDESH_OPEN_ATTR_LEN) + len(_XML_SANDESH_OPEN_END))
        # pad the length with leading 0s
        len_str = (str(msg_len)).zfill(len_width)
        encoded_buf = _XML_SANDESH_OPEN_ATTR_LEN + len_str + \
            _XML_SANDESH_OPEN_END + msg + _XML_SANDESH_CLOSE
        return encoded_buf
    # end encode_sandesh

    def send_msg(self, sandesh, more):
        send_buf = self.encode_sandesh(sandesh)
        if send_buf is None:
            self._logger.error('Failed to send sandesh')
            return -1
        # update sandesh tx stats
        self._sandesh_instance.msg_stats().update_tx_stats(
            sandesh.__class__.__name__, len(send_buf))
        if more:
            self._send_msg_more(send_buf)
        else:
            self._send_msg_all(send_buf)
        return 0
    # end send_msg

    # Private functions

    def _send_msg_more(self, send_buf):
        self._send_buf_cache += send_buf
        if len(self._send_buf_cache) >= self._MAX_SEND_BUF_SIZE:
            # send the message
            self._send(self._send_buf_cache)
            # reset the cache
            self._send_buf_cache = ''
    # end _send_msg_more

    def _send_msg_all(self, send_buf):
        # send the message
        self._send(self._send_buf_cache + send_buf)
        # reset the cache
        self._send_buf_cache = ''
    # end _send_msg_all

    def _send(self, send_buf):
        if self._session.write(send_buf) < 0:
            self._logger.error('Error sending message')
    # end _send

# end class SandeshWriter


class SandeshSendQueue(WorkQueue):

    _SENDQ_WATERMARKS = [
        # (size, sandesh_level, is_high_watermark)
        (50*1024*1024, SandeshLevel.SYS_UVE,True),
        (30*1024*1024, SandeshLevel.SYS_EMERG, True),
        (20*1024*1024, SandeshLevel.SYS_ERR, True),
        (1*1024*1024, SandeshLevel.SYS_DEBUG, True),
        (35*1024*1024, SandeshLevel.SYS_EMERG, False),
        (25*1024*1024, SandeshLevel.SYS_ERR, False),
        (15*1024*1024, SandeshLevel.SYS_DEBUG, False),
        (2*1024, SandeshLevel.INVALID, False)]

    class Element(object):
        def __init__(self, sandesh):
            self.sandesh = sandesh
            self.size = sys.getsizeof(sandesh)
    # end class Element

    def increment_queue_size(self, element):
        self._qsize += element.size
        return self._qsize
    # end increment_queue_size

    def decrement_queue_size(self, element):
        self._qsize -= element.size
    # end decrement_queue_size

# end class SandeshSendQueue


class SandeshSession(SslSession):
    _KEEPALIVE_IDLE_TIME = 15  # in secs
    _KEEPALIVE_INTERVAL = 3  # in secs
    _KEEPALIVE_PROBES = 5
    _TCP_USER_TIMEOUT_OPT = 18
    _TCP_USER_TIMEOUT_VAL = 30000 # ms

    def __init__(self, sandesh_instance, server, event_handler,
                 sandesh_msg_handler):
        sandesh_config = sandesh_instance.config()
        super(SandeshSession, self).__init__(server,
            sandesh_config.sandesh_ssl_enable, sandesh_config.keyfile,
            sandesh_config.certfile, sandesh_config.ca_cert)
        self._dscp_value = sandesh_config.dscp_value
        self._sandesh_instance = sandesh_instance
        self._logger = sandesh_instance._logger
        self._event_handler = event_handler
        self._reader = SandeshReader(self, sandesh_msg_handler)
        self._writer = SandeshWriter(self)
        self._stats_client = None
        self._send_queue = SandeshSendQueue(self._send_sandesh,
                                            self._is_ready_to_send_sandesh)
        self._send_level = SandeshLevel.INVALID
        self.set_send_queue_watermarks(SandeshSendQueue._SENDQ_WATERMARKS)
    # end __init__

    def _set_send_level(self, count, sandesh_level):
        if self._send_level != sandesh_level:
            self._logger.info('Sandesh Send Level [%s] -> [%s]' % \
                              (SandeshLevel._VALUES_TO_NAMES[self._send_level],
                               SandeshLevel._VALUES_TO_NAMES[sandesh_level]))
            self._send_level = sandesh_level
    # end _set_send_level

    # Public functions

    def send_level(self):
        return self._send_level
    # end send_level

    def set_send_queue_watermarks(self, watermarks):
        # watermarks is a list of tuples
        # (size, sandesh_level, is_high_watermark)
        wm_callback = self._set_send_level
        high_wm = []
        low_wm = []
        for wm in watermarks:
            if wm[2] is True:
                high_wm.append(WaterMark(wm[0], partial(wm_callback,
                                    sandesh_level=wm[1])))
            else:
                low_wm.append(WaterMark(wm[0], partial(wm_callback,
                                    sandesh_level=wm[1])))
        self._send_queue.set_high_watermarks(high_wm)
        self._send_queue.set_low_watermarks(low_wm)
    # end set_send_queue_watermarks

    def set_stats_collector(self, stats_collector):
        self._stats_client = StatsClient(self, stats_collector)

    def sandesh_instance(self):
        return self._sandesh_instance
    # end sandesh_instance

    def is_send_queue_empty(self):
        return self._send_queue.is_queue_empty()
    # end is_send_queue_empty

    def is_connected(self):
        return self._connected
    # end is_connected

    def enqueue_sandesh(self, sandesh):
        self._send_queue.enqueue(SandeshSendQueue.Element(sandesh))
    # end enqueue_sandesh

    def send_queue(self):
        return self._send_queue
    # end send_queue

    def dscp_value(self):
        dscp = 0
        try:
            dscp = self._socket.getsockopt(socket.IPPROTO_IP, socket.IP_TOS)
        except :
            self._logger.error('Error fetching DSCP value from Sandesh session')
        return dscp
    # end dscp_value

    # Overloaded functions from SslSession

    def connect(self):
        super(SandeshSession, self).connect(timeout=5)
    # end connect

    def _on_read(self, buf):
        if self._reader.read_msg(buf) < 0:
            self._logger.error('SandeshReader Error. Close Collector session')
            self.close()
    # end _on_read

    def _handle_event(self, event):
        self._event_handler(self, event)
    # end _handle_event

    def _set_socket_options(self):
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, 'TCP_KEEPIDLE'):
            self._socket.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                self._KEEPALIVE_IDLE_TIME)
        if hasattr(socket, 'TCP_KEEPALIVE'):
            self._socket.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPALIVE,
                self._KEEPALIVE_IDLE_TIME)
        if hasattr(socket, 'TCP_KEEPINTVL'):
            self._socket.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPINTVL,
                self._KEEPALIVE_INTERVAL)
        if hasattr(socket, 'IP_TOS') and (self._dscp_value != 0):
            #The 'value' argument is expected to have DSCP value between 0 and
            #63 ie., in the lower order 6 bits of a byte. However, setsockopt
            #expects DSCP value in upper 6 bits of a byte. Hence left shift the
            #value by 2 digits before passing it to setsockopt
            value = self._dscp_value << 2
            self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, value)
        if hasattr(socket, 'TCP_KEEPCNT'):
            self._socket.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPCNT, self._KEEPALIVE_PROBES)
        try:
            self._socket.setsockopt(socket.IPPROTO_TCP,
                self._TCP_USER_TIMEOUT_OPT, self._TCP_USER_TIMEOUT_VAL)
        except:
            self._logger.error('setsockopt failed: option %d, value %d' %
                (self._TCP_USER_TIMEOUT_OPT, self._TCP_USER_TIMEOUT_VAL))
    # end _set_socket_options

    # Private functions

    def _send_sandesh(self, queue_element):
        sandesh = queue_element.sandesh
        if self._send_queue.is_queue_empty():
            more = False
        else:
            more = True
        if not self._connected:
            if self._sandesh_instance.is_logging_dropped_allowed(sandesh):
                self._logger.error(
                    "SANDESH: %s: %s" % ("Not connected", sandesh.log()))
            self._sandesh_instance.drop_tx_sandesh(sandesh,
                SandeshTxDropReason.SessionNotConnected)
            return
        if sandesh.is_logging_allowed(self._sandesh_instance):
            self._logger.log(
                SandeshLogger.get_py_logger_level(sandesh.level()),
                sandesh.log())
        self._writer.send_msg(sandesh, more)
        if self._stats_client and  sandesh.type() == SandeshType.UVE:
            self._stats_client.send_msg(sandesh)
    # end _send_sandesh

    def _is_ready_to_send_sandesh(self):
        return self._sandesh_instance.is_send_queue_enabled()
    # end _is_ready_to_send_sandesh

# end class SandeshSession
