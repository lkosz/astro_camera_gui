#!/usr/bin/env python3

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import *
from astropy import units as u,wcs
from astropy.coordinates import Angle,EarthLocation,SkyCoord,AltAz
from astropy.io import fits
from astropy.time import Time
from astropy.utils.exceptions import AstropyWarning
from collections import deque
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg, sys, requests, threading, time, json, queue, numpy as np, subprocess, datetime, os, tifffile as tiff, traceback, warnings
os.environ["OPENCV_LOG_LEVEL"] ="OFF"
import cv2
warnings.simplefilter('ignore', category=AstropyWarning)

#############################################################################################

kill_thread = False
req_cmd = queue.Queue()
req_canon = queue.Queue()
sterownik_uri = 'http://eq1.embedded'
t_telescope = {
  'ra':  Angle('00h00m00s'),
  'dec': Angle('00d00m00s'),
  'alt': Angle('00d00m00s'),
  'az':  Angle('00d00m00s'),
  'loc': EarthLocation(lat=51.0982246264821*u.deg, lon=17.019650955565243*u.deg, height=134*u.m),
}
screen = None
connection_ok = False
filter_reset_done = False

q_a120mc_platesolve = deque(maxlen=1)
q_a120mc_raw        = deque(maxlen=2)
q_a120mc_ready      = deque(maxlen=2)
q_a120mc_save_to_file = deque(maxlen=100)
q_a120mm_platesolve = deque(maxlen=1)
q_a120mm_raw        = deque(maxlen=2)
q_a120mm_ready      = deque(maxlen=2)
q_a120mm_save_to_file = deque(maxlen=100)
q_a183mm_platesolve   = deque(maxlen=1)
q_a183mm_raw          = deque(maxlen=2)
q_a183mm_ready        = deque(maxlen=2)
q_a183mm_save_to_file = deque(maxlen=100)
q_a533mc_platesolve   = deque(maxlen=1)
q_a533mc_raw          = deque(maxlen=2)
q_a533mc_ready        = deque(maxlen=2)
q_a533mc_save_to_file = deque(maxlen=100)
q_a462mc_platesolve   = deque(maxlen=1)
q_a462mc_raw          = deque(maxlen=2)
q_a462mc_ready        = deque(maxlen=2)
q_a462mc_save_to_file = deque(maxlen=100)
q_canon_platesolve = deque(maxlen=1)
q_canon_raw        = deque(maxlen=2)
q_canon_ready      = deque(maxlen=1)

viewer_a120mm_deployed = False
viewer_a120mc_deployed = False
viewer_canon_deployed = False
viewer_a183mm_deployed = False
viewer_a533mc_deployed = False
viewer_a462mc_deployed = False
run_plate_solve_a120mm = False
run_plate_solve_a120mc = False
run_plate_solve_canon = False
run_plate_solve_a183mm = False
run_plate_solve_a533mc = False
run_plate_solve_a462mc = False
plate_solve_canon_status = 'NULL'
plate_solve_a120mm_status = 'NULL'
plate_solve_a120mc_status = 'NULL'
plate_solve_a183mm_status = 'NULL'
plate_solve_a533mc_status = 'NULL'
plate_solve_a462mc_status = 'NULL'
plate_solve_results = {}
canon_last_frame = False
canon_last_frame_time = 0.0

cam_settings = {
  'canon':{
    'disp_frame_time': 0,
    'rotate': 0,
    'last_rotate': 0,
  },
  'a462mc': {
  },
  'a183mm': {
  },
  'a533mc': {
  },
  'a120mc': {
  },
  'a120mm': {
  }
}


#############################################################################################


def f_requests_send():
  global req_cmd, kill_thread, connection_ok

  while kill_thread == False:
    if not req_cmd.empty():
      payload = req_cmd.get()
      while kill_thread == False:
        try:
          out = requests.post(sterownik_uri, data=json.dumps(payload), timeout=3)
          if out.status_code == 200:
            connection_ok = True
            break
          else:
            connection_ok = False
            time.sleep(0.1)
        except Exception as e:
          connection_ok = False
          time.sleep(0.5)
          print(traceback.format_exc())
          pass

    if req_cmd.empty():
      time.sleep(0.1)

def f_requests_canon_send():
  global req_canon, kill_thread

  while kill_thread == False:
    if not req_canon.empty():
      url = req_canon.get()
      while kill_thread == False:
        try:
          out = requests.get(url, timeout=3)
          if out.status_code == 200:
            break
          else:
            time.sleep(0.5)
        except Exception as e:
          print(traceback.format_exc())
          time.sleep(0.5)
          pass

    if req_canon.empty():
      time.sleep(0.5)

def f_run_periodic_functions():
  global kill_thread, screen

  while kill_thread == False:
    try:
      screen.print_telescope_position()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a533mc_cam_update_values(load_slider=False)
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a183mm_cam_update_values(load_slider=False)
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a462mc_cam_update_values(load_slider=False)
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a120mc_cam_update_values(load_slider=False)
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a120mm_cam_update_values(load_slider=False)
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_canon_update_values(load_slider=False)
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_filter_reset(automatic = True)
    except Exception as e:
      print(traceback.format_exc())
      pass
    time.sleep(1)

def f_photo_refresh():
  global kill_thread, screen, q_a120mm_raw, q_a120mc_raw, q_a462mc_raw, viewer_a120mm_deployed, viewer_a462mc_deployed, viewer_a120mc_deployed, q_a183mm_raw, viewer_a183mm_deployed, q_a533mc_raw, viewer_a533mc_deployed

  while kill_thread == False:
    try:
      if viewer_canon_deployed and screen.t_prawy.currentIndex() == 5:
        screen.f_canon_window_refresh_event()
      if viewer_a120mc_deployed and screen.t_prawy.currentIndex() == 4:
        screen.f_a120mc_window_refresh_event()
      if viewer_a120mm_deployed and screen.t_prawy.currentIndex() == 3:
        screen.f_a120mm_window_refresh_event()
      if viewer_a462mc_deployed and screen.t_prawy.currentIndex() == 2:
        screen.f_a462mc_window_refresh_event()
      if viewer_a533mc_deployed and screen.t_prawy.currentIndex() == 1:
        screen.f_a533mc_window_refresh_event()
      if viewer_a183mm_deployed and screen.t_prawy.currentIndex() == 0:
        screen.f_a183mm_window_refresh_event()
    except Exception as e:
      print(traceback.format_exc())
      time.sleep(0.5)
      pass
    time.sleep(0.1)


#############################################################################################

def f_save_img_universal(queue):
  global kill_thread

  while not kill_thread:
    while not queue and not kill_thread:
      time.sleep(0.1)
    if kill_thread:
      break

    frame = queue.pop()

    imgdir = os.path.expanduser('~') + '/' + 'zzz_' + str(frame['camname']) + '_autosave_' + frame['dirname']
    if os.path.exists(imgdir) and not os.path.isdir(imgdir):
      print("ERR: " + imgdir + " exists and is not a dir. Can't save there")
      continue

    if not os.path.exists(imgdir):
      os.mkdir(imgdir)

    filename = imgdir +\
    '/raw_' + str(frame['time']) +\
    '.exp_' + str(frame['exposure']) +\
    '.off_' + str(frame['offset']) +\
    '.gain_' + str(frame['gain']) +\
    '.bin_' + str(frame['bin']) +\
    '.t_' + str(int(frame['temperature']*10)) +\
    '.color_' + str(frame['iscolor']) +\
    '.png'

    if frame['iscolor']:
      cv2.imwrite(filename, frame['frame16'])
    else:
      cv2.imwrite(filename, frame['frame16'][:, :, 1])

def f_save_a183mm_img():
  global q_a183mm_save_to_file
  f_save_img_universal(queue=q_a183mm_save_to_file)

def f_save_a533mc_img():
  global q_a533mc_save_to_file
  f_save_img_universal(queue=q_a533mc_save_to_file)

def f_save_a462mc_img():
  global q_a462mc_save_to_file
  f_save_img_universal(queue=q_a462mc_save_to_file)

def f_save_a120mm_img():
  global q_a120mm_save_to_file
  f_save_img_universal(queue=q_a120mm_save_to_file)

def f_save_a120mc_img():
  global q_a120mc_save_to_file
  f_save_img_universal(queue=q_a120mc_save_to_file)


