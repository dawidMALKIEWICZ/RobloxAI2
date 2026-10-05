# Track RNG (Roblox)

Gra RNG: klikasz **Roll** i losujesz kafelki toru, od prostej (1 na 2) po **Sky Leap**
(1 na 19 mln: teleport, pętla i skok). Kafelki stawiasz w trybie **Build** na siatce swojej
działki i budujesz mini tor (startowo 7x7 pól i 30 elementów; Skills rozszerzają do 15x15 pól
i 190 elementów). Mini auto jeździ po torze od linii startu i zarabia za każdy przejechany kafelek.
Za pieniądze kupujesz auta, style wyspy, mikstury, kostki i Skills.

## Jak otworzyć

**Najprościej:** pobierz `TrackRNG.rbxl` i otwórz go w Roblox Studio (File → Open from File).
Wszystko jest już w środku.

**Przez Rojo (do dalszej pracy)** potrzebujesz **Rojo 7.6.1** (serwer i plugin w Studio).
Starsze Rojo gubi obrazki UI zapisane w nowym formacie.
```
git pull
rojo serve
```
Potem w Studio, w pluginie Rojo, kliknij **Connect**.

Testy w Studio:
- Przyciski za Robux działają za darmo **tylko w Studio**, dopóki w `tools/gamedata.py`
  (`PRODUCTS`) nie wpiszesz prawdziwych ID produktów i gamepassów.
- Zapis danych w Studio wymaga *Game Settings → Security → Enable Studio Access to API Services*.

## Co jest w grze

| Element | Gdzie |
|---|---|
| Wyspa główna (stragany, plac, wielka złota kostka) + 8 wysp graczy w morzu + mosty | `Workspace/Map` |
| 4 stragany: Cars, Island Styles, Potions, Dice (podejdź i wciśnij E) | `Map/Hub/Shop_*` |
| 16 kafelków toru + Start (Common → Secret), meshe bez nachodzenia | `ReplicatedStorage/Assets/Tiles` |
| 10 aut (im rzadsze, tym bogatsze) | `ReplicatedStorage/Assets/Cars` |
| 8 stylów wyspy (kolory trawy, klifu i plaży + dekoracje, podgląd 3D w sklepie) | `ReplicatedStorage/Assets/IslandStyles` |
| 13 kostek (x5 → x60 000 szczęścia) i 12 mikstur (łączone bonusy, timery) | `ReplicatedStorage/Shared/GameData` |
| UI (Twoje ze Studio, zapisane jako `.rbxm`) | `StarterGui/MainGui` |
| Efekty, dźwięki, muzyka, sekwencje „WOW” dla rzadkich losowań | `ReplicatedStorage/ClientVFX`, `RollReveal` |
| Logika serwera | `ServerScriptService/Server` |
| Klient (podpina UI pod serwer) | `StarterPlayer/StarterPlayerScripts/Client` |

Ustawienia gracza (muzyka, dźwięki, jakość efektów dla słabych telefonów) są w przyciskach
obok licznika pieniędzy i zapisują się na serwerze.

## Jak to jest zbudowane

Modele powstają w Blenderze jako lekkie meshe: jeden mesh z jedną wspólną teksturą-paletą plus
osobne meshe dla świecących (Neon) i szklanych części. Gotowe meshe, ikony i dźwięki są już
wgrane na Robloxa, a ich ID są w `tools/mesh_ids.json` i `tools/media_ids.json`.

| Krok | Skrypt |
|---|---|
| Kafelki toru (trasa w `tools/trackpaths.py`) | `blender/models/tiles.py` |
| Auta | `blender/models/cars.py` |
| Wyspy, hub, mosty, stragany, drzewa | `blender/models/world.py` |
| Ikony kostek i mikstur | `blender/models/item_icons.py` |
| Dźwięki i muzyka (syntezowane od zera) | `tools/sfx.py` |
| Wgranie nowych/zmienionych plików (`ROBLOX_API_KEY`, `ROBLOX_USER_ID` w zmiennych środowiskowych) | `tools/upload_assets.py meshes` / `media` |
| Generowanie modeli dla Rojo | `tools/gamedata.py`, `build_map.py`, `build_tiles.py`, `build_assets.py` |
| Poprawki UI na Twoim `MainGui.rbxm` (sklepy, pasek kostek, ustawienia) | `lune run tools/lune/patch_ui.luau` |
| Podglądy (bez Studio) | `tools/preview.py overview,hub,plot,shops,bridge` |

