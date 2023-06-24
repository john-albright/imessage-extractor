import sqlite3
import re
import datetime
import sys
import glob
import os
import shutil
import platform
import math
from datetime import datetime
from dotenv import load_dotenv

# Flag to determine whether image files are saved or a .txt file with their paths is created
SAVE_IMAGE_FILES = False

# Flag to determine whether the vcf file should be processed 
USE_VCF = True

# Load environment variables from .env file
load_dotenv()
chat_db_location = os.getenv('CHAT_DB')
apple_contact_db_location = os.getenv('CONTACT_DB')

# Get system information about the current MacBook
mac_info = platform.mac_ver()
os_version = mac_info[0]
os_sub_version = int(re.findall('(?<=[.]).*(?=[.])', os_version)[0])
high_sierra_min = True if os_sub_version > 11 else False

if __name__ == '__main__':
	# Start the timer
	start_time = datetime.now()

	# Connect to the database
	db = sqlite3.connect(chat_db_location)

	# Create a cursor
	cur = db.cursor()

	# Initialize the dictionary that will map handle ids to phone numbers and emails
	# Example key-value pairs: { 1: '17733333333', 309: 'abby1234567@me.org' }
	handle_dict = {}

	# Declare regex strings to be used for filtering phone numbers 
	remove_unicode_reg = '[^\u0000-\u007F]+'
	remove_nondigits_reg = '[^\d]*'

	# Get the ROWID and id from the handle table
	cur.execute('SELECT ROWID, id FROM handle')

	# Populate handle_dict
	for row in cur.fetchall():
		handle_dict[row[0]] = re.sub('^[+]', '', row[1])

	my_addresses = []

	# Get emails and numbers of the user 
	cur.execute('SELECT DISTINCT last_addressed_handle FROM chat')

	for my_handle in cur.fetchall():
		my_address = my_handle[0]
		# Update list with contact information
		if my_address and my_address not in my_addresses:
			if not re.findall('^[A-Za-z]', my_address):
				my_address = re.sub(remove_nondigits_reg, '', my_address)
			my_addresses.append(my_address)

	#print(my_addresses)
	#sys.exit(2)
	# Optional print statements to check the values of the handle dictionary
	#print(handle_dict)
	#for k, v in sorted(handle_dict.items()): 
	#	print(k, v)

	# Initialize the dictionary that will map contact information to names
	# Example key-value pair: { 'poodle@gmail123.com': 'Favorite Poodle' }
	contact_dict = {}

	# Initialize strings to be emptied and refilled if using a vcf file
	# Otherwise initialize strings to be filled when searching the Apple .db file
	name = ''
	email = ''
	telephone = ''

	if USE_VCF:
		# Open vCard file 
		try:
			vcfFile = open('contacts.vcf', 'r')
		except FileNotFoundError:
			print('No file \'contacts.vcf\' found in the parent directory.')
			sys.exit(0)

		name_reg = 'FN:(.*)'
		email_reg = 'EMAIL.*:(.*)'
		tel_reg = 'TEL.*:(.*)'

		for line in vcfFile:
			if re.search(name_reg, line):
				name = re.findall(name_reg, line)[0]
			if re.search(email_reg, line):
				email = re.findall(email_reg, line)[0]
			if re.search(tel_reg, line):
				telephone = re.findall(tel_reg, line, re.MULTILINE)[0]
				telephone = re.sub(remove_unicode_reg, '', telephone)
				telephone = re.sub(remove_nondigits_reg, '', telephone)
			if re.search('END:VCARD.*', line):
				name = ''
			
			if name:
				if email and email not in my_addresses:
					contact_dict[email] = name
					email = ''
				if telephone and telephone not in my_addresses:
					contact_dict[telephone] = name
					telephone = ''
	else:
		#print(apple_contact_db_location)
		if os.path.isfile(apple_contact_db_location):
			db2 = sqlite3.connect(apple_contact_db_location)
		else:
			print(f'No file path ${apple_contact_db_location} exists.')
			sys.exit(1)

		cur2 = db2.cursor()

		# Perform an SQL operation to select all phone numbers and emails and the first and 
		# last names associated with those by joining the tables ZABCDRECORD, ZABCDPHONENUMBER,
		# and ZABCDEMAILADDRESS
		cur2.execute('SELECT ph.ZFULLNUMBER, em.ZADDRESSNORMALIZED, ZFIRSTNAME, ZLASTNAME FROM ZABCDRECORD INNER JOIN ZABCDPHONENUMBER AS ph ON ZABCDRECORD.Z_PK = ph.ZOWNER INNER JOIN ZABCDEMAILADDRESS AS em ON ZABCDRECORD.Z_PK = em.ZOWNER')

		for contact in cur2.fetchall():
			#print(contact)
			#continue
			telephone = contact[0]
			telephone = re.sub(remove_unicode_reg, '', telephone)
			telephone = re.sub(removeNondigitsReg, '', telephone)
			email = contact[1]
			if contact[2]:
				name = contact[2]
			if contact[3]:
				name = name + " " + contact[3] 
			if not name:
				print(telephone, "No name")
				continue
			
			# Map telephone numbers and email addresses to full names
			if telephone not in my_addresses:
				contact_dict[telephone] = name
			if email not in my_addresses:
				contact_dict[email] = name

			# Reset all variables
			name = ''
			telephone = ''
			email = ''


	# Initialize the dictionary that will map chat ids to contact information of the iMessage user
	my_contact_info = {}

	# Add contacts of the iMessage user, i.e. all email accounts and phone numbers
	# associated with the user
	cur.execute('SELECT ROWID, last_addressed_handle FROM chat')

	for row in cur.fetchall():
		chat_id = row[0]
		contact_info = row[1]
		#print(chat_id, contact_info)
		
		if not contact_info:
			contact_info = 'multiple addresses'
		if not re.findall('^[A-Za-z]', contact_info):
			contact_info = re.sub(remove_nondigits_reg, '', contact_info)

		# Update dictionary with chat_id and contact_info	
		my_contact_info[chat_id] = contact_info

	#print(my_contact_info)
	#print(my_contacts)
	#sys.exit(8)

	# Initialize the dictionary that will map cache roomnames to group names
	# Example key-value pair: { 'chat797599165314668063' : 'group77' }
	groups_dict = {}

	cur.execute('SELECT room_name, display_name, ROWID FROM chat WHERE room_name IS NOT NULL')

	misc_group_num = 0

	for chat in cur.fetchall():
		if chat[0]:
			if chat[1]:
				groups_dict[chat[0]] = chat[1]
			else:
				misc_group_num += 1
				groups_dict[chat[0]] = f'group{misc_group_num}'

	#print(groups_dict)

	#sys.exit(4)

	# Initialize the dictionary that will map chat ids to image file paths
	# Example key-value pair: { '621': { 'filepath': '~\Library\IMG_6542.jpg', 'name': 'IMG_652.jpg' }}
	attachments = {}

	cur.execute('SELECT message_attachment_join.message_id, filename, transfer_name FROM attachment INNER JOIN message_attachment_join ON attachment.ROWID=message_attachment_join.attachment_id')

	for attachment in cur.fetchall():
		#filepath = re.sub('^~', '/Users/John', attachment[1])
		filepath = attachment[1]
		#print(attachment[1])
		attachments[attachment[0]] = {'filepath': filepath, 'name': attachment[2]}

	#print(attachments)
	#sys.exit(0)

	# Create dictionary that will map chat_id to message_id
	# Example key-value pairs: { 21: ['124123333', '15745634442', '1238433324'] }
	groups_handle_ids_dict = {}

	cur.execute('SELECT * FROM chat_handle_join WHERE chat_id IN (SELECT chat_id FROM chat_handle_join GROUP BY chat_id HAVING COUNT(*)>1)')
	
	for groups in cur.fetchall():
		chat_id = groups[0]
		handle_id = groups[1]
		# Create the array value if the chat_id key is not yet saved in the dictionary
		# Add the email address or phone number the user is using in the group chat
		if not groups_handle_ids_dict.get(chat_id):
			groups_handle_ids_dict[chat_id] = [my_contact_info[chat_id], handle_dict[handle_id]]
		else:
			groups_handle_ids_dict[chat_id].append(handle_dict[handle_id])

	#print(groups_handle_ids_dict)

	#sys.exit(2);

	# Populate the chat_to_handle_dict
	#for pairing in cur.fetchall():
	#	chat_id = pairing[0]
	#	handle_id = pairing[1]
	#	if not chat_to_handle.get(chat_id):
	#		chat_to_handle_dict[pairing[0]] = pairing[1]

	# Initialize general chat info dictionary that maps people or group names to a dictionary with 
	# three keys: isGroup and participants
	general_chat_info = {}

	# Get information from the messages table
	cur.execute('SELECT handle_id, date, text, is_from_me, account, ROWID, cache_roomnames, cache_has_attachments, service, chat_id, share_direction, group_action_type FROM message INNER JOIN chat_message_join ON message.ROWID=chat_message_join.message_id ORDER BY ROWID DESC')

	# Initialize the list that will map the name to the message
	# Example key-value pair: { 'Johnny Appleseed': [{ 'source': 'email', 'time': 16088449385, 
	# 'text': 'Hello'}, { 'source': 188888888, 'time': 16088449387, 'text': 'Hello' }] }
	# Example key-value pair for group chats: { 'group3': [{ 'memberNumbers': ['11111111', '222222',
	# '333333'], { 'source': '1111111', 'time': 187293742837, 'text': 'No way!' } }]}

	text_history = {}
	misc_contact_num = 0

	# Get seconds between January 1, 1970 and January 1, 2001
	date1 = datetime(2001, 1, 1, 0, 0)
	date2 = datetime(1970, 1, 1, 0, 0)
	duration = date1 - date2 

	for message in cur.fetchall():
		handle_id = message[0]
		seconds = message[1]
		time = datetime.utcfromtimestamp(duration.total_seconds() + seconds).strftime('%Y-%m-%d %H:%M:%S')
		text = message[2]
		is_from_me = True if message[3] == 1 else False # necessary?
		my_account = message[4] # never used
		row_id = message[5]
		group_name = message[6]
		has_attachment = True if message[7] == 1 else False # never used
		service = message[8]
		chat_id = message[9]
		share_direction = True if message[10] == 1 else False
		group_action_type = True if message[11] == 1 else False

		# Divide seconds by a million if the current OSx is High Sierra or higher
		if high_sierra_min:
			seconds = seconds / 10 ** 9

		#print(text)

		# Get the source (email or phone number)
		source = handle_dict.get(handle_id)
		#if source:
		#	source = re.sub('^[+]', '', source)

		# Filter out messages that are sent to oneself
		if source in my_addresses:
			is_from_me = True
		
		if share_direction:
			text = "Direction shared"
			group_name = None
		
		# Flag to be used when miscellaneous (unsaved) contacts are added to contact_dict
		misc_contact_created = False

		# Process group chats and individual chats
		# Group chats include an extra name key
		if group_name: 
			try:
				if group_action_type:
					text = "Group created"
				name = groups_dict[group_name]
				#print(group_name, name)
				if not general_chat_info.get(name):
					group_info = {}
					participants_array = groups_handle_ids_dict[chat_id]
					#print(group_name, participants_array)

					# Add unknown contacts to contact_dict
					for participant_num in participants_array:
						if not contact_dict.get(participant_num) and participant_num not in my_addresses:
							misc_contact_num += 1
							misc_contact_created = True
							#print('group loop', participant_num, misc_contact_num)
							#print(message)
							contact_dict[participant_num] = f'contact{misc_contact_num}'
					group_info['isGroup'] = True
					group_info['participants'] = participants_array
					group_info['saved'] = False if misc_contact_created else True
					general_chat_info[name] = group_info
					#print(general_chat_info[name])
			except KeyError:
				#print(f'key error with group_dict: key {group_name} doesn\'t exist')
				continue
		else: 
			name = contact_dict.get(source)
			# Establish miscellaneous contact in the contact_dict
			if not name and not is_from_me:
				misc_contact_num += 1
				#print('individual loop', name, source, misc_contact_num)
				contact_dict[source] = f'contact{misc_contact_num}'
				name = contact_dict[source]
				misc_contact_created = True
				#print(source, name)
			# Add general chat info to the dictionary
			if not general_chat_info.get(name):
				individual_info = {}
				participants_info = [source, my_contact_info[chat_id]]
				individual_info['isGroup'] = False
				individual_info['participants'] = participants_info
				individual_info['saved'] = False if misc_contact_created else True
				general_chat_info[name] = individual_info
			

		#print(message[5], source)
		#print(name, source, time, text)

		if name: 
			info_obj = {}
			if is_from_me:
				source = my_contact_info[chat_id]
				info_obj["isFromMe"] = True
			else: 
				info_obj["isFromMe"] = False
			info_obj["source"] = source
			info_obj["time"] = time
			info_obj["text"] = text
			if attachments.get(row_id):
				info_obj['photofilepath'] = attachments[row_id]['filepath']
				info_obj['text'] = info_obj['text'] + attachments[row_id]['name']
				#print(info_obj)
			#if not text_history.get(name):
			#	text_history[name] = []
				#if group_name: 
				#	contactsObj = { "memberNumbers" : [] }
				#	text_history[name].append(contactsObj)
			#if group_name:
				# Update the first object with the contact information
				#firstObj = text_history[name][0].get("memberNumbers")
				#print(message, text_history, source, firstObj)
				#if firstObj != None:
				#	if source not in firstObj and not is_from_me:
				#		text_history[name][0]["memberNumbers"].append(source)
				
				#member_name = contact_dict.get(source)
				#if not member_name and not is_from_me:
				#	misc_contact_num += 1
				#	contact_dict[source] = f'contact{misc_contact_num}'
				#info_obj['member_name'] = 'me' if is_from_me else contact_dict[source]
				#text_history[name].insert(1, info_obj)
			#else:
			if not text_history.get(name):
				text_history[name] = []
			
			text_history[name].insert(0, info_obj)

	#print(contact_dict.values())
	#for contact in my_addresses:
	#	print(contact)
	#	if contact in contact_dict.keys():
	#		print('BOOM')
	#sys.exit(2)

	#print(general_chat_info)
	#sys.exit(10)

	# Get current working directory
	cwd = os.getcwd()
	count = 0
	name = ""

	for key in text_history:
		#print(key, text_history[key], '\n')
		#count += 1
		#if count > 10:
		#	sys.exit(3)
		#else:
		#	continue
		name = key.replace(" ", "_")

		# Create folder  
		dst_dir = cwd + "/messages/" 
		os.makedirs(dst_dir, exist_ok=True)

		# Create sub-folders
		if general_chat_info[key]["isGroup"]:
			dst_dir = dst_dir + "groups/"
			os.makedirs(dst_dir, exist_ok=True)
		else:
			dst_dir = dst_dir + "individuals/"
			os.makedirs(dst_dir, exist_ok=True)
		
		if general_chat_info[key]["saved"]:
			dst_dir = dst_dir + "saved/"
			os.makedirs(dst_dir, exist_ok=True)
		else:
			dst_dir = dst_dir + "unsaved/"
			os.makedirs(dst_dir, exist_ok=True)

		dst_dir = dst_dir + name + "/"
		os.makedirs(dst_dir, exist_ok=True)

		#if text_history[key][0].get("memberNumbers"):
		#if group_num:
		#	dst_dir = dst_dir + "groups/"
		#	os.makedirs(dst_dir, exist_ok=True)

			#all_numbers_stored = True

			#for group_member_number in text_history[key][0].get("memberNumbers"):
			#	if not contact_dict.get(group_member_number):
			#		all_numbers_stored = False
			#		break
			#if not all_numbers_stored:
			#	dst_dir = dst_dir + "not_saved/" + name + "/"
			#else:
			#	dst_dir = dst_dir + "saved/" + name + "/"
		#	dst_dir = dst_dir + name + "/"
		#else: 
		#	dst_dir = dst_dir + "individuals/"
		#	os.makedirs(dst_dir, exist_ok=True)

		#	if 'contact' in key:
		#		dst_dir = dst_dir + "not_saved/" + name + "/"
		#	else:
		#		dst_dir = dst_dir + "saved/" + name + "/"

		#os.makedirs(dst_dir, exist_ok=True)

		# Create path for .txt file and start writing the file 
		textfile = dst_dir + name + ".txt"
		f = open(textfile, 'a')
		#print(f'{text_dict["source"]} @ {text_dict["time"]}]:{text_dict["text"]}\n')

		img_dir = dst_dir + "images/"

		participants_str = "Participants:\n"

		for contact in general_chat_info[key]["participants"]:
			if contact_dict.get(contact):
				participants_str = participants_str + f"{contact} ({contact_dict[contact]})\n"
				#if contact_dict.get(contact):
				#	participants_str = participants_str + f"({contact_dict[contact]})" 
			else:
				#print(contact)
				participants_str = participants_str + f"{contact}\n"
		
		participants_str = participants_str + "\n"	

		if general_chat_info[key]["isGroup"]:
			f.write(f'GROUP CHAT\n{participants_str}')
		else:
			f.write(f'INDIVIDUAL CHAT\n{participants_str}')

		#is_group = hasattr(text_history[key][0], "memberNumbers")
		#print(is_group)

		for text_dict in text_history[key]:
			# Get image information
			if text_dict.get('photofilepath'):
				if SAVE_IMAGE_FILES:
					os.makedirs(img_dir, exist_ok=True)
					imgFile = os.path.join(os.path.expanduser(text_dict['photofilepath']))
					#print(imgFile)
					shutil.copy(imgFile, dst_dir)
				else:
					img_file = dst_dir + name + "_images" + ".txt"
					f2 = open(img_file, 'a')
					f2.write(f'[{text_dict["source"]} @ {text_dict["time"]}]: {text_dict["photofilepath"]}\n')
				
			if contact_dict.get(text_dict["source"]):
				f.write(f'[{text_dict["source"]} ({contact_dict[text_dict["source"]]}) @ {text_dict["time"]}]: {text_dict["text"]}\n')
			else:
				if text_dict["isFromMe"]:
					f.write(f'[{text_dict["source"]} (self) @ {text_dict["time"]}]: {text_dict["text"]}\n')
				elif not text_dict["source"]:
					f.write(f'[{text_dict["time"]}]: {text_dict["text"]}\n')
				else:
					f.write(f'[{text_dict["source"]} (??) @ {text_dict["time"]}]: {text_dict["text"]}\n')
				
			
			#print(text_dict)

			#if is_group:
			#	if text_dict.get("memberNumbers"):	
			#		group_members_string = 'Group members:\n'
			#		if text_dict["memberNumbers"] != None:
			#			for number in text_dict["memberNumbers"]:
			#				group_members_string += f"{number} ({contact_dict[number]})\n"

			#		f.write(group_members_string + "\n")
			#	else:
			#		f.write(f'[{text_dict["source"]} ({text_dict["memberName"]}) @ {text_dict["time"]}]: {text_dict["text"]}\n')
			#else:
			#	try: 
					
			#	except KeyError:
			#		print(textHistory[key][1], text_dict)


	# Stop the timer
	end_time = datetime.now()

	# Calculate the overall time of execution
	time_diff = end_time - start_time
	total_seconds = time_diff.total_seconds()
	program_run_seconds = math.trunc(total_seconds)
	program_run_milliseconds = math.trunc((total_seconds - program_run_seconds) * 1000)

	print(f"Program run time: {time_diff} seconds")
	print(f"Program run time: {program_run_seconds} seconds and {program_run_milliseconds} milliseconds")