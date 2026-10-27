# Data Proposal: Discurs instigator la ură în comentarii românești de pe social media

## 1. De ce acest dataset?

Propunem un set de comentarii în limba română de pe rețele sociale (Instagram și TikTok),
etichetate în trei clase: **neutral**, **offensive** (insulte, vulgarități la adresa unei persoane)
și **hate_speech** (atacuri asupra unui grup pe baza etniei, orientării sexuale, genului, religiei etc.).

**La ce e bun:** antrenarea și evaluarea modelelor de detecție automată a discursului instigator la ură
pentru limba română, o limbă cu puține resurse în acest domeniu.

**Cine l-ar folosi:** cercetători NLP care lucrează cu limba română, echipe de moderare de conținut,
ONG-uri care monitorizează discursul urii online.

**Ce aduce în plus:** seturile existente pentru română (ex. RO-Offense, FB-RO-Offense, CoRoSeOf)
provin din alte surse (forumuri de știri, Facebook, Twitter) și sunt colectate înainte de 2022.
Setul propus:
- va proveni de pe platforme vizuale, cu conținut recent, cu limbaj, argou și emoji specifice;
- va separa explicit limbajul *ofensator* de discursul *instigator la ură*, în loc de o etichetă binară toxic / non-toxic;
- va păstra contextul conversației (dacă un comentariu e răspuns, postarea din care face parte).

Un set existent nu ajunge pentru că modelele antrenate pe Twitter sau forumuri nu se transferă bine
pe stilul comentariilor de pe Instagram și TikTok. În plus, lipsa distincției ofensator / ură face
imposibilă moderarea diferențiată (ascundere vs. raportare).

## 2. Surse

| Sursă | Link | Licență | Dimensiune aproximativă |
|---|---|---|---|
| Comentarii la postări publice Instagram | https://www.instagram.com | Fără licență deschisă: conținutul aparține utilizatorilor ([Termenii Meta](https://help.instagram.com/581066165581870)) | [de stabilit] |
| Comentarii la clipuri publice TikTok | https://www.tiktok.com | Fără licență deschisă ([Termenii TikTok](https://www.tiktok.com/legal/terms-of-service)) | [de stabilit] |

Colectarea se va face cu scrapere proprii (Playwright). Lista URL-urilor postărilor se va păstra privat.
Etichetele și schema vor fi publicate sub **CC BY-NC 4.0**. Textul comentariilor va fi publicat doar
ca eșantion anonimizat; setul complet va fi oferit doar în scop de cercetare, la cerere.

## 3. Date sensibile

Da. Datele conțin:
- **informații personale directe:** nume de utilizator, nume afișate, @mențiuni și linkuri în text, id-uri de comentarii;
- **categorii speciale de date (GDPR, art. 9):** comentariile se referă la etnie, orientare sexuală, gen și religie.

Ce facem cu ele:
- numele de utilizator și URL-ul postării sunt înlocuite cu un hash SHA-256 cu sare secretă
  (sarea nu se salvează), iar numele afișat se elimină;
- în text, @mențiunile devin `@USER`, iar linkurile devin `URL`;
- id-ul original al comentariului nu se publică, pentru că ar permite găsirea comentariului pe platformă;
- **datele brute nu se urcă pe GitHub**: rămân doar local, la membrii echipei.

## 4. Schema

O înregistrare din setul final:

| Câmp | Tip | Descriere |
|---|---|---|
| `id` | string | identificator intern, pseudonimizat |
| `platform` | `"instagram"` \| `"tiktok"` | platforma sursă |
| `text` | string | textul comentariului, anonimizat |
| `label` | `"neutral"` \| `"offensive"` \| `"hate_speech"` | eticheta |
| `post_hash` | string | hash al postării; grupează comentariile din același fir |
| `is_reply` | bool | comentariul e răspuns la alt comentariu |
| `created_at` | string (ISO 8601) | data comentariului |

Exemple (din [eșantion](../data/sample/sample.jsonl)):

```json
{"id": "ig_61047cf03048", "platform": "instagram", "text": "Acum au parte de o discriminare pozitivă. Această etnie urăște de moarte poporul român.", "label": "hate_speech", "post_hash": "d05466543420", "is_reply": false, "created_at": "2026-02-23T11:28:54Z"}
{"id": "ig_70cf439ca976", "platform": "instagram", "text": "Esti căzut în cap? Urăști drepturile omului?", "label": "offensive", "post_hash": "dccfdbe19c73", "is_reply": true, "created_at": "2026-02-12T16:15:03Z"}
{"id": "ig_5f840d396d9b", "platform": "instagram", "text": "Ai dreptate fiecare trebuie să-și  trăiască  viața  frumos și  împlinit .", "label": "neutral", "post_hash": "0b46a33873fb", "is_reply": false, "created_at": "2026-04-17T07:51:21Z"}
```

## 5. Cum arătăm că setul e util

Antrenăm același model o dată pe un set românesc existent și o dată pe setul nostru, apoi le evaluăm
pe același set de test din comentarii Instagram/TikTok, verificat manual. Dacă modelul antrenat
pe setul nostru dă rezultate mai bune, setul acoperă un domeniu pe care cele existente nu îl acoperă.

## Eșantion

Eșantion pilot de 30 de comentarii reale, colectate și anonimizate pentru a ilustra schema: [`data/sample/sample.jsonl`](../data/sample/sample.jsonl).
