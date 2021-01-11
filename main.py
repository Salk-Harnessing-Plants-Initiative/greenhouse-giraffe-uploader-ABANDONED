import os
import time
import threading
import json
import boxsdk as box
from PIL import Image
from pyzbar.pyzbar import decode
import psycopg2
from psycopg2 import Error
from aws_s3_desktop_uploader import desktop_uploader
# print(desktop_uploader.get_file_created("test/iguana.jpg"))

SECONDS_DELAY = 10.0
last_reference = {}
lock = threading.Lock()
with lock:
	t = threading.Timer(SECONDS_DELAY, process)

with open('config.json') as f:
	config = json.load(f)
	oauth = box.OAuth2(
		client_id=config['client_id'],
		client_secret=config['client_secret'],
		access_token=config['access_token'] # developer token
	)
	client = box.Client(oauth)

def process():
	files = os.listdir(unprocessed_dir)
	for file in files:
		path = os.path.join(unprocessed_dir, file)
		qr_codes = [qr_object.date.decode() for qr_object in decode(Image.open(file))]
		for qr_code in qr_codes:
			update_reference(qr_code)
		try:
			upload_to_box(path)
			upload_to_s3(path)
		except:
			desktop_uploader.move(path, os.path.join(error_dir, file))
		finally:
			desktop_uploader.move(path, os.path.join(done_dir, file))

def upload_to_box(file):
	root_folder = client.folder(folder_id=last_reference['box_folder_id'])
	uploaded_file = shared_folder.upload(file)

	shared_folder = root_folder.create_subfolder('hello_world')
	uploaded_file = shared_folder.upload('test/iguana.jpg')

class GiraffeEventHandler(FileSystemEventHandler):
    """Handler for what to do if watchdog detects a filesystem change
    """
    def on_created(self, event):
        is_file = not event.is_directory
        if is_file:
            with t.lock():
            	t.cancel()

# Setup the watchdog handler for new files that are added while the script is running
if watchdog_platform.is_darwin():
    # Bug workaround for watchdog 1.0.1
    # For now you should NOT use this script for production use because
    # the polling observer is usually used as the a last resort in the watchdog library
    # and is literally implemented by spinning / constantly poking the filesystem
    observer = PollingObserver()
else:
    observer = Observer()
observer.schedule(GiraffeEventHandler(), unprocessed_dir, recursive=True)
observer.start()


while True:
	with lock:
		t = threading.Timer(SECONDS_DELAY, process)
		t.start()
	t.join()




	







# Attempt to get QR code from image

	# If so, query from database the Box folder id for this experiment

# Get file creation date

# Get subfolder id for file creation date, creating it if necessary

# Uplaod to subfolder

# Move to done 