from gvoice import *
import getpass
import sys
import re
import os

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
			input_list = raw_input("Enter a list of the indexes (coma, space or otherwise delimeted)\nof those contacts you DO NOT wish to contact this session.\nPress enter when finished:  ")
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
				print "{0}: {1}".format(phone_number_item[0], phone_number_item[1][1])
			print separator()
			forwarding_number_input = get_numeric_input("Choose from your numbers: ")

		if forwarding_number_input in range(1, len(phone_number_items) + 1):
			forwarding_number = phone_number_items[forwarding_number_input - 1][1]
		
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
