#!/usr/bin/env python3

from gpapi.googleplay import GooglePlayAPI, config
from google_play_scraper import app, search

import sys
import os
# import argparse
import json
import accounts
from time import sleep
import random
import shutil
import datetime

# import logging
# log = logging.getLogger()
# log.setLevel(logging.INFO)
# log.addHandler(logging.StreamHandler()) #Exporting logs to the screen


# GPAPI_GSFID = int(os.environ["GPAPI_GSFID"])
# GPAPI_AUTH_TOKEN = os.environ["GPAPI_GSFID"]

GPAPI_GSFID = None
GPAPI_AUTH_TOKEN = None

LOCALE = os.environ["GPAPI_LOCALE"]
TIMEZONE = os.environ["GPAPI_TIMEZONE"]

GOOGLE_EMAIL = os.environ["GOOGLE_EMAIL"]
GOOGLE_APP_PASSWORD = os.environ["GOOGLE_APP_PASSWORD"]

# DOWNLOAD_PATH = os.environ["APK_DOWNLOAD_PATH"]
DOWNLOAD_PATH = '../data/apks'

SLEEP_SECONDS_MIN = 15
SLEEP_SECONDS_MAX = 30

DOWNLOAD_APKS_LIMIT = -1
DOWNLOADS_PROGRESS_FILENAME = 'downloads-progress.json'
DOWNLOADS_PROGRESS_DIFF_FILENAME = 'downloads-progress-diff.json'
DOWNLOADS_PROGRESS_ORGANIZER_FILENAME = 'downloads-progress-organizer.json'

DOWNLOADED_FILE = f"{DOWNLOAD_PATH}/downloaded.json"
DOWNLOADED_FILE_DEFAULT_KEYS =  {
    'by_device': {},
    'by_email': {},
}

DEVICES = {
    'GB': [
        'op_5t',
        'op_8_pro',
    ],
    'US': [
        # 'op_7t',
        # 'rm_note_5',
        'US_poco_f1'
    ],
    'FR': [
        'FR2_poco_f1'
    ],
    'DE': [
        'DE_poco_f1'
    ],
    'BR': [
        # 'BR_poco_f1',
        "BR_sm_s9_plus",
    ],
}

def makeDirsRecursivelyForFile(file_path):
    folder = os.path.dirname(file_path)
    os.makedirs(folder, exist_ok = True)

def uniqueList(items):
    # All this work to get an unique list... really!!!
    return list(set(items))

def forceMoveDir(from_dir, to_dir):
    backup = None

    if os.path.isdir(to_dir):
        backup = f"{to_dir}-backup"
        os.rename(to_dir, backup)

    try:
        os.rename(from_dir, to_dir)
    except Exception as e:
        print(e)

    if backup:
        shutil.rmtree(backup, ignore_errors=False, onerror=None)

def randomSleep():
    # keep a slow pace to avoid being blacklisted.
    seconds = random.randint(SLEEP_SECONDS_MIN, SLEEP_SECONDS_MAX)

    while seconds > 0:
        print(f"\tSleeping for {seconds} seconds...", end="\r")
        sleep(1)
        seconds -= 1

def buildApkFolderPath(app_id, country_code, category_id):
    return f"{DOWNLOAD_PATH}/{category_id}/{country_code}/{app_id}"

def buildApkFilePath(app_id, country_code, category_id, filename, extension):
    folder = buildApkFolderPath(app_id, country_code, category_id)
    os.makedirs(folder, exist_ok = True)
    return f"{folder}/{filename}.{extension}"

def buildBaseDownloadResult(metadata):
    return {
        'login_failed': False,
        'download_failed': False,
        'base_download_failed': False,
        'additional_files_download_failed': False,
        'split_download_failed': False,
        'error': {
            'login': None,
            'base_download': None,
            'additional_files_download': None,
            'split_download': None,
        },
        'metadata': metadata,
        'already_downloaded_for': {},
    }

def readJsonFile(filename, default = []):
    if not os.path.exists(filename):
        return default

    with open(filename) as file:
        return json.load(file)

def writeToJsonFile(filename, data):
    with open(filename, "w") as file:
        json.dump(data, file, indent = 4) #, default=list)

