"""
Yet Another Python Event Emitter.
Made to be simple, fast and understandable
"""

import asyncio

from typing import Callable, Coroutine, Generic, TypeVar, TypeAlias, Any

__all__ = ("EventEmitterMixin", "EventEmitter")

E = TypeVar("E")
Listener: TypeAlias = "Callable[..., Coroutine[Any, Any, None]] | Callable[..., None]"
Waiter: TypeAlias = "Callable[..., bool]"


# https://www.joeltok.com/blog/2021-3/building-an-event-bus-in-python
class EventEmitterMixin(Generic[E]):
    """Event emitter mixin"""

    __slots__ = ()

    SLOTS = ("_listeners", "_coro_listeners", "_waiters")

    # required attributes
    # weak ref set leads to lambda functions get garbage collected almost instantly
    _listeners: dict[E, set[Listener]]
    _coro_listeners: set[Listener]  # listeners coroutines
    _waiters: dict[E, set[Waiter]]

    def _init_attributes(self):
        self._listeners = {}
        self._coro_listeners = set()
        self._waiters = {}

    async def _on_listener_error(self, event: E, listener: Listener, args: tuple, e: Exception):
        """Override this if you want to handle exceptions from listener"""
        raise e

    async def _listener_wrapper(self, event: E, listener: Listener, args: tuple):
        """Wrap and await listener call to propagate exception"""

        try:
            await listener(*args) if listener in self._coro_listeners else listener(*args)
        except Exception as e:
            await self._on_listener_error(event, listener, args, e)

    def emit(self, event: E, *args):
        for listener in self._listeners.get(event, ()):
            asyncio.create_task(self._listener_wrapper(event, listener, args))  # schedule listener async execution

        if event in self._waiters:
            # remove waiters, list compr. required to avoid waiter set size change during iteration
            self._waiters[event].difference_update([waiter for waiter in self._waiters[event] if waiter(*args)])

    def enlist(self, event: E, listener: Listener = None):
        """Register listener"""

        def set_listener(f: Listener):  # no need in functools.wraps as we return original func
            asyncio.iscoroutinefunction(f) and self._coro_listeners.add(f)  # mark listener as coro

            if event in self._listeners:
                self._listeners[event].add(f)
            else:
                self._listeners[event] = {f}
            return f

        return set_listener if listener is None else set_listener(listener)  # decorator vs arg

    def delist(self, event: E, listener: Listener):
        """Remove listener from list"""

        self._listeners[event].remove(listener)
        if listener in self._coro_listeners:
            self._coro_listeners.remove(listener)

    def wait_for(self, event: E, predicate: Waiter = lambda *_: True, timeout: float = None):
        """
        Wait for event to occur with timeout.
        Error from `predicate` function will be propagated and reraised there

        :param event: event to wait for
        :param predicate: predicate function
        :param timeout: timeout in seconds with fractions
        :return: args tuple passed to `emit`with current event
        :raises TimeoutError: if `timeout` is exceeded
        """

        future = asyncio.get_running_loop().create_future()

        def waiter(*args):
            try:
                res = predicate(*args)
            except Exception as e:
                future.set_exception(e)
                return True  # remove current waiter
            else:
                if res:
                    if len(args) == 0:
                        future.set_result(None)
                    elif len(args) == 1:
                        future.set_result(args[0])
                    else:
                        future.set_result(args)

                return res

        if event in self._waiters:
            self._waiters[event].add(waiter)
        else:
            self._waiters[event] = {waiter}

        return asyncio.wait_for(future, timeout=timeout)

    def delist_all(self, event: E = None):
        """Remove listeners for specific `event` or all listeners if `event` is `None`"""

        if event is not None:
            self._listeners[event].clear()
        else:
            self._listeners.clear()


class EventEmitter(EventEmitterMixin[E]):
    """Ready to use event emitter class"""

    __slots__ = EventEmitterMixin.SLOTS

    def __init__(self):
        self._init_attributes()
