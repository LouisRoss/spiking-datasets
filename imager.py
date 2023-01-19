import matplotlib.pyplot as pyplot
import numpy as numpy
import tensorflow as tensorflow

import tensorflow_datasets as tfds

import time
import socket
import math

from model_layout import modelLayout
from support.model_framework import ModelFramework



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

measurements = None
results = None

def run_image(rawbytes):
  global measurements
  global results

  with ModelFramework('Research4.lan', 10000, 'mnist-2', 'normal') as model:
    model.deploy(log_enable=False, record_enable=True, record_synapse_enable=True, record_activation=True, record_hypersensitive=True)
    for i in range(20):
      model.send_spikes(rawbytes)
      model.run_for_ticks(250)

    measurements = model.undeploy()
    results = model.results

ds = tfds.load('mnist', split='train', as_supervised=True)
ds = ds.take(1)

print('Image:')
for image, label in tfds.as_numpy(ds):

  print(image.shape, label)
  pretty_print(image)

  buffer = encode_image(image)

  print('Buffer contains ' + str(len(buffer)) + ' spikes')
  run_image(buffer)

  #print('Done')