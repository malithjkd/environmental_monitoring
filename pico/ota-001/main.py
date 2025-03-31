import network
from time import sleep
from machine import Pin
import sys  # Import sys to read inputs from Thonny
from WIFI_CONFIG import SSID, PASSWORD
from controller import controller
from ota import OTAUpdater

firmware_url = "https://raw.githubusercontent.com/malithjkd/environmental_monitoring/refs/heads/master/pico/ota-001/"
ota_updater = OTAUpdater(firmware_url, "controller.py")
main_controller = controller()


# Initialize the onboard LED
pico_led = Pin("LED", Pin.OUT)


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
            sleep(1)
            pico_led.on()
            count += 1
        else:
            count = 60
    
    if count == 30:
        print("Connection attempt failed")
        ip = 0
        pico_led.off()
        sleep(60)
        ip = wifi_connect(SSID, PASSWORD)
    else:
        ip = wlan.ifconfig()[0]
        print("Connection Successful!")
        print(f'Connected on {ip}')
        pico_led.off()
        
    return ip


# Main function to run both tasks
def main():
    
    sleep(1)
    while True:
        if network.WLAN(network.STA_IF).isconnected():
            print("wifi is connected")
            main_controller.controller_stop()
            ota_updater.download_and_install_update_if_available()
            main_controller.controller_start()
            #main_controller.IO_Control()
            sleep(1)
        else:
            print("Wi-Fi disconnected. Reconnecting...")
            ip = wifi_connect(SSID, PASSWORD)
            if ip:
                print(f"Connected to Wi-Fi. IP: {ip}")
            else:
                print("Failed to connect to Wi-Fi. Retrying in the background...")
            sleep(1)
        
        sleep(120)
        
            
# Run the main function
main()

