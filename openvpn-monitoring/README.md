<a href="https://lacework.com"><img src="https://techally-content.s3-us-west-1.amazonaws.com/public-content/lacework_logo_full.png" width="600"></a>

# OpenVPN Monitoring @ Lacework

See the blog post [OpenVPN at Scale. Part 2: Monitoring!](https://engineering.lacework.net/?p=5630).

At Lacework we use a combination of Telegraf input plugins to pull data out of the OpenVPN CLI (`sacli`) to make sure we have good alerting on OpenVPN.

Among other things, we're pulling the following data:

* **Concurrent user count**
* **SSL certificate expiry**
* **Per-user connection time**
* **Per-user bytes transferred (in/out)**

## The code

You'll find the following directories:

* `wavefront`: A Wavefront dashboard, in JSON
* `scripts`: a helper script that takes the output from "`sacli VPNSummary`" and converts to influx-stype line format.
* `telegraf`: one input exec plugin to pull data from `sacli` and one x509_cert plugin to pull SSL certificate data.

## Wavefront
We use [Wavefront](https://www.wavefront.com/) as our time-series metrics platform. The sample dashboard should give you ideas for your own dashboard (or you can import directly to Wavefront).

![](https://engineering.lacework.net/wp-content/uploads/2020/09/openvpn-dashboard.png)

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
