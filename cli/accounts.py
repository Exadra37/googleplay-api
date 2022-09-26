from gpapi.googleplay import GooglePlayAPI, config

import sys
import os
import json
import random
import encryption

import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler()) #Exporting logs to the screen

GOOGLE_ACCOUNTS_FILE = os.environ["GOOGLE_ACCOUNTS_FILE"]


def getRandomDeviceCodeName():
    devices = config.getDevicesCodenames()
    return random.choice(devices)

def getAccounts():
    if not os.path.exists(GOOGLE_ACCOUNTS_FILE):
        return dict()

    with open(GOOGLE_ACCOUNTS_FILE) as file:
        return json.load(file)

def save(account, validate_login=True):
    if account['device_code_name'] is None:
        account['device_code_name'] = random.choice(config.getDevicesCodenames())

    email = account['email']
    device_code_name = account['device_code_name']

    logger.info(f"\n---> Creating an account for device_code_name: {device_code_name}")

    if not 'plain_text_password' in account:
        return None

    if validate_login and not login(account):
        return False

    print('account: ', account)

    if 'plain_text_password' in account:
        account['password'] = encryption.base64_encrypt_string(account['plain_text_password'])
        account.pop('plain_text_password')

    if 'api.gsfId' in account:
        account['gsfId'] = account['api.gsfId']
        account.pop('api.gsfId')

    if 'api.authSubToken' in account:
        account['authSubToken'] = encryption.base64_encrypt_string(account['api.authSubToken'])
        account.pop('api.authSubToken')

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


def getAccountsForDevice(device_code_name):
    accounts = getAccounts()

    if device_code_name in accounts['by_device']:
        return accounts['by_device'][device_code_name]['accounts']

    return None


def login_for_device(device_code_name, email):
    accounts = getAccountsForDevice(device_code_name)

    if accounts is None:
        logger.error(f"\nAccount not found for device code name: {device_code_name}")
        return False

    return {
        "account": accounts[email],
        "api": login(accounts[email])
    }

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

    return {
        "account": accounts[email],
        "api": login(accounts[email])
    }


def login(account):
    api = GooglePlayAPI(account['locale'], account['timezone'], account['device_code_name'])

    if ('gsfId' in account and 'authSubToken' in account) and (account['gsfId'] and account['authSubToken']):
        logger.info("\n--> Attempting to login with the GPAPI_GSFID and GPAPI_GSFID\n")

        gsfId = account['gsfId'][0]
        authSubToken = encryption.base64_decrypt_string(account['authSubToken'])

        api.login(None, None, gsfId, authSubToken)

    elif 'plain_text_password' in account:
        logger.info('\n--> Logging in with GOOGLE_EMAIL and GOOGLE_APP_PASSWORD\n')

        api.login(account['email'], account['plain_text_password'], None, None)

        account['api.gsfId'] = api.gsfId,
        account['api.authSubToken'] = api.authSubToken

        save(account, False)

    else:
        logger.info("\n--> You need to login first with GOOGLE_EMAIL and GOOGLE_APP_PASSWORD\n")
        return False

    return api
