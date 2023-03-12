# Copyright 2023 Johan Thelin
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import network
import urequests
import json
import time
from pimoroni import Button, RGBLED
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY, PEN_P4
from secrets import token, wlan_ssid, wlan_psk, hass_base_url

display = PicoGraphics(display=DISPLAY_PICO_DISPLAY, pen_type=PEN_P4, rotate=90)

# Darken the display during start-up
pen_black = display.create_pen(0, 0, 0)
display.set_pen(pen_black)
display.clear()
display.update()
display.set_backlight(0.0)

# Use the RGB to indicate WiFi status
led = RGBLED(6, 7, 8)
led.set_rgb(255, 0, 0)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
led.set_rgb(255, 100, 0)

wlan.connect(wlan_ssid, wlan_psk)

odd = True
while not wlan.isconnected() and wlan.status() >= 0:
    if odd:
        led.set_rgb(255, 100, 0)
    else:
        led.set_rgb(0, 0, 0)
    odd = not odd
    time.sleep(1)
    
# Turn off LED and go on with life
led.set_rgb(0, 0, 0)

width, height = display.get_bounds()

class LampButton(Button):
    def __init__(self, pin, action, long_action):
        Button.__init__(self, pin)
        self.__counter = 0
        self.__long_counter = 0
        self.__action = action
        self.__long_action = long_action
        self.__is_pressed = False
        
    def down(self):
        if self.__counter == 0:
            self.__is_pressed = True
        self.__counter = 8
        self.__long_counter += 1
        if self.__long_counter > 32:
            self.__is_pressed = False
            if self.__long_action:
                self.__long_action()

    def up(self):
        self.__counter = max(0, self.__counter-1)
        if self.__counter > 0:
            self.__long_counter += 1
        else:
            if self.__long_counter < 32 and self.__is_pressed == True:
                self.__is_pressed = False
                if self.__action:
                    self.__action()
            self.__long_counter = 0
    
    def is_down(self):
       return self.__counter > 0
    
    def is_long(self):
        return self.__long_counter >= 32

def make_hass_get_request(service, show_led):
    # Use the LED to indicate request status
    if show_led:
        led.set_rgb(100, 50, 0)
    r = urequests.get(hass_base_url + "/api/states/" + service, headers={'Authorization': 'Bearer '+token, 'content-type': 'application/json'})
    if r.status_code != 200:
        led.set_rgb(255, 0, 0)
    else:
        led.set_rgb(0, 0, 0)
    res = r.content
    r.close()
    return res

light_value = 128
window_state = False
ceiling_state = False

def poll_states(show_led):
    global window_state, ceiling_state, light_value
    data = json.loads(make_hass_get_request('light.dimmable_light_7', show_led))
    ceiling_state = data['state'] == 'on'
    if ceiling_state:
        light_value = data['attributes']['brightness']
    window_state = json.loads(make_hass_get_request('switch.fonsterlampan_sovrum', show_led))['state'] == 'on'

# Initialize
poll_states(True)

def make_hass_post_request(service, data):
    # Use the LED to indicate request status
    led.set_rgb(100, 50, 0)
    r = urequests.post(hass_base_url + "/api/services/" + service, data=data, headers={'Authorization': 'Bearer '+token, 'content-type': 'application/json'})
    if r.status_code != 200:
        led.set_rgb(255, 0, 0)
    else:
        led.set_rgb(0, 0, 0)
    r.close()

def action_toggle_window():
    global window_state
    if window_state == True:
        make_hass_post_request("switch/turn_off", '{"entity_id":"switch.fonsterlampan_sovrum"}')
        window_state = False
    else:
        make_hass_post_request("switch/turn_on", '{"entity_id":"switch.fonsterlampan_sovrum"}')
        window_state = True

def action_brighten_ceiling():
    global ceiling_state, light_value
    ceiling_state = True
    light_value = min(255, light_value+10)
    make_hass_post_request("light/turn_on", '{"entity_id":"light.dimmable_light_7", "brightness":"' + str(light_value) + '"}')

def action_dim_ceiling():
    global ceiling_state, light_value
    light_value = max(0, light_value-10)
    ceiling_state = True
    make_hass_post_request("light/turn_on", '{"entity_id":"light.dimmable_light_7", "brightness":"' + str(light_value) + '"}')

