#!/usr/bin/python

from Adafruit_I2C import Adafruit_I2C
from MCP23017 import MCP23017
from evdev import UInput, ecodes as e
import RPIO as GPIO
import sys
import math
import traceback
import time
import subprocess

keymap = [
	e.KEY_5, e.KEY_1, e.KEY_LEFT, e.KEY_UP, e.KEY_RIGHT, e.KEY_DOWN, e.KEY_ENTER, e.KEY_SPACE, e.KEY_HOME, e.KEY_END, e.KEY_PAGEUP, e.KEY_PAGEDOWN,
	e.KEY_6, e.KEY_2, e.KEY_A, e.KEY_W, e.KEY_D, e.KEY_S, e.KEY_F, e.KEY_R, e.KEY_G, e.KEY_T, e.KEY_H, e.KEY_Y,
	e.KEY_7, e.KEY_3, e.KEY_J, e.KEY_I, e.KEY_L, e.KEY_K, e.KEY_7, e.KEY_U, e.KEY_8, e.KEY_9,
	e.KEY_8, e.KEY_4, e.KEY_Z, e.KEY_X, e.KEY_C, e.KEY_B, e.KEY_N, e.KEY_M, e.KEY_Q, e.KEY_E
	]
btnmap = []
#goodgpios=[4,7,8,9,10,11,14,15,17,18,22,23,24,25,27,28]
goodgpios=[4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27]
gpios = []
#mcps = [[0x25,4,0,0,[]],[0x26,27,16,0,[]]]
mcps = []
labels = ["coin","start","left","up","right","down","topleft","botleft","topmid","botmid","toprt","botrt"]
gpiostate = {}
gpiopins = []
callbacks = []

def readconfig():
	try:
		fh = open("inter.cfg","r+")
	except IOError as ie:
		fh = open("inter.cfg","w+")
	data = fh.readlines()
	fh.close()
	if (len(data)==0):
		fh = open("inter.cfg","w+")
		fh.write(",".join(str(x) for x in range(0,44)))
		fh.close()
	if (len(data)>0):
		l1 = data[0].rstrip().split(",")
		if (len(l1)==(4*len(labels))-4):
			bmi=-1
			for x in l1:
				bmi = bmi + 1
				btnmap.append(int(x))
			print("Button Config Loaded: %s" % (",".join(str(x) for x in btnmap)))
		else:
			print("Bad Button config length: %d != %d" % (len(l1),(4*len(labels))-4))
	if (len(data)>1):
		l2 = data[1].rstrip().split(",")
		for x in l2:
			if(x!=""):
				gpios.append(int(x))
	if (len(data)>2):
		l3 = data[2].rstrip().split(",")
		mcpi = 0
		for i in range(0,len(l3)):
			if (l3[i] != ""):
				mcp = MCP23017(address = int(l3[mcpi]), num_gpios = 16) # MCP23017
				mcps.append([l3[mcpi],0,(16*i),mcp,[]])
				mcpi = mcpi + 1
	if (len(data)>3):
		l4 = data[3].rstrip().split(",")
		if(len(l4)==len(mcps)):
			mcpi = 0
			for x in l4:
				mcps[mcpi][1] = int(x)
				mcpi = mcpi + 1
	mcptxt=", ".join("%s %s" % (x[0],x[1]) for x in mcps)
	gpiotxt=",".join(str(x) for x in gpios)
	print("Current Config: MCPs: %s GPIOs: %s" % (mcptxt,gpiotxt))

def i2cd():
	raw = subprocess.check_output(["i2cdetect -y 1 | sed -e 's:^....::' | tail -n +3 | grep [0-9] | sed -e 's: \-\-::g' | tr ' ' '\\n' | grep [0-9] | tr '\\n' ' ' | sed -e 's:[^0-9]: :g' | sed -e 's:\s*$::'"], shell=True).decode("UTF8").split(" ")
	i=0
	ret=[]
	for x in raw:
		if(x!=""):
			ret.append(int(x,16))
	return ret

def setup():
	taken = []
	i2cs = i2cd()
	callbacks = []
	if(i2cs!=""):
		print("Found I2C devices: %s" % (", ".join(str(x) for x in i2cs)))
	else:
		print("No I2C devices found!")
	for mcpi in range(0,len(mcps)):
		if(type(mcps[mcpi][3]).__name__=="MCP23017"):
			mcps[mcpi][3].cleanup()
