# Rezervační systém pro parkovací místa
Adam Kopec

Martin Dressler

Pavel Michenka





### Lokální spuštění projektu

1. **Vytvoření a aktivace virtuálního prostředí:**
```bash
python3 -m venv venv
source venv/bin/activate  # Pro Windows použijte: venv\Scripts\activate
```

2. **Instalace závislostí**
```bash
pip install -r requirements.txt
```

3. **Spuštění serveru:**
```bash
cd src
python manage.py migrate    # inicializace databáze bez které by to nejelo (ta na githubu není, je v .gitignore)
python manage.py runserver  # samotné spuštění serveru
```



## CP1 walking skeleton
POST /reservations
→ validate (uživatel nemá na dnešek jinou rezervaci a místo je volné)
→ persist (uložení rezervace se stavem DRAFT/CONFIRMED)
→ return reservation ID
→ automated check (ověření vráceného HTTP statusu a dat v odpovědi)