#############################################################################################
def f_universal_plate_solve_run(q_platesolve, camname, lab_plate_solve_status, radius, cam_scale_pixel_scale, grid):
  global t_telescope, plate_solve_results, kill_thread, screen, req_cmd

  lab_plate_solve_status.setText('Plate solve status: WAITING FOR FRAME...')
  while not q_platesolve and not kill_thread:
    time.sleep(0.1)

  frame = q_platesolve.pop()
  out = subprocess.check_output(['rm', '-rf', '/dev/shm/' + camname + '_platesolve'])
  out = subprocess.check_output(['mkdir', '-p', '/dev/shm/' + camname + '_platesolve'])
  cv2.imwrite('/dev/shm/' + camname + '_platesolve/frame.png', frame['gray'])

  platesolve_cmd_1 = [
    'solve-field',
    '--scale-units',
    'arcsecperpix',
    '--scale-low',
    str(cam_scale_pixel_scale.value()*0.8),
    '--scale-high',
    str(cam_scale_pixel_scale.value()*1.2),
    '--no-plots',
    '--downsample',
    '2',
  ]
  platesolve_cmd_2 = [
    '--ra',
    Angle(t_telescope['ra']).to_string(sep=':', precision=0),
    '--dec',
    Angle(t_telescope['dec']).to_string(sep=':', precision=0),
    '--radius',
    '2',
  ]
  platesolve_cmd_3 = [
    '--temp-dir',
    '/dev/shm/' + camname + '_platesolve',
    '/dev/shm/' + camname + '_platesolve/frame.png'
  ]

  if radius:
    platesolve_cmd = platesolve_cmd_1 + platesolve_cmd_2 + platesolve_cmd_3
  else:
    platesolve_cmd = platesolve_cmd_1 + platesolve_cmd_3

  try:
    lab_plate_solve_status.setText('Plate solve status: SOLVING...')
    out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
    out = subprocess.check_output(['wcsinfo', '/dev/shm/' + camname + '_platesolve/frame.wcs'])
    opts = {}
    for i in out.decode().split('\n'):
      if i != '':
        key, val = i.split(' ')
        opts[key] = val

    if opts['dec_center_sign'] == '-1':
      signum = '-'
    else:
      signum = ''

    _ra = opts['ra_center_h'] + 'h' + opts['ra_center_m'] + 'm' + opts['ra_center_s'] + 's'
    _dec = signum + opts['dec_center_d'] + 'd' + opts['dec_center_m'] + 'm' + opts['dec_center_s'] + 's'
    payload = {
      'mode': 'radec',
      'ra': _ra,
      'dec': _dec,
      'move': False,
      'update_pos': True
    }
    req_cmd.put(payload)

    imagew = int(opts['imagew']) - 1
    imageh = int(opts['imageh']) - 1
    wcsfile = fits.open('/dev/shm/' + camname + '_platesolve/frame.wcs')
    w = wcs.WCS(wcsfile[0].header)
    corners = np.array([[0, 0], [imagew,0], [imagew,imageh], [0, imageh], [0, 0]], dtype=np.float32)
    world = w.wcs_pix2world(corners, 0)
    poly = ','.join(map(str, world.flatten()))

    map_url_tab = [
      'http://legacysurvey.org/viewer/?ra=',
      opts['ra_center'],
      '&dec=',
      opts['dec_center'],
      '&layer=unwise-neo6&poly=',
      poly,
    ]
    plate_solve_results['url'] = ''.join(map_url_tab)

    plotann_arr = [
      'plotann.py',
      '/dev/shm/' + camname + '_platesolve/frame.wcs',
      '/dev/shm/' + camname + '_platesolve/frame.png',
      '/dev/shm/' + camname + '_platesolve/frame_hdcat.png',
      '--hdcat=/home/dom/GIT/puppet/astro/astro_gui/hd.fits',
      '--grid-size=' + str(grid),
      '--grid-label=' + str(grid),
    ]
    out = subprocess.check_output(plotann_arr)
    plate_solve_results['hdcat'] = cv2.imread('/dev/shm/' + camname + '_platesolve/frame_hdcat.png')

    plotann_arr = [
      'plotann.py',
      '/dev/shm/' + camname + '_platesolve/frame.wcs',
      '/dev/shm/' + camname + '_platesolve/frame.png',
      '/dev/shm/' + camname + '_platesolve/frame_tycho2cat.png',
      '--tycho2cat=/home/dom/GIT/puppet/astro/astro_gui/tycho2.kd',
      '--grid-size=' + str(grid),
      '--grid-label=' + str(grid),
    ]
    out = subprocess.check_output(plotann_arr)
    plate_solve_results['tycho2cat'] = cv2.imread('/dev/shm/' + camname + '_platesolve/frame_tycho2cat.png')
    lab_plate_solve_status.setText('Plate solve status: DONE at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    screen.f_solved_tabs_refresh_event()
  except:
    lab_plate_solve_status.setText('Plate solve status: FAILED at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    pass
#############################################################################################

def f_a183mm_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a183mm

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a183mm:
      run_plate_solve_a183mm = False
      f_universal_plate_solve_run(
        camname = 'a183mm',
        radius = True,
        q_platesolve = q_a183mm_platesolve,
        lab_plate_solve_status = screen.lab_a183mm_plate_solve_status,
        cam_scale_pixel_scale = screen.a183mm_cam_scale_pixel_scale,
        grid = '0.02',
      )

def f_a533mc_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a533mc

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a533mc:
      run_plate_solve_a533mc = False
      f_universal_plate_solve_run(
        camname = 'a533mc',
        radius = True,
        q_platesolve = q_a533mc_platesolve,
        lab_plate_solve_status = screen.lab_a533mc_plate_solve_status,
        cam_scale_pixel_scale = screen.a533mc_cam_scale_pixel_scale,
        grid = '0.02',
      )

def f_a462mc_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a462mc

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a462mc:
      run_plate_solve_a462mc = False
      f_universal_plate_solve_run(
        camname = 'a462mc',
        radius = True,
        q_platesolve = q_a462mc_platesolve,
        lab_plate_solve_status = screen.lab_a462mc_plate_solve_status,
        cam_scale_pixel_scale = screen.a462mc_cam_scale_pixel_scale,
        grid = '0.02',
      )

def f_a120mc_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a120mc

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a120mc:
      run_plate_solve_a120mc = False
      f_universal_plate_solve_run(
        camname = 'a120mc',
        radius = False,
        q_platesolve = q_a120mc_platesolve,
        lab_plate_solve_status = screen.lab_a120mc_plate_solve_status,
        cam_scale_pixel_scale = screen.a120mc_cam_scale_pixel_scale,
        grid = '0.1',
      )

def f_a120mm_plate_solve_loop():

  global screen, kill_thread, run_plate_solve_a120mm

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a120mm:
      run_plate_solve_a120mm = False
      f_universal_plate_solve_run(
        camname = 'a120mm',
        radius = False,
        q_platesolve = q_a120mm_platesolve,
        lab_plate_solve_status = screen.lab_a120mm_plate_solve_status,
        cam_scale_pixel_scale = screen.a120mm_cam_scale_pixel_scale,
        grid = '0.1',
      )

def f_canon_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_canon

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_canon:
      run_plate_solve_canon = False
      f_universal_plate_solve_run(
        camname = 'canon',
        radius = True,
        q_platesolve = q_canon_platesolve,
        lab_plate_solve_status = screen.lab_canon_plate_solve_status,
        cam_scale_pixel_scale = screen.canon_scale_pixel_scale,
      )

#############################################################################################

def f_camera_params(cam_name, method):
  global cam_settings, screen, kill_thread

  if method == 'initial':
    if cam_name == 'a183mm':
      uri = 'http://127.0.0.2:8003/settings'
    elif cam_name == 'a533mc':
      uri = 'http://127.0.0.2:8004/settings'
    elif cam_name == 'a462mc':
      uri = 'http://127.0.0.2:8000/settings'
    elif cam_name == 'a120mm':
      uri = 'http://127.0.0.2:8001/settings'
    else:
      uri = 'http://127.0.0.2:8002/settings'

    while kill_thread == False:
      try:
        out = requests.get(uri, timeout=3)
        if out.status_code == 200:
          response = json.loads(out.text)
          break
        else:
          time.sleep(0.1)
          continue
      except:
        time.sleep(0.1)
        pass
    if kill_thread:
      return
    del cam_settings[cam_name]
    cam_settings[cam_name] = response

    if cam_name == 'a183mm':
      screen.f_a183mm_cam_update_values(load_slider=True)
    elif cam_name == 'a533mc':
      screen.f_a533mc_cam_update_values(load_slider=True)
    elif cam_name == 'a462mc':
      screen.f_a462mc_cam_update_values(load_slider=True)
    elif cam_name == 'a120mm':
      screen.f_a120mm_cam_update_values(load_slider=True)
    elif cam_name == 'a120mc':
      screen.f_a120mc_cam_update_values(load_slider=True)

  elif method == 'send_params_to_cam':
    if cam_name == 'a183mm':
      uri = 'http://127.0.0.2:8003/set_settings'
    elif cam_name == 'a533mc':
      uri = 'http://127.0.0.2:8004/set_settings'
    elif cam_name == 'a462mc':
      uri = 'http://127.0.0.2:8000/set_settings'
    elif cam_name == 'a120mm':
      uri = 'http://127.0.0.2:8001/set_settings'
    else:
      uri = 'http://127.0.0.2:8002/set_settings'

    payload = cam_settings[cam_name]

    while kill_thread == False:
      try:
        out = requests.post(uri, data=json.dumps(payload), timeout=3)
        if out.status_code == 200:
          break
        else:
          time.sleep(0.1)
      except:
        time.sleep(0.1)
        pass
    if kill_thread:
      return

  elif method == 'refresh_deployed':
    if cam_name == 'a183mm':
      uri = 'http://127.0.0.2:8003/settings'
    elif cam_name == 'a533mc':
      uri = 'http://127.0.0.2:8004/settings'
    elif cam_name == 'a462mc':
      uri = 'http://127.0.0.2:8000/settings'
    elif cam_name == 'a120mm':
      uri = 'http://127.0.0.2:8001/settings'
    else:
      uri = 'http://127.0.0.2:8002/settings'

    while kill_thread == False:
      try:
        out = requests.get(uri, timeout=3)
        if out.status_code == 200:
          response = json.loads(out.text)
          break
        else:
          time.sleep(0.1)
          continue
      except:
        time.sleep(0.1)
        pass
    if kill_thread:
      return
    depl_err_local = 0

    param_tab = []
    for i in cam_settings[cam_name].keys():
      if isinstance(cam_settings[cam_name][i], dict) and 'depl' in cam_settings[cam_name][i]:
        param_tab.append(i)

    for i in param_tab:
      cam_settings[cam_name][i]['depl'] = response[i]['depl']
      if cam_settings[cam_name][i]['depl'] != cam_settings[cam_name][i]['Value']:
        depl_err_local = depl_err_local + 1

    if cam_name == 'a183mm':
      if 'temperature' in cam_settings['a183mm']['info']:
        cam_settings['a183mm']['info']['temperature'] = response['info']['temperature']
      if 'cooler_pwr' in cam_settings['a183mm']['info']:
        cam_settings['a183mm']['info']['cooler_pwr'] = response['info']['cooler_pwr']

    if cam_name == 'a533mc':
      if 'temperature' in cam_settings['a533mc']['info']:
        cam_settings['a533mc']['info']['temperature'] = response['info']['temperature']
      if 'cooler_pwr' in cam_settings['a533mc']['info']:
        cam_settings['a533mc']['info']['cooler_pwr'] = response['info']['cooler_pwr']

    if 'depl_error' in cam_settings[cam_name] and depl_err_local > 0:
      cam_settings[cam_name]['depl_error'] = cam_settings[cam_name]['depl_error'] + 1
    else:
      cam_settings[cam_name]['depl_error'] = 0
    if cam_settings[cam_name]['depl_error'] > 3:
      print('resend params to cam')
      f_camera_params(cam_name=cam_name, method='send_params_to_cam')


#############################################################################################

def f_a183mm_settings():
  global cam_a183mm, cam_settings, kill_thread

  while kill_thread == False:
    try:
      out = requests.get('http://127.0.0.2:8003/settings', timeout=1)
      if out.status_code == 200:
        break
      else:
        time.sleep(1)
    except:
      time.sleep(1)
      pass

  f_camera_params(cam_name = 'a183mm', method = 'initial')
  if 'param_time' in cam_settings['a183mm']:
    last_settings_time = cam_settings['a183mm']['param_time']
  else:
    last_settings_time = 'NULL'

  while kill_thread == False:
    f_camera_params(cam_name = 'a183mm', method = 'refresh_deployed')
    if 'param_time' in cam_settings['a183mm']:
      if last_settings_time != cam_settings['a183mm']['param_time']:
        f_camera_params(cam_name = 'a183mm', method = 'send_params_to_cam')
        last_settings_time = cam_settings['a183mm']['param_time']
    time.sleep(1)

def f_a533mc_settings():
  global cam_a533mc, cam_settings, kill_thread

  while kill_thread == False:
    try:
      out = requests.get('http://127.0.0.2:8004/settings', timeout=1)
      if out.status_code == 200:
        break
      else:
        time.sleep(1)
    except:
      time.sleep(1)
      pass

  f_camera_params(cam_name = 'a533mc', method = 'initial')
  if 'param_time' in cam_settings['a533mc']:
    last_settings_time = cam_settings['a533mc']['param_time']
  else:
    last_settings_time = 'NULL'

  while kill_thread == False:
    f_camera_params(cam_name = 'a533mc', method = 'refresh_deployed')
    if 'param_time' in cam_settings['a533mc']:
      if last_settings_time != cam_settings['a533mc']['param_time']:
        f_camera_params(cam_name = 'a533mc', method = 'send_params_to_cam')
        last_settings_time = cam_settings['a533mc']['param_time']
    time.sleep(1)

def f_a183mm_preview():
  global cam_a183mm, q_a183mm_raw, cam_settings, kill_thread

  last_frame_time = 0
  while kill_thread == False:
    time.sleep(0.01)
    if 'info' in cam_settings['a183mm']:
        try:
          if os.path.isfile(cam_settings['a183mm']['info']['data_path']) and os.path.isfile(cam_settings['a183mm']['info']['time_path']):
            f = open(cam_settings['a183mm']['info']['time_path'], 'r')
            _time = float(f.read())
            f.close()
            if _time == last_frame_time:
              continue
            frame = {
              'time': _time,
              'raw_data': np.load(cam_settings['a183mm']['info']['data_path']),
            }
            q_a183mm_raw.append(frame)
            cam_settings['a183mm']['frame_time'] = _time
            last_frame_time = _time
        except Exception as e:
          #print(traceback.format_exc())
          time.sleep(0.01)
          pass

def f_a533mc_preview():
  global cam_a533mc, q_a533mc_raw, cam_settings, kill_thread

  last_frame_time = 0
  while kill_thread == False:
    time.sleep(0.01)
    if 'info' in cam_settings['a533mc']:
        try:
          if os.path.isfile(cam_settings['a533mc']['info']['data_path']) and os.path.isfile(cam_settings['a533mc']['info']['time_path']):
            f = open(cam_settings['a533mc']['info']['time_path'], 'r')
            _time = float(f.read())
            f.close()
            if _time == last_frame_time:
              continue
            frame = {
              'time': _time,
              'raw_data': np.load(cam_settings['a533mc']['info']['data_path']),
            }
            q_a533mc_raw.append(frame)
            cam_settings['a533mc']['frame_time'] = _time
            last_frame_time = _time
        except Exception as e:
          #print(traceback.format_exc())
          time.sleep(0.01)
          pass


def f_a462mc_settings():
  global cam_a462mc, cam_settings, kill_thread

  while kill_thread == False:
    try:
      out = requests.get('http://127.0.0.2:8000/settings', timeout=1)
      if out.status_code == 200:
        break
      else:
        time.sleep(1)
    except:
      time.sleep(1)
      pass

  f_camera_params(cam_name = 'a462mc', method = 'initial')
  if 'param_time' in cam_settings['a462mc']:
    last_settings_time = cam_settings['a462mc']['param_time']
  else:
    last_settings_time = 'NULL'

  while kill_thread == False:
    f_camera_params(cam_name = 'a462mc', method = 'refresh_deployed')
    if 'param_time' in cam_settings['a462mc']:
      if last_settings_time != cam_settings['a462mc']['param_time']:
        f_camera_params(cam_name = 'a462mc', method = 'send_params_to_cam')
        last_settings_time = cam_settings['a462mc']['param_time']
    time.sleep(1)

def f_a462mc_preview():
  global cam_a462mc, q_a462mc_raw, cam_settings, kill_thread

  last_frame_time = 0
  while kill_thread == False:
    time.sleep(0.01)
    if 'info' in cam_settings['a462mc']:
        try:
          if os.path.isfile(cam_settings['a462mc']['info']['data_path']) and os.path.isfile(cam_settings['a462mc']['info']['time_path']):
            f = open(cam_settings['a462mc']['info']['time_path'], 'r')
            _time = float(f.read())
            f.close()
            if _time == last_frame_time:
              continue
            frame = {
              'time': _time,
              'raw_data': np.load(cam_settings['a462mc']['info']['data_path']),
            }
            q_a462mc_raw.append(frame)
            cam_settings['a462mc']['frame_time'] = _time
            last_frame_time = _time
        except Exception as e:
          #print(traceback.format_exc())
          time.sleep(0.01)
          pass




def f_a120mc_settings():
  global cam_a120mc, cam_settings, kill_thread

  while kill_thread == False:
    try:
      out = requests.get('http://127.0.0.2:8002/settings', timeout=1)
      if out.status_code == 200:
        break
      else:
        time.sleep(1)
    except:
      time.sleep(1)
      pass

  f_camera_params(cam_name = 'a120mc', method = 'initial')
  if 'param_time' in cam_settings['a120mc']:
    last_settings_time = cam_settings['a120mc']['param_time']
  else:
    last_settings_time = 'NULL'

  while kill_thread == False:
    f_camera_params(cam_name = 'a120mc', method = 'refresh_deployed')
    if 'param_time' in cam_settings['a120mc']:
      if last_settings_time != cam_settings['a120mc']['param_time']:
        f_camera_params(cam_name = 'a120mc', method = 'send_params_to_cam')
        last_settings_time = cam_settings['a120mc']['param_time']
    time.sleep(1)

def f_a120mc_preview():
  global cam_a120mc, q_a120mc_raw, cam_settings, kill_thread

  last_frame_time = 0
  while kill_thread == False:
    time.sleep(0.01)
    if 'info' in cam_settings['a120mc']:
        try:
          if os.path.isfile(cam_settings['a120mc']['info']['data_path']) and os.path.isfile(cam_settings['a120mc']['info']['time_path']):
            f = open(cam_settings['a120mc']['info']['time_path'], 'r')
            _time = float(f.read())
            f.close()
            if _time == last_frame_time:
              continue
            frame = {
              'time': _time,
              'raw_data': np.load(cam_settings['a120mc']['info']['data_path']),
            }
            q_a120mc_raw.append(frame)
            cam_settings['a120mc']['frame_time'] = _time
            last_frame_time = _time
        except Exception as e:
          #print(traceback.format_exc())
          time.sleep(0.01)
          pass



def f_a120mm_settings():
  global cam_a120mm, cam_settings, kill_thread

  while kill_thread == False:
    try:
      out = requests.get('http://127.0.0.2:8001/settings', timeout=1)
      if out.status_code == 200:
        break
      else:
        time.sleep(1)
    except:
      time.sleep(1)
      pass

  f_camera_params(cam_name = 'a120mm', method = 'initial')
  if 'param_time' in cam_settings['a120mm']:
    last_settings_time = cam_settings['a120mm']['param_time']
  else:
    last_settings_time = 'NULL'

  while kill_thread == False:
    f_camera_params(cam_name = 'a120mm', method = 'refresh_deployed')
    if 'param_time' in cam_settings['a120mm']:
      if last_settings_time != cam_settings['a120mm']['param_time']:
        f_camera_params(cam_name = 'a120mm', method = 'send_params_to_cam')
        last_settings_time = cam_settings['a120mm']['param_time']
    time.sleep(1)

def f_a120mm_preview():
  global cam_a120mm, q_a120mm_raw, cam_settings, kill_thread

  last_frame_time = 0
  while kill_thread == False:
    time.sleep(0.01)
    if 'info' in cam_settings['a120mm']:
        try:
          if os.path.isfile(cam_settings['a120mm']['info']['data_path']) and os.path.isfile(cam_settings['a120mm']['info']['time_path']):
            f = open(cam_settings['a120mm']['info']['time_path'], 'r')
            _time = float(f.read())
            f.close()
            if _time == last_frame_time:
              continue
            frame = {
              'time': _time,
              'raw_data': np.load(cam_settings['a120mm']['info']['data_path']),
            }
            q_a120mm_raw.append(frame)
            cam_settings['a120mm']['frame_time'] = _time
            last_frame_time = _time
        except Exception as e:
          #print(traceback.format_exc())
          time.sleep(0.01)
          pass



def f_canon_preview():
  global cam_canon, q_canon_raw, cam_settings, kill_thread

  last_frametime = 0
  while kill_thread == False:
    time.sleep(0.1)
    try:
      if os.path.isfile('/dev/shm/canon/time'):
        f = open('/dev/shm/canon/time', 'r')
        frametime = int(f.read())
        f.close()
        if last_frametime != frametime:
          frame = {
            'time': frametime,
            'raw_data': tiff.imread('/dev/shm/canon/frame.tiff'),
          }
          q_canon_raw.append(frame)
          last_frametime = frametime
    except Exception as e:
      print(traceback.format_exc())
      time.sleep(0.1)


#############################################################################################


def f_frame_processing_universal(q_raw, q_ready, q_platesolve, q_save_to_file, camname, cam_save_dirname, cam_exp_slider, cam_offset_slider, cam_gain_slider, cam_bin, cam_save_img, color_scheme):
  global cam_settings

  while kill_thread == False:
    while kill_thread == False and not q_raw:
      time.sleep(0.1)
    if kill_thread:
      break
    raw_frame = q_raw.pop()
    ready_frame = {
      'time': raw_frame['time']
    }
    ready_frame['frame16'] = cv2.cvtColor(raw_frame['raw_data'], color_scheme)
    ready_frame['frameRGB'] = (ready_frame['frame16']/256).astype('uint8')
    ready_frame['gray'] = cv2.cvtColor(ready_frame['frameRGB'], cv2.COLOR_RGB2GRAY)
    c = np.percentile(ready_frame['frame16'],[0,1,50,99,99.99])
    ready_frame['percentile_stat'] = "0: " + str(round(c[0])) + ",   1: " + str(round(c[1])) + ",   50: " + str(round(c[2])) + ",   99: " + str(round(c[3])) + ",   99.99: " + str(round(c[4]))

    if cam_save_img.isChecked():
      ready_frame['dirname'] = str(cam_save_dirname.text())
      ready_frame['exposure'] = int(cam_exp_slider.value())
      ready_frame['offset'] = int(cam_offset_slider.value())
      ready_frame['gain'] = int(cam_gain_slider.value())
      ready_frame['bin'] = int(cam_bin.currentText())
      ready_frame['camname'] = camname
      if camname in cam_settings.keys() and 'info' in cam_settings[camname].keys() and 'temperature' in cam_settings[camname]['info'].keys():
        ready_frame['temperature'] = cam_settings[camname]['info']['temperature']
        ready_frame['iscolor'] = cam_settings[camname]['info']['IsColorCam']
      else:
        ready_frame['temperature'] = 'nan'
      q_save_to_file.append(ready_frame)

    q_ready.append(ready_frame)
    q_platesolve.append(ready_frame)

def f_a183mm_frame_processing():
  global q_a183mm_raw, q_a183mm_ready, q_a183mm_platesolve, q_a183mm_save_to_file
  global screen, cam_settings

  f_frame_processing_universal(
    camname = 'a183mm',
    q_raw = q_a183mm_raw,
    q_ready = q_a183mm_ready,
    q_platesolve = q_a183mm_platesolve,
    q_save_to_file = q_a183mm_save_to_file,
    cam_save_dirname = screen.a183mm_cam_save_dirname,
    cam_exp_slider = screen.a183mm_cam_exp_slider,
    cam_offset_slider = screen.a183mm_cam_offset_slider,
    cam_gain_slider = screen.a183mm_cam_gain_slider,
    cam_bin = screen.a183mm_cam_bin,
    cam_save_img = screen.a183mm_cam_save_img,
    color_scheme = cv2.COLOR_GRAY2RGB,
  )

def f_a533mc_frame_processing():
  global q_a533mc_raw, q_a533mc_ready, q_a533mc_platesolve, q_a533mc_save_to_file
  global screen, cam_settings

  f_frame_processing_universal(
    camname = 'a533mc',
    q_raw = q_a533mc_raw,
    q_ready = q_a533mc_ready,
    q_platesolve = q_a533mc_platesolve,
    q_save_to_file = q_a533mc_save_to_file,
    cam_save_dirname = screen.a533mc_cam_save_dirname,
    cam_exp_slider = screen.a533mc_cam_exp_slider,
    cam_offset_slider = screen.a533mc_cam_offset_slider,
    cam_gain_slider = screen.a533mc_cam_gain_slider,
    cam_bin = screen.a533mc_cam_bin,
    cam_save_img = screen.a533mc_cam_save_img,
    color_scheme = cv2.COLOR_BAYER_RG2RGB,
  )

def f_a462mc_frame_processing():
  global q_a462mc_raw, q_a462mc_ready, q_a462mc_platesolve, q_a462mc_save_to_file
  global screen, cam_settings

  f_frame_processing_universal(
    camname = 'a462mc',
    q_raw = q_a462mc_raw,
    q_ready = q_a462mc_ready,
    q_platesolve = q_a462mc_platesolve,
    q_save_to_file = q_a462mc_save_to_file,
    cam_save_dirname = screen.a462mc_cam_save_dirname,
    cam_exp_slider = screen.a462mc_cam_exp_slider,
    cam_offset_slider = screen.a462mc_cam_offset_slider,
    cam_gain_slider = screen.a462mc_cam_gain_slider,
    cam_bin = screen.a462mc_cam_bin,
    cam_save_img = screen.a462mc_cam_save_img,
    color_scheme = cv2.COLOR_BAYER_RG2RGB,
  )

def f_a120mc_frame_processing():
  global q_a120mc_raw, q_a120mc_ready, q_a120mc_platesolve, q_a120mc_save_to_file
  global screen, cam_settings

  f_frame_processing_universal(
    camname = 'a120mc',
    q_raw = q_a120mc_raw,
    q_ready = q_a120mc_ready,
    q_platesolve = q_a120mc_platesolve,
    q_save_to_file = q_a120mc_save_to_file,
    cam_save_dirname = screen.a120mc_cam_save_dirname,
    cam_exp_slider = screen.a120mc_cam_exp_slider,
    cam_offset_slider = screen.a120mc_cam_offset_slider,
    cam_gain_slider = screen.a120mc_cam_gain_slider,
    cam_bin = screen.a120mc_cam_bin,
    cam_save_img = screen.a120mc_cam_save_img,
    color_scheme = cv2.COLOR_BAYER_GR2RGB,
  )

def f_a120mm_frame_processing():
  global q_a120mm_raw, q_a120mm_ready, q_a120mm_platesolve, q_a120mm_save_to_file
  global screen, cam_settings

  f_frame_processing_universal(
    camname = 'a120mm',
    q_raw = q_a120mm_raw,
    q_ready = q_a120mm_ready,
    q_platesolve = q_a120mm_platesolve,
    q_save_to_file = q_a120mm_save_to_file,
    cam_save_dirname = screen.a120mm_cam_save_dirname,
    cam_exp_slider = screen.a120mm_cam_exp_slider,
    cam_offset_slider = screen.a120mm_cam_offset_slider,
    cam_gain_slider = screen.a120mm_cam_gain_slider,
    cam_bin = screen.a120mm_cam_bin,
    cam_save_img = screen.a120mm_cam_save_img,
    color_scheme = cv2.COLOR_GRAY2RGB,
  )

def f_canon_frame_processing():
  global q_canon_raw, q_canon_ready, q_canon_platesolve
  global screen, cam_settings

  while kill_thread == False:
    while kill_thread == False and not q_canon_raw:
      time.sleep(0.1)
    if kill_thread:
      break
    raw_frame = q_canon_raw.pop()
    ready_frame = {
      'time': raw_frame['time']
    }
    ready_frame['frame16'] = raw_frame['raw_data'].copy()
    ready_frame['frameRGB'] = (ready_frame['frame16']/256).astype('uint8')
    ready_frame['gray'] = cv2.cvtColor(ready_frame['frameRGB'], cv2.COLOR_RGB2GRAY)

    q_canon_ready.append(ready_frame)
    q_canon_platesolve.append(ready_frame)



#############################################################################################


class PhotoViewer(QtWidgets.QGraphicsView):
    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._empty = True
        self.zoom = 0
        self.one_time_done = False
        self._scene = QtWidgets.QGraphicsScene(self)
        self._photo = QtWidgets.QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def hasPhoto(self):
        return not self._empty

    def fitInView(self, scale=True):
        rect = QtCore.QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self.zoom = 0

    def setPhoto(self, pixmap=None):
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
            self._photo.setPixmap(QtGui.QPixmap())
        if not self.one_time_done:
            self.one_time_done = True
            self.fitInView()

    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self.zoom += 1
            else:
                factor = 0.8
                self.zoom -= 1
            if self.zoom > 0:
                self.scale(factor, factor)
            elif self.zoom == 0:
                self.fitInView()
            else:
                self.zoom = 0

    def toggleDragMode(self):
        if self.dragMode() == QtWidgets.QGraphicsView.ScrollHandDrag:
            self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)


#############################################################################################


class Window(QWidget):
  global req_cmd

  def __init__(self):
    QWidget.__init__(self)

    layout = QHBoxLayout()

    self.t_lewy = QTabWidget()
    self.t_lewy.setTabPosition(QTabWidget.West)
    self.t_lewy.tabBarClicked.connect(self.f_changed_tab_left)
    self.lewy_tab1 = QWidget()
    self.lewy_tab2 = QWidget()
    self.lewy_tab3 = QWidget()
    self.lewy_tab4 = QWidget()
    self.lewy_tab5 = QWidget()
    self.lewy_tab6 = QWidget()
    self.lewy_tab7 = QWidget()
    self.lewy_tab8 = QWidget()
    self.lewy_tab9 = QWidget()
    self.t_lewy.addTab(self.lewy_tab1, "POSITION")
    self.t_lewy.addTab(self.lewy_tab2, "183MM")
    self.t_lewy.addTab(self.lewy_tab3, "533MC")
    self.t_lewy.addTab(self.lewy_tab4, "462MC")
    self.t_lewy.addTab(self.lewy_tab5, "120MM")
    self.t_lewy.addTab(self.lewy_tab6, "120MC")
    self.t_lewy.addTab(self.lewy_tab7, "CANON 20D")
    self.t_lewy.addTab(self.lewy_tab8, "MISC")
    self.t_lewy.addTab(self.lewy_tab9, "FILTERS")

    self.t_prawy = QWidget()
    self.t_prawy.setStyleSheet("background-color: green;")
    self.t_prawy = QTabWidget()
    self.t_prawy.setTabPosition(QTabWidget.East)
    self.prawy_tab1 = QWidget()
    self.prawy_tab2 = QWidget()
    self.prawy_tab3 = QWidget()
    self.prawy_tab4 = QWidget()
    self.prawy_tab5 = QWidget()
    self.prawy_tab6 = QWidget()
    self.prawy_tab7 = QWidget()
    self.prawy_tab8 = QWidget()
    self.prawy_tab9 = QWidget()
    self.t_prawy.addTab(self.prawy_tab1, "183MM cam")
    self.t_prawy.addTab(self.prawy_tab2, "533MC cam")
    self.t_prawy.addTab(self.prawy_tab3, "462MC cam")
    self.t_prawy.addTab(self.prawy_tab4, "120MM cam")
    self.t_prawy.addTab(self.prawy_tab5, "120MC cam")
    self.t_prawy.addTab(self.prawy_tab6, "CANON 20D")
    self.t_prawy.addTab(self.prawy_tab7, "TYCHO2 solved")
    self.t_prawy.addTab(self.prawy_tab8, "HD solved")
    self.t_prawy.addTab(self.prawy_tab9, "SKY MAP")

    layout.addWidget(self.t_lewy, stretch=1)
    layout.addWidget(self.t_prawy, stretch=4)
    self.setLayout(layout)


    self.hist_pen_r = pg.mkPen(color=(255,0,0), width=2)
    self.hist_pen_g = pg.mkPen(color=(0,191,41), width=2)
    self.hist_pen_b = pg.mkPen(color=(0,0,255), width=2)
    self.hist_pen_gray = pg.mkPen(color=(0,0,0), width=2)

    self.tab1_lewyUI()
    self.tab2_lewyUI()
    self.tab3_lewyUI()
    self.tab4_lewyUI()
    self.tab5_lewyUI()
    self.tab6_lewyUI()
    self.tab7_lewyUI()
    self.tab8_lewyUI()
    self.tab9_lewyUI()
    self.tab_1_prawyUI()
    self.tab_2_prawyUI()
    self.tab_3_prawyUI()
    self.tab_4_prawyUI()
    self.tab_5_prawyUI()
    self.tab_6_prawyUI()
    self.tab_7_prawyUI()
    self.tab_8_prawyUI()
    self.tab_9_prawyUI()

#############################################################################################

  def tab1_lewyUI(self):

    self.headline = QFont('SansSerif', 11, QFont.Bold)


    self.ost_lat = QLabel("FOCUS")
    self.ost_lat.setFont(self.headline)
    self.ost_lat.setAlignment(Qt.AlignCenter)

    self.ost_slider = QSlider(Qt.Horizontal)
    self.ost_slider.setTickPosition(QSlider.TicksBothSides)
    self.ost_slider.setMinimum(-100)
    self.ost_slider.setMaximum(100)
    self.ost_slider.setTickInterval(20)
    self.ost_slider.setSliderPosition(0)
    self.ost_slider.sliderReleased.connect(self.slider_center)
    self.ost_slider.valueChanged.connect(self.f_ost_slider)
    self.ost_slider.setMinimumWidth(350)
    self.ost_slider.setMaximumWidth(350)


    self.ost_joystick_left_button = QToolButton()
    self.ost_joystick_left_button.setArrowType(QtCore.Qt.LeftArrow)
    self.ost_joystick_left_button.clicked.connect(self.ost_joystick_left)

    self.ost_joystick_right_button = QToolButton()
    self.ost_joystick_right_button.setArrowType(QtCore.Qt.RightArrow)
    self.ost_joystick_right_button.clicked.connect(self.ost_joystick_right)

    self.ost_joystick_arc = QSpinBox()
    self.ost_joystick_arc.setMinimum(1)
    self.ost_joystick_arc.setMaximum(300)
    self.ost_joystick_arc.setValue(1)


    self.act_pos_1 = QLabel("Position of telescope")
    self.act_pos_1.setFont(self.headline)

    self.radec_position1 = QLabel("00H 00m 00s")
    self.altaz_position1 = QLabel("00D 00m 00s")

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)
    separator6 = QFrame()
    separator6.setFrameShape(QFrame.HLine)
    separator7 = QFrame()
    separator7.setFrameShape(QFrame.HLine)
    separator8 = QFrame()
    separator8.setFrameShape(QFrame.HLine)


    layout = QVBoxLayout()

    sliders_layout = QHBoxLayout()
    sliders_layout2 = QVBoxLayout()
    sliders_layout2.addWidget(self.ost_lat)
    sliders_layout2.addWidget(self.ost_slider)
    sliders_layout2_1 = QHBoxLayout()
    sliders_layout2_1.addWidget(self.ost_joystick_left_button)
    sliders_layout2_1.addWidget(self.ost_joystick_arc)
    sliders_layout2_1.addWidget(self.ost_joystick_right_button)
    sliders_layout2.addLayout(sliders_layout2_1)
    sliders_layout.addLayout(sliders_layout2)
    layout.addLayout(sliders_layout)

    layout.addWidget(separator1)

    layout.addWidget(self.act_pos_1, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.radec_position1)
    layout.addWidget(self.altaz_position1)

    layout.addStretch()

    self.lewy_tab1.setLayout(layout)

