""" Wrap the socket API to the repository to do a subset of functions.
"""

import json
import socket
import select
from struct import *

from numpy import true_divide


class ControlManager:

  def __init__(self, engine, engine_period):
    self._host = ''
    self._engine = engine
    self._enginePeriod = engine_period
    self._socket = None

    self.settings = {}
    self.query = {}
    self.response = {}

    with open('/configuration/settings.json') as f:
      self.settings = json.load(f)
      
    self._host = next((e["host"] for e in self.settings["engines"] if e["name"] == engine), None)
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  def connect(self):
    self._socket.connect((self._host, 8000))

  def close(self):
    self._socket.close()

  def send_deploy(self, model, deployment=None):
    if not deployment:
      deployment = model
    query = { "query": 'deploy', "model": model, "deployment": deployment, "engine": self._engine }
    print("Sending deploy command: " + json.dumps(query))
    return self._transact(query, lambda query, response: 'query' in query and query['query'] == 'deploy' and 'result' in response and response['result'] == 'ok')

  def send_undeploy(self):
    query = { "query": 'deploy', "model": "", "deployment": "", "engine": self._engine }
    print("Sending undeploy command: " + json.dumps(query))
    return self._transact(query, lambda query, response: 'query' in query and query['query'] == 'deploy' and 'result' in response and response['result'] == 'ok')

  def send_test_settings(self):
    control = { "query": 'settings', "values": [["RecordFilePath", "/record/"]] }
    print("Sending test settings command: " + json.dumps(control))
    return self._transact(control, lambda query, response: 'query' in query and query['query'] == 'settings' and 'result' in response and response['result'] == 'ok')

  def send_test_setup(self, log_enable=False, record_enable=False, record_synapse_enable=False, record_activation=False, record_hypersensitive=False):
    control = { "query": 'control', "values": { "logenable": log_enable, "recordenable": record_enable, "recordsynapses": record_synapse_enable, "recordactivation": record_activation, "recordhypersensitive": record_hypersensitive, "engineperiod": self._enginePeriod, "loglevel": 0 } }
    print("Sending test setup command: " + json.dumps(control))
    return self._transact(control, lambda query, response: 
      'query' in query and query['query'] == 'control' and 
      'result' in response and response['result'] == 'ok' and 
      'status' in response and 'recordfile' in response['status'])

  def get_test_measurements(self):
    measurements = { "query": 'runmeasurements' }
    print("Sending test measurements request: " + json.dumps(measurements))
    self._transact(measurements, lambda query, response: 'query' in query and query['query'] == 'runmeasurements' and 'result' in response and response['result'] == 'ok')
    return self.response

  def send_test_start(self):
    control = { "query": 'control', "values": { "startmeasurement": True } }
    print("Sending test start command: " + json.dumps(control))
    return self._transact(control, lambda query, response: 
      'query' in query and query['query'] == 'control' and 
      'result' in response and response['result'] == 'ok' and 
      'status' in response and 'recordfile' in response['status'])

  def _transact(self, request, predicate):
    request_json = json.dumps(request)
    self._socket.sendall(request_json.encode('utf-8'))

    return self._read_response(predicate)

  def _read_response(self, predicate):
    success = False
    done = False

    while not done:
      readable, writable, _ = select.select([self._socket], [], [])
      if len(readable) == 0:
        done = True
        success = False
      else:
        length_bytes = self._socket.recv(2)
        length, = unpack('H', length_bytes)
        response = self._read_buffer(length)
        if response:
          success, done = self._parse_response(response, predicate)
        else:
          done = True
          success = False

    return success

  """
  def Poll(self, predicate):
    readable, writable, _ = select.select([self._socket], [], [])
    if len(readable) == 0:
      return

    lengthBytes = self._socket.recv(2)
    length, = unpack('H', lengthBytes)
    response = self._read_buffer(length)
    if response:
      self._parse_response(response, predicate)
  """

  def _read_buffer(self, length):
    chunks = []
    bytesRead = 0
    while bytesRead < length:
      chunk = self._socket.recv(min(length - bytesRead, 2048))
      if chunk == b'':
        return None

      chunks.append(chunk)
      bytesRead += len(chunk)

    receiveData = b''.join(chunks).decode('utf-8')
    response = json.loads(receiveData)
    return response


  def _parse_response(self, response, predicate):
    if 'query' in response:
      self.query = response['query']

    if 'response' in response and 'result' in response['response'] and response['response']['result'] != 'ok':
      self.response = response['response']
      return False, True

    elif 'response' in response and 'result' in response['response'] and response['response']['result'] == 'ok' and 'query' in response:
      self.response = response['response']

    if predicate(self.query, self.response):
      return True, True

    return False, False
    
