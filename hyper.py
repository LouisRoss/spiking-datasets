import json
from support.model_manager import ModelManager


hyper_template = {
  "method": "projection",
  "neurons": [
    {
      "name": "input",
      "dims": [10, 1],
      "height": 0,
      "import": 0.2,
      "export": 0.0
    },
    {
      "name": "x",
      "dims": [10, 1],
      "height": 0,
      "import": 0.2,
      "export": 0.0
    },
    {
      "name": "output",
      "dims": [2, 1],
      "height": 1,
      "import": 0.2,
      "export": 0.0
    },
    {
      "name": "training",
      "dims": [2, 1],
      "height": 1,
      "import": 0.2,
      "export": 0.0
    }
  ],
  "policies": [
    {
      "type": "Excitatory",
      "source": "input",
      "target": "x",
      "fraction": 1.0,
      "fanout": 1.0,
      "mean": 0.15,
      "sd": 0.1
    },
    {
      "type": "Excitatory",
      "source": "x",
      "target": "output",
      "fraction": 1.0,
      "fanout": 1.0,
      "mean": 0.2,
      "sd": 0.2
    },
    {
      "method": "unique",
      "type": "Attention",
      "source": "training",
      "target": "output"
    }
  ]
}

class NeuronAssignments:
  Input1 = 0
  Input2 = 1
  Input3 = 2
  Input4 = 3
  Input5 = 4
  Input6 = 5
  Input7 = 6
  Input8 = 7
  Input9 = 8
  Input10 = 9
  X1 = 10
  X2 = 11
  X3 = 12
  X4 = 13
  X5 = 14
  X6 = 15
  X7 = 16
  X8 = 17
  X9 = 18
  X10 = 19
  Output1 = 20
  Output2 = 21
  Training1 = 22
  Training2 = 23

trainingSpikePattern = [
  [0, NeuronAssignments.Training1],
  [500, NeuronAssignments.Training2]
]

fullSpikePattern = [
  [1, NeuronAssignments.Input1],
  [1, NeuronAssignments.Input3],
  [1, NeuronAssignments.Input5],
  [1, NeuronAssignments.Input7],
  [1, NeuronAssignments.Input9],

  [501, NeuronAssignments.Input2],
  [501, NeuronAssignments.Input4],
  [501, NeuronAssignments.Input6],
  [501, NeuronAssignments.Input8],
  [501, NeuronAssignments.Input10]
]

testName = 'hypertest'
iterations = 1
measurements = None
###engines = [{ 'name': 'Research4', 'period': 1000}, { 'name': 'Research4', 'period': 1000}]
engines = [{ 'name': 'Research4.lan', 'period': 1000}]

def prepareSpikePattern(model):
  global trainingSpikePattern
  global fullSpikePattern

  spikePattern = []
  for spike in trainingSpikePattern:
    spikePattern.extend(model.frequency_encode(spike[0], spike[1], 255, 400))

  for spike in fullSpikePattern:
    spikePattern.extend(model.frequency_encode(spike[0], spike[1], 230, 400))

  spikePattern = model.generate_spike_sequence(spikePattern, iterations, pitch=1000)
  print(spikePattern)

  return spikePattern

def buildAndRunModel():
  with ModelManager(engines, model_name=testName) as model:
    model.write_template_file(hyper_template, testName)
    model.create_model()
    model.apply_templates_to_model(['little/' + testName, 'big/' + testName])
    model.create_deployment()
    model.deploy(log_enable=False, record_enable=True, record_synapse_enable=True, record_activation=True, record_hypersensitive=True)
    model.send_spikes(prepareSpikePattern(model))
    model.run_for_ticks(200 + iterations * 1000)
    measurements = model.undeploy()


buildAndRunModel()