#############################################################################################

  def tab2_lewyUI(self):
    global cam_settings
    layout = QVBoxLayout()

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)
    separator6 = QFrame()
    separator6.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.lab_a183mm_cam = QLabel("ASI183MM PRO CAM")
    self.lab_a183mm_cam.setFont(self.headline)
    self.lab_a183mm_cam.setAlignment(Qt.AlignCenter)

    self.lab_a183mm_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a183mm_cam_time_frame = QLabel("Last frame time: -1s ago")
    self.lab_a183mm_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a183mm_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a183mm_rotate = QLabel("Rotate: null")
    self.lab_a183mm_cooling = QLabel("Cooler: NULL")

    self.a183mm_cam_exp_slider = QDoubleSpinBox()
    self.a183mm_cam_exp_slider.valueChanged.connect(self.f_a183mm_cam_params_changed)
    self.a183mm_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a183mm_cam_gain_slider = QSpinBox()
    self.a183mm_cam_gain_slider.valueChanged.connect(self.f_a183mm_cam_params_changed)

    self.a183mm_cam_offset_slider = QSpinBox()
    self.a183mm_cam_offset_slider.valueChanged.connect(self.f_a183mm_cam_params_changed)

    self.a183mm_cam_cooler = QCheckBox()
    self.a183mm_cam_cooler.setChecked(False)
    self.a183mm_cam_cooler.stateChanged.connect(self.f_a183mm_cam_params_changed)

    self.a183mm_cam_bin = QComboBox()
    self.a183mm_cam_bin.addItems(['NULL'])
    self.a183mm_cam_bin.currentIndexChanged.connect(self.f_a183mm_cam_params_changed)

    self.a183mm_cam_target_temp_slider = QSpinBox()
    self.a183mm_cam_target_temp_slider.valueChanged.connect(self.f_a183mm_cam_params_changed)

    self.a183mm_cam_reset_settings_button = QPushButton('RST settings', self)
    self.a183mm_cam_reset_settings_button.clicked.connect(self.f_a183mm_cam_reset_settings)
    self.a183mm_photo_reload = QPushButton('Reload', self)
    self.a183mm_photo_reload.clicked.connect(self.f_a183mm_window_refresh)

    self.a183mm_photo_rotate = QPushButton('Rot', self)
    self.a183mm_photo_rotate.clicked.connect(self.f_a183mm_rotate)

    self.a183mm_cam_save_img = QCheckBox()
    self.a183mm_cam_save_img.setChecked(False)

    self.a183mm_cam_save_dirname = QLineEdit(self)
    self.a183mm_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a183mm_cam_save_dirname.setValidator(validator1)
    self.a183mm_cam_save_dirname.setText('teleskop')

    self.a183mm_cam_circ_x = QSpinBox()
    self.a183mm_cam_circ_x.setMinimum(0)
    self.a183mm_cam_circ_x.setMaximum(5496)
    self.a183mm_cam_circ_x.setValue(int(5496/2))

    self.a183mm_cam_circ_y = QSpinBox()
    self.a183mm_cam_circ_y.setMinimum(0)
    self.a183mm_cam_circ_y.setMaximum(3672)
    self.a183mm_cam_circ_y.setValue(int(3672/2))

    self.a183mm_cam_circ_d = QSpinBox()
    self.a183mm_cam_circ_d.setMinimum(0)
    self.a183mm_cam_circ_d.setMaximum(1936)
    self.a183mm_cam_circ_d.setValue(0)

    self.a183mm_cam_circ_c = QSpinBox()
    self.a183mm_cam_circ_c.setMinimum(0)
    self.a183mm_cam_circ_c.setMaximum(2000)
    self.a183mm_cam_circ_c.setValue(0)

    self.a183mm_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.a183mm_b_plate_solve.clicked.connect(self.f_a183mm_plate_solve)

    self.a183mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a183mm_b_plate_solve_cancel.clicked.connect(self.f_a183mm_platesolve_stop)

    self.lab_a183mm_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a183mm_cam_scale_pixel_size = QDoubleSpinBox()
    self.a183mm_cam_scale_pixel_size.setMinimum(0.1)
    self.a183mm_cam_scale_pixel_size.setMaximum(99.0)
    self.a183mm_cam_scale_pixel_size.setValue(2.9)
    self.a183mm_cam_scale_pixel_size.valueChanged.connect(self.f_a183mm_cam_pix_scale_calc)

    self.a183mm_cam_scale_focal = QSpinBox()
    self.a183mm_cam_scale_focal.setMinimum(1)
    self.a183mm_cam_scale_focal.setMaximum(9999)
    self.a183mm_cam_scale_focal.setValue(2450)
    self.a183mm_cam_scale_focal.valueChanged.connect(self.f_a183mm_cam_pix_scale_calc)

    self.a183mm_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a183mm_cam_scale_pixel_scale.setMinimum(0.0)
    self.a183mm_cam_scale_pixel_scale.setMaximum(999.0)
    self.a183mm_cam_scale_pixel_scale.setValue(0.24)

    self.a183mm_cam_bri = QSpinBox()
    self.a183mm_cam_bri.setValue(0)
    self.a183mm_cam_bri.setMinimum(-255)
    self.a183mm_cam_bri.setMaximum(255)

    self.a183mm_cam_sat = QDoubleSpinBox()
    self.a183mm_cam_sat.setValue(1.0)
    self.a183mm_cam_sat.setMinimum(0.0)
    self.a183mm_cam_sat.setMaximum(10.0)
    self.a183mm_cam_sat.setSingleStep(0.01)

    self.a183mm_cam_gam = QDoubleSpinBox()
    self.a183mm_cam_gam.setValue(1.0)
    self.a183mm_cam_gam.setMinimum(0.0)
    self.a183mm_cam_gam.setMaximum(10.0)
    self.a183mm_cam_gam.setSingleStep(0.01)

    self.a183mm_cam_inverse = QCheckBox()
    self.a183mm_cam_inverse.setChecked(False)

    self.a183mm_cam_hist_equal = QCheckBox()
    self.a183mm_cam_hist_equal.setChecked(False)

    self.a183mm_cam_normalize = QCheckBox()
    self.a183mm_cam_normalize.setChecked(False)

    self.a183mm_cam_normalize_l = QDoubleSpinBox()
    self.a183mm_cam_normalize_l.setValue(0.0)
    self.a183mm_cam_normalize_l.setMinimum(0.0)
    self.a183mm_cam_normalize_l.setMaximum(100.0)
    self.a183mm_cam_normalize_l.setSingleStep(0.01)

    self.a183mm_cam_normalize_h = QDoubleSpinBox()
    self.a183mm_cam_normalize_h.setMinimum(0.0)
    self.a183mm_cam_normalize_h.setMaximum(100.0)
    self.a183mm_cam_normalize_h.setSingleStep(0.01)
    self.a183mm_cam_normalize_h.setValue(100.0)

    self.a183mm_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a183mm_cam_bri_sat_gam_rst.clicked.connect(self.f_a183mm_cam_bri_sat_gam_rst)

    self.lab_a183mm_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.graphWidget_a183mm = pg.PlotWidget()
    self.hist_color_a183mm = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_a183mm = pg.mkPen(color=(0,0,0))
    self.graphWidget_a183mm.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_a183mm)
    self.graphWidget_a183mm.setBackground(self.hist_color_a183mm)
    self.graphWidget_a183mm.hideAxis('bottom')
    self.graphWidget_a183mm.hideAxis('left')


    layout.addWidget(self.lab_a183mm_cam)
    layout.addWidget(self.lab_a183mm_cam_time_param)
    layout.addWidget(self.lab_a183mm_cam_time_frame)
    layout.addWidget(self.lab_a183mm_cam_time_disp_frame)
    layout.addWidget(self.lab_a183mm_rotate)
    layout.addWidget(self.lab_a183mm_cam_temp)
    layout.addWidget(self.lab_a183mm_cooling)
    layout.addWidget(separator1)
    layout.addWidget(self.a183mm_cam_exp_gain_depl)
    layout.addWidget(separator2)

    cam_a183mm_gain_layout = QHBoxLayout()
    cam_a183mm_gain_layout.addWidget(QLabel("Exp:"))
    cam_a183mm_gain_layout.addWidget(self.a183mm_cam_exp_slider)
    cam_a183mm_gain_layout.addWidget(QLabel("ms"))
    cam_a183mm_gain_layout.addWidget(QLabel("Gain:"))
    cam_a183mm_gain_layout.addWidget(self.a183mm_cam_gain_slider)
    cam_a183mm_gain_layout.addWidget(QLabel("Offset:"))
    cam_a183mm_gain_layout.addWidget(self.a183mm_cam_offset_slider)
    cam_a183mm_gain_layout.addStretch()
    layout.addLayout(cam_a183mm_gain_layout)

    cam_a183mm_temp_layout = QHBoxLayout()
    cam_a183mm_temp_layout.addWidget(QLabel("Cooler EN: "))
    cam_a183mm_temp_layout.addWidget(self.a183mm_cam_cooler)
    cam_a183mm_temp_layout.addWidget(QLabel("Temp: "))
    cam_a183mm_temp_layout.addWidget(self.a183mm_cam_target_temp_slider)
    cam_a183mm_temp_layout.addStretch()
    layout.addLayout(cam_a183mm_temp_layout)

    cam_a183mm_butt_group2 = QHBoxLayout()
    cam_a183mm_butt_group2.addWidget(self.a183mm_cam_reset_settings_button)
    cam_a183mm_butt_group2.addWidget(self.a183mm_photo_reload)
    cam_a183mm_butt_group2.addWidget(self.a183mm_photo_rotate)
    cam_a183mm_butt_group2.addWidget(QLabel("bin:"))
    cam_a183mm_butt_group2.addWidget(self.a183mm_cam_bin)
    cam_a183mm_butt_group2.addStretch()
    layout.addLayout(cam_a183mm_butt_group2)

    cam_a183mm_butt_group3 = QHBoxLayout()
    cam_a183mm_butt_group3.addWidget(QLabel("Cir X"))
    cam_a183mm_butt_group3.addWidget(self.a183mm_cam_circ_x)
    cam_a183mm_butt_group3.addWidget(QLabel("Y"))
    cam_a183mm_butt_group3.addWidget(self.a183mm_cam_circ_y)
    cam_a183mm_butt_group3.addWidget(QLabel("D"))
    cam_a183mm_butt_group3.addWidget(self.a183mm_cam_circ_d)
    cam_a183mm_butt_group3.addWidget(QLabel("C"))
    cam_a183mm_butt_group3.addWidget(self.a183mm_cam_circ_c)
    layout.addLayout(cam_a183mm_butt_group3)

    cam_a183mm_butt_group4 = QHBoxLayout()
    cam_a183mm_butt_group4.addWidget(QLabel("Save to file"))
    cam_a183mm_butt_group4.addWidget(self.a183mm_cam_save_img)
    cam_a183mm_butt_group4.addWidget(QLabel("Dirname"))
    cam_a183mm_butt_group4.addWidget(self.a183mm_cam_save_dirname)
    layout.addLayout(cam_a183mm_butt_group4)

    cam_a183mm_butt_group5 = QHBoxLayout()
    cam_a183mm_butt_group5.addWidget(self.a183mm_b_plate_solve)
    cam_a183mm_butt_group5.addWidget(self.a183mm_b_plate_solve_cancel)
    layout.addLayout(cam_a183mm_butt_group5)
    layout.addWidget(self.lab_a183mm_plate_solve_status)
    layout.addWidget(separator3)

    cam_a183mm_pixel_scale = QHBoxLayout()
    cam_a183mm_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a183mm_pixel_scale.addWidget(self.a183mm_cam_scale_pixel_size)
    cam_a183mm_pixel_scale.addWidget(QLabel("F:"))
    cam_a183mm_pixel_scale.addWidget(self.a183mm_cam_scale_focal)
    cam_a183mm_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a183mm_pixel_scale.addWidget(self.a183mm_cam_scale_pixel_scale)
    layout.addLayout(cam_a183mm_pixel_scale)

    cam_a183mm_pic_adj = QHBoxLayout()
    cam_a183mm_pic_adj.addWidget(QLabel("BRI:"))
    cam_a183mm_pic_adj.addWidget(self.a183mm_cam_bri)
    cam_a183mm_pic_adj.addWidget(QLabel("SAT:"))
    cam_a183mm_pic_adj.addWidget(self.a183mm_cam_sat)
    cam_a183mm_pic_adj.addWidget(QLabel("GAM:"))
    cam_a183mm_pic_adj.addWidget(self.a183mm_cam_gam)
    layout.addLayout(cam_a183mm_pic_adj)

    cam_a183mm_pic_adj2 = QHBoxLayout()
    cam_a183mm_pic_adj2.addWidget(QLabel("INV:"))
    cam_a183mm_pic_adj2.addWidget(self.a183mm_cam_inverse)
    cam_a183mm_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a183mm_pic_adj2.addWidget(self.a183mm_cam_hist_equal)
    cam_a183mm_pic_adj2.addStretch()
    cam_a183mm_pic_adj2.addWidget(self.a183mm_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a183mm_pic_adj2)

    cam_a183mm_pic_adj3 = QHBoxLayout()
    cam_a183mm_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a183mm_pic_adj3.addWidget(self.a183mm_cam_normalize)
    cam_a183mm_pic_adj3.addWidget(QLabel("L:"))
    cam_a183mm_pic_adj3.addWidget(self.a183mm_cam_normalize_l)
    cam_a183mm_pic_adj3.addWidget(QLabel("H:"))
    cam_a183mm_pic_adj3.addWidget(self.a183mm_cam_normalize_h)
    cam_a183mm_pic_adj3.addStretch()
    layout.addLayout(cam_a183mm_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a183mm_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a183mm)

    self.lewy_tab2.setLayout(layout)

#############################################################################################

  def tab3_lewyUI(self):
    global cam_settings
    layout = QVBoxLayout()

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)
    separator6 = QFrame()
    separator6.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.lab_a533mc_cam = QLabel("ASI533MC PRO CAM")
    self.lab_a533mc_cam.setFont(self.headline)
    self.lab_a533mc_cam.setAlignment(Qt.AlignCenter)

    self.lab_a533mc_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a533mc_cam_time_frame = QLabel("Last frame time: -1s ago")
    self.lab_a533mc_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a533mc_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a533mc_rotate = QLabel("Rotate: null")
    self.lab_a533mc_cooling = QLabel("Cooler: NULL")

    self.a533mc_cam_exp_slider = QDoubleSpinBox()
    self.a533mc_cam_exp_slider.valueChanged.connect(self.f_a533mc_cam_params_changed)
    self.a533mc_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a533mc_cam_gain_slider = QSpinBox()
    self.a533mc_cam_gain_slider.valueChanged.connect(self.f_a533mc_cam_params_changed)

    self.a533mc_cam_offset_slider = QSpinBox()
    self.a533mc_cam_offset_slider.valueChanged.connect(self.f_a533mc_cam_params_changed)

    self.a533mc_cam_cooler = QCheckBox()
    self.a533mc_cam_cooler.setChecked(False)
    self.a533mc_cam_cooler.stateChanged.connect(self.f_a533mc_cam_params_changed)

    self.a533mc_cam_bin = QComboBox()
    self.a533mc_cam_bin.addItems(['NULL'])
    self.a533mc_cam_bin.currentIndexChanged.connect(self.f_a533mc_cam_params_changed)

    self.a533mc_cam_target_temp_slider = QSpinBox()
    self.a533mc_cam_target_temp_slider.valueChanged.connect(self.f_a533mc_cam_params_changed)

    self.a533mc_cam_reset_settings_button = QPushButton('RST settings', self)
    self.a533mc_cam_reset_settings_button.clicked.connect(self.f_a533mc_cam_reset_settings)
    self.a533mc_photo_reload = QPushButton('Reload', self)
    self.a533mc_photo_reload.clicked.connect(self.f_a533mc_window_refresh)

    self.a533mc_photo_rotate = QPushButton('Rot', self)
    self.a533mc_photo_rotate.clicked.connect(self.f_a533mc_rotate)

    self.a533mc_cam_save_img = QCheckBox()
    self.a533mc_cam_save_img.setChecked(False)

    self.a533mc_cam_save_dirname = QLineEdit(self)
    self.a533mc_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a533mc_cam_save_dirname.setValidator(validator1)
    self.a533mc_cam_save_dirname.setText('teleskop')

    self.a533mc_cam_circ_x = QSpinBox()
    self.a533mc_cam_circ_x.setMinimum(0)
    self.a533mc_cam_circ_x.setMaximum(5496)
    self.a533mc_cam_circ_x.setValue(int(5496/2))

    self.a533mc_cam_circ_y = QSpinBox()
    self.a533mc_cam_circ_y.setMinimum(0)
    self.a533mc_cam_circ_y.setMaximum(3672)
    self.a533mc_cam_circ_y.setValue(int(3672/2))

    self.a533mc_cam_circ_d = QSpinBox()
    self.a533mc_cam_circ_d.setMinimum(0)
    self.a533mc_cam_circ_d.setMaximum(1936)
    self.a533mc_cam_circ_d.setValue(0)

    self.a533mc_cam_circ_c = QSpinBox()
    self.a533mc_cam_circ_c.setMinimum(0)
    self.a533mc_cam_circ_c.setMaximum(2000)
    self.a533mc_cam_circ_c.setValue(0)

    self.a533mc_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.a533mc_b_plate_solve.clicked.connect(self.f_a533mc_plate_solve)

    self.a533mc_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a533mc_b_plate_solve_cancel.clicked.connect(self.f_a533mc_platesolve_stop)

    self.lab_a533mc_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a533mc_cam_scale_pixel_size = QDoubleSpinBox()
    self.a533mc_cam_scale_pixel_size.setMinimum(0.1)
    self.a533mc_cam_scale_pixel_size.setMaximum(99.0)
    self.a533mc_cam_scale_pixel_size.setValue(3.76)
    self.a533mc_cam_scale_pixel_size.valueChanged.connect(self.f_a533mc_cam_pix_scale_calc)

    self.a533mc_cam_scale_focal = QSpinBox()
    self.a533mc_cam_scale_focal.setMinimum(1)
    self.a533mc_cam_scale_focal.setMaximum(9999)
    self.a533mc_cam_scale_focal.setValue(2450)
    self.a533mc_cam_scale_focal.valueChanged.connect(self.f_a533mc_cam_pix_scale_calc)

    self.a533mc_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a533mc_cam_scale_pixel_scale.setMinimum(0.0)
    self.a533mc_cam_scale_pixel_scale.setMaximum(999.0)
    self.a533mc_cam_scale_pixel_scale.setValue(0.24)

    self.a533mc_cam_bri = QSpinBox()
    self.a533mc_cam_bri.setValue(0)
    self.a533mc_cam_bri.setMinimum(-255)
    self.a533mc_cam_bri.setMaximum(255)

    self.a533mc_cam_sat = QDoubleSpinBox()
    self.a533mc_cam_sat.setValue(1.0)
    self.a533mc_cam_sat.setMinimum(0.0)
    self.a533mc_cam_sat.setMaximum(10.0)
    self.a533mc_cam_sat.setSingleStep(0.01)

    self.a533mc_cam_gam = QDoubleSpinBox()
    self.a533mc_cam_gam.setValue(1.0)
    self.a533mc_cam_gam.setMinimum(0.0)
    self.a533mc_cam_gam.setMaximum(10.0)
    self.a533mc_cam_gam.setSingleStep(0.01)

    self.a533mc_cam_inverse = QCheckBox()
    self.a533mc_cam_inverse.setChecked(False)

    self.a533mc_cam_hist_equal = QCheckBox()
    self.a533mc_cam_hist_equal.setChecked(False)

    self.a533mc_cam_normalize = QCheckBox()
    self.a533mc_cam_normalize.setChecked(False)

    self.a533mc_cam_normalize_l = QDoubleSpinBox()
    self.a533mc_cam_normalize_l.setValue(0.0)
    self.a533mc_cam_normalize_l.setMinimum(0.0)
    self.a533mc_cam_normalize_l.setMaximum(100.0)
    self.a533mc_cam_normalize_l.setSingleStep(0.01)

    self.a533mc_cam_normalize_h = QDoubleSpinBox()
    self.a533mc_cam_normalize_h.setMinimum(0.0)
    self.a533mc_cam_normalize_h.setMaximum(100.0)
    self.a533mc_cam_normalize_h.setSingleStep(0.01)
    self.a533mc_cam_normalize_h.setValue(100.0)

    self.a533mc_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a533mc_cam_bri_sat_gam_rst.clicked.connect(self.f_a533mc_cam_bri_sat_gam_rst)

    self.lab_a533mc_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.graphWidget_a533mc = pg.PlotWidget()
    self.hist_color_a533mc = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_a533mc = pg.mkPen(color=(0,0,0))
    self.graphWidget_a533mc.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_a533mc)
    self.graphWidget_a533mc.setBackground(self.hist_color_a533mc)
    self.graphWidget_a533mc.hideAxis('bottom')
    self.graphWidget_a533mc.hideAxis('left')


    layout.addWidget(self.lab_a533mc_cam)
    layout.addWidget(self.lab_a533mc_cam_time_param)
    layout.addWidget(self.lab_a533mc_cam_time_frame)
    layout.addWidget(self.lab_a533mc_cam_time_disp_frame)
    layout.addWidget(self.lab_a533mc_rotate)
    layout.addWidget(self.lab_a533mc_cam_temp)
    layout.addWidget(self.lab_a533mc_cooling)
    layout.addWidget(separator1)
    layout.addWidget(self.a533mc_cam_exp_gain_depl)
    layout.addWidget(separator2)

    cam_a533mc_gain_layout = QHBoxLayout()
    cam_a533mc_gain_layout.addWidget(QLabel("Exp:"))
    cam_a533mc_gain_layout.addWidget(self.a533mc_cam_exp_slider)
    cam_a533mc_gain_layout.addWidget(QLabel("ms"))
    cam_a533mc_gain_layout.addWidget(QLabel("Gain:"))
    cam_a533mc_gain_layout.addWidget(self.a533mc_cam_gain_slider)
    cam_a533mc_gain_layout.addWidget(QLabel("Offset:"))
    cam_a533mc_gain_layout.addWidget(self.a533mc_cam_offset_slider)
    cam_a533mc_gain_layout.addStretch()
    layout.addLayout(cam_a533mc_gain_layout)

    cam_a533mc_temp_layout = QHBoxLayout()
    cam_a533mc_temp_layout.addWidget(QLabel("Cooler EN: "))
    cam_a533mc_temp_layout.addWidget(self.a533mc_cam_cooler)
    cam_a533mc_temp_layout.addWidget(QLabel("Temp: "))
    cam_a533mc_temp_layout.addWidget(self.a533mc_cam_target_temp_slider)
    cam_a533mc_temp_layout.addStretch()
    layout.addLayout(cam_a533mc_temp_layout)

    cam_a533mc_butt_group2 = QHBoxLayout()
    cam_a533mc_butt_group2.addWidget(self.a533mc_cam_reset_settings_button)
    cam_a533mc_butt_group2.addWidget(self.a533mc_photo_reload)
    cam_a533mc_butt_group2.addWidget(self.a533mc_photo_rotate)
    cam_a533mc_butt_group2.addWidget(QLabel("bin:"))
    cam_a533mc_butt_group2.addWidget(self.a533mc_cam_bin)
    cam_a533mc_butt_group2.addStretch()
    layout.addLayout(cam_a533mc_butt_group2)

    cam_a533mc_butt_group3 = QHBoxLayout()
    cam_a533mc_butt_group3.addWidget(QLabel("Cir X"))
    cam_a533mc_butt_group3.addWidget(self.a533mc_cam_circ_x)
    cam_a533mc_butt_group3.addWidget(QLabel("Y"))
    cam_a533mc_butt_group3.addWidget(self.a533mc_cam_circ_y)
    cam_a533mc_butt_group3.addWidget(QLabel("D"))
    cam_a533mc_butt_group3.addWidget(self.a533mc_cam_circ_d)
    cam_a533mc_butt_group3.addWidget(QLabel("C"))
    cam_a533mc_butt_group3.addWidget(self.a533mc_cam_circ_c)
    layout.addLayout(cam_a533mc_butt_group3)

    cam_a533mc_butt_group4 = QHBoxLayout()
    cam_a533mc_butt_group4.addWidget(QLabel("Save to file"))
    cam_a533mc_butt_group4.addWidget(self.a533mc_cam_save_img)
    cam_a533mc_butt_group4.addWidget(QLabel("Dirname"))
    cam_a533mc_butt_group4.addWidget(self.a533mc_cam_save_dirname)
    layout.addLayout(cam_a533mc_butt_group4)

    cam_a533mc_butt_group5 = QHBoxLayout()
    cam_a533mc_butt_group5.addWidget(self.a533mc_b_plate_solve)
    cam_a533mc_butt_group5.addWidget(self.a533mc_b_plate_solve_cancel)
    layout.addLayout(cam_a533mc_butt_group5)
    layout.addWidget(self.lab_a533mc_plate_solve_status)
    layout.addWidget(separator3)

    cam_a533mc_pixel_scale = QHBoxLayout()
    cam_a533mc_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a533mc_pixel_scale.addWidget(self.a533mc_cam_scale_pixel_size)
    cam_a533mc_pixel_scale.addWidget(QLabel("F:"))
    cam_a533mc_pixel_scale.addWidget(self.a533mc_cam_scale_focal)
    cam_a533mc_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a533mc_pixel_scale.addWidget(self.a533mc_cam_scale_pixel_scale)
    layout.addLayout(cam_a533mc_pixel_scale)

    cam_a533mc_pic_adj = QHBoxLayout()
    cam_a533mc_pic_adj.addWidget(QLabel("BRI:"))
    cam_a533mc_pic_adj.addWidget(self.a533mc_cam_bri)
    cam_a533mc_pic_adj.addWidget(QLabel("SAT:"))
    cam_a533mc_pic_adj.addWidget(self.a533mc_cam_sat)
    cam_a533mc_pic_adj.addWidget(QLabel("GAM:"))
    cam_a533mc_pic_adj.addWidget(self.a533mc_cam_gam)
    layout.addLayout(cam_a533mc_pic_adj)

    cam_a533mc_pic_adj2 = QHBoxLayout()
    cam_a533mc_pic_adj2.addWidget(QLabel("INV:"))
    cam_a533mc_pic_adj2.addWidget(self.a533mc_cam_inverse)
    cam_a533mc_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a533mc_pic_adj2.addWidget(self.a533mc_cam_hist_equal)
    cam_a533mc_pic_adj2.addStretch()
    cam_a533mc_pic_adj2.addWidget(self.a533mc_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a533mc_pic_adj2)

    cam_a533mc_pic_adj3 = QHBoxLayout()
    cam_a533mc_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a533mc_pic_adj3.addWidget(self.a533mc_cam_normalize)
    cam_a533mc_pic_adj3.addWidget(QLabel("L:"))
    cam_a533mc_pic_adj3.addWidget(self.a533mc_cam_normalize_l)
    cam_a533mc_pic_adj3.addWidget(QLabel("H:"))
    cam_a533mc_pic_adj3.addWidget(self.a533mc_cam_normalize_h)
    cam_a533mc_pic_adj3.addStretch()
    layout.addLayout(cam_a533mc_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a533mc_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a533mc)

    self.lewy_tab3.setLayout(layout)

