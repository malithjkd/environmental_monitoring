
# 24V Digital I/O Expansion Board for Raspberry Pi Pico W Datasheet

Link: https://docs.google.com/document/d/12GmoNtrdBUoliFpNDVI0cBlCPV6Y2Ioz_7njKLbrr48/edit?tab=t.0

**Technical Specification** 

| No | Description | Value | Unit |
| :---- | :---- | :---- | :---- |
| Isolated Input and output specification |  |  |  |
| 1.1 | Number of digital output | 9 | Each |
| 1.2 | Number of digital output | 6 | Each |
| 1.3 | Digital output voltage | 24 | Vdc |
| 1.4 | Digital input voltage | 24 | Vdc |
| 1.5 | Collector (load) current IC  | 100 | mA |
| Non-isolated  inputs and outputs |  |  |  |
| 2.1 | Number of analog input  | 3 | Each |
| 2.2 | Analog input voltage | 0\~3.0 | Vdc |
| 2.3 | Digital inputs or outputs \[shared pins J3\] | 4 | Each |
| 2.4 | Digital input or output voltage | 3.3 | Vdc |
| 2.5 | 3.3Vdc communication (UART/I2C/SPI)\[shaired pins J3\] | 1 | Each |
| Input power specification for AC |  |  |  |
| 3.1 | Input voltage range | 110 \- 250 | V |
| 3.2 | Maximum input current | 0.1 | A |
| 3.3 | Input frequency  | 50 / 60 | Hz |
| 3.4 | Maximum leakage current | 0.63 | mA |
| Input power specification for DC (when powering on without AC input) |  |  |  |
| 4.1 | Input voltage range | 21.6 \- 26.4 | V |
| 4.2 | Input current  | 0.5 | A |
| Operational condition  |  |  |  |
| 5.1 | Operational temperature | \-10  to 40 | C |
| Mechanical specification |  |  |  |
| 6.1 | Unit dimensions (L  x W x H) | 281 x 71.5 x 28 | mm |
| 6.2 | Unit weight | 350 | kg |

**Introduction**   
The remote I/O module is a WiFi-based remote terminal unit, designed to simplify integration of traditional industrial systems.

The remote I/O module has been meticulously engineered to seamlessly interface with 24Vdc systems and enable connectivity to WiFi networks. With the incorporation of input current filters, the module demonstrates exceptional performance even in high-noise environments. It offers versatile power options, accepting either 110V AC-240V AC or a 24Vdc power supply. Alongside its comprehensive connectivity features, encompassing 9 digital outputs and 6 digital inputs, the module also incorporates three 3.3Vdc analog sensory inputs. Subsequent chapters delve into detailed descriptions of the connection arrangements and appropriate pinouts for the system.

**1\. Document Scope**  
Document will cover the technical specifications of the OSIRIS Remote I/O module.

**2\. Module Overview**  
The OSIRIS Remote I/O module serves as a 24Vdc input and output interface for the Raspberry Pi Pico W microcontroller. Figure 2.1 offers a comprehensive overview of the module's connector interfaces, detailing the various input and output connections available.

![][image1]

**3\. Power supplies**   
The OSIRIS Remote I/O module offers flexible power options, allowing it to be powered using either:

* 110-240Vac via the J1 port  
* 24Vdc input via J2


However, it is important to note that powering the module using both power supplies simultaneously is not recommended, to avoid potential damage or instability.

**Powering up using AC voltages**  
When utilising 110-240Vac power supply via J1, connected to the mains supply, the J2 connector can also be utilised as a 24Vdc source, capable of supplying currents up to 300mA. For reference, the electrical specifications of the J1 input connector are outlined in Table 1, while the detailed connector pinout is provided in Table 2\.

Table 1: 110Vac \- 240Vac   Power input requirements

| Description  | Value  |
| :---- | :---: |
| Input voltage range | 100Vac \- 240Vac |
| Input frequency  | 50 / 60Hz |
| Input current rating | 0 \~ 0.24A  |
| Leakage current | 0.63 mA |

			  
Table 2: J1 connector 

| Pin | Signal | Description  |
| :---- | :---- | :---- |
| 1 | G | Ground |
| 2 | G | Ground |
| 3 | L | Live |
| 4 | N | Neutral |

**Powering up using DC voltage**  
The module can be powered directly using a 24Vdc source by connecting it to the J2 port. The input power specifications for this option are outlined in Table 3, and the detailed pinout for the J2 port is provided in Table 4\.

Table 3: 24Vdx   Power input requirements

| Description  | Value  |
| :---- | :---: |
| Input voltage range | 21.6Vdc \- 26.4Vdc |
| Reflected ripple current | 8 \- 20 mA p \- p |

Table 4: J2 connector 

| Pin | Signal | Description  |
| :---- | :---- | :---- |
| 1 | \- | Negative / Ground |
| 2 | \- | Negative / Ground |
| 3 | \+ | Positive |
| 4 | \+ | Positive |

**4\. Non-isolated communication**  
The J3 port grants access to various communication protocols supported by the microcontroller. The pin arrangement of the J3 port is outlined in Table 5\.

Table 5: J3 connector

