"""The stored autopilot account record, whichever way it was saved (12 Nov 2026): compressed in `z` (zlib, base64) since the function
began to store it that way, or plain text in `data` before. `stockiq-ai-trader`'s own `item_json` does the same inside the function."""
import base64, json, zlib


def text(item):
    """The record's JSON text."""
    return zlib.decompress(base64.b64decode(item['z'])).decode('utf-8') if item.get('z') else item['data']


def load(item):
    return json.loads(text(item))


def stored_bytes(item):
    """What the item takes in the table (DynamoDB's limit is 400 KB an item), not what it is once unpacked."""
    return len((item.get('z') or item.get('data') or '').encode())