def saveApkFrom(download, app_id, country_code, category_id = 'UNKNOWN'):
    print("\n--> Attempting to download the APK")

    try:
        file_path = buildApkFilePath(app_id, country_code, category_id, "base", "apk")

        # We will skip files already downloaded to speedup the process, but we
        # may not always want this behavior, therefore we may want to add a
        # force option.
        # @TODO ad force option to save apk
        if os.path.isfile(file_path):
            return True, None

        with open(file_path, "wb") as apk_file:
            parts = int(download['file']['total_size']) / download['file']['chunk_size']
            for index, chunk in enumerate(download.get("file").get("data")):
                apk_file.write(chunk)
                print(f"\tDownloading: {round((index/parts)*100)}% complete...", end="\r")

            print("\n\tDownload successful\n")

        return True, None

    except Exception as e:
        error = f"Base Download Error: {e}"
        print(f"\n{error}\n")
        return False, error


def saveAdditionalFilesFrom(download, app_id, country_code, category_id = 'UNKNOWN'):
    print('\n--> Attempting to download additional files')

    try:
        for obb in download['additionalData']:
            # name = DOWNLOAD_PATH + obb['type'] + '.' + str(obb['versionCode']) + '.' + app_id + '.obb'
            filename = obb['type'] + '.' + str(obb['versionCode'])
            filepath = buildApkFilePath(app_id, country_code, category_id, filename, 'obb')

            # We will skip files already downloaded to speedup the process, but we
            # may not always want this behavior, therefore we may want to add a
            # force option.
            # @TODO ad force option to save apk
            if os.path.isfile(filepath):
                continue

            with open(filepath, 'wb') as second:
                parts = int(obb['file']['total_size']) / obb['file']['chunk_size']
                for index, chunk in enumerate(obb.get("file").get("data")):
                    print(f"Downloading: {round((index/parts)*100)}% complete...", end="\r")
                    second.write(chunk)

                print("\n\tAdditional Download successful\n")

        return True, None

    except Exception as e:
        error = f"Additional Download Files Error: {e}"
        print(f"\n{error}\n")
        return False, error

def saveSplitsFrom(download, app_id, country_code, category_id = 'UNKNOWN'):
    print("\n--> Attempting to download splits")

    try:
        splits = download.get('splits')
        if splits:
            for split in splits:
                # split_path = DOWNLOAD_PATH + f"{app_id}_{split['name']}.apk"
                filepath = buildApkFilePath(app_id, country_code, category_id, split['name'], 'apk')

                print(f"Split file path: {filepath}")

                # We will skip files already downloaded to speedup the process, but we
                # may not always want this behavior, therefore we may want to add a
                # force option.
                # @TODO ad force option to save apk
                if os.path.isfile(filepath):
                    continue

                with open(filepath, 'wb') as f:
                    parts = int(split['file']['total_size']) / split['file']['chunk_size']
                    for index, chunk in enumerate(split.get('file').get('data')):
                        print(f"Downloading: {round((index/parts)*100)}% complete...", end="\r")
                        f.write(chunk)

            print("\n\tSplits Download successful\n")

        return True, None

    except Exception as e:
        error = f"Split Download Error: {e}"
        print(f"\n{error}\n")
        return False, error

def downloadApkWithRandomLogin(app_id, country_code, category_id = 'UNKNOWN'):
    print(f"\n\n-------------------- {app_id} ---------------------\n")
    device_code_name = random.choice(DEVICES[country_code])

    try:
        login = accounts.random_login(device_code_name)
    except Exception as e:
        metadata = {
            'app_id': app_id,
            'email': 'UNKNOWN',
            'device_code_name': device_code_name,
            'category_id': category_id,
            'country_code': country_code,
        }

        download_result = buildBaseDownloadResult(metadata)

        download_result['login_failed'] = True
        download_result['error']['login'] = f"downloadApkWithRandomLogin(): {e}"

        return download_result

    return _downloadAppApk(app_id, login, country_code, category_id)

