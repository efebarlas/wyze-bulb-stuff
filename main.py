from typing import Sequence
from dataclasses import dataclass
from diskcache import Cache
from pathlib import Path
Path("./cache-dir").mkdir(parents=True, exist_ok=True)

cache = Cache(directory='./cache-dir')
import random
import os
from wyze_sdk import Client
from ratelimit import limits

@dataclass
class WyzeCredResponse:
    access_token: str
    refresh_token: str

@cache.memoize(expire=36000)
def get_wyze_creds() -> WyzeCredResponse:
    response = Client().login(email=os.environ['WYZE_EMAIL'], password=os.environ['WYZE_PASSWORD'], api_key=os.environ['WYZE_API_KEY'], key_id=os.environ['WYZE_KEY_ID'])
    return WyzeCredResponse(response['access_token'], response['refresh_token'])

def get_wyze_client(creds: WyzeCredResponse) -> Client:
    client = Client(token=creds.access_token)
    return client

def get_devices(client: Client):
    response = client.devices_list()
    return response


def get_bulb_by_name(client: Client, name):
    for device in get_devices(client):
        if device.nickname == name:
            living_room_mac = device.mac
    return client.bulbs.info(device_mac=living_room_mac)


@dataclass
class FlameState:
    brightness: float
    rgb: str

def flame_colors():
    """
    Generator function that yields RGB color codes mimicking a flame with smooth transitions.
    """
    r, g, b = 150, 50, 0  # Start with reddish color
    brightness = 1.0        # Start with maximum brightness

    while True:
        # Convert RGB values to hexadecimal strings
        r_hex = hex(int(r * brightness))[2:].zfill(2)
        g_hex = hex(int(g * brightness))[2:].zfill(2)
        b_hex = hex(int(b * brightness))[2:].zfill(2)

        # Construct and yield the RGB color code
        rgb_code = f"{r_hex}{g_hex}{b_hex}"
        yield FlameState(brightness=brightness, rgb=rgb_code)

        # Update RGB values for the next iteration
        r_change = random.randint(-10, 30)
        g_change = random.randint(-20, 20)
        b_change = random.randint(-5, 5)

        r = max(180, min(255, r + r_change))  # Keep red component high
        g = max(50, min(180, g + g_change))   # Allow green to vary
        b = max(0, min(50, b + b_change))     # Keep blue component low

        brightness_change = random.uniform(-0.4, 0.5)
        brightness = max(0.3, min(1.0, brightness + brightness_change))

client = get_wyze_client(get_wyze_creds())
living_room_bulb = get_bulb_by_name(client, 'Color Bulb 3')

@limits(calls=4, period=1)
def make_fire(client, bulb_info):
    for flame_color in flame_colors():
        client.bulbs.set_brightness(device_mac=bulb_info.mac, device_model=bulb_info.product.model, brightness=int(flame_color.brightness * 100))
        client.bulbs.set_color(device_mac=bulb_info.mac, device_model=bulb_info.product.model, color=flame_color.rgb)
        
make_fire(client, living_room_bulb)