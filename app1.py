#!/usr/bin/env python3

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebEngineWidgets import *
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from functools import partial
import sys, requests, threading, time, json, queue, cv2, numpy as np, subprocess, datetime, os
from astropy.coordinates import Angle
from astropy import units as u
from astropy import wcs
from astropy.io import fits
from astropy.coordinates import ICRS
from collections import deque
import tifffile as tiff
from simple_pid import PID
import warnings
import traceback
from astropy.utils.exceptions import AstropyWarning

warnings.simplefilter('ignore', category=AstropyWarning)

kill_thread = False
req_cmd = queue.Queue()
req_canon = queue.Queue()
sterownik_uri = 'http://eq1.embedded'
telescope_stats = {}
screen = None
connection_ok = False
last_response_time = 0.0
filter_reset_done = False

cam_a120mm = None
cam_a120mc = None
cam_a183mm   = None
q_a183mm_raw          = deque(maxlen=2)
q_a183mm_ready        = deque(maxlen=2)
q_a183mm_platesolve   = deque(maxlen=1)
q_a183mm_save_to_file = deque(maxlen=50)
cam_a462mc   = None
q_a462mc_raw          = deque(maxlen=2)
q_a462mc_ready        = deque(maxlen=2)
q_a462mc_platesolve   = deque(maxlen=1)
q_a462mc_save_to_file = deque(maxlen=50)
q_a120mm_save_to_file = deque(maxlen=50)
q_a120mc_save_to_file = deque(maxlen=50)
q_a120mm_ready      = deque(maxlen=2)
q_a120mm_raw        = deque(maxlen=2)
q_a120mm_platesolve = deque(maxlen=1)
q_a120mm_proc_guiding = deque(maxlen=1)
q_a120mc_ready      = deque(maxlen=2)
q_a120mc_raw        = deque(maxlen=2)
q_a120mc_platesolve = deque(maxlen=1)
q_a120mc_proc_guiding = deque(maxlen=1)
q_canon_ready      = deque(maxlen=1)
q_canon_ready_last = deque(maxlen=1)
q_canon_raw        = deque(maxlen=2)
q_canon_platesolve = deque(maxlen=1)

viewer_a120mm_deployed = False
viewer_a120mc_deployed = False
viewer_canon_deployed = False
viewer_a183mm_deployed = False
viewer_a462mc_deployed = False
ra_mode_initial_done = False
run_plate_solve_a120mm = False
run_plate_solve_a120mc = False
run_plate_solve_canon = False
run_plate_solve_a183mm = False
run_plate_solve_a462mc = False
plate_solve_canon_status = 'NULL'
plate_solve_a120mm_status = 'NULL'
plate_solve_a120mc_status = 'NULL'
plate_solve_a183mm_status = 'NULL'
plate_solve_a462mc_status = 'NULL'
plate_solve_results = {}
canon_last_frame = False
canon_last_frame_time = 0.0
meridian_after_launch_done = False
ra_guiding_graph = [0]*500
dec_guiding_graph = [0]*500

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
  'a120mc': {
  },
  'a120mm': {
  }
}


#############################################################################################


def f_requests_send():
  global req_cmd, kill_thread, connection_ok, last_response_time

  while kill_thread == False:
    if not req_cmd.empty():
      payload = req_cmd.get()
      while kill_thread == False:
        try:
          out = requests.post(sterownik_uri, data=json.dumps(payload), timeout=3)
          if out.status_code == 200:
            connection_ok = True
            last_response_time = time.time()
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

def f_get_telescope_stats():
  global telescope_stats, connection_ok, kill_thread, last_response_time

  while kill_thread == False:
    try:
      out = requests.get(sterownik_uri + '/stats', timeout=3)
      if out.status_code == 200:
        connection_ok = True
        last_response_time = time.time()
        telescope_stats = json.loads(out.text)
      else:
        connection_ok = False

    except Exception as e:
      #print(traceback.format_exc())
      connection_ok = False
      time.sleep(0.5)
      pass

    time.sleep(1)

def f_run_periodic_functions():
  global kill_thread, screen

  while kill_thread == False:
    try:
      screen.update_meridian_state()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a183mm_plate_solve_status_refresh()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a462mc_plate_solve_status_refresh()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a120mc_plate_solve_status_refresh()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_a120mm_plate_solve_status_refresh()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_canon_plate_solve_status_refresh()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_ra_natural_refresh()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.print_telescope_position()
    except Exception as e:
      print(traceback.format_exc())
      pass
    try:
      screen.f_update_battery_state()
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
  global kill_thread, screen, q_a120mm_raw, q_a120mc_raw, q_a462mc_raw, viewer_a120mm_deployed, viewer_a462mc_deployed, viewer_a120mc_deployed, q_a183mm_raw, viewer_a183mm_deployed

  while kill_thread == False:
    try:
      if viewer_canon_deployed and screen.t_prawy.currentIndex() == 4:
        screen.f_canon_window_refresh_event()
      if viewer_a120mc_deployed and screen.t_prawy.currentIndex() == 3:
        screen.f_a120mc_window_refresh_event()
      if viewer_a120mm_deployed and screen.t_prawy.currentIndex() == 2:
        screen.f_a120mm_window_refresh_event()
      if viewer_a462mc_deployed and screen.t_prawy.currentIndex() == 1:
        screen.f_a462mc_window_refresh_event()
      if viewer_a183mm_deployed and screen.t_prawy.currentIndex() == 0:
        screen.f_a183mm_window_refresh_event()
    except Exception as e:
      print(traceback.format_exc())
      time.sleep(0.5)
      pass
    time.sleep(0.1)


#############################################################################################

def f_save_a183mm_img():
  global q_a183mm_save_to_file

  while not kill_thread:
    while not q_a183mm_save_to_file and not kill_thread:
      time.sleep(0.1)
    if kill_thread:
      break
    frame = q_a183mm_save_to_file.pop()
    imgdir = os.path.expanduser('~') + '/' + 'zzz_a183mm_autosave_' + frame['dirname']
    if os.path.exists(imgdir) and not os.path.isdir(imgdir):
      print("ERR: " + imgdir + " exists. Can't save there")
      continue

    if not os.path.exists(imgdir):
      os.mkdir(imgdir)

    filename = imgdir + '/raw_' + str(time.time()) + '.png'
    cv2.imwrite(filename, frame['frame16'])

def f_save_a462mc_img():
  global q_a462mc_save_to_file

  while not kill_thread:
    while not q_a462mc_save_to_file and not kill_thread:
      time.sleep(0.1)
    if kill_thread:
      break
    frame = q_a462mc_save_to_file.pop()
    imgdir = os.path.expanduser('~') + '/' + 'zzz_a462mc_autosave_' + frame['dirname']
    if os.path.exists(imgdir) and not os.path.isdir(imgdir):
      print("ERR: " + imgdir + " exists. Can't save there")
      continue

    if not os.path.exists(imgdir):
      os.mkdir(imgdir)

    filename = imgdir + '/raw_' + str(time.time()) + '.png'
    cv2.imwrite(filename, frame['frame16'])


def f_save_a120mm_img():
  global q_a120mm_save_to_file

  while not kill_thread:
    while not q_a120mm_save_to_file and not kill_thread:
      time.sleep(0.1)
    if kill_thread:
      break
    frame = q_a120mm_save_to_file.pop()
    imgdir = os.path.expanduser('~') + '/' 'zzz_a120mm_autosave'
    if os.path.exists(imgdir) and not os.path.isdir(imgdir):
      print("ERR: " + imgdir + " exists. Can't save there")
      continue

    if not os.path.exists(imgdir):
      os.mkdir(imgdir)

    filename = imgdir + '/raw_' + str(time.time()) + '.png'
    cv2.imwrite(filename, frame['frame16'])

def f_save_a120mc_img():
  global q_a120mc_save_to_file

  while not kill_thread:
    while not q_a120mc_save_to_file and not kill_thread:
      time.sleep(0.1)
    if kill_thread:
      break
    frame = q_a120mc_save_to_file.pop()
    imgdir = os.path.expanduser('~') + '/' + 'zzz_a120mc_autosave'
    if os.path.exists(imgdir) and not os.path.isdir(imgdir):
      print("ERR: " + imgdir + " exists. Can't save there")
      continue

    if not os.path.exists(imgdir):
      os.mkdir(imgdir)

    filename = imgdir + '/raw_' + str(time.time()) + '.png'
    cv2.imwrite(filename, frame['frame16'])


#############################################################################################
# czcz

def f_guiding_proc():
  global q_a120mm_proc_guiding, q_a120mc_proc_guiding, kill_thread, screen, ra_guiding_graph, dec_guiding_graph, telescope_stats, req_cmd

  while not kill_thread:
    if not screen.guiding_on_box.isChecked():
      screen.lab_guiding_state.setText('State: OFF')
      if 'a120mm_correction_ra' in telescope_stats and 'a120mm_correction_dec' in telescope_stats:
        if telescope_stats['a120mm_correction_ra'] != 0 or telescope_stats['a120mm_correction_dec'] != 0:
          payload = {
            'mode': 'a120mm_correction',
            'ra':  0,
            'dec': 0,
          }
          req_cmd.put(payload)
      time.sleep(1)
    else:
      screen.lab_guiding_state.setText('State: initializing...')

      if screen.guiding_source.currentText() == '120MC':
        while not q_a120mc_proc_guiding and not kill_thread:
          time.sleep(0.1)
      else:
        while not q_a120mm_proc_guiding and not kill_thread:
          time.sleep(0.1)
      if kill_thread:
        break

      if screen.guiding_source.currentText() == '120MC':
        frame = q_a120mc_proc_guiding.pop()
      else:
        frame = q_a120mm_proc_guiding.pop()

      out = subprocess.check_output(['rm', '-rf', '/dev/shm/guiding_proc'])
      out = subprocess.check_output(['mkdir', '-p', '/dev/shm/guiding_proc'])
      cv2.imwrite('/dev/shm/guiding_proc/frame.png', frame['gray'])

      if screen.guiding_source.currentText() == '120MC':
        scale_lo = str(screen.a120mc_cam_scale_pixel_scale.value()*0.95)
        scale_hi = str(screen.a120mc_cam_scale_pixel_scale.value()*1.05)
      else:
        scale_lo = str(screen.a120mm_cam_scale_pixel_scale.value()*0.95)
        scale_hi = str(screen.a120mm_cam_scale_pixel_scale.value()*1.05)

      platesolve_cmd = [
        'solve-field',
        '--scale-units',
        'arcsecperpix',
        '--scale-low',
        scale_lo,
        '--scale-high',
        scale_hi,
        '--no-plots',
        '--cpulimit',
        '5',
        '--temp-dir',
        '/dev/shm/guiding_proc',
        '/dev/shm/guiding_proc/frame.png'
      ]
      print(platesolve_cmd)

      try:
        out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
        wcsfile = fits.open('/dev/shm/guiding_proc/frame.wcs')
        w = wcs.WCS(wcsfile[0].header)
        coord = wcs.utils.pixel_to_skycoord(500,500,w, mode='wcs').transform_to(ICRS)
        ra = coord.ra.to_string(unit=u.hour,sep=':', precision=0)
        dec = coord.dec.to_string(sep=':', precision=0)
        original_ra = coord.ra
        original_dec = coord.dec
        screen.lab_guiding_state.setText('State: initialized')
      except:
        screen.lab_guiding_state.setText('State: error in ra/dec det')
        print('error in ra/dec determining')
        continue

      ra_pid = PID(screen.guiding_ra_kp.value(), screen.guiding_ra_ki.value(), screen.guiding_ra_kd.value(), setpoint=0)
      dec_pid = PID(screen.guiding_dec_kp.value(), screen.guiding_dec_ki.value(), screen.guiding_dec_kd.value(), setpoint=0)
      ra_pid.output_limits = (-1400,1400)
      dec_pid.output_limits = (-1400,1400)
      ra_guiding_graph = [0]*500
      dec_guiding_graph = [0]*500

      while not kill_thread:
        if not screen.guiding_on_box.isChecked():
          break

        if screen.guiding_source.currentText() == '120MC':
          while not q_a120mc_proc_guiding and not kill_thread:
            time.sleep(0.1)
        else:
          while not q_a120mm_proc_guiding and not kill_thread:
            time.sleep(0.1)
        if kill_thread:
          break

        if screen.guiding_source.currentText() == '120MC':
          frame = q_a120mc_proc_guiding.pop()
        else:
          frame = q_a120mm_proc_guiding.pop()

        out = subprocess.check_output(['rm', '-rf', '/dev/shm/guiding_proc'])
        out = subprocess.check_output(['mkdir', '-p', '/dev/shm/guiding_proc'])
        cv2.imwrite('/dev/shm/guiding_proc/frame.png', frame['gray'])

        platesolve_cmd = [
          'solve-field',
          '--scale-units',
          'arcsecperpix',
          '--scale-low',
          scale_lo,
          '--scale-high',
          scale_hi,
          '--no-plots',
          '--cpulimit',
          '2',
          '--ra',
          ra,
          '--dec',
          dec,
          '--radius',
          '1',
          '--temp-dir',
          '/dev/shm/guiding_proc',
          '/dev/shm/guiding_proc/frame.png'
        ]

        try:
          out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
          wcsfile = fits.open('/dev/shm/guiding_proc/frame.wcs')
          w = wcs.WCS(wcsfile[0].header)
          coord = wcs.utils.pixel_to_skycoord(500,500,w, mode='wcs').transform_to(ICRS)
          curr_ra = coord.ra
          curr_dec = coord.dec
        except:
          payload = {
            'mode': 'a120mm_correction',
            'ra':   0,
            'dec':  0,
          }
          req_cmd.put(payload)
          screen.lab_guiding_state.setText('State: working - calc err')
          print('error in ra/dec determining')
          continue

        diff_ra = original_ra - curr_ra
        diff_dec = original_dec - curr_dec
        diff_ra_sec = diff_ra.degree * 3600
        diff_dec_sec = diff_dec.degree * 3600
        ra_guiding_graph.append(diff_ra_sec)
        dec_guiding_graph.append(diff_dec_sec)
        ra_guiding_graph.pop(0)
        dec_guiding_graph.pop(0)

        if ra_pid.tunings != (screen.guiding_ra_kp.value(), screen.guiding_ra_ki.value(), screen.guiding_ra_kd.value()):
          ra_pid.tunings = (screen.guiding_ra_kp.value(), screen.guiding_ra_ki.value(), screen.guiding_ra_kd.value())

        if dec_pid.tunings != (screen.guiding_dec_kp.value(), screen.guiding_dec_ki.value(), screen.guiding_dec_kd.value()):
          dec_pid.tunings = (screen.guiding_dec_kp.value(), screen.guiding_dec_ki.value(), screen.guiding_dec_kd.value())

        pp, ii, dd = ra_pid.tunings
        pp = round(pp,2)
        ii = round(ii,2)
        dd = round(dd,2)
        screen.lab_ra_pid_params.setText("RA PID = " + str(pp) + ", " + str(ii) + ", " + str(dd))
        pp,ii, dd = dec_pid.tunings
        pp = round(pp,2)
        ii = round(ii,2)
        dd = round(dd,2)
        screen.lab_dec_pid_params.setText("DEC PID = " + str(pp) + ", " + str(ii) + ", " + str(dd))

        screen.guiding_graph_refresh_butt.click()

        ra_signal = ra_pid(float(diff_ra_sec) * 42.66666666666666)
        dec_signal = dec_pid(float(diff_dec_sec) * 28.444444444444444)

        if screen.guiding_dec_on_positive_box.isChecked():
          if int(dec_signal) < 0:
            dec_signal = 0
        else:
          if int(dec_signal) > 0:
            dec_signal = 0

        print(ra_signal)
        payload = {
          'mode': 'a120mm_correction',
          'ra':   int(ra_signal),
          'dec':  int(dec_signal),
        }
        req_cmd.put(payload)
        screen.lab_guiding_state.setText('State: working | corr ra = ' + str(telescope_stats['a120mm_correction_ra']) + ' dec = ' + str(telescope_stats['a120mm_correction_dec']))



