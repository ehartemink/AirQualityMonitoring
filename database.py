import os
import pandas as pd
import numpy as np
from threading import Lock

class DataBase:
	schema = {
		"metric": str,
		"value": np.float64,
		"timestamp": np.float64
	}

	def __init__(self, path):
		self.path = path
		self.lock = Lock()
		try:
			self.open_table()
		# File may not exist
		except FileNotFoundError:
			self._initialize_table()

	def batch_write(self, batch):
		self.lock.acquire()
		output_data = pd.DataFrame.from_records(batch)
		output_data.to_csv(self.path, index=False, mode="a", header=False)
		self.lock.release()

	def open_table(self):
		df = pd.read_csv(self.path, engine="c", dtype=self.schema)
		return df

	def _initialize_table(self):
		df = pd.DataFrame(columns=self.schema.keys())
		try:
			df.to_csv(self.path, index=False)
		# Folder that should contain file does not exist
		except FileNotFoundError:
			# create folder recursively
			split_path = self.path.split(sep="/")
			create_folder = ""
			for folder in split_path[:-1]:
				create_folder += folder
				os.mkdir(create_folder)
			df.to_csv(self.path, index=False)


class ThreadSafeDict:

	def __init__(self):
		self._cache = {} 
		self._locks = {}

	def __setitem__(self, key, value):
		if key not in self._cache:	
			self._locks[key] = Lock()
		self._locks[key].acquire()
		self._cache[key] = value
		self._locks[key].release()

	def __getitem__(self, key):
		self._locks[key].acquire()
		output = self._cache[key]
		self._locks[key].release()
		return output

	def aqcuire_lock(self, key):
		self._locks[key].acquire()
	
	def release_lock(self, key):
		self._locks[key].release()

	def get_unsafe(self, key):
		return self._cache[key]
	
	def set_unsafe(self, key, value):
		self._cache[key] = value

