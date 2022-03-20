from re import X
import pytest
from test1 import AnticipateRunner

@pytest.fixture(scope="session")
def run():
  runner = AnticipateRunner('Research1')
  runner.run(5)
  return runner


class TestAnticipate:
  def test_successful_setup(self, run):
    assert 'Setup' in run.results
    assert run.results['Setup'] == 'success'

  def test_successful_template(self, run):
    assert 'Template' in run.results
    assert run.results['Template'] == 'success'

  def test_successful_expansion(self, run):
    assert 'Expansion' in run.results
    assert run.results['Expansion'] == 'success'

  def test_successful_population(self, run):
    assert 'Population' in run.results
    assert run.results['Population'] == 'success'

  def test_has_multiple_epochs(self, run):
    assert 'Setup' in run.results
    assert run.results['Setup'] == 'success'

  def test_epochs_are_properly_separated(self, run):
    a = 'hi'
    assert 'i' in a
  