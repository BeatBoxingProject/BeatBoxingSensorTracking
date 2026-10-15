# BeatBoxing Sensor Tracking – Projektstand (Mai – Oktober 2026)

**Ziel:** Die Schlagstärke beim Schlag auf einen Boxsack messen und live an eine Unity-Anwendung übertragen.

---

## 1. Welche Ansätze gibt es?

Wir haben vier Messprinzipien recherchiert und verglichen:

| Ansatz                    | Was wird gemessen? | Vorteil | Nachteil                                                                                                                             |
|:--------------------------| :--- | :--- |:-------------------------------------------------------------------------------------------------------------------------------------|
| **IMU auf dem Handschuh** | Beschleunigung und Drehrate der Faust | günstig, mobil, erkennt auch die Schlagart (Jab, Hook …) | Kraft nur **indirekt** über F = m·a. Die „effektive Masse“ des Arms ist unbekannt, außerdem Drift und Verrutschen auf deme Handschuh |
| **Piezo / FSR am Sack**   | Druck an der Kontaktfläche | sehr schnell, genauer Zeitpunkt des Treffers | misst nur dort, wo der Sensor sitzt. FSR nichtlinear und mechanisch empfindlich                                                      |
| **Kamera-Tracking**       | 3D-Bewegung der Faust | berührungslos | braucht ≥ 1000 fps, Faust wird oft verdeckt, hoher Aufwand                                                                           |
| **Wägezelle (Load Cell)** | Kraft an der Aufhängung des Sacks | misst Kraft **direkt** in Newton, linear, robust, einfach mit Gewichten kalibrierbar | mechanischer Umbau der Aufhängung nötig, schneller ADC nötig                                                                         |

**Entscheidung:** Wir verfolgen **IMU** (für Bewegung und Schlagerkennung) und **Wägezelle** (für die eigentliche Kraft in Newton).

---

## 2. Was haben wir bisher gemacht?

| Zeitraum             | Arbeitsschritt |
|:---------------------| :--- |
| **Mai 2026**         | **IMU-System aufgebaut:** Raspberry Pi Zero 2W mit zwei BNO055-IMUs (je Handschuh eines) über einen I²C-Multiplexer (TCA9548A), weil beide Sensoren dieselbe Adresse haben. Die Daten gehen als JSON per UDP an den PC bzw. an Unity. Dazu ein Live-Plotter (Matplotlib), Fehlerbehandlung bei abgerissenen Kabeln und das Umrechnen der Sensorachsen auf das Unity-Koordinatensystem. |
| **Sept. 2026**       | **ADC eingebunden:** Waveshare AD HAT (ADS1263, 32 Bit, bis 38 kSPS) per SPI angebunden, erste Tests mit Piezo-Sensoren. |
| **Ende Sept. 2026**  | **Code umgebaut:** modulare Sensor-Architektur (`core/ad_hat/`) mit eigenen Klassen für Piezo und Wägezelle, Tara- und Kalibrierfunktion für die Wägezelle und ein Testprogramm (Kanal-Scan, Differenzmessung, Abtastraten-Benchmark, Piezo- und Wägezellen-Test). |
| **Anfang Okt. 2026** | **Aufhängungen verglichen:** theoretische Analyse, wie man den Sack mit Wägezellen instrumentieren kann (siehe Abschnitt 3). |
| **Okt. 2026**        | **Erste Messungen am Boxsack:** Wägezelle oben zwischen Decke und Sack eingebaut. Getestet einmal ohne und einmal mit Befestigung unten, die Messwerte aufgenommen und visualisiert (Ergebnisse siehe Abschnitt 4). |

---

## 3. Mögliche Aufhängungen des Boxsacks

Die Wägezelle misst nur die Kraft an der Stelle, an der sie sitzt. Wie viel von der Schlagkraft dort ankommt, hängt davon ab, wie der Sack befestigt ist.

| | **A: nur oben, unten frei**                                             | **B: oben Sensor, unten fest**                    | **C: oben + unten Sensor**                             |
| :--- |:------------------------------------------------------------------------|:--------------------------------------------------|:-------------------------------------------------------|
| Prinzip | Sack schwingt wie ein Pendel                                            | Sack wirkt wie ein Hebel                          | Kraft verteilt sich auf zwei Auflager                  |
| Ergebnis | nur Energie bzw. Impuls aus der Schwingung                              | Spitzenkraft und Impuls                           | Spitzenkraft, Impuls **und Trefferhöhe**               |
| Spitzenkraft | **schlecht:** die Trägheit des Sacks und die Füllung dämpfen den Schlag | nur berechenbar, wenn die Trefferhöhe bekannt ist | **sehr gut:** Kraft ist unabhängig von der Trefferhöhe |
| Aufwand | 1 Kanal, einfach, sicher                                                | 1 Kanal, Bodenanker mit Vorspannung               | 2 Kanäle, zweite Wägezelle, beide Seiten vorgespannt   |
| **Status** | **getestet**                                                            | **getestet** (nicht voll gespannt)                | **noch nicht getestet**                                |

---

## 4. Ergebnisse der ersten Messungen

