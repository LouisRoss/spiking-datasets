from support.h5model import h5model
from support.h5deployment import h5deployment
from support.control_manager import ControlManager
from support.realtime_manager import RealtimeManager

""" 
"""

class testFramework:
  modelName = 'test'
  model = None
  controlManager = None

  template = {}
  expansion = []


  def __init__(self, template, expansion, engineName):
    print("***** Start of Test")
    print()
    self.template = template
    self.expansion = expansion
    self.engineName = engineName
    self.results = {}

  def __enter__(self):
    self.controlManager = ControlManager(self.engineName)
    self.controlManager.Connect()
    return self

  def __exit__(self, type, value, traceback):
    self.controlManager.Close()
    print("***** End of test")
    return False   # Suppress propagation of any exception that occurred in the caller.

  def Setup(self, signon):
    print("***** Setup  " + signon)

    self.model = h5model(self.modelName)

    print("Creating model '" + self.model.modelName + "'")
    self.model.createModel()
    if self.model.responseStatus == 200:
      self.results['Setup'] = 'success'
    else:
      self.results['Setup'] = self.model.failureReason

    print()

  def Create(self):
    print("***** Create")
    # Calculate the total neurons needed plus the starting offset and count for the population.
    neuronIndexes = {}
    nextIndex = 0
    populations = self.template["neurons"]
    for population in populations:
      count = 1
      for dim in population["dims"]:
        count *= dim
      neuronIndexes[population["name"]] = { "shape": population["dims"], "index": nextIndex, "count": count }
      population.update({ "index": nextIndex, "count": count })
      nextIndex += count

    print("Adding template and expansion to model '" + self.model.modelName + "'")
    print("template:")
    print(self.template)
    self.model.addTemplateToModel(self.modelName, self.template)
    if self.model.responseStatus == 200:
      self.results['Template'] = 'success'
    else:
      self.results['Template'] = self.model.failureReason
    self.model.addExpansionToModel(0, self.modelName, nextIndex, self.expansion)
    if self.model.responseStatus == 201:
      self.results['Expansion'] = 'success'
    else:
      self.results['Expansion'] = self.model.failureReason

    population = {}
    population["neuroncount"] = nextIndex
    population["templates"] = [{'template': self.modelName, 'population': self.modelName, 'indexes': neuronIndexes }]
    self.model.updatePopulationInModel(population)
    if self.model.responseStatus == 201:
      self.results['Population'] = 'success'
    else:
      self.results['Population'] = self.model.failureReason
    print()

  def AddDeployment(self):
    print("***** Adding deployment '" + self.modelName + "' to model with one engine, '" + self.engineName + "'")
    deployment = h5deployment(self.modelName)
    deployment.createModelDeployment()
    deployment.addDeploymentToModel(self.modelName, [self.engineName])
    print()

  def Deploy(self):
    print("***** Deploying model")
    self.controlManager.SendTestSettings()
    self.Poll(lambda query, response: 'query' in query and query['query'] == 'settings' and 'result' in response and response['result'] == 'ok')
    self.controlManager.SendDeploy(self.modelName)
    self.Poll(lambda query, response: 'query' in query and query['query'] == 'deploy' and 'result' in response and response['result'] == 'ok')
    self.controlManager.SendTestSetup()
    self.Poll(lambda query, response: 
      'query' in query and query['query'] == 'control' and 
      'result' in response and response['result'] == 'ok' and 
      'status' in response and 'recordfile' in response['status'])
    print("Recording into " + self.controlManager.response['status']['recordfile'])
    print()

  def GenerateSpikeSequence(self, pattern, repeat, pitch=100):
    tick = pitch
    spikes = []
    for i in range(repeat):
      for spike in pattern:
        spikes.append([spike[0] + tick, spike[1]])
      tick += pitch

    return spikes

  def SendSpikes(self, spikes):
    print("***** Sending test spikes to engine")
    with RealtimeManager(self.engineName) as realtimeManager:
      realtimeManager.SendSpikes(spikes)
    print()

  def RunForTicks(self, tickCount):
    print("***** Polling for " + str(tickCount) + " ticks")
    startTicks = 0
    if 'status' in self.controlManager.response and 'iterations' in self.controlManager.response['status']:
      startTicks = self.controlManager.response['status']['iterations']
    print("Starting tick: " + str(startTicks))

    self.Poll(lambda request, response: 'status' in response and 'iterations' in response['status'] and response['status']['iterations'] > startTicks + tickCount)
    print("Final tick: " + str(self.controlManager.response['status']['iterations']))
    print()

  def Poll(self, predicate):
    while not predicate(self.controlManager.query, self.controlManager.response):
      self.controlManager.Poll()
      if 'status' in self.controlManager.response and 'iterations' in self.controlManager.response['status']:
        print(self.controlManager.response['status']['iterations'], end='\r')
      #print(self.controlManager.query)
      #print(self.controlManager.response)

  def Undeploy(self):
    print("***** Undeploying all models from all engines")
    self.controlManager.SendUndeploy()
    print()

  def TearDown(self):
    print("***** Deleting model '" + self.model.modelName + "'")
    #self.model.deleteModel()
    print()
