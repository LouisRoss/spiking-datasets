import os
import sys
import copy
import json
import time
import csv
import re
from enum import Enum
from pathlib import Path
from datetime import datetime,timedelta

from support.configuration import Configuration

'''
Extract the configured channels from the record CSV file
and write a new cleaned CSV file with a unique column for
each of the configured channels.
'''
class NeuronRecordType(Enum):
    InputSignal = 0
    Decay = 1
    Spike = 2
    Refractory = 3
    SynapseAdjust = 4
    HyperSensitive = 5


class RecordFileParser:
    def __init__(self, configuration, deployment):
      self.configuration = configuration
      self.record_path = self.configuration.find_record_path()
      self.deployment_path = self.record_path + '/' + str(deployment['engine'])
      self.deployment_offset = int(deployment['offset'])
      self.samples = []
      self.capacity = 0
      self.current = 0
      self.tick_offset = 0

    def create_parser(self):
      print('Parsing record file at ' + str(self.deployment_path))
      record_file = 'ModelEngineRecord.csv'
      if 'RecordFile' in self.configuration.control:
          record_file = self.configuration.control['RecordFile']

      self.samples = list(csv.DictReader(open(self.deployment_path + '/' + record_file, newline='')))
      self.current = 0
      self.capacity = len(self.samples)

    def at_end(self):
      return self.current >= self.capacity
    
    def synchronize(self, target_tick):
        if target_tick <= 0:
            self.tick_offset = 0
        else:
            tick = int(self.samples[self.current]['tick'])
            self.tick_offset = target_tick - tick

        return self.get_current_tick()

    def next(self):
        if not self.at_end():
            self.current += 1

        return self.get_current_tick()

    def get_current_sample(self):
        if self.at_end():
            return None
        
        print('Sampling record from engine ' + self.deployment_path)
        sample = self.samples[self.current]
        return {
            'tick': int(sample['tick']) + self.tick_offset,
            'Neuron-Event-Type': int(sample['Neuron-Event-Type']),
            'Neuron-Index': int(sample['Neuron-Index']) + self.deployment_offset,
            'Neuron-Activation': int(sample['Neuron-Activation']),
            'Hypersensitive': int(sample['Hypersensitive']),
            'Synapse-Index': int(sample['Synapse-Index']) if sample['Synapse-Index'] != 'N/A' else None,
            'Synapse-Strength': int(sample['Synapse-Strength']) if sample['Synapse-Strength'] != 'N/A' else None
        }
    
    def get_current_tick(self):
        current_tick = 0
        if not self.at_end():
            current_tick = int(self.samples[self.current]['tick']) + self.tick_offset

        return current_tick

    def get_current_time(self):
        if self.at_end():
            return None
        
        time_stamp = self.samples[self.current]['time']
        time_stamp_parts = time_stamp.split('.')

        current_time = datetime.fromisoformat(time_stamp_parts[0])

        nanoseconds = int(time_stamp_parts[-1])
        microseconds = round(nanoseconds / 1000)
        current_time_offset = timedelta(microseconds=microseconds)
        current_time += current_time_offset

        return current_time


class Records:
    def __init__(self, configuration):
      self.configuration = configuration
      self.record_path = self.configuration.find_record_path()
      self.record_file_parsers = []

    def create_parsers(self):
      starting_tick = 0

      for deployment in self.configuration.get_deployment_map():
          parser = RecordFileParser(self.configuration, deployment)
          parser.create_parser()
          starting_tick = parser.synchronize(starting_tick)
          self.record_file_parsers.append(parser)

    def get_next_sample(self):
        first_tick = sys.maxsize
        first_parser = 0
        done = True

        for index, parser in enumerate(self.record_file_parsers):
            if not parser.at_end():
                parser_current_tick = parser.get_current_tick()
                if parser_current_tick < first_tick:
                    first_tick = parser_current_tick
                    first_parser = index
                    done = False

        if done:
            return None
        
        sample = self.record_file_parsers[first_parser].get_current_sample()
        self.record_file_parsers[first_parser].next()
        return sample