#############################################################################################

  def tab4_lewyUI(self):
    global cam_settings
    layout = QVBoxLayout()

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)
    separator6 = QFrame()
    separator6.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.lab_a462mc_cam = QLabel("ASI462MC CAM")
    self.lab_a462mc_cam.setFont(self.headline)
    self.lab_a462mc_cam.setAlignment(Qt.AlignCenter)

    self.lab_a462mc_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a462mc_cam_time_frame = QLabel("Last frame time: -1s ago")
    self.lab_a462mc_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a462mc_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a462mc_rotate = QLabel("Rotate: null")

    self.a462mc_cam_exp_slider = QDoubleSpinBox()
    self.a462mc_cam_exp_slider.valueChanged.connect(self.f_a462mc_cam_params_changed)
    self.a462mc_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a462mc_cam_gain_slider = QSpinBox()
    self.a462mc_cam_gain_slider.valueChanged.connect(self.f_a462mc_cam_params_changed)

    self.a462mc_cam_offset_slider = QSpinBox()
    self.a462mc_cam_offset_slider.valueChanged.connect(self.f_a462mc_cam_params_changed)

    self.a462mc_cam_reset_settings_button = QPushButton('RST settings', self)
    self.a462mc_cam_reset_settings_button.clicked.connect(self.f_a462mc_cam_reset_settings)
    self.a462mc_photo_reload = QPushButton('Reload', self)
    self.a462mc_photo_reload.clicked.connect(self.f_a462mc_window_refresh)

    self.a462mc_photo_rotate = QPushButton('Rot', self)
    self.a462mc_photo_rotate.clicked.connect(self.f_a462mc_rotate)

    self.a462mc_cam_bin = QComboBox()
    self.a462mc_cam_bin.addItems(['NULL'])
    self.a462mc_cam_bin.currentIndexChanged.connect(self.f_a462mc_cam_params_changed)

    self.a462mc_cam_save_img = QCheckBox()
    self.a462mc_cam_save_img.setChecked(False)

    self.a462mc_cam_save_dirname = QLineEdit(self)
    self.a462mc_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a462mc_cam_save_dirname.setValidator(validator1)
    self.a462mc_cam_save_dirname.setText('teleskop')

    self.a462mc_cam_circ_x = QSpinBox()
    self.a462mc_cam_circ_x.setMinimum(0)
    self.a462mc_cam_circ_x.setMaximum(1936)
    self.a462mc_cam_circ_x.setValue(968)

    self.a462mc_cam_circ_y = QSpinBox()
    self.a462mc_cam_circ_y.setMinimum(0)
    self.a462mc_cam_circ_y.setMaximum(1096)
    self.a462mc_cam_circ_y.setValue(548)

    self.a462mc_cam_circ_d = QSpinBox()
    self.a462mc_cam_circ_d.setMinimum(0)
    self.a462mc_cam_circ_d.setMaximum(1936)
    self.a462mc_cam_circ_d.setValue(0)

    self.a462mc_cam_circ_c = QSpinBox()
    self.a462mc_cam_circ_c.setMinimum(0)
    self.a462mc_cam_circ_c.setMaximum(600)
    self.a462mc_cam_circ_c.setValue(0)

    self.a462mc_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.a462mc_b_plate_solve.clicked.connect(self.f_a462mc_plate_solve)

    self.a462mc_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a462mc_b_plate_solve_cancel.clicked.connect(self.f_a462mc_platesolve_stop)

    self.lab_a462mc_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a462mc_cam_scale_pixel_size = QDoubleSpinBox()
    self.a462mc_cam_scale_pixel_size.setMinimum(0.1)
    self.a462mc_cam_scale_pixel_size.setMaximum(99.0)
    self.a462mc_cam_scale_pixel_size.setValue(2.9)
    self.a462mc_cam_scale_pixel_size.valueChanged.connect(self.f_a462mc_cam_pix_scale_calc)

    self.a462mc_cam_scale_focal = QSpinBox()
    self.a462mc_cam_scale_focal.setMinimum(1)
    self.a462mc_cam_scale_focal.setMaximum(9999)
    self.a462mc_cam_scale_focal.setValue(2450)
    self.a462mc_cam_scale_focal.valueChanged.connect(self.f_a462mc_cam_pix_scale_calc)

    self.a462mc_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a462mc_cam_scale_pixel_scale.setMinimum(0.0)
    self.a462mc_cam_scale_pixel_scale.setMaximum(999.0)
    self.a462mc_cam_scale_pixel_scale.setValue(0.24)

    self.a462mc_cam_bri = QSpinBox()
    self.a462mc_cam_bri.setValue(0)
    self.a462mc_cam_bri.setMinimum(-255)
    self.a462mc_cam_bri.setMaximum(255)

    self.a462mc_cam_sat = QDoubleSpinBox()
    self.a462mc_cam_sat.setValue(1.0)
    self.a462mc_cam_sat.setMinimum(0.0)
    self.a462mc_cam_sat.setMaximum(10.0)
    self.a462mc_cam_sat.setSingleStep(0.01)

    self.a462mc_cam_gam = QDoubleSpinBox()
    self.a462mc_cam_gam.setValue(1.0)
    self.a462mc_cam_gam.setMinimum(0.0)
    self.a462mc_cam_gam.setMaximum(10.0)
    self.a462mc_cam_gam.setSingleStep(0.01)

    self.a462mc_cam_inverse = QCheckBox()
    self.a462mc_cam_inverse.setChecked(False)

    self.a462mc_cam_hist_equal = QCheckBox()
    self.a462mc_cam_hist_equal.setChecked(False)

    self.a462mc_cam_normalize = QCheckBox()
    self.a462mc_cam_normalize.setChecked(False)

    self.a462mc_cam_normalize_l = QDoubleSpinBox()
    self.a462mc_cam_normalize_l.setValue(0.0)
    self.a462mc_cam_normalize_l.setMinimum(0.0)
    self.a462mc_cam_normalize_l.setMaximum(100.0)
    self.a462mc_cam_normalize_l.setSingleStep(0.01)

    self.a462mc_cam_normalize_h = QDoubleSpinBox()
    self.a462mc_cam_normalize_h.setMinimum(0.0)
    self.a462mc_cam_normalize_h.setMaximum(100.0)
    self.a462mc_cam_normalize_h.setSingleStep(0.01)
    self.a462mc_cam_normalize_h.setValue(100.0)

    self.a462mc_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a462mc_cam_bri_sat_gam_rst.clicked.connect(self.f_a462mc_cam_bri_sat_gam_rst)

    self.lab_a462mc_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.graphWidget_a462mc = pg.PlotWidget()
    self.hist_color_a462mc = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_a462mc = pg.mkPen(color=(0,0,0))
    self.graphWidget_a462mc.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_a462mc)
    self.graphWidget_a462mc.setBackground(self.hist_color_a462mc)
    self.graphWidget_a462mc.hideAxis('bottom')
    self.graphWidget_a462mc.hideAxis('left')


    layout.addWidget(self.lab_a462mc_cam)
    layout.addWidget(self.lab_a462mc_cam_time_param)
    layout.addWidget(self.lab_a462mc_cam_time_frame)
    layout.addWidget(self.lab_a462mc_cam_time_disp_frame)
    layout.addWidget(self.lab_a462mc_cam_temp)
    layout.addWidget(self.lab_a462mc_rotate)
    layout.addWidget(separator1)
    layout.addWidget(self.a462mc_cam_exp_gain_depl)
    layout.addWidget(separator2)

    cam_a462mc_gain_layout = QHBoxLayout()
    cam_a462mc_gain_layout.addWidget(QLabel("Exposure:"))
    cam_a462mc_gain_layout.addWidget(self.a462mc_cam_exp_slider)
    cam_a462mc_gain_layout.addWidget(QLabel("ms"))
    cam_a462mc_gain_layout.addWidget(QLabel("Gain:"))
    cam_a462mc_gain_layout.addWidget(self.a462mc_cam_gain_slider)
    cam_a462mc_gain_layout.addWidget(QLabel("Offset:"))
    cam_a462mc_gain_layout.addWidget(self.a462mc_cam_offset_slider)
    cam_a462mc_gain_layout.addStretch()
    layout.addLayout(cam_a462mc_gain_layout)

    cam_a462mc_butt_group2 = QHBoxLayout()
    cam_a462mc_butt_group2.addWidget(self.a462mc_cam_reset_settings_button)
    cam_a462mc_butt_group2.addWidget(self.a462mc_photo_reload)
    cam_a462mc_butt_group2.addWidget(self.a462mc_photo_rotate)
    cam_a462mc_butt_group2.addWidget(QLabel("bin:"))
    cam_a462mc_butt_group2.addWidget(self.a462mc_cam_bin)
    cam_a462mc_butt_group2.addStretch()
    layout.addLayout(cam_a462mc_butt_group2)

    cam_a462mc_butt_group3 = QHBoxLayout()
    cam_a462mc_butt_group3.addWidget(QLabel("Cir X"))
    cam_a462mc_butt_group3.addWidget(self.a462mc_cam_circ_x)
    cam_a462mc_butt_group3.addWidget(QLabel("Y"))
    cam_a462mc_butt_group3.addWidget(self.a462mc_cam_circ_y)
    cam_a462mc_butt_group3.addWidget(QLabel("D"))
    cam_a462mc_butt_group3.addWidget(self.a462mc_cam_circ_d)
    cam_a462mc_butt_group3.addWidget(QLabel("C"))
    cam_a462mc_butt_group3.addWidget(self.a462mc_cam_circ_c)
    layout.addLayout(cam_a462mc_butt_group3)

    cam_a462mc_butt_group4 = QHBoxLayout()
    cam_a462mc_butt_group4.addWidget(QLabel("Save to file"))
    cam_a462mc_butt_group4.addWidget(self.a462mc_cam_save_img)
    cam_a462mc_butt_group4.addWidget(QLabel("Dirname"))
    cam_a462mc_butt_group4.addWidget(self.a462mc_cam_save_dirname)
    layout.addLayout(cam_a462mc_butt_group4)

    cam_a462mc_butt_group5 = QHBoxLayout()
    cam_a462mc_butt_group5.addWidget(self.a462mc_b_plate_solve)
    cam_a462mc_butt_group5.addWidget(self.a462mc_b_plate_solve_cancel)
    layout.addLayout(cam_a462mc_butt_group5)
    layout.addWidget(self.lab_a462mc_plate_solve_status)
    layout.addWidget(separator3)

    cam_a462mc_pixel_scale = QHBoxLayout()
    cam_a462mc_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a462mc_pixel_scale.addWidget(self.a462mc_cam_scale_pixel_size)
    cam_a462mc_pixel_scale.addWidget(QLabel("F:"))
    cam_a462mc_pixel_scale.addWidget(self.a462mc_cam_scale_focal)
    cam_a462mc_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a462mc_pixel_scale.addWidget(self.a462mc_cam_scale_pixel_scale)
    layout.addLayout(cam_a462mc_pixel_scale)

    cam_a462mc_pic_adj = QHBoxLayout()
    cam_a462mc_pic_adj.addWidget(QLabel("BRI:"))
    cam_a462mc_pic_adj.addWidget(self.a462mc_cam_bri)
    cam_a462mc_pic_adj.addWidget(QLabel("SAT:"))
    cam_a462mc_pic_adj.addWidget(self.a462mc_cam_sat)
    cam_a462mc_pic_adj.addWidget(QLabel("GAM:"))
    cam_a462mc_pic_adj.addWidget(self.a462mc_cam_gam)
    layout.addLayout(cam_a462mc_pic_adj)

    cam_a462mc_pic_adj2 = QHBoxLayout()
    cam_a462mc_pic_adj2.addWidget(QLabel("INV:"))
    cam_a462mc_pic_adj2.addWidget(self.a462mc_cam_inverse)
    cam_a462mc_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a462mc_pic_adj2.addWidget(self.a462mc_cam_hist_equal)
    cam_a462mc_pic_adj2.addStretch()
    cam_a462mc_pic_adj2.addWidget(self.a462mc_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a462mc_pic_adj2)

    cam_a462mc_pic_adj3 = QHBoxLayout()
    cam_a462mc_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a462mc_pic_adj3.addWidget(self.a462mc_cam_normalize)
    cam_a462mc_pic_adj3.addWidget(QLabel("L:"))
    cam_a462mc_pic_adj3.addWidget(self.a462mc_cam_normalize_l)
    cam_a462mc_pic_adj3.addWidget(QLabel("H:"))
    cam_a462mc_pic_adj3.addWidget(self.a462mc_cam_normalize_h)
    cam_a462mc_pic_adj3.addStretch()
    layout.addLayout(cam_a462mc_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a462mc_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a462mc)

    self.lewy_tab4.setLayout(layout)

#############################################################################################

  def tab5_lewyUI(self):
    global cam_settings
    layout = QVBoxLayout()

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)
    separator6 = QFrame()
    separator6.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.lab_a120mm_cam = QLabel("ASI120MM mini CAM")
    self.lab_a120mm_cam.setFont(self.headline)
    self.lab_a120mm_cam.setAlignment(Qt.AlignCenter)

    self.lab_a120mm_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a120mm_cam_time_frame = QLabel("Last frame time: -1s ago")
    self.lab_a120mm_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a120mm_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a120mm_rotate = QLabel("Rotate: null")

    self.a120mm_cam_exp_slider = QDoubleSpinBox()
    self.a120mm_cam_exp_slider.valueChanged.connect(self.f_a120mm_cam_params_changed)
    self.a120mm_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a120mm_cam_gain_slider = QSpinBox()
    self.a120mm_cam_gain_slider.valueChanged.connect(self.f_a120mm_cam_params_changed)

    self.a120mm_cam_offset_slider = QSpinBox()
    self.a120mm_cam_offset_slider.valueChanged.connect(self.f_a120mm_cam_params_changed)

    self.a120mm_cam_reset_settings_button = QPushButton('RST settings', self)
    self.a120mm_cam_reset_settings_button.clicked.connect(self.f_a120mm_cam_reset_settings)
    self.a120mm_photo_reload = QPushButton('Reload photo', self)
    self.a120mm_photo_reload.clicked.connect(self.f_a120mm_window_refresh)

    self.a120mm_photo_rotate = QPushButton('Rotate', self)
    self.a120mm_photo_rotate.clicked.connect(self.f_a120mm_rotate)

    self.a120mm_cam_bin = QComboBox()
    self.a120mm_cam_bin.addItems(['NULL'])
    self.a120mm_cam_bin.currentIndexChanged.connect(self.f_a120mm_cam_params_changed)

    self.a120mm_cam_circ_x = QSpinBox()
    self.a120mm_cam_circ_x.setMinimum(0)
    self.a120mm_cam_circ_x.setMaximum(1280)
    self.a120mm_cam_circ_x.setValue(640)

    self.a120mm_cam_circ_y = QSpinBox()
    self.a120mm_cam_circ_y.setMinimum(0)
    self.a120mm_cam_circ_y.setMaximum(960)
    self.a120mm_cam_circ_y.setValue(480)

    self.a120mm_cam_circ_d = QSpinBox()
    self.a120mm_cam_circ_d.setMinimum(0)
    self.a120mm_cam_circ_d.setMaximum(1200)
    self.a120mm_cam_circ_d.setValue(0)

    self.a120mm_cam_circ_c = QSpinBox()
    self.a120mm_cam_circ_c.setMinimum(0)
    self.a120mm_cam_circ_c.setMaximum(900)
    self.a120mm_cam_circ_c.setValue(0)

    self.a120mm_cam_save_img = QCheckBox()
    self.a120mm_cam_save_img.setChecked(False)

    self.a120mm_cam_save_dirname = QLineEdit(self)
    self.a120mm_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a120mm_cam_save_dirname.setValidator(validator1)
    self.a120mm_cam_save_dirname.setText('teleskop')

    self.a120mm_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.a120mm_b_plate_solve.clicked.connect(self.f_a120mm_plate_solve)
    self.a120mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a120mm_b_plate_solve_cancel.clicked.connect(self.f_a120mm_platesolve_stop)
    self.lab_a120mm_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a120mm_cam_scale_pixel_size = QDoubleSpinBox()
    self.a120mm_cam_scale_pixel_size.setMinimum(0.1)
    self.a120mm_cam_scale_pixel_size.setMaximum(99.0)
    self.a120mm_cam_scale_pixel_size.setValue(3.75)
    self.a120mm_cam_scale_pixel_size.valueChanged.connect(self.f_a120mm_cam_pix_scale_calc)

    self.a120mm_cam_scale_focal = QSpinBox()
    self.a120mm_cam_scale_focal.setMinimum(1)
    self.a120mm_cam_scale_focal.setMaximum(9999)
    self.a120mm_cam_scale_focal.setValue(505)
    self.a120mm_cam_scale_focal.valueChanged.connect(self.f_a120mm_cam_pix_scale_calc)

    self.a120mm_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a120mm_cam_scale_pixel_scale.setMinimum(0.0)
    self.a120mm_cam_scale_pixel_scale.setMaximum(999.0)
    self.a120mm_cam_scale_pixel_scale.setValue(1.53)

    self.a120mm_cam_bri = QSpinBox()
    self.a120mm_cam_bri.setValue(0)
    self.a120mm_cam_bri.setMinimum(-255)
    self.a120mm_cam_bri.setMaximum(255)

    self.a120mm_cam_sat = QDoubleSpinBox()
    self.a120mm_cam_sat.setValue(1.0)
    self.a120mm_cam_sat.setMinimum(0.0)
    self.a120mm_cam_sat.setMaximum(10.0)
    self.a120mm_cam_sat.setSingleStep(0.01)

    self.a120mm_cam_gam = QDoubleSpinBox()
    self.a120mm_cam_gam.setValue(1.0)
    self.a120mm_cam_gam.setMinimum(0.0)
    self.a120mm_cam_gam.setMaximum(10.0)
    self.a120mm_cam_gam.setSingleStep(0.01)

    self.a120mm_cam_inverse = QCheckBox()
    self.a120mm_cam_inverse.setChecked(False)

    self.a120mm_cam_hist_equal = QCheckBox()
    self.a120mm_cam_hist_equal.setChecked(False)

    self.a120mm_cam_normalize = QCheckBox()
    self.a120mm_cam_normalize.setChecked(False)

    self.a120mm_cam_normalize_l = QDoubleSpinBox()
    self.a120mm_cam_normalize_l.setValue(0.0)
    self.a120mm_cam_normalize_l.setMinimum(0.0)
    self.a120mm_cam_normalize_l.setMaximum(100.0)
    self.a120mm_cam_normalize_l.setSingleStep(0.01)

    self.a120mm_cam_normalize_h = QDoubleSpinBox()
    self.a120mm_cam_normalize_h.setMinimum(0.0)
    self.a120mm_cam_normalize_h.setMaximum(100.0)
    self.a120mm_cam_normalize_h.setSingleStep(0.01)
    self.a120mm_cam_normalize_h.setValue(100.0)

    self.a120mm_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a120mm_cam_bri_sat_gam_rst.clicked.connect(self.f_a120mm_cam_bri_sat_gam_rst)

    self.lab_a120mm_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.graphWidget_a120mm = pg.PlotWidget()
    self.hist_color_a120mm = self.palette().color(QtGui.QPalette.Window)
    self.graphWidget_a120mm.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_gray)
    self.graphWidget_a120mm.setBackground(self.hist_color_a120mm)
    self.graphWidget_a120mm.hideAxis('bottom')
    self.graphWidget_a120mm.hideAxis('left')


    layout.addWidget(self.lab_a120mm_cam)
    layout.addWidget(self.lab_a120mm_cam_time_param)
    layout.addWidget(self.lab_a120mm_cam_time_frame)
    layout.addWidget(self.lab_a120mm_cam_time_disp_frame)
    layout.addWidget(self.lab_a120mm_cam_temp)
    layout.addWidget(self.lab_a120mm_rotate)
    layout.addWidget(separator1)
    layout.addWidget(self.a120mm_cam_exp_gain_depl)
    layout.addWidget(separator2)

    cam_a120mm_gain_layout = QHBoxLayout()
    cam_a120mm_gain_layout.addWidget(QLabel("Exposure:"))
    cam_a120mm_gain_layout.addWidget(self.a120mm_cam_exp_slider)
    cam_a120mm_gain_layout.addWidget(QLabel("ms"))
    cam_a120mm_gain_layout.addWidget(QLabel("Gain:"))
    cam_a120mm_gain_layout.addWidget(self.a120mm_cam_gain_slider)
    cam_a120mm_gain_layout.addWidget(QLabel("Offset:"))
    cam_a120mm_gain_layout.addWidget(self.a120mm_cam_offset_slider)
    cam_a120mm_gain_layout.addStretch()
    layout.addLayout(cam_a120mm_gain_layout)

    cam_a120mm_butt_group2 = QHBoxLayout()
    cam_a120mm_butt_group2.addWidget(self.a120mm_cam_reset_settings_button)
    cam_a120mm_butt_group2.addWidget(self.a120mm_photo_reload)
    cam_a120mm_butt_group2.addWidget(self.a120mm_photo_rotate)
    cam_a120mm_butt_group2.addWidget(QLabel("bin:"))
    cam_a120mm_butt_group2.addWidget(self.a120mm_cam_bin)
    cam_a120mm_butt_group2.addStretch()
    layout.addLayout(cam_a120mm_butt_group2)

    cam_a120mm_butt_group3 = QHBoxLayout()
    cam_a120mm_butt_group3.addWidget(QLabel("Cir X"))
    cam_a120mm_butt_group3.addWidget(self.a120mm_cam_circ_x)
    cam_a120mm_butt_group3.addWidget(QLabel("Y"))
    cam_a120mm_butt_group3.addWidget(self.a120mm_cam_circ_y)
    cam_a120mm_butt_group3.addWidget(QLabel("D"))
    cam_a120mm_butt_group3.addWidget(self.a120mm_cam_circ_d)
    cam_a120mm_butt_group3.addWidget(QLabel("C"))
    cam_a120mm_butt_group3.addWidget(self.a120mm_cam_circ_c)
    layout.addLayout(cam_a120mm_butt_group3)

    cam_a120mm_butt_group4 = QHBoxLayout()
    cam_a120mm_butt_group4.addWidget(QLabel("Save to file"))
    cam_a120mm_butt_group4.addWidget(self.a120mm_cam_save_img)
    cam_a120mm_butt_group4.addWidget(QLabel("Dirname"))
    cam_a120mm_butt_group4.addWidget(self.a120mm_cam_save_dirname)
    cam_a120mm_butt_group4.addStretch()
    layout.addLayout(cam_a120mm_butt_group4)

    cam_a120mm_butt_group5 = QHBoxLayout()
    cam_a120mm_butt_group5.addWidget(self.a120mm_b_plate_solve)
    cam_a120mm_butt_group5.addWidget(self.a120mm_b_plate_solve_cancel)
    layout.addLayout(cam_a120mm_butt_group5)
    layout.addWidget(self.lab_a120mm_plate_solve_status)
    layout.addWidget(separator3)

    cam_a120mm_pixel_scale = QHBoxLayout()
    cam_a120mm_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a120mm_pixel_scale.addWidget(self.a120mm_cam_scale_pixel_size)
    cam_a120mm_pixel_scale.addWidget(QLabel("F:"))
    cam_a120mm_pixel_scale.addWidget(self.a120mm_cam_scale_focal)
    cam_a120mm_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a120mm_pixel_scale.addWidget(self.a120mm_cam_scale_pixel_scale)
    layout.addLayout(cam_a120mm_pixel_scale)

    cam_a120mm_pic_adj = QHBoxLayout()
    cam_a120mm_pic_adj.addWidget(QLabel("BRI:"))
    cam_a120mm_pic_adj.addWidget(self.a120mm_cam_bri)
    cam_a120mm_pic_adj.addWidget(QLabel("SAT:"))
    cam_a120mm_pic_adj.addWidget(self.a120mm_cam_sat)
    cam_a120mm_pic_adj.addWidget(QLabel("GAM:"))
    cam_a120mm_pic_adj.addWidget(self.a120mm_cam_gam)
    layout.addLayout(cam_a120mm_pic_adj)

    cam_a120mm_pic_adj2 = QHBoxLayout()
    cam_a120mm_pic_adj2.addWidget(QLabel("INV:"))
    cam_a120mm_pic_adj2.addWidget(self.a120mm_cam_inverse)
    cam_a120mm_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a120mm_pic_adj2.addWidget(self.a120mm_cam_hist_equal)
    cam_a120mm_pic_adj2.addStretch()
    cam_a120mm_pic_adj2.addWidget(self.a120mm_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a120mm_pic_adj2)

    cam_a120mm_pic_adj3 = QHBoxLayout()
    cam_a120mm_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a120mm_pic_adj3.addWidget(self.a120mm_cam_normalize)
    cam_a120mm_pic_adj3.addWidget(QLabel("L:"))
    cam_a120mm_pic_adj3.addWidget(self.a120mm_cam_normalize_l)
    cam_a120mm_pic_adj3.addWidget(QLabel("H:"))
    cam_a120mm_pic_adj3.addWidget(self.a120mm_cam_normalize_h)
    cam_a120mm_pic_adj3.addStretch()
    layout.addLayout(cam_a120mm_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a120mm_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a120mm)

    self.lewy_tab5.setLayout(layout)

