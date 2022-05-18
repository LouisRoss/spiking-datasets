import time
import json
import requests

from support.control_manager import ControlManager
from support.realtime_manager import RealtimeManager

class ModelManager:
  templateStoragePath = '/templates/'

  def __init__(self, engine_name, engine_period, model_name='test'):
    self._engine_name = engine_name
    self._deployment_name = engine_name
    self._engine_period = engine_period
    self._model_name = model_name
    self._control_manager = None

    self.headers = { 'Accept': 'application/json' }

    with open('/configuration/configuration.json') as f:
        self.configuration = json.load(f)

    self.host = self.configuration['services']['modelPackager']['host']
    self.port = self.configuration['services']['modelPackager']['port']
    self.modelBaseUrl = self.host + ":" + self.port

  def __enter__(self):
    self._control_manager = ControlManager(self._engine_name, self._engine_period)
    self._control_manager.connect()

    return self

  def __exit__(self, type, value, traceback):
    self._control_manager.close()
    return False   # Suppress propagation of any exception that occurred in the caller.

  def writeTemplateFile(self, template):
    with open(ModelManager.templateStoragePath + self._model_name + '.json', 'w') as templateFile:
      json.dump(template, templateFile)

  def createModel(self):
    fullUrl = self.modelBaseUrl + '/model/' + self._model_name
    print('POSTting to URL: ' + fullUrl)

    response = requests.post(fullUrl, headers=self.headers)
    print(response.status_code)
    #print()
    if response.status_code != 200:
        return False

    self.pollComplete(response)
    return True


  def deleteModel(self):
    fullUrl = self.modelBaseUrl + '/model/' + self._model_name
    print('DELETEing to URL: ' + fullUrl)

    response = requests.delete(fullUrl, headers=self.headers)
    print(response.status_code)
    #print()
    if response.status_code != 200:
        return False

    self.pollComplete(response)
    return True


  def applyTemplateToModel(self):
    fullUrl = self.modelBaseUrl + '/package/' + self._model_name
    print('PUTing to URL: ' + fullUrl)

    response = requests.put(fullUrl, json=[self._model_name + '/' + self._model_name])
    print(response.status_code)
    #print()
    if response.status_code != 200:
        return False

    self.pollComplete(response)
    return True


  def createDeployment(self):
    fullUrl = self.modelBaseUrl + '/model/' + self._model_name + '/deployment/' + self._deployment_name
    print('PUTing to URL: ' + fullUrl)

    response = requests.put(fullUrl, json=[self._engine_name])
    print(response.status_code)
    #print()
    if response.status_code != 200:
        return False

    return True


  def pollComplete(self, response):
    done = False
    printedInProgressOnce = False
    while not done:
      status = response.json()
      if 'completed' in status:
        if status['completed']:
          print(status['status'])
          done = True
        else:
          if not printedInProgressOnce:
            print(status['status'])
            printedInProgressOnce = True
      time.sleep(.025)
      response = requests.get(status['link'], headers=self.headers)


  def deploy(self, log_enable=False, record_enable=True, record_synapse_enable=True, record_activation=True, record_hypersensitive=True):
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

    if not self._control_manager.send_deploy(self._model_name, self._deployment_name):
      print('Failed send_deploy(' + self._model_name + ') with error ' + self._control_manager.response['error'])
      return False

    if not self._control_manager.send_test_setup(log_enable=log_enable, record_enable=record_enable, record_synapse_enable=record_synapse_enable, record_activation=record_activation, record_hypersensitive=record_hypersensitive):
      print('Failed send_test_setup with error ' + self._control_manager.response['error'])
      return False

    if not self._control_manager.send_test_start():
      print('Failed send_test_start with error ' + self._control_manager.response['error'])
      return False

    print("Recording into " + self._control_manager.response['status']['recordfile'])
    print()
    return True

  def stepAndRepeat(self, singleSpikePattern, step, repeat):
    """ Given a single instance of the spike pattern, 
        plus the stepping distance between patterns and a repeat count,
        copy the spike pattern to the 'repeat' number of
        places, separated by 'step' indices.
    """
    fullSpikePattern = []
    for i in range(repeat):
      offset = i * step
      for spikePattern in singleSpikePattern:
        fullSpikePattern.append([spikePattern[0], spikePattern[1] + offset])

    return fullSpikePattern

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

