# Architektura rezervačního systému

Tento dokument popisuje návrh a architekturu systému pro rezervaci parkovacích míst.

---

## 1. Use Case Diagram
Zachycuje hlavní případy užití z pohledu zaměstnance a správce firmy.




![Use Case Diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/use-case.puml)





---

## 2. Sekvenční diagram
Popisuje interakci uživatele, aplikační logiky (Django views) a databáze během procesu vytváření rezervace, včetně ošetření chybového stavu.


![Use Case Diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/sequence.puml)


---

## 3. Activity Diagram
Rozděluje rezervační proces na kroky prováděné uživatelem na frontendu a operace zpracovávané na pozadí v Djangu.


![Use Case Diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/activity.puml)

---

## 4. Class Diagram
Reprezentuje strukturu databázových modelů, jejich atributy a vzájemné relace.

![Use Case Diagram](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/AidenCze/SWI-Project/main/docs/diagramy/class.puml)