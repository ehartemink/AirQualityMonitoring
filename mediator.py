import datetime as dt 

def transform(data, wakeword):
	return wakewords[wakeword](data, wakeword)

def _create_record_from_field(data, key):
	output_data = {
		"metric": key,
		"value": data[key],
		"timestamp": dt.datetime.now().timestamp()
	}
	return output_data

def _spec_transform(data, wakeword):
	return [_create_record_from_field(data, wakeword)]

def _u_thing_transform(data, wakeword):
	return [_create_record_from_field(data, key) for key in ("temperature", "pressure", "humidity", "IAQ", "eqCO2")]

def _sd011_transform(data, wakeword):
	return [_create_record_from_field(data, key) for key in ("pm2.5", "pm10")]

def _co2_meter_transform(data, wakeword):
	if data[wakeword] > 5000:
		return []
	else:
		return [_create_record_from_field(data, wakeword)]

wakewords = {
	"O3": _spec_transform,
	"CO": _spec_transform,
	"NO2": _spec_transform,
	"VOC": _u_thing_transform,
	"PM": _sd011_transform,
	"CO2": _co2_meter_transform
}	
