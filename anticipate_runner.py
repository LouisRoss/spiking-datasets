import math

""" Test 1.  The simple anticipate test.
    Configure a small microcircuit with inputs I1 and I2,
    and outputs N1 and N2.  I1 always precedes I2 by a few
    milliseconds.  Show that the network adapts so that output
    N2 anticiaptes input I2, even if it does not occur.
"""

from support.model_framework import ModelFramework

template = {
  "method": "projection",
  "neurons": [
    {
      "name": "input",
      "dims": [10, 10],
      "height": 0,
      "import": 0.2,
      "export": 0.0
    }
  ],
  "policies": []
}

class NeuronAssignments:
  In1 = 1
  In2 = 2
  I1 = 3
  I2 = 4
  Inh1 = 5
  Inh2 = 6
  N1 = 7
  N2 = 8

expansion = [
    [NeuronAssignments.In1,  NeuronAssignments.I1,   1.02, 0],
    [NeuronAssignments.I1,   NeuronAssignments.N1,   1.02, 0],
    [NeuronAssignments.In2,  NeuronAssignments.I2,   1.02, 0],
    [NeuronAssignments.I2,   NeuronAssignments.N2,   1.02, 0],
    [NeuronAssignments.N1,   NeuronAssignments.N2,   0.50, 0],
    [NeuronAssignments.N2,   NeuronAssignments.N1,   0.50, 0],
    [NeuronAssignments.N1,   NeuronAssignments.Inh1, 1.02, 0],
    [NeuronAssignments.Inh1, NeuronAssignments.I1,   1.02, 1],
    [NeuronAssignments.N2,   NeuronAssignments.Inh2, 1.02, 0],
    [NeuronAssignments.Inh2, NeuronAssignments.I2,   1.02, 1]
]

spikePattern = [
  [0, NeuronAssignments.In1],
  [30, NeuronAssignments.In2]
]

def stepAndRepeat(singleExpansion, singleSpikePattern, step, repeat):
  """ Given a single instance of the expansion pattern and corresponding spike patter, 
      plus the stepping distance between patterns and a repeat count,
      copy the expansion pattern to the 'repeat' number of
      places, separated by 'step' indices.
  """
  fullExpansion = []
  fullSpikePattern = []
  for i in range(repeat):
    offset = i * step
    for expansionValue in singleExpansion:
      fullExpansion.append([expansionValue[0] + offset, expansionValue[1] + offset, expansionValue[2], expansionValue[3]])
    for spikePattern in singleSpikePattern:
      fullSpikePattern.append([spikePattern[0], spikePattern[1] + offset])

  return fullExpansion, fullSpikePattern

class AnticipateRunner:
  def __init__(self, engineName, enginePeriod, dimensions, log_enable=False, record_enable=True, record_synapse_enable=True, record_activation=True, record_hypersensitive=True):
    self.title = 'Test 1.  The Anticipate test.'
    self.engineName = engineName
    self.enginePeriod = enginePeriod
    template['neurons'][0]['dims'] = dimensions
    self.neuronCount = dimensions[0] * dimensions[1]
    self.log_enable = log_enable
    self.record_enable = record_enable
    self.record_synapse_enable = record_synapse_enable
    self.record_activation = record_activation
    self.record_hypersensitive = record_hypersensitive

  def run(self, iterations):
    step = 10
    patternCount = math.floor(self.neuronCount / step)
    fullExpansion, fullSpikePattern = stepAndRepeat(expansion, spikePattern, step, patternCount)
    with ModelFramework(self.engineName, self.enginePeriod, 'test', 'test', template, fullExpansion) as model:
      model.setup(self.title)
      model.create()
      model.add_deployment()
      model.deploy(log_enable=self.log_enable, record_enable=self.record_enable, record_synapse_enable=self.record_synapse_enable, record_activation=self.record_enable, record_hypersensitive=self.record_hypersensitive)
      model.send_spikes(model.generate_spike_sequence(fullSpikePattern, iterations))
      model.run_for_ticks(200 + iterations * 100)
      self.measurements = model.undeploy()
      model.teardown()
      
      self.results = model.results
