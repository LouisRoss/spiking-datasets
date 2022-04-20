""" Provide a generic framework to control the lifetime of a model,
    including creating and deleting the model in persistent store,
    adding template, expansion, and deployment, as well as deploying
    and undeploying the model to the engines configured in the deployment.
    While the model is deployed to its engine(s), allow a facility to
    send spikes to the live model as specified by a pattern.
"""

from support.h5model import h5model
from support.h5deployment import h5deployment
from support.control_manager import ControlManager
from support.realtime_manager import RealtimeManager

class ModelFramework:
  def __init__(self, template, expansion, engine_name, engine_period):
    print("***** Start of Test")
    print()

    self._model_name = 'test'
    self._model = None
    self._control_manager = None
    self._template = template
    self._expansion = expansion
    self._engine_name = engine_name
    self._engine_period = engine_period
    self.results = {}

  def __enter__(self):
    self._control_manager = ControlManager(self._engine_name, self._engine_period)
    self._control_manager.connect()
    return self

  def __exit__(self, type, value, traceback):
    self._control_manager.close()
    print("***** End of test")
    return False   # Suppress propagation of any exception that occurred in the caller.

  def setup(self, signon):
    """ Create an empty model in the repository.
        The model is identified with self._model_name.
    """
    print("***** Setup  " + signon)

    self._model = h5model(self._model_name)

    print("Creating model '" + self._model.modelName + "'")
    self._model.createModel()
    if self._model.responseStatus == 200:
      self.results['setup'] = 'success'
    else:
      self.results['setup'] = self._model.failureReason

    print()

  def create(self):
    """ Modify an existing model in persistent store by replacing
        any existing template, expansion, and population with new
        ones.
        The template and expansion must be pre-designed and injected
        into this object when it is constructed.
        Note that the model self._model_name must exist in the repository.
    """
    print("***** Create")
    # Calculate the total neurons needed plus the starting offset and count for the population.
    neuronIndexes = {}
    nextIndex = 0
    populations = self._template["neurons"]
    for population in populations:
      count = 1
      for dim in population["dims"]:
        count *= dim
      neuronIndexes[population["name"]] = { "shape": population["dims"], "index": nextIndex, "count": count }
      population.update({ "index": nextIndex, "count": count })
      nextIndex += count

    print("Adding template and expansion to model '" + self._model.modelName + "'")
    print("template:")
    print(self._template)
    self._model.addTemplateToModel(self._model_name, self._template)
    if self._model.responseStatus == 200 or self._model.responseStatus == 201:
      self.results['template'] = 'success'
    else:
      self.results['template'] = self._model.failureReason
    self._model.addExpansionToModel(0, self._model_name, nextIndex, self._expansion)
    if self._model.responseStatus == 201:
      self.results['expansion'] = 'success'
    else:
      self.results['expansion'] = self._model.failureReason

    population = {}
    population["neuroncount"] = nextIndex
    population["templates"] = [{'template': self._model_name, 'population': self._model_name, 'indexes': neuronIndexes }]
    self._model.updatePopulationInModel(population)
    if self._model.responseStatus == 201:
      self.results['population'] = 'success'
    else:
      self.results['population'] = self._model.failureReason
    print()

  def add_deployment(self):
    """ Add a deployment to the model self._model_name.
        At this time, the whole model is deployed to a single
        engine, self._engine_name.
    """
    print("***** Adding deployment '" + self._model_name + "' to model with one engine, '" + self._engine_name + "'")
    deployment = h5deployment(self._model_name)
    deployment.createModelDeployment()
    deployment.addDeploymentToModel(self._model_name, [self._engine_name])
    print()

  def deploy(self, log_enable=False, record_enable=True, record_synapse_enable=True):
    """ Deploy the model per the deployment with the same name as
        the model, self._model_name.  The model may exist in the repository
        through some manual configuration, or may have been built using the
        above methods of this class.  As long as it exists in the
        repository, the model may be deployed and undeployed multiple times.
        Note that the deploy action includes three steps: Send test settings,
        deploy, and send test setup.
        * Send test settings:  This refers to any modifications to memory
                               image read from the settings file.  This can
                               include, but is not limited to, the recording
                               path.
        * Deploy:              Deploy according to the deployment in the
                               repository with the same name as the model.
        * Send test setup:     Control the run parameters that can only be
                               modified on a running model, such as log enable,
                               record enable, and engine period.
    """
    print("***** Deploying model")
    if not self._control_manager.send_test_settings():
      print('Failed send_test_settings with error ' + self._control_manager.response['error'])
      return False

    if not self._control_manager.send_deploy(self._model_name):
      print('Failed send_deploy(' + self._model_name + ') with error ' + self._control_manager.response['error'])
      return False

    if not self._control_manager.send_test_setup(log_enable=log_enable, record_enable=record_enable, record_synapse_enable=record_synapse_enable):
      print('Failed send_test_setup with error ' + self._control_manager.response['error'])
      return False

    if not self._control_manager.send_test_start():
      print('Failed send_test_start with error ' + self._control_manager.response['error'])
      return False

    print("Recording into " + self._control_manager.response['status']['recordfile'])
    print()
    return True

  def generate_spike_sequence(self, pattern, repeat, pitch=100):
    """ Expand the supplied spike pattern by repeating it the number
        of times specified by 'repeat'.  Each repeat is separated in
        ticks by the specified 'pitch'.
        A pattern is an array of two-element arrays. Each of the two-
        element arrays is of the format [tick, neuron], describing the
        time that a specified neuron should spike.
        The returned spikes sequence is suitable to be sent to send_spikes().
    """
    tick = pitch
    spikes = []
    for i in range(repeat):
      for spike in pattern:
        spikes.append([spike[0] + tick, spike[1]])
      tick += pitch

    return spikes

  def send_spikes(self, spikes):
    """ Send the spike sequence to a single engine, to be
        executed per the embedded spike ticks.
    """
    print("***** Sending test spikes to engine")
    with RealtimeManager(self._engine_name) as realtimeManager:
      realtimeManager.SendSpikes(spikes)
    print()

  def run_for_ticks(self, tickCount):
    """ Allow the model to run until the returned status
        packets indicate the specified number of ticks have elapsed.
    """
    print("***** Polling for " + str(tickCount) + " ticks")
    startTicks = 0
    if 'status' in self._control_manager.response and 'iterations' in self._control_manager.response['status']:
      startTicks = self._control_manager.response['status']['iterations']
    print("Starting tick: " + str(startTicks))

    self._control_manager._read_response(lambda request, response: 
      'status' in response and 
      'iterations' in response['status'] and 
      response['status']['iterations'] > startTicks + tickCount)
    print("Final tick: " + str(self._control_manager.response['status']['iterations']))
    print()

  def undeploy(self):
    """ Undeploy the model from all engines.  Leave any changes made to the
        settings during deployment in place.
    """
    print("***** Undeploying all models from all engines")
    self._control_manager.send_undeploy()
    measurements = self._control_manager.get_test_measurements()
    print()

    return measurements

  def teardown(self):
    """ Delete the model and its associated deployments from the repository.
    """
    print("***** Deleting model '" + self._model.modelName + "'")
    self._model.deleteModel()
    print()
