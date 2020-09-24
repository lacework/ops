import credstash
from os import environ

def str_to_bool(string):
	if isinstance(string,str):
		if string.lower() in ('true', 'false'):
		   return string.lower() == 'true'

	return string

if environ.get("expire_age") == None:
	exit("Error: missing env variable related to {}".format(key))

# all this will connect to the k8s config map via environment variables
config = {
	"dump_metric_to_console": str_to_bool(environ.get("dump_metric_to_console")),
	"slack": str_to_bool(environ.get("send_slack")),
	"disable_key": str_to_bool(environ.get("disable_key")),
	"jira_ticket": str_to_bool(environ.get("create_jira")),
	"expire_age": int(environ.get("expire_age")),
	"jira_server_address": environ.get("jira_server_address"),
	"atlassian_api_email":credstash.getSecret(environ.get("credstash_keyname_atlassian_api_email"), region=environ.get("credstash_region"), profile_name=environ.get("credstash_aws_profile_name")),
	"jira_project_key":environ.get("jira_project_key"),
	"atlassian_api_token":credstash.getSecret(environ.get("credstash_keyname_atlassian_api_token"), region=environ.get("credstash_region"), profile_name=environ.get("credstash_aws_profile_name")),
	"slack_api_token":credstash.getSecret(environ.get("credstash_keyname_slack_api_token"), region=environ.get("credstash_region"), profile_name=environ.get("credstash_aws_profile_name")),
	"aws_dynamodb_profile_name": environ.get("aws_dynamodb_profile_name"),
	"aws_dynamodb_region": environ.get("aws_dynamodb_region")
}

# ensure all env variables are set
for key, value in config.items():
	if value == None:
		exit("Error: missing env variable related to {}".format(key))
