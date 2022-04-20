from datetime import datetime,timedelta
import csv

class EventTypes:
  Decay_Event = 1
  Spike_Event = 2
  Adjust_Event = 4

class AnticipateAdjustment:
  def __init__(self, neuron, synapse, strength):
    self.neuron_index = neuron
    self.synapse_index = synapse
    self.synapse_strength = strength

class AnticipateEvent:
  def __init__(self, row=None):
    if row:
      self.tick = int(row['tick'])
      self.parse_time(row['time'])
      self.neuron_index = int(row['Neuron-Index'])
      self.type = int(row['Neuron-Event-Type'])
    self.synapse_adjustments = []

  def _add_adjustment(self, row):
    self.synapse_adjustments.append(AnticipateAdjustment(int(row['Neuron-Index']), int(row['Synapse-Index']), int(row['Synapse-Strength'])))

  def parse_time(self, timeString):
    dotPos = timeString.find('.')
    self.datetime = datetime.strptime(timeString[:dotPos], '%Y-%m-%d %H:%M:%S')
    self.nanosecond = int(timeString[dotPos+1:])

  def to_delta(self):
    return timedelta(days=self.datetime.day, 
                     hours=self.datetime.hour, 
                     minutes=self.datetime.minute, 
                     seconds=self.datetime.second, 
                     microseconds=round(self.nanosecond/1000))

class AnticipateEpoch:
  def __init__(self, row):
    self.events = []
    self.last_event = None
    self.add_event(row)

  def add_event(self, row):
    if int(row['Neuron-Event-Type']) == EventTypes.Adjust_Event:
      if self.last_event:
        self.last_event._add_adjustment(row)
    elif int(row['Neuron-Event-Type']) == EventTypes.Spike_Event:
      self.last_event = AnticipateEvent(row)
      self.events.append(self.last_event)


class AnticipateRun:
  def __init__(self, filename, epoch_index):
    self.epochs = []
    epoch = None
    with open(filename, newline='') as recordFile:
      reader = csv.DictReader(recordFile)
      for row in reader:
        if int(row['Neuron-Index']) == epoch_index and int(row['Neuron-Event-Type']) == EventTypes.Spike_Event:
          if epoch:
            self.epochs.append(epoch)
            epoch = None
          epoch = AnticipateEpoch(row)
        else:
          if epoch:
            epoch.add_event(row)

    if epoch:
      self.epochs.append(epoch)


#run = AnticipateRun('/media/louis/seagate8T/record/test/test/Research1/ModelEngineRecord.csv', 1)
