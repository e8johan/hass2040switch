# hass2040switch

This is a rp2040w-based Home Assistant light switch letting me control two lights (one dimmable, and one switch) from a pimoroni pico display.

# How to use

Put `main.py` onto your rp2040w, and create a `secrets.py` with the following variables:

```
token = 'YOUR HOME ASSISTANT REST API ACCESS TOKEN'
wlan_ssid = 'YOUR WLAN SSID'
wlan_psk = 'YOUR WLAN PSK'
hass_base_url = 'http://192.168.xx.yy:8123' # The IP / URL of your home assistant install
```

Then tweak what the various functions do, what POST requests to make to your HA, e.g.:

```
make_hass_post_request("light/turn_on", '{"entity_id":"light.dimmable_light_7", "brightness":"' + str(light_value) + '"}')
```

Which reads POST to `light/turn_on` with the data `{ ... }`.

The buttons have two callbacks, one for clicks and one for long-presses (which repeat), e.g. the button on pin 15 toggles the ceiling light on clicks and brightens it on a long press:

```
LampButton(15, action_toggle_ceiling, action_brighten_ceiling)
```

There's more and the code is pretty specific, but I leave it there for the interested reader to enjoy.
