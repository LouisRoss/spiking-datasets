import csv

Decay_Event = 1
Spike_Event = 2
Adjust_Event = 4

class AnticipateAdjustment:
  def __init__(self, neuron, synapse, strength):
    self.neuron_index = neuron
    self.synapse_index = synapse
    self.synapse_strength = strength

class AnticipateEvent:
  def __init__(self, row):
    self.tick = int(row['tick'])
    self.neuron_index = int(row['Neuron-Index'])
    self.type = int(row['Neuron-Event-Type'])
    self.synapse_adjustments = []

  def addAdjustment(self, row):
    self.synapse_adjustments.append(AnticipateAdjustment(int(row['Neuron-Index']), int(row['Synapse-Index']), int(row['Synapse-Strength'])))


class AnticipateEpoch:

  def __init__(self, row):
    self.events = []
    self.last_event = None
    self.addEvent(row)

  def addEvent(self, row):
    if int(row['Neuron-Event-Type']) == Adjust_Event:
      if self.last_event:
        self.last_event.addAdjustment(row)
    elif int(row['Neuron-Event-Type']) == Spike_Event:
      self.last_event = AnticipateEvent(row)
      self.events.append(self.last_event)


class AnticipateRun:
  def __init__(self, filename, epoch_index):
    self.epochs = []
    epoch = None
    with open(filename, newline='') as recordFile:
      reader = csv.DictReader(recordFile)
      for row in reader:
        if int(row['Neuron-Index']) == epoch_index and int(row['Neuron-Event-Type']) == Spike_Event:
          if epoch:
            self.epochs.append(epoch)
            epoch = None
          epoch = AnticipateEpoch(row)
        else:
          if epoch:
            epoch.addEvent(row)

    if epoch:
      self.epochs.append(epoch)


#run = AnticipateRun('/media/louis/seagate8T/record/test/test/Research1/ModelEngineRecord.csv', 1)
