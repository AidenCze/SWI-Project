# Architektura rezervačního systému

Tento dokument popisuje návrh a architekturu systému pro rezervaci parkovacích míst.

---

## 1. Use Case Diagram
Zachycuje hlavní případy užití z pohledu zaměstnance a správce firmy.




```plantuml

@startuml
left to right direction
skinparam packageStyle rectangle

' Nastavení barev
skinparam usecase {
    BackgroundColor LightGray
    BorderColor Black
}

actor "Zaměstnanec" as emp
actor "Správce firmy" as admin

' Správce dědí práva od zaměstnance
admin -|> emp

rectangle "Rezervační systém parkování" {
    
    ' Use Casy Zaměstnance
    usecase "Zobrazení volných míst" as view
    usecase "Rezervace parkovacího místa" as reserve
    usecase "Zrušení rezervace" as cancel
    
    ' Specifické Use Casy pouze pro Správce
    usecase "Správa zaměstnanců" as manage_emps
    usecase "Správa všech rezervací" as manage_all_res
}

' Propojení aktéra Zaměstnanec
emp --> view
emp --> reserve
emp --> cancel

' Propojení aktéra Správce (zbytek dědí)
admin --> manage_emps
admin --> manage_all_res

@enduml
```





---

## 2. Sekvenční diagram
Popisuje interakci uživatele, aplikační logiky (Django views) a databáze během procesu vytváření rezervace, včetně ošetření chybového stavu.


```plantuml
@startuml
autonumber

actor Zaměstnanec as zam
participant "Šablona (Uživatelské rozhraní)" as tpl
participant "View (Aplikační logika)" as view
database "Databáze / Model" as db

note over zam, db: Předpoklad: Zaměstnanec je již úspěšně přihlášen.

== 1. Fáze: Výběr dne ==
zam -> tpl ++ : Zvolí požadované datum
tpl -> view ++ : Požadavek na načtení míst

view -> db ++ : Dotaz na neobsazená místa
db --> view -- : Seznam dostupných míst

view --> tpl -- : Předání dat k vykreslení
tpl --> zam -- : Zobrazení plánku s volnými místy

== 2. Fáze: Potvrzení místa ==
zam -> tpl ++ : Vybere konkrétní místo a potvrdí
tpl -> view ++ : Požadavek na vytvoření rezervace

view -> db ++ : Kontrola dostupnosti a zápis

alt Místo je stále volné (Úspěch)
    db --> view -- : Záznam úspěšně uložen
    view --> tpl -- : Zobrazení potvrzovací obrazovky
    tpl --> zam -- : Zpráva: "Rezervace byla úspěšná"
else Místo bylo mezitím obsazeno (Souběh)
    db --> view -- : Zápis zamítnut
    view --> tpl -- : Znovuvykreslení výběru s chybovou hláškou
    tpl --> zam -- : Upozornění: "Místo již někdo obsadil, vyberte jiné"
end

@enduml
```


---

## 3. Activity Diagram
Rozděluje rezervační proces na kroky prováděné uživatelem na frontendu a operace zpracovávané na pozadí v Djangu.


```plantuml
@startuml
skinparam ActivityBackgroundColor LightGray
skinparam ActivityBorderColor Black
skinparam defaultTextAlignment center

' Definice plaveckých drah
|Zaměstnanec|
|Systém (Django)|

|Zaměstnanec|
start
:Výběr data a času pro parkování;

|Systém (Django)|
:Dotaz do databáze na existující\nrezervace pro zadaný termín;
:Zobrazení volných a obsazených míst;

|Zaměstnanec|
:Vybrání volného místa;
:Odeslání rezervačního formuláře;

|Systém (Django)|
' Rozhodovací uzel pro kontrolu dostupnosti
if (Je vybrané místo stále volné?) then (Ano)
    :Uložení nového objektu\nReservation do databáze;
    |Zaměstnanec|
    :Zobrazení stránky s potvrzením\no úspěšné rezervaci;
else (Ne - někdo byl rychlejší)
    |Systém (Django)|
    :Vygenerování chybové hlášky;
    |Zaměstnanec|
    :Zobrazení chybové hlášky;
    :Návrat na výběr místa v mapě;
    stop
endif

|Zaměstnanec|
stop
@enduml
```
---

## 4. Class Diagram
Reprezentuje strukturu databázových modelů, jejich atributy a vzájemné relace.

```plantuml
@startuml
skinparam classAttributeIconSize 0
hide methods

enum SpotType {
    NORMAL
    DISABLED_ONLY
    EV_ONLY
}

class User <<Django Auth>> {
    + username: CharField
    + is_staff: BooleanField
}

class ParkingLot {
    + name: CharField
    + floor: IntegerField
}

class ParkingSpot {
    + number: CharField
    + spot_type: SpotType
    + is_active: BooleanField
}

class Reservation {
    + date: DateField
    + start_time: TimeField
    + end_time: TimeField
    + created_at: DateTimeField
}

' Relace a kardinalita
ParkingLot "1" -- "0..*" ParkingSpot : obsahuje >
ParkingSpot "1" -- "0..*" Reservation : je rezervováno v >
User "1" -- "0..*" Reservation : vytváří >
SpotType -left-* ParkingSpot

@enduml
```