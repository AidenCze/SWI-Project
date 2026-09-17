# Rezervační systém pro parkovací místa

**Tým:** VibeCoders

## Členové týmu
- Adam Kopec
- Martin Dressler
- Pavel Michenka

## Repozitář
[GitHub repository](https://github.com/AidenCze/SWI-Project)

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

Nejjednodušší end-to-end průchod systémem pro úspěšné vytvoření rezervace parkovacího místa:

1. **POST /reservations** 
   (Uživatel odešle požadavek na rezervaci daného parkovacího místa na daný den).
2. **→ validate** 
   (Systém ověří dvě věci: 1. Místo je volné. 2. Uživatel na dnešek ještě žádné jiné místo nemá).
3. **→ persist** 
   (Systém uloží rezervaci do databáze se stavem CONFIRMED).
4. **→ return reservation ID** 
   (Systém odpoví uživateli a vrátí mu ID vytvořené rezervace).
5. **→ automated check**
   (Automatický test pošle zkušební požadavek a ověří, že API vrátilo správný HTTP status a rezervace se zapsala do databáze).