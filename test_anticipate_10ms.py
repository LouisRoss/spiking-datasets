from re import X
import pytest
import time
from anticipate_runner import AnticipateRunner,NeuronAssignments
from analysis.anticipate_record import AnticipateRun

testEngine = 'Research1'
testEnginePeriod = 10000
testEpochs = 50

@pytest.fixture(scope="session")
def run():
  runner = AnticipateRunner(testEngine, testEnginePeriod, [10, 10])
  runner.run(testEpochs)
  return runner

@pytest.fixture(scope="session")
def record(run):
  time.sleep(5)   # Give engine time to copy records to public storage.
  recording = AnticipateRun('/record/test/test/' + run.engineName + '/ModelEngineRecord.csv', 1)
  return recording

def getSynapticStrengths(record, neuronIndex, synapseIndex):
  strengths = []
  for epoch in record.epochs:
    neuronEvents = filter(lambda event: event.neuron_index == neuronIndex, epoch.events)
    for event in neuronEvents:
      adjustments = filter(lambda adjustment: adjustment.synapse_index == synapseIndex, event.synapse_adjustments)
      for adjustment in adjustments:
        strengths.append(adjustment.synapse_strength)

  return strengths

def duration_per_tick(record, epoch):
  M = len(record.epochs[epoch].events) - 1
  epoch_tick_separation = record.epochs[epoch].events[M].tick - record.epochs[epoch].events[0].tick
  epoch_duration_separation = record.epochs[epoch].events[M].to_delta() - record.epochs[epoch].events[0].to_delta()
  epoch_duration_separation_us = epoch_duration_separation.seconds * 1000000 + epoch_duration_separation.microseconds
  epoch_duration_separation_ms = round(epoch_duration_separation_us / 1000)
  duration_per_tick = round(epoch_duration_separation_ms / epoch_tick_separation)
  return duration_per_tick

class TestAnticipate10ms:
  def test_successful_setup(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'Setup' operation.
    """
    assert 'setup' in run.results
    assert run.results['setup'] == 'success'

  def test_successful_template(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'Template' operation.
    """
    assert 'template' in run.results
    assert run.results['template'] == 'success'

  def test_successful_expansion(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'Expansion' operation.
    """
    assert 'expansion' in run.results
    assert run.results['expansion'] == 'success'

  def test_successful_population(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'Population' operation.
    """
    assert 'population' in run.results
    assert run.results['population'] == 'success'

  def test_correct_epoch_count(self, record):
    """ The AnticipateRun record should contain the correct number of epochs.
    """
    assert len(record.epochs) == testEpochs
  
  def test_epochs_are_properly_separated(self, record):
    """ The AnticipateRun record should show that epochs are separated by the correct number of ticks.
    """
    epoch0 = record.epochs[0].events[0].tick
    epoch1 = record.epochs[1].events[0].tick
    assert epoch1 - epoch0 == 100

    epochN_1 = record.epochs[len(record.epochs) - 2].events[0].tick
    epochN   = record.epochs[len(record.epochs) - 1].events[0].tick
    assert epochN - epochN_1 == 100

  def test_first_ticks_are_correct_duration(self, record):
    """ The AnticipateRun record should show the correct number of microseconds per tick at the start.
    """
    ms_per_tick = duration_per_tick(record, 0)
    assert ms_per_tick == testEnginePeriod / 1000

  def test_last_ticks_are_correct_duration(self, record):
    """ The AnticipateRun record should show the correct number of microseconds per tick at the end.
    """
    ms_per_tick = duration_per_tick(record, len(record.epochs) - 1)
    assert ms_per_tick == testEnginePeriod / 1000

  def test_N1_N2_synapse_increases(self, record):
    strengths = getSynapticStrengths(record, NeuronAssignments.N2, 1)
    assert len(strengths) > 0
    assert strengths[len(strengths) - 1] > strengths[0]
    
  def test_first_epoch_I2_precedes_N2(self, record):
    """ The AnticipateRun record should show that the I2 spike precedes the N2 spike at the start.
    """
    epoch0 = record.epochs[0]
    firstI2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.I2, epoch0.events), None)
    firstN2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N2, epoch0.events), None)
    assert firstI2 and firstN2
    assert firstI2.tick < firstN2.tick

  def test_last_epoch_N2_precedes_I2(self, record):
    """ The AnticipateRun record should show that the I2 spike does not precede the N2 spike at the end.
    """
    epochN = record.epochs[len(record.epochs) - 1]
    lastI2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.I2, epochN.events), None)
    lastN2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N2, epochN.events), None)
    assert lastN2
    if lastI2:
      assert lastN2.tick < lastI2.tick

  def test_N1_N2_gap_decreases(self, record):
    """ The AnticipateRun record should show that the interval between N1 spike and N2 spike
        is shorter at the end than at the start.
    """
    epoch0 = record.epochs[0]
    firstN1 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N1, epoch0.events), None)
    firstN2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N2, epoch0.events), None)

    epochN = record.epochs[len(record.epochs) - 1]
    lastN1 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N1, epochN.events), None)
    lastN2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N2, epochN.events), None)
    assert firstN1 and firstN2 and lastN1 and lastN2
    assert lastN2.tick - lastN1.tick < firstN2.tick - firstN1.tick

