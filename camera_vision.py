#!/usr/bin/env python3

import sys, requests, threading, time, ujson, queue, os, argparse, numpy as np, traceback
import zwoasi as asi
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer

asi.init('<PATH TO FILE>/ASI_linux_mac_SDK_V1.19.1/lib/x64/libASICamera2.so.1.19.1')

params_tab   = ['Exposure', 'Gain', 'Offset']
kill_app     = False
camera       = None
cam_settings = {}
kill_exp     = False


#############################################################################################


def f_camera_params(cam_obj, method):
  global cam_settings, params_tab, asi

  if method == 'initial':
    cam_settings['info'] = {}

    cam_settings['info']['data_path'] = '/dev/shm/' + args.cam_name.replace(' ', '_') + '.npy'
    cam_settings['info']['time_path'] = '/dev/shm/' + args.cam_name.replace(' ', '_') + '.time'
    cam_settings['info']['temperature'] = cam_obj.get_control_value(asi.ASI_TEMPERATURE)[0]/10

    for i in ['SupportedBins', 'IsColorCam', 'PixelSize', 'IsCoolerCam']:
      cam_settings['info'][i] = camera.get_camera_property()[i]

    if cam_settings['info']['IsCoolerCam']:
      params_tab.append('TargetTemp')
      params_tab.append('CoolerOn')

    for i in params_tab:
      cam_settings[i] = {}
      for j in ['DefaultValue', 'MinValue', 'MaxValue']:
        cam_settings[i][j] = cam_obj.get_controls()[i][j]
      cam_settings[i]['Value'] = cam_settings[i]['DefaultValue']

    cam_settings['Exposure']['Value'] = 1000000
    cam_settings['HardwareBin'] = {
      'DefaultValue': cam_settings['info']['SupportedBins'][0],
      'MinValue': cam_settings['info']['SupportedBins'][0],
      'MaxValue': cam_settings['info']['SupportedBins'][-1],
      'Value': cam_settings['info']['SupportedBins'][0],
      'depl': cam_settings['info']['SupportedBins'][0],
    }

    if cam_settings['info']['IsCoolerCam']:
      cam_settings['info']['cooler_pwr'] = cam_obj.get_control_value(asi.ASI_COOLER_POWER_PERC)[0]

    cam_settings['time'] = time.time()

  elif method == 'send_params_to_cam':
    cam_obj.set_control_value(asi.ASI_EXPOSURE,      int(cam_settings['Exposure']['Value']))
    cam_obj.set_control_value(asi.ASI_GAIN,          int(cam_settings['Gain']['Value']))
    cam_obj.set_control_value(asi.ASI_OFFSET,        int(cam_settings['Offset']['Value']))
    if cam_settings['info']['IsColorCam']:
      cam_obj.set_control_value(asi.ASI_WB_B,        int(cam_obj.get_controls()['WB_B']['DefaultValue']))
      cam_obj.set_control_value(asi.ASI_WB_R,        int(cam_obj.get_controls()['WB_R']['DefaultValue']))
    if cam_settings['info']['IsCoolerCam']:
      cam_obj.set_control_value(asi.ASI_TARGET_TEMP, int(cam_settings['TargetTemp']['Value']))
      cam_obj.set_control_value(asi.ASI_COOLER_ON,   int(cam_settings['CoolerOn']['Value']))

    camera.set_roi(bins=cam_settings['HardwareBin']['Value'])
    cam_settings['HardwareBin']['depl'] = camera.get_roi_format()[2]

    for i in params_tab:
      cam_settings[i]['depl']  = cam_settings[i]['Value']

    cam_settings['param_time'] = time.time()


#############################################################################################

parser = argparse.ArgumentParser(description='Serwowanie wizji kamery astro')
parser.add_argument('--cam_name',  dest='cam_name',  required=True, type=str,                                     help='Nazwa kamery w API')
parser.add_argument('--port',      dest='port',      required=True, type=int,                                     help='Port TCP serwera HTTP')
args = parser.parse_args()

#############################################################################################

