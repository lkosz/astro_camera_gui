#!/usr/bin/env python3

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import *
from astropy import units as u,wcs
from astropy.coordinates import Angle,EarthLocation,SkyCoord,AltAz
from astropy.coordinates import FK5
from astropy.io import fits
from astropy.time import Time
from astropy.utils.exceptions import AstropyWarning
from collections import deque
import pyqtgraph as pg
import pathlib, sys, requests, threading, time, json, queue, numpy as np, subprocess, datetime, os, tifffile as tiff, traceback, warnings, tifffile
import inspect, zwoasi as asi
from guider import Guider
os.environ["OPENCV_LOG_LEVEL"] ="OFF"
import cv2, multiprocessing as mp, select, glob
warnings.simplefilter('ignore', category=AstropyWarning)
asi.init('./libASICamera2.so.1.26')

#############################################################################################

PD_key = '-pd-api-key-'
phd2_working = None
bahtinov_focus_working = None
mpd = {}
kill_thread = False
req_cmd_eq6 = queue.Queue()
req_cmd_eq5 = queue.Queue()
req_canon = queue.Queue()
eq6_stats = {
  'ra':  Angle('00h00m00s'),
  'dec': Angle('00d00m00s'),
  'alt': Angle('00d00m00s'),
  'az':  Angle('00d00m00s'),
  'loc': EarthLocation(lat=57.1121*u.deg, lon=27.019650955565243*u.deg, height=134*u.m),
  'epoch': 'J' + str(datetime.datetime.now().year) + '.' + str(datetime.datetime.now().month),
  'new_ra':  Angle('00h00m00s'),
  'new_dec': Angle('00d00m00s'),
  'file_to_align_ra':  Angle('00h00m00s'),
  'file_to_align_dec': Angle('00d00m00s'),
}

screen = None
connection_ok = False
filter_reset_done = False
filters_set = ['NULL', 'NULL']
filter_wheel_responds = False
quick_check_align_original_tab = 0


q_a120mc_platesolve        = deque(maxlen=1)
q_a120mc_raw               = deque(maxlen=1)
q_a120mc_ready             = deque(maxlen=2)
q_a120mc_save_to_file      = deque(maxlen=100)
q_a120mm_platesolve        = deque(maxlen=1)
q_a120mm_raw               = deque(maxlen=1)
q_a120mm_ready             = deque(maxlen=2)
q_a120mm_save_to_file      = deque(maxlen=100)
q_a174mm_platesolve        = deque(maxlen=1)
q_a174mm_raw               = deque(maxlen=1)
q_a174mm_ready             = deque(maxlen=2)
q_a174mm_save_to_file      = deque(maxlen=100)
q_a183mm_platesolve        = deque(maxlen=1)
q_a183mm_raw               = deque(maxlen=1)
q_a183mm_ready             = deque(maxlen=2)
q_a183mm_save_to_file      = deque(maxlen=100)
q_a290mm_platesolve        = deque(maxlen=1)
q_a290mm_raw               = deque(maxlen=1)
q_a290mm_ready             = deque(maxlen=2)
q_a290mm_save_to_file      = deque(maxlen=100)
q_a432mm_platesolve        = deque(maxlen=1)
q_a432mm_raw               = deque(maxlen=1)
q_a432mm_ready             = deque(maxlen=2)
q_a432mm_save_to_file      = deque(maxlen=100)
q_a462mc_platesolve        = deque(maxlen=1)
q_a462mc_raw               = deque(maxlen=1)
q_a462mc_ready             = deque(maxlen=2)
q_a462mc_save_to_file      = deque(maxlen=100)
q_a533mc_platesolve        = deque(maxlen=1)
q_a533mc_raw               = deque(maxlen=1)
q_a533mc_ready             = deque(maxlen=2)
q_a533mc_save_to_file      = deque(maxlen=100)
q_a533mm_platesolve        = deque(maxlen=1)
q_a533mm_raw               = deque(maxlen=1)
q_a533mm_ready             = deque(maxlen=2)
q_a533mm_save_to_file      = deque(maxlen=100)
q_canon_platesolve         = deque(maxlen=1)
q_canon_raw                = deque(maxlen=3)
q_canon_ready              = deque(maxlen=1)
q_file_to_align_platesolve = deque(maxlen=1)

viewer_a174mm_deployed = False
viewer_a290mm_deployed = False
viewer_a432mm_deployed = False
viewer_a120mm_deployed = False
viewer_a120mc_deployed = False
viewer_canon_deployed = False
viewer_a183mm_deployed = False
viewer_a533mc_deployed = False
viewer_a533mm_deployed = False
viewer_a462mc_deployed = False
run_plate_solve_a120mm = False
run_plate_solve_a290mm = False
run_plate_solve_a432mm = False
run_plate_solve_a174mm = False
run_plate_solve_a120mc = False
run_plate_solve_canon = False
run_plate_solve_a183mm = False
run_plate_solve_a533mc = False
run_plate_solve_a533mm = False
run_plate_solve_a462mc = False

run_plate_solve_a120mm_mount_eq6 = False
run_plate_solve_a290mm_mount_eq6 = False
run_plate_solve_a432mm_mount_eq6 = False
run_plate_solve_a174mm_mount_eq6 = False
run_plate_solve_a120mc_mount_eq6 = False
run_plate_solve_canon_mount_eq6  = False
run_plate_solve_a183mm_mount_eq6 = False
run_plate_solve_a533mc_mount_eq6 = False
run_plate_solve_a533mm_mount_eq6 = False
run_plate_solve_a462mc_mount_eq6 = False

run_plate_solve_file_to_align = False
run_plate_solve_file_to_align_mount_eq6 = False
plate_solve_canon_status = 'NULL'
plate_solve_a120mm_status = 'NULL'
plate_solve_a290mm_status = 'NULL'
plate_solve_a432mm_status = 'NULL'
plate_solve_a174mm_status = 'NULL'
plate_solve_a120mc_status = 'NULL'
plate_solve_a183mm_status = 'NULL'
plate_solve_a533mc_status = 'NULL'
plate_solve_a533mm_status = 'NULL'
plate_solve_a462mc_status = 'NULL'
plate_solve_results = {}
canon_last_frame = False
canon_last_frame_time = 0.0
indi_properties = {}
cameras = {
  'a462mc': {
    'name': 'ZWO ASI462MC',
  },
  'a183mm': {
    'name': 'ZWO ASI183MM Pro',
  },
  'a533mc': {
    'name': 'ZWO ASI533MC Pro',
  },
  'a533mm': {
    'name': 'ZWO ASI533MM Pro',
  },
  'a120mc': {
    'name': 'ZWO ASI120MC-S',
  },
  'a120mm': {
    'name': 'ZWO ASI120MM Mini',
  },
  'a290mm': {
    'name': 'ZWO ASI290MM',
  },
  'a432mm': {
    'name': 'ZWO ASI432MM',
  },
  'a174mm': {
    'name': 'ZWO ASI174MM Mini',
  },
  'canon':{
    'disp_frame_time': 0,
    'rotate': 0,
    'last_rotate': 0,
  },
}


app_settings = {}
indi_slider_valtab = ['1x', '2x', '4x', '8x', '32x', '64x', '128x', '600x', '700x', '800x']
eq5_slider_valtab = ['2', '5', '10', '20', '30', '40', '50', '60', '80', '100']
last_indi_response_time = 0
indi_slider_paramtab = [
  'EQMod Mount.TELESCOPE_SLEW_RATE.1x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.2x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.3x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.4x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.5x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.6x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.7x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.8x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.9x',
  'EQMod Mount.TELESCOPE_SLEW_RATE.SLEW_MAX',
]
last_eq5_response_time = 0
eq5_stats = {}


#############################################################################################

def f_autooff_date(hour, minute):
  t = datetime.datetime.now()
  t = t.replace(hour=hour, minute=minute, second=0, microsecond=0)

  if int(t.timestamp()) < int(datetime.datetime.now().timestamp()):
    t = t + datetime.timedelta(days=1)

  return(int(t.timestamp()))

def f_autooff_phd_query():
  try:
    with Guider("localhost") as guider:
      guider.Connect()
      guider.StopCapture()
  except Exception as e:
    print(traceback.format_exc())
    pass

def f_autooff_turnoff_phd():
  global screen, phd2_working, kill_thread
  timeout = 0
  f_autooff_phd_query()
  while phd2_working == True and timeout < 6 and kill_thread == False:
    timeout += 1
    time.sleep(10)
    f_autooff_phd_query()
  screen.lab_phd2_mon_en.setChecked(False)

def f_autooff_stop_file_save():
  global screen
  for i in vars(screen).keys():
    if i.endswith('_cam_save_img'):
      vars(screen)[i].setChecked(False)

def f_autooff_stop_cameras():
  global screen, kill_thread, cameras

  cameras_cp = cameras.copy()

  for c in cameras_cp.keys():
    if 'info' in cameras[c].keys() and  vars(screen)[c + '_cam_on'].isChecked() == True:
      screen.autooff_state.setText("Shutdown 3/10: Turnoff camera " + c)
      vars(screen)[c + '_cam_exp_slider'].setValue(1000.0)
      if 'cooler_pwr' in cameras[c]['info'].keys() and cameras[c]['info']['cooler_pwr'] > 0:
        while cameras[c]['info']['cooler_pwr'] > 0 and kill_thread == False:
          vars(screen)[c + '_cam_target_temp_slider'].setValue(int(cameras[c]['info']['temperature']) + 5)
          screen.autooff_state.setText("Shutdown 4/6: Turnoff cooling in " + c + " cooler pwr: " + str(cameras[c]['info']['cooler_pwr']) + ' temp: ' + str(cameras[c]['info']['temperature']))
          time.sleep(1)
        vars(screen)[c + '_cam_cooler'].setChecked(False)
      time.sleep(5)
      vars(screen)[c + '_cam_on'].setChecked(False)
    if kill_thread:
      return

def f_autooff_park_scope():
  global screen, indi_properties

  screen.autooff_state.setText("Shutdown 5/6: Park scope - goto zenith")
  screen.f_coord_zenith_eq6()
  time.sleep(1)
  screen.f_altaz_goto_eq6()
  time.sleep(5)

  screen.autooff_state.setText("Shutdown 5/6: Park scope - busy")
  for i in range(10):
    if 'EQMod Mount.RASTATUS.RAGoto' in indi_properties.keys() and indi_properties['EQMod Mount.RASTATUS.RAGoto'].lower() == 'ok':
      time.sleep(5)
    else:
      break
  for i in range(10):
    if 'EQMod Mount.DESTATUS.DEGoto' in indi_properties.keys() and indi_properties['EQMod Mount.DESTATUS.DEGoto'].lower() == 'ok':
      time.sleep(5)
    else:
      break
  screen.autooff_state.setText("Shutdown 5/6: Park scope - done")
  time.sleep(5)
  screen.mount_tracking_eq6.setChecked(False)
  time.sleep(6)

  for i in range(10):
    if 'EQMod Mount.TELESCOPE_TRACK_STATE.TRACK_ON' in indi_properties and indi_properties['EQMod Mount.TELESCOPE_TRACK_STATE.TRACK_ON'] != 'On':
      break
    mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_TRACK_STATE.TRACK_OFF=On'})
    time.sleep(6)


def f_autooff_cover():
  screen.f_bahtinov_angle_eq6(angle=8)
  time.sleep(5)

def f_autooff_alerting_off():
  screen.lab_phd2_alert_en.setChecked(False)

def t_autooff():
  global screen, kill_thread, phd2_working, cameras

  prev_enable_state = False
  step = 0

  while kill_thread == False:

    if screen.autooff_enable.isChecked() != prev_enable_state:
      prev_enable_state = screen.autooff_enable.isChecked()
      timestamp = f_autooff_date(hour = screen.autooff_hour.value(), minute = screen.autooff_minute.value())
    if screen.autooff_enable.isChecked():
      if screen.lab_phd2_mon_en.isChecked() == False:
        screen.lab_phd2_mon_en.setChecked(True)
      remaining = timestamp - int(time.time())
      screen.autooff_state.setText("ENABLED, seconds remaining: " + str(remaining))
      screen.autooff_state.setStyleSheet("background-color: #7cf29b;")
      if remaining < 0:
        screen.autooff_state.setStyleSheet("background-color: #ff8d03;")

        screen.autooff_state.setText("Shutdown 1/6: Disable alerting")
        try:
          f_autooff_alerting_off()
        except Exception as e:
          print(traceback.format_exc())

        if kill_thread:
          break

        screen.autooff_state.setText("Shutdown 2/6: Turnoff phd2")
        try:
          f_autooff_turnoff_phd()
        except Exception as e:
          print(traceback.format_exc())
        if kill_thread:
          break

        screen.autooff_state.setText("Shutdown 3/6: Stop file save")
        try:
          f_autooff_stop_file_save()
        except Exception as e:
          print(traceback.format_exc())
        if kill_thread:
          break

        screen.autooff_state.setText("Shutdown 4/6: Turnoff cameras")
        try:
          f_autooff_stop_cameras()
        except Exception as e:
          print(traceback.format_exc())
        if kill_thread:
          break

        #screen.autooff_state.setText("Shutdown 5/6: Park scope")
        #try:
        #  f_autooff_park_scope()
        #except Exception as e:
        #  print(traceback.format_exc())
        #if kill_thread:
        #  break

        screen.autooff_state.setText("Shutdown 6/6: Cover scope")
        try:
          f_autooff_cover()
        except Exception as e:
          print(traceback.format_exc())
        if kill_thread:
          break

        screen.autooff_enable.setChecked(False)

    else:
      screen.autooff_state.setText("OFF")
      screen.autooff_state.setStyleSheet("background-color: grey;")

    time.sleep(1)

#############################################################################################

def p_indi_getprop_update(q_ptc, q_ctp):
  local_indi_properties = {}
  mount_turned_on = False
  while True:
    if not q_ptc.empty():
      cmd = q_ptc.get()
      if cmd['cmd'] == 'shutdown':
        return
      elif cmd['cmd'] == 'mount_turned_on':
        mount_turned_on = cmd['mount_turned_on']
      else:
        print("In process " + str(inspect.stack()[0][3]) + " - unknown cmd: " + str(cmd['cmd']))

    if not q_ptc.empty():
      continue

    if mount_turned_on == False:
      time.sleep(0.2)
      continue

    try:
      out = subprocess.check_output('/usr/bin/timeout 2 /usr/bin/indi_getprop -t 1', shell=True)
    except:
      time.sleep(1)
      continue
      pass
    try:
      for line in out.splitlines():
        key, val = line.decode('utf8').split('=')
        if key.startswith('EQMod'):
          local_indi_properties[key] = val
      q_ctp.put({'indi_properties': local_indi_properties})
    except Exception as e:
      print(traceback.format_exc())
      time.sleep(1)
      pass
    time.sleep(0.1)

def t_indi_getprop_update():
  global indi_properties, indi_slider_valtab, indi_slider_paramtab, screen, eq6_stats, mpd, last_indi_response_time

  indi_properties = {}
  while kill_thread == False:
    time.sleep(0.3)

    if 'p_indi_getprop_update' in mpd:
      d = {
        'cmd': 'mount_turned_on',
        'mount_turned_on': screen.turn_on_mount_eq6.isChecked()
      }
      mpd['p_indi_getprop_update']['ptc'].put(d)

      if screen.turn_on_mount_eq6.isChecked() == False:
        indi_properties = {}
      if mpd['p_indi_getprop_update']['ctp'].qsize() == 0:
        continue
      el = mpd['p_indi_getprop_update']['ctp'].get()
      indi_properties = el['indi_properties']
      last_indi_response_time = time.time()
    else:
      time.sleep(1)
      continue


def f_setprop(prop):
  out = subprocess.check_output('/usr/bin/indi_setprop "' + prop + '"', shell=True)

def p_indi(q_ptc, q_ctp):
  while True:
    cmd = q_ptc.get()
    if cmd['cmd'] == 'shutdown':
      return
    elif cmd['cmd'] == 'indi_setprop':
      try:
        f_setprop(cmd['prop'])
      except Exception as e:
        print(traceback.format_exc(), flush=True)
        pass
    elif cmd['cmd'] == 'sync_telescope_pos':
      try:
        msg = 'diff ra: ' + str((cmd['new_ra'] - cmd['ra']).to_string(unit=u.hour)) + ' dec: ' + str(Angle(cmd['new_dec']) - Angle(cmd['dec']))
        q_ctp.put({'last_radec_diff': msg})
        f_setprop('EQMod Mount.HORIZONLIMITSLIMITGOTO.HORIZONLIMITSLIMITGOTODISABLE=On')
        f_setprop('EQMod Mount.HORIZONLIMITSONLIMIT.HORIZONLIMITSONLIMITTRACK=Off')
        f_setprop('EQMod Mount.HORIZONLIMITSONLIMIT.HORIZONLIMITSONLIMITSLEW=Off')
        f_setprop('EQMod Mount.HORIZONLIMITSONLIMIT.HORIZONLIMITSONLIMITGOTO=Off')
        f_setprop('EQMod Mount.ALIGNLIST.ALIGNLISTCLEAR=On')
        f_setprop('EQMod Mount.ALIGNMODE.ALIGNNEAREST=On')
        f_setprop('EQMod Mount.ON_COORD_SET.TRACK=Off')
        f_setprop('EQMod Mount.ON_COORD_SET.SLEW=Off')
        f_setprop('EQMod Mount.ON_COORD_SET.SYNC=On')
        time.sleep(1)
        f_setprop('EQMod Mount.EQUATORIAL_EOD_COORD.RA;DEC=' + str(cmd['new_ra'].hour) + ';' + str(Angle(cmd['new_dec']).degree))
      except Exception as e:
        print(traceback.format_exc(), flush=True)
        pass
    elif cmd['cmd'] == 'goto_telescope_pos':
      try:
        msg = 'diff ra: ' + str((cmd['new_ra'] - cmd['ra']).to_string(unit=u.hour)) + ' dec: ' + str(Angle(cmd['new_dec']) - Angle(cmd['dec']))
        q_ctp.put({'last_radec_diff': msg})
        f_setprop('EQMod Mount.ON_COORD_SET.TRACK=Off')
        f_setprop('EQMod Mount.ON_COORD_SET.SLEW=On')
        f_setprop('EQMod Mount.ON_COORD_SET.SYNC=Off')
        time.sleep(1)
        f_setprop('EQMod Mount.EQUATORIAL_EOD_COORD.RA;DEC=' + str(cmd['new_ra'].hour) + ';' + str(Angle(cmd['new_dec']).degree))
      except Exception as e:
        print(traceback.format_exc(), flush=True)
        pass
    else:
      print("In process " + str(inspect.stack()[0][3]) + " - unknown cmd: " + str(cmd['cmd']))

    time.sleep(0.1)


def f_restore_settings():
  global app_settings
  cfg_path = os.path.expanduser('~') + '/.astro_gui2.json'
  if os.path.isfile(cfg_path):
    f = open(cfg_path, 'r')
    app_settings = json.loads(f.read())
    f.close()

def f_save_settings():
  global screen
  cfg = {}

  cfg['a183mm_cam_circ_x'] = screen.a183mm_cam_circ_x.value()
  cfg['a183mm_cam_circ_y'] = screen.a183mm_cam_circ_y.value()
  cfg['a183mm_cam_circ_d'] = screen.a183mm_cam_circ_d.value()
  cfg['a183mm_cam_scale_focal'] = screen.a183mm_cam_scale_focal.value()

  cfg['a533mc_cam_circ_x'] = screen.a533mc_cam_circ_x.value()
  cfg['a533mc_cam_circ_y'] = screen.a533mc_cam_circ_y.value()
  cfg['a533mc_cam_circ_d'] = screen.a533mc_cam_circ_d.value()
  cfg['a533mc_cam_scale_focal'] = screen.a533mc_cam_scale_focal.value()

  cfg['a533mm_cam_circ_x'] = screen.a533mm_cam_circ_x.value()
  cfg['a533mm_cam_circ_y'] = screen.a533mm_cam_circ_y.value()
  cfg['a533mm_cam_circ_d'] = screen.a533mm_cam_circ_d.value()
  cfg['a533mm_cam_scale_focal'] = screen.a533mm_cam_scale_focal.value()

  cfg['a462mc_cam_circ_x'] = screen.a462mc_cam_circ_x.value()
  cfg['a462mc_cam_circ_y'] = screen.a462mc_cam_circ_y.value()
  cfg['a462mc_cam_circ_d'] = screen.a462mc_cam_circ_d.value()
  cfg['a462mc_cam_scale_focal'] = screen.a462mc_cam_scale_focal.value()

  cfg['a120mm_cam_circ_x'] = screen.a120mm_cam_circ_x.value()
  cfg['a120mm_cam_circ_y'] = screen.a120mm_cam_circ_y.value()
  cfg['a120mm_cam_circ_d'] = screen.a120mm_cam_circ_d.value()
  cfg['a120mm_cam_scale_focal'] = screen.a120mm_cam_scale_focal.value()

  cfg['a290mm_cam_circ_x'] = screen.a290mm_cam_circ_x.value()
  cfg['a290mm_cam_circ_y'] = screen.a290mm_cam_circ_y.value()
  cfg['a290mm_cam_circ_d'] = screen.a290mm_cam_circ_d.value()
  cfg['a290mm_cam_scale_focal'] = screen.a290mm_cam_scale_focal.value()

  cfg['a432mm_cam_circ_x'] = screen.a432mm_cam_circ_x.value()
  cfg['a432mm_cam_circ_y'] = screen.a432mm_cam_circ_y.value()
  cfg['a432mm_cam_circ_d'] = screen.a432mm_cam_circ_d.value()
  cfg['a432mm_cam_scale_focal'] = screen.a432mm_cam_scale_focal.value()

  cfg['a174mm_cam_circ_x'] = screen.a174mm_cam_circ_x.value()
  cfg['a174mm_cam_circ_y'] = screen.a174mm_cam_circ_y.value()
  cfg['a174mm_cam_circ_d'] = screen.a174mm_cam_circ_d.value()
  cfg['a174mm_cam_scale_focal'] = screen.a174mm_cam_scale_focal.value()

  cfg['a120mc_cam_circ_x'] = screen.a120mc_cam_circ_x.value()
  cfg['a120mc_cam_circ_y'] = screen.a120mc_cam_circ_y.value()
  cfg['a120mc_cam_circ_d'] = screen.a120mc_cam_circ_d.value()
  cfg['a120mc_cam_scale_focal'] = screen.a120mc_cam_scale_focal.value()

  cfg_path = os.path.expanduser('~') + '/.astro_gui2.json'
  f = open(cfg_path, 'w')
  f.write(json.dumps(cfg, indent=4))
  f.close()

def t_requests_send_eq6():
  global req_cmd_eq6, kill_thread, bahtinov_focus_working

  while kill_thread == False:
    if bahtinov_focus_working != True:
      time.sleep(1)
      continue
    if req_cmd_eq6.empty():
      time.sleep(0.2)
    else:
      payload = req_cmd_eq6.get()
      try:
        out = requests.post('http://eq4.embedded', data=json.dumps(payload), timeout=3)
      except Exception as e:
        print(traceback.format_exc())
        pass

def t_requests_send_eq5():
  global req_cmd_eq5, kill_thread, screen, eq5_stats

  while kill_thread == False:
    if req_cmd_eq5.empty():
      time.sleep(0.1)
    else:
      payload = req_cmd_eq5.get()
      if screen.turn_on_mount_eq5.isChecked():
        if payload['mode'] == 'radec' and 'position' in eq5_stats.keys():
          new_ra = Angle(payload['ra'])
          new_dec = Angle(payload['dec'])
          curr_ra = Angle(eq5_stats['position']['ra'])
          curr_dec = Angle(eq5_stats['position']['dec'])
          screen.last_radec_diff_eq5.setText('diff ra: ' + str((new_ra-curr_ra).to_string(unit=u.hour))  + ' dec: ' + str((new_dec-curr_dec).to_string(unit=u.deg)))
        try:
          out = requests.post('http://eq1-wifi.embedded', data=json.dumps(payload), timeout=3)
        except Exception as e:
          print(traceback.format_exc())
          pass
      else:
        print('dropping ' + str(payload))


def t_requests_canon_send():
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

def t_run_periodic_functions():
  global kill_thread, screen

  while kill_thread == False:
    try:
      screen.f_cam_update_values_universal(camname='a533mc')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_cam_update_values_universal(camname='a533mm')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_cam_update_values_universal(camname='a183mm')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_cam_update_values_universal(camname='a462mc')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_cam_update_values_universal(camname='a120mc')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_cam_update_values_universal(camname='a120mm')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_cam_update_values_universal(camname='a290mm')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_cam_update_values_universal(camname='a432mm')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_cam_update_values_universal(camname='a174mm')
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.print_eq6_position()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.print_eq5_position()
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
    time.sleep(0.3)

def p_ping_wifi_devices(q_ptc, q_ctp):
  while True:
    if not q_ptc.empty():
      cmd = q_ptc.get()
      if cmd['cmd'] == 'shutdown':
        return
      else:
        print("In process " + str(inspect.stack()[0][3]) + " - unknown cmd: " + str(cmd['cmd']))

    try:
      out = subprocess.check_output(['ping', '-w1', '-c1', 'eq4.embedded'])
    except:
      pass
    try:
      out = subprocess.check_output(['ping', '-w1', '-c1', 'eq3.embedded'])
    except:
      pass
    try:
      out = subprocess.check_output(['ping', '-w1', '-c1', 'eq2.embedded'])
    except:
      pass
    time.sleep(1)

def t_photo_refresh():
  global kill_thread, screen, viewer_a120mm_deployed, viewer_a462mc_deployed, viewer_a120mc_deployed, viewer_a183mm_deployed, viewer_a533mc_deployed, viewer_a533mm_deployed, viewer_a290mm_deployed, viewer_a174mm_deployed, viewer_a432mm_deployed

  while kill_thread == False:
    try:
      if viewer_canon_deployed and screen.t_prawy.currentIndex() == 9:
        screen.f_canon_window_refresh_event()
      if viewer_a120mc_deployed and screen.t_prawy.currentIndex() == 8:
        screen.f_a120mc_window_refresh_event()
      if viewer_a174mm_deployed and screen.t_prawy.currentIndex() == 7:
        screen.f_a174mm_window_refresh_event()
      if viewer_a290mm_deployed and screen.t_prawy.currentIndex() == 6:
        screen.f_a290mm_window_refresh_event()
      if viewer_a120mm_deployed and screen.t_prawy.currentIndex() == 5:
        screen.f_a120mm_window_refresh_event()
      if viewer_a462mc_deployed and screen.t_prawy.currentIndex() == 4:
        screen.f_a462mc_window_refresh_event()
      if viewer_a432mm_deployed and screen.t_prawy.currentIndex() == 3:
        screen.f_a432mm_window_refresh_event()
      if viewer_a533mc_deployed and screen.t_prawy.currentIndex() == 2:
        screen.f_a533mc_window_refresh_event()
      if viewer_a533mm_deployed and screen.t_prawy.currentIndex() == 1:
        screen.f_a533mm_window_refresh_event()
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

  last_frame_saved_time = 0.0
  while not kill_thread:
    while not queue and not kill_thread:
      time.sleep(0.1)
    if kill_thread:
      break

    frame = queue.popleft()

    if last_frame_saved_time + frame['save_delay'] >= frame['time']:
      continue

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
    '.filter1_' + str(frame['filter1']) +\
    '.filter2_' + str(frame['filter2']) +\
    '.tiff'

    last_frame_saved_time = frame['time']

    tifffile.imwrite(filename, frame['raw_data'], compress=1)

def t_save_a183mm_img():
  global q_a183mm_save_to_file
  f_save_img_universal(queue=q_a183mm_save_to_file)

def t_save_a533mc_img():
  global q_a533mc_save_to_file
  f_save_img_universal(queue=q_a533mc_save_to_file)

def t_save_a533mm_img():
  global q_a533mm_save_to_file
  f_save_img_universal(queue=q_a533mm_save_to_file)

def t_save_a462mc_img():
  global q_a462mc_save_to_file
  f_save_img_universal(queue=q_a462mc_save_to_file)

def t_save_a120mm_img():
  global q_a120mm_save_to_file
  f_save_img_universal(queue=q_a120mm_save_to_file)

def t_save_a290mm_img():
  global q_a290mm_save_to_file
  f_save_img_universal(queue=q_a290mm_save_to_file)

def t_save_a432mm_img():
  global q_a432mm_save_to_file
  f_save_img_universal(queue=q_a432mm_save_to_file)

def t_save_a174mm_img():
  global q_a174mm_save_to_file
  f_save_img_universal(queue=q_a174mm_save_to_file)

def t_save_a120mc_img():
  global q_a120mc_save_to_file
  f_save_img_universal(queue=q_a120mc_save_to_file)


