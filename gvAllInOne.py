import csv
import getpass
import os
import re
import sys
import urllib
import urllib2
import time

class GoogleVoiceLogin:
	""" 
	Class that attempts to log in the Google Voice 	using the provided 
	credentials. 
	
	If either no password or email is provided, the user will be 
	prompted for them.
	
	Once instantiated, you can check to see the status of the log in 
	request by accessing the "logged_in" attribute
	
	The primary usage of a GoogleVoiceLogin object is to be passed
	in to other constructors, such as the TextSender, or NumberDialer
	"""

	def __init__(self, email = None, password = None):
		"""
		Given the email and password values, this method will attempt to log
		in to Google Voice. The "response" attribute can be checked to 
		see if the login was a success or not.
		 
		If the login was successful, the "opener" and "key" attributes will
		be available to use when creating other objects. 
		
		To use an this object with the other classes in this module, simply
		pass it in to the constructor. (ie text_sender = TextSender(gv_login))
		"""

		if email is None:
			email = raw_input("Please enter your Google Account username: ")
		if password is None:
			import getpass
			password = getpass.getpass("Please enter your Google Account password: ")

		# Set up our opener
		self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
		urllib2.install_opener(self.opener)

		# Define URLs
		self.login_page_url = 'https://accounts.google.com/ServiceLogin?service=grandcentral'
		self.authenticate_url = 'https://accounts.google.com/ServiceLoginAuth?service=grandcentral'
		self.gv_home_page_url = 'https://www.google.com/voice/#inbox'
		self.contacts_url = 'https://www.google.com/voice/c/u/{0}/ui/ContactManager'
		
		# Load sign in page
		login_page_contents = self.opener.open(self.login_page_url).read()

		# Find GALX value
		galx_match_obj = re.search(r'name="GALX"\s*value="([^"]+)"', login_page_contents, re.IGNORECASE)

		galx_value = galx_match_obj.group(1) if galx_match_obj.group(1) is not None else ''

		# Set up login credentials
		login_params = urllib.urlencode({
			'Email' : email,
			'Passwd' : password,
			'continue' : 'https://www.google.com/voice/account/signin',
			'GALX': galx_value
		})

		# Login
		self.opener.open(self.authenticate_url, login_params)

		# Open GV home page
		gv_home_page_contents = self.opener.open(self.gv_home_page_url).read()

		# Fine _rnr_se value
		key = re.search('name="_rnr_se".*?value="(.*?)"', gv_home_page_contents)

		if not key:
			self.logged_in = False
		else:
			self.logged_in = True
			self.key = key.group(1)
			
			username = email.split('@')[0]
			contacts_content = self.opener.open(self.contacts_url.format(username)).read()
			tok_match_obj = re.search(r"var\s+tok\s*=\s*'([^']+)'", contacts_content, re.IGNORECASE)
			
			self.contact_tok = tok_match_obj.group(1) if tok_match_obj.group(1) is not None else ''

class ContactLoader():
	""" 
	This class is used to download and organize a csv file 
	of Google Contacts.It is often used in conjunction with 
	the ContactSelector class.
	
	Example:
	
	contact_loader = ContactLoader(gv_login)
	contact_selector = ContactSelector(contact_loader)
	"""
	def __init__(self, gv_login):
		""" 
		Pass in a GoogleVoiceLogin object, and the persons Google Contacts
		Will be downloaded and organized into a structure called 
		"contacts_by_group_list"
		which is organized in form:
		
		[(1, ('group_name', [contact_list])), (2, ('group_name', [contact_list]))]
		
		Which allows for easy access to any group. 
		"""
		self.opener = gv_login.opener
		self.contacts_csv_url = "https://mail.google.com/mail/c/u/0/data/export"
		self.contacts_csv_url += "?groupToExport=^Mine&exportType=ALL&out=OUTLOOK_CSV&tok={0}".format(gv_login.contact_tok)

		# Load ALL Google Contacts into csv dictionary
		self.contacts = csv.DictReader(self.opener.open(self.contacts_csv_url))

		# Create dictionary to store contacts and groups in an easier format
		self.contact_group = {}
		# Assigned each person to a group that we can get at later
		for row in self.contacts:
			if row['First Name'] != '':
				for category in row['Categories'].split(';'):
					if category == '':
						category = 'Ungrouped'
					if category not in self.contact_group:
						self.contact_group[category] = [Contact(row)]
					else:
						self.contact_group[category].append(Contact(row))

		# Load contacts into a list of tuples... 
		# [(1, ('group_name', [contact_list])), (2, ('group_name', [contact_list]))]
		self.contacts_by_group_list = [(id + 1, group_contact_item)
									   for id, group_contact_item in enumerate(self.contact_group.items())]

class Contact():
	""" 
	Simple class to contain information on each Google Contact person.
	
	Only stores information on:
	First Name
	Last Name
	Mobile Number
	Email address
	"""
	def __init__(self, contact_detail):
		""" 
		Extract data from the given contact_detail
		
		The following attributes are available:
		
		first_name
		last_name
		mobile
		email
		"""
		self.first_name = contact_detail['First Name'].strip()
		self.last_name = contact_detail['Last Name'].strip()
		self.mobile = contact_detail['Mobile Phone'].strip()
		self.email = contact_detail['E-mail Address'].strip()

	def __str__(self):
		return self.first_name + ' ' + self.last_name