Pełne przebudowanie po zmianach:
```
blender-python blender/models/tiles.py      # (i cars.py / world.py / item_icons.py)
python3 tools/mutation_palettes.py          # tekstury mutacji (po każdym wypieku z nowymi kolorami)
python3 tools/upload_assets.py meshes && python3 tools/upload_assets.py media
cd tools && python3 gamedata.py && python3 build_map.py && python3 build_tiles.py \
  && python3 build_assets.py && cd ..
lune run tools/lune/patch_ui.luau
rojo build -o TrackRNG.rbxl
```

## Sterowanie budowaniem

- **Build** otwiera tylko menu budowania i nie przenosi gracza. Do teleportu służą przyciski u góry: Cars, Base, Styles.
- W menu kliknij kafelek w ekwipunku, a pojawi się blueprint (zielony = można postawić).
- `R` obraca kafelek, lewy klik stawia, prawy klik lub `Q` anuluje, **Delete** zdejmuje kafelki z toru.
- Auto startuje z linii startu na środku działki i jedzie, dopóki droga się łączy. Gdy tor wraca do startu od tyłu, jeździ w kółko.

Podglądy (rendery z Blendera) są w folderze `renders/`.

## Nowe systemy

| System | Jak działa |
|---|---|
| **Mutacje torów** | Każde losowanie może dać zmutowany kafelek: Golden x1.5, Frozen x2, Diamond x3, Neon x4, Rainbow x6, Void x10 (do zarobku z tego kafelka). Szansa rośnie lekko ze szczęściem. Kilka sztuk tego samego toru może mieć różne mutacje: w Build każda ma osobną kartę z odznaką. Zmutowany kafelek ma inną teksturę, świecenie i iskry. |
| **Fuzja kostek** | 3 takie same kostki dają 1 kostkę następnego poziomu, a w 10% przypadków „JACKPOT” przeskakuje o dwa poziomy. Przycisk **FUSE** jest na karcie kostki w sklepie i jako 🔮 na pasku kostek nad Roll. |
| **Zarabianie offline** | Po powrocie gra wypłaca 25% dochodu z czasu nieobecności (maks. 8 h) i pokazuje okno „Welcome back”. Do stawki offline nie liczą się mikstury ani bonus za znajomych. |
| **Drugie piętro** | Przycisk **🔒 2nd Floor** w menu Build (100K, drugi klik potwierdza). Zakup buduje się na oczach gracza: rosną wieże i dźwigary. W pakiecie są 2 kafelki **Sky Ramp** (spiralny wjazd). `F` lub przycisk przełącza piętro 1/2. Pod każdym kafelkiem na 2. piętrze wyrastają filary. Tor wjeżdża rampą na górę, jeździ po piętrze i zjeżdża drugą rampą. Bardzo wysokie kafelki (Sky Leap) nie zmieszczą się pod piętrem. |

### Komendy testowe (Studio lub właściciel gry)

| Komenda | Co robi |
|---|---|
| `/alltracks [n]` | +n (domyślnie 25) każdego kafelka |
| `/mutations [n]` | +n (domyślnie 2) każdego kafelka w każdej mutacji |
| `/cash [n]` | dodaje pieniądze (domyślnie 1 mld) |
| `/dice [n]` | +n każdej kostki (do testu fuzji) |
| `/potions` | włącza wszystkie mikstury |
| `/floor` | od razu odblokowuje 2. piętro (z animacją budowy) |
| `/offline [h]` | symuluje powrót po h godzinach (okno „Welcome back”) |
