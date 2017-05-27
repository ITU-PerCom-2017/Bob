import time
import binascii
import pycom
import socket
import _thread
from machine import I2C
from machine import Pin
from struct import unpack
from network import LoRa
from network import WLAN



# Hardcoded values for colors at lower brightness.
off = 0x000000
red = 0x220000
green = 0x002200
blue = 0x000022


# Hardcoded values declaring variables for emon.itu.dk.
tempVar = b'\xAA'
moistVar = b'\xBB'
lightVar = b'\xCC'


# Values for SDA and SCL pins positions.
SDA = Pin.exp_board.G17
SCL = Pin.exp_board.G16

#values for PIR
p_in=Pin(Pin.exp_board.G10, mode=Pin.IN, pull=Pin.PULL_UP)


class Chirp:
	def __init__(self, address):
		self.i2c = I2C(0, I2C.MASTER, baudrate=10000)
		self.address = address

	def get_reg(self, reg):
		val = unpack('<H', (self.i2c.readfrom_mem(self.address, reg, 2)))[0]
		return (val >> 8) + ((val & 0xFF) << 8)

	def moist(self):
		return self.get_reg(0)

	def temp(self):
		return self.get_reg(5)

	def light(self):
		self.i2c.writeto(self.address, '\x03')
		time.sleep(1.5)
		return self.get_reg(4)

class LoRaNetwork:
	def __init__(self):
		# Turn off hearbeat LED
		pycom.heartbeat(False)
		# Initialize LoRaWAN radio
		self.lora = LoRa(mode=LoRa.LORAWAN)
		# Connect to sensors.
		#wlan = WLAN(mode=WLAN.STA)
		# Uncomment next line to disable wifi
		#wlan.deinit()
		# go for fixed IP settings (IP, Subnet, Gateway, DNS)
		   
		# Set network keys
		app_eui = binascii.unhexlify('70B3D57EF0003F19')
		app_key = binascii.unhexlify('0EFCC322B67F7BC848E683AD0A27F64A')
		# Join the network
		self.lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)
		#pycom.rgbled(red)
		# Loop until joined
		while not self.lora.has_joined():
			print('Not joined yet...')
			pycom.rgbled(off)
			time.sleep(0.1)
			#pycom.rgbled(red)
			pycom.rgbled(red)
			time.sleep(0.1)
			pycom.rgbled(green)
			time.sleep(0.1)
			pycom.rgbled(blue)
			time.sleep(0.1)
			pycom.rgbled(off)
			time.sleep(2)
		print('Joined')
		#pycom.rgbled(blue)
		self.s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
		self.s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)
		self.s.setblocking(True)
		self.bytesarraytemp = bytearray(2)
		#sensor
		addr = 0x20 #or 32
		self.chirp = Chirp(addr)

	def convertbytes(self, data):
		self.bytesarraytemp[0] = (data & 0xFF00) >> 8
		self.bytesarraytemp[1] = (data & 0x00FF)
		return self.bytesarraytemp
	
	def senddata(self):
		while True:
			print("temp")
			print(self.chirp.temp())
			count = self.s.send(tempVar+self.convertbytes(self.chirp.temp()))
			#print(count)
			print("moist")
			globalMoist=self.chirp.moist()
			print(globalMoist)
			count = self.s.send(moistVar+self.convertbytes(self.chirp.moist()))	
			#print(count)
			print("light")
			print(self.chirp.light())
			count = self.s.send(lightVar+self.convertbytes(self.chirp.light()))
			#print(count)
			#pycom.rgbled(green)
			time.sleep(0.5)
			#pycom.rgbled(blue)
			time.sleep(50)
            
def th_func(chi):
    # get data from the sensor / thread function
    pir_state=0
    while True:
        while True:
            #detecting movement
			if p_in()==1:
#				if pir_state==0 and globalMoist<350 :
#					print("motion detected")
#					pycom.rgbled(red)
#					pir_state=1
#				if pir_state==0 and globalMoist>350 :
#					print("motion detected")
#					pycom.rgbled(blue)
#					pir_state=1
				if pir_state==0:
					local=chi.moist()
					print("ici")
					print(local)
					if local<300:#might need some change here : maybe 250? or 275?
						print("motion detected")
						pycom.rgbled(red)
						pir_state=1
					else:
						print("motion detected")
						pycom.rgbled(blue)
						pir_state=1
                        
                    

			else:
				if pir_state==1:
					print("motion ended")
					pir_state=0
					pycom.rgbled(green)
					time.sleep(0.5)
					pycom.rgbled(off)
            
        

wlan = WLAN()
wlan.mode(WLAN.STA)
nets = wlan.scan()
for net in nets:
    if net.ssid == 'sensors':
        print('Network found!')
        wlan.connect(net.ssid, auth=(net.sec, 'n0n53n53'), timeout=5000)
        while not wlan.isconnected():
            print('Wlan not connected')
            time.sleep(0.5)
        print('WLAN connection succeeded!')
        print('Connected to with IP address: ' + wlan.ifconfig()[0])
        break
start = LoRaNetwork()
#start thread function
_thread.start_new_thread(th_func, (start.chirp, ))

while True :
    start.senddata()