# Class to assist in selected contacts by groups 
class ContactSelector():
    """
    Class with helps select contacts after using the ContactLoader
    object to download them.
    
    Provides methods to:
    1) Display the list of groups (get_group_list())
    2) Set the selected group to work with (set_selected_group(group_id))
    3) Get the contacts from the working list (get_contacts_list())
    4) Remove names from the working list(remove_from_contact_list(contacts_to_remove_list))
    """
    def __init__(self, contact_loader):
        """
        Initialize the object - a ContactLoader object is expected here
        """
        self.contacts_by_group_list = contact_loader.contacts_by_group_list
        self.contact_list = None

    def get_group_list(self):
        """
        Extract a list of all the groups. 
        List is in the form:
        [(1, 'Group Name'), (2, 'Groups Name'), ...]
        """
        return [(item[0], item[1][0]) for item in self.contacts_by_group_list]

    def set_selected_group(self, group_id):
        """
        Select the group to work with. 

        This method will make the working contact_list contain all the
        contacts from the selected group. 
        """
        self.contact_list = self.contacts_by_group_list[group_id - 1][1][1]

	# Return the contact list so far
    def get_contacts_list(self):
        """
        Return a list of all the contacts, and assign them each a number

        List is in the form:
        [(1, Contact), (2, Contact), ...]
        """
        return [(id + 1, contact) for id, contact in enumerate(self.contact_list)]

    def remove_from_contact_list(self, contacts_to_remove_list):
        """
         Accepts a one based list of ids, indicating which contacts
         to remove from the list.
         
         List needs to be a list in ints:
         [3, 6, 7]
        """
        if self.contact_list is None:
            return
        for id in contacts_to_remove_list:
            if id in range(0, len(self.contact_list) + 1):
                self.contact_list[id - 1] = None
        self.contact_list = [contact for contact in self.contact_list if contact is not None]

class NumberRetriever():
    """
    Class that will allow you to retrieve all stored phone numbers and their aliases
    """

    def __init__(self, gv_login):
        """
        Pass in the GoogleVoiceLogin object, this class will then
        download all the numbers and aliases of the persons GV Account
        """
        self.opener = gv_login.opener
        self.phone_numbers_url = 'https://www.google.com/voice/settings/tab/phones'
        phone_numbers_page_content = self.opener.open(self.phone_numbers_url).read()

		# Build list of all numbers and their aliases
        self.phone_number_items = [(match.group(1), match.group(2))
                                   for match
                                   in re.finditer('"name":"([^"]+)","phoneNumber":"([^"]+)"',
                                                            phone_numbers_page_content)]

    def get_phone_numbers(self):
        """
        Return the list of phone numbers in the form:
        [(1, number), (2, number)...]
        """
        return [(id + 1, (phone_number_item))
                for id, phone_number_item
                in enumerate(self.phone_number_items)]

class TextSender():
    """
    Class used to send text messages.
    
    Example usage:
    
    gv_login = GoogleVoiceLogin('username', 'password')
    text_sender = TextSender(gv_login)
    text_sender.text = "This is an example"
    text_sender.send_text('555-555-5555')
    
    if text_sender.response:
        print "Success!"
     else:
        print "Fail!"
    """
    def __init__(self, gv_login):
        """ 
        Pass in a GoogleVoiceLogin object, set the text message 
        and then call send_text
        """
        self.opener = gv_login.opener
        self.key = gv_login.key
        self.sms_url = 'https://www.google.com/voice/sms/send/'
        self.text = ''

    def send_text(self, phone_number):
        """
        Sends a text message containing self.text to phone_number
        """
        sms_params = urllib.urlencode({
            '_rnr_se': self.key,
            'phoneNumber': phone_number,
            'text': self.text
        })
        # Send the text, display status message  
        self.response = "true" in self.opener.open(self.sms_url, sms_params).read()

class NumberDialer():
    """ 
    Class used to make phone calls.

    Example usage:

    gv_login = GoogleVoiceLogin('username', 'password')
    number_dialer = NumberDialer(gv_login)
    number_dialer.forwarding_number = 'number-to-call-you-at'

    number_dialer.place_call('number-to-call')

    if number_dialer.response:
        print "Success!"
     else:
        print "Fail!"
    """
    def __init__(self, gv_login):
        self.opener = gv_login.opener
        self.key = gv_login.key
        self.call_url = 'https://www.google.com/voice/call/connect/'
        self.forwarding_number = None

    def place_call(self, number):
        """ 
        Pass in a GoogleVoiceLogin object, set the forwarding_number
        and then call place_call('number-to-call')
        """
        call_params = urllib.urlencode({
            'outgoingNumber' : number,
            'forwardingNumber' : self.forwarding_number,
            'subscriberNumber' : 'undefined',
            'remember' : '0',
            '_rnr_se': self.key
        })

        # Send the text, display status message  
        self.response = self.opener.open(self.call_url, call_params).read()

