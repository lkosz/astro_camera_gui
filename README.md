## GUI for astrocameras

### camera_vision.py

This app gets frame from ASI camera and store in /dev/shm. It'll be read by second app

### app1.py app2.py

app1 is older one, for EQ5 DIY GOTO
app2 is new, used with EQ6-R mount

This app have following functions:
- via REST API send query to camera_vision.py to get frame from camera, then read it and show
- control camera settings via REST API and camera_vision.py
- live set filters (contrast, brightness, gamma, histogram stretch)
- store images
- platesolving using astrometry package and store actual position
- draw solved image + grid + star description using two star catalogues: Tycho2 and HD
- generate link to sky map with marked frame on that map (as in nova.astrometry.net)
- control EQ5 DIY GOTO (app1.py only)
- control focuser
- control filterwheel
- guiding (app1.py only)
