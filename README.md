# iMessage Extractor

This iMessage Extractor was created as the final project for CS50x Introduction to Computer Science. It builds on Python and SQL skills taught in [Week 6](https://cs50.harvard.edu/x/2023/weeks/6/) and [Week 7](https://cs50.harvard.edu/x/2023/weeks/7/) of the course. This application is a command-line tool that can be run with the command `python imessage_extractor.py`. It works in tandem with `sqlite3` and `dotenv` to extract every conversation stored on a Macbook Pro.

To use the file, a .env file must be created containing the paths of the database used for the Apple Contacts application. These environment variables are to be named `CONTACT_DB` and `CHAT_DB`. Here's a sample of what that .env file may look like:
```
export CONTACT_DB="/Users/userName/Library/Application Support/AddressBook/Sources/872138947528352384907502735/AddressBook-v22.abcddb"
export CHAT_DB="/Users/userName/Library/Messages/chat.db"
```

The program can also be run if a `contacts.vcf` file is saved in the same folder as the principal python file. This can be created by opening the Apple Contacts application, selecting all the contacts (ctl + A), and navigating to File > Export > Export vCard... The .abcddb file may not be completely up to date on your MacBook, so exporting a vCard file may be a better strategy.

There are 3 settings that can be modified by flipping 1 of 3 flag values from `True` to `False` or vice-versa. They are: `USE_VCF`, `SAVE_IMAGE_FILES`, and `PRIVACY_MODE`.

By default, the program will process the `contacts.vcf` file before using the `CHAT_DB` flag stored as an environment variable. This can be changed by switching the flag `USE_VCF` found at the top of the `imessage_extractor.py` file to `True`. 

If the user is concerned about the image files taking up space, there is the option to create a .txt file called `images.txt` that will store all the filepaths (somewhere in your MacBook Pro's Library folder) and the date/times they were sent and the source. If the `SAVE_IMAGE_FILES` flag at the top of the `imessage_extractor.py` file is `True`, the images will save to an `images` folder within the folder of assigned to each person or group.  

If the user would like to keep the contents of each text message more private, there is a `PRIVACY_MODE` flag that can be turned on and off. When `True`, contacts will be stored in the contact dict as if they were unsaved, e.g. contact1, contact2, etc. Then, in the .txt files, phone numbers and emails will be hidden, e.g. \*\*\*\*@gmail.com or 1847\*\*\*\*\*\*\*. The messages will all be encrypted usin Caesar's cipher, a simple encryption method introduced in [Week 2 of CS50x](https://cs50.harvard.edu/x/2023/psets/2/caesar/). 

The run-time of the program is printed out once the program finishes populating a messages folder. 

Various websites and discussions were referred to for this project: [a Medium article showing how the chat database is structured for MacBooks](https://medium.com/@yaskalidis/heres-how-you-can-access-your-entire-imessage-history-on-your-mac-f8878276c6e9), [a StackOverflow discussion post showing how to use regular expressions to parse vCard files](https://stackoverflow.com/questions/54551712/reading-vcf-file-data-using-python-and-re-library), and a [StackOverflow discussion post showing how to strip non-ASCII characters from a string](https://stackoverflow.com/questions/123336/how-can-you-strip-non-ascii-characters-from-a-string-in-c).  