#############################################################################################

def f_a183mm_plate_solve_loop():
  global q_a183mm_platesolve, kill_thread, run_plate_solve_a183mm, plate_solve_a183mm_status, plate_solve_results
  global screen

  while not kill_thread:
    if run_plate_solve_a183mm:
      if not 'position' in telescope_stats.keys():
        run_plate_solve_a183mm = False
        continue
      plate_solve_a183mm_status = 'WAITING FOR FRAME...'
      while not q_a183mm_platesolve and not kill_thread:
        time.sleep(0.1)

      run_plate_solve_a183mm = False
      frame = q_a183mm_platesolve.pop()
      out = subprocess.check_output(['rm', '-rf', '/dev/shm/a183mm_platesolve'])
      out = subprocess.check_output(['mkdir', '-p', '/dev/shm/a183mm_platesolve'])
      cv2.imwrite('/dev/shm/a183mm_platesolve/frame.png', frame['gray'])

      platesolve_cmd = [
        'solve-field',
        '--scale-units',
        'arcsecperpix',
        '--scale-low',
        str(screen.a183mm_cam_scale_pixel_scale.value() - 0.01),
        '--scale-high',
        str(screen.a183mm_cam_scale_pixel_scale.value() + 0.01),
        '--no-plots',
        '--downsample',
        '2',
        '--ra',
        Angle(telescope_stats['position']['ra']).to_string(sep=':', precision=0),
        '--dec',
        Angle(telescope_stats['position']['dec']).to_string(sep=':', precision=0),
        '--radius',
        '2',
        '--temp-dir',
        '/dev/shm/a183mm_platesolve',
        '/dev/shm/a183mm_platesolve/frame.png'
      ]
      try:
        plate_solve_a183mm_status = 'SOLVING...'
        out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
        out = subprocess.check_output(['wcsinfo', '/dev/shm/a183mm_platesolve/frame.wcs'])
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
        wcsfile = fits.open('/dev/shm/a183mm_platesolve/frame.wcs')
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

        homedir = os.path.expanduser("~")
        plotann_arr = [
          'plotann.py',
          '/dev/shm/a183mm_platesolve/frame.wcs',
          '/dev/shm/a183mm_platesolve/frame.png',
          '/dev/shm/a183mm_platesolve/frame_hdcat.png',
          '--hdcat=/home/dom/GIT/puppet/astro_gui/hd.fits',
          '--grid-size=0.01',
          '--grid-label=0.01',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['hdcat'] = cv2.imread('/dev/shm/a183mm_platesolve/frame_hdcat.png')

        plotann_arr = [
          'plotann.py',
          '/dev/shm/a183mm_platesolve/frame.wcs',
          '/dev/shm/a183mm_platesolve/frame.png',
          '/dev/shm/a183mm_platesolve/frame_tycho2cat.png',
          '--tycho2cat=/home/dom/GIT/puppet/astro_gui/tycho2.kd',
          '--grid-size=0.01',
          '--grid-label=0.01',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['tycho2cat'] = cv2.imread('/dev/shm/a183mm_platesolve/frame_tycho2cat.png')
        plate_solve_a183mm_status = 'DONE at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        screen.f_solved_tabs_refresh_event()
      except:
        plate_solve_a183mm_status = 'FAILED at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        pass
    else:
      time.sleep(0.5)

def f_a462mc_plate_solve_loop():
  global q_a462mc_platesolve, kill_thread, run_plate_solve_a462mc, plate_solve_a462mc_status, plate_solve_results
  global screen

  while not kill_thread:
    if run_plate_solve_a462mc:
      if not 'position' in telescope_stats.keys():
        run_plate_solve_a462mc = False
        continue
      plate_solve_a462mc_status = 'WAITING FOR FRAME...'
      while not q_a462mc_platesolve and not kill_thread:
        time.sleep(0.1)

      run_plate_solve_a462mc = False
      frame = q_a462mc_platesolve.pop()
      out = subprocess.check_output(['rm', '-rf', '/dev/shm/a462mc_platesolve'])
      out = subprocess.check_output(['mkdir', '-p', '/dev/shm/a462mc_platesolve'])
      cv2.imwrite('/dev/shm/a462mc_platesolve/frame.png', frame['gray'])

      platesolve_cmd = [
        'solve-field',
        '--scale-units',
        'arcsecperpix',
        '--scale-low',
        str(screen.a462mc_cam_scale_pixel_scale.value() - 0.01),
        '--scale-high',
        str(screen.a462mc_cam_scale_pixel_scale.value() + 0.01),
        '--no-plots',
        '--downsample',
        '2',
        '--ra',
        Angle(telescope_stats['position']['ra']).to_string(sep=':', precision=0),
        '--dec',
        Angle(telescope_stats['position']['dec']).to_string(sep=':', precision=0),
        '--radius',
        '2',
        '--temp-dir',
        '/dev/shm/a462mc_platesolve',
        '/dev/shm/a462mc_platesolve/frame.png'
      ]
      try:
        plate_solve_a462mc_status = 'SOLVING...'
        out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
        out = subprocess.check_output(['wcsinfo', '/dev/shm/a462mc_platesolve/frame.wcs'])
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
        wcsfile = fits.open('/dev/shm/a462mc_platesolve/frame.wcs')
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

        homedir = os.path.expanduser("~")
        plotann_arr = [
          'plotann.py',
          '/dev/shm/a462mc_platesolve/frame.wcs',
          '/dev/shm/a462mc_platesolve/frame.png',
          '/dev/shm/a462mc_platesolve/frame_hdcat.png',
          '--hdcat=/home/dom/GIT/puppet/astro_gui/hd.fits',
          '--grid-size=0.01',
          '--grid-label=0.01',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['hdcat'] = cv2.imread('/dev/shm/a462mc_platesolve/frame_hdcat.png')

        plotann_arr = [
          'plotann.py',
          '/dev/shm/a462mc_platesolve/frame.wcs',
          '/dev/shm/a462mc_platesolve/frame.png',
          '/dev/shm/a462mc_platesolve/frame_tycho2cat.png',
          '--tycho2cat=/home/dom/GIT/puppet/astro_gui/tycho2.kd',
          '--grid-size=0.01',
          '--grid-label=0.01',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['tycho2cat'] = cv2.imread('/dev/shm/a462mc_platesolve/frame_tycho2cat.png')
        plate_solve_a462mc_status = 'DONE at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        screen.f_solved_tabs_refresh_event()
      except:
        plate_solve_a462mc_status = 'FAILED at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        pass
    else:
      time.sleep(0.5)


def f_a120mc_plate_solve_loop():
  global q_a120mc_platesolve, kill_thread, run_plate_solve_a120mc, plate_solve_a120mc_status, plate_solve_results
  global screen

  while not kill_thread:
    if run_plate_solve_a120mc:
      plate_solve_a120mc_status = 'WAITING FOR FRAME...'
      while not q_a120mc_platesolve and not kill_thread:
        time.sleep(0.1)

      run_plate_solve_a120mc = False
      frame = q_a120mc_platesolve.pop()
      out = subprocess.check_output(['rm', '-rf', '/dev/shm/a120mc_platesolve'])
      out = subprocess.check_output(['mkdir', '-p', '/dev/shm/a120mc_platesolve'])
      cv2.imwrite('/dev/shm/a120mc_platesolve/frame.png', frame['gray'])
      platesolve_cmd = [
        'solve-field',
        '--scale-units',
        'arcsecperpix',
        '--scale-low',
        str(screen.a120mc_cam_scale_pixel_scale.value() - screen.a120mc_cam_scale_pixel_scale.value()*0.2),
        '--scale-high',
        str(screen.a120mc_cam_scale_pixel_scale.value() + screen.a120mc_cam_scale_pixel_scale.value()*0.2),
        '--no-plots',
        '--downsample',
        '2',
        '--cpulimit',
        '5',
        '--temp-dir',
        '/dev/shm/a120mc_platesolve',
        '/dev/shm/a120mc_platesolve/frame.png'
      ]
      try:
        plate_solve_a120mc_status = 'SOLVING...'
        out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
        out = subprocess.check_output(['wcsinfo', '/dev/shm/a120mc_platesolve/frame.wcs'])
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
        wcsfile = fits.open('/dev/shm/a120mc_platesolve/frame.wcs')
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

        homedir = os.path.expanduser("~")
        plotann_arr = [
          'plotann.py',
          '/dev/shm/a120mc_platesolve/frame.wcs',
          '/dev/shm/a120mc_platesolve/frame.png',
          '/dev/shm/a120mc_platesolve/frame_hdcat.png',
          '--hdcat=/home/dom/GIT/puppet/astro_gui/hd.fits',
          '--grid-size=0.1',
          '--grid-label=0.1',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['hdcat'] = cv2.imread('/dev/shm/a120mc_platesolve/frame_hdcat.png')

        plotann_arr = [
          'plotann.py',
          '/dev/shm/a120mc_platesolve/frame.wcs',
          '/dev/shm/a120mc_platesolve/frame.png',
          '/dev/shm/a120mc_platesolve/frame_tycho2cat.png',
          '--tycho2cat=/home/dom/GIT/puppet/astro_gui/tycho2.kd',
          '--grid-size=0.1',
          '--grid-label=0.1',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['tycho2cat'] = cv2.imread('/dev/shm/a120mc_platesolve/frame_tycho2cat.png')
        plate_solve_a120mc_status = 'DONE at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        screen.f_solved_tabs_refresh_event()
      except:
        plate_solve_a120mc_status = 'FAILED at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        pass
    else:
      time.sleep(0.5)


def f_a120mm_plate_solve_loop():
  global q_a120mm_platesolve, kill_thread, run_plate_solve_a120mm, plate_solve_a120mm_status, plate_solve_results
  global screen

  while not kill_thread:
    if run_plate_solve_a120mm:
      plate_solve_a120mm_status = 'WAITING FOR FRAME...'
      while not q_a120mm_platesolve and not kill_thread:
        time.sleep(0.1)

      run_plate_solve_a120mm = False
      frame = q_a120mm_platesolve.pop()
      out = subprocess.check_output(['rm', '-rf', '/dev/shm/a120mm_platesolve'])
      out = subprocess.check_output(['mkdir', '-p', '/dev/shm/a120mm_platesolve'])
      cv2.imwrite('/dev/shm/a120mm_platesolve/frame.png', frame['gray'])
      platesolve_cmd = [
        'solve-field',
        '--scale-units',
        'arcsecperpix',
        '--scale-low',
        str(screen.a120mm_cam_scale_pixel_scale.value() - screen.a120mm_cam_scale_pixel_scale.value()*0.2),
        '--scale-high',
        str(screen.a120mm_cam_scale_pixel_scale.value() + screen.a120mm_cam_scale_pixel_scale.value()*0.2),
        '--no-plots',
        '--downsample',
        '2',
        '--cpulimit',
        '5',
        '--temp-dir',
        '/dev/shm/a120mm_platesolve',
        '/dev/shm/a120mm_platesolve/frame.png'
      ]
      try:
        plate_solve_a120mm_status = 'SOLVING...'
        out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
        out = subprocess.check_output(['wcsinfo', '/dev/shm/a120mm_platesolve/frame.wcs'])
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
        wcsfile = fits.open('/dev/shm/a120mm_platesolve/frame.wcs')
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

        homedir = os.path.expanduser("~")
        plotann_arr = [
          'plotann.py',
          '/dev/shm/a120mm_platesolve/frame.wcs',
          '/dev/shm/a120mm_platesolve/frame.png',
          '/dev/shm/a120mm_platesolve/frame_hdcat.png',
          '--hdcat=/home/dom/GIT/puppet/astro_gui/hd.fits',
          '--grid-size=0.05',
          '--grid-label=0.05',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['hdcat'] = cv2.imread('/dev/shm/a120mm_platesolve/frame_hdcat.png')

        plotann_arr = [
          'plotann.py',
          '/dev/shm/a120mm_platesolve/frame.wcs',
          '/dev/shm/a120mm_platesolve/frame.png',
          '/dev/shm/a120mm_platesolve/frame_tycho2cat.png',
          '--tycho2cat=/home/dom/GIT/puppet/astro_gui/tycho2.kd',
          '--grid-size=0.05',
          '--grid-label=0.05',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['tycho2cat'] = cv2.imread('/dev/shm/a120mm_platesolve/frame_tycho2cat.png')
        plate_solve_a120mm_status = 'DONE at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        screen.f_solved_tabs_refresh_event()
      except:
        plate_solve_a120mm_status = 'FAILED at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        pass
    else:
      time.sleep(0.5)

def f_canon_plate_solve_loop():
  global q_canon_platesolve, kill_thread, run_plate_solve_canon, plate_solve_canon_status, plate_solve_results
  global screen

  while not kill_thread:
    if run_plate_solve_canon:
      plate_solve_canon_status = 'WAITING FOR FRAME...'
      while not q_canon_platesolve and not kill_thread:
        time.sleep(0.1)

      run_plate_solve_canon = False
      frame = q_canon_platesolve.pop()
      out = subprocess.check_output(['rm', '-rf', '/dev/shm/canon_platesolve'])
      out = subprocess.check_output(['mkdir', '-p', '/dev/shm/canon_platesolve'])
      cv2.imwrite('/dev/shm/canon_platesolve/frame.png', frame['gray'])
      platesolve_cmd = [
        'solve-field',
        '--scale-units',
        'arcsecperpix',
        '--scale-low',
        str(screen.canon_scale_pixel_scale.value() - screen.canon_scale_pixel_scale.value()*0.2),
        '--scale-high',
        str(screen.canon_scale_pixel_scale.value() + screen.canon_scale_pixel_scale.value()*0.2),
        '--no-plots',
        '--downsample',
        '4',
        '--cpulimit',
        '10',
        '--temp-dir',
        '/dev/shm/canon_platesolve',
        '/dev/shm/canon_platesolve/frame.png'
      ]
      try:
        plate_solve_canon_status = 'SOLVING...'
        out = subprocess.check_output(platesolve_cmd, stderr=subprocess.STDOUT)
        out = subprocess.check_output(['wcsinfo', '/dev/shm/canon_platesolve/frame.wcs'])
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
        wcsfile = fits.open('/dev/shm/canon_platesolve/frame.wcs')
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

        homedir = os.path.expanduser("~")
        plotann_arr = [
          'plotann.py',
          '/dev/shm/canon_platesolve/frame.wcs',
          '/dev/shm/canon_platesolve/frame.png',
          '/dev/shm/canon_platesolve/frame_hdcat.png',
          '--hdcat=/home/dom/GIT/puppet/astro_gui/hd.fits',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['hdcat'] = cv2.imread('/dev/shm/canon_platesolve/frame_hdcat.png')

        plotann_arr = [
          'plotann.py',
          '/dev/shm/canon_platesolve/frame.wcs',
          '/dev/shm/canon_platesolve/frame.png',
          '/dev/shm/canon_platesolve/frame_tycho2cat.png',
          '--tycho2cat=/home/dom/GIT/puppet/astro_gui/tycho2.kd',
        ]
        out = subprocess.check_output(plotann_arr)
        plate_solve_results['tycho2cat'] = cv2.imread('/dev/shm/canon_platesolve/frame_tycho2cat.png')
        plate_solve_canon_status = 'DONE at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        screen.f_solved_tabs_refresh_event()
      except:
        plate_solve_canon_status = 'FAILED at ' + str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        pass
    else:
      time.sleep(0.5)

#############################################################################################

def f_camera_params(cam_name, method):
  global cam_settings, screen, kill_thread

  if method == 'initial':
    if cam_name == 'a183mm':
      uri = 'http://127.0.0.2:8003/settings'
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
    elif cam_name == 'a462mc':
      screen.f_a462mc_cam_update_values(load_slider=True)
    elif cam_name == 'a120mm':
      screen.f_a120mm_cam_update_values(load_slider=True)
    elif cam_name == 'a120mc':
      screen.f_a120mc_cam_update_values(load_slider=True)

  elif method == 'send_params_to_cam':
    if cam_name == 'a183mm':
      uri = 'http://127.0.0.2:8003/set_settings'
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

def f_a183mm_frame_processing():
  global q_a183mm_raw, q_a183mm_ready, q_a183mm_platesolve

  while kill_thread == False:
    while kill_thread == False and not q_a183mm_raw:
      time.sleep(0.1)
    if kill_thread:
      break
    raw_frame = q_a183mm_raw.pop()
    ready_frame = {
      'time': raw_frame['time']
    }
    ready_frame['frame16'] = cv2.cvtColor(raw_frame['raw_data'], cv2.COLOR_GRAY2RGB)
    ready_frame['frameRGB'] = (ready_frame['frame16']/256).astype('uint8')
    ready_frame['gray'] = cv2.cvtColor(ready_frame['frameRGB'], cv2.COLOR_RGB2GRAY)

    q_a183mm_ready.append(ready_frame)
    q_a183mm_platesolve.append(ready_frame)

def f_a462mc_frame_processing():
  global q_a462mc_raw, q_a462mc_ready, q_a462mc_platesolve

  while kill_thread == False:
    while kill_thread == False and not q_a462mc_raw:
      time.sleep(0.1)
    if kill_thread:
      break
    raw_frame = q_a462mc_raw.pop()
    ready_frame = {
      'time': raw_frame['time']
    }
    ready_frame['frame16'] = cv2.cvtColor(raw_frame['raw_data'], cv2.COLOR_BAYER_RG2RGB)
    ready_frame['frameRGB'] = (ready_frame['frame16']/256).astype('uint8')
    ready_frame['gray'] = cv2.cvtColor(ready_frame['frameRGB'], cv2.COLOR_RGB2GRAY)

    q_a462mc_ready.append(ready_frame)
    q_a462mc_platesolve.append(ready_frame)

def f_a120mc_frame_processing():
  global q_a120mc_raw, q_a120mc_ready, q_a120mc_platesolve, q_a120mc_proc_guiding

  while kill_thread == False:
    while kill_thread == False and not q_a120mc_raw:
      time.sleep(0.1)
    if kill_thread:
      break
    raw_frame = q_a120mc_raw.pop()
    ready_frame = {
      'time': raw_frame['time']
    }
    ready_frame['frame16'] = cv2.cvtColor(raw_frame['raw_data'], cv2.COLOR_BAYER_GR2RGB)
#    ready_frame['frame16'] = cv2.cvtColor(raw_frame['raw_data'], cv2.COLOR_GRAY2RGB)
    ready_frame['frameRGB'] = (ready_frame['frame16']/256).astype('uint8')
    ready_frame['gray'] = cv2.cvtColor(ready_frame['frameRGB'], cv2.COLOR_RGB2GRAY)

    q_a120mc_ready.append(ready_frame)
    q_a120mc_platesolve.append(ready_frame)
    q_a120mc_proc_guiding.append(ready_frame)

def f_a120mm_frame_processing():
  global q_a120mm_raw, q_a120mm_ready, q_a120mm_platesolve, q_a120mm_proc_guiding

  while kill_thread == False:
    while kill_thread == False and not q_a120mm_raw:
      time.sleep(0.1)
    if kill_thread:
      break
    raw_frame = q_a120mm_raw.pop()
    ready_frame = {
      'time': raw_frame['time']
    }
    ready_frame['frame16'] = cv2.cvtColor(raw_frame['raw_data'], cv2.COLOR_GRAY2RGB)
#    ready_frame['frame16'] = cv2.cvtColor(raw_frame['raw_data'], cv2.COLOR_BAYER_GR2RGB)
    ready_frame['frameRGB'] = (ready_frame['frame16']/256).astype('uint8')
    ready_frame['gray'] = cv2.cvtColor(ready_frame['frameRGB'], cv2.COLOR_RGB2GRAY)

    q_a120mm_ready.append(ready_frame)
    q_a120mm_platesolve.append(ready_frame)
    q_a120mm_proc_guiding.append(ready_frame)

def f_canon_frame_processing():
  global q_canon_raw, q_canon_ready, q_canon_platesolve

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
    self.lewy_tab10 = QWidget()
    self.t_lewy.addTab(self.lewy_tab1, "POSITION")
    self.t_lewy.addTab(self.lewy_tab2, "183MM")
    self.t_lewy.addTab(self.lewy_tab3, "462MC")
    self.t_lewy.addTab(self.lewy_tab4, "120MM")
    self.t_lewy.addTab(self.lewy_tab5, "120MC")
    self.t_lewy.addTab(self.lewy_tab6, "CANON 20D")
    self.t_lewy.addTab(self.lewy_tab7, "MISC")
    self.t_lewy.addTab(self.lewy_tab8, "BATTERY")
    self.t_lewy.addTab(self.lewy_tab9, "FILTERS")
    self.t_lewy.addTab(self.lewy_tab10, "GUIDING")

    #self.lewy_tab1.setStyleSheet("background-color: red;")
    #self.lewy_tab2.setStyleSheet("background-color: yellow;")
    #self.lewy_tab3.setStyleSheet("background-color: pink;")


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
    self.t_prawy.addTab(self.prawy_tab1, "183MM cam")
    self.t_prawy.addTab(self.prawy_tab2, "462MC cam")
    self.t_prawy.addTab(self.prawy_tab3, "120MM cam")
    self.t_prawy.addTab(self.prawy_tab4, "120MC cam")
    self.t_prawy.addTab(self.prawy_tab5, "CANON 20D")
    self.t_prawy.addTab(self.prawy_tab6, "TYCHO2 solved")
    self.t_prawy.addTab(self.prawy_tab7, "HD solved")
    self.t_prawy.addTab(self.prawy_tab8, "SKY MAP")

#    self.prawy_tab1.setStyleSheet("background-color: green;")
#    self.prawy_tab2.setStyleSheet("background-color: gray;")
#    self.prawy_tab3.setStyleSheet("background-color: purple;")


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
    self.tab10_lewyUI()
    self.tab_1_prawyUI()
    self.tab_2_prawyUI()
    self.tab_3_prawyUI()
    self.tab_4_prawyUI()
    self.tab_5_prawyUI()
    self.tab_6_prawyUI()
    self.tab_7_prawyUI()
    self.tab_8_prawyUI()

#############################################################################################

  def tab1_lewyUI(self):

    self.headline = QFont('SansSerif', 11, QFont.Bold)


    self.lab_radec_move = QLabel("RA/DEC")
    self.lab_radec_move.setFont(self.headline)
    self.lab_radec_move.setAlignment(Qt.AlignCenter)

    self.ra_slider = QSlider(Qt.Horizontal)
    self.ra_slider.setTickPosition(QSlider.TicksBothSides)
    self.ra_slider.setMinimum(-100)
    self.ra_slider.setMaximum(100)
    self.ra_slider.setTickInterval(20)
    self.ra_slider.setSliderPosition(0)
    self.ra_slider.sliderReleased.connect(partial(self.slider_center, 'ra'))
    self.ra_slider.valueChanged.connect(self.f_ra_slider)
    self.ra_slider.setMinimumWidth(200)
    self.ra_slider.setMaximumWidth(200)

    self.dec_slider = QSlider(Qt.Vertical)
    self.dec_slider.setTickPosition(QSlider.TicksBothSides)
    self.dec_slider.setMinimum(-100)
    self.dec_slider.setMaximum(100)
    self.dec_slider.setTickInterval(20)
    self.dec_slider.setSliderPosition(0)
    self.dec_slider.sliderReleased.connect(partial(self.slider_center, 'dec'))
    self.dec_slider.valueChanged.connect(self.f_dec_slider)
    self.dec_slider.setMinimumHeight(200)
    self.dec_slider.setMaximumHeight(200)

    self.ost_lat = QLabel("FOCUS")
    self.ost_lat.setFont(self.headline)
    self.ost_lat.setAlignment(Qt.AlignCenter)

    self.ra_mode_label = QLabel("RA Natural")
    self.ra_mode_label.setFont(self.headline)

    self.ra_mode = QComboBox()
    self.ra_mode.addItems(['OFF', 'STAR', 'SUN', 'MOON'])
    self.ra_mode.setEditable = False
    self.ra_mode.currentIndexChanged.connect(self.f_ra_natural)

    self.ra_mode_status = QLabel("RA natural status: NULL")

    self.ost_slider = QSlider(Qt.Horizontal)
    self.ost_slider.setTickPosition(QSlider.TicksBothSides)
    self.ost_slider.setMinimum(-100)
    self.ost_slider.setMaximum(100)
    self.ost_slider.setTickInterval(20)
    self.ost_slider.setSliderPosition(0)
    self.ost_slider.sliderReleased.connect(partial(self.slider_center, 'ost'))
    self.ost_slider.valueChanged.connect(self.f_ost_slider)
    self.ost_slider.setMinimumWidth(200)
    self.ost_slider.setMaximumWidth(200)


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


    self.ra_input = QLabel("RA")
    self.ra_input.setFont(self.headline)
    self.ra_input.setAlignment(Qt.AlignCenter)
    self.ra_h1 = QSpinBox(self)
    self.ra_h1.setValue(0)
    self.ra_h1.setMinimum(0)
    self.ra_h1.setMaximum(24)
    self.ra_m1 = QSpinBox(self)
    self.ra_m1.setValue(0)
    self.ra_m1.setMinimum(0)
    self.ra_m1.setMaximum(59)
    self.ra_s1 = QSpinBox(self)
    self.ra_s1.setValue(0)
    self.ra_s1.setMinimum(0)
    self.ra_s1.setMaximum(59)

    self.dec_input = QLabel("DEC")
    self.dec_input.setFont(self.headline)
    self.dec_input.setAlignment(Qt.AlignCenter)
    self.dec_sign1 = QSpinBox(self)
    self.dec_sign1.setValue(1)
    self.dec_sign1.setMinimum(-1)
    self.dec_sign1.setMaximum(1)
    self.dec_d1 = QSpinBox(self)
    self.dec_d1.setValue(0)
    self.dec_d1.setMinimum(0)
    self.dec_d1.setMaximum(179)
    self.dec_m1 = QSpinBox(self)
    self.dec_m1.setValue(0)
    self.dec_m1.setMinimum(0)
    self.dec_m1.setMaximum(59)
    self.dec_s1 = QSpinBox(self)
    self.dec_s1.setValue(0)
    self.dec_s1.setMinimum(0)
    self.dec_s1.setMaximum(59)

    self.move_to_obj_lab = QLabel("Move to object")
    self.move_to_obj_lab.setFont(self.headline)
    self.move_to_obj_lab.setAlignment(Qt.AlignCenter)
    self.radec_button = QPushButton('GO', self)
    self.radec_button.setToolTip('Set telescope to desired position')
    self.radec_button.clicked.connect(self.radec_move)

    self.obj_name = QLineEdit(self)
    self.obj_name_button_find = QPushButton('FIND', self)
    self.obj_name_button_find.clicked.connect(self.goto_object_find)
    find_button_width = self.obj_name_button_find.fontMetrics().boundingRect('FIND').width() + 12
    self.obj_name_button_find.setMaximumWidth(find_button_width)
    self.obj_name_button_set = QPushButton('SET', self)
    self.obj_name_button_set.clicked.connect(self.goto_object_set)
    set_button_width = self.obj_name_button_set.fontMetrics().boundingRect('SET').width() + 12
    self.obj_name_button_set.setMaximumWidth(set_button_width)
    self.obj_name_button_go = QPushButton('GO', self)
    self.obj_name_button_go.clicked.connect(self.goto_object_go)
    go_button_width = self.obj_name_button_go.fontMetrics().boundingRect('GO').width() + 12
    self.obj_name_button_go.setMaximumWidth(go_button_width)
    self.obj_name_goto_info1 = QLabel("NULL")
    self.obj_name_goto_info2 = QLabel("NULL")

    self.az_input = QLabel("Azimuth")
    self.az_input.setFont(self.headline)
    self.az_input.setAlignment(Qt.AlignCenter)
    self.az_d1 = QSpinBox(self)
    self.az_d1.setValue(0)
    self.az_d1.setMinimum(0)
    self.az_d1.setMaximum(359)
    self.az_m1 = QSpinBox(self)
    self.az_m1.setValue(0)
    self.az_m1.setMinimum(0)
    self.az_m1.setMaximum(59)

    self.elev_input = QLabel("Elevation")
    self.elev_input.setFont(self.headline)
    self.elev_input.setAlignment(Qt.AlignCenter)
    self.elev_d1 = QSpinBox(self)
    self.elev_d1.setValue(0)
    self.elev_d1.setMinimum(0)
    self.elev_d1.setMaximum(89)
    self.elev_m1 = QSpinBox(self)
    self.elev_m1.setValue(0)
    self.elev_m1.setMinimum(0)
    self.elev_m1.setMaximum(59)

    self.altaz_button = QPushButton('GO', self)
    self.altaz_button.setToolTip('Set telescope to desired position')
    self.altaz_button.clicked.connect(self.altaz_move)

    self.get_telescope_position_tab1_button = QPushButton('Get telescope position', self)
    self.get_telescope_position_tab1_button.setToolTip('Get current telescope position')
    self.get_telescope_position_tab1_button.clicked.connect(self.get_telescope_position_tab1)

    self.act_pos_1 = QLabel("Position received from telescope")
    self.act_pos_1.setFont(self.headline)

    self.radec_position1 = QLabel("00H 00m 00s")
    self.altaz_position1 = QLabel("00D 00m 00s")
    self.conn_state1 = QLabel("Conn state: NULL")
    self.goto_state1 = QLabel("GOTO moving: NULL")

    self.joystick_label = QLabel("Move RA/DEC by arc min")
    self.joystick_label.setFont(self.headline)

    self.joystick_up_button = QToolButton()
    self.joystick_up_button.setArrowType(QtCore.Qt.UpArrow)
    self.joystick_up_button.clicked.connect(self.joystick_up)

    self.joystick_down_button = QToolButton()
    self.joystick_down_button.setArrowType(QtCore.Qt.DownArrow)
    self.joystick_down_button.clicked.connect(self.joystick_down)

    self.joystick_left_button = QToolButton()
    self.joystick_left_button.setArrowType(QtCore.Qt.LeftArrow)
    self.joystick_left_button.clicked.connect(self.joystick_left)

    self.joystick_right_button = QToolButton()
    self.joystick_right_button.setArrowType(QtCore.Qt.RightArrow)
    self.joystick_right_button.clicked.connect(self.joystick_right)

    self.joystick_arc = QLineEdit(self)
    self.joystick_arc.setValidator(QRegExpValidator(QRegExp("\d{1,3}.\d")))
    self.joystick_arc.setText('00')
    self.joystick_arc.setFixedWidth(70)

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

    layout.addWidget(self.lab_radec_move)

    sliders_layout = QHBoxLayout()
    sliders_layout.addWidget(self.dec_slider)
    sliders_layout2 = QVBoxLayout()
    sliders_layout2.addWidget(self.ra_slider)
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

    layout.addWidget(separator2)

    ra_mode_layout = QHBoxLayout()
    ra_mode_layout.addWidget(self.ra_mode_label)
    ra_mode_layout.addWidget(self.ra_mode)
    layout.addLayout(ra_mode_layout)
    layout.addWidget(self.ra_mode_status)

    layout.addWidget(separator7)

    whole_ra_input_layout = QVBoxLayout()
    ra_input_layout = QHBoxLayout()
    ra_input_layout.addWidget(self.ra_input)
    ra_input_layout.addWidget(self.ra_h1)
    ra_input_layout.addWidget(QLabel("H"))
    ra_input_layout.addWidget(self.ra_m1)
    ra_input_layout.addWidget(QLabel("m"))
    ra_input_layout.addWidget(self.ra_s1)
    ra_input_layout.addWidget(QLabel("s"))
    whole_ra_input_layout.addLayout(ra_input_layout)
    layout.addLayout(whole_ra_input_layout)

    whole_dec_input_layout = QVBoxLayout()
    dec_input_layout = QHBoxLayout()
    dec_input_layout.addWidget(self.dec_input)
    dec_input_layout.addWidget(self.dec_sign1)
    dec_input_layout.addWidget(self.dec_d1)
    dec_input_layout.addWidget(QLabel("D"))
    dec_input_layout.addWidget(self.dec_m1)
    dec_input_layout.addWidget(QLabel("m"))
    dec_input_layout.addWidget(self.dec_s1)
    dec_input_layout.addWidget(QLabel("s"))
    whole_dec_input_layout.addLayout(dec_input_layout)
    whole_dec_input_layout.addWidget(self.radec_button)
    layout.addLayout(whole_dec_input_layout)

    layout.addWidget(separator3)

    whole_obj_input_layout = QVBoxLayout()
    whole_obj_input_layout.addWidget(self.move_to_obj_lab)
    obj_input_layout = QHBoxLayout()
    obj_input_layout.addWidget(self.obj_name)
    obj_input_layout.addWidget(self.obj_name_button_find)
    obj_input_layout.addWidget(self.obj_name_button_set)
    obj_input_layout.addWidget(self.obj_name_button_go)
    whole_obj_input_layout.addLayout(obj_input_layout)
    layout.addLayout(whole_obj_input_layout)
    layout.addWidget(self.obj_name_goto_info1)
    layout.addWidget(self.obj_name_goto_info2)

    layout.addWidget(separator4)

    whole_az_input_layout = QVBoxLayout()
    az_input_layout = QHBoxLayout()
    az_input_layout.addWidget(self.az_input)
    az_input_layout.addWidget(self.az_d1)
    az_input_layout.addWidget(QLabel("D"))
    az_input_layout.addWidget(self.az_m1)
    az_input_layout.addWidget(QLabel("m"))
    whole_az_input_layout.addLayout(az_input_layout)
    layout.addLayout(whole_az_input_layout)

    whole_elev_input_layout = QVBoxLayout()
    elev_input_layout = QHBoxLayout()
    elev_input_layout.addWidget(self.elev_input)
    elev_input_layout.addWidget(self.elev_d1)
    elev_input_layout.addWidget(QLabel("D"))
    elev_input_layout.addWidget(self.elev_m1)
    elev_input_layout.addWidget(QLabel("m"))
    whole_elev_input_layout.addLayout(elev_input_layout)
    whole_elev_input_layout.addWidget(self.altaz_button)
    layout.addLayout(whole_elev_input_layout)

    layout.addWidget(separator5)

    layout.addWidget(self.get_telescope_position_tab1_button)

    layout.addWidget(separator6)

    layout.addWidget(self.joystick_label, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.joystick_up_button, alignment=QtCore.Qt.AlignCenter)
    j_lr_layout = QHBoxLayout()
    j_lr_layout.addWidget(self.joystick_left_button, alignment=QtCore.Qt.AlignCenter)
    j_lr_layout.addWidget(self.joystick_arc, alignment=QtCore.Qt.AlignCenter)
    j_lr_layout.addWidget(self.joystick_right_button, alignment=QtCore.Qt.AlignCenter)
    layout.addLayout(j_lr_layout)
    layout.addWidget(self.joystick_down_button, alignment=QtCore.Qt.AlignCenter)

    layout.addWidget(self.act_pos_1, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.radec_position1)
    layout.addWidget(self.altaz_position1)
    layout.addWidget(self.conn_state1)
    layout.addWidget(self.goto_state1)


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
    self.lab_a183mm_plate_solve_change = QLabel("Last change: NULL")
    self.lab_a183mm_plate_solve_change_t = QLabel("NULL")

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
    layout.addWidget(self.lab_a183mm_plate_solve_change)
    layout.addWidget(self.lab_a183mm_plate_solve_change_t)
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
    self.lab_a462mc_plate_solve_change = QLabel("Last change: NULL")
    self.lab_a462mc_plate_solve_change_t = QLabel("NULL")

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
    layout.addWidget(self.lab_a462mc_plate_solve_change)
    layout.addWidget(self.lab_a462mc_plate_solve_change_t)
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
    layout.addWidget(self.graphWidget_a462mc)

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

    self.a120mm_cam_cross = QCheckBox()
    self.a120mm_cam_cross.setChecked(False)

    self.a120mm_cam_cross_x = QSpinBox()
    self.a120mm_cam_cross_x.setMinimum(1)
    self.a120mm_cam_cross_x.setMaximum(700)
    self.a120mm_cam_cross_x.setValue(600)
    self.a120mm_cam_cross_x.setSingleStep(5)

    self.a120mm_cam_cross_y = QSpinBox()
    self.a120mm_cam_cross_y.setMinimum(1)
    self.a120mm_cam_cross_y.setMaximum(700)
    self.a120mm_cam_cross_y.setValue(600)
    self.a120mm_cam_cross_y.setSingleStep(5)

    self.a120mm_cam_save_img = QCheckBox()
    self.a120mm_cam_save_img.setChecked(False)

    self.a120mm_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.a120mm_b_plate_solve.clicked.connect(self.f_a120mm_plate_solve)
    self.a120mm_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a120mm_b_plate_solve_cancel.clicked.connect(self.f_a120mm_platesolve_stop)
    self.lab_a120mm_plate_solve_status = QLabel("Plate solve status: NULL")
    self.lab_a120mm_plate_solve_change = QLabel("Last change: NULL")
    self.lab_a120mm_plate_solve_change_t = QLabel("NULL")

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
    cam_a120mm_butt_group3.addWidget(QLabel("Enable circle"))
    cam_a120mm_butt_group3.addWidget(self.a120mm_cam_cross)
    cam_a120mm_butt_group3.addWidget(QLabel("width"))
    cam_a120mm_butt_group3.addWidget(self.a120mm_cam_cross_x)
    cam_a120mm_butt_group3.addWidget(QLabel("height"))
    cam_a120mm_butt_group3.addWidget(self.a120mm_cam_cross_y)
    layout.addLayout(cam_a120mm_butt_group3)

    cam_a120mm_butt_group4 = QHBoxLayout()
    cam_a120mm_butt_group4.addWidget(QLabel("Save to file"))
    cam_a120mm_butt_group4.addWidget(self.a120mm_cam_save_img)
    cam_a120mm_butt_group4.addStretch()
    layout.addLayout(cam_a120mm_butt_group4)

    cam_a120mm_butt_group5 = QHBoxLayout()
    cam_a120mm_butt_group5.addWidget(self.a120mm_b_plate_solve)
    cam_a120mm_butt_group5.addWidget(self.a120mm_b_plate_solve_cancel)
    layout.addLayout(cam_a120mm_butt_group5)
    layout.addWidget(self.lab_a120mm_plate_solve_status)
    layout.addWidget(self.lab_a120mm_plate_solve_change)
    layout.addWidget(self.lab_a120mm_plate_solve_change_t)
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
    layout.addWidget(self.graphWidget_a120mm)

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

    self.a120mc_cam_cross1 = QCheckBox()
    self.a120mc_cam_cross1.setChecked(False)

    self.a120mc_cam_cross1_x = QSpinBox()
    self.a120mc_cam_cross1_x.setMinimum(1)
    self.a120mc_cam_cross1_x.setMaximum(700)
    self.a120mc_cam_cross1_x.setValue(600)
    self.a120mc_cam_cross1_x.setSingleStep(5)

    self.a120mc_cam_cross1_y = QSpinBox()
    self.a120mc_cam_cross1_y.setMinimum(1)
    self.a120mc_cam_cross1_y.setMaximum(700)
    self.a120mc_cam_cross1_y.setValue(600)
    self.a120mc_cam_cross1_y.setSingleStep(5)

    self.a120mc_cam_cross2 = QCheckBox()
    self.a120mc_cam_cross2.setChecked(False)

    self.a120mc_cam_cross2_x = QSpinBox()
    self.a120mc_cam_cross2_x.setMinimum(1)
    self.a120mc_cam_cross2_x.setMaximum(700)
    self.a120mc_cam_cross2_x.setValue(500)
    self.a120mc_cam_cross2_x.setSingleStep(5)

    self.a120mc_cam_cross2_y = QSpinBox()
    self.a120mc_cam_cross2_y.setMinimum(1)
    self.a120mc_cam_cross2_y.setMaximum(700)
    self.a120mc_cam_cross2_y.setValue(500)
    self.a120mc_cam_cross2_y.setSingleStep(5)

    self.a120mc_cam_save_img = QCheckBox()
    self.a120mc_cam_save_img.setChecked(False)

    self.a120mc_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.a120mc_b_plate_solve.clicked.connect(self.f_a120mc_plate_solve)
    self.a120mc_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.a120mc_b_plate_solve_cancel.clicked.connect(self.f_a120mc_platesolve_stop)
    self.lab_a120mc_plate_solve_status = QLabel("Plate solve status: NULL")
    self.lab_a120mc_plate_solve_change = QLabel("Last change: NULL")
    self.lab_a120mc_plate_solve_change_t = QLabel("NULL")

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
    cam_a120mc_butt_group3.addWidget(QLabel("Enable circle red"))
    cam_a120mc_butt_group3.addWidget(self.a120mc_cam_cross1)
    cam_a120mc_butt_group3.addWidget(QLabel("width"))
    cam_a120mc_butt_group3.addWidget(self.a120mc_cam_cross1_x)
    cam_a120mc_butt_group3.addWidget(QLabel("height"))
    cam_a120mc_butt_group3.addWidget(self.a120mc_cam_cross1_y)
    layout.addLayout(cam_a120mc_butt_group3)

    cam_a120mc_butt_group4 = QHBoxLayout()
    cam_a120mc_butt_group4.addWidget(QLabel("Enable circle green"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_cross2)
    cam_a120mc_butt_group4.addWidget(QLabel("width"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_cross2_x)
    cam_a120mc_butt_group4.addWidget(QLabel("height"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_cross2_y)
    layout.addLayout(cam_a120mc_butt_group4)

    cam_a120mc_butt_group4 = QHBoxLayout()
    cam_a120mc_butt_group4.addWidget(QLabel("Save to file"))
    cam_a120mc_butt_group4.addWidget(self.a120mc_cam_save_img)
    cam_a120mc_butt_group4.addStretch()
    layout.addLayout(cam_a120mc_butt_group4)

    cam_a120mc_butt_group5 = QHBoxLayout()
    cam_a120mc_butt_group5.addWidget(self.a120mc_b_plate_solve)
    cam_a120mc_butt_group5.addWidget(self.a120mc_b_plate_solve_cancel)
    layout.addLayout(cam_a120mc_butt_group5)
    layout.addWidget(self.lab_a120mc_plate_solve_status)
    layout.addWidget(self.lab_a120mc_plate_solve_change)
    layout.addWidget(self.lab_a120mc_plate_solve_change_t)
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
    layout.addWidget(self.graphWidget_a120mc)

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

    self.canon_cross = QCheckBox()
    self.canon_cross.setChecked(False)

    self.canon_cross_x = QSpinBox()
    self.canon_cross_x.setMinimum(1)
    self.canon_cross_x.setMaximum(700)
    self.canon_cross_x.setValue(600)
    self.canon_cross_x.setSingleStep(5)

    self.canon_cross_y = QSpinBox()
    self.canon_cross_y.setMinimum(1)
    self.canon_cross_y.setMaximum(700)
    self.canon_cross_y.setValue(600)
    self.canon_cross_y.setSingleStep(5)

    self.canon_b_plate_solve = QPushButton('Solve plate and upd. coords', self)
    self.canon_b_plate_solve.clicked.connect(self.f_canon_plate_solve)
    self.canon_b_plate_solve_cancel = QPushButton('Cancel', self)
    self.canon_b_plate_solve_cancel.clicked.connect(self.f_canon_platesolve_stop)
    self.lab_canon_plate_solve_status = QLabel("Plate solve status: NULL")
    self.lab_canon_plate_solve_change = QLabel("Last change: NULL")
    self.lab_canon_plate_solve_change_t = QLabel("NULL")

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
    cam_canon_butt_group3.addWidget(QLabel("Enable circle"))
    cam_canon_butt_group3.addWidget(self.canon_cross)
    cam_canon_butt_group3.addWidget(QLabel("width"))
    cam_canon_butt_group3.addWidget(self.canon_cross_x)
    cam_canon_butt_group3.addWidget(QLabel("height"))
    cam_canon_butt_group3.addWidget(self.canon_cross_y)
    layout.addLayout(cam_canon_butt_group3)

    cam_canon_butt_group5 = QHBoxLayout()
    cam_canon_butt_group5.addWidget(self.canon_b_plate_solve)
    cam_canon_butt_group5.addWidget(self.canon_b_plate_solve_cancel)
    layout.addLayout(cam_canon_butt_group5)
    layout.addWidget(self.lab_canon_plate_solve_status)
    layout.addWidget(self.lab_canon_plate_solve_change)
    layout.addWidget(self.lab_canon_plate_solve_change_t)
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

    self.lewy_tab6.setLayout(layout)

#############################################################################################

  def tab7_lewyUI(self):
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

    self.get_telescope_position_tab3_button = QPushButton('Get telescope position', self)
    self.get_telescope_position_tab3_button.setToolTip('Get current telescope position')
    self.get_telescope_position_tab3_button.clicked.connect(self.get_telescope_position_tab3)

    self.set_pos_zenith = QPushButton('SET pos to Zenith', self)
    self.set_pos_zenith.clicked.connect(self.set_zenith)

    self.goto_pos_180_25 = QPushButton('goto az:180 alt:25', self)
    self.goto_pos_180_25.clicked.connect(self.goto_180_25)

    self.goto_pos_90_25 = QPushButton('goto az:90 alt:25', self)
    self.goto_pos_90_25.clicked.connect(self.goto_90_25)

    self.goto_pos_143_40_23_40 = QPushButton('goto az:143d40m alt:23d40m', self)
    self.goto_pos_143_40_23_40.clicked.connect(self.goto_143_40_23_40)

    self.goto_pos_171_10_6_20 = QPushButton('goto az:171d10m alt:6d20m', self)
    self.goto_pos_171_10_6_20.clicked.connect(self.goto_171_10_6_20)

    self.goto_pos_zenith = QPushButton('park at zenith', self)
    self.goto_pos_zenith.clicked.connect(self.goto_zenith)

    self.meridian_box = QCheckBox()
    self.meridian_box.setChecked(False)
    self.meridian_box.stateChanged.connect(self.meridian_change)

    self.meridian_state = QLabel("State: NULL")

    self.solved_tabs_refresh = QPushButton('Reload tabs with solved plate', self)
    self.solved_tabs_refresh.clicked.connect(self.f_solved_tabs_refresh)

    self.act_pos_3 = QLabel("Position received from telescope")
    self.act_pos_3.setFont(self.headline)
    self.radec_position = QLabel("00H 00m 00s")
    self.altaz_position = QLabel("00D 00m 00s")
    self.conn_state = QLabel("Conn state: NULL")
    self.goto_state3 = QLabel("GOTO moving: NULL")

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
    whole_az_input_layout.addLayout(az_input_layout)
    layout.addLayout(whole_az_input_layout)

    whole_elev_input_layout = QVBoxLayout()
    whole_elev_input_layout.addWidget(self.elev_input)
    elev_input_layout = QHBoxLayout()
    elev_input_layout.addWidget(self.elev_d)
    elev_input_layout.addWidget(QLabel("D"))
    elev_input_layout.addWidget(self.elev_m)
    elev_input_layout.addWidget(QLabel("m"))
    whole_elev_input_layout.addLayout(elev_input_layout)
    whole_elev_input_layout.addWidget(self.altaz_button)
    layout.addLayout(whole_elev_input_layout)

    layout.addWidget(separator2)



    layout.addWidget(self.get_telescope_position_tab3_button)
    goto3_layout = QHBoxLayout()
    goto3_layout.addWidget(self.set_pos_zenith)
    goto3_layout.addWidget(self.goto_pos_zenith)
    layout.addLayout(goto3_layout)

    goto1_layout = QHBoxLayout()
    goto1_layout.addWidget(self.goto_pos_180_25)
    goto1_layout.addWidget(self.goto_pos_90_25)
    layout.addLayout(goto1_layout)

    goto2_layout = QHBoxLayout()
    goto2_layout.addWidget(self.goto_pos_143_40_23_40)
    goto2_layout.addWidget(self.goto_pos_171_10_6_20)
    layout.addLayout(goto2_layout)

    layout.addWidget(separator5)

    meridian_layout = QHBoxLayout()
    meridian_layout.addWidget(QLabel("After meridian:"))
    meridian_layout.addWidget(self.meridian_box)
    meridian_layout.addWidget(self.meridian_state)
    meridian_layout.addStretch()
    layout.addLayout(meridian_layout)

    layout.addWidget(separator3)
    layout.addWidget(self.act_pos_3, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.radec_position)
    layout.addWidget(self.altaz_position)
    layout.addWidget(self.conn_state)
    layout.addWidget(self.goto_state3)

    layout.addWidget(separator4)
    layout.addStretch()

    bat_buttons_layout = QHBoxLayout()
    bat_buttons_layout.addWidget(self.b_restart)
    bat_buttons_layout.addWidget(self.b_reboot_scope)
    bat_buttons_layout.addWidget(self.b_shutdown)
    layout.addLayout(bat_buttons_layout)
    layout.addWidget(self.solved_tabs_refresh)

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

    self.lab_bat1 = QLabel("Battery 1")
    self.lab_bat1.setFont(self.headline)
    self.lab_bat1_state = QLabel("State: ON")
    self.lab_bat1_voltage = QLabel("Voltage: 0V")
    self.lab_bat1_current = QLabel("Current: 0A")
    self.lab_bat1_capacity = QLabel("Used: 0mAh")

    self.lab_bat2 = QLabel("Battery 2")
    self.lab_bat2.setFont(self.headline)
    self.lab_bat2_state = QLabel("State: ON")
    self.lab_bat2_voltage = QLabel("Voltage: 0V")
    self.lab_bat2_current = QLabel("Current: 0A")
    self.lab_bat2_capacity = QLabel("Used: 0mAh")

    self.lab_bat3 = QLabel("Battery 3")
    self.lab_bat3.setFont(self.headline)
    self.lab_bat3_state = QLabel("State: ON")
    self.lab_bat3_voltage = QLabel("Voltage: 0V")
    self.lab_bat3_current = QLabel("Current: 0A")
    self.lab_bat3_capacity = QLabel("Used: 0mAh")

    self.lab_bat4 = QLabel("Battery 4")
    self.lab_bat4.setFont(self.headline)
    self.lab_bat4_state = QLabel("State: ON")
    self.lab_bat4_voltage = QLabel("Voltage: 0V")
    self.lab_bat4_current = QLabel("Current: 0A")
    self.lab_bat4_capacity = QLabel("Used: 0mAh")

    self.b_bat1_auto = QPushButton('AUTO', self)
    self.b_bat1_auto.clicked.connect(self.f_bat1_auto)
    self.b_bat1_on = QPushButton('FORCED ON', self)
    self.b_bat1_on.clicked.connect(self.f_bat1_forced_on)
    self.b_bat1_off = QPushButton('FORCED OFF', self)
    self.b_bat1_off.clicked.connect(self.f_bat1_forced_off)

    self.b_bat2_auto = QPushButton('AUTO', self)
    self.b_bat2_auto.clicked.connect(self.f_bat2_auto)
    self.b_bat2_on = QPushButton('FORCED ON', self)
    self.b_bat2_on.clicked.connect(self.f_bat2_forced_on)
    self.b_bat2_off = QPushButton('FORCED OFF', self)
    self.b_bat2_off.clicked.connect(self.f_bat2_forced_off)

    self.b_bat3_auto = QPushButton('AUTO', self)
    self.b_bat3_auto.clicked.connect(self.f_bat3_auto)
    self.b_bat3_on = QPushButton('FORCED ON', self)
    self.b_bat3_on.clicked.connect(self.f_bat3_forced_on)
    self.b_bat3_off = QPushButton('FORCED OFF', self)
    self.b_bat3_off.clicked.connect(self.f_bat3_forced_off)

    self.b_bat4_auto = QPushButton('AUTO', self)
    self.b_bat4_auto.clicked.connect(self.f_bat4_auto)
    self.b_bat4_on = QPushButton('FORCED ON', self)
    self.b_bat4_on.clicked.connect(self.f_bat4_forced_on)
    self.b_bat4_off = QPushButton('FORCED OFF', self)
    self.b_bat4_off.clicked.connect(self.f_bat4_forced_off)

    self.b_bat_zero_mah = QPushButton('Zero Batt Usage', self)
    self.b_bat_zero_mah.clicked.connect(self.f_bat_zero_mah)


    layout.addWidget(self.lab_bat1, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.lab_bat1_state)
    layout.addWidget(self.lab_bat1_voltage)
    layout.addWidget(self.lab_bat1_current)
    layout.addWidget(self.lab_bat1_capacity)
    bat1_layout = QHBoxLayout()
    bat1_layout.addWidget(self.b_bat1_auto)
    bat1_layout.addWidget(self.b_bat1_on)
    bat1_layout.addWidget(self.b_bat1_off)
    layout.addLayout(bat1_layout)

    layout.addWidget(separator1)
    layout.addWidget(self.lab_bat2, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.lab_bat2_state)
    layout.addWidget(self.lab_bat2_voltage)
    layout.addWidget(self.lab_bat2_current)
    layout.addWidget(self.lab_bat2_capacity)
    bat2_layout = QHBoxLayout()
    bat2_layout.addWidget(self.b_bat2_auto)
    bat2_layout.addWidget(self.b_bat2_on)
    bat2_layout.addWidget(self.b_bat2_off)
    layout.addLayout(bat2_layout)

    layout.addWidget(separator2)
    layout.addWidget(self.lab_bat3, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.lab_bat3_state)
    layout.addWidget(self.lab_bat3_voltage)
    layout.addWidget(self.lab_bat3_current)
    layout.addWidget(self.lab_bat3_capacity)
    bat3_layout = QHBoxLayout()
    bat3_layout.addWidget(self.b_bat3_auto)
    bat3_layout.addWidget(self.b_bat3_on)
    bat3_layout.addWidget(self.b_bat3_off)
    layout.addLayout(bat3_layout)

    layout.addWidget(separator3)
    layout.addWidget(self.lab_bat4, alignment=QtCore.Qt.AlignCenter)
    layout.addWidget(self.lab_bat4_state)
    layout.addWidget(self.lab_bat4_voltage)
    layout.addWidget(self.lab_bat4_current)
    layout.addWidget(self.lab_bat4_capacity)
    bat4_layout = QHBoxLayout()
    bat4_layout.addWidget(self.b_bat4_auto)
    bat4_layout.addWidget(self.b_bat4_on)
    bat4_layout.addWidget(self.b_bat4_off)
    layout.addLayout(bat4_layout)

    layout.addWidget(separator4)
    layout.addWidget(self.b_bat_zero_mah)
    layout.addWidget(separator5)

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

    self.lab_guiding = QLabel("GUIDING")
    self.lab_guiding.setFont(self.headline)
    self.lab_guiding.setAlignment(Qt.AlignCenter)

    self.lab_guiding_state = QLabel("State: NULL")

    self.guiding_on_box = QCheckBox()
    self.guiding_on_box.setChecked(False)

    self.guiding_proc_platesolve_stop_butt = QPushButton('Cancel curr platesolve', self)
    self.guiding_proc_platesolve_stop_butt.clicked.connect(self.f_guiding_proc_platesolve_stop)

    self.guiding_source = QComboBox()
    self.guiding_source.addItems(['120MM', '120MC'])
    self.guiding_source.setEditable = False

    self.lab_ra_pid = QLabel("RA PID")
    self.lab_ra_pid.setFont(self.headline)
    self.lab_ra_pid.setAlignment(Qt.AlignCenter)

    self.guiding_ra_kp = QDoubleSpinBox()
    self.guiding_ra_kp.setMinimum(-100.0)
    self.guiding_ra_kp.setMaximum(100.0)
    self.guiding_ra_kp.setValue(-0.6)
    self.guiding_ra_kp.setSingleStep(0.01)

    self.guiding_ra_ki = QDoubleSpinBox()
    self.guiding_ra_ki.setMinimum(-10.0)
    self.guiding_ra_ki.setMaximum(10.0)
    self.guiding_ra_ki.setValue(0.0)
    self.guiding_ra_ki.setSingleStep(0.01)

    self.guiding_ra_kd = QDoubleSpinBox()
    self.guiding_ra_kd.setMinimum(-10.0)
    self.guiding_ra_kd.setMaximum(10.0)
    self.guiding_ra_kd.setValue(-0.6)
    self.guiding_ra_kd.setSingleStep(0.01)

    self.lab_dec_pid = QLabel("DEC PID")
    self.lab_dec_pid.setFont(self.headline)
    self.lab_dec_pid.setAlignment(Qt.AlignCenter)

    self.guiding_dec_kp = QDoubleSpinBox()
    self.guiding_dec_kp.setMinimum(-100.0)
    self.guiding_dec_kp.setMaximum(100.0)
    self.guiding_dec_kp.setValue(-3.0)
    self.guiding_dec_kp.setSingleStep(0.01)

    self.guiding_dec_on_positive_box = QCheckBox()
    self.guiding_dec_on_positive_box.setChecked(True)

    self.guiding_dec_ki = QDoubleSpinBox()
    self.guiding_dec_ki.setMinimum(-10.0)
    self.guiding_dec_ki.setMaximum(10.0)
    self.guiding_dec_ki.setValue(0.0)
    self.guiding_dec_ki.setSingleStep(0.01)

    self.guiding_dec_kd = QDoubleSpinBox()
    self.guiding_dec_kd.setMinimum(-10.0)
    self.guiding_dec_kd.setMaximum(10.0)
    self.guiding_dec_kd.setValue(-3.0)
    self.guiding_dec_kd.setSingleStep(0.01)

    self.guiding_graph = pg.PlotWidget()
    self.guiding_hist_color_window = self.palette().color(QtGui.QPalette.Window)
    self.guiding_hist_pen_ra = pg.mkPen(color=(255,0,0))
    self.guiding_hist_pen_dec = pg.mkPen(color=(0,255,0))
    self.guiding_graph.plot(x=list(range(500)), y=list(range(500)), pen=self.guiding_hist_pen_ra)
    self.guiding_graph.plot(x=list(range(500)), y=list(range(500)), pen=self.guiding_hist_pen_dec)
    self.guiding_graph.setBackground(self.guiding_hist_color_window)
    self.guiding_graph.hideAxis('bottom')

    self.lab_ra_pid_params = QLabel("RA PID = NULL")
    self.lab_dec_pid_params = QLabel("DEC PID = NULL")

    self.draw_ra = QCheckBox()
    self.draw_ra.setChecked(True)

    self.draw_dec = QCheckBox()
    self.draw_dec.setChecked(True)

    self.guiding_graph_refresh_butt = QPushButton('Refresh graph', self)
    self.guiding_graph_refresh_butt.clicked.connect(self.guiding_graph_refresh)



    layout.addWidget(self.lab_guiding)
    guiding_layout1 = QHBoxLayout()
    guiding_layout1.addWidget(QLabel("Turn on guiding: "))
    guiding_layout1.addWidget(self.guiding_on_box)
    guiding_layout1.addStretch()
    guiding_layout1.addWidget(self.guiding_proc_platesolve_stop_butt)
    layout.addLayout(guiding_layout1)


    guiding_layout8 = QHBoxLayout()
    guiding_layout8.addWidget(self.guiding_source)
    guiding_layout8.addWidget(self.guiding_graph_refresh_butt)
    layout.addLayout(guiding_layout8)

    layout.addWidget(self.lab_guiding_state)

    layout.addWidget(separator1)

    layout.addWidget(self.lab_ra_pid)

    guiding_layout2 = QHBoxLayout()
    guiding_layout2.addWidget(QLabel("RA Kp: "))
    guiding_layout2.addWidget(self.guiding_ra_kp)
    guiding_layout2.addStretch()
    layout.addLayout(guiding_layout2)

    guiding_layout3 = QHBoxLayout()
    guiding_layout3.addWidget(QLabel("RA Ki: "))
    guiding_layout3.addWidget(self.guiding_ra_ki)
    guiding_layout3.addStretch()
    layout.addLayout(guiding_layout3)

    guiding_layout4 = QHBoxLayout()
    guiding_layout4.addWidget(QLabel("RA Kd: "))
    guiding_layout4.addWidget(self.guiding_ra_kd)
    guiding_layout4.addStretch()
    layout.addLayout(guiding_layout4)

    layout.addWidget(separator2)

    layout.addWidget(self.lab_dec_pid)

    guiding_layout5 = QHBoxLayout()
    guiding_layout5.addWidget(QLabel("DEC Kp: "))
    guiding_layout5.addWidget(self.guiding_dec_kp)
    guiding_layout5.addStretch()
    guiding_layout5.addWidget(QLabel("Run on pos only (or neg only): "))
    guiding_layout5.addWidget(self.guiding_dec_on_positive_box)
    layout.addLayout(guiding_layout5)

    guiding_layout6 = QHBoxLayout()
    guiding_layout6.addWidget(QLabel("DEC Ki: "))
    guiding_layout6.addWidget(self.guiding_dec_ki)
    guiding_layout6.addStretch()
    layout.addLayout(guiding_layout6)

    guiding_layout7 = QHBoxLayout()
    guiding_layout7.addWidget(QLabel("DEC Kd: "))
    guiding_layout7.addWidget(self.guiding_dec_kd)
    guiding_layout7.addStretch()
    layout.addLayout(guiding_layout7)

    layout.addWidget(separator3)
    layout.addWidget(self.lab_ra_pid_params)
    layout.addWidget(self.lab_dec_pid_params)

    guiding_layout9 = QHBoxLayout()
    guiding_layout9.addWidget(QLabel("Draw RA: "))
    guiding_layout9.addWidget(self.draw_ra)
    guiding_layout9.addWidget(QLabel("Draw DEC: "))
    guiding_layout9.addWidget(self.draw_dec)
    guiding_layout9.addStretch()
    layout.addLayout(guiding_layout9)

    layout.addWidget(separator4)
    layout.addWidget(self.guiding_graph)

    layout.addStretch()
    self.lewy_tab10.setLayout(layout)

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
    global viewer_a462mc_deployed
    layout = QVBoxLayout()
    self.viewer_a462mc = PhotoViewer(self)
    layout.addWidget(self.viewer_a462mc)
    self.prawy_tab2.setLayout(layout)
    viewer_a462mc_deployed = True

#############################################################################################

  def tab_3_prawyUI(self):
    global viewer_a120mm_deployed
    layout = QVBoxLayout()
    self.viewer_a120mm = PhotoViewer(self)
    layout.addWidget(self.viewer_a120mm)
    self.prawy_tab3.setLayout(layout)
    viewer_a120mm_deployed = True

#############################################################################################

  def tab_4_prawyUI(self):
    global viewer_a120mc_deployed
    layout = QVBoxLayout()
    self.viewer_a120mc = PhotoViewer(self)
    layout.addWidget(self.viewer_a120mc)
    self.prawy_tab4.setLayout(layout)
    viewer_a120mc_deployed = True

#############################################################################################

  def tab_5_prawyUI(self):
    global viewer_canon_deployed
    layout = QVBoxLayout()
    self.viewer_canon = PhotoViewer(self)
    layout.addWidget(self.viewer_canon)
    self.prawy_tab5.setLayout(layout)
    viewer_canon_deployed = True

#############################################################################################

  def tab_6_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_tycho2 = PhotoViewer(self)
    layout.addWidget(self.viewer_tycho2)
    self.prawy_tab6.setLayout(layout)

#############################################################################################

  def tab_7_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_hd = PhotoViewer(self)
    layout.addWidget(self.viewer_hd)
    self.prawy_tab7.setLayout(layout)

#############################################################################################

  def tab_8_prawyUI(self):
    layout = QVBoxLayout()
    self.viewer_skymap = QWebEngineView()
    layout.addWidget(self.viewer_skymap)
    self.prawy_tab8.setLayout(layout)

#############################################################################################

  def guiding_graph_refresh(self):
    self.guiding_graph.clear()
    if self.draw_ra.isChecked():
      self.guiding_graph.plot(x=list(range(500)), y=list(ra_guiding_graph), pen=self.guiding_hist_pen_ra)
    if self.draw_dec.isChecked():
      self.guiding_graph.plot(x=list(range(500)), y=list(dec_guiding_graph), pen=self.guiding_hist_pen_dec)

  def meridian_change(self):
    global req_cmd

    if self.meridian_box.isChecked():
      verb = 'after'
    else:
      verb = 'before'

    payload = {
      'mode': 'meridian',
      'value': verb,
    }
    req_cmd.put(payload)

  def update_meridian_state(self):
    global telescope_stats, meridian_after_launch_done
    if 'after_meridian' in telescope_stats:
      self.meridian_state.setText('State: ' + str(telescope_stats['after_meridian']))

      if not meridian_after_launch_done:
        meridian_after_launch_done = True
        if telescope_stats['after_meridian']:
          self.meridian_box.setChecked(True)
      else:
        if telescope_stats['after_meridian'] != self.meridian_box.isChecked():
          self.meridian_change()
    else:
      self.meridian_state.setText('State: NULL')


  def f_a120mc_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a120mc_platesolve/frame.axy'])

  def f_a120mm_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a120mm_platesolve/frame.axy'])

  def f_a183mm_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a183mm_platesolve/frame.axy'])

  def f_a462mc_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/a462mc_platesolve/frame.axy'])

  def f_canon_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/canon_platesolve/frame.axy'])

  def f_guiding_proc_platesolve_stop(self):
    out = subprocess.check_output(['rm', '-rf', '/dev/shm/guiding_proc/frame.axy'])

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

  def f_a120mc_plate_solve_status_refresh(self):
    global run_plate_solve_a120mc, plate_solve_a120mc_status, telescope_stats
    self.lab_a120mc_plate_solve_status.setText('Plate solve status: ' + str(plate_solve_a120mc_status))
    if telescope_stats != {}:
      self.lab_a120mc_plate_solve_change.setText('Change RA: ' + str(telescope_stats['last_ra_change']) + " DEC: " + str(telescope_stats['last_dec_change']))
      self.lab_a120mc_plate_solve_change_t.setText('Change RADEC: ' + str(int(time.time() - telescope_stats['last_radec_change_t'])) + "s ago")

  def f_a120mm_plate_solve_status_refresh(self):
    global run_plate_solve_a120mm, plate_solve_a120mm_status, telescope_stats
    self.lab_a120mm_plate_solve_status.setText('Plate solve status: ' + str(plate_solve_a120mm_status))
    if telescope_stats != {}:
      self.lab_a120mm_plate_solve_change.setText('Change RA: ' + str(telescope_stats['last_ra_change']) + " DEC: " + str(telescope_stats['last_dec_change']))
      self.lab_a120mm_plate_solve_change_t.setText('Change RADEC: ' + str(int(time.time() - telescope_stats['last_radec_change_t'])) + "s ago")

  def f_canon_plate_solve_status_refresh(self):
    global run_plate_solve_canon, plate_solve_canon_status, telescope_stats
    self.lab_canon_plate_solve_status.setText('Plate solve status: ' + str(plate_solve_canon_status))
    if telescope_stats != {}:
      self.lab_canon_plate_solve_change.setText('Change RA: ' + str(telescope_stats['last_ra_change']) + " DEC: " + str(telescope_stats['last_dec_change']))
      self.lab_canon_plate_solve_change_t.setText('Change RADEC: ' + str(int(time.time() - telescope_stats['last_radec_change_t'])) + "s ago")

  def f_a183mm_plate_solve(self):
    global run_plate_solve_a183mm
    run_plate_solve_a183mm = True

  def f_a183mm_plate_solve_status_refresh(self):
    global run_plate_solve_a183mm, plate_solve_a183mm_status, telescope_stats
    self.lab_a183mm_plate_solve_status.setText('Plate solve status: ' + str(plate_solve_a183mm_status))
    if telescope_stats != {}:
      self.lab_a183mm_plate_solve_change.setText('Change RA: ' + str(telescope_stats['last_ra_change']) + " DEC: " + str(telescope_stats['last_dec_change']))
      self.lab_a183mm_plate_solve_change_t.setText('Change RADEC: ' + str(int(time.time() - telescope_stats['last_radec_change_t'])) + "s ago")

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


  def f_a462mc_plate_solve(self):
    global run_plate_solve_a462mc
    run_plate_solve_a462mc = True

  def f_a462mc_plate_solve_status_refresh(self):
    global run_plate_solve_a462mc, plate_solve_a462mc_status, telescope_stats
    self.lab_a462mc_plate_solve_status.setText('Plate solve status: ' + str(plate_solve_a462mc_status))
    if telescope_stats != {}:
      self.lab_a462mc_plate_solve_change.setText('Change RA: ' + str(telescope_stats['last_ra_change']) + " DEC: " + str(telescope_stats['last_dec_change']))
      self.lab_a462mc_plate_solve_change_t.setText('Change RADEC: ' + str(int(time.time() - telescope_stats['last_radec_change_t'])) + "s ago")

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
    global cam_settings
    cam_settings['a120mc']['Exposure']['Value'] = cam_settings['a120mc']['Exposure']['DefaultValue']
    cam_settings['a120mc']['Gain']['Value'] = cam_settings['a120mc']['Gain']['DefaultValue']
    cam_settings['a120mc']['Offset']['Value'] = cam_settings['a120mc']['Offset']['DefaultValue']
    self.f_a120mc_cam_update_values(load_slider=True)
    self.f_a120mc_cam_params_changed()

  def f_a120mm_cam_reset_settings(self):
    global cam_settings
    cam_settings['a120mm']['Exposure']['Value'] = cam_settings['a120mm']['Exposure']['DefaultValue']
    cam_settings['a120mm']['Offset']['Value'] = cam_settings['a120mm']['Offset']['DefaultValue']
    cam_settings['a120mm']['Gain']['Value'] = cam_settings['a120mm']['Gain']['DefaultValue']
    self.f_a120mm_cam_update_values(load_slider=True)
    self.f_a120mm_cam_params_changed()

  def f_a183mm_cam_reset_settings(self):
    global cam_settings
    cam_settings['a183mm']['Exposure']['Value'] = cam_settings['a183mm']['Exposure']['DefaultValue']
    cam_settings['a183mm']['Offset']['Value'] = cam_settings['a183mm']['Offset']['DefaultValue']
    cam_settings['a183mm']['Gain']['Value'] = cam_settings['a183mm']['Gain']['DefaultValue']
    self.f_a183mm_cam_update_values(load_slider=True)
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

  def f_a462mc_cam_reset_settings(self):
    global cam_settings
    cam_settings['a462mc']['Exposure']['Value'] = cam_settings['a462mc']['Exposure']['DefaultValue']
    cam_settings['a462mc']['Offset']['Value'] = cam_settings['a462mc']['Offset']['DefaultValue']
    cam_settings['a462mc']['Gain']['Value'] = cam_settings['a462mc']['Gain']['DefaultValue']
    self.f_a462mc_cam_update_values(load_slider=True)
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

    if q_a120mc_ready and viewer_a120mc_deployed and q_a120mc_ready:
      frame = q_a120mc_ready.pop()

      if not 'rotate' in cam_settings['a120mc']:
        cam_settings['a120mc']['rotate'] = 0
        cam_settings['a120mc']['last_rotate'] = 0
      if cam_settings['a120mc']['rotate'] == 90:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_CLOCKWISE)
      elif cam_settings['a120mc']['rotate'] == 180:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_180)
      elif cam_settings['a120mc']['rotate'] == 270:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_COUNTERCLOCKWISE)
      else:
        _frame = frame['frameRGB']

      if self.a120mc_cam_inverse.isChecked():
        _frame = 255 - _frame

      h, s, v = cv2.split(cv2.cvtColor(_frame.astype("float32"), cv2.COLOR_RGB2HSV))
      s = s*self.a120mc_cam_sat.value()
      s = np.clip(s,0.0,255.0)
      v = v + int(self.a120mc_cam_bri.value())
      v = np.power(v, self.a120mc_cam_gam.value())
      v = np.clip(v,0.0,255.0)
      _frame = cv2.cvtColor(cv2.merge((h,s,v)), cv2.COLOR_HSV2RGB).astype("uint8")

      if self.a120mc_cam_hist_equal.isChecked():
        img_yuv = cv2.cvtColor(_frame, cv2.COLOR_BGR2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        _frame = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

      height, width, channel = _frame.shape

      if self.a120mc_cam_normalize.isChecked():
        l = np.percentile(_frame,self.a120mc_cam_normalize_l.value())
        h = np.percentile(_frame,self.a120mc_cam_normalize_h.value())
        _frame = np.clip((((_frame - l)/(h-l))*255), 0, 255).astype('uint8')


      #b,g,r = cv2.split(_frame)
      #histogram_b, bin_edges_b = np.histogram(b, bins=256, range=(0, 256))
      #histogram_g, bin_edges_g = np.histogram(g, bins=256, range=(0, 256))
      #histogram_r, bin_edges_r = np.histogram(r, bins=256, range=(0, 256))
      histogram_gray, bin_edges_gray = np.histogram(cv2.cvtColor(_frame, cv2.COLOR_RGB2GRAY), bins=256, range=(0, 256))

      if self.a120mc_cam_cross1.isChecked():
        self.a120mc_cam_cross1_x.setMaximum(width)
        self.a120mc_cam_cross1_y.setMaximum(height)
        center_coordinates = (self.a120mc_cam_cross1_x.value(), self.a120mc_cam_cross1_y.value())
        radius = 20
        color = (0, 0, 255)
        thickness = 2
        _frame = cv2.circle(_frame, center_coordinates, radius, color, thickness)

      if self.a120mc_cam_cross2.isChecked():
        self.a120mc_cam_cross2_x.setMaximum(width)
        self.a120mc_cam_cross2_y.setMaximum(height)
        center_coordinates = (self.a120mc_cam_cross2_x.value(), self.a120mc_cam_cross2_y.value())
        radius = 20
        color = (0, 255, 0)
        thickness = 2
        _frame = cv2.circle(_frame, center_coordinates, radius, color, thickness)

      self.graphWidget_a120mc.clear()
      #self.graphWidget_a120mc.plot(x=list(range(256)), y=histogram_b, pen=self.hist_pen_b)
      #self.graphWidget_a120mc.plot(x=list(range(256)), y=histogram_g, pen=self.hist_pen_g)
      #self.graphWidget_a120mc.plot(x=list(range(256)), y=histogram_r, pen=self.hist_pen_r)
      #self.graphWidget_a120mc.plot(x=list(range(256)), y=histogram_gray, pen=self.hist_pen_gray)
      bytesPerLine = 3 * width
      qImg = QImage(_frame, width, height, bytesPerLine, QImage.Format_BGR888)
      self.viewer_a120mc.setPhoto(QtGui.QPixmap(qImg))
      cam_settings['a120mc']['disp_frame_time'] = frame['time']


      if cam_settings['a120mc']['last_rotate'] != cam_settings['a120mc']['rotate']:
        self.viewer_a120mc.fitInView()
        cam_settings['a120mc']['last_rotate'] = cam_settings['a120mc']['rotate']

      if self.a120mc_cam_save_img.isChecked():
        q_a120mc_save_to_file.append(frame)

  def f_a120mm_window_refresh(self):
    global q_a120mm_ready, viewer_a120mm_deployed, cam_settings, q_a120mm_save_to_file

    if q_a120mm_ready and viewer_a120mm_deployed and q_a120mm_ready:
      frame = q_a120mm_ready.pop()

      if not 'rotate' in cam_settings['a120mm']:
        cam_settings['a120mm']['rotate'] = 0
        cam_settings['a120mm']['last_rotate'] = 0
      if cam_settings['a120mm']['rotate'] == 90:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_CLOCKWISE)
      elif cam_settings['a120mm']['rotate'] == 180:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_180)
      elif cam_settings['a120mm']['rotate'] == 270:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_COUNTERCLOCKWISE)
      else:
        _frame = frame['frameRGB']

      if self.a120mm_cam_inverse.isChecked():
        _frame = 255 - _frame

      h, s, v = cv2.split(cv2.cvtColor(_frame.astype("float32"), cv2.COLOR_RGB2HSV))
      s = s*self.a120mm_cam_sat.value()
      s = np.clip(s,0.0,255.0)
      v = v + int(self.a120mm_cam_bri.value())
      v = np.power(v, self.a120mm_cam_gam.value())
      v = np.clip(v,0.0,255.0)
      _frame = cv2.cvtColor(cv2.merge((h,s,v)), cv2.COLOR_HSV2RGB).astype("uint8")

      if self.a120mm_cam_hist_equal.isChecked():
        img_yuv = cv2.cvtColor(_frame, cv2.COLOR_BGR2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        _frame = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

      height, width, channel = _frame.shape

      if self.a120mm_cam_normalize.isChecked():
        l = np.percentile(_frame,self.a120mm_cam_normalize_l.value())
        h = np.percentile(_frame,self.a120mm_cam_normalize_h.value())
        _frame = np.clip((((_frame - l)/(h-l))*255), 0, 255).astype('uint8')

      #b,g,r = cv2.split(_frame)
      #histogram_b, bin_edges_b = np.histogram(b, bins=256, range=(0, 256))
      #histogram_g, bin_edges_g = np.histogram(g, bins=256, range=(0, 256))
      #histogram_r, bin_edges_r = np.histogram(r, bins=256, range=(0, 256))
      histogram_gray, bin_edges_gray = np.histogram(cv2.cvtColor(_frame, cv2.COLOR_RGB2GRAY), bins=256, range=(0, 256))

      if self.a120mm_cam_cross.isChecked():
        self.a120mm_cam_cross_x.setMaximum(width)
        self.a120mm_cam_cross_y.setMaximum(height)
        center_coordinates = (self.a120mm_cam_cross_x.value(), self.a120mm_cam_cross_y.value())
        radius = 20
        color = (255, 0, 0)
        thickness = 2
        _frame = cv2.circle(_frame, center_coordinates, radius, color, thickness)

      self.graphWidget_a120mm.clear()
      #self.graphWidget_a120mm.plot(x=list(range(256)), y=histogram_b, pen=self.hist_pen_b)
      #self.graphWidget_a120mm.plot(x=list(range(256)), y=histogram_g, pen=self.hist_pen_g)
      #self.graphWidget_a120mm.plot(x=list(range(256)), y=histogram_r, pen=self.hist_pen_r)
      #self.graphWidget_a120mm.plot(x=list(range(256)), y=histogram_gray, pen=self.hist_pen_gray)
      bytesPerLine = 3 * width
      qImg = QImage(_frame, width, height, bytesPerLine, QImage.Format_BGR888)
      self.viewer_a120mm.setPhoto(QtGui.QPixmap(qImg))
      cam_settings['a120mm']['disp_frame_time'] = frame['time']


      if cam_settings['a120mm']['last_rotate'] != cam_settings['a120mm']['rotate']:
        self.viewer_a120mm.fitInView()
        cam_settings['a120mm']['last_rotate'] = cam_settings['a120mm']['rotate']

      if self.a120mm_cam_save_img.isChecked():
        q_a120mm_save_to_file.append(frame)

  def f_canon_window_refresh(self):
    global q_canon_ready, viewer_canon_deployed, cam_settings, canon_last_frame, canon_last_frame_time

    if viewer_canon_deployed:
      if q_canon_ready:
        frame = q_canon_ready.pop()
        canon_last_frame = frame.copy()
      elif canon_last_frame != False and (time.time() - canon_last_frame_time) > 3:
        frame = canon_last_frame.copy()
        canon_last_frame_time = time.time()
      else:
        return

      if cam_settings['canon']['rotate'] == 90:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_CLOCKWISE)
      elif cam_settings['canon']['rotate'] == 180:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_180)
      elif cam_settings['canon']['rotate'] == 270:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_COUNTERCLOCKWISE)
      else:
        _frame = frame['frameRGB']

      if self.canon_inverse.isChecked():
        _frame = 255 - _frame

      h, s, v = cv2.split(cv2.cvtColor(_frame.astype("float32"), cv2.COLOR_RGB2HSV))
      s = s*self.canon_sat.value()
      s = np.clip(s,0.0,255.0)
      v = v + int(self.canon_bri.value())
      v = np.power(v, self.canon_gam.value())
      v = np.clip(v,0.0,255.0)
      _frame = cv2.cvtColor(cv2.merge((h,s,v)), cv2.COLOR_HSV2RGB).astype("uint8")

      if self.canon_hist_equal.isChecked():
        img_yuv = cv2.cvtColor(_frame, cv2.COLOR_BGR2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        _frame = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

      #b,g,r = cv2.split(_frame)
      #histogram_b, bin_edges_b = np.histogram(b, bins=256, range=(0, 256))
      #histogram_g, bin_edges_g = np.histogram(g, bins=256, range=(0, 256))
      #histogram_r, bin_edges_r = np.histogram(r, bins=256, range=(0, 256))
      #histogram_gray, bin_edges_gray = np.histogram(cv2.cvtColor(_frame, cv2.COLOR_RGB2GRAY), bins=256, range=(0, 256))

      height, width, channel = _frame.shape

      if self.canon_cam_normalize.isChecked():
        l = np.percentile(_frame,self.canon_cam_normalize_l.value())
        h = np.percentile(_frame,self.canon_cam_normalize_h.value())
        _frame = np.clip((((_frame - l)/(h-l))*255), 0, 255).astype('uint8')

      if self.canon_cross.isChecked():
        self.canon_cross_x.setMaximum(width)
        self.canon_cross_y.setMaximum(height)
        center_coordinates = (self.canon_cross_x.value(), self.canon_cross_y.value())
        radius = 20
        color = (255, 0, 0)
        thickness = 2
        _frame = cv2.circle(_frame, center_coordinates, radius, color, thickness)

      self.graphWidget_canon.clear()
      #self.graphWidget_canon.plot(x=list(range(256)), y=histogram_b, pen=self.hist_pen_b)
      #self.graphWidget_canon.plot(x=list(range(256)), y=histogram_g, pen=self.hist_pen_g)
      #self.graphWidget_canon.plot(x=list(range(256)), y=histogram_r, pen=self.hist_pen_r)
      #self.graphWidget_canon.plot(x=list(range(256)), y=histogram_gray, pen=self.hist_pen_gray)
      bytesPerLine = 3 * width
      qImg = QImage(_frame, width, height, bytesPerLine, QImage.Format_BGR888)
      self.viewer_canon.setPhoto(QtGui.QPixmap(qImg))
      cam_settings['canon']['disp_frame_time'] = frame['time']

      if cam_settings['canon']['last_rotate'] != cam_settings['canon']['rotate']:
        self.viewer_canon.fitInView()
        cam_settings['canon']['last_rotate'] = cam_settings['canon']['rotate']

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

    if q_a183mm_ready and viewer_a183mm_deployed and q_a183mm_ready:
      frame = q_a183mm_ready.pop()

      if not 'rotate' in cam_settings['a183mm']:
        cam_settings['a183mm']['rotate'] = 0
        cam_settings['a183mm']['last_rotate'] = 0
      if cam_settings['a183mm']['rotate'] == 90:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_CLOCKWISE)
      elif cam_settings['a183mm']['rotate'] == 180:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_180)
      elif cam_settings['a183mm']['rotate'] == 270:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_COUNTERCLOCKWISE)
      else:
        _frame = frame['frameRGB']

      if self.a183mm_cam_inverse.isChecked():
        _frame = 255 - _frame

      if self.a183mm_cam_sat.value() != 1.0 or int(self.a183mm_cam_bri.value()) != 0 or self.a183mm_cam_gam.value() != 1.0:
        h, s, v = cv2.split(cv2.cvtColor(_frame.astype("float32"), cv2.COLOR_RGB2HSV))
        s = s*self.a183mm_cam_sat.value()
        s = np.clip(s,0.0,255.0)
        v = v + int(self.a183mm_cam_bri.value())
        v = np.power(v, self.a183mm_cam_gam.value())
        v = np.clip(v,0.0,255.0)
        _frame = cv2.cvtColor(cv2.merge((h,s,v)), cv2.COLOR_HSV2RGB).astype("uint8")

      if self.a183mm_cam_hist_equal.isChecked():
        img_yuv = cv2.cvtColor(_frame, cv2.COLOR_BGR2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        _frame = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

      height, width, channel = _frame.shape

      if self.a183mm_cam_normalize.isChecked():
        l = np.percentile(_frame,self.a183mm_cam_normalize_l.value())
        h = np.percentile(_frame,self.a183mm_cam_normalize_h.value())
        _frame = np.clip((((_frame - l)/(h-l))*255), 0, 255).astype('uint8')

      #b,g,r = cv2.split(_frame)
      #histogram_b, bin_edges_b = np.histogram(b, bins=256, range=(0, 256))
      #histogram_g, bin_edges_g = np.histogram(g, bins=256, range=(0, 256))
      #histogram_r, bin_edges_r = np.histogram(r, bins=256, range=(0, 256))

      #histogram_gray, bin_edges_gray = np.histogram(cv2.cvtColor(_frame, cv2.COLOR_RGB2GRAY), bins=256, range=(0, 256))

      if self.a183mm_cam_circ_d.value() > 0:
        x = self.a183mm_cam_circ_x.value()
        y = self.a183mm_cam_circ_y.value()
        center_coordinates = (x,y)
        radius = self.a183mm_cam_circ_d.value()
        color = (0, 0, 255)
        thickness = 2
        _frame = cv2.circle(_frame, center_coordinates, radius, color, thickness)
        if self.a183mm_cam_circ_c.value() > 0:
          while True:
            radius = radius + self.a183mm_cam_circ_c.value()
            if radius > 1936 or self.a183mm_cam_circ_c.value() == 0:
              break
            _frame = cv2.circle(_frame, center_coordinates, radius, color, thickness)

      self.graphWidget_a183mm.clear()
      #self.graphWidget_a183mm.plot(x=list(range(256)), y=histogram_b, pen=self.hist_pen_b)
      #self.graphWidget_a183mm.plot(x=list(range(256)), y=histogram_g, pen=self.hist_pen_g)
      #self.graphWidget_a183mm.plot(x=list(range(256)), y=histogram_r, pen=self.hist_pen_r)
      #self.graphWidget_a183mm.plot(x=list(range(256)), y=histogram_gray, pen=self.hist_pen_gray)
      bytesPerLine = 3 * width
      qImg = QImage(_frame, width, height, bytesPerLine, QImage.Format_BGR888)
      self.viewer_a183mm.setPhoto(QtGui.QPixmap(qImg))
      cam_settings['a183mm']['disp_frame_time'] = frame['time']

      if self.a183mm_cam_save_img.isChecked():
        frame['dirname'] = str(self.a183mm_cam_save_dirname.text())
        q_a183mm_save_to_file.append(frame)

      if cam_settings['a183mm']['last_rotate'] != cam_settings['a183mm']['rotate']:
        self.viewer_a183mm.fitInView()
        cam_settings['a183mm']['last_rotate'] = cam_settings['a183mm']['rotate']


  def f_a183mm_window_refresh_event(self):
    self.a183mm_photo_reload.click()


  def f_a462mc_window_refresh(self):
    global q_a462mc_ready, viewer_a462mc_deployed, cam_settings, q_a462mc_save_to_file

    if q_a462mc_ready and viewer_a462mc_deployed and q_a462mc_ready:
      frame = q_a462mc_ready.pop()

      if not 'rotate' in cam_settings['a462mc']:
        cam_settings['a462mc']['rotate'] = 0
        cam_settings['a462mc']['last_rotate'] = 0
      if cam_settings['a462mc']['rotate'] == 90:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_CLOCKWISE)
      elif cam_settings['a462mc']['rotate'] == 180:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_180)
      elif cam_settings['a462mc']['rotate'] == 270:
        _frame = cv2.rotate(frame['frameRGB'], cv2.ROTATE_90_COUNTERCLOCKWISE)
      else:
        _frame = frame['frameRGB']

      if self.a462mc_cam_inverse.isChecked():
        _frame = 255 - _frame

      h, s, v = cv2.split(cv2.cvtColor(_frame.astype("float32"), cv2.COLOR_RGB2HSV))
      s = s*self.a462mc_cam_sat.value()
      s = np.clip(s,0.0,255.0)
      v = v + int(self.a462mc_cam_bri.value())
      v = np.power(v, self.a462mc_cam_gam.value())
      v = np.clip(v,0.0,255.0)
      _frame = cv2.cvtColor(cv2.merge((h,s,v)), cv2.COLOR_HSV2RGB).astype("uint8")

      if self.a462mc_cam_hist_equal.isChecked():
        img_yuv = cv2.cvtColor(_frame, cv2.COLOR_RGB2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        _frame = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

      height, width, channel = _frame.shape

      if self.a462mc_cam_normalize.isChecked():
        l = np.percentile(_frame,self.a462mc_cam_normalize_l.value())
        h = np.percentile(_frame,self.a462mc_cam_normalize_h.value())
        _frame = np.clip((((_frame - l)/(h-l))*255), 0, 255).astype('uint8')

      #b,g,r = cv2.split(_frame)
      #histogram_b, bin_edges_b = np.histogram(b, bins=256, range=(0, 256))
      #histogram_g, bin_edges_g = np.histogram(g, bins=256, range=(0, 256))
      #histogram_r, bin_edges_r = np.histogram(r, bins=256, range=(0, 256))
#      histogram_gray, bin_edges_gray = np.histogram(cv2.cvtColor(_frame, cv2.COLOR_RGB2GRAY), bins=256, range=(0, 256))

      if self.a462mc_cam_circ_d.value() > 0:
        x = self.a462mc_cam_circ_x.value()
        y = self.a462mc_cam_circ_y.value()
        center_coordinates = (x,y)
        radius = self.a462mc_cam_circ_d.value()
        color = (0, 0, 255)
        thickness = 2
        _frame = cv2.circle(_frame, center_coordinates, radius, color, thickness)
        if self.a462mc_cam_circ_c.value() > 0:
          while True:
            radius = radius + self.a462mc_cam_circ_c.value()
            if radius > 1936 or self.a462mc_cam_circ_c.value() == 0:
              break
            _frame = cv2.circle(_frame, center_coordinates, radius, color, thickness)


      self.graphWidget_a462mc.clear()
      #self.graphWidget_a462mc.plot(x=list(range(256)), y=histogram_b, pen=self.hist_pen_b)
      #self.graphWidget_a462mc.plot(x=list(range(256)), y=histogram_g, pen=self.hist_pen_g)
      #self.graphWidget_a462mc.plot(x=list(range(256)), y=histogram_r, pen=self.hist_pen_r)
#      self.graphWidget_a462mc.plot(x=list(range(256)), y=histogram_gray, pen=self.hist_pen_gray)
      bytesPerLine = 3 * width
      qImg = QImage(_frame, width, height, bytesPerLine, QImage.Format_BGR888)
      self.viewer_a462mc.setPhoto(QtGui.QPixmap(qImg))
      cam_settings['a462mc']['disp_frame_time'] = frame['time']

      if self.a462mc_cam_save_img.isChecked():
        frame['dirname'] = str(self.a462mc_cam_save_dirname.text())
        q_a462mc_save_to_file.append(frame)

      if cam_settings['a462mc']['last_rotate'] != cam_settings['a462mc']['rotate']:
        self.viewer_a462mc.fitInView()
        cam_settings['a462mc']['last_rotate'] = cam_settings['a462mc']['rotate']


  def f_a462mc_window_refresh_event(self):
    self.a462mc_photo_reload.click()


  def f_ra_natural_refresh(self):
    global telescope_stats, ra_mode_initial_done

    modes = ['OFF', 'STAR', 'SUN', 'MOON']
    try:
      self.ra_mode_status.setText('RA natural status: ' + telescope_stats['ra_natual'])
      if ra_mode_initial_done == False:
        self.ra_mode.setCurrentIndex(modes.index(telescope_stats['ra_natual']))
        ra_mode_initial_done = True
      #if telescope_stats['ra_natual'] != self.ra_mode.currentText():
      #  self.f_ra_natural(index=0)
    except:
      self.ra_mode_status.setText('RA natural status: UNKNOWN')


  def print_telescope_position(self):
    global telescope_stats, connection_ok, last_response_time

    try:
      if telescope_stats != {}:
        self.radec_position1.setText('RA: ' + str(telescope_stats['position']['ra']) + "   DEC: " + str(telescope_stats['position']['dec']))
        self.altaz_position1.setText('AZ: ' + Angle(telescope_stats['position']['az'] * u.deg).to_string(unit=u.deg) + '   ALT: ' + Angle(telescope_stats['position']['alt'] * u.deg).to_string(unit=u.deg))
        self.radec_position.setText('RA: ' + str(telescope_stats['position']['ra']) + "   DEC: " + str(telescope_stats['position']['dec']))
        self.altaz_position.setText('AZ: ' + Angle(telescope_stats['position']['az'] * u.deg).to_string(unit=u.deg) + '   ALT: ' + Angle(telescope_stats['position']['alt'] * u.deg).to_string(unit=u.deg))

    except Exception as e:
      print(traceback.format_exc())
      pass

    if connection_ok:
      state = 'OK'
    else:
      state = 'ERROR'
    resp_ago = time.time() - last_response_time
    self.conn_state1.setText('Conn state: ' + state + ';  Last response: ' + str(format(resp_ago, '.2f')) + 'sec ago')
    self.conn_state.setText('Conn state: ' + state + ';  Last response: ' + str(format(resp_ago, '.2f')) + 'sec ago')
    if telescope_stats != {}:
      self.goto_state1.setText('GOTO moving: ' + str(telescope_stats['goto_working']))
      self.goto_state3.setText('GOTO moving: ' + str(telescope_stats['goto_working']))

  def slider_center(self,axis):
    if axis == 'ra':
      self.ra_slider.setSliderPosition(0)
    elif axis == 'dec':
      self.dec_slider.setSliderPosition(0)
    else:
      self.ost_slider.setSliderPosition(0)

  def radec_move(self):
    if self.dec_sign1.value() < 0:
      signum = '-'
    else:
      signum = ''

    payload = {
      'mode': 'radec',
      'ra': str(self.ra_h1.value()) + 'h' + str(self.ra_m1.value()) + 'm' + str(self.ra_s1.value()) + 's',
      'dec': signum + str(self.dec_d1.value()) + 'd' + str(self.dec_m1.value()) + 'm' + str(self.dec_s1.value()) + 's',
      'move': True,
      'update_pos': True
    }
    req_cmd.put(payload)

  def altaz_move(self):
    payload = {
      'mode': 'altaz',
      'az': str(self.az_d1.value()) + 'd' + str(self.az_m1.value()) + 'm',
      'alt': str(self.elev_d1.value()) + 'd' + str(self.elev_m1.value()) + 'm',
      'move': True,
      'update_pos': True
    }
    req_cmd.put(payload)

  def goto_object_find(self):
    ob = self.obj_name.text()
    if ob:
      out = requests.get('http://localhost:8090/api/objects/info?name=' + ob + '&format=map')
      if out.status_code == 200:
        data = json.loads(out.text)
        l1 = 'AZ: ' + format(data['azimuth'],'.4f') + " ALT: " + format(data['altitude'],'.4f')
        l2 = ob + '=' + data['localized-name']
      else:
        l1 = "ERR Resp: " + str(out.status_code)
        l2 = "NULL"
    else:
      l1 = "ERR"
      l2 = "NULL"

    self.obj_name_goto_info1.setText(l1)
    self.obj_name_goto_info2.setText(l2)

  def goto_object_go(self):
    ob = self.obj_name.text()
    if ob:
      out = requests.get('http://localhost:8090/api/objects/info?name=' + ob + '&format=map')
      if out.status_code == 200:
        data = json.loads(out.text)
        l1 = 'GOTO AZ: ' + format(data['azimuth'],'.4f') + " ALT: " + format(data['altitude'],'.4f')
        l2 = ob + '=' + data['localized-name']
        az = Angle(data['azimuth']*u.deg)
        alt = Angle(data['altitude']*u.deg)
        az_str = str(int(az.dms.d)) + 'd' + str(int(abs(az.dms.m))) + 'm' + str(int(abs(az.dms.s))) + 's'
        alt_str = str(int(alt.dms.d)) + 'd' + str(int(abs(alt.dms.m))) + 'm' + str(int(abs(alt.dms.s))) + 's'
        payload = {
          'mode': 'altaz',
          'alt': alt_str,
          'az': az_str,
          'move': True,
          'update_pos': True
        }
        req_cmd.put(payload)
      else:
        l1 = "ERR Resp: " + str(out.status_code)
        l2 = "NULL"
    else:
      l1 = "ERR"
      l2 = "NULL"

    self.obj_name_goto_info1.setText(l1)
    self.obj_name_goto_info2.setText(l2)

  def goto_object_set(self):
    ob = self.obj_name.text()
    if ob:
      out = requests.get('http://localhost:8090/api/objects/info?name=' + ob + '&format=map')
      if out.status_code == 200:
        data = json.loads(out.text)
        l1 = 'SET AZ: ' + format(data['azimuth'],'.4f') + " ALT: " + format(data['altitude'],'.4f')
        l2 = ob + '=' + data['localized-name']
        az = Angle(data['azimuth']*u.deg)
        alt = Angle(data['altitude']*u.deg)
        az_str = str(int(az.dms.d)) + 'd' + str(int(abs(az.dms.m))) + 'm' + str(int(abs(az.dms.s))) + 's'
        alt_str = str(int(alt.dms.d)) + 'd' + str(int(abs(alt.dms.m))) + 'm' + str(int(abs(alt.dms.s))) + 's'
        payload = {
          'mode': 'altaz',
          'alt': alt_str,
          'az': az_str,
          'move': False,
          'update_pos': True
        }
        req_cmd.put(payload)
      else:
        l1 = "ERR Resp: " + str(out.status_code)
        l2 = "NULL"
    else:
      l1 = "ERR"
      l2 = "NULL"

    self.obj_name_goto_info1.setText(l1)
    self.obj_name_goto_info2.setText(l2)

  def get_telescope_position_tab1(self):
    global telescope_stats
    if Angle(telescope_stats['position']['dec']).dms.d < 0:
      self.dec_sign1.setValue(-1)
      self.dec_d1.setValue(-1 * int(Angle(telescope_stats['position']['dec']).dms.d))
    else:
      self.dec_sign1.setValue(1)
      self.dec_d1.setValue(int(Angle(telescope_stats['position']['dec']).dms.d))

    self.ra_h1.setValue(int(Angle(telescope_stats['position']['ra']).hms.h))
    self.ra_m1.setValue(int(Angle(telescope_stats['position']['ra']).hms.m))
    self.ra_s1.setValue(int(Angle(telescope_stats['position']['ra']).hms.s))
    self.dec_m1.setValue(int(Angle(telescope_stats['position']['dec']).dms.m))
    self.dec_s1.setValue(int(Angle(telescope_stats['position']['dec']).dms.s))
    self.az_d1.setValue(int(Angle(telescope_stats['position']['az']*u.deg).dms.d))
    self.az_m1.setValue(int(Angle(telescope_stats['position']['az']*u.deg).dms.m))
    self.elev_d1.setValue(int(Angle(telescope_stats['position']['alt']*u.deg).dms.d))
    self.elev_m1.setValue(int(Angle(telescope_stats['position']['alt']*u.deg).dms.m))

  def get_telescope_position_tab3(self):
    global telescope_stats
    if Angle(telescope_stats['position']['dec']).dms.d < 0:
      self.dec_sign3.setValue(-1)
      self.dec_d.setValue(-1 * int(Angle(telescope_stats['position']['dec']).dms.d))
    else:
      self.dec_sign3.setValue(1)
      self.dec_d.setValue(int(Angle(telescope_stats['position']['dec']).dms.d))

    self.ra_h.setValue(int(Angle(telescope_stats['position']['ra']).hms.h))
    self.ra_m.setValue(int(Angle(telescope_stats['position']['ra']).hms.m))
    self.ra_s.setValue(int(Angle(telescope_stats['position']['ra']).hms.s))
    self.dec_d.setValue(int(Angle(telescope_stats['position']['dec']).dms.d))
    self.dec_m.setValue(int(Angle(telescope_stats['position']['dec']).dms.m))
    self.dec_s.setValue(int(Angle(telescope_stats['position']['dec']).dms.s))
    self.az_d.setValue(int(Angle(telescope_stats['position']['az']*u.deg).dms.d))
    self.az_m.setValue(int(Angle(telescope_stats['position']['az']*u.deg).dms.m))
    self.elev_d.setValue(int(Angle(telescope_stats['position']['alt']*u.deg).dms.d))
    self.elev_m.setValue(int(Angle(telescope_stats['position']['alt']*u.deg).dms.m))

  def radec_set(self):
    if self.dec_sign3.value() < 0:
      signum = '-'
    else:
      signum = ''

    payload = {
      'mode': 'radec',
      'ra': str(self.ra_h.value()) + 'h' + str(self.ra_m.value()) + 'm' + str(self.ra_s.value()) + 's',
      'dec': signum + str(self.dec_d.value()) + 'd' + str(self.dec_m.value()) + 'm' + str(self.dec_s.value()) + 's',
      'move': False,
      'update_pos': True
    }
    req_cmd.put(payload)

  def altaz_set(self):
    payload = {
      'mode': 'altaz',
      'az': str(self.az_d.value()) + 'd' + str(self.az_m.value()) + 'm',
      'alt': str(self.elev_d.value()) + 'd' + str(self.elev_m.value()) + 'm',
      'move': False,
      'update_pos': True
    }
    req_cmd.put(payload)


  def goto_180_25(self):
    payload = {
      'mode': 'altaz',
      'alt': '25d00m',
      'az': '180d00m',
      'move': True,
      'update_pos': True
    }
    req_cmd.put(payload)

  def goto_90_25(self):
    payload = {
      'mode': 'altaz',
      'alt': '25d00m',
      'az': '90d00m',
      'move': True,
      'update_pos': True
    }
    req_cmd.put(payload)

  def goto_143_40_23_40(self):
    payload = {
      'mode': 'altaz',
      'alt': '23d40m',
      'az': '143d40m',
      'move': True,
      'update_pos': True
    }
    req_cmd.put(payload)

  def goto_171_10_6_20(self):
    payload = {
      'mode': 'altaz',
      'alt': '6d20m',
      'az': '171d10m',
      'move': True,
      'update_pos': True
    }
    req_cmd.put(payload)

  def goto_zenith(self):
    payload = {
      'mode': 'altaz',
      'alt': '89d59m',
      'az': '180d0m',
      'move': True,
      'update_pos': True
    }
    req_cmd.put(payload)

  def joystick_up(self):
    self.joystick_arc.setText(str(float(self.joystick_arc.text())))
    payload = {
      'mode': 'joystick',
      'side': 'up',
      'angle': float(self.joystick_arc.text()),
    }
    req_cmd.put(payload)

  def joystick_down(self):
    self.joystick_arc.setText(str(float(self.joystick_arc.text())))
    payload = {
      'mode': 'joystick',
      'side': 'down',
      'angle': float(self.joystick_arc.text()),
    }
    req_cmd.put(payload)

  def joystick_left(self):
    self.joystick_arc.setText(str(float(self.joystick_arc.text())))
    payload = {
      'mode': 'joystick',
      'side': 'left',
      'angle': float(self.joystick_arc.text()),
    }
    req_cmd.put(payload)

  def joystick_right(self):
    global req_cmd
    self.joystick_arc.setText(str(float(self.joystick_arc.text())))
    payload = {
      'mode': 'joystick',
      'side': 'right',
      'angle': float(self.joystick_arc.text()),
    }
    req_cmd.put(payload)

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

  def set_zenith(self):
    payload = {
      'mode': 'altaz',
      'alt': '90d00m',
      'az': '00d00m',
      'move': False,
      'update_pos': True
    }
    req_cmd.put(payload)

  def f_ra_natural(self, index):
    payload = {
      'mode': 'ra_natural',
      'speed': self.ra_mode.currentText(),
    }
    req_cmd.put(payload)


  def f_ra_slider(self, value):
    global req_cmd
    payload = {
      'mode': 'ra_manual',
      'speed': -1 * value,
    }
    req_cmd.put(payload)

  def f_dec_slider(self, value):
    global req_cmd
    payload = {
      'mode': 'dec_manual',
      'speed': -1 * value,
    }
    req_cmd.put(payload)

  def f_ost_slider(self, value):
    global req_cmd
    payload = {
      'mode': 'ost_manual',
      'speed': value,
    }
    req_cmd.put(payload)

  def f_update_battery_state(self):
    global telescope_stats

    if telescope_stats != {}:
      self.lab_bat1_state.setText("State: "     + str(telescope_stats['battery']['1']['state']))
      self.lab_bat1_voltage.setText("Voltage: " + str(telescope_stats['battery']['1']['voltage'])   + 'V')
      self.lab_bat1_current.setText("Current: " + str(telescope_stats['battery']['1']['current'])   + 'A')
      self.lab_bat1_capacity.setText("Used: "   + str(format(telescope_stats['battery']['1']['used'], '.2f')) + 'mAh')

      self.lab_bat2_state.setText("State: "     + str(telescope_stats['battery']['2']['state']))
      self.lab_bat2_voltage.setText("Voltage: " + str(telescope_stats['battery']['2']['voltage'])   + 'V')
      self.lab_bat2_current.setText("Current: " + str(telescope_stats['battery']['2']['current'])   + 'A')
      self.lab_bat2_capacity.setText("Used: "   + str(format(telescope_stats['battery']['2']['used'], '.2f')) + 'mAh')

      self.lab_bat3_state.setText("State: "     + str(telescope_stats['battery']['3']['state']))
      self.lab_bat3_voltage.setText("Voltage: " + str(telescope_stats['battery']['3']['voltage'])   + 'V')
      self.lab_bat3_current.setText("Current: " + str(telescope_stats['battery']['3']['current'])   + 'A')
      self.lab_bat3_capacity.setText("Used: "   + str(format(telescope_stats['battery']['3']['used'], '.2f')) + 'mAh')

      self.lab_bat4_state.setText("State: "     + str(telescope_stats['battery']['4']['state']))
      self.lab_bat4_voltage.setText("Voltage: " + str(telescope_stats['battery']['4']['voltage'])   + 'V')
      self.lab_bat4_current.setText("Current: " + str(telescope_stats['battery']['4']['current'])   + 'A')
      self.lab_bat4_capacity.setText("Used: "   + str(format(telescope_stats['battery']['4']['used'], '.2f')) + 'mAh')

  def f_bat1_auto(self):
   self.f_bat_options_common(battery=1, bat_val='AUTO')

  def f_bat1_forced_on(self):
   self.f_bat_options_common(battery=1, bat_val='FORCED ON')

  def f_bat1_forced_off(self):
   self.f_bat_options_common(battery=1, bat_val='FORCED OFF')

  def f_bat2_auto(self):
   self.f_bat_options_common(battery=2, bat_val='AUTO')

  def f_bat2_forced_on(self):
   self.f_bat_options_common(battery=2, bat_val='FORCED ON')

  def f_bat2_forced_off(self):
   self.f_bat_options_common(battery=2, bat_val='FORCED OFF')

  def f_bat3_auto(self):
   self.f_bat_options_common(battery=3, bat_val='AUTO')

  def f_bat3_forced_on(self):
   self.f_bat_options_common(battery=3, bat_val='FORCED ON')

  def f_bat3_forced_off(self):
   self.f_bat_options_common(battery=3, bat_val='FORCED OFF')

  def f_bat4_auto(self):
   self.f_bat_options_common(battery=4, bat_val='AUTO')

  def f_bat4_forced_on(self):
   self.f_bat_options_common(battery=4, bat_val='FORCED ON')

  def f_bat4_forced_off(self):
   self.f_bat_options_common(battery=4, bat_val='FORCED OFF')

  def f_bat_options_common(self,battery, bat_val):
    global req_cmd
    payload = {
      'mode': 'battery',
      'set': bat_val,
      'battery': battery,
    }
    req_cmd.put(payload)

  def f_bat_zero_mah(self):
    global req_cmd
    payload = {
      'mode': 'battery',
      'set': 'zero_mah',
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


app = QApplication(sys.argv)
screen = Window()

thread_list = []

t = threading.Thread(target=f_requests_send)
thread_list.append(t)

t = threading.Thread(target=f_get_telescope_stats)
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

t = threading.Thread(target=f_photo_refresh)
thread_list.append(t)

t = threading.Thread(target=f_a462mc_frame_processing)
thread_list.append(t)

t = threading.Thread(target=f_a183mm_frame_processing)
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

t = threading.Thread(target=f_guiding_proc)
thread_list.append(t)

t = threading.Thread(target=f_canon_plate_solve_loop)
thread_list.append(t)

t = threading.Thread(target=f_a462mc_settings)
thread_list.append(t)

t = threading.Thread(target=f_a183mm_settings)
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
