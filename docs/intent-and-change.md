

# Project Frame

## Reservation domain

Firemní parkovací místa.

## Purpose

Systém slouží zaměstnancům k včasnému zajištění parkovacího místa před příjezdem na pracoviště. Zabraňuje rannímu stresu z hledání volného místa a umožňuje firmě efektivně sledovat a spravovat vytíženost parkovacích kapacit.

## Users / Stakeholders

1. **Zaměstnanec (Řidič)** – Vytváří a ruší své rezervace, kontroluje dostupnost.
2. **Správce parkoviště (Admin)** – Spravuje parkovací místa (vyřazuje je z provozu např. kvůli údržbě) a má přehled o všech rezervacích.

## Core concepts

* **Reservation** (samotná rezervace s časovým oknem)
* **Parking Spot** (rezervovaný Resource – konkrétní místo, např. "A12")
* **Employee** (User)
* **Parking Zone** (logické seskupení míst, např. podzemní garáž, venkovní stání)

## Core operations

* Create reservation
* Confirm / approve reservation
* Cancel reservation
* Check availability

## Persistent state

* **Reservation ukládáme:** ID zaměstnance, ID parkovacího místa, časový interval (Datum a čas OD-DO), stav rezervace (např. DRAFT, CONFIRMED, CANCELLED).
* **Resource (Parking Spot) ukládáme:** ID místa, označení (např. "B4"), typ místa (standard, EV nabíječka, ZTP), provozní stav (dostupné / mimo provoz).

## State-changing operation

* **DRAFT → CONFIRMED** (Vytvořený požadavek je systémem ověřen proti kapacitě a pravidlům, a následně potvrzen).
* **CONFIRMED → CANCELLED** (Zaměstnanec se rozhodne nepřijet a místo uvolní).

## Common business rule

Dvě potvrzené rezervace pro stejné parkovací místo se nesmí časově překrývat.

## Domain-specific business rule

Zaměstnanec může mít v jeden kalendářní den aktivní (CONFIRMED) rezervaci maximálně na 1 parkovací místo. (Aby se zamezilo blokování více míst jedním člověkem).

## External / system boundary

**Notification Service** (Odeslání potvrzovacího e-mailu nebo push notifikace s informací o úspěšné rezervaci a přesným označením parkovacího místa).

## Assumption

Předpokládáme, že zaměstnanci budou rezervace tvořit a rušit převážně přes mobilní telefon těsně před odjezdem do práce (případně při změně plánu z domova), systém proto musí být navržen tak, aby na mobilních klientech v budoucnu reagoval rychle.

## Unknown
Zatím nevíme, jak systémově vyřešíme situaci, kdy zaměstnanec na rezervované místo nepřijede, a zda místo po určité době automaticky uvolníme pro ostatní.

## Selected future pressure
Category: C (Changeability)
# Concrete pressure:
Přidání nového typu zdroje (nabíjecí stanice pro elektromobily) s nutností validovat, zda má uživatel registrovaný elektromobil.
# Why it is relevant to our reservation system:
Parkovací infrastruktura se mění směrem k elektromobilitě a firma pravděpodobně v blízké budoucnosti vyhradí část míst pouze pro nabíjení. Náš systém na tento nový typ resource musí být připraven.
