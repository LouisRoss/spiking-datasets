import json
import socket
import select
from struct import *


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

    # WARNING: If buffer is 8192 or greater in length, the resulting packet
    # will exceed 64K bytes, and will overflow the receiving C++ buffer.
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

