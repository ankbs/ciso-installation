# Oracle Cloud Infrastructure (OCI) - Schritt-für-Schritt-Bereitstellungsanleitung

Diese Anleitung führt dich (oder deine Endkunden) durch die erstmalige Bereitstellung des sicheren M365-Compliance-Dienstes in der Oracle Cloud (OCI). Es sind keine Vorkenntnisse in Linux, OCI oder Terraform erforderlich.

---

## 🔑 Teil 1: API-Schlüssel im Oracle-Portal generieren (Einmalig)

Damit unsere Skripte und die REST-API sicher mit deinem Cloud-Konto kommunizieren können, benötigst du einen API-Schlüssel.

1. **Anmelden:** Melde dich in deinem [Oracle Cloud Portal](https://cloud.oracle.com/) an.
2. **Benutzereinstellungen öffnen:** Klicke oben rechts auf das **Profil-Symbol** (Kreis mit Personensymbol) und wähle **User Settings** (Benutzereinstellungen).
3. **API-Keys aufrufen:** Scrolle ganz nach unten und klicke auf der linken Seite unter *Resources* (Ressourcen) auf **API Keys**.
4. **Schlüssel hinzufügen:** Klicke in der Mitte auf den blauen Button **Add API Key** (API-Schlüssel hinzufügen).
5. **Schlüssel herunterladen:**
   * Wähle die Option **Generate API Key Pair** (API-Schlüsselpaar generieren).
   * Klicke auf den Button **Download Private Key** (Privaten Schlüssel herunterladen) und speichere die Datei (z. B. `oracle_api_key.pem`) sicher auf deinem PC ab.
   * Klicke danach auf den blauen Button **Add** (Hinzufügen).
6. **Konfigurationsdaten kopieren:**
   * Es öffnet sich ein Fenster namens *Configuration File Preview*.
   * Kopiere den gesamten dort angezeigten Textblock. Er sieht in etwa so aus:
     ```text
     [DEFAULT]
     user=ocid1.user.oc1..aaaaaaaaxxx...
     fingerprint=aa:bb:cc:dd:ee:...
     tenancy=ocid1.tenancy.oc1..aaaaaaaaxxx...
     region=eu-frankfurt-1
     key_file=<path to your private keyfile>
     ```
   * Klicke auf **Close** (Schließen). Du hast die Vorbereitung erfolgreich abgeschlossen!

---

## 📦 Teil 2: Infrastruktur vollautomatisch starten (OCI Resource Manager)

Wir nutzen den kostenlosen Oracle-Dienst **Resource Manager**, um das gesamte sichere Netzwerk, die Firewall, die Bastion und die VM aufzubauen. Du musst dafür nichts lokal auf deinem PC installieren.

### Schritt 1: Konfigurations-Zip erstellen
1. Navigiere auf deinem PC in den Ordner `iac/` dieses Projekts.
2. Wähle alle Dateien in diesem Ordner aus:
   * `main.tf`
   * `variables.tf`
   * `outputs.tf`
   * `cloud-init.yaml`
3. Erstelle daraus ein Zip-Archiv (z. B. `iac-deploy.zip`).

### Schritt 2: Stack in Oracle erstellen
1. Klicke im Oracle-Portal oben links auf das **Hamburger-Menü** (drei Striche).
2. Navigiere zu **Developer Services** (Entwickler-Services) -> **Resource Manager** -> und klicke auf **Stacks**.
3. Klicke auf den blauen Button **Create Stack** (Stack erstellen).
4. Konfiguriere das Setup:
   * **My Configuration (Meine Konfiguration):** Ausgewählt lassen.
   * **Stack Source:** Wähle **.ZIP file** (.ZIP-Datei).
   * **Zip-Datei hochladen:** Ziehe deine erstellte `iac-deploy.zip` per Drag-and-Drop in das Upload-Feld.
   * **Name:** Gib dem Stack einen Namen (z. B. `GRC-Infrastruktur`).
   * Klicke ganz unten auf **Next** (Weiter).

### Schritt 3: Variablen ausfüllen
Der Resource Manager hat deine Variablen automatisch erkannt. Trage nun deine Werte ein, die du in Teil 1 kopiert hast:
* **tenancy_ocid:** Füge den Wert von `tenancy` aus deinem kopierten API-Textblock ein.
* **user_ocid:** Füge den Wert von `user` aus deinem kopierten API-Textblock ein.
* **fingerprint:** Füge den Wert von `fingerprint` ein.
* **private_key_path:** Trage den Pfad ein, unter dem du deinen privaten OCI-Schlüssel (aus Teil 1) lokal gespeichert hast.
* **compartment_ocid:** Trage dieselbe ID ein wie bei `tenancy_ocid` (wenn du keine speziellen Abteilungen nutzt).
* **ssh_public_key:** Kopiere deinen SSH-Public-Key hier hinein (wird für den SSH-Zugriff benötigt).
* Klicke auf **Next** (Weiter).

### Schritt 4: Ausführen und Erstellen
1. Überprüfe die Zusammenfassung und klicke auf **Create** (Erstellen).
2. Du wirst auf die Detailseite des Stacks weitergeleitet. Klicke oben auf den Button **Apply** (Ausführen) und bestätige im sich öffnenden Fenster.
3. Oracle baut nun im Hintergrund deine gesamte GRC-Umgebung auf. Dies dauert ca. **2 bis 3 Minuten**. Sobald das Statussymbol grün wird (Succeeded), steht deine Umgebung!

---

## 🔒 Teil 3: Verbindung & Zugriff auf deine private VM (Über Bastion)

Da wir die VM aus Sicherheitsgründen komplett privat ohne offene Internet-Ports aufgesetzt haben, nutzen wir für Wartungsarbeiten (wie Linux-Updates) den **OCI Bastion Service**.

1. **Zugangsdaten auslesen:**
   * Scrolle auf deiner Stack-Detailseite ganz nach unten und klicke links auf **Outputs** (Ausgaben).
   * Hier siehst du die private IP deiner VM (z. B. `10.250.250.4`) und eine fertige Befehlszeile (`bastion_ssh_command_template`).
2. **SSH-Tunnel aufbauen:**
   * Kopiere den Befehl aus `bastion_ssh_command_template` und passe ihn an (ersetze `YOUR_SSH_PUBLIC_KEY` durch deinen SSH-Public-Key).
   * Führe den Befehl in deiner lokalen PowerShell aus. Dies baut einen verschlüsselten Tunnel über Oracle zu deiner privaten VM auf.
   * Du bist nun sicher mit der VM verbunden und kannst bei Bedarf Wartungsarbeiten durchführen (z. B. `sudo apt update`), während die VM für das restliche Internet unsichtbar bleibt.
3. **Web-Zugriff nutzen:**
   * Dein CISO Assistant startet vollautomatisch auf der VM über das cloud-init-Skript.
   * Der Zugriff auf das GRC-Dashboard erfolgt über den konfigurierten Cloudflare Tunnel verschlüsselt und geschützt.
