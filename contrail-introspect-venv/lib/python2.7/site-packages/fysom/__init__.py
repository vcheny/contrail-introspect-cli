# coding=utf-8
#
# fysom - pYthOn Finite State Machine - this is a port of Jake
#         Gordon's javascript-state-machine to python
#         https://github.com/jakesgordon/javascript-state-machine
#
# Copyright (C) 2011 Mansour Behabadi <mansour@oxplot.com>, Jake Gordon
#                                        and other contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import collections
import functools
import weakref
import types
import sys

__author__ = 'Mansour Behabadi'
__copyright__ = 'Copyright 2011, Mansour Behabadi and Jake Gordon'
__credits__ = ['Mansour Behabadi', 'Jake Gordon']
__license__ = 'MIT'
__version__ = '2.1.5'
__maintainer__ = 'Mansour Behabadi'
__email__ = 'mansour@oxplot.com'


WILDCARD = '*'
SAME_DST = '='


class FysomError(Exception):

    '''
        Raised whenever an unexpected event gets triggered.
        Optionally the event object can be attached to the exception
        in case of sharing event data.
    '''

    def __init__(self, msg, event=None):
        super(FysomError, self).__init__(msg)
        self.event = event


class Canceled(FysomError):

    '''
        Raised when an event is canceled due to the
        onbeforeevent handler returning False
    '''


def _weak_callback(func):
    '''
    Store a weak reference to a callback or method.
    '''
    if isinstance(func, types.MethodType):
        # Don't hold a reference to the object, otherwise we might create
        # a cycle.
        # Reference: http://stackoverflow.com/a/6975682
        # Tell coveralls to not cover this if block, as the Python 2.x case
        # doesn't test the 3.x code and vice versa.
        if sys.version_info[0] < 3:  # pragma: no cover
            # Python 2.x case
            obj_ref = weakref.ref(func.im_self)
            func_ref = weakref.ref(func.im_func)
        else:  # pragma: no cover
            # Python 3.x case
            obj_ref = weakref.ref(func.__self__)
            func_ref = weakref.ref(func.__func__)
        func = None

        def _callback(*args, **kwargs):
            obj = obj_ref()
            func = func_ref()
            if (obj is None) or (func is None):
                return
            return func(obj, *args, **kwargs)
        return _callback
    else:
        # We should be safe enough holding callback functions ourselves.
        return func


