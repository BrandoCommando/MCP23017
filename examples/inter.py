#!/usr/bin/python

from Adafruit_I2C import Adafruit_I2C
from MCP23017 import MCP23017
from evdev import UInput, ecodes as e
import RPIO as GPIO
import sys
import math
import traceback
import time

keymap = [
	e.KEY_A, e.KEY_W, e.KEY_D, e.KEY_S, e.KEY_F, e.KEY_R, e.KEY_G, e.KEY_T, e.KEY_H, e.KEY_Y,
	e.KEY_LEFT, e.KEY_UP, e.KEY_RIGHT, e.KEY_DOWN, e.KEY_ENTER, e.KEY_SPACE, e.KEY_HOME, e.KEY_END, e.KEY_PAGEUP, e.KEY_PAGEDOWN,
	e.KEY_J, e.KEY_I, e.KEY_L, e.KEY_K, e.KEY_7, e.KEY_U, e.KEY_8, e.KEY_9,
	e.KEY_Z, e.KEY_X, e.KEY_C, e.KEY_B, e.KEY_N, e.KEY_M, e.KEY_Q, e.KEY_E
	]
btnmap = [
	0,1,2,3,4,5,6,7,8,9,
	10,11,12,13,14,15,16,17,18,19,
	20,21,22,23,24,25,26,27,
	28,29,30,31,32,33,34,35
	]
gpios = [15,18,23,24]
mcps = [[0x25,4,0,0],[0x26,14,16,0]]
labels = ["left","up","right","down","topleft","botleft","topmid","botmid","toprt","botrt"]

def readconfig():
	try:
		fh = open("inter.cfg","r+")
	except IOError as ie:
		fh = open("inter.cfg","w+")
	data = fh.readlines()
	if (len(data)==0):
		fh = open("inter.cfg","w+")
		fh.write(",".join(str(x) for x in btnmap))
		fh.close()
	if (len(data)>0):
		l1 = data[0].split(",")
		if (len(l1)==36):
			bmi=-1
			for x in l1:
				bmi = bmi + 1
				btnmap[bmi] = int(x)
			print("Button Config Loaded: %s" % (",".join(str(x) for x in btnmap)))
	if (len(data)>1):
		l2 = data[1].split(",")
		gpios=",".join(int(x) for x in data[1])
	if (len(data)>2):
		l3 = data[2].split(",")
		mcpcnt = len(l3)/2
		mcps = []
		for i in range(0,mcpcnt+1):
			mcps.append([int(l3[i*2],16),l3[(i*2)+1],16*i,0])

def setup():
	bmi = -1
	for player in range(1,5):
		ps = "Player %d" % (player)
		lbli = 0
		for label in labels:
			lbli = lbli + 1
			if (player > 2 and lbli > 8):
				continue
			bmi = bmi + 1
			cur = btnmap[bmi]
			print("Press button for %s %s [%s]: " % (ps, label, cur))
			btn=pollall()
			btn=pollall()
			print("Button pressed: %s" % (btn))
			btnmap[bmi] = btn
			time.sleep(0.5)
	fh = open("inter.cfg","w+")
	fh.write(",".join(str(x) for x in btnmap))
	fh.close()

def pollall():
	mcpi = -1
	while True:
		for mcpa in mcps:
			mcpi = mcpi + 1
			for pin in range(0,16):
				val=mcpa[3].input(pin)
				if (val==0):
					return int(mcpi*16) + int(pin)
		gpi=-1
		for gpio in gpios:
			gpi = gpi + 1
			val=GPIO.input(gpio)
			if (val==0):
				return int(16*len(mcps))+int(gpi);

# interrupt callback function
# just get the pin and values and print them
def intcall(k, val):
	mcpi=-1
	for mcpa in mcps:
		mcpi = mcpi + 1
		pin, value = mcpa[3].readInterrupt()
		if (type(pin).__name__=="int"):
			pin = (mcpi*16)+pin;
			try:
				pin=btnmap.index(pin)
			except Exception as ex:
				if (verbose):
					traceback.print_ex()
			kc=keymap[pin]
			if (verbose):
				lbli=bm%10
				pl=math.floor(bm/10) + 1
				if(pin>20):
					lbli=(bm-20)%8
					pl=math.floor((bm-20)/8) + 1
				lbl=labels[lbli]
				print("I(%d) %s %s %s %s %s" % (mcpi + 1, pin, value, kc, pl, lbl))
			ui.write(e.EV_KEY, kc, 1 - value)
			ui.syn()
		
def btncall(pin, value):
# 	if (type(pin).__name__=="int"):
	gpin=pin
	pin=(16*len(mcps))+gpios.index(pin)
	bm=btnmap.index(pin)
	kc=keymap[bm]
	if (verbose):
		print("G(%d) %s %s %s" % (gpin, pin, value, kc))
	ui.write(e.EV_KEY, kc, 1 - value)
	ui.syn()

try:
	ui = UInput(name="retrogame")
	
	readconfig()

	mcpi = 0
	
	verbose = 0
	mode = 1
	if (len(sys.argv) == 2 and sys.argv[1] == "setup"):
		mode = 2
	if (len(sys.argv) == 2 and sys.argv[1] == "verbose"):
		verbose = 1
	
	for mcpa in mcps:
		mcp = MCP23017(address = mcpa[0], num_gpios = 16) # MCP23017
		if (mode == 1):
			mcp.configSystemInterrupt(mcp.INTMIRRORON, mcp.INTPOLACTIVEHIGH)

		for pin in range(0,16):
			mcp.pinMode(pin, mcp.INPUT)
			mcp.pullUp(pin, 1)
			if (mode == 1):
				mcp.configPinInterrupt(pin, mcp.INTERRUPTON, mcp.INTERRUPTCOMPAREPREVIOUS)

		if (mode == 1):
			GPIO.add_interrupt_callback(mcpa[1], intcall, edge='both', pull_up_down=GPIO.PUD_DOWN)
		
		mcps[mcpi][3] = mcp
		mcpi = mcpi + 1
	
	for pin in gpios:
		GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		if (verbose):
			print("%s %s" % (pin, GPIO.input(pin)))
		if (mode == 1):
			GPIO.add_interrupt_callback(pin, btncall, edge='both', pull_up_down=GPIO.PUD_UP)

	if (mode == 2):
		setup()

	else:
		# regular GPIO wait for interrupts
		GPIO.wait_for_interrupts(threaded=True)
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
				if (type(mcpa[3]).__name__!="int"):
					mcpa[3].clearInterrupts()

except Exception as e:
	traceback.print_exc()
finally:
	for mcpa in mcps:
		if(type(mcpa[3]).__name__!="int"):
			mcpa[3].cleanup()
	GPIO.cleanup()
	ui.close()
