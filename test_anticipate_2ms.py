from re import X
import pytest
from anticipate_runner import AnticipateRunner
from analysis.anticipate_record import AnticipateEvent

testEngine = 'Research1'
testEnginePeriod = 2000
testEpochs = 50

@pytest.fixture(scope="session")
def run():
  runner = AnticipateRunner(testEngine, testEnginePeriod, [80, 80], log_enable=False, record_enable=False, record_synapse_enable=False)
  runner.run(testEpochs)
  return runner

class TestAnticipate2ms:
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

  def test_correct_measurements(self, run):
    assert 'runmeasurements' in run.measurements
    startEvent = AnticipateEvent()

    startEvent.parse_time(run.measurements['runmeasurements']['enginestarttime'])
    startTime = startEvent.to_delta()

    stopEvent = AnticipateEvent()
    stopEvent.parse_time(run.measurements['runmeasurements']['enginestoptime'])
    endTime = stopEvent.to_delta()

    runTime = endTime - startTime
    runDuration = runTime.seconds * 1000000 + runTime.microseconds
    runTicks = int(run.measurements['runmeasurements']['iterations'])

    assert testEnginePeriod == round(runDuration / runTicks)

