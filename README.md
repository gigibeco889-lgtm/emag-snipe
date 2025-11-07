# emag-snipe
Proiectul asta este facut pentru persoanele care vor sa de-a snipe la biletul de 10 lei.
<img width="1600" height="818" alt="image" src="https://github.com/user-attachments/assets/13110ab5-3aa0-489f-9f5b-0cf27f8c1306" />

# SETUP:

1. pip install -r requirements.txt

2. Seteaza Chronium

3. Instaleaza ChromeDriver:
   - Link: https://chromedriver.chromium.org/
   - Sau:
     Ubuntu/Debian: sudo apt install chromium-chromedriver
     Arch Linux: sudo pacman -S chromedriver
     Fedora: sudo dnf install chromedriver

# CUM SE FOLOSESTE:

Start:
   python emag_bot.py

Applicatia va face asta:
- Un prompt sa alegi `[1] main` (Beach Please 10 lei), `[2] test` (Test pe un page eMag unde poti modifica adauga to cos si tot asa), `[3] Captcha Test` (Sa testezi daca merge sistemul de Captcha Resolver eMag) si `[4] cookie help` (sa pui cookie ul de la eMag)
- Da load numai la ce are domeniul, `emag`
- Da refresh pana incepe Black Friday
- Da click pe shopping cart
- Tine browser ul deschis in caz de orice si completeaza orice erroare de securirtate emag

# NOTES:
-> Momentan sistemul de mouse movment nu este pus pe versiunea asta, poti sa te duci sa il pui tu singur este destul de usor cred ca si GPT 5 poate sa-l puna nu am mai avut timp  mai pe scurt modelul local va lua tot ce trb pentru captcha si tot asa tu doar trb sa ai gata acolo toate informatile contului ( https://auth.emag.ro/user/login am vazut ca inca merge), mult succes!
