import sys
import json

from support.realtime_manager import RealtimeManager,BufferManager

def parse_args():
  filename = ''
  repeats = 250
  period = 250    # microseconds
  multiples = 1
  step = 0

  if len(sys.argv) < 2:
    print(f'Usage: {sys.argv[0]} <filename> [repeats] [period(ms)] [multiples] [step(indexes)]')
    return False, filename, repeats, period, multiples, step

  if len(sys.argv) > 1:
    filename = sys.argv[1]
  
  if len(sys.argv) > 2:
    repeats = int(sys.argv[2])
  
  if len(sys.argv) > 3:
    period = int(sys.argv[3])

  if len(sys.argv) > 4:
    multiples = int(sys.argv[4])

  if len(sys.argv) > 5:
    step = int(sys.argv[5])
  
  print(f'Expanding file {filename} {multiples:d} times at offsets of {step:d}.  Sending the resulting expansion {repeats:d} times, repeating every {period:d} milliseconds')
  return True, filename, repeats, period, multiples, step


def load_pattern(filename):
  # A return variable
  spikepattern = []

  # Load the specified json file.
  f = open(filename)
  settings = json.load(f)

  # Get the spike pattern array from the file if present.
  if 'spikepattern' in settings:
    spikepattern = settings['spikepattern']

  # If a neuron assignments dictionary exists, use it to translate neuron symbols to indexes.
  if 'neuronassignments' in settings:
    neuronassignments = settings['neuronassignments']
    for spike in spikepattern:
      if spike[1] in neuronassignments:
        spike[1] = neuronassignments[spike[1]]

  print(spikepattern)
  return spikepattern


def step_multiple(singleSpikePattern, step, multiple):
  """ Given a single instance of the spike pattern, 
      plus the step distance between patterns and a multiple count,
      copy the pattern to the 'multple' number of
      places, separated by 'step' indices.
  """
  fullSpikePattern = []
  for i in range(multiple):
    offset = i * step
    for spikePattern in singleSpikePattern:
      fullSpikePattern.append([spikePattern[0], spikePattern[1] + offset])

  print(fullSpikePattern)
  return fullSpikePattern



if __name__ == "__main__":
  success, filename, repeats, period, multiple, step = parse_args()
  if not success:
    sys.exit()

  spikepattern = load_pattern(filename)
  fullSpikePattern = step_multiple(spikepattern, step, multiple)
  with RealtimeManager('Research1') as realtime:
    realtime.send_spikes_repeat(fullSpikePattern, period / 1000, repeats)