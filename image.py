import matplotlib.pyplot as pyplot
import numpy as numpy
import tensorflow as tensorflow

import tensorflow_datasets as tfds

import time
import socket

from model_layout import modelLayout


# Scaled value = raw value * scale
scale = 16 / 256
min_ms_between_pulses = 15

# Window size is milliseconds between packets - buffer contains spike times for the full window
window = 250

conversionMap = {}

index_10x10_conversion = [
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81],
  [71, 42, 43, 44, 45,  46, 47, 48, 49, 82],
  [70, 41, 29, 21, 22,  23, 24, 25, 50, 83],
  [69, 40, 19,  6,  7,   8,  9, 26, 51, 84],
  [68, 39, 18,  5, 00,   1, 10, 27, 52, 85],

  [67, 38, 17,  4,  3,   2, 11, 28, 53, 86],
  [66, 37, 16, 15, 14,  13, 12, 28, 54, 87],
  [65, 36, 35, 34, 33,  32, 31, 30, 55, 88],
  [64, 63, 62, 61, 60,  59, 58, 57, 56, 89],
  [99, 98, 97, 96, 95,  94, 93, 92, 91, 90]
]

index_28x28_conversion = [
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],

  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 196, 255, 254,  253, 252, 251, 250, 249,  248, 247, 246, 245, 244,  243, 242, 241, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 197, 144, 195,  194, 193, 192, 191, 190,  189, 188, 187, 186, 185,  184, 183, 240, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 198, 145, 100,  143, 142, 141, 140, 139,  138, 137, 136, 135, 134,  133, 182, 239, 75, 76,  77, 78, 79],

  [72, 73, 74, 75, 76,  77, 78, 199, 146, 101,   64,  99,  98,  97,  96,   95,  94,  93,  92,  91,  132, 181, 238, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 200, 147, 102,   65,  36,  63,  62,  61,   60,  59,  58,  57,  90,  131, 180, 237, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 201, 148, 103,   66,  37,  16,  35,  34,   33,  32,  31,  56,  89,  130, 179, 236, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 202, 149, 104,   67,  38,  17,   4,  15,   14,  13,  30,  55,  88,  129, 178, 235, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 203, 150, 105,   68,  39,  18,   5,  00,    3,  12,  29,  54,  87,  128, 177, 234, 75, 76,  77, 78, 79],

  [72, 73, 74, 75, 76,  77, 78, 204, 151, 106,   69,  40,  19,   6,   1,    2,  11,  28,  53,  86,  127, 176, 233, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 205, 152, 107,   70,  41,  20,   7,   8,    9,  10,  27,  52,  85,  126, 175, 232, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 206, 153, 108,   71,  42,  21,  22,  23,   24,  25,  26,  51,  84,  125, 174, 231, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 207, 154, 109,   72,  43,  44,  45,  46,   47,  48,  49,  50,  83,  124, 173, 230, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 208, 155, 110,   73,  74,  75,  76,  77,   78,  79,  80,  81,  82,  123, 172, 229, 75, 76,  77, 78, 79],

  [72, 73, 74, 75, 76,  77, 78, 209, 156, 111,  112, 113, 114, 115, 116,  117, 118, 119, 120, 121,  122, 171, 228, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 210, 157, 158,  159, 160, 161, 162, 163,  164, 165, 166, 167, 168,  169, 170, 227, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 211, 212, 213,  214, 215, 216, 217, 218,  219, 220, 221, 222, 223,  224, 225, 226, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],

  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79],
  [72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79, 80, 81,  72, 73, 74, 75, 76,  77, 78, 79]
]

def pretty_print(image):
  for i in range(0, image.shape[0]):
    line = []
    for j in range(0, image.shape[1]):
      line.append(image[i][j][0])

    print(line)

def frequency_encode(neuron_index, excitation):
  buffer = []
  if excitation > 0:
    ms_between_pulses = scale * (256 - excitation) + min_ms_between_pulses
    time_offset = 0
    while time_offset < window:
      buffer.append([int(time_offset), neuron_index])
      time_offset += ms_between_pulses

  return buffer

def get_min_max(size):
  margin = size - 10
  if margin < 0:
    margin = 0
  margin //= 2
  min = int(margin)
  max = size - int(margin) - 1
  if margin > 0 and max - min < 9:
    max += 1

  return min, max

def encode_image(image):
  buffer = []

  min_i, max_i = get_min_max(image.shape[0])
  min_j, max_j = get_min_max(image.shape[1])

  for i in range(min_i, max_i):
    for j in range(min_j, max_j):
      excitation = int(image[i][j][0])
      if excitation > 0:
        neuron_index = index_10x10_conversion[i-min_i][j-min_j]
        neuron_buffer = frequency_encode(neuron_index, excitation)
        buffer.extend(neuron_buffer)

  return buffer



def encode_image2(image):
  buffer = []
  conversion_map = None

  neuron_count = image.shape[0] * image.shape[1]
  if neuron_count not in conversionMap.keys():
    layout_engine = modelLayout('')
    conversionMap[neuron_count] = layout_engine.layoutSquare(neuron_count, [int(image.shape[0] / 2) - 1, 0, int(image.shape[1] / 2) - 1])

  conversion_map = conversionMap[neuron_count]
  for i in range(neuron_count):
    x, _, y = conversion_map[i]
    excitation = int(image[x][y][0])
    neuron_buffer = frequency_encode(i, excitation)
    buffer.extend(neuron_buffer)

  return buffer

ds = tfds.load('mnist', split='train', as_supervised=True)
ds = ds.take(20)

HOST = '192.168.1.142'  # The server's hostname or IP address
PORT = 8001             # The port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
  s.connect((HOST, PORT))

  print('Image:')
  for image, label in tfds.as_numpy(ds):

    print(image.shape, label)
    pretty_print(image)

    buffer = encode_image2(image)

    pair_count = len(buffer)
    print('Buffer contains ' + str(pair_count) + ' spikes')
    rawbytes = bytearray()
    rawbytes.append(pair_count & 0xff)
    rawbytes.append(pair_count >> 8 & 0xff)

    # WARNING: If buffer is 8192 or greater in length, the resulting packet
    # will exceed 64K bytes, and will overflow the receiving C++ buffer.
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