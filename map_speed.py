import csv
from anticipate_runner import AnticipateRunner
from analysis.anticipate_record import AnticipateEvent

testEngine = 'Research1'
testEpochs = 50

def run(engine_period, neuron_count):
  runner = AnticipateRunner(testEngine, engine_period, [neuron_count, 1], log_enable=False, record_enable=False, record_synapse_enable=False)
  runner.run(testEpochs)
  return runner.measurements


def extractTicksAndDuration(measurements):
    start_event = AnticipateEvent()
    start_event.parse_time(measurements['runmeasurements']['enginestarttime'])
    start_time = start_event.to_delta()

    stop_event = AnticipateEvent()
    stop_event.parse_time(measurements['runmeasurements']['enginestoptime'])
    end_time = stop_event.to_delta()

    run_time = end_time - start_time
    run_duration_us = run_time.seconds * 1000000 + run_time.microseconds
    run_ticks = int(measurements['runmeasurements']['iterations'])

    return run_ticks, run_duration_us

def map():
  results = []
  neuron_count = 4000
  for period in range(250, 1100, 50):
    measurements = run(period, neuron_count)
    tick, duration = extractTicksAndDuration(measurements)
    results.append([neuron_count, period, tick, duration])

def map2(neuron_count):
  results = []
  target_tick = 5000
  delta_tick = -500
  succeeded_count = 0
  failed_count = 0
  while failed_count < 4:
    measurements = run(target_tick, neuron_count)
    tick, duration = extractTicksAndDuration(measurements)
    result = [neuron_count, target_tick, tick, duration]
    results.append(result)
    success = abs(1 - result[1]/(result[3]/result[2])) < 0.1
    if success:
      print('Succeeded with target tick ' + str(target_tick))
      succeeded_count += 1
      if delta_tick >= 0:
        delta_tick /= -2
    else:
      print('failed with target tick ' + str(target_tick))
      failed_count += 1
      if delta_tick < 0:
        delta_tick /= -2

    target_tick += delta_tick
    print('Using ' + str(neuron_count) + ' neurons, changing target tick to ' + str(target_tick))
  
  return results

def map3(neuron_count):
  results = []
  target_tick = 200
  measurements = run(target_tick, neuron_count)
  tick, duration = extractTicksAndDuration(measurements)
  result = [neuron_count, target_tick, tick, duration]
  results.append(result)
  
  return results

def analyze():
  results = []
  for neuron_count in range(4000, 10000, 500):
    count_results = map3(neuron_count)
    for result in count_results:
      results.append(result)

  print('Test results')
  print('------------')

  for result in results:
    count = result[0]
    period = result[1]
    ticks = result[2]
    duration_us = result[3]
    duration_ms = duration_us / 1000.0
    tick_duration_ms = duration_ms / ticks
    tick_duration_us = duration_us / ticks
    success = abs(1 - period/tick_duration_us) < 0.1
    
    print(f'{count:5d} Neurons with target tick {period:4.4f} us:    {duration_ms:.3f} ms / {ticks:.4f} ticks = {tick_duration_ms:.3f} ms/tick => {success}')

  with open('/record/speed_vs_size.csv', 'w', newline='') as csvfile:
    resultwriter = csv.writer(csvfile)
    resultwriter.writerow(['neuron count', 'target tick us', 'actual tick count', 'actual duration'])
    for result in results:
      resultwriter.writerow(result)

analyze()
