import json

import pytest
from trio_websocket import WebSocketConnection
from unittest.mock import AsyncMock

from server import listen_browser
from models import WindowBounds


@pytest.fixture
def ws() -> AsyncMock:
    return AsyncMock(spec=WebSocketConnection)


@pytest.mark.trio
async def test_listen_browser_success(ws):
    test_message = json.dumps({
        'msgType': 'newBounds',
        'data': {
            'south_lat': 1,
            'north_lat': 2,
            'west_lng': 3,
            'east_lng': 4,
        },
    })
    ws.get_message.side_effect = [
        test_message,
        'break',  # without it with while true in listen_browser tests won't be success
    ]
    bounds = WindowBounds(south_lat=-90, north_lat=90, west_lng=-180, east_lng=180)
    await listen_browser(ws, bounds, False)
    assert bounds.south_lat == 1
    assert bounds.north_lat == 2
    assert bounds.west_lng == 3
    assert bounds.east_lng == 4


@pytest.mark.trio
async def test_listen_browser_invalid_json(ws):
    ws.get_message.side_effect = ['invalid json', 'break']
    bounds = WindowBounds(south_lat=-90, north_lat=90, west_lng=-180, east_lng=180)
    await listen_browser(ws, bounds, False)

    assert ws.send_message.call_count == 1
    message = ws.send_message.call_args.args[0]
    assert isinstance(message, str)
    decoded_message = json.loads(message)
    assert 'msgType' in decoded_message
    assert decoded_message['msgType'] == 'Errors'
    assert 'errors' in decoded_message
    assert isinstance(decoded_message['errors'], list)
    assert len(decoded_message['errors']) == 1


@pytest.mark.trio
async def test_listen_browser_invalid_data(ws):
    test_message = json.dumps({
        'msgType': 'wrong',
        'data': {
            'south_lat': -95,
            'north_lat': 107,
            'west_lng': -210,
            'east_lng': 415,
        },
    })
    ws.get_message.side_effect = [
        test_message,
        'break',  # without it with while true in listen_browser tests won't be success
    ]
    bounds = WindowBounds(south_lat=-90, north_lat=90, west_lng=-180, east_lng=180)
    await listen_browser(ws, bounds, False)

    assert ws.send_message.call_count == 1
    message = ws.send_message.call_args.args[0]
    assert isinstance(message, str)
    decoded_message = json.loads(message)
    assert 'msgType' in decoded_message
    assert decoded_message['msgType'] == 'Errors'
    assert 'errors' in decoded_message
    assert isinstance(decoded_message['errors'], list)
    assert len(decoded_message['errors']) == 5
    assert len([error for error in decoded_message['errors'] if 'south_lat' in error['loc']]) == 1
    assert len([error for error in decoded_message['errors'] if 'north_lat' in error['loc']]) == 1
    assert len([error for error in decoded_message['errors'] if 'west_lng' in error['loc']]) == 1
    assert len([error for error in decoded_message['errors'] if 'east_lng' in error['loc']]) == 1
    assert len([error for error in decoded_message['errors'] if 'msgType' in error['loc']]) == 1


@pytest.mark.trio
async def test_listen_browser_incomplete_data(ws):
    test_message = json.dumps({
        'msgType': 'newBounds',
        'data': {
            'south_lat': 80,
            'north_lat': 80,
            'west_lng': 80,
        },
    })
    ws.get_message.side_effect = [
        test_message,
        'break',  # without it with while true in listen_browser tests won't be success
    ]
    bounds = WindowBounds(south_lat=-90, north_lat=90, west_lng=-180, east_lng=180)
    await listen_browser(ws, bounds, False)

    assert ws.send_message.call_count == 1
    message = ws.send_message.call_args.args[0]
    assert isinstance(message, str)
    decoded_message = json.loads(message)
    assert 'msgType' in decoded_message
    assert decoded_message['msgType'] == 'Errors'
    assert 'errors' in decoded_message
    assert isinstance(decoded_message['errors'], list)
    assert len(decoded_message['errors']) == 1
    assert len([error for error in decoded_message['errors'] if 'east_lng' in error['loc']]) == 1
