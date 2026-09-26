import gpiozero
import time
from RPLCD.i2c import CharLCD

lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, rows=2, dotsize=8)
abs=["a","b","c","d","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","w","x","y","z","å","ä","ö","1","2","3","4","5","6","7","8","9","0",",",".","-","_",";",":"]
lcd.clear()

swt=gpiozero.Button(17)
swt2=gpiozero.Button(26) 
touch=gpiozero.DigitalInputDevice(23, pull_up=False)

lcd.cursor_mode = 'blink'

index=0
cursor=0


print("press ctrl+c to exit")
while True:
	if index == len(abs):
		index=0
	if swt.is_pressed:
		if cursor == 0:
			print("out of bounds")
		else:		
			cursor-=1
	lcd.cursor_pos = (0,4)
	if swt2.is_pressed:
		cursor+=1
	if touch.value == 1:
		if index==(len(abs)-1):
			index=0
		else:
			index+=1
			time.sleep(0.7)

	lcd.cursor_pos = (0,cursor)
	lcd.write_string(str(abs[index]))
 

	time.sleep(0.2)
