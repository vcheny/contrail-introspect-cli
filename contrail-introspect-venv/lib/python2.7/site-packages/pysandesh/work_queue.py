#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Work Queue
#

import gevent
from gevent.queue import Queue, Empty
import bisect


class Runner(object):

    def __init__(self, work_queue, max_work_load):
        self._work_q = work_queue
        self._max_work_load = max_work_load
        self._running = False
    # end __init__

    def start(self):
        if not self._running:
            self._running = True
            gevent.spawn(self._do_work)
    # end start

    def running(self):
        return self._running
    # end running

    def _do_work(self):
        while True:
            work_load = self._max_work_load
            work_item = self._work_q.dequeue()
            while work_item:
                self._work_q.worker(work_item)
                work_load -= 1
                if work_load == 0:
                    break
                work_item = self._work_q.dequeue()

            if self._work_q.runner_done():
                self._running = False
                break
            else:
                # yield
                gevent.sleep()
    # end _do_work

# end class Runner


class WaterMark(object):

    def __init__(self, size, callback):
        self.size = size
        self.callback = callback
    # end __init__

    def __eq__(self, other):
        return self.size == other.size
    # end __eq__

    def __lt__(self, other):
        return self.size < other.size
    # end __lt__

    def __hash__(self):
        return self.size
    # end __hash__

# end class WaterMark


class WorkQueue(object):

    _MAX_QUEUE_SIZE = 1024
    _MAX_WORKLOAD = 16

    def __init__(self, worker, start_runner=None,
                 max_qsize=None, max_work_load=None):
        self.worker = worker
        self._start_runner = start_runner
        self._max_qsize = max_qsize or WorkQueue._MAX_QUEUE_SIZE
        self._max_work_load = max_work_load or WorkQueue._MAX_WORKLOAD
        self._bounded = False
        self._queue = Queue()
        self._qsize = 0
        self._num_enqueues = 0
        self._num_dequeues = 0
        self._drops = 0
        self._high_watermarks = None
        self._low_watermarks = None
        self._hwm_index = -1
        self._lwm_index = -1
        self._runner = Runner(self, self._max_work_load)
        self._max_qlen = 0
    # end __init__

    def set_bounded(self, bounded):
        self._bounded = bounded
    # end set_bounded

    def bounded(self):
        return self._bounded
    # end bounded

    def set_high_watermarks(self, high_wm):
        # weed out duplicates and store the watermarks in sorted order
        self._high_watermarks = list(sorted(set(high_wm)))
        self._set_watermark_indices(-1, -1)
    # end set_high_watermarks

    def high_watermarks(self):
        return self._high_watermarks
    # end high_watermarks

    def set_low_watermarks(self, low_wm):
        # weed out duplicates and store the watermarks in sorted order
        self._low_watermarks = list(sorted(set(low_wm)))
        self._set_watermark_indices(-1, -1)
    # end set_low_watermarks

    def low_watermarks(self):
        return self._low_watermarks
    # end low_watermarks

    def watermark_indices(self):
        return self._hwm_index, self._lwm_index
    # end watermark_indices

    def enqueue(self, work_item):
        if self.increment_queue_size(work_item) > self._max_qlen:
            self._max_qlen = self._qsize
        if self._bounded:
            if self._qsize > self._max_qsize:
                self.decrement_queue_size(work_item)
                self._max_qlen = self._qsize
                self._drops += 1
                return False
        self._num_enqueues += 1
        self._process_high_watermarks()
        self._queue.put(work_item)
        self.may_be_start_runner()
        return True
    # end enqueue

    def dequeue(self):
        try:
            work_item = self._queue.get_nowait()
        except Empty:
            work_item = None
        else:
            self.decrement_queue_size(work_item)
            self._num_dequeues += 1
            self._process_low_watermarks()
        return work_item
    # end dequeue

    def increment_queue_size(self, work_item):
        self._qsize += 1
        return self._qsize
    # end increment_queue_size

    def decrement_queue_size(self, work_item):
        self._qsize -= 1
    # end decrement_queue_size

    def size(self):
        return self._qsize
    # end size

    def max_qlen(self):
        return self._max_qlen

    def may_be_start_runner(self):
        if self._queue.empty() or \
           (self._start_runner and not self._start_runner()):
            return
        self._runner.start()
    # end may_be_start_runner

    def runner_done(self):
        if self._queue.empty() or \
           (self._start_runner and not self._start_runner()):
            return True
        return False
    # end runner_done

    def is_queue_empty(self):
        if self._queue.empty():
            return True
        return False
    # end is_queue_empty

    def num_enqueues(self):
        return self._num_enqueues
    # end num_enqueues

    def num_dequeues(self):
        return self._num_dequeues
    # end num_dequeues

    def drops(self):
        return self._drops
    # end drops

    def runner(self):
        return self._runner
    # end runner

    def _set_watermark_indices(self, hwm_index, lwm_index):
        self._hwm_index = hwm_index
        self._lwm_index = lwm_index
    # end _set_watermark_indices

    def _process_high_watermarks(self):
        if not self._high_watermarks:
            return
        # Check if we have crossed any high watermarks.
        # Find the index of the first element greater than self._qsize
        # in self._high_watermarks.
        index = bisect.bisect_right(self._high_watermarks,
                                    WaterMark(self._qsize, None))
        # If the first element > qsize, then we have not crossed any
        # high watermark.
        if index == 0:
            return
        # We have crossed (index-1)th watermark in the list.
        hwm_index = index - 1
        if hwm_index == self._hwm_index:
            return
        self._set_watermark_indices(hwm_index, hwm_index+1)
        # Now invoke the watermark callback
        self._high_watermarks[self._hwm_index].callback(self._qsize)
    # end _process_high_watermarks

    def _process_low_watermarks(self):
        if not self._low_watermarks:
            return
        # Check if we have crossed any low watermarks.
        # Find the index of the first element not less than self._qsize
        # in self._low_watermarks.
        index = bisect.bisect_left(self._low_watermarks,
                                   WaterMark(self._qsize, None))
        # If there is no element >= qsize, then we have not crossed any
        # low watermark.
        if index == len(self._low_watermarks):
            return
        lwm_index = index
        if lwm_index == self._lwm_index:
            return
        self._set_watermark_indices(lwm_index-1, lwm_index)
        # Now invoke the watermark callback
        self._low_watermarks[self._lwm_index].callback(self._qsize)
    # end _process_low_watermarks

# end class WorkQueue
