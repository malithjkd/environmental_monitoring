# Rpi pico W based enviromental condition monitoring


## RPI Pico W (micropython) UART communication with Sensorair S8

Pico W used to programed with micropython and all the documentation for Sensorair S8 written for python.  
The follwoing figure illustrate the connection have to make to enable the communication bitween sensor and RPI Pico W. 
The [sensorair_test.py](https://github.com/malithjkd/environmental_monitoring/blob/master/pico/sensorair_test.py) communication and getting feedback from the sensor. 


<img src="/docs/assets/Sensor_Air_S8_connect_to_raspberry_pi_pico_w.jpg" alt="/docs/assets/Sensor_Air_S8_connect_to_raspberry_pi_pico_w.jpg" width="900"/>

https://github.com/malithjkd/environmental_monitoring/blob/master/docs/assets/Sensor_Air_S8_connect_to_raspberry_pi_pico_w.jpg




### Install mosquitto 

Install mosquitto on raspberry pi 

```consol
sudo apt update && sudo apt upgrade
```

```consol
sudo apt install -y mosquitto mosquitto-clients
```

test running or not
```cernal
mosquitto -v
```

enable defalt start

```cernal
sudo systemctl enable mosquitto.service
```

https://randomnerdtutorials.com/how-to-install-mosquitto-broker-on-raspberry-pi/#mosquitto-set-user-password