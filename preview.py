#!/usr/bin/python3
""" preview.py - show information from cloudatcost.com and ethermine.org
    v0.2.3 - 2021-11-05 - nelbren@nelbren.com"""
import os
import re
import sys
import shutil
import argparse
import tempfile
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from argparse import RawTextHelpFormatter
from datetime import datetime, timedelta
import imgkit
import peewee
import mining_at_cloudatcost
import mining_at_ethermine
from database import db, Unpaid
from deltas_and_tags import (
    tags_row,
    tags_title,
    get_goal_msg,
    set_deltas_empty,
    set_deltas,
)
from table import (
    get_columns_and_lines,
    make_table,
    set_and_and_row_date,
    add_row,
    add_last_row,
    show_progress,
)
from config import get_config
import big_text

TS_FMT = "%Y-%m-%d %H:%M:%S"
next_update = {}


def setup_db():
    """Setup"""
    models = [Unpaid]
    db.connect()
    db.create_tables(models)


def setup_jpg(html):
    """Setup JPG"""
    html2 = os.path.splitext(html)[0] + "_temp.html"
    shutil.copyfile(html, html2)
    with open(html2, "r+", encoding="utf-8") as _file:
        text = _file.read()
        text = re.sub("⛏️", "&nbsp;", text)
        text = re.sub("🎯", "&nbsp;&nbsp;", text)
        _file.seek(0)
        _file.write(text)
        _file.truncate()
    options = {"encoding": "latin_1", "quiet": ""}
    img = os.path.splitext(html)[0] + ".jpg"
    imgkit.from_file(html2, img, options=options)
    os.unlink(html2)


def setup_html(html):
    """Setup HTML"""
    with open(html, "r+", encoding="utf-8") as _file:
        text = _file.read()
        pre = "pre { color: #ffffff; background-color: #000000; font-size: 41px; }"
        text = re.sub("</style>", f"{pre}\n</style>", text)
        _file.seek(0)
        _file.write(text)
        _file.truncate()
    setup_jpg(html)


def mail_data(params, numbers, tag):
    """Mail"""
    cfg = get_config()
    if not cfg["mail_from"] or not cfg["mail_to"]:
        print("Please set the FROM and TO fields of MAIL!")
        sys.exit(0)
    msg = MIMEMultipart()
    msg["From"] = cfg["mail_from"]
    msg["To"] = cfg["mail_to"]
    subject = ""
    if numbers[0]:
        subject += f"⛏️ E{numbers[0]} 🎯{tag['ethermine_goal_pm_usd']}% "
    if numbers[1]:
        subject += f"⛏️ B{numbers[1]} 🎯{tag['cloudatcost_goal_pm_usd']}%"
    msg["Subject"] = subject

    name = "miner_preview.jpg"
    filename = params["save_dir"] + "/" + name
    with open(filename, "rb") as _file:
        part = MIMEApplication(_file.read(), Name=name)
    part["Content-Decomposition"] = f"attachment, filename={name}"
    msg.attach(part)

    smtp = smtplib.SMTP("localhost")
    smtp.sendmail(msg["From"], msg["To"], msg.as_string())
    smtp.close()


def get_params():
    """Get params"""
    eth_addr = "0x0892c9b9b58ad5a7878d5dcd4da4ee72109c32c6"
    email = "nelbren@nelbren.com"
    parser = argparse.ArgumentParser(
        description=(
            "Get wallet balance from Ethermine and Cloudatcost "
            f"mining process.\nDonate ETH 👉 {eth_addr}"
            f"\nContact email 👉{email}"
        ),
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--cloudatcost",
        action="store_true",
        default=False,
        dest="cloudatcost",
        help="Only show cloudatcost info",
    )
    parser.add_argument(
        "-e",
        "--ethermine",
        action="store_true",
        default=False,
        dest="ethermine",
        help="Only show ethermine info",
    )
    parser.add_argument(
        "-r",
        "--records",
        type=int,
        required=False,
        default=-1,
        help="The number of last records to get (0 = All)",
    )
    parser.add_argument(
        "-s",
        "--save_dir",
        required=False,
        default="",
        help="Directory to save the output (HTML and JPG)",
    )
    crontab = "1 2,6,10,14,18,22 * * * /path/preview.py -u"
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        default=False,
        dest="update",
        help=f"Only update database, crontab 👇\n{crontab}",
    )
    parser.add_argument(
        "-b",
        action="store_true",
        default=False,
        dest="big",
        help="Only show big text",
    )
    parser.add_argument(
        "-m",
        "--mail",
        action="store_true",
        default=False,
        dest="mail",
        help=f"Send an email with the image attachment, crontab 👇\n{crontab}",
    )
    args = parser.parse_args()
    if not args.ethermine and not args.cloudatcost:
        cfg = get_config()
        if cfg["address"]:
            args.ethermine = True
        if cfg["username"]:
            args.cloudatcost = True
    if args.mail:
        args.save_dir = tempfile.gettempdir()
    return {
        "big": args.big,
        "ethermine": args.ethermine,
        "cloudatcost": args.cloudatcost,
        "update": args.update,
        "records": args.records,
        "save_dir": args.save_dir,
        "mail": args.mail,
    }


