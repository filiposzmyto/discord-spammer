# Uruchamianie projektu

To jest bot Discord napisany w Pythonie 3.11, a nie aplikacja webowa. Używaj workflow **Discord bot** z komendą `python bot.py`; nie jest potrzebny port ani podgląd webowy.

Sekret `DISCORD_BOT_TOKEN` jest pobierany z Replit Secrets. Bot rejestruje komendę `/spam` po połączeniu z Discordem. `/spam` z opcją `On` tworzy prywatną kategorię z 1–5 kanałami i daje dostęp tylko wybranym osobom/rolom oraz botowi. `speed` ma minimum 0,5 sekundy. Opcja `Off` zatrzymuje serię i automatycznie sprząta, a `Cleanup` usuwa tylko kanały oznaczone przez tego bota.

Wymagane uprawnienia bota: **Manage Channels**, **View Channels**, **Send Messages** oraz **Mention Everyone** dla niewzmiankowalnych ról. Domyślna konfiguracja znajduje się w `config.json`; wartości do skopiowania są w `config.example.json`.