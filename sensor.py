import json
import serial
import struct
import time
from smbus2 import SMBus, i2c_msg

class ISensor:
	
	def __init__(self, serial_path, baud_rate, gas):
		pass

	def read_data(): 
		pass


class SpecSensor(ISensor):
	
	gas_to_unit = { 
		"O3": "ppb",
		"CO": "ppb",
		"NO2": "ppb"
	}

	def __init__(self, serial_path, baud_rate, gas):
		self.timeout = 5     # seconds
		self.serial = serial.Serial(serial_path, baud_rate, timeout=self.timeout)
		# self.serial.write(b"r")
		self.gas = gas 
		self.labels = ["serial_number", self.gas, "temp", "humidity", "raw_value", "temp_digital", "humidity_digital", "day", "hour", "minute", "second"]
		self.serial.write(b"c")

	def read_data(self, retries=3):
		current_char = ""	   
		output_list = []
		start = time.time()
		while current_char != "\n" and (time.time() - start) < self.timeout:
			current_char = self.serial.read(1).decode("utf-8")
			output_list.append(current_char) 
		output_str = "".join(output_list)[:-2]
		output = self.convert_to_json(output_str, retries)
		return output

	def convert_to_json(self, output_str, retries):
		# retry if empty
		if not output_str: 
			self.serial.write(b"c")
			return self.read_data(retries=retries-1)
		if retries > 0:
			try: 
				return {label: val for (label, val) in zip(self.labels, output_str.split(sep=", "))}
			except Exception as e: 
				print(e)
				return {}
		else:
			return {label: val for (label, val) in zip(self.labels, output_str.split(sep=", "))}
			

class UThingSensor(ISensor):

	def __init__(self, serial_path, baud_rate, gas):
		self.serial = serial.Serial(serial_path, baud_rate)

	def read_data(self): 
		current_char = ""
		output_list = []
		while current_char != "\n":
			current_char = self.serial.read(1).decode("utf-8")
			output_list.append(current_char)
		output_str = "".join(output_list) 
		try:
			return json.loads(output_str)
		except Exception as e:
			print(e)	
			return {}	

class SDS011Sensor(ISensor):
		
	encoder = {
		"head": b'\xaa',
		"tail": b'\xab',
		"cmd_id": b'\xb4',
		"read": b'\x00',
		"write": b'\x01',
		"report_mode_cmd": b'\x02',
		"active": b'x\00',
		"passive": b'x\01',
		"query_cmd": b'\x04',
		"sleep_cmd": b'\x06',
		"sleep": b'\x00',
		"work": b'\x01',
		"work_period_cmd": b'\x08',
		"start": b'\xc0'
	}

	def __init__(self, serial_path, baud_rate, gas):
		self.timeout = 5
		self.serial = serial.Serial(serial_path, baud_rate, timeout=self.timeout)
		self.serial.flush()

	def read_data(self):
		"""Query the device and read the data.
		@return: Air particulate density in micrograms per cubic meter.
		@rtype: tuple(float, float) -> (PM2.5, PM10)
		"""
		time.sleep(0.8)
		cmd = self._cmd_begin()
		cmd += (self.encoder["query_cmd"]
				+ b"\x00" * 12)
		cmd = self._finish_cmd(cmd)
		self._execute(cmd)

		raw = self._get_reply()
		if raw is None:
			return None  #TODO:
		data = struct.unpack('<HH', raw[2:6])
		pm25 = data[0] / 10.0
		pm10 = data[1] / 10.0
		return {"pm2.5": pm25, "pm10": pm10} 

	def set_report_mode(self, read=False, active=False):
		"""Get sleep command. Does not contain checksum and tail.
		@rtype: list
		"""
		cmd = self.cmd_begin()
		cmd += (self.encoder["report_mode_cmd"]
			+ (self.encoder["read"] if read else self.encoder["write"])
			+ (self.encoder["active"] if active else self.encoder["passive"])
			+ b"\x00" * 10)
		cmd = self._finish_cmd(cmd)
		self._execute(cmd)
		self._get_reply()

	def _execute(self, cmd_bytes):
		"""Writes a byte sequence to the serial.
		"""
		self.serial.write(cmd_bytes)

	def _cmd_begin(self):
		"""Get command header and command ID bytes.
		@rtype: list
		"""
		return self.encoder["head"] + self.encoder["cmd_id"]

	def _get_reply(self):
		"""Read reply from device."""
		raw = self.serial.read(size=10)
		data = raw[2:8]
		if len(data) == 0:
			return None
		if (sum(d for d in data) & 255) != raw[8]:
			raise Exception("Checksum Failed")
		return raw

	def _finish_cmd(self, cmd, id1=b"\xff", id2=b"\xff"):
		cmd += id1 + id2
		checksum = sum(d for d in cmd[2:]) % 256
		cmd += bytes([checksum]) + self.encoder["tail"]
		return cmd

class CO2Meter_I2C(ISensor):
	CMD_READ_REG = 0x22
	REG_CO2_PPM = 0x08
	I2C_SLAVE = 0x0703
	addr = 0x68

	def __init__(self, serial_path, baud_rate, gas):
		self.bus_number = int(serial_path[-1])
		checksum = (self.CMD_READ_REG + self.REG_CO2_PPM) & 0xFF
		self._write_request = i2c_msg.write(self.addr, [self.CMD_READ_REG, 0x00, self.REG_CO2_PPM, checksum])

	def _request_data(self):
		self.bus.i2c_rdwr(self._write_request)

	def _read_data(self):
		read_request = i2c_msg.read(self.addr, 4)
		raw_data = self.bus.i2c_rdwr(read_request)
		return list(read_request)

	def read_data(self):
		try:
			self.bus = SMBus(self.bus_number)
			time.sleep(3.0)
			self._request_data()
			time.sleep(0.025)
			list_output = self._read_data()
			final_output = ((list_output[1] & 0xFF) << 8) | (list_output[2] & 0xFF)
			self.bus.close()
			return {"CO2": final_output}
		except Exception as e:
			self.bus.close()
			print("Exception in CO2Meter: ", e)
			return self.read_data()

class CO2Meter(ISensor):

	def __init__(self, serial_path, baud_rate, gas):
		self.serial = serial.Serial(serial_path, baud_rate, timeout=5)
	
	def read_data(self):
		self.serial.flushInput()
		self.serial.write(b"\xFE\x44\x00\x08\x02\x9F\x25")
		time.sleep(2)
		resp = self.serial.read(7)
		co2 = resp[3]*256 +resp[4]
		time.sleep(0.1)
		return {"CO2": co2}
