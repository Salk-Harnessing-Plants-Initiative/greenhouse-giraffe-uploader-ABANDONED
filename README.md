# Greenhouse giraffe uploader
The "giraffe" is a custom imaging apparatus we use in our greenhouse. This script processes its images.

# Dependencies
```
git clone --recursive git@github.com:Salk-Harnessing-Plants-Initiative/greenhouse-giraffe-uploader.git
cd greenhouse-giraffe-uploader
pipenv install
```

You need `zbar`.

# Configure
## Box 

1. `Create New App` > `Custom App` > `Server Authentication with JWT` > (go to app Configuration tab) > `Generate a Public/Private keypair` > `Download as JSON` > rename JSON to `box_config.json` and put in same directory as `main.py`
2. Enable this script to access your folders by sharing the relevant root folder with the email address of this "Service user". Find the email address by running the following:
```
pipenv run python get_email_address.py
```

## config.json
```
cp example_config.json config.json
```
Then fill out the settings

# To run
```
pipenv run python main.py
```
