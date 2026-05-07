# =============================================================================
#  azure_uploader.py
#  Sends ESP32 bus telemetry to Azure IoT Hub.
#
#  MODES:
#    - Standalone / simulation: run directly with `python azure_uploader.py`
#      Generates realistic fake bus data without needing the ESP32 or MQTT.
#    - Integrated with central.py: import this module and call
#      `azure_uploader.set_real_data(ultimo_estado)` from inside central.py's
#      on_message() callback. Then start the uploader thread with
#      `azure_uploader.start_background()`.
# =============================================================================

import datetime
import json
import math
import random
import threading
import time

from azure.iot.device import IoTHubDeviceClient, Message

# ─────────────────────────── CONFIGURATION ───────────────────────────────────

IOTHUB_DEVICE_CONNECTION_STRING = (
    'HostName=IoT2MasterMQM.azure-devices.net;'
    'DeviceId=ESP32Bus01;'
    'SharedAccessKey=sxfaTMtzlOWc4gIxVBSXNgktdAqKGBzuxtiKnH6IiwA='
)

# How often (seconds) to push a message to Azure
UPLOAD_PERIOD = 5

# Set to False when you want to use real data from central.py instead
SIMULATE = True

# ─────────────────── SIMULATED ROUTE (Valencia, Spain) ───────────────────────
# A short circular route approximating a city bus line.
# Coordinates: (longitude, latitude)
_SIM_WAYPOINTS = [
    (-0.3763, 39.4699),
    (-0.3748, 39.4712),
    (-0.3730, 39.4725),
    (-0.3715, 39.4738),
    (-0.3700, 39.4750),
    (-0.3690, 39.4735),
    (-0.3705, 39.4718),
    (-0.3720, 39.4705),
    (-0.3740, 39.4695),
    (-0.3763, 39.4699),  # back to start (loop)
]

# ─────────────────────────── SHARED STATE ────────────────────────────────────
# central.py writes here via set_real_data(); the uploader thread reads it.
_real_data_lock = threading.Lock()
_latest_real_data: dict | None = None

# ─────────────────────────── PUBLIC API ──────────────────────────────────────

def set_real_data(estado: dict) -> None:
    """
    Called by central.py to push the latest ESP32 data to the uploader.

    Example usage inside central.py's on_message():
        import azure_uploader
        azure_uploader.set_real_data(ultimo_estado)
    """
    global _latest_real_data
    with _real_data_lock:
        _latest_real_data = dict(estado)


def start_background() -> threading.Thread:
    """
    Start the Azure uploader in a background daemon thread.
    Use this when importing azure_uploader from central.py.

    Returns the Thread object (already started).
    """
    t = threading.Thread(target=main, daemon=True, name="AzureUploader")
    t.start()
    return t

# ─────────────────────────── SIMULATION HELPERS ──────────────────────────────

def _interpolate_route(step: int, total_steps: int) -> tuple[float, float]:
    """Return (lon, lat) smoothly interpolated along the simulated route."""
    n = len(_SIM_WAYPOINTS) - 1          # number of segments
    pos = (step % total_steps) / total_steps * n
    seg = int(pos)
    t   = pos - seg
    lon = _SIM_WAYPOINTS[seg][0] + t * (_SIM_WAYPOINTS[seg + 1][0] - _SIM_WAYPOINTS[seg][0])
    lat = _SIM_WAYPOINTS[seg][1] + t * (_SIM_WAYPOINTS[seg + 1][1] - _SIM_WAYPOINTS[seg][1])
    return round(lon, 6), round(lat, 6)


