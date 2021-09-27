from serial import Serial
import struct
from multiprocessing import Process, Queue

STOP_CODE = 0 #random defined number of STOP_CODE to be treated as special number

class MotorControllerHandler():
    def __init__(self, port, baudrate, timeout, queue):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.motor1 = 0
        self.motor2 = 0
        self.motor3 = 0
        self.thrower = 0
        self.disable_failsafe = 0

        self.process = Process(target=self.run, args=(queue,))

    def start(self, queue):
        self.process.start()
        print("Motor controller started")

    def set_motors(self, data):
        motor1, motor2, motor3, thrower = data
        if motor1 is not None:
            self.motor1 = motor1
        if motor2 is not None:
            self.motor2 = motor2
        if motor3 is not None:
            self.motor3 = motor3
        if thrower is not None:
            self.thrower = thrower
            
    def run(self, queue):
        with Serial(self.port, self.baudrate, timeout=self.timeout) as ser:
            while True:
                callback = None #by default there is no callback
                if not queue.empty():
                    data = queue.get() #get first item from queue
                    if data == STOP_CODE:
                        break
                    *motors, callback = data #extract callback from queue data and assume that everything else is motor data
                    self.set_motors(motors) #sets local motor speeds if changed

                send = struct.pack('<hhhHBH', self.motor1, self.motor2, self.motor3, 
                                            self.thrower, self.disable_failsafe, 0xAAAA)
                
                ser.write(send)
                recv = struct.unpack('<hhhH', ser.read(8))

                if callback is not None:
                    callback(recv)
        print("Motor controller stopped")

class MotorDriver(MotorControllerHandler):
    def __init__(self, port, baudrate=115200, timeout=1):
        self.send_queue = Queue(5) #send items in this queue to motor controller 
        super().__init__(port, baudrate, timeout, self.send_queue)

        self.speed = 0
        self.direction = 0

    def __enter__(self):
        super().start(self.send_queue)
        return self

    def get_target_motor_speeds(self):
        motor1 = motor2 = motor3 = self.speed
        # TODO vector conversion
        #
        #
        return motor1, motor2, motor3

    #add new motor movement into queue that sends data to controller. 
    #Return true if successfuly added into queue
    def send(self, speed=None, direction=None, thrower=None, callback=None):
        if speed is not None:
            self.speed = speed
        if direction is not None:
            self.direction = direction

        motor1, motor2, motor3 = self.get_target_motor_speeds()
        if not self.send_queue.full(): #ignore when send queue is full
            self.send_queue.put_nowait((motor1, motor2, motor3, thrower, callback))
            return True
        return False

    def close(self):
        self.send_queue.put(STOP_CODE)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":
    #callback functions must be globally accessable for example __main__.callback
    #because lambda doesn't have name, they can't be used
    def callback(x):
        print(x)
    with MotorDriver("/dev/ttyACM0") as driver:
        driver.send(speed=20, direction=0, callback=None) #add new data to send into controller