def downloadApkForDevice(app_id, device_code_name, country_code, category_id, email):
    print(f"\n\n-------------------- {app_id} ---------------------\n")

    if email is None:
        account = accounts.getRandomAccountForDevice(device_code_name)

        if account is None:
            return {
                'error': f"No email provided and no accounts found for the device: {device_code_name}"
            }

        email = account['email']

    login = accounts.login_for_device(device_code_name, email)

    if 'error' in login:
        # raise login['error']
        return {'error': login['error']}

    return _downloadAppApk(app_id, login, country_code, category_id)

def downloadApkForCountryDevice(app_id, country_code, email, category_id):
    print(f"\n\n-------------------- {app_id} ---------------------\n")

    device_code_name = random.choice(DEVICES[country_code.upper()])

    login = accounts.login_for_device(device_code_name, email)

    if 'error' in login:
        raise login['error']

    return _downloadAppApk(app_id, login, country_code, category_id)

def _downloadAppApk(app_id, login, country_code, category_id = 'UNKNOWN'):
    api = login['api']
    email = login['account']['email']
    device_code_name = login['account']['device_code_name']

    metadata = {
        'app_id': app_id,
        'email': email,
        'device_code_name': device_code_name,
        'category_id': category_id,
        'country_code': country_code,
    }

    download_result = buildBaseDownloadResult(metadata)

    if 'api' in login:
        download_result['login_failed'] = False

        print(f"\n--> Download APK for {app_id} on device {device_code_name} with account {email} for category {category_id}\n")

        try:
            downloaded = readJsonFile(DOWNLOADED_FILE, DOWNLOADED_FILE_DEFAULT_KEYS)

            # if device_code_name in downloaded['by_device'] and app_id in downloaded['by_device'][device_code_name]:
            #     download_result['already_downloaded_for'] = downloaded['by_device'][device_code_name][app_id]
            #     download_result['download_failed'] = True
            #     return download_result

            download = api.download(app_id)

            download_succeeded, error = saveApkFrom(download, app_id, country_code, category_id)

            if not download_succeeded:
                download_result['download_failed'] = True
                download_result['base_download_failed'] = True
                download_result['error']['base_download'] = error
                return download_result

            download_succeeded, error = saveAdditionalFilesFrom(download, app_id, country_code, category_id)

            if not download_succeeded:
                download_result['download_failed'] = True
                download_result['additional_files_download_failed'] = True
                download_result['error']['additional_files_download'] = error

            download_succeeded, error = saveSplitsFrom(download, app_id, country_code, category_id)

            if not download_succeeded:
                download_result['download_failed'] = True
                download_result['split_download_failed'] = True
                download_result['error']['split_download'] = error

            metadata_file = buildApkFilePath(app_id, country_code, category_id, "metadata", "json")

            writeToJsonFile(metadata_file, metadata)

            if not device_code_name in downloaded['by_device']:
                downloaded['by_device'][device_code_name] = {}

            if not app_id in downloaded['by_device'][device_code_name]:
                downloaded['by_device'][device_code_name][app_id] = {}

            downloaded['by_device'][device_code_name][app_id] = metadata

            if not email in downloaded['by_email']:
                downloaded['by_email'][email] = {}

            if not app_id in downloaded['by_email'][email]:
                downloaded['by_email'][email][app_id] = {}

            downloaded['by_email'][email][app_id] = metadata

            writeToJsonFile(DOWNLOADED_FILE, downloaded)

        except Exception as e:
            # raise(e)
            message = f"downloadApk() Exception: {e}"
            print(message)
            download_result['download_failed'] = True
            download_result['exception'] = message

    return download_result


def dowanloadApksByCategory(category_id):
    filename = f"../data/scrapped/apps/{category_id}.json"

    if not os.path.exists(filename):
        return {'error': f"File not found: {filename}"}

    with open(filename) as file:
        data = json.load(file)
        data['category'] = category_id

        if not 'date' in data:
            data['date'] = None

        if not 'country' in data:
            data['country'] = None

        return downloadApksForApps(data)


