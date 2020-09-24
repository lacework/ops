<a href="https://lacework.com"><img src="https://techally-content.s3-us-west-1.amazonaws.com/public-content/lacework_logo_full.png" width="600"></a>

# IAM Access Key Monitoring @ Lacework

## Introduction

See the blog post [Keeping an eye on IAM Keys. No more stale keys!](https://engineering.lacework.net/?p=5601)

At Lacework, we follow many recommended best practices including [regularly rotating AWS credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#rotate-credentials). 

Since it's harder to remind users with programatic AWS access to rotate or change passwords (or not as easy as it is for an interactive login), we automated this.

### Goals

* Ensure that old or stale keys are disabled
* Notify users in Slack about keys nearing expiration
* File Jiras against users to rotate keys - work doesn't happen without a Jira *amiright*?
* Send relevant telemetry to our monitoring platform to alert on expiring/expired keys (and track that as it relates to service health)

### How it works
Lacework uses [Wavefront](https://www.wavefront.com/) as it's observability/monitoring platform and to simplify this code and make it more consumable, the Python script is ran from a [Telegraf Exec Input Plugin](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/exec). You can adjust the output plugin to suite your environment.

The Python script does the following in sequential order:

* Scans all IAM users for an AWS profile (passed in as an input on the command line)
* For each IAM user, checks age of all their IAM Access Keys and labels each key as either "ok", "expiring", or "expired"
* If key is "expiring" or "expired, it files a Jira and notifies the user through Slack (if not done already)
* If key is "expired", then disable the key in AWS
* Outputs to STDOUT InfluxDB line formatted data for Telegraf to scrape - for all keys

_Note_: A key is said to be "expiring" if it is within 15 days of reaching its expiry age. The expiry age is set to 180 days by default, however, this of course can be changed.

Fundementally, if a key is labelled as "expired" or "expiring", then the system checks for 2 things:
- When was the last time we pinged the key's owner on slack telling them to rotate this access key? 
- Has there already been a jira issue filled for rotating this access key?

The code is smart enough to file only one Jira but will nag the user on Slack at least once every 24 hours.

Because we :heart: our users, Slack notices include directions on how to programatically rotate keys:

> To rotate your key, run the following CLI commands:
> 
> ```aws iam create-access-key --user-name <user_name>```
> ```aws iam update-access-key --access-key-id <OLD ACCESS KEY> --status Inactive --user-name <user_name>```
>
> For more information visit https://aws.amazon.com/blogs/security/how-to-rotate-access-keys-for-iam-users/

Here's what a sample slack message looks like:
<img src="https://user-images.githubusercontent.com/55153449/94055879-84f36500-fdab-11ea-9552-0c1d3dd18436.png">

The code uses a DynamoDB table to track state, mostly to avoid spamming users with multiple Jiras and Slack messages. It keeps track of the last time a user was messaged on slack by access key. By default, this uses the table `iam-access-key-alert` and will automaticaly create such a table if it does not exist.

_Note_: By default, users are only ping'd on Slack if they have not been ping'd in the last 24 hours _and_ the configuration parameter `send_slack` is `True`. Likewise, Jira issues will only be filed if there isn't a prior open Jira _and_ `create_jira` is `True`.

See below for other configuration options.

### Observabilty & Monitoring
We run this through Telegraf and the output is InfluxDB formatted by default. You can adjust the output plugin for your environment.

As shown from the example below, the metrics dumped include the last 5 digits of the access key, the account alias, and the key age. Note that metrics for ALL keys will be dumped into STDOUT, regardless of their status.

Example output (influxDB format):
```
iam,name=dev_afiunel,key=VHXVM,status=disabled,accountAlias=lacework-devtest age=197
```

From here, Telegraf scrapes STDOUT and handles pushing these to your monitoring platform with `outputs.<plugin>`

## Getting Started

Even though the code runs out of Telegraf, it can run standalone. You could easily adapt it to run out of `cron` or even as a scheduled container job and skip the Telegraf telemetry output.

The code uses standard `boto3` conventions. You can specify the AWS profile name anyway that `boto3` expects.

```   
/opt/keycheck/iam-accesskey-check.py AWS_PROFILE
```

### The code

You'll find the following directories:

* `aws`: sample "`~/.aws/config`", used for `boto3`-based authentication
* `wavefront`: a Wavefront dashboard, in JSON
* `keycheck`: the actual code
* `k8s-templates`: Kubernetes templates

### Slack IDs

Within `keycheck` you'll find a `slack_ID_mapping.py` file. You will need to fill this in. Despite Slack having an API which gives you Slack-ID from a user's email, there is no way of obtaining someone's Slack-ID from IAM. The IAM role for a user doesn’t have any metadata associated.

Instructions on how to fill in the slack ID's are in the `slack_ID_mapping.py` file. Here is an example:
```
mapping = {
       "IAM_user_id1":"slack_id1",
       "IAM_user_id2":"slack_id2",
       "IAM_user_id3":"slack_id3"
   }
```


### Dependencies
The code uses several things where some prior knowledge may be helpful. Directions are terse on building the container and running it either locally or within Kubernetes (though some hints are provided).

* Docker
* Telegaf
* AWS IAM roles & permissions
* AWS DynamoDB
* Kubernetes
* Boto3
* [`credstash`](https://github.com/fugue/credstash): used for lightweight, secure credential storage

**Store these in `credstash`:**

* Slack API token. Create a new app and token [here](https://api.slack.com/apps).
* Atlassian API token (see [here to generate your token](https://confluence.atlassian.com/cloud/api-tokens-938839638.html ))
* Email associated with the Atlassian API token

You will deposit the keynames of these into your config (outlined in the configuration parameters)

## Running the code

### Configuring AWS access
The code makes use of standard `boto` syntax for access.

`aws/config` is a sample "`~/.aws/config`" file that you can use for inspiration. You'll need to customize this for your environment.

In Lacework-land, we are making use of EC2 Instance Roles for cross-account IAM read access. YMMV.

We use a Kubernetes secrest object to mount the `~/.aws/config` file into the container, refer to the "Running in Kubernetes section bellow"

### Configuring `telegraf.conf`

Your `telegraf.conf` is responsible for 3 things:
- Running the script with `inputs.exec`
- Scraping STDOUT for metrics
- Sending telemetry to your monitoring platform with `outputs.<output_plugin>`

At Lacework, we use `outputs.wavefront`.You'll need to update the output plugin for your environment and update the exec input plugin. Please refer to the sample `telegraf.conf` in this repo, in addition to these examples: https://github.com/influxdata/telegraf/tree/master/plugins/outputs

As noted elsewhere, `iam-accesskey-check` is falled with the AWS profile as the single command line argument. You will only need to change the "AWS_PROFILE" from the `[[inputs.exec]]` section.
The syntax is simliar to:

```
[[inputs.exec]]
 commands = [
   "/opt/keycheck/iam-accesskey-check.py AWS_PROFILE",
   ]
```

For more information on this plugin, refer to https://github.com/influxdata/telegraf/tree/master/plugins/inputs/exec 

By default, our telegraf has a `timeout` of `120s`. This is because for our AWS profile with the largest number of users, it takes approximately 80 seconds for the script to run. Depending on the number of users in your AWS profiles, you may want to increase this.

Telegraf logs are a good place to keep an eye out on the status of the `input` and `output` plugins

To configure the `[agent]` section, and more instruction on how to build a `telegraf.conf`, please refer to https://docs.influxdata.com/telegraf/v1.15/administration/configuration/.

### Configuration parameters
#### Basics

If you run this locally or outside of Kubernetes, you'll want to set these variables in `env_setup.sh` and `source env_setup.sh`.

If you run this in Kubernetes, you'll want to update the ConfigMap with these variables. We've provided examples in our `k8s-templates` folder

| Variable                | Type             | Purpose                                                                 |
|-------------------------|------------------|-------------------------------------------------------------------------|
| `send_slack`            | Boolean          | Toggles pinging users on slack                                          |
| `create_jira`           | Boolean          | Toggles creating a Jira issue                                           |
| `dump_metric_to_console`| Boolean          | Toggles sending metrics to STDOUT in InfluxDB format                    |
| `disable_key`           | Boolean          | Toggles automaticaly disabling expired AWS IAM keys                     |
| `expire_age`            | Numeric          | The value used to define an expired key. Defaults to 180 days.          |
| `jira_server_address`   | Text             | Jira server URL                                                         |
| `jira_project_key`      | Text             | Jira Project Key                                                        |

The code also depends on `credstash` for credential secrets. These are the names of the key in `credstash`:

| `crestash` key                             | Value
|--------------------------------------------|-------------------------------------------------------------------------|
| `credstash_aws_profile_name`               | AWS Profile where `credstash` credentials are stored                    |
| `credstash_keyname_atlassian_api_email`    | Key containing the email associated with your Atlassian API             |
| `credstash_keyname_atlassian_api_token`    | Key containing Atlassian API token                                      |
| `credstash_keyname_slack_api_token`        | Key containing Slack API token                                          |
| `aws_dynamodb_profile_name`                | Key containing AWS Profile where DynamoDB table is.                     |


Each of these variables needs to be a string (wrap "" around them). Examples: `expire_age="125"`, `send_slack="True"`

### Building the container

You can build this container with the following (make sure you're in the correct dir with this Dockerfile):

```
$ docker build -t lacework/aws-access-key .
```

### Running in Kubernetes

You can use the files in `k8s-templates` for inspiration and customize for your environment.

You will need to fill in the `configmap.yaml` with the configurations above, the template file will have all the parameters. Refer to https://kubernetes.io/docs/concepts/configuration/configmap/ for more information.

We decided to mount the `telegraf.conf` and AWS `config` files as kubernetes secrets. Refer to https://kubernetes.io/docs/concepts/configuration/secret/ for more info on this.

The `pod.yaml` handles deploying the pod itself which will host the program, pulling the docker image from the respective docker repo.

For more and better examples refer to https://kubernetes.io/blog/2019/07/23/get-started-with-kubernetes-using-python/ and https://kubernetes.io/docs/concepts/workloads/pods/

When you've build these 3 files, run `kubectl apply -f <this_repo>/k8s-templates` and it will apply all 3 yamls.

## Wavefront
We use [Wavefront](https://www.wavefront.com/) as our time-series metrics platform. The sample dashboard should give you ideas for your own dashboard (or you can import directly to Wavefront).

![](https://engineering.lacework.net/wp-content/uploads/2020/09/iam-key-dashboard.png)

## Reporting Issues

Issues can be reported by using [GitHub Issues](https://github.com/lacework/ops/issues).

## License and Copyright
Copyright 2020, Lacework Inc.

```
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
