import network
import urequests
import os
import json
import machine
from time import sleep

class OTAUpdater:
    """ This class handles OTA updates. It connects to the Wi-Fi, checks for updates, downloads and installs them."""
    def __init__(self, repo_url, filename):
        self.filename = filename
        self.repo_url = repo_url
    
    def get_current_fw_version(self):
        # get the current version (stored in version.json)
        if 'version.json' in os.listdir():    
            with open('version.json') as f:
                self.current_version = float(json.load(f)['version'])
            f.close()
            print(f"Current device firmware version is '{self.current_version}'")

        else:
            self.current_version = 0
            # save the current version
            with open('version.json', 'w') as f:
                json.dump({'version': self.current_version}, f)
        
        

        
    def check_for_updates(self):
        self.version_url = self.repo_url + 'version.json'
        print(f'Checking for latest version... on {self.version_url}')
        response = urequests.get(self.version_url)
        data = json.loads(response.text)
                
        self.latest_version = float(data['version'])
        print(f'latest version is: {self.latest_version}')
        
        #get current verson
        self.get_current_fw_version()
        
        # compare versions
        newer_version_available = True if self.current_version < self.latest_version else False
        
        print(f'Newer version available: {newer_version_available}')    
        return newer_version_available

    
    def fetch_latest_code(self)->bool:
        """ Fetch the latest code from the repo, returns False if not found."""
        print("fetch_latest_code started")
        self.firmware_url = self.repo_url + self.filename
        
        # Fetch the latest code from the repo.
        response = urequests.get(self.firmware_url)
        if response.status_code == 200:
            print(f'Fetched latest firmware code, status: {response.status_code}, -  {response.text}')
    
            # Save the fetched code to memory
            self.latest_code = response.text
            
            return True
        
        elif response.status_code == 404:
            print(f'Firmware not found - {self.firmware_url}.')
            return False


    def update_no_reset(self):
        """ Update the code without resetting the device."""

        # Save the fetched code and update the version file to latest version.
        with open('latest_code.py', 'w') as f:
            f.write(self.latest_code)
        
        # update the version in memory
        self.current_version = self.latest_version

        # save the current version
        with open('version.json', 'w') as f:
            json.dump({'version': self.current_version}, f)
        
        # free up some memory
        self.latest_code = None
        
    
    def update_and_reset(self):
        """ Update the code and reset the device."""

        print(f"Updating device... (Renaming latest_code.py to {self.filename})", end="")

        # Overwrite the old code.
        os.rename('latest_code.py', self.filename)  

        # Restart the device to run the new code.
        print('Restarting device...')
        machine.reset()  # Reset the device to run the new code.
        
        
        

    def download_and_install_update_if_available(self):
        """ Check for updates, download and install them."""
        if self.check_for_updates():
            if self.fetch_latest_code():
                print("inside if state")
                self.update_no_reset() 
                self.update_and_reset() 
        else:
            print('No new updates available.')