#############################################################################################

  def tab6_lewyUI(self):
    global cam_settings
    layout = QVBoxLayout()

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)
    separator6 = QFrame()
    separator6.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.lab_a120mc_cam = QLabel("ASI120MC CAM")
    self.lab_a120mc_cam.setFont(self.headline)
    self.lab_a120mc_cam.setAlignment(Qt.AlignCenter)

    self.lab_a120mc_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a120mc_cam_time_frame = QLabel("Last frame time: -1s ago")
    self.lab_a120mc_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a120mc_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a120mc_rotate = QLabel("Rotate: null")

    self.a120mc_cam_exp_slider = QDoubleSpinBox()
    self.a120mc_cam_exp_slider.valueChanged.connect(self.f_a120mc_cam_params_changed)
    self.a120mc_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a120mc_cam_gain_slider = QSpinBox()
    self.a120mc_cam_gain_slider.valueChanged.connect(self.f_a120mc_cam_params_changed)

    self.a120mc_cam_offset_slider = QSpinBox()
    self.a120mc_cam_offset_slider.valueChanged.connect(self.f_a120mc_cam_params_changed)

    self.a120mc_cam_reset_settings_button = QPushButton('RST settings', self)
    self.a120mc_cam_reset_settings_button.clicked.connect(self.f_a120mc_cam_reset_settings)
    self.a120mc_photo_reload = QPushButton('Reload photo', self)
    self.a120mc_photo_reload.clicked.connect(self.f_a120mc_window_refresh)

    self.a120mc_photo_rotate = QPushButton('Rotate', self)
    self.a120mc_photo_rotate.clicked.connect(self.f_a120mc_rotate)

    self.a120mc_cam_bin = QComboBox()
    self.a120mc_cam_bin.addItems(['NULL'])
    self.a120mc_cam_bin.currentIndexChanged.connect(self.f_a120mc_cam_params_changed)

    self.a120mc_cam_circ_x = QSpinBox()
    self.a120mc_cam_circ_x.setMinimum(0)
    self.a120mc_cam_circ_x.setMaximum(1280)
    self.a120mc_cam_circ_x.setValue(640)

    self.a120mc_cam_circ_y = QSpinBox()
    self.a120mc_cam_circ_y.setMinimum(0)
    self.a120mc_cam_circ_y.setMaximum(960)
    self.a120mc_cam_circ_y.setValue(480)

    self.a120mc_cam_circ_d = QSpinBox()
    self.a120mc_cam_circ_d.setMinimum(0)
    self.a120mc_cam_circ_d.setMaximum(1200)
    self.a120mc_cam_circ_d.setValue(0)

    self.a120mc_cam_circ_c = QSpinBox()
    self.a120mc_cam_circ_c.setMinimum(0)
    self.a120mc_cam_circ_c.setMaximum(900)
    self.a120mc_cam_circ_c.setValue(0)

    self.a120mc_cam_save_img = QCheckBox()
    self.a120mc_cam_save_img.setChecked(False)

    self.a120mc_cam_save_dirname = QLineEdit(self)
    self.a120mc_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a120mc_cam_save_dirname.setValidator(validator1)
    self.a120mc_cam_save_dirname.setText('teleskop')

    self.a120mc_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.a120mc_b_plate_solve.clicked.connect(self.f_a120mc_plate_solve)
    self.a120mc_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a120mc_b_plate_solve_cancel.clicked.connect(self.f_a120mc_platesolve_stop)
    self.lab_a120mc_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a120mc_cam_scale_pixel_size = QDoubleSpinBox()
    self.a120mc_cam_scale_pixel_size.setMinimum(0.1)
    self.a120mc_cam_scale_pixel_size.setMaximum(99.0)
    self.a120mc_cam_scale_pixel_size.setValue(3.75)
    self.a120mc_cam_scale_pixel_size.valueChanged.connect(self.f_a120mc_cam_pix_scale_calc)

    self.a120mc_cam_scale_focal = QSpinBox()
    self.a120mc_cam_scale_focal.setMinimum(1)
    self.a120mc_cam_scale_focal.setMaximum(9999)
    self.a120mc_cam_scale_focal.setValue(216)
    self.a120mc_cam_scale_focal.valueChanged.connect(self.f_a120mc_cam_pix_scale_calc)

    self.a120mc_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a120mc_cam_scale_pixel_scale.setMinimum(0.0)
    self.a120mc_cam_scale_pixel_scale.setMaximum(999.0)
    self.a120mc_cam_scale_pixel_scale.setValue(3.58)

    self.a120mc_cam_bri = QSpinBox()
    self.a120mc_cam_bri.setValue(0)
    self.a120mc_cam_bri.setMinimum(-255)
    self.a120mc_cam_bri.setMaximum(255)

    self.a120mc_cam_sat = QDoubleSpinBox()
    self.a120mc_cam_sat.setValue(1.0)
    self.a120mc_cam_sat.setMinimum(0.0)
    self.a120mc_cam_sat.setMaximum(10.0)
    self.a120mc_cam_sat.setSingleStep(0.01)

    self.a120mc_cam_gam = QDoubleSpinBox()
    self.a120mc_cam_gam.setValue(1.0)
    self.a120mc_cam_gam.setMinimum(0.0)
    self.a120mc_cam_gam.setMaximum(10.0)
    self.a120mc_cam_gam.setSingleStep(0.01)

    self.a120mc_cam_inverse = QCheckBox()
    self.a120mc_cam_inverse.setChecked(False)

    self.a120mc_cam_hist_equal = QCheckBox()
    self.a120mc_cam_hist_equal.setChecked(False)

    self.a120mc_cam_normalize = QCheckBox()
    self.a120mc_cam_normalize.setChecked(False)

    self.a120mc_cam_normalize_l = QDoubleSpinBox()
    self.a120mc_cam_normalize_l.setValue(0.0)
    self.a120mc_cam_normalize_l.setMinimum(0.0)
    self.a120mc_cam_normalize_l.setMaximum(100.0)
    self.a120mc_cam_normalize_l.setSingleStep(0.01)

    self.a120mc_cam_normalize_h = QDoubleSpinBox()
    self.a120mc_cam_normalize_h.setMinimum(0.0)
    self.a120mc_cam_normalize_h.setMaximum(100.0)
    self.a120mc_cam_normalize_h.setSingleStep(0.01)
    self.a120mc_cam_normalize_h.setValue(100.0)

    self.a120mc_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a120mc_cam_bri_sat_gam_rst.clicked.connect(self.f_a120mc_cam_bri_sat_gam_rst)

    self.lab_a120mc_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.graphWidget_a120mc = pg.PlotWidget()
    self.hist_color_a120mc = self.palette().color(QtGui.QPalette.Window)
    self.graphWidget_a120mc.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_gray)
    self.graphWidget_a120mc.setBackground(self.hist_color_a120mc)
    self.graphWidget_a120mc.hideAxis('bottom')
    self.graphWidget_a120mc.hideAxis('left')


    layout.addWidget(self.lab_a120mc_cam)
    layout.addWidget(self.lab_a120mc_cam_time_param)
    layout.addWidget(self.lab_a120mc_cam_time_frame)
    layout.addWidget(self.lab_a120mc_cam_time_disp_frame)
    layout.addWidget(self.lab_a120mc_cam_temp)
    layout.addWidget(self.lab_a120mc_rotate)
    layout.addWidget(separator1)
    layout.addWidget(self.a120mc_cam_exp_gain_depl)
    layout.addWidget(separator2)

    cam_a120mc_gain_layout = QHBoxLayout()
    cam_a120mc_gain_layout.addWidget(QLabel("Exposure:"))
    cam_a120mc_gain_layout.addWidget(self.a120mc_cam_exp_slider)
    cam_a120mc_gain_layout.addWidget(QLabel("ms"))
    cam_a120mc_gain_layout.addWidget(QLabel("Gain:"))
    cam_a120mc_gain_layout.addWidget(self.a120mc_cam_gain_slider)
    cam_a120mc_gain_layout.addWidget(QLabel("Offset:"))
    cam_a120mc_gain_layout.addWidget(self.a120mc_cam_offset_slider)
    cam_a120mc_gain_layout.addStretch()
    layout.addLayout(cam_a120mc_gain_layout)

    cam_a120mc_butt_group2 = QHBoxLayout()
    cam_a120mc_butt_group2.addWidget(self.a120mc_cam_reset_settings_button)
    cam_a120mc_butt_group2.addWidget(self.a120mc_photo_reload)
    cam_a120mc_butt_group2.addWidget(self.a120mc_photo_rotate)
    cam_a120mc_butt_group2.addWidget(QLabel("bin:"))
    cam_a120mc_butt_group2.addWidget(self.a120mc_cam_bin)
    cam_a120mc_butt_group2.addStretch()
    layout.addLayout(cam_a120mc_butt_group2)

    cam_a120mc_butt_group3 = QHBoxLayout()
    cam_a120mc_butt_group3.addWidget(QLabel("Cir X"))
    cam_a120mc_butt_group3.addWidget(self.a120mc_cam_circ_x)
    cam_a120mc_butt_group3.addWidget(QLabel("Y"))
    cam_a120mc_butt_group3.addWidget(self.a120mc_cam_circ_y)
    cam_a120mc_butt_group3.addWidget(QLabel("D"))
    cam_a120mc_butt_group3.addWidget(self.a120mc_cam_circ_d)
    cam_a120mc_butt_group3.addWidget(QLabel("C"))
    cam_a120mc_butt_group3.addWidget(self.a120mc_cam_circ_c)
    layout.addLayout(cam_a120mc_butt_group3)

    cam_a120mc_butt_group4 = QHBoxLayout()
    cam_a120mc_butt_group4.addWidget(QLabel("Save to file"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_save_img)
    cam_a120mc_butt_group4.addWidget(QLabel("Dirname"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_save_dirname)
    cam_a120mc_butt_group4.addStretch()
    layout.addLayout(cam_a120mc_butt_group4)

    cam_a120mc_butt_group5 = QHBoxLayout()
    cam_a120mc_butt_group5.addWidget(self.a120mc_b_plate_solve)
    cam_a120mc_butt_group5.addWidget(self.a120mc_b_plate_solve_cancel)
    layout.addLayout(cam_a120mc_butt_group5)
    layout.addWidget(self.lab_a120mc_plate_solve_status)
    layout.addWidget(separator3)

    cam_a120mc_pixel_scale = QHBoxLayout()
    cam_a120mc_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a120mc_pixel_scale.addWidget(self.a120mc_cam_scale_pixel_size)
    cam_a120mc_pixel_scale.addWidget(QLabel("F:"))
    cam_a120mc_pixel_scale.addWidget(self.a120mc_cam_scale_focal)
    cam_a120mc_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a120mc_pixel_scale.addWidget(self.a120mc_cam_scale_pixel_scale)
    layout.addLayout(cam_a120mc_pixel_scale)

    cam_a120mc_pic_adj = QHBoxLayout()
    cam_a120mc_pic_adj.addWidget(QLabel("BRI:"))
    cam_a120mc_pic_adj.addWidget(self.a120mc_cam_bri)
    cam_a120mc_pic_adj.addWidget(QLabel("SAT:"))
    cam_a120mc_pic_adj.addWidget(self.a120mc_cam_sat)
    cam_a120mc_pic_adj.addWidget(QLabel("GAM:"))
    cam_a120mc_pic_adj.addWidget(self.a120mc_cam_gam)
    layout.addLayout(cam_a120mc_pic_adj)

    cam_a120mc_pic_adj2 = QHBoxLayout()
    cam_a120mc_pic_adj2.addWidget(QLabel("INV:"))
    cam_a120mc_pic_adj2.addWidget(self.a120mc_cam_inverse)
    cam_a120mc_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a120mc_pic_adj2.addWidget(self.a120mc_cam_hist_equal)
    cam_a120mc_pic_adj2.addStretch()
    cam_a120mc_pic_adj2.addWidget(self.a120mc_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a120mc_pic_adj2)

    cam_a120mc_pic_adj3 = QHBoxLayout()
    cam_a120mc_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a120mc_pic_adj3.addWidget(self.a120mc_cam_normalize)
    cam_a120mc_pic_adj3.addWidget(QLabel("L:"))
    cam_a120mc_pic_adj3.addWidget(self.a120mc_cam_normalize_l)
    cam_a120mc_pic_adj3.addWidget(QLabel("H:"))
    cam_a120mc_pic_adj3.addWidget(self.a120mc_cam_normalize_h)
    cam_a120mc_pic_adj3.addStretch()
    layout.addLayout(cam_a120mc_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a120mc_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a120mc)

    self.lewy_tab6.setLayout(layout)

#############################################################################################

  def tab7_lewyUI(self):
    global cam_settings
    layout = QVBoxLayout()

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)
    separator6 = QFrame()
    separator6.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.lab_canon = QLabel("CANON 20D")
    self.lab_canon.setFont(self.headline)
    self.lab_canon.setAlignment(Qt.AlignCenter)

    self.lab_canon_time_frame = QLabel("Last frame time: -1s ago")
    self.lab_canon_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_canon_rotate = QLabel("Rotate: null")

    self.canon_exp_slider = QDoubleSpinBox()
    self.canon_exp_slider.setSingleStep(0.5)
    self.canon_exp_slider.setValue(1.0)

    self.canon_iso = QComboBox()
    self.canon_iso.addItems(['100','200','400','800','1600'])
    self.canon_iso.setCurrentIndex(4)
    self.canon_iso.currentIndexChanged.connect(self.f_canon_iso_change)

    self.canon_gain_depl = QLabel("ISO set: X")

    self.canon_make_photo = QPushButton('Make photo', self)
    self.canon_make_photo.clicked.connect(self.f_canon_make_photo)

    self.canon_photo_reload = QPushButton('Reload photo', self)
    self.canon_photo_reload.clicked.connect(self.f_canon_window_refresh)

    self.canon_photo_rotate = QPushButton('Rotate', self)
    self.canon_photo_rotate.clicked.connect(self.f_canon_rotate)

    self.canon_cam_circ_x = QSpinBox()
    self.canon_cam_circ_x.setMinimum(0)
    self.canon_cam_circ_x.setMaximum(1280)
    self.canon_cam_circ_x.setValue(640)

    self.canon_cam_circ_y = QSpinBox()
    self.canon_cam_circ_y.setMinimum(0)
    self.canon_cam_circ_y.setMaximum(960)
    self.canon_cam_circ_y.setValue(480)

    self.canon_cam_circ_d = QSpinBox()
    self.canon_cam_circ_d.setMinimum(0)
    self.canon_cam_circ_d.setMaximum(1200)
    self.canon_cam_circ_d.setValue(0)

    self.canon_cam_circ_c = QSpinBox()
    self.canon_cam_circ_c.setMinimum(0)
    self.canon_cam_circ_c.setMaximum(900)
    self.canon_cam_circ_c.setValue(0)


    self.canon_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.canon_b_plate_solve.clicked.connect(self.f_canon_plate_solve)
    self.canon_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.canon_b_plate_solve_cancel.clicked.connect(self.f_canon_platesolve_stop)
    self.lab_canon_plate_solve_status = QLabel("Plate solve status: NULL")

    self.canon_scale_pixel_size = QDoubleSpinBox()
    self.canon_scale_pixel_size.setMinimum(0.1)
    self.canon_scale_pixel_size.setMaximum(99.0)
    self.canon_scale_pixel_size.setValue(6.4)
    self.canon_scale_pixel_size.valueChanged.connect(self.f_canon_pix_scale_calc)

    self.canon_scale_focal = QSpinBox()
    self.canon_scale_focal.setMinimum(1)
    self.canon_scale_focal.setMaximum(9999)
    self.canon_scale_focal.setValue(1000)
    self.canon_scale_focal.valueChanged.connect(self.f_canon_pix_scale_calc)

    self.canon_scale_pixel_scale = QDoubleSpinBox()
    self.canon_scale_pixel_scale.setMinimum(0.0)
    self.canon_scale_pixel_scale.setMaximum(999.0)
    self.canon_scale_pixel_scale.setValue(1.32)

    self.canon_bri = QSpinBox()
    self.canon_bri.setValue(0)
    self.canon_bri.setMinimum(-255)
    self.canon_bri.setMaximum(255)

    self.canon_sat = QDoubleSpinBox()
    self.canon_sat.setValue(1.0)
    self.canon_sat.setMinimum(0.0)
    self.canon_sat.setMaximum(10.0)
    self.canon_sat.setSingleStep(0.01)

    self.canon_gam = QDoubleSpinBox()
    self.canon_gam.setValue(1.0)
    self.canon_gam.setMinimum(0.0)
    self.canon_gam.setMaximum(10.0)
    self.canon_gam.setSingleStep(0.01)

    self.canon_inverse = QCheckBox()
    self.canon_inverse.setChecked(False)

    self.canon_hist_equal = QCheckBox()
    self.canon_hist_equal.setChecked(False)

    self.canon_cam_normalize = QCheckBox()
    self.canon_cam_normalize.setChecked(False)

    self.canon_cam_normalize_l = QDoubleSpinBox()
    self.canon_cam_normalize_l.setValue(0.0)
    self.canon_cam_normalize_l.setMinimum(0.0)
    self.canon_cam_normalize_l.setMaximum(100.0)
    self.canon_cam_normalize_l.setSingleStep(0.01)

    self.canon_cam_normalize_h = QDoubleSpinBox()
    self.canon_cam_normalize_h.setMinimum(0.0)
    self.canon_cam_normalize_h.setMaximum(100.0)
    self.canon_cam_normalize_h.setSingleStep(0.01)
    self.canon_cam_normalize_h.setValue(100.0)

    self.canon_bri_sat_gam_rst = QPushButton('RST', self)
    self.canon_bri_sat_gam_rst.clicked.connect(self.f_canon_bri_sat_gam_rst)

    self.graphWidget_canon = pg.PlotWidget()
    self.hist_color_canon = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_canon = pg.mkPen(color=(0,0,0))
    self.graphWidget_canon.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_canon)
    self.graphWidget_canon.setBackground(self.hist_color_canon)
    self.graphWidget_canon.hideAxis('bottom')
    self.graphWidget_canon.hideAxis('left')





    layout.addWidget(self.lab_canon)
    layout.addWidget(self.lab_canon_time_frame)
    layout.addWidget(self.lab_canon_time_disp_frame)
    layout.addWidget(self.lab_canon_rotate)
    layout.addWidget(separator1)

    cam_canon_exp_layout = QHBoxLayout()
    cam_canon_exp_layout.addWidget(QLabel("Exposure:"))
    cam_canon_exp_layout.addWidget(self.canon_exp_slider)
    cam_canon_exp_layout.addWidget(QLabel("s"))
    cam_canon_exp_layout.addWidget(QLabel("ISO:"))
    cam_canon_exp_layout.addWidget(self.canon_iso)
    layout.addLayout(cam_canon_exp_layout)
    layout.addWidget(self.canon_gain_depl)
    layout.addWidget(self.canon_make_photo)

    cam_canon_butt_group2 = QHBoxLayout()
    cam_canon_butt_group2.addWidget(self.canon_photo_reload)
    cam_canon_butt_group2.addWidget(self.canon_photo_rotate)
    layout.addLayout(cam_canon_butt_group2)

    cam_canon_butt_group3 = QHBoxLayout()
    cam_canon_butt_group3.addWidget(QLabel("Cir X"))
    cam_canon_butt_group3.addWidget(self.canon_cam_circ_x)
    cam_canon_butt_group3.addWidget(QLabel("Y"))
    cam_canon_butt_group3.addWidget(self.canon_cam_circ_y)
    cam_canon_butt_group3.addWidget(QLabel("D"))
    cam_canon_butt_group3.addWidget(self.canon_cam_circ_d)
    cam_canon_butt_group3.addWidget(QLabel("C"))
    cam_canon_butt_group3.addWidget(self.canon_cam_circ_c)
    layout.addLayout(cam_canon_butt_group3)

    cam_canon_butt_group5 = QHBoxLayout()
    cam_canon_butt_group5.addWidget(self.canon_b_plate_solve)
    cam_canon_butt_group5.addWidget(self.canon_b_plate_solve_cancel)
    layout.addLayout(cam_canon_butt_group5)
    layout.addWidget(self.lab_canon_plate_solve_status)
    layout.addWidget(separator3)

    cam_canon_pixel_scale = QHBoxLayout()
    cam_canon_pixel_scale.addWidget(QLabel("Px size:"))
    cam_canon_pixel_scale.addWidget(self.canon_scale_pixel_size)
    cam_canon_pixel_scale.addWidget(QLabel("F:"))
    cam_canon_pixel_scale.addWidget(self.canon_scale_focal)
    cam_canon_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_canon_pixel_scale.addWidget(self.canon_scale_pixel_scale)
    layout.addLayout(cam_canon_pixel_scale)

    cam_canon_pic_adj = QHBoxLayout()
    cam_canon_pic_adj.addWidget(QLabel("BRI:"))
    cam_canon_pic_adj.addWidget(self.canon_bri)
    cam_canon_pic_adj.addWidget(QLabel("SAT:"))
    cam_canon_pic_adj.addWidget(self.canon_sat)
    cam_canon_pic_adj.addWidget(QLabel("GAM:"))
    cam_canon_pic_adj.addWidget(self.canon_gam)
    layout.addLayout(cam_canon_pic_adj)

    cam_canon_pic_adj2 = QHBoxLayout()
    cam_canon_pic_adj2.addWidget(QLabel("INV:"))
    cam_canon_pic_adj2.addWidget(self.canon_inverse)
    cam_canon_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_canon_pic_adj2.addWidget(self.canon_hist_equal)
    cam_canon_pic_adj2.addStretch()
    cam_canon_pic_adj2.addWidget(self.canon_bri_sat_gam_rst)
    layout.addLayout(cam_canon_pic_adj2)

    cam_canon_pic_adj3 = QHBoxLayout()
    cam_canon_pic_adj3.addWidget(QLabel("NORM:"))
    cam_canon_pic_adj3.addWidget(self.canon_cam_normalize)
    cam_canon_pic_adj3.addWidget(QLabel("L:"))
    cam_canon_pic_adj3.addWidget(self.canon_cam_normalize_l)
    cam_canon_pic_adj3.addWidget(QLabel("H:"))
    cam_canon_pic_adj3.addWidget(self.canon_cam_normalize_h)
    cam_canon_pic_adj3.addStretch()
    layout.addLayout(cam_canon_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.graphWidget_canon)

    self.lewy_tab7.setLayout(layout)

