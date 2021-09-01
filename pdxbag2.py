import argparse
from pathlib import Path, PurePath
import os
import csv
import sys
import requests
import json
import time
import pprint
import bagit
import bagit_profile
import iso8601
from pycountry import Languages
import shutil
from xml.dom import minidom
from datetime import date

VALID_PROFILES = {
	"A1": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_A1.json",
	"A2": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_A2.json",
	"A3": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_A3.json",
	"A4": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_A4.json",
	"DCP1": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_DCP1.json",
	"IMG-SEQ1": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_IMG-SEQ1.json",
	"IMG-SEQ2": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_IMG-SEQ2.json",
	"IMG-SEQ3": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_IMG-SEQ3.json",
	"MIX1": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_MIX1.json",
	"TEST": "https://raw.githubusercontent.com/alula-pds/Bagit_Packager/main/Bagit_Packager/Bagit_Profile_ID_TEST.json",
}

# VALID_PROFILES = ["northstar-picture", "northstar-audio"]
pp = pprint.PrettyPrinter(indent=2)

def has_valid_permissions(folder_path):
	incorrect_permissions = []
	for item in Path(folder_path).rglob("*"):
		# print(item.stat().st_file_attributes)
		if not (os.access(item, os.X_OK | os.W_OK)):
			incorrect_permissions.append(item)
	if len(incorrect_permissions):
		print()
		print("Missing Permissions for the following files:")
		for _ in incorrect_permissions:
			print(_)
		print()
		return False
	return True


def open_permissions(folder_path):
	for root, dirs, files in os.walk(folder_path):  
		for file in files:
			fname = os.path.join(root, file)
			os.chmod(fname, 0o777)

def validate_path(file_path, type):

	if not file_path:
		return None

	resolved_path = Path(file_path).resolve()

	if not Path.exists(resolved_path):
		return None
	if type == "metadata":
		if not Path.is_file(resolved_path or not resolved_path.suffix.lower() == "csv"):
			return None
	if type == "folder":
		if not Path.is_dir(resolved_path):
			print("Cannot access folder, or folder does not exist")
			sys.exit(1)

	return resolved_path


def check(file):
	with open(file) as f:
		datafile = f.readlines()
	found = False  
	for line in datafile:
		if "Audio" in line:           
			return True
	return False 

def extract_audio_content(file):
	with open(file) as f:
		datafile = f.readlines()
	found = False  
	for line in datafile:
		if "Audio_Content" in line:           
			return line.split("Audio_Content: ")[1].lstrip().rstrip("\n")
	return None

def extract_audio_loudness(file):
	with open(file) as f:
		datafile = f.readlines()
	found = False  
	for line in datafile:
		if "Audio_Loudness" in line:           
			return line.split("Audio_Loudness: ")[1].lstrip().rstrip("\n")
	return None

def extract_audio_language(file):
	with open(file) as f:
		datafile = f.readlines()
	found = False  
	for line in datafile:
		if "Audio_Language" in line:           
			return line.split("Audio_Language: ")[1].lstrip().rstrip("\n")
	return None

