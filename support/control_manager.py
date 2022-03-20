import json
import socket
import select
from struct import *


class ControlManager:
  engine = ''
  host = ''
  settings = {}
  query = {}
  response = {}

  def __init__(self, engine):
    self.engine = engine
    self.socket = None

    f = open('/configuration/settings.json')
    self.settings = json.load(f)
    self.host = next((e["host"] for e in self.settings["engines"] if e["name"] == engine), None)
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  def Connect(self):
    self.socket.connect((self.host, 8000))

  def Close(self):
    self.socket.close()

  def SendDeploy(self, model):
    query = { "query": 'deploy', "model": model, "deployment": model, "engine": self.engine }
    self.socket.sendall(json.dumps(query).encode())

  def SendUndeploy(self):
    query = { "query": 'deploy', "model": "", "deployment": "", "engine": self.engine }
    self.socket.sendall(json.dumps(query).encode())

  def SendTestSettings(self):
    control = { "query": 'settings', "values": [["RecordFilePath", "../record/"]] }
    print("Sending test settings command: " + json.dumps(control))
    self.socket.sendall(json.dumps(control).encode('utf-8'))

  def SendTestSetup(self):
    control = { "query": 'control', "values": { "recordenable": True, "recordsynapses": True, "engineperiod": 10000 } }
    print("Sending test setup command: " + json.dumps(control))
    self.socket.sendall(json.dumps(control).encode('utf-8'))

  def Poll(self):
    readable, writable, _ = select.select([self.socket], [], [])
    if len(readable) == 0:
      return

    lengthBytes = self.socket.recv(2)
    length, = unpack('H', lengthBytes)
    self.readBuffer(length)

  def readBuffer(self, length):
    chunks = []
    bytesRead = 0
    while bytesRead < length:
      chunk = self.socket.recv(min(length - bytesRead, 2048))
      if chunk == b'':
        return

      chunks.append(chunk)
      bytesRead += len(chunk)

      receiveData = b''.join(chunks).decode('utf-8')
      response = json.loads(receiveData)
      self.ParseResponse(response)


  def ParseResponse(self, response):
    if 'query' in response:
      self.query = response['query']

    if 'response' in response and 'result' in response['response'] and response['response']['result'] != 'ok':
      self.response = response['response']
      print("Got a response with error '" + self.response['error'] + "'")

    elif 'response' in response and 'result' in response['response'] and response['response']['result'] == 'ok' and 'query' in response:
      self.response = response['response']

