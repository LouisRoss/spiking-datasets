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