def convert_to_xml(baginfo, md5, bag):
	absolute_path = os.path.dirname(os.path.abspath(bag))
	name_of_bag = os.path.basename(bag)
	
	root = minidom.Document()  
	xml = root.createElement('root') 
	root.appendChild(xml)
	
	title = root.createElement('Title')
	asset = root.createElement('Asset')
	files = root.createElement('Files')
	package_name_element = root.createElement("PackageName")
	#path_element = root.createElement("Path")
	#path_text = root.createTextNode()
	file_seq_element = root.createElement("FileSequence")
	package_name_text = root.createTextNode(str(name_of_bag))
	package_name_element.appendChild(package_name_text)
	#path_element.appendChild(path_text)
	#files.appendChild(path_element)
	files.appendChild(file_seq_element)
	files.appendChild(package_name_element)

	#hasAudio = check(str(bag)+"/"+baginfo)
	#if hasAudio:
	#	audio_element = root.createElement("Audio")
	#	asset.appendChild(audio_element)

	with open(str(bag)+"/"+baginfo) as f:
		for line in f:
			key_text = line.split(":")[0].rstrip("\n")
			value_text = line.split(":")[1].lstrip().rstrip("\n")
			key = root.createElement(key_text)
			text = root.createTextNode(value_text)
			if "UMCVARID" in key_text:
				title.appendChild(key)
				key.appendChild(text)
			elif ("Bag" not in key_text 
				and "Audio" not in key_text):
				asset.appendChild(key)
				key.appendChild(text)
			
			if "Audio_Configuration" in key_text:
				audio_element = root.createElement("Audio")
				asset.appendChild(audio_element)

				config_id = key_text.split("Audio_Configuration")[1]
				config_id_element = root.createElement("Config_ID")
				config_value_element = root.createElement("Audio_Configuration")
				config_value_text = root.createTextNode(value_text)
				config_value_element.appendChild(config_value_text)
				config_id_text = root.createTextNode(config_id)
				config_id_element.appendChild(config_id_text)
				audio_element.appendChild(config_id_element)
				audio_element.appendChild(config_value_element)
				
				audio_content_element = root.createElement("Audio_Content")
				audio_content_text = root.createTextNode(extract_audio_content(str(bag)+"/"+baginfo))
				audio_content_element.appendChild(audio_content_text)
				
				audio_loudness_element = root.createElement("Audio_Loudness")
				audio_loudness_text = root.createTextNode(extract_audio_loudness(str(bag)+"/"+baginfo))
				audio_loudness_element.appendChild(audio_loudness_text)
				
				audio_language_element = root.createElement("Audio_Language")
				audio_language_text = root.createTextNode(extract_audio_language(str(bag)+"/"+baginfo))
				audio_language_element.appendChild(audio_language_text)
				
				audio_element.appendChild(audio_content_element)
				audio_element.appendChild(audio_loudness_element)
				audio_element.appendChild(audio_language_element)

	n = 1
	with open(str(bag)+"/"+md5) as f:
		for line in f:
			md5_hash = line.split()[0].rstrip("\n")
			filename_path = line.split()[1].lstrip().rstrip("\n")
			filename = os.path.basename(filename_path)
			sequence_id = n
			last_mod_date = date.fromtimestamp(os.path.getmtime(str(bag)+'/'+filename_path))
			file_element = root.createElement("File")
			files.appendChild(file_element)
			
			sequence_id_element = root.createElement("SequenceID")
			sequence_id_text = root.createTextNode(str(n))
			sequence_id_element.appendChild(sequence_id_text)
			
			md5_element = root.createElement("MD5")
			md5_text = root.createTextNode(md5_hash)
			md5_element.appendChild(md5_text)

			filename_element = root.createElement("Filename")
			file_text = root.createTextNode(filename_path)
			filename_element.appendChild(file_text)         
			
			last_mod_element = root.createElement("LastModifiedDate")
			last_mod_text = root.createTextNode(str(last_mod_date))
			last_mod_element.appendChild(last_mod_text)

			file_element.appendChild(sequence_id_element)
			file_element.appendChild(md5_element)
			file_element.appendChild(filename_element)
			file_element.appendChild(last_mod_element)
			
			file_seq_element.appendChild(file_element)
			n+=1

	xml.appendChild(title)  
	xml.appendChild(asset) 
	xml.appendChild(files) 

	xml_str = root.toprettyxml(indent ="\t") 
  
	save_path_file = str(bag)+".xml"
  
	with open(save_path_file, "w") as f:
		f.write(xml_str) 

def create_bag(folder_path, bag_name, metadata, threads=1):

	print("Moving files into 'data' folder and creating MD5 hashes")
	# Temporarily move files to temp root folder
	
	tic = time.perf_counter()
	bagit.make_bag(folder_path, metadata, threads, ["md5"])
	toc = time.perf_counter()
	print(f"Bag created in {toc - tic:0.4f} seconds with {threads} threads.")
	
	if bag_name:
		print(f"Renaming folder to provided name {bag_name}")
		# old_name = pathlib.Path(folder_path)
		new_name = Path(folder_path).parent.joinpath(bag_name)
		# print("Old:", old_name, type(old_name))
		# print("New:", new_name, type(new_name))
		print(str(new_name))
		Path(folder_path).rename(str(new_name))
		for f in os.listdir(new_name):
			if "bag-info.txt" in f:
				baginfo=f
			elif "manifest-md5.txt" in f:
				md5=f
		convert_to_xml(baginfo, md5, new_name)

def get_fields_from_file(file_path):
	fields = {}

	with open(file_path, "r") as f:
		for line in f.readlines():
			line = line.strip("\n")
			if ":" in line:
				key = line.split(":")[0]
				value = "".join(line.split(":")[1:])
				fields[key.replace("-", "_")] = value.strip()

	return fields


