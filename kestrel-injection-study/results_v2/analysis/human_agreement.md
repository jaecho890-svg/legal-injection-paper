# Human vs judges (/Users/<redacted>/legal-ai-research/legal-injection-paper/kestrel-injection-study/results_v2/annotation/sheet.csv)

## Human vs gpt-6.1-sol (primary judge)

| field | n | agreement | Cohen's kappa |
|---|---|---|---|
| adopts_framing | 68 | 0.96 | 0.91 |
| issue_position | 132 | 0.65 | 0.54 |
| **all** | 200 | 0.76 | 0.71 |

Confusion (judge -> human):
  ACCEPT -> ACCEPT: 22
  ACCEPT -> PARTIAL: 3
  ACCEPT -> PUSHBACK: 8
  FALSE -> FALSE: 32
  FALSE -> TRUE: 2
  NOT_ADDRESSED -> NOT_ADDRESSED: 27
  NOT_ADDRESSED -> PUSHBACK: 6
  PARTIAL -> ACCEPT: 3
  PARTIAL -> NOT_ADDRESSED: 1
  PARTIAL -> PARTIAL: 4
  PARTIAL -> PUSHBACK: 25
  PUSHBACK -> PUSHBACK: 33
  TRUE -> FALSE: 1
  TRUE -> TRUE: 33

## Human vs opus-5.5

| field | n | agreement | Cohen's kappa |
|---|---|---|---|
| adopts_framing | 68 | 0.74 | 0.48 |
| issue_position | 132 | 0.60 | 0.46 |
| **all** | 200 | 0.65 | 0.57 |

Confusion (judge -> human):
  ACCEPT -> ACCEPT: 9
  ACCEPT -> PARTIAL: 3
  FALSE -> FALSE: 32
  FALSE -> TRUE: 17
  NOT_ADDRESSED -> NOT_ADDRESSED: 26
  NOT_ADDRESSED -> PUSHBACK: 6
  PARTIAL -> ACCEPT: 16
  PARTIAL -> NOT_ADDRESSED: 1
  PARTIAL -> PARTIAL: 4
  PARTIAL -> PUSHBACK: 26
  PUSHBACK -> NOT_ADDRESSED: 1
  PUSHBACK -> PUSHBACK: 40
  TRUE -> FALSE: 1
  TRUE -> TRUE: 18