def downloadApksForApps(data, retry_failed_downloads=True):
    country_code = data['country'].upper()
    category_id = data['category'].upper()
    date = data['date']

    default = {
        'country_code': country_code,
        'category_id': category_id,
        'scrape_date': date,
        'total_to_download': 0,
        'total_downloaded': 0,
        'total_remaining': 0,
        'total_download_failures': 0,
        'excluded': {
            'paid_apps': [],
            'outdated_apps': [],
            'less_then_1000_installs': [],
        },
        'download_failures': {},
        'downloaded_app_ids': [],
        'remaining_app_ids': [],
    }

    progress_file_path = f"{DOWNLOAD_PATH}/{category_id}/{country_code}_{date}_{DOWNLOADS_PROGRESS_FILENAME}"

    progress = readJsonFile(progress_file_path, default)

    app_ids = []

    progress['category_id'] = category_id
    progress['excluded']['paid_apps'] = []
    progress['excluded']['outdated_apps'] = []
    progress['excluded']['less_then_1000_installs'] = []

    apps = data['apps'].items()

    # progress['to_download'] = []

    for app_id, app in apps:
        folder =  buildApkFolderPath(app_id, country_code, category_id)

        # Speedup download by skipping the ones already downloaded in a previous run
        # This check is naive and we may risk having an incomplete apk or an
        # empty folder
        if os.path.isdir(folder):
            contents = os.listdir(folder)

            if len(contents) > 0 and 'base.apk' in contents:
                continue
            else:
                # progress['to_download'].append(app_id)
                shutil.rmtree(folder, ignore_errors=False, onerror=None)

        # else:
        #     # progress['to_download'].append(app_id)
        #     shutil.rmtree(folder, ignore_errors=False, onerror=None)

        if app['price'] > 0:
            progress['excluded']['paid_apps'].append(app_id)

            if app_id in progress['remaining_app_ids']:
                progress['remaining_app_ids'].remove(app_id)

            if app_id in progress['download_failures']:
                progress['download_failures'].pop(app_id)

            continue

        # 1577836800 => 1 January 2020 00:00:00 GMT+00:00

        if 'updated' in app and app['updated'] < 1577836800:
            progress['excluded']['outdated_apps'].append(app_id)

            if app_id in progress['remaining_app_ids']:
                progress['remaining_app_ids'].remove(app_id)

            if app_id in progress['download_failures']:
                progress['download_failures'].pop(app_id)

            continue

        if 'realInstalls' in app and app['realInstalls'] < 1000:
            progress['excluded']['less_then_1000_installs'].append(app_id)

            if app_id in progress['remaining_app_ids']:
                progress['remaining_app_ids'].remove(app_id)

            if app_id in progress['download_failures']:
                progress['download_failures'].pop(app_id)

            continue

        app_ids.append(app_id)

    progress['remaining_app_ids'] = app_ids

    if retry_failed_downloads:
        download_failures_ids = list(progress['download_failures'].keys())
        progress['remaining_app_ids'] = download_failures_ids + progress['remaining_app_ids']

    progress['remaining_app_ids'] = uniqueList(progress['remaining_app_ids'])
    progress['downloaded_app_ids'] = uniqueList(progress['downloaded_app_ids'])

    total_to_download = len(progress['remaining_app_ids'])

    progress['total_remaining'] = total_to_download
    progress['total_to_download'] = total_to_download
    progress['total_downloaded'] = len(progress['downloaded_app_ids'])

    remaining_app_ids = enumerate(progress['remaining_app_ids'][:])

    # print("TO DOWNLOAD: ", app_ids)
    # print("TOTAL TO DOWNLOAD: ", len(app_ids))
    # remaining_app_ids = []

    for index, app_id in remaining_app_ids:
        if DOWNLOAD_APKS_LIMIT > 0 and index > DOWNLOAD_APKS_LIMIT:
            return {'progress': progress}

        print(f"\n\n---> Starting Downloading ({index}/{total_to_download}) APK for {app_id} on category {category_id} <---")

        result = downloadApkWithRandomLogin(app_id, country_code, category_id)

        if result['login_failed'] == True or result['download_failed'] == True:
            progress['download_failures'][app_id] = result
            progress['total_download_failures'] = len(progress['download_failures'])
        else:
            if app_id in progress['download_failures']:
                progress['download_failures'].pop(app_id)

            progress['downloaded_app_ids'].append(app_id)

        # No matter if downloaded succeeded or failed we want to remove the app
        # id  and update the totals accordingly.
        progress['remaining_app_ids'].remove(app_id)
        progress['total_downloaded'] = len(progress['downloaded_app_ids'])
        progress['total_remaining'] = len(progress['remaining_app_ids'])
        progress['total_download_failures'] = len(progress['download_failures'])

        # print("\n-> PROGRESS: ", progress)

        writeToJsonFile(progress_file_path, progress)

        # keep a slow pace to avoid being blacklisted.
        randomSleep()


    return {
        'dir': DOWNLOAD_PATH,
        'progress': progress,
    }


