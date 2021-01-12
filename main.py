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
# (For bug workaround for watchdog 1.0.1)
from watchdog.utils import platform as watchdog_platform
from watchdog.observers.polling import PollingObserver
# print(desktop_uploader.get_file_created("test/iguana.jpg"))

SECONDS_DELAY = 10.0
last_reference = {}
try:
    with open('persist.json') as f:
        last_reference = json.load(f)
except:
    pass
lock = threading.Lock()
t = None

with open('config.json') as f:
    config = json.load(f)
    oauth = boxsdk.OAuth2(
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        access_token=config['access_token'] # developer token
    )
    client = boxsdk.Client(oauth)
    unprocessed_dir = config['unprocessed_dir']
    error_dir = config['error_dir']
    done_dir = config['done_dir']

    # Assert none of the dirs are the same as another
    dirs = [unprocessed_dir, error_dir, done_dir]
    assert (len(dirs) == len(set(dirs)))

def process():
    files = sorted(os.listdir(unprocessed_dir))
    print("Processing files in the order: {}".format(files))
    for file in files:
        # Filter out unaccepted files
        if file.lower() == ".DS_Store".lower():
            continue
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
            upload_to_box(path)
            # upload_to_s3(path)
        except:
            error_path = desktop_uploader.make_parallel_path(unprocessed_dir, error_dir, path)
            desktop_uploader.move(path, error_path)
        finally:
            done_path = desktop_uploader.make_parallel_path(unprocessed_dir, done_dir, path)
            desktop_uploader.move(path, done_path)

def update_reference(qr_code):
    section_id = qr_code
    try:
        # Connect to an existing database
        """
        connection = psycopg2.connect(user=os.environ['user'],
                                      password=os.environ['password'],
                                      host=os.environ['host'],
                                      port=os.environ['port'],
                                      database=os.environ['database'])
        """
        connection = psycopg2.connect(user=sys.argv[1],
                                      password=sys.argv[2],
                                      host=sys.argv[3],
                                      port=sys.argv[4],
                                      database=sys.argv[5])
        # Create a cursor to perform database operations
        cursor = connection.cursor()
        # Executing a SQL query
        result = cursor.execute("SELECT box_folder_id, experiment_id FROM greenhouse_section WHERE section_id = '{}'".format(section_id))
        box_folder_id = result[0][0]
        experiment_id = result[0][1]
        last_reference['box_folder_id'] = box_folder_id
        last_reference['experiment_id'] = experiment_id
        print("Updated to box_folder_id {}, experiment_id {}".format(box_folder_id, experiment_id))
        with open('persist.json', 'w') as f:
            json.dump(last_reference, f)

    except (Exception, Error) as error:
        raise Exception("Error while connecting to PostgreSQL: ", error)
    finally:
        if (connection):
            cursor.close()
            connection.close()
    
def upload_to_box(file):
    root_folder = client.folder(folder_id=last_reference['box_folder_id']).get()
    print(root_folder)
    folders = [item for item in root_folder.get_items() if type(item) == boxsdk.object.folder.Folder]
    folder_names = [folder.name for folder in folders]
    print(folder_names)
    todays_date = datetime.today().strftime('%Y-%m-%d') # todo: replace with file creation time
    if todays_date not in folder_names:
        date_folder = root_folder.create_subfolder(todays_date)
    else:
        date_folder = None
        for folder in folders:
            if folder.name == todays_date:
                date_folder = folder
    date_folder.upload(file)

class GiraffeEventHandler(FileSystemEventHandler):
    """Handler for what to do if watchdog detects a filesystem change
    """
    def on_created(self, event):
        is_file = not event.is_directory
        if is_file:
            # Attempt to cancel the thread if in countdown mode
            with t.lock():
                t.cancel()

def main():
    # process() will run after the countdown if not interrupted during countdown
    with lock:
        t = threading.Timer(SECONDS_DELAY, process)
    # Setup the watchdog handler for new files that are added while the script is running
    if watchdog_platform.is_darwin():
        # Bug workaround for watchdog 1.0.1
        observer = PollingObserver()
    else:
        observer = Observer()
    observer.schedule(GiraffeEventHandler(), unprocessed_dir, recursive=True)
    observer.start()

    # run process() with countdown indefinitely
    while True:
        with lock:
            t = threading.Timer(SECONDS_DELAY, process)
            t.start()
        t.join()

if __name__ == "__main__":
    print("running...")
    main()