class Fysom(object):

    '''
        Wraps the complete finite state machine operations.
    '''

    def __init__(self, cfg={}, initial=None, events=None, callbacks=None,
                 final=None, **kwargs):
        '''
        Construct a Finite State Machine.

        Arguments:

            cfg         finite state machine specification,
                        a dictionary with keys 'initial', 'events', 'callbacks', 'final'

            initial     initial state

            events      a list of dictionaries (keys: 'name', 'src', 'dst')
                        or a list tuples (event name, source state or states,
                        destination state or states)

            callbacks   a dictionary mapping callback names to functions

            final       a state of the FSM where its is_finished() method returns True

        Named arguments override configuration dictionary.

        Example:

        >>> fsm = Fysom(events=[('tic', 'a', 'b'), ('toc', 'b', 'a')], initial='a')
        >>> fsm.current
        'a'
        >>> fsm.tic()
        >>> fsm.current
        'b'
        >>> fsm.toc()
        >>> fsm.current
        'a'

        '''
        if (sys.version_info[0] >= 3):
            super().__init__(**kwargs)
        cfg = dict(cfg)
        # override cfg with named arguments
        if "events" not in cfg:
            cfg["events"] = []
        if "callbacks" not in cfg:
            cfg["callbacks"] = {}
        if initial:
            cfg["initial"] = initial
        if final:
            cfg["final"] = final
        if events:
            cfg["events"].extend(list(events))
        if callbacks:
            cfg["callbacks"].update(dict(callbacks))
        # convert 3-tuples in the event specification to dicts
        events_dicts = []
        for e in cfg["events"]:
            if isinstance(e, collections.Mapping):
                events_dicts.append(e)
            elif hasattr(e, "__iter__"):
                name, src, dst = list(e)[:3]
                events_dicts.append({"name": name, "src": src, "dst": dst})
        cfg["events"] = events_dicts
        self._apply(cfg)

    def isstate(self, state):
        '''
            Returns if the given state is the current state.
        '''
        return self.current == state

    is_state = isstate

    def can(self, event):
        '''
            Returns if the given event be fired in the current machine state.
        '''
        return (
            event in self._map and
            ((self.current in self._map[event]) or WILDCARD in self._map[event]) and not
            hasattr(self, 'transition'))

    def cannot(self, event):
        '''
            Returns if the given event cannot be fired in the current state.
        '''
        return not self.can(event)

    def is_finished(self):
        '''
            Returns if the state machine is in its final state.
        '''
        return self._final and (self.current == self._final)

    def _apply(self, cfg):
        '''
            Does the heavy lifting of machine construction. More notably:
             >> Sets up the initial and finals states.
             >> Sets the event methods and callbacks into the same object namespace.
             >> Prepares the event to state transitions map.
        '''
        init = cfg['initial'] if 'initial' in cfg else None
        if self._is_base_string(init):
            init = {'state': init}

        self._final = cfg['final'] if 'final' in cfg else None

        events = cfg['events'] if 'events' in cfg else []
        callbacks = cfg['callbacks'] if 'callbacks' in cfg else {}
        tmap = {}
        self._map = tmap

        def add(e):
            '''
                Adds the event into the machine map.
            '''
            if 'src' in e:
                src = [e['src']] if self._is_base_string(
                    e['src']) else e['src']
            else:
                src = [WILDCARD]
            if e['name'] not in tmap:
                tmap[e['name']] = {}
            for s in src:
                tmap[e['name']][s] = e['dst']

        # Consider initial state as any other state that can have transition from none to
        # initial value on occurance of startup / init event ( if specified).
        if init:
            if 'event' not in init:
                init['event'] = 'startup'
            add({'name': init['event'], 'src': 'none', 'dst': init['state']})

        for e in events:
            add(e)

        # For all the events as present in machine map, construct the event
        # handler.
        for name in tmap:
            setattr(self, name, self._build_event(name))

        # For all the callbacks, register them into the current object
        # namespace.
        for name in callbacks:
            setattr(self, name, _weak_callback(callbacks[name]))

        self.current = 'none'

        # If initialization need not be deferred, trigger the event for
        # transition to initial state.
        if init and 'defer' not in init:
            getattr(self, init['event'])()

    def _build_event(self, event):
        '''
            For every event in the state machine, prepares the event handler and
            registers the same into current object namespace.
        '''
        def fn(*args, **kwargs):

            if hasattr(self, 'transition'):
                raise FysomError(
                    "event %s inappropriate because previous transition did not complete" % event)

            # Check if this event can be triggered in the current state.
            if not self.can(event):
                raise FysomError(
                    "event %s inappropriate in current state %s" % (event, self.current))

            # On event occurence, source will always be the current state.
            src = self.current
            # Finds the destination state, after this event is completed.
            dst = ((src in self._map[event] and self._map[event][src]) or
                   WILDCARD in self._map[event] and self._map[event][WILDCARD])
            if dst == SAME_DST:
                dst = src

            # Prepares the object with all the meta data to be passed to
            # callbacks.
            class _e_obj(object):
                pass
            e = _e_obj()
            e.fsm, e.event, e.src, e.dst = self, event, src, dst
            for k in kwargs:
                setattr(e, k, kwargs[k])

            setattr(e, 'args', args)

            # Try to trigger the before event, unless it gets canceled.
            if self._before_event(e) is False:
                raise Canceled(
                    "Cannot trigger event {0} because the onbefore{0} handler returns False".format(e.event))

            # Wraps the activities that must constitute a single successful
            # transaction.
            if self.current != dst:
                def _tran():
                    delattr(self, 'transition')
                    self.current = dst
                    self._enter_state(e)
                    self._change_state(e)
                    self._after_event(e)
                self.transition = _tran

                # Hook to perform asynchronous transition.
                if self._leave_state(e) is not False:
                    self.transition()
            else:
                self._reenter_state(e)
                self._after_event(e)

        fn.__name__ = str(event)
        fn.__doc__ = ("Event handler for an {event} event. This event can be " +
                      "fired if the machine is in {states} states.".format(
                          event=event, states=self._map[event].keys()))

        return fn

    def _before_event(self, e):
        '''
            Checks to see if the callback is registered before this event can be triggered.
        '''
        for fnname in ['onbefore' + e.event, 'on_before_' + e.event]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _after_event(self, e):
        '''
            Checks to see if the callback is registered for, after this event is completed.
        '''
        for fnname in ['onafter' + e.event, 'on' + e.event,
                       'on_after_' + e.event, 'on_' + e.event]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _leave_state(self, e):
        '''
            Checks to see if the machine can leave the current state and perform the transition.
            This is helpful if the asynchronous job needs to be completed before the machine can
            leave the current state.
        '''
        for fnname in ['onleave' + e.src, 'on_leave_' + e.src]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _enter_state(self, e):
        '''
            Executes the callback for onenter_state_ or on_state_.
        '''
        for fnname in ['onenter' + e.dst, 'on' + e.dst,
                       'on_enter_' + e.dst, 'on_' + e.dst]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _reenter_state(self, e):
        '''
            Executes the callback for onreenter_state_.
            This allows callbacks following reflexive transitions (i.e. where src == dst)
        '''
        for fnname in ['onreenter' + e.dst, 'on_reenter_' + e.dst]:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _change_state(self, e):
        '''
            A general change state callback. This gets triggered at the time of state transition.
        '''
        for fnname in ['onchangestate', 'on_change_state']:
            if hasattr(self, fnname):
                return getattr(self, fnname)(e)

    def _is_base_string(self, object):  # pragma: no cover
        '''
            Returns if the object is an instance of basestring.
        '''
        try:
            return isinstance(object, basestring)
        except NameError:
            return isinstance(object, str)

    def trigger(self, event, *args, **kwargs):
        '''
            Triggers the given event.
            The event can be triggered by calling the event handler directly, for ex: fsm.eat()
            but this method will come in handy if the event is determined dynamically and you have
            the event name to trigger as a string.
        '''
        if not hasattr(self, event):
            raise FysomError(
                "There isn't any event registered as %s" % event)
        return getattr(self, event)(*args, **kwargs)