# 	for pin in goodgpios:
# 		GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	for addy in i2cs:
		while True:
			gpio=input("Enter callback pin for MCP at %s: " % (addy))
			if(gpio == ""):
				break
			if(gpio not in taken):
				taken.append(gpio)
				break
			else:
				print("Button %s already used" % gpio)
				time.sleep(0.5)
		if(gpio!=""):
			callbacks.append(gpio)
			time.sleep(0.5)
		else:
			break
	
	GPIO.cleanup()
	for x in gpiostate:
		gpiostate.remove(x)
	for mcpi in range(0,len(mcps)):
		print("Setting up %s on %s" % (mcps[mcpi][0],callbacks[mcpi]))
		mcp = setupMCP(int(mcps[mcpi][0]),int(callbacks[mcpi]))
		mcps[mcpi][3] = mcp[0]
		mcps[mcpi][4] = mcp[1]
	for pin in goodgpios:
		if(str(pin) not in callbacks):
			gpiostate[pin] = getgpio(pin)
			# GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
		
	bmi = -1
	for player in range(1,5):
		ps = "Player %d" % (player)
		lbli = 0
		for label in labels:
			lbli = lbli + 1
			if (player > 2 and lbli > len(labels) - 2):
				continue
			bmi = bmi + 1
			if(bmi in btnmap):
				cur = btnmap[bmi]
			else:
				cur = 0
			while True:
				btn=pollall("Press button for %s %s [%s]: " % (ps, label, cur))
				if(btn not in taken):
					taken.append(btn)
					break
				else:
					print("Button %s already used" % btn)
					time.sleep(0.5)
# 			print("Button pressed: %s" % (btn))
			btnmap[bmi] = btn
			time.sleep(0.5)

	print(",".join(str(x) for x in btnmap))
	print(",".join(str(x) for x in gpios))
	print(",".join(str(x) for x in i2cs))
	print(",".join(callbacks))

	fh = open("inter.cfg","w+")

	for i in range(0,len(btnmap)):
		fh.write(str(btnmap[i]))
		if(i < len(btnmap) - 1):
			fh.write(",")
		else:
			fh.write("\n")
	fh.write("%s\n" % ",".join(str(x) for x in gpios))
	fh.write("%s\n" % ",".join(str(x) for x in i2cs))
	fh.write("%s\n" % ",".join(callbacks))
	
	fh.close()
	
	print("Done writing to inter.cfg")

def getgpio(pin):
	if (str(pin) in callbacks):
		return False
	if (pin < 32 and pin in goodgpios):
		if (pin not in gpiostate):
			GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		try:
			state = GPIO.input(pin)
		except Exception as e:
			state = gpiostate[pin]
	elif (pin >= 32):
		mcpi = int(pin / 32) - 1
		pin = pin % 16
		if(mcpi in mcps and type(mcps[mcpi][3]).__name__=="MCP23017" and mcps[mcpi][3].connected == 1):
			state = mcps[mcpi][3].input(pin)
		else:
			return -1
	else:
		return -1
	gpiostate[pin] = state
	return state

def pollall(prompt=False, mcp=True):
	starts = {}
	# 1st set defaults
	for pin in goodgpios:
		starts[pin] = getgpio(pin)
	if(mcp == True):
		for mcpi in range(0,len(mcps)):
			mcp = mcps[mcpi][3]
			if(type(mcp).__name__!="MCP23017"):
				continue
			if(mcp.connected != 1):
				continue
			for ch in range(0,16):
				pin=32+(16*mcpi)+ch
				val=mcp.input(ch)
				starts[pin]=val

	# 2nd show prompt
	if(prompt != False):
		print(prompt)
		time.sleep(0.5)

	# Now poll
	while True:
		for pin in goodgpios:
			val=getgpio(pin)
			if(starts[pin]!=val):
				if(prompt != False):
					print(pin)
				return pin
		if(mcp == False):
			continue
		for mcpi in range(0,len(mcps)):
			mcp = mcps[mcpi][3]
			if(type(mcp).__name__!="MCP23017"):
				continue
			if(mcp.connected != 1):
				continue
			for ch in range(0,16):
				pin=32+(16*mcpi)+ch
				val=mcp.input(ch)
				if(pin not in starts):
					starts[pin] = val
				if(starts[pin]!=val):
					if(prompt != False):
						print(pin)
					return pin

