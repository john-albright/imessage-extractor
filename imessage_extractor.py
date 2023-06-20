import sqlite3
import re
import datetime
import sys
import glob
import os
import shutil
import platform
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
	handleDict = {}

	# Get the ROWID and id from the handle table
	cur.execute('SELECT ROWID, id FROM handle')

	# Populate handleDict
	for row in cur.fetchall():
		handleDict[row[0]] = row[1]
	
	#print(handleDict)

	# Initialize the dictionary that will map contact information to names
	# Example key-value pair: { 'poodle@gmail123.com': 'Favorite Poodle' }
	contactDict = {}

	# Initialize strings to be emptied and refilled if using a vcf file
	# Otherwise initialize strings to be filled when searching the Apple .db file
	name = ''
	email = ''
	telephone = ''

	# Declare regex strings to be used for filtering phone numbers 
	removeUnicodeReg = '[^\u0000-\u007F]+'
	removeNondigitsReg = '[^\d]*'

	if USE_VCF:
		# Open vCard file 
		try:
			vcfFile = open('contacts.vcf', 'r')
		except FileNotFoundError:
			print('No file \'contacts.vcf\' found in the parent directory.')
			sys.exit(0)

		nameReg = 'FN:(.*)'
		emailReg = 'EMAIL.*:(.*)'
		telReg = 'TEL.*:(.*)'

		for line in vcfFile:
			if re.search(nameReg, line):
				name = re.findall(nameReg, line)[0]
			if re.search(emailReg, line):
				email = re.findall(emailReg, line)[0]
			if re.search(telReg, line):
				telephone = re.findall(telReg, line, re.MULTILINE)[0]
				telephone = re.sub(removeUnicodeReg, '', telephone)
				telephone = re.sub(removeNondigitsReg, '', telephone)
			if re.search('END:VCARD.*', line):
				name = ''
			
			if name:
				if email:
					contactDict[email] = name
					email = ''
				if telephone:
					contactDict[telephone] = name
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
			telephone = re.sub(removeUnicodeReg, '', telephone)
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
			contactDict[telephone] = name
			contactDict[email] = name

			# Reset all variables
			name = ''
			telephone = ''
			email = ''

	#print(contactDict)

	# Initialize the dictionary that will map cache roomnames to group names
	# Example key-value pair: { 'chat797599165314668063' : 'group77' }
	groupsDict = {}

	cur.execute('SELECT room_name, display_name FROM chat WHERE room_name IS NOT NULL')

	miscGroupNum = 0

	for chat in cur.fetchall():
		if chat[0]:
			if chat[1]:
				groupsDict[chat[0]] = chat[1]
			else:
				miscGroupNum += 1
				groupsDict[chat[0]] = f'group{miscGroupNum}'

	#print(groupsDict)

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

	# Get information from the messages table
	cur.execute('SELECT handle_id, date, text, is_from_me, account, ROWID, cache_roomnames, cache_has_attachments, service FROM message ORDER BY ROWID DESC')

	# Initialize the list that will map the name to the message
	# Example key-value pair: { 'Johnny Appleseed': [{ 'source': 'email', 'time': 16088449385, 
	# 'text': 'Hello'}, { 'source': 188888888, 'time': 16088449387, 'text': 'Hello' }] }
	# Example key-value pair for group chats: { 'group3': [{ 'memberNumbers': ['11111111', '222222',
	# '333333'], { 'source': '1111111', 'time': 187293742837, 'text': 'No way!' } }]}
	#

	textHistory = {}
	miscContactNum = 0

	# Get seconds between January 1, 1970 and January 1, 2001
	date1 = datetime(2001, 1, 1, 0, 0)
	date2 = datetime(1970, 1, 1, 0, 0)
	duration = date1 - date2 

	for message in cur.fetchall():
		handleId = message[0]
		#time = datetime(str(message[1]) + datetime.strftime("%s", "2001-01-01") , "unixepoch", "localtime")
		seconds = message[1]
		
		# Divide seconds by a million if the current OSx is High Sierra or higher
		if high_sierra_min:
			seconds = seconds / 10 ** 9
		
		time = datetime.utcfromtimestamp(duration.total_seconds() + seconds).strftime('%Y-%m-%d %H:%M:%S')
		text = message[2]
		isFromMe = True if message[3] == 1 else False
		myAccount = message[4]
		rowId = message[5]
		groupNum = message[6]
		hasAttachment = True if message[7] == 1 else False
		service = message[8]

		#print(text)

		# Get the source (email or phone number)
		source = handleDict.get(handleId)
		if source:
			source = re.sub('^[+]', '', source)

		# Process group chats and individual chats
		# Group chats include an extra name key
		if groupNum: 
			try:
				name = groupsDict[groupNum]
			except KeyError:
				continue
		else: 
			name = contactDict.get(source)

			# Establish miscellaneous contact in the contactDict
			if not name:
				miscContactNum += 1
				contactDict[source] = f'contact{miscContactNum}'
				name = contactDict[source]
			
		#print(message[5], source)
		#print(name, source, time, text)

		if isFromMe:
			source = 'phone' if service == 'SMS' else 'email'

		if name: 
			infoObj = { 'source': source, 'time': time, 'text': text }
			if attachments.get(rowId):
				infoObj['photofilepath'] = attachments[rowId]['filepath']
				infoObj['text'] = infoObj['text'] + attachments[rowId]['name']
				#print(infoObj)
			#if not textHistory.get(name):
			#	textHistory[name] = []
				#if groupNum: 
				#	contactsObj = { "memberNumbers" : [] }
				#	textHistory[name].append(contactsObj)
			if groupNum:
				# Update the first object with the contact information
				#firstObj = textHistory[name][0].get("memberNumbers")
				#print(message, textHistory, source, firstObj)
				#if firstObj != None:
				#	if source not in firstObj and not isFromMe:
				#		textHistory[name][0]["memberNumbers"].append(source)
				
				memberName = contactDict.get(source)
				if not memberName:
					miscContactNum += 1
					contactDict[source] = f'contact{miscContactNum}'
				infoObj['memberName'] = 'me' if isFromMe else contactDict[source]
				#textHistory[name].insert(1, infoObj)
			#else:
			if not textHistory.get(name):
				textHistory[name] = []
			
			textHistory[name].insert(0, infoObj)

	# Get current working directory
	cwd = os.getcwd()
	count = 0

	for key in textHistory:
		#print(key, textHistory[key], '\n')
		#count += 1
		#if count > 10:
		#	sys.exit(3)
		#else:
		#	continue
		name = key.replace(" ", "_")

		# Create folder  
		dstDir = cwd + "/messages/" + name + "/"
		os.makedirs(dstDir, exist_ok=True)

		# Create sub-folders
		#if textHistory[key][0].get("memberNumbers"):
		#if groupNum:
		#	dstDir = dstDir + "groups/"
		#	os.makedirs(dstDir, exist_ok=True)

			#all_numbers_stored = True

			#for group_member_number in textHistory[key][0].get("memberNumbers"):
			#	if not contactDict.get(group_member_number):
			#		all_numbers_stored = False
			#		break
			#if not all_numbers_stored:
			#	dstDir = dstDir + "not_saved/" + name + "/"
			#else:
			#	dstDir = dstDir + "saved/" + name + "/"
		#	dstDir = dstDir + name + "/"
		#else: 
		#	dstDir = dstDir + "individuals/"
		#	os.makedirs(dstDir, exist_ok=True)

		#	if 'contact' in key:
		#		dstDir = dstDir + "not_saved/" + name + "/"
		#	else:
		#		dstDir = dstDir + "saved/" + name + "/"

		#os.makedirs(dstDir, exist_ok=True)

		# Create path for .txt file and start writing the file 
		textfile = dstDir + name + ".txt"
		f = open(textfile, 'w')
		#print(f'{textDict["source"]} @ {textDict["time"]}]:{textDict["text"]}\n')

		imgDir = dstDir + "images/"
				
		if textHistory.get("memberName"):
			f.write(f'GROUP CHAT\n')

		#is_group = hasattr(textHistory[key][0], "memberNumbers")
		#print(is_group)

		for textDict in textHistory[key]:
			# Get image information
			if textDict.get('photofilepath'):
				if SAVE_IMAGE_FILES:
					os.makedirs(imgDir, exist_ok=True)
					imgFile = os.path.join(os.path.expanduser(textDict['photofilepath']))
					#print(imgFile)
					shutil.copy(imgFile, dstDir)
				else:
					img_file = dstDir + name + "_images" + ".txt"
					f2 = open(img_file, 'w+')
					f2.write(f'[{textDict["source"]} @ {textDict["time"]}]: {textDict["photofilepath"]}\n')
					
			
			#print(textDict)

			#if is_group:
			#	if textDict.get("memberNumbers"):	
			#		group_members_string = 'Group members:\n'
			#		if textDict["memberNumbers"] != None:
			#			for number in textDict["memberNumbers"]:
			#				group_members_string += f"{number} ({contactDict[number]})\n"

			#		f.write(group_members_string + "\n")
			#	else:
			#		f.write(f'[{textDict["source"]} ({textDict["memberName"]}) @ {textDict["time"]}]: {textDict["text"]}\n')
			#else:
			#	try: 
					f.write(f'[{textDict["source"]} @ {textDict["time"]}]: {textDict["text"]}\n')
			#	except KeyError:
			#		print(textHistory[key][1], textDict)


			
	end_time = datetime.now()
	time_diff = end_time - start_time
	program_run_seconds = time_diff.total_seconds()
	program_run_milliseconds = program_run_seconds / 60

	print(f"Program run time: {program_run_seconds} seconds and {program_run_milliseconds} milliseconds")
