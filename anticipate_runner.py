import math

""" Test 1.  The simple anticipate test.
    Configure a small microcircuit with inputs I1 and I2,
    and outputs N1 and N2.  I1 always precedes I2 by a few
    milliseconds.  Show that the network adapts so that output
    N2 anticiaptes input I2, even if it does not occur.
"""

from support.model_framework import ModelFramework
from support.model_manager import ModelManager

template = {
  "method": "explicit",
  "neurons": [
    {
      "name": "input",
      "dims": [2, 1],
      "height": 0,
      "import": 0.2,
      "export": 0.0
    },
    {
      "name": "I",
      "dims": [2, 1],
      "height": 10,
      "import": 0.2,
      "export": 0.0
    },
    {
      "name": "inhibit",
      "dims": [2, 1],
      "height": 20,
      "import": 0.2,
      "export": 0.0
    },
    {
      "name": "N",
      "dims": [2, 1],
      "height": 30,
      "import": 0.2,
      "export": 0.0
    }
  ],
  "policies": [
    {
      "type": "Excitatory", "source": "input", "target": "I",
      "expansion": [
        [0, 0, 1.02],
        [1, 1, 1.02]
      ]
    },
    {
      "type": "Excitatory", "source": "I", "target": "N",
      "expansion": [
        [0, 0, 1.02],
        [1, 1, 1.02]
      ]
    },
    {
      "type": "Excitatory", "source": "N", "target": "N", 
      "expansion": [
        [0, 1, 0.5],
        [1, 0, 0.5]
      ]
    },
    {
      "type": "Excitatory", "source": "N", "target": "inhibit",
      "expansion": [
        [0, 0, 1.02],
        [1, 1, 1.02]
      ]
    },
    {
      "type": "Inhibitory", "source": "inhibit", "target": "I", 
      "expansion": [
        [0, 0, 1.02],
        [1, 1, 1.02]
      ]
    }
  ]
}

class NeuronAssignments:
  In1 = 0
  In2 = 1
  I1 = 2
  I2 = 3
  Inh1 = 4
  Inh2 = 5
  N1 = 6
  N2 = 7


template_unified = {
  "neurons": [
    {
      "name": "all",
      "dims": [10, 1],
      "height": 0,
      "import": 0.2,
      "export": 0.0
    }
  ],
  "policies": [
    {
      "method": "explicit",
      "type": "Excitatory", "source": "all", "target": "all",
      "expansion": [
        [NeuronAssignments.In1,  NeuronAssignments.I1,   1.02],
        [NeuronAssignments.I1,   NeuronAssignments.N1,   1.02],
        [NeuronAssignments.In2,  NeuronAssignments.I2,   1.02],
        [NeuronAssignments.I2,   NeuronAssignments.N2,   1.02],
        [NeuronAssignments.N1,   NeuronAssignments.N2,   0.50],
        [NeuronAssignments.N2,   NeuronAssignments.N1,   0.50],
        [NeuronAssignments.N1,   NeuronAssignments.Inh1, 1.02],
        [NeuronAssignments.N2,   NeuronAssignments.Inh2, 1.02]
      ]
    },
    {
      "method": "explicit",
      "type": "Inhibitory", "source": "all", "target": "all", 
      "expansion": [
        [NeuronAssignments.Inh1, NeuronAssignments.I1,   1.02],
        [NeuronAssignments.Inh2, NeuronAssignments.I2,   1.02]
      ]
    }
  ]
}


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

engines = [{ 'name': 'Research1', 'period': 1000}, { 'name': 'Research4', 'period': 1000}]

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
  
class AnticipateRunner:
  def __init__(self, engines, log_enable=False, record_enable=True, record_synapse_enable=True, record_activation=True, record_hypersensitive=True):
    #self.title = 'Test 1.  The Anticipate test.'
    self._template = template    # Modify this manually to change templates.
    self.engines = engines
    #template['neurons'][0]['dims'] = dimensions
    #self.neuronCount = dimensions[0] * dimensions[1]
    self.log_enable = log_enable
    self.record_enable = record_enable
    self.record_synapse_enable = record_synapse_enable
    self.record_activation = record_activation
    self.record_hypersensitive = record_hypersensitive

  def run(self, iterations):
    step = templateNeuronCount(self._template)
    fullSpikePattern = stepAndRepeat(spikePattern, step, len(self.engines))
    #with ModelFramework(self.engineName, self.enginePeriod, 'test', 'test', template, fullExpansion) as model:
    with ModelManager(self.engines, model_name='test', deployment_name='test') as model:
      #model.setup(self.title)
      model.write_template_file(template, 'testTemplate')
      model.create_model()

      success = True
      if success:
        templates = []
        for templateNumber in range(len(self.engines)):
          templates.append('anticipate' + str(templateNumber) + '/testTemplate')
        success = model.apply_templates_to_model(templates)

      if success:
        success = model.create_deployment()
        if success:
          success = model.deploy(log_enable=self.log_enable, record_enable=self.record_enable, record_synapse_enable=self.record_synapse_enable, record_activation=self.record_enable, record_hypersensitive=self.record_hypersensitive)
          if success:
            success = model.send_spikes(model.generate_spike_sequence(fullSpikePattern, iterations))
            if success:
              success = model.run_for_ticks(200 + iterations * 100)
            self.measurements = model.undeploy()
      model.delete_model()
      
      self.results = model.results
