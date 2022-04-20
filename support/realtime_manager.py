from curses import window
import time
import math
import json
import socket
import select
from struct import *

class BufferManager:
  _window = 250
  _min_ms_between_pulses = 15
  _frequency_map = None

  def __init__(self, window):
    BufferManager._window = window

  def get_frequency_map():
    if (BufferManager._frequency_map == None):
      BufferManager._frequency_map = []
      for excitation in range(256):
        BufferManager._frequency_map.append(round(math.exp(-0.015 * excitation) * BufferManager._window))

    return BufferManager._frequency_map

  def frequency_encode(neuron_index, excitation):
    buffer = []
    fmap = BufferManager.get_frequency_map()

    if excitation > 0:
      #ms_between_pulses = scale * (256 - excitation) + min_ms_between_pulses
      ms_between_pulses = max(fmap[excitation], BufferManager.min_ms_between_pulses)
      time_offset = ms_between_pulses / 2
      while time_offset <= window:
        buffer.append([int(time_offset), neuron_index])
        time_offset += ms_between_pulses

    return buffer


class RealtimeManager:
  engine = ''
  host = ''

  def __init__(self, engine):
    self.engine = engine
    self.socket = None

    f = open('/configuration/settings.json')
    self.settings = json.load(f)
    self.host = next((e["host"] for e in self.settings["engines"] if e["name"] == engine), None)
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  def __enter__(self):
    self.socket.connect((self.host, 8001))
    return self

  def __exit__(self, type, value, traceback):
    self.socket.close()
    return True   # Suppress propagation of any exception that occurred in the caller.

  def SendSpikes(self, spikes):
    pair_count = len(spikes)
    print('Spikes buffer contains ' + str(pair_count) + ' spikes')
    rawbytes = bytearray()
    rawbytes.append(pair_count & 0xff)
    rawbytes.append(pair_count >> 8 & 0xff)
    rawbytes.append(pair_count >> 16 & 0xff)
    rawbytes.append(pair_count >> 24 & 0xff)

    # WARNING: If buffer is 8192 or greater in length, the resulting packet
    # will exceed 64K bytes, and will overflow the receiving C++ buffer.
    # NOTE: After changing the spike counter to a 32-bit int, this does not seem to be an issue.
    #       I don't see why this affects things, so am leaving the note above in place.
    for spike in spikes:
      rawbytes.append(spike[0] & 0xff)
      rawbytes.append(spike[0] >> 8 & 0xff)
      rawbytes.append(spike[0] >> 16 & 0xff)
      rawbytes.append(spike[0] >> 24 & 0xff)
      rawbytes.append(spike[1] & 0xff)
      rawbytes.append(spike[1] >> 8 & 0xff)
      rawbytes.append(spike[1] >> 16 & 0xff)
      rawbytes.append(spike[1] >> 24 & 0xff)

    self.socket.sendall(rawbytes)

  def make_spike_packet(self, spikes):
    pair_count = len(spikes)
    print(f'Spikes buffer contains {pair_count:d} spikes')

    rawbytes = bytearray()
    rawbytes.append(pair_count & 0xff)
    rawbytes.append(pair_count >> 8 & 0xff)
    rawbytes.append(pair_count >> 16 & 0xff)
    rawbytes.append(pair_count >> 24 & 0xff)

    # WARNING: If buffer is 8192 or greater in length, the resulting packet
    # will exceed 64K bytes, and will overflow the receiving C++ buffer.
    # NOTE: After changing the spike counter to a 32-bit int, this does not seem to be an issue.
    #       I don't see why this affects things, so am leaving the note above in place.
    for spike in spikes:
      rawbytes.append(spike[0] & 0xff)
      rawbytes.append(spike[0] >> 8 & 0xff)
      rawbytes.append(spike[0] >> 16 & 0xff)
      rawbytes.append(spike[0] >> 24 & 0xff)
      rawbytes.append(spike[1] & 0xff)
      rawbytes.append(spike[1] >> 8 & 0xff)
      rawbytes.append(spike[1] >> 16 & 0xff)
      rawbytes.append(spike[1] >> 24 & 0xff)

    return rawbytes

  def send_spikes_repeat(self, spikes, period, repeats):
    rawbytes = self.make_spike_packet(spikes)

    for i in range(repeats):
      print(f'Iteration {i:d}')
      self.socket.sendall(rawbytes)

      time.sleep(period)

  def send_spikes(self, spikes):
    rawbytes = self.make_spike_packet(spikes)
    self.socket.sendall(rawbytes)