**Variante A (unten frei):** Nach einem Schlag fängt der Sack an zu schwingen. Die Schwingung erzeugt selbst deutliche Ausschläge an der Wägezelle. Im Signal lässt sich deshalb nicht unterscheiden, ob gerade ein neuer Schlag kommt oder der Sack nur nachschwingt. Für Schlagkombinationen ist A damit nicht brauchbar.

**Variante B (unten befestigt):** Mit Befestigung unten wird das Nachschwingen deutlich kleiner und die Schläge lassen sich besser voneinander trennen. Der Sack war dabei aber nicht komplett gespannt. Ob das Problem bei voller Spannung ganz verschwindet, ist noch offen.

---

## 5. Aktuelle Probleme

1. **Spannung gegen Schlaggefühl:** Je stärker der Sack gespannt ist, desto weniger schwingt er. Ein voll gespannter Sack gibt aber kaum nach und fühlt sich an, als würde man auf Beton schlagen. Das ist unangenehm und belastet die Handgelenke. Gesucht ist eine Spannung, die genug Schwingung unterdrückt und trotzdem noch nachgibt.
2. **Mit einem Sensor ist die Trefferhöhe unbekannt:** Auch bei voll gespanntem Sack bleibt eine physikalische Grenze. Die Schlagkraft verteilt sich auf die obere und die untere Befestigung, und zwar je nachdem, auf welcher Höhe getroffen wird. Ein Sensor oben misst nur seinen Anteil. Ohne die Trefferhöhe lässt sich daraus die echte Kraft nicht berechnen. Ein Körpertreffer weiter unten wird z. B. deutlich schwächer gemessen als ein gleich starker Kopftreffer. Mit nur einem Sensor geht es also nur, wenn man die Schlaghöhe vorgibt.
3. **Variante C ungetestet:** Mit je einer Wägezelle oben und unten wäre die Trefferhöhe kein Problem mehr, weil sich die Kraft als Summe beider Messwerte ergibt und die Höhe aus ihrem Verhältnis folgt. Das ist bisher nur Theorie, dafür müsste man eine zweite Wägezelle und einen zweiten ADC-Kanal anschließen.
4. **Synchronisation bei zwei Wägezellen:** Bei Variante C werden die Messwerte oben und unten addiert. Das funktioniert nur, wenn beide Werte zum selben Zeitpunkt gehören. Da ein Schlag nur 15–30 ms dauert, braucht man eine Synchronisation im Millisekundenbereich. Eine WLAN-Übertragung ist für solche Echtzeitdaten unzuverlässig. Ohne Kabelverbindung kämen die Daten der beiden Sensoren wahrscheinlich nie genau gleichzeitig an, und selbst über LAN ist das vermutlich nicht perfekt.
5. **Unbekannte Verluste und keine Referenz:** Ein Teil der Schlagenergie geht in die Verformung des Sacks, in Wärme und in Reibung. Wie groß dieser Anteil ist, können wir nicht genau bestimmen. Außerdem haben wir kein Referenzmessgerät, gegen das wir die Schlagkraft kalibrieren könnten. Die Wägezelle lässt sich zwar statisch mit Gewichten kalibrieren, aber das sagt nichts über einen dynamischen Schlag aus. Wir können deshalb nie garantieren, dass die gemessene Kraft der tatsächlichen Schlagkraft entspricht. Vergleiche zwischen Schlägen (stärker oder schwächer) sind möglich, absolute Werte in Newton bleiben unsicher.
6. **Abtastrate:** Ein Schlag dauert nur 15–30 ms, dafür braucht man mindestens 200–400 Hz pro Kanal. Bei zwei Wägezellen muss der ADS1263 zwischen den Kanälen umschalten, dadurch halbiert sich die Rate pro Kanal ungefähr. Das müssen wir für Variante C sicherstellen.
7. **Noch keine Werte in Newton:** Die Wägezelle ist noch nicht mit bekannten Gewichten kalibriert, und die Umrechnung auf die Schlagkraft fehlt noch.
8. **IMU-Messrate:** Aktuell senden wir nur mit 20 Hz. Für die Schlagerkennung reicht das, für eine Kraftabschätzung nicht.

---

## 6. Wie könnte es weitergehen?

1. **Variante B voll gespannt testen:** prüfen, ob das Nachschwingen bei voller Spannung ganz verschwindet. Dabei schrittweise Spannung erhöhen und festhalten, ab wann sich der Sack zu hart anfühlt.
2. **Variante C aufbauen:** zweite Wägezelle unten einbauen, beide Kanäle gleichzeitig auslesen und mit Schlägen auf verschiedenen Höhen prüfen, ob die Summe wirklich unabhängig von der Trefferhöhe ist.
3. **Kalibrieren und aufzeichnen:** Wägezellen mit bekannten Gewichten kalibrieren, die Daten mit Zeitstempel speichern und pro Schlag Spitzenkraft, Impuls und Kontaktdauer auswerten.

---

**Hardware aktuell:** Raspberry Pi Zero 2W · 2× BNO055 (SEN0253) · TCA9548A · Waveshare AD HAT (ADS1263) · Piezo-Sensoren · Wägezelle DYZ-101, 500 kg