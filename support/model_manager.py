import time
import math
import json
import requests

from support.control_manager import ControlManager
from support.realtime_manager import RealtimeManager

class ModelManager:
  templateStoragePath = '/templates/'
  frequencyMap = None
  min_ms_between_pulses = 15

  def __init__(self, engines, model_name='test', deployment_name='test'):
    """ 'engines' must be a list of objects where each object must have a
        'name' and 'period' field. Each 'name' must be an engine name 
        as enumerated in the 'engines' section of the settings Json file, 
        or a raw IP address or host name.
    """
    self._engines = engines
    self._model_name = model_name
    self._deployment_name = deployment_name
    self._control_managers = []

    self._headers = { 'Accept': 'application/json' }

    with open('/configuration/configuration.json') as f:
        self._configuration = json.load(f)

    self._host = self._configuration['services']['modelPackager']['host']
    self._port = self._configuration['services']['modelPackager']['port']
    self._model_base_url = self._host + ":" + self._port
    self.results = {}

  def __enter__(self):
    for engine in self._engines:
      manager = ControlManager(engine['name'], engine['period'])
      manager.connect()
      self._control_managers.append(manager)

    return self

  def __exit__(self, type, value, traceback):
    for manager in self._control_managers:
      manager.close()
      
    return False   # Suppress propagation of any exception that occurred in the caller.

  def write_template_file(self, template, template_name):
    with open(ModelManager.templateStoragePath + template_name + '.json', 'w') as template_file:
      json.dump(template, template_file)
    self.results['template'] = 'success'

  def create_model(self):
    full_url = self._model_base_url + '/model/' + self._model_name
    print('POSTting to URL: ' + full_url)

    response = requests.post(full_url, headers=self._headers)
    print(response.status_code)
    #print()
    if response.status_code != 200:
        self.results['setup'] = self._model.failureReason
        return False

    self.poll_complete(response)
    self.results['setup'] = 'success'
    return True


  def delete_model(self):
    full_url = self._model_base_url + '/model/' + self._model_name
    print('DELETEing to URL: ' + full_url)

    response = requests.delete(full_url, headers=self._headers)
    print(response.status_code)
    #print()
    if response.status_code != 200:
        return False

    self.poll_complete(response)
    return True


  def apply_templates_to_model(self, templates):
    """ 'templates' must be an array of strings.  Each string has
        the format '<populationName>/<templateName>'.
        Here, 'populationName' is a reference name, and can be anything.
        'templateName' names a template file that must exist in the model,
        possibly by using 'writeTemplateFile' above.
    """
    full_url = self._model_base_url + '/package/' + self._model_name
    print('PUTing to URL: ' + full_url)

    response = requests.put(full_url, json=templates)
    print(response.status_code)
    #print()
    if response.status_code != 200:
        self.results['expansion'] = self._model.failureReason
        return False

    self.poll_complete(response)
    self.results['expansion'] = 'success'
    return True


  def create_deployment(self):
    fullUrl = self._model_base_url + '/model/' + self._model_name + '/deployment/' + self._deployment_name
    print('PUTing to URL: ' + fullUrl)

    engines = [engine['name'] for engine in self._engines]
    response = requests.put(fullUrl, json=engines)
    print(response.status_code)
    #print()
    if response.status_code != 200:
        return False

    return True


  def poll_complete(self, response):
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
      response = requests.get(status['link'], headers=self._headers)


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
    self.results['deploy'] = 'success'
    success = True
    for manager in self._control_managers:
      print("***** Deploying model")
      if not manager.send_test_settings():
        print('Failed send_test_settings to engine ' + manager._engine + '(' + manager._host + ') with error ' + manager.response['errordetail'])
        self.results['deploy'] = manager.response['errordetail']
        success = False
        break

      if not manager.send_deploy(self._model_name, self._deployment_name):
        print('Failed send_deploy(' + self._model_name + ') to engine ' + manager._engine + '(' + manager._host + ') with error ' + self._control_manager.response['errordetail'])
        self.results['deploy'] = manager.response['errordetail']
        success = False
        break

      if not manager.send_test_setup(log_enable=log_enable, record_enable=record_enable, record_synapse_enable=record_synapse_enable, record_activation=record_activation, record_hypersensitive=record_hypersensitive):
        print('Failed send_test_setup to engine ' + manager._engine + '(' + manager._host + ') with error ' + manager.response['errordetail'])
        self.results['deploy'] = manager.response['errordetail']
        success = False
        break

      if not manager.send_test_start():
        print('Failed send_test_start to engine ' + manager._engine + '(' + manager._host + ') with error ' + manager.response['errordetail'])
        self.results['deploy'] = manager.response['errordetail']
        success = False
        break

      print("Recording into " +  manager.response['status']['recordfile'])
      print()

    return success

  def get_frequency_map(self):
    if (ModelManager.frequencyMap == None):
      ModelManager.frequencyMap = []
      for excitation in range(256):
        ModelManager.frequencyMap.append(round(math.exp(-0.015 * excitation) * 1000))

    return ModelManager.frequencyMap

  def frequency_encode(self, start, neuron_index, excitation, duration):
    buffer = []
    fmap = self.get_frequency_map()

    if excitation > 0:
      #ms_between_pulses = scale * (256 - excitation) + min_ms_between_pulses
      ms_between_pulses = max(fmap[excitation], ModelManager.min_ms_between_pulses)
      time_offset = ms_between_pulses / 2
      while time_offset <= duration:
        buffer.append([start + int(time_offset), neuron_index])
        time_offset += ms_between_pulses

    return buffer

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

    print("Single spike pattern, spike sequence:")
    print(pattern)
    print(spikes)
    return spikes
  
  def get_deployment_map(self):
    """ Request the population map and deployment for self's
        model and deployment, and build an array containing
        [
          { 'engine': engine1, 'offset': start_of_engine1_neurons, 'count': Neuron_count_in_engine1 },
          { 'engine': engine2, 'offset': start_of_engine2_neurons, 'count': Neuron_count_in_engine2 },
          ...
        ]

        On failure, add a description to self.results['sendspikes'] and return None.
    """

    full_url = self._model_base_url + '/model/' + self._model_name + '/population'
    print('GETting from URL: ' + full_url)

    response = requests.get(full_url, headers=self._headers)
    print(response.status_code)
    if response.status_code != 200:
        self.results['sendspikes'] = 'Failed to read population for model ' + self._model_name + ': status ' + str(response.status_code)
        return None
    population = response.json()

    full_url = self._model_base_url + '/model/' + self._model_name + '/deployment/' + self._deployment_name
    print('GETting from URL: ' + full_url)

    response = requests.get(full_url, headers=self._headers)
    print(response.status_code)
    if response.status_code != 200:
        self.results['sendspikes'] = 'Failed to read deployment for model ' + self._model_name + ', deployment ' + self._deployment_name + ': status ' + str(response.status_code)
        return None
    deploymentEngines = response.json()

    deployment = []
    totalNeuronCount = 0
    for i in range(len(population['templates'])):
      template = population['templates'][i]
      deploymentEngine = deploymentEngines[i]

      neuronCount = 0
      for name, value in template['indexes'].items():
        neuronCount += value['count']

      deployment.append({'engine': deploymentEngine, 'offset': totalNeuronCount, 'count': neuronCount })
      totalNeuronCount += neuronCount
    
    return deployment

  def send_spikes(self, spikes):
    """ Send the spike sequence to a single engine, to be
        executed per the embedded spike ticks.
    """
    deployment_map = self.get_deployment_map()

    self.results['sendspikes'] = 'success'
    success = True
    for population_index, deployment in enumerate(deployment_map):
      print("***** Sending test spikes to engine " + deployment['engine'])
      with RealtimeManager(deployment['engine']) as realtimeManager:
        deployment_offset = deployment['offset']
        deployment_count = deployment['count']
        first_spike = next((index for index, spike in enumerate(spikes) if spike[1] >= deployment_offset), len(spikes))
        last_spike = next((index for index, spike in enumerate(spikes) if spike[1] >= deployment_offset + deployment_count), len(spikes))
        print('Sending spikes[' + str(first_spike) + ':' + str(last_spike) + '] to engine ' + deployment['engine'] + ', using population index ' + str(population_index))
        engine_spikes = [[spike[0], spike[1]-deployment_offset] for spike in spikes[first_spike:last_spike]]
        if not realtimeManager.SendSpikes(engine_spikes, population_index):
          self.results['sendspikes'] = 'failed to send ' + str(len(spikes)) + ' spikes to engine ' + deployment['engine']
          success = False
          break
      print()
    
    return success

  def run_for_ticks(self, tickCount):
    """ Allow the model to run until the returned status
        packets indicate the specified number of ticks have elapsed.
    """
    print("***** Polling for " + str(tickCount) + " ticks")
    for manager in self._control_managers:
      startTicks = 0
      if 'status' in manager.response and 'iterations' in manager.response['status']:
        startTicks = manager.response['status']['iterations']
      print("Starting tick: " + str(startTicks))

      manager._read_response(lambda request, response: 
        'status' in response and 
        'iterations' in response['status'] and 
        response['status']['iterations'] > startTicks + tickCount)
      print("Final tick: " + str(manager.response['status']['iterations']))
      print()

  def undeploy(self):
    """ Undeploy the model from all engines.  Leave any changes made to the
        settings during deployment in place.
    """
    print("***** Undeploying all models from all engines")
    measurements = []
    for manager in self._control_managers:
      manager.send_undeploy()
      measurements.append(manager.get_test_measurements())
      print()

    return measurements

