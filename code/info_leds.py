import socket
import time
from gpiozero import LED

led = LED(14)

def check_internet(host="1.1.1.1", port=53, timeout=3):
	try:
		socket.setdefaulttimeout(timeout)
		socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
		return True
	except OSError:
		return False

led.blink(on_time=0.5, off_time=0.5)
was_connected = False

while True:
	is_connected = check_internet()
	
	if is_connected and not was_connected:
		led.on()
		was_connected = True
	elif not is_connected and was_connected:
		led.blink(on_time=0.5,off_time=0.5)
		was_connected = False
	
	time.sleep(5)
