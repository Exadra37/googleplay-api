#!/usr/bin/env python3

from gpapi.googleplay import GooglePlayAPI, config

import os

import click
import download
import accounts
import encryption
import categories
import sensortower
import search

LOCALE = os.environ["GPAPI_LOCALE"]
TIMEZONE = os.environ["GPAPI_TIMEZONE"]

ENCRYPTION_KEY_FILE = os.environ["ENCRYPTION_KEY_FILE"]

def echoSuccess(message):
    click.secho(message, fg='green')


def echoWarn(message):
    click.secho(message, fg='yellow')

def echoError(message):
    click.secho(message, err=True, fg='red')


@click.group()
@click.option('--debug/--no-debug', default=False)
def cli(debug):
    click.echo(f"Debug mode is {'on' if debug else 'off'}")

@cli.command(help = "Add a new google account")  # @cli, not @click!
@click.option("--email", required=True, help="The email for your device Google account")
@click.option("--password", required=True, help="The password for your Google account or an App password")
@click.option("--device", default=None, help="The device code name, e.g angler. [default: random]")
@click.option("--locale", default=LOCALE, show_default=True, help="The locale for your Google account, e.g en_PT.")
@click.option("--timezone", default=TIMEZONE, show_default=True, help="The timezone for your Google account, e.g Europe/Lisbon.")
def account(email, password, device, locale, timezone):
    click.echo('Creating a new account...')
    click.echo(f"email: {email}")
    click.echo(f"password: {password}")
    click.echo(f"device: {device}")

    account = {
        'email': email,
        'plain_text_password': password,
        'device_code_name': device,
        'locale': locale,
        'timezone': timezone,
        'gsfId': None,
        'authSubToken': None,
    }

    if accounts.save(account):
        echoSuccess("Account created...")
        exit(0)

    echoError("Unable to add account due to failure in the Login")
    exit(1)


@cli.command(help="Login to a device with the given Google account email")
@click.option("--device", required=True, help="The device code name, e.g angler. [default: random]")
@click.option("--email", required=True, help="The email for your device Google account")
def login(device, email):
    result = accounts.login_for_device(device, email)

    if 'api' in result and 'account' in result:
        account = result['account']
        api = result['api']

        click.echo(f"device: {account['device_code_name']}")
        click.echo(f"email: {account['email']}")
        click.echo(f"GSFID: {api.gsfId}")
        click.echo(f"TOKEN: {api.authSubToken}")

        echoSuccess(f"Logged-in successfully...")
        exit(0)

    echoError(f"\nFailed login attempt...")
    exit(1)


@cli.command(help="Login to a device with a random Google account email")
@click.option("--device", default=None, help="The device code name, e.g angler. [default: random]")
def login_random(device):
    result = accounts.random_login(device)

    if result == None:
        echoError(f"Failed to find an account for the given device...")
        exit(1)

    if result == False:
        echoError("Failed random login attempt...")
        exit(1)

    if 'api' in result and 'account' in result:
        account = result['account']
        api = result['api']

        click.echo(f"device: {account['device_code_name']}")
        click.echo(f"email: {account['email']}")
        click.echo(f"GSFID: {api.gsfId}")
        click.echo(f"TOKEN: {api.authSubToken}")

        echoSuccess("Randomly logged-in successfully...")
        exit(0)

    echoError("I have no idea about what went wrong!!!")
    exit(1)


@cli.command(help=f"Generates a symmetric key into {ENCRYPTION_KEY_FILE} file to later use to encrypt/decrypt data.")
def generate_encryption_key():
    result = accounts.generate_encryption_key()

    if result == False:
        echoError(f"Failed to generate the encryption key...")
        exit(1)

    if result == None:
        echoWarn(f"Encryption key already exists: {ENCRYPTION_KEY_FILE}")
        exit(0)

    if result == True:
        echoSuccess(f"Encryption key generated into file: {ENCRYPTION_KEY_FILE}")
        exit(0)


@cli.command(help="Encrypts the given string")
@click.option("--text", default=None, help="The string to encrypt")
def encrypt_string(text):
    result = encryption.encrypt_string(text)
    print(result)

