import json
import time
import numpy as np
import mediator
import threading
import database
import datetime as dt
from sensor import * 

database_path = "persist/table.csv"
with open("config.json", "r") as f:
	json_string = f.read()

config = json.loads(json_string)
print(config)

sensors = {}

for (gas, serial_path) in config.items():
	full_serial_path = "/dev/" + serial_path
	if gas == "VOC":
		sensors[gas] = UThingSensor(full_serial_path, 9600, gas)
	elif gas in "CO O3 NO2".split(): 
		sensors[gas] = SpecSensor(full_serial_path, 9600, gas)
	elif gas == "PM":
		sensors[gas] = SDS011Sensor(full_serial_path, 9600, gas)
	elif gas == "CO2":
		sensors[gas] = CO2Meter(full_serial_path, 9600, gas)
	else:
		print("Sensor not found ", gas)

db = database.DataBase(database_path)

def read_and_print_data(wakeword, sensor, mediator, db):
	while True:
		try:
			raw_data = sensor.read_data()
			processed_data = mediator.transform(raw_data, wakeword)
			db.batch_write(processed_data)
		except:
			print(f"{dt.datetime.now()}: exception in sensor: {wakeword}")
def data_cleaning_daemon(db):
	while True:
		time.sleep(60)		
		db.remove_old_logs()

new_threads = {} 

for (port, sensor) in sensors.items():
	new_threads[port] = threading.Thread(target=read_and_print_data, name=port, args=(port, sensor, mediator, db))
new_threads["remove_old_logs"] = threading.Thread(target=data_cleaning_daemon, name="remove old logs", args=[db])

for port, thread in new_threads.items():
	thread.start()
for port, thread in new_threads.items():
	thread.join()