class FysomGlobalMixin(object):
    GSM = None  # global state machine instance, override this

    def __init__(self, *args, **kwargs):
        super(FysomGlobalMixin, self).__init__(*args, **kwargs)
        if self.is_state('none'):
            _initial = self.GSM._initial
            if _initial and not _initial.get('defer'):
                self.trigger(_initial['event'])

    def __getattribute__(self, attr):
        '''
            Proxy public event methods to global machine if available.
        '''
        try:
            return super(FysomGlobalMixin, self).__getattribute__(attr)
        except AttributeError as err:
            if not attr.startswith('_'):
                gsm_attr = getattr(self.GSM, attr)
                if callable(gsm_attr):
                    return functools.partial(gsm_attr, self)
            raise  # pragma: no cover

    @property
    def current(self):
        '''
            Simulate the behavior of Fysom's "current" attribute.
        '''
        return self.GSM.current(self)

    @current.setter
    def current(self, state):
        setattr(self, self.GSM.state_field, state)


class FysomGlobal(object):
    '''
        Target to be used as global machine.
    '''

    def __init__(self, cfg={}, initial=None, events=None, callbacks=None,
                 final=None, state_field=None, **kwargs):
        '''
        Construct a Global Finite State Machine.

        Takes same arguments as Fysom and an additional state_field
        to specify which field holds the state to be processed.

        Difference with Fysom:

        1.  Initial state will only be automatically triggered for class
            derived with FysomGlobalMixin.
        2.  Conditions and conditional transition are implemented.
        3.  When an event/transition is canceled, the event object will
            be attached to the raised Canceled exception. By doing this,
            additional information can be passed through the exception.

        Example:

        class Model(FysomGlobalMixin, object):
            GSM = FysomGlobal(
                events=[('warn',  'green',  'yellow'),
                        {
                            'name': 'panic',
                            'src': ['green', 'yellow'],
                            'dst': 'red',
                            'cond': [  # can be function object or method name
                                'is_angry',  # by default target is "True"
                                {True: 'is_very_angry', 'else': 'yellow'}
                            ]
                        },
                        ('calm',  'red',    'yellow'),
                        ('clear', 'yellow', 'green')],
                initial='green',
                final='red',
                state_field='state'
            )

            def __init__(self):
                self.state = None
                super(Model, self).__init__()

            def is_angry(self, event):
                return True

            def is_very_angry(self, event):
                return False

        >>> obj = Model()
        >>> obj.current
        'green'
        >>> obj.warn()
        >>> obj.is_state('yellow')
        True
        >>> obj.panic()
        >>> obj.current
        'yellow'
        >>> obj.is_finished()
        False

        '''
        if sys.version_info[0] >= 3:
            super().__init__(**kwargs)
        cfg = dict(cfg)

        # state_field is required for global machine
        if not state_field:
            raise FysomError('state_field required for global machine')
        self.state_field = state_field

        if "events" not in cfg:
            cfg["events"] = []
        if "callbacks" not in cfg:
            cfg["callbacks"] = {}
        if initial:
            cfg['initial'] = initial
        if events:
            cfg["events"].extend(list(events))
        if callbacks:
            cfg["callbacks"].update(dict(callbacks))
        if final:
            cfg["final"] = final
        # convert 3-tuples in the event specification to dicts
        events_dicts = []
        for e in cfg["events"]:
            if isinstance(e, collections.Mapping):
                events_dicts.append(e)
            elif hasattr(e, "__iter__"):
                name, src, dst = list(e)[:3]
                events_dicts.append({"name": name, "src": src, "dst": dst})
        cfg["events"] = events_dicts

        self._map = {}  # different with Fysom's _map attribute
        self._callbacks = {}
        self._initial = None
        self._final = None
        self._apply(cfg)

    def _apply(self, cfg):
        def add(e):
            if 'src' in e:
                src = [e['src']] if self._is_base_string(
                    e['src']) else e['src']
            else:
                src = [WILDCARD]

            _e = {'src': set(src), 'dst': e['dst']}
            conditions = e.get('cond')
            if conditions:
                _e['cond'] = _c = []
                if self._is_base_string(conditions) or callable(conditions):
                    _c.append({True: conditions})
                else:
                    for cond in conditions:
                        if self._is_base_string(cond):
                            _c.append({True: cond})
                        else:
                            _c.append(cond)
            self._map[e['name']] = _e

        initial = cfg['initial'] if 'initial' in cfg else None
        if self._is_base_string(initial):
            initial = {'state': initial}
        if initial:
            if 'event' not in initial:
                initial['event'] = 'startup'
            self._initial = initial
            add({'name': initial['event'],
                 'src': 'none', 'dst': initial['state']})

        if 'final' in cfg:
            self._final = cfg['final']

        for e in cfg['events']:
            add(e)

        for event in self._map:
            setattr(self, event, self._build_event(event))

        for name, callback in cfg['callbacks'].items():
            self._callbacks[name] = _weak_callback(callback)

    def _build_event(self, event):
        def fn(obj, *args, **kwargs):
            if not self.can(obj, event):
                raise FysomError(
                    'event %s inappropriate in current state %s'
                    % (event, self.current(obj)))

            # Prepare the event object with all the meta data to pas through.
            # On event occurrence, source will always be the current state.
            e = self._e_obj()
            e.fsm, e.obj, e.event, e.src, e.dst = (
                self, obj, event, self.current(obj), self._map[event]['dst'])
            setattr(e, 'args', args)
            setattr(e, 'kwargs', kwargs)
            for k, v in kwargs.items():
                setattr(e, k, v)

            # check conditions first, event dst may change during
            # checking conditions
            for c in self._map[event].get('cond', ()):
                target = True in c
                cond = c[target]
                _c_r = self._check_condition(obj, cond, target, e)
                if not _c_r:
                    if 'else' in c:
                        e.dst = c['else']
                        break
                    else:
                        raise Canceled(
                            'Cannot trigger event {0} because the {1} '
                            'condition not returns {2}'.format(
                                event, cond, target), e
                        )

            # try to trigger the before event, unless it gets cancelled.
            if self._before_event(obj, e) is False:
                raise Canceled(
                    'Cannot trigger event {0} because the onbefore{0} '
                    'handler returns False'.format(event), e)

            # wraps the activities that must constitute a single transaction
            if self.current(obj) != e.dst:
                def _trans():
                    delattr(obj, 'transition')
                    setattr(obj, self.state_field, e.dst)
                    self._enter_state(obj, e)
                    self._change_state(obj, e)
                    self._after_event(obj, e)
                obj.transition = _trans

                # Hook to perform asynchronous transition
                if self._leave_state(obj, e) is not False:
                    obj.transition()
            else:
                self._reenter_state(obj, e)
                self._after_event(obj, e)

        fn.__name__ = str(event)
        fn.__doc__ = (
            "Event handler for an {event} event. This event can be "
            "fired if the machine is in {states} states.".format(
                event=event, states=self._map[event]['src']))

        return fn

    class _e_obj(object):
        pass

    @staticmethod
    def _is_base_string(object):  # pragma: no cover
        try:
            return isinstance(object, basestring)  # noqa
        except NameError:
            return isinstance(object, str)  # noqa

    def _do_callbacks(self, obj, callbacks, *args, **kwargs):
        for cb in callbacks:
            if cb in self._callbacks:
                return self._callbacks[cb](*args, **kwargs)
            if hasattr(obj, cb):
                return getattr(obj, cb)(*args, **kwargs)

    def _check_condition(self, obj, func, target, e):
        if callable(func):
            return func(e) is target
        return self._do_callbacks(obj, [func], e) is target

    def _before_event(self, obj, e):
        callbacks = ['onbefore' + e.event, 'on_before_' + e.event]
        return self._do_callbacks(obj, callbacks, e)

    def _after_event(self, obj, e):
        callbacks = ['onafter' + e.event, 'on' + e.event,
                     'on_after_' + e.event, 'on_' + e.event]
        return self._do_callbacks(obj, callbacks, e)

    def _leave_state(self, obj, e):
        callbacks = ['onleave' + e.src, 'on_leave_' + e.src]
        return self._do_callbacks(obj, callbacks, e)

    def _enter_state(self, obj, e):
        callbacks = ['onenter' + e.dst, 'on' + e.dst,
                     'on_enter_' + e.dst, 'on_' + e.dst]
        return self._do_callbacks(obj, callbacks, e)

    def _reenter_state(self, obj, e):
        callbacks = ['onreenter' + e.dst, 'on_reenter_' + e.dst]
        return self._do_callbacks(obj, callbacks, e)

    def _change_state(self, obj, e):
        callbacks = ['onchangestate', 'on_change_state']
        return self._do_callbacks(obj, callbacks, e)

    def current(self, obj):
        return getattr(obj, self.state_field) or 'none'

    def isstate(self, obj, state):
        return self.current(obj) == state

    is_state = isstate

    def can(self, obj, event):
        if event not in self._map or hasattr(obj, 'transition'):
            return False
        src = self._map[event]['src']
        return self.current(obj) in src or WILDCARD in src

    def cannot(self, obj, event):
        return not self.can(obj, event)

    def is_finished(self, obj):
        return self._final and (self.current(obj) == self._final)

    def trigger(self, obj, event, *args, **kwargs):
        if not hasattr(self, event):
            raise FysomError(
                "There isn't any event registered as %s" % event)
        return getattr(self, event)(obj, *args, **kwargs)
