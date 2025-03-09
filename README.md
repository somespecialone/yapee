# Yet Another Python Event Emitter

[![Made in Ukraine](https://img.shields.io/badge/made_in-ukraine-ffd700.svg?labelColor=0057b7)](https://stand-with-ukraine.pp.ua)
[![license](https://img.shields.io/github/license/somespecialone/yapee)](https://github.com/somespecialone/yapee/blob/main/LICENSE)
[![pypi](https://img.shields.io/pypi/v/yapee)](https://pypi.org/project/yapee)
[![Publish](https://github.com/somespecialone/yapee/actions/workflows/publish.yml/badge.svg)](https://github.com/somespecialone/yapee/actions/workflows/publish.yml)
[![Tests](https://github.com/somespecialone/yapee/actions/workflows/tests.yml/badge.svg)](https://github.com/somespecialone/yapee/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/somespecialone/yapee/branch/main/graph/badge.svg?token=SP7EQKPIQ3)](https://codecov.io/gh/somespecialone/yapee)

_ASAP_ (as _simple_ as possible), _fast_, and _understandable_ brokerless, zero-dependent event emitter for
Python.

## Features

- Supports both synchronous and asynchronous listeners.
- Provides event waiting with predicates and optional timeouts.
- Allows dynamic listener registration and removal.
- Built-in error propagation and handling.

## Installation

Project published on [PyPi](https://pypi.org) under [yapee](https://pypi.org/project/yapee) name.
So you can do next:

```sh
poetry add yapee
```

```sh
pip install yapee
```

## Usage

### Basic Example

```python
import asyncio

from yapee import EventEmitter

ee = EventEmitter()


@ee.enlist("my_event")
def my_listener(data):
    print(f"Received data: {data}")


ee.emit("my_event", "Hello, EventEmitter!")
```

### Asynchronous Listeners

```python
@ee.enlist("async_event")
async def async_listener(data):
    await asyncio.sleep(1)  # Do some async work
    print(f"Async received: {data}")


async def main():
    ee.emit("async_event", "Hello Async!")
    await asyncio.sleep(2)  # Give time for async execution


asyncio.run(main())
```

### Waiting for an Event

```python
async def trigger_event():
    await asyncio.sleep(2)
    ee.emit("wait_event", "Waited data")


asyncio.create_task(trigger_event())
data = await ee.wait_for("wait_event", timeout=5)
print(f"Waited and got: {data}")
```

### Waiting for an Event with Predicate Function

```python
async def trigger_event():
    await asyncio.sleep(2)
    ee.emit("filtered_event", 49)  # Emit event with data, will not pass predicate, as 49 < 50
    await asyncio.sleep(2)
    ee.emit("filtered_event", 51)  # Will pass predicate and wait_for will return 51


asyncio.create_task(trigger_event())

data = await ee.wait_for("filtered_event", predicate=lambda x: x > 50)
print(f"Received matching event data: {data}")
```

### Removing Listeners

```python
# Removing a specific listener
ee.delist("my_event", my_listener)
ee.delist("my_event", async_listener)

# Removing all listeners for an event
ee.delist_all("my_event")

# Removing all listeners for all events
ee.delist_all()
```

### Error Handling in Listeners

By default, any exception inside a listener **will be raised**. You can override `_on_listener_error` to customize error
handling:

```python
class MyCustomEmitter(EventEmitter):
    async def _on_listener_error(self, event, listener, args, e):
        print(f"Error in listener {listener} for event {event}: {e}")


my_custom_ee = MyCustomEmitter()
```
