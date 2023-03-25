import argparse
import contextlib
import json
import logging

import trio
import trio_websocket
from trio_websocket import serve_websocket, ConnectionClosed
import pydantic

import models

logger = logging.getLogger(__name__)


async def communicate_with_browser(request: trio_websocket.WebSocketRequest):
    """Run coroutines which interact with browser."""
    window_bounds = models.WindowBounds(
        south_lat=-90,
        north_lat=90,
        west_lng=-180,
        east_lng=180
    )  # это нужно здесь, т.к. для каждого вебсокета (клиента) свои границы
    async with trio.open_nursery() as nursery:
        ws = await request.accept()
        nursery.start_soon(listen_browser, ws, window_bounds)
        nursery.start_soon(talk_to_browser, ws, window_bounds)


async def listen_browser(
    ws: trio_websocket.WebSocketConnection,
    bounds: models.WindowBounds,
    prod_mode=True,
):
    """
    Listen browser messages.

    :param ws: web socket
    :param bounds: current windown bounds in browser
    :param prod_mode: value for the test, because without it the tests fail due to the while true loop
    """
    while True:
        errors = []
        try:
            message = await ws.get_message()
            if not prod_mode and message == 'break':
                break
            try:
                decoded_message = json.loads(message)
                new_bounds = models.NewBoundsMessage(**decoded_message).data
                bounds.update(**new_bounds.dict())
                logger.debug(f'update window bounds {bounds}')
            except json.JSONDecodeError:
                errors.append(f'can not decode message "{message}" to JSON')
            except pydantic.ValidationError as e:
                errors += e.errors()

            if errors:
                error_message = json.dumps({'msgType': 'Errors', 'errors': errors}, ensure_ascii=True)
                await ws.send_message(error_message)
                logger.warning(f'got wrong message from browser {error_message}')
        except ConnectionClosed:
            break


async def talk_to_browser(ws: trio_websocket.WebSocketConnection, bounds: models.WindowBounds):
    """Send regular messages to browser."""
    send_every_seconds = 1
    while True:
        try:
            await send_buses(ws, bounds)
            await trio.sleep(send_every_seconds)
        except ConnectionClosed:
            break


async def send_buses(ws: trio_websocket.WebSocketConnection, bounds: models.WindowBounds):
    """Send message with buses."""
    buses_in_window = {
        bus_id: bus.dict()
        for bus_id, bus
        in buses.items()
        if bounds.is_inside(bus)
    }
    logger.debug(f'{len(buses_in_window)} buses in window from {len(buses)}')
    message = json.dumps(
        {
            'msgType': 'Buses',
            'buses': list(buses_in_window.values()),
        },
        ensure_ascii=False
    )
    logger.debug(f'send new message with buses: {message}')
    await ws.send_message(message)


async def get_bus_updates(request: trio_websocket.WebSocketRequest, prod_mode: bool = True):
    """
    Get updates from microservice with buses info.

    :param request: request from microservice
    :param prod_mode: value for the test, because without it the tests fail due to the while true loop
    also it creates global variable buses, which absents when you run tests
    """
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()

            if not prod_mode:
                global buses
                buses = {}
            if not prod_mode and message == 'break':
                break

            errors = []
            try:
                decoded_message = json.loads(message)
                bus = models.Bus(**decoded_message)
                buses[bus.busId] = bus
                logger.debug(f'get new bus info: {message}')
            except json.JSONDecodeError:
                errors.append(f'can not decode message "{message}" to JSON')
            except pydantic.ValidationError as e:
                errors += e.errors()

            if errors:
                error_message = json.dumps({'msgType': 'Errors', 'errors': errors}, ensure_ascii=True)
                await ws.send_message(error_message)
                logger.warning(f'got wrong message from browser {error_message}')
        except ConnectionClosed:
            break


async def main():
    parser = argparse.ArgumentParser(
        prog='Server of buses',
        description='Get data from bus microservice and from browsers and send data to browsers',
    )
    parser.add_argument('-host', '--host', type=str, required=True,
                        help='server address, example "127.0.0.1"')
    parser.add_argument('-lp', '--bus_port', type=int, required=True,
                        help='port where server listen buses ws')
    parser.add_argument('-sp', '--browser_port', type=int, required=True,
                        help='port where server send info')
    parser.add_argument('-v', '--verbosity', type=int, default=0, choices=range(0, 51, 10),
                        help='level of log verbosity from 0 (notset) to 50 (only critical) through 10, default 0')

    args = parser.parse_args()

    logging.basicConfig(level=args.verbosity)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(serve_websocket, communicate_with_browser, args.host, args.browser_port, None)
        nursery.start_soon(serve_websocket, get_bus_updates, args.host, args.bus_port, None)


if __name__ == '__main__':
    buses = {}
    with contextlib.suppress(KeyboardInterrupt):
        trio.run(main)
