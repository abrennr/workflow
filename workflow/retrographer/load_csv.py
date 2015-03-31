import sys
import os
os.environ["DJANGO_SETTINGS_MODULE"] = 'geodata.settings'
import geodata.retrographer.models
import csv 
import datetime

def filter_nan(s):
	return s.replace('NaN', '""')

def load_data(data_file):
	"""load retrographer tag data in csv format."""
	csv_data = csv.DictReader(open(data_file, 'r'))
	for line in csv_data:
		tag = geodata.retrographer.models.Tag()
		tag.id = int(line['tag id'])
		tag.photo_id = line['photo identifier']
		tag.retrographer_id = int(line['retrographer ID'])
		tag.user_id = int(line['user id'])
		tag.user_first_name = line['user first name']
		tag.lat = float(line['lat'])
		tag.long = float(line['long'])
		try:
			tag.heading = float(filter_nan(line['heading']))
		except:
			pass
		try:
			tag.pitch = float(filter_nan(line['pitch']))
		except:
			pass	
		try:
			tag.zoom = float(filter_nan(line['zoom']))
		except:
			pass
		tag.timestamp =  datetime.datetime.strptime(line['created_at'], '%Y-%m-%d %H:%M:%S %Z')
		tag.is_used = bool(line['is used'])
		tag.save()

def main():
	load_data(sys.argv[1])
		
if __name__ == '__main__':
	main()