#############################################################################################
def f_universal_plate_solve_run(q_platesolve, camname, lab_plate_solve_status, radius, cam_scale_pixel_scale, downsample, cam_scale_pixel_size, cam_scale_focal, mount_eq6):
  global eq5_stats, eq6_stats, plate_solve_results, kill_thread, screen, req_cmd_eq5, req_cmd_eq6, cameras, mpd

  lab_plate_solve_status.setText('Plate solve status: WAITING FOR FRAME...')
  while not q_platesolve and not kill_thread:
    time.sleep(0.1)

  frame = q_platesolve.popleft()
  frame['gray16'] = cv2.cvtColor(frame['frameRGB16'], cv2.COLOR_RGB2GRAY)
  frame['gray'] = cv2.cvtColor(frame['frameRGB'], cv2.COLOR_RGB2GRAY)

  if camname == 'file_to_align':
    rotated_frame16 = frame['gray16'].copy()
    rotated_frame = frame['gray16'].copy()
  else:
    rotated_frame16 = screen.f_rotate_frame(frame=frame['gray16'], rotate=cameras[camname]['rotate'])
    rotated_frame = screen.f_rotate_frame(frame=frame['gray'], rotate=cameras[camname]['rotate'])

  stretched = screen.f_normalize(frame=rotated_frame16, normalize=True, low=0.05, high=99.5)

  out = subprocess.check_output(['rm', '-rf', '/dev/shm/' + camname + '_platesolve'])
  out = subprocess.check_output(['mkdir', '-p', '/dev/shm/' + camname + '_platesolve'])
  cv2.imwrite('/dev/shm/' + camname + '_platesolve/frame.jpg', stretched)
  cv2.imwrite('/dev/shm/' + camname + '_platesolve/frame_ann.jpg', rotated_frame)

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
    str(downsample),
  ]
  platesolve_cmd_1a = [
    'solve-field',
    '--scale-units',
    'arcsecperpix',
    '--no-plots',
    '--downsample',
    str(downsample),
  ]
  if camname != 'file_to_align':
    if mount_eq6:
      platesolve_cmd_2 = [
        '--ra',
        Angle(eq6_stats['ra']).to_string(sep=':', precision=0),
        '--dec',
        Angle(eq6_stats['dec']).to_string(sep=':', precision=0),
        '--radius',
        '2',
      ]
    else:
      platesolve_cmd_2 = [
        '--ra',
        Angle(Angle(eq5_stats['position']['ra'])).to_string(sep=':', precision=0),
        '--dec',
        Angle(Angle(eq5_stats['position']['dec'])).to_string(sep=':', precision=0),
        '--radius',
        '2',
      ]
  platesolve_cmd_3 = [
    '--temp-dir',
    '/dev/shm/' + camname + '_platesolve',
    '/dev/shm/' + camname + '_platesolve/frame.jpg'
  ]

  if camname == 'file_to_align':
    platesolve_cmd = platesolve_cmd_1a + platesolve_cmd_3
  else:
    if radius:
      platesolve_cmd = platesolve_cmd_1 + platesolve_cmd_2 + platesolve_cmd_3
    else:
      platesolve_cmd = platesolve_cmd_1 + platesolve_cmd_3

  try:
    lab_plate_solve_status.setText('Plate solve status: SOLVING...')
    out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
    lab_plate_solve_status.setText('Plate solve status: PLOTTING...')
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
    coord_jnow = SkyCoord(ra=_ra, dec=_dec, frame="fk5").transform_to(FK5(equinox=eq6_stats['epoch']))

    if camname == 'file_to_align':
      eq6_stats['file_to_align_ra'] = Angle(coord_jnow.ra)
      eq6_stats['file_to_align_dec'] = Angle(coord_jnow.dec)
    else:
      if mount_eq6:
        eq6_stats['new_ra'] = Angle(coord_jnow.ra)
        eq6_stats['new_dec'] = Angle(coord_jnow.dec)
        c = {
          'cmd': 'sync_telescope_pos',
          'new_ra': eq6_stats['new_ra'],
          'ra': eq6_stats['ra'],
          'dec': str(eq6_stats['dec']),
          'new_dec': str(eq6_stats['new_dec']),
        }
        mpd['p_indi']['ptc'].put(c)
      else:
        new_ra =  Angle(coord_jnow.ra)
        new_dec = Angle(coord_jnow.dec)

        payload = {
          'mode': 'radec',
          'ra': new_ra.to_string(),
          'dec': new_dec.to_string(),
          'move': False,
          'update_pos': True
        }
        req_cmd_eq5.put(payload)

    grid = 0.1
    px_scale = opts['pixscale']
    if camname == 'file_to_align':
      screen.file_to_align_px_scale.setText('Px scale: ' + str(px_scale))
    else:
      cam_scale_pixel_size.setValue(float(cameras[camname]['info']['PixelSize']))
      cam_scale_focal.setValue(int(float(cameras[camname]['info']['PixelSize'])  * 206.265 / float(px_scale)))

      if float(px_scale) < 0.75:
        grid = 0.02

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

    plotann_arr1 = [
      'plotann.py',
      '/dev/shm/' + camname + '_platesolve/frame.wcs',
      '/dev/shm/' + camname + '_platesolve/frame_ann.jpg',
      '/dev/shm/' + camname + '_platesolve/frame_hdcat.jpg',
      '--hdcat=/home/dom/GIT/puppet/astro/astrometry_catalogs/hd.fits',
      '--grid-size=' + str(grid),
      '--grid-label=' + str(grid),
      '--no-bright',
      '--no-const',
    ]
    out1 = subprocess.Popen(plotann_arr1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    plotann_arr2 = [
      'plotann.py',
      '/dev/shm/' + camname + '_platesolve/frame.wcs',
      '/dev/shm/' + camname + '_platesolve/frame_ann.jpg',
      '/dev/shm/' + camname + '_platesolve/frame_tycho2cat.jpg',
      '--tycho2cat=/home/dom/GIT/puppet/astro/astrometry_catalogs/tycho2.kd',
      '--grid-size=' + str(grid),
      '--grid-label=' + str(grid),
      '--no-bright',
      '--no-const',
      '--no-ngc',
    ]
    out2 = subprocess.Popen(plotann_arr2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    plotann_arr3 = [
      'plotann.py',
      '/dev/shm/' + camname + '_platesolve/frame.wcs',
      '/dev/shm/' + camname + '_platesolve/frame_ann.jpg',
      '/dev/shm/' + camname + '_platesolve/frame_galaxy.jpg',
      '--uzccat=/home/dom/GIT/puppet/astro/astrometry_catalogs/uzc2000.fits',
      '--abellcat=/home/dom/GIT/puppet/astro/astrometry_catalogs/abell-all.fits',
      '--grid-size=' + str(grid),
      '--grid-label=' + str(grid),
      '--no-bright',
      '--no-const',
      '--no-ngc',
    ]
    out3 = subprocess.Popen(plotann_arr3, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    out1.wait()
    out2.wait()
    out3.wait()

    plate_solve_results['hdcat'] = cv2.imread('/dev/shm/' + camname + '_platesolve/frame_hdcat.jpg')
    plate_solve_results['tycho2cat'] = cv2.imread('/dev/shm/' + camname + '_platesolve/frame_tycho2cat.jpg')
    plate_solve_results['galaxy'] = cv2.imread('/dev/shm/' + camname + '_platesolve/frame_galaxy.jpg')

    print(plate_solve_results['url'])
    lab_plate_solve_status.setText('Plate solve status: DONE at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    screen.f_solved_tabs_refresh_event()
  except Exception as e:
    print(traceback.format_exc())
    lab_plate_solve_status.setText('Plate solve status: FAILED at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    pass
#############################################################################################

def t_a183mm_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a183mm, run_plate_solve_a183mm_mount_eq6


  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a183mm:
      run_plate_solve_a183mm = False
      f_universal_plate_solve_run(
        camname = 'a183mm',
        radius = screen.a183mm_cam_solve_radius.isChecked(),
        q_platesolve = q_a183mm_platesolve,
        lab_plate_solve_status = screen.lab_a183mm_plate_solve_status,
        cam_scale_pixel_scale = screen.a183mm_cam_scale_pixel_scale,
        downsample = screen.a183mm_downsample.value(),
        cam_scale_pixel_size = screen.a183mm_cam_scale_pixel_size,
        cam_scale_focal = screen.a183mm_cam_scale_focal,
        mount_eq6 = run_plate_solve_a183mm_mount_eq6,
      )

def t_a533mm_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a533mm, run_plate_solve_a533mm_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a533mm:
      run_plate_solve_a533mm = False
      f_universal_plate_solve_run(
        camname = 'a533mm',
        radius = screen.a533mm_cam_solve_radius.isChecked(),
        q_platesolve = q_a533mm_platesolve,
        lab_plate_solve_status = screen.lab_a533mm_plate_solve_status,
        cam_scale_pixel_scale = screen.a533mm_cam_scale_pixel_scale,
        downsample = screen.a533mm_downsample.value(),
        cam_scale_pixel_size = screen.a533mm_cam_scale_pixel_size,
        cam_scale_focal = screen.a533mm_cam_scale_focal,
        mount_eq6 = run_plate_solve_a533mm_mount_eq6,
      )

def t_a533mc_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a533mc, run_plate_solve_a533mc_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a533mc:
      run_plate_solve_a533mc = False
      f_universal_plate_solve_run(
        camname = 'a533mc',
        radius = screen.a533mc_cam_solve_radius.isChecked(),
        q_platesolve = q_a533mc_platesolve,
        lab_plate_solve_status = screen.lab_a533mc_plate_solve_status,
        cam_scale_pixel_scale = screen.a533mc_cam_scale_pixel_scale,
        downsample = screen.a533mc_downsample.value(),
        cam_scale_pixel_size = screen.a533mc_cam_scale_pixel_size,
        cam_scale_focal = screen.a533mc_cam_scale_focal,
        mount_eq6 = run_plate_solve_a533mc_mount_eq6,
      )

def t_a462mc_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a462mc, run_plate_solve_a462mc_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a462mc:
      run_plate_solve_a462mc = False
      f_universal_plate_solve_run(
        camname = 'a462mc',
        radius = screen.a462mc_cam_solve_radius.isChecked(),
        q_platesolve = q_a462mc_platesolve,
        lab_plate_solve_status = screen.lab_a462mc_plate_solve_status,
        cam_scale_pixel_scale = screen.a462mc_cam_scale_pixel_scale,
        downsample = screen.a462mc_downsample.value(),
        cam_scale_pixel_size = screen.a462mc_cam_scale_pixel_size,
        cam_scale_focal = screen.a462mc_cam_scale_focal,
        mount_eq6 = run_plate_solve_a462mc_mount_eq6,
      )

def t_a120mc_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_a120mc, run_plate_solve_a120mc_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a120mc:
      run_plate_solve_a120mc = False
      f_universal_plate_solve_run(
        camname = 'a120mc',
        radius = screen.a120mc_cam_solve_radius.isChecked(),
        q_platesolve = q_a120mc_platesolve,
        lab_plate_solve_status = screen.lab_a120mc_plate_solve_status,
        cam_scale_pixel_scale = screen.a120mc_cam_scale_pixel_scale,
        downsample = screen.a120mc_downsample.value(),
        cam_scale_pixel_size = screen.a120mc_cam_scale_pixel_size,
        cam_scale_focal = screen.a120mc_cam_scale_focal,
        mount_eq6 = run_plate_solve_a120mc_mount_eq6,
      )

def t_a120mm_plate_solve_loop():

  global screen, kill_thread, run_plate_solve_a120mm, run_plate_solve_a120mm_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a120mm:
      run_plate_solve_a120mm = False
      f_universal_plate_solve_run(
        camname = 'a120mm',
        radius = screen.a120mm_cam_solve_radius.isChecked(),
        q_platesolve = q_a120mm_platesolve,
        lab_plate_solve_status = screen.lab_a120mm_plate_solve_status,
        cam_scale_pixel_scale = screen.a120mm_cam_scale_pixel_scale,
        downsample = screen.a120mm_downsample.value(),
        cam_scale_pixel_size = screen.a120mm_cam_scale_pixel_size,
        cam_scale_focal = screen.a120mm_cam_scale_focal,
        mount_eq6 = run_plate_solve_a120mm_mount_eq6,
      )

def t_a290mm_plate_solve_loop():

  global screen, kill_thread, run_plate_solve_a290mm, run_plate_solve_a290mm_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a290mm:
      run_plate_solve_a290mm = False
      f_universal_plate_solve_run(
        camname = 'a290mm',
        radius = screen.a290mm_cam_solve_radius.isChecked(),
        q_platesolve = q_a290mm_platesolve,
        lab_plate_solve_status = screen.lab_a290mm_plate_solve_status,
        cam_scale_pixel_scale = screen.a290mm_cam_scale_pixel_scale,
        downsample = screen.a290mm_downsample.value(),
        cam_scale_pixel_size = screen.a290mm_cam_scale_pixel_size,
        cam_scale_focal = screen.a290mm_cam_scale_focal,
        mount_eq6 = run_plate_solve_a290mm_mount_eq6,
      )

def t_a432mm_plate_solve_loop():

  global screen, kill_thread, run_plate_solve_a432mm, run_plate_solve_a432mm_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a432mm:
      run_plate_solve_a432mm = False
      f_universal_plate_solve_run(
        camname = 'a432mm',
        radius = screen.a432mm_cam_solve_radius.isChecked(),
        q_platesolve = q_a432mm_platesolve,
        lab_plate_solve_status = screen.lab_a432mm_plate_solve_status,
        cam_scale_pixel_scale = screen.a432mm_cam_scale_pixel_scale,
        downsample = screen.a432mm_downsample.value(),
        cam_scale_pixel_size = screen.a432mm_cam_scale_pixel_size,
        cam_scale_focal = screen.a432mm_cam_scale_focal,
        mount_eq6 = run_plate_solve_a432mm_mount_eq6,
      )

def t_a174mm_plate_solve_loop():

  global screen, kill_thread, run_plate_solve_a174mm, run_plate_solve_a174mm_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_a174mm:
      run_plate_solve_a174mm = False
      f_universal_plate_solve_run(
        camname = 'a174mm',
        radius = screen.a174mm_cam_solve_radius.isChecked(),
        q_platesolve = q_a174mm_platesolve,
        lab_plate_solve_status = screen.lab_a174mm_plate_solve_status,
        cam_scale_pixel_scale = screen.a174mm_cam_scale_pixel_scale,
        downsample = screen.a174mm_downsample.value(),
        cam_scale_pixel_size = screen.a174mm_cam_scale_pixel_size,
        cam_scale_focal = screen.a174mm_cam_scale_focal,
        mount_eq6 = run_plate_solve_a174mm_mount_eq6,
      )

def t_canon_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_canon, run_plate_solve_canon_mount_eq6

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
        downsample = screen.canon_downsample.value(),
        cam_scale_pixel_size = screen.canon_scale_pixel_size,
        cam_scale_focal = screen.canon_scale_focal,
        mount_eq6 = run_plate_solve_canon_mount_eq6,
      )

def t_file_to_align_plate_solve_loop():
  global screen, kill_thread, run_plate_solve_file_to_align, run_plate_solve_file_to_align_mount_eq6

  while not kill_thread:
    time.sleep(0.5)
    if run_plate_solve_file_to_align:
      run_plate_solve_file_to_align = False
      f_universal_plate_solve_run(
        camname = 'file_to_align',
        radius = False,
        q_platesolve = q_file_to_align_platesolve,
        lab_plate_solve_status = screen.file_to_align_platesolve_state,
        cam_scale_pixel_scale = screen.canon_scale_pixel_scale,
        downsample = 2,
        cam_scale_pixel_size = None,
        cam_scale_focal = None,
        mount_eq6 = run_plate_solve_file_to_align_mount_eq6,
      )

#############################################################################################


def t_a183mm_preview():
  camname      = 'a183mm'
  color_scheme = cv2.COLOR_GRAY2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_a533mm_preview():
  camname      = 'a533mm'
  color_scheme = cv2.COLOR_GRAY2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_a533mc_preview():
  camname      = 'a533mc'
  color_scheme = cv2.COLOR_BAYER_RG2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_a462mc_preview():
  camname      = 'a462mc'
  color_scheme = cv2.COLOR_BAYER_RG2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_a120mc_preview():
  camname      = 'a120mc'
  color_scheme = cv2.COLOR_BAYER_GR2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_a120mm_preview():
  camname      = 'a120mm'
  color_scheme = cv2.COLOR_GRAY2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_a174mm_preview():
  camname      = 'a174mm'
  color_scheme = cv2.COLOR_GRAY2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_a290mm_preview():
  camname      = 'a290mm'
  color_scheme = cv2.COLOR_GRAY2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_a432mm_preview():
  camname      = 'a432mm'
  color_scheme = cv2.COLOR_GRAY2RGB
  f_camera_universal(camname=camname, color_scheme=color_scheme)

def t_camera_parse_raw_frame(cam_var, color_scheme):
  global screen, cameras, filters_set, kill_thread
  global q_a183mm_ready, q_a183mm_platesolve, q_a183mm_save_to_file, q_a183mm_raw
  global q_a533mm_ready, q_a533mm_platesolve, q_a533mm_save_to_file, q_a533mm_raw
  global q_a533mc_ready, q_a533mc_platesolve, q_a533mc_save_to_file, q_a533mc_raw
  global q_a462mc_ready, q_a462mc_platesolve, q_a462mc_save_to_file, q_a462mc_raw
  global q_a120mc_ready, q_a120mc_platesolve, q_a120mc_save_to_file, q_a120mc_raw
  global q_a120mm_ready, q_a120mm_platesolve, q_a120mm_save_to_file, q_a120mm_raw
  global q_a174mm_ready, q_a174mm_platesolve, q_a174mm_save_to_file, q_a174mm_raw
  global q_a290mm_ready, q_a290mm_platesolve, q_a290mm_save_to_file, q_a290mm_raw
  global q_a432mm_ready, q_a432mm_platesolve, q_a432mm_save_to_file, q_a432mm_raw

  q_raw             = globals()['q_' + cam_var + '_raw']
  q_ready           = globals()['q_' + cam_var + '_ready']
  q_platesolve      = globals()['q_' + cam_var + '_platesolve']
  q_save_to_file    = globals()['q_' + cam_var + '_save_to_file']
  cam_save_dirname  = getattr(screen,cam_var + '_cam_save_dirname')
  cam_exp_slider    = getattr(screen,cam_var + '_cam_exp_slider')
  cam_offset_slider = getattr(screen,cam_var + '_cam_offset_slider')
  cam_gain_slider   = getattr(screen,cam_var + '_cam_gain_slider')
  cam_bin           = getattr(screen,cam_var + '_cam_bin')
  cam_save_img      = getattr(screen,cam_var + '_cam_save_img')
  save_delay        = getattr(screen,cam_var + '_cam_save_delay')

  while not kill_thread and not cameras[cam_var]['kill_thread']:
    try:
      if not q_raw:
        time.sleep(0.1)
        continue

      save_frame = q_raw.popleft()
      other_frame = {
        'time': save_frame['time'],
      }
      debayer = cv2.cvtColor(save_frame['raw_data'], color_scheme)
      other_frame['frameRGB'] = (debayer/256).astype('uint8')
      other_frame['frameRGB16'] = debayer.copy()
      c = np.percentile(save_frame['raw_data'],[0,1,50,99,99.99])
      other_frame['percentile_stat'] = "0: " + str(round(c[0])) + ",   1: " + str(round(c[1])) + ",   50: " + str(round(c[2])) + ",   99: " + str(round(c[3])) + ",   99.99: " + str(round(c[4]))

      if cam_save_img.isChecked():
        save_frame['dirname'] = str(cam_save_dirname.text())
        save_frame['exposure'] = int(cam_exp_slider.value())
        save_frame['offset'] = int(cam_offset_slider.value())
        save_frame['gain'] = int(cam_gain_slider.value())
        save_frame['bin'] = int(cam_bin.currentText())
        save_frame['camname'] = cam_var
        save_frame['filter1'] = filters_set[0]
        save_frame['filter2'] = filters_set[1]
        save_frame['save_delay'] = float(save_delay.value())
        if cam_var in cameras.keys() and 'info' in cameras[cam_var].keys() and 'temperature' in cameras[cam_var]['info'].keys():
          save_frame['temperature'] = cameras[cam_var]['info']['temperature']
          save_frame['iscolor'] = cameras[cam_var]['info']['IsColorCam']
        else:
          save_frame['temperature'] = 'nan'
        q_save_to_file.append(save_frame)

      q_ready.append(other_frame)
      q_platesolve.append(other_frame)

    except Exception as e:
      print(traceback.format_exc())
      time.sleep(0.01)
      pass

def f_camera_setup(camname):
  global asi, cameras

  cameras_found = asi.list_cameras()
  cameras[camname]['camera'] = asi.Camera(cameras_found.index(cameras[camname]['name']))
  cameras[camname]['camera'].stop_video_capture()
  cameras[camname]['camera'].stop_exposure()
  cameras[camname]['camera'].set_control_value(asi.ASI_BANDWIDTHOVERLOAD, int(cameras[camname]['camera'].get_controls()['BandWidth']['MaxValue']*0.7))
  cameras[camname]['camera'].disable_dark_subtract()
  cameras[camname]['camera'].set_control_value(asi.ASI_EXPOSURE, 1000000)
  cameras[camname]['camera'].set_control_value(asi.ASI_GAIN,     0)
  cameras[camname]['camera'].set_control_value(asi.ASI_OFFSET,   8)
  cameras[camname]['camera'].set_roi(bins=1)
  cameras[camname]['camera'].set_image_type(asi.ASI_IMG_RAW16)


def f_camera_set_values(camname):
  global cameras

  cameras[camname]['info'] = {}
  cameras[camname]['info']['temperature'] = cameras[camname]['camera'].get_control_value(asi.ASI_TEMPERATURE)[0]/10

  for i in ['SupportedBins', 'IsColorCam', 'PixelSize', 'IsCoolerCam']:
    cameras[camname]['info'][i] = cameras[camname]['camera'].get_camera_property()[i]

  params_tab   = ['Exposure', 'Gain', 'Offset']
  if cameras[camname]['info']['IsCoolerCam']:
    params_tab.append('TargetTemp')
    params_tab.append('CoolerOn')

  for i in params_tab:
    cameras[camname][i] = {}
    for j in ['DefaultValue', 'MinValue', 'MaxValue']:
      cameras[camname][i][j] = cameras[camname]['camera'].get_controls()[i][j]
    cameras[camname][i]['Value'] = cameras[camname][i]['DefaultValue']

  cameras[camname]['HardwareBin'] = {
    'DefaultValue': cameras[camname]['info']['SupportedBins'][0],
    'MinValue': cameras[camname]['info']['SupportedBins'][0],
    'MaxValue': cameras[camname]['info']['SupportedBins'][-1],
    'Value': cameras[camname]['info']['SupportedBins'][0],
    'depl': cameras[camname]['info']['SupportedBins'][0],
  }

  if cameras[camname]['info']['IsCoolerCam']:
    cameras[camname]['camera'].set_control_value(asi.ASI_TARGET_TEMP, 0)
    cameras[camname]['camera'].set_control_value(asi.ASI_COOLER_ON,   False)
    cameras[camname]['info']['cooler_pwr'] = cameras[camname]['camera'].get_control_value(asi.ASI_COOLER_POWER_PERC)[0]

  if cameras[camname]['info']['IsColorCam']:
    cameras[camname]['camera'].set_control_value(asi.ASI_WB_B, int(cameras[camname]['camera'].get_controls()['WB_B']['DefaultValue']))
    cameras[camname]['camera'].set_control_value(asi.ASI_WB_R, int(cameras[camname]['camera'].get_controls()['WB_R']['DefaultValue']))

  cameras[camname]['Exposure']['Value']   = 1000000
  cameras[camname]['Gain']['Value']       = 0
  cameras[camname]['Offset']['Value']     = 8
  if cameras[camname]['info']['IsCoolerCam']:
    cameras[camname]['CoolerOn']['Value']   = False
  cameras[camname]['param_time'] = time.time()
  cameras[camname]['kill_thread'] = False


def f_set_gui_camera_values(camname):
  global cameras, screen

  cam_exp_slider    = getattr(screen,camname + '_cam_exp_slider')
  cam_offset_slider = getattr(screen,camname + '_cam_offset_slider')
  cam_gain_slider   = getattr(screen,camname + '_cam_gain_slider')
  cam_bin           = getattr(screen,camname + '_cam_bin')
  if cameras[camname]['info']['IsCoolerCam']:
    cam_cooler      = getattr(screen,camname + '_cam_cooler')
    cam_target_temp = getattr(screen,camname + '_cam_target_temp_slider')

  cam_exp_slider.setMinimum(cameras[camname]['Exposure']['MinValue']/1000)
  cam_exp_slider.setMaximum(cameras[camname]['Exposure']['MaxValue']/1000)
  cam_gain_slider.setMinimum(cameras[camname]['Gain']['MinValue'])
  cam_gain_slider.setMaximum(cameras[camname]['Gain']['MaxValue'])
  cam_offset_slider.setMinimum(cameras[camname]['Offset']['MinValue'])
  cam_offset_slider.setMaximum(cameras[camname]['Offset']['MaxValue'])
  if cameras[camname]['info']['IsCoolerCam']:
    cam_target_temp.setMinimum(cameras[camname]['TargetTemp']['MinValue'])
    cam_target_temp.setMaximum(cameras[camname]['TargetTemp']['MaxValue'])

  cam_exp_slider.setValue(float(cameras[camname]['Exposure']['Value']/1000))
  cam_gain_slider.setValue(cameras[camname]['Gain']['Value'])
  cam_offset_slider.setValue(cameras[camname]['Offset']['Value'])
  if cameras[camname]['info']['IsCoolerCam']:
    cam_cooler.setChecked(False)
    cam_target_temp.setValue(0)
  cameras[camname]['Rotate'] = 0

  cam_bin.clear()
  for i in range(cameras[camname]['HardwareBin']['MinValue'], cameras[camname]['HardwareBin']['MaxValue']+1):
    cam_bin.addItem(str(i))
  cam_bin.setCurrentIndex(0)

def t_camera_image(camname, color_scheme):
  global cameras, kill_thread
  global q_a183mm_raw, q_a183mm_raw, q_a533mm_raw, q_a533mc_raw, q_a462mc_raw, q_a120mc_raw, q_a120mm_raw, q_a174mm_raw, q_a432mm_raw, q_a290mm_raw

  out = False
  q_raw = globals()['q_' + camname + '_raw']
  while not kill_thread and not cameras[camname]['kill_thread']:
    try:
      cameras[camname]['camera'].stop_exposure()
      cameras[camname]['camera'].set_image_type(asi.ASI_IMG_RAW16)
      out = cameras[camname]['camera'].capture(initial_sleep=False, poll=0.001)
      _frame = {
        'time': time.time(),
        'raw_data': out,
      }
      q_raw.append(_frame)
      d = time.time()
    except:
      print(traceback.format_exc(), flush=True)
      time.sleep(1)
      pass

def f_check_cam_param_change(camname):
  global cameras, screen

  cameras[camname]['info']['temperature'] = cameras[camname]['camera'].get_control_value(asi.ASI_TEMPERATURE)[0]/10

  cam_exp_slider    = getattr(screen,camname + '_cam_exp_slider')
  cam_offset_slider = getattr(screen,camname + '_cam_offset_slider')
  cam_gain_slider   = getattr(screen,camname + '_cam_gain_slider')
  cam_bin           = getattr(screen,camname + '_cam_bin')
  if cameras[camname]['info']['IsCoolerCam']:
    cam_cooler      = getattr(screen,camname + '_cam_cooler')
    cam_target_temp = getattr(screen,camname + '_cam_target_temp_slider')


  if cameras[camname]['camera'].get_control_value(asi.ASI_EXPOSURE)[0]/1000 != float(cam_exp_slider.value()) or cameras[camname]['camera'].get_control_value(asi.ASI_GAIN)[0] != int(cam_gain_slider.value()) or cameras[camname]['camera'].get_control_value(asi.ASI_OFFSET)[0] != int(cam_offset_slider.value()) or (cam_bin.currentText() != 'NULL' and cameras[camname]['HardwareBin']['Value'] != int(cam_bin.currentText())):
    cameras[camname]['camera'].set_control_value(asi.ASI_EXPOSURE,      int(cam_exp_slider.value()*1000.0))
    cameras[camname]['camera'].set_control_value(asi.ASI_GAIN,          int(cam_gain_slider.value()))
    cameras[camname]['camera'].set_control_value(asi.ASI_OFFSET,        int(cam_offset_slider.value()))
    if cam_bin.currentText() != 'NULL':
      cameras[camname]['camera'].set_roi(bins=int(cam_bin.currentText()))
      cameras[camname]['HardwareBin']['value'] = cameras[camname]['camera'].get_roi_format()[2]
    cameras[camname]['camera'].stop_exposure()
    cameras[camname]['camera'].stop_video_capture()
    cameras[camname]['param_time'] = time.time()
  cameras[camname]['Exposure']['Value']    = cameras[camname]['camera'].get_control_value(asi.ASI_EXPOSURE)[0]/1000
  cameras[camname]['Gain']['Value']        = cameras[camname]['camera'].get_control_value(asi.ASI_GAIN)[0]
  cameras[camname]['Offset']['Value']      = cameras[camname]['camera'].get_control_value(asi.ASI_OFFSET)[0]


  if cameras[camname]['info']['IsCoolerCam']:
    if cameras[camname]['camera'].get_control_value(asi.ASI_COOLER_ON)[0] != cam_cooler.isChecked() or cameras[camname]['camera'].get_control_value(asi.ASI_TARGET_TEMP)[0] != cam_target_temp.value():
      cameras[camname]['camera'].set_control_value(asi.ASI_TARGET_TEMP, int(cam_target_temp.value()))
      cameras[camname]['camera'].set_control_value(asi.ASI_COOLER_ON,   cam_cooler.isChecked())
      cameras[camname]['param_time'] = time.time()
    cameras[camname]['CoolerOn']['Value']   = cameras[camname]['camera'].get_control_value(asi.ASI_COOLER_ON)[0]
    cameras[camname]['info']['cooler_pwr'] = cameras[camname]['camera'].get_control_value(asi.ASI_COOLER_POWER_PERC)[0]

def f_camera_universal(camname, color_scheme):
  global screen, kill_thread, cameras

  thread = None
  thread2 = None
  while not kill_thread:
    time.sleep(1)
    if getattr(screen,camname + '_cam_on').isChecked():
      if thread == None:
        if 'camera' in cameras[camname].keys():
          cameras[camname]['camera'].close()
          temp = cameras[camname]['name']
          del cameras[camname]
          cameras[camname] = {}
          cameras[camname]['name'] = temp
        try:
          f_camera_setup(camname=camname)
        except:
          print(traceback.format_exc(), flush=True)
          time.sleep(1)
          continue
          pass
        f_camera_set_values(camname=camname)
        f_set_gui_camera_values(camname=camname)

        thread = threading.Thread(target=t_camera_image, args=(camname, color_scheme))
        thread.start()
        thread2 = threading.Thread(target=t_camera_parse_raw_frame, args=(camname, color_scheme))
        thread2.start()

      else:
        f_check_cam_param_change(camname=camname)
    else:
      if thread != None:
        cameras[camname]['kill_thread'] = True
        cameras[camname]['camera'].stop_exposure()
        cameras[camname]['camera'].stop_video_capture()
        thread.join()
        thread = None
        thread2.join()
        thread2 = None
        if 'camera' in cameras[camname].keys():
          cameras[camname]['camera'].close()
          temp = cameras[camname]['name']
          del cameras[camname]
          cameras[camname] = {}
          cameras[camname]['name'] = temp

####################################################################################

def t_canon_preview():
  global cam_canon, q_canon_raw, kill_thread

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


def t_canon_frame_processing():
  global q_canon_raw, q_canon_ready, q_canon_platesolve
  global screen

  while kill_thread == False:
    while kill_thread == False and not q_canon_raw:
      time.sleep(0.1)
    if kill_thread:
      break
    raw_frame = q_canon_raw.popleft()
    ready_frame = {
      'time': raw_frame['time']
    }
    ready_frame['frameRGB'] = (ready_frame['raw_data']/256).astype('uint8')

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
  global req_cmd_eq6

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
    self.lewy_tab10 = QWidget()
    self.lewy_tab11 = QWidget()
    self.lewy_tab12 = QWidget()
    self.lewy_tab13 = QWidget()
    self.lewy_tab14 = QWidget()
    self.t_lewy.addTab(self.lewy_tab1, "EQ6")
    self.t_lewy.addTab(self.lewy_tab2, "EQ5")
    self.t_lewy.addTab(self.lewy_tab3, "183MM")
    self.t_lewy.addTab(self.lewy_tab4, "533MM")
    self.t_lewy.addTab(self.lewy_tab5, "533MC")
    self.t_lewy.addTab(self.lewy_tab6, "432MM")
    self.t_lewy.addTab(self.lewy_tab7, "462MC")
    self.t_lewy.addTab(self.lewy_tab8, "120MM")
    self.t_lewy.addTab(self.lewy_tab9, "290MM")
    self.t_lewy.addTab(self.lewy_tab10, "174MM")
    self.t_lewy.addTab(self.lewy_tab11, "120MC")
    self.t_lewy.addTab(self.lewy_tab12, "CANON 20D")
    self.t_lewy.addTab(self.lewy_tab13, "FILTERS & MISC")
    self.t_lewy.addTab(self.lewy_tab14, "ALIGN TO FILE")

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
    self.prawy_tab10 = QWidget()
    self.prawy_tab11 = QWidget()
    self.prawy_tab12 = QWidget()
    self.prawy_tab13 = QWidget()
    self.prawy_tab14 = QWidget()
    self.prawy_tab15 = QWidget()
    self.t_prawy.addTab(self.prawy_tab1, "183MM")
    self.t_prawy.addTab(self.prawy_tab2, "533MM")
    self.t_prawy.addTab(self.prawy_tab3, "533MC")
    self.t_prawy.addTab(self.prawy_tab4, "432MM")
    self.t_prawy.addTab(self.prawy_tab5, "462MC")
    self.t_prawy.addTab(self.prawy_tab6, "120MM")
    self.t_prawy.addTab(self.prawy_tab7, "290MM")
    self.t_prawy.addTab(self.prawy_tab8, "174MM")
    self.t_prawy.addTab(self.prawy_tab9, "120MC")
    self.t_prawy.addTab(self.prawy_tab10, "CANON 20D")
    self.t_prawy.addTab(self.prawy_tab11, "Align Pic")
    self.t_prawy.addTab(self.prawy_tab12, "TYCHO2")
    self.t_prawy.addTab(self.prawy_tab13, "HD")
    self.t_prawy.addTab(self.prawy_tab14, "GALAXY")
    self.t_prawy.addTab(self.prawy_tab15, "SKY MAP")

    layout.addWidget(self.t_lewy, stretch=1)
    layout.addWidget(self.t_prawy, stretch=4)
    self.setLayout(layout)


    self.hist_pen_r = pg.mkPen(color=(255,0,0), width=2)
    self.hist_pen_g = pg.mkPen(color=(0,191,41), width=2)
    self.hist_pen_b = pg.mkPen(color=(0,0,255), width=2)
    self.hist_pen_gray = pg.mkPen(color=(0,0,0), width=2)

    self.tracking_color_timer = QTimer()
    self.tracking_color_timer.timeout.connect(self.f_tracking_color)
    self.tracking_color_timer.setInterval(1000)
    self.tracking_color_timer.start()

    self.tab1_lewyUI()
    self.tab2_lewyUI()
    self.tab3_lewyUI()
    self.tab4_lewyUI()
    self.tab5_lewyUI()
    self.tab6_lewyUI()
    self.tab7_lewyUI()
    self.tab8_lewyUI()
    self.tab9_lewyUI()
    self.tab10_lewyUI()
    self.tab11_lewyUI()
    self.tab12_lewyUI()
    self.tab13_lewyUI()
    self.tab14_lewyUI()
    self.tab_1_prawyUI()
    self.tab_2_prawyUI()
    self.tab_3_prawyUI()
    self.tab_4_prawyUI()
    self.tab_5_prawyUI()
    self.tab_6_prawyUI()
    self.tab_7_prawyUI()
    self.tab_8_prawyUI()
    self.tab_9_prawyUI()
    self.tab_10_prawyUI()
    self.tab_11_prawyUI()
    self.tab_12_prawyUI()
    self.tab_13_prawyUI()
    self.tab_14_prawyUI()
    self.tab_15_prawyUI()


#############################################################################################

  def tab1_lewyUI(self):

    self.headline = QFont('SansSerif', 11, QFont.Bold)


    self.ost_lat_eq6 = QLabel("FOCUS")
    self.ost_lat_eq6.setFont(self.headline)
    self.ost_lat_eq6.setAlignment(Qt.AlignCenter)

    self.ost_joystick_left_button_eq6 = QToolButton()
    self.ost_joystick_left_button_eq6.setArrowType(QtCore.Qt.LeftArrow)
    self.ost_joystick_left_button_eq6.clicked.connect(self.f_ost_joystick_left_eq6)

    self.ost_joystick_right_button_eq6 = QToolButton()
    self.ost_joystick_right_button_eq6.setArrowType(QtCore.Qt.RightArrow)
    self.ost_joystick_right_button_eq6.clicked.connect(self.f_ost_joystick_right_eq6)

    self.ost_joystick_arc_eq6 = QSpinBox()
    self.ost_joystick_arc_eq6.setMinimum(1)
    self.ost_joystick_arc_eq6.setMaximum(600)
    self.ost_joystick_arc_eq6.setValue(1)

    self.bahtinov_lab_eq6 = QLabel("Bahtinov")
    self.bahtinov_lab_eq6.setFont(self.headline)
    self.bahtinov_lab_eq6.setAlignment(Qt.AlignCenter)

    self.bahtinov_angle_5_eq6 = QPushButton('5', self)
    self.bahtinov_angle_5_eq6.clicked.connect(lambda: self.f_bahtinov_angle_eq6(angle=5))

    self.bahtinov_angle_8_eq6 = QPushButton('8', self)
    self.bahtinov_angle_8_eq6.clicked.connect(lambda: self.f_bahtinov_angle_eq6(angle=8))

    self.bahtinov_angle_270_eq6 = QPushButton('270', self)
    self.bahtinov_angle_270_eq6.clicked.connect(lambda: self.f_bahtinov_angle_eq6(angle=270))

    self.bahtinov_angle_eq6 = QSpinBox()
    self.bahtinov_angle_eq6.setMinimum(5)
    self.bahtinov_angle_eq6.setMaximum(270)
    self.bahtinov_angle_eq6.setValue(5)

    self.bahtinov_button_eq6 = QPushButton('SET', self)
    self.bahtinov_button_eq6.clicked.connect(self.f_bahtinov_eq6)

    self.bahtinov_focus_state_lab_eq6 = QLabel("Bahtinov and focus state NULL")

    self.act_pos_1_eq6 = QLabel("Position of telescope")
    self.act_pos_1_eq6.setFont(self.headline)

    self.radec_position1_eq6 = QLabel("00H 00m 00s")
    self.altaz_position1_eq6 = QLabel("00D 00m 00s")
    self.last_radec_diff_eq6 = QLabel("DIFF RA: 0h00m00.0000000s DEC: 0d00m00.00000000s")


    self.mount_move_left_button_eq6 = QToolButton()
    self.mount_move_left_button_eq6.setArrowType(QtCore.Qt.LeftArrow)
    self.mount_move_left_button_eq6.pressed.connect(self.f_move_left_press_eq6)
    self.mount_move_left_button_eq6.released.connect(self.f_move_left_release_eq6)

    self.mount_move_right_button_eq6 = QToolButton()
    self.mount_move_right_button_eq6.setArrowType(QtCore.Qt.RightArrow)
    self.mount_move_right_button_eq6.pressed.connect(self.f_move_right_press_eq6)
    self.mount_move_right_button_eq6.released.connect(self.f_move_right_release_eq6)

    self.mount_move_up_button_eq6 = QToolButton()
    self.mount_move_up_button_eq6.setArrowType(QtCore.Qt.UpArrow)
    self.mount_move_up_button_eq6.pressed.connect(self.f_move_up_press_eq6)
    self.mount_move_up_button_eq6.released.connect(self.f_move_up_release_eq6)

    self.mount_move_down_button_eq6 = QToolButton()
    self.mount_move_down_button_eq6.setArrowType(QtCore.Qt.DownArrow)
    self.mount_move_down_button_eq6.pressed.connect(self.f_move_down_press_eq6)
    self.mount_move_down_button_eq6.released.connect(self.f_move_down_release_eq6)

    self.mount_move_stop_button_eq6 = QToolButton()
    self.mount_move_stop_button_eq6.setArrowType(QtCore.Qt.NoArrow)
    self.mount_move_stop_button_eq6.clicked.connect(self.f_move_stop_eq6)

    self.slider_speed_selected_eq6 = QLabel("-99x")
    self.slider_speed_selected_eq6.setFont(self.headline)

    self.slider_speed_red_from_indi_eq6 = QLabel("indi: -99x")

    self.speed_slider_eq6 = QSlider(Qt.Horizontal)
    self.speed_slider_eq6.setTickPosition(QSlider.TicksBothSides)
    self.speed_slider_eq6.setMinimum(0)
    self.speed_slider_eq6.setMaximum(9)
    self.speed_slider_eq6.setTickInterval(1)
    self.speed_slider_eq6.setMaximumWidth(350)
    self.speed_slider_eq6.setSliderPosition(3)
    self.speed_slider_eq6.valueChanged.connect(self.f_speed_slider_eq6)

    self.move_flip_ud_eq6 = QCheckBox()
    self.move_flip_ud_eq6.setChecked(False)

    self.move_flip_lr_eq6 = QCheckBox()
    self.move_flip_lr_eq6.setChecked(False)

    self.mount_pier_side_eq6 = QLabel("Pier side: ???")

    self.mount_tracking_state_eq6 = QLabel("Tracking: ???")
    self.mount_tracking_state_eq6.setFont(self.headline)

    self.mount_tracking_eq6 = QCheckBox()
    self.mount_tracking_eq6.setChecked(True)
    self.mount_tracking_eq6.stateChanged.connect(self.f_mount_tracking_eq6)

    self.track_speed_eq6 = QComboBox()
    self.track_speed_eq6.addItems(['SIDEREAL', 'SUN', 'MOON'])
    self.track_speed_eq6.setCurrentIndex(0)
    self.track_speed_eq6.currentIndexChanged.connect(self.f_track_speed_change_eq6)


    self.ra_input_eq6 = QLabel("RA")
    self.ra_input_eq6.setFont(self.headline)
    self.ra_input_eq6.setAlignment(Qt.AlignCenter)
    self.ra_h_eq6 = QSpinBox(self)
    self.ra_h_eq6.setValue(0)
    self.ra_h_eq6.setMinimum(0)
    self.ra_h_eq6.setMaximum(24)
    self.ra_m_eq6 = QSpinBox(self)
    self.ra_m_eq6.setValue(0)
    self.ra_m_eq6.setMinimum(0)
    self.ra_m_eq6.setMaximum(59)
    self.ra_s_eq6 = QDoubleSpinBox(self)
    self.ra_s_eq6.setValue(0.0)
    self.ra_s_eq6.setMinimum(0.0)
    self.ra_s_eq6.setMaximum(59.9999999)
    self.ra_s_eq6.setSingleStep(1.0)
    self.ra_s_eq6.setDecimals(3)

    self.dec_input_eq6 = QLabel("DEC")
    self.dec_input_eq6.setFont(self.headline)
    self.dec_input_eq6.setAlignment(Qt.AlignCenter)
    self.dec_sign3_eq6 = QSpinBox(self)
    self.dec_sign3_eq6.setValue(1)
    self.dec_sign3_eq6.setMinimum(-1)
    self.dec_sign3_eq6.setMaximum(1)
    self.dec_d_eq6 = QSpinBox(self)
    self.dec_d_eq6.setValue(0)
    self.dec_d_eq6.setMinimum(0)
    self.dec_d_eq6.setMaximum(179)
    self.dec_m_eq6 = QSpinBox(self)
    self.dec_m_eq6.setValue(0)
    self.dec_m_eq6.setMinimum(0)
    self.dec_m_eq6.setMaximum(59)
    self.dec_s_eq6 = QDoubleSpinBox(self)
    self.dec_s_eq6.setValue(0.0)
    self.dec_s_eq6.setMinimum(0.0)
    self.dec_s_eq6.setMaximum(59.999999)
    self.dec_s_eq6.setSingleStep(1.0)
    self.dec_s_eq6.setDecimals(3)

    self.radec_button_set_eq6 = QPushButton('SET', self)
    self.radec_button_set_eq6.clicked.connect(self.f_radec_set_eq6)
    self.radec_button_goto_eq6 = QPushButton('GOTO', self)
    self.radec_button_goto_eq6.clicked.connect(self.f_radec_goto_eq6)
    self.radec_button_get_all_eq6 = QPushButton('GET ALL', self)
    self.radec_button_get_all_eq6.clicked.connect(lambda: self.f_radec_get_eq6(ra=True, dec=True))
    self.radec_button_get_ra_eq6 = QPushButton('GET RA', self)
    self.radec_button_get_ra_eq6.clicked.connect(lambda: self.f_radec_get_eq6(ra=True, dec=False))
    self.radec_button_get_dec_eq6 = QPushButton('GET DEC', self)
    self.radec_button_get_dec_eq6.clicked.connect(lambda: self.f_radec_get_eq6(ra=False, dec=True))
    self.radec_button_dec_reverse_eq6 = QPushButton('CALC REV', self)
    self.radec_button_dec_reverse_eq6.clicked.connect(self.f_dec_reverse_eq6)

    self.az_input_eq6 = QLabel("AZ")
    self.az_input_eq6.setFont(self.headline)
    self.az_input_eq6.setAlignment(Qt.AlignCenter)
    self.az_d_eq6 = QSpinBox(self)
    self.az_d_eq6.setValue(0)
    self.az_d_eq6.setMinimum(0)
    self.az_d_eq6.setMaximum(359)
    self.az_m_eq6 = QSpinBox(self)
    self.az_m_eq6.setValue(0)
    self.az_m_eq6.setMinimum(0)
    self.az_m_eq6.setMaximum(59)

    self.elev_input_eq6 = QLabel("EL")
    self.elev_input_eq6.setFont(self.headline)
    self.elev_input_eq6.setAlignment(Qt.AlignCenter)
    self.elev_d_eq6 = QSpinBox(self)
    self.elev_d_eq6.setValue(0)
    self.elev_d_eq6.setMinimum(0)
    self.elev_d_eq6.setMaximum(89)
    self.elev_m_eq6 = QSpinBox(self)
    self.elev_m_eq6.setValue(0)
    self.elev_m_eq6.setMinimum(0)
    self.elev_m_eq6.setMaximum(59)

    self.altaz_button_goto_eq6 = QPushButton('GOTO', self)
    self.altaz_button_goto_eq6.clicked.connect(self.f_altaz_goto_eq6)
    self.altaz_button_set_eq6 = QPushButton('SET', self)
    self.altaz_button_set_eq6.clicked.connect(self.f_altaz_set_eq6)
    self.altaz_button_get_all_eq6 = QPushButton('GET ALL', self)
    self.altaz_button_get_all_eq6.clicked.connect(lambda: self.f_altaz_get_eq6(alt=True, az=True))
    self.altaz_button_get_az_eq6 = QPushButton('GET AZ', self)
    self.altaz_button_get_az_eq6.clicked.connect(lambda: self.f_altaz_get_eq6(alt=False, az=True))
    self.altaz_button_get_alt_eq6 = QPushButton('GET ALT', self)
    self.altaz_button_get_alt_eq6.clicked.connect(lambda: self.f_altaz_get_eq6(alt=True, az=False))

    self.but_coord_rog_bloku_eq6 = QPushButton('Rog bloku', self)
    self.but_coord_rog_bloku_eq6.clicked.connect(self.f_coord_rog_bloku_eq6)
    self.but_coord_zenith_eq6 = QPushButton('Zenit', self)
    self.but_coord_zenith_eq6.clicked.connect(self.f_coord_zenith_eq6)
    self.but_coord_skytower_lampa_eq6 = QPushButton('Skytower lampa', self)
    self.but_coord_skytower_lampa_eq6.clicked.connect(self.f_coord_skytower_lampa_eq6)


    self.obj_name_eq6 = QLineEdit(self)
    self.obj_name_button_find_eq6 = QPushButton('FIND', self)
    self.obj_name_button_find_eq6.clicked.connect(self.f_goto_object_find_eq6)
    find_button_width = self.obj_name_button_find_eq6.fontMetrics().boundingRect('FIND').width() + 12
    self.obj_name_button_find_eq6.setMaximumWidth(find_button_width)
    self.obj_name_goto_info_eq6 = QLabel("NULL")

    self.turn_on_mount_eq6 = QCheckBox()
    self.turn_on_mount_eq6.setChecked(False)
    self.turn_on_mount_eq6.stateChanged.connect(self.f_eq6_turn_on)
    self.mount_state_eq6 = QLabel("state: NULL")




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
    separator9 = QFrame()
    separator9.setFrameShape(QFrame.HLine)
    separator10 = QFrame()
    separator10.setFrameShape(QFrame.HLine)


    layout = QVBoxLayout()

    sliders_layout = QHBoxLayout()
    sliders_layout2 = QVBoxLayout()
    sliders_layout2.addWidget(self.ost_lat_eq6)
    sliders_layout2_1 = QHBoxLayout()
    sliders_layout2_1.addWidget(self.ost_joystick_left_button_eq6)
    sliders_layout2_1.addWidget(self.ost_joystick_arc_eq6)
    sliders_layout2_1.addWidget(self.ost_joystick_right_button_eq6)
    sliders_layout2.addLayout(sliders_layout2_1)
    sliders_layout.addLayout(sliders_layout2)
    layout.addLayout(sliders_layout)

    layout.addWidget(self.bahtinov_lab_eq6)
    bahtinov_layout = QHBoxLayout()
    bahtinov_layout.addWidget(self.bahtinov_angle_5_eq6)
    bahtinov_layout.addWidget(self.bahtinov_angle_8_eq6)
    bahtinov_layout.addWidget(self.bahtinov_angle_270_eq6)
    bahtinov_layout.addWidget(self.bahtinov_angle_eq6)
    bahtinov_layout.addWidget(self.bahtinov_button_eq6)
    layout.addLayout(bahtinov_layout)

    layout.addWidget(self.bahtinov_focus_state_lab_eq6)

    layout.addWidget(separator1)


    layout.addStretch()

    layout.addWidget(separator10)
    mount_on_layout = QHBoxLayout()
    mount_on_layout.addWidget(self.turn_on_mount_eq6)
    mount_on_layout.addWidget(QLabel("Turn on EQ6 mount"))
    mount_on_layout.addWidget(self.mount_state_eq6)
    mount_on_layout.addStretch()
    layout.addLayout(mount_on_layout)
    layout.addWidget(separator2)

    stellarium_l = QHBoxLayout()
    stellarium_l.addWidget(self.obj_name_eq6)
    stellarium_l.addWidget(self.obj_name_button_find_eq6)
    layout.addLayout(stellarium_l)
    layout.addWidget(self.obj_name_goto_info_eq6)

    layout.addWidget(separator3)
    but_coord_layout = QHBoxLayout()
    but_coord_layout.addWidget(self.but_coord_rog_bloku_eq6)
    but_coord_layout.addWidget(self.but_coord_zenith_eq6)
    but_coord_layout.addWidget(self.but_coord_skytower_lampa_eq6)
    layout.addLayout(but_coord_layout)

    layout.addWidget(separator4)
    ra_input_layout = QHBoxLayout()
    ra_input_layout.addWidget(self.ra_input_eq6)
    ra_input_layout.addWidget(self.ra_h_eq6)
    ra_input_layout.addWidget(QLabel("H"))
    ra_input_layout.addWidget(self.ra_m_eq6)
    ra_input_layout.addWidget(QLabel("m"))
    ra_input_layout.addWidget(self.ra_s_eq6)
    ra_input_layout.addWidget(QLabel("s"))
    ra_input_layout.addStretch()
    layout.addLayout(ra_input_layout)

    whole_dec_input_layout = QVBoxLayout()
    dec_input_layout = QHBoxLayout()
    dec_input_layout.addWidget(self.dec_input_eq6)
    dec_input_layout.addWidget(self.dec_sign3_eq6)
    dec_input_layout.addWidget(self.dec_d_eq6)
    dec_input_layout.addWidget(QLabel("D"))
    dec_input_layout.addWidget(self.dec_m_eq6)
    dec_input_layout.addWidget(QLabel("m"))
    dec_input_layout.addWidget(self.dec_s_eq6)
    dec_input_layout.addWidget(QLabel("s"))
    dec_input_layout.addStretch()
    dec_input_layout.addWidget(self.radec_button_dec_reverse_eq6)
    whole_dec_input_layout.addLayout(dec_input_layout)
    radec_butt_input_layout = QHBoxLayout()
    radec_butt_input_layout.addWidget(self.radec_button_goto_eq6)
    radec_butt_input_layout.addWidget(self.radec_button_set_eq6)
    radec_butt_input_layout.addWidget(self.radec_button_get_all_eq6)
    radec_butt_input_layout.addWidget(self.radec_button_get_ra_eq6)
    radec_butt_input_layout.addWidget(self.radec_button_get_dec_eq6)
    whole_dec_input_layout.addLayout(radec_butt_input_layout)
    layout.addLayout(whole_dec_input_layout)

    layout.addWidget(separator5)

    az_input_layout = QHBoxLayout()
    az_input_layout.addWidget(self.az_input_eq6)
    az_input_layout.addWidget(self.az_d_eq6)
    az_input_layout.addWidget(QLabel("D"))
    az_input_layout.addWidget(self.az_m_eq6)
    az_input_layout.addWidget(QLabel("m"))
    az_input_layout.addStretch()
    layout.addLayout(az_input_layout)

    whole_elev_input_layout = QVBoxLayout()
    elev_input_layout = QHBoxLayout()
    elev_input_layout.addWidget(self.elev_input_eq6)
    elev_input_layout.addWidget(self.elev_d_eq6)
    elev_input_layout.addWidget(QLabel("D"))
    elev_input_layout.addWidget(self.elev_m_eq6)
    elev_input_layout.addWidget(QLabel("m"))
    elev_input_layout.addStretch()
    whole_elev_input_layout.addLayout(elev_input_layout)
    altaz_butt_input_layout = QHBoxLayout()
    altaz_butt_input_layout.addWidget(self.altaz_button_goto_eq6)
    altaz_butt_input_layout.addWidget(self.altaz_button_set_eq6)
    altaz_butt_input_layout.addWidget(self.altaz_button_get_all_eq6)
    altaz_butt_input_layout.addWidget(self.altaz_button_get_az_eq6)
    altaz_butt_input_layout.addWidget(self.altaz_button_get_alt_eq6)
    whole_elev_input_layout.addLayout(altaz_butt_input_layout)
    layout.addLayout(whole_elev_input_layout)



    layout.addWidget(separator6)
    layout.addWidget(self.act_pos_1_eq6, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.radec_position1_eq6)
    layout.addWidget(self.altaz_position1_eq6)
    layout.addWidget(separator7)
    layout.addWidget(self.last_radec_diff_eq6)

    layout.addWidget(separator8)
    l_track = QHBoxLayout()
    l_track.addWidget(self.mount_tracking_state_eq6)
    l_track.addStretch()
    l_track.addWidget(self.mount_tracking_eq6)
    l_track.addWidget(QLabel("Track on"))
    l_track.addStretch()
    l_track.addWidget(self.mount_pier_side_eq6)
    l_track.addStretch()
    l_track.addWidget(self.track_speed_eq6)
    layout.addLayout(l_track)

    layout.addWidget(separator9)
    l_block = QHBoxLayout()
    l_move = QVBoxLayout()
    l_move_1 = QHBoxLayout()
    l_move_2 = QHBoxLayout()
    l_move_3 = QHBoxLayout()
    l_move_1.addWidget(self.mount_move_up_button_eq6)
    l_move_2.addWidget(self.mount_move_left_button_eq6)
    l_move_2.addWidget(self.mount_move_stop_button_eq6)
    l_move_2.addWidget(self.mount_move_right_button_eq6)
    l_move_3.addWidget(self.mount_move_down_button_eq6)
    l_move.addLayout(l_move_1)
    l_move.addLayout(l_move_2)
    l_move.addLayout(l_move_3)

    l_flip = QVBoxLayout()
    l_flip.setAlignment(Qt.AlignVCenter)
    l_flip_l1 = QHBoxLayout()
    l_flip_l2 = QHBoxLayout()
    l_flip_l1.addWidget(self.move_flip_ud_eq6)
    l_flip_l1.addWidget(QLabel("Flip U/D"))
    l_flip_l2.addWidget(self.move_flip_lr_eq6)
    l_flip_l2.addWidget(QLabel("Flip L/R"))
    l_flip.addLayout(l_flip_l1)
    l_flip.addLayout(l_flip_l2)

    l_speed = QVBoxLayout()
    l_speed.setAlignment(Qt.AlignVCenter)
    l_speed_txt = QHBoxLayout()
    l_speed_txt.addStretch()
    l_speed_txt.addWidget(self.slider_speed_selected_eq6)
    l_speed_txt.addStretch()

    l_speed_indi = QHBoxLayout()
    l_speed_indi.addStretch()
    l_speed_indi.addWidget(self.slider_speed_red_from_indi_eq6)
    l_speed_indi.addStretch()

    l_speed.addWidget(self.speed_slider_eq6)
    l_speed.addLayout(l_speed_txt)
    l_speed.addLayout(l_speed_indi)

    l_block.addLayout(l_speed)
    l_block.addItem(QSpacerItem(5, 10, QSizePolicy.Minimum, QSizePolicy.Minimum))
    l_block.addLayout(l_flip)
    l_block.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Minimum))
    l_block.addLayout(l_move)
    layout.addLayout(l_block)

    self.lewy_tab1.setLayout(layout)

#############################################################################################

  def tab2_lewyUI(self):

    self.headline = QFont('SansSerif', 11, QFont.Bold)


    self.ost_lat_eq5 = QLabel("FOCUS")
    self.ost_lat_eq5.setFont(self.headline)
    self.ost_lat_eq5.setAlignment(Qt.AlignCenter)

    self.ost_joystick_left_button_eq5 = QToolButton()
    self.ost_joystick_left_button_eq5.setArrowType(QtCore.Qt.LeftArrow)
    self.ost_joystick_left_button_eq5.clicked.connect(self.f_ost_joystick_left_eq5)

    self.ost_joystick_right_button_eq5 = QToolButton()
    self.ost_joystick_right_button_eq5.setArrowType(QtCore.Qt.RightArrow)
    self.ost_joystick_right_button_eq5.clicked.connect(self.f_ost_joystick_right_eq5)

    self.ost_joystick_arc_eq5 = QSpinBox()
    self.ost_joystick_arc_eq5.setMinimum(1)
    self.ost_joystick_arc_eq5.setMaximum(600)
    self.ost_joystick_arc_eq5.setValue(1)

    self.act_pos_1_eq5 = QLabel("Position of telescope")
    self.act_pos_1_eq5.setFont(self.headline)

    self.radec_position1_eq5 = QLabel("00H 00m 00s")
    self.altaz_position1_eq5 = QLabel("00D 00m 00s")
    self.last_radec_diff_eq5 = QLabel("DIFF RA: 0h00m00.0000000s DEC: 0d00m00.00000000s")


    self.mount_move_left_button_eq5 = QToolButton()
    self.mount_move_left_button_eq5.setArrowType(QtCore.Qt.LeftArrow)
    self.mount_move_left_button_eq5.pressed.connect(self.f_move_left_press_eq5)
    self.mount_move_left_button_eq5.released.connect(self.f_move_ra_release_eq5)

    self.mount_move_right_button_eq5 = QToolButton()
    self.mount_move_right_button_eq5.setArrowType(QtCore.Qt.RightArrow)
    self.mount_move_right_button_eq5.pressed.connect(self.f_move_right_press_eq5)
    self.mount_move_right_button_eq5.released.connect(self.f_move_ra_release_eq5)

    self.mount_move_up_button_eq5 = QToolButton()
    self.mount_move_up_button_eq5.setArrowType(QtCore.Qt.UpArrow)
    self.mount_move_up_button_eq5.pressed.connect(self.f_move_up_press_eq5)
    self.mount_move_up_button_eq5.released.connect(self.f_move_dec_release_eq5)

    self.mount_move_down_button_eq5 = QToolButton()
    self.mount_move_down_button_eq5.setArrowType(QtCore.Qt.DownArrow)
    self.mount_move_down_button_eq5.pressed.connect(self.f_move_down_press_eq5)
    self.mount_move_down_button_eq5.released.connect(self.f_move_dec_release_eq5)

    self.mount_move_stop_button_eq5 = QToolButton()
    self.mount_move_stop_button_eq5.setArrowType(QtCore.Qt.NoArrow)
    self.mount_move_stop_button_eq5.clicked.connect(self.f_immediate_stop_eq5)

    self.slider_speed_selected_eq5 = QLabel("-99x")
    self.slider_speed_selected_eq5.setFont(self.headline)

    self.speed_slider_eq5 = QSlider(Qt.Horizontal)
    self.speed_slider_eq5.setTickPosition(QSlider.TicksBothSides)
    self.speed_slider_eq5.setMinimum(0)
    self.speed_slider_eq5.setMaximum(9)
    self.speed_slider_eq5.setTickInterval(1)
    self.speed_slider_eq5.setMaximumWidth(350)
    self.speed_slider_eq5.setSliderPosition(3)
    self.speed_slider_eq5.valueChanged.connect(self.f_speed_slider_eq5)

    self.move_flip_ud_eq5 = QCheckBox()
    self.move_flip_ud_eq5.setChecked(False)

    self.move_flip_lr_eq5 = QCheckBox()
    self.move_flip_lr_eq5.setChecked(False)

    self.mount_pier_side_eq5 = QLabel("Pier side: ???")

    self.mount_tracking_state_eq5 = QLabel("Tracking: ???")
    self.mount_tracking_state_eq5.setFont(self.headline)

    self.mount_tracking_eq5 = QCheckBox()
    self.mount_tracking_eq5.setChecked(True)
    self.mount_tracking_eq5.stateChanged.connect(self.f_mount_tracking_eq5)

    self.track_speed_eq5 = QComboBox()
    self.track_speed_eq5.addItems(['SIDEREAL', 'SUN', 'MOON'])
    self.track_speed_eq5.setCurrentIndex(0)
    self.track_speed_eq5.currentIndexChanged.connect(self.f_mount_tracking_eq5)


    self.ra_input_eq5 = QLabel("RA")
    self.ra_input_eq5.setFont(self.headline)
    self.ra_input_eq5.setAlignment(Qt.AlignCenter)
    self.ra_h_eq5 = QSpinBox(self)
    self.ra_h_eq5.setValue(0)
    self.ra_h_eq5.setMinimum(0)
    self.ra_h_eq5.setMaximum(24)
    self.ra_m_eq5 = QSpinBox(self)
    self.ra_m_eq5.setValue(0)
    self.ra_m_eq5.setMinimum(0)
    self.ra_m_eq5.setMaximum(59)
    self.ra_s_eq5 = QDoubleSpinBox(self)
    self.ra_s_eq5.setValue(0.0)
    self.ra_s_eq5.setMinimum(0.0)
    self.ra_s_eq5.setMaximum(59.9999999)
    self.ra_s_eq5.setSingleStep(1.0)
    self.ra_s_eq5.setDecimals(3)

    self.dec_input_eq5 = QLabel("DEC")
    self.dec_input_eq5.setFont(self.headline)
    self.dec_input_eq5.setAlignment(Qt.AlignCenter)
    self.dec_sign3_eq5 = QSpinBox(self)
    self.dec_sign3_eq5.setValue(1)
    self.dec_sign3_eq5.setMinimum(-1)
    self.dec_sign3_eq5.setMaximum(1)
    self.dec_d_eq5 = QSpinBox(self)
    self.dec_d_eq5.setValue(0)
    self.dec_d_eq5.setMinimum(0)
    self.dec_d_eq5.setMaximum(179)
    self.dec_m_eq5 = QSpinBox(self)
    self.dec_m_eq5.setValue(0)
    self.dec_m_eq5.setMinimum(0)
    self.dec_m_eq5.setMaximum(59)
    self.dec_s_eq5 = QDoubleSpinBox(self)
    self.dec_s_eq5.setValue(0.0)
    self.dec_s_eq5.setMinimum(0.0)
    self.dec_s_eq5.setMaximum(59.999999)
    self.dec_s_eq5.setSingleStep(1.0)
    self.dec_s_eq5.setDecimals(3)

    self.radec_button_set_eq5 = QPushButton('SET', self)
    self.radec_button_set_eq5.clicked.connect(self.f_radec_set_eq5)
    self.radec_button_goto_eq5 = QPushButton('GOTO', self)
    self.radec_button_goto_eq5.clicked.connect(self.f_radec_goto_eq5)
    self.radec_button_get_all_eq5 = QPushButton('GET ALL', self)
    self.radec_button_get_all_eq5.clicked.connect(lambda: self.f_radec_get_eq5(ra=True, dec=True))
    self.radec_button_get_ra_eq5 = QPushButton('GET RA', self)
    self.radec_button_get_ra_eq5.clicked.connect(lambda: self.f_radec_get_eq5(ra=True, dec=False))
    self.radec_button_get_dec_eq5 = QPushButton('GET DEC', self)
    self.radec_button_get_dec_eq5.clicked.connect(lambda: self.f_radec_get_eq5(ra=False, dec=True))
    self.radec_button_dec_reverse_eq5 = QPushButton('CALC REV', self)
    self.radec_button_dec_reverse_eq5.clicked.connect(self.f_dec_reverse_eq5)

    self.az_input_eq5 = QLabel("AZ")
    self.az_input_eq5.setFont(self.headline)
    self.az_input_eq5.setAlignment(Qt.AlignCenter)
    self.az_d_eq5 = QSpinBox(self)
    self.az_d_eq5.setValue(0)
    self.az_d_eq5.setMinimum(0)
    self.az_d_eq5.setMaximum(359)
    self.az_m_eq5 = QSpinBox(self)
    self.az_m_eq5.setValue(0)
    self.az_m_eq5.setMinimum(0)
    self.az_m_eq5.setMaximum(59)

    self.elev_input_eq5 = QLabel("EL")
    self.elev_input_eq5.setFont(self.headline)
    self.elev_input_eq5.setAlignment(Qt.AlignCenter)
    self.elev_d_eq5 = QSpinBox(self)
    self.elev_d_eq5.setValue(0)
    self.elev_d_eq5.setMinimum(0)
    self.elev_d_eq5.setMaximum(89)
    self.elev_m_eq5 = QSpinBox(self)
    self.elev_m_eq5.setValue(0)
    self.elev_m_eq5.setMinimum(0)
    self.elev_m_eq5.setMaximum(59)

    self.altaz_button_goto_eq5 = QPushButton('GOTO', self)
    self.altaz_button_goto_eq5.clicked.connect(self.f_altaz_goto_eq5)
    self.altaz_button_set_eq5 = QPushButton('SET', self)
    self.altaz_button_set_eq5.clicked.connect(self.f_altaz_set_eq5)
    self.altaz_button_get_all_eq5 = QPushButton('GET ALL', self)
    self.altaz_button_get_all_eq5.clicked.connect(lambda: self.f_altaz_get_eq5(alt=True, az=True))
    self.altaz_button_get_az_eq5 = QPushButton('GET AZ', self)
    self.altaz_button_get_az_eq5.clicked.connect(lambda: self.f_altaz_get_eq5(alt=False, az=True))
    self.altaz_button_get_alt_eq5 = QPushButton('GET ALT', self)
    self.altaz_button_get_alt_eq5.clicked.connect(lambda: self.f_altaz_get_eq5(alt=True, az=False))

    self.but_coord_rog_bloku_eq5 = QPushButton('Rog bloku', self)
    self.but_coord_rog_bloku_eq5.clicked.connect(self.f_coord_rog_bloku_eq5)
    self.but_coord_zenith_eq5 = QPushButton('Zenit', self)
    self.but_coord_zenith_eq5.clicked.connect(self.f_coord_zenith_eq5)
    self.but_coord_skytower_lampa_eq5 = QPushButton('Skytower lampa', self)
    self.but_coord_skytower_lampa_eq5.clicked.connect(self.f_coord_skytower_lampa_eq5)


    self.obj_name_eq5 = QLineEdit(self)
    self.obj_name_button_find_eq5 = QPushButton('FIND', self)
    self.obj_name_button_find_eq5.clicked.connect(self.f_goto_object_find_eq5)
    find_button_width = self.obj_name_button_find_eq5.fontMetrics().boundingRect('FIND').width() + 12
    self.obj_name_button_find_eq5.setMaximumWidth(find_button_width)
    self.obj_name_goto_info_eq5 = QLabel("NULL")

    self.turn_on_mount_eq5 = QCheckBox()
    self.turn_on_mount_eq5.setChecked(False)
    self.turn_on_mount_eq5.stateChanged.connect(self.f_eq5_turn_on)
    self.mount_state_eq5 = QLabel("state: NULL")

    self.after_meridian_eq5 = QCheckBox()
    self.after_meridian_eq5.setChecked(False)



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
    separator9 = QFrame()
    separator9.setFrameShape(QFrame.HLine)
    separator10 = QFrame()
    separator10.setFrameShape(QFrame.HLine)


    layout = QVBoxLayout()

    sliders_layout = QHBoxLayout()
    sliders_layout2 = QVBoxLayout()
    sliders_layout2.addWidget(self.ost_lat_eq5)
    sliders_layout2_1 = QHBoxLayout()
    sliders_layout2_1.addWidget(self.ost_joystick_left_button_eq5)
    sliders_layout2_1.addWidget(self.ost_joystick_arc_eq5)
    sliders_layout2_1.addWidget(self.ost_joystick_right_button_eq5)
    sliders_layout2.addLayout(sliders_layout2_1)
    sliders_layout.addLayout(sliders_layout2)
    layout.addLayout(sliders_layout)


    layout.addWidget(separator1)


    layout.addStretch()

    layout.addWidget(separator10)
    mount_on_layout = QHBoxLayout()
    mount_on_layout.addWidget(self.turn_on_mount_eq5)
    mount_on_layout.addWidget(QLabel("Turn on EQ5 mount"))
    mount_on_layout.addWidget(self.mount_state_eq5)
    mount_on_layout.addStretch()
    layout.addLayout(mount_on_layout)
    layout.addWidget(separator2)

    stellarium_l = QHBoxLayout()
    stellarium_l.addWidget(self.obj_name_eq5)
    stellarium_l.addWidget(self.obj_name_button_find_eq5)
    layout.addLayout(stellarium_l)
    layout.addWidget(self.obj_name_goto_info_eq5)

    layout.addWidget(separator3)
    but_coord_layout = QHBoxLayout()
    but_coord_layout.addWidget(self.but_coord_rog_bloku_eq5)
    but_coord_layout.addWidget(self.but_coord_zenith_eq5)
    but_coord_layout.addWidget(self.but_coord_skytower_lampa_eq5)
    layout.addLayout(but_coord_layout)

    layout.addWidget(separator4)
    ra_input_layout = QHBoxLayout()
    ra_input_layout.addWidget(self.ra_input_eq5)
    ra_input_layout.addWidget(self.ra_h_eq5)
    ra_input_layout.addWidget(QLabel("H"))
    ra_input_layout.addWidget(self.ra_m_eq5)
    ra_input_layout.addWidget(QLabel("m"))
    ra_input_layout.addWidget(self.ra_s_eq5)
    ra_input_layout.addWidget(QLabel("s"))
    ra_input_layout.addStretch()
    layout.addLayout(ra_input_layout)

    whole_dec_input_layout = QVBoxLayout()
    dec_input_layout = QHBoxLayout()
    dec_input_layout.addWidget(self.dec_input_eq5)
    dec_input_layout.addWidget(self.dec_sign3_eq5)
    dec_input_layout.addWidget(self.dec_d_eq5)
    dec_input_layout.addWidget(QLabel("D"))
    dec_input_layout.addWidget(self.dec_m_eq5)
    dec_input_layout.addWidget(QLabel("m"))
    dec_input_layout.addWidget(self.dec_s_eq5)
    dec_input_layout.addWidget(QLabel("s"))
    dec_input_layout.addStretch()
    dec_input_layout.addWidget(self.radec_button_dec_reverse_eq5)
    whole_dec_input_layout.addLayout(dec_input_layout)
    radec_butt_input_layout = QHBoxLayout()
    radec_butt_input_layout.addWidget(self.radec_button_goto_eq5)
    radec_butt_input_layout.addWidget(self.radec_button_set_eq5)
    radec_butt_input_layout.addWidget(self.radec_button_get_all_eq5)
    radec_butt_input_layout.addWidget(self.radec_button_get_ra_eq5)
    radec_butt_input_layout.addWidget(self.radec_button_get_dec_eq5)
    whole_dec_input_layout.addLayout(radec_butt_input_layout)
    layout.addLayout(whole_dec_input_layout)

    layout.addWidget(separator5)

    az_input_layout = QHBoxLayout()
    az_input_layout.addWidget(self.az_input_eq5)
    az_input_layout.addWidget(self.az_d_eq5)
    az_input_layout.addWidget(QLabel("D"))
    az_input_layout.addWidget(self.az_m_eq5)
    az_input_layout.addWidget(QLabel("m"))
    az_input_layout.addStretch()
    layout.addLayout(az_input_layout)

    whole_elev_input_layout = QVBoxLayout()
    elev_input_layout = QHBoxLayout()
    elev_input_layout.addWidget(self.elev_input_eq5)
    elev_input_layout.addWidget(self.elev_d_eq5)
    elev_input_layout.addWidget(QLabel("D"))
    elev_input_layout.addWidget(self.elev_m_eq5)
    elev_input_layout.addWidget(QLabel("m"))
    elev_input_layout.addStretch()
    whole_elev_input_layout.addLayout(elev_input_layout)
    altaz_butt_input_layout = QHBoxLayout()
    altaz_butt_input_layout.addWidget(self.altaz_button_goto_eq5)
    altaz_butt_input_layout.addWidget(self.altaz_button_set_eq5)
    altaz_butt_input_layout.addWidget(self.altaz_button_get_all_eq5)
    altaz_butt_input_layout.addWidget(self.altaz_button_get_az_eq5)
    altaz_butt_input_layout.addWidget(self.altaz_button_get_alt_eq5)
    whole_elev_input_layout.addLayout(altaz_butt_input_layout)
    layout.addLayout(whole_elev_input_layout)



    layout.addWidget(separator6)
    layout.addWidget(self.act_pos_1_eq5, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.radec_position1_eq5)
    layout.addWidget(self.altaz_position1_eq5)
    layout.addWidget(separator7)
    layout.addWidget(self.last_radec_diff_eq5)

    layout.addWidget(separator8)
    l_track = QHBoxLayout()
    l_track.addWidget(self.mount_tracking_state_eq5)
    l_track.addStretch()
    l_track.addWidget(self.mount_tracking_eq5)
    l_track.addWidget(QLabel("Track on"))
    l_track.addStretch()
    l_track.addWidget(self.mount_pier_side_eq5)
    l_track.addStretch()
    l_track.addWidget(self.track_speed_eq5)
    layout.addLayout(l_track)

    layout.addWidget(separator9)
    l_block = QHBoxLayout()
    l_move = QVBoxLayout()
    l_move_1 = QHBoxLayout()
    l_move_2 = QHBoxLayout()
    l_move_3 = QHBoxLayout()
    l_move_1.addWidget(self.mount_move_up_button_eq5)
    l_move_2.addWidget(self.mount_move_left_button_eq5)
    l_move_2.addWidget(self.mount_move_stop_button_eq5)
    l_move_2.addWidget(self.mount_move_right_button_eq5)
    l_move_3.addWidget(self.mount_move_down_button_eq5)
    l_move.addLayout(l_move_1)
    l_move.addLayout(l_move_2)
    l_move.addLayout(l_move_3)

    l_flip = QVBoxLayout()
    l_flip.setAlignment(Qt.AlignVCenter)
    l_flip_l1 = QHBoxLayout()
    l_flip_l2 = QHBoxLayout()
    l_flip_l3 = QHBoxLayout()
    l_flip_l1.addWidget(self.move_flip_ud_eq5)
    l_flip_l1.addWidget(QLabel("Flip U/D"))
    l_flip_l2.addWidget(self.move_flip_lr_eq5)
    l_flip_l2.addWidget(QLabel("Flip L/R"))
    l_flip_l3.addWidget(self.after_meridian_eq5)
    l_flip_l3.addWidget(QLabel("Meridian"))
    l_flip.addLayout(l_flip_l1)
    l_flip.addLayout(l_flip_l2)
    l_flip.addLayout(l_flip_l3)

    l_speed = QVBoxLayout()
    l_speed.setAlignment(Qt.AlignVCenter)
    l_speed_txt = QHBoxLayout()
    l_speed_txt.addStretch()
    l_speed_txt.addWidget(self.slider_speed_selected_eq5)
    l_speed_txt.addStretch()

    l_speed.addWidget(self.speed_slider_eq5)
    l_speed.addLayout(l_speed_txt)

    l_block.addLayout(l_speed)
    l_block.addItem(QSpacerItem(5, 10, QSizePolicy.Minimum, QSizePolicy.Minimum))
    l_block.addLayout(l_flip)
    l_block.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Minimum))
    l_block.addLayout(l_move)
    layout.addLayout(l_block)

    self.lewy_tab2.setLayout(layout)

