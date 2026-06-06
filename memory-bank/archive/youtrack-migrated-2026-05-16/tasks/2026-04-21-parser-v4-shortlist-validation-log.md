# Parser v4 shortlist validation log

Дата: 2026-04-21 (Europe/Moscow)

Цель: не гонять одни и те же кейсы повторно и иметь явный журнал подтверждённых нормализаций.

## Status
- [x] Case 01 (art_id 3778)
  - EO: `jxeti ion kontraux iun` / `jxeti ion al iu`
  - RU: `бросаться чем-л. в кого-л.`
  - Note: `_или_` раскрываем в две EO-ветки.

- [x] Case 02 (art_id 237)
  - EO: `stiri auxton` / `konduki auxton`
  - RU: `вести автомобиль`

- [x] Case 03 (art_id 237)
  - EO: `veturi per auxto` / `veturi en auxto`
  - RU: `ехать на автомобиле`

- [x] Case 04 (art_id 273)
  - EO: `transporti per auxtoj` / `transporti per auxtomobiloj`
  - RU: `перевозить автотранспортом`

- [ ] Case 05 (art_id 312)
- [ ] Case 06 (art_id 1223)
- [ ] Case 07 (art_id 1380)
- [ ] Case 08 (art_id 1462)
- [ ] Case 09 (art_id 1467)
- [ ] Case 10 (art_id 1467)

## Next
После shortlist переход к unresolved/incomplete кейсам (в т.ч. case 17, case 41) по полному контексту строк.

## Checkpoint from chat
- Последний ранее разобранный кейс в shortlist: `art_id: 1` (`а I`), EO-альтернативы (подтверждено пользователем).

## Unresolved resolution notes (confirmed)
- `[балл`он]`:
  - при прямых скобках в EO разворачиваем варианты:
    - `botelo`
    - `ujo`
    - `cilindra ujo`
- `[авиадес`ант]`:
  - курсивные скобки в препозиции трактуем как поясняющий маркер смысла RU (label),
    а не как отдельный переводный токен.
  - Пример:
    - `(_высадка_) parasxutigo de trupoj`
    - `(_атака_) atako de parasxutaj trupoj`

## Unresolved: `[без]` (dataset truncation fixed)
- Причина unresolved: в `2026-04-21-parser-v4-hard-cases-eo-ru.md` был скопирован только фрагмент статьи `[без]`, без полного контекста.
- Статус: помечено как `incomplete/truncated in dataset`; разбор выполняется по полной строке из корпуса.

### Нормализация по подтверждённым правилам

1) Фрагмент:
- RU: `~ вс`якой прич`ины`
- EO (source): `sen ia ajn kauxzo (_или_ kialo), senkauxze, nenial;`
- Разбор:
  - `sen ia ajn kauxzo`
  - `sen ia ajn kialo`
  - `senkauxze`
  - `nenial`
- Нормализация:
  - `без всякой причины` ↔ `sen ia ajn kauxzo | sen ia ajn kialo | senkauxze | nenial`

2) Тред после `@` / ромба:
- RU: `не ~ тог`о, не ~ `этого`
- EO (source):
  - `(_немного_) iom; iomete;`
  - `(_и это имеет место_) ankaux tio havas lokon en la afero;`
  - `(_и этого нельзя отрицать_) ankaux tio ne estas neadebla; ankaux tion oni ne povas nei;`
  - `(_и это очевидно_) ankaux tio evidentas;`
- Правило:
  - слева раскрываем `~` в два RU-варианта: `не без того | не без этого`;
  - справа делим по `;`, курсивные скобки в препозиции трактуем как labels, не отдельные EO-токены.
- EO-варианты:
  - `iom`
  - `iomete`
  - `ankaux tio havas lokon en la afero`
  - `ankaux tio ne estas neadebla`
  - `ankaux tion oni ne povas nei`
  - `ankaux tio evidentas`

## Shortlist continuation notes
- Case `[адрес]` (`fari rimarkon direkte al iu`):
  - RU-скобки должны раскрываться в варианты регулярно:
    - `делать замечание в адрес кого-л.`
    - `сделать замечание в адрес кого-л.`
  - Проблема отмечена как повторяющаяся: раскрытие RU-скобок сейчас срабатывает нестабильно.

