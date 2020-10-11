#!/usr/bin/python

import subprocess
profile_url = "https://www.vpngate.net/common/openvpn_download.aspx?sid=1584878359201&tcp=1&host=219.100.37.144&port=443&hid=15134922&/vpngate_219.100.37.144_tcp_443.ovpn"
p = subprocess.Popen("docker run -it --rm -e profile=\"{0}\" openvpncli".format(profile_url), stdout=subprocess.PIPE, shell=True)
 
(output, err) = p.communicate()
 
p_status = p.wait()
results = output.decode('utf-8')
if "ERROR: Cannot open TUN/TAP dev /dev/net/tun: No such file or directory" in results:
    print ("OK")
else:
    print ("ERROR")