def dowanloadApksByCountryCategory(country_file):

    data = readJsonFile(country_file, {})

    # country_code = top_free_apps['country'].upper()
    # category_id = top_free_apps['category'].upper()
    # date = top_free_apps['date']

    # category_dir = os.path.join(DOWNLOAD_PATH, category_id)
    # country_dir = os.path.join(category_dir, country_code)
    # uncategorized_dir = os.path.join(category_dir, 'UNCATEGORIZED')

    # print("\n---> Starting to organize apks by country category")

    return downloadApksForApps(data)

    # return {
    #     'dir': DOWNLOAD_PATH,
    #     'progress': progress,
    # }


def fixDownloadedApksByCategory(category_id):
    default = {
        'category_id': category_id,
        'total_to_download': 0,
        'total_downloaded': 0,
        'total_remaining': 0,
        'total_download_failures': 0,
        'download_failures': {},
        'downloaded_app_ids': [],
        'remaining_app_ids': [],
    }

    progress_file_path = f"{DOWNLOAD_PATH}/{category_id}/{DOWNLOADS_PROGRESS_FILENAME}"
    fixed_progress_file_path = f"{DOWNLOAD_PATH}/{category_id}/fixed-{DOWNLOADS_PROGRESS_FILENAME}"

    downloaded = readJsonFile(DOWNLOADED_FILE, DOWNLOADED_FILE_DEFAULT_KEYS)

    progress = readJsonFile(progress_file_path, default)
    fixed_app_ids = readJsonFile(fixed_progress_file_path, default)

    fix_app_ids = []

    progress['category_id'] = category_id

    for app_id in progress['downloaded_app_ids']:
        apks_path = f"{DOWNLOAD_PATH}/{category_id}/{app_id}"
        print('apks_path: ', apks_path)

        files = os.listdir(apks_path)

        if 'base.apk' not in files:
            print('files: ', files)
            fix_app_ids.append(app_id)

    fixed_app_ids['total_to_download'] = progress['total_to_download']
    fixed_app_ids['remaining_app_ids'] = fix_app_ids

    total_to_download = len(fix_app_ids)

    remaining_app_ids = enumerate(fixed_app_ids['remaining_app_ids'])

    for index, app_id in remaining_app_ids:
        if DOWNLOAD_APKS_LIMIT > 0 and index > DOWNLOAD_APKS_LIMIT:
            return {'progress': fixed_app_ids}

        print(f"\n\n---> Starting fixing APK Download ({index}/{total_to_download}) for {app_id} on category {category_id} <---")

        app = {}

        device_apps = downloaded['by_device'].items()

        # When exists, we need to get the device account used for the download,
        # otherwise we risk not being able to download the apk due to account or
        # device restrictions and/or incompatibilities.
        for device_id, apps in device_apps:
            for package_name, app_data in apps.items():
                if package_name == app_id and app_data['category_id'] == category_id:
                    device_accounts = accounts.getAccountsForDevice(app_data['device_code_name'])
                    print('device_id: ', device_id)
                    print('app_data: ', app_data)

                    if device_accounts is None:
                        device_account = accounts.getRandomAccount()
                        print('device_account1: ', device_account)
                    else:
                        email = random.choice(list(device_accounts))
                        device_account =  device_accounts[email]
                        print('device_account2: ', device_account)

                    break

        result = downloadApkForDevice(app_id, device_account['device_code_name'], device_account['email'], category_id)

        if result['login_failed'] == True or result['download_failed'] == True:
            fixed_app_ids['download_failures'][app_id] = result
            fixed_app_ids['total_download_failures'] = len(fixed_app_ids['download_failures'])
        else:
            fixed_app_ids['downloaded_app_ids'].append(app_id)

        # No matter if downloaded succeeded or failed we want to remove the app
        # id  and update the totals accordingly.
        fixed_app_ids['remaining_app_ids'].remove(app_id)
        fixed_app_ids['total_downloaded'] = len(fixed_app_ids['downloaded_app_ids'])
        fixed_app_ids['total_remaining'] = len(fixed_app_ids['remaining_app_ids'])

        writeToJsonFile(fixed_progress_file_path, fixed_app_ids)

        # keep a slow pace to avoid being blacklisted.
        randomSleep()

    return {
        'dir': DOWNLOAD_PATH,
        'progress': fixed_app_ids,
    }

