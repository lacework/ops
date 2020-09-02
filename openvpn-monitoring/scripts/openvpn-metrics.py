from __future__ import print_function

import os
import sys
import json
import time


def main(vpn_status_file):
    if vpn_status_file:
        with open("vpnstatus.json", 'r') as vpnstatus_file:
            vpn_status = json.load(vpnstatus_file)
    else:
        stream = os.popen('/usr/local/openvpn_as/scripts/sacli VPNStatus')
        output = stream.read()
        vpn_status = json.loads(output)

    total_clients = 0
    client_metrics = []
    vpn_metrics = []
    timestamp = int(time.time())
    for k, v in vpn_status.items():
        total_clients += len(v.get('client_list'))
        headers = v.get('client_list_header')
        bytes_rec_header = headers.get('Bytes Received')
        bytes_sent_header = headers.get('Bytes Sent')
        username_header = headers.get('Username')
        connected_since_header = headers.get('Connected Since (time_t)')

        for user in v.get('client_list'):
            client_metrics.append(
                'vpn,username={} status_client_bytes_recv={},status_client_bytes_sent={},status_client_connected_duration={}'.format(
                    user[username_header],
                    user[bytes_rec_header],
                    user[bytes_sent_header],
                    timestamp - int(user[connected_since_header]),
                )
            )

        vpn_metrics.append(
            'vpn,vpn={} max_bcast_mcast_queue_length={}'.format(
                k,
                v.get('global_stats').get('Max bcast/mcast queue length'),
            )
        )

    vpn_metrics.append(
        'vpn client_total={}'.format(
            total_clients,
        )
    )

    [print(_) for _ in client_metrics]
    [print(_) for _ in vpn_metrics]


if __name__ == '__main__':
    if len(sys.argv) > 1:
        inf = sys.argv[1]
        main(inf)
    else:
        main(None)

