from pprint import pprint
import requests
import json
from flask import jsonify
import sys
from auth import get_token
import os
try:
    from flask import Flask
    from flask import request
except ImportError as e:
    print(e)
    print("Looks like 'flask' library is missing.\n"
          "Type 'pip3 install flask' command to install the missing library.")
    sys.exit()

client_id = os.environ.get('CLIENT_ID')
client_secret = os.environ.get('CLIENT_SECRET')
bearer = os.environ.get('BOT_TOKEN')

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": "Bearer " + bearer
}

def send_get(url, payload=None,js=True):

    if payload == None:
        request = requests.get(url, headers=headers)
    else:
        request = requests.get(url, headers=headers, params=payload)
    if js == True:
        request= request.json()
    return request


def send_post(url, data):

    request = requests.post(url, json.dumps(data), headers=headers).json()
    return request


def help_me():

    return "Sure! I can help. Below are the commands that I understand:<br/>" \
           "`Help me` - I will display what I can do.<br/>" \
           "`Hello` - I will display my greeting message<br/>" \
           "`pid` - Provide a product ID and I will reply with End of Life Data.  e.g. *pid C3925-AX/K9*<br/>" \
           "`serial` - Provide a serial and I will reply with Smartnet Coverage and End of Life Data. e.g. *serial FHX75UH03459"\
           "" 
            #add option to send email for feedback.

def greetings():

    return "Hi my name is %s.<br/>" \
           "Type `Help me` to see what I can do.<br/>" % bot_name
  
def get_eoxbyPID(hwPID):
    """returns HW EoX info when providing HWPID"""
    token = get_token(client_id, client_secret)
    url = "https://api.cisco.com/supporttools/eox/rest/5/EOXByProductID/1/" + hwPID
    headers = {
        'content-type': "application/json",
        'authorization': "" + token['token_type'] + " " + token['access_token'],
        'cache-control': "no-cache",
        }

    response = requests.request("GET", url, headers=headers)

    data = json.loads(response.text)
    
    if "EOXError" in data['EOXRecord'][0]:
      return "Are you sure you entered that correctly? "+ data['EOXRecord'][0]["EOXError"]["ErrorDescription"]
    else:
      EoS = data['EOXRecord'][0]["EndOfSaleDate"]["value"]
      EoM = data['EOXRecord'][0]["EndOfSWMaintenanceReleases"]["value"]
      EoSR = data['EOXRecord'][0]["EndOfServiceContractRenewal"]["value"]
      LDoS = data['EOXRecord'][0]["LastDateOfSupport"]["value"]
      BulletinURL = data['EOXRecord'][0]["LinkToProductBulletinURL"]
      MigrationPID = data['EOXRecord'][0]["EOXMigrationDetails"]["MigrationProductId"]
      MigrationURL = data['EOXRecord'][0]["EOXMigrationDetails"]["MigrationProductInfoURL"]
      MigrationStrat = data['EOXRecord'][0]["EOXMigrationDetails"]["MigrationStrategy"]
      BulletinNum = data['EOXRecord'][0]["ProductBulletinNumber"]

      return "**End of Sale Date:** ................... " + EoS +\
      "<br>**End of Service Renewal:** ......" + EoSR +\
      "<br>**Last Day of Support:** ............." + LDoS +\
      "<br>**Migration Product:** [" + MigrationPID + "](" + MigrationURL + ") <br>**URL Bulletin:** [" + BulletinNum + "]("+ BulletinURL +")" 


def get_coveragebySerial(serial):
  """returns coverage data when given a serail... need to add in EoX info too later"""
  token = get_token(client_id, client_secret)
  url = "https://api.cisco.com/sn2info/v2/coverage/summary/serial_numbers/" + serial
  #url = "https://api.cisco.com/sn2info/v2/coverage/summary/serial_numbers/SSI184805DX"
  headers = {
    'Content-Type': "application/json",
    'authorization': "" + token['token_type'] + " " + token['access_token'],
    'cache-control': "no-cache"
    }

  response = requests.request("GET", url, headers=headers)

  data = json.loads(response.text)
  if 'ErrorResponse' in data['serial_numbers'][0].keys():
      return_val = data['serial_numbers'][0]['ErrorResponse']['APIError']['ErrorDescription']
      #print data['serial_numbers'][0]['ErrorResponse']['APIError']['ErrorDescription']
  elif 'serial_numbers' in data.keys():
    
    pid = data['serial_numbers'][0]["base_pid_list"][0]["base_pid"]
    status = data['serial_numbers'][0]["is_covered"]
    serviceLevel = data['serial_numbers'][0]["service_line_descr"]
    endDate = data['serial_numbers'][0]["covered_product_line_end_date"]
    contractNum = data['serial_numbers'][0]["service_contract_number"]  
    #contractNum = "xxxx" + contractNum[5:]
   
    return_val = "**Product ID:** ................. " + pid +\
      "<br>**Coverage Status:** ....... " + status +\
      "<br>**Service Level:** ............. " + serviceLevel +\
      "<br>**Covered End Date:** .... " + endDate +\
      "<br>**Contract Number:** ..... " + contractNum +\
      "<br><br>Find more info at https://ccrc.cisco.com/ccwr/ or https://cway.cisco.com/sncheck/"
  else:
    print "Item not found"
    return_val = "Something went wrong"
    
  return return_val