def get_records(records, source, currency):
    """Get records and recalculate number of records"""
    try:
        if records == 0:
            unpaids = (
                Unpaid.select()
                .where(
                    (Unpaid.source == source) & (Unpaid.currency == currency)
                )
                .order_by(Unpaid.work.desc(), Unpaid.step.desc())
            )
        else:
            unpaids = (
                Unpaid.select()
                .where(
                    (Unpaid.source == source) & (Unpaid.currency == currency)
                )
                .order_by(Unpaid.work.desc(), Unpaid.step.desc())
                .limit(records)
            )
            last_unpaid = unpaids[-1]
            count, item = records - 1, 0
            for unpaid in unpaids:  # reversed(unpaids):
                count -= 1
                if count <= 0:
                    break
                if unpaid.timestamp[:10] != last_unpaid.timestamp[:10]:
                    last_unpaid = unpaid
                    item += 1

            item += 1  # First and Last
            records -= item  # Extra line of summary
            unpaids = (
                Unpaid.select()
                .where(
                    (Unpaid.source == source) & (Unpaid.currency == currency)
                )
                .order_by(Unpaid.work.desc(), Unpaid.step.desc())
                .limit(records)
            )

    except peewee.DoesNotExist:
        print("do-something")
    return records, unpaids


def iterate_on_records(source, currency, table, params, data):
    """Iterate on records"""

    # print('LS: ', data["lines_show"])
    tag = {}
    tag["currency"] = "[cyan]"
    # print('ANTES: ', params["records"])
    params[f"records_{currency}"], unpaids = get_records(
        params[f"records_{currency}"], source, currency
    )
    # print('DESPUES: ', params[f"records_{currency}"])
    data["last_unpaid"] = None
    delta = last_delta = {}
    delta[source] = data["unpaid_save"]

    item = 0
    for unpaid in reversed(unpaids):
        item += 1
        if data["last_unpaid"] is None:
            set_deltas_empty(unpaid, delta)
            last_delta = delta.copy()
        else:
            last_delta = delta.copy()
            set_deltas(data["last_unpaid"], unpaid, last_delta, delta)
        tags_row(tag, data["last_unpaid"], unpaid, last_delta, delta)
        if last_delta["date"] != delta["date"] or item == 1:
            set_and_and_row_date(table, data["last_unpaid"], unpaid, delta)
            data["lines_show"] -= 1
        add_row(table, tag, delta, unpaid)
        data["lines_show"] -= 1
        if item == unpaids.count():
            timestamp_obj = datetime.strptime(unpaid.timestamp, TS_FMT)
            next_update["timestamp"] = timestamp_obj + timedelta(hours=4)
            next_update["timestamp"] = next_update["timestamp"].replace(
                minute=1, second=0
            )
        data["last_unpaid"] = unpaid

    add_last_row(table, delta, data["last_unpaid"])
    data["lines_show"] -= 4  # 1 Summary + 3 Header


def show_data(console, params, unpaid_save, size_term):
    """Show time"""
    if params["records"] == -1:
        params["records"] = size_term["lines"]
        if params["ethermine"] and params["cloudatcost"]:
            params["records"] = int(params["records"] / 2)  # Sharing
        params["records"] -= 4  # 3 Lines of header + 1 of Footer
    sources = []
    if params["ethermine"]:
        sources.append("ethermine")
        params["records_eth"] = params["records"]
    if params["cloudatcost"]:
        sources.append("cloudatcost")
        params["records_btc"] = params["records"]

    lines_show = size_term["lines"] - 1
    if lines_show < 3 and params["records"]:
        print("Too small to show")
        sys.exit(0)
    print(chr(27) + "[2J")

    data = {
        "lines_show": lines_show,
        "next_update": next_update,
        "last_unpaid": None,
        "unpaid_save": unpaid_save,
    }
    # console = Console(record=True)
    tag = {}
    for source in sources:
        if source == "cloudatcost":
            currency = "btc"
        else:
            currency = "eth"
        table = make_table()
        iterate_on_records(source, currency, table, params, data)
        timestamp = datetime.now().strftime(TS_FMT)
        tags_title(tag, data["last_unpaid"], timestamp)
        size_term = get_columns_and_lines()
        console.print(
            f"{tag['title']} ⛏️ {currency.upper()}@"
            f"[bold white]{timestamp}[not bold black] "
            f"{tag['ok']}{get_goal_msg(source, currency, tag, data['last_unpaid'], size_term)}",
            style=tag["style"],
            justify="center",
        )
        console.print(table)
    if params["records"] != 0:
        while data["lines_show"] > 0:
            data["lines_show"] -= 1
            console.print("")
    if params["save_dir"]:
        html = params["save_dir"] + "/miner_preview.html"
        console.save_html(html)
        setup_html(html)
    next_update["missing"] = next_update["timestamp"] - datetime.now()
    return next_update["missing"].total_seconds(), tag


