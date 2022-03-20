import time

from support.test_framework import testFramework

""" Test 1.  The simple anticipate test.
    Configure a small microcircuit with inputs I1 and I2,
    and outputs N1 and N2.  I1 always precedes I2 by a few
    milliseconds.  Show that the network adapts so that output
    N2 anticiaptes input I2, even if it does not occur.
"""

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

# I1 = 11
# I2 = 12
# Inh1 = 21
# Inh2 = 22
# N1 = 31
# N2 = 32
expansion = [
    [1,  11, 1.02, 0],
    [11, 31, 1.02, 0],
    [2,  12, 1.02, 0],
    [12, 32, 1.02, 0],
    [31, 32, 0.50, 0],
    [32, 31, 0.50, 0],
    [31, 21, 1.02, 0],
    [21, 11, 1.02, 1],
    [32, 22, 1.02, 0],
    [22, 12, 1.02, 1]
]

spikeSequence = [
  [100, 11],
  [115, 12],

  [200, 11],
  [215, 12],

  [300, 11],
  [315, 12],

  [400, 11],
  [415, 12],

  [500, 11],
  [515, 12],

  [600, 11],
  [615, 12],

  [700, 11],
  [715, 12],

  [800, 11],
  [815, 12],

  [900, 11],
  [915, 12],

  [1000, 11],
  [1015, 12]
]

spikePattern = [
  [0, 1],
  [30, 2]
]


class AnticipateRunner:
  def __init__(self, engineName):
    self.title = 'Test 1.  The Anticipate test.'
    self.engineName = engineName

  def run(self, iterations):
    with testFramework(template, expansion, self.engineName) as test:
      test.Setup(self.title)
      test.Create()
      test.AddDeployment()
      test.Deploy()
      test.SendSpikes(test.GenerateSpikeSequence(spikePattern, iterations))
      test.RunForTicks(200 + iterations * 100)
      test.Undeploy()
      test.TearDown()
      
      self.results = test.results
