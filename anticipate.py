import os
import glob
from re import X

from anticipate_data import template, spikePattern, NeuronAssignments
from support.model_utilities import templateNeuronCount, stepAndRepeat, extract_monitor_neurons
from support.configuration import Configuration
from support.model_manager import ModelManager
from clean_record import Cleaner
from plot_record import plot_cleaned_run,plot_epochs

engines_1 = [{ 'name': 'Research1.lan', 'period': 10000}]
engines_4 = [{ 'name': 'Research4.lan', 'period': 1000}]
engines_1_4 = [{ 'name': 'Research1.lan', 'period': 10000}, { 'name': 'Research4.lan', 'period': 10000}]

monitor_no_in = { 'I1', 'I2', 'Inh1', 'Inh2', 'N1', 'N2' }
monitor_i_n = { 'I1', 'I2', 'N1', 'N2' }

class Anticipate:
  def __init__(self, engines,  model='test', deployment='test', log_enable=False, record_enable=True, record_synapse_enable=True, record_activation=True, record_hypersensitive=True):
    self._template = template    # Modify this manually to change templates.
    self.engines = engines
    self.model = model
    self.deployment = deployment
    self.configuration = Configuration(self.model, self.deployment)
    self.log_enable = log_enable
    self.record_enable = record_enable
    self.record_synapse_enable = record_synapse_enable
    self.record_activation = record_activation
    self.record_hypersensitive = record_hypersensitive

  def run(self, iterations):
    step = templateNeuronCount(self._template)
    fullSpikePattern = stepAndRepeat(spikePattern, step, len(self.engines))
    with ModelManager(self.engines, model_name=self.model, deployment_name=self.deployment) as model:
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

    if 'sendspikes' in self.results and self.results['sendspikes'] == 'success':
      if self.record_enable:
        self.plot()

  def plot(self):
    record_path = self.configuration.find_record_path()
    files = glob.glob(record_path + '/*csv')
    for f in files:
      os.remove(f)

    files = glob.glob(record_path + '/*png')
    for f in files:
      os.remove(f)

    deployments = self.configuration.get_deployment_map()
    index_map = []
    for deployment in deployments:
      for index in range(deployment['count']):
        while len(index_map) <= index:
          index_map.append([])
        index_map[index].append(index + deployment['offset'])

    print(index_map)
    is_trigger = lambda sample: sample['Neuron-Event-Type'] == 2 and sample['Neuron-Index'] in index_map[NeuronAssignments.In1]
    cleaner = Cleaner(self.configuration, extract_monitor_neurons(self.configuration, NeuronAssignments, monitor_i_n), is_trigger)
    cleaner.clean_data()

    plot_cleaned_run(self.configuration)
    plot_epochs(self.configuration)