# interrupt callback function
# just get the pin and values and print them
def intcall(k, val):
	mcpi=-1
	for mcpa in mcps:
		if(type(mcpa[3]).__name__!="MCP23017"):
			continue
		mcpi = mcpi + 1
		pin, value = mcpa[3].readInterrupt()
		if (type(pin).__name__=="int"):
			pin = 32+(mcpi*16)+pin;
			gpin=pin
			if(pin in btnmap):
				pin=btnmap.index(pin)
			kc=keymap[pin]
			if (verbose):
				lbli=pin%10
				pl=math.floor(pin/11) + 1
				if(pin>32):
					lbli=(pin-33)%10
					pl=math.floor((pin-20)/10) + 1
				lbl=labels[lbli]
				if (value==0):
					print("I(%d) %s %s %s %s %s %s" % (mcpi + 1, gpin, pin, value, kc, pl, lbl))
			ui.write(e.EV_KEY, kc, 1 - value)
			ui.syn()
		
def btncall(pin, value):
# 	if (type(pin).__name__=="int"):
	gpin=pin
	if(pin in btnmap):
		pin = btnmap.index(pin)
# 	if(bm not in keymap):
# 		print("%s not found" % bm)
# 		return
	kc = keymap[pin]
	if (verbose and value==0):
		print("G(%d) %s %s %s" % (gpin, pin, value, kc))
	ui.write(e.EV_KEY, kc, 1 - value)
	ui.syn()
	
def setupMCP(addy,callpin):
	if(verbose):
		print("Callback: %s: %s" % (addy, callpin))
	mcp = MCP23017(address = addy, num_gpios = 16)
	if(mcp.connected != 1):
		print("Unable to setup MCP on %s" % addy)
		return [-1,[]]
	success = mcp.configSystemInterrupt(mcp.INTMIRRORON, mcp.INTPOLACTIVEHIGH)
	states = []
	for pin in range(0,16):
		mcp.pinMode(pin, mcp.INPUT)
		mcp.pullUp(pin, 1)
		mcp.configPinInterrupt(pin, mcp.INTERRUPTON, mcp.INTERRUPTCOMPAREPREVIOUS)
		val = mcp.input(pin)
		states.append(mcp.input(pin))
	GPIO.add_interrupt_callback(callpin, intcall, edge='both', pull_up_down = GPIO.PUD_DOWN)
	gpiostate[callpin] = 2
	return [mcp,states]
	
def cleanup():
	for addy in i2cd():
		mcp = MCP23017(address = addy, num_gpios = 16)
		mcp.cleanup()
	GPIO.cleanup()
	print("All cleaned up.")

try:
	ui = UInput(name="retrogame")
	
	i2cs = i2cd()
	
	readconfig()

	mcpi = 0
	
	verbose = 0
	mode = 1
	if (len(sys.argv) == 2 and sys.argv[1] == "setup"):
		setup()
	if (len(sys.argv) == 2 and sys.argv[1] == "verbose"):
		verbose = 1
	
	for mcpi in range(0,len(i2cs)):
		addy=i2cs[mcpi]
		if(mcpi not in mcps):
			mcps.append([addy,4,32+(mcpi*16),0,[]]);
		mcpa = mcps[mcpi]

		mcpp = setupMCP(i2cs[mcpi], mcpa[1])
		mcps[mcpi][3] = mcpp[0]
		mcps[mcpi][4] = mcpp[1]
	
	for pin in gpios:
		if (type(pin).__name__!="int" or pin == 0):
			continue
		if (verbose):
			print("Setting up %s" % pin)
		GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		if (verbose):
			print("%s %s" % (pin, GPIO.input(pin)))
		if (mode == 1):
			GPIO.add_interrupt_callback(pin, btncall, edge='both', pull_up_down=GPIO.PUD_UP)

	if (mode == 2):
		setup()

	else:
		# regular GPIO wait for interrupts
		if(len(mcps)>0):
			thread=True
		else:
			thread=False
		GPIO.wait_for_interrupts(threaded=thread)
		while (True):
			time.sleep(.5)
# 			mcp.output(ledpin, 1)
# 			time.sleep(.2)
# 			mcp.output(ledpin, 0)
# 			time.sleep(.3)
			# this is a failsafe for the instance when two interrupts happen before 
			# the debounce timeout expires. it will check for interrupts on the pin 
			# three times in a row, .5 seconds apart. if it gets to the end of 3 
			# iterations, we're probably stuck so it will reset
			for mcpa in mcps:
				if (type(mcpa[3]).__name__=="MCP23017"):
					mcpa[3].clearInterrupts()

except Exception as e:
	traceback.print_exc()
finally:
	cleanup()
	ui.close()