def _generate_simulated_data(step: int) -> dict:
    """
    Build a realistic fake sensor reading.

    - Speed follows a sinusoidal profile (stop–accelerate–cruise–brake cycle).
    - Temperature and humidity drift slowly with small random noise.
    - Passengers accumulate on the way out and drop on the return leg.
    - GPS follows the predefined Valencia route.
    """
    total_steps = 120   # full loop in steps

    # Speed: 0–70 km/h with a sine wave so it feels like a real route
    speed_raw = 35 + 35 * math.sin(2 * math.pi * step / total_steps)
    speed     = round(max(0.0, speed_raw + random.uniform(-3, 3)), 1)

    # Temperature: base 22 °C ±4 slow drift + tiny noise
    temp_base = 22 + 4 * math.sin(2 * math.pi * step / (total_steps * 2))
    temp      = round(temp_base + random.uniform(-0.5, 0.5), 1)

    # Humidity: base 55 % ±10
    hum_base  = 55 + 10 * math.cos(2 * math.pi * step / total_steps)
    hum       = round(max(10.0, min(95.0, hum_base + random.uniform(-1, 1))), 1)

    # Passengers: 0–60 triangle wave
    half       = total_steps // 2
    phase      = step % total_steps
    passengers = int((phase / half) * 60) if phase < half else int(((total_steps - phase) / half) * 60)

    lon, lat   = _interpolate_route(step, total_steps)
    alerta     = "BUS LLENO" if passengers >= 50 else "OK"

    return {
        "speed":      speed,
        "temp":       temp,
        "hum":        hum,
        "passengers": passengers,
        "lon":        lon,
        "lat":        lat,
        "alerta":     alerta,
    }

# ─────────────────────────── AZURE HANDLERS ──────────────────────────────────

def _cloud_to_device_handler(message) -> None:
    """Handle commands received from Azure IoT Hub (cloud-to-device)."""
    global UPLOAD_PERIOD
    try:
        cmd = json.loads(message.data)
        if "period" in cmd:
            UPLOAD_PERIOD = int(cmd["period"])
            print(f"[Azure] Upload period updated → {UPLOAD_PERIOD}s")
        if "message" in cmd:
            print(f"[Azure] Cloud message: {cmd['message']}")
    except Exception as exc:
        print(f"[Azure] Could not parse C2D command: {exc}")

# ─────────────────────────── MAIN LOOP ───────────────────────────────────────

def main() -> None:
    print("[Azure] Connecting to IoT Hub…")
    client = IoTHubDeviceClient.create_from_connection_string(
        IOTHUB_DEVICE_CONNECTION_STRING
    )
    client.connect()
    client.on_message_received = _cloud_to_device_handler
    print("[Azure] Connected. Starting upload loop.")

    step = 0
    while True:
        # ── Gather data ──────────────────────────────────────────────────────
        if SIMULATE:
            sensor_data = _generate_simulated_data(step)
            source = "SIM"
        else:
            with _real_data_lock:
                sensor_data = dict(_latest_real_data) if _latest_real_data else None
            if sensor_data is None:
                print("[Azure] Waiting for real data from central.py…")
                time.sleep(1)
                continue
            source = "ESP32"

        # ── Build payload ────────────────────────────────────────────────────
        payload = {
            "when":       datetime.datetime.now().isoformat(),
            "source":     source,
            "speed":      sensor_data.get("speed", 0),
            "temp":       sensor_data.get("temp", 0),
            "hum":        sensor_data.get("hum", 0),
            "passengers": sensor_data.get("passengers", 0),
            "lon":        sensor_data.get("lon", 0),
            "lat":        sensor_data.get("lat", 0),
            "alerta":     sensor_data.get("alerta", "OK"),
        }

        # ── Send to Azure ────────────────────────────────────────────────────
        msg = Message(json.dumps(payload, default=str))
        msg.content_encoding = "utf-8"
        msg.content_type     = "application/json"

        try:
            client.send_message(msg)
            print(
                f"[Azure][{source}] speed={payload['speed']:5.1f} km/h | "
                f"temp={payload['temp']:5.1f}°C | hum={payload['hum']:4.1f}% | "
                f"pax={payload['passengers']:3d} | alerta={payload['alerta']}"
            )
        except Exception as exc:
            print(f"[Azure] Send failed: {exc}")

        step += 1
        time.sleep(UPLOAD_PERIOD)


# ─────────────────────────── ENTRY POINT ─────────────────────────────────────

if __name__ == "__main__":
    # Running standalone → always simulate regardless of the SIMULATE flag
    SIMULATE = True
    print("=" * 60)
    print(" azure_uploader.py  —  Standalone simulation mode")
    print(f" IoT Hub : {IOTHUB_DEVICE_CONNECTION_STRING.split(';')[0]}")
    print(f" Period  : {UPLOAD_PERIOD}s")
    print("=" * 60)
    main()