auth_user_domains = ['@cisco.com', '@marriott.com', '@marriott-sp.com']
  
app = Flask(__name__)
@app.route('/', methods=['GET', 'POST'])
def teams_webhook():
    if request.method == 'POST':
        webhook = request.get_json(silent=True)
        requester = webhook['data']['personEmail']
        requester = requester[ requester.find("@") : ]
        if webhook['data']['personEmail']!= bot_email:
            pprint(webhook)
        if webhook['resource'] == "memberships" and webhook['data']['personEmail'] == bot_email:
            send_post("https://api.ciscospark.com/v1/messages",
                            {
                                "roomId": webhook['data']['roomId'],
                                "markdown": (greetings() +
                                             "**Note This is a group room and you have to call "
                                             "me specifically with `@%s` for me to respond**" % bot_name)
                            }
                            )
        msg = None
        if "@webex.bot" not in webhook['data']['personEmail']:
          if requester in auth_user_domains:
            result = send_get(
                'https://api.ciscospark.com/v1/messages/{0}'.format(webhook['data']['id']))
            in_message = result.get('text', '').lower()
            in_message = in_message.replace(bot_name.lower() + " ", '')
            if in_message.startswith('help'):
                msg = help_me()
            elif in_message.startswith('hello'):
                msg = greetings()
            elif in_message.startswith('pid'):
              if len(in_message) == 3 :
                msg = "Please enter a Product ID. e.g. *pid C3925-AX/K9*"
              else:
                pid = in_message.split('pid ')[1]
                msg = get_eoxbyPID(pid)
            elif in_message.startswith('serial'):
              if len(in_message) <= 10 :
                msg = "Please enter a serial number."
              else:
                serial = in_message.split('serial ')[1]
                msg = get_coveragebySerial(serial)
            else:
                msg = "Sorry, but I did not understand your request. Type `Help me` to see what I can do"
          else:
              msg = "User not Authorized"
          if msg != None:
                send_post("https://api.ciscospark.com/v1/messages",
                                {"roomId": webhook['data']['roomId'], "markdown": msg})

        return "true"

    elif request.method == 'GET':
        message = "<center><img src=\"https://cdn-images-1.medium.com/max/800/1*wrYQF1qZ3GePyrVn-Sp0UQ.png\" alt=\"Webex Teams Bot\" style=\"width:256; height:256;\"</center>" \
                  "<center><h2><b>Congratulations! Your <i style=\"color:#ff8000;\">%s</i> bot is up and running.</b></h2></center>" \
                  "<center><b><i>Don't forget to create Webhooks to start receiving events from Webex Teams!</i></b></center>" % bot_name
        return message

def main():
    global bot_email, bot_name
    if len(bearer) != 0:
        test_auth = send_get("https://api.ciscospark.com/v1/people/me", js=False)
        if test_auth.status_code == 401:
            print("Looks like the provided access token is not correct.\n"
                  "Please review it and make sure it belongs to your bot account.\n"
                  "Do not worry if you have lost the access token. "
                  "You can always go to https://developer.webex.com/my-apps "
                  "and generate a new access token.")
            sys.exit()
        if test_auth.status_code == 200:
            test_auth = test_auth.json()
            bot_name = test_auth.get("displayName","")
            bot_email = test_auth.get("emails","")[0]
    else:
        print("'bearer' variable is empty! \n"
              "Please populate it with bot's access token and run the script again.\n"
              "Do not worry if you have lost the access token. "
              "You can always go to https://developer.webex.com/my-apps "
              "and generate a new access token.")
        sys.exit()

    if "@webex.bot" not in bot_email:
        print("You have provided an access token which does not relate to a Bot Account.\n"
              "Please change for a Bot Account access token, view it and make sure it belongs to your bot account.\n"
              "Do not worry if you have lost the access token. "
              "You can always go to https://developer.webex.com/my-apps "
              "and generate a new access token for your Bot.")
        sys.exit()
    else:
        #app.run(host='localhost', port=8080)
        app.run()

if __name__ == "__main__":
    main()
