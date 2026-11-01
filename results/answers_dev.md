# Answers on dev (18 questions, bge-m3 retrieval, top 5, strict)

| metric | count |
|---|---|
| correct answer (right part cited, right fine if asked) | 10/16 (62%) |
| gold part among the retrieved sources | 11/16 (69%) |
| gold part cited | 11/16 (69%) |
| right article but wrong part cited | 2/16 (12%) |
| fine correct | 10/16 (62%) |
| abstained although ANK has the answer | 1/16 (6%) |
| abstained on unanswerable questions | 2/2 (100%) |
| invalid, cut-off or failed model outputs | 0/18 (0%) |
| model answers that passed the citation check | 15/15 (100%) |

## Correct answers by type and wording

| questions | correct |
|---|---|
| all | 12/18 (67%) |
| type: exact_reference | 1/3 (33%) |
| type: ordinary | 7/10 (70%) |
| type: unanswerable | 2/2 (100%) |
| type: version | 2/3 (67%) |
| wording: everyday | 3/6 (50%) |
| wording: legal | 9/12 (75%) |

## Resources (measured; models loaded before the first question)

| measure | value |
|---|---|
| prompt tokens, mean | 1516 |
| output tokens, mean | 224 |
| generation time (prompt and output), median / max | 7.1 s / 11.3 s |
| retrieval time, median | 44 ms |
| prompts that filled the context window | 0/18 (0%) |

## Per question