#############################################################################################

  def tab3_lewyUI(self):
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
    camname = 'a183mm'

    self.a183mm_cam_on = QCheckBox()
    self.a183mm_cam_on.setChecked(False)

    self.lab_a183mm_cam = QLabel("ASI183MM PRO CAM")
    self.lab_a183mm_cam.setFont(self.headline)
    self.lab_a183mm_cam.setAlignment(Qt.AlignCenter)

    self.lab_a183mm_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a183mm_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a183mm_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a183mm_rotate = QLabel("Rotate: null")
    self.lab_a183mm_cooling = QLabel("Cooler: NULL")

    self.a183mm_cam_exp_slider = QDoubleSpinBox()
    self.a183mm_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a183mm_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a183mm_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a183mm_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a183mm_cam_gain_slider = QSpinBox()

    self.a183mm_cam_offset_slider = QSpinBox()

    self.a183mm_cam_cooler = QCheckBox()
    self.a183mm_cam_cooler.setChecked(False)

    self.a183mm_cam_bin = QComboBox()
    self.a183mm_cam_bin.addItems(['NULL'])

    self.a183mm_cam_target_temp_slider = QSpinBox()

    self.a183mm_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a183mm_cam_photo_settings_button.clicked.connect(self.f_a183mm_cam_button_photo_settings)

    self.a183mm_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a183mm_cam_preview_settings_button.clicked.connect(self.f_a183mm_cam_button_preview_settings)

    self.a183mm_photo_reload = QPushButton('Reload', self)
    self.a183mm_photo_reload.clicked.connect(self.f_a183mm_window_refresh)

    self.a183mm_photo_rotate = QPushButton('Rot', self)
    self.a183mm_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a183mm_cam_save_img = QCheckBox()
    self.a183mm_cam_save_img.setChecked(False)

    self.a183mm_cam_save_dirname = QLineEdit(self)
    self.a183mm_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a183mm_cam_save_dirname.setValidator(validator1)
    self.a183mm_cam_save_dirname.setText('teleskop')

    self.a183mm_cam_save_delay = QDoubleSpinBox()
    self.a183mm_cam_save_delay.setMinimum(0.0)
    self.a183mm_cam_save_delay.setMaximum(1000.0)
    self.a183mm_cam_save_delay.setValue(0.0)
    self.a183mm_cam_save_delay.setSingleStep(1.0)

    self.a183mm_cam_circ_x = QSpinBox()
    self.a183mm_cam_circ_x.setMinimum(0)
    self.a183mm_cam_circ_x.setMaximum(5496)
    self.a183mm_cam_circ_x.setValue(int(5496/2))
    if 'a183mm_cam_circ_x' in app_settings.keys():
      self.a183mm_cam_circ_x.setValue(app_settings['a183mm_cam_circ_x'])
    else:
      self.a183mm_cam_circ_x.setValue(int(5496/2))

    self.a183mm_cam_circ_y = QSpinBox()
    self.a183mm_cam_circ_y.setMinimum(0)
    self.a183mm_cam_circ_y.setMaximum(3672)
    if 'a183mm_cam_circ_y' in app_settings.keys():
      self.a183mm_cam_circ_y.setValue(app_settings['a183mm_cam_circ_y'])
    else:
      self.a183mm_cam_circ_y.setValue(int(3672/2))

    self.a183mm_cam_circ_d = QSpinBox()
    self.a183mm_cam_circ_d.setMinimum(0)
    self.a183mm_cam_circ_d.setMaximum(1936)
    if 'a183mm_cam_circ_d' in app_settings.keys():
      self.a183mm_cam_circ_d.setValue(app_settings['a183mm_cam_circ_d'])
    else:
      self.a183mm_cam_circ_d.setValue(0)

    self.a183mm_cam_circ_c = QSpinBox()
    self.a183mm_cam_circ_c.setMinimum(0)
    self.a183mm_cam_circ_c.setMaximum(2000)
    self.a183mm_cam_circ_c.setValue(0)

    self.a183mm_downsample = QSpinBox()
    self.a183mm_downsample.setMinimum(1)
    self.a183mm_downsample.setMaximum(64)
    self.a183mm_downsample.setValue(4)

    self.a183mm_cam_solve_radius = QCheckBox()
    self.a183mm_cam_solve_radius.setChecked(True)

    self.a183mm_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a183mm_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))

    self.a183mm_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a183mm_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a183mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a183mm_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))

    self.lab_a183mm_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a183mm_cam_scale_pixel_size = QDoubleSpinBox()
    self.a183mm_cam_scale_pixel_size.setMinimum(0.1)
    self.a183mm_cam_scale_pixel_size.setMaximum(99.0)
    self.a183mm_cam_scale_pixel_size.setValue(2.9)
    self.a183mm_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a183mm_cam_scale_focal = QSpinBox()
    self.a183mm_cam_scale_focal.setMinimum(1)
    self.a183mm_cam_scale_focal.setMaximum(9999)
    if 'a183mm_cam_scale_focal' in app_settings.keys():
      self.a183mm_cam_scale_focal.setValue(app_settings['a183mm_cam_scale_focal'])
    else:
      self.a183mm_cam_scale_focal.setValue(2450)
    self.a183mm_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a183mm_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a183mm_cam_scale_pixel_scale.setMinimum(0.0)
    self.a183mm_cam_scale_pixel_scale.setMaximum(999.0)
    self.a183mm_cam_scale_pixel_scale.setValue(0.24)
    self.a183mm_cam_scale_pixel_scale.setDecimals(5)

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

    self.a183mm_cam_hist_draw = QCheckBox()
    self.a183mm_cam_hist_draw.setChecked(False)

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
    self.a183mm_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a183mm_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a183mm = QCheckBox()
    self.loghist_a183mm.setChecked(True)

    self.graphWidget_a183mm = pg.PlotWidget()
    self.hist_color_a183mm = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_a183mm = pg.mkPen(color=(0,0,0))
    self.graphWidget_a183mm.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_a183mm)
    self.graphWidget_a183mm.setBackground(self.hist_color_a183mm)


    cam_a183mm_title_layout = QHBoxLayout()
    cam_a183mm_title_layout.addStretch()
    cam_a183mm_title_layout.addWidget(self.lab_a183mm_cam)
    cam_a183mm_title_layout.addStretch()
    cam_a183mm_title_layout.addWidget(self.a183mm_cam_on)
    cam_a183mm_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a183mm_title_layout)

    layout.addWidget(self.lab_a183mm_cam_time_param)
    layout.addWidget(self.lab_a183mm_cam_time_disp_frame)
    layout.addWidget(self.lab_a183mm_rotate)
    layout.addWidget(self.lab_a183mm_cam_temp)
    layout.addWidget(self.lab_a183mm_cooling)
    layout.addWidget(separator1)
    cam_a183mm_exp_quickcheck_layout = QHBoxLayout()
    cam_a183mm_exp_quickcheck_layout.addWidget(self.a183mm_cam_exp_gain_depl)
    cam_a183mm_exp_quickcheck_layout.addStretch()
    cam_a183mm_exp_quickcheck_layout.addWidget(self.a183mm_cam_quick_check_align_photo)
    layout.addLayout(cam_a183mm_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a183mm_gain_layout = QHBoxLayout()
    cam_a183mm_gain_layout.addWidget(QLabel("Exp:"))
    cam_a183mm_gain_layout.addWidget(self.a183mm_cam_exp_slider)
    cam_a183mm_gain_layout.addWidget(QLabel("ms"))
    cam_a183mm_gain_layout.addWidget(QLabel("Gain:"))
    cam_a183mm_gain_layout.addWidget(self.a183mm_cam_gain_slider)
    cam_a183mm_gain_layout.addWidget(QLabel("Offset:"))
    cam_a183mm_gain_layout.addWidget(self.a183mm_cam_offset_slider)
    cam_a183mm_gain_layout.addWidget(QLabel("bin:"))
    cam_a183mm_gain_layout.addWidget(self.a183mm_cam_bin)
    layout.addLayout(cam_a183mm_gain_layout)

    cam_a183mm_temp_layout = QHBoxLayout()
    cam_a183mm_temp_layout.addWidget(QLabel("Cooler EN: "))
    cam_a183mm_temp_layout.addWidget(self.a183mm_cam_cooler)
    cam_a183mm_temp_layout.addWidget(QLabel("Temp: "))
    cam_a183mm_temp_layout.addWidget(self.a183mm_cam_target_temp_slider)
    cam_a183mm_temp_layout.addStretch()
    layout.addLayout(cam_a183mm_temp_layout)

    cam_a183mm_butt_group2 = QHBoxLayout()
    cam_a183mm_butt_group2.addWidget(self.a183mm_cam_photo_settings_button)
    cam_a183mm_butt_group2.addWidget(self.a183mm_cam_preview_settings_button)
    cam_a183mm_butt_group2.addWidget(self.a183mm_photo_reload)
    cam_a183mm_butt_group2.addWidget(self.a183mm_photo_rotate)
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
    cam_a183mm_butt_group4.addWidget(QLabel("Save"))
    cam_a183mm_butt_group4.addWidget(self.a183mm_cam_save_img)
    cam_a183mm_butt_group4.addWidget(QLabel("Dir"))
    cam_a183mm_butt_group4.addWidget(self.a183mm_cam_save_dirname)
    cam_a183mm_butt_group4.addWidget(QLabel("Delay"))
    cam_a183mm_butt_group4.addWidget(self.a183mm_cam_save_delay)
    layout.addLayout(cam_a183mm_butt_group4)

    cam_a183mm_butt_group5 = QHBoxLayout()
    cam_a183mm_butt_group5.addWidget(QLabel("Downsample"))
    cam_a183mm_butt_group5.addWidget(self.a183mm_downsample)
    cam_a183mm_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a183mm_butt_group5.addWidget(self.a183mm_cam_solve_radius)
    cam_a183mm_butt_group5.addWidget(self.a183mm_b_plate_solve_eq5)
    cam_a183mm_butt_group5.addWidget(self.a183mm_b_plate_solve_eq6)
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
    cam_a183mm_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a183mm_pic_adj3.addWidget(self.a183mm_cam_hist_draw)
    cam_a183mm_pic_adj3.addWidget(QLabel("Log:"))
    cam_a183mm_pic_adj3.addWidget(self.loghist_a183mm)
    layout.addLayout(cam_a183mm_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a183mm_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a183mm)

    self.lewy_tab3.setLayout(layout)

#############################################################################################

  def tab4_lewyUI(self):
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
    camname = 'a533mm'

    self.a533mm_cam_on = QCheckBox()
    self.a533mm_cam_on.setChecked(False)

    self.lab_a533mm_cam = QLabel("ASI533MM PRO CAM")
    self.lab_a533mm_cam.setFont(self.headline)
    self.lab_a533mm_cam.setAlignment(Qt.AlignCenter)

    self.lab_a533mm_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a533mm_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a533mm_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a533mm_rotate = QLabel("Rotate: null")
    self.lab_a533mm_cooling = QLabel("Cooler: NULL")

    self.a533mm_cam_exp_slider = QDoubleSpinBox()
    self.a533mm_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a533mm_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a533mm_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a533mm_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a533mm_cam_gain_slider = QSpinBox()

    self.a533mm_cam_offset_slider = QSpinBox()

    self.a533mm_cam_cooler = QCheckBox()
    self.a533mm_cam_cooler.setChecked(False)

    self.a533mm_cam_bin = QComboBox()
    self.a533mm_cam_bin.addItems(['NULL'])

    self.a533mm_cam_target_temp_slider = QSpinBox()

    self.a533mm_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a533mm_cam_photo_settings_button.clicked.connect(self.f_a533mm_cam_button_photo_settings)

    self.a533mm_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a533mm_cam_preview_settings_button.clicked.connect(self.f_a533mm_cam_button_preview_settings)

    self.a533mm_photo_reload = QPushButton('Reload', self)
    self.a533mm_photo_reload.clicked.connect(self.f_a533mm_window_refresh)

    self.a533mm_photo_rotate = QPushButton('Rot', self)
    self.a533mm_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a533mm_cam_save_img = QCheckBox()
    self.a533mm_cam_save_img.setChecked(False)

    self.a533mm_cam_save_dirname = QLineEdit(self)
    self.a533mm_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a533mm_cam_save_dirname.setValidator(validator1)
    self.a533mm_cam_save_dirname.setText('teleskop')

    self.a533mm_cam_save_delay = QDoubleSpinBox()
    self.a533mm_cam_save_delay.setMinimum(0.0)
    self.a533mm_cam_save_delay.setMaximum(1000.0)
    self.a533mm_cam_save_delay.setValue(0.0)
    self.a533mm_cam_save_delay.setSingleStep(1.0)

    self.a533mm_cam_circ_x = QSpinBox()
    self.a533mm_cam_circ_x.setMinimum(0)
    self.a533mm_cam_circ_x.setMaximum(3008)
    if 'a533mm_cam_circ_x' in app_settings.keys():
      self.a533mm_cam_circ_x.setValue(app_settings['a533mm_cam_circ_x'])
    else:
      self.a533mm_cam_circ_x.setValue(int(3008/2))

    self.a533mm_cam_circ_y = QSpinBox()
    self.a533mm_cam_circ_y.setMinimum(0)
    self.a533mm_cam_circ_y.setMaximum(3008)
    if 'a533mm_cam_circ_y' in app_settings.keys():
      self.a533mm_cam_circ_y.setValue(app_settings['a533mm_cam_circ_y'])
    else:
      self.a533mm_cam_circ_y.setValue(int(3008/2))

    self.a533mm_cam_circ_d = QSpinBox()
    self.a533mm_cam_circ_d.setMinimum(0)
    self.a533mm_cam_circ_d.setMaximum(1936)
    if 'a533mm_cam_circ_d' in app_settings.keys():
      self.a533mm_cam_circ_d.setValue(app_settings['a533mm_cam_circ_d'])
    else:
      self.a533mm_cam_circ_d.setValue(0)

    self.a533mm_cam_circ_c = QSpinBox()
    self.a533mm_cam_circ_c.setMinimum(0)
    self.a533mm_cam_circ_c.setMaximum(2000)
    self.a533mm_cam_circ_c.setValue(0)

    self.a533mm_downsample = QSpinBox()
    self.a533mm_downsample.setMinimum(1)
    self.a533mm_downsample.setMaximum(64)
    self.a533mm_downsample.setValue(4)

    self.a533mm_cam_solve_radius = QCheckBox()
    self.a533mm_cam_solve_radius.setChecked(True)

    self.a533mm_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a533mm_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.a533mm_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a533mm_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a533mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a533mm_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))

    self.lab_a533mm_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a533mm_cam_scale_pixel_size = QDoubleSpinBox()
    self.a533mm_cam_scale_pixel_size.setMinimum(0.1)
    self.a533mm_cam_scale_pixel_size.setMaximum(99.0)
    self.a533mm_cam_scale_pixel_size.setValue(3.76)
    self.a533mm_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a533mm_cam_scale_focal = QSpinBox()
    self.a533mm_cam_scale_focal.setMinimum(1)
    self.a533mm_cam_scale_focal.setMaximum(9999)
    if 'a533mm_cam_scale_focal' in app_settings.keys():
      self.a533mm_cam_scale_focal.setValue(app_settings['a533mm_cam_scale_focal'])
    else:
      self.a533mm_cam_scale_focal.setValue(2450)
    self.a533mm_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a533mm_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a533mm_cam_scale_pixel_scale.setMinimum(0.0)
    self.a533mm_cam_scale_pixel_scale.setMaximum(999.0)
    self.a533mm_cam_scale_pixel_scale.setValue(0.24)
    self.a533mm_cam_scale_pixel_scale.setDecimals(5)

    self.a533mm_cam_bri = QSpinBox()
    self.a533mm_cam_bri.setValue(0)
    self.a533mm_cam_bri.setMinimum(-255)
    self.a533mm_cam_bri.setMaximum(255)

    self.a533mm_cam_sat = QDoubleSpinBox()
    self.a533mm_cam_sat.setValue(1.0)
    self.a533mm_cam_sat.setMinimum(0.0)
    self.a533mm_cam_sat.setMaximum(10.0)
    self.a533mm_cam_sat.setSingleStep(0.01)

    self.a533mm_cam_gam = QDoubleSpinBox()
    self.a533mm_cam_gam.setValue(1.0)
    self.a533mm_cam_gam.setMinimum(0.0)
    self.a533mm_cam_gam.setMaximum(10.0)
    self.a533mm_cam_gam.setSingleStep(0.01)

    self.a533mm_cam_inverse = QCheckBox()
    self.a533mm_cam_inverse.setChecked(False)

    self.a533mm_cam_hist_draw = QCheckBox()
    self.a533mm_cam_hist_draw.setChecked(False)

    self.a533mm_cam_hist_equal = QCheckBox()
    self.a533mm_cam_hist_equal.setChecked(False)

    self.a533mm_cam_normalize = QCheckBox()
    self.a533mm_cam_normalize.setChecked(False)

    self.a533mm_cam_normalize_l = QDoubleSpinBox()
    self.a533mm_cam_normalize_l.setValue(0.0)
    self.a533mm_cam_normalize_l.setMinimum(0.0)
    self.a533mm_cam_normalize_l.setMaximum(100.0)
    self.a533mm_cam_normalize_l.setSingleStep(0.01)

    self.a533mm_cam_normalize_h = QDoubleSpinBox()
    self.a533mm_cam_normalize_h.setMinimum(0.0)
    self.a533mm_cam_normalize_h.setMaximum(100.0)
    self.a533mm_cam_normalize_h.setSingleStep(0.01)
    self.a533mm_cam_normalize_h.setValue(100.0)

    self.a533mm_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a533mm_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a533mm_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a533mm = QCheckBox()
    self.loghist_a533mm.setChecked(True)

    self.graphWidget_a533mm = pg.PlotWidget()
    self.hist_color_a533mm = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_a533mm = pg.mkPen(color=(0,0,0))
    self.graphWidget_a533mm.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_a533mm)
    self.graphWidget_a533mm.setBackground(self.hist_color_a533mm)


    cam_a533mm_title_layout = QHBoxLayout()
    cam_a533mm_title_layout.addStretch()
    cam_a533mm_title_layout.addWidget(self.lab_a533mm_cam)
    cam_a533mm_title_layout.addStretch()
    cam_a533mm_title_layout.addWidget(self.a533mm_cam_on)
    cam_a533mm_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a533mm_title_layout)

    layout.addWidget(self.lab_a533mm_cam_time_param)
    layout.addWidget(self.lab_a533mm_cam_time_disp_frame)
    layout.addWidget(self.lab_a533mm_rotate)
    layout.addWidget(self.lab_a533mm_cam_temp)
    layout.addWidget(self.lab_a533mm_cooling)
    layout.addWidget(separator1)
    cam_a533mm_exp_quickcheck_layout = QHBoxLayout()
    cam_a533mm_exp_quickcheck_layout.addWidget(self.a533mm_cam_exp_gain_depl)
    cam_a533mm_exp_quickcheck_layout.addStretch()
    cam_a533mm_exp_quickcheck_layout.addWidget(self.a533mm_cam_quick_check_align_photo)
    layout.addLayout(cam_a533mm_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a533mm_gain_layout = QHBoxLayout()
    cam_a533mm_gain_layout.addWidget(QLabel("Exp:"))
    cam_a533mm_gain_layout.addWidget(self.a533mm_cam_exp_slider)
    cam_a533mm_gain_layout.addWidget(QLabel("ms"))
    cam_a533mm_gain_layout.addWidget(QLabel("Gain:"))
    cam_a533mm_gain_layout.addWidget(self.a533mm_cam_gain_slider)
    cam_a533mm_gain_layout.addWidget(QLabel("Offset:"))
    cam_a533mm_gain_layout.addWidget(self.a533mm_cam_offset_slider)
    cam_a533mm_gain_layout.addWidget(QLabel("bin:"))
    cam_a533mm_gain_layout.addWidget(self.a533mm_cam_bin)
    layout.addLayout(cam_a533mm_gain_layout)

    cam_a533mm_temp_layout = QHBoxLayout()
    cam_a533mm_temp_layout.addWidget(QLabel("Cooler EN: "))
    cam_a533mm_temp_layout.addWidget(self.a533mm_cam_cooler)
    cam_a533mm_temp_layout.addWidget(QLabel("Temp: "))
    cam_a533mm_temp_layout.addWidget(self.a533mm_cam_target_temp_slider)
    cam_a533mm_temp_layout.addStretch()
    layout.addLayout(cam_a533mm_temp_layout)

    cam_a533mm_butt_group2 = QHBoxLayout()
    cam_a533mm_butt_group2.addWidget(self.a533mm_cam_photo_settings_button)
    cam_a533mm_butt_group2.addWidget(self.a533mm_cam_preview_settings_button)
    cam_a533mm_butt_group2.addWidget(self.a533mm_photo_reload)
    cam_a533mm_butt_group2.addWidget(self.a533mm_photo_rotate)
    cam_a533mm_butt_group2.addStretch()
    layout.addLayout(cam_a533mm_butt_group2)

    cam_a533mm_butt_group3 = QHBoxLayout()
    cam_a533mm_butt_group3.addWidget(QLabel("Cir X"))
    cam_a533mm_butt_group3.addWidget(self.a533mm_cam_circ_x)
    cam_a533mm_butt_group3.addWidget(QLabel("Y"))
    cam_a533mm_butt_group3.addWidget(self.a533mm_cam_circ_y)
    cam_a533mm_butt_group3.addWidget(QLabel("D"))
    cam_a533mm_butt_group3.addWidget(self.a533mm_cam_circ_d)
    cam_a533mm_butt_group3.addWidget(QLabel("C"))
    cam_a533mm_butt_group3.addWidget(self.a533mm_cam_circ_c)
    layout.addLayout(cam_a533mm_butt_group3)

    cam_a533mm_butt_group4 = QHBoxLayout()
    cam_a533mm_butt_group4.addWidget(QLabel("Save"))
    cam_a533mm_butt_group4.addWidget(self.a533mm_cam_save_img)
    cam_a533mm_butt_group4.addWidget(QLabel("Dir"))
    cam_a533mm_butt_group4.addWidget(self.a533mm_cam_save_dirname)
    cam_a533mm_butt_group4.addWidget(QLabel("Delay"))
    cam_a533mm_butt_group4.addWidget(self.a533mm_cam_save_delay)
    layout.addLayout(cam_a533mm_butt_group4)

    cam_a533mm_butt_group5 = QHBoxLayout()
    cam_a533mm_butt_group5.addWidget(QLabel("Downsample"))
    cam_a533mm_butt_group5.addWidget(self.a533mm_downsample)
    cam_a533mm_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a533mm_butt_group5.addWidget(self.a533mm_cam_solve_radius)
    cam_a533mm_butt_group5.addWidget(self.a533mm_b_plate_solve_eq5)
    cam_a533mm_butt_group5.addWidget(self.a533mm_b_plate_solve_eq6)
    cam_a533mm_butt_group5.addWidget(self.a533mm_b_plate_solve_cancel)
    layout.addLayout(cam_a533mm_butt_group5)
    layout.addWidget(self.lab_a533mm_plate_solve_status)
    layout.addWidget(separator3)

    cam_a533mm_pixel_scale = QHBoxLayout()
    cam_a533mm_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a533mm_pixel_scale.addWidget(self.a533mm_cam_scale_pixel_size)
    cam_a533mm_pixel_scale.addWidget(QLabel("F:"))
    cam_a533mm_pixel_scale.addWidget(self.a533mm_cam_scale_focal)
    cam_a533mm_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a533mm_pixel_scale.addWidget(self.a533mm_cam_scale_pixel_scale)
    layout.addLayout(cam_a533mm_pixel_scale)

    cam_a533mm_pic_adj = QHBoxLayout()
    cam_a533mm_pic_adj.addWidget(QLabel("BRI:"))
    cam_a533mm_pic_adj.addWidget(self.a533mm_cam_bri)
    cam_a533mm_pic_adj.addWidget(QLabel("SAT:"))
    cam_a533mm_pic_adj.addWidget(self.a533mm_cam_sat)
    cam_a533mm_pic_adj.addWidget(QLabel("GAM:"))
    cam_a533mm_pic_adj.addWidget(self.a533mm_cam_gam)
    layout.addLayout(cam_a533mm_pic_adj)

    cam_a533mm_pic_adj2 = QHBoxLayout()
    cam_a533mm_pic_adj2.addWidget(QLabel("INV:"))
    cam_a533mm_pic_adj2.addWidget(self.a533mm_cam_inverse)
    cam_a533mm_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a533mm_pic_adj2.addWidget(self.a533mm_cam_hist_equal)
    cam_a533mm_pic_adj2.addStretch()
    cam_a533mm_pic_adj2.addWidget(self.a533mm_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a533mm_pic_adj2)

    cam_a533mm_pic_adj3 = QHBoxLayout()
    cam_a533mm_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a533mm_pic_adj3.addWidget(self.a533mm_cam_normalize)
    cam_a533mm_pic_adj3.addWidget(QLabel("L:"))
    cam_a533mm_pic_adj3.addWidget(self.a533mm_cam_normalize_l)
    cam_a533mm_pic_adj3.addWidget(QLabel("H:"))
    cam_a533mm_pic_adj3.addWidget(self.a533mm_cam_normalize_h)
    cam_a533mm_pic_adj3.addStretch()
    cam_a533mm_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a533mm_pic_adj3.addWidget(self.a533mm_cam_hist_draw)
    cam_a533mm_pic_adj3.addWidget(QLabel("Log:"))
    cam_a533mm_pic_adj3.addWidget(self.loghist_a533mm)
    layout.addLayout(cam_a533mm_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a533mm_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a533mm)

    self.lewy_tab4.setLayout(layout)

#############################################################################################

  def tab5_lewyUI(self):
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
    camname = 'a533mc'

    self.a533mc_cam_on = QCheckBox()
    self.a533mc_cam_on.setChecked(False)

    self.lab_a533mc_cam = QLabel("ASI533MC PRO CAM")
    self.lab_a533mc_cam.setFont(self.headline)
    self.lab_a533mc_cam.setAlignment(Qt.AlignCenter)

    self.lab_a533mc_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a533mc_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a533mc_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a533mc_rotate = QLabel("Rotate: null")
    self.lab_a533mc_cooling = QLabel("Cooler: NULL")

    self.a533mc_cam_exp_slider = QDoubleSpinBox()
    self.a533mc_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a533mc_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a533mc_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a533mc_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a533mc_cam_gain_slider = QSpinBox()

    self.a533mc_cam_offset_slider = QSpinBox()

    self.a533mc_cam_cooler = QCheckBox()
    self.a533mc_cam_cooler.setChecked(False)

    self.a533mc_cam_bin = QComboBox()
    self.a533mc_cam_bin.addItems(['NULL'])

    self.a533mc_cam_target_temp_slider = QSpinBox()

    self.a533mc_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a533mc_cam_photo_settings_button.clicked.connect(self.f_a533mc_cam_button_photo_settings)

    self.a533mc_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a533mc_cam_preview_settings_button.clicked.connect(self.f_a533mc_cam_button_preview_settings)

    self.a533mc_photo_reload = QPushButton('Reload', self)
    self.a533mc_photo_reload.clicked.connect(self.f_a533mc_window_refresh)

    self.a533mc_photo_rotate = QPushButton('Rot', self)
    self.a533mc_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a533mc_cam_save_img = QCheckBox()
    self.a533mc_cam_save_img.setChecked(False)

    self.a533mc_cam_save_dirname = QLineEdit(self)
    self.a533mc_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a533mc_cam_save_dirname.setValidator(validator1)
    self.a533mc_cam_save_dirname.setText('teleskop')

    self.a533mc_cam_save_delay = QDoubleSpinBox()
    self.a533mc_cam_save_delay.setMinimum(0.0)
    self.a533mc_cam_save_delay.setMaximum(1000.0)
    self.a533mc_cam_save_delay.setValue(0.0)
    self.a533mc_cam_save_delay.setSingleStep(1.0)

    self.a533mc_cam_circ_x = QSpinBox()
    self.a533mc_cam_circ_x.setMinimum(0)
    self.a533mc_cam_circ_x.setMaximum(3008)
    if 'a533mc_cam_circ_x' in app_settings.keys():
      self.a533mc_cam_circ_x.setValue(app_settings['a533mc_cam_circ_x'])
    else:
      self.a533mc_cam_circ_x.setValue(int(3008/2))

    self.a533mc_cam_circ_y = QSpinBox()
    self.a533mc_cam_circ_y.setMinimum(0)
    self.a533mc_cam_circ_y.setMaximum(3008)
    if 'a533mc_cam_circ_y' in app_settings.keys():
      self.a533mc_cam_circ_y.setValue(app_settings['a533mc_cam_circ_y'])
    else:
      self.a533mc_cam_circ_y.setValue(int(3008/2))

    self.a533mc_cam_circ_d = QSpinBox()
    self.a533mc_cam_circ_d.setMinimum(0)
    self.a533mc_cam_circ_d.setMaximum(1936)
    if 'a533mc_cam_circ_d' in app_settings.keys():
      self.a533mc_cam_circ_d.setValue(app_settings['a533mc_cam_circ_d'])
    else:
      self.a533mc_cam_circ_d.setValue(0)

    self.a533mc_cam_circ_c = QSpinBox()
    self.a533mc_cam_circ_c.setMinimum(0)
    self.a533mc_cam_circ_c.setMaximum(2000)
    self.a533mc_cam_circ_c.setValue(0)

    self.a533mc_downsample = QSpinBox()
    self.a533mc_downsample.setMinimum(1)
    self.a533mc_downsample.setMaximum(64)
    self.a533mc_downsample.setValue(4)

    self.a533mc_cam_solve_radius = QCheckBox()
    self.a533mc_cam_solve_radius.setChecked(True)

    self.a533mc_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a533mc_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.a533mc_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a533mc_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a533mc_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a533mc_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))

    self.lab_a533mc_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a533mc_cam_scale_pixel_size = QDoubleSpinBox()
    self.a533mc_cam_scale_pixel_size.setMinimum(0.1)
    self.a533mc_cam_scale_pixel_size.setMaximum(99.0)
    self.a533mc_cam_scale_pixel_size.setValue(3.76)
    self.a533mc_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a533mc_cam_scale_focal = QSpinBox()
    self.a533mc_cam_scale_focal.setMinimum(1)
    self.a533mc_cam_scale_focal.setMaximum(9999)
    if 'a533mc_cam_scale_focal' in app_settings.keys():
      self.a533mc_cam_scale_focal.setValue(app_settings['a533mc_cam_scale_focal'])
    else:
      self.a533mc_cam_scale_focal.setValue(2450)
    self.a533mc_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a533mc_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a533mc_cam_scale_pixel_scale.setMinimum(0.0)
    self.a533mc_cam_scale_pixel_scale.setMaximum(999.0)
    self.a533mc_cam_scale_pixel_scale.setValue(0.24)
    self.a533mc_cam_scale_pixel_scale.setDecimals(5)

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

    self.a533mc_cam_hist_draw = QCheckBox()
    self.a533mc_cam_hist_draw.setChecked(False)

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
    self.a533mc_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a533mc_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a533mc = QCheckBox()
    self.loghist_a533mc.setChecked(True)

    self.graphWidget_a533mc = pg.PlotWidget()
    self.hist_color_a533mc = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_a533mc = pg.mkPen(color=(0,0,0))
    self.graphWidget_a533mc.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_a533mc)
    self.graphWidget_a533mc.setBackground(self.hist_color_a533mc)


    cam_a533mc_title_layout = QHBoxLayout()
    cam_a533mc_title_layout.addStretch()
    cam_a533mc_title_layout.addWidget(self.lab_a533mc_cam)
    cam_a533mc_title_layout.addStretch()
    cam_a533mc_title_layout.addWidget(self.a533mc_cam_on)
    cam_a533mc_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a533mc_title_layout)

    layout.addWidget(self.lab_a533mc_cam_time_param)
    layout.addWidget(self.lab_a533mc_cam_time_disp_frame)
    layout.addWidget(self.lab_a533mc_rotate)
    layout.addWidget(self.lab_a533mc_cam_temp)
    layout.addWidget(self.lab_a533mc_cooling)
    layout.addWidget(separator1)
    cam_a533mc_exp_quickcheck_layout = QHBoxLayout()
    cam_a533mc_exp_quickcheck_layout.addWidget(self.a533mc_cam_exp_gain_depl)
    cam_a533mc_exp_quickcheck_layout.addStretch()
    cam_a533mc_exp_quickcheck_layout.addWidget(self.a533mc_cam_quick_check_align_photo)
    layout.addLayout(cam_a533mc_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a533mc_gain_layout = QHBoxLayout()
    cam_a533mc_gain_layout.addWidget(QLabel("Exp:"))
    cam_a533mc_gain_layout.addWidget(self.a533mc_cam_exp_slider)
    cam_a533mc_gain_layout.addWidget(QLabel("ms"))
    cam_a533mc_gain_layout.addWidget(QLabel("Gain:"))
    cam_a533mc_gain_layout.addWidget(self.a533mc_cam_gain_slider)
    cam_a533mc_gain_layout.addWidget(QLabel("Offset:"))
    cam_a533mc_gain_layout.addWidget(self.a533mc_cam_offset_slider)
    cam_a533mc_gain_layout.addWidget(QLabel("bin:"))
    cam_a533mc_gain_layout.addWidget(self.a533mc_cam_bin)
    layout.addLayout(cam_a533mc_gain_layout)

    cam_a533mc_temp_layout = QHBoxLayout()
    cam_a533mc_temp_layout.addWidget(QLabel("Cooler EN: "))
    cam_a533mc_temp_layout.addWidget(self.a533mc_cam_cooler)
    cam_a533mc_temp_layout.addWidget(QLabel("Temp: "))
    cam_a533mc_temp_layout.addWidget(self.a533mc_cam_target_temp_slider)
    cam_a533mc_temp_layout.addStretch()
    layout.addLayout(cam_a533mc_temp_layout)

    cam_a533mc_butt_group2 = QHBoxLayout()
    cam_a533mc_butt_group2.addWidget(self.a533mc_cam_photo_settings_button)
    cam_a533mc_butt_group2.addWidget(self.a533mc_cam_preview_settings_button)
    cam_a533mc_butt_group2.addWidget(self.a533mc_photo_reload)
    cam_a533mc_butt_group2.addWidget(self.a533mc_photo_rotate)
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
    cam_a533mc_butt_group4.addWidget(QLabel("Save"))
    cam_a533mc_butt_group4.addWidget(self.a533mc_cam_save_img)
    cam_a533mc_butt_group4.addWidget(QLabel("Dir"))
    cam_a533mc_butt_group4.addWidget(self.a533mc_cam_save_dirname)
    cam_a533mc_butt_group4.addWidget(QLabel("Delay"))
    cam_a533mc_butt_group4.addWidget(self.a533mc_cam_save_delay)
    layout.addLayout(cam_a533mc_butt_group4)

    cam_a533mc_butt_group5 = QHBoxLayout()
    cam_a533mc_butt_group5.addWidget(QLabel("Downsample"))
    cam_a533mc_butt_group5.addWidget(self.a533mc_downsample)
    cam_a533mc_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a533mc_butt_group5.addWidget(self.a533mc_cam_solve_radius)
    cam_a533mc_butt_group5.addWidget(self.a533mc_b_plate_solve_eq5)
    cam_a533mc_butt_group5.addWidget(self.a533mc_b_plate_solve_eq6)
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
    cam_a533mc_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a533mc_pic_adj3.addWidget(self.a533mc_cam_hist_draw)
    cam_a533mc_pic_adj3.addWidget(QLabel("Log:"))
    cam_a533mc_pic_adj3.addWidget(self.loghist_a533mc)
    layout.addLayout(cam_a533mc_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a533mc_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a533mc)

    self.lewy_tab5.setLayout(layout)

#############################################################################################

  def tab6_lewyUI(self):
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
    camname = 'a432mm'

    self.a432mm_cam_on = QCheckBox()
    self.a432mm_cam_on.setChecked(False)

    self.lab_a432mm_cam = QLabel("ASI432MM mini CAM")
    self.lab_a432mm_cam.setFont(self.headline)
    self.lab_a432mm_cam.setAlignment(Qt.AlignCenter)

    self.lab_a432mm_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a432mm_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a432mm_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a432mm_rotate = QLabel("Rotate: null")

    self.a432mm_cam_exp_slider = QDoubleSpinBox()
    self.a432mm_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a432mm_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a432mm_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a432mm_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a432mm_cam_gain_slider = QSpinBox()

    self.a432mm_cam_offset_slider = QSpinBox()

    self.a432mm_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a432mm_cam_photo_settings_button.clicked.connect(self.f_a432mm_cam_button_photo_settings)

    self.a432mm_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a432mm_cam_preview_settings_button.clicked.connect(self.f_a432mm_cam_button_preview_settings)

    self.a432mm_photo_reload = QPushButton('Reload', self)
    self.a432mm_photo_reload.clicked.connect(self.f_a432mm_window_refresh)

    self.a432mm_photo_rotate = QPushButton('Rotate', self)
    self.a432mm_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a432mm_cam_bin = QComboBox()
    self.a432mm_cam_bin.addItems(['NULL'])

    self.a432mm_cam_circ_x = QSpinBox()
    self.a432mm_cam_circ_x.setMinimum(0)
    self.a432mm_cam_circ_x.setMaximum(1608)
    if 'a432mm_cam_circ_x' in app_settings.keys():
      self.a432mm_cam_circ_x.setValue(app_settings['a432mm_cam_circ_x'])
    else:
      self.a432mm_cam_circ_x.setValue(804)

    self.a432mm_cam_circ_y = QSpinBox()
    self.a432mm_cam_circ_y.setMinimum(0)
    self.a432mm_cam_circ_y.setMaximum(1104)
    if 'a432mm_cam_circ_y' in app_settings.keys():
      self.a432mm_cam_circ_y.setValue(app_settings['a432mm_cam_circ_y'])
    else:
      self.a432mm_cam_circ_y.setValue(552)

    self.a432mm_cam_circ_d = QSpinBox()
    self.a432mm_cam_circ_d.setMinimum(0)
    self.a432mm_cam_circ_d.setMaximum(1200)
    if 'a432mm_cam_circ_d' in app_settings.keys():
      self.a432mm_cam_circ_d.setValue(app_settings['a432mm_cam_circ_d'])
    else:
      self.a432mm_cam_circ_d.setValue(0)

    self.a432mm_cam_circ_c = QSpinBox()
    self.a432mm_cam_circ_c.setMinimum(0)
    self.a432mm_cam_circ_c.setMaximum(900)
    self.a432mm_cam_circ_c.setValue(0)

    self.a432mm_cam_save_img = QCheckBox()
    self.a432mm_cam_save_img.setChecked(False)

    self.a432mm_cam_save_dirname = QLineEdit(self)
    self.a432mm_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a432mm_cam_save_dirname.setValidator(validator1)
    self.a432mm_cam_save_dirname.setText('teleskop')

    self.a432mm_cam_save_delay = QDoubleSpinBox()
    self.a432mm_cam_save_delay.setMinimum(0.0)
    self.a432mm_cam_save_delay.setMaximum(1000.0)
    self.a432mm_cam_save_delay.setValue(0.0)
    self.a432mm_cam_save_delay.setSingleStep(1.0)

    self.a432mm_downsample = QSpinBox()
    self.a432mm_downsample.setMinimum(1)
    self.a432mm_downsample.setMaximum(64)
    self.a432mm_downsample.setValue(2)

    self.a432mm_cam_solve_radius = QCheckBox()
    self.a432mm_cam_solve_radius.setChecked(True)

    self.a432mm_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a432mm_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.a432mm_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a432mm_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a432mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a432mm_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))
    self.lab_a432mm_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a432mm_cam_scale_pixel_size = QDoubleSpinBox()
    self.a432mm_cam_scale_pixel_size.setMinimum(0.1)
    self.a432mm_cam_scale_pixel_size.setMaximum(99.0)
    self.a432mm_cam_scale_pixel_size.setValue(9.0)
    self.a432mm_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a432mm_cam_scale_focal = QSpinBox()
    self.a432mm_cam_scale_focal.setMinimum(1)
    self.a432mm_cam_scale_focal.setMaximum(9999)
    if 'a432mm_cam_scale_focal' in app_settings.keys():
      self.a432mm_cam_scale_focal.setValue(app_settings['a432mm_cam_scale_focal'])
    else:
      self.a432mm_cam_scale_focal.setValue(505)
    self.a432mm_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a432mm_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a432mm_cam_scale_pixel_scale.setMinimum(0.0)
    self.a432mm_cam_scale_pixel_scale.setMaximum(999.0)
    self.a432mm_cam_scale_pixel_scale.setValue(1.53)
    self.a432mm_cam_scale_pixel_scale.setDecimals(5)

    self.a432mm_cam_bri = QSpinBox()
    self.a432mm_cam_bri.setValue(0)
    self.a432mm_cam_bri.setMinimum(-255)
    self.a432mm_cam_bri.setMaximum(255)

    self.a432mm_cam_sat = QDoubleSpinBox()
    self.a432mm_cam_sat.setValue(1.0)
    self.a432mm_cam_sat.setMinimum(0.0)
    self.a432mm_cam_sat.setMaximum(10.0)
    self.a432mm_cam_sat.setSingleStep(0.01)

    self.a432mm_cam_gam = QDoubleSpinBox()
    self.a432mm_cam_gam.setValue(1.0)
    self.a432mm_cam_gam.setMinimum(0.0)
    self.a432mm_cam_gam.setMaximum(10.0)
    self.a432mm_cam_gam.setSingleStep(0.01)

    self.a432mm_cam_inverse = QCheckBox()
    self.a432mm_cam_inverse.setChecked(False)

    self.a432mm_cam_hist_draw = QCheckBox()
    self.a432mm_cam_hist_draw.setChecked(False)

    self.a432mm_cam_hist_equal = QCheckBox()
    self.a432mm_cam_hist_equal.setChecked(False)

    self.a432mm_cam_normalize = QCheckBox()
    self.a432mm_cam_normalize.setChecked(False)

    self.a432mm_cam_normalize_l = QDoubleSpinBox()
    self.a432mm_cam_normalize_l.setValue(0.0)
    self.a432mm_cam_normalize_l.setMinimum(0.0)
    self.a432mm_cam_normalize_l.setMaximum(100.0)
    self.a432mm_cam_normalize_l.setSingleStep(0.01)

    self.a432mm_cam_normalize_h = QDoubleSpinBox()
    self.a432mm_cam_normalize_h.setMinimum(0.0)
    self.a432mm_cam_normalize_h.setMaximum(100.0)
    self.a432mm_cam_normalize_h.setSingleStep(0.01)
    self.a432mm_cam_normalize_h.setValue(100.0)

    self.a432mm_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a432mm_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a432mm_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a432mm = QCheckBox()
    self.loghist_a432mm.setChecked(True)

    self.graphWidget_a432mm = pg.PlotWidget()
    self.hist_color_a432mm = self.palette().color(QtGui.QPalette.Window)
    self.graphWidget_a432mm.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_gray)
    self.graphWidget_a432mm.setBackground(self.hist_color_a432mm)


    cam_a432mm_title_layout = QHBoxLayout()
    cam_a432mm_title_layout.addStretch()
    cam_a432mm_title_layout.addWidget(self.lab_a432mm_cam)
    cam_a432mm_title_layout.addStretch()
    cam_a432mm_title_layout.addWidget(self.a432mm_cam_on)
    cam_a432mm_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a432mm_title_layout)

    layout.addWidget(self.lab_a432mm_cam_time_param)
    layout.addWidget(self.lab_a432mm_cam_time_disp_frame)
    layout.addWidget(self.lab_a432mm_cam_temp)
    layout.addWidget(self.lab_a432mm_rotate)
    layout.addWidget(separator1)
    cam_a432mm_exp_quickcheck_layout = QHBoxLayout()
    cam_a432mm_exp_quickcheck_layout.addWidget(self.a432mm_cam_exp_gain_depl)
    cam_a432mm_exp_quickcheck_layout.addStretch()
    cam_a432mm_exp_quickcheck_layout.addWidget(self.a432mm_cam_quick_check_align_photo)
    layout.addLayout(cam_a432mm_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a432mm_gain_layout = QHBoxLayout()
    cam_a432mm_gain_layout.addWidget(QLabel("Exp:"))
    cam_a432mm_gain_layout.addWidget(self.a432mm_cam_exp_slider)
    cam_a432mm_gain_layout.addWidget(QLabel("ms"))
    cam_a432mm_gain_layout.addWidget(QLabel("Gain:"))
    cam_a432mm_gain_layout.addWidget(self.a432mm_cam_gain_slider)
    cam_a432mm_gain_layout.addWidget(QLabel("Offset:"))
    cam_a432mm_gain_layout.addWidget(self.a432mm_cam_offset_slider)
    cam_a432mm_gain_layout.addWidget(QLabel("bin:"))
    cam_a432mm_gain_layout.addWidget(self.a432mm_cam_bin)
    layout.addLayout(cam_a432mm_gain_layout)

    cam_a432mm_butt_group2 = QHBoxLayout()
    cam_a432mm_butt_group2.addWidget(self.a432mm_cam_photo_settings_button)
    cam_a432mm_butt_group2.addWidget(self.a432mm_cam_preview_settings_button)
    cam_a432mm_butt_group2.addWidget(self.a432mm_photo_reload)
    cam_a432mm_butt_group2.addWidget(self.a432mm_photo_rotate)
    cam_a432mm_butt_group2.addStretch()
    layout.addLayout(cam_a432mm_butt_group2)

    cam_a432mm_butt_group3 = QHBoxLayout()
    cam_a432mm_butt_group3.addWidget(QLabel("Cir X"))
    cam_a432mm_butt_group3.addWidget(self.a432mm_cam_circ_x)
    cam_a432mm_butt_group3.addWidget(QLabel("Y"))
    cam_a432mm_butt_group3.addWidget(self.a432mm_cam_circ_y)
    cam_a432mm_butt_group3.addWidget(QLabel("D"))
    cam_a432mm_butt_group3.addWidget(self.a432mm_cam_circ_d)
    cam_a432mm_butt_group3.addWidget(QLabel("C"))
    cam_a432mm_butt_group3.addWidget(self.a432mm_cam_circ_c)
    layout.addLayout(cam_a432mm_butt_group3)

    cam_a432mm_butt_group4 = QHBoxLayout()
    cam_a432mm_butt_group4.addWidget(QLabel("Save"))
    cam_a432mm_butt_group4.addWidget(self.a432mm_cam_save_img)
    cam_a432mm_butt_group4.addWidget(QLabel("Dir"))
    cam_a432mm_butt_group4.addWidget(self.a432mm_cam_save_dirname)
    cam_a432mm_butt_group4.addWidget(QLabel("Delay"))
    cam_a432mm_butt_group4.addWidget(self.a432mm_cam_save_delay)
    layout.addLayout(cam_a432mm_butt_group4)

    cam_a432mm_butt_group5 = QHBoxLayout()
    cam_a432mm_butt_group5.addWidget(QLabel("Downsample"))
    cam_a432mm_butt_group5.addWidget(self.a432mm_downsample)
    cam_a432mm_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a432mm_butt_group5.addWidget(self.a432mm_cam_solve_radius)
    cam_a432mm_butt_group5.addWidget(self.a432mm_b_plate_solve_eq5)
    cam_a432mm_butt_group5.addWidget(self.a432mm_b_plate_solve_eq6)
    cam_a432mm_butt_group5.addWidget(self.a432mm_b_plate_solve_cancel)
    layout.addLayout(cam_a432mm_butt_group5)
    layout.addWidget(self.lab_a432mm_plate_solve_status)
    layout.addWidget(separator3)

    cam_a432mm_pixel_scale = QHBoxLayout()
    cam_a432mm_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a432mm_pixel_scale.addWidget(self.a432mm_cam_scale_pixel_size)
    cam_a432mm_pixel_scale.addWidget(QLabel("F:"))
    cam_a432mm_pixel_scale.addWidget(self.a432mm_cam_scale_focal)
    cam_a432mm_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a432mm_pixel_scale.addWidget(self.a432mm_cam_scale_pixel_scale)
    layout.addLayout(cam_a432mm_pixel_scale)

    cam_a432mm_pic_adj = QHBoxLayout()
    cam_a432mm_pic_adj.addWidget(QLabel("BRI:"))
    cam_a432mm_pic_adj.addWidget(self.a432mm_cam_bri)
    cam_a432mm_pic_adj.addWidget(QLabel("SAT:"))
    cam_a432mm_pic_adj.addWidget(self.a432mm_cam_sat)
    cam_a432mm_pic_adj.addWidget(QLabel("GAM:"))
    cam_a432mm_pic_adj.addWidget(self.a432mm_cam_gam)
    layout.addLayout(cam_a432mm_pic_adj)

    cam_a432mm_pic_adj2 = QHBoxLayout()
    cam_a432mm_pic_adj2.addWidget(QLabel("INV:"))
    cam_a432mm_pic_adj2.addWidget(self.a432mm_cam_inverse)
    cam_a432mm_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a432mm_pic_adj2.addWidget(self.a432mm_cam_hist_equal)
    cam_a432mm_pic_adj2.addStretch()
    cam_a432mm_pic_adj2.addWidget(self.a432mm_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a432mm_pic_adj2)

    cam_a432mm_pic_adj3 = QHBoxLayout()
    cam_a432mm_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a432mm_pic_adj3.addWidget(self.a432mm_cam_normalize)
    cam_a432mm_pic_adj3.addWidget(QLabel("L:"))
    cam_a432mm_pic_adj3.addWidget(self.a432mm_cam_normalize_l)
    cam_a432mm_pic_adj3.addWidget(QLabel("H:"))
    cam_a432mm_pic_adj3.addWidget(self.a432mm_cam_normalize_h)
    cam_a432mm_pic_adj3.addStretch()
    cam_a432mm_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a432mm_pic_adj3.addWidget(self.a432mm_cam_hist_draw)
    cam_a432mm_pic_adj3.addWidget(QLabel("Log:"))
    cam_a432mm_pic_adj3.addWidget(self.loghist_a432mm)
    layout.addLayout(cam_a432mm_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a432mm_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a432mm)

    self.lewy_tab6.setLayout(layout)

#############################################################################################

  def tab7_lewyUI(self):
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
    camname = 'a462mc'

    self.a462mc_cam_on = QCheckBox()
    self.a462mc_cam_on.setChecked(False)

    self.lab_a462mc_cam = QLabel("ASI462MC CAM")
    self.lab_a462mc_cam.setFont(self.headline)
    self.lab_a462mc_cam.setAlignment(Qt.AlignCenter)

    self.lab_a462mc_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a462mc_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a462mc_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a462mc_rotate = QLabel("Rotate: null")

    self.a462mc_cam_exp_slider = QDoubleSpinBox()
    self.a462mc_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a462mc_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a462mc_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a462mc_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a462mc_cam_gain_slider = QSpinBox()

    self.a462mc_cam_offset_slider = QSpinBox()

    self.a462mc_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a462mc_cam_photo_settings_button.clicked.connect(self.f_a462mc_cam_button_photo_settings)

    self.a462mc_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a462mc_cam_preview_settings_button.clicked.connect(self.f_a462mc_cam_button_preview_settings)

    self.a462mc_photo_reload = QPushButton('Reload', self)
    self.a462mc_photo_reload.clicked.connect(self.f_a462mc_window_refresh)

    self.a462mc_photo_rotate = QPushButton('Rot', self)
    self.a462mc_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a462mc_cam_bin = QComboBox()
    self.a462mc_cam_bin.addItems(['NULL'])

    self.a462mc_cam_save_img = QCheckBox()
    self.a462mc_cam_save_img.setChecked(False)

    self.a462mc_cam_save_dirname = QLineEdit(self)
    self.a462mc_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a462mc_cam_save_dirname.setValidator(validator1)
    self.a462mc_cam_save_dirname.setText('teleskop')

    self.a462mc_cam_save_delay = QDoubleSpinBox()
    self.a462mc_cam_save_delay.setMinimum(0.0)
    self.a462mc_cam_save_delay.setMaximum(1000.0)
    self.a462mc_cam_save_delay.setValue(0.0)
    self.a462mc_cam_save_delay.setSingleStep(1.0)

    self.a462mc_cam_circ_x = QSpinBox()
    self.a462mc_cam_circ_x.setMinimum(0)
    self.a462mc_cam_circ_x.setMaximum(1936)
    if 'a462mc_cam_circ_x' in app_settings.keys():
      self.a462mc_cam_circ_x.setValue(app_settings['a462mc_cam_circ_x'])
    else:
      self.a462mc_cam_circ_x.setValue(968)

    self.a462mc_cam_circ_y = QSpinBox()
    self.a462mc_cam_circ_y.setMinimum(0)
    self.a462mc_cam_circ_y.setMaximum(1096)
    if 'a462mc_cam_circ_y' in app_settings.keys():
      self.a462mc_cam_circ_y.setValue(app_settings['a462mc_cam_circ_y'])
    else:
      self.a462mc_cam_circ_y.setValue(548)

    self.a462mc_cam_circ_d = QSpinBox()
    self.a462mc_cam_circ_d.setMinimum(0)
    self.a462mc_cam_circ_d.setMaximum(1936)
    if 'a462mc_cam_circ_d' in app_settings.keys():
      self.a462mc_cam_circ_d.setValue(app_settings['a462mc_cam_circ_d'])
    else:
      self.a462mc_cam_circ_d.setValue(0)

    self.a462mc_cam_circ_c = QSpinBox()
    self.a462mc_cam_circ_c.setMinimum(0)
    self.a462mc_cam_circ_c.setMaximum(600)
    self.a462mc_cam_circ_c.setValue(0)

    self.a462mc_downsample = QSpinBox()
    self.a462mc_downsample.setMinimum(1)
    self.a462mc_downsample.setMaximum(64)
    self.a462mc_downsample.setValue(2)

    self.a462mc_cam_solve_radius = QCheckBox()
    self.a462mc_cam_solve_radius.setChecked(True)

    self.a462mc_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a462mc_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.a462mc_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a462mc_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a462mc_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a462mc_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))

    self.lab_a462mc_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a462mc_cam_scale_pixel_size = QDoubleSpinBox()
    self.a462mc_cam_scale_pixel_size.setMinimum(0.1)
    self.a462mc_cam_scale_pixel_size.setMaximum(99.0)
    self.a462mc_cam_scale_pixel_size.setValue(2.9)
    self.a462mc_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a462mc_cam_scale_focal = QSpinBox()
    self.a462mc_cam_scale_focal.setMinimum(1)
    self.a462mc_cam_scale_focal.setMaximum(9999)
    if 'a462mc_cam_scale_focal' in app_settings.keys():
      self.a462mc_cam_scale_focal.setValue(app_settings['a462mc_cam_scale_focal'])
    else:
      self.a462mc_cam_scale_focal.setValue(2450)
    self.a462mc_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a462mc_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a462mc_cam_scale_pixel_scale.setMinimum(0.0)
    self.a462mc_cam_scale_pixel_scale.setMaximum(999.0)
    self.a462mc_cam_scale_pixel_scale.setValue(0.24)
    self.a462mc_cam_scale_pixel_scale.setDecimals(5)

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

    self.a462mc_cam_hist_draw = QCheckBox()
    self.a462mc_cam_hist_draw.setChecked(False)

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
    self.a462mc_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a462mc_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a462mc = QCheckBox()
    self.loghist_a462mc.setChecked(True)

    self.graphWidget_a462mc = pg.PlotWidget()
    self.hist_color_a462mc = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_a462mc = pg.mkPen(color=(0,0,0))
    self.graphWidget_a462mc.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_a462mc)
    self.graphWidget_a462mc.setBackground(self.hist_color_a462mc)


    cam_a462mc_title_layout = QHBoxLayout()
    cam_a462mc_title_layout.addStretch()
    cam_a462mc_title_layout.addWidget(self.lab_a462mc_cam)
    cam_a462mc_title_layout.addStretch()
    cam_a462mc_title_layout.addWidget(self.a462mc_cam_on)
    cam_a462mc_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a462mc_title_layout)

    layout.addWidget(self.lab_a462mc_cam_time_param)
    layout.addWidget(self.lab_a462mc_cam_time_disp_frame)
    layout.addWidget(self.lab_a462mc_cam_temp)
    layout.addWidget(self.lab_a462mc_rotate)
    layout.addWidget(separator1)
    cam_a462mc_exp_quickcheck_layout = QHBoxLayout()
    cam_a462mc_exp_quickcheck_layout.addWidget(self.a462mc_cam_exp_gain_depl)
    cam_a462mc_exp_quickcheck_layout.addStretch()
    cam_a462mc_exp_quickcheck_layout.addWidget(self.a462mc_cam_quick_check_align_photo)
    layout.addLayout(cam_a462mc_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a462mc_gain_layout = QHBoxLayout()
    cam_a462mc_gain_layout.addWidget(QLabel("Exp:"))
    cam_a462mc_gain_layout.addWidget(self.a462mc_cam_exp_slider)
    cam_a462mc_gain_layout.addWidget(QLabel("ms"))
    cam_a462mc_gain_layout.addWidget(QLabel("Gain:"))
    cam_a462mc_gain_layout.addWidget(self.a462mc_cam_gain_slider)
    cam_a462mc_gain_layout.addWidget(QLabel("Offset:"))
    cam_a462mc_gain_layout.addWidget(self.a462mc_cam_offset_slider)
    cam_a462mc_gain_layout.addWidget(QLabel("bin:"))
    cam_a462mc_gain_layout.addWidget(self.a462mc_cam_bin)
    layout.addLayout(cam_a462mc_gain_layout)

    cam_a462mc_butt_group2 = QHBoxLayout()
    cam_a462mc_butt_group2.addWidget(self.a462mc_cam_photo_settings_button)
    cam_a462mc_butt_group2.addWidget(self.a462mc_cam_preview_settings_button)
    cam_a462mc_butt_group2.addWidget(self.a462mc_photo_reload)
    cam_a462mc_butt_group2.addWidget(self.a462mc_photo_rotate)
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
    cam_a462mc_butt_group4.addWidget(QLabel("Save"))
    cam_a462mc_butt_group4.addWidget(self.a462mc_cam_save_img)
    cam_a462mc_butt_group4.addWidget(QLabel("Dir"))
    cam_a462mc_butt_group4.addWidget(self.a462mc_cam_save_dirname)
    cam_a462mc_butt_group4.addWidget(QLabel("Delay"))
    cam_a462mc_butt_group4.addWidget(self.a462mc_cam_save_delay)
    layout.addLayout(cam_a462mc_butt_group4)

    cam_a462mc_butt_group5 = QHBoxLayout()
    cam_a462mc_butt_group5.addWidget(QLabel("Downsample"))
    cam_a462mc_butt_group5.addWidget(self.a462mc_downsample)
    cam_a462mc_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a462mc_butt_group5.addWidget(self.a462mc_cam_solve_radius)
    cam_a462mc_butt_group5.addWidget(self.a462mc_b_plate_solve_eq5)
    cam_a462mc_butt_group5.addWidget(self.a462mc_b_plate_solve_eq6)
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
    cam_a462mc_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a462mc_pic_adj3.addWidget(self.a462mc_cam_hist_draw)
    cam_a462mc_pic_adj3.addWidget(QLabel("Log:"))
    cam_a462mc_pic_adj3.addWidget(self.loghist_a462mc)
    layout.addLayout(cam_a462mc_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a462mc_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a462mc)

    self.lewy_tab7.setLayout(layout)

#############################################################################################

  def tab8_lewyUI(self):
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
    camname = 'a120mm'

    self.a120mm_cam_on = QCheckBox()
    self.a120mm_cam_on.setChecked(False)

    self.lab_a120mm_cam = QLabel("ASI120MM mini CAM")
    self.lab_a120mm_cam.setFont(self.headline)
    self.lab_a120mm_cam.setAlignment(Qt.AlignCenter)

    self.lab_a120mm_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a120mm_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a120mm_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a120mm_rotate = QLabel("Rotate: null")

    self.a120mm_cam_exp_slider = QDoubleSpinBox()
    self.a120mm_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a120mm_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a120mm_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a120mm_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a120mm_cam_gain_slider = QSpinBox()

    self.a120mm_cam_offset_slider = QSpinBox()

    self.a120mm_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a120mm_cam_photo_settings_button.clicked.connect(self.f_a120mm_cam_button_photo_settings)

    self.a120mm_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a120mm_cam_preview_settings_button.clicked.connect(self.f_a120mm_cam_button_preview_settings)

    self.a120mm_photo_reload = QPushButton('Reload', self)
    self.a120mm_photo_reload.clicked.connect(self.f_a120mm_window_refresh)

    self.a120mm_photo_rotate = QPushButton('Rotate', self)
    self.a120mm_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a120mm_cam_bin = QComboBox()
    self.a120mm_cam_bin.addItems(['NULL'])

    self.a120mm_cam_circ_x = QSpinBox()
    self.a120mm_cam_circ_x.setMinimum(0)
    self.a120mm_cam_circ_x.setMaximum(1280)
    if 'a120mm_cam_circ_x' in app_settings.keys():
      self.a120mm_cam_circ_x.setValue(app_settings['a120mm_cam_circ_x'])
    else:
      self.a120mm_cam_circ_x.setValue(640)

    self.a120mm_cam_circ_y = QSpinBox()
    self.a120mm_cam_circ_y.setMinimum(0)
    self.a120mm_cam_circ_y.setMaximum(960)
    if 'a120mm_cam_circ_y' in app_settings.keys():
      self.a120mm_cam_circ_y.setValue(app_settings['a120mm_cam_circ_y'])
    else:
      self.a120mm_cam_circ_y.setValue(480)

    self.a120mm_cam_circ_d = QSpinBox()
    self.a120mm_cam_circ_d.setMinimum(0)
    self.a120mm_cam_circ_d.setMaximum(1200)
    if 'a120mm_cam_circ_d' in app_settings.keys():
      self.a120mm_cam_circ_d.setValue(app_settings['a120mm_cam_circ_d'])
    else:
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

    self.a120mm_cam_save_delay = QDoubleSpinBox()
    self.a120mm_cam_save_delay.setMinimum(0.0)
    self.a120mm_cam_save_delay.setMaximum(1000.0)
    self.a120mm_cam_save_delay.setValue(0.0)
    self.a120mm_cam_save_delay.setSingleStep(1.0)

    self.a120mm_downsample = QSpinBox()
    self.a120mm_downsample.setMinimum(1)
    self.a120mm_downsample.setMaximum(64)
    self.a120mm_downsample.setValue(2)

    self.a120mm_cam_solve_radius = QCheckBox()
    self.a120mm_cam_solve_radius.setChecked(False)

    self.a120mm_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a120mm_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.a120mm_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a120mm_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a120mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a120mm_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))
    self.lab_a120mm_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a120mm_cam_scale_pixel_size = QDoubleSpinBox()
    self.a120mm_cam_scale_pixel_size.setMinimum(0.1)
    self.a120mm_cam_scale_pixel_size.setMaximum(99.0)
    self.a120mm_cam_scale_pixel_size.setValue(3.75)
    self.a120mm_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a120mm_cam_scale_focal = QSpinBox()
    self.a120mm_cam_scale_focal.setMinimum(1)
    self.a120mm_cam_scale_focal.setMaximum(9999)
    if 'a120mm_cam_scale_focal' in app_settings.keys():
      self.a120mm_cam_scale_focal.setValue(app_settings['a120mm_cam_scale_focal'])
    else:
      self.a120mm_cam_scale_focal.setValue(505)
    self.a120mm_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a120mm_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a120mm_cam_scale_pixel_scale.setMinimum(0.0)
    self.a120mm_cam_scale_pixel_scale.setMaximum(999.0)
    self.a120mm_cam_scale_pixel_scale.setValue(1.53)
    self.a120mm_cam_scale_pixel_scale.setDecimals(5)

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

    self.a120mm_cam_hist_draw = QCheckBox()
    self.a120mm_cam_hist_draw.setChecked(False)

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
    self.a120mm_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a120mm_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a120mm = QCheckBox()
    self.loghist_a120mm.setChecked(True)

    self.graphWidget_a120mm = pg.PlotWidget()
    self.hist_color_a120mm = self.palette().color(QtGui.QPalette.Window)
    self.graphWidget_a120mm.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_gray)
    self.graphWidget_a120mm.setBackground(self.hist_color_a120mm)


    cam_a120mm_title_layout = QHBoxLayout()
    cam_a120mm_title_layout.addStretch()
    cam_a120mm_title_layout.addWidget(self.lab_a120mm_cam)
    cam_a120mm_title_layout.addStretch()
    cam_a120mm_title_layout.addWidget(self.a120mm_cam_on)
    cam_a120mm_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a120mm_title_layout)

    layout.addWidget(self.lab_a120mm_cam_time_param)
    layout.addWidget(self.lab_a120mm_cam_time_disp_frame)
    layout.addWidget(self.lab_a120mm_cam_temp)
    layout.addWidget(self.lab_a120mm_rotate)
    layout.addWidget(separator1)
    cam_a120mm_exp_quickcheck_layout = QHBoxLayout()
    cam_a120mm_exp_quickcheck_layout.addWidget(self.a120mm_cam_exp_gain_depl)
    cam_a120mm_exp_quickcheck_layout.addStretch()
    cam_a120mm_exp_quickcheck_layout.addWidget(self.a120mm_cam_quick_check_align_photo)
    layout.addLayout(cam_a120mm_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a120mm_gain_layout = QHBoxLayout()
    cam_a120mm_gain_layout.addWidget(QLabel("Exp:"))
    cam_a120mm_gain_layout.addWidget(self.a120mm_cam_exp_slider)
    cam_a120mm_gain_layout.addWidget(QLabel("ms"))
    cam_a120mm_gain_layout.addWidget(QLabel("Gain:"))
    cam_a120mm_gain_layout.addWidget(self.a120mm_cam_gain_slider)
    cam_a120mm_gain_layout.addWidget(QLabel("Offset:"))
    cam_a120mm_gain_layout.addWidget(self.a120mm_cam_offset_slider)
    cam_a120mm_gain_layout.addWidget(QLabel("bin:"))
    cam_a120mm_gain_layout.addWidget(self.a120mm_cam_bin)
    layout.addLayout(cam_a120mm_gain_layout)

    cam_a120mm_butt_group2 = QHBoxLayout()
    cam_a120mm_butt_group2.addWidget(self.a120mm_cam_photo_settings_button)
    cam_a120mm_butt_group2.addWidget(self.a120mm_cam_preview_settings_button)
    cam_a120mm_butt_group2.addWidget(self.a120mm_photo_reload)
    cam_a120mm_butt_group2.addWidget(self.a120mm_photo_rotate)
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
    cam_a120mm_butt_group4.addWidget(QLabel("Save"))
    cam_a120mm_butt_group4.addWidget(self.a120mm_cam_save_img)
    cam_a120mm_butt_group4.addWidget(QLabel("Dir"))
    cam_a120mm_butt_group4.addWidget(self.a120mm_cam_save_dirname)
    cam_a120mm_butt_group4.addWidget(QLabel("Delay"))
    cam_a120mm_butt_group4.addWidget(self.a120mm_cam_save_delay)
    layout.addLayout(cam_a120mm_butt_group4)

    cam_a120mm_butt_group5 = QHBoxLayout()
    cam_a120mm_butt_group5.addWidget(QLabel("Downsample"))
    cam_a120mm_butt_group5.addWidget(self.a120mm_downsample)
    cam_a120mm_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a120mm_butt_group5.addWidget(self.a120mm_cam_solve_radius)
    cam_a120mm_butt_group5.addWidget(self.a120mm_b_plate_solve_eq5)
    cam_a120mm_butt_group5.addWidget(self.a120mm_b_plate_solve_eq6)
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
    cam_a120mm_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a120mm_pic_adj3.addWidget(self.a120mm_cam_hist_draw)
    cam_a120mm_pic_adj3.addWidget(QLabel("Log:"))
    cam_a120mm_pic_adj3.addWidget(self.loghist_a120mm)
    layout.addLayout(cam_a120mm_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a120mm_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a120mm)

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
    camname = 'a290mm'

    self.a290mm_cam_on = QCheckBox()
    self.a290mm_cam_on.setChecked(False)

    self.lab_a290mm_cam = QLabel("ASI290MM mini CAM")
    self.lab_a290mm_cam.setFont(self.headline)
    self.lab_a290mm_cam.setAlignment(Qt.AlignCenter)

    self.lab_a290mm_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a290mm_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a290mm_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a290mm_rotate = QLabel("Rotate: null")

    self.a290mm_cam_exp_slider = QDoubleSpinBox()
    self.a290mm_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a290mm_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a290mm_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a290mm_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a290mm_cam_gain_slider = QSpinBox()

    self.a290mm_cam_offset_slider = QSpinBox()

    self.a290mm_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a290mm_cam_photo_settings_button.clicked.connect(self.f_a290mm_cam_button_photo_settings)

    self.a290mm_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a290mm_cam_preview_settings_button.clicked.connect(self.f_a290mm_cam_button_preview_settings)

    self.a290mm_photo_reload = QPushButton('Reload', self)
    self.a290mm_photo_reload.clicked.connect(self.f_a290mm_window_refresh)

    self.a290mm_photo_rotate = QPushButton('Rotate', self)
    self.a290mm_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a290mm_cam_bin = QComboBox()
    self.a290mm_cam_bin.addItems(['NULL'])

    self.a290mm_cam_circ_x = QSpinBox()
    self.a290mm_cam_circ_x.setMinimum(0)
    self.a290mm_cam_circ_x.setMaximum(1936)
    if 'a290mm_cam_circ_x' in app_settings.keys():
      self.a290mm_cam_circ_x.setValue(app_settings['a290mm_cam_circ_x'])
    else:
      self.a290mm_cam_circ_x.setValue(968)

    self.a290mm_cam_circ_y = QSpinBox()
    self.a290mm_cam_circ_y.setMinimum(0)
    self.a290mm_cam_circ_y.setMaximum(1096)
    if 'a290mm_cam_circ_y' in app_settings.keys():
      self.a290mm_cam_circ_y.setValue(app_settings['a290mm_cam_circ_y'])
    else:
      self.a290mm_cam_circ_y.setValue(548)

    self.a290mm_cam_circ_d = QSpinBox()
    self.a290mm_cam_circ_d.setMinimum(0)
    self.a290mm_cam_circ_d.setMaximum(1200)
    if 'a290mm_cam_circ_d' in app_settings.keys():
      self.a290mm_cam_circ_d.setValue(app_settings['a290mm_cam_circ_d'])
    else:
      self.a290mm_cam_circ_d.setValue(0)

    self.a290mm_cam_circ_c = QSpinBox()
    self.a290mm_cam_circ_c.setMinimum(0)
    self.a290mm_cam_circ_c.setMaximum(900)
    self.a290mm_cam_circ_c.setValue(0)

    self.a290mm_cam_save_img = QCheckBox()
    self.a290mm_cam_save_img.setChecked(False)

    self.a290mm_cam_save_dirname = QLineEdit(self)
    self.a290mm_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a290mm_cam_save_dirname.setValidator(validator1)
    self.a290mm_cam_save_dirname.setText('teleskop')

    self.a290mm_cam_save_delay = QDoubleSpinBox()
    self.a290mm_cam_save_delay.setMinimum(0.0)
    self.a290mm_cam_save_delay.setMaximum(1000.0)
    self.a290mm_cam_save_delay.setValue(0.0)
    self.a290mm_cam_save_delay.setSingleStep(1.0)

    self.a290mm_downsample = QSpinBox()
    self.a290mm_downsample.setMinimum(1)
    self.a290mm_downsample.setMaximum(64)
    self.a290mm_downsample.setValue(2)

    self.a290mm_cam_solve_radius = QCheckBox()
    self.a290mm_cam_solve_radius.setChecked(False)

    self.a290mm_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a290mm_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.a290mm_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a290mm_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a290mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a290mm_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))
    self.lab_a290mm_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a290mm_cam_scale_pixel_size = QDoubleSpinBox()
    self.a290mm_cam_scale_pixel_size.setMinimum(0.1)
    self.a290mm_cam_scale_pixel_size.setMaximum(99.0)
    self.a290mm_cam_scale_pixel_size.setValue(2.9)
    self.a290mm_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a290mm_cam_scale_focal = QSpinBox()
    self.a290mm_cam_scale_focal.setMinimum(1)
    self.a290mm_cam_scale_focal.setMaximum(9999)
    if 'a290mm_cam_scale_focal' in app_settings.keys():
      self.a290mm_cam_scale_focal.setValue(app_settings['a290mm_cam_scale_focal'])
    else:
      self.a290mm_cam_scale_focal.setValue(505)
    self.a290mm_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a290mm_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a290mm_cam_scale_pixel_scale.setMinimum(0.0)
    self.a290mm_cam_scale_pixel_scale.setMaximum(999.0)
    self.a290mm_cam_scale_pixel_scale.setValue(1.53)
    self.a290mm_cam_scale_pixel_scale.setDecimals(5)

    self.a290mm_cam_bri = QSpinBox()
    self.a290mm_cam_bri.setValue(0)
    self.a290mm_cam_bri.setMinimum(-255)
    self.a290mm_cam_bri.setMaximum(255)

    self.a290mm_cam_sat = QDoubleSpinBox()
    self.a290mm_cam_sat.setValue(1.0)
    self.a290mm_cam_sat.setMinimum(0.0)
    self.a290mm_cam_sat.setMaximum(10.0)
    self.a290mm_cam_sat.setSingleStep(0.01)

    self.a290mm_cam_gam = QDoubleSpinBox()
    self.a290mm_cam_gam.setValue(1.0)
    self.a290mm_cam_gam.setMinimum(0.0)
    self.a290mm_cam_gam.setMaximum(10.0)
    self.a290mm_cam_gam.setSingleStep(0.01)

    self.a290mm_cam_inverse = QCheckBox()
    self.a290mm_cam_inverse.setChecked(False)

    self.a290mm_cam_hist_draw = QCheckBox()
    self.a290mm_cam_hist_draw.setChecked(False)

    self.a290mm_cam_hist_equal = QCheckBox()
    self.a290mm_cam_hist_equal.setChecked(False)

    self.a290mm_cam_normalize = QCheckBox()
    self.a290mm_cam_normalize.setChecked(False)

    self.a290mm_cam_normalize_l = QDoubleSpinBox()
    self.a290mm_cam_normalize_l.setValue(0.0)
    self.a290mm_cam_normalize_l.setMinimum(0.0)
    self.a290mm_cam_normalize_l.setMaximum(100.0)
    self.a290mm_cam_normalize_l.setSingleStep(0.01)

    self.a290mm_cam_normalize_h = QDoubleSpinBox()
    self.a290mm_cam_normalize_h.setMinimum(0.0)
    self.a290mm_cam_normalize_h.setMaximum(100.0)
    self.a290mm_cam_normalize_h.setSingleStep(0.01)
    self.a290mm_cam_normalize_h.setValue(100.0)

    self.a290mm_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a290mm_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a290mm_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a290mm = QCheckBox()
    self.loghist_a290mm.setChecked(True)

    self.graphWidget_a290mm = pg.PlotWidget()
    self.hist_color_a290mm = self.palette().color(QtGui.QPalette.Window)
    self.graphWidget_a290mm.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_gray)
    self.graphWidget_a290mm.setBackground(self.hist_color_a290mm)


    cam_a290mm_title_layout = QHBoxLayout()
    cam_a290mm_title_layout.addStretch()
    cam_a290mm_title_layout.addWidget(self.lab_a290mm_cam)
    cam_a290mm_title_layout.addStretch()
    cam_a290mm_title_layout.addWidget(self.a290mm_cam_on)
    cam_a290mm_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a290mm_title_layout)

    layout.addWidget(self.lab_a290mm_cam_time_param)
    layout.addWidget(self.lab_a290mm_cam_time_disp_frame)
    layout.addWidget(self.lab_a290mm_cam_temp)
    layout.addWidget(self.lab_a290mm_rotate)
    layout.addWidget(separator1)
    cam_a290mm_exp_quickcheck_layout = QHBoxLayout()
    cam_a290mm_exp_quickcheck_layout.addWidget(self.a290mm_cam_exp_gain_depl)
    cam_a290mm_exp_quickcheck_layout.addStretch()
    cam_a290mm_exp_quickcheck_layout.addWidget(self.a290mm_cam_quick_check_align_photo)
    layout.addLayout(cam_a290mm_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a290mm_gain_layout = QHBoxLayout()
    cam_a290mm_gain_layout.addWidget(QLabel("Exp:"))
    cam_a290mm_gain_layout.addWidget(self.a290mm_cam_exp_slider)
    cam_a290mm_gain_layout.addWidget(QLabel("ms"))
    cam_a290mm_gain_layout.addWidget(QLabel("Gain:"))
    cam_a290mm_gain_layout.addWidget(self.a290mm_cam_gain_slider)
    cam_a290mm_gain_layout.addWidget(QLabel("Offset:"))
    cam_a290mm_gain_layout.addWidget(self.a290mm_cam_offset_slider)
    cam_a290mm_gain_layout.addWidget(QLabel("bin:"))
    cam_a290mm_gain_layout.addWidget(self.a290mm_cam_bin)
    layout.addLayout(cam_a290mm_gain_layout)

    cam_a290mm_butt_group2 = QHBoxLayout()
    cam_a290mm_butt_group2.addWidget(self.a290mm_cam_photo_settings_button)
    cam_a290mm_butt_group2.addWidget(self.a290mm_cam_preview_settings_button)
    cam_a290mm_butt_group2.addWidget(self.a290mm_photo_reload)
    cam_a290mm_butt_group2.addWidget(self.a290mm_photo_rotate)
    cam_a290mm_butt_group2.addStretch()
    layout.addLayout(cam_a290mm_butt_group2)

    cam_a290mm_butt_group3 = QHBoxLayout()
    cam_a290mm_butt_group3.addWidget(QLabel("Cir X"))
    cam_a290mm_butt_group3.addWidget(self.a290mm_cam_circ_x)
    cam_a290mm_butt_group3.addWidget(QLabel("Y"))
    cam_a290mm_butt_group3.addWidget(self.a290mm_cam_circ_y)
    cam_a290mm_butt_group3.addWidget(QLabel("D"))
    cam_a290mm_butt_group3.addWidget(self.a290mm_cam_circ_d)
    cam_a290mm_butt_group3.addWidget(QLabel("C"))
    cam_a290mm_butt_group3.addWidget(self.a290mm_cam_circ_c)
    layout.addLayout(cam_a290mm_butt_group3)

    cam_a290mm_butt_group4 = QHBoxLayout()
    cam_a290mm_butt_group4.addWidget(QLabel("Save"))
    cam_a290mm_butt_group4.addWidget(self.a290mm_cam_save_img)
    cam_a290mm_butt_group4.addWidget(QLabel("Dir"))
    cam_a290mm_butt_group4.addWidget(self.a290mm_cam_save_dirname)
    cam_a290mm_butt_group4.addWidget(QLabel("Delay"))
    cam_a290mm_butt_group4.addWidget(self.a290mm_cam_save_delay)
    layout.addLayout(cam_a290mm_butt_group4)

    cam_a290mm_butt_group5 = QHBoxLayout()
    cam_a290mm_butt_group5.addWidget(QLabel("Downsample"))
    cam_a290mm_butt_group5.addWidget(self.a290mm_downsample)
    cam_a290mm_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a290mm_butt_group5.addWidget(self.a290mm_cam_solve_radius)
    cam_a290mm_butt_group5.addWidget(self.a290mm_b_plate_solve_eq5)
    cam_a290mm_butt_group5.addWidget(self.a290mm_b_plate_solve_eq6)
    cam_a290mm_butt_group5.addWidget(self.a290mm_b_plate_solve_cancel)
    layout.addLayout(cam_a290mm_butt_group5)
    layout.addWidget(self.lab_a290mm_plate_solve_status)
    layout.addWidget(separator3)

    cam_a290mm_pixel_scale = QHBoxLayout()
    cam_a290mm_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a290mm_pixel_scale.addWidget(self.a290mm_cam_scale_pixel_size)
    cam_a290mm_pixel_scale.addWidget(QLabel("F:"))
    cam_a290mm_pixel_scale.addWidget(self.a290mm_cam_scale_focal)
    cam_a290mm_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a290mm_pixel_scale.addWidget(self.a290mm_cam_scale_pixel_scale)
    layout.addLayout(cam_a290mm_pixel_scale)

    cam_a290mm_pic_adj = QHBoxLayout()
    cam_a290mm_pic_adj.addWidget(QLabel("BRI:"))
    cam_a290mm_pic_adj.addWidget(self.a290mm_cam_bri)
    cam_a290mm_pic_adj.addWidget(QLabel("SAT:"))
    cam_a290mm_pic_adj.addWidget(self.a290mm_cam_sat)
    cam_a290mm_pic_adj.addWidget(QLabel("GAM:"))
    cam_a290mm_pic_adj.addWidget(self.a290mm_cam_gam)
    layout.addLayout(cam_a290mm_pic_adj)

    cam_a290mm_pic_adj2 = QHBoxLayout()
    cam_a290mm_pic_adj2.addWidget(QLabel("INV:"))
    cam_a290mm_pic_adj2.addWidget(self.a290mm_cam_inverse)
    cam_a290mm_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a290mm_pic_adj2.addWidget(self.a290mm_cam_hist_equal)
    cam_a290mm_pic_adj2.addStretch()
    cam_a290mm_pic_adj2.addWidget(self.a290mm_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a290mm_pic_adj2)

    cam_a290mm_pic_adj3 = QHBoxLayout()
    cam_a290mm_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a290mm_pic_adj3.addWidget(self.a290mm_cam_normalize)
    cam_a290mm_pic_adj3.addWidget(QLabel("L:"))
    cam_a290mm_pic_adj3.addWidget(self.a290mm_cam_normalize_l)
    cam_a290mm_pic_adj3.addWidget(QLabel("H:"))
    cam_a290mm_pic_adj3.addWidget(self.a290mm_cam_normalize_h)
    cam_a290mm_pic_adj3.addStretch()
    cam_a290mm_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a290mm_pic_adj3.addWidget(self.a290mm_cam_hist_draw)
    cam_a290mm_pic_adj3.addWidget(QLabel("Log:"))
    cam_a290mm_pic_adj3.addWidget(self.loghist_a290mm)
    layout.addLayout(cam_a290mm_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a290mm_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a290mm)

    self.lewy_tab9.setLayout(layout)

#############################################################################################

  def tab10_lewyUI(self):
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
    camname = 'a174mm'

    self.a174mm_cam_on = QCheckBox()
    self.a174mm_cam_on.setChecked(False)

    self.lab_a174mm_cam = QLabel("ASI174MM mini CAM")
    self.lab_a174mm_cam.setFont(self.headline)
    self.lab_a174mm_cam.setAlignment(Qt.AlignCenter)

    self.lab_a174mm_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a174mm_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a174mm_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a174mm_rotate = QLabel("Rotate: null")

    self.a174mm_cam_exp_slider = QDoubleSpinBox()
    self.a174mm_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a174mm_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a174mm_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a174mm_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a174mm_cam_gain_slider = QSpinBox()

    self.a174mm_cam_offset_slider = QSpinBox()

    self.a174mm_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a174mm_cam_photo_settings_button.clicked.connect(self.f_a174mm_cam_button_photo_settings)

    self.a174mm_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a174mm_cam_preview_settings_button.clicked.connect(self.f_a174mm_cam_button_preview_settings)

    self.a174mm_photo_reload = QPushButton('Reload', self)
    self.a174mm_photo_reload.clicked.connect(self.f_a174mm_window_refresh)

    self.a174mm_photo_rotate = QPushButton('Rotate', self)
    self.a174mm_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a174mm_cam_bin = QComboBox()
    self.a174mm_cam_bin.addItems(['NULL'])

    self.a174mm_cam_circ_x = QSpinBox()
    self.a174mm_cam_circ_x.setMinimum(0)
    self.a174mm_cam_circ_x.setMaximum(1936)
    if 'a174mm_cam_circ_x' in app_settings.keys():
      self.a174mm_cam_circ_x.setValue(app_settings['a174mm_cam_circ_x'])
    else:
      self.a174mm_cam_circ_x.setValue(968)

    self.a174mm_cam_circ_y = QSpinBox()
    self.a174mm_cam_circ_y.setMinimum(0)
    self.a174mm_cam_circ_y.setMaximum(1216)
    if 'a174mm_cam_circ_y' in app_settings.keys():
      self.a174mm_cam_circ_y.setValue(app_settings['a174mm_cam_circ_y'])
    else:
      self.a174mm_cam_circ_y.setValue(608)

    self.a174mm_cam_circ_d = QSpinBox()
    self.a174mm_cam_circ_d.setMinimum(0)
    self.a174mm_cam_circ_d.setMaximum(1200)
    if 'a174mm_cam_circ_d' in app_settings.keys():
      self.a174mm_cam_circ_d.setValue(app_settings['a174mm_cam_circ_d'])
    else:
      self.a174mm_cam_circ_d.setValue(0)

    self.a174mm_cam_circ_c = QSpinBox()
    self.a174mm_cam_circ_c.setMinimum(0)
    self.a174mm_cam_circ_c.setMaximum(900)
    self.a174mm_cam_circ_c.setValue(0)

    self.a174mm_cam_save_img = QCheckBox()
    self.a174mm_cam_save_img.setChecked(False)

    self.a174mm_cam_save_dirname = QLineEdit(self)
    self.a174mm_cam_save_dirname.setMaxLength(50)
    regex1 = QRegExp('^[a-z0-9_\-]+$')
    validator1 = QRegExpValidator(regex1)
    self.a174mm_cam_save_dirname.setValidator(validator1)
    self.a174mm_cam_save_dirname.setText('teleskop')

    self.a174mm_cam_save_delay = QDoubleSpinBox()
    self.a174mm_cam_save_delay.setMinimum(0.0)
    self.a174mm_cam_save_delay.setMaximum(1000.0)
    self.a174mm_cam_save_delay.setValue(0.0)
    self.a174mm_cam_save_delay.setSingleStep(1.0)

    self.a174mm_downsample = QSpinBox()
    self.a174mm_downsample.setMinimum(1)
    self.a174mm_downsample.setMaximum(64)
    self.a174mm_downsample.setValue(2)

    self.a174mm_cam_solve_radius = QCheckBox()
    self.a174mm_cam_solve_radius.setChecked(False)

    self.a174mm_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a174mm_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.a174mm_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a174mm_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a174mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a174mm_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))
    self.lab_a174mm_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a174mm_cam_scale_pixel_size = QDoubleSpinBox()
    self.a174mm_cam_scale_pixel_size.setMinimum(0.1)
    self.a174mm_cam_scale_pixel_size.setMaximum(99.0)
    self.a174mm_cam_scale_pixel_size.setValue(5.86)
    self.a174mm_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a174mm_cam_scale_focal = QSpinBox()
    self.a174mm_cam_scale_focal.setMinimum(1)
    self.a174mm_cam_scale_focal.setMaximum(9999)
    if 'a174mm_cam_scale_focal' in app_settings.keys():
      self.a174mm_cam_scale_focal.setValue(app_settings['a174mm_cam_scale_focal'])
    else:
      self.a174mm_cam_scale_focal.setValue(505)
    self.a174mm_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a174mm_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a174mm_cam_scale_pixel_scale.setMinimum(0.0)
    self.a174mm_cam_scale_pixel_scale.setMaximum(999.0)
    self.a174mm_cam_scale_pixel_scale.setValue(1.53)
    self.a174mm_cam_scale_pixel_scale.setDecimals(5)

    self.a174mm_cam_bri = QSpinBox()
    self.a174mm_cam_bri.setValue(0)
    self.a174mm_cam_bri.setMinimum(-255)
    self.a174mm_cam_bri.setMaximum(255)

    self.a174mm_cam_sat = QDoubleSpinBox()
    self.a174mm_cam_sat.setValue(1.0)
    self.a174mm_cam_sat.setMinimum(0.0)
    self.a174mm_cam_sat.setMaximum(10.0)
    self.a174mm_cam_sat.setSingleStep(0.01)

    self.a174mm_cam_gam = QDoubleSpinBox()
    self.a174mm_cam_gam.setValue(1.0)
    self.a174mm_cam_gam.setMinimum(0.0)
    self.a174mm_cam_gam.setMaximum(10.0)
    self.a174mm_cam_gam.setSingleStep(0.01)

    self.a174mm_cam_inverse = QCheckBox()
    self.a174mm_cam_inverse.setChecked(False)

    self.a174mm_cam_hist_draw = QCheckBox()
    self.a174mm_cam_hist_draw.setChecked(False)

    self.a174mm_cam_hist_equal = QCheckBox()
    self.a174mm_cam_hist_equal.setChecked(False)

    self.a174mm_cam_normalize = QCheckBox()
    self.a174mm_cam_normalize.setChecked(False)

    self.a174mm_cam_normalize_l = QDoubleSpinBox()
    self.a174mm_cam_normalize_l.setValue(0.0)
    self.a174mm_cam_normalize_l.setMinimum(0.0)
    self.a174mm_cam_normalize_l.setMaximum(100.0)
    self.a174mm_cam_normalize_l.setSingleStep(0.01)

    self.a174mm_cam_normalize_h = QDoubleSpinBox()
    self.a174mm_cam_normalize_h.setMinimum(0.0)
    self.a174mm_cam_normalize_h.setMaximum(100.0)
    self.a174mm_cam_normalize_h.setSingleStep(0.01)
    self.a174mm_cam_normalize_h.setValue(100.0)

    self.a174mm_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.a174mm_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a174mm_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a174mm = QCheckBox()
    self.loghist_a174mm.setChecked(True)

    self.graphWidget_a174mm = pg.PlotWidget()
    self.hist_color_a174mm = self.palette().color(QtGui.QPalette.Window)
    self.graphWidget_a174mm.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_gray)
    self.graphWidget_a174mm.setBackground(self.hist_color_a174mm)


    cam_a174mm_title_layout = QHBoxLayout()
    cam_a174mm_title_layout.addStretch()
    cam_a174mm_title_layout.addWidget(self.lab_a174mm_cam)
    cam_a174mm_title_layout.addStretch()
    cam_a174mm_title_layout.addWidget(self.a174mm_cam_on)
    cam_a174mm_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a174mm_title_layout)

    layout.addWidget(self.lab_a174mm_cam_time_param)
    layout.addWidget(self.lab_a174mm_cam_time_disp_frame)
    layout.addWidget(self.lab_a174mm_cam_temp)
    layout.addWidget(self.lab_a174mm_rotate)
    layout.addWidget(separator1)
    cam_a174mm_exp_quickcheck_layout = QHBoxLayout()
    cam_a174mm_exp_quickcheck_layout.addWidget(self.a174mm_cam_exp_gain_depl)
    cam_a174mm_exp_quickcheck_layout.addStretch()
    cam_a174mm_exp_quickcheck_layout.addWidget(self.a174mm_cam_quick_check_align_photo)
    layout.addLayout(cam_a174mm_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a174mm_gain_layout = QHBoxLayout()
    cam_a174mm_gain_layout.addWidget(QLabel("Exp:"))
    cam_a174mm_gain_layout.addWidget(self.a174mm_cam_exp_slider)
    cam_a174mm_gain_layout.addWidget(QLabel("ms"))
    cam_a174mm_gain_layout.addWidget(QLabel("Gain:"))
    cam_a174mm_gain_layout.addWidget(self.a174mm_cam_gain_slider)
    cam_a174mm_gain_layout.addWidget(QLabel("Offset:"))
    cam_a174mm_gain_layout.addWidget(self.a174mm_cam_offset_slider)
    cam_a174mm_gain_layout.addWidget(QLabel("bin:"))
    cam_a174mm_gain_layout.addWidget(self.a174mm_cam_bin)
    layout.addLayout(cam_a174mm_gain_layout)

    cam_a174mm_butt_group2 = QHBoxLayout()
    cam_a174mm_butt_group2.addWidget(self.a174mm_cam_photo_settings_button)
    cam_a174mm_butt_group2.addWidget(self.a174mm_cam_preview_settings_button)
    cam_a174mm_butt_group2.addWidget(self.a174mm_photo_reload)
    cam_a174mm_butt_group2.addWidget(self.a174mm_photo_rotate)
    cam_a174mm_butt_group2.addStretch()
    layout.addLayout(cam_a174mm_butt_group2)

    cam_a174mm_butt_group3 = QHBoxLayout()
    cam_a174mm_butt_group3.addWidget(QLabel("Cir X"))
    cam_a174mm_butt_group3.addWidget(self.a174mm_cam_circ_x)
    cam_a174mm_butt_group3.addWidget(QLabel("Y"))
    cam_a174mm_butt_group3.addWidget(self.a174mm_cam_circ_y)
    cam_a174mm_butt_group3.addWidget(QLabel("D"))
    cam_a174mm_butt_group3.addWidget(self.a174mm_cam_circ_d)
    cam_a174mm_butt_group3.addWidget(QLabel("C"))
    cam_a174mm_butt_group3.addWidget(self.a174mm_cam_circ_c)
    layout.addLayout(cam_a174mm_butt_group3)

    cam_a174mm_butt_group4 = QHBoxLayout()
    cam_a174mm_butt_group4.addWidget(QLabel("Save"))
    cam_a174mm_butt_group4.addWidget(self.a174mm_cam_save_img)
    cam_a174mm_butt_group4.addWidget(QLabel("Dir"))
    cam_a174mm_butt_group4.addWidget(self.a174mm_cam_save_dirname)
    cam_a174mm_butt_group4.addWidget(QLabel("Delay"))
    cam_a174mm_butt_group4.addWidget(self.a174mm_cam_save_delay)
    layout.addLayout(cam_a174mm_butt_group4)

    cam_a174mm_butt_group5 = QHBoxLayout()
    cam_a174mm_butt_group5.addWidget(QLabel("Downsample"))
    cam_a174mm_butt_group5.addWidget(self.a174mm_downsample)
    cam_a174mm_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a174mm_butt_group5.addWidget(self.a174mm_cam_solve_radius)
    cam_a174mm_butt_group5.addWidget(self.a174mm_b_plate_solve_eq5)
    cam_a174mm_butt_group5.addWidget(self.a174mm_b_plate_solve_eq6)
    cam_a174mm_butt_group5.addWidget(self.a174mm_b_plate_solve_cancel)
    layout.addLayout(cam_a174mm_butt_group5)
    layout.addWidget(self.lab_a174mm_plate_solve_status)
    layout.addWidget(separator3)

    cam_a174mm_pixel_scale = QHBoxLayout()
    cam_a174mm_pixel_scale.addWidget(QLabel("Px size:"))
    cam_a174mm_pixel_scale.addWidget(self.a174mm_cam_scale_pixel_size)
    cam_a174mm_pixel_scale.addWidget(QLabel("F:"))
    cam_a174mm_pixel_scale.addWidget(self.a174mm_cam_scale_focal)
    cam_a174mm_pixel_scale.addWidget(QLabel("Px scale:"))
    cam_a174mm_pixel_scale.addWidget(self.a174mm_cam_scale_pixel_scale)
    layout.addLayout(cam_a174mm_pixel_scale)

    cam_a174mm_pic_adj = QHBoxLayout()
    cam_a174mm_pic_adj.addWidget(QLabel("BRI:"))
    cam_a174mm_pic_adj.addWidget(self.a174mm_cam_bri)
    cam_a174mm_pic_adj.addWidget(QLabel("SAT:"))
    cam_a174mm_pic_adj.addWidget(self.a174mm_cam_sat)
    cam_a174mm_pic_adj.addWidget(QLabel("GAM:"))
    cam_a174mm_pic_adj.addWidget(self.a174mm_cam_gam)
    layout.addLayout(cam_a174mm_pic_adj)

    cam_a174mm_pic_adj2 = QHBoxLayout()
    cam_a174mm_pic_adj2.addWidget(QLabel("INV:"))
    cam_a174mm_pic_adj2.addWidget(self.a174mm_cam_inverse)
    cam_a174mm_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_a174mm_pic_adj2.addWidget(self.a174mm_cam_hist_equal)
    cam_a174mm_pic_adj2.addStretch()
    cam_a174mm_pic_adj2.addWidget(self.a174mm_cam_bri_sat_gam_rst)
    layout.addLayout(cam_a174mm_pic_adj2)

    cam_a174mm_pic_adj3 = QHBoxLayout()
    cam_a174mm_pic_adj3.addWidget(QLabel("NORM:"))
    cam_a174mm_pic_adj3.addWidget(self.a174mm_cam_normalize)
    cam_a174mm_pic_adj3.addWidget(QLabel("L:"))
    cam_a174mm_pic_adj3.addWidget(self.a174mm_cam_normalize_l)
    cam_a174mm_pic_adj3.addWidget(QLabel("H:"))
    cam_a174mm_pic_adj3.addWidget(self.a174mm_cam_normalize_h)
    cam_a174mm_pic_adj3.addStretch()
    cam_a174mm_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a174mm_pic_adj3.addWidget(self.a174mm_cam_hist_draw)
    cam_a174mm_pic_adj3.addWidget(QLabel("Log:"))
    cam_a174mm_pic_adj3.addWidget(self.loghist_a174mm)
    layout.addLayout(cam_a174mm_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a174mm_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a174mm)

    self.lewy_tab10.setLayout(layout)

#############################################################################################

  def tab11_lewyUI(self):
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
    camname = 'a120mc'

    self.a120mc_cam_on = QCheckBox()
    self.a120mc_cam_on.setChecked(False)

    self.lab_a120mc_cam = QLabel("ASI120MC CAM")
    self.lab_a120mc_cam.setFont(self.headline)
    self.lab_a120mc_cam.setAlignment(Qt.AlignCenter)

    self.lab_a120mc_cam_time_param = QLabel("Last param set: -1s ago")
    self.lab_a120mc_cam_time_disp_frame = QLabel("Displayed frame made: -1s ago")
    self.lab_a120mc_cam_temp = QLabel("Sensor temp: 999 Celsius")
    self.lab_a120mc_rotate = QLabel("Rotate: null")

    self.a120mc_cam_exp_slider = QDoubleSpinBox()
    self.a120mc_cam_exp_gain_depl = QLabel("Exposure set: X us")

    self.a120mc_cam_quick_check_align_photo = QPushButton('Quick check align', self)
    self.a120mc_cam_quick_check_align_photo.pressed.connect(self.f_quick_check_align_photo_pressed)
    self.a120mc_cam_quick_check_align_photo.released.connect(self.f_quick_check_align_photo_released)

    self.a120mc_cam_gain_slider = QSpinBox()

    self.a120mc_cam_offset_slider = QSpinBox()

    self.a120mc_cam_photo_settings_button = QPushButton('PHOTO', self)
    self.a120mc_cam_photo_settings_button.clicked.connect(self.f_a120mc_cam_button_photo_settings)

    self.a120mc_cam_preview_settings_button = QPushButton('PREVIEW', self)
    self.a120mc_cam_preview_settings_button.clicked.connect(self.f_a120mc_cam_button_preview_settings)

    self.a120mc_photo_reload = QPushButton('Reload', self)
    self.a120mc_photo_reload.clicked.connect(self.f_a120mc_window_refresh)

    self.a120mc_photo_rotate = QPushButton('Rotate', self)
    self.a120mc_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname=camname))

    self.a120mc_cam_bin = QComboBox()
    self.a120mc_cam_bin.addItems(['NULL'])

    self.a120mc_cam_circ_x = QSpinBox()
    self.a120mc_cam_circ_x.setMinimum(0)
    self.a120mc_cam_circ_x.setMaximum(1280)
    if 'a120mc_cam_circ_x' in app_settings.keys():
      self.a120mc_cam_circ_x.setValue(app_settings['a120mc_cam_circ_x'])
    else:
      self.a120mc_cam_circ_x.setValue(640)

    self.a120mc_cam_circ_y = QSpinBox()
    self.a120mc_cam_circ_y.setMinimum(0)
    self.a120mc_cam_circ_y.setMaximum(960)
    if 'a120mc_cam_circ_y' in app_settings.keys():
      self.a120mc_cam_circ_y.setValue(app_settings['a120mc_cam_circ_y'])
    else:
      self.a120mc_cam_circ_y.setValue(480)

    self.a120mc_cam_circ_d = QSpinBox()
    self.a120mc_cam_circ_d.setMinimum(0)
    self.a120mc_cam_circ_d.setMaximum(1200)
    if 'a120mc_cam_circ_d' in app_settings.keys():
      self.a120mc_cam_circ_d.setValue(app_settings['a120mc_cam_circ_d'])
    else:
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

    self.a120mc_cam_save_delay = QDoubleSpinBox()
    self.a120mc_cam_save_delay.setMinimum(0.0)
    self.a120mc_cam_save_delay.setMaximum(1000.0)
    self.a120mc_cam_save_delay.setValue(0.0)
    self.a120mc_cam_save_delay.setSingleStep(1.0)

    self.a120mc_downsample = QSpinBox()
    self.a120mc_downsample.setMinimum(1)
    self.a120mc_downsample.setMaximum(64)
    self.a120mc_downsample.setValue(2)

    self.a120mc_cam_solve_radius = QCheckBox()
    self.a120mc_cam_solve_radius.setChecked(False)

    self.a120mc_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.a120mc_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.a120mc_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.a120mc_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.a120mc_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a120mc_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))
    self.lab_a120mc_plate_solve_status = QLabel("Plate solve status: NULL")

    self.a120mc_cam_scale_pixel_size = QDoubleSpinBox()
    self.a120mc_cam_scale_pixel_size.setMinimum(0.1)
    self.a120mc_cam_scale_pixel_size.setMaximum(99.0)
    self.a120mc_cam_scale_pixel_size.setValue(3.75)
    self.a120mc_cam_scale_pixel_size.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a120mc_cam_scale_focal = QSpinBox()
    self.a120mc_cam_scale_focal.setMinimum(1)
    self.a120mc_cam_scale_focal.setMaximum(9999)
    if 'a120mc_cam_scale_focal' in app_settings.keys():
      self.a120mc_cam_scale_focal.setValue(app_settings['a120mc_cam_scale_focal'])
    else:
      self.a120mc_cam_scale_focal.setValue(216)
    self.a120mc_cam_scale_focal.valueChanged.connect(lambda: self.f_cam_pix_scale_calc_universal(camname=camname))

    self.a120mc_cam_scale_pixel_scale = QDoubleSpinBox()
    self.a120mc_cam_scale_pixel_scale.setMinimum(0.0)
    self.a120mc_cam_scale_pixel_scale.setMaximum(999.0)
    self.a120mc_cam_scale_pixel_scale.setValue(3.58)
    self.a120mc_cam_scale_pixel_scale.setDecimals(5)

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

    self.a120mc_cam_hist_draw = QCheckBox()
    self.a120mc_cam_hist_draw.setChecked(False)

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
    self.a120mc_cam_bri_sat_gam_rst.clicked.connect(lambda: self.f_cam_bri_sat_gam_rst_universal(camname=camname))

    self.lab_a120mc_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_a120mc = QCheckBox()
    self.loghist_a120mc.setChecked(True)

    self.graphWidget_a120mc = pg.PlotWidget()
    self.hist_color_a120mc = self.palette().color(QtGui.QPalette.Window)
    self.graphWidget_a120mc.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_gray)
    self.graphWidget_a120mc.setBackground(self.hist_color_a120mc)


    cam_a120mc_title_layout = QHBoxLayout()
    cam_a120mc_title_layout.addStretch()
    cam_a120mc_title_layout.addWidget(self.lab_a120mc_cam)
    cam_a120mc_title_layout.addStretch()
    cam_a120mc_title_layout.addWidget(self.a120mc_cam_on)
    cam_a120mc_title_layout.addWidget(QLabel("ON"))
    layout.addLayout(cam_a120mc_title_layout)

    layout.addWidget(self.lab_a120mc_cam_time_param)
    layout.addWidget(self.lab_a120mc_cam_time_disp_frame)
    layout.addWidget(self.lab_a120mc_cam_temp)
    layout.addWidget(self.lab_a120mc_rotate)
    layout.addWidget(separator1)
    cam_a120mc_exp_quickcheck_layout = QHBoxLayout()
    cam_a120mc_exp_quickcheck_layout.addWidget(self.a120mc_cam_exp_gain_depl)
    cam_a120mc_exp_quickcheck_layout.addStretch()
    cam_a120mc_exp_quickcheck_layout.addWidget(self.a120mc_cam_quick_check_align_photo)
    layout.addLayout(cam_a120mc_exp_quickcheck_layout)
    layout.addWidget(separator2)

    cam_a120mc_gain_layout = QHBoxLayout()
    cam_a120mc_gain_layout.addWidget(QLabel("Exp:"))
    cam_a120mc_gain_layout.addWidget(self.a120mc_cam_exp_slider)
    cam_a120mc_gain_layout.addWidget(QLabel("ms"))
    cam_a120mc_gain_layout.addWidget(QLabel("Gain:"))
    cam_a120mc_gain_layout.addWidget(self.a120mc_cam_gain_slider)
    cam_a120mc_gain_layout.addWidget(QLabel("Offset:"))
    cam_a120mc_gain_layout.addWidget(self.a120mc_cam_offset_slider)
    cam_a120mc_gain_layout.addWidget(QLabel("bin:"))
    cam_a120mc_gain_layout.addWidget(self.a120mc_cam_bin)
    layout.addLayout(cam_a120mc_gain_layout)

    cam_a120mc_butt_group2 = QHBoxLayout()
    cam_a120mc_butt_group2.addWidget(self.a120mc_cam_photo_settings_button)
    cam_a120mc_butt_group2.addWidget(self.a120mc_cam_preview_settings_button)
    cam_a120mc_butt_group2.addWidget(self.a120mc_photo_reload)
    cam_a120mc_butt_group2.addWidget(self.a120mc_photo_rotate)
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
    cam_a120mc_butt_group4.addWidget(QLabel("Save"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_save_img)
    cam_a120mc_butt_group4.addWidget(QLabel("Dir"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_save_dirname)
    cam_a120mc_butt_group4.addWidget(QLabel("Delay"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_save_delay)
    layout.addLayout(cam_a120mc_butt_group4)

    cam_a120mc_butt_group5 = QHBoxLayout()
    cam_a120mc_butt_group5.addWidget(QLabel("Downsample"))
    cam_a120mc_butt_group5.addWidget(self.a120mc_downsample)
    cam_a120mc_butt_group5.addWidget(QLabel("Limit radius"))
    cam_a120mc_butt_group5.addWidget(self.a120mc_cam_solve_radius)
    cam_a120mc_butt_group5.addWidget(self.a120mc_b_plate_solve_eq5)
    cam_a120mc_butt_group5.addWidget(self.a120mc_b_plate_solve_eq6)
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
    cam_a120mc_pic_adj3.addWidget(QLabel("Hist:"))
    cam_a120mc_pic_adj3.addWidget(self.a120mc_cam_hist_draw)
    cam_a120mc_pic_adj3.addWidget(QLabel("Log:"))
    cam_a120mc_pic_adj3.addWidget(self.loghist_a120mc)
    layout.addLayout(cam_a120mc_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_a120mc_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_a120mc)

    self.lewy_tab11.setLayout(layout)

#############################################################################################

  def tab12_lewyUI(self):
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

    self.canon_photo_reload = QPushButton('Reload', self)
    self.canon_photo_reload.clicked.connect(self.f_canon_window_refresh)

    self.canon_photo_rotate = QPushButton('Rotate', self)
    self.canon_photo_rotate.clicked.connect(lambda: self.f_cam_rotate_universal(camname='canon'))

    self.canon_cam_bin = QComboBox()
    self.canon_cam_bin.addItems(['1'])

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


    self.canon_downsample = QSpinBox()
    self.canon_downsample.setMinimum(1)
    self.canon_downsample.setMaximum(64)
    self.canon_downsample.setValue(2)

    self.canon_b_plate_solve_eq5 = QPushButton('Solve EQ5', self)
    self.canon_b_plate_solve_eq5.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq5'))
    self.canon_b_plate_solve_eq6 = QPushButton('Solve EQ6', self)
    self.canon_b_plate_solve_eq6.clicked.connect(lambda: self.f_cam_plate_solve_universal(camname=camname, mount='eq6'))

    self.canon_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.canon_b_plate_solve_cancel.clicked.connect(lambda: self.f_cam_platesolve_stop_universal(camname=camname))
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
    self.canon_scale_pixel_scale.setDecimals(5)

    self.canon_cam_bri = QSpinBox()
    self.canon_cam_bri.setValue(0)
    self.canon_cam_bri.setMinimum(-255)
    self.canon_cam_bri.setMaximum(255)

    self.canon_cam_sat = QDoubleSpinBox()
    self.canon_cam_sat.setValue(1.0)
    self.canon_cam_sat.setMinimum(0.0)
    self.canon_cam_sat.setMaximum(10.0)
    self.canon_cam_sat.setSingleStep(0.01)

    self.canon_cam_gam = QDoubleSpinBox()
    self.canon_cam_gam.setValue(1.0)
    self.canon_cam_gam.setMinimum(0.0)
    self.canon_cam_gam.setMaximum(10.0)
    self.canon_cam_gam.setSingleStep(0.01)

    self.canon_cam_inverse = QCheckBox()
    self.canon_cam_inverse.setChecked(False)

    self.canon_cam_hist_draw = QCheckBox()
    self.canon_cam_hist_draw.setChecked(False)

    self.canon_cam_hist_equal = QCheckBox()
    self.canon_cam_hist_equal.setChecked(False)

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

    self.canon_cam_bri_sat_gam_rst = QPushButton('RST', self)
    self.canon_cam_bri_sat_gam_rst.clicked.connect(self.f_canon_cam_bri_sat_gam_rst)

    self.lab_canon_cam_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_canon = QCheckBox()
    self.loghist_canon.setChecked(True)

    self.graphWidget_canon = pg.PlotWidget()
    self.hist_color_canon = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_canon = pg.mkPen(color=(0,0,0))
    self.graphWidget_canon.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_canon)
    self.graphWidget_canon.setBackground(self.hist_color_canon)





    layout.addWidget(self.lab_canon)
    layout.addWidget(self.lab_canon_time_frame)
    layout.addWidget(self.lab_canon_time_disp_frame)
    layout.addWidget(self.lab_canon_rotate)
    layout.addWidget(separator1)

    cam_canon_exp_layout = QHBoxLayout()
    cam_canon_exp_layout.addWidget(QLabel("Exp:"))
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
    cam_canon_butt_group2.addWidget(QLabel("bin:"))
    cam_canon_butt_group2.addWidget(self.canon_cam_bin)
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
    cam_canon_butt_group5.addWidget(QLabel("Downsample"))
    cam_canon_butt_group5.addWidget(self.canon_downsample)
    cam_canon_butt_group5.addWidget(self.canon_b_plate_solve_eq5)
    cam_canon_butt_group5.addWidget(self.canon_b_plate_solve_eq6)
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
    cam_canon_pic_adj.addWidget(self.canon_cam_bri)
    cam_canon_pic_adj.addWidget(QLabel("SAT:"))
    cam_canon_pic_adj.addWidget(self.canon_cam_sat)
    cam_canon_pic_adj.addWidget(QLabel("GAM:"))
    cam_canon_pic_adj.addWidget(self.canon_cam_gam)
    layout.addLayout(cam_canon_pic_adj)

    cam_canon_pic_adj2 = QHBoxLayout()
    cam_canon_pic_adj2.addWidget(QLabel("INV:"))
    cam_canon_pic_adj2.addWidget(self.canon_cam_inverse)
    cam_canon_pic_adj2.addWidget(QLabel("HIST EQ:"))
    cam_canon_pic_adj2.addWidget(self.canon_cam_hist_equal)
    cam_canon_pic_adj2.addStretch()
    cam_canon_pic_adj2.addWidget(self.canon_cam_bri_sat_gam_rst)
    layout.addLayout(cam_canon_pic_adj2)

    cam_canon_pic_adj3 = QHBoxLayout()
    cam_canon_pic_adj3.addWidget(QLabel("NORM:"))
    cam_canon_pic_adj3.addWidget(self.canon_cam_normalize)
    cam_canon_pic_adj3.addWidget(QLabel("L:"))
    cam_canon_pic_adj3.addWidget(self.canon_cam_normalize_l)
    cam_canon_pic_adj3.addWidget(QLabel("H:"))
    cam_canon_pic_adj3.addWidget(self.canon_cam_normalize_h)
    cam_canon_pic_adj3.addStretch()
    cam_canon_pic_adj3.addWidget(QLabel("Hist:"))
    cam_canon_pic_adj3.addWidget(self.canon_cam_hist_draw)
    cam_canon_pic_adj3.addWidget(QLabel("Log:"))
    cam_canon_pic_adj3.addWidget(self.loghist_canon)
    layout.addLayout(cam_canon_pic_adj3)

    layout.addWidget(separator4)
    layout.addWidget(self.lab_canon_cam_photo_pixel_stat)
    layout.addWidget(self.graphWidget_canon)

    self.lewy_tab12.setLayout(layout)

#############################################################################################

  def tab13_lewyUI(self):
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
    separator7 = QFrame()
    separator7.setFrameShape(QFrame.HLine)
    separator8 = QFrame()
    separator8.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)
    self.lab_wheel = QLabel("FILTER WHEEL")
    self.lab_wheel.setFont(self.headline)
    self.lab_wheel.setAlignment(Qt.AlignCenter)

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



    self.b_restart = QPushButton('RESTART', self)
    self.b_restart.clicked.connect(self.f_restart)

    self.b_reboot_scope = QPushButton('REBOOT', self)
    self.b_reboot_scope.clicked.connect(self.f_reboot_scope)

    self.b_shutdown = QPushButton('SHUTDOWN', self)
    self.b_shutdown.clicked.connect(self.f_shutdown)

    self.solved_tabs_refresh = QPushButton('Reload tabs with solved plate', self)
    self.solved_tabs_refresh.clicked.connect(self.f_solved_tabs_refresh)


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


    self.lab_phd2_mon = QLabel("PHD2 MONITORING")
    self.lab_phd2_mon.setFont(self.headline)
    self.lab_phd2_mon.setAlignment(Qt.AlignCenter)

    self.lab_phd2_mon_en = QCheckBox()
    self.lab_phd2_mon_en.setChecked(False)
    self.lab_phd2_alert_en = QCheckBox()
    self.lab_phd2_alert_en.setChecked(False)
    self.lab_phd2_state = QLabel("NULL")

    self.phd2_alert_occurences = QSpinBox()
    self.phd2_alert_occurences.setMinimum(1)
    self.phd2_alert_occurences.setMaximum(200)
    self.phd2_alert_occurences.setValue(36)



    self.lab_autooff = QLabel("AUTOMATIC TURN OFF")
    self.lab_autooff.setFont(self.headline)
    self.lab_autooff.setAlignment(Qt.AlignCenter)

    self.autooff_hour = QSpinBox()
    self.autooff_hour.setValue(4)
    self.autooff_hour.setMinimum(0)
    self.autooff_hour.setMaximum(23)
    self.autooff_hour.setSingleStep(1)

    self.autooff_minute = QSpinBox()
    self.autooff_minute.setValue(0)
    self.autooff_minute.setMinimum(0)
    self.autooff_minute.setMaximum(59)
    self.autooff_minute.setSingleStep(1)

    self.autooff_enable = QCheckBox()
    self.autooff_enable.setChecked(False)

    self.autooff_state = QLabel("NULL")






    layout.addWidget(self.lab_wheel)
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

    layout.addWidget(separator4)
    layout.addWidget(self.lab_phd2_mon)
    phd2_layout1 = QHBoxLayout()
    phd2_layout1.addWidget(self.lab_phd2_mon_en)
    phd2_layout1.addWidget(QLabel("Enable monitoring"))
    phd2_layout1.addStretch()
    layout.addLayout(phd2_layout1)
    phd2_layout2 = QHBoxLayout()
    phd2_layout2.addWidget(self.lab_phd2_alert_en)
    phd2_layout2.addWidget(QLabel("Enable alerting"))
    phd2_layout2.addStretch()
    phd2_layout2.addWidget(QLabel("Occurences to alert:"))
    phd2_layout2.addWidget(self.phd2_alert_occurences)
    phd2_layout2.addStretch()
    layout.addLayout(phd2_layout2)
    layout.addWidget(self.lab_phd2_state)


    layout.addWidget(self.lab_autooff)
    autooff_layout1 = QHBoxLayout()
    autooff_layout1.addWidget(QLabel("ENABLE: "))
    autooff_layout1.addWidget(self.autooff_enable)
    autooff_layout1.addWidget(QLabel(" turnoff at: "))
    autooff_layout1.addWidget(self.autooff_hour)
    autooff_layout1.addWidget(QLabel("hour"))
    autooff_layout1.addWidget(self.autooff_minute)
    autooff_layout1.addWidget(QLabel("minute"))
    autooff_layout1.addStretch()
    layout.addLayout(autooff_layout1)
    layout.addWidget(self.autooff_state)


    layout.addWidget(separator7)
    layout.addStretch()
    layout.addWidget(separator8)

    bat_buttons_layout = QHBoxLayout()
    bat_buttons_layout.addWidget(self.b_restart)
    bat_buttons_layout.addWidget(self.b_reboot_scope)
    bat_buttons_layout.addWidget(self.b_shutdown)
    layout.addLayout(bat_buttons_layout)
    layout.addWidget(self.solved_tabs_refresh)
    self.lewy_tab13.setLayout(layout)

#############################################################################################

  def tab14_lewyUI(self):
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
    separator7 = QFrame()
    separator7.setFrameShape(QFrame.HLine)
    separator8 = QFrame()
    separator8.setFrameShape(QFrame.HLine)

    self.headline = QFont('SansSerif', 11, QFont.Bold)

    self.file_to_align_title = QLabel('ALIGN TELESCOPE TO FILE')
    self.file_to_align_title.setFont(self.headline)
    self.file_to_align_title.setAlignment(Qt.AlignCenter)

    self.file_to_align_path = QLineEdit(self)
    self.file_to_align_but1 = QPushButton('OPEN FILE', self)
    self.file_to_align_but1.clicked.connect(self.f_open_file)
    self.file_to_align_but2 = QPushButton('(RE)LOAD', self)
    self.file_to_align_but2.clicked.connect(self.f_load_file)

    self.file_to_align_normalize = QCheckBox()
    self.file_to_align_normalize.setChecked(False)

    self.file_to_align_normalize_l = QDoubleSpinBox()
    self.file_to_align_normalize_l.setValue(0.0)
    self.file_to_align_normalize_l.setMinimum(0.0)
    self.file_to_align_normalize_l.setMaximum(100.0)
    self.file_to_align_normalize_l.setSingleStep(0.01)

    self.file_to_align_normalize_h = QDoubleSpinBox()
    self.file_to_align_normalize_h.setMinimum(0.0)
    self.file_to_align_normalize_h.setMaximum(100.0)
    self.file_to_align_normalize_h.setSingleStep(0.01)
    self.file_to_align_normalize_h.setValue(100.0)

    self.file_to_align_debayer = QComboBox()
    self.file_to_align_debayer.addItems(['NONE', 'RG2RGB', 'GR2RGB'])

    self.file_to_align_rotate = QComboBox()
    self.file_to_align_rotate.addItems(['0', '90', '180', '270'])

    self.file_to_align_platesolve_run = QPushButton('Solve plate', self)
    self.file_to_align_platesolve_run.clicked.connect(self.f_file_to_align_platesolve_run)

    self.file_to_align_platesolve_cancel = QPushButton('Cancel', self)
    self.file_to_align_platesolve_cancel.clicked.connect(self.f_file_to_align_platesolve_cancel)

    self.file_to_align_platesolve_set_eq5 = QPushButton('SET RADEC on EQ5 page', self)
    self.file_to_align_platesolve_set_eq5.clicked.connect(lambda: self.f_file_to_align_platesolve_set_radec(mount='eq5'))

    self.file_to_align_platesolve_set_eq6 = QPushButton('SET RADEC on EQ6 page', self)
    self.file_to_align_platesolve_set_eq6.clicked.connect(lambda: self.f_file_to_align_platesolve_set_radec(mount='eq6'))

    self.file_to_align_px_scale = QLabel("Px scale: NULL")
    self.file_to_align_platesolve_state = QLabel("NULL")

    self.lab_file_to_align_photo_pixel_stat = QLabel("0: 99999, 1: 99999, 50: 99999, 99: 99999, 100: 99999")

    self.loghist_file_to_align = QCheckBox()
    self.loghist_file_to_align.setChecked(True)

    self.graphWidget_file_to_align = pg.PlotWidget()
    self.hist_color_file_to_align = self.palette().color(QtGui.QPalette.Window)
    self.hist_pen_file_to_align = pg.mkPen(color=(0,0,0))
    self.graphWidget_file_to_align.plot(x=list(range(256)), y=list(range(256)), pen=self.hist_pen_file_to_align)
    self.graphWidget_file_to_align.setBackground(self.hist_color_file_to_align)




    layout.addWidget(self.file_to_align_title)
    file_to_align_layout = QHBoxLayout()
    file_to_align_layout.addWidget(self.file_to_align_path)
    file_to_align_layout.addWidget(self.file_to_align_but1)
    file_to_align_layout.addWidget(self.file_to_align_but2)
    layout.addLayout(file_to_align_layout)

    file_to_align_layout2 = QHBoxLayout()
    file_to_align_layout2.addWidget(QLabel("Debayer"))
    file_to_align_layout2.addWidget(self.file_to_align_debayer)
    file_to_align_layout2.addWidget(QLabel("Rotate"))
    file_to_align_layout2.addWidget(self.file_to_align_rotate)
    file_to_align_layout2.addStretch()
    layout.addLayout(file_to_align_layout2)

    file_to_align_layout4 = QHBoxLayout()
    file_to_align_layout4.addWidget(self.file_to_align_platesolve_run)
    file_to_align_layout4.addWidget(self.file_to_align_platesolve_cancel)
    file_to_align_layout4.addWidget(self.file_to_align_platesolve_set_eq5)
    file_to_align_layout4.addWidget(self.file_to_align_platesolve_set_eq6)
    layout.addLayout(file_to_align_layout4)
    layout.addWidget(self.file_to_align_platesolve_state)
    layout.addWidget(self.file_to_align_px_scale)

    layout.addWidget(separator1)

    file_to_align_layout3 = QHBoxLayout()
    file_to_align_layout3.addWidget(QLabel("NORM:"))
    file_to_align_layout3.addWidget(self.file_to_align_normalize)
    file_to_align_layout3.addWidget(QLabel("L:"))
    file_to_align_layout3.addWidget(self.file_to_align_normalize_l)
    file_to_align_layout3.addWidget(QLabel("H:"))
    file_to_align_layout3.addWidget(self.file_to_align_normalize_h)
    file_to_align_layout3.addWidget(QLabel("Log hist:"))
    file_to_align_layout3.addWidget(self.loghist_file_to_align)
    file_to_align_layout3.addStretch()
    layout.addLayout(file_to_align_layout3)

    layout.addWidget(self.lab_file_to_align_photo_pixel_stat)
    layout.addWidget(self.graphWidget_file_to_align)
    layout.addWidget(separator2)
    layout.addStretch()

    self.lewy_tab14.setLayout(layout)

#############################################################################################

  def tab_1_prawyUI(self):
    global viewer_a183mm_deployed
    layout = QVBoxLayout()
    self.viewer_a183mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a183mm)
    self.prawy_tab1.setLayout(layout)
    viewer_a183mm_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a183mm')

