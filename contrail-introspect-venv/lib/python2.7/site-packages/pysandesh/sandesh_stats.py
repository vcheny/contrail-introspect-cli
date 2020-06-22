#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# sandesh_stats.py
#

from pysandesh.sandesh_base import Sandesh
from pysandesh.gen_py.sandesh_uve.ttypes import SandeshMessageStats
from pysandesh.gen_py.sandesh.ttypes import SandeshTxDropReason, \
    SandeshRxDropReason

class SandeshMessageStatistics(object):

    def __init__(self):
        self._message_type_stats = {}
        self._aggregate_stats = SandeshMessageStats()
    # end __init__

    def message_type_stats(self):
        return self._message_type_stats
    # end message_type_stats

    def aggregate_stats(self):
        return self._aggregate_stats
    # end aggregate_stats

    def update_tx_stats(self, message_type, nbytes,
                        drop_reason=SandeshTxDropReason.NoDrop):
        if SandeshTxDropReason.MinDropReason < drop_reason < \
           SandeshTxDropReason.MaxDropReason:
            try:
                message_stats = self._message_type_stats[message_type]
            except KeyError:
                message_stats = SandeshMessageStats()
                self._message_type_stats[message_type] = message_stats
            finally:
                self._update_tx_stats_internal(message_stats, nbytes,
                                               drop_reason)
                self._update_tx_stats_internal(self._aggregate_stats, nbytes,
                                               drop_reason)
                return True
        return False
    # end update_tx_stats

    def update_rx_stats(self, message_type, nbytes,
                        drop_reason=SandeshRxDropReason.NoDrop):
        if SandeshRxDropReason.MinDropReason < drop_reason < \
           SandeshRxDropReason.MaxDropReason:
            try:
                message_stats = self._message_type_stats[message_type]
            except KeyError:
                message_stats = SandeshMessageStats()
                self._message_type_stats[message_type] = message_stats
            finally:
                self._update_rx_stats_internal(message_stats, nbytes,
                                               drop_reason)
                self._update_rx_stats_internal(self._aggregate_stats, nbytes,
                                               drop_reason)
                return True
        return False
    # end update_rx_stats

    def _update_tx_stats_internal(self, msg_stats, nbytes, drop_reason):
        if drop_reason is SandeshTxDropReason.NoDrop:
            try:
                msg_stats.messages_sent += 1
                msg_stats.bytes_sent += nbytes
            except TypeError:
                msg_stats.messages_sent = 1
                msg_stats.bytes_sent = nbytes
        else:
            if msg_stats.messages_sent_dropped:
                msg_stats.messages_sent_dropped += 1
                msg_stats.bytes_sent_dropped += nbytes
            else:
                msg_stats.messages_sent_dropped = 1
                msg_stats.bytes_sent_dropped = nbytes
            if drop_reason is SandeshTxDropReason.ValidationFailed:
                if msg_stats.messages_sent_dropped_validation_failed:
                    msg_stats.messages_sent_dropped_validation_failed += 1
                    msg_stats.bytes_sent_dropped_validation_failed += nbytes
                else:
                    msg_stats.messages_sent_dropped_validation_failed = 1
                    msg_stats.bytes_sent_dropped_validation_failed = nbytes
            elif drop_reason is SandeshTxDropReason.QueueLevel:
                if msg_stats.messages_sent_dropped_queue_level:
                    msg_stats.messages_sent_dropped_queue_level += 1
                    msg_stats.bytes_sent_dropped_queue_level += nbytes
                else:
                    msg_stats.messages_sent_dropped_queue_level = 1
                    msg_stats.bytes_sent_dropped_queue_level = nbytes
            elif drop_reason is SandeshTxDropReason.NoClient:
                if msg_stats.messages_sent_dropped_no_client:
                    msg_stats.messages_sent_dropped_no_client += 1
                    msg_stats.bytes_sent_dropped_no_client += nbytes
                else:
                    msg_stats.messages_sent_dropped_no_client = 1
                    msg_stats.bytes_sent_dropped_no_client = nbytes
            elif drop_reason is SandeshTxDropReason.NoSession:
                if msg_stats.messages_sent_dropped_no_session:
                    msg_stats.messages_sent_dropped_no_session += 1
                    msg_stats.bytes_sent_dropped_no_session += nbytes
                else:
                    msg_stats.messages_sent_dropped_no_session = 1
                    msg_stats.bytes_sent_dropped_no_session = nbytes
            elif drop_reason is SandeshTxDropReason.NoQueue:
                if msg_stats.messages_sent_dropped_no_queue:
                    msg_stats.messages_sent_dropped_no_queue += 1
                    msg_stats.bytes_sent_dropped_no_queue += nbytes
                else:
                    msg_stats.messages_sent_dropped_no_queue = 1
                    msg_stats.bytes_sent_dropped_no_queue = nbytes
            elif drop_reason is SandeshTxDropReason.ClientSendFailed:
                if msg_stats.messages_sent_dropped_client_send_failed:
                    msg_stats.messages_sent_dropped_client_send_failed += 1
                    msg_stats.bytes_sent_dropped_client_send_failed += nbytes
                else:
                    msg_stats.messages_sent_dropped_client_send_failed = 1
                    msg_stats.bytes_sent_dropped_client_send_failed = nbytes
            elif drop_reason is SandeshTxDropReason.HeaderWriteFailed:
                if msg_stats.messages_sent_dropped_header_write_failed:
                    msg_stats.messages_sent_dropped_header_write_failed += 1
                    msg_stats.bytes_sent_dropped_header_write_failed += nbytes
                else:
                    msg_stats.messages_sent_dropped_header_write_failed = 1
                    msg_stats.bytes_sent_dropped_header_write_failed = nbytes
            elif drop_reason is SandeshTxDropReason.WriteFailed:
                if msg_stats.messages_sent_dropped_write_failed:
                    msg_stats.messages_sent_dropped_write_failed += 1
                    msg_stats.bytes_sent_dropped_write_failed += nbytes
                else:
                    msg_stats.messages_sent_dropped_write_failed = 1
                    msg_stats.bytes_sent_dropped_write_failed = nbytes
            elif drop_reason is SandeshTxDropReason.SessionNotConnected:
                if msg_stats.messages_sent_dropped_session_not_connected:
                    msg_stats.messages_sent_dropped_session_not_connected += 1
                    msg_stats.bytes_sent_dropped_session_not_connected += nbytes
                else:
                    msg_stats.messages_sent_dropped_session_not_connected = 1
                    msg_stats.bytes_sent_dropped_session_not_connected = nbytes
            elif drop_reason is SandeshTxDropReason.WrongClientSMState:
                if msg_stats.messages_sent_dropped_wrong_client_sm_state:
                    msg_stats.messages_sent_dropped_wrong_client_sm_state += 1
                    msg_stats.bytes_sent_dropped_wrong_client_sm_state += nbytes
                else:
                    msg_stats.messages_sent_dropped_wrong_client_sm_state = 1
                    msg_stats.bytes_sent_dropped_wrong_client_sm_state = nbytes
            elif drop_reason is SandeshTxDropReason.RatelimitDrop:
                if msg_stats.messages_sent_dropped_rate_limited:
                    msg_stats.messages_sent_dropped_rate_limited += 1
                    msg_stats.bytes_sent_dropped_rate_limited += nbytes
                else:
                    msg_stats.messages_sent_dropped_rate_limited = 1
                    msg_stats.bytes_sent_dropped_rate_limited = nbytes
            elif drop_reason is SandeshTxDropReason.SendingDisabled:
                if msg_stats.messages_sent_dropped_sending_disabled:
                    msg_stats.messages_sent_dropped_sending_disabled+= 1
                    msg_stats.bytes_sent_dropped_sending_disabled += nbytes
                else:
                    msg_stats.messages_sent_dropped_sending_disabled = 1
                    msg_stats.bytes_sent_dropped_sending_disabled = nbytes
            elif drop_reason is SandeshTxDropReason.SendingToSyslog:
                if msg_stats.messages_sent_dropped_sending_to_syslog:
                    msg_stats.messages_sent_dropped_sending_to_syslog += 1
                    msg_stats.bytes_sent_dropped_sending_to_syslog += nbytes
                else:
                    msg_stats.messages_sent_dropped_sending_to_syslog = 1
                    msg_stats.bytes_sent_dropped_sending_to_syslog = nbytes
            else:
                assert 0, 'Unhandled Tx drop reason <%s>' % (str(drop_reason))
    # end _update_tx_stats_internal

    def _update_rx_stats_internal(self, msg_stats, nbytes, drop_reason):
        if drop_reason is SandeshRxDropReason.NoDrop:
            if msg_stats.messages_received:
                msg_stats.messages_received += 1
                msg_stats.bytes_received += nbytes
            else:
                msg_stats.messages_received = 1
                msg_stats.bytes_received = nbytes
        else:
            if msg_stats.messages_received_dropped:
                msg_stats.messages_received_dropped += 1
                msg_stats.bytes_received_dropped += nbytes
            else:
                msg_stats.messages_received_dropped = 1
                msg_stats.bytes_received_dropped = nbytes
            if drop_reason is SandeshRxDropReason.QueueLevel:
                if msg_stats.messages_received_dropped_queue_level:
                    msg_stats.messages_received_dropped_queue_level += 1
                    msg_stats.bytes_received_dropped_queue_level += nbytes
                else:
                    msg_stats.messages_received_dropped_queue_level = 1
                    msg_stats.bytes_received_dropped_queue_level = nbytes
            elif drop_reason is SandeshRxDropReason.NoQueue:
                if msg_stats.messages_received_dropped_no_queue:
                    msg_stats.messages_received_dropped_no_queue += 1
                    msg_stats.bytes_received_dropped_no_queue += nbytes
                else:
                    msg_stats.messages_received_dropped_no_queue = 1
                    msg_stats.bytes_received_dropped_no_queue = nbytes
            elif drop_reason is SandeshRxDropReason.ControlMsgFailed:
                if msg_stats.messages_received_dropped_control_msg_failed:
                    msg_stats.messages_received_dropped_control_msg_failed += 1
                    msg_stats.bytes_received_dropped_control_msg_failed += nbytes
                else:
                    msg_stats.messages_received_dropped_control_msg_failed = 1
                    msg_stats.bytes_received_dropped_control_msg_failed = nbytes
            elif drop_reason is SandeshRxDropReason.CreateFailed:
                if msg_stats.messages_received_dropped_create_failed:
                    msg_stats.messages_received_dropped_create_failed += 1
                    msg_stats.bytes_received_dropped_create_failed += nbytes
                else:
                    msg_stats.messages_received_dropped_create_failed = 1
                    msg_stats.bytes_received_dropped_create_failed = nbytes
            elif drop_reason is SandeshRxDropReason.DecodingFailed:
                if msg_stats.messages_received_dropped_decoding_failed:
                    msg_stats.messages_received_dropped_decoding_failed += 1
                    msg_stats.bytes_received_dropped_decoding_failed += nbytes
                else:
                    msg_stats.messages_received_dropped_decoding_failed = 1
                    msg_stats.bytes_received_dropped_decoding_failed = nbytes
            else:
                assert 0, 'Unhandled Rx drop reason <%s>' % (str(drop_reason))
    # end _update_rx_stats_internal

# end class SandeshMessageStatistics