class http_server(BaseHTTPRequestHandler):
  global cam_settings, args, kill_app, camera, kill_exp, camera

  def do_GET(self):
    global cam_settings, args, kill_app, camera
    try:
      if self.path == '/settings':
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        cam_settings['info']['temperature'] = camera.get_control_value(asi.ASI_TEMPERATURE)[0]/10
        if cam_settings['info']['IsCoolerCam']:
          cam_settings['info']['cooler_pwr'] = camera.get_control_value(asi.ASI_COOLER_POWER_PERC)[0]
        self.wfile.write(bytes(ujson.dumps(cam_settings), "utf-8"))
      elif self.path == '/shutdown':
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        kill_app = True
        self.wfile.write(bytes('OK', "utf-8"))
      else:
        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("Not found", "utf-8"))
    except:
      self.send_response(500)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(bytes('FAIL', "utf-8"))

  def do_POST(self):
    global cam_settings, args, kill_exp
    try:
      if self.path == '/set_settings':
        content_len = int(self.headers.get('Content-Length'))
        post_body = ujson.loads(self.rfile.read(content_len))
        if post_body == {}:
          raise NameError('nok')

        cam_settings['Exposure']['Value'] = post_body['Exposure']['Value']
        cam_settings['Gain']['Value'] = post_body['Gain']['Value']
        cam_settings['Offset']['Value'] = post_body['Offset']['Value']
        cam_settings['HardwareBin']['Value'] = post_body['HardwareBin']['Value']
        cam_settings['param_time'] = post_body['param_time']

        if 'TargetTemp' in post_body:
          cam_settings['TargetTemp']['Value'] = post_body['TargetTemp']['Value']

        if 'CoolerOn' in post_body:
          cam_settings['CoolerOn']['Value'] = post_body['CoolerOn']['Value']

        kill_exp = True

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes('ACK', "utf-8"))
      else:
        self.send_response(404)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("Not found", "utf-8"))
    except:
      self.send_response(500)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(bytes('FAIL', "utf-8"))

def f_http_server():
  while True:
    try:
      server = HTTPServer(("127.0.0.2", args.port), http_server)
      server.serve_forever()
    except:
      print('Can not start server')
      time.sleep(1)
      pass

#############################################################################################

def cam_capture(camobj):
  global kill_exp
  buffer_=None
  ASI_EXP_WORKING = 1
  ASI_EXP_SUCCESS = 2
  ASI_IMG_RAW16 = 2

  camobj.start_exposure()
  while camobj.get_exposure_status() == ASI_EXP_WORKING:
    if kill_exp:
      kill_exp = False
      camobj.stop_exposure()
      f_camera_params(cam_obj = camobj, method = 'send_params_to_cam')
      return []
    time.sleep(0.1)
  status = camobj.get_exposure_status()

  if status != ASI_EXP_SUCCESS:
    raise Exception('Could not capture image')

  data = camobj.get_data_after_exposure(buffer_)
  whbi = camobj.get_roi_format()
  shape = [whbi[1], whbi[0]]
  img = np.frombuffer(data, dtype=np.uint16)
  img = img.reshape(shape)
  return img

last_settings_time = 0
one_time_done = False
while kill_app == False:
  try:
    cameras_found = asi.list_cameras()
    camera = asi.Camera(cameras_found.index(args.cam_name))
    camera.stop_video_capture()
    camera.stop_exposure()
    camera.set_control_value(asi.ASI_BANDWIDTHOVERLOAD, int(camera.get_controls()['BandWidth']['MaxValue']*0.7))
    camera.disable_dark_subtract()
    f_camera_params(cam_obj = camera, method = 'initial')
    camera.set_image_type(asi.ASI_IMG_RAW16)
    f_camera_params(cam_obj = camera, method = 'send_params_to_cam')
    last_settings_time = cam_settings['param_time']
  except Exception as e:
    print(traceback.format_exc())
    time.sleep(0.3)
    try:
      camera.close()
    except:
      pass
    continue

  if not one_time_done:
    threading.Thread(target=f_http_server, daemon=True).start()
    one_time_done = True

  while kill_app == False:
    try:
      if last_settings_time != cam_settings['param_time']:
        f_camera_params(cam_obj = camera, method = 'send_params_to_cam')
        last_settings_time = cam_settings['param_time']

      while kill_app == False:
        out = cam_capture(camobj = camera)
        if len(out) > 0:
          break

      f = open(cam_settings['info']['time_path'], 'w')
      f.write(str(time.time()))
      f.close()
      np.save(cam_settings['info']['data_path'], out)

    except Exception as e:
      print(traceback.format_exc())
      time.sleep(0.3)
      break
  try:
    camera.close()
  except:
    pass

sys.exit(0)