def downloadApksFromDiff(diff_file, email, retry_failed_downloads=False):

    diff = readJsonFile(diff_file, {})

    # print(diff)

    country_code = diff['country'].upper()
    category_id = diff['category'].upper()
    date = diff['date']

    # progress_file = f"{DOWNLOAD_PATH}/{category_id}/{DOWNLOADS_PROGRESS_FILENAME}"
    progress_diff_file = f"{DOWNLOAD_PATH}/{category_id}/{country_code}-{date}-{DOWNLOADS_PROGRESS_DIFF_FILENAME}"

    default = {
        'country': country_code,
        'category_id': category_id,
        'date': date,
        'total_to_download': 0,
        'total_downloaded': 0,
        'total_remaining': 0,
        'total_download_failures': 0,
        'excluded': {
            'paid_apps': [],
            'outdated_apps': [],
            'less_then_1000_installs': [],
        },
        'download_failures': {},
        'downloaded_app_ids': [],
        'remaining_app_ids': diff['in_download_failures'] + diff['to_download'],
    }

    progress = readJsonFile(progress_diff_file, default)

    if retry_failed_downloads:
        download_failures_ids = list(progress['download_failures'].keys())
        progress['remaining_app_ids'] = download_failures_ids + progress['remaining_app_ids']

    # progress['remaining_app_ids'] = diff['to_download']
    print("\n---> Starting to download apks in the diff for remaining downloads")

    progress['remaining_app_ids'] = uniqueList(progress['remaining_app_ids'])
    progress['downloaded_app_ids'] = uniqueList(progress['downloaded_app_ids'])

    for app_id in progress['remaining_app_ids'][:]:

        result = downloadApkForCountryDevice(app_id, country_code, email, category_id)

        if result['login_failed'] == True or result['download_failed'] == True:
            progress['download_failures'][app_id] = result
            progress['total_download_failures'] = len(progress['download_failures'])
        else:
            progress['downloaded_app_ids'].append(app_id)

            if app_id in download_failures_ids and not result['base_download_failed'] and not result['additional_files_download_failed'] and not result['split_download_failed']:
                progress['download_failures'].pop(app_id)

        # No matter if downloaded succeeded or failed we want to remove the app
        # id  and update the totals accordingly.
        progress['remaining_app_ids'].remove(app_id)
        progress['total_downloaded'] = len(progress['downloaded_app_ids'])
        progress['total_download_failures'] = len(progress['download_failures'])
        progress['total_remaining'] = len(progress['remaining_app_ids'])

        # print("\n-> PROGRESS: ", progress)

        writeToJsonFile(progress_diff_file, progress)

        # keep a slow pace to avoid being blacklisted.
        randomSleep()


    return {
        'dir': DOWNLOAD_PATH,
        'progress': progress,
    }

