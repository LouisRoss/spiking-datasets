import math

""" Test 1.  The simple anticipate test.
    Configure a small microcircuit with inputs I1 and I2,
    and outputs N1 and N2.  I1 always precedes I2 by a few
    milliseconds.  Show that the network adapts so that output
    N2 anticiaptes input I2, even if it does not occur.
"""

from support.model_manager import ModelManager
from anticipate_data import template, spikePattern
from support.model_utilities import templateNeuronCount, stepAndRepeat

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
