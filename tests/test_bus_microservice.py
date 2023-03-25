import json

import pytest
from unittest.mock import AsyncMock

from server import get_bus_updates


@pytest.fixture
def ws_request():
    ws_request = AsyncMock()
    ws_request.accept.return_value = AsyncMock()
    return ws_request


@pytest.mark.trio
async def test_get_bus_updates(ws_request):
    test_message = json.dumps({
        'busId': '1',
        'lat': 1,
        'lng': 2,
        'route': 'A',
    })
    ws_request.accept.return_value.get_message.side_effect = [
        test_message,
        'break'
    ]
    await get_bus_updates(ws_request, False)

    assert ws_request.send_message.call_count == 0


@pytest.mark.trio
async def test_get_bus_updates_invalid_json(ws_request):
    ws_request.accept.return_value.get_message.side_effect = ['invalid json', 'break']
    await get_bus_updates(ws_request, False)

    assert ws_request.accept.return_value.send_message.call_count == 1
    message = ws_request.accept.return_value.send_message.call_args.args[0]
    assert isinstance(message, str)
    message_dict = json.loads(message)
    assert 'msgType' in message_dict
    assert message_dict['msgType'] == 'Errors'
    assert 'errors' in message_dict
    assert isinstance(message_dict['errors'], list)
    assert len(message_dict['errors']) == 1


@pytest.mark.trio
async def test_get_bus_updates_invalid_data(ws_request):
    test_message = json.dumps({
        'busId': [],
        'lat': -100,
        'lng': 200,
        'route': [],
    })
    ws_request.accept.return_value.get_message.side_effect = [
        test_message,
        'break'
    ]
    await get_bus_updates(ws_request, False)

    assert ws_request.accept.return_value.send_message.call_count == 1
    message = ws_request.accept.return_value.send_message.call_args.args[0]
    assert isinstance(message, str)
    decoded_message = json.loads(message)
    assert 'msgType' in decoded_message
    assert decoded_message['msgType'] == 'Errors'
    assert 'errors' in decoded_message
    assert isinstance(decoded_message['errors'], list)
    assert len(decoded_message['errors']) == 4
    assert len([error for error in decoded_message['errors'] if 'busId' in error['loc']]) == 1
    assert len([error for error in decoded_message['errors'] if 'lat' in error['loc']]) == 1
    assert len([error for error in decoded_message['errors'] if 'lng' in error['loc']]) == 1
    assert len([error for error in decoded_message['errors'] if 'route' in error['loc']]) == 1

@pytest.mark.trio
async def test_get_bus_updates_incomplete_data(ws_request):
    test_message = json.dumps({
        'busId': '43',
        'lat': -17,
        'lng': 20,
    })
    ws_request.accept.return_value.get_message.side_effect = [
        test_message,
        'break'
    ]
    await get_bus_updates(ws_request, False)

    assert ws_request.accept.return_value.send_message.call_count == 1
    message = ws_request.accept.return_value.send_message.call_args.args[0]
    assert isinstance(message, str)
    decoded_message = json.loads(message)
    assert 'msgType' in decoded_message
    assert decoded_message['msgType'] == 'Errors'
    assert 'errors' in decoded_message
    assert isinstance(decoded_message['errors'], list)
    assert len(decoded_message['errors']) == 1
    assert len([error for error in decoded_message['errors'] if 'route' in error['loc']]) == 1
