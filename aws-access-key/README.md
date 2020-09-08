<a href="https://lacework.com"><img src="https://techally-content.s3-us-west-1.amazonaws.com/public-content/lacework_logo_full.png" width="600"></a>

# IAM Access Key Monitoring @ Lacework

See the blog post [Keeping an eye on IAM Keys. No more stale keys!](https://engineering.lacework.net/?p=5601)

At Lacework, we follow many recommended best practices including [regularly rotating AWS credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#rotate-credentials). 

Since it's harder to remind users with programatic AWS access to rotate or change passwords (or not as easy as it is for an interactive login), we automated this.

**Goals:**

* ensure that old or stale keys are disabled
* notify users in Slack about keys nearing expiration
* file Jiras against users to rotate keys - work doesn't happen without a Jira *amiright*?
* send relevant telemetry to our monitoring platform to alert on expiring/expired keys (and track that as it relates to service health)


## The code

You'll find the following directories:

* `aws`: sample "`~/.aws/config`", used for `boto`-based authentication
* `wavefront`: A Wavefront dashboard, in JSON


## Running the code

### Configuring AWS access
The code makes use of standard `boto` syntax for access.

`aws/config` is a sample "`~/.aws/config`" file that you can use for inspiration. You'll need to customize this for your environment.

In Lacework-land, we are making use of EC2 Instance Roles for cross-account IAM read access. YMMV.

### Variables

### Dependencies

### Building the container


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
