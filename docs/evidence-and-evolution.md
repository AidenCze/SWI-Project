# C01 Engineering Spike

**Question / unknown:**
Lze naši inicializační kostru projektu stáhnout a bez problémů lokálně spustit na počítači jiného člena týmu pouze podle instrukcí v README?

**What we did:**
Zvolili jsme variantu C (Reproducible build/config). Jeden člen vytvořil základní kostru Django projektu s konfigurací virtuálního prostředí, připravil `requirements.txt` a vytvořil Pull Request. Člen druhý postupoval podle instalačních kroků.

**Observed result:**
Projekt se podařilo bez problémů nainstalovat. Samotný server úspěšně běžel na lokálním portu 8000. 

**Decision / what changes because of the result:**
Potvrdili jsme, že náš inicializační setup a sdílení přes repozitář funguje. Pull Request byl schválen, issue propojeno a projekt je připraven pro vývoj CP1.