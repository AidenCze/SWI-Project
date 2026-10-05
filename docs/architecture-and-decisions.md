# Architektura a specifikace rezervačního systému ParkSys

## 1. Rozsah projektu a MVP (Minimum Viable Product)
Cílem projektu je vytvořit funkční rezervační systém pro správu firemních parkovacích míst.
* **In scope:** Autentizace uživatelů, interaktivní výběr a rezervace parkovacích míst, správa vlastních rezervací, administrátorský modul pro řízení uživatelů a globálních rezervací.
* **Out of scope:**  Automatické rozpoznávání SPZ kamerovým systémem, pronájem míst třetím stranám.

## 2. Analýza požadavků

### Funkční požadavky
Vycházejí přímo z navrženého Use Case diagramu.
* Společnou funkcí pro všechny uživatele je přihlášení do systému, které ověřuje existenci uživatele, shodu hesla a vytváří uživatelskou relaci.
* **Zaměstnanec:** Může provádět rezervaci parkovacího místa a následně provést zrušení rezervace.
* **Správce firmy:** Architektonicky dědí všechna práva běžného zaměstnance. Navíc obsluhuje přidání zaměstnance, odebrání zaměstnance a komplexní správu všech rezervací.

### Nefunkční požadavky
* **Bezpečnost:** Hesla uživatelů jsou ukládána jako zabezpečený hash a systém generuje náhodná bezpečná hesla pro nové uživatele.
* **Integrita dat a výkon:** Ošetření tzv. race condition (souběhu) při pokusu více uživatelů o stejné místo je řešeno pomocí dočasného zámku. Systém rovněž zamezuje smazání aktuálně přihlášeného účtu správce.
* **Uživatelské rozhraní:** Server-side rendering přes Django šablony.

---

## 3. Architektonická rozhodnutí (ADR)
* **ADR 1: Dědičnost uživatelských rolí**
  Pro zjednodušení autorizační logiky je architektura navržena tak, že role Správce plně dědí oprávnění Zaměstnance.
* **ADR 2: Ochrana proti souběhu transakcí (Race Condition)**
  Při kliknutí na volné místo se aktivuje dočasný zámek (např. na 5 minut), během kterého je místo pro ostatní uživatele skryto. Pokud uživatel rezervaci nepotvrdí ve stanoveném limitu, místo se opět uvolní.
* **ADR 3: Kaskádové mazání uživatelů**
  Při odebrání zaměstnance z databáze systém nejprve automaticky zruší všechny jeho budoucí rezervace, čímž se místa uvolní pro ostatní uživatele.
* **ADR 4: Restrikce manipulace s historií**
  Logika zrušení rezervace (jak pro zaměstnance, tak pro správce) explicitně kontroluje platnost termínu; historické rezervace, jejichž termín již minul, nelze rušit.

---

## 4. Použité technologie
* **Backend:** Python 3.12, Django.
* **Frontend:** Django Templates, HTML5, Bootstrap.
* **Databáze:** SQLite (vývojové prostředí).

---

## 5. Diagramy architektury a procesů

### 5.1 Use Case Diagram
![Use Case Diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/use-case.puml)

### 5.2 Activity Diagramy


* **Přihlášení do systému:** 
  ![Activity Diagram - Login](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/activity-login.puml)
* **Přidání zaměstnance:** Formulář vyžaduje pouze e-mailovou adresu, která slouží jako uživatelské jméno. V případě shody s již existujícím e-mailem v databázi se vygeneruje chybová hláška.
  ![Activity Diagram - Add Employee](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/activity-add-emp.puml)
* **Odebrání zaměstnance:**
  ![Activity Diagram - Delete Employee](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/activity-delete-emp.puml)
* **Rezervace místa:** 
  ![Activity Diagram - Reservation](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/activity-reservation.puml)
* **Zrušení rezervace zaměstnancem:** 
  ![Activity Diagram - Cancel Reservation](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/activity-cancel-reservation.puml)
* **Správa všech rezervací:** Umožňuje administrátorovi vyhledat konkrétní rezervaci podle data, místa či zaměstnance. Po odstranění objektu administrátorem systém odesílá informační e-mail dotčenému zaměstnanci.
  ![Activity Diagram - Manage Reservations](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/activity-manage-reservations.puml)