@cli.command(help="Decrypts the given string")
@click.option("--text", default=None, help="The string to decrypt")
def decrypt_string(text):
    result = encryption.decrypt_string(text)
    print(result)

@cli.command(help="List all categories in the Google Play store")
def list_categories():
    result = categories.browse()

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'file' in result:
        echoSuccess("List of categories saved to: ../data/categories.json")
        exit(0)

@cli.command(help="List a category rank in the Google Play store")
@click.option("--category-id", required=True, help="The Category ID to list the ranks for, e.g. FINANCE")
def list_ranks(category_id):
    result = categories.list_ranks(category_id)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'file' in result:
        echoSuccess("List of category ranks saved to: ../data/categories-ranks.json")
        exit(0)


@cli.command(help="List the top free in a category by country on the Google Play store")
@click.option("--category-id", required=True, help="The Category ID to list the ranks for, e.g. FINANCE")
@click.option("--country", required=True, help="The country to list the category ranks, e.g. US")
@click.option("--limit", default=200, help="The limit for the number of top free apps. Defaults to 200")
@click.option("--date", default=None, help="The date for the top free apps. Defaults to use todays date.")
def list_top_free(category_id, country, limit, date):
    result = sensortower.list_top_free(category_id, country, date, limit)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'file' in result:
        echoSuccess(f"Top free apps for category {category_id} saved to: {result['file']}")
        exit(0)

@cli.command(help="List a category in the Google Play store")
@click.option("--category-id", required=True, help="The Category ID to list the ranks for, e.g. FINANCE")
def list(category_id):
    result = categories.list(category_id)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'file' in result:
        echoSuccess("List of category ranks saved to: ../data/categories-ranks.json")
        exit(0)

@cli.command(help="Search for a term in the Google Play store")
@click.option("--term", required=True, help="The term to search for, e.g. fintech")
def find(term):
    result = search.lookup(term)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'file' in result:
        echoSuccess(f"Search result saved to: {result['file']}")
        exit(0)

@cli.command(help="Downloads the App APK with a random device and Google account")
@click.option("--app-id", required=True, help="The APP ID to download, e.g. com.example.app")
def download_apk(app_id):
    result = download.downloadApkWithRandomLogin(app_id)

    if 'login_failed' in result:
        echoError(f"Failed to login for device {result['device_code_name']} with email {result['email']}")
        exit(1)

    if 'download_failed' in result:
        echoError(f"Failed to download APK for device {result['device_code_name']} with email {result['email']}")
        exit(1)

    echoSuccess('Downloaded successfully the App APK...')
    exit(0)

@cli.command(help="Downloads the App APK for a specific device and Google account")
@click.option("--app-id", required=True, help="The APP ID to download, e.g. com.example.app")
@click.option("--device", required=True, help="The device code name, e.g angler. [default: random]")
@click.option("--country-code", required=True, help="The country code for the APP category, e.g US")
@click.option("--category-id", required=True, help="The Category ID to download the APKs, e.g. FINANCE")
@click.option("--email", default=None, help="The email for your device Google account")
def download_device_apk(app_id, device, country_code, category_id, email):
    result = download.downloadApkForDevice(app_id, device, country_code, category_id, email)

    if 'error' in result and type(result['error']) is not dict:
        echoError(f"\n---> ERROR: {result['error']}")
        exit(1)

    if 'download_failed' in result and result['login_failed'] == True:
        echoError(f"\n---> Failed to download APK for device {result['metadata']['device_code_name']} with email {result['metadata']['email']}")
        echoError(result['error'])
        exit(1)

    if 'login_failed' in result and result['login_failed'] == True:
        echoError(f"\n--> Failed to login for device {result['metadata']['device_code_name']} with email {result['metadata']['email']}")
        exit(1)

    if 'download_failed' in result and result['download_failed'] == True:
        echoError(f"\n---> Failed to download APK for device {result['metadata']['device_code_name']} with email {result['metadata']['email']}")
        exit(1)


    echoSuccess('\n---> Downloaded successfully the App APK...\n')
    exit(0)