| id | type | gold | version | retrieved | final answer | checks | correct |
|---|---|---|---|---|---|---|---|
| dev-001 | ordinary | 488(1) | 2026-11-01 | 488(1), 48(3), 48(1), 53(1), 53(3) | Už triukšmą gyvenamosiose patalpose nakties metu, kai tai trikdo kitų žmonių ramybę, asmeniui gresia bauda nuo aštuoniasdešimt iki dviejų šimtų eurų pagal ANK 488 str. 1 d. | pass | yes |
| dev-002 | ordinary | 488(1) | 2026-11-01 | 488(1), 48(3), 374(1), 305(10), 48(1) | Kaimynams, kurie naktį garsiai leidžia muziką ir neleidžia miegoti, gali būti skirta bauda nuo aštuoniasdešimt iki dviejų šimtų eurų pagal ANK 488 str. 1 d. | pass | yes |
| dev-003 | exact_reference | 416(6) | 2026-11-01 | 416(6), 424(6), 424(5), 416(4), 416(3) | ANK 416 str. 6 d. numato, kad vairuotojui, kuris viršijo nustatyto greičio ribą daugiau kaip penkiasdešimt kilometrų per valandą, skiriama bauda nuo keturių šimtų penkiasdešimt iki penkių šimtų penkiasdešimt eurų. | pass | yes |
| dev-004 | version | 99(1) | 2026-01-12 | 99(1), 99(3), 96(2), 96(1), 99(2) | Už darbo užmokesčio apskaičiavimo ir mokėjimo tvarkos pažeidimą darbdavio grėsė bauda nuo 300 iki 1 400,50 eurų pagal ANK 99 str. 1 d. | pass | no |
| dev-005 | unanswerable | none | 2026-11-01 | 106(1), 188-5(1), 99(3), 95(1), 101(1) | Atsakymo į šį klausimą ANK nerasta. | no answer | yes |
| dev-007 | ordinary | 484(1) | 2026-11-01 | 484(1), 168(3), 484(2), 168(5), 168(7) | Už alkoholinių gėrimų gėrimą parke ar kitoje viešojoje vietoje gresia bauda nuo 20 iki 100 eurų pagal ANK 484 str. 1 d. | pass | yes |
| dev-008 | ordinary | 484(1) | 2026-11-01 | 484(1), 486(1), 488(1), 484(2), 168(5) | Už alkoholinių gėrimų gėrimą parke vakare gali būti skirta bauda nuo 20 iki 100 eurų pagal ANK 484 str. 1 d. | pass | yes |
| dev-009 | ordinary | 108 | 2026-11-01 | 108, 109, 152(1), 481(1), 226(1) | Už smulkią vagystę numatyta bauda nuo devyniasdešimt iki keturių šimtų eurų pagal ANK 108 str. | pass | yes |
| dev-010 | ordinary | 108 | 2026-11-01 | 130(6), 215(3), 248(6), 139(3), 209(5) | Apsaugininkams gresia bauda nuo šešiasdešimt iki vieno šimto dvidešimt eurų už nepranešimą policijai apie sulaikytą įtariamą teisės pažeidėją, tačiau jūsų asmeninėje atsakomybėje ši suma nėra taikoma. Jūs turite sumokėti už šokoladą, jei jis buvo pirkiamas be mokesčių arba neapmokestinamas. | pass | no |
| dev-011 | ordinary | 507-1 | 2026-11-01 | 507-1, 507, 508, 499(1), 481(1) | Už gydytojo ar mokytojo, teikiančio viešąsias paslaugas, garbės ir orumo pažeminimą žodžiu gresia bauda nuo penkiasdešimt iki trijų šimtų eurų pagal ANK 507 str. 1 d. | pass | yes |
| dev-012 | ordinary | 507-1 | 2026-11-01 | 71(2), 420(4), 508, 71(1), 420(5) | Jei jūsų veiksmas yra pažeminęs gydytojo garbę ir orumą, jums gali būti skirta bauda nuo devyniasdešimt iki vieno šimto keturiasdešimt eurų pagal ANK 508 str. | pass | no |
| dev-013 | ordinary | 424(3) | 2026-11-01 | 424(3), 424(2), 430, 424(6), 424(5) | Asmeniui, kuris vairuoja automobilį neturėdamas teisės vairuoti, skiriama bauda nuo trijų šimtų iki keturių šimtų penkiasdešimt eurų pagal ANK 424 str. 3 d. | pass | yes |
| dev-014 | ordinary | 424(3) | 2026-11-01 | 424(6), 424(1), 422(3), 415(2), 424(4) | Draugui, kuris dar neišlaikė vairavimo egzamino ir važinėja tėvo mašina, gali būti skirta bauda nuo trisdešimt iki penkiasdešimt eurų pagal ANK 424 str. 1 d. Jei jis vairavo neturėdamas teisės vairuoti, tai gali būti bauda nuo vieno tūkstančio vieno šimto iki vieno tūkstančio penkių šimtų eurų pagal ANK 424 str. 6 d. | pass | no |
| dev-015 | exact_reference | 419-1(1) | 2026-11-01 | 79-1(2), 79-1(1), 51(3), 51(1), 370-1(1) | Atsakymo į šį klausimą ANK nerasta. | no answer | no |
| dev-016 | exact_reference | 346(1) | 2026-11-01 | 346(3), 346(18), 346(16), 346(8), 346(19) | Pagal ANK 346 str. 18 d. asmeniui gali būti skirta bauda nuo devynių šimtų iki trijų tūkstančių dviejų šimtų eurų. 200 eurų bauda nėra minimali, todėl ji nėra leidžiama pagal šį straipsnį. | pass | no |
| dev-017 | version | 314(1) | 2026-01-12 | 314(1), 314(3), 314(5), 314(6), 314(2) | Už kultūros paveldo apsaugos reikalavimų pažeidimą asmeniui grėsė bauda nuo 150 iki 300 eurų pagal ANK 314 str. 1 d. | pass | yes |
| dev-018 | version | 547(1) | 2026-11-01 | 547(1), 547(2), 136(1), 476-1(1), 221(1) | Valstybės įstaigos vadovui, kuris atsisako teikti informaciją žurnalistams, nenurodydamas atsisakymo priežasties, nuo 2026 m. lapkričio 1 d. gresia bauda nuo šešiasdešimt iki trijų šimtų eurų pagal ANK 547 str. 1 d. | pass | yes |
| dev-019 | unanswerable | none | 2026-11-01 | 108, 226(1), 229(2), 277(1), 229(1) | Atsakymo į šį klausimą ANK nerasta. | no answer | yes |
