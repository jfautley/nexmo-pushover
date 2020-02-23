## Here we import the various modules that are required for this application to
## function.

# Chalice - AWS Lambda/API Gateway integration
# https://github.com/aws/chalice
from chalice import Chalice, Response, BadRequestError

# Chump - Pushover Integration
# https://github.com/karanlyons/chump
from chump import Application

# python-phonenumbers - allows us to convert a phonenumber to a country
# https://github.com/daviddrysdale/python-phonenumbers
import phonenumbers

# Misc. wrappers for additional functionality
from datetime import datetime
from pytz import timezone
import json
import logging
import html
import boto3

# We keep our sensitive information (API keys, etc.) in AWS Systems Manager
# Parameter Store. This means we keep anything security-sensitive out of our
# source control system and away from prying eyes.
# https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html
#
# This variable defines the path for our Pushover API/User keys
SSM_PATH='/pushover/sms'

# Instantiate our Chalice application, switch on uber-logging
app = Chalice(app_name='nexmo')
app.log.setLevel(logging.DEBUG)

# Obtain our Pushover credentials from SSM
# We ask SSM to automatically handle decryption for us, as well.
ssm = boto3.client('ssm')
ssm_params = ssm.get_parameters_by_path(Path=SSM_PATH, WithDecryption=True)

# Convert the response from SSM into a dictionary for easy reference later on
pushover_params = {}
if 'Parameters' in ssm_params and len(ssm_params.get('Parameters')) > 0:
  # We actually have some parameters back from SSM
  for param in ssm_params.get('Parameters'):
    pushover_params[param.get('Name').split('/')[-1]] = param.get('Value')

# Create our Pushover API client, and test we're actually authenticated
# successfully (the API key is valid) and we're trying to route our request to
# a valid user/group key.
pushover = Application(pushover_params['AppKey'])
assert pushover.is_authenticated

user = pushover.get_user(pushover_params['UserKey'])
assert user.is_authenticated

### The real excitement starts here...
# In case anyone hits our API directly, give them a firm but friendly greeting.
@app.route('/')
def index():
    return Response(body='OK', status_code=200)

# We will be accepting SMS from Nexmo at this endpoint.
# The URL you need for your Nexmo dashboard will be output by Chalice deploy -
# add /sms to the end of it to get the complete URL.
# NB: Ensure your Nexmo account is configured with POST-JSON as the HTTP Request type!
#
# Fairly simple here - get our inbound HTTP POSTed object, confirm it has a
# JSON formatted body, and pass this to our process_message() function.
# If someone tries to post something other than JSON, return an error code.
# Finally, return an HTTP/204 resposne to Nexmo to confirm we're handling the message.
@app.route('/sms', methods=['POST'])
def handle_sms():
    if app.current_request.json_body:
        process_message(app.current_request.json_body)
    else:
        return Response(body='Invalid request', status_code=400)

    # Nexmo expects HTTP/204, else it will keep trying to redeliver the message
    return Response(body='Accepted', status_code=204)

# This is a little 'safety net' in case someone tries to send a GET request to
# our /sms endpoint.
@app.route('/sms')
def MethodNotAllowed():
    return Response(body='Unsupported method.', status_code=405)

# This is where we accept the JSON body from Nexmo, and perform the data
# extraction and enrichment, before sending on to Pushover to deliver to our
# handset.
# This process is essentially:
#  1. Dump the whole JSON object received to our debug log so we can see exactly what was received
#  2. Extract the timestamp from the message - we pass this to Pushover so the
#     SMS time and the Pushover message time are the same.
#  3. Lookup the number the SMS was sent to (this is your Nexmo allocated
#     number) from the JSON object, and determine the destination country code.
#     This is used so we can inject the destination country code into the Pushover
#     notification to easily identify the likely purpose of the message.
#  4. Deliver the message to the Pushover API
#
# TODO:
#  - Handle multi-part messages
#  - Don't just blindly assume the message made it to the Pushover API successfully
def process_message(message):
    app.log.debug(message)

    message_timestamp = timezone('UTC').localize(datetime.strptime(message['message-timestamp'], '%Y-%m-%d %H:%M:%S'))

    try:
        sent_to = phonenumbers.parse('+' + message['to'])
        cc = phonenumbers.region_code_for_number(sent_to)
    except phonenumbers.phonenumberutil.NumberParseException:
        sender_info = message['to']
        cc = "UNKNOWN"

    m = user.send_message(title="{} (To: {}/+{})".format(message['msisdn'], cc, message['to']),
                          message="<b>{}: </b>{}".format(cc, html.escape(message['text'])),
                          html=True, timestamp = message_timestamp)

    return True