#############################################################################################

  def tab8_lewyUI(self):
    layout = QVBoxLayout()

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.ra_input = QLabel("Set RA w/o move")
    self.ra_input.setFont(self.headline)
    self.ra_input.setAlignment(Qt.AlignCenter)
    self.ra_h = QSpinBox(self)
    self.ra_h.setValue(0)
    self.ra_h.setMinimum(0)
    self.ra_h.setMaximum(24)
    self.ra_m = QSpinBox(self)
    self.ra_m.setValue(0)
    self.ra_m.setMinimum(0)
    self.ra_m.setMaximum(59)
    self.ra_s = QSpinBox(self)
    self.ra_s.setValue(0)
    self.ra_s.setMinimum(0)
    self.ra_s.setMaximum(59)

    self.dec_input = QLabel("Set DEC w/o move")
    self.dec_input.setFont(self.headline)
    self.dec_input.setAlignment(Qt.AlignCenter)
    self.dec_sign3 = QSpinBox(self)
    self.dec_sign3.setValue(1)
    self.dec_sign3.setMinimum(-1)
    self.dec_sign3.setMaximum(1)
    self.dec_d = QSpinBox(self)
    self.dec_d.setValue(0)
    self.dec_d.setMinimum(0)
    self.dec_d.setMaximum(179)
    self.dec_m = QSpinBox(self)
    self.dec_m.setValue(0)
    self.dec_m.setMinimum(0)
    self.dec_m.setMaximum(59)
    self.dec_s = QSpinBox(self)
    self.dec_s.setValue(0)
    self.dec_s.setMinimum(0)
    self.dec_s.setMaximum(59)

    self.radec_button = QPushButton('SET', self)
    self.radec_button.setToolTip('Set telescope to desired position without move')
    self.radec_button.clicked.connect(self.radec_set)

    self.az_input = QLabel("Set Azimuth w/o move")
    self.az_input.setFont(self.headline)
    self.az_input.setAlignment(Qt.AlignCenter)
    self.az_d = QSpinBox(self)
    self.az_d.setValue(0)
    self.az_d.setMinimum(0)
    self.az_d.setMaximum(359)
    self.az_m = QSpinBox(self)
    self.az_m.setValue(0)
    self.az_m.setMinimum(0)
    self.az_m.setMaximum(59)

    self.elev_input = QLabel("Set Elevation w/o move")
    self.elev_input.setFont(self.headline)
    self.elev_input.setAlignment(Qt.AlignCenter)
    self.elev_d = QSpinBox(self)
    self.elev_d.setValue(0)
    self.elev_d.setMinimum(0)
    self.elev_d.setMaximum(89)
    self.elev_m = QSpinBox(self)
    self.elev_m.setValue(0)
    self.elev_m.setMinimum(0)
    self.elev_m.setMaximum(59)

    self.altaz_button = QPushButton('SET', self)
    self.altaz_button.setToolTip('Set telescope to desired position without move')
    self.altaz_button.clicked.connect(self.altaz_set)

    self.pos_skytower = QLabel("Skytower lampa: 171d10m; 6d20m")

    self.solved_tabs_refresh = QPushButton('Reload tabs with solved plate', self)
    self.solved_tabs_refresh.clicked.connect(self.f_solved_tabs_refresh)

    self.act_pos_3 = QLabel("Position of telescope")
    self.act_pos_3.setFont(self.headline)
    self.radec_position = QLabel("00H 00m 00s")
    self.altaz_position = QLabel("00D 00m 00s")

    self.b_restart = QPushButton('RESTART', self)
    self.b_restart.clicked.connect(self.f_restart)

    self.b_reboot_scope = QPushButton('REBOOT', self)
    self.b_reboot_scope.clicked.connect(self.f_reboot_scope)

    self.b_shutdown = QPushButton('SHUTDOWN', self)
    self.b_shutdown.clicked.connect(self.f_shutdown)

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)


    whole_ra_input_layout = QVBoxLayout()
    whole_ra_input_layout.addWidget(self.ra_input)
    ra_input_layout = QHBoxLayout()
    ra_input_layout.addWidget(self.ra_h)
    ra_input_layout.addWidget(QLabel("H"))
    ra_input_layout.addWidget(self.ra_m)
    ra_input_layout.addWidget(QLabel("m"))
    ra_input_layout.addWidget(self.ra_s)
    ra_input_layout.addWidget(QLabel("s"))
    ra_input_layout.addStretch()
    whole_ra_input_layout.addLayout(ra_input_layout)
    layout.addLayout(whole_ra_input_layout)

    whole_dec_input_layout = QVBoxLayout()
    whole_dec_input_layout.addWidget(self.dec_input)
    dec_input_layout = QHBoxLayout()
    dec_input_layout.addWidget(self.dec_sign3)
    dec_input_layout.addWidget(self.dec_d)
    dec_input_layout.addWidget(QLabel("D"))
    dec_input_layout.addWidget(self.dec_m)
    dec_input_layout.addWidget(QLabel("m"))
    dec_input_layout.addWidget(self.dec_s)
    dec_input_layout.addWidget(QLabel("s"))
    dec_input_layout.addStretch()
    whole_dec_input_layout.addLayout(dec_input_layout)
    whole_dec_input_layout.addWidget(self.radec_button)
    layout.addLayout(whole_dec_input_layout)

    layout.addWidget(separator1)

    whole_az_input_layout = QVBoxLayout()
    whole_az_input_layout.addWidget(self.az_input)
    az_input_layout = QHBoxLayout()
    az_input_layout.addWidget(self.az_d)
    az_input_layout.addWidget(QLabel("D"))
    az_input_layout.addWidget(self.az_m)
    az_input_layout.addWidget(QLabel("m"))
    az_input_layout.addStretch()
    whole_az_input_layout.addLayout(az_input_layout)
    layout.addLayout(whole_az_input_layout)

    whole_elev_input_layout = QVBoxLayout()
    whole_elev_input_layout.addWidget(self.elev_input)
    elev_input_layout = QHBoxLayout()
    elev_input_layout.addWidget(self.elev_d)
    elev_input_layout.addWidget(QLabel("D"))
    elev_input_layout.addWidget(self.elev_m)
    elev_input_layout.addWidget(QLabel("m"))
    elev_input_layout.addStretch()
    whole_elev_input_layout.addLayout(elev_input_layout)
    whole_elev_input_layout.addWidget(self.altaz_button)
    layout.addLayout(whole_elev_input_layout)

    layout.addWidget(separator2)
    layout.addWidget(self.pos_skytower)

    layout.addWidget(separator3)
    layout.addWidget(self.act_pos_3, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.radec_position)
    layout.addWidget(self.altaz_position)

    layout.addWidget(separator4)
    layout.addStretch()

    bat_buttons_layout = QHBoxLayout()
    bat_buttons_layout.addWidget(self.b_restart)
    bat_buttons_layout.addWidget(self.b_reboot_scope)
    bat_buttons_layout.addWidget(self.b_shutdown)
    layout.addLayout(bat_buttons_layout)
    layout.addWidget(self.solved_tabs_refresh)

    self.lewy_tab8.setLayout(layout)

#############################################################################################

  def tab9_lewyUI(self):
    layout = QVBoxLayout()

    separator1 = QFrame()
    separator1.setFrameShape(QFrame.HLine)
    separator2 = QFrame()
    separator2.setFrameShape(QFrame.HLine)
    separator3 = QFrame()
    separator3.setFrameShape(QFrame.HLine)
    separator4 = QFrame()
    separator4.setFrameShape(QFrame.HLine)
    separator5 = QFrame()
    separator5.setFrameShape(QFrame.HLine)
    separator6 = QFrame()
    separator6.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.lab_f1 = QLabel("Wheel 1")
    self.filter1 = QComboBox()
    self.filter1.addItems(['NULL'])

    self.lab_f2 = QLabel("Wheel 2")
    self.filter2 = QComboBox()
    self.filter2.addItems(['NULL'])

    self.filter_set = QPushButton('SET', self)
    self.filter_set.clicked.connect(self.f_filter_set)

    self.filter_reset = QPushButton('RESET', self)
    self.filter_reset.clicked.connect(self.f_filter_reset)


    self.filter1_manual_lab = QLabel("Wheel 1")
    self.filter1_manual = QSpinBox()
    self.filter1_manual.setValue(0)
    self.filter1_manual.setMinimum(-96)
    self.filter1_manual.setMaximum(96)
    self.filter1_manual.setSingleStep(12)
    self.filter1_manual_set = QPushButton('MOVE', self)
    self.filter1_manual_set.clicked.connect(self.f_filter1_manual_set)

    self.filter2_manual_lab = QLabel("Wheel 2")
    self.filter2_manual = QSpinBox()
    self.filter2_manual.setValue(0)
    self.filter2_manual.setMinimum(-96)
    self.filter2_manual.setMaximum(96)
    self.filter2_manual.setSingleStep(12)
    self.filter2_manual_set = QPushButton('MOVE', self)
    self.filter2_manual_set.clicked.connect(self.f_filter2_manual_set)


    layout.addWidget(self.lab_f1)
    layout.addWidget(self.filter1)
    layout.addWidget(self.lab_f2)
    layout.addWidget(self.filter2)
    layout.addWidget(self.filter_set)
    layout.addWidget(self.filter_reset)

    filter1_manual_layout = QHBoxLayout()
    filter1_manual_layout.addWidget(self.filter1_manual_lab)
    filter1_manual_layout.addWidget(self.filter1_manual)
    filter1_manual_layout.addWidget(self.filter1_manual_set)
    layout.addLayout(filter1_manual_layout)

    filter2_manual_layout = QHBoxLayout()
    filter2_manual_layout.addWidget(self.filter2_manual_lab)
    filter2_manual_layout.addWidget(self.filter2_manual)
    filter2_manual_layout.addWidget(self.filter2_manual_set)
    layout.addLayout(filter2_manual_layout)

    layout.addStretch()
    self.lewy_tab9.setLayout(layout)

#############################################################################################

  def tab_1_prawyUI(self):
    global viewer_a183mm_deployed
    layout = QVBoxLayout()
    self.viewer_a183mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a183mm)
    self.prawy_tab1.setLayout(layout)
    viewer_a183mm_deployed = True

#############################################################################################

  def tab_2_prawyUI(self):
    global viewer_a533mc_deployed
    layout = QVBoxLayout()
    self.viewer_a533mc = PhotoViewer(self)
    layout.addWidget(self.viewer_a533mc)
    self.prawy_tab2.setLayout(layout)
    viewer_a533mc_deployed = True

#############################################################################################

  def tab_3_prawyUI(self):
    global viewer_a462mc_deployed
    layout = QVBoxLayout()
    self.viewer_a462mc = PhotoViewer(self)
    layout.addWidget(self.viewer_a462mc)
    self.prawy_tab3.setLayout(layout)
    viewer_a462mc_deployed = True

#############################################################################################

  def tab_4_prawyUI(self):
    global viewer_a120mm_deployed
    layout = QVBoxLayout()
    self.viewer_a120mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a120mm)
    self.prawy_tab4.setLayout(layout)
    viewer_a120mm_deployed = True

#############################################################################################

  def tab_5_prawyUI(self):
    global viewer_a120mc_deployed
    layout = QVBoxLayout()
    self.viewer_a120mc = PhotoViewer(self)
    layout.addWidget(self.viewer_a120mc)
    self.prawy_tab5.setLayout(layout)
    viewer_a120mc_deployed = True

#############################################################################################

  def tab_6_prawyUI(self):
    global viewer_canon_deployed
    layout = QVBoxLayout()
    self.viewer_canon = PhotoViewer(self)
    layout.addWidget(self.viewer_canon)
    self.prawy_tab6.setLayout(layout)
    viewer_canon_deployed = True

#############################################################################################

  def tab_7_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_tycho2 = PhotoViewer(self)
    layout.addWidget(self.viewer_tycho2)
    self.prawy_tab7.setLayout(layout)

#############################################################################################

  def tab_8_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_hd = PhotoViewer(self)
    layout.addWidget(self.viewer_hd)
    self.prawy_tab8.setLayout(layout)

#############################################################################################

  def tab_9_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_skymap = QWebEngineView()
    layout.addWidget(self.viewer_skymap)
    self.prawy_tab9.setLayout(layout)

