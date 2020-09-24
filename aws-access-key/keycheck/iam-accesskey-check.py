#!/usr/bin/env python3

from pprint import pprint

import boto3
import datetime
import logging
from slack_ID_mapping import mapping
from config_parser import config
import requests
from jira.client import JIRA
import credstash
import os
import sys

class access_key_alert:
    def __init__(self):
        if len(sys.argv) != 2:
            exit("Error: please enter exactly 1 CLI argument - AWS profile name")
        # boto3 client for aws - we take the account alias from telegraf's first CLI argument
        self.iam = boto3.session.Session(profile_name=sys.argv[1]).client('iam')
        self.dynamo_client = boto3.session.Session(profile_name=config["aws_dynamodb_profile_name"], region_name=config["aws_dynamodb_region"]).client("dynamodb")

        # check if env variable is logging info level
        if os.environ.get("LOGGING_LEVEL") == "INFO":
            logging.basicConfig(level=logging.INFO)
        else:
            # log the config
            logging.basicConfig(level=logging.WARNING)

        if config.get("expire_age") == '' or config.get("expire_age") == None: config["expire_age"] = 180

        logging.info(" Program configs are: Expire_age={} Slack={}, dump_metric_to_console={}, Jira={}, Disabling_expired_keys={}".format(
            config["expire_age"], config["slack"], config["dump_metric_to_console"], config["jira_ticket"], config["disable_key"]))

        self.accountAlias = sys.argv[1]

        # fetching api keys from credstash
        self.ATLASSIAN_API_TOKEN = config["atlassian_api_token"]
        self.SLACK_API_TOKEN = config["slack_api_token"] 

        self.key_rotation_string = """ 
To rotate your key you must:

You can rotate your access key using the `awscli`:

`aws iam create-access-key --user-name <user_name>`

`aws iam update-access-key --access-key-id <old_key_id> --status Inactive --user-name <user_name>`

`aws iam delete-access-key --access-key-id <old_key_id> --user-name <user_name>`

For more information visit aws.amazon.com/blogs/security/how-to-rotate-access-keys-for-iam-users/
        """

        self.run()


    def run(self):

        logging.info("Account Alias is: {}".format(self.accountAlias))

        # 1000 is the maxiumum number of IAM users that an AWS profile can hold. This way, we are guarenteed to get all users.
        iam_users_obj = self.iam.list_users(MaxItems=1000) 
        if iam_users_obj["IsTruncated"]:
            logging.info(" Some users will be missing, call to IAM.listusers has been truncated")
        
        # fetching all the AWS users which have IAM
        for user in iam_users_obj['Users']: 
            UserName = user['UserName'] # fetching the username so we can pass it into the IAM api

            # fetching the most recent access key so we can check how old it is
            AccessKeys = self.iam.list_access_keys(UserName=UserName)["AccessKeyMetadata"]

            for key in AccessKeys: # 2 keys to check
                self.jira_ticket_url = ""

                # remove the time zone offset and the age of the access key
                user_access_key_date = key['CreateDate'].replace(tzinfo=None)
                age_in_days = (datetime.datetime.now() - user_access_key_date).days

                expiry_date = datetime.datetime.now() + datetime.timedelta(days=config["expire_age"]-age_in_days)
                expiry_date = expiry_date.strftime("%m/%d/%Y")

                logging.info(" age for {}'s key with ID {} is {} days old".format(UserName, key["AccessKeyId"], age_in_days))

                self.jira_exists = self.does_jira_exist(key_id=key["AccessKeyId"]) # if a jira ticket exsists, then we can update the global variable

                if age_in_days >= config["expire_age"] - 15:

                    if (config['jira_ticket']):
                        if self.jira_exists: # if we find a jira ticket for this key id, then we don't want to create a new jira
                            logging.info(" Jira ticket already exsists for {} with key ID {}. {}".format(UserName, key["AccessKeyId"], self.jira_ticket_url))
                        else:
                            # we want to create a jira ticket for the users which have expired access keys, only if there already does not exsist one for this key
                            self.create_jira_ticket(user_name=UserName, key_id=key["AccessKeyId"], expiry_date=expiry_date)

                    if (config['slack'] and self.last_message_age(key_id=key["AccessKeyId"]) > 24):
                        # if the access key age is either expired or nearly expired, we want to ping the users on slack
                        self.send_slack_message(user_name=UserName, key_age=age_in_days, key_id=key["AccessKeyId"], expiry_date=expiry_date)

                # conditions for the users with expired access keys
                if age_in_days >= config["expire_age"]:
                    if (config['disable_key']):
                        # expired access keys need to be disabled, only the access keys which are in the slackID mapping (we don't want to touch prod keys)
                        if (UserName in mapping): self.disable_access_key(user_name=UserName, key_id=key["AccessKeyId"])

                if (config['dump_metric_to_console']):
                    # we want to dump a metric to console for telegraf regardless of if the user's access key is expiring or not
                    self.dump_metric_to_console(user_name=UserName, key_age=age_in_days, key_id=key["AccessKeyId"])

    def send_slack_message(self, user_name, key_age, key_id, expiry_date):

        url = "https://slack.com/api/chat.postMessage"
        headers = {'Authorization': 'Bearer {}'.format(self.SLACK_API_TOKEN)}
        logging.info(" sending slack message for {}'s access key".format(user_name))

        # If a user does not have a mapping in the slack channel, then we dump it into the dedicated channel
        if mapping.get(user_name) == None:
            return
        # for the case in which the AWS access key is expired
        elif (key_age >= config["expire_age"]):
            payload = {
            "text":"Your AWS Access Key with ID ending in ******{}, in `{}` is {} day(s) old. It will be expired as of {}. For Account Alias `{}` \n {} \n {}".format(
                key_id[-5:], user_name, key_age, expiry_date, self.accountAlias, self.key_rotation_message(user_name, key_id), self.jira_ticket_url),
            'as_user':"true",
            "channel": mapping[user_name]
            }
        # for the case which the keys are 15 days away from expiring
        else:
            payload = {
            "text":"Your AWS Access Key with ID ending in ******{}, in `{}` is {} day(s) old. It will be expired as of {}. For Account Alias `{}` \n {}".format(
                key_id[-5:], user_name, key_age, expiry_date, self.accountAlias, self.jira_ticket_url),
            'as_user':"true",
            "channel": mapping[user_name]
            }

        # api request to send the slack message
        try:
            requests.post(url=url, headers=headers, data=payload)
        except requests.exceptions.RequestException as err: # catch the error and log it
            logging.info(" Error: {}".format(err))

        # after we send a slack message, we want to update the dynamodb entry for the last time we sent a message for this particular aws-access-key
        ping_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        item = {
            "iam_access_key_id": {"S":key_id},
            "last_pinged_time": {"S":ping_time}
        }
        # we first want to make sure that a table exsists
        if self.dynamo_client.list_tables().get('TableNames') == None or ("iam_access_key_alert" not in self.dynamo_client.list_tables()['TableNames']):
            # create a table if it does not exsit
            self.dynamo_client.create_table(
                AttributeDefinitions=[
                {
                    "AttributeName": "iam_access_key_id",
                    "AttributeType": "S"
                },
                {
                    "AttributeName": "last_pinged_time",
                    "AttributeType": "S"
                }
            ],
                TableName="iam_access_key_alert",
                KeySchema=[
            {
                "AttributeName": "iam_access_key_id",
                "KeyType": "HASH"
            },
            {
                "AttributeName": "last_pinged_time",
                "KeyType": "RANGE"
            }])


        self.dynamo_client.update_item(TableName="iam_access_key_alert", Key=item)

    # returns the age in hours of the last time we pinged a user regarding their expiring access key given the key ID
    def last_message_age(self, key_id):
        results = self.dynamo_client.query(TableName="iam_access_key_alert", KeyConditionExpression='iam_access_key_id = :key_id',
            ExpressionAttributeValues={
                ':key_id': {'S': key_id}
                }
        ).get("Items")

        # if we cannot find the last time we pinged a user with this key ID, we return 30 hours to ensure that the slack message will send
        if results == []:
            return 30

        last_messaged_time = results[-1]["last_pinged_time"]["S"] # fetch the time as a string
        message_age = (datetime.datetime.now() - datetime.datetime.strptime(last_messaged_time, '%Y-%m-%d %H:%M:%S')).total_seconds()//3600 # convert the datetime obj to hours

        return message_age

    def dump_metric_to_console(self, user_name, key_age, key_id):
        # evaluate the status of the key
        if key_age < config["expire_age"] - 15: status = "ok"
        elif key_age < config["expire_age"]: status = "expiring"
        else: status = "disabled"

        # additionally, we need to dump the JSON of the metrics so that Telegraf can parse STDOUT
        influx_metric = 'iam,name={},key={},status={},accountAlias={} age={}'.format(user_name, key_id[-5:], status, self.accountAlias, key_age)
        print(influx_metric)

    def create_jira_ticket(self, user_name, key_id, expiry_date):
        # create jira ticket for key rotation
        ticket_text = "Rotate AWS access key ****{} from AWS profile {}".format(key_id[-5:], user_name)
        payload = {
                "fields": {
                    "project": {
                        "key": config["jira_project_key"]
                    },
                    "summary": "AWS Access key is soon to expire - {}".format(user_name),
                    "description": "AWS Access Key must be rotated for {} with Key ID ending in ****{}. This key is set to expire on {}. The AccountAlias is {} \n {}".format(user_name, key_id[-5:], expiry_date, self.accountAlias, self.key_rotation_string),

                    "issuetype": {
                        "name": "Story"
                    },
                    "labels": [
                        "AWS-User-Key-Rotation"
                    ]
                }
        }

        header = {
            'Content-type': 'application/json',
            'Accept-type': 'application/json'
            }

        url = "{}/rest/api/2/issue/".format(config["jira_server_address"]) # api endpoint to create jira tickets

        # create an instance of the API request
        jira_ticket = requests.request("POST", url=url, json=payload, headers=header, auth=(config["atlassian_api_email"], self.ATLASSIAN_API_TOKEN))

        # fetch the ticket URL and log it to the console, we can also include this in the slack message
        if (jira_ticket.ok == True):
            jira_ticket = jira_ticket.json()
            self.jira_ticket_url = '{}/browse/'.format(config["jira_server_address"]) + jira_ticket['key']
            logging.info(" Jira ticket created for user {} with Key ID {}: {}".format(user_name, key_id, self.jira_ticket_url))

    def key_rotation_message(self, user_name, key_id):
        return """ 
    To rotate your key you must:

    You can rotate your access key using the `awscli` shown below. This is what your key rotation would look like:

    `aws iam create-access-key --user-name {}`

    `aws iam update-access-key --access-key-id {} --status Inactive --user-name {}`

    `aws iam delete-access-key --access-key-id {} --user-name {}`

    For more information visit aws.amazon.com/blogs/security/how-to-rotate-access-keys-for-iam-users/
            """.format(user_name, key_id, user_name, key_id, user_name)

    def does_jira_exist(self, key_id):
        # we check for if a jira already exsists for this access key - we don't want to spam the users

        jira_options={'server': config["jira_server_address"]}
        jira_instance=JIRA(options=jira_options,basic_auth=(config["atlassian_api_email"],self.ATLASSIAN_API_TOKEN)) # using the jira sdk for python

        jql_query = 'status not in (Closed, Cancelled,  Resolved, "In Progress") and description~"{}" and labels=AWS-User-Key-Rotation'.format(key_id[-5:])

        issues_in_OPS = jira_instance.search_issues(jql_str=jql_query, maxResults=5) # query looks for any tickets that have this access key ID in it and are open

        # if we find a ticket regarding this expiring key id, then we change the global jira ticket url, otherwise we return false
        if issues_in_OPS == []: return False
        else:
            self.jira_ticket_url = "{}/browse/{}".format(config["jira_server_address"], issues_in_OPS[0])
            return True

    def disable_access_key(self, user_name, key_id):
        logging.info(" Disabling access key with ID: {} for user {}".format(key_id, user_name))

        # the AWS api to disable access keys
        self.iam.update_access_key(UserName=user_name, AccessKeyId=key_id, Status='Inactive')

if __name__ == "__main__":
    access_key_alert()