#############################################################################################

  def tab_2_prawyUI(self):
    global viewer_a533mm_deployed
    layout = QVBoxLayout()
    self.viewer_a533mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a533mm)
    self.prawy_tab2.setLayout(layout)
    viewer_a533mm_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a533mm')

#############################################################################################

  def tab_3_prawyUI(self):
    global viewer_a533mc_deployed
    layout = QVBoxLayout()
    self.viewer_a533mc = PhotoViewer(self)
    layout.addWidget(self.viewer_a533mc)
    self.prawy_tab3.setLayout(layout)
    viewer_a533mc_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a533mc')

#############################################################################################

  def tab_4_prawyUI(self):
    global viewer_a432mm_deployed
    layout = QVBoxLayout()
    self.viewer_a432mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a432mm)
    self.prawy_tab4.setLayout(layout)
    viewer_a432mm_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a432mm')

#############################################################################################

  def tab_5_prawyUI(self):
    global viewer_a462mc_deployed
    layout = QVBoxLayout()
    self.viewer_a462mc = PhotoViewer(self)
    layout.addWidget(self.viewer_a462mc)
    self.prawy_tab5.setLayout(layout)
    viewer_a462mc_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a462mc')

#############################################################################################

  def tab_6_prawyUI(self):
    global viewer_a120mm_deployed
    layout = QVBoxLayout()
    self.viewer_a120mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a120mm)
    self.prawy_tab6.setLayout(layout)
    viewer_a120mm_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a120mm')