| Pin | Signal | Description  |
| :---- | :---- | :---- |
| 1 | \+5Vdc | \+5Vdc  positive  |
| 2 | GPIO5 | UART1 RX / I2C0 SDA / SPI0 CSn |
| 3 | GPIO4 | UART1 TX / I2C SDA / SP00 RX |
| 4 | GPIO3 | I2C1 SCL / SPI0 TX |
| 5 | GPIO2 | I2C1 SDA / SPI0 SCK |
| 6 | GND | 0 Vdc connector / Ground  |

**5\. Non-isolated analog input connector**  
J4 port provides facilities to access microcontroller analog to digital converter capabilities. The port pin arrangement is summarised in table 6\. 

Table 6 : J4 connector

| Pin | Signal | Description  |
| :---- | :---- | :---- |
| 1 | ADC0 | Analog sensor input 0 |
| 2 | ADC1 | Analog sensor input 1 |
| 3 | AGND | Analog ground |
| 4 | ADC2 | Analog sensor input 2 |
| 5 | ADC-VREF | Analog input voltage ref |
| 6 | 3.3V | 3.3V voltage output |

**6\. Isolated 24V digital input**   
The J5 port establishes connections for 6 digital inputs to the module. The pinout for the digital input port is documented in Table 7\.

Table 7 : J5 port pinout

| Pin | GPIO | Signal | Description  |
| :---- | :---- | :---- | :---- |
| 1 | GPIO 16 | IN 0+  | Digital input 0 positive 24 Vdc in |
| 2 | GPIO 17 | IN 1+  | Digital input 1 positive 24 Vdc in |
| 3 | GPIO 18 | IN 2+  | Digital input 2 positive 24 Vdc in |
| 4 | GPIO 19 | IN 3+  | Digital input 3 positive 24 Vdc in |
| 5 | GPIO 20 | IN 4+  | Digital input 4 positive 24 Vdc in |
| 6 | GPIO 21 | IN 5+  | Digital input 5 positive 24 Vdc in |
| 7 |  | GND | 24Vdc ground input/ output |
| 8 |  | GND  | 24Vdc ground input / output |
| 9 |  | \+24 v dc | 24Vdc positive input / output |

**7\. Isolated 24V digital outputs**  
J6 and J7 house the connections for the 9 digital outputs. The pinouts for the connectors are provided in Table 8, while Table 9 details the specifications for the digital outputs.

Table 8 : J7 and J6 port pinout 

| Port | Pin | GPIO | Signal | Description  |
| :---- | :---- | :---- | :---- | :---- |
| J7 | 1 | GPIO 7 | OUT 0 \-  | Digital out 0 negative out (0 Vdc) |
| J7 | 2 | \- | OUT 0 \+ | Digital out 0 positive out (+24 Vdc) |
| J7 | 3 | GPIO 8 | OUT 1 \-  | Digital out 1 negative out (0 Vdc) |
| J7 | 4 | \- | OUT 1 \+ | Digital out 1 positive out (+24 Vdc) |
| J7 | 5 | GPIO 9 | OUT 2 \-  | Digital out 2 negative out (0 Vdc) |
| J7 | 6 | \- | OUT 2 \+ | Digital out 2 positive out (+24 Vdc) |
| J7 | 7 | GPIO 10 | OUT 3 \-  | Digital out 3 negative out (0 Vdc) |
| J7 | 8 | \- | OUT 3 \+ | Digital out 3 positive out (+24 Vdc) |
| J7 | 9 | GPIO 11 | OUT 4 \-  | Digital out 4 negative out (0 Vdc) |
| J6 | 1 | \- | OUT 5 \+ | Digital out 4 positive out (+24 Vdc) |
| J6 | 2 | GPIO 12 | OUT 5 \-  | Digital out 5 negative out (0 Vdc) |
| J6 | 3 | \- | OUT 6+ | Digital out 5 positive out (+24 Vdc) |
| J6 | 4 | GPIO 13 | OUT 6 \-  | Digital out 6 negative out (0 Vdc) |
| J6 | 5 | \- | OUT 7 \+ | Digital out 6 positive out (+24 Vdc) |
| J6 | 6 | GPIO 14 | OUT 7 \-  | Digital out 7 negative out (0 Vdc) |
| J6 | 7 | \- | OUT 8 \+ | Digital out 7 positive out (+24 Vdc) |
| J6 | 8 | GPIO 15 | OUT 8 \-  | Digital out 8 negative out (0 Vdc) |
| J6 | 9 | \- | OUT 8 \+ | Digital out 8 positive out (+24 Vdc) |

**8\. Dimensions** 

![][image2]

**9\. Ordering part numbers** 

Modules can be ordered with and without power supply and power filter connected. The below part numbers specify the module durings the ordering process.

| Pin | Part number | Description  |
| :---- | :---- | :---- |
| 1 | EAI0001A | Complete OSIRIS Remote I/O module with power supply and active nice filter. Able to power up the module using 24Vdc or 110-240V ac. |
| 2 | EAI0001B | OSIRIS Remote I/O module without power supply and active nice filter. Only able to power up using 24Vdc |

