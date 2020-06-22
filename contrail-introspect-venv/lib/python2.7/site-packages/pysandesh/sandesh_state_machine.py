#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Sandesh State Machine
#

import gevent
from fysom import Fysom
from work_queue import WorkQueue
from sandesh_logger import SandeshLogger
from sandesh_session import SandeshSession
from gen_py.sandesh.ttypes import SandeshTxDropReason

class State(object):
    # FSM states
    _IDLE = 'Idle'
    _DISCONNECT = 'Disconnect'
    _CONNECT = 'Connect'
    _CLIENT_INIT = 'ClientInit'
    _ESTABLISHED = 'Established'

#end class State

class Event(object):
    # FSM events
    _EV_START = 'EvStart'
    _EV_STOP = 'EvStop'
    _EV_IDLE_HOLD_TIMER_EXPIRED = 'EvIdleHoldTimerExpired'
    _EV_CONNECT_TIMER_EXPIRED = 'EvConnectTimerExpired'
    _EV_COLLECTOR_UNKNOWN = 'EvCollectorUnknown'
    _EV_TCP_CONNECTED = 'EvTcpConnected'
    _EV_TCP_CONNECT_FAIL = 'EvTcpConnectFail'
    _EV_TCP_CLOSE = 'EvTcpClose'
    _EV_COLLECTOR_CHANGE = 'EvCollectorChange'
    _EV_SANDESH_CTRL_MESSAGE_RECV = 'EvSandeshCtrlMessageRecv'
    _EV_SANDESH_UVE_SEND = 'EvSandeshUVESend'

    def __init__(self, event, session=None, msg=None, source=None,
                 collectors=None):
        self.event = event
        self.session = session
        self.msg = msg
        self.source = source
        self.collectors = collectors
    #end __init__

#end class Event