#############################################################################################

  def tab_7_prawyUI(self):
    global viewer_a290mm_deployed
    layout = QVBoxLayout()
    self.viewer_a290mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a290mm)
    self.prawy_tab7.setLayout(layout)
    viewer_a290mm_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a290mm')

#############################################################################################

  def tab_8_prawyUI(self):
    global viewer_a174mm_deployed
    layout = QVBoxLayout()
    self.viewer_a174mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a174mm)
    self.prawy_tab8.setLayout(layout)
    viewer_a174mm_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a174mm')

#############################################################################################

  def tab_9_prawyUI(self):
    global viewer_a120mc_deployed
    layout = QVBoxLayout()
    self.viewer_a120mc = PhotoViewer(self)
    layout.addWidget(self.viewer_a120mc)
    self.prawy_tab9.setLayout(layout)
    viewer_a120mc_deployed = True
    self.f_cam_pix_scale_calc_universal(camname='a120mc')

#############################################################################################

  def tab_10_prawyUI(self):
    global viewer_canon_deployed
    layout = QVBoxLayout()
    self.viewer_canon = PhotoViewer(self)
    layout.addWidget(self.viewer_canon)
    self.prawy_tab10.setLayout(layout)
    viewer_canon_deployed = True
    self.f_canon_pix_scale_calc(0)

