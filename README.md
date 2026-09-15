# Rezervační systém pro parkovací místa
Adam Kopec

Bc. Martin Dressler

Pavel Michenka

## CP1 walking skeleton
POST /reservations
→ validate (uživatel nemá na dnešek jinou rezervaci a místo je volné)
→ persist (uložení rezervace se stavem DRAFT/CONFIRMED)
→ return reservation ID
→ automated check (ověření vráceného HTTP statusu a dat v odpovědi)