def validate_datatypes(bag):
	"""Assumes a valid bag/bag info; returns true if all datatypes in bag pass"""

	dates = []
	langz = []

	bag_dates_to_validate = ["Date_Start", "Date_End", "Bagging_Date"]
	bag_info_data = get_fields_from_file(
		PurePath(str(bag)).joinpath("bag-info.txt")
	)

	for k, v in bag_info_data.items():
		if k in bag_dates_to_validate:
			dates.append(v)
		if k == "Language":
			langz.append(v)

	if dates:
		for date in dates:
			try:
				iso8601.parse_date(date)
			except:
				print("Invalid Date: '{}'".format(date))
				return False

	if langz:
		for language in langz:
			try:
				languages.lookup(language)
			except:
				print("Invalid Language Code: '{}'".format(language))
				return False
	return True


def validate_bag(folder_path, profile_url, threads=1):
	bag = bagit.Bag(folder_path)
	profile = bagit_profile.Profile(profile_url)

	print()
	print("Validating bag and verifying MD5 hashes.")
	tic = time.perf_counter()

	try:
		bag.validate()
		print("\tBag valid according to BagIt specification")
		bag_is_valid = True
	except bagit.BagValidationError as e:
		print("\tBag invalid according to BagIt specification")
		print(e)
		sys.exit(1)

	print()
	print("Validating bag profile.")
	try:
		profile.validate_serialization(folder_path)
		print("\tBag serialization validates")
		bag_profile_serialization_is_valid = True
	except:
		print("\tBag serialization does not validate")
		sys.exit(1)

	if profile.validate(bag):
		print("\tBag valid according to Northstar profile")
		bag_profile_valid = True
	else:
		print("\tBag invalid according to Northstar profile")
		sys.exit(1)

	if validate_datatypes(bag):
		print("\tAll datatypes in bag are valid")
		bag_datatypes_valid = True
	else:
		print("\tInvalid datatypes")
		sys.exit(1)


def get_profile_data(profile_name=None):
	"""Returns "Bag-Info" from Alula-PDS BagIt profile on GitHub with provided ID

	Parameters:
	profile_name (string): ID of profile in GitHub repo at "https://github.com/alula-pds/Bagit_Packager/tree/main/Bagit_Packager"

	Returns:
	profile_bag_info (dict): "Bag-Info" section from retrieved BagIt Profile

	"""

	profile_url = VALID_PROFILES[profile_name]

	try:
		response = json.loads(requests.get(profile_url).text)
		profile_bag_info = response["Bag-Info"]
	except:
		print("Error retrieving profile JSON from GitHub")
		sys.exit(1)

	return profile_bag_info

def parse_metadata(metadata_file=None):
	"""Returns Data from fields in Metadata file

	Parameters:
	csv_file (string): CSV file with Metadata keys and values

	Returns:
	provided_metadata (dict): Keys and values from Metadata file

	"""

	if metadata_file.suffix == ".csv":
		data = None
		with open(metadata_file, "r", encoding="utf-8-sig") as source:
			csv_reader = csv.DictReader(source)
			line_count = 0
			for row in csv_reader:
				line_count += 1
				if line_count == 1:
					pp.pprint(row)
					data = row
				else:
					break
		return data
	if metadata_file.suffix == ".json":
		print("Not Yet Implemented")

