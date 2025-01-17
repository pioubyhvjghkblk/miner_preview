#!/usr/bin/python3
""" config.py - get configuration
    v0.0.6 - 2022-05-07 - nelbren@nelbren.com """
import os
import sys
import configparser


def check_config(path, filename):
    """Check if config file exist"""
    if not os.path.exists(path + "/" + filename):
        print(
            f'Create the file "{filename}" using the '
            'template "secret.cfg.EXAMPLE"!'
        )
        sys.exit(1)


def get_config():
    """Get config"""
    config = configparser.ConfigParser()
    path = os.path.dirname(os.path.realpath(__file__))
    filename = ".secret.cfg"
    check_config(path, filename)
    config.read(path + "/" + filename)
    section = "CRYPTOATCOST"
    hostname = config.get(section, "HOSTNAME", fallback=None)
    username = config.get(section, "USERNAME", fallback=None)
    password = config.get(section, "PASSWORD", fallback=None)
    code_2fa = config.get(section, "CODE_2FA", fallback=None)
    cac_goal_usd = config.get(section, "GOAL_USD", fallback=None)
    cac_goal_btc = config.get(section, "GOAL_BTC", fallback=None)
    section = "ETHERMINE"
    address = config.get(section, "ADDRESS", fallback=None)
    etm_goal_usd = config.get(section, "GOAL_USD", fallback=None)
    etm_goal_btc = config.get(section, "GOAL_ETH", fallback=None)
    section = "NICEHASH"
    nch_org = config.get(section, "ORG", fallback=None)
    nch_key = config.get(section, "KEY", fallback=None)
    nch_secret = config.get(section, "SECRET", fallback=None)
    nch_goal_usd = config.get(section, "GOAL_USD", fallback=None)
    nch_goal_btc = config.get(section, "GOAL_BTC", fallback=None)
    section = "MAIL"
    mail_from = config.get(section, "FROM", fallback=None)
    mail_to = config.get(section, "TO", fallback=None)
    section = "TELEGRAM"
    telegram_token = config.get(section, "TOKEN", fallback=None)
    telegram_id = config.get(section, "ID", fallback=None)
    return {
        "hostname": hostname,
        "username": username,
        "password": password,
        "code_2fa": code_2fa,
        "cac_goal_usd": cac_goal_usd,
        "cac_goal_btc": cac_goal_btc,
        "address": address,
        "etm_goal_usd": etm_goal_usd,
        "etm_goal_btc": etm_goal_btc,
        "nch_org": NHbQh4sxVTJSUAFrKBPV9VP8aBW54FBiSoE5,
        "nch_key": 314ba359-0ba3-4b90-b3c2-f34d3934b8b8
        "nch_secret": 4da6f0a5-c970-49a7-bc89-3e0dafb8875744ea413e-9562-482d-91cc-1c0378f88776
        "nch_goal_usd": 17000,
        "nch_goal_btc": 1,
        "mail_from": mail_from,
        "mail_to": mail_to,
        "telegram_token": telegram_token,
        "telegram_id": telegram_id,
    }
