import asyncio

import pytest

from yapee import EventEmitter


@pytest.fixture
def event_emitter():
    return EventEmitter()


@pytest.mark.asyncio
async def test_sync_listener(event_emitter):
    received = []

    @event_emitter.enlist("test_event")
    def listener(data):
        received.append(data)

    event_emitter.emit("test_event", "hello")
    await asyncio.sleep(0)  # Wait until loop make single iteration and listeners wrapped in tasks will be executed
    assert received == ["hello"]


@pytest.mark.asyncio
async def test_async_listener(event_emitter):
    received = []

    @event_emitter.enlist("async_event")
    async def async_listener(data):
        await asyncio.sleep(0.1)
        received.append(data)

    event_emitter.emit("async_event", "async hello")
    await asyncio.sleep(0.2)  # Allow async task to complete
    assert received == ["async hello"]


@pytest.mark.asyncio
async def test_multiple_listeners(event_emitter):
    received = []

    @event_emitter.enlist("test_event")
    def listener1(data):
        received.append(data)

    @event_emitter.enlist("test_event")
    def listener2(data):
        received.append(data)

    event_emitter.emit("test_event", "hello")
    await asyncio.sleep(0)  # Wait until loop make single iteration and listeners wrapped in tasks will be executed
    assert received == ["hello", "hello"]


@pytest.mark.asyncio
async def test_listener_with_multiple_args(event_emitter):
    received = []

    @event_emitter.enlist("test_event")
    def listener(arg1, arg2):
        received.append([arg1, arg2])

    event_emitter.emit("test_event", "arg1", "arg2")
    await asyncio.sleep(0)  # explanation above
    assert received == [["arg1", "arg2"]]


@pytest.mark.asyncio
async def test_wait_for(event_emitter):
    async def trigger():
        await asyncio.sleep(0.1)
        event_emitter.emit("wait_event")  # no args
        await asyncio.sleep(0.1)
        event_emitter.emit("wait_event", 42)  # single arg
        await asyncio.sleep(0.1)
        event_emitter.emit("wait_event", 42, 43)  # multiple args

    asyncio.create_task(trigger())
    result = await event_emitter.wait_for("wait_event", timeout=1)
    assert result is None

    result = await event_emitter.wait_for("wait_event", timeout=1)
    assert result == 42

    result = await event_emitter.wait_for("wait_event", timeout=1)
    assert result == (42, 43)


@pytest.mark.asyncio
async def test_wait_for_with_predicate(event_emitter):
    async def trigger():
        await asyncio.sleep(0.1)
        event_emitter.emit("wait_event", 10)
        event_emitter.emit("wait_event", 42)  # This one should pass predicate

    asyncio.create_task(trigger())
    result = await event_emitter.wait_for("wait_event", predicate=lambda x: x == 42, timeout=1)
    assert result == 42


@pytest.mark.asyncio
async def test_wait_for_with_error_predicate(event_emitter):
    async def trigger():
        await asyncio.sleep(0.1)
        event_emitter.emit("wait_event", 10)

    asyncio.create_task(trigger())

    try:
        await event_emitter.wait_for("wait_event", predicate=lambda x: x / 0, timeout=1)
    except Exception as e:
        assert isinstance(e, ZeroDivisionError)


def test_delist(event_emitter):
    received = []

    @event_emitter.enlist("test_event")
    def sync_listener(data):
        received.append(data)

    @event_emitter.enlist("test_event")
    async def async_listener(data):
        received.append(data)

    event_emitter.delist("test_event", sync_listener)
    event_emitter.delist("test_event", async_listener)
    event_emitter.emit("test_event", "should not be received")
    assert received == []


def test_delist_all_for_event(event_emitter):
    received = []

    @event_emitter.enlist("test_event")
    def listener1(data):
        received.append(data)

    @event_emitter.enlist("test_event")
    def listener2(data):
        received.append(data)

    event_emitter.delist_all("test_event")
    event_emitter.emit("test_event", "should not be received")
    assert received == []


def test_delist_literally_all(event_emitter):
    received = []

    for i in range(9):
        @event_emitter.enlist("test_event")
        def listener(data):
            received.append(data)

    event_emitter.delist_all()
    event_emitter.emit("test_event", "should not be received also")
    assert received == []


@pytest.mark.asyncio
async def test_listener_error(event_emitter, monkeypatch):
    error_caught = None

    async def monkey_listener_wrapper(self: EventEmitter, event, listener, args: tuple):
        nonlocal error_caught

        try:
            await listener(*args) if listener in self._coro_listeners else listener(*args)
        except Exception as e:
            try:
                await self._on_listener_error(event, listener, args, e)
            except Exception as e1:
                error_caught = e1

    monkeypatch.setattr(EventEmitter, "_listener_wrapper", monkey_listener_wrapper)

    @event_emitter.enlist("error_event")
    def error_listener(_):
        raise ValueError("Test error")

    event_emitter.emit("error_event", None)

    await asyncio.sleep(0.1)
    assert isinstance(error_caught, ValueError)


@pytest.mark.asyncio
async def test_override_listener_error():
    class CustomEmitter(EventEmitter):
        def __init__(self):
            super().__init__()
            self.error_caught = None

        async def _on_listener_error(self, event, listener, args, e):
            self.error_caught = e

    custom_emitter = CustomEmitter()

    @custom_emitter.enlist("error_event")
    def error_listener(_):
        raise ValueError("Test error")

    custom_emitter.emit("error_event", None)
    await asyncio.sleep(0.1)
    assert isinstance(custom_emitter.error_caught, ValueError)
