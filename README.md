# Discord Spammer Bot

Bot Discord z komendami `/spam on` i `/spam off`.

Spamuje wiadomości **co 0.5 sekundy** na skonfigurowanym kanale z możliwością @mentionowania wybranych użytkowników i ról.

## Funkcje

- `/spam on` – włącza spam
- `/spam off` – wyłącza spam
- `/spam_status` – sprawdza status
- `/reload_config` – przeładowuje config bez restartu
- Uprawnienia ograniczone do wybranych użytkowników / ról
- Wiadomość konfigurowalna z `{mentions}`

## Instalacja

1. Sklonuj repo:
```bash
git clone https://github.com/filiposzmyto/discord-spammer.git
cd discord-spammer
```

2. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

3. Skopiuj pliki konfiguracyjne:
```bash
cp .env.example .env
cp config.example.json config.json
```

4. Uzupełnij `.env` tokenem bota i `config.json` swoimi ID.

5. Uruchom:
```bash
python bot.py
```

## Konfiguracja (`config.json`)

| Pole | Opis |
|------|------|
| `spam_channel_id` | ID kanału, na który ma spamować |
| `allowed_user_ids` | Lista ID użytkowników, którzy mogą używać komend |
| `allowed_role_ids` | Lista ID ról, które mogą używać komend |
| `mention_user_ids` | Lista ID użytkowników do @mentionowania |
| `mention_role_ids` | Lista ID ról do @mentionowania |
| `spam_message` | Treść wiadomości (`{mentions}` zostanie zastąpione) |

## Uprawnienia bota

Bot potrzebuje:
- Send Messages
- Use Application Commands
- Mention Everyone (jeśli chcesz mentionować role)
- Server Members Intent (włącz w Developer Portal)

## Uwagi

- Discord **nie pozwala** na wiadomości widoczne tylko dla wybranych osób na publicznym kanale. Użyj prywatnego kanału.
- Spam co 0.5s jest agresywny – Discord może nałożyć rate limit.
- Nigdy nie commituj `.env` ani `config.json` z prawdziwymi danymi.

## Licencja

MIT