@cli.command(help="Download all Apps APKs for the given category ID.")
@click.option("--category-id", required=True, help="The Category ID to download the APKs, e.g. FINANCE")
def download_category_apks(category_id):
    result = download.dowanloadApksByCategory(category_id)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'progress' in result:
        echoSuccess(f"APKS downloaded to: {result['dir']}")
        click.echo(f"category total: {result['progress']['category_total']}")
        click.echo(f"total downloaded: {result['progress']['total_downloaded']}")
        click.echo(f"total remaining: {result['progress']['total_remaining']}")
        click.echo(f"total download failures: {result['progress']['total_download_failures']}")
        exit(0)

@cli.command(help="Download all Apps APKs for the given category ID and Country Code.")
@click.option("--country-file", required=True, help="The path to the country file")
def download_country_category_apks(country_file):
    result = download.dowanloadApksByCountryCategory(country_file)
    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'progress' in result:
        echoSuccess(f"APKS downloaded to: {result['dir']}")
        click.echo(f"category total: {result['progress']['category_total']}")
        click.echo(f"total downloaded: {result['progress']['total_downloaded']}")
        click.echo(f"total remaining: {result['progress']['total_remaining']}")
        click.echo(f"total download failures: {result['progress']['total_download_failures']}")
        exit(0)

@cli.command(help="Fix already downloaded Apps APKs for the given category ID.")
@click.option("--category-id", required=True, help="The Category ID to fix the downloaded APKs, e.g. FINANCE")
def download_fix_category_apks(category_id):
    result = download.fixDownloadedApksByCategory(category_id)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'progress' in result:
        echoSuccess(f"APKS downloaded to: {result['dir']}")
        click.echo(f"category total: {result['progress']['category_total']}")
        click.echo(f"total downloaded: {result['progress']['total_downloaded']}")
        click.echo(f"total remaining: {result['progress']['total_remaining']}")
        click.echo(f"total download failures: {result['progress']['total_download_failures']}")
        exit(0)

@cli.command(help="Fix top free diff with the already downloaded Apps APKs for a category ID.")
@click.option("--diff-file", required=True, help="The path to the diff file")
@click.option("--email", required=True, help="The email for your device Google account")
@click.option("--retry-failed", default=False, help="Retry the failed downloads")
def download_apks_from_diff(diff_file, email, retry_failed):
    # diff_file = f"../../report/data/diff-200-top-free-GB-finance-2022-10-17.json"

    result = download.downloadApksFromDiff(diff_file, email, retry_failed)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    if 'progress' in result:
        echoSuccess(f"APKS downloaded to: {result['dir']}")
        click.echo(f"category total: {result['progress']['category_total']}")
        click.echo(f"total downloaded: {result['progress']['total_downloaded']}")
        click.echo(f"total remaining: {result['progress']['total_remaining']}")
        click.echo(f"total download failures: {result['progress']['total_download_failures']}")
        exit(0)

@cli.command(help="Validate downloaded APKs by category and country.")
@click.option("--country-file", required=True, help="The path to the country file")
def download_validate_country_category_folder(country_file):
    result = download.validateCountryCategoryFolder(country_file)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    echoSuccess(f"Country APKS dir: {result['dir']}")
    click.echo(f"Folder Total APKS: {result['folder-total-apks']}")
    click.echo(f"Top Free Total APKS: {result['top-free-total-apks']}")
    click.echo(f"Folder Diff: {result['folder-diff']}")
    click.echo(f"Top Free Diff: {result['top-free-diff']}")
    exit(0)

@cli.command(help="Get the details for the given app ID.")
@click.option("--app-id", required=True, help="The app id, e.g. com.example.app")
@click.option("--country-code", required=True, help="The country code for the APP category, e.g US")
def fetch_app_details(app_id, country_code):
    result = download.fetch_app_metadata(app_id, country_code)

    if 'error' in result:
        echoError(result['error'])
        exit(1)

    echoSuccess(f"App metadata fetched successfully...")
    click.echo(f"App details saved to: {result['dir']}")
    exit(0)


@cli.command(help="List all device hardware identifiers")
def devices():
    click.echo(config.getDevicesCodenames())


if __name__ == '__main__':
    cli(obj={})
