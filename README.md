# Discord private spam room bot

Bot Discord z komendą `/spam`, która przy opcji `On` tworzy prywatną kategorię i do pięciu kanałów tekstowych. W każdym kanale wysyła tę samą wiadomość w serii ograniczonej do 20 partii, co około 0,5 sekundy. Opcja `Off` zatrzymuje wysyłanie, ale nie usuwa kategorii ani historii.

Widoczność kanałów:

- `@everyone` nie widzi kategorii ani kanałów;
- widzą je tylko wybrane osoby i role;
- bot ma dostęp potrzebny do wysyłania;
- administratorzy Discorda nadal mogą widzieć kanały, ponieważ Discord omija dla nich ograniczenia widoczności.

## Uruchomienie

1. Utwórz aplikację bota w [Discord Developer Portal](https://discord.com/developers/applications).
2. Dodaj sekret `DISCORD_BOT_TOKEN` w Replit albo zmienną `DISCORD_TOKEN` lokalnie.
3. Zaproś bota przez OAuth2 z zakresami `bot` i `applications.commands`.
4. Nadaj mu na serwerze: **Manage Channels**, **View Channels**, **Send Messages** oraz **Mention Everyone**, jeśli ma oznaczać niewzmiankowalne role.
5. Zainstaluj zależności:

   ```bash
   pip install -r requirements.txt
   ```

6. Skopiuj `config.example.json` do `config.json` i uzupełnij opcjonalne wartości domyślne, a następnie uruchom:

   ```bash
   python bot.py
   ```

Na Replitu użyj workflow **Discord bot** (`python bot.py`).

## Komenda `/spam`

Wybierz `On` lub `Off`. Przy `On` możesz wskazać do dwóch osób i dwóch ról oraz podać własną wiadomość. Jeżeli nie wskażesz ich w komendzie, bot użyje `private_user_ids` i `private_role_ids` z `config.json` (a dla zgodności także `mention_user_ids` i `mention_role_ids`).

Osoba uruchamiająca komendę musi mieć **Manage Server**, należeć do `allowed_user_ids`/`allowed_role_ids` albo być dopuszczona przez te ustawienia w konfiguracji. Drugi aktywny pokój na tym samym serwerze nie jest tworzony.

`{mentions}` w wiadomości zostanie zastąpione wzmiankami wybranych osób i ról. Jeśli placeholdera nie ma, wzmianki zostaną dopisane na końcu. Limit chroni przed niekończącym się wysyłaniem i rate limitami Discorda.

## Konfiguracja

`config.example.json` zawiera:

- `allowed_user_ids`, `allowed_role_ids` — kto może sterować komendą;
- `private_user_ids`, `private_role_ids` — osoby i role widzące prywatne kanały;
- `spam_category_name`, `spam_channel_prefix` — nazwy kategorii i kanałów;
- `spam_message`, `max_batches`, `interval_seconds` — wiadomość i limity.

Nie commituj `config.json`, `.env` ani prawdziwego tokena.