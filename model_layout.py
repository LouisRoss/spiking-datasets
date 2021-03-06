from enum import Enum


class squareMovement(Enum):
  XINC = 1
  ZINC = 2
  XDEC = 3
  ZDEC = 4
  XZBUMP = 5

class modelLayout:
  def __init__(self, modelName):
    self.modelName = modelName
    self.movement = squareMovement.XINC

  def layoutRasterSquare(self, dimensions, startPosition):
    maxX, maxZ = dimensions
    startX, startY, startZ = startPosition

    lowX = maxX / -2
    highX = maxX / 2
    if maxX %2 != 0:
      lowX = (maxX - 1) / -2
      highX = (maxX + 1) / 2

    lowZ = maxZ / -2
    highZ = maxZ / 2
    if maxZ %2 != 0:
      lowZ = (maxZ - 1) / -2
      highZ = (maxZ + 1) / 2

    layout = []
    for z in range(int(lowZ), int(highZ)):
      for x in range(int(lowX), int(highX)):
        layout.append([startX + x, startY, startZ + z])

    return layout

  def layoutSquare(self, count, startPosition):
    startX, startY, startZ = startPosition
    layout = []
    limits = { 'lowerLimit': 0, 'upperLimit': 0, 'movement': squareMovement.ZDEC }
    position = [0, 1]
    if count % 2 == 0:
      limits = { 'lowerLimit': 1, 'upperLimit': 0, 'movement': squareMovement.XZBUMP }
      position = [1, 1]

    while len(layout) < count:
      position = self.nextXZ(position, limits)
      layout.append([startX + position[0], startY, startZ + position[1]])

    return layout

  def nextXZ(self, position, limits):
    x, z = position

    if limits['movement'] == squareMovement.XINC:
      x += 1
      if x >= limits['upperLimit']:
        limits['movement'] = squareMovement.ZINC
    elif limits['movement'] == squareMovement.ZINC:
      z += 1
      if z >= limits['upperLimit']:
        limits['movement'] = squareMovement.XDEC
    elif limits['movement'] == squareMovement.XDEC:
      x -= 1
      if x <= limits['lowerLimit']:
        if z <= (limits['lowerLimit'] + 1):
          limits['movement'] = squareMovement.XZBUMP
        else:
          limits['movement'] = squareMovement.ZDEC
    elif limits['movement'] == squareMovement.ZDEC:
      z -= 1
      if z <= (limits['lowerLimit'] + 1):
        limits['movement'] = squareMovement.XZBUMP
    else:
      limits['lowerLimit'] -= 1
      limits['upperLimit'] += 1
      x = z = limits['lowerLimit']
      limits['movement'] = squareMovement.XINC

    return [x, z]
