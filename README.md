This library implements a python 3 library for the MCP23017 port expander chip. It is intended to be used on a Raspberry Pi in conjunction with the built in GPIO pins.


Requirements:

* python 3 port of Adafruit's I2C library, which is included in this repo
* python 3 smbus module. See [wiki](smbus python 3) for instructions to install on a Raspberry Pi.

Features:

* Simple digital input and output via all pins
* Input interrupts
* Interrupt port mirroring is configurable – either INTA and INTB can trigger independently for their respective GPIO port banks, or both INTA and INTB can trigger at the same time regardless of what GPIO pin causes the interrupt
* Configurable interrupt polarity – INT could pull the pin high or push it low
* Each GPIO pin can be configured for interrupts independently to either compare against the previous value or against a default pin value
* A utility method cleanupInterrupts that can be called periodically to clear the interrupt if it somehow gets stuck on.