##############################################################################
##############################################################################
##############################################################################

# Function used to create a separator
def separator():
	return '-' * 25

def get_numeric_input(prompt):
	try:
		return int(raw_input(prompt))
	except:
		pass

# Function to clear the screen 
def clear_screen():
	if os.name == "posix":
		# *nix systems
		os.system('clear')
	elif os.name in ("nt", "dos", "ce"):
		# Windows
		os.system('CLS')

# Main method to be run		
def main():
	# Log in
	gv_login = GoogleVoiceLogin()
	if not gv_login.logged_in:
		print "Could not log in with provided credentials"
		sys.exit(1)
	else:
		print "Login successful!"

	# Use the ContactLoader to download Google Contacts		
	contact_loader = ContactLoader(gv_login)

	# Use the ContactSelector to select the group and 
	# final list of contacts to contact
	contact_selector = ContactSelector(contact_loader)

	clear_screen()
	group_list = contact_selector.get_group_list()
	selected_group = None
	while selected_group not in range(1, len(group_list) + 1):
		print "Your Google Groups"
		print separator()
		for group_item in group_list:
			print "{0}: {1}".format(group_item[0], group_item[1])
		print separator()
		selected_group = get_numeric_input("Enter the index of the group to select: ")

	clear_screen()
	# Now that a group is selected, narrow down the list of people in the group
	contact_selector.set_selected_group(selected_group)
	removing = True
	while removing:
		print "Contact List"
		print separator()
		for contact_item in contact_selector.get_contacts_list():
			print "{0}: {1}".format(contact_item[0], contact_item[1])
		print separator()
		try:
			input_list = raw_input("Enter a list of the indexes (coma, space or otherwise delimeted)\nof those contacts you do not wish to contact this session.\nPress enter when finished:  ")
			if input_list != '':
				contacts_to_remove_list = [int(match.group(1)) for match in re.finditer(r"(\d+)", input_list)]
				contact_selector.remove_from_contact_list(contacts_to_remove_list)
			else:
				removing = False
		except:
			pass

	clear_screen()
	# Print final list
	clear_screen()
	print "Final List:"
	print separator()
	for contact_item in contact_selector.get_contacts_list():
		print "{0}".format(contact_item[1])
	selected_option = None
	while selected_option not in [1, 2]:
		print separator()
		print "Options: "
		print "1: Send Text"
		print "2: Call"
		print separator()
		selected_option = get_numeric_input("Select which action to take: ")

	# Send texts to all people in contact list	
	if (selected_option == 1):
		print separator()
		text_sender = TextSender(gv_login)
		text = raw_input("Enter text message. Press enter when finished: ")
		text_sender.text = text
		for contact in contact_selector.get_contacts_list():
			number = contact[1].mobile
			if number == '':
				print "{0} does not have a mobile number".format(contact[1])
			else:
				print "Sending message to {0} at {1}...".format(contact[1], contact[1].mobile),
				text_sender.send_text(contact[1].mobile)
				if text_sender.response:
					print "Success!"
				else:
					print "Failed!!"
			print "Waiting 5 seconds to send next..."
			time.sleep(5)

	# Call all people in contact list					
	elif (selected_option == 2):
		print separator()
		number_dialer = NumberDialer(gv_login)

		number_retriever = NumberRetriever(gv_login)
		phone_number_items = number_retriever.get_phone_numbers()

		clear_screen()
		# Get the forwarding number
		forwarding_number_input = None
		while forwarding_number_input not in range(1, len(phone_number_items) + 2):
			print "Select forwarding number"
			print separator()
			for phone_number_item in phone_number_items:
				print "{0}: {1}".format(phone_number_item[0], phone_number_item[1][0])
			print "{0}: {1}".format(len(phone_number_items) + 1, "Other")
			print separator()
			forwarding_number_input = get_numeric_input("Choose from your previously entered numbers, or select  \"Other\": ")

		if forwarding_number_input in range(1, len(phone_number_items) + 1):
			forwarding_number = phone_number_items[forwarding_number_input - 1][1]
		else:
			forwarding_number = ''
			while not re.match(r"\(?\b[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}\b\Z", forwarding_number):
				forwarding_number = raw_input("Enter the forwarding number to dial: ")
		number_dialer.forwarding_number = forwarding_number

		print separator()
		# Loop through and make the calls
		for contact in contact_selector.get_contacts_list():
			number = contact[1].mobile
			if number == '':
				print "{0} does not have a mobile number".format(contact[1])
			else:
				input = None
				while input not in ['', 'n', 'N', 'q', 'Q'] :
					input = raw_input("Press enter to call {0} at {1} ('n' to skip, 'q' to quit): ".format(contact[1], contact[1].mobile))
				if input == '':
					print "Calling {0}....".format(contact[1]),
					number_dialer.place_call(number)
					if number_dialer.response:
						print "Success!"
					else:
						print "Failed!!"
				elif input .upper() == 'N':
					pass
				elif input.upper() == 'Q':
					print "Call chain aborted."
					break

if __name__ == "__main__":
	main()
