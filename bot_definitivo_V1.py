import sys
import time
import random
import datetime
import telegram
import logging
from telegram.ext import MessageHandler, Updater, Filters
import RPi.GPIO as GPIO
import cv2
from skimage.measure import compare_ssim as ssim

# Set Gpio
GPIO.setmode(GPIO.BCM)
# Input
PB_DX = 23 # PushButtonDX
PB_SX = 24 # PushButtonSX
GPIO.setup([PB_SX, PB_DX], GPIO.IN)
# Output
POWER = 12 # Power relay
HBED = 16  # Heated bed relay
LIGHT = 25  # Light relay
INIT = 8   # Init relay
LED = 18   # LED
GPIO.setup([POWER, HBED, LIGHT, INIT, LED], GPIO.OUT)
GPIO.output([POWER, HBED, LIGHT, INIT, LED], GPIO.LOW)

# Global variable
state = [False, False, False, False, False, False, False]  # State of printer: ON/OFF, PRINTING, SHUTTING DOWN, MANUAL MODE, CAMERA BUSY, HEATED BED, LIGHT
chat_id = 25188214 # chat ID Ale Torri
control_var = 0 # How many controll()==True before
last_control = time.time()
last_msg = last_control
control_time = 30 #Determine the time for controll()

# On-off functions
def on(pin):
    GPIO.output(pin, GPIO.HIGH)
    return


def off(pin):
    GPIO.output(pin, GPIO.LOW)
    return

# Photo function
def photo(save):
    global state
    while state[4]:
        time.sleep(0.001)
    state[4] = True
    cam = cv2.VideoCapture(0)
    if cam.isOpened():
        ret, frame = cam.read()
        if ret:
            if save:
                cv2.imwrite("temp_image.jpg", frame)
            cam.release()
            state[4] = False
            return frame
        else:
            state[4] = False
            exit(1)
    else:
        state[4] = False
        exit(1)

# Controllin function   
def control():
    global control_var
    frame_1 = photo(False)
    cv2.waitKey(700)
    frame_2 = photo(False)
    sim = ssim(frame_1[0, :, :], frame_2[0, :, :], multichannel=True)
    if sim >= 0.85:
        control_var += 1
        print('Control passed True: %s' % control_var)
        return True
    else:
        control_var = 0
        return False

# Main loop for message income
def messageLoop(bot, update):
    global chat_id
    command = update.message.text

    print('Got command: %s' % command)
    
    global state
    if state[2]:
        if command == 'Y':
            off(HBED)
            time.sleep(0.01)
            off(POWER)
            bot.send_message(chat_id, text="Printer OFF")
            print('Printer OFF')
            state = [False, False, False, False, False, False, False]
        elif command == 'N':
            bot.send_message(chat_id, text="Keep printer ON")
            state[2] = False
        else:
            bot.send_message(chat_id, text="Input Y/N")
            return

    if command == 'On' and not state[0]:
        on(POWER)
        bot.send_message(chat_id, text='Printer ON')
        print('Printer ON')
        state[0] = True

    if command == 'Off' and state[0]:
        frame = photo(True)
        bot.send_photo(chat_id, open("temp_image.jpg", "rb"), '%s' %datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')) #Or better send GIF
        bot.send_message (chat_id, text = 'Do you want to shut down the printer?? (Y/N)')
        state[2] = True
          
    if command == 'Start' and state[0]:
        bot.send_message(chat_id, text='Start')
        state[1] = True

    if command == 'Stop' and state[0]:
        bot.send_message(chat_id, text = 'Stop')
        state[1] = False
    
    if command == 'Bed' and state[0]:
        if state[5]:
            bot.send_message(chat_id, 'Heated bed OFF')
            off(HBED)
            state[5] = False
        else:
            bot.send_message(chat_id, 'Heated bed ON')
            on(HBED)
            state[5] = True

    if command == 'Photo':
        frame = photo(True)
        bot.send_photo(chat_id, open("temp_image.jpg", "rb"), '%s' %datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    if command == 'State':
        bot.send_message(chat_id, 'State is: %s' % state)
        
    if command == 'Light':
        if state[6]:
            bot.send_message(chat_id, 'Light OFF')
            off(LIGHT)
            state[6] = False
        else:
            bot.send_message(chat_id, 'Light ON')
            on(LIGHT)
            state[6] = True        

bot = telegram.Bot('660828097:AAH3n-5T7jMX2CbHAVSkuSKCY9i0wN80Lc4')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
updater = Updater('660828097:AAH3n-5T7jMX2CbHAVSkuSKCY9i0wN80Lc4')
updater.dispatcher.add_handler(MessageHandler(Filters.text, messageLoop))
updater.start_polling()
print('I am listening...')

# Main loop
while 1:

    if (GPIO.input(PB_SX)): # ON-OFF Button
        while(GPIO.input(PB_SX)): # Debounce
            time.sleep(0.1)
        if (not state[0]):
            on(POWER)
            bot.send_message(chat_id, text='Printer ON')
            print('Printer ON')
            state[0] = True
        else:
            off(HBED)
            time.sleep(0.01)
            off(POWER)
            bot.send_message(chat_id, text="Printer OFF")
            print('Printer OFF')
            state = [False, False, False, False, False, False, False]
            control_var = 0

    if (GPIO.input(PB_DX)): # Manual Mode Button
        while(GPIO.input(PB_DX)): # Debounce
            time.sleep(0.1)
        if (not state[3]):
            on(LED)
            bot.send_message(chat_id, text='Manual Mode ON')
            print('Manual Mode ON')
            state[3] = True
        else:
            off(LED)
            bot.send_message(chat_id, text="Manual Mode OFF")
            print('Manual Mode OFF')
            state[3] = False
        
    if state[0] and state [1]: # Prinetr ON and Print ONGOING
        current_time = time.time()
        if current_time >= last_msg+1200:
            last_msg = current_time
            bot.send_message(chat_id, 'The print is going, OK!')
        control_time_1 = control_time
        if control_var > 1:
            control_time_1 = 30
        if current_time >= (last_control+control_time_1):
                last_control = current_time
                print('Controlling: %s' % last_control)
                flag = control()
                print('%s' % flag)
                if flag and control_var > 5:
                    ##shtu down request
                    print('Print DONE!')
                    bot.send_message(chat_id, 'Great, the printer is finished!!!')
                    control_var = 0
                time.sleep(0.02)
                    
    time.sleep(0.02)
        
                

while 1:
    try:   
        time.sleep(0.5)

    except KeyboardInterrupt:
        print('\n Program interrupted')
        GPIO.cleanup()
        exit()

    except:
        print('Other error or exception occured!')
        GPIO.cleanup()
        exit()