class Cleaner:
    def __init__(self, configuration, monitor_neurons = None, trigger_callback=None):
        ''' Create the header for the cleaned CSV file, with the neuron's
            name and numeric ID for column head.  Clean the output row
            to contain the correct number of int values in preparation.
            monitor_neurons should be an array of objects like { name: "JenniferAniston", index: 42 }
        '''
        self.configuration = configuration
        self.monitor_neurons = monitor_neurons
        self.is_trigger = trigger_callback
        self.outputheader = []
        self.outputrow = []

        self.outputheader.append('time')
        self.outputrow.append(0)
        self.output = []
        self.epochoutput = []
        self.trigger = None

        if not self.monitor_neurons:
            self.monitor_neurons = self.generate_monitor_neurons()

        self.monitor_indices = []
        self.first_sample = []

        for neuron in self.monitor_neurons:
            name = neuron[0] + '(' + str(neuron[1]) + ')'
            self.outputheader.append(name)
            self.outputrow.append(0)
            self.monitor_indices.append(neuron[1])
            self.first_sample.append(0)

        self.output.append(copy.copy(self.outputheader))
        self.output.append(copy.copy(self.first_sample))
        self.reset_epoch_output()

    def clean_data(self):
        last_tick = 0
        last_row = []

        records = Records(self.configuration)
        records.create_parsers()

        sample = records.get_next_sample()
        last_tick = sample['tick']
        while sample is not None:
            event_type = sample['Neuron-Event-Type']
            if event_type == NeuronRecordType.Decay.value or event_type == NeuronRecordType.Spike.value or event_type == NeuronRecordType.Refractory.value or event_type == NeuronRecordType.SynapseAdjust.value:
                active_neuron = sample['Neuron-Index']
                if active_neuron in self.monitor_indices:
                    tick = sample['tick']
                    last_row = copy.copy(self.outputrow)
                    if last_tick != 0 and tick != last_tick:
                        self.fill_output(last_row, last_tick, tick)
                    self.outputrow[self.monitor_indices.index(active_neuron) + 1] = sample['Neuron-Activation']
                    last_tick = tick

                if self.is_trigger:
                    if self.is_trigger(sample):
                        print('Trigger sample found')
                        tick = sample['tick']
                        if last_tick != 0 and tick != last_tick:
                            self.fill_output(last_row, last_tick, tick)
                        self.write_cleaned_epoch()
                        last_tick = tick

            sample = records.get_next_sample()

        self.write_cleaned_epoch()
        self.write_cleaned_run()

    def generate_monitor_neurons(self):
        ''' Iterate through the whole CSV file, and collect all unique
            neuron indexes.  Generate names for each neuron, and create
            monitor_neurons as an array of objects like { name: "JenniferAniston", index: 42 }
        '''
        monitor_indices = []

        records = Records(self.configuration)
        records.create_parsers()
        while True:
            sample = records.get_next_sample()
            if sample is None:
                break

            if sample['Neuron-Index'] not in monitor_indices:
                monitor_indices.append(sample['Neuron-Index'])

        monitor_neurons = []
        for monitor_index in monitor_indices:
            monitor_neurons.append(['Neuron'+str(monitor_index), monitor_index])

        return monitor_neurons


    def fill_output(self, row, first_tick, last_tick):
        ''' Extend a straigt-line value from first_tick through last_tick,
            ensuring that the cleaned output file has a value for all ticks.
        '''
        tick = first_tick
        row[0] = tick
        self.output.append(copy.copy(row))
        self.epochoutput.append(copy.copy(row))

        tick += 1
        while tick < last_tick:
            row[0] = tick
            self.output.append(copy.copy(row))
            self.epochoutput.append(copy.copy(row))
            tick += 1

    def write_cleaned_run(self):
        ''' Write the cleaned data for the entire run to the configured clean output file.
        '''
        record_path = self.configuration.find_record_path()
        clean_record_file = self.configuration.control['CleanRecordFile']
        record_path = record_path + '/' + clean_record_file
        print("Writing clean record file '" + record_path + "'")
        with open(record_path, mode='w') as clean_data:
            data_writer = csv.writer(clean_data, delimiter=',', quoting=csv.QUOTE_NONE)
            data_writer.writerows(self.output)

    def write_cleaned_epoch(self):
        ''' Write the cleaned epoch data to the configured clean output file.
            Note this may be called when the first epoch starts, so skip that one.
        '''
        if len(self.epochoutput) > 2:
            for i in range(1, len(self.epochoutput)):
                self.epochoutput[i][0] = i           # Tick starts with 1 for all epochs.
            record_path = self.configuration.find_record_path()
            epoch_number = self.get_next_epoch_number(Path(record_path))
            record_path = record_path.rstrip('/') + '/' + "epoch" + str(epoch_number) + ".csv"
            print("Writing clean epoch file '" + record_path + "'")
            with open(record_path, mode='w') as clean_data:
                data_writer = csv.writer(clean_data, delimiter=',', quoting=csv.QUOTE_NONE)
                data_writer.writerows(self.epochoutput)

        self.reset_epoch_output()

    def reset_epoch_output(self):
        self.epochoutput = []   # Clear the epoch data, starting over with just a header row.
        self.epochoutput.append(copy.copy(self.outputheader))
        self.epochoutput.append(copy.copy(self.first_sample))


    def get_next_epoch_number(self, record_path):
        ''' Examine all the existing 'epochN.csv' files, looking
            for the largest N.  Return N+1.
        '''
        largest_epoch = 0
        epochs_in_project = (entry for entry in record_path.glob('epoch*csv'))
        for epoch in epochs_in_project:
            epoch_name = str(epoch).split('/')[-1]
            epoch_number = int(re.search(r"([a-zA-Z]*)(\d*)", epoch_name).group(2))
            if (epoch_number > largest_epoch):
                largest_epoch = epoch_number

        return largest_epoch + 1

def execute(configuration):
    cleaner = Cleaner(configuration)
    cleaner.clean_data()

def run():
    conf = configuration()
    execute(conf)

if __name__ == "__main__":
    run()
