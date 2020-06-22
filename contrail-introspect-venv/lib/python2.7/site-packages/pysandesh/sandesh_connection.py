#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Sandesh Connection
#

import gevent
import os
from transport import TTransport
from protocol import TXMLProtocol
from sandesh_session import SandeshSession, SandeshReader
from sandesh_state_machine import SandeshStateMachine, Event
from sandesh_uve import SandeshUVETypeMaps
from gen_py.sandesh.ttypes import SandeshRxDropReason
from gen_py.sandesh.constants import *

class SandeshConnection(object):

    def __init__(self, sandesh_instance, client, collectors, stats_collector):
        self._sandesh_instance = sandesh_instance
        self._logger = sandesh_instance.logger()
        self._client = client
        # Collector name. Updated upon receiving the control message 
        # from the Collector during connection negotiation.
        self._admin_down = False
        self._state_machine = SandeshStateMachine(self, self._logger, 
                                                  collectors, stats_collector)
        self._state_machine.initialize()
    #end __init__

    # Public methods

    def session(self):
        return self._state_machine.session()
    #end session

    def statemachine(self):
        return self._state_machine
    #end statemachine

    def sandesh_instance(self):
        return self._sandesh_instance
    #end sandesh_instance

    def collectors(self):
        return self._state_machine.collectors()
    # end collectors

    def collector(self):
        return self._state_machine.collector()
    # end collector

    def collector_name(self):
        return self._state_machine.collector_name()
    # end collector_name

    def state(self):
        return self._state_machine.state()
    #end state

    def handle_initialized(self, count):
        uve_types = []
        uve_global_map = self._sandesh_instance._uve_type_maps.get_uve_global_map()
        for uve_type_key in uve_global_map.iterkeys():
            uve_types.append(uve_type_key)
        from gen_py.sandesh_ctrl.ttypes import SandeshCtrlClientToServer
        ctrl_msg = SandeshCtrlClientToServer(self._sandesh_instance.source_id(),
            self._sandesh_instance.module(), count, uve_types, os.getpid(), 0,
            self._sandesh_instance.node_type(), 
            self._sandesh_instance.instance_id())
        self._logger.debug('Send sandesh control message. uve type count # %d' % (len(uve_types)))
        ctrl_msg.request('ctrl', sandesh=self._sandesh_instance)
    #end handle_initialized

    def handle_sandesh_ctrl_msg(self, ctrl_msg):
        self._client.handle_sandesh_ctrl_msg(ctrl_msg)
    #end handle_sandesh_ctrl_msg

    def handle_sandesh_uve_msg(self, uve_msg):
        self._client.send_sandesh(uve_msg)
    #end handle_sandesh_uve_msg

    def set_admin_state(self, down):
        if self._admin_down != down:
            self._admin_down = down
            self._state_machine.set_admin_state(down)
    #end set_admin_state

    def set_collectors(self, collectors):
        self._state_machine.enqueue_event(Event(
            event=Event._EV_COLLECTOR_CHANGE, collectors=collectors))
    # end set_collectors

    # Private methods

    def _receive_sandesh_msg(self, session, msg):
        (hdr, hdr_len, sandesh_name) = SandeshReader.extract_sandesh_header(msg)
        if sandesh_name is None:
            self._sandesh_instance.msg_stats().update_rx_stats('__UNKNOWN__',
                len(msg), SandeshRxDropReason.DecodingFailed)
            self._logger.error('Failed to decode sandesh header for "%s"' % (msg))
            return
        if hdr.Hints & SANDESH_CONTROL_HINT:
            self._logger.debug('Received sandesh control message [%s]' % (sandesh_name))
            if sandesh_name != 'SandeshCtrlServerToClient':
                self._sandesh_instance.msg_stats().update_rx_stats(
                    sandesh_name, len(msg),
                    SandeshRxDropReason.ControlMsgFailed)
                self._logger.error('Invalid sandesh control message [%s]' % (sandesh_name))
                return
            transport = TTransport.TMemoryBuffer(msg[hdr_len:])
            protocol_factory = TXMLProtocol.TXMLProtocolFactory()
            protocol = protocol_factory.getProtocol(transport)
            from gen_py.sandesh_ctrl.ttypes import SandeshCtrlServerToClient
            sandesh_ctrl_msg = SandeshCtrlServerToClient()
            if sandesh_ctrl_msg.read(protocol) == -1:
                self._sandesh_instance.msg_stats().update_rx_stats(
                    sandesh_name, len(msg),
                    SandeshRxDropReason.DecodingFailed)
                self._logger.error('Failed to decode sandesh control message "%s"' %(msg))
            else:
                self._sandesh_instance.msg_stats().update_rx_stats(
                    sandesh_name, len(msg))
                self._state_machine.on_sandesh_ctrl_msg_receive(session, sandesh_ctrl_msg, 
                                                                hdr.Source)
        else:
            self._logger.debug('Received sandesh message [%s]' % (sandesh_name))
            self._client.handle_sandesh_msg(sandesh_name,
                msg[hdr_len:], len(msg))
    #end _receive_sandesh_msg

#end class SandeshConnection
