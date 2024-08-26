# Main program for raspberry Pi Pico

from machine import Pin, PWM, ADC, I2C
from ssd1306 import SSD1306_I2C

import math
import time


# CONST
GEAR_RATIO = 75
PULSES_PER_REVOLUTION = 6
WHEEL_DIAMETER = 40

CELL_DISTANCE = 180

# THRESHOLDS
LEFT_TURN_THR = 45000
RIGHT_TURN_THR = 45000
FORWARD_TURN_THR = 30000

SPEED = 12000
ROTATE_SPEED = 5000

# MAZE
MAZE_SIZE = 6
MAZE_START_X = 4
MAZE_START_Y = 0

led = Pin(25, Pin.OUT)
led.on()

# Init motor pins
motor1A = PWM(Pin(16))
motor1B = PWM(Pin(17))

motor1A.freq(1000)
motor1B.freq(1000)
              
motor2A = PWM(Pin(18))
motor2B = PWM(Pin(19))

motor2A.freq(1000)
motor2B.freq(1000)
              

# Init LEDS
rightLed = ADC(Pin(26))
rightLedValue = rightLed.read_u16()
middleLed = ADC(Pin(27))
middleLedValue = middleLed.read_u16()
leftLed = ADC(Pin(28))
leftLedValue = leftLed.read_u16()

i2c = I2C(0, scl = Pin(13), sda = Pin(12), freq=400000)
time.sleep(1)
display = SSD1306_I2C(128, 64, i2c)

button = Pin(10, Pin.IN, Pin.PULL_UP)

mode = 0

def RotateSquare(squareID: int):
    if squareID > 7:
        squareID = squareID << 1
        squareID -= 16
        squareID += 1
    else:
        squareID = squareID << 1

    return squareID


class Encoder():
    def __init__(self, pinID: int) -> None:
        self._encoderPin = Pin(pinID, Pin.IN, Pin.PULL_DOWN)

        self._count = 0
        self._lastState = self._encoderPin.value()

    def Update(self) -> None:
        state = self._encoderPin.value()

        if state != self._lastState:
            self._count += 1
            self._lastState = state

    def GetRevolutionCount(self) -> float:
        return self._count / (GEAR_RATIO * PULSES_PER_REVOLUTION)
    
    def ResetCounter(self):
        self._count = 0

def SetMotorSpeeds(leftSpeed: int, rightSpeed: int) -> None:
    if rightSpeed < 0:
        motor1A.duty_u16(2 ** 16 - 1 + rightSpeed)
        motor1B.duty_u16(2 ** 16 - 1)
    else:
        motor1A.duty_u16(2 ** 16 - 1)
        motor1B.duty_u16(2 ** 16 - 1 - rightSpeed)
    
    if leftSpeed < 0:
        motor2A.duty_u16(2 ** 16 - 1 + leftSpeed)
        motor2B.duty_u16(2 ** 16 - 1)
    else:
        motor2A.duty_u16(2 ** 16 - 1)
        motor2B.duty_u16(2 ** 16 - 1 - leftSpeed)    
       
    
# Init encoders
leftEncoder: Encoder = Encoder(6)
rightEncoder: Encoder = Encoder(8)


def MoveDistance(targetDistance: float, speed: int) -> None:
    startLeftRevolutions = leftEncoder.GetRevolutionCount()
    startRightRevolutions = rightEncoder.GetRevolutionCount()

    while leftEncoder.GetRevolutionCount() - startLeftRevolutions < abs(targetDistance):
        leftEncoder.Update()
        rightEncoder.Update()

        delta = (rightEncoder.GetRevolutionCount() - startRightRevolutions) - (leftEncoder.GetRevolutionCount() - startLeftRevolutions)
        SetMotorSpeeds(int(speed - delta * 30000), int(speed + delta * 30000))

    SetMotorSpeeds(0, 0)

def RotateDistance(targetDistance: float, speed: int, leftRight: float) -> None:
    startLeftRevolutions = leftEncoder.GetRevolutionCount()
    startRightRevolutions = rightEncoder.GetRevolutionCount()

    SetMotorSpeeds(int(speed - speed * leftRight), int(-speed - speed * leftRight))
    while leftEncoder.GetRevolutionCount() - startLeftRevolutions < abs(targetDistance) and rightEncoder.GetRevolutionCount() - startRightRevolutions < abs(targetDistance):
        leftEncoder.Update()
        rightEncoder.Update()

    SetMotorSpeeds(0, 0)