#############################################################################################

  def f_a120mc_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a120mc_platesolve/frame.axy'])

  def f_a120mm_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a120mm_platesolve/frame.axy'])

  def f_a183mm_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a183mm_platesolve/frame.axy'])

  def f_a533mc_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a533mc_platesolve/frame.axy'])

  def f_a462mc_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a462mc_platesolve/frame.axy'])

  def f_canon_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/canon_platesolve/frame.axy'])

  def f_filter1_manual_set(self):
    val = self.filter1_manual.value()
    try:
      out = requests.get('http://eq3.embedded/manual/gora/' + str(val), timeout=3)
    except:
      pass

  def f_filter2_manual_set(self):
    val = self.filter2_manual.value()
    try:
      out = requests.get('http://eq3.embedded/manual/dol/' + str(val), timeout=3)
    except:
      pass

  def f_filter_set(self):
    f1 = self.filter1.currentText()
    f2 = self.filter2.currentText()
    try:
      out = requests.get('http://eq3.embedded/set/gora/' + f1, timeout=3)
    except:
      self.filter1.clear()
      self.filter1.addItem('ERR')
      pass
    try:
      out = requests.get('http://eq3.embedded/set/dol/' + f2, timeout=3)
    except:
      self.filter2.clear()
      self.filter2.addItem('ERR')
      pass

  def f_filter_reset(self, automatic = False):
    global filter_reset_done

    if not automatic or (not filter_reset_done and automatic):
      filter_reset_done = True
      try:
        out = requests.get('http://eq3.embedded/state', timeout=3)
        if out.status_code == 200:
          state = json.loads(out.text)
          self.filter1.clear()
          self.filter2.clear()
          for i in state['filtry']['gora']:
            self.filter1.addItem(i)
          for i in state['filtry']['dol']:
            self.filter2.addItem(i)
          self.filter1.setCurrentIndex(state['state']['gora'])
          self.filter2.setCurrentIndex(state['state']['dol'])
      except:
        self.filter1.clear()
        self.filter2.clear()
        self.filter1.addItem('ERR')
        self.filter2.addItem('ERR')
        pass

  def f_canon_make_photo(self):
    global req_canon
    val = self.canon_exp_slider.value()
    req_canon.put('http://127.0.0.1:8003/frame/' + str(val))

  def f_a183mm_cam_bri_sat_gam_rst(self):
    self.a183mm_cam_bri.setValue(0)
    self.a183mm_cam_sat.setValue(1.0)
    self.a183mm_cam_gam.setValue(1.0)
    self.a183mm_cam_inverse.setChecked(False)
    self.a183mm_cam_hist_equal.setChecked(False)
    self.a183mm_cam_normalize.setChecked(False)
    self.a183mm_cam_normalize_l.setValue(0.0)
    self.a183mm_cam_normalize_h.setValue(100.0)

  def f_a183mm_cam_pix_scale_calc(self,val):
    self.a183mm_cam_scale_pixel_scale.setValue(float(float(self.a183mm_cam_scale_pixel_size.value()) * 206.265 / float(self.a183mm_cam_scale_focal.value())))

  def f_a533mc_cam_bri_sat_gam_rst(self):
    self.a533mc_cam_bri.setValue(0)
    self.a533mc_cam_sat.setValue(1.0)
    self.a533mc_cam_gam.setValue(1.0)
    self.a533mc_cam_inverse.setChecked(False)
    self.a533mc_cam_hist_equal.setChecked(False)
    self.a533mc_cam_normalize.setChecked(False)
    self.a533mc_cam_normalize_l.setValue(0.0)
    self.a533mc_cam_normalize_h.setValue(100.0)

  def f_a533mc_cam_pix_scale_calc(self,val):
    self.a533mc_cam_scale_pixel_scale.setValue(float(float(self.a533mc_cam_scale_pixel_size.value()) * 206.265 / float(self.a533mc_cam_scale_focal.value())))

  def f_a462mc_cam_bri_sat_gam_rst(self):
    self.a462mc_cam_bri.setValue(0)
    self.a462mc_cam_sat.setValue(1.0)
    self.a462mc_cam_gam.setValue(1.0)
    self.a462mc_cam_inverse.setChecked(False)
    self.a462mc_cam_hist_equal.setChecked(False)
    self.a462mc_cam_normalize.setChecked(False)
    self.a462mc_cam_normalize_l.setValue(0.0)
    self.a462mc_cam_normalize_h.setValue(100.0)

  def f_a462mc_cam_pix_scale_calc(self,val):
    self.a462mc_cam_scale_pixel_scale.setValue(float(float(self.a462mc_cam_scale_pixel_size.value()) * 206.265 / float(self.a462mc_cam_scale_focal.value())))

  def f_a120mc_cam_bri_sat_gam_rst(self):
    self.a120mc_cam_bri.setValue(0)
    self.a120mc_cam_sat.setValue(1.0)
    self.a120mc_cam_gam.setValue(1.0)
    self.a120mc_cam_inverse.setChecked(False)
    self.a120mc_cam_hist_equal.setChecked(False)
    self.a120mc_cam_normalize.setChecked(False)
    self.a120mc_cam_normalize_l.setValue(0.0)
    self.a120mc_cam_normalize_h.setValue(100.0)

  def f_a120mm_cam_bri_sat_gam_rst(self):
    self.a120mm_cam_bri.setValue(0)
    self.a120mm_cam_sat.setValue(1.0)
    self.a120mm_cam_gam.setValue(1.0)
    self.a120mm_cam_inverse.setChecked(False)
    self.a120mm_cam_hist_equal.setChecked(False)
    self.a120mm_cam_normalize.setChecked(False)
    self.a120mm_cam_normalize_l.setValue(0.0)
    self.a120mm_cam_normalize_h.setValue(100.0)

  def f_canon_bri_sat_gam_rst(self):
    self.canon_bri.setValue(0)
    self.canon_sat.setValue(1.0)
    self.canon_gam.setValue(1.0)
    self.canon_inverse.setChecked(False)
    self.canon_hist_equal.setChecked(False)
    self.canon_cam_normalize.setChecked(False)
    self.canon_cam_normalize_l.setValue(0.0)
    self.canon_cam_normalize_h.setValue(100.0)

  def f_a120mc_cam_pix_scale_calc(self,val):
    self.a120mc_cam_scale_pixel_scale.setValue(float(float(self.a120mc_cam_scale_pixel_size.value()) * 206.265 / float(self.a120mc_cam_scale_focal.value())))

  def f_a120mm_cam_pix_scale_calc(self,val):
    self.a120mm_cam_scale_pixel_scale.setValue(float(float(self.a120mm_cam_scale_pixel_size.value()) * 206.265 / float(self.a120mm_cam_scale_focal.value())))

  def f_canon_pix_scale_calc(self,val):
    self.canon_scale_pixel_scale.setValue(float(float(self.canon_scale_pixel_size.value()) * 206.265 / float(self.canon_scale_focal.value())))

  def f_a183mm_cam_pix_scale_calc(self,val):
    self.a183mm_cam_scale_pixel_scale.setValue(float(float(self.a183mm_cam_scale_pixel_size.value()) * 206.265 / float(self.a183mm_cam_scale_focal.value())))

  def f_a533mc_cam_pix_scale_calc(self,val):
    self.a533mc_cam_scale_pixel_scale.setValue(float(float(self.a533mc_cam_scale_pixel_size.value()) * 206.265 / float(self.a533mc_cam_scale_focal.value())))

  def f_a462mc_cam_pix_scale_calc(self,val):
    self.a462mc_cam_scale_pixel_scale.setValue(float(float(self.a462mc_cam_scale_pixel_size.value()) * 206.265 / float(self.a462mc_cam_scale_focal.value())))

  def f_a120mc_plate_solve(self):
    global run_plate_solve_a120mc
    run_plate_solve_a120mc = True

  def f_a120mm_plate_solve(self):
    global run_plate_solve_a120mm
    run_plate_solve_a120mm = True

  def f_canon_plate_solve(self):
    global run_plate_solve_canon
    run_plate_solve_canon = True

  def f_a183mm_plate_solve(self):
    global run_plate_solve_a183mm
    run_plate_solve_a183mm = True

  def f_a183mm_cam_update_values(self, load_slider = False):
    global cam_settings

    curr_time = time.time()
    if 'param_time' in cam_settings['a183mm']:
      self.lab_a183mm_cam_time_param.setText("Last param set: " + str(format(curr_time - cam_settings['a183mm']['param_time'], '.1f')) + "s ago")
    else:
      self.lab_a183mm_cam_time_param.setText("Last param set: NULL")
    if 'frame_time' in cam_settings['a183mm']:
      self.lab_a183mm_cam_time_frame.setText("Last frame time: " + str(format(curr_time - cam_settings['a183mm']['frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a183mm_cam_time_frame.setText("Last frame time: NULL")
    if 'disp_frame_time' in cam_settings['a183mm']:
      self.lab_a183mm_cam_time_disp_frame.setText("Displayed frame made: " + str(format(curr_time - cam_settings['a183mm']['disp_frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a183mm_cam_time_disp_frame.setText("Displayed frame made: NULL")
    if 'info' in cam_settings['a183mm'] and 'temperature' in cam_settings['a183mm']['info']:
      self.lab_a183mm_cam_temp.setText("Sensor temp: " + str(cam_settings['a183mm']['info']['temperature']) + " Celsius")
    else:
      self.lab_a183mm_cam_temp.setText("Sensor temp: NULL")
    if 'Exposure' in cam_settings['a183mm'] and 'Gain' in cam_settings['a183mm']:
      self.a183mm_cam_exp_gain_depl.setText("Exp: " + str(cam_settings['a183mm']['Exposure']['depl']/1000) + " ms; Gain: " + str(cam_settings['a183mm']['Gain']['depl']) + " pt; Offset: " + str(cam_settings['a183mm']['Offset']['depl']))
    else:
      self.a183mm_cam_exp_gain_depl.setText("Exp: NULL")
    if 'rotate' in cam_settings['a183mm'] and 'HardwareBin' in cam_settings['a183mm']:
      self.lab_a183mm_rotate.setText("Rotate: " + str(cam_settings['a183mm']['rotate']) + "; Bin: " + str(cam_settings['a183mm']['HardwareBin']['depl']))
    else:
      self.lab_a183mm_rotate.setText("Rotate: NULL")
    if 'CoolerOn' in cam_settings['a183mm'] and 'info' in cam_settings['a183mm'] and 'cooler_pwr' in cam_settings['a183mm']['info']:
      self.lab_a183mm_cooling.setText("Cooler on: " + str(cam_settings['a183mm']['CoolerOn']['Value']) + "; PWR: " + str(cam_settings['a183mm']['info']['cooler_pwr']) )
    else:
      self.lab_a183mm_cooling.setText("Cooling: NULL")

    if load_slider:
      if 'Exposure' in cam_settings['a183mm']:
        self.a183mm_cam_exp_slider.setMinimum(cam_settings['a183mm']['Exposure']['MinValue']/1000)
        self.a183mm_cam_exp_slider.setMaximum(cam_settings['a183mm']['Exposure']['MaxValue']/1000)
        self.a183mm_cam_exp_slider.setValue(cam_settings['a183mm']['Exposure']['Value']/1000)
      else:
        self.a183mm_cam_exp_slider.setMinimum(0)
        self.a183mm_cam_exp_slider.setMaximum(0)
        self.a183mm_cam_exp_slider.setValue(0)
      if 'Gain' in cam_settings['a183mm']:
        self.a183mm_cam_gain_slider.setMinimum(cam_settings['a183mm']['Gain']['MinValue'])
        self.a183mm_cam_gain_slider.setMaximum(cam_settings['a183mm']['Gain']['MaxValue'])
        self.a183mm_cam_gain_slider.setValue(cam_settings['a183mm']['Gain']['Value'])
      else:
        self.a183mm_cam_gain_slider.setMinimum(0)
        self.a183mm_cam_gain_slider.setMaximum(0)
        self.a183mm_cam_gain_slider.setValue(0)
      if 'Offset' in cam_settings['a183mm']:
        self.a183mm_cam_offset_slider.setMinimum(cam_settings['a183mm']['Offset']['MinValue'])
        self.a183mm_cam_offset_slider.setMaximum(cam_settings['a183mm']['Offset']['MaxValue'])
        self.a183mm_cam_offset_slider.setValue(cam_settings['a183mm']['Offset']['Value'])
      else:
        self.a183mm_cam_offset_slider.setMinimum(0)
        self.a183mm_cam_offset_slider.setMaximum(0)
        self.a183mm_cam_offset_slider.setValue(0)
      if 'TargetTemp' in cam_settings['a183mm']:
        self.a183mm_cam_target_temp_slider.setMinimum(cam_settings['a183mm']['TargetTemp']['MinValue'])
        self.a183mm_cam_target_temp_slider.setMaximum(cam_settings['a183mm']['TargetTemp']['MaxValue'])
        self.a183mm_cam_target_temp_slider.setValue(cam_settings['a183mm']['TargetTemp']['Value'])
      else:
        self.a183mm_cam_target_temp_slider.setMinimum(0)
        self.a183mm_cam_target_temp_slider.setMaximum(0)
        self.a183mm_cam_target_temp_slider.setValue(0)
      if 'CoolerOn' in cam_settings['a183mm']:
        if cam_settings['a183mm']['CoolerOn']['Value'] == 0:
          self.a183mm_cam_cooler.setChecked(False)
        else:
          self.a183mm_cam_cooler.setChecked(True)
      if 'HardwareBin' in cam_settings['a183mm']:
        self.a183mm_cam_bin.clear()
        for i in range(cam_settings['a183mm']['HardwareBin']['MinValue'], cam_settings['a183mm']['HardwareBin']['MaxValue']+1):
          self.a183mm_cam_bin.addItem(str(i))
        self.a183mm_cam_bin.setCurrentIndex(0)
      else:
        self.a183mm_cam_bin.clear()
        self.a183mm_cam_bin.addItem('NULL')
        self.a183mm_cam_bin.setCurrentIndex(0)

  def f_a533mc_plate_solve(self):
    global run_plate_solve_a533mc
    run_plate_solve_a533mc = True

  def f_a533mc_cam_update_values(self, load_slider = False):
    global cam_settings

    curr_time = time.time()
    if 'param_time' in cam_settings['a533mc']:
      self.lab_a533mc_cam_time_param.setText("Last param set: " + str(format(curr_time - cam_settings['a533mc']['param_time'], '.1f')) + "s ago")
    else:
      self.lab_a533mc_cam_time_param.setText("Last param set: NULL")
    if 'frame_time' in cam_settings['a533mc']:
      self.lab_a533mc_cam_time_frame.setText("Last frame time: " + str(format(curr_time - cam_settings['a533mc']['frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a533mc_cam_time_frame.setText("Last frame time: NULL")
    if 'disp_frame_time' in cam_settings['a533mc']:
      self.lab_a533mc_cam_time_disp_frame.setText("Displayed frame made: " + str(format(curr_time - cam_settings['a533mc']['disp_frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a533mc_cam_time_disp_frame.setText("Displayed frame made: NULL")
    if 'info' in cam_settings['a533mc'] and 'temperature' in cam_settings['a533mc']['info']:
      self.lab_a533mc_cam_temp.setText("Sensor temp: " + str(cam_settings['a533mc']['info']['temperature']) + " Celsius")
    else:
      self.lab_a533mc_cam_temp.setText("Sensor temp: NULL")
    if 'Exposure' in cam_settings['a533mc'] and 'Gain' in cam_settings['a533mc']:
      self.a533mc_cam_exp_gain_depl.setText("Exp: " + str(cam_settings['a533mc']['Exposure']['depl']/1000) + " ms; Gain: " + str(cam_settings['a533mc']['Gain']['depl']) + " pt; Offset: " + str(cam_settings['a533mc']['Offset']['depl']))
    else:
      self.a533mc_cam_exp_gain_depl.setText("Exp: NULL")
    if 'rotate' in cam_settings['a533mc'] and 'HardwareBin' in cam_settings['a533mc']:
      self.lab_a533mc_rotate.setText("Rotate: " + str(cam_settings['a533mc']['rotate']) + "; Bin: " + str(cam_settings['a533mc']['HardwareBin']['depl']))
    else:
      self.lab_a533mc_rotate.setText("Rotate: NULL")
    if 'CoolerOn' in cam_settings['a533mc'] and 'info' in cam_settings['a533mc'] and 'cooler_pwr' in cam_settings['a533mc']['info']:
      self.lab_a533mc_cooling.setText("Cooler on: " + str(cam_settings['a533mc']['CoolerOn']['Value']) + "; PWR: " + str(cam_settings['a533mc']['info']['cooler_pwr']) )
    else:
      self.lab_a533mc_cooling.setText("Cooling: NULL")

    if load_slider:
      if 'Exposure' in cam_settings['a533mc']:
        self.a533mc_cam_exp_slider.setMinimum(cam_settings['a533mc']['Exposure']['MinValue']/1000)
        self.a533mc_cam_exp_slider.setMaximum(cam_settings['a533mc']['Exposure']['MaxValue']/1000)
        self.a533mc_cam_exp_slider.setValue(cam_settings['a533mc']['Exposure']['Value']/1000)
      else:
        self.a533mc_cam_exp_slider.setMinimum(0)
        self.a533mc_cam_exp_slider.setMaximum(0)
        self.a533mc_cam_exp_slider.setValue(0)
      if 'Gain' in cam_settings['a533mc']:
        self.a533mc_cam_gain_slider.setMinimum(cam_settings['a533mc']['Gain']['MinValue'])
        self.a533mc_cam_gain_slider.setMaximum(cam_settings['a533mc']['Gain']['MaxValue'])
        self.a533mc_cam_gain_slider.setValue(cam_settings['a533mc']['Gain']['Value'])
      else:
        self.a533mc_cam_gain_slider.setMinimum(0)
        self.a533mc_cam_gain_slider.setMaximum(0)
        self.a533mc_cam_gain_slider.setValue(0)
      if 'Offset' in cam_settings['a533mc']:
        self.a533mc_cam_offset_slider.setMinimum(cam_settings['a533mc']['Offset']['MinValue'])
        self.a533mc_cam_offset_slider.setMaximum(cam_settings['a533mc']['Offset']['MaxValue'])
        self.a533mc_cam_offset_slider.setValue(cam_settings['a533mc']['Offset']['Value'])
      else:
        self.a533mc_cam_offset_slider.setMinimum(0)
        self.a533mc_cam_offset_slider.setMaximum(0)
        self.a533mc_cam_offset_slider.setValue(0)
      if 'TargetTemp' in cam_settings['a533mc']:
        self.a533mc_cam_target_temp_slider.setMinimum(cam_settings['a533mc']['TargetTemp']['MinValue'])
        self.a533mc_cam_target_temp_slider.setMaximum(cam_settings['a533mc']['TargetTemp']['MaxValue'])
        self.a533mc_cam_target_temp_slider.setValue(cam_settings['a533mc']['TargetTemp']['Value'])
      else:
        self.a533mc_cam_target_temp_slider.setMinimum(0)
        self.a533mc_cam_target_temp_slider.setMaximum(0)
        self.a533mc_cam_target_temp_slider.setValue(0)
      if 'CoolerOn' in cam_settings['a533mc']:
        if cam_settings['a533mc']['CoolerOn']['Value'] == 0:
          self.a533mc_cam_cooler.setChecked(False)
        else:
          self.a533mc_cam_cooler.setChecked(True)
      if 'HardwareBin' in cam_settings['a533mc']:
        self.a533mc_cam_bin.clear()
        for i in range(cam_settings['a533mc']['HardwareBin']['MinValue'], cam_settings['a533mc']['HardwareBin']['MaxValue']+1):
          self.a533mc_cam_bin.addItem(str(i))
        self.a533mc_cam_bin.setCurrentIndex(0)
      else:
        self.a533mc_cam_bin.clear()
        self.a533mc_cam_bin.addItem('NULL')
        self.a533mc_cam_bin.setCurrentIndex(0)

  def f_a462mc_plate_solve(self):
    global run_plate_solve_a462mc
    run_plate_solve_a462mc = True

  def f_a462mc_cam_update_values(self, load_slider = False):
    global cam_settings

    curr_time = time.time()
    if 'param_time' in cam_settings['a462mc']:
      self.lab_a462mc_cam_time_param.setText("Last param set: " + str(format(curr_time - cam_settings['a462mc']['param_time'], '.1f')) + "s ago")
    else:
      self.lab_a462mc_cam_time_param.setText("Last param set: NULL")
    if 'frame_time' in cam_settings['a462mc']:
      self.lab_a462mc_cam_time_frame.setText("Last frame time: " + str(format(curr_time - cam_settings['a462mc']['frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a462mc_cam_time_frame.setText("Last frame time: NULL")
    if 'disp_frame_time' in cam_settings['a462mc']:
      self.lab_a462mc_cam_time_disp_frame.setText("Displayed frame made: " + str(format(curr_time - cam_settings['a462mc']['disp_frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a462mc_cam_time_disp_frame.setText("Displayed frame made: NULL")
    if 'info' in cam_settings['a462mc'] and 'temperature' in cam_settings['a462mc']['info']:
      self.lab_a462mc_cam_temp.setText("Sensor temp: " + str(cam_settings['a462mc']['info']['temperature']) + " Celsius")
    else:
      self.lab_a462mc_cam_temp.setText("Sensor temp: NULL")
    if 'Exposure' in cam_settings['a462mc'] and 'Gain' in cam_settings['a462mc']:
      self.a462mc_cam_exp_gain_depl.setText("Exp: " + str(cam_settings['a462mc']['Exposure']['depl']/1000) + " ms; Gain: " + str(cam_settings['a462mc']['Gain']['depl']) + " pt; Offset: " + str(cam_settings['a462mc']['Offset']['depl']))
    else:
      self.a462mc_cam_exp_gain_depl.setText("Exp: NULL")
    if 'rotate' in cam_settings['a462mc'] and 'HardwareBin' in cam_settings['a462mc']:
      self.lab_a462mc_rotate.setText("Rotate: " + str(cam_settings['a462mc']['rotate']) + "; Bin: " + str(cam_settings['a462mc']['HardwareBin']['depl']))
    else:
      self.lab_a462mc_rotate.setText("Rotate: NULL")

    if load_slider:
      if 'Exposure' in cam_settings['a462mc']:
        self.a462mc_cam_exp_slider.setMinimum(cam_settings['a462mc']['Exposure']['MinValue']/1000)
        self.a462mc_cam_exp_slider.setMaximum(cam_settings['a462mc']['Exposure']['MaxValue']/1000)
        self.a462mc_cam_exp_slider.setValue(cam_settings['a462mc']['Exposure']['Value']/1000)
      else:
        self.a462mc_cam_exp_slider.setMinimum(0)
        self.a462mc_cam_exp_slider.setMaximum(0)
        self.a462mc_cam_exp_slider.setValue(0)
      if 'Gain' in cam_settings['a462mc']:
        self.a462mc_cam_gain_slider.setMinimum(cam_settings['a462mc']['Gain']['MinValue'])
        self.a462mc_cam_gain_slider.setMaximum(cam_settings['a462mc']['Gain']['MaxValue'])
        self.a462mc_cam_gain_slider.setValue(cam_settings['a462mc']['Gain']['Value'])
      else:
        self.a462mc_cam_gain_slider.setMinimum(0)
        self.a462mc_cam_gain_slider.setMaximum(0)
        self.a462mc_cam_gain_slider.setValue(0)
      if 'Offset' in cam_settings['a462mc']:
        self.a462mc_cam_offset_slider.setMinimum(cam_settings['a462mc']['Offset']['MinValue'])
        self.a462mc_cam_offset_slider.setMaximum(cam_settings['a462mc']['Offset']['MaxValue'])
        self.a462mc_cam_offset_slider.setValue(cam_settings['a462mc']['Offset']['Value'])
      else:
        self.a462mc_cam_offset_slider.setMinimum(0)
        self.a462mc_cam_offset_slider.setMaximum(0)
        self.a462mc_cam_offset_slider.setValue(0)
      if 'HardwareBin' in cam_settings['a462mc']:
        self.a462mc_cam_bin.clear()
        for i in range(cam_settings['a462mc']['HardwareBin']['MinValue'], cam_settings['a462mc']['HardwareBin']['MaxValue']+1):
          self.a462mc_cam_bin.addItem(str(i))
        self.a462mc_cam_bin.setCurrentIndex(0)
      else:
        self.a462mc_cam_bin.clear()
        self.a462mc_cam_bin.addItem('NULL')
        self.a462mc_cam_bin.setCurrentIndex(0)

  def f_a120mc_cam_update_values(self, load_slider = False):
    global cam_settings

    curr_time = time.time()
    if 'param_time' in cam_settings['a120mc']:
      self.lab_a120mc_cam_time_param.setText("Last param set: " + str(format(curr_time - cam_settings['a120mc']['param_time'], '.1f')) + "s ago")
    else:
      self.lab_a120mc_cam_time_param.setText("Last param set: NULL")
    if 'frame_time' in cam_settings['a120mc']:
      self.lab_a120mc_cam_time_frame.setText("Last frame time: " + str(format(curr_time - cam_settings['a120mc']['frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a120mc_cam_time_frame.setText("Last frame time: NULL")
    if 'disp_frame_time' in cam_settings['a120mc']:
      self.lab_a120mc_cam_time_disp_frame.setText("Displayed frame made: " + str(format(curr_time - cam_settings['a120mc']['disp_frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a120mc_cam_time_disp_frame.setText("Displayed frame made: NULL")
    if 'info' in cam_settings['a120mc'] and 'temperature' in cam_settings['a120mc']['info']:
      self.lab_a120mc_cam_temp.setText("Sensor temp: " + str(cam_settings['a120mc']['info']['temperature']) + " Celsius")
    else:
      self.lab_a120mc_cam_temp.setText("Sensor temp: NULL")
    if 'Exposure' in cam_settings['a120mc'] and 'Gain' in cam_settings['a120mc']:
      self.a120mc_cam_exp_gain_depl.setText("Exp: " + str(cam_settings['a120mc']['Exposure']['depl']/1000) + " ms; Gain: " + str(cam_settings['a120mc']['Gain']['depl']) + " pt; Offset: " + str(cam_settings['a120mc']['Offset']['depl']))
    else:
      self.a120mc_cam_exp_gain_depl.setText("Exp: NULL")
    if 'rotate' in cam_settings['a120mc'] and 'HardwareBin' in cam_settings['a120mc']:
      self.lab_a120mc_rotate.setText("Rotate: " + str(cam_settings['a120mc']['rotate']) + "; Bin: " + str(cam_settings['a120mc']['HardwareBin']['depl']))
    else:
      self.lab_a120mc_rotate.setText("Rotate: NULL")

    if load_slider:
      if 'Exposure' in cam_settings['a120mc']:
        self.a120mc_cam_exp_slider.setMinimum(cam_settings['a120mc']['Exposure']['MinValue']/1000)
        self.a120mc_cam_exp_slider.setMaximum(cam_settings['a120mc']['Exposure']['MaxValue']/1000)
        self.a120mc_cam_exp_slider.setValue(cam_settings['a120mc']['Exposure']['Value']/1000)
      else:
        self.a120mc_cam_exp_slider.setMinimum(0)
        self.a120mc_cam_exp_slider.setMaximum(0)
        self.a120mc_cam_exp_slider.setValue(0)
      if 'Gain' in cam_settings['a120mc']:
        self.a120mc_cam_gain_slider.setMinimum(cam_settings['a120mc']['Gain']['MinValue'])
        self.a120mc_cam_gain_slider.setMaximum(cam_settings['a120mc']['Gain']['MaxValue'])
        self.a120mc_cam_gain_slider.setValue(cam_settings['a120mc']['Gain']['Value'])
      else:
        self.a120mc_cam_gain_slider.setMinimum(0)
        self.a120mc_cam_gain_slider.setMaximum(0)
        self.a120mc_cam_gain_slider.setValue(0)
      if 'Offset' in cam_settings['a120mc']:
        self.a120mc_cam_offset_slider.setMinimum(cam_settings['a120mc']['Offset']['MinValue'])
        self.a120mc_cam_offset_slider.setMaximum(cam_settings['a120mc']['Offset']['MaxValue'])
        self.a120mc_cam_offset_slider.setValue(cam_settings['a120mc']['Offset']['Value'])
      else:
        self.a120mc_cam_offset_slider.setMinimum(0)
        self.a120mc_cam_offset_slider.setMaximum(0)
        self.a120mc_cam_offset_slider.setValue(0)
      if 'HardwareBin' in cam_settings['a120mc']:
        self.a120mc_cam_bin.clear()
        for i in range(cam_settings['a120mc']['HardwareBin']['MinValue'], cam_settings['a120mc']['HardwareBin']['MaxValue']+1):
          self.a120mc_cam_bin.addItem(str(i))
        self.a120mc_cam_bin.setCurrentIndex(0)
      else:
        self.a120mc_cam_bin.clear()
        self.a120mc_cam_bin.addItem('NULL')
        self.a120mc_cam_bin.setCurrentIndex(0)

  def f_a120mm_cam_update_values(self, load_slider = False):
    global cam_settings

    curr_time = time.time()
    if 'param_time' in cam_settings['a120mm']:
      self.lab_a120mm_cam_time_param.setText("Last param set: " + str(format(curr_time - cam_settings['a120mm']['param_time'], '.1f')) + "s ago")
    else:
      self.lab_a120mm_cam_time_param.setText("Last param set: NULL")
    if 'frame_time' in cam_settings['a120mm']:
      self.lab_a120mm_cam_time_frame.setText("Last frame time: " + str(format(curr_time - cam_settings['a120mm']['frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a120mm_cam_time_frame.setText("Last frame time: NULL")
    if 'disp_frame_time' in cam_settings['a120mm']:
      self.lab_a120mm_cam_time_disp_frame.setText("Displayed frame made: " + str(format(curr_time - cam_settings['a120mm']['disp_frame_time'], '.1f')) + "s ago")
    else:
      self.lab_a120mm_cam_time_disp_frame.setText("Displayed frame made: NULL")
    if 'info' in cam_settings['a120mm'] and 'temperature' in cam_settings['a120mm']['info']:
      self.lab_a120mm_cam_temp.setText("Sensor temp: " + str(cam_settings['a120mm']['info']['temperature']) + " Celsius")
    else:
      self.lab_a120mm_cam_temp.setText("Sensor temp: NULL")
    if 'Exposure' in cam_settings['a120mm'] and 'Gain' in cam_settings['a120mm']:
      self.a120mm_cam_exp_gain_depl.setText("Exp: " + str(cam_settings['a120mm']['Exposure']['depl']/1000) + " ms; Gain: " + str(cam_settings['a120mm']['Gain']['depl']) + " pt; Offset: " + str(cam_settings['a120mm']['Offset']['depl']))
    else:
      self.a120mm_cam_exp_gain_depl.setText("Exp: NULL")
    if 'rotate' in cam_settings['a120mm'] and 'HardwareBin' in cam_settings['a120mm']:
      self.lab_a120mm_rotate.setText("Rotate: " + str(cam_settings['a120mm']['rotate']) + "; Bin: " + str(cam_settings['a120mm']['HardwareBin']['depl']))
    else:
      self.lab_a120mm_rotate.setText("Rotate: NULL")

    if load_slider:
      if 'Exposure' in cam_settings['a120mm']:
        self.a120mm_cam_exp_slider.setMinimum(cam_settings['a120mm']['Exposure']['MinValue']/1000)
        self.a120mm_cam_exp_slider.setMaximum(cam_settings['a120mm']['Exposure']['MaxValue']/1000)
        self.a120mm_cam_exp_slider.setValue(cam_settings['a120mm']['Exposure']['Value']/1000)
      else:
        self.a120mm_cam_exp_slider.setMinimum(0)
        self.a120mm_cam_exp_slider.setMaximum(0)
        self.a120mm_cam_exp_slider.setValue(0)
      if 'Offset' in cam_settings['a120mm']:
        self.a120mm_cam_offset_slider.setMinimum(cam_settings['a120mm']['Offset']['MinValue'])
        self.a120mm_cam_offset_slider.setMaximum(cam_settings['a120mm']['Offset']['MaxValue'])
        self.a120mm_cam_offset_slider.setValue(cam_settings['a120mm']['Offset']['Value'])
      else:
        self.a120mm_cam_offset_slider.setMinimum(0)
        self.a120mm_cam_offset_slider.setMaximum(0)
        self.a120mm_cam_offset_slider.setValue(0)
      if 'HardwareBin' in cam_settings['a120mm']:
        self.a120mm_cam_bin.clear()
        for i in range(cam_settings['a120mm']['HardwareBin']['MinValue'], cam_settings['a120mm']['HardwareBin']['MaxValue']+1):
          self.a120mm_cam_bin.addItem(str(i))
        self.a120mm_cam_bin.setCurrentIndex(0)
      else:
        self.a120mm_cam_bin.clear()
        self.a120mm_cam_bin.addItem('NULL')
        self.a120mm_cam_bin.setCurrentIndex(0)

  def f_canon_update_values(self, load_slider = False):
    global cam_settings

    curr_time = time.time()
    try:
      out = requests.get('http://127.0.0.1:8003/get_iso_value', timeout=1)
      if out.status_code == 200:
        self.canon_gain_depl.setText("ISO set: " + str(json.loads(out.text)['iso_value']))
    except:
      pass
    if os.path.isfile('/dev/shm/canon/time'):
      f = open('/dev/shm/canon/time', 'r')
      val = f.read()
      f.close()
      self.lab_canon_time_frame.setText("Last frame time: " + str(int(curr_time) - int(val)) + "s ago")
    self.lab_canon_time_disp_frame.setText("Displayed frame made: " + str(format(curr_time - cam_settings['canon']['disp_frame_time'], '.1f')) + "s ago")
    self.lab_canon_rotate.setText("Rotate: " + str(cam_settings['canon']['rotate']))

  def f_a120mc_cam_reset_settings(self):
    self.a120mc_cam_exp_slider.setValue(1000)
    self.a120mc_cam_offset_slider.setValue(2)
    self.a120mc_cam_gain_slider.setValue(99)
    self.f_a120mc_cam_params_changed()

  def f_a120mm_cam_reset_settings(self):
    self.a120mm_cam_exp_slider.setValue(1000)
    self.a120mm_cam_offset_slider.setValue(2)
    self.a120mm_cam_gain_slider.setValue(99)
    self.f_a120mm_cam_params_changed()

  def f_a183mm_cam_reset_settings(self):
    self.a183mm_cam_exp_slider.setValue(1000)
    self.a183mm_cam_offset_slider.setValue(10)
    self.a183mm_cam_gain_slider.setValue(115)
    self.f_a183mm_cam_params_changed()

  def f_a183mm_cam_params_changed(self):
    global viewer_a183mm_deployed, cam_settings

    if viewer_a183mm_deployed:
      cam_settings['a183mm']['Exposure']['Value'] = int(self.a183mm_cam_exp_slider.value()*1000)
      cam_settings['a183mm']['Offset']['Value'] = int(self.a183mm_cam_offset_slider.value())
      cam_settings['a183mm']['Gain']['Value'] = int(self.a183mm_cam_gain_slider.value())
      cam_settings['a183mm']['TargetTemp']['Value'] = int(self.a183mm_cam_target_temp_slider.value())
      if self.a183mm_cam_bin.currentText() != '':
        cam_settings['a183mm']['HardwareBin']['Value'] = int(self.a183mm_cam_bin.currentText())

      if self.a183mm_cam_cooler.isChecked():
        cam_settings['a183mm']['CoolerOn']['Value'] = 1
      else:
        cam_settings['a183mm']['CoolerOn']['Value'] = 0

      cam_settings['a183mm']['param_time'] = time.time()

  def f_a533mc_cam_reset_settings(self):
    self.a533mc_cam_exp_slider.setValue(1000)
    self.a533mc_cam_offset_slider.setValue(40)
    self.a533mc_cam_gain_slider.setValue(110)
    self.f_a533mc_cam_params_changed()

  def f_a533mc_cam_params_changed(self):
    global viewer_a533mc_deployed, cam_settings

    if viewer_a533mc_deployed:
      cam_settings['a533mc']['Exposure']['Value'] = int(self.a533mc_cam_exp_slider.value()*1000)
      cam_settings['a533mc']['Offset']['Value'] = int(self.a533mc_cam_offset_slider.value())
      cam_settings['a533mc']['Gain']['Value'] = int(self.a533mc_cam_gain_slider.value())
      cam_settings['a533mc']['TargetTemp']['Value'] = int(self.a533mc_cam_target_temp_slider.value())
      if self.a533mc_cam_bin.currentText() != '':
        cam_settings['a533mc']['HardwareBin']['Value'] = int(self.a533mc_cam_bin.currentText())

      if self.a533mc_cam_cooler.isChecked():
        cam_settings['a533mc']['CoolerOn']['Value'] = 1
      else:
        cam_settings['a533mc']['CoolerOn']['Value'] = 0

      cam_settings['a533mc']['param_time'] = time.time()

  def f_a462mc_cam_reset_settings(self):
    self.a462mc_cam_exp_slider.setValue(1000)
    self.a462mc_cam_offset_slider.setValue(10)
    self.a462mc_cam_gain_slider.setValue(90)
    self.f_a462mc_cam_params_changed()

  def f_a462mc_cam_params_changed(self):
    global viewer_a462mc_deployed, cam_settings

    if viewer_a462mc_deployed:
      cam_settings['a462mc']['Exposure']['Value'] = int(self.a462mc_cam_exp_slider.value()*1000)
      cam_settings['a462mc']['Offset']['Value'] = int(self.a462mc_cam_offset_slider.value())
      cam_settings['a462mc']['Gain']['Value'] = int(self.a462mc_cam_gain_slider.value())
      if self.a462mc_cam_bin.currentText() != '':
        cam_settings['a462mc']['HardwareBin']['Value'] = int(self.a462mc_cam_bin.currentText())
      cam_settings['a462mc']['param_time'] = time.time()

  def f_a120mc_cam_params_changed(self):
    global viewer_a120mc_deployed, cam_settings

    if viewer_a120mc_deployed:
      cam_settings['a120mc']['Exposure']['Value'] = int(self.a120mc_cam_exp_slider.value()*1000)
      cam_settings['a120mc']['Offset']['Value'] = int(self.a120mc_cam_offset_slider.value())
      cam_settings['a120mc']['Gain']['Value'] = int(self.a120mc_cam_gain_slider.value())
      if self.a120mc_cam_bin.currentText() != '':
        cam_settings['a120mc']['HardwareBin']['Value'] = int(self.a120mc_cam_bin.currentText())
      cam_settings['a120mc']['param_time'] = time.time()

  def f_a120mm_cam_params_changed(self):
    global viewer_a120mm_deployed, cam_settings

    if viewer_a120mm_deployed:
      cam_settings['a120mm']['Exposure']['Value'] = int(self.a120mm_cam_exp_slider.value()*1000)
      cam_settings['a120mm']['Offset']['Value'] = int(self.a120mm_cam_offset_slider.value())
      cam_settings['a120mm']['Gain']['Value'] = int(self.a120mm_cam_gain_slider.value())
      if self.a120mm_cam_bin.currentText() != '':
        cam_settings['a120mm']['HardwareBin']['Value'] = int(self.a120mm_cam_bin.currentText())
      cam_settings['a120mm']['param_time'] = time.time()

  def f_canon_iso_change(self):
    global req_canon
    val = self.canon_iso.currentText()
    req_canon.put('http://127.0.0.1:8003/set_iso/' + str(val))


  def f_solved_tabs_refresh(self):
    global plate_solve_results

    if set(['url', 'hdcat', 'tycho2cat']).issubset(set(plate_solve_results.keys())):
      height, width, channel = plate_solve_results['tycho2cat'].shape
      bytesPerLine = 3 * width
      qImg = QImage(plate_solve_results['tycho2cat'], width, height, bytesPerLine, QImage.Format_BGR888)
      self.viewer_tycho2.setPhoto(QtGui.QPixmap(qImg))
      self.viewer_tycho2.fitInView()

      height, width, channel = plate_solve_results['hdcat'].shape
      bytesPerLine = 3 * width
      qImg = QImage(plate_solve_results['hdcat'], width, height, bytesPerLine, QImage.Format_BGR888)
      self.viewer_hd.setPhoto(QtGui.QPixmap(qImg))
      self.viewer_hd.fitInView()

      self.viewer_skymap.load(QUrl(plate_solve_results['url']))
      self.viewer_skymap.show()

  def f_a120mc_window_refresh(self):
    global q_a120mc_ready, viewer_a120mc_deployed, cam_settings, q_a120mc_save_to_file
    self.f_window_refresh_universal(cam_name = 'a120mc',
                                    q_ready = q_a120mc_ready,
                                    viewer_deployed = viewer_a120mc_deployed,
                                    cam_inverse = self.a120mc_cam_inverse,
                                    cam_sat = self.a120mc_cam_sat,
                                    cam_bri = self.a120mc_cam_bri,
                                    cam_gam = self.a120mc_cam_gam,
                                    cam_hist_equal = self.a120mc_cam_hist_equal,
                                    cam_normalize = self.a120mc_cam_normalize,
                                    cam_normalize_l = self.a120mc_cam_normalize_l,
                                    cam_normalize_h = self.a120mc_cam_normalize_h,
                                    cam_circ_d = self.a120mc_cam_circ_d.value(),
                                    cam_circ_c = self.a120mc_cam_circ_c.value(),
                                    cam_circ_x = self.a120mc_cam_circ_x.value(),
                                    cam_circ_y = self.a120mc_cam_circ_y.value(),
                                    graph_obj = self.graphWidget_a120mc,
                                    viewer_obj = self.viewer_a120mc,
                                    pixel_stat = self.lab_a120mc_cam_photo_pixel_stat,
                                    )
    return

  def f_a120mm_window_refresh(self):
    global q_a120mm_ready, viewer_a120mm_deployed, cam_settings, q_a120mm_save_to_file
    self.f_window_refresh_universal(cam_name = 'a120mm',
                                    q_ready = q_a120mm_ready,
                                    viewer_deployed = viewer_a120mm_deployed,
                                    cam_inverse = self.a120mm_cam_inverse,
                                    cam_sat = self.a120mm_cam_sat,
                                    cam_bri = self.a120mm_cam_bri,
                                    cam_gam = self.a120mm_cam_gam,
                                    cam_hist_equal = self.a120mm_cam_hist_equal,
                                    cam_normalize = self.a120mm_cam_normalize,
                                    cam_normalize_l = self.a120mm_cam_normalize_l,
                                    cam_normalize_h = self.a120mm_cam_normalize_h,
                                    cam_circ_d = self.a120mm_cam_circ_d.value(),
                                    cam_circ_c = self.a120mm_cam_circ_c.value(),
                                    cam_circ_x = self.a120mm_cam_circ_x.value(),
                                    cam_circ_y = self.a120mm_cam_circ_y.value(),
                                    graph_obj = self.graphWidget_a120mm,
                                    viewer_obj = self.viewer_a120mm,
                                    pixel_stat = self.lab_a120mm_cam_photo_pixel_stat,
                                    )

  def f_canon_window_refresh(self):
    global q_canon_ready, viewer_canon_deployed, cam_settings, canon_last_frame, canon_last_frame_time
    self.f_window_refresh_universal(cam_name = 'canon',
                                    q_ready = q_canon_ready,
                                    viewer_deployed = viewer_canon_deployed,
                                    cam_inverse = self.canon_inverse,
                                    cam_sat = self.canon_sat,
                                    cam_bri = self.canon_bri,
                                    cam_gam = self.canon_gam,
                                    cam_hist_equal = self.canon_hist_equal,
                                    cam_normalize = self.canon_cam_normalize,
                                    cam_normalize_l = self.canon_cam_normalize_l,
                                    cam_normalize_h = self.canon_cam_normalize_h,
                                    cam_circ_d = self.canon_cam_circ_d.value(),
                                    cam_circ_c = self.canon_cam_circ_c.value(),
                                    cam_circ_x = self.canon_cam_circ_x.value(),
                                    cam_circ_y = self.canon_cam_circ_y.value(),
                                    graph_obj = self.graphWidget_canon,
                                    viewer_obj = self.viewer_canon,
                                    )

  def f_a120mc_window_refresh_event(self):
    self.a120mc_photo_reload.click()

  def f_a120mm_window_refresh_event(self):
    self.a120mm_photo_reload.click()

  def f_canon_window_refresh_event(self):
    self.canon_photo_reload.click()

  def f_solved_tabs_refresh_event(self):
    self.solved_tabs_refresh.click()

  def f_a183mm_rotate(self):
    global cam_settings
    cam_settings['a183mm']['rotate'] = (cam_settings['a183mm']['rotate'] + 90) % 360

  def f_a533mc_rotate(self):
    global cam_settings
    cam_settings['a533mc']['rotate'] = (cam_settings['a533mc']['rotate'] + 90) % 360

  def f_a462mc_rotate(self):
    global cam_settings
    cam_settings['a462mc']['rotate'] = (cam_settings['a462mc']['rotate'] + 90) % 360

  def f_a120mc_rotate(self):
    global cam_settings
    cam_settings['a120mc']['rotate'] = (cam_settings['a120mc']['rotate'] + 90) % 360

  def f_a120mm_rotate(self):
    global cam_settings
    cam_settings['a120mm']['rotate'] = (cam_settings['a120mm']['rotate'] + 90) % 360

  def f_canon_rotate(self):
    global cam_settings
    cam_settings['canon']['rotate'] = (cam_settings['canon']['rotate'] + 90) % 360

  def f_a183mm_window_refresh(self):
    global q_a183mm_ready, viewer_a183mm_deployed, cam_settings, q_a183mm_save_to_file
    self.f_window_refresh_universal(cam_name = 'a183mm',
                                    q_ready = q_a183mm_ready,
                                    viewer_deployed = viewer_a183mm_deployed,
                                    cam_inverse = self.a183mm_cam_inverse,
                                    cam_sat = self.a183mm_cam_sat,
                                    cam_bri = self.a183mm_cam_bri,
                                    cam_gam = self.a183mm_cam_gam,
                                    cam_hist_equal = self.a183mm_cam_hist_equal,
                                    cam_normalize = self.a183mm_cam_normalize,
                                    cam_normalize_l = self.a183mm_cam_normalize_l,
                                    cam_normalize_h = self.a183mm_cam_normalize_h,
                                    cam_circ_d = self.a183mm_cam_circ_d.value(),
                                    cam_circ_c = self.a183mm_cam_circ_c.value(),
                                    cam_circ_x = self.a183mm_cam_circ_x.value(),
                                    cam_circ_y = self.a183mm_cam_circ_y.value(),
                                    graph_obj = self.graphWidget_a183mm,
                                    viewer_obj = self.viewer_a183mm,
                                    pixel_stat = self.lab_a183mm_cam_photo_pixel_stat,
                                    )


  def f_a183mm_window_refresh_event(self):
    self.a183mm_photo_reload.click()


  def f_a533mc_window_refresh(self):
    global q_a533mc_ready, viewer_a533mc_deployed, cam_settings, q_a533mc_save_to_file
    self.f_window_refresh_universal(cam_name = 'a533mc',
                                    q_ready = q_a533mc_ready,
                                    viewer_deployed = viewer_a533mc_deployed,
                                    cam_inverse = self.a533mc_cam_inverse,
                                    cam_sat = self.a533mc_cam_sat,
                                    cam_bri = self.a533mc_cam_bri,
                                    cam_gam = self.a533mc_cam_gam,
                                    cam_hist_equal = self.a533mc_cam_hist_equal,
                                    cam_normalize = self.a533mc_cam_normalize,
                                    cam_normalize_l = self.a533mc_cam_normalize_l,
                                    cam_normalize_h = self.a533mc_cam_normalize_h,
                                    cam_circ_d = self.a533mc_cam_circ_d.value(),
                                    cam_circ_c = self.a533mc_cam_circ_c.value(),
                                    cam_circ_x = self.a533mc_cam_circ_x.value(),
                                    cam_circ_y = self.a533mc_cam_circ_y.value(),
                                    graph_obj = self.graphWidget_a533mc,
                                    viewer_obj = self.viewer_a533mc,
                                    pixel_stat = self.lab_a533mc_cam_photo_pixel_stat,
                                    )


  def f_a533mc_window_refresh_event(self):
    self.a533mc_photo_reload.click()


  def f_a462mc_window_refresh(self):
    global q_a462mc_ready, viewer_a462mc_deployed, cam_settings, q_a462mc_save_to_file

    self.f_window_refresh_universal(cam_name = 'a462mc',
                                    q_ready = q_a462mc_ready,
                                    viewer_deployed = viewer_a462mc_deployed,
                                    cam_inverse = self.a462mc_cam_inverse,
                                    cam_sat = self.a462mc_cam_sat,
                                    cam_bri = self.a462mc_cam_bri,
                                    cam_gam = self.a462mc_cam_gam,
                                    cam_hist_equal = self.a462mc_cam_hist_equal,
                                    cam_normalize = self.a462mc_cam_normalize,
                                    cam_normalize_l = self.a462mc_cam_normalize_l,
                                    cam_normalize_h = self.a462mc_cam_normalize_h,
                                    cam_circ_d = self.a462mc_cam_circ_d.value(),
                                    cam_circ_c = self.a462mc_cam_circ_c.value(),
                                    cam_circ_x = self.a462mc_cam_circ_x.value(),
                                    cam_circ_y = self.a462mc_cam_circ_y.value(),
                                    graph_obj = self.graphWidget_a462mc,
                                    viewer_obj = self.viewer_a462mc,
                                    pixel_stat = self.lab_a462mc_cam_photo_pixel_stat,
                                    )


  def f_window_refresh_universal(self, q_ready, viewer_deployed, cam_name, cam_inverse, cam_sat, cam_bri, cam_gam, cam_hist_equal, cam_normalize, cam_normalize_l, cam_normalize_h, cam_circ_d, cam_circ_c, cam_circ_x, cam_circ_y, graph_obj, viewer_obj, pixel_stat):
    if q_ready and viewer_deployed:
      frame = q_ready.pop()

      if not 'rotate' in cam_settings[cam_name]:
        cam_settings[cam_name]['rotate'] = 0
        cam_settings[cam_name]['last_rotate'] = 0

      _frame = self.f_rotate_frame(frame=frame['frameRGB'], rotate=cam_settings[cam_name]['rotate'])
      _frame = self.f_inverse_frame(frame=_frame, inverse=cam_inverse.isChecked())
      _frame = self.f_bri_sat_gam(frame=_frame, sat=cam_sat.value(), bri=cam_bri.value(), gam=cam_gam.value())
      _frame = self.f_hist_equal(frame=_frame, equal=cam_hist_equal.isChecked())
      _frame = self.f_normalize(frame=_frame, normalize=cam_normalize.isChecked(), low=cam_normalize_l.value(), high=cam_normalize_h.value())
      _frame = self.f_circ(frame=_frame, d=cam_circ_d, c=cam_circ_c, x=cam_circ_x, y=cam_circ_y)

      pixel_stat.setText(frame['percentile_stat'])
      #self.f_histogram(frame=_frame, graph_obj=graph_obj)
      self.f_viewer_frame(frame=_frame, viewer_obj=viewer_obj)

      cam_settings[cam_name]['disp_frame_time'] = frame['time']

      if cam_settings[cam_name]['last_rotate'] != cam_settings[cam_name]['rotate']:
        viewer_obj.fitInView()
        cam_settings[cam_name]['last_rotate'] = cam_settings[cam_name]['rotate']

  def f_a462mc_window_refresh_event(self):
    self.a462mc_photo_reload.click()

  def f_viewer_frame(self, frame, viewer_obj):
      height, width, channel = frame.shape
      bytesPerLine = 3 * width
      qImg = QImage(frame, width, height, bytesPerLine, QImage.Format_BGR888)
      viewer_obj.setPhoto(QtGui.QPixmap(qImg))

  def f_histogram(self, frame, graph_obj):
    hist_pen_r = pg.mkPen(color=(255,0,0), width=2)
    hist_pen_g = pg.mkPen(color=(0,191,41), width=2)
    hist_pen_b = pg.mkPen(color=(0,0,255), width=2)
    hist_pen_gray = pg.mkPen(color=(0,0,0), width=2)

    b,g,r = cv2.split(frame)
    histogram_b, bin_edges_b = np.histogram(b, bins=256, range=(0, 256))
    histogram_g, bin_edges_g = np.histogram(g, bins=256, range=(0, 256))
    histogram_r, bin_edges_r = np.histogram(r, bins=256, range=(0, 256))
    histogram_gray, bin_edges_gray = np.histogram(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), bins=256, range=(0, 256))

    graph_obj.clear()
    graph_obj.plot(x=list(range(256)), y=histogram_b, pen=hist_pen_b)
    graph_obj.plot(x=list(range(256)), y=histogram_g, pen=hist_pen_g)
    graph_obj.plot(x=list(range(256)), y=histogram_r, pen=hist_pen_r)
    graph_obj.plot(x=list(range(256)), y=histogram_gray, pen=hist_pen_gray)

  def f_circ(self,frame, d, c, x, y):
    if d > 0:
      center_coordinates = (x,y)
      color = (0, 0, 255)
      thickness = 2
      _frame = cv2.circle(frame, center_coordinates, d, color, thickness)
      if c > 0:
        while True:
          d = d + c
          if d > 1936 or c == 0:
            break
          _frame = cv2.circle(frame, center_coordinates, d, color, thickness)
      return(_frame)
    else:
      return(frame)

  def f_normalize(self, frame, normalize, low, high):
    if normalize:
      l = np.percentile(frame,low)
      h = np.percentile(frame,high)
      return(np.clip((((frame - l)/(h-l))*255), 0, 255).astype('uint8'))
    else:
      return(frame)

  def f_hist_equal(self, frame, equal):
    if equal:
      img_yuv = cv2.cvtColor(frame, cv2.COLOR_RGB2YUV)
      img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
      return(cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR))
    else:
      return(frame)

  def f_bri_sat_gam(self,frame,sat,bri,gam):
    if float(sat) != 1.0 or bri != 0 or float(gam) != 1.0:
      h, s, v = cv2.split(cv2.cvtColor(frame.astype("float32"), cv2.COLOR_RGB2HSV))
      if float(sat) != 1.0:
        s = s*sat
        s = np.clip(s,0.0,255.0)
      if bri != 0:
        v = v + bri
      if float(gam) != 0.0:
        v = np.power(v, gam)
      if bri != 0 or float(gam) != 1.0:
        v = np.clip(v,0.0,255.0)
      return(cv2.cvtColor(cv2.merge((h,s,v)), cv2.COLOR_HSV2RGB).astype("uint8"))
    else:
      return(frame)


  def f_inverse_frame(self,frame,inverse):
    if inverse:
      return(255 - frame)
    else:
      return(frame)

  def f_rotate_frame(self,frame,rotate):
    if rotate == 90:
      return(cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE))
    elif rotate == 180:
      return(cv2.rotate(frame, cv2.ROTATE_180))
    elif rotate == 270:
      return(cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE))
    else:
      return(frame)

  def print_telescope_position(self):
    global t_telescope, connection_ok, last_response_time

    self.get_pos_stat()

    try:
      self.radec_position1.setText('RA: ' + str(t_telescope['ra']) + "   DEC: " + str(t_telescope['dec']))
      self.altaz_position1.setText('AZ: ' + Angle(t_telescope['az'] * u.deg).to_string(unit=u.deg) + '   ALT: ' + Angle(t_telescope['alt'] * u.deg).to_string(unit=u.deg))
      self.radec_position.setText('RA: ' + str(t_telescope['ra']) + "   DEC: " + str(t_telescope['dec']))
      self.altaz_position.setText('AZ: ' + Angle(t_telescope['az'] * u.deg).to_string(unit=u.deg) + '   ALT: ' + Angle(t_telescope['alt'] * u.deg).to_string(unit=u.deg))
    except Exception as e:
      print(traceback.format_exc())
      pass

    if connection_ok:
      state = 'OK'
    else:
      state = 'ERROR'

  def slider_center(self):
    self.ost_slider.setSliderPosition(0)

  def radec_set(self):
    global t_telescope

    if self.dec_sign3.value() < 0:
      signum = '-'
    else:
      signum = ''

    t_telescope['ra']  = Angle(str(self.ra_h.value()) + 'h' + str(self.ra_m.value()) + 'm' + str(self.ra_s.value()) + 's')
    t_telescope['dec'] = Angle(signum + str(self.dec_d.value()) + 'd' + str(self.dec_m.value()) + 'm' + str(self.dec_s.value()) + 's')

  def altaz_set(self):
    global t_telescope

    t = Time('J2021.10').now()
    alt_str = str(self.elev_d.value()) + 'd' + str(self.elev_m.value()) + 'm'
    az_str = str(self.az_d.value()) + 'd' + str(self.az_m.value()) + 'm'
    radec_place = SkyCoord(alt = Angle(alt_str), az = Angle(az_str), obstime = t, frame = 'altaz', location = t_telescope['loc'])
    t_telescope['ra'] =  Angle(radec_place.icrs.ra.to_string(unit=u.hour))
    t_telescope['dec'] = Angle(radec_place.icrs.dec.to_string(unit=u.deg))

  def ost_joystick_left(self):
    payload = {
      'mode': 'ost_joystick',
      'side': 'right',
      'steps': self.ost_joystick_arc.value(),
    }
    req_cmd.put(payload)

  def ost_joystick_right(self):
    payload = {
      'mode': 'ost_joystick',
      'side': 'left',
      'steps': self.ost_joystick_arc.value(),
    }
    req_cmd.put(payload)

  def f_ost_slider(self, value):
    global req_cmd
    payload = {
      'mode': 'ost_manual',
      'speed': value,
    }
    req_cmd.put(payload)

  def f_changed_tab_left(self,tab):
    if tab == 1:
      self.t_prawy.setCurrentIndex(0)
    elif tab == 2:
      self.t_prawy.setCurrentIndex(1)
    elif tab == 3:
      self.t_prawy.setCurrentIndex(2)
    elif tab == 4:
      self.t_prawy.setCurrentIndex(3)
    elif tab == 5:
      self.t_prawy.setCurrentIndex(4)

  def f_shutdown(self):
    global kill_thread
    for i in ['http://127.0.0.2:8000/shutdown', 'http://127.0.0.2:8001/shutdown', 'http://127.0.0.2:8002/shutdown', 'http://127.0.0.2:8003/shutdown', 'http://eq1.embedded/shutdown', 'http://eq3.embedded/shutdown', 'http://eq2.embedded/shutdown']:
      try:
        out = requests.get(i, timeout=3)
      except:
        pass
    kill_thread = True

  def f_reboot_scope(self):
    global kill_thread
    for i in ['http://eq1.embedded/reboot']:
      try:
        out = requests.get(i, timeout=3)
      except:
        pass

  def f_restart(self):
    global kill_thread
    for i in ['http://eq1.embedded/restart']:
      try:
        out = requests.get(i, timeout=3)
      except:
        pass

  def get_pos_stat(self):
    global t_telescope

    t = Time('J2021.10').now()
    actual = SkyCoord(ra=t_telescope['ra'], dec=t_telescope['dec'], frame='icrs')
    actual_altaz = actual.transform_to(AltAz(obstime=t,location=t_telescope['loc']))
    t_telescope['alt'] = actual_altaz.alt.wrap_at(180 * u.deg).degree
    t_telescope['az']  = actual_altaz.az.wrap_at(360 * u.deg).degree


app = QApplication(sys.argv)
screen = Window()

thread_list = []

t = threading.Thread(target=f_requests_send)
thread_list.append(t)

t = threading.Thread(target=f_run_periodic_functions)
thread_list.append(t)

t = threading.Thread(target=f_a120mm_preview)
thread_list.append(t)

t = threading.Thread(target=f_a120mc_preview)
thread_list.append(t)

t = threading.Thread(target=f_a462mc_preview)
thread_list.append(t)

t = threading.Thread(target=f_a183mm_preview)
thread_list.append(t)

t = threading.Thread(target=f_a533mc_preview)
thread_list.append(t)

t = threading.Thread(target=f_photo_refresh)
thread_list.append(t)

t = threading.Thread(target=f_a462mc_frame_processing)
thread_list.append(t)

t = threading.Thread(target=f_a183mm_frame_processing)
thread_list.append(t)

t = threading.Thread(target=f_a533mc_frame_processing)
thread_list.append(t)

t = threading.Thread(target=f_a120mm_frame_processing)
thread_list.append(t)

t = threading.Thread(target=f_a120mc_frame_processing)
thread_list.append(t)

t = threading.Thread(target=f_a120mm_plate_solve_loop)
thread_list.append(t)

t = threading.Thread(target=f_a120mc_plate_solve_loop)
thread_list.append(t)

t = threading.Thread(target=f_a462mc_plate_solve_loop)
thread_list.append(t)

t = threading.Thread(target=f_save_a462mc_img)
thread_list.append(t)

t = threading.Thread(target=f_a183mm_plate_solve_loop)
thread_list.append(t)

t = threading.Thread(target=f_save_a183mm_img)
thread_list.append(t)

t = threading.Thread(target=f_a533mc_plate_solve_loop)
thread_list.append(t)

t = threading.Thread(target=f_save_a533mc_img)
thread_list.append(t)

t = threading.Thread(target=f_save_a120mm_img)
thread_list.append(t)

t = threading.Thread(target=f_save_a120mc_img)
thread_list.append(t)

t = threading.Thread(target=f_requests_canon_send)
thread_list.append(t)

t = threading.Thread(target=f_canon_preview)
thread_list.append(t)

t = threading.Thread(target=f_canon_frame_processing)
thread_list.append(t)

t = threading.Thread(target=f_canon_plate_solve_loop)
thread_list.append(t)

t = threading.Thread(target=f_a462mc_settings)
thread_list.append(t)

t = threading.Thread(target=f_a183mm_settings)
thread_list.append(t)

t = threading.Thread(target=f_a533mc_settings)
thread_list.append(t)

t = threading.Thread(target=f_a120mc_settings)
thread_list.append(t)

t = threading.Thread(target=f_a120mm_settings)
thread_list.append(t)

for thread in thread_list:
    thread.start()

screen.showMaximized()
app.exec_()


kill_thread = True
