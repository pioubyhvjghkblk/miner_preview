#!/usr/bin/python3
""" miner.py - get information from CAC
    v0.1.3 - 2021-10-30 - nelbren@nelbren.com
    NOTE: 2FA code thanks to Isonium"""
import re
import os
import sys
import pickle
import configparser
import tempfile
import requests
import pyotp


class Error(Exception):
    """Base class for other exceptions"""


class CantGetCsrf(Error):
    """Raised when Can't get _csrf"""


class CantGetAuth2FA(Error):
    """Raised when Can't get Auth 2FA"""


class MissingAuth2FA(Error):
    """Raised when Missing Auth 2FA"""


class CantGetUSDandBTC(Error):
    """Raised when Can't get usd and btc"""


def debug(is_ok):
    """Show tag"""
    if DEBUG:
        tag = 1 if is_ok else 0
        print(f"{TAG[tag]} ", end="")


def check_config(path, filename):
    """Check if config file exist"""
    if not os.path.exists(path + "/" + filename):
        print(
            f'Create the file "{filename}" using the template "secret.cfg.EXAMPLE"!'
        )
        sys.exit(1)


class CACPanel:
    """Class to manage the access to CAC Panel"""

    url_base = "https://wallet.cloudatcost.com"
    cookie = ".wallet_cloudatcost.cookie"
    logged = False

    def auth_2fa(self, headers, page):
        """Auth 2FA process"""
        reg = r"(Two Factor Auth)"
        match = re.findall(reg, page.content.decode("utf-8"))
        if match:
            if not self.code_2fa:
                print(f"{TAG[0]} Missing CODE_2FA")
                raise MissingAuth2FA
            if DEBUG:
                print("2FA -> ", end="")
            url = self.url_base + "/auth"
            totp = pyotp.TOTP(self.code_2fa)
            data = {"authCode": totp.now(), "_csrf": self._csrf}
            self.session.post(url, data=data, headers=headers)
            page = self.session.get(self.url_base)
            return page
        if not self.code_2fa:
            return page
        print(f"{TAG[0]} Can't get Auth 2FA")
        raise CantGetAuth2FA

    def login(self):
        """Login process"""
        if DEBUG:
            print("Login -> ", end="")
        data = {
            "email": self.username,
            "password": self.password,
            "_csrf": self._csrf,
        }
        headers = {
            "accept-language": "en-US,en;q=0.9,es;q=0.8",
            "accept-encoding": "gzip, deflate, br",
            "content-type": "application/x-www-form-urlencoded",
            "connection": "keep-alive",
            "origin": "https://wallet.cloudatcost.com",
            "referer": "https://wallet.cloudatcost.com/login",
            "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
            + "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Mobile Safari/537.36",
        }
        url = self.url_base + "/login"
        self.session.post(url, data=data, headers=headers)
        with open(self.cookie, "wb") as _file:
            pickle.dump(self.session.cookies, _file)
        page = self.session.get(self.url_base)
        try:
            page = self.auth_2fa(headers, page)
        except MissingAuth2FA:
            sys.exit(4)
        reg = r">(Miners)<"
        match = re.findall(reg, page.content.decode("utf-8"))
        self.logged = match
        debug(self.logged)

    def pre_login(self):
        """Pre-login process"""
        if DEBUG:
            print("Pre-login -> ", end="")
        url = self.url_base + "/login"
        page = self.session.get(url)
        reg = r'_csrf" value="([^"]+)"'
        match = re.findall(reg, page.content.decode("utf-8"))
        debug(match)
        if match:
            self._csrf = match[0]
            self.login()
        else:
            print(f"{TAG[0]} Can't get _csrf")
            raise CantGetCsrf

    def __init__(self):
        config = configparser.ConfigParser()
        path = os.path.dirname(os.path.realpath(__file__))
        filename = ".secret.cfg"
        check_config(path, filename)
        config.read_file(open(path + "/" + filename))
        self.username = config.get("CAC_WALLET", "USERNAME")
        self.password = config.get("CAC_WALLET", "PASSWORD")
        self.code_2fa = config.get("CAC_WALLET", "CODE_2FA", fallback="")
        self.session = requests.session()
        self.cookie = tempfile.gettempdir() + "/" + self.cookie
        if os.path.exists(self.cookie):
            if DEBUG:
                print(f"Reusing 🍪 ({self.cookie})-> ", end="")
            with open(self.cookie, "rb") as _file:
                self.session.cookies.update(pickle.load(_file))
            try:
                page = self.session.get(self.url_base)
            except requests.exceptions.ConnectionError:
                print(f"Connection problem to {self.url_base}!")
                sys.exit(2)
            reg = r">(Miners)<"
            match = re.findall(reg, page.content.decode("utf-8"))
            self.logged = match
            debug(match)
            if match:
                return
        self.pre_login()

    def wallet(self):
        """Get Wallet information"""
        if not self.logged:
            return -1, -1
        if DEBUG:
            print("Wallet 💰-> ", end="")
        url = self.url_base + "/wallet"
        page = self.session.get(url)
        reg = r'font-30">\$(?P<usd>.+)&nbsp;USD</h1>\n.*font-30">(?P<btc>.+)&nbsp;BTC<'
        parse = re.search(reg, page.content.decode("utf-8"))
        debug(parse)
        if parse:
            _usd = float(parse.groupdict()["usd"])
            _btc = float(parse.groupdict()["btc"])
        else:
            print(f"{TAG[0]} Can't get crypto info")
            raise CantGetUSDandBTC
        return _btc, _usd


DEBUG = 0
TAG = ["✖", "✔"]

if __name__ == "__main__":
    cacpanel = CACPanel()
    try:
        btc, usd = cacpanel.wallet()
    except CantGetCsrf:
        sys.exit(3)
    except CantGetUSDandBTC:
        sys.exit(5)
    else:
        print(f"BTC: {btc:1.8f} USD: {usd:05.2f}")
