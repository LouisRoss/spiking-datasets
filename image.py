import matplotlib.pyplot as pyplot
import numpy as numpy
import tensorflow as tensorflow

import tensorflow_datasets as tfds

import time
import socket
import math

from model_layout import modelLayout


# Scaled value = raw value * scale
scale = 16 / 256
min_ms_between_pulses = 15

# Window size is milliseconds between packets - buffer contains spike times for the full window
window = 250

conversionMap = {}


def pretty_print(image):
  for i in range(0, image.shape[0]):
    line = ''
    for j in range(0, image.shape[1]):
      line += '{ex:3d} '.format(ex = image[i][j][0])

    print(line)

frequencyMap = None
def get_frequency_map():
  global frequencyMap
  if (frequencyMap == None):
    frequencyMap = []
    for excitation in range(256):
      frequencyMap.append(round(math.exp(-0.015 * excitation) * window))

  return frequencyMap

def frequency_encode(neuron_index, excitation):
  buffer = []
  fmap = get_frequency_map()

  if excitation > 0:
    #ms_between_pulses = scale * (256 - excitation) + min_ms_between_pulses
    ms_between_pulses = max(fmap[excitation], min_ms_between_pulses)
    time_offset = ms_between_pulses / 2
    while time_offset <= window:
      buffer.append([int(time_offset), neuron_index])
      time_offset += ms_between_pulses

  return buffer


def encode_image(image):
  buffer = []
  conversion_map = None

  neuron_count = image.shape[0] * image.shape[1]
  if neuron_count not in conversionMap.keys():
    layout_engine = modelLayout('')
    #conversionMap[neuron_count] = layout_engine.layoutSquare(neuron_count, [int(image.shape[0] / 2) - 1, 0, int(image.shape[1] / 2) - 1])
    conversionMap[neuron_count] = layout_engine.layoutRasterSquare([image.shape[0], image.shape[1]], [int(image.shape[0] / 2), 0, int(image.shape[1] / 2)])

  conversion_map = conversionMap[neuron_count]
  for i in range(neuron_count):
    x, _, y = conversion_map[i]
    excitation = int(image[x][y][0])
    neuron_buffer = frequency_encode(i, excitation)
    buffer.extend(neuron_buffer)

  return buffer

ds = tfds.load('mnist', split='train', as_supervised=True)
#ds = ds.take(20)

HOST = '192.168.1.142'  # The server's hostname or IP address
PORT = 8001             # The port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
  s.connect((HOST, PORT))

  print('Image:')
  for image, label in tfds.as_numpy(ds):

    print(image.shape, label)
    pretty_print(image)

    buffer = encode_image(image)

    pair_count = len(buffer)
    print('Buffer contains ' + str(pair_count) + ' spikes')
    rawbytes = bytearray()
    rawbytes.append(pair_count & 0xff)
    rawbytes.append(pair_count >> 8 & 0xff)
    rawbytes.append(pair_count >> 16 & 0xff)
    rawbytes.append(pair_count >> 24 & 0xff)

    # WARNING: If buffer is 8192 or greater in length, the resulting packet
    # will exceed 64K bytes, and will overflow the receiving C++ buffer.
    # NOTE - this may not be true after extending the pair count to 32 bits.
    for spike in buffer:
      rawbytes.append(spike[0] & 0xff)
      rawbytes.append(spike[0] >> 8 & 0xff)
      rawbytes.append(spike[0] >> 16 & 0xff)
      rawbytes.append(spike[0] >> 24 & 0xff)
      rawbytes.append(spike[1] & 0xff)
      rawbytes.append(spike[1] >> 8 & 0xff)
      rawbytes.append(spike[1] >> 16 & 0xff)
      rawbytes.append(spike[1] >> 24 & 0xff)

    for i in range(0, 20):
      print('Iteration ' + str(i))
      s.sendall(rawbytes)
      time.sleep(0.250)

  #print('Done')