# Track RNG (Roblox)

Gra RNG: kręcisz (SPIN) i losujesz części toru, od zwykłej prostej (1 na 2) po **Sky Leap**
(1 na 19 mln: teleport, potem pętla i skok nad wszystkim). Każdy z 8 graczy ma swoją wyspę i swój
tor, a samochód jeździ po nim i zarabia pieniądze. Za pieniądze kupujesz lepsze auta, style
wyspy, mikstury, lucky blocki i ulepszenia z drzewka.

## Jak otworzyć

**Najprościej:** pobierz `TrackRNG.rbxl` i otwórz go w Roblox Studio (File → Open from File).
Wszystko już jest w środku.

**Przez Rojo (do dalszej pracy):**
```
git pull
rojo serve
```
Potem w Studio, w pluginie Rojo, kliknij **Connect**.

Testy w Studio: przyciski za Robux działają za darmo **tylko w Studio**, dopóki w
`tools/gamedata.py` (`PRODUCTS`) nie wpiszesz prawdziwych ID produktów i gamepassów.
Zapis danych w Studio wymaga włączenia *Game Settings → Security → Enable Studio Access to API
Services*.

## Co jest w grze

| Element | Gdzie |
|---|---|
| Wyspa główna + 8 wysp graczy + mosty | `Workspace/Map` |
| 4 sklepy: Potions, Lucky Blocks, Car Dealer, Island Styles (podejdź i wciśnij E) | `Map/Hub/Shop_*` |
| 16 części toru (Common → Secret) | `ReplicatedStorage/Assets/TrackPieces` |
| 10 samochodów | `ReplicatedStorage/Assets/Cars` |
| 8 stylów wyspy (kolory + dekoracje) | `ReplicatedStorage/Assets/IslandStyles` |
| UI zbudowane jako obiekty (HUD, Shop, Daily, Index, Pass, Rebirth, Upgrades, sklepy) | `StarterGui/MainGui` |
| Logika serwera | `ServerScriptService/Server` |
| Klient (podpina UI pod serwer) | `StarterPlayer/StarterPlayerScripts/Client` |
| Balans gry (ceny, szanse, nagrody) | `ReplicatedStorage/Shared/GameData` |

## Edycja

Mapa, części toru, auta, style i UI są generowane skryptami Pythona z folderu `tools/`. Po zmianie
uruchom:
```
cd tools
python3 gamedata.py && python3 build_map.py && python3 build_track.py \
  && python3 build_assets.py && python3 build_ui.py
cd .. && rojo build -o TrackRNG.rbxl
```
Możesz też zmieniać wszystko bezpośrednio w Studio. UI to zwykłe Frame/TextButton.

Podglądy (renderowane w Blenderze i przeglądarce) są w folderze `renders/`.