def organizeByCountryCategory(country_file):
    top_free_apps = readJsonFile(country_file, {})

    country_code = top_free_apps['country'].upper()
    category_id = top_free_apps['category'].upper()
    date = top_free_apps['date']

    category_dir = os.path.join(DOWNLOAD_PATH, category_id)
    country_dir = os.path.join(category_dir, country_code)
    uncategorized_dir = os.path.join(category_dir, 'UNCATEGORIZED')

    print("\n---> Starting to organize apks by country category")

    try:
        app_ids = os.listdir(uncategorized_dir)
    except FileNotFoundError:
        return {
            'error': f"Category dir not found: {uncategorized_dir}",
        }


    os.makedirs(country_dir, exist_ok = True)
    os.makedirs(uncategorized_dir, exist_ok = True)

    progress = {
        'country': country_code,
        'category_id': category_id,
        'date': date,
        'total_categorized': 0,
        'total_uncategorized': 0,
        'categorized_app_ids': [],
        'uncategorized_app_ids': [],
    }

    progress_file = f"{DOWNLOAD_PATH}/{category_id}/{country_code}-{date}-{DOWNLOADS_PROGRESS_ORGANIZER_FILENAME}"
    # progress = readJsonFile(progress_file, default)

    for app_id in app_ids[:]:

        if len(app_id) < 3:
            # It looks like a folder for a country
            continue

        app_uncategory_dir = os.path.join(uncategorized_dir, app_id)

        if os.path.isdir(app_uncategory_dir):
            if app_id in top_free_apps['top_free']:
                app_category_country_dir = os.path.join(country_dir, app_id)
                print(f"\n---> Copy From: {app_uncategory_dir} To: {app_category_country_dir}")
                # forceMoveDir(app_uncategory_dir, app_category_country_dir)
                shutil.copytree(app_uncategory_dir, app_category_country_dir) # dirs_exist_ok=True)
                progress['categorized_app_ids'].append(app_id)

            else:
                # app_uncategorized_dir = os.path.join(uncategorized_dir, app_id)
                # print(f"\n---> Move From: {app_category_dir} To: {app_uncategorized_dir}")
                # forceMoveDir(app_category_dir, app_uncategorized_dir)
                progress['uncategorized_app_ids'].append(app_id)

        progress['total_categorized'] = len(progress['categorized_app_ids'])
        progress['total_uncategorized'] = len(progress['uncategorized_app_ids'])

        writeToJsonFile(progress_file, progress)

    return {
        'dir': country_dir,
        'progress': progress,
    }


def validateCountryCategoryFolder(country_file):

    if not os.path.exists(country_file):
        return {'error': f"FIle not found: {country_file}"}

    top_free_apps = readJsonFile(country_file, {})

    country_code = top_free_apps['country'].upper()
    category_id = top_free_apps['category'].upper()
    date = top_free_apps['date']

    category_dir = os.path.join(DOWNLOAD_PATH, category_id)
    country_dir = os.path.join(category_dir, country_code)

    print("\n---> Starting to validate APKS folder by country category")

    progress = {
        'country': country_code,
        'category_id': category_id,
        'date': date,
        'total_categorized': 0,
        'total_uncategorized': 0,
        'categorized_app_ids': [],
        'uncategorized_app_ids': [],
    }

    # progress_file = f"{country_dir}-{date}-apks-foldervalidation.json"

    folder_app_ids = os.listdir(country_dir)

    top_free_app_ids = top_free_apps['apps'].keys()

    return {
        'dir': country_dir,
        'folder-total-apks': len(folder_app_ids),
        'top-free-total-apks': len(top_free_app_ids),
        'folder-diff': folder_app_ids - top_free_app_ids,
        'top-free-diff': top_free_app_ids - folder_app_ids,
    }


def fetch_app_details(app_id, country='us', lang='en'):
    return app(
        app_id,
        lang=lang,
        country=country # defaults to 'us'
    )

def fetch_app_metadata(app_id, country_code):

    device_code_name = random.choice(DEVICES[country_code.upper()])

    account = accounts.getRandomAccountForDevice(device_code_name)

    if account is None:
        return {
            'error': f"No email provided and no accounts found for the device: {device_code_name}"
        }

    email = account['email']

    login = accounts.login_for_device(device_code_name, email)

    if 'error' in login:
        return login

    api = login['api']

    result = api.details(app_id)

    file_path = f"../data/apps/{app_id}/{country_code}/details.json"

    makeDirsRecursivelyForFile(file_path)

    writeToJsonFile(file_path, result)

    result = fetch_app_details(app_id, country_code.lower())

    file_path = f"../data/apps/{app_id}/{country_code}/details2.json"

    makeDirsRecursivelyForFile(file_path)

    writeToJsonFile(file_path, result)

    return {'dir': file_path}
