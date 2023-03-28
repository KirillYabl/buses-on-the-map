import argparse
import contextlib
import functools
import glob
import os
import json
import random
import time
import logging
import typing

import trio
import trio_websocket
import wsproto.utilities
from trio_websocket import open_websocket_url

logger = logging.getLogger(__name__)


def load_routes(directory_path: str = 'routes', routes_number: int = 0):
    """
    Load routes with buses from file system generator.

    :param directory_path: path of files of routes
    :param routes_number: the number of routes to download if < 0 => all routes
    :return:
    """
    if routes_number <= 0:
        routes_number = 10 ** 9

    for filename in glob.glob(os.path.join(directory_path, '*.json'))[:routes_number]:
        with open(filename, 'r', encoding='utf8') as file:
            yield json.load(file)


async def run_bus(send_channel: trio.MemorySendChannel, bus_id: str, route: dict, delta: int, sleep: int):
    """
    Coroutine which send info about one bus.

    :param send_channel: channel (queue) which accept buses
    :param bus_id: id of bus
    :param route: route with bus points on map
    :param delta: shift from start of route for emulating, it can be many buses with this route
    and they mustn't be in one point and because of that they must be different delta
    :param sleep: send info every :sleep: seconds
    """
    coordinates = route['coordinates']
    name = route['name']
    coordinate_points_count = len(coordinates)
    while True:
        step = 1 / sleep
        coordinates_index = (delta + int(time.time() * step)) % coordinate_points_count
        lat, lng = coordinates[coordinates_index]
        message = json.dumps({
            'busId': bus_id,
            'route': name,
            'lat': lat,
            'lng': lng,
        }, ensure_ascii=False)
        logger.debug(f'send value to channel: {message}')
        await send_channel.send(message)
        await trio.sleep(sleep)


def relaunch_on_disconnect(async_function: typing.Callable) -> typing.Callable:
    """Decorator which relaunch coroutine after network errors."""

    @functools.wraps(async_function)
    async def wrapper(*args, **kwargs):
        while True:
            try:
                await async_function(*args, **kwargs)
            except (
                trio_websocket.HandshakeError,
                wsproto.utilities.LocalProtocolError,
                trio_websocket.ConnectionClosed
            ):
                wait_seconds = 5
                logger.warning(f'Problems with connection, trying to reconnect through {wait_seconds} seconds')
                await trio.sleep(wait_seconds)

    return wrapper


@relaunch_on_disconnect
async def send_updates(server_address: str, receive_channel: trio.MemoryReceiveChannel):
    """Send updates about buses to server."""
    async with open_websocket_url(server_address) as ws:
        async for bus_update in receive_channel:
            logger.debug(f'send message from channel: {bus_update}')
            await ws.send_message(bus_update)


def generate_bus_id(emulator_id: str, route_id: str, bus_index: int) -> str:
    """Generate unique bus id."""
    return f'{emulator_id}-{route_id}-{bus_index}'


class LimitedInt:
    """Int with top and bottom limits, init only create caller, which accept numbers."""

    def __init__(self, min_value: typing.Optional[int] = None, max_value: typing.Optional[int] = None):
        """
        Accept limits.

        :param min_value: min included value
        :param max_value: max included value
        """
        if min_value is None and max_value is None:
            raise ValueError('No need to use it class without limits, use int instead')
        self.min_value = min_value
        self.max_value = max_value

    def __call__(self, number: int) -> int:
        """Try to accept number and check limits."""
        number = int(number)
        if self.min_value is not None and number < self.min_value:
            raise ValueError(f'min value should be {self.min_value} ({number} < {self.min_value})')
        if self.max_value is not None and number > self.max_value:
            raise ValueError(f'max value should be {self.max_value} ({number} > {self.max_value})')
        return number

    def get_readable_limits(self) -> str:
        """Readable format for __repr__."""
        limits = []
        if self.min_value is not None:
            limits.append(f'min={self.min_value}')
        if self.max_value is not None:
            limits.append(f'min={self.max_value}')
        return ', '.join(limits)

    def __repr__(self) -> str:
        """Readable representation."""
        return f'LimitedInt ({self.get_readable_limits()})'


async def main():
    parser = argparse.ArgumentParser(
        prog='Emulator of buses routes',
        description='Program read routes with buses and emulates microservice which send data from buses GPS',
    )
    parser.add_argument('-server', '--server', type=str, required=True,
                        help='server address, example "ws://127.0.0.1:8080"')
    parser.add_argument('-rn', '--routes_number', type=LimitedInt(0, 10 ** 9), required=True,
                        help='take first "routes_number" routes from directory with routes, 0 for all')
    parser.add_argument('-b', '--buses_per_route', type=LimitedInt(0, 100), required=True,
                        help='number of buses in different points for every route')
    parser.add_argument('-id', '--emulator_id', type=str, required=True,
                        help='some unique combination to understand, which program send data, if it is many emulator instances')
    parser.add_argument('-wn', '--websockets_number', type=LimitedInt(1, 20), default=5,
                        help='number of websockets connections, from 1 to 20, default 5')
    parser.add_argument('-t', '--refresh_timeout', type=LimitedInt(0, 60), default=1,
                        help='send data every "refresh_timeout" seconds')
    parser.add_argument('-v', '--verbosity', type=int, default=0, choices=range(0, 51, 10),
                        help='level of log verbosity from 0 (notset) to 50 (only critical) through 10, default 0')

    args = parser.parse_args()
    delta_multiplier = 100  # how many point between buses from same route, no need to set by user
    delta_start = random.randint(0, 1000)  # random start delta if many emulators run

    logging.basicConfig(level=args.verbosity)
    send_channels = []
    receive_channels = []

    async with trio.open_nursery() as nursery:
        for websocket_number in range(args.websockets_number):
            send_channel, receive_channel = trio.open_memory_channel(max_buffer_size=0)
            send_channels.append(send_channel)
            receive_channels.append(receive_channel)
        for receive_channel in receive_channels:
            nursery.start_soon(send_updates, args.server, receive_channel)
        for route in load_routes(routes_number=args.routes_number):
            for bus_index in range(args.buses_per_route):
                bus_id = generate_bus_id(args.emulator_id, route['name'], bus_index)
                delta = delta_start + bus_index * delta_multiplier
                send_channel = random.choice(send_channels)
                nursery.start_soon(run_bus, send_channel, bus_id, route, delta, args.refresh_timeout)


if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt):
        trio.run(main)
