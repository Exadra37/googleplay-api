from gpapi.googleplay import GooglePlayAPI, RequestError, config

import sys
import os
import json
import random
import encryption

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler()) #Exporting logs to the screen

# GOOGLE_ACCOUNTS_FILE = os.environ["GOOGLE_ACCOUNTS_FILE"]
GOOGLE_ACCOUNTS_FILE = '../data/google_accounts.json'


def getRandomDeviceCodeName():

    devices = config.getDevicesCodenames()

    return random.choice(devices)


def getAccounts():
    if not os.path.exists(GOOGLE_ACCOUNTS_FILE):
        return dict()

    with open(GOOGLE_ACCOUNTS_FILE) as file:
        return json.load(file)


def getAccountsForDevice(device_code_name):
    accounts = getAccounts()

    if 'by_device' in accounts and  device_code_name in accounts['by_device']:
        return accounts['by_device'][device_code_name]['accounts']

    return None

def getRandomAccountForDevice(device_code_name):
    accounts = getAccounts()

    if 'by_device' in accounts and  device_code_name in accounts['by_device']:
        device_accounts = accounts['by_device'][device_code_name]['accounts']
        email = random.choice(list(device_accounts))
        return device_accounts[email]

    return None


def getRandomAccount():

    accounts = getAccounts()

    device_code_name = random.choice(list(accounts['by_device']))

    email = random.choice(list(accounts['by_device'][device_code_name]['accounts']))

    return accounts['by_device'][device_code_name]['accounts'][email]


def save(account, validate_login=True):
    if account['device_code_name'] is None:
        account['device_code_name'] = getRandomDeviceCodeName()

    email = account['email']
    device_code_name = account['device_code_name']

    logger.info(f"\n---> Creating an account for device_code_name: {device_code_name}")

    if not 'plain_text_password' in account:
        return None

    api = login(account)

    if api == False:
        return False

    if api.gsfId:
        account['gsfId'] = api.gsfId

    if api.authSubToken:
        account['authSubToken'] = encryption.base64_encrypt_string(api.authSubToken)

    if 'plain_text_password' in account:
        account['password'] = encryption.base64_encrypt_string(account['plain_text_password'])
        account.pop('plain_text_password')

    accounts = getAccounts()

    if not 'by_device' in accounts:
        accounts['by_device'] = {}

    if not device_code_name in accounts['by_device']:
        accounts['by_device'][device_code_name] = {'accounts': {}}

    accounts['by_device'][device_code_name]['accounts'][email] = account

    if not 'by_email' in accounts:
        accounts['by_email'] = {}

    if not email in accounts['by_email']:
        accounts['by_email'][email] = {'devices': {}}

    accounts['by_email'][email]['devices'][device_code_name] = account

    logger.debug("SAVED ACCOUNT:")
    logger.debug(account)

    with open(GOOGLE_ACCOUNTS_FILE, "w") as file:
        json.dump(accounts, file, indent = 4)

    return True


def login_for_device(device_code_name, email):
    accounts = getAccountsForDevice(device_code_name)

    if accounts is None:
        message = f"Account not found for device code name {device_code_name} with email {email}"
        logger.error(message)

        return {
            "error": {
                'message': message,
                'metadata': {
                    'email': email,
                    'device_code_name': device_code_name,
                }
            }
        }

    return handle_login(accounts, email, device_code_name)


def random_login(device_code_name = None):
    if not device_code_name == None:
        accounts = getAccountsForDevice(device_code_name)

        if accounts is None:
            return None

    if device_code_name == None:
        found_account = False

        while not found_account:

            device_code_name = getRandomDeviceCodeName()

            logger.debug(f"\n---> Attempting to find account for device code name: {device_code_name}")
            accounts = getAccountsForDevice(device_code_name)

            if accounts is None:
                continue

            found_account = True

    email = random.choice(list(accounts.keys()))

    return handle_login(accounts, email, device_code_name)

def handle_login(accounts, email, device_code_name):

    print(f"\n---> Google account login for device {device_code_name} with email {email}")

    api = login(accounts[email])

    if api is False:
        return {
            "error": {
                'message': f"\n ---> ERROR: Failed login for device {device_code_name} with email {email}",
                'metadata': {
                    'email': email,
                    'device_code_name': device_code_name,
                }
            }
        }

    print(f"---> Logged in successfully with device {device_code_name} and email {email}")

    return {
        "account": accounts[email],
        "api": api
    }

def login(account):
    try:
        api = GooglePlayAPI(account['locale'], account['timezone'], account['device_code_name'])

        if ('gsfId' in account and 'authSubToken' in account) and (account['gsfId'] and account['authSubToken']):
            print(f"\n--> Attempting to login via GPAPI_GSFID and GPAPI_GSFID on device {account['device_code_name']} with account {account['email']}\n")

            gsfId = account['gsfId']
            authSubToken = encryption.base64_decrypt_string(account['authSubToken'])

            api.login(None, None, gsfId, authSubToken)

        elif 'plain_text_password' in account:
            logger.info(f"\n--> Attempting to login via email/password combo on device {account['device_code_name']} with account {account['email']}\n")

            api.login(account['email'], account['plain_text_password'], None, None)

        else:
            logger.info("\n--> You need to login first with GOOGLE_EMAIL and GOOGLE_APP_PASSWORD\n")
            return False

    except RequestError as e:
        # print(dir(e))
        logger.error(e)
        return False

    return api
