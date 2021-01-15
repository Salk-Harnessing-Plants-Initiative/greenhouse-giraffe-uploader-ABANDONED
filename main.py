import sys
import os
import time
from datetime import datetime
import threading
import json
import boxsdk
from PIL import Image
from pyzbar.pyzbar import decode
import psycopg2
from psycopg2 import Error
from aws_s3_desktop_uploader import desktop_uploader
# For detecting new files
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
# print(desktop_uploader.get_file_created("test/iguana.jpg"))

# Global
logger = logging.getLogger(__name__)
SECONDS_DELAY = 10.0
last_reference = {}
try:
    with open('persist.json') as f:
        last_reference = json.load(f)
except:
    pass
lock = threading.Lock()
t = None
auth = boxsdk.JWTAuth.from_settings_file('box_config.json')
client = boxsdk.Client(auth)
with open('config.json') as f:
    config = json.load(f)
unprocessed_dir = config['unprocessed_dir']
error_dir = config['error_dir']
done_dir = config['done_dir']
postgres = config['postgres']

# Fail on startup if something's wrong
print("Checking the connections...")
# None of the dirs should be the same as another
assert (len([unprocessed_dir, error_dir, done_dir]) == len(set([unprocessed_dir, error_dir, done_dir])))
# Check Box connection
client.user().get()
# Check postgres connection
psycopg2.connect(user=postgres['user'],
    password=postgres['password'],
    host=postgres['host'],
    port=postgres['port'],
    database=postgres['database']
).cursor().execute("SELECT version();")

def process():
    files = sorted([file for file in os.listdir(unprocessed_dir) if not f[0] == '.'])
    if len(files) > 0:
        print("Processing files in the order: {}".format(files))
    for file in files:
        path = os.path.join(unprocessed_dir, file)
        # QR code if present
        try:
            qr_codes = [qr_object.date.decode() for qr_object in decode(Image.open(file))]
            for qr_code in qr_codes:
                update_reference(qr_code)
        except:
            pass
        # Process
        try:
            for match in last_reference['matches']:
                upload_to_box(path, match['box_folder_id'])
            # upload_to_s3(path)
            done_path = desktop_uploader.make_parallel_path(unprocessed_dir, done_dir, path)
            desktop_uploader.move(path, done_path)
        except Exception as e:
            print("Error: ", e)
            error_path = desktop_uploader.make_parallel_path(unprocessed_dir, error_dir, path)
            desktop_uploader.move(path, error_path)

def update_reference(qr_code):
    try:
        # Connect to database
        connection = psycopg2.connect(user=postgres['user'],
            password=postgres['password'],
            host=postgres['host'],
            port=postgres['port'],
            database=postgres['database']
        )
        # Create a cursor to perform database operations
        cursor = connection.cursor()
        # Executing a SQL query
        query = (
            "SELECT box_folder_id, experiment_id, section_name FROM greenhouse_box"
            "INNER JOIN section USING(section_name)"
            "WHERE section_id = '{value}' OR section_name = '{value}';".format(value=qr_code)
        )
        results = cursor.execute(query)
        for result in results:
            match = {}
            match['box_folder_id'] = result[0]
            match['experiment_id'] = result[1]
            match['section_name'] = result[2]
            last_reference['matches'].append(match)

        print("Updated to {}".format(last_reference))
        with open('persist.json', 'w') as f:
            json.dump(last_reference, f)

    except (Exception, Error) as error:
        raise Exception("Error while connecting to PostgreSQL: ", error)
    finally:
        if (connection):
            cursor.close()
            connection.close()

def get_subfolder(box_folder, subfolder_name):
    subfolders = [item for item in box_folder.get_items() if type(item) == boxsdk.object.folder.Folder]
    subfolder_names = [subfolder.name for subfolder in subfolders]
    if subfolder_name not in subfolder_names:
        subfolder = box_folder.create_subfolder(subfolder_name)
        return subfolder
    else:
        for subfolder in subfolders:
            if subfolder.name == subfolder_name:
                return subfolder

def upload_to_box(file, box_folder_id, use_date_subfolder=True, use_section_subfolder=True):
    root_folder = client.folder(folder_id=box_folder_id).get()
    current_folder = root_folder

    if use_date_subfolder:
        file_creation_timestamp = desktop_uploader.creation_date(file)
        file_creation_date = datetime.fromtimestamp(file_creation_timestamp).strftime('%Y-%m-%d')
        current_folder = get_subfolder(current_folder, file_creation_date)

    if use_section_subfolder:
        current_folder = get_subfolder(current_folder, last_reference['section_name'])

    current_folder.upload(file)

class GiraffeEventHandler(FileSystemEventHandler):
    """Handler for what to do if watchdog detects a filesystem change
    """
    def on_created(self, event):
        is_file = not event.is_directory
        if is_file:
            # Attempt to cancel the thread if in countdown mode
            with lock:
                t.cancel()

def main():
    global t
    # process() will run after the countdown if not interrupted during countdown
    with lock:
        t = threading.Timer(SECONDS_DELAY, process)
    # Setup the watchdog handler for new files that are added while the script is running
    observer = Observer()
    observer.schedule(GiraffeEventHandler(), unprocessed_dir, recursive=True)
    observer.start()
    # run process() with countdown indefinitely
    try:
        while True:
            with lock:
                t = threading.Timer(SECONDS_DELAY, process)
                t.start()
            t.join()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt: shutting down...")
        observer.stop()
        observer.join()
        t.stop()
        t.join()

if __name__ == "__main__":
    print("Running Greenhouse Giraffe Uploader...")
    main()
