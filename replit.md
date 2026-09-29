# Uruchamianie projektu

To jest bot Discord napisany w Pythonie 3.11, a nie aplikacja webowa. Używaj workflow **Discord bot** z komendą `python bot.py`; nie jest potrzebny port ani podgląd webowy.

Sekret `DISCORD_BOT_TOKEN` jest pobierany z Replit Secrets. Bot rejestruje komendę `/spam` po połączeniu z Discordem. `/spam` z opcją `On` tworzy prywatną kategorię z maksymalnie pięcioma kanałami i daje dostęp tylko wybranym osobom/rolom oraz botowi. Opcja `Off` zatrzymuje aktywną serię bez usuwania historii.

Wymagane uprawnienia bota: **Manage Channels**, **View Channels**, **Send Messages** oraz **Mention Everyone** dla niewzmiankowalnych ról. Domyślna konfiguracja znajduje się w `config.json`; wartości do skopiowania są w `config.example.json`.