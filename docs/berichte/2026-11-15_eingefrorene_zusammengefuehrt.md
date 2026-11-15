# Eingefrorene Kurse in zusammengeführten Kursreihen

Erstellt 15.11.2026 09:50 mit `tools/pruefe_eingefrorene_zusammengefuehrt.py`. Kriterien vor der Suche festgehalten (docs/FUNDAMENTAL.md, „Fünfte Datenkorrektur“, Jakob 15.11.2026). Nichts wurde korrigiert.

Grundmenge: 22 Firmen mit mehr als einer gültigen Teilreihe (2488 AMD/AMD, 11199 BMS/BMS, 1166691 CMCSA/CMCSK, 1418135 DPS/KDP, 33213 EQT/EQT, 1274494 FSLR/FSLR, 898293 JBL/JBL, 833444 JCI/TYC, 1004980 PCG/PCG, 97210 TER/TER, 1308161 TFCF/TFCFA, 1103982 KFT/MDLZ, 1283699 PCS/TMUS, 1336920 SAI/LDOS, 1564708 NWSA/NWS, 1652044 GOOG/GOOGL, 1437107 DISCK/WBD, 1140536 WLTW/WTW, 4281 ARNC/HWM, 1478242 Q/IQV, 1666700 DWDP/DD, 1754301 FOX/FOXA). Funde (E1): 3.

„Übernommen“ = Tage des Laufs, an denen die zusammengeführte Reihe den Wert dieser Teilreihe nimmt (keine früher geladene Teilreihe hat den Tag). Nur solche Tage wirken in Backtest und Index-Nachbau.

| Firma | Teilreihe (Quelle) | Mitgliedschaft der Zeile | eingefroren | Tage | Kurs | erster echter Kurs danach | in der Mitgliedschaft | übernommen | bereits gekappt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 11199 | BMS (tiingo, BMS) | 2011-01-03 – 2014-12-05 | 2019-06-11 – 2019-06-28 | 12 | 57.25 | Reihenende | nein | 12 | nein |
| 11199 | BMS (tiingo, BMS) | 2019-06-07 – 2019-06-11 | 2019-06-11 – 2019-06-28 | 12 | 57.25 | Reihenende | ja | 0 | nein |
| 1437107 | DISCK (tiingo, DISCK) | 2014-08-06 – 2022-04-11 | 2022-04-14 – 2022-09-16 | 25 | 24.42 | Reihenende | nein | 25 | ja |
