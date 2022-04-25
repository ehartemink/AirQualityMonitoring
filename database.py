import os
import pandas as pd
import numpy as np
import datetime as dt
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
			self._open_table()
		# File may not exist
		except FileNotFoundError:
			self._initialize_table()

	def batch_write(self, batch):
		self.lock.acquire()
		output_data = pd.DataFrame.from_records(batch)
		output_data.to_csv(self.path, index=False, mode="a", header=False)
		self.lock.release()

	def open_table(self):
		self.lock.acquire()
		try:
			df = self._open_table()
		except pd.errors.EmptyDataError:
			self.lock.release()
			return self.open_table()
		self.lock.release()
		return df

	def _open_table(self):
		return pd.read_csv(self.path, engine="c", dtype=self.schema)

	def remove_old_logs(self):
		start = dt.datetime.now()
		self.lock.acquire()
		df = self._open_table()

		# remove logs older than 1 week
		one_week_ago = (dt.datetime.now() - dt.timedelta(seconds=60 * 60 * 24 * 7)).timestamp()
		df = df[df.timestamp > one_week_ago]

		# consolidate logs older than 1 hour into minute-by-minute logs
		one_hour_ago = (dt.datetime.now() - dt.timedelta(seconds=3600)).timestamp()
		older_than_one_week_ago = df.timestamp > one_hour_ago
		last_hour_df = df[older_than_one_week_ago]
		older_than_hour_df = df[~older_than_one_week_ago]
		older_than_hour_df["timestamp"] = (older_than_hour_df["timestamp"] // 60) * 60.0
		older_than_hour_df.groupby(["metric", "timestamp"]).mean().reset_index()
		output_df = pd.concat([older_than_hour_df, last_hour_df], ignore_index=True)
		output_df.to_csv(self.path, index=False)
		self.lock.release()

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

