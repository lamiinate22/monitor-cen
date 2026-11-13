#!/usr/bin/env python3
"""Monitor cen: co 5 min pobiera ceny, zapisuje do SQLite i wysyła powiadomienie
na Telegram, gdy cena jest niższa niż dotychczasowe minimum danego sklepu."""
import logging
import os
import re
import sqlite3
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).parent
DB_PATH = BASE / "ceny.db"
INTERVAL = 5 * 60
LOG_PATH = BASE / "monitor.log"
log = logging.getLogger("monitor")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Selektory CSS wzięte z kodu stron podanego w TODO.md
SITES = [
    {"name": "Ceneo", "url": "https://www.ceneo.pl/96964384",
     "selector": ".product-offer-summary__price-box .price"},
]


def setup_logging():
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler = RotatingFileHandler(LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    console = logging.StreamHandler()
    for h in (file_handler, console):
        h.setFormatter(fmt)
        log.addHandler(h)
    log.setLevel(logging.INFO)


def load_env():
    """Wczytuje TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID z pliku .env (jeśli jest)."""
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def parse_price(text):
    """'2 249,00 zł' / '2 699' -> 2249.0 / 2699.0"""
    text = re.sub(r"\s+", " ", text).replace("zł", "")
    m = re.search(r"\d[\d ]*(?:[.,]\d{1,2})?", text)
    if not m:
        raise ValueError(f"brak ceny w: {text!r}")
    return float(m.group().replace(" ", "").replace(",", "."))


def fetch_http(site):
    r = requests.get(site["url"], headers={"User-Agent": UA, "Accept-Language": "pl-PL,pl;q=0.9"}, timeout=30)
    r.raise_for_status()
    el = BeautifulSoup(r.text, "html.parser").select_one(site["selector"])
    if el is None:
        raise ValueError("nie znaleziono elementu z ceną")
    return parse_price(el.get_text(" ", strip=True))


def notify(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.warning("Brak konfiguracji Telegrama (.env) – powiadomienie pominięte: %s", text)
        return
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": text}, timeout=15)
    r.raise_for_status()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""CREATE TABLE IF NOT EXISTS ceny (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sklep TEXT NOT NULL, cena REAL NOT NULL, czas TEXT NOT NULL)""")
    return db


def check_site(db, site):
    price = fetch_http(site)
    # minimum sprawdzamy PRZED zapisem nowej ceny
    prev_min = db.execute("SELECT MIN(cena) FROM ceny WHERE sklep=?", (site["name"],)).fetchone()[0]
    db.execute("INSERT INTO ceny (sklep, cena, czas) VALUES (?,?,?)",
               (site["name"], price, datetime.now().isoformat(timespec="seconds")))
    db.commit()
    log.info("%s: %.2f zł (dotychczasowe min: %s)", site["name"], price, prev_min)
    if prev_min is not None and price < prev_min:
        try:
            notify(f"Nowa najniższa cena w {site['name']}: {price:.2f} zł "
                   f"(poprzednio {prev_min:.2f} zł)\n{site['url']}")
        except Exception:  # błąd powiadomienia nie może zatrzymać monitora
            log.exception("Nie udało się wysłać powiadomienia Telegram")


def run_once(db):
    for site in SITES:
        try:
            check_site(db, site)
        except Exception:  # awaria pobierania nie zatrzymuje pętli
            log.exception("%s: błąd pobierania ceny", site["name"])


def main():
    setup_logging()
    load_env()
    db = init_db()
    while True:
        started = time.monotonic()
        run_once(db)
        time.sleep(max(0, INTERVAL - (time.monotonic() - started)))


if __name__ == "__main__":
    main()
