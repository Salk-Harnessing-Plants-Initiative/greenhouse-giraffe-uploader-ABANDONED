import json
import boxsdk as box
from aws_s3_desktop_uploader import desktop_uploader

with open('config.json') as f:
	config = json.load(f)
	oauth = box.OAuth2(
		client_id=config['client_id'],
		client_secret=config['client_secret'],
		access_token=config['access_token'] # developer token
	)
	client = box.Client(oauth)
	root_folder = client.folder(folder_id='0')
	shared_folder = root_folder.create_subfolder('hello_world')
	uploaded_file = shared_folder.upload('test/iguana.jpg')

if __name__ == "__main__":
	print("Hi")
	print(desktop_uploader.get_file_created("test/iguana.jpg"))




# Attempt to get QR code from image

	# If so, query from database the Box folder id for this experiment

# Get file creation date

# Get subfolder id for file creation date, creating it if necessary

# Uplaod to subfolder

# Move to done 