def save_data(source, currency, value, usd):
    """Save record"""
    if value == -1:
        return 0
    try:
        unpaid = (
            Unpaid.select()
            .where((Unpaid.source == source) & (Unpaid.currency == currency))
            .order_by(Unpaid.work.desc(), Unpaid.step.desc())
            .get()
        )
    except peewee.DoesNotExist:
        last_value, work, step = 0, 1, 1
    else:
        last_value, work, step = unpaid.value, unpaid.work, unpaid.step + 1
        timestamp = unpaid.timestamp

    if last_value != value:
        timestamp = f"{datetime.now()}"
        timestamp_obj = datetime.strptime(timestamp, TS_FMT + ".%f")
        timestamp = timestamp_obj.strftime(TS_FMT)
        unpaid = Unpaid(
            source=source,
            currency=currency,
            work=work,
            step=step,
            timestamp=timestamp,
            value=value,
            usd=usd,
        )
        unpaid.save()
        # pylint: disable=no-member
        unpaid_save = unpaid.id
    else:
        unpaid_save = 0
    return unpaid_save


def show_big():
    """Show big"""
    datas = [
        {"source": "ethermine", "currency": "eth"},
        {"source": "cloudatcost", "currency": "btc"},
    ]
    for data in datas:
        source = data["source"]
        currency = data["currency"]
        unpaids = (
            Unpaid.select()
            .where((Unpaid.source == source) & (Unpaid.currency == currency))
            .order_by(Unpaid.work.desc(), Unpaid.step.desc())
            .limit(2)
        )
        if len(unpaids) >= 1:
            data["number"] = unpaids[0].usd
        if len(unpaids) == 2:
            if unpaids[0].usd == unpaids[1].usd:
                data["tag"] = "="
                data["color"] = "white"
            elif unpaids[0].usd > unpaids[1].usd:
                data["tag"] = "^"
                data["color"] = "green"
            else:
                data["tag"] = "v"
                data["color"] = "red"
        else:
            data["tag"] = "="
            data["color"] = "white"
    tags = {"number1": datas[0]["tag"], "number2": datas[1]["tag"]}
    colors = {
        "normal": "black",
        "number1": datas[0]["color"],
        "number2": datas[1]["color"],
    }
    usd_etm, usd_cac = datas[0]["number"], datas[1]["number"]
    console, numbers = big_text.show_big(usd_etm, usd_cac, tags, colors)
    return console, numbers


def get_data():
    """Get data from miner"""
    source, currency = "ethermine", "eth"
    etmpanel = mining_at_ethermine.ETMPanel()
    eth, usd_etm = etmpanel.wallet()
    unpaid_save_etm = save_data(source, currency, eth, usd_etm)
    source, currency = "cloudatcost", "btc"
    cacpanel = mining_at_cloudatcost.CACPanel()
    btc, usd_cac = cacpanel.wallet()
    unpaid_save_cac = save_data(source, currency, btc, usd_cac)
    console, numbers = show_big()
    return console, numbers, {"etm": unpaid_save_etm, "cac": unpaid_save_cac}


def do_loop():
    """Eternal Loop 4 forever & ever"""
    setup_db()
    size_term = get_columns_and_lines()
    params = get_params()
    while True:
        console, numbers, unpaid_save = get_data()
        if params["big"]:
            return
        if params["update"]:
            timestamp = datetime.now().strftime(TS_FMT)
            id_save = unpaid_save
            print(f"{timestamp} => {id_save}")
            return
        seconds, tag = show_data(console, params, unpaid_save, size_term)
        if params["mail"]:
            mail_data(params, numbers, tag)
        if params["records"] == 0 or params["save_dir"] or params["mail"]:
            return
        try:
            show_progress(seconds, next_update)
        except KeyboardInterrupt:
            sys.exit(0)


do_loop()