# Calibrate wall distances
targetLeftValue = leftLed.read_u16()
targetRightValue = rightLed.read_u16()

direction = 1

x = MAZE_START_X + 1
y = MAZE_START_Y

mazeFile = open("maze.txt", "w")
logFile = open("log.txt", "w")

targetDistance = CELL_DISTANCE / (WHEEL_DIAMETER * math.pi)

lastLeftRevolutions = leftEncoder.GetRevolutionCount()
lastRightRevolutions = rightEncoder.GetRevolutionCount()

mazeMap = [-1] * (MAZE_SIZE ** 2)

lastButton = button.value()

while True:
    buttonValue = button.value()

    if buttonValue != lastButton:
        lastButton = buttonValue

        if buttonValue == 0:
            print("YAAY")
            mode = 1 - mode

            # Calibrate wall distances
            targetLeftValue = leftLed.read_u16()
            targetRightValue = rightLed.read_u16()

            time.sleep(1)
        

    if mode == 0:
        SetMotorSpeeds(0, 0)

        rightLedValue = rightLed.read_u16()
        middleLedValue = middleLed.read_u16()
        leftLedValue = leftLed.read_u16()

        display.fill(0)
        display.text("r: " + str(rightLedValue) + "/" + str(RIGHT_TURN_THR), 0, 35)
        display.text("m: " + str(middleLedValue) + "/" + str(FORWARD_TURN_THR), 0, 45)
        display.text("l: " + str(leftLedValue) + "/" + str(LEFT_TURN_THR), 0, 55)

        display.show()

    elif mode == 1:
        # Read encoders values
        leftEncoder.Update()
        rightEncoder.Update()

        leftRevolutions = leftEncoder.GetRevolutionCount()
        rightRevolutions = rightEncoder.GetRevolutionCount()
        
        delta = (rightRevolutions - lastRightRevolutions) - (leftRevolutions - lastLeftRevolutions)

        # Read LED values

        rightLedValue = rightLed.read_u16()
        middleLedValue = middleLed.read_u16()
        leftLedValue = leftLed.read_u16()

        deltaLed = (rightLedValue - targetRightValue) - (leftLedValue - targetLeftValue)

        deltaLed = min(deltaLed, 6000)
        deltaLed = max(deltaLed, -6000)

        delta = min(delta, 0.2)
        delta = max(delta, -0.2)

        if leftRevolutions - lastLeftRevolutions > targetDistance or middleLedValue < 20000:
            # Evaluate intersection

            SetMotorSpeeds(0, 0)

            leftTurn = leftLedValue > LEFT_TURN_THR
            rightTurn = rightLedValue > RIGHT_TURN_THR
            forwardTurn = middleLedValue > FORWARD_TURN_THR
                
            # Calculate maze squere ID and store to maze map
            if 0 <= x <= MAZE_SIZE - 1 and 0 <= y <= MAZE_SIZE - 1:
                if mazeMap[(MAZE_SIZE - y - 1) * MAZE_SIZE + x] == -1:
                    cell = 0

                    if not forwardTurn:
                        cell += 1

                    if not rightTurn:
                        cell += 2

                    if not leftTurn:
                        cell += 8

                    for i in range(direction % 4):
                        cell = RotateSquare(cell)

                    mazeMap[(MAZE_SIZE - y - 1) * MAZE_SIZE + x] = cell

            #while button.value():
                #pass

            # Right hand rule
            if rightTurn:
                direction += 1

                MoveDistance(0.1, -SPEED)
                RotateDistance(0.50 * 2, ROTATE_SPEED, -1)

                targetDistance = CELL_DISTANCE / (WHEEL_DIAMETER * math.pi) - 0.55

            elif forwardTurn:
                targetDistance = CELL_DISTANCE / (WHEEL_DIAMETER * math.pi)

            elif leftTurn:
                direction -= 1

                MoveDistance(0.1, -SPEED)
                RotateDistance(0.50 * 2, -ROTATE_SPEED, 1)

                targetDistance = CELL_DISTANCE / (WHEEL_DIAMETER * math.pi) - 0.55

            else:
                direction += 2

                RotateDistance(0.53 * 2, SPEED, 0.12)
                
                targetDistance = CELL_DISTANCE / (WHEEL_DIAMETER * math.pi) - 0.55
        

            # Calculate new coordinates
            if x == 4 and y == 0:
                SetMotorSpeeds(0, 0)
                break

            if direction % 4 == 0:
                y += 1
            elif direction % 4 == 1:
                x += 1
            elif direction % 4 == 2:
                y -= 1
            elif direction % 4 == 3:
                x -= 1

            SetMotorSpeeds(0, 0)

            lastLeftRevolutions = leftEncoder.GetRevolutionCount()
            lastRightRevolutions = rightEncoder.GetRevolutionCount()

        # Check for wall situation
        if rightLedValue <= RIGHT_TURN_THR - 2000 and leftLedValue <= LEFT_TURN_THR - 2000:    
            SetMotorSpeeds(int(SPEED + deltaLed / 1.4), int(SPEED - deltaLed / 1.4))
        elif rightLedValue <= RIGHT_TURN_THR - 2000:
            rightDelta = rightLedValue - targetRightValue
            rightDelta = min(rightDelta, 6000)
            rightDelta = max(rightDelta, -6000)

            sign = 1
            if rightDelta < 0:
                sign = -1

            SetMotorSpeeds(int(SPEED + abs(rightDelta) ** (1 / 2) * 60 * sign), int(SPEED - abs(rightDelta) ** (1 / 2) * 60 * sign))
        elif leftLedValue <= LEFT_TURN_THR - 2000:
            leftDelta = leftLedValue - targetLeftValue
            leftDelta = min(leftDelta, 6000)
            leftDelta = max(leftDelta, -6000)

            sign = 1
            if leftDelta < 0:
                sign = -1

            SetMotorSpeeds(int(SPEED - abs(leftDelta) ** (1 / 2) * 60 * sign), int(SPEED + abs(leftDelta) ** (1 / 2) * 60 * sign))

        else:
            SetMotorSpeeds(int(SPEED + delta * 60000), int(SPEED - delta * 60000)) 


