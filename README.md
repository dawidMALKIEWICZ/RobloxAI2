# Track RNG (Roblox)

Gra RNG: klikasz **Roll** i losujesz kafelki toru, od prostej (1 na 2) po **Sky Leap**
(1 na 19 mln: teleport, pętla i skok). W trybie **Build** stawiasz je na siatce swojej kwadratowej
działki i budujesz mini tor (startowo 7x7 pól i 30 elementów; Skills rozszerzają do 15x15 pól
i 190 elementów). Mini auto jeździ po torze od linii startu i zarabia za każdy przejechany kafelek.
Za pieniądze kupujesz auta (Car Dealer), style wyspy, mikstury, specjalne kostki i Skills.

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
| 4 sklepy: Car Dealer, Island Styles, Potions, Dice Shop (podejdź i wciśnij E) | `Map/Hub/Shop_*` |
| 16 kafelków toru + Start (Common → Secret) | `ReplicatedStorage/Assets/Tiles` |
| 10 mini samochodów | `ReplicatedStorage/Assets/Cars` |
| 8 stylów wyspy (kolory + dekoracje) | `ReplicatedStorage/Assets/IslandStyles` |
| UI zbudowane jako obiekty (HUD, Build, Roll, Skills, Shop, Daily, Index, Pass, sklepy) | `StarterGui/MainGui` |
| Logika serwera | `ServerScriptService/Server` |
| Klient (podpina UI pod serwer) | `StarterPlayer/StarterPlayerScripts/Client` |
| Balans gry (ceny, szanse, nagrody) | `ReplicatedStorage/Shared/GameData` |

## Edycja

Mapa, części toru, auta, style i UI są generowane skryptami Pythona z folderu `tools/`. Po zmianie
uruchom:
```
cd tools
python3 gamedata.py && python3 build_map.py && python3 build_tiles.py \
  && python3 build_assets.py && python3 build_ui.py
cd .. && rojo build -o TrackRNG.rbxl
```
Możesz też zmieniać wszystko bezpośrednio w Studio. UI to zwykłe Frame/TextButton.

## Sterowanie budowaniem

**Build** → kliknij kafelek w ekwipunku → pojawia się blueprint (zielony = można postawić).
`R` obraca, lewy klik stawia, prawy klik/`Q` anuluje, **Delete** zdejmuje kafelki z toru.
Auto startuje z linii startu na środku działki i jedzie, dopóki droga się łączy. Gdy tor wraca do
startu od tyłu, jeździ w kółko.

Podglądy (renderowane w Blenderze i przeglądarce) są w folderze `renders/`.
