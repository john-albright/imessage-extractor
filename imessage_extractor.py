import sqlite3
import re
import datetime
import sys
import glob
import os
import shutil
from datetime import datetime

# vcf help: https://stackoverflow.com/questions/54551712/reading-vcf-file-data-using-python-and-re-library
# iMessage db help: https://medium.com/@yaskalidis/heres-how-you-can-access-your-entire-imessage-history-on-your-mac-f8878276c6e9
# strip non-ASCII characters: https://stackoverflow.com/questions/123336/how-can-you-strip-non-ascii-characters-from-a-string-in-c


def convertEpochBfHighSierra(time):
	return 

if __name__ == '__main__':
	# Connect to the database
	db = sqlite3.connect('/Users/John/Library/Messages/chat.db')

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

	# Open vCard file 
	vcfFile = open('contacts.vcf', 'r')

	name = ''
	email = ''
	telephone = ''
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
			telephone = re.sub('[^\u0000-\u007F]+', '', telephone)
			telephone = re.sub('[^\d]*', '', telephone)
		if re.search('END:VCARD.*', line):
			name = ''
		
		if name:
			if email:
				contactDict[email] = name
				email = ''
			if telephone:
				contactDict[telephone] = name
				telephone = ''
		
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

	# Initialize the dictionary that will map chat ids to image file paths
	# Example key-value pair: { '621': { 'filepath': '~\Library\IMG_6542.jpg', 'name': 'IMG_652.jpg' }}
	attachments = {}

	cur.execute('SELECT message_attachment_join.message_id, filename, transfer_name FROM attachment INNER JOIN message_attachment_join on attachment.ROWID=message_attachment_join.attachment_id')

	for attachment in cur.fetchall():
		#filepath = re.sub('^~', '/Users/John', attachment[1])
		filepath = attachment[1]
		#print(attachment[1])
		attachments[attachment[0]] = {'filepath': filepath, 'name': attachment[2]}

	#print(attachments)
	#sys.exit(0)

	# Get information from the messages table
	cur.execute('SELECT handle_id, date, text, is_from_me, account, ROWID, cache_roomnames, cache_has_attachments, service FROM message ORDER BY ROWID DESC LIMIT 1000')

	# Initialize the list that will map the name to the message
	# Example key-value pair: { 'Johnny Appleseed': [{ 'source': 'email', 'time': 16088449385, 
	# 'text': 'Hello'}, { 'source': 188888888, 'time': 16088449387, 'text': 'Hello' }] }
	textHistory = {}
	miscContactNum = 0

	# Get seconds between January 1, 1970 and January 1, 2001
	date1 = datetime(2001, 1, 1, 0, 0)
	date2 = datetime(1970, 1, 1, 0, 0)
	duration = date1 - date2 

	for message in cur.fetchall():
		handleId = message[0]
		#time = datetime(str(message[1]) + datetime.strftime("%s", "2001-01-01") , "unixepoch", "localtime")
		time = datetime.utcfromtimestamp(duration.total_seconds() + message[1]).strftime('%Y-%m-%d %H:%M:%S')
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
			if not textHistory.get(name):
				textHistory[name] = []
			if groupNum:
				memberName = contactDict.get(source)
				if not memberName:
					miscContactNum += 1
					contactDict[source] = f'contact{miscContactNum}'
				infoObj['memberName'] = 'me' if isFromMe else contactDict[source]
			
			textHistory[name].insert(0, infoObj)

	# Get current working directory
	cwd = os.getcwd()

	for key in textHistory:
		#print(key, textHistory[key], '\n')
		name = key.replace(" ", "_")

		# Create folder 
		dstDir = cwd + "/messages/" + name + "/"
		os.makedirs(dstDir, exist_ok=True)

		# Create path for .txt file and start writing the file 
		textfile = dstDir + name + ".txt"
		f = open(textfile, 'w')
		#print(f'{textDict["source"]} @ {textDict["time"]}]:{textDict["text"]}\n')

		for textDict in textHistory[key]:
			# Get image information
			if textDict.get('photofilepath'):
				imgFile = os.path.join(os.path.expanduser(textDict['photofilepath']))
				#print(imgFile)
				shutil.copy(imgFile, dstDir)
			#print(textDict)

			if textDict

			f.write(f'[{textDict["source"]} @ {textDict["time"]}]: {textDict["text"]}\n')
			