def action_toggle_ceiling():
    global ceiling_state
    if ceiling_state == True:
        make_hass_post_request("light/turn_off", '{"entity_id":"light.dimmable_light_7"}')
        ceiling_state = False
    else:
        make_hass_post_request("light/turn_on", '{"entity_id":"light.dimmable_light_7"}')
        ceiling_state = True
        

buttons = [
    LampButton(12, action_toggle_window, None),
    LampButton(13, action_toggle_window, None),
    LampButton(14, action_toggle_ceiling, action_dim_ceiling),
    LampButton(15, action_toggle_ceiling, action_brighten_ceiling)
    ]

pen_outline = display.create_pen(23, 89, 196)
pen_light = display.create_pen(196, 196, 0)

backlight_timer = 0
backlight = 1.0

lamp_outlines = [
        [64, 20, 24],
        [49, 45, 2],
        [48, 47, 2],
        [47, 49, 2],
        [46, 51, 2],
        [45, 53, 2],
        [44, 55, 2],
        [43, 57, 2],
        [42, 59, 2],
        [41, 61, 2],
        [40, 63, 2],
        [39, 65, 2],
        [38, 67, 2],
        [37, 69, 2],
        [36, 71, 2],
        [35, 73, 2],
        [34, 75, 2],
        [33, 77, 2],
        [32, 79, 2],
        [31, 81, 2],
        [30, 83, 2],
        [59, 90, 3],
        [60, 93, 2],
        [61, 95, 2],
        [62, 97, 1],
        [64, 98, 1],
        [66, 99, 1],
        [53, 130, 2],
        [52, 132, 3],
        [51, 135, 4],
        [50, 139, 3],
        [49, 142, 4],
        [48, 146, 3],
        [47, 149, 4],
        [46, 153, 3],
        [45, 156, 4],
        [44, 160, 3],
        [43, 163, 2],
        [62, 170, 49],
        [48, 220, 9],
    ]

ceiling_outline = [
        [54, 55, 2],
        [53, 57, 2],
        [52, 59, 2],
        [51, 61, 2],
        [50, 63, 2],
        [49, 65, 2],
        [48, 67, 2],
        [47, 69, 2],
        [46, 71, 2],
        [45, 73, 2],
    ]

window_outline = [
        [59, 140, 2],
        [58, 142, 3],
        [57, 145, 4],
        [56, 149, 3],
        [55, 152, 3],
    ]

def draw_outline(display, pen, outline):
    display.set_pen(pen)
    for line in outline:
        display.rectangle(line[0], line[1], width-2*line[0]+1, line[2]+1)

poll_counter = 1800

while True:
    display.set_pen(pen_black)
    display.clear()
    draw_outline(display, pen_outline, lamp_outlines)
    if window_state:
        draw_outline(display, pen_light, window_outline)
    else:
        draw_outline(display, pen_black, window_outline)
    if ceiling_state:
        draw_outline(display, pen_light, ceiling_outline)
    else:
        draw_outline(display, pen_black, ceiling_outline)
    
    display.set_pen(pen_light)
    for b in buttons:
        if b.raw():
            b.down()
            backlight_timer = 0
        else:
            b.up()

    if buttons[2].is_down():
        if buttons[2].is_long():
            display.circle(20, 20, 16)
        else:
            display.circle(20, 20, 12)
    if buttons[0].is_down():
        if buttons[0].is_long():
            display.circle(20, height-20, 16)
        else:
            display.circle(20, height-20, 12)
    if buttons[3].is_down():
        if buttons[3].is_long():
            display.circle(width-20, 20, 16)
        else:
            display.circle(width-20, 20, 12)
    if buttons[1].is_down():
        if buttons[1].is_long():
            display.circle(width-20, height-20, 16)
        else:
            display.circle(width-20, height-20, 12)
    
    # Backlight timer
    if backlight_timer > 250:
        backlight = backlight * 0.95
        if backlight < 0.1:
            backlight = 0.0
        display.set_backlight(backlight)
    elif backlight_timer == 0:
        backlight_timer += 1
        backlight = 1.0
        display.set_backlight(backlight)
    else:
        backlight_timer += 1
        backlight = 1.0

    display.update()
    time.sleep(0.01)
    poll_counter -= 1
    if poll_counter <= 0:
        poll_states(False)
        poll_counter = 1800
