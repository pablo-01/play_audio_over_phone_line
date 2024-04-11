import serial
import time
import threading
import atexit
import sys
import wave

# Define a class to encapsulate modem operations
class Modem:
    def __init__(self):
        self.analog_modem = serial.Serial()
        self.analog_modem.port = "/dev/ttyACM0"
        self.analog_modem.baudrate = 57600
        self.analog_modem.bytesize = serial.EIGHTBITS
        self.analog_modem.parity = serial.PARITY_NONE
        self.analog_modem.stopbits = serial.STOPBITS_ONE
        self.analog_modem.timeout = 3
        self.analog_modem.xonxoff = False
        self.analog_modem.rtscts = False
        self.analog_modem.dsrdtr = False
        self.analog_modem.writeTimeout = 3

        self.disable_modem_event_listener = True
        self.RINGS_BEFORE_AUTO_ANSWER = 2

    def init_modem_settings(self):
        try:
            self.analog_modem.open()
        except Exception as e:
            print(f"Error: Unable to open the Serial Port. {e}")
            sys.exit()

        try:
            self.analog_modem.flushInput()
            self.analog_modem.flushOutput()

            commands = ["AT", "ATZ3", "ATV1", "ATE1", "AT+VCID=1"]
            for cmd in commands:
                if not self.exec_AT_cmd(cmd):
                    print(f"Error: Command {cmd} failed")
                    sys.exit()
        except Exception as e:
            print(f"Error: unable to Initialize the Modem. {e}")
            sys.exit()

    def exec_AT_cmd(self, modem_AT_cmd):
        try:
            self.disable_modem_event_listener = True

            cmd = modem_AT_cmd + "\r"
            self.analog_modem.write(cmd.encode())

            modem_response = self.analog_modem.readline().decode() + self.analog_modem.readline().decode()

            print(modem_response)

            self.disable_modem_event_listener = False

            if ("OK" in modem_response) or (("CONNECT" in modem_response) and (modem_AT_cmd in ["AT+VTX", "AT+VRX"])):
                return True
            else:
                return False
        except Exception as e:
            print(f"Error: unable to write AT command to the modem... {e}")
            self.disable_modem_event_listener = False
            return False

    def play_audio(self):
        print("Play Audio Msg - Start")
        if not self.exec_AT_cmd("AT+FCLASS=8"):
            print("Error: Failed to put modem into voice mode.")
            return

        if not self.exec_AT_cmd("AT+VSM=128,8000"):
            print("Error: Failed to set compression method and sampling rate specifications.")
            return

        if not self.exec_AT_cmd("AT+VLS=1") or not self.exec_AT_cmd("AT+VTX"):
            print("Error: Unable put modem into TAD mode.")
            return

        time.sleep(1)
        self.disable_modem_event_listener = True

        with wave.open('sample.wav', 'rb') as wf:
            chunk = 1024
            data = wf.readframes(chunk)
            while data:
                self.analog_modem.write(data)
                data = wf.readframes(chunk)
                time.sleep(.12)

        cmd = "<DLE><ETX>\r".encode()
        self.analog_modem.write(cmd)

        timeout = time.time() + 120  # 2 minutes
        while True:
            if "OK" in self.analog_modem.readline().decode() or time.time() > timeout:
                break

        self.disable_modem_event_listener = False
        self.exec_AT_cmd("ATH")
        print("Play Audio Msg - END")

    def read_data(self):
        ring_data = ""
        while True:
            if not self.disable_modem_event_listener:
                modem_data = self.analog_modem.readline().decode()
                if modem_data:
                    print(modem_data)
                    # Process ring data
                    if "RING" in modem_data:
                        ring_data += modem_data
                        if ring_data.count("RING") == self.RINGS_BEFORE_AUTO_ANSWER:
                            ring_data = ""
                            self.play_audio()

    def close_modem_port(self):
        self.exec_AT_cmd("ATH")
        if self.analog_modem.isOpen():
            self.analog_modem.close()
            print("Serial Port closed...")

modem = Modem()
modem.init_modem_settings()

# Start a new thread to listen to modem data
data_listener_thread = threading.Thread(target=modem.read_data)
data_listener_thread.start()

# Ensure the modem is closed properly upon program termination
atexit.register(modem.close_modem_port)