#############################################################################################

  def tab_11_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_align_picture = PhotoViewer(self)
    layout.addWidget(self.viewer_align_picture)
    self.prawy_tab11.setLayout(layout)

#############################################################################################

  def tab_12_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_tycho2 = PhotoViewer(self)
    layout.addWidget(self.viewer_tycho2)
    self.prawy_tab12.setLayout(layout)

#############################################################################################

  def tab_13_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_hd = PhotoViewer(self)
    layout.addWidget(self.viewer_hd)
    self.prawy_tab13.setLayout(layout)

#############################################################################################

  def tab_14_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_galaxy = PhotoViewer(self)
    layout.addWidget(self.viewer_galaxy)
    self.prawy_tab14.setLayout(layout)

#############################################################################################

  def tab_15_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_skymap = QWebEngineView()
    layout.addWidget(self.viewer_skymap)
    self.prawy_tab15.setLayout(layout)

#############################################################################################


  def f_immediate_stop_eq5(self):
    global req_cmd_eq5

    payload = {
      'mode': 'immediate_stop',
    }
    req_cmd_eq5.put(payload)

  def f_coord_rog_bloku_eq5(self):
    self.az_d_eq5.setValue(145)
    self.az_m_eq5.setValue(10)
    self.elev_d_eq5.setValue(23)
    self.elev_m_eq5.setValue(35)

  def f_coord_zenith_eq5(self):
    self.az_d_eq5.setValue(88)
    self.az_m_eq5.setValue(0)
    self.elev_d_eq5.setValue(88)
    self.elev_m_eq5.setValue(0)

  def f_coord_skytower_lampa_eq5(self):
    self.az_d_eq5.setValue(171)
    self.az_m_eq5.setValue(10)
    self.elev_d_eq5.setValue(6)
    self.elev_m_eq5.setValue(20)

  def f_altaz_get_eq5(self, alt=False, az=False):
    global eq5_stats
    if az:
      self.az_d_eq5.setValue(int(Angle(eq5_stats['position']['az'] * u.deg).dms.d))
      self.az_m_eq5.setValue(int(Angle(eq5_stats['position']['az'] * u.deg).dms.m))
    if alt:
      self.elev_d_eq5.setValue(int(Angle(eq5_stats['position']['alt'] * u.deg).dms.d))
      self.elev_m_eq5.setValue(int(Angle(eq5_stats['position']['alt'] * u.deg).dms.m))

  def f_altaz_goto_eq5(self):
    global eq5_stats, eq6_stats, req_cmd_eq5

    t = Time(eq6_stats['epoch']).now()
    alt_str = str(self.elev_d_eq5.value()) + 'd' + str(self.elev_m_eq5.value()) + 'm'
    az_str = str(self.az_d_eq5.value()) + 'd' + str(self.az_m_eq5.value()) + 'm'
    radec_place = SkyCoord(alt = Angle(alt_str), az = Angle(az_str), obstime = t, frame = 'altaz', location = eq6_stats['loc'])

    new_ra =  Angle(radec_place.icrs.ra.to_string(unit=u.hour))
    new_dec = Angle(radec_place.icrs.dec.to_string(unit=u.deg))

    payload = {
      'mode': 'radec',
      'ra': new_ra.to_string(),
      'dec': new_dec.to_string(),
      'move': True,
      'update_pos': True
    }
    req_cmd_eq5.put(payload)

  def f_altaz_set_eq5(self):
    global eq5_stats, eq6_stats, req_cmd_eq5

    t = Time(eq6_stats['epoch']).now()
    alt_str = str(self.elev_d_eq5.value()) + 'd' + str(self.elev_m_eq5.value()) + 'm'
    az_str = str(self.az_d_eq5.value()) + 'd' + str(self.az_m_eq5.value()) + 'm'
    radec_place = SkyCoord(alt = Angle(alt_str), az = Angle(az_str), obstime = t, frame = 'altaz', location = eq6_stats['loc'])

    new_ra =  Angle(radec_place.icrs.ra.to_string(unit=u.hour))
    new_dec = Angle(radec_place.icrs.dec.to_string(unit=u.deg))

    payload = {
      'mode': 'radec',
      'ra': new_ra.to_string(),
      'dec': new_dec.to_string(),
      'move': False,
      'update_pos': True
    }
    req_cmd_eq5.put(payload)

  def f_dec_reverse_eq5(self):
    global eq5_stats
    if self.dec_sign3_eq5.value() < 0:
      signum = '-'
    else:
      signum = ''
    new_dec = Angle(signum + str(self.dec_d_eq5.value()) + 'd' + str(self.dec_m_eq5.value()) + 'm' + str(self.dec_s_eq5.value()) + 's')
    curr_dec = Angle(eq5_stats['position']['dec'])
    diff = curr_dec-new_dec
    rev_dec = curr_dec + diff
    self.dec_sign3_eq5.setValue(int(rev_dec.signed_dms.sign))
    self.dec_d_eq5.setValue(int(rev_dec.signed_dms.d))
    self.dec_m_eq5.setValue(int(rev_dec.signed_dms.m))
    self.dec_s_eq5.setValue(float(rev_dec.signed_dms.s))

  def f_radec_get_eq5(self, ra=False, dec=False):
    global eq5_stats
    if ra:
      self.ra_h_eq5.setValue(int(Angle(eq5_stats['position']['ra']).hms.h))
      self.ra_m_eq5.setValue(int(Angle(eq5_stats['position']['ra']).hms.m))
      self.ra_s_eq5.setValue(float(Angle(eq5_stats['position']['ra']).hms.s))
    if dec:
      self.dec_sign3_eq5.setValue(int(Angle(eq5_stats['position']['dec']).signed_dms.sign))
      self.dec_d_eq5.setValue(int(Angle(eq5_stats['position']['dec']).signed_dms.d))
      self.dec_m_eq5.setValue(int(Angle(eq5_stats['position']['dec']).signed_dms.m))
      self.dec_s_eq5.setValue(float(Angle(eq5_stats['position']['dec']).signed_dms.s))

  def f_radec_set_eq5(self):
    global req_cmd_eq5

    if self.dec_sign3_eq5.value() < 0:
      signum = '-'
    else:
      signum = ''

    new_ra  = str(self.ra_h_eq5.value()) + 'h' + str(self.ra_m_eq5.value()) + 'm' + str(self.ra_s_eq5.value()) + 's'
    new_dec = signum + str(self.dec_d_eq5.value()) + 'd' + str(self.dec_m_eq5.value()) + 'm' + str(self.dec_s_eq5.value()) + 's'

    payload = {
      'mode': 'radec',
      'ra': new_ra,
      'dec': new_dec,
      'move': False,
      'update_pos': True
    }
    req_cmd_eq5.put(payload)

  def f_radec_goto_eq5(self):
    global req_cmd_eq5

    if self.dec_sign3_eq5.value() < 0:
      signum = '-'
    else:
      signum = ''

    new_ra  = str(self.ra_h_eq5.value()) + 'h' + str(self.ra_m_eq5.value()) + 'm' + str(self.ra_s_eq5.value()) + 's'
    new_dec = signum + str(self.dec_d_eq5.value()) + 'd' + str(self.dec_m_eq5.value()) + 'm' + str(self.dec_s_eq5.value()) + 's'

    payload = {
      'mode': 'radec',
      'ra': new_ra,
      'dec': new_dec,
      'move': True,
      'update_pos': True
    }
    req_cmd_eq5.put(payload)


  def f_ost_joystick_left_eq5(self):
    global req_cmd_eq5

    payload = {
      'mode': 'ost_joystick',
      'side': 'right',
      'steps': self.ost_joystick_arc_eq5.value(),
    }
    req_cmd_eq5.put(payload)

  def f_ost_joystick_right_eq5(self):
    global req_cmd_eq5

    payload = {
      'mode': 'ost_joystick',
      'side': 'left',
      'steps': self.ost_joystick_arc_eq5.value(),
    }
    req_cmd_eq5.put(payload)

  def f_eq6_turn_on(self):
    if self.turn_on_mount_eq6.isChecked():
      self.f_track_speed_change_eq6()
      self.f_mount_tracking_eq6()
      self.f_speed_slider_eq6()

  def f_eq5_turn_on(self):
    if self.turn_on_mount_eq5.isChecked():
      self.f_mount_tracking_eq5()
      self.f_speed_slider_eq5()

  def f_quick_check_align_photo_pressed(self):
    global quick_check_align_original_tab
    quick_check_align_original_tab = self.t_prawy.currentIndex()
    self.t_prawy.setCurrentIndex(10)

  def f_quick_check_align_photo_released(self):
    global quick_check_align_original_tab
    self.t_prawy.setCurrentIndex(quick_check_align_original_tab)

  def f_open_file(self):
    homedir = str(pathlib.Path.home())
    fname, _ = QFileDialog.getOpenFileName(self, 'Open file', homedir,"Image files (*.jpg *.JPG *.jpeg *.JPEG *.tif *.TIF *.tiff *.TIFF *.png *.PNG)")
    self.file_to_align_path.setText(fname)

  def f_file_to_align_platesolve_run(self):
    global run_plate_solve_file_to_align
    print('run platesolve')
    run_plate_solve_file_to_align = True

  def f_file_to_align_platesolve_cancel(self):
    print('cancel platesolve')
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/file_to_align_platesolve/frame.axy'])

  def f_file_to_align_platesolve_set_radec(self, mount):
    if mount == 'eq5':
      self.ra_h_eq5.setValue(int(eq6_stats['file_to_align_ra'].hms.h))
      self.ra_m_eq5.setValue(int(eq6_stats['file_to_align_ra'].hms.m))
      self.ra_s_eq5.setValue(float(eq6_stats['file_to_align_ra'].hms.s))
      self.dec_sign3_eq5.setValue(int(eq6_stats['file_to_align_dec'].signed_dms.sign))
      self.dec_d_eq5.setValue(int(eq6_stats['file_to_align_dec'].signed_dms.d))
      self.dec_m_eq5.setValue(int(eq6_stats['file_to_align_dec'].signed_dms.m))
      self.dec_s_eq5.setValue(float(eq6_stats['file_to_align_dec'].signed_dms.s))
    else:
      self.ra_h_eq6.setValue(int(eq6_stats['file_to_align_ra'].hms.h))
      self.ra_m_eq6.setValue(int(eq6_stats['file_to_align_ra'].hms.m))
      self.ra_s_eq6.setValue(float(eq6_stats['file_to_align_ra'].hms.s))
      self.dec_sign3_eq6.setValue(int(eq6_stats['file_to_align_dec'].signed_dms.sign))
      self.dec_d_eq6.setValue(int(eq6_stats['file_to_align_dec'].signed_dms.d))
      self.dec_m_eq6.setValue(int(eq6_stats['file_to_align_dec'].signed_dms.m))
      self.dec_s_eq6.setValue(float(eq6_stats['file_to_align_dec'].signed_dms.s))

  def f_load_file(self):
    global q_file_to_align_platesolve
    filename = self.file_to_align_path.text()
    if filename == '':
      print('No file, ignoring')
      return
    extension = str(pathlib.Path(filename).suffix).replace('.', '')
    if extension.lower() in ['tif', 'tiff']:
      raw = tiff.imread(filename)
    else:
      raw = cv2.imread(filename, -1)

    try:
      if self.file_to_align_debayer.currentText() == 'RG2RGB':
        raw = cv2.cvtColor(raw, cv2.COLOR_BAYER_RG2RGB)
      elif self.file_to_align_debayer.currentText() == 'GR2RGB':
        raw = cv2.cvtColor(raw, cv2.COLOR_BAYER_GR2RGB)
    except:
      print('Ignoring error in debayer')
      pass

    raw = self.f_rotate_frame(frame = raw, rotate = int(self.file_to_align_rotate.currentText()))
    frame_hist = raw.copy()

    frame = self.f_normalize(frame=raw, normalize=self.file_to_align_normalize.isChecked(), low=self.file_to_align_normalize_l.value(), high=self.file_to_align_normalize_h.value())
    frame16 = frame.copy()

    if frame.dtype == 'uint16':
      frame = (frame/256).astype('uint8')

    if frame_hist.dtype == 'uint16':
      frame_hist = (frame_hist/256).astype('uint8')

    if len(frame.shape) == 3:
      iscolor = True
      if frame.shape[2] == 1:
        iscolor = False
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        frame_hist = cv2.cvtColor(frame_hist, cv2.COLOR_GRAY2RGB)
    else:
      iscolor = False
      frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
      frame_hist = cv2.cvtColor(frame_hist, cv2.COLOR_GRAY2RGB)

    if not iscolor:
      frame16 = cv2.cvtColor(frame16, cv2.COLOR_GRAY2RGB)

    q_file_to_align_platesolve.append({'frameRGB': frame, 'frameRGB16': frame16,})
    height, width, channel = frame.shape
    bytesPerLine = 3 * width
    qImg = QImage(frame, width, height, bytesPerLine, QImage.Format_BGR888)
    self.viewer_align_picture.setPhoto(QtGui.QPixmap(qImg))
    self.viewer_align_picture.fitInView()

    self.f_histogram(frame=frame_hist, graph_obj=self.graphWidget_file_to_align, is_color = iscolor, log_hist = self.loghist_file_to_align)
    c = np.percentile(raw,[0,1,50,99,99.99])
    self.lab_file_to_align_photo_pixel_stat.setText("0: " + str(round(c[0])) + ",   1: " + str(round(c[1])) + ",   50: " + str(round(c[2])) + ",   99: " + str(round(c[3])) + ",   99.99: " + str(round(c[4])))

  def f_tracking_color(self):
    global indi_properties, mpd, t_telecope, indi_slider_paramtab, phd2_working, bahtinov_focus_working, last_indi_response_time, last_eq5_response_time

    if self.turn_on_mount_eq6.isChecked():
      if time.time() - last_indi_response_time > 10.0:
        self.mount_state_eq6.setText('state: no connection, indi not responding')
        self.mount_state_eq6.setStyleSheet("background-color: #ff7575")
      else:
        self.mount_state_eq6.setText('state: OK')
        self.mount_state_eq6.setStyleSheet("background-color: #7cf29b")
    else:
      self.mount_state_eq6.setText('state: OFF')
      self.mount_state_eq6.setStyleSheet("background-color: gray")

    if self.turn_on_mount_eq5.isChecked():
      if time.time() - last_eq5_response_time > 10.0:
        self.mount_state_eq5.setText('state: no connection, eq5 api not responding')
        self.mount_state_eq5.setStyleSheet("background-color: #ff7575")
      else:
        self.mount_state_eq5.setText('state: OK')
        self.mount_state_eq5.setStyleSheet("background-color: #7cf29b")
    else:
      self.mount_state_eq5.setText('state: OFF')
      self.mount_state_eq5.setStyleSheet("background-color: gray")

    if 'after_meridian' in eq5_stats.keys():
      if eq5_stats['after_meridian']:
        self.mount_pier_side_eq5.setText('Side: east(point west)')
        self.mount_pier_side_eq5.setStyleSheet("background-color: #ff7575")
      else:
        self.mount_pier_side_eq5.setText('Side: west(point east)')
        self.mount_pier_side_eq5.setStyleSheet("background-color: #7cf29b")
    else:
      self.mount_pier_side_eq5.setStyleSheet("background-color: gray")

    if 'ra_natual' in eq5_stats.keys():
      self.mount_tracking_state_eq5.setText('Tracking: ' + str(eq5_stats['ra_natual']))
      if eq5_stats['ra_natual'] in ['STAR', 'SUN', 'MOON']:
        self.mount_tracking_state_eq5.setStyleSheet("background-color: #7cf29b")
      else:
        self.mount_tracking_state_eq5.setStyleSheet("background-color: #ff7575")
    else:
      self.mount_tracking_state_eq5.setText('Tracking: ???')
      self.mount_tracking_state_eq5.setStyleSheet("background-color: gray")

    if 'EQMod Mount.TELESCOPE_TRACK_STATE.TRACK_ON' in indi_properties.keys():
      self.mount_tracking_state_eq6.setText('Tracking: ' + indi_properties['EQMod Mount.TELESCOPE_TRACK_STATE.TRACK_ON'])
      if indi_properties['EQMod Mount.TELESCOPE_TRACK_STATE.TRACK_ON'] == 'On':
        self.mount_tracking_state_eq6.setStyleSheet("background-color: #7cf29b")
      else:
        self.mount_tracking_state_eq6.setStyleSheet("background-color: #ff7575")

      for i in range(len(indi_slider_paramtab)):
        if indi_properties[indi_slider_paramtab[i]] == 'On':
          break
      self.slider_speed_red_from_indi_eq6.setText('indi: ' + str(indi_slider_valtab[i]))

      if 'EQMod Mount.EQUATORIAL_EOD_COORD.RA' in indi_properties.keys() and 'EQMod Mount.EQUATORIAL_EOD_COORD.DEC' in indi_properties.keys():
        eq6_stats['ra'] = Angle(str(indi_properties['EQMod Mount.EQUATORIAL_EOD_COORD.RA']) + 'h')
        eq6_stats['dec'] = Angle(str(indi_properties['EQMod Mount.EQUATORIAL_EOD_COORD.DEC']) + 'd')
    else:
      self.mount_tracking_state_eq6.setText('Tracking: ???')
      self.mount_tracking_state_eq6.setStyleSheet("background-color: gray")

    if 'EQMod Mount.TELESCOPE_PIER_SIDE.PIER_WEST' in indi_properties.keys():
      if indi_properties['EQMod Mount.TELESCOPE_PIER_SIDE.PIER_WEST'] == 'On':
        self.mount_pier_side_eq6.setText('Side: west(point east)')
        self.mount_pier_side_eq6.setStyleSheet("background-color: #7cf29b")
      else:
        self.mount_pier_side_eq6.setText('Side: east(point west)')
        self.mount_pier_side_eq6.setStyleSheet("background-color: #ff7575")
    else:
      self.mount_pier_side_eq6.setStyleSheet("background-color: gray")

    if phd2_working == True:
      self.lab_phd2_state.setStyleSheet("background-color: #7cf29b")
    elif phd2_working == False:
      self.lab_phd2_state.setStyleSheet("background-color: #ff7575")
    else:
      self.lab_phd2_state.setStyleSheet("background-color: gray")

    if bahtinov_focus_working == True:
      self.bahtinov_focus_state_lab_eq6.setStyleSheet("background-color: #7cf29b")
      self.bahtinov_focus_state_lab_eq6.setText('Bahtinov focus state: OK')
    elif bahtinov_focus_working == False:
      self.bahtinov_focus_state_lab_eq6.setStyleSheet("background-color: #ff7575")
      self.bahtinov_focus_state_lab_eq6.setText('Bahtinov focus state: FAIL')
    else:
      self.bahtinov_focus_state_lab_eq6.setStyleSheet("background-color: gray")
      self.bahtinov_focus_state_lab_eq6.setText('Bahtinov focus state: NULL')


  def f_cam_platesolve_stop_universal(self, camname):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/' + camname + '_platesolve/frame.axy'])

  def f_filter1_manual_set(self):
    global filter_wheel_responds

    if not filter_wheel_responds:
      self.filter1.clear()
      self.filter2.clear()
      self.filter1.addItem('ERR')
      self.filter2.addItem('ERR')
      return

    val = self.filter1_manual.value()
    try:
      out = requests.get('http://eq3.embedded/manual/gora/' + str(val), timeout=3)
    except:
      pass

  def f_filter2_manual_set(self):
    global filter_wheel_responds

    if not filter_wheel_responds:
      self.filter1.clear()
      self.filter2.clear()
      self.filter1.addItem('ERR')
      self.filter2.addItem('ERR')
      return

    val = self.filter2_manual.value()
    try:
      out = requests.get('http://eq3.embedded/manual/dol/' + str(val), timeout=3)
    except:
      pass

  def f_filter_set(self):
    global filter_wheel_responds

    if not filter_wheel_responds:
      self.filter1.clear()
      self.filter2.clear()
      self.filter1.addItem('ERR')
      self.filter2.addItem('ERR')
      return

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
    global filter_reset_done, filters_set, filter_wheel_responds

    if not filter_wheel_responds:
      self.filter1.clear()
      self.filter2.clear()
      self.filter1.addItem('ERR')
      self.filter2.addItem('ERR')
      return

    try:
      out = requests.get('http://eq3.embedded/state', timeout=3)
      if out.status_code == 200:
        state = json.loads(out.text)
        filters_set[0] = state['filtry']['gora'][state['state']['gora']]
        filters_set[1] = state['filtry']['dol'][state['state']['dol']]
    except:
      pass

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

  def f_cam_bri_sat_gam_rst_universal(self, camname):
    getattr(self,camname + '_cam_bri').setValue(0)
    getattr(self,camname + '_cam_sat').setValue(1.0)
    getattr(self,camname + '_cam_gam').setValue(1.0)
    getattr(self,camname + '_cam_inverse').setChecked(False)
    getattr(self,camname + '_cam_hist_equal').setChecked(False)
    getattr(self,camname + '_cam_normalize').setChecked(False)
    getattr(self,camname + '_cam_normalize_l').setValue(0.0)
    getattr(self,camname + '_cam_normalize_h').setValue(100.0)

  def f_cam_pix_scale_calc_universal(self, camname):
    getattr(self,camname + '_cam_scale_pixel_scale').setValue(float(float(getattr(self,camname + '_cam_scale_pixel_size').value()) * 206.265 / float(getattr(self,camname + '_cam_scale_focal').value())))

  def f_canon_cam_bri_sat_gam_rst(self):
    self.canon_cam_bri.setValue(0)
    self.canon_cam_sat.setValue(1.0)
    self.canon_cam_gam.setValue(1.0)
    self.canon_cam_inverse.setChecked(False)
    self.canon_cam_hist_equal.setChecked(False)
    self.canon_cam_normalize.setChecked(False)
    self.canon_cam_normalize_l.setValue(0.0)
    self.canon_cam_normalize_h.setValue(100.0)

  def f_canon_pix_scale_calc(self,val):
    self.canon_scale_pixel_scale.setValue(float(float(self.canon_scale_pixel_size.value()) * 206.265 / float(self.canon_scale_focal.value())))

  def f_cam_plate_solve_universal(self, camname, mount):
    if mount == 'eq6':
      globals()['run_plate_solve_' + camname + '_mount_eq6'] = True
    else:
      globals()['run_plate_solve_' + camname + '_mount_eq6'] = False
    globals()['run_plate_solve_' + camname] = True

  def f_cam_update_values_universal(self, camname):
    global cameras

    curr_time = time.time()
    if 'param_time' in cameras[camname]:
      getattr(self,'lab_' + camname + '_cam_time_param').setText("Last param set: " + str(format(curr_time - cameras[camname]['param_time'], '.1f')) + "s ago")
    else:
      getattr(self,'lab_' + camname + '_cam_time_param').setText("Last param set: NULL")
    if 'disp_frame_time' in cameras[camname]:
      getattr(self,'lab_' + camname + '_cam_time_disp_frame').setText("Displayed frame made: " + str(format(curr_time - cameras[camname]['disp_frame_time'], '.1f')) + "s ago")
    else:
      getattr(self,'lab_' + camname + '_cam_time_disp_frame').setText("Displayed frame made: NULL")
    if 'info' in cameras[camname] and 'temperature' in cameras[camname]['info']:
      getattr(self,'lab_' + camname + '_cam_temp').setText("Sensor temp: " + str(cameras[camname]['info']['temperature']) + " Celsius")
    else:
      getattr(self,'lab_' + camname + '_cam_temp').setText("Sensor temp: NULL")
    if 'Exposure' in cameras[camname] and 'Gain' in cameras[camname]:
      getattr(self,camname + '_cam_exp_gain_depl').setText("Exp: " + str(cameras[camname]['Exposure']['Value']) + " ms; Gain: " + str(cameras[camname]['Gain']['Value']) + " pt; Offset: " + str(cameras[camname]['Offset']['Value']))
    else:
      getattr(self,camname + '_cam_exp_gain_depl').setText("Exp: NULL")
    if 'rotate' in cameras[camname] and 'HardwareBin' in cameras[camname]:
      getattr(self,'lab_' + camname + '_rotate').setText("Rotate: " + str(cameras[camname]['rotate']) + "; Bin: " + str(cameras[camname]['HardwareBin']['Value']))
    else:
      getattr(self,'lab_' + camname + '_rotate').setText("Rotate: NULL")
    if 'CoolerOn' in cameras[camname] and 'info' in cameras[camname] and 'cooler_pwr' in cameras[camname]['info']:
      getattr(self,'lab_' + camname + '_cooling').setText("Cooler on: " + str(cameras[camname]['CoolerOn']['Value']) + "; PWR: " + str(cameras[camname]['info']['cooler_pwr']) )
    else:
      if 'info' in cameras[camname] and 'cooler_pwr' in cameras[camname]['info']:
        getattr(self,'lab_' + camname + '_cooling').setText("Cooling: NULL")



  def f_canon_update_values(self, load_slider = False):
    global cameras

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
    self.lab_canon_time_disp_frame.setText("Displayed frame made: " + str(format(curr_time - cameras['canon']['disp_frame_time'], '.1f')) + "s ago")
    self.lab_canon_rotate.setText("Rotate: " + str(cameras['canon']['rotate']))


  def f_a120mc_cam_button_photo_settings(self):
    self.a120mc_cam_exp_slider.setValue(1000)
    self.a120mc_cam_offset_slider.setValue(2)
    self.a120mc_cam_gain_slider.setValue(29)

  def f_a120mm_cam_button_photo_settings(self):
    self.a120mm_cam_exp_slider.setValue(1000)
    self.a120mm_cam_offset_slider.setValue(2)
    self.a120mm_cam_gain_slider.setValue(29)

  def f_a290mm_cam_button_photo_settings(self):
    self.a290mm_cam_exp_slider.setValue(1000)
    self.a290mm_cam_offset_slider.setValue(8)
    self.a290mm_cam_gain_slider.setValue(112)

  def f_a432mm_cam_button_photo_settings(self):
    self.a432mm_cam_exp_slider.setValue(1000)
    self.a432mm_cam_offset_slider.setValue(8)
    self.a432mm_cam_gain_slider.setValue(145)

  def f_a174mm_cam_button_photo_settings(self):
    self.a174mm_cam_exp_slider.setValue(1000)
    self.a174mm_cam_offset_slider.setValue(16)
    self.a174mm_cam_gain_slider.setValue(180)

  def f_a183mm_cam_button_photo_settings(self):
    self.a183mm_cam_exp_slider.setValue(1000)
    self.a183mm_cam_offset_slider.setValue(16)
    self.a183mm_cam_gain_slider.setValue(115)

  def f_a533mm_cam_button_photo_settings(self):
    self.a533mm_cam_exp_slider.setValue(1000)
    self.a533mm_cam_offset_slider.setValue(40)
    self.a533mm_cam_gain_slider.setValue(105)

  def f_a533mc_cam_button_photo_settings(self):
    self.a533mc_cam_exp_slider.setValue(1000)
    self.a533mc_cam_offset_slider.setValue(40)
    self.a533mc_cam_gain_slider.setValue(105)

  def f_a462mc_cam_button_photo_settings(self):
    self.a462mc_cam_exp_slider.setValue(1000)
    self.a462mc_cam_offset_slider.setValue(10)
    self.a462mc_cam_gain_slider.setValue(85)

  def f_a120mc_cam_button_preview_settings(self):
    self.a120mc_cam_exp_slider.setValue(1000)
    self.a120mc_cam_offset_slider.setValue(2)
    self.a120mc_cam_gain_slider.setValue(99)

  def f_a120mm_cam_button_preview_settings(self):
    self.a120mm_cam_exp_slider.setValue(1000)
    self.a120mm_cam_offset_slider.setValue(2)
    self.a120mm_cam_gain_slider.setValue(99)

  def f_a290mm_cam_button_preview_settings(self):
    self.a290mm_cam_exp_slider.setValue(1000)
    self.a290mm_cam_offset_slider.setValue(8)
    self.a290mm_cam_gain_slider.setValue(350)

  def f_a432mm_cam_button_preview_settings(self):
    self.a432mm_cam_exp_slider.setValue(1000)
    self.a432mm_cam_offset_slider.setValue(8)
    self.a432mm_cam_gain_slider.setValue(350)

  def f_a174mm_cam_button_preview_settings(self):
    self.a174mm_cam_exp_slider.setValue(1000)
    self.a174mm_cam_offset_slider.setValue(16)
    self.a174mm_cam_gain_slider.setValue(400)

  def f_a183mm_cam_button_preview_settings(self):
    self.a183mm_cam_exp_slider.setValue(1000)
    self.a183mm_cam_offset_slider.setValue(16)
    self.a183mm_cam_gain_slider.setValue(450)

  def f_a533mm_cam_button_preview_settings(self):
    self.a533mm_cam_exp_slider.setValue(1000)
    self.a533mm_cam_offset_slider.setValue(40)
    self.a533mm_cam_gain_slider.setValue(550)

  def f_a533mc_cam_button_preview_settings(self):
    self.a533mc_cam_exp_slider.setValue(1000)
    self.a533mc_cam_offset_slider.setValue(40)
    self.a533mc_cam_gain_slider.setValue(550)

  def f_a462mc_cam_button_preview_settings(self):
    self.a462mc_cam_exp_slider.setValue(1000)
    self.a462mc_cam_offset_slider.setValue(10)
    self.a462mc_cam_gain_slider.setValue(450)


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

      height, width, channel = plate_solve_results['galaxy'].shape
      bytesPerLine = 3 * width
      qImg = QImage(plate_solve_results['galaxy'], width, height, bytesPerLine, QImage.Format_BGR888)
      self.viewer_galaxy.setPhoto(QtGui.QPixmap(qImg))
      self.viewer_galaxy.fitInView()

      self.viewer_skymap.load(QUrl(plate_solve_results['url']))
      self.viewer_skymap.show()

  def f_cam_rotate_universal(self, camname):
    global cameras
    cameras[camname]['rotate'] = (cameras[camname]['rotate'] + 90) % 360

  def f_a120mc_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a120mc')

  def f_a120mm_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a120mm')

  def f_a290mm_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a290mm')

  def f_a432mm_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a432mm')

  def f_a174mm_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a174mm')

  def f_canon_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'canon')

  def f_a183mm_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a183mm')

  def f_a533mm_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a533mm')

  def f_a533mc_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a533mc')

  def f_a462mc_window_refresh(self):
    self.f_window_refresh_universal(cam_name = 'a462mc')

  def f_a120mc_window_refresh_event(self):
    self.a120mc_photo_reload.click()

  def f_a120mm_window_refresh_event(self):
    self.a120mm_photo_reload.click()

  def f_a290mm_window_refresh_event(self):
    self.a290mm_photo_reload.click()

  def f_a432mm_window_refresh_event(self):
    self.a432mm_photo_reload.click()

  def f_a174mm_window_refresh_event(self):
    self.a174mm_photo_reload.click()

  def f_canon_window_refresh_event(self):
    self.canon_photo_reload.click()

  def f_solved_tabs_refresh_event(self):
    self.solved_tabs_refresh.click()

  def f_a183mm_window_refresh_event(self):
    self.a183mm_photo_reload.click()

  def f_a533mm_window_refresh_event(self):
    self.a533mm_photo_reload.click()

  def f_a533mc_window_refresh_event(self):
    self.a533mc_photo_reload.click()

  def f_a462mc_window_refresh_event(self):
    self.a462mc_photo_reload.click()

  def f_window_refresh_universal(self, cam_name):
    q_ready         = globals()['q_' + cam_name + '_ready']
    viewer_deployed = globals()['viewer_' + cam_name + '_deployed']
    cam_inverse     = getattr(self,cam_name + '_cam_inverse')
    cam_sat         = getattr(self,cam_name + '_cam_sat')
    cam_bri         = getattr(self,cam_name + '_cam_bri')
    cam_gam         = getattr(self,cam_name + '_cam_gam')
    cam_hist_equal  = getattr(self,cam_name + '_cam_hist_equal')
    cam_normalize   = getattr(self,cam_name + '_cam_normalize')
    cam_normalize_l = getattr(self,cam_name + '_cam_normalize_l')
    cam_normalize_h = getattr(self,cam_name + '_cam_normalize_h')
    cam_circ_d      = getattr(self,cam_name + '_cam_circ_d').value()
    cam_circ_c      = getattr(self,cam_name + '_cam_circ_c').value()
    cam_circ_x      = getattr(self,cam_name + '_cam_circ_x').value()
    cam_circ_y      = getattr(self,cam_name + '_cam_circ_y').value()
    graph_obj       = getattr(self,'graphWidget_' + cam_name)
    viewer_obj      = getattr(self,'viewer_' + cam_name)
    pixel_stat      = getattr(self,'lab_' + cam_name + '_cam_photo_pixel_stat')
    hist_draw       = getattr(self,cam_name + '_cam_hist_draw')
    cameras         = globals()['cameras']
    log_hist        = getattr(self,'loghist_' + cam_name)
    cam_bin         = getattr(self,cam_name + '_cam_bin').currentText()

    if q_ready and viewer_deployed:
      frame = q_ready.popleft()

      if not 'rotate' in cameras[cam_name]:
        cameras[cam_name]['rotate'] = 0
        cameras[cam_name]['last_rotate'] = 0

      _frame = self.f_bri_sat_gam(frame=frame['frameRGB'], sat=cam_sat.value(), bri=cam_bri.value(), gam=cam_gam.value())
      _frame = self.f_hist_equal(frame=_frame, equal=cam_hist_equal.isChecked())
      _frame = self.f_normalize(frame=_frame, normalize=cam_normalize.isChecked(), low=cam_normalize_l.value(), high=cam_normalize_h.value())
      _frame = self.f_inverse_frame(frame=_frame, inverse=cam_inverse.isChecked())
      _frame = self.f_circ(frame=_frame, d=cam_circ_d, c=cam_circ_c, x=cam_circ_x, y=cam_circ_y, cam_bin=cam_bin)
      _frame = self.f_rotate_frame(frame=_frame, rotate=cameras[cam_name]['rotate'])

      if pixel_stat != None:
        pixel_stat.setText(frame['percentile_stat'])
      if hist_draw.isChecked():
        hist_draw.setChecked(False)
        if 'IsColorCam' in cameras[cam_name]['info'].keys():
          is_color = cameras[cam_name]['info']['IsColorCam']
        else:
          is_color = True
        self.f_histogram(frame=frame['frameRGB'], graph_obj=graph_obj, is_color = is_color, log_hist = log_hist)
      self.f_viewer_frame(frame=_frame, viewer_obj=viewer_obj)

      cameras[cam_name]['disp_frame_time'] = frame['time']

      if cameras[cam_name]['last_rotate'] != cameras[cam_name]['rotate']:
        viewer_obj.fitInView()
        cameras[cam_name]['last_rotate'] = cameras[cam_name]['rotate']

  def f_viewer_frame(self, frame, viewer_obj):
      height, width, channel = frame.shape
      bytesPerLine = 3 * width
      qImg = QImage(frame, width, height, bytesPerLine, QImage.Format_BGR888)
      viewer_obj.setPhoto(QtGui.QPixmap(qImg))

  def f_histogram(self, frame, graph_obj, is_color, log_hist):
    hist_pen_r = pg.mkPen(color=(255,0,0), width=2)
    hist_pen_g = pg.mkPen(color=(0,191,41), width=2)
    hist_pen_b = pg.mkPen(color=(0,0,255), width=2)
    hist_pen_gray = pg.mkPen(color=(0,0,0), width=2)

    b,g,r = cv2.split(frame)
    if is_color:
      histogram_b, bin_edges_b = np.histogram(b, bins=256, range=(0, 256))
      histogram_g, bin_edges_g = np.histogram(g, bins=256, range=(0, 256))
      histogram_r, bin_edges_r = np.histogram(r, bins=256, range=(0, 256))
    else:
      histogram_gray, bin_edges_gray = np.histogram(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), bins=256, range=(0, 256))

    graph_obj.clear()
    if log_hist.isChecked():
      graph_obj.setLogMode(True, True)
    else:
      graph_obj.setLogMode(False, False)
    if is_color:
      graph_obj.plot(x=list(range(256)), y=histogram_b, pen=hist_pen_b)
      graph_obj.plot(x=list(range(256)), y=histogram_g, pen=hist_pen_g)
      graph_obj.plot(x=list(range(256)), y=histogram_r, pen=hist_pen_r)
    else:
      graph_obj.plot(x=list(range(256)), y=histogram_gray, pen=hist_pen_gray)
    graph_obj.autoRange()

  def f_circ(self,frame, d, c, x, y, cam_bin):
    if cam_bin != 'NULL':
      frac = int(cam_bin)
      _d = int(d / frac)
      _c = int(c / frac)
      _x = int(x / frac)
      _y = int(y / frac)
    else:
      _d = d
      _c = c
      _x = x
      _y = y

    if _d > 0:
      center_coordinates = (_x,_y)
      color = (0, 0, 255)
      thickness = 2
      _frame = cv2.circle(frame, center_coordinates, _d, color, thickness)
      if _c > 0:
        while True:
          _d = _d + _c
          if _d > 1936 or _c == 0:
            break
          _frame = cv2.circle(frame, center_coordinates, _d, color, thickness)
      return(_frame)
    else:
      return(frame)

  def f_normalize(self, frame, normalize, low, high):
    if normalize:
      l = np.percentile(frame,low)
      h = np.percentile(frame,high)
      if h == l:
        h += 1.0
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

  def print_eq6_position(self):
    global eq6_stats

    self.get_pos_stat()

    try:
      self.radec_position1_eq6.setText('RA: ' + str(eq6_stats['ra']) + "   DEC: " + str(eq6_stats['dec']))
      self.altaz_position1_eq6.setText('AZ: ' + str(eq6_stats['az']) + '   ALT: ' + str(eq6_stats['alt']))
    except Exception as e:
      print(traceback.format_exc())
      pass

  def print_eq5_position(self):
    global eq5_stats

    self.get_pos_stat()

    try:
      if 'position' in eq5_stats.keys():
        self.radec_position1_eq5.setText('RA: ' + str(eq5_stats['position']['ra']) + "   DEC: " + str(eq5_stats['position']['dec']))
        self.altaz_position1_eq5.setText('AZ: ' + str(eq5_stats['position']['az']) + '   ALT: ' + str(eq5_stats['position']['alt']))
    except Exception as e:
      print(traceback.format_exc())
      pass

  def f_radec_goto_eq6(self):
    global eq6_stats

    if self.dec_sign3_eq6.value() < 0:
      signum = '-'
    else:
      signum = ''

    eq6_stats['new_dec'] = Angle(signum + str(self.dec_d_eq6.value()) + 'd' + str(self.dec_m_eq6.value()) + 'm' + str(self.dec_s_eq6.value()) + 's')
    eq6_stats['new_ra']  = Angle(str(self.ra_h_eq6.value()) + 'h' + str(self.ra_m_eq6.value()) + 'm' + str(self.ra_s_eq6.value()) + 's')
    c = {
      'cmd': 'goto_telescope_pos',
      'new_ra': eq6_stats['new_ra'],
      'ra': eq6_stats['ra'],
      'dec': str(eq6_stats['dec']),
      'new_dec': str(eq6_stats['new_dec']),
    }
    mpd['p_indi']['ptc'].put(c)

  def f_radec_set_eq6(self):
    global eq6_stats, mpd

    if self.dec_sign3_eq6.value() < 0:
      signum = '-'
    else:
      signum = ''

    eq6_stats['new_ra']  = Angle(str(self.ra_h_eq6.value()) + 'h' + str(self.ra_m_eq6.value()) + 'm' + str(self.ra_s_eq6.value()) + 's')
    eq6_stats['new_dec'] = Angle(signum + str(self.dec_d_eq6.value()) + 'd' + str(self.dec_m_eq6.value()) + 'm' + str(self.dec_s_eq6.value()) + 's')
    c = {
      'cmd': 'sync_telescope_pos',
      'new_ra': eq6_stats['new_ra'],
      'ra': eq6_stats['ra'],
      'dec': str(eq6_stats['dec']),
      'new_dec': str(eq6_stats['new_dec']),
    }
    mpd['p_indi']['ptc'].put(c)


  def f_altaz_goto_eq6(self):
    global eq6_stats

    t = Time(eq6_stats['epoch']).now()
    alt_str = str(self.elev_d_eq6.value()) + 'd' + str(self.elev_m_eq6.value()) + 'm'
    az_str = str(self.az_d_eq6.value()) + 'd' + str(self.az_m_eq6.value()) + 'm'
    radec_place = SkyCoord(alt = Angle(alt_str), az = Angle(az_str), obstime = t, frame = 'altaz', location = eq6_stats['loc'])

    eq6_stats['new_ra'] =  Angle(radec_place.icrs.ra.to_string(unit=u.hour))
    eq6_stats['new_dec'] = Angle(radec_place.icrs.dec.to_string(unit=u.deg))
    c = {
      'cmd': 'goto_telescope_pos',
      'new_ra': eq6_stats['new_ra'],
      'ra': eq6_stats['ra'],
      'dec': str(eq6_stats['dec']),
      'new_dec': str(eq6_stats['new_dec']),
    }
    mpd['p_indi']['ptc'].put(c)


  def f_altaz_set_eq6(self):
    global eq6_stats, mpd

    t = Time(eq6_stats['epoch']).now()
    alt_str = str(self.elev_d_eq6.value()) + 'd' + str(self.elev_m_eq6.value()) + 'm'
    az_str = str(self.az_d_eq6.value()) + 'd' + str(self.az_m_eq6.value()) + 'm'
    radec_place = SkyCoord(alt = Angle(alt_str), az = Angle(az_str), obstime = t, frame = 'altaz', location = eq6_stats['loc'])
    eq6_stats['new_ra'] =  Angle(radec_place.icrs.ra.to_string(unit=u.hour))
    eq6_stats['new_dec'] = Angle(radec_place.icrs.dec.to_string(unit=u.deg))
    c = {
      'cmd': 'sync_telescope_pos',
      'new_ra': eq6_stats['new_ra'],
      'ra': eq6_stats['ra'],
      'dec': str(eq6_stats['dec']),
      'new_dec': str(eq6_stats['new_dec']),
    }
    mpd['p_indi']['ptc'].put(c)

  def f_dec_reverse_eq6(self):
    global eq6_stats
    if self.dec_sign3_eq6.value() < 0:
      signum = '-'
    else:
      signum = ''
    new_dec = Angle(signum + str(self.dec_d_eq6.value()) + 'd' + str(self.dec_m_eq6.value()) + 'm' + str(self.dec_s_eq6.value()) + 's')
    curr_dec = eq6_stats['dec']
    diff = curr_dec-new_dec
    rev_dec = curr_dec + diff
    self.dec_sign3_eq6.setValue(int(rev_dec.signed_dms.sign))
    self.dec_d_eq6.setValue(int(rev_dec.signed_dms.d))
    self.dec_m_eq6.setValue(int(rev_dec.signed_dms.m))
    self.dec_s_eq6.setValue(float(rev_dec.signed_dms.s))

  def f_radec_get_eq6(self, ra=False, dec=False):
    global eq6_stats
    if ra:
      self.ra_h_eq6.setValue(int(eq6_stats['ra'].hms.h))
      self.ra_m_eq6.setValue(int(eq6_stats['ra'].hms.m))
      self.ra_s_eq6.setValue(float(eq6_stats['ra'].hms.s))
    if dec:
      self.dec_sign3_eq6.setValue(int(eq6_stats['dec'].signed_dms.sign))
      self.dec_d_eq6.setValue(int(eq6_stats['dec'].signed_dms.d))
      self.dec_m_eq6.setValue(int(eq6_stats['dec'].signed_dms.m))
      self.dec_s_eq6.setValue(float(eq6_stats['dec'].signed_dms.s))

  def f_altaz_get_eq6(self, alt=False, az=False):
    global eq6_stats
    if az:
      self.az_d_eq6.setValue(int(eq6_stats['az'].dms.d))
      self.az_m_eq6.setValue(int(eq6_stats['az'].dms.m))
    if alt:
      self.elev_d_eq6.setValue(int(eq6_stats['alt'].dms.d))
      self.elev_m_eq6.setValue(int(eq6_stats['alt'].dms.m))

  def f_ost_joystick_left_eq6(self):
    payload = {
      'mode': 'focus',
      'side': 'left',
      'steps': self.ost_joystick_arc_eq6.value(),
    }
    req_cmd_eq6.put(payload)

  def f_ost_joystick_right_eq6(self):
    payload = {
      'mode': 'focus',
      'side': 'right',
      'steps': self.ost_joystick_arc_eq6.value(),
    }
    req_cmd_eq6.put(payload)

  def f_bahtinov_eq6(self):
    payload = {
      'mode': 'bahtinov',
      'angle': self.bahtinov_angle_eq6.value(),
    }
    req_cmd_eq6.put(payload)

  def f_bahtinov_angle_eq6(self, angle):
    payload = {
      'mode': 'bahtinov',
      'angle': int(angle),
    }
    req_cmd_eq6.put(payload)

  def f_goto_object_find_eq5(self):
    global eq6_stats

    ob = self.obj_name_eq5.text()
    if ob:
      out = requests.get('http://localhost:8090/api/objects/info?name=' + ob + '&format=map')
      if out.status_code == 200:
        data = json.loads(out.text)
        l2 = ob + '=' + data['localized-name']
      else:
        l2 = "ERR"
    else:
      l2 = "ERR"

    self.obj_name_goto_info_eq5.setText(l2)
    if l2 == "ERR":
      return
    pos_ra = Angle(str(data['ra']) + 'd').wrap_at(360 * u.deg)
    pos_dec = Angle(str(data['dec']) + 'd')

    t = Time(eq6_stats['epoch']).now()
    actual_radec = SkyCoord(ra=pos_ra, dec=pos_dec, frame='icrs')
    actual_altaz = actual_radec.transform_to(AltAz(obstime=t,location=eq6_stats['loc']))
    pos_el = Angle(actual_altaz.alt.wrap_at(180 * u.deg).degree * u.deg)
    pos_az = Angle(actual_altaz.az.wrap_at(360 * u.deg).degree * u.deg)

    self.ra_h_eq5.setValue(int(pos_ra.hms.h))
    self.ra_m_eq5.setValue(int(pos_ra.hms.m))
    self.ra_s_eq5.setValue(float(pos_ra.hms.s))
    self.dec_sign3_eq5.setValue(int(pos_dec.signed_dms.sign))
    self.dec_d_eq5.setValue(int(pos_dec.signed_dms.d))
    self.dec_m_eq5.setValue(int(pos_dec.signed_dms.m))
    self.dec_s_eq5.setValue(float(pos_dec.signed_dms.s))

    self.az_d_eq5.setValue(int(pos_az.dms.d))
    self.az_m_eq5.setValue(int(pos_az.dms.m))
    self.elev_d_eq5.setValue(int(pos_el.dms.d))
    self.elev_m_eq5.setValue(int(pos_el.dms.m))

  def f_goto_object_find_eq6(self):
    global eq6_stats

    ob = self.obj_name_eq6.text()
    if ob:
      out = requests.get('http://localhost:8090/api/objects/info?name=' + ob + '&format=map')
      if out.status_code == 200:
        data = json.loads(out.text)
        l2 = ob + '=' + data['localized-name']
      else:
        l2 = "ERR"
    else:
      l2 = "ERR"

    self.obj_name_goto_info_eq6.setText(l2)
    if l2 == "ERR":
      return
    pos_ra = Angle(str(data['ra']) + 'd').wrap_at(360 * u.deg)
    pos_dec = Angle(str(data['dec']) + 'd')

    t = Time(eq6_stats['epoch']).now()
    actual_radec = SkyCoord(ra=pos_ra, dec=pos_dec, frame='icrs')
    actual_altaz = actual_radec.transform_to(AltAz(obstime=t,location=eq6_stats['loc']))
    pos_el = Angle(actual_altaz.alt.wrap_at(180 * u.deg).degree * u.deg)
    pos_az = Angle(actual_altaz.az.wrap_at(360 * u.deg).degree * u.deg)

    self.ra_h_eq6.setValue(int(pos_ra.hms.h))
    self.ra_m_eq6.setValue(int(pos_ra.hms.m))
    self.ra_s_eq6.setValue(float(pos_ra.hms.s))
    self.dec_sign3_eq6.setValue(int(pos_dec.signed_dms.sign))
    self.dec_d_eq6.setValue(int(pos_dec.signed_dms.d))
    self.dec_m_eq6.setValue(int(pos_dec.signed_dms.m))
    self.dec_s_eq6.setValue(float(pos_dec.signed_dms.s))

    self.az_d_eq6.setValue(int(pos_az.dms.d))
    self.az_m_eq6.setValue(int(pos_az.dms.m))
    self.elev_d_eq6.setValue(int(pos_el.dms.d))
    self.elev_m_eq6.setValue(int(pos_el.dms.m))



  def f_coord_rog_bloku_eq6(self):
    self.az_d_eq6.setValue(143)
    self.az_m_eq6.setValue(28)
    self.elev_d_eq6.setValue(23)
    self.elev_m_eq6.setValue(5)

  def f_coord_zenith_eq6(self):
    self.az_d_eq6.setValue(88)
    self.az_m_eq6.setValue(0)
    self.elev_d_eq6.setValue(88)
    self.elev_m_eq6.setValue(0)

  def f_coord_skytower_lampa_eq6(self):
    self.az_d_eq6.setValue(171)
    self.az_m_eq6.setValue(10)
    self.elev_d_eq6.setValue(6)
    self.elev_m_eq6.setValue(20)

  def f_mount_tracking_eq5(self):
    global req_cmd_eq5

    if self.mount_tracking_eq5.isChecked():
      if self.track_speed_eq5.currentText() == 'SIDEREAL':
        speed = 'STAR'
      elif self.track_speed_eq5.currentText() == 'SUN':
        speed = 'SUN'
      else:
        speed = 'MOON'
    else:
      speed = 'OFF'

    payload = {
      'mode': 'ra_natural',
      'speed': speed,
    }
    req_cmd_eq5.put(payload)

  def f_mount_tracking_eq6(self):
    global mpd
    if self.mount_tracking_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_TRACK_STATE.TRACK_ON=On'})
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.HORIZONLIMITSLIMITGOTO.HORIZONLIMITSLIMITGOTODISABLE=On'})
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.HORIZONLIMITSONLIMIT.HORIZONLIMITSONLIMITTRACK=Off'})
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.HORIZONLIMITSONLIMIT.HORIZONLIMITSONLIMITSLEW=Off'})
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.HORIZONLIMITSONLIMIT.HORIZONLIMITSONLIMITGOTO=Off'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_TRACK_STATE.TRACK_OFF=On'})

  def f_track_speed_change_eq6(self):
    global mpd
    if self.track_speed_eq6.currentText() == 'SIDEREAL':
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_TRACK_MODE.TRACK_SIDEREAL=On'})
    elif self.track_speed_eq6.currentText() == 'SUN':
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_TRACK_MODE.TRACK_SOLAR=On'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_TRACK_MODE.TRACK_LUNAR=On'})

  def f_speed_slider_eq6(self):
    global indi_properties, indi_slider_valtab, indi_slider_paramtab, mpd

    self.slider_speed_selected_eq6.setText(indi_slider_valtab[self.speed_slider_eq6.value()])
    mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': indi_slider_paramtab[self.speed_slider_eq6.value()] + '=On'})

  def f_speed_slider_eq5(self):
    global eq5_slider_valtab

    self.slider_speed_selected_eq5.setText(eq5_slider_valtab[self.speed_slider_eq5.value()])

  def f_move_up_press_eq5(self):
    global req_cmd_eq5, eq5_slider_valtab
    if self.move_flip_ud_eq5.isChecked():
      signum = -1
    else:
      signum = 1
    payload = {
      'mode': 'dec_manual',
      'speed': int(eq5_slider_valtab[self.speed_slider_eq5.value()]) * signum,
    }
    req_cmd_eq5.put(payload)

  def f_move_down_press_eq5(self):
    global req_cmd_eq5, eq5_slider_valtab
    if self.move_flip_ud_eq5.isChecked():
      signum = 1
    else:
      signum = -1
    payload = {
      'mode': 'dec_manual',
      'speed': int(eq5_slider_valtab[self.speed_slider_eq5.value()]) * signum,
    }
    req_cmd_eq5.put(payload)

  def f_move_dec_release_eq5(self):
    global req_cmd_eq5, eq5_slider_valtab
    payload = {
      'mode': 'dec_manual',
      'speed': 0,
    }
    req_cmd_eq5.put(payload)

  def f_move_left_press_eq5(self):
    global req_cmd_eq5, eq5_slider_valtab
    if self.move_flip_lr_eq5.isChecked():
      signum = -1
    else:
      signum = 1
    payload = {
      'mode': 'ra_manual',
      'speed': int(eq5_slider_valtab[self.speed_slider_eq5.value()]) * signum,
    }
    req_cmd_eq5.put(payload)

  def f_move_right_press_eq5(self):
    global req_cmd_eq5, eq5_slider_valtab
    if self.move_flip_lr_eq5.isChecked():
      signum = 1
    else:
      signum = -1
    payload = {
      'mode': 'ra_manual',
      'speed': int(eq5_slider_valtab[self.speed_slider_eq5.value()]) * signum,
    }
    req_cmd_eq5.put(payload)

  def f_move_ra_release_eq5(self):
    global req_cmd_eq5, eq5_slider_valtab
    payload = {
      'mode': 'ra_manual',
      'speed': 0,
    }
    req_cmd_eq5.put(payload)

  def f_move_left_press_eq6(self):
    global mpd
    if self.move_flip_lr_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_WE.MOTION_EAST=On'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_WE.MOTION_WEST=On'})

  def f_move_right_press_eq6(self):
    global mpd
    if self.move_flip_lr_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_WE.MOTION_WEST=On'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_WE.MOTION_EAST=On'})

  def f_move_up_press_eq6(self):
    global mpd
    if self.move_flip_ud_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_NS.MOTION_SOUTH=On'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_NS.MOTION_NORTH=On'})

  def f_move_down_press_eq6(self):
    global mpd
    if self.move_flip_ud_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_NS.MOTION_NORTH=On'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_NS.MOTION_SOUTH=On'})

  def f_move_left_release_eq6(self):
    global mpd
    if self.move_flip_lr_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_WE.MOTION_EAST=Off'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_WE.MOTION_WEST=Off'})

  def f_move_right_release_eq6(self):
    global mpd
    if self.move_flip_lr_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_WE.MOTION_WEST=Off'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_WE.MOTION_EAST=Off'})

  def f_move_up_release_eq6(self):
    global mpd
    if self.move_flip_ud_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_NS.MOTION_SOUTH=Off'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_NS.MOTION_NORTH=Off'})

  def f_move_down_release_eq6(self):
    global mpd
    if self.move_flip_ud_eq6.isChecked():
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_NS.MOTION_NORTH=Off'})
    else:
      mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_MOTION_NS.MOTION_SOUTH=Off'})

  def f_move_stop_eq6(self):
    global mpd
    mpd['p_indi']['ptc'].put({'cmd': 'indi_setprop', 'prop': 'EQMod Mount.TELESCOPE_ABORT_MOTION.ABORT=On'})

  def f_changed_tab_left(self,tab):
    if tab == 2:
      self.t_prawy.setCurrentIndex(0)
    elif tab == 3:
      self.t_prawy.setCurrentIndex(1)
    elif tab == 4:
      self.t_prawy.setCurrentIndex(2)
    elif tab == 5:
      self.t_prawy.setCurrentIndex(3)
    elif tab == 6:
      self.t_prawy.setCurrentIndex(4)
    elif tab == 7:
      self.t_prawy.setCurrentIndex(5)
    elif tab == 8:
      self.t_prawy.setCurrentIndex(6)
    elif tab == 9:
      self.t_prawy.setCurrentIndex(7)
    elif tab == 10:
      self.t_prawy.setCurrentIndex(8)
    elif tab == 11:
      self.t_prawy.setCurrentIndex(9)
    elif tab == 13:
      self.t_prawy.setCurrentIndex(10)

  def f_shutdown(self):
    global kill_thread
    for i in ['http://127.0.0.2:8003/shutdown', 'http://eq4.embedded/shutdown', 'http://eq3.embedded/shutdown', 'http://eq2.embedded/shutdown', 'http://eq1-wifi.embedded/shutdown']:
      try:
        out = requests.get(i, timeout=3)
      except:
        pass

  def f_reboot_scope(self):
    global kill_thread
    for i in ['http://eq4.embedded/reboot', 'http://eq3.embedded/reboot', 'http://eq2.embedded/reboot']:
      try:
        out = requests.get(i, timeout=3)
      except:
        pass

  def f_restart(self):
    global kill_thread
    for i in ['http://eq4.embedded/restart', 'http://eq3.embedded/restart', 'http://eq2.embedded/restart']:
      try:
        out = requests.get(i, timeout=3)
      except:
        pass

  def get_pos_stat(self):
    global eq6_stats

    t = Time(eq6_stats['epoch']).now()
    actual = SkyCoord(ra=eq6_stats['ra'], dec=eq6_stats['dec'], frame='icrs')
    actual_altaz = actual.transform_to(AltAz(obstime=t,location=eq6_stats['loc']))
    eq6_stats['alt'] = Angle(actual_altaz.alt.wrap_at(180 * u.deg).degree * u.deg)
    eq6_stats['az']  = Angle(actual_altaz.az.wrap_at(360 * u.deg).degree * u.deg)