def validate_metadata(metadata, profile):
	"""Returns true if provided Metadata is valid for the selected Profile

	Parameters:
	metadata (dict): CSV file with Metadata keys and values
	profile (dict): Keys and values from Metadata file

	Returns:
	valid_metadata (dict): Updated metadata (dict) if all required data is provided else None
	
	"""
	metadata_keys = metadata.keys()
	profile_keys = profile.keys()

	missing_required_keys = []
	invalid_values = []
	additional_keys = []
	empty_optional_keys = []

	## Missing Keys in Metadata that are 'required' in Profile ##
	for key in profile_keys:
		if profile[key]["required"] and key not in metadata_keys:
			missing_required_keys.append(key)
			continue
	
	for key in metadata_keys:
		value = metadata[key]

		## Additional Keys in Metadata that are not in Profile ##
		if key not in profile_keys:
			## Additional Key has value set - keep in metadata
			if value:
				additional_keys.append((key, value))
			## Additional Key is empty or has no value set - to be removed
			else:
				empty_optional_keys.append(key)

		## Keys in Metadata that are in Profile ##
		else:
			## Key empty or has no value set ##
			if not value:
				## Empty Key is required in Profile - cannot proceed
				if profile[key]["required"]:
					invalid_values.append((key, value))
					continue
				## Empty Key is optional - to be removed
				else:
					# print("Empty key is optional, but has no value:", key)
					empty_optional_keys.append(key)
			
			try:
				## Key has specific possible Values specified in Profile
				allowed_values = profile[key]["values"]
				## Value not in Allowed Values - cannot proceed
				if value not in allowed_values:
					if key not in empty_optional_keys:
						invalid_values.append((key, value))
						continue

			except: 
				## Key can have any value
				# print("Key can have any value:", key)
				continue


	if len(missing_required_keys):
		valid_metadata = None
		print("Missing Required Data for Profile")
		for _ in missing_required_keys:
			print("-", _)
	if len(invalid_values):
		valid_metadata = None
		print("Found Invalid Values for Profile")
		for _ in invalid_values:
			print("-", _[0], ":", _[1] or "NO VALUE PROVIDED")

	if len(empty_optional_keys):
		for key in empty_optional_keys:
			# print()
			print("Deleting Empty Optional Key:", key)
			# print("Before:")
			# pp.pprint([_ for _ in metadata.keys()])
			del metadata[key]
			# print("After:")
			# pp.pprint([_ for _ in metadata.keys()])
		print()

	valid_metadata = metadata
	
	return valid_metadata

def transpose_bagit():
	pass
	

if __name__ == "__main__":

	## Setup Arguments ##
	parser = argparse.ArgumentParser(description="PDX Bag CLI")
	parser.add_argument("folder", help="Path to Bag folder or Folder to be bagged")
	parser.add_argument(
		"action", help="Action to perform on folder", choices=["create", "validate"]
	)
	parser.add_argument("-m", "--metadata", help="Path to CSV file with Bag Metadata")
	parser.add_argument(
		"-p",
		"--profile",
		help="Name of Bagit Profile to use when creating or validating bag",
	)
	parser.add_argument("-n", "--name", help="Bag Name to be used when creating bag")
	parser.add_argument(
		"-t", "--threads", help="Number of threads to use for operations"
	)
	args = parser.parse_args()

	## Validate Arguments ##
	folder_path = validate_path(args.folder, "folder")
	metadata_path = validate_path(args.metadata, "metadata")
	bag_name = args.name.strip() if args.name else None
	bag_name = (
		bag_name + ".pdxbag"
		if bag_name is not None and not bag_name.lower().endswith(".pdxbag")
		else bag_name
	)
	profile_name = (
		args.profile
		if args.profile is not None and args.profile in VALID_PROFILES.keys()
		else None
	)
	threads = args.threads if args.threads else 1

	## Create PDXBAG ##
	if args.action == "create":
		if not profile_name:
			print("Profile Name Missing or Incorrect")
			sys.exit(1)
		if not metadata_path:
			print("Cannot access metadata file, or file does not exist")
			sys.exit(1)
		if not has_valid_permissions(folder_path):
			#print("Skipping Bag Creation")
			#sys.exit(1)
			print("Opening permissions...")
			open_permissions(folder_path)
		
		profile_bag_info = get_profile_data(profile_name)
		profile_url = VALID_PROFILES[profile_name]
		# pp.pprint(profile_bag_info)
		provided_metadata = parse_metadata(metadata_path)
		provided_metadata["BagIt-Profile-Identifier"] = profile_url
		# pp.pprint(provided_metadata)

		if not provided_metadata:
			print("Error reading Metadata file")
			sys.exit(1)

		valid_metadata = validate_metadata(provided_metadata, profile_bag_info)
		if valid_metadata:
			try:
				'''
				folder_to_preserve = os.path.basename(folder_path)
				absolute_path = os.path.dirname(os.path.abspath(folder_path))
				dest = absolute_path+"/temp/"+folder_to_preserve
				if not os.path.exists(dest):
					os.makedirs(dest)
				files = os.listdir(str(folder_path))
				for f in files:
					shutil.move(str(folder_path)+"/"+f, dest)
				if len(os.listdir(folder_path)) == 0:
					os.rmdir(folder_path)
				'''
				create_bag(folder_path, bag_name, provided_metadata, threads)
			except bagit.BagError:
				print("Error creating bag")
				sys.exit(1)
	
	## Create PDXBAG ##
	if args.action == "validate":
		try:        
			profile_url = VALID_PROFILES[profile_name]
			validate_bag(str(folder_path), profile_url, threads)
		except bagit.BagError as error:
			print("Error validating bag")
			print(repr(error))
			sys.exit(1)