# pico/ota-002/main.py
# MicroPython OTA-enabled IoT Controller with asyncio to run on Raspberry Pi Pico W
# This version uses uasyncio for non-blocking operations

import uasyncio as asyncio
import machine
import time
import network
from WIFI_CONFIG import SSID, PASSWORD
from controller import controller
from ota import OTAUpdater

wdt = machine.WDT(timeout=8000)
led = machine.Pin("LED", machine.Pin.OUT)

def wifi_connect(SSID, PASSWORD):
    """
    Connect to WLAN and return the IP address.
    """
    print(SSID, PASSWORD)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    count = 0 
    while count < 30:
        wlan.connect(SSID, PASSWORD)
        if not wlan.isconnected():
            print(f"Attempt {count} to connect... ")
            time.sleep(1)
            led.on()
            count += 1
        else:
            count = 60
            machine.reset() 
    
    if count == 30:
        print("Connection attempt failed")
        ip = 0
        led.off()
        time.sleep(60)
        ip = wifi_connect(SSID, PASSWORD)
    else:
        ip = wlan.ifconfig()[0]
        print("Connection Successful!")
        print(f'Connected on {ip}')
        led.off()
        
    return ip




async def main_controller():
    await asyncio.sleep(1)
    while True:
        if network.WLAN(network.STA_IF).isconnected():
            print("wifi is connected")
            controller.controller_stop()
            OTAUpdater.download_and_install_update_if_available()
            controller.controller_start()
            #controller.IO_Control()
            await asyncio.sleep(1)
        else:
            print("Wi-Fi disconnected. Reconnecting...")
            ip = wifi_connect(SSID, PASSWORD)
            if ip:
                print(f"Connected to Wi-Fi. IP: {ip}")
            else:
                print("Failed to connect to Wi-Fi. Retrying in the background...")
            await asyncio.sleep(1)
            
        # watchdog.feed()  # Reset watchdog timer to prevent auto-reset
        await asyncio.sleep(120)


async def feed_watchdog():
    """Periodically feeds the watchdog timer to prevent reset."""
    while True:
        print("Feeding watchdog...")
        wdt.feed()
        await asyncio.sleep(500)



async def blink_led():
    """Periodically blinks the LED."""
    while True:
        led.toggle()
        await asyncio.sleep(1)



async def background_task():
    while True:
        print(SSID, PASSWORD)
        await asyncio.sleep(5)

async def main_loop():
    # You can start multiple tasks here
    asyncio.create_task(feed_watchdog())
    #asyncio.create_task(blink_led())
    #asyncio.create_task(background_task())
    asyncio.create_task(main_controller())

    print("All tasks started, main loop sleeping indefinitely.")
    while True:
        await asyncio.sleep(3600) # Sleep for a long time, allowing other tasks to run
    

# ================= MAIN PROGRAM =================
# This is the entry point for asyncio
try:
    print("MicroPython OTA-enabled IoT Controller")
    print("Press Ctrl+C now to access REPL without running the application")
    asyncio.run(main_loop())
except KeyboardInterrupt:
    print("\nProgram interrupted by Ctrl+C")
    print("REPL is accessible for debugging")
except Exception as e:
    print(f"Fatal error: {e}")
    print("System halted, REPL is accessible for debugging")
finally:
    # Ensure the event loop is clean for the next run
    asyncio.new_event_loop()
    
