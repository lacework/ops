<a href="https://lacework.com"><img src="https://techally-content.s3-us-west-1.amazonaws.com/public-content/lacework_logo_full.png" width="600"></a>

# IAM Access Key Monitoring @ Lacework

## Introduction

See the blog post [Keeping an eye on IAM Keys. No more stale keys!](https://engineering.lacework.net/?p=5601)

At Lacework, we follow many recommended best practices including [regularly rotating AWS credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#rotate-credentials). 

Since it's harder to remind users with programatic AWS access to rotate or change passwords (or not as easy as it is for an interactive login), we automated this.

### Goals

* ensure that old or stale keys are disabled
* notify users in Slack about keys nearing expiration
* file Jiras against users to rotate keys - work doesn't happen without a Jira *amiright*?
* send relevant telemetry to our monitoring platform to alert on expiring/expired keys (and track that as it relates to service health)

### How it works
Lacework uses [Wavefront](https://www.wavefront.com/) as it's observability/monitoring platform and to simplify this code and make it more consumable, the Python code is run from a [Telegraf Exec Input Plugin](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/exec). You can adjust the output plugin to suite your environment.

The Python script does the following:

* Scans all IAM Access Keys for an AWS profile (passed in on the command line)
* Checks age of IAM Access Keys
* If key is nearing expiration, it files a Jira and notifies the user through Slack
* If key is expired, disable the key in AWS
* Outputs to STDOUT InfluxDB line formatted data for Telegraf

The code is smart enough to file only one Jira but will nag the user on Slack at least once every 24 hours.

Because we :heart: our users, Slack notices include directions on how to programatically rotate keys:

> To rotate your key, run the following CLI commands:
> 
> ```aws iam create-access-key --user-name Alice```
> ```aws iam update-access-key --access-key-id <OLD ACCESS KEY> --status Inactive --user-name Alice```
>
> For more information visit https://aws.amazon.com/blogs/security/how-to-rotate-access-keys-for-iam-users/

Here's what a sample slack message looks like:
<img src="https://user-images.githubusercontent.com/55153449/94055879-84f36500-fdab-11ea-9552-0c1d3dd18436.png">

The code uses a DynamoDB table to track state, mostly to avoid spamming users with multiple Jiras and Slack messages. It keeps track of the last time a user was messaged. By default, this uses the table `iam-access-key-alert` and will automaticaly create it if missing.

_Note_: By default, users are only ping'd on Slack if they have not been ping'd in the last 24 hours _and_ the configuration parameter `send_slack` is `True`. Likewise, Jira issues will only be filed if there isn't a prior open Jira _and_ `create_jira` is `True`.

See below for other configuration options.

### Observabilty & Monitoring
We run this through Telegraf and the output is InfluxDB formatted. You can adjust the output plugin for your environment.

Example output:
```
iam,name=dev_afiunel,key=VHXVM,status=disabled,accountAlias=lacework-devtest age=197
```


## Getting Started

Even though the code runs out of Telegraf, it can run standalone. You could easily adapt it to run out of `cron` or even as a scheduled container job and skip the Telegraf telemetry output.

The code uses standard `boto3` conventions. You can specify the AWS profile name anyway that `boto3` expects.

```   
/opt/keycheck/iam-accesskey-check.py AWS_PROFILE
```

### The code

You'll find the following directories:

* `aws`: sample "`~/.aws/config`", used for `boto`-based authentication
* `wavefront`: a Wavefront dashboard, in JSON
* `keycheck`: the actual code
* `k8s-templates`: Kubernetes templates


### Dependencies
The code uses several things where some prior knowledge may be helpful. Directions are terse on building the container and running it either locally or within Kubernetes (though some hints are provided).

* Docker
* Telegaf
* AWS IAM roles & permissions
* AWS DynamoDB
* Kubernetes
* Boto
* [`credstash`](https://github.com/fugue/credstash): used for lightweight, secure credential storage

**API Keys:**

* Atlassian API token (see [here to generate your token](https://confluence.atlassian.com/cloud/api-tokens-938839638.html ))
* Slack API token. Create a new app and token [here](https://api.slack.com/apps).

These API tokens should be store in `credstash`.


## Running the code

### Configuring AWS access
The code makes use of standard `boto` syntax for access.

`aws/config` is a sample "`~/.aws/config`" file that you can use for inspiration. You'll need to customize this for your environment.

In Lacework-land, we are making use of EC2 Instance Roles for cross-account IAM read access. YMMV.

### Configuring `telegraf.conf`
You'll need to update the output plugin for your environment and update the exec input plugin. As noted elsewhere, `iam-accesskey-check` is falled with the AWS profile as the single command line argument. 
The syntax is simliar to:

```
[[inputs.exec]]
 commands = [
   "/opt/keycheck/iam-accesskey-check.py AWS_PROFILE",
   ]
```

### Configuration parameters
#### Basics

If you run this locally or outside of Kubernetes, you'll want to set these variables in `env_setup.sh` and `source env_setup.sh`.

If you run this in Kubernetes, you'll want to update the ConfigMap with these variables.

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




### Building the container

You can build this container with the following:

```
$ docker build -t lacework/aws-access-key .
```

### Running in Kubernetes

You can use the files in `k8s-templates` for inspiration and customize for your environment.


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