- Case `[адрес]` (extended example, resolved):
  - Source:
    - RU: `в`аше замеч`ание (сд`елано) не по ~у`
    - EO: `via kritiko havas misan (_или_ malgxustan) direkton; via rimarko estas misdirektita;`
  - Expansion rules applied on both sides:
    - RU parentheses: `(сд`елано)` => two RU variants
    - EO `_или_` in parentheses => branch into two EO variants
  - Normalized mapping:
    - `ваше замечание не по адресу`
    - `ваше замечание сделано не по адресу`
    ->
    - `via kritiko havas misan direkton`
    - `via kritiko havas malgxustan direkton`
    - `via rimarko estas misdirektita`

- Case `[ан`ал|из]` combinatorics clarification:
  - RU has two independent optional groups: `(_или_ сд`елать)` and `(кр`ови)`.
  - RU normalized variants (2x2):
    - `сдать анализ на диабет`
    - `сдать анализ крови на диабет`
    - `сделать анализ на диабет`
    - `сделать анализ крови на диабет`
  - EO side remains:
    - `fari sanganalizon pri diabeto`

- Case `[аутс`айдер]` line-merge correction:
  - Full source value: `2. _эк._ (_предприятие, не входящее в монополию_) ne monopoligita entrepreno;`
  - Interpretation:
    - `_эк._` = label
    - italic parentheses = explanatory gloss, not translation token
  - Correct pair:
    - `аутсайдер` -> `ne monopoligita entrepreno`

- Case `[ахт`и]` confirmed:
  - RU: `не ахти как` / `не ахти как хорошо`
  - EO: `ne tre bone` / `iele-trapele`

- Case `[а I]` line-break merge recovered from source (sense 11 example):
  - RU: `прошло много лет, а я прекрасно помню это событие`
  - EO variants:
    - `pasis multaj jaroj, tamen mi bonege memoras tiun eventon`
    - `pasis multaj jaroj, sed mi bonege memoras tiun eventon`
  - Note: RU->EO source formatting is irregular (manual authoring, weak indentation discipline), causing frequent false splits in multiline merge.

## Strategy note (draft)
- Предпочтительно: сначала довести стабильность EO->RU пайплайна (где структура чаще предсказуема),
  параллельно собрать правила склейки для RU->EO на корпусе проблемных примеров.
- Для RU->EO включать "strict" режим: при низкой уверенности в склейке помечать fragment as incomplete и не автоприменять.

- Case 05 `[аг`ент]` correction:
  - `(_кадров_)` is italic explanatory gloss (not translation token).
  - RU variants:
    - `агентство по найму`
    - `агентство по трудоустройству`
  - EO: `dungoficejo`

- Case 06 `[антип`ати|я]` confirmed:
  - RU: `чувствовать антипатию к кому-л.` / `испытывать антипатию к кому-л.`
  - EO: `antipatii iun`

- Case 13 `[астра]` ordering note:
  - Canonical RU in botanical usage: `астра китайская`, `астра садовая`.
  - Search aliases may include reverse order: `китайская астра`, `садовая астра`.
- Case 14 `[атака]` confirmed.

- Case 30 `[бог]` merge-fix:
  - Full source: `да поможет вам ~!, помоги вам ~!, ~ в помощь! helpu vin (_или_ al vi) Dio!;`
  - RU side stays:
    - `да поможет вам Бог`
    - `помоги вам Бог`
    - `Бог в помощь`
  - EO side corrected:
    - `helpu vin Dio!`
    - `helpu al vi Dio!`
- Cases 28, 29, 31 confirmed without changes.

- Case 38 `[а I]` merge-fix:
  - Full source: `он утверждает это, а я сомневаюсь li asertas tion, tamen (_или_ sed) mi dubas;`
  - EO normalized:
    - `li asertas tion, tamen mi dubas`
    - `li asertas tion, sed mi dubas`
- Cases 40 and 42 confirmed.

## Merge heuristic (confirmed by user)
- Для RU->EO (и в целом при multiline parse): если текущая строка перевода НЕ заканчивается `,` или `;`,
  считать это сильным сигналом продолжения на следующей строке.
- Склейка: `current_line + " " + next_line` (с нормализацией пробелов).
- Если заканчивается `,` или `;` — блок обычно завершён (если нет иных конфликтных сигналов).
- Дополнение к merge-heuristic:
  - Точка `.` также может быть валидным завершающим знаком (особенно в конце статьи/значения).
  - Эвристика завершения строки перевода: финальные `,` / `;` / `.`.

## Bracket expansion rule (critical, confirmed)
- Без пробела перед `(` => внутрисловная вариативность (orthographic/morphological), не отдельное слово.
  - Примеры:
    - `(с)делать` -> `делать` | `сделать`
    - `орангутан(г)` -> `орангутан` | `орангутанг`
    - `вын(има)ть` -> `вынуть` | `вынимать` (rule may need stem-aware morph handling)
- С пробелом перед `(` => отдельный опциональный сегмент/слово.
  - Пример:
    - `анализ (крови)` -> `анализ` | `анализ крови`