def p_filter_wheel_state(q_ptc, q_ctp):
  wheel_responds = False

  while True:
    if not q_ptc.empty():
      cmd = q_ptc.get()
      if cmd['cmd'] == 'shutdown':
        return
      else:
        print("In process " + str(inspect.stack()[0][3]) + " - unknown cmd: " + str(cmd['cmd']))

    try:
      out = requests.get('http://eq3.embedded/state', timeout=3)
      if out.status_code == 200:
        state = json.loads(out.text)
        wheel_responds = True
      else:
        wheel_responds = False
    except:
      wheel_responds = False
      pass

    q_ctp.put({'wheel_responds': wheel_responds})
    time.sleep(1)


def t_filter_wheel_state():
  global kill_thread, mpd, filter_wheel_responds

  while not kill_thread:
    time.sleep(0.5)
    if mpd['p_filter_wheel_state']['ctp'].qsize() > 0:
      filter_wheel_responds = mpd['p_filter_wheel_state']['ctp'].get()['wheel_responds']


def p_bahtinov_focus_state(q_ptc, q_ctp):
  bahtinov_focus_responds = False

  while True:
    if not q_ptc.empty():
      cmd = q_ptc.get()
      if cmd['cmd'] == 'shutdown':
        return
      else:
        print("In process " + str(inspect.stack()[0][3]) + " - unknown cmd: " + str(cmd['cmd']))

    try:
      out = requests.get('http://eq4.embedded/state', timeout=3)
      if out.status_code == 200:
        bahtinov_focus_responds = True
      else:
        bahtinov_focus_responds = False
    except:
      bahtinov_focus_responds = False
      pass

    q_ctp.put({'bahtinov_focus_responds': bahtinov_focus_responds})
    time.sleep(1)