for i in range(MAZE_SIZE):
    for j in range(MAZE_SIZE):
        mazeFile.write(str(mazeMap[MAZE_SIZE * i + j]) + " ")

    mazeFile.write("\n")

logFile.write("Total distance left wheel: {} mm, Total distance right wheel: {} mm\n".format(leftEncoder.GetRevolutionCount() * (WHEEL_DIAMETER * math.pi), rightEncoder.GetRevolutionCount() * (WHEEL_DIAMETER * math.pi)))


display.fill(0)

xOffset = 64 - 18
yOffset = 18
size = 6

for i in range(6):
    for j in range(6):
        code = mazeMap[MAZE_SIZE * i + j]

        if code == -1:
            continue

        if code & 1:
            display.line(xOffset + j * size, yOffset + i * size, xOffset + (j + 1) * size, yOffset + i * size, 1)

        if code & 2:
            display.line(xOffset + (j + 1) * size, yOffset + i * size, xOffset + (j + 1) * size, yOffset + (i + 1) * size, 1)
            
        if code & 4:
            display.line(xOffset + j * size, yOffset + (i + 1) * size, xOffset + (j + 1) * size, yOffset + (i + 1) * size, 1)

        if code & 8:
            display.line(xOffset + j * size, yOffset + i * size, xOffset + j * size, yOffset + (i + 1) * size, 1)

        #display.rect(xOffset + j * size, yOffset + i * size, size, size, 1)



finishX = -1
finishY = -1

for i in range(MAZE_SIZE - 1):
    for j in range(MAZE_SIZE - 1):
        UpLeft = mazeMap[MAZE_SIZE * i + j]
        UpRight = mazeMap[MAZE_SIZE * i + j + 1]
        DownLeft = mazeMap[MAZE_SIZE * (i + 1) + j]
        DownRight = mazeMap[MAZE_SIZE * (i + 1) + j + 1]

        count = 0

        if UpLeft & 2 or UpLeft & 4:
            count += 1

        if UpRight & 4 or UpRight & 8:
            count += 1

        if DownLeft & 1 or DownLeft & 2:
            count += 1

        if DownRight & 1 or DownRight & 8:
            count += 1
    
        if count == 0:
            finishX = j
            finishY = MAZE_SIZE - 1 - i

display.text("{}, {}".format(finishX, finishY), 0, 55)
print(finishX, finishY)


display.show()


led.off()
mazeFile.close()
logFile.close()
