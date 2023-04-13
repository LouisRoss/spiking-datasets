import inspect

def stepAndRepeat(singleSpikePattern, step, repeat):
  """ Given a single instance of the expansion pattern and corresponding spike pattern, 
      plus the stepping distance between patterns and a repeat count,
      copy the expansion pattern to the 'repeat' number of
      places, separated by 'step' indices.
  """
  fullSpikePattern = []
  for i in range(repeat):
    offset = i * step
    for spikePattern in singleSpikePattern:
      fullSpikePattern.append([spikePattern[0], spikePattern[1] + offset])

  print("Single spike pattern, full spike pattern:")
  print(singleSpikePattern)
  print(fullSpikePattern)
  return fullSpikePattern

def templateNeuronCount(template):
    totalCount = 0
    populations = template["neurons"]
    for population in populations:
      count = 1
      for dim in population["dims"]:
        count *= dim
      totalCount += count
    
    return totalCount
  
def extract_monitor_neurons(configuration, neurons, filter_list=None):
  monitor_neurons = []

  neurons_dict = neurons.__dict__

  for deployment in configuration.get_deployment_map():
    deployment_offset =  + int(deployment['offset'])
    if filter_list:
      for filter_neuron in filter_list:
        if filter_neuron in neurons_dict:
          monitor_neurons.append([filter_neuron, neurons_dict[filter_neuron] + deployment_offset])
    else:
      for key, value in neurons_dict.items():
        if not key.startswith('__') and not inspect.ismethod(value):
          monitor_neurons.append([key, value + deployment_offset])

  return monitor_neurons