def t_bahtinov_focus_state():
  global kill_thread, mpd, bahtinov_focus_working

  while not kill_thread:
    time.sleep(0.5)
    if mpd['p_bahtinov_focus_state']['ctp'].qsize() > 0:
      bahtinov_focus_working = mpd['p_bahtinov_focus_state']['ctp'].get()['bahtinov_focus_responds']


def f_make_mpd(function, camname=None):
  global mpd
  function_name = function.__name__
  mpd[function_name] = {}
  mpd[function_name]['ptc'] = mp.Queue()
  mpd[function_name]['ctp'] = mp.Queue()
  if camname != None:
    mpd[function_name]['p'] = mp.Process(target=function, args=(mpd[function_name]['ptc'],mpd[function_name]['ctp'],camname,))
  else:
    mpd[function_name]['p'] = mp.Process(target=function, args=(mpd[function_name]['ptc'],mpd[function_name]['ctp'],))


def t_mpd_print():
  global mpd, kill_thread

  while not kill_thread:
    time.sleep(1)
    for i in mpd.keys():
      s_ptc = mpd[i]['ptc'].qsize()
      s_ctp = mpd[i]['ctp'].qsize()
      if s_ptc > 0 or s_ctp > 0:
        print(i)
        print("    ptc: " + str(s_ptc))
        print("    ctp: " + str(s_ctp))
    print()


def t_process_thread_interaction():
  global mpd, screen, kill_thread

  while not kill_thread:
    time.sleep(0.1)

    if mpd['p_indi']['ctp'].qsize() > 0:
      msg = mpd['p_indi']['ctp'].get()['last_radec_diff']
      print(msg)
      screen.last_radec_diff_eq6.setText(msg)

def p_eq5_stats(q_ptc, q_ctp):
  mount_turned_on = False
  while True:
    if not q_ptc.empty():
      cmd = q_ptc.get()
      if cmd['cmd'] == 'shutdown':
        return
      elif cmd['cmd'] == 'mount_turned_on':
        mount_turned_on = cmd['mount_turned_on']
      else:
        print("In process " + str(inspect.stack()[0][3]) + " - unknown cmd: " + str(cmd['cmd']))

    if not q_ptc.empty():
      continue

    if mount_turned_on == False:
      time.sleep(0.2)
      continue

    try:
      out = requests.get('http://eq1-wifi.embedded/stats', timeout=3)
      if out.status_code == 200:
        last_response_time = time.time()
        telescope_stats = json.loads(out.text)
        connection_ok = True
    except Exception as e:
      connection_ok = False
      telescope_stats = {}
      print(traceback.format_exc())
    d = {
      'connection_ok': connection_ok,
      'telescope_stats': telescope_stats,
    }
    q_ctp.put(d)
    time.sleep(1)


def t_eq5_stats():
  global eq5_stats, last_eq5_response_time, screen, mpd

  eq5_stats = {}
  while kill_thread == False:
    time.sleep(0.3)

    if 'p_eq5_stats' in mpd:
      d = {
        'cmd': 'mount_turned_on',
        'mount_turned_on': screen.turn_on_mount_eq5.isChecked()
      }
      mpd['p_eq5_stats']['ptc'].put(d)

      if screen.turn_on_mount_eq5.isChecked() == False:
        eq5_stats = {}
      if mpd['p_eq5_stats']['ctp'].qsize() == 0:
        continue
      el = mpd['p_eq5_stats']['ctp'].get()
      eq5_stats = el['telescope_stats']
      last_eq5_response_time = time.time()
    else:
      time.sleep(1)
      continue

def p_phd2(q_ptc, q_ctp):
  occurences = 0
  while True:
    if not q_ptc.empty():
      cmd = q_ptc.get()
      if cmd['cmd'] == 'shutdown':
        return
      elif cmd['cmd'] == 'check':
        guiding_work = False
        try:
          list_of_files = glob.glob('/home/dom/PHD2/PHD2_GuideLog*')
          t = time.time()
          file = None
          for i in list_of_files:
            if abs(t - os.path.getmtime(i)) < 30:
              file = i
              break
          if file == None:
            status = "Guiding stopped, PHD not working?"
          else:
            line = subprocess.check_output(['/usr/bin/tail', '-1', file])
            phd_state = line.decode('utf-8').replace('\n', '').split(',')
            f_state = phd_state[-1].replace('"', '')
            if str(f_state) == '0' or str(f_state) == '1':
              status = "Guiding status: OK"
              guiding_work = True
            else:
              status = "Guiding status: " + str(f_state)
        except Exception as e:
          print(traceback.format_exc())
          status = "Internal app error"

        if guiding_work:
          occurences = 0
        else:
          occurences += 1
          print("PHD ERR occurences = " + str(occurences))

        status = status + ',  occurences: ' + str(occurences)

        if cmd['alert'] and not guiding_work and occurences > cmd['occurences']:
          try:
            headers = {"Content-Type": "application/json"}
            payload = {
              "payload": {
                "summary": status,
                "severity": "critical",
                "source": "GUI app"
              },
              "routing_key": cmd['PD_key'],
              "dedup_key": "phd2",
              "event_action": "trigger"
            }
            out = requests.post('https://events.pagerduty.com/v2/enqueue', headers=headers, data=json.dumps(payload))
          except Exception as e:
            print(traceback.format_exc())
        q_ctp.put({'status': status, 'guiding_work': guiding_work})
      else:
        print("In process " + str(inspect.stack()[0][3]) + " - unknown cmd: " + str(cmd['cmd']))
    time.sleep(1)

def t_phd2():
  global mpd, kill_thread, screen, PD_key, phd2_working

  while not kill_thread:
    if not mpd['p_phd2']['ctp'].empty():
      resp = mpd['p_phd2']['ctp'].get()
      screen.lab_phd2_state.setText(str(resp['status']))
      phd2_working = resp['guiding_work']
    if screen.lab_phd2_mon_en.isChecked():
      mpd['p_phd2']['ptc'].put({'cmd': 'check', 'PD_key': PD_key, 'alert': screen.lab_phd2_alert_en.isChecked(), 'occurences': screen.phd2_alert_occurences.value()})
    else:
      screen.lab_phd2_state.setText('OFF')
      phd2_working = None
    time.sleep(5)



###############################################################################################################

if __name__ == '__main__':
  mp.set_start_method('spawn')
  f_make_mpd(p_ping_wifi_devices)
  f_make_mpd(p_indi_getprop_update)
  f_make_mpd(p_indi)
  f_make_mpd(p_filter_wheel_state)
  f_make_mpd(p_phd2)
  f_make_mpd(p_bahtinov_focus_state)
  f_make_mpd(p_eq5_stats)

  for proc in mpd.keys():
    mpd[proc]['p'].start()

###############################################################################################################

  f_restore_settings()
  app = QApplication(sys.argv)
  screen = Window()


  thread_list = []

  t = threading.Thread(target=t_a183mm_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a533mm_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a533mc_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a462mc_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a120mc_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a120mm_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a174mm_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a432mm_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a290mm_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_a120mm_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_a290mm_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_a432mm_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_a174mm_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_a120mc_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_a462mc_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_a183mm_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_a533mc_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_a533mm_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_canon_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_file_to_align_plate_solve_loop)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a462mc_img)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a183mm_img)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a533mc_img)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a533mm_img)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a120mm_img)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a290mm_img)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a432mm_img)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a174mm_img)
  thread_list.append(t)

  t = threading.Thread(target=t_save_a120mc_img)
  thread_list.append(t)

  t = threading.Thread(target=t_requests_canon_send)
  thread_list.append(t)

  t = threading.Thread(target=t_canon_preview)
  thread_list.append(t)

  t = threading.Thread(target=t_canon_frame_processing)
  thread_list.append(t)

  t = threading.Thread(target=t_requests_send_eq6)
  thread_list.append(t)

  t = threading.Thread(target=t_requests_send_eq5)
  thread_list.append(t)

  t = threading.Thread(target=t_eq5_stats)
  thread_list.append(t)

#  t = threading.Thread(target=t_mpd_print)
#  thread_list.append(t)

  t = threading.Thread(target=t_indi_getprop_update)
  thread_list.append(t)

  t = threading.Thread(target=t_process_thread_interaction)
  thread_list.append(t)

  t = threading.Thread(target=t_run_periodic_functions)
  thread_list.append(t)

  t = threading.Thread(target=t_photo_refresh)
  thread_list.append(t)

  t = threading.Thread(target=t_filter_wheel_state)
  thread_list.append(t)

  t = threading.Thread(target=t_phd2)
  thread_list.append(t)

  t = threading.Thread(target=t_bahtinov_focus_state)
  thread_list.append(t)

  t = threading.Thread(target=t_autooff)
  thread_list.append(t)

################################################################################

  for thread in thread_list:
    thread.start()


  screen.showMaximized()
  app.exec_()

  f_save_settings()
  kill_thread = True

  for proc in mpd.keys():
    mpd[proc]['ptc'].put({'cmd': 'shutdown'})

  time.sleep(1)
  for proc in mpd.keys():
    mpd[proc]['p'].terminate()

  for thread in thread_list:
    thread.join()
