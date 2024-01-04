"""
 CISCO DataMiner Support Libary

 Auther:  Donnie Savage, 2022
 Derived work from: Steve Hartman, Cisco Systems, INc

"""
import sys
import os
import time
import math
import re
import logging
import shutil
import requests

from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
'''
    Data need by function - must be set by importer
=======================================================================
'''
token = None				# Used for Making API Requests
tokenStartTime = 0			# Tracks time the token was created
tokenUrl = None				# Full path of oAuth endpoint: <protocolscheme><host><path>

authScope = None			# # Specify the access level or permissions. Default is None
grantType = None			# Grant Type being used - defalt: client_credentials
clientId = None				# Used to store the Client ID
clientSecret = None			# Used to store the Client Secret
grantType = "client_credentials"	# Grant Type being used - defalt: client_credentials
cacheControl = "no-cache"		# By default, dont cache

'''
Begin defining functions neeed to support PXC and SNTC DataMiners
=======================================================================
'''
# Function to generate or clear output and temp folders for use.
def storage(csv_dir=None, json_dir=None, temp_dir=None):

    # Output CSV
    if csv_dir:
        print("Saving data in CSV format")
        if os.path.isdir(csv_dir):
            shutil.rmtree(csv_dir)
            os.mkdir(csv_dir)
        else:
            os.mkdir(csv_dir)

    # Output JSON
    if json_dir:
        print("Saving data in JSON format")
        if os.path.isdir(json_dir):
            shutil.rmtree(json_dir)
            os.mkdir(json_dir)
        else:
            os.mkdir(json_dir)

    # Temp dir for download data
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir)
        os.mkdir(temp_dir)
    else:
        os.mkdir(temp_dir)

#
# Fix file name to be Windows compatable
def filename(json_filename):
    # Define a pattern to match characters not allowed in Windows filenames
    invalid_char_pattern = re.compile(r'[<>:"/\\|?* &\x00-\x1F]+')

    # Replace invalid characters with an underscore
    name = invalid_char_pattern.sub('_', json_filename)
    return name

#
# JSON Naming Convention: <page_name>_Page_{page}.json
def pagename(page_name, page):
    page = page_name + "_Page_" + str(page) + ".json"
    return filename(page)

#
# JSON Naming Convention: <page_name>_Page_{page}_of_{total}.json
def pageofname(page_name, page, total):
    page = page_name + "_Page_" + str(page) + "_of_" + str(total) + ".json"
    return filename(page)

#
# common error handling
def api_exception(e):
    if hasattr(e, 'request') and e.request:
        # Logging.Info details of the request that caused the exception
        logging.error(f"{e.request.method} Request URL: {e.request.url}")
        logging.debug(f"Request Headers{e.request.headers}")
        logging.debug(f"Request Body:{e.request.body}")

    if hasattr(e, 'response') and e.response:
        logging.error(f"Response Status Code:{e.response.status_code}")
        logging.debug(f"Response Headers:{e.response.headers}")
        logging.debug(f"Response Content:{e.response.text}")

#
# handle the send
def api_header():
    headers = {'Authorization': f'Bearer {token}'}
    return headers
#
# handle the send
def api_send(method, url, headers, **kwargs):
    return requests.request(method, url, headers=headers, verify=True, timeout=10, **kwargs)
            
#
# function to contain the error logic for any API request call
def api_request(method, url, headers, **kwargs):
    global token
    firstTime = True
    tries = 1
    response = []

    # Include all HTTP error codes (4xx and 5xx) in status_forcelist
    all_error_codes = [code for code in range(400, 600)]

    # Create a custom Retry object with max retries
    retry_strategy = Retry(
        total=30,		# Maximum number of retries
        backoff_factor=0.1,	# Factor to apply between retry attempts
        status_forcelist=all_error_codes,
    )
    
    # Create a custom HTTPAdapter with the Retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)

    # Create a Session and mount the custom adapter
    session = requests.Session()
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    # Rather Chatty ...
    logging.debug(f"{method}: URL:{url}")

    while True:
        try:
            response = api_send(method, url, headers, **kwargs)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
            if tries >= 2:
                logging.info("\nSuccess on retry! \nContinuing.")
            break
        except requests.exceptions.ReadTimeout as e:
            logging.error(f"ReadTimeoutError: Method:{method} Attempt:{tries}")
            api_exception(e)
        except requests.exceptions.Timeout as e:
            logging.error(f"TimeoutError: Method:{method} Attempt:{tries}")
            api_exception(e)
        except ConnectionError as e:
            logging.error(f"ConnectionError: Method:{method} Attempt:{tries}")
            api_exception(e)
        except requests.exceptions.RequestException as e:
            logging.error(f"RequestException: Method:{method} Attempt:{tries}")
            api_exception(e)
        except Exception as e:
            logging.error(f"Unexpected error: Method:{method} Attempt:{tries}")
            api_exception(e)
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTPError: Method:{method} Attempt:{tries}")
            api_exception(e)
            if response.status_code >= 500:
                logging.info("Server Error: Retrying API call")
            elif response.status_code == 401 or response.status_code == 403:
                if firstTime:
                    # Unauthorized? lets see if a new token will help.. but only try once
                    token()
                    firstTiome = FALSE
            elif response.status_code >= 400:
                logging.error("Client Error: Aborting API call")
                response = []
                break
        finally:
            tries += 1
            token_refresh()		# check to see if token refresh is needed
            time.sleep(2)		# 2 seconds delay before the next attempt

        #End Try
    #End While
    return response

# If needed, refresh the token so it does not expire
def token_refresh():
    checkTime = time.time()
    tokenTime = math.ceil(int(checkTime - tokenStartTime) / 60)
    if tokenTime > 99:
        logging.info(f"Token Time is :{tokenTime} minutes, Refreshing")
        token()
    else:
        logging.debug(f"Token time is :{tokenTime} minutes")


# Function to get a valid API token from PX Cloud
def token():
    global token
    global tokenStartTime

    print("\nGetting API Access Token")
    url = (tokenUrl
           + "?grant_type="    + grantType
           + "&client_id="     + clientId
           + "&client_secret=" + clientSecret
           + "&cache-control=" + cacheControl
           + "&scope="         + authScope
    )
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    response = requests.request("POST", url, headers=headers)
    if response:
        reply = response.json()
        token = reply.get("access_token", None)
    else:
        token = None
        
    tokenStartTime = time.time()
    logging.debug(f"API Token:{token}")
    if token:
        print("Done!")
        print("====================\n\n")

    else: 
        logging.critical("Unable to retrieve a valid token\n"
              "Check config.ini and ensure your API Keys and if your using the Sandbox or Production for accuracy")
        logging.critical(f"Client ID: {pxc_client_id}")
        logging.critical(f"Client Secret: {pxc_client_secret}")
        logging.critical(f"Production APIs? : {useProductionURL}")
        sys.exit()



