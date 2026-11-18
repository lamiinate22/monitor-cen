# Monitor cen

Skrypt w Pythonie, który co 5 minut sprawdza cenę konsoli Xbox Series S 512GB na Ceneo, zapisuje ją w bazie SQLite i wysyła powiadomienie na Telegram, gdy cena jest niższa niż dotychczasowe minimum.

## Wymagania

- Python 3.10 lub nowszy (testowane na 3.14)
- macOS lub Linux
- Konto Telegram i bot utworzony przez @BotFather

## Instalacja

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Konfiguracja

Skopiuj `.env.example` do `.env` i uzupełnij:

```
TELEGRAM_BOT_TOKEN=<token od @BotFather>
TELEGRAM_CHAT_ID=<Twoje id czatu>
```

Jak je zdobyć:
1. Napisz do @BotFather, wyślij `/newbot`, skopiuj token.
2. Napisz dowolną wiadomość do swojego nowego bota. Bez tego bot nie może pisać pierwszy.
3. Otwórz `https://api.telegram.org/bot<TOKEN>/getUpdates` i odczytaj `chat.id`.

Jeśli `.env` jest pusty, skrypt działa dalej, ale zamiast wysyłać alert tylko wypisuje go w konsoli.

Plik `.env` zawiera sekret. Jest w `.gitignore` i nie wolno go commitować.

## Uruchomienie

```bash
.venv/bin/python monitor.py
```

Skrypt działa w pętli bez końca (zatrzymanie: Ctrl+C), więc terminal musi zostać otwarty. Do pracy w tle po restarcie komputera można użyć `launchd` (macOS) lub `systemd` (Linux).

## Jak to działa

Co 5 minut, dla strony z listy `SITES`:

1. Pobiera stronę i wyciąga cenę selektorem CSS.
2. Odczytuje z bazy dotychczasowe minimum (przed zapisem nowej ceny).
3. Zapisuje nową cenę do bazy.
4. Jeśli nowa cena jest niższa od minimum, wysyła powiadomienie na Telegram. Przy pierwszym pomiarze minimum nie istnieje, więc alertu nie ma.

## Baza danych

SQLite, plik `ceny.db` w katalogu projektu. Tworzy się automatycznie przy pierwszym uruchomieniu.

Tabela `ceny`:

| Kolumna | Typ | Opis |
|---|---|---|
| `id` | INTEGER, klucz główny | numer kolejny |
| `sklep` | TEXT | nazwa źródła z `SITES` |
| `cena` | REAL | cena w zł |
| `czas` | TEXT | czas pomiaru w UTC, ISO 8601 (np. `2026-11-13T14:25:31+00:00`) |

Przykładowe zapytanie:

```bash
sqlite3 ceny.db "SELECT sklep, cena, czas FROM ceny ORDER BY id DESC LIMIT 20;"
```

## Logi i błędy

Skrypt zapisuje komunikaty (czas w UTC) (pomiary, ostrzeżenia, błędy z pełnym stack trace) w `monitor.log` i wypisuje je w konsoli. Plik rotuje się po 1 MB i zachowuje 3 kopie (`monitor.log.1`–`.3`). Błąd pobierania ceny lub wysyłki na Telegram jest logowany, a pętla działa dalej.

## Struktura projektu

| Plik | Przeznaczenie |
|---|---|
| `monitor.py` | cały program |
| `requirements.txt` | zależności Pythona (`requests`, `beautifulsoup4`) |
| `.env.example` | wzór konfiguracji |
| `.env` | prawdziwa konfiguracja (poza repozytorium) |
| `ceny.db` | baza z historią cen (powstaje przy uruchomieniu) |
| `monitor.log` | log działania i błędów (rotacja: 1 MB, 3 kopie) |
| `TODO.md` | pierwotne zadanie wraz ze źródłami HTML z cenami |

## Rozszerzanie

**Dodanie strony:** dopisz słownik do listy `SITES` w `monitor.py`:

```python
{"name": "Nazwa", "url": "https://...", "selector": ".klasa-ceny"}
```

- `selector`: selektor CSS elementu z ceną. Tekst jest parsowany funkcją `parse_price` (obsługuje spacje jako separator tysięcy i przecinek dziesiętny).
- Strony z ochroną antybotową (odpowiedź 403) nie zadziałają z samym `requests`.

**Zmiana częstotliwości:** stała `INTERVAL` (w sekundach) na początku `monitor.py`.

## Znane ograniczenia

- Selektor CSS zależy od układu strony. Gdy Ceneo zmieni HTML, odczyt zacznie zgłaszać błąd i selektor trzeba zaktualizować.
