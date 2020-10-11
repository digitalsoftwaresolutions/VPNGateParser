#!/bin/bash

wget "$profile" -O /home/profile.ovpn
openvpn --config /home/profile.ovpn --resolv-retry 1 --auth-retry none --connect-retry 1 --connect-timeout 10 --tls-timeout 10 --connect-retry-max 1
