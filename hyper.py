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
      "dims": [4, 1],
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
    }
  ],
  "policies": [
    {
      "source": "input",
      "target": "x",
      "fraction": 1.0,
      "fanout": 0.5,
      "mean": 0.6,
      "sd": 0.2
    },
    {
      "source": "x",
      "target": "output",
      "fraction": 1.0,
      "fanout": 1.0,
      "mean": 0.6,
      "sd": 0.2
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
  X2 = 12
  X2 = 13
  Output1 = 14
  Output2 = 15


fullSpikePattern = [
  [0, NeuronAssignments.Input1],
  [1, NeuronAssignments.Input3],
  [2, NeuronAssignments.Input5],
  [3, NeuronAssignments.Input7],
  [4, NeuronAssignments.Input9],

  [20, NeuronAssignments.Input2],
  [21, NeuronAssignments.Input4],
  [22, NeuronAssignments.Input6],
  [23, NeuronAssignments.Input8],
  [24, NeuronAssignments.Input10]
]

testName = 'hypertest'
iterations = 10
measurements = None


def buildAndRunModel():
  with ModelManager('Research1', 10000, model_name=testName) as model:
    model.writeTemplateFile(hyper_template)
    model.createModel()
    model.applyTemplateToModel()
    model.createDeployment()
    model.deploy(log_enable=False, record_enable=True, record_synapse_enable=True, record_activation=True, record_hypersensitive=True)
    model.send_spikes(model.generate_spike_sequence(fullSpikePattern, iterations))
    model.run_for_ticks(200 + iterations * 100)
    measurements = model.undeploy()


buildAndRunModel()
