#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Sandesh Client
#

from sandesh_connection import SandeshConnection
from sandesh_logger import SandeshLogger
from transport import TTransport
from protocol import TXMLProtocol
from sandesh_uve import SandeshUVETypeMaps
from gen_py.sandesh.ttypes import SandeshTxDropReason, SandeshRxDropReason
from util import UTCTimestampUsec

class SandeshClient(object):
    _INITIAL_SM_SESSION_CLOSE_INTERVAL_MSEC = 10 * 1000;
    _MAX_SM_SESSION_CLOSE_INTERVAL_MSEC = 60 * 1000;

    def __init__(self, sandesh):
        self._sandesh_instance = sandesh
        self._logger = sandesh._logger
        self._connection = None
        self._session_close_interval_msec = 0
        self._session_close_time_usec = 0
    #end __init__

    @staticmethod
    def _do_close_sm_session(now_usec, last_close_usec,
                            last_close_interval_usec):
        # If this is the first time, we will accept the next close
        # only after the initial close interval time
        if last_close_interval_usec == 0 or last_close_usec == 0:
            return (True,
                SandeshClient._INITIAL_SM_SESSION_CLOSE_INTERVAL_MSEC)
        assert now_usec >= last_close_usec
        time_since_close_usec = now_usec - last_close_usec
        # We will ignore close events receive before the last close
        # interval is finished
        if time_since_close_usec <= last_close_interval_usec:
            return (False, 0)
        # We will double the close interval time if we get a close
        # event between last close interval and 2 * last close interval.
        # If the close event is between 2 * last close interval and
        # 4 * last close interval, then the close interval will be
        # same as the current close interval. If the close event is
        # after 4 * last close interval, then we will reset the close
        # interval to the initial close interval
        if (time_since_close_usec > last_close_interval_usec) and \
                (time_since_close_usec <= 2 * last_close_interval_usec):
            nclose_interval_msec = (2 * last_close_interval_usec)/1000
            close_interval_msec = min(nclose_interval_msec,
                SandeshClient._MAX_SM_SESSION_CLOSE_INTERVAL_MSEC)
            return (True, close_interval_msec)
        elif (2 * last_close_interval_usec <= time_since_close_usec) and \
                (time_since_close_usec <= 4 * last_close_interval_usec):
            close_interval_msec = last_close_interval_usec/1000;
            return (True, close_interval_msec)
        else:
            return (True,
                SandeshClient._INITIAL_SM_SESSION_CLOSE_INTERVAL_MSEC)
    #end _do_close_sm_session

    # Public functions

    def initiate(self, collectors):
        stats_collector = self._sandesh_instance.config().stats_collector
        self._connection = SandeshConnection(self._sandesh_instance, self,
                                             collectors, stats_collector)
    #end initiate

    def session_close_interval_msec(self):
        return self._session_close_interval_msec
    #end session_close_interval_msec

    def session_close_time_usec(self):
        return self._session_close_time_usec
    #end session_close_time_usec

    def set_collectors(self, collectors):
        self._connection.set_collectors(collectors)
    # end set_collectors

    def connection(self):
        return self._connection
    #end connection

    def send_sandesh(self, sandesh):
        if (self._connection.session() is not None) and \
                (self._sandesh_instance._module is not None) and \
                (self._sandesh_instance._module != ""):
            self._connection.session().enqueue_sandesh(sandesh)
        else:
            if (self._connection.session() is None):
                self._sandesh_instance.drop_tx_sandesh(sandesh,
                    SandeshTxDropReason.NoSession)
            else:
                self._sandesh_instance.drop_tx_sandesh(sandesh,
                    SandeshTxDropReason.ClientSendFailed)
        return 0
    #end send_sandesh

    def send_uve_sandesh(self, uve_sandesh):
        self._connection.statemachine().on_sandesh_uve_msg_send(uve_sandesh)
    #end send_uve_sandesh

    def close_sm_session(self):
        connection = self._connection
        if not connection:
            return False
        session = connection.session()
        if not session:
            return False
        now_usec = UTCTimestampUsec()
        (close, close_interval_msec) = self._do_close_sm_session(now_usec,
            self._session_close_time_usec,
            self._session_close_interval_msec * 1000)
        if close:
            self._session_close_time_usec = now_usec
            self._session_close_interval_msec = close_interval_msec
            session.close()
            return True
        return False
   #end close_sm_session

    def handle_sandesh_msg(self, sandesh_name, sandesh_xml, msg_len):
        transport = TTransport.TMemoryBuffer(sandesh_xml)
        protocol_factory = TXMLProtocol.TXMLProtocolFactory()
        protocol = protocol_factory.getProtocol(transport)
        sandesh_req = self._sandesh_instance.get_sandesh_request_object(sandesh_name)
        if sandesh_req:
            if sandesh_req.read(protocol) == -1:
                self._sandesh_instance.update_rx_stats(sandesh_name, msg_len,
                    SandeshRxDropReason.DecodingFailed)
                self._logger.error('Failed to decode sandesh request "%s"' \
                    % (sandesh_name))
            else:
                self._sandesh_instance.update_rx_stats(sandesh_name, msg_len)
                self._sandesh_instance.enqueue_sandesh_request(sandesh_req)
        else:
            self._sandesh_instance.update_rx_stats(sandesh_name, msg_len,
                SandeshRxDropReason.CreateFailed)
    #end handle_sandesh_msg

    def handle_sandesh_ctrl_msg(self, sandesh_ctrl_msg):
        uve_type_map = {}
        self._logger.debug('Number of uve types in sandesh control message is %d' % (len(sandesh_ctrl_msg.type_info)))
        for type_info in sandesh_ctrl_msg.type_info:
            uve_type_map[type_info.type_name] = type_info.seq_num
        self._sandesh_instance._uve_type_maps.sync_all_uve_types(uve_type_map, self._sandesh_instance)
    #end handle_sandesh_ctrl_msg

#end class SandeshClient
