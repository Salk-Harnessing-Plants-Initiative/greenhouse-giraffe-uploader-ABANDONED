from boxsdk import JWTAuth, Client

auth = JWTAuth.from_settings_file('box_config.json')
client = Client(auth)
service_account = client.user().get()
print('Service Account user email is {0}\nShare your root folder with this address for the script to be able to access the subfolders.'.format(service_account.login))