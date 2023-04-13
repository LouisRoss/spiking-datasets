import sys
import os
import json
from pathlib import Path

class Configuration:
    default_stack_configuration_file = 'configuration.json'
    default_control_file = 'defaultcontrol.json'
    settings_file = './ModelSettings.json'

    width = 50
    height = 25
    max_index = 0

    def __init__(self, model, deployment):
        self.configuration_path = None
        self.control_file = None
        self.stack_config_file = None

        self.model_name = model
        self.deployment_name = deployment

        self.settings = None
        self.stack_configuration = None
        self.control = None

        self.load_settings()
        self.load_control()
        self.load_stack_configuration()

    def load_settings(self):
        with open(Configuration.settings_file) as f:
            self.settings = json.load(f)

        self.configuration_path = '.'
        if 'ConfigFilePath' in self.settings:
            self.configuration_path = self.settings['ConfigFilePath']

        self.configuration_path = self.configuration_path.rstrip('/') + '/'

    def load_stack_configuration(self):
        if not self.stack_config_file:
            if 'DefaultStackConfigurationFile' in self.settings:
                self.stack_config_file = self.settings['DefaultStackConfigurationFile']
            else:
                self.stack_config_file = Configuration.default_stack_configuration_file

            if not self.stack_config_file.endswith('.json'):
                self.stack_config_file += '.json'

            self.stack_config_file = self.configuration_path + '/' + self.stack_config_file

            with open(self.stack_config_file) as f:
                self.stack_configuration = json.load(f)

        print("Using stack configuration path '" + self.stack_config_file + "'")

    def load_control(self):
        if not self.control_file:
            if 'DefaultControlFile' in self.settings:
                self.control_file = self.settings['DefaultControlFile']
            else:
                self.control_file = Configuration.default_control_file

            if not self.control_file.endswith('.json'):
                self.control_file += '.json'

            self.control_file = self.configuration_path + '/' + self.control_file

            with open(self.control_file) as f:
                self.control = json.load(f)

        print("Using control path '" + self.control_file + "'")

    def find_record_path(self):
        record_path = self.settings['RecordFilePath'].rstrip('/') + '/' + self.model_name + '/' + self.deployment_name
        # Path(record_path).mkdir(parents=True, exist_ok=True)
        return record_path

    def get_deployment_map(self):
      deployment_map = []
      deployment_map_path = self.find_record_path() + '/DeploymentMap.json'
      if os.path.exists(deployment_map_path):
        with open(deployment_map_path) as f:
            deployment_map = json.load(f)

      return deployment_map
    
    def resolve_neuron_index(self, position):
        return position[0] * self.width + position[1]

    def get_neuron_index(self, neuron_name):
        if 'Model' not in self.configuration:
            print ('Required "Model" section not in configuration, unable to resolve neuron "' + neuron_name + '"')
            return 1<<30

        if 'Neurons' not in self.configuration['Model']:
            print ('Required key "Neurons" not in configuration "Model" section, unable to resolve neuron "' + neuron_name + '"')
            return 1<<30

        named_neurons_element = self.configuration['Model']['Neurons']
        
        if neuron_name not in named_neurons_element:
            print ('Neuron "' + neuron_name + '" not listed in "Neurons" element, unable to resolve neuron')
            return 1<<30

        return self.resolve_neuron_index(named_neurons_element[neuron_name])