class SandeshStateMachine(object):

    _IDLE_HOLD_TIME = 4 # in seconds
    _CONNECT_TIME = 30 # in seconds

    def __init__(self, connection, logger, collectors, stats_collector):

        def _update_connection_state(e, status):
            from connection_info import ConnectionState
            from gen_py.process_info.ttypes import ConnectionType
            collector_addr = e.sm.collector()
            if collector_addr is None:
                collector_addr = ''
            ConnectionState.update(conn_type = ConnectionType.COLLECTOR,
                name = 'Collector',
                status = status,
                server_addrs = [collector_addr],
                message = '%s to %s on %s' % (e.src, e.dst, e.event))
        #end _update_connection_state

        def _connection_state_up(e):
            from gen_py.process_info.ttypes import ConnectionStatus
            _update_connection_state(e, ConnectionStatus.UP)
        #end _connection_state_up

        def _connection_state_down(e):
            from gen_py.process_info.ttypes import ConnectionStatus
            _update_connection_state(e, ConnectionStatus.DOWN)
        #end _connection_state_down

        def _connection_state_init(e):
            from gen_py.process_info.ttypes import ConnectionStatus
            _update_connection_state(e, ConnectionStatus.INIT)
        #end _connection_state_init

        def _on_idle(e):
            if e.sm._connect_timer is not None:
                e.sm._cancel_connect_timer()
            # clean up existing connection
            e.sm._delete_session()
            if e.sm._disable != True:
	        e.sm._start_idle_hold_timer()
            # update connection state
            _connection_state_down(e)
            e.sm._collector_name = None
            e.sm._connection.sandesh_instance().send_generator_info()
        #end _on_idle

        def _on_disconnect(e):
            # update connection state
            _connection_state_down(e)
        #end _on_disconnect

        def _on_connect(e):
            if e.sm._idle_hold_timer is not None:
                e.sm._cancel_idle_hold_timer()
            e.sm._collector_name = None
            # clean up existing connection
            e.sm._delete_session()
            collector = e.sm._get_next_collector()
            if collector is not None:
                # update connection state
                _connection_state_init(e)
                e.sm._create_session(collector)
                e.sm._start_connect_timer()
                e.sm._session.connect()
            else:
                e.sm.enqueue_event(Event(event = Event._EV_COLLECTOR_UNKNOWN))
        #end _on_connect

        def _on_client_init(e):
            e.sm._connects += 1
            gevent.spawn(e.sm._session.read)
            e.sm._connection.handle_initialized(e.sm._connects)
            e.sm._connection.sandesh_instance().send_generator_info()
            # update connection state
            _connection_state_init(e)
        #end _on_client_init
        
        def _on_established(e):
            e.sm._cancel_connect_timer()
            e.sm._collector_name = e.sm_event.source
            e.sm._connection.handle_sandesh_ctrl_msg(e.sm_event.msg)
            e.sm._connection.sandesh_instance().send_generator_info()
            # update connection state
            _connection_state_up(e)
        #end _on_established

        # FSM - Fysom
        self._fsm = Fysom({
                           'initial': {'state' : State._IDLE,
                                       'event' : Event._EV_START,
                                       'defer' : True
                                      },
                           'events': [
                                      # _IDLE
                                      {'name' : Event._EV_IDLE_HOLD_TIMER_EXPIRED,
                                       'src'  : State._IDLE,
                                       'dst'  : State._CONNECT
                                      },
                                      {'name' : Event._EV_COLLECTOR_CHANGE,
                                       'src'  : State._IDLE,
                                       'dst'  : State._CONNECT
                                      },
                                      {'name' : Event._EV_START,
                                       'src'  : State._IDLE,
                                       'dst'  : State._CONNECT
                                      },

                                      # _DISCONNECT 
                                      {'name' : Event._EV_COLLECTOR_CHANGE,
                                       'src'  : State._DISCONNECT,
                                       'dst'  : State._CONNECT
                                      },

                                      # _CONNECT
                                      {'name' : Event._EV_COLLECTOR_UNKNOWN,
                                       'src'  : State._CONNECT,
                                       'dst'  : State._DISCONNECT
                                      },
                                      {'name' : Event._EV_TCP_CONNECT_FAIL,
                                       'src'  : State._CONNECT,
                                       'dst'  : State._IDLE
                                      },
                                      {'name' : Event._EV_CONNECT_TIMER_EXPIRED,
                                       'src'  : State._CONNECT,
                                       'dst'  : State._IDLE
                                      },
                                      {'name' : Event._EV_COLLECTOR_CHANGE,
                                       'src'  : State._CONNECT,
                                       'dst'  : State._IDLE
                                      },
                                      {'name' : Event._EV_TCP_CONNECTED,
                                       'src'  : State._CONNECT,
                                       'dst'  : State._CLIENT_INIT
                                      },

                                      # _CLIENT_INIT
                                      {'name' : Event._EV_CONNECT_TIMER_EXPIRED,
                                       'src'  : State._CLIENT_INIT,
                                       'dst'  : State._IDLE
                                      },
                                      {'name' : Event._EV_TCP_CLOSE,
                                       'src'  : State._CLIENT_INIT,
                                       'dst'  : State._IDLE
                                      },
                                      {'name' : Event._EV_COLLECTOR_CHANGE,
                                       'src'  : State._CLIENT_INIT,
                                       'dst'  : State._IDLE
                                      },
                                      {'name' : Event._EV_SANDESH_CTRL_MESSAGE_RECV,
                                       'src'  : State._CLIENT_INIT,
                                       'dst'  : State._ESTABLISHED
                                      },

                                      # _ESTABLISHED
                                      {'name' : Event._EV_TCP_CLOSE,
                                       'src'  : State._ESTABLISHED,
                                       'dst'  : State._CONNECT
                                      },
                                      {'name' : Event._EV_STOP,
                                       'src'  : State._ESTABLISHED,
                                       'dst'  : State._IDLE
                                      },
                                      {'name' : Event._EV_COLLECTOR_CHANGE,
                                       'src'  : State._ESTABLISHED,
                                       'dst'  : State._CONNECT
                                      }
                                     ],
                           'callbacks': {
                                         'on' + State._IDLE : _on_idle,
                                         'on' + State._CONNECT : _on_connect,
                                         'on' + State._CLIENT_INIT : _on_client_init,
                                         'on' + State._ESTABLISHED : _on_established,
                                        }
                          })

        self._connection = connection
        self._session = None
        self._connects = 0
        self._disable = False
        self._idle_hold_timer = None
        self._connect_timer = None
        self._collectors = collectors
        self._stats_collector = stats_collector
        self._collector_name = None
        self._collector_index = -1
        self._logger = logger
        self._event_queue = WorkQueue(self._dequeue_event,
                                      self._is_ready_to_dequeue_event)
    #end __init__

    # Public functions

    def initialize(self):
        self.enqueue_event(Event(event = Event._EV_START))
    #end initialize

    def session(self):
        return self._session 
    #end session 

    def state(self):
        return self._fsm.current
    #end state 

    def shutdown(self):
        self._disable = True
        self.enqueue_event(Event(event = Event._EV_STOP))
    #end shutdown

    def set_admin_state(self, down):
        if down == True:
            self._disable = True
            self.enqueue_event(Event(event = Event._EV_STOP))
        else:
            self._disable = False
            self.enqueue_event(Event(event = Event._EV_START))
    #end set_admin_state

    def connect_count(self):
        return self._connects
    #end connect_count

    def collector(self):
        if self._collector_index is -1:
            return None
        return self._collectors[self._collector_index]
    # end collector

    def collector_name(self):
        return self._collector_name
    # end collector_name

    def collectors(self):
        return self._collectors
    # end collectors

    def enqueue_event(self, event):
        self._event_queue.enqueue(event)
    #end enqueue_event

    def on_session_event(self, session, event):
        if session is not self._session:
            self._logger.error("Ignore session event [%d] received for old session" % (event))
            return 
        if SandeshSession.SESSION_ESTABLISHED == event:
            self._logger.info("Session Event: TCP Connected")
            self.enqueue_event(Event(event = Event._EV_TCP_CONNECTED,
                                     session = session))
        elif SandeshSession.SESSION_ERROR == event:
            self._logger.error("Session Event: TCP Connect Fail")
            self.enqueue_event(Event(event = Event._EV_TCP_CONNECT_FAIL,
                                     session = session))
        elif SandeshSession.SESSION_CLOSE == event:
            self._logger.error("Session Event: TCP Connection Closed")
            self.enqueue_event(Event(event = Event._EV_TCP_CLOSE,
                                     session = session))
        else:
            self._logger.error("Received unknown session event [%d]" % (event))
    #end on_session_event

    def on_sandesh_ctrl_msg_receive(self, session, sandesh_ctrl, collector):
        if sandesh_ctrl.success == True:
            self.enqueue_event(Event(event = Event._EV_SANDESH_CTRL_MESSAGE_RECV, 
                                     session = session,
                                     msg = sandesh_ctrl,
                                     source = collector))
        else:
            # Negotiation with the Collector failed, reset the 
            # connection and retry after sometime.
            self._logger.error("Negotiation with the Collector %s failed." % (collector))
            self._session.close()
    #end on_sandesh_ctrl_msg_receive

    def on_sandesh_uve_msg_send(self, sandesh_uve):
        self.enqueue_event(Event(event = Event._EV_SANDESH_UVE_SEND,
                                 msg = sandesh_uve))
    #end on_sandesh_uve_msg_send

    # Private functions

    def _create_session(self, collector):
        assert self._session is None
        collector_ip_port = collector.split(':')
        server = (collector_ip_port[0], int(collector_ip_port[1]))
        self._session = SandeshSession(self._connection.sandesh_instance(),
                                       server,
                                       self.on_session_event,
                                       self._connection._receive_sandesh_msg)
        if self._stats_collector:
            self._session.set_stats_collector(self._stats_collector)
    #end _create_session

    def _delete_session(self):
        if self._session:
            if self._stats_collector:
                self._session.stats_client().close()
            self._session.close()
            self._session = None
            self._collector_name = None
    #end _delete_session 

    def _get_next_collector(self):
        if self._collector_index is -1:
            if not self._collectors:
                return None
            self._collector_index = 0
        else:
            self._collector_index += 1
            if self._collector_index == len(self._collectors):
                self._collector_index = 0
        return self._collectors[self._collector_index]
    # end _get_next_collector

    def _start_idle_hold_timer(self):
        if self._idle_hold_timer is None:
            if self._IDLE_HOLD_TIME:
                self._idle_hold_timer = gevent.spawn_later(self._IDLE_HOLD_TIME,
                                            self._idle_hold_timer_expiry_handler)
            else:
                self.enqueue_event(Event(event = Event._EV_IDLE_HOLD_TIMER_EXPIRED))
    #end _start_idle_hold_timer

    def _cancel_idle_hold_timer(self):
        if self._idle_hold_timer is not None:
            gevent.kill(self._idle_hold_timer)
            self._idle_hold_timer = None
    #end _cancel_idle_hold_timer

    def _idle_hold_timer_expiry_handler(self):
        self._idle_hold_timer = None
        self.enqueue_event(Event(event = Event._EV_IDLE_HOLD_TIMER_EXPIRED))
    #end _idle_hold_timer_expiry_handler
    
    def _start_connect_timer(self):
        if self._connect_timer is None:
            self._connect_timer = gevent.spawn_later(self._CONNECT_TIME,
                                        self._connect_timer_expiry_handler, 
                                        self._session)
    #end _start_connect_timer

    def _cancel_connect_timer(self):
        if self._connect_timer is not None:
            gevent.kill(self._connect_timer)
            self._connect_timer = None
    #end _cancel_connect_timer

    def _connect_timer_expiry_handler(self, session):
        self._connect_timer = None
        self.enqueue_event(Event(event = Event._EV_CONNECT_TIMER_EXPIRED,
                                 session = session))
    #end _connect_timer_expiry_handler

    def _is_ready_to_dequeue_event(self):
        return True
    #end _is_ready_to_dequeue_event

    def _log_event(self, event):
        if self._fsm.current == State._ESTABLISHED and \
           event.event == Event._EV_SANDESH_UVE_SEND:
           return False
        return True
    #end _log_event

    def _dequeue_event(self, event):
        if self._log_event(event):
            self._logger.info("Processing event[%s] in state[%s]" \
                              % (event.event, self._fsm.current))
        if event.session is not None and event.session is not self._session:
            self._logger.info("Ignore event [%s] received for old session" \
                              % (event.event))
            return
        if event.event == Event._EV_COLLECTOR_CHANGE:
            collector = self.collector()
            self._collector_index = -1
            collector_list_change = False
            if self._collectors != event.collectors:
                self._collectors = event.collectors
                collector_list_change = True
            if self._collectors and self._collectors[0] == collector:
                self._collector_index = 0
                self._logger.info("No change in active collector. "
                    "Ignore event [%s]" % (event.event))
                if collector_list_change:
                    # update the collector_list in the ModuleClientState UVE
                    self._connection.sandesh_instance().send_generator_info()
                return
            self._connection.sandesh_instance().send_generator_info()
        if event.event == Event._EV_SANDESH_UVE_SEND:
            if self._fsm.current == State._ESTABLISHED or self._fsm.current == State._CLIENT_INIT:
                self._connection.handle_sandesh_uve_msg(event.msg)
            else:
                self._connection.sandesh_instance().drop_tx_sandesh(event.msg,
                    SandeshTxDropReason.WrongClientSMState)
                self._logger.info("Discarding event[%s] in state[%s]" \
                                  % (event.event, self._fsm.current))
        elif event.event == Event._EV_SANDESH_CTRL_MESSAGE_RECV and \
                self._fsm.current == State._ESTABLISHED:
            self._connection.handle_sandesh_ctrl_msg(event.msg)
        elif self._fsm.cannot(event.event) is True:
            self._logger.info("Unconsumed event[%s] in state[%s]" \
                              % (event.event, self._fsm.current))
        else:
            prev_state = self.state()
            getattr(self._fsm, event.event)(sm = self, sm_event = event)
            # Log state transition
            self._logger.info("Sandesh Client: Event[%s] => State[%s] -> State[%s]" \
                              % (event.event, prev_state, self.state()))
    #end _dequeue_event

#end class SandeshStateMachine
