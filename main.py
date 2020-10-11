from datetime import datetime

from HttpService import HttpService
from bs4 import BeautifulSoup
import threading
import os
from urllib.parse import urlparse, parse_qs
import mysql.connector

http = HttpService()
connection = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd="",
    database="openvpn"
)

DEBUG = True
API_CSV_URL = "http://www.vpngate.net/api/iphone/"
API_HTML_URL = "https://www.vpngate.net/en/"


def write_to_file(filename, content):
    current_dir = os.path.dirname(os.path.realpath("__file__"))  # Hacky Way :)
    folder = os.path.join(current_dir, 'profiles')
    fname = os.path.join(folder, filename)
    f = open(fname, mode='w')
    f.write(content.decode('utf-8'))
    f.close()


def download_profile(server):
    udp = server['udp']
    tcp = server['tcp']
    ip = server['ip']
    print("Download Profiles for {0}\n".format(ip))
    if tcp is not None:
        res = http.get(tcp)
        write_to_file("{0}_tcp.ovpn".format(ip), res)
    if udp is not None:
        res = http.get(udp)
        write_to_file("{0}_udp.ovpn".format(ip), res)


def parse_table(raw_html):
    servers = []
    soup = BeautifulSoup(raw_html, 'lxml')
    tables = soup.find_all(id='vg_hosts_table_id')
    table = tables[2]
    rows = table.find_all('tr')
    for tr in rows:
        try:
            cols = tr.find_all('td')
            if cols[0]['class'][0] == 'vg_table_row_0' or cols[0]['class'][0] == 'vg_table_row_1':
                country = cols[0].contents[2]
                ip = cols[1].contents[2].text
                active_sessions = cols[2].contents[0].text
                uptime = cols[2].contents[2].text
                speed = cols[3].contents[0].text
                traffic = cols[3].contents[6].text
                vpn_link = cols[6].find('a')
                if vpn_link is None:
                    print("OpenVPN Not Available")
                    continue
                else:
                    vpn_link = vpn_link['href']

                parsed_url = urlparse(API_HTML_URL + vpn_link)
                parsed_qs = parse_qs(parsed_url.query)

                download_url_tcp = "https://www.vpngate.net/common/openvpn_download.aspx?sid={0}&tcp=1&host={1}&port={2}&hid={3}&/vpngate_{1}_tcp_{2}.ovpn" \
                    .format(
                    parsed_qs['sid'][0],
                    parsed_qs['ip'][0],
                    parsed_qs['tcp'][0],
                    parsed_qs['hid'][0],
                )
                download_url_udp = "https://www.vpngate.net/common/openvpn_download.aspx?sid={0}&udp=1&host={1}&port={2}&hid={3}&/vpngate_{1}_udp_{2}.ovpn" \
                    .format(
                    parsed_qs['sid'][0],
                    parsed_qs['ip'][0],
                    parsed_qs['udp'][0],
                    parsed_qs['hid'][0],
                )

                if parsed_qs['tcp'][0] == '0':
                    download_url_tcp = None
                if parsed_qs['udp'][0] == '0':
                    download_url_udp = None

                score = cols[9].text
                servers.append({
                    'country': country,
                    'ip': ip,
                    'sessions': active_sessions,
                    'uptime': uptime,
                    'speed': speed,
                    'traffic': traffic,
                    'tcp': download_url_tcp,
                    'udp': download_url_udp,
                    'score': score
                })
        except Exception as ex:
            print(ex)
    return servers


def html_request():
    try:
        res = http.get(API_HTML_URL)
        servers = parse_table(res)
        threads = []

        cur = connection.cursor()
        insert = "INSERT INTO servers(ip,country,sessions,uptime,speed,traffic,tcp,udp,score) values ('{0}','{1}',{2},{3},{4},{5},'{6}','{7}',{8})"
        update = "UPDATE servers SET country = '{1}',sessions = {2},uptime = {3},speed = {4},traffic = {5},tcp = '{6}',udp = '{7}',score = {8}, updated = '{9}' WHERE  ip = '{0}'"
        check_ip = "SELECT * FROM servers where ip = '{0}'"
        updated = 0
        new = 0
        for server in servers:
            if DEBUG:
                print(server)
            if server['udp'] is None and server['tcp'] is None:
                continue
            sessions = server['sessions'].split(' ')[0].replace(',', '') if server['sessions'].count(' ') > 0 else 0
            speed = 0
            uptime = 0
            traffic = 0

            try:
                uptime_mess = server['uptime'].split(' ')[1]
                if uptime_mess == 'mins':
                    uptime = int(server['uptime'].split(' ')[0])
                elif uptime_mess == 'hours':
                    uptime = int(server['uptime'].split(' ')[0]) * 60
                elif uptime_mess == 'days':
                    uptime = int(server['uptime'].split(' ')[0]) * 24 * 60
            except Exception as ex:
                print(ex)

            try:
                speed_mess = server['speed'].split(' ')[1]
                if speed_mess == 'Mbps':
                    speed = float(server['speed'].split(' ')[0].replace(',', ''))
                elif speed_mess == 'GB':
                    speed = float(server['speed'].split(' ')[0].replace(',', '')) * 1024
            except Exception as ex:
                print(ex)

            try:
                traffic_mess = server['traffic'].split(' ')[1]
                if traffic_mess == 'GB':
                    traffic = float(server['traffic'].split(' ')[0].replace(',', ''))
            except Exception as ex:
                print(ex)

            search_stmt = check_ip.format(server['ip'])
            cur.execute(search_stmt)
            cur.fetchall()
            now = datetime.now()
            str_now = now.date().isoformat()
            if cur.rowcount is 0:
                stmt = insert.format(
                    server['ip'],
                    server['country'],
                    sessions,
                    uptime,
                    speed,
                    traffic,
                    server['tcp'] if server['tcp'] is not None else "",
                    server['udp'] if server['udp'] is not None else "",
                    int(server['score'].replace(',', '')),
                )
                try:
                    cur.execute(stmt)
                    connection.commit()
                    new += 1
                except Exception as ex:
                    print('SQL Error' + str(ex))
            elif cur.rowcount is 1:
                stmt = update.format(
                    server['ip'],
                    server['country'],
                    sessions,
                    uptime,
                    speed,
                    traffic,
                    server['tcp'] if server['tcp'] is not None else "",
                    server['udp'] if server['udp'] is not None else "",
                    int(server['score'].replace(',', '')),
                    str_now
                )
                try:
                    cur.execute(stmt)
                    connection.commit()
                    updated += 1
                except Exception as ex:
                    print('SQL Error' + str(ex))
            thread = threading.Thread(target=download_profile, args=(server,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
        print("Got New {0} Servers , Updated {1} Server".format(new,updated))
    except Exception as ex:
        print(ex)


def pre_check():
    current_dir = os.path.dirname(os.path.realpath(__file__))
    folder = os.path.join(current_dir, 'profiles')
    if not os.path.exists(folder):
        os.makedirs(folder)


def main():
    pre_check()
    html_request()


if __name__ == '__main__':
    main()
