from re import X
import pytest
import time
from anticipate_runner import AnticipateRunner
from anticipate_data import NeuronAssignments
from analysis.anticipate_record import AnticipateRun

engines_1 = [{ 'name': 'Research1.lan', 'period': 10000}]
engines_4 = [{ 'name': 'Research4.lan', 'period': 10000}]
engines_1_4 = [{ 'name': 'Research1.lan', 'period': 10000}, { 'name': 'Research4.lan', 'period': 10000}]
testEngine = 'Research4.lan'
testEnginePeriod = 10000
testEpochs = 50

@pytest.fixture(scope="session")
def run():
  runner = AnticipateRunner(engines_4)
  runner.run(testEpochs)
  return runner

@pytest.fixture(scope="session")
def record(run):
  time.sleep(5)   # Give engine time to copy records to public storage.
  recording = AnticipateRun(run.engines, NeuronAssignments.In1)
  recording.print()
  return recording

def getSynapticStrengths(epochs, neuronIndex, synapseIndex):
  strengths = []
  for epoch in epochs:
    neuronEvents = filter(lambda event: event.neuron_index == neuronIndex, epoch.events)
    for event in neuronEvents:
      adjustments = filter(lambda adjustment: adjustment.synapse_index == synapseIndex, event.synapse_adjustments)
      for adjustment in adjustments:
        strengths.append(adjustment.synapse_strength)

  return strengths

def duration_per_tick(epochs, epoch):
  M = len(epochs[epoch].events) - 1
  epoch_tick_separation = epochs[epoch].events[M].tick - epochs[epoch].events[0].tick
  epoch_duration_separation = epochs[epoch].events[M].to_delta() - epochs[epoch].events[0].to_delta()
  epoch_duration_separation_us = epoch_duration_separation.seconds * 1000000 + epoch_duration_separation.microseconds
  epoch_duration_separation_ms = round(epoch_duration_separation_us / 1000)
  duration_per_tick = round(epoch_duration_separation_ms / epoch_tick_separation)
  return duration_per_tick

class TestAnticipate10ms:
  def test_successful_setup(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'setup' operation.
    """
    assert 'setup' in run.results
    assert run.results['setup'] == 'success'

  def test_successful_template(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'template' operation.
    """
    assert 'template' in run.results
    assert run.results['template'] == 'success'

  def test_successful_expansion(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'expansion' operation.
    """
    assert 'expansion' in run.results
    assert run.results['expansion'] == 'success'

  def test_successful_deploy(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'deploy' operation.
    """
    assert 'deploy' in run.results
    assert run.results['deploy'] == 'success'

  def test_successful_send_spikes(self, run):
    """ Confirm the AnticipateRunner object recorded 'success' for the 'sendspikes' operation.
    """
    assert 'sendspikes' in run.results
    assert run.results['sendspikes'] == 'success'
########
#  def test_successful_population(self, run):
#    """ Confirm the AnticipateRunner object recorded 'success' for the 'Population' operation.
#    """
#    assert 'population' in run.results
#    assert run.results['population'] == 'success'
########
  def test_correct_epoch_count(self, record):
    """ The AnticipateRun record should contain the correct number of epochs.
    """
    for epochs in record.records:
      assert len(epochs) == testEpochs
  
  def test_epochs_are_properly_separated(self, record):
    """ The AnticipateRun record should show that epochs are separated by the correct number of ticks.
    """
    for epochs in record.records:
      epoch0 = epochs[0].events[0].tick
      epoch1 = epochs[1].events[0].tick
      assert epoch1 - epoch0 == 100

      epochN_1 = epochs[len(epochs) - 2].events[0].tick
      epochN   = epochs[len(epochs) - 1].events[0].tick
      assert epochN - epochN_1 == 100

  def test_first_ticks_are_correct_duration(self, record):
    """ The AnticipateRun record should show the correct number of microseconds per tick at the start.
    """
    for epochs in record.records:
      ms_per_tick = duration_per_tick(epochs, 0)
      assert ms_per_tick == testEnginePeriod / 1000

  def test_last_ticks_are_correct_duration(self, record):
    """ The AnticipateRun record should show the correct number of microseconds per tick at the end.
    """
    for epochs in record.records:
      ms_per_tick = duration_per_tick(epochs, len(epochs) - 1)
      assert ms_per_tick == testEnginePeriod / 1000

  def test_N1_N2_synapse_increases(self, record):
    for epochs in record.records:
      strengths = getSynapticStrengths(epochs, NeuronAssignments.N2, 1)
      assert len(strengths) > 0
      assert strengths[len(strengths) - 1] > strengths[0]
    
  def test_first_epoch_I2_precedes_N2(self, record):
    """ The AnticipateRun record should show that the I2 spike precedes the N2 spike at the start.
    """
    for epochs in record.records:
      epoch0 = epochs[0]
      firstI2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.I2, epoch0.events), None)
      firstN2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N2, epoch0.events), None)
      assert firstI2 and firstN2
      assert firstI2.tick < firstN2.tick

  def test_last_epoch_N2_precedes_I2(self, record):
    """ The AnticipateRun record should show that the I2 spike does not precede the N2 spike at the end.
    """
    for epochs in record.records:
      epochN = epochs[len(epochs) - 1]
      lastI2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.I2, epochN.events), None)
      lastN2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N2, epochN.events), None)
      assert lastN2
      if lastI2:
        assert lastN2.tick < lastI2.tick

  def test_N1_N2_gap_decreases(self, record):
    """ The AnticipateRun record should show that the interval between N1 spike and N2 spike
        is shorter at the end than at the start.
    """
    for epochs in record.records:
      epoch0 = epochs[0]
      firstN1 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N1, epoch0.events), None)
      firstN2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N2, epoch0.events), None)

      epochN = epochs[len(epochs) - 1]
      lastN1 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N1, epochN.events), None)
      lastN2 = next(filter(lambda event: event.neuron_index == NeuronAssignments.N2, epochN.events), None)
      assert firstN1 and firstN2 and lastN1 and lastN2
      assert lastN2.tick - lastN1.tick < firstN2.tick - firstN1.tick

