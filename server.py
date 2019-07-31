from pprint import pprint
import requests
import json
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
           "`eox` - Provide a product ID and I will reply with End of Life Data.  e.g. *eox C3925-AX/K9*<br/>"


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

      return "**End of Sale:** " + EoS + "<br>**End of Service Renewal:** " + EoSR + "<br>**Last Day of Support:** " + LDoS + "<br>**Migration Product:** [" + MigrationPID + "](" + MigrationURL + ") <br>**URL Bulletin:** [" + BulletinNum + "]("+ BulletinURL +")" 

app = Flask(__name__)
@app.route('/', methods=['GET', 'POST'])
def teams_webhook():
    if request.method == 'POST':
        webhook = request.get_json(silent=True)
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
            result = send_get(
                'https://api.ciscospark.com/v1/messages/{0}'.format(webhook['data']['id']))
            in_message = result.get('text', '').lower()
            in_message = in_message.replace(bot_name.lower() + " ", '')
            if in_message.startswith('help'):
                msg = help_me()
            elif in_message.startswith('hello'):
                msg = greetings()
            elif in_message.startswith('eox'):
              if len(in_message) == 3 :
                msg = "Please enter a Product ID. e.g. *eox C3925-AX/K9*"
              else:
                pid = in_message.split('eox ')[1]
                msg = get_eoxbyPID(pid)
            else:
                msg = "Sorry, but I did not understand your request. Type `Help me` to see what I can do"
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
