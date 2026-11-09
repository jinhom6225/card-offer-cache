# card-offer-cache

카드 보너스 알림 앱이 읽는 **미국 신용카드 보너스 데이터**입니다.

진호님이 `data/cards.yaml` 하나를 GitHub 웹에서 고치면, GitHub Actions가 검증한 뒤 `docs/cards_v1.json`을 만들어 GitHub Pages(`https://jinhom6225.github.io/card-offer-cache/cards_v1.json`)로 배포합니다. 검증에 실패하면 JSON은 그대로 두고 텔레그램으로 오류를 알립니다. 자세한 내용은 아래 "앱 JSON 만들기와 배포"를 보세요.

- 카드사 페이지를 자동으로 긁어 오지 않습니다. 모든 숫자는 사람이 공식 페이지를 보고 적습니다.
- 커뮤니티(마일모아, Doctor of Credit, Frequent Miler, Reddit, The Points Guy) 내용과 단축 주소(bit.ly 등)는 이 파일에 **절대 넣지 않습니다**. 검증기가 막습니다.
- 지금 `data/cards.yaml`의 2장은 형식 확인용 **샘플(가짜)** 입니다. 실제 30종으로 교체할 예정입니다.

## GitHub 웹에서 고치는 법

1. 저장소에서 `data/cards.yaml`을 엽니다 → 오른쪽 위 연필(✏️ Edit this file) 버튼.
2. 고칠 카드를 찾아 값을 바꿉니다. **들여쓰기(앞쪽 빈칸)는 그대로** 두세요. 탭 대신 스페이스만 씁니다.
3. 아래 **Commit changes…** → 메시지(예: `Update sample-travel-card bonus`) → **Commit changes**.
4. 1–2분 뒤 Actions가 끝납니다. 검증에 실패하면 텔레그램으로 오류 목록이 오고, 앱 데이터(`docs/cards_v1.json`)는 바뀌지 않습니다. 오류 줄을 보고 다시 고치면 됩니다. 성공하면 봇(`github-actions[bot]`)이 `docs/cards_v1.json`만 커밋합니다.

오류 메시지는 이렇게 나옵니다. `카드 id → 항목 경로: 설명` 순서입니다.

```
[오류] sample-travel-card → bonus.current.min_spend: 숫자만 적어 주세요(쉼표·$·% 없이, 예: 4000).
[경고] 전체 → cards: 카드가 2장입니다(출시 기준 30장). 배포는 막지 않습니다.
```

## 카드 한 장의 항목

| 항목 | 뜻 | 예 / 규칙 |
|---|---|---|
| `id` | 카드 고유 이름(앱 내부용) | 소문자·숫자·`-`만. `chase-sapphire-preferred`. 카드끼리 겹치면 안 됨. **한 번 정하면 바꾸지 않기**(알림 기준) |
| `name` | 카드 공식 영문 이름 | `Sample Travel Rewards Card` |
| `issuer` | 발급사 이름 | 아래 "발급사와 공식 도메인" 표의 7개 중 하나를 **글자 그대로**(`Chase`, `American Express` …) |
| `segment` | 개인/비즈니스 | `personal` 또는 `business` |
| `official_url` | 카드사 **기본 상품 페이지** | `https://`로 시작, **그 카드 `issuer`의** 도메인만 |
| `last_verified` | 진호님이 공식 페이지를 마지막으로 확인한 날 | `2026-11-09` (미래 날짜 불가) |
| `sources` | 검수용 출처 주소 목록(앱에는 안 나감) | `https://` 주소 1개 이상(아래 "주소 규칙") |
| `annual_fee.amount` | 연회비(달러) | `95`, 없으면 `0` |
| `annual_fee.first_year_waived` | 첫해 면제 여부 | `true` / `false` |
| `foreign_tx_fee_pct` | 외화 수수료(%) | `0`, `2.7`, `3` |
| `bonus.current` | **지금** 공식 페이지에 나온 보너스 | 아래 "보너스 적는 법" |
| `bonus.current.min_spend` | 최소 사용 금액(달러) | `4000` |
| `bonus.current.spend_months` | 그 금액을 써야 하는 기간(개월) | `3` |
| `bonus.usual` | **평소** 보너스(진호님 기준값) | `parts`만 필수 |
| `elevated` | "평소보다 높음" 표시 | 아래 "높음 표시" |
| `earn` | 카테고리별 적립률 | `category_en`, `category_ko`, `rate`, `unit` |
| `benefits` | 주요 혜택(크레딧, 보험, 라운지 등) | `en`, `ko`. 비워 둬도 됨(`[]`) |

### 발급사와 공식 도메인

`issuer`는 이 7개 중 하나만 쓸 수 있고(대소문자·띄어쓰기까지 똑같이), `official_url`은 **그 발급사의 도메인**(또는 하위 도메인, 예: `creditcards.chase.com`)이어야 합니다. 예: `issuer: Chase`인데 `official_url`이 `americanexpress.com`이면 오류.

| `issuer` | 도메인 |
|---|---|
| `Chase` | `chase.com` |
| `American Express` | `americanexpress.com` |
| `Citi` | `citi.com` |
| `Capital One` | `capitalone.com` |
| `Discover` | `discover.com` |
| `Wells Fargo` | `wellsfargo.com` |
| `Bank of America` | `bankofamerica.com` |

### 주소 규칙 (`official_url`, `sources` 모두)

- `https://`로 시작해야 합니다.
- 주소 앞뒤·중간에 빈칸, 탭, 보이지 않는 글자, 역슬래시(`\`)가 있으면 안 됩니다. 복사할 때 딸려 온 빈칸을 지워 주세요.
- `아이디@`나 `아이디:비밀번호@`가 들어간 주소는 안 됩니다(`https://chase.com@evil.io`처럼 속이는 주소 방지).
- 도메인은 영문 소문자·숫자·`.`·`-`만(대문자는 자동으로 소문자로 봅니다). `*`, `%`, `_`, `[::1]` 같은 IPv6 주소는 안 됩니다.
- 포트는 쓰지 않거나 `:443`만 됩니다(`:8443` 등은 오류).
- 단축 주소(`bit.ly`, `tinyurl.com`, `t.co`, `goo.gl`, `ow.ly`, `is.gd`, `buff.ly`, `rebrand.ly`, `lnkd.in`)는 안 됩니다. 원래 주소를 적어 주세요.

`_ko`로 끝나는 한국어 항목(`note_ko`, `category_ko`, `ko`)은 **비워도 됩니다**(`""`이나 아예 빼기). 앱이 영어로 보여 줍니다. `note_en`도 선택입니다.

### 보너스 적는 법 (`parts`)

보너스는 여러 부분으로 적을 수 있습니다. 각 부분은 `value`(0보다 큰 숫자) + `unit`입니다.

| `unit` | 뜻 |
|---|---|
| `points` | 포인트 |
| `miles` | 마일 |
| `cash` | 캐시백(달러) |
| `free_night` | 무료 숙박(박 수) |
| `credit` | 크레딧(달러) |
| `percent_match` | 첫해 적립 매칭(%, 예: Cashback Match 100) |

```yaml
    bonus:
      current:
        parts:
          - value: 80000
            unit: points
          - value: 1
            unit: free_night
        min_spend: 4000
        spend_months: 3
        note_en: "Up to 80,000 points (as high as offer)"
        note_ko: "최대 80,000 포인트"
      usual:
        parts:
          - value: 60000
            unit: points
```

"as high as", Cashback Match 세부, 첫해 추가 적립처럼 숫자 하나로 안 되는 내용은 `note_en`/`note_ko`에 글로 적습니다.

`earn`의 `unit`은 `points`, `miles`, `cash`(= % 캐시백) 중 하나입니다. 예: 여행 3배 포인트 → `rate: 3, unit: points` / 1.5% 캐시백 → `rate: 1.5, unit: cash`.

## "평소보다 높음" 표시 (`elevated`)

보너스가 평소보다 높은지는 **진호님이 직접** 판단해서 표시합니다(자동 비교 없음).

```yaml
    elevated:
      start: 2026-11-01   # 높아진 것을 확인한 날 (= 알림 기준)
      end: 2026-12-31     # 카드사가 밝힌 종료일. 모르면 null 또는 줄 삭제
```

- **평소 상태**: `elevated` 블록을 통째로 지우거나 `elevated: null`.
- **높아짐을 처음 발견**: `elevated`를 넣고 `start`를 오늘 날짜로. → 앱 사용자에게 알림이 갑니다.
- **이미 높음인데 보너스가 더 오름**(예: 75,000 → 90,000): `bonus.current`를 고치고 **`start`를 오늘 날짜로 바꾸기**(**`start`가 이미 오늘이면 어제 날짜로** — 미래 날짜는 쓸 수 없고, 같은 날짜면 오퍼 id가 그대로라 다시 알리지 않습니다). `start`가 바뀌어야 새 오퍼로 보고 다시 알립니다. `start`를 그대로 두면 "오타 정정"으로 보고 알리지 않습니다.
- **보너스가 오르지 않았으면 `start`를 바꾸지 마세요.** `start`만 바뀌어도 앱 사용자에게 다시 알림이 갑니다(빌드가 경고를 보냄).
- **보너스가 내려감·끝남**: `bonus.current`를 고치고 `elevated`를 지우면 됩니다. 알림은 가지 않습니다.
- **끝났다가 다시 열림**: 새로 `elevated`를 넣고 `start`를 오늘로(이미 오늘이면 어제로). 새 오퍼로 다시 알립니다. 예전 `start`를 그대로 두고 `end`만 늘리면 같은 오퍼로 보고 알리지 않습니다(종료일 연장일 때만 이렇게).
- `start`는 미래 날짜를 쓸 수 없습니다(오늘까지만, 미국 서부 기준).
- `bonus`·`elevated` 안에는 위 표에 있는 항목만 쓸 수 있습니다. 오타(`ends`, `min_spnd` 등)는 **오류**입니다(오퍼가 조용히 틀어지는 것을 막기 위해).
- `end`가 지나면 매일 도는 빌드가 앱 JSON에서 자동으로 "종료"로 바꿉니다(종료일 **다음 날 0시, 미국 서부 기준**부터). `cards.yaml`은 봇이 고치지 않으니, 텔레그램 "자동 종료된 오퍼" 알림을 보면 `elevated`를 지우고 `bonus.current`를 평소 값으로 정리하세요.
- `end`는 `start`보다 앞설 수 없습니다(같은 날은 가능).

`last_verified`는 공식 페이지를 확인할 때마다 그날로 바꿔 주세요. 날짜 기준은 **미국 서부(LA) 시간**입니다.

## 검증기가 막는 것 (오류 → 배포 안 됨)

- 필수 항목이 없거나 비어 있음 (`_ko`·`note_en` 제외)
- `id` 형식이 틀림(대문자, `_`, 빈칸, 한글 등) 또는 다른 카드와 중복
- `segment`, `unit`이 허용 값이 아님
- `issuer`가 위 표의 7개가 아님
- 주소 규칙 위반(`https://` 아님, 빈칸·역슬래시·`아이디@`, 443 외 포트, 이상한 도메인 글자, 단축 주소)
- `official_url`이 그 카드 `issuer`의 도메인이 아님. `chase.com.evil.io` 같은 흉내 주소도 거부
- **어느 항목에든**(항목 이름 포함) 커뮤니티 이름·주소가 있음 — `sources`, 메모 포함. 막는 것: milemoa/마일모아, doctorofcredit/Doctor of Credit/닥터오브크레딧, frequentmiler/프리퀀트 마일러, reddit/레딧/`r/churning` 같은 게시판 표기, thepointsguy/The Points Guy/더 포인츠 가이. `%72eddit`처럼 % 인코딩하거나 전각 글자(`ｒｅｄｄｉｔ`)로 써도 잡습니다. (`크레딧`은 괜찮습니다.)
- `last_verified` 또는 `elevated.start`가 미래 날짜
- `elevated.end`가 `start`보다 앞섬
- `bonus`·`elevated` 안의 알 수 없는 항목(오타)
- 신용 판단을 암시하는 금지 문구(대소문자·띄어쓰기·하이픈·전각 글자 무시):
  - 영어: `pre-approved`/`preapproved`, `pre-qualified`, `guaranteed approval`/`approval guaranteed`/`guaranteed to be approved`/`guaranteed acceptance`, `instant approval`, `no credit check`/`without a credit check`, `approval odds`, `best card for you`/`best card for your ...`
  - 한국어: `사전 승인`/`사전승인`, `승인 보장`/`승인을 보장`, `무조건 승인`, `신용조회 없음`/`없이`/`불필요`, `승인 가능성`/`승인될 가능성`/`승인 확률`
  - `guaranteed`는 **승인과 붙을 때만** 막습니다. "Guaranteed 4PM late checkout" 같은 혜택은 그대로 적어도 됩니다. "best card for young adults"처럼 다른 단어의 일부인 경우도 괜찮습니다.
- 숫자 자리에 글자(`4,000`, `$95`, `3%`), `.nan`·`.inf`, 글자 자리에 yes/no·숫자·날짜, 존재하지 않는 날짜(`2026-02-30`)
- 카드가 한 장도 없음

**경고만 (배포는 됨):** 카드가 30장이 아님 · `bonus`·`elevated` 밖의 알 수 없는 항목 이름(오타 가능성, 예: `elevaetd`).

**파일을 아예 읽지 않는 경우(오류, "N번째 줄"을 알려 줌):** YAML 문법 오류 · 같은 항목 이름이 두 번 · `0500`/`1:30`/`0x1f` 같은 숫자 · 달력에 없는 날짜 · 별칭(`&이름`/`*이름`) · UTF-8이 아닌 파일.

## YAML 함정 (꼭 읽어 주세요)

- 숫자는 **쉼표·$·% 없이**: `4000` (O) / `4,000`, `$4000` (X). 큰 숫자는 `75000` 또는 `75_000`.
- 숫자를 **0으로 시작하지 마세요**: `0500`은 YAML이 8진수(320)로 바꿉니다. `1:30`은 90(60진수)이 됩니다. 검증기가 이런 값을 오류로 막으니 `500`처럼 숫자만 적어 주세요. 글자로 쓰려면 따옴표: `"1:30"`.
- 값이 딱 `yes`, `no`, `on`, `off`, `true`, `false` 하나면 YAML이 참/거짓으로 바꿉니다. 글자로 쓰려면 따옴표: `ko: "no"`. (`No Fee Card`처럼 다른 글자가 붙은 문장은 괜찮습니다.) 숫자·날짜만으로 된 글자도 마찬가지로 따옴표.
- `:`이나 `#`이 들어간 설명은 따옴표로 감싸세요: `note_en: "Earn 3x: travel"`.
- 날짜는 `2026-11-09` 형식(따옴표 있어도 없어도 됨). 시각은 넣지 않습니다.
- 같은 항목 이름을 두 번 쓰면(예: `elevated` 안에 `start`가 두 줄) **오류**입니다. 메시지 예: `6번째 줄: 'start' 항목이 두 번 있습니다.` 줄 번호는 **두 번째로 나온 줄**입니다. 둘 중 하나를 지우세요. 맨 위 `cards:`가 두 번 있어도 같습니다.
- `&이름`·`*이름`(별칭)은 쓰지 마세요. 값을 직접 적어야 합니다.
- 파일은 UTF-8로 저장합니다(GitHub 웹에서 고치면 자동으로 UTF-8).

## 앱 JSON 만들기와 배포 (`docs/cards_v1.json`)

### 언제 만들어지나

| 실행 | 언제 | 하는 일 |
|---|---|---|
| 데이터 수정 | `data/`, `scripts/`, `requirements*.txt`, `.github/workflows/build-cards.yml`을 main에 커밋할 때마다 | 테스트 → 검증 → JSON 생성 → 바뀌었으면 커밋 → 빌드 경고가 있으면 텔레그램 |
| 매일 | 10:23 UTC (= 미국 서부 02:23 PST / 03:23 PDT, 한국 19:23) | 위와 같음 + 자동 종료 반영 + 확인 공백·높음 표시 누락 보고 + 성공 요약 |
| 수동 | Actions → **Build cards JSON** → Run workflow | 매일 실행과 같음. `force_fail`을 켜면 일부러 실패(실패 알림 확인용) |

GitHub 예약 실행은 몇 분~몇십 분 늦게 시작할 수 있습니다. 같은 workflow는 한 번에 하나만 돕니다(`concurrency: build-cards`).

### 만드는 순서 (`scripts/build_cards.py`)

1. `data/cards.yaml`을 검증합니다(위 "검증기가 막는 것"과 같은 규칙). **오류가 하나라도 있으면 기존 `docs/cards_v1.json`을 한 바이트도 바꾸지 않고** 실패합니다.
2. 카드마다 앱에 필요한 항목만 골라 정해진 순서로 적습니다. `sources`와 알 수 없는 항목은 빠지고, 비어 있는 한국어 설명(`note_ko`, `category_ko`, `ko`)과 빈 `note_en`은 **키째 생략**합니다(앱이 영어로 보여 줌).
3. `elevated`가 있으면 **오퍼**를 만듭니다. 오퍼 id = `카드id@start날짜`(예: `chase-sapphire-preferred@2026-11-09`). 앱은 처음 보는 오퍼 id가 "높음"이면 알림을 한 번 보냅니다.
   - "높음" = `elevated`가 있고 `end`가 비었거나 `end`가 오늘(미국 서부) 이후. `end`가 지나면 `status: "ended"`, `ended_auto: true`.
4. 직전 `docs/cards_v1.json`과 비교해 카드별 **변동 기록**(`history`)을 붙입니다. 한 빌드에 카드당 최대 1건, 카드당 최근 20건만 남깁니다. 이전 기록은 `date`, `type`, `current_parts`(`value`, `unit`)만 옮깁니다. `parts`는 **순서와 상관없이** 비교합니다(순서만 바꾸면 변동 아님).
   - `elevated`: 새 "높음" 오퍼가 생김(처음 표시, `start`를 바꾼 상향, 끝났다 다시 열림)
   - `ended`: "높음"이 끝남(`elevated`를 지웠거나 종료일이 지남)
   - `changed`: 그 밖에 `bonus.current.parts`가 바뀜
5. 저장은 임시 파일에 쓴 뒤 한 번에 바꿔치기합니다(반쯤 쓴 파일이 배포되지 않음).

**바뀐 게 없으면 파일을 다시 쓰지 않습니다.** `generated_at`만 빼고 새로 만든 글자(바이트)가 기존 파일과 똑같으면 그대로 두므로 커밋도 생기지 않고 Pages ETag도 그대로입니다. 값이 같아도 표기가 다르면(예: `75000.0` → `75000`, 들여쓰기·줄바꿈 차이) 다시 씁니다. 그래서 `generated_at`은 "JSON 파일이 마지막으로 바뀐 빌드 시각"이고, 매일 바뀌지는 않습니다.

이전 `docs/cards_v1.json`이 깨졌거나 모양이 다르면(예: `offer`가 객체나 `null`이 아님, `bonus.current.parts`·`history` 모양이 다름) 변동 기록을 지키기 위해 빌드를 멈추고 `[오류]`로 알립니다. 그 밖의 예기치 못한 오류도 `[오류] 예기치 못한 오류: 종류: 내용` 한 줄로 텔레그램에 옵니다.

### JSON 맨 위 항목

| 항목 | 뜻 |
|---|---|
| `schema` | 형식 번호. 지금은 `1` |
| `generated_at` | JSON 내용이 마지막으로 바뀐 빌드 시각(UTC, `...Z`) |
| `data_updated_at` | **`data/cards.yaml`을 마지막으로 커밋한 시각**(UTC). 앱 홈의 "최근 업데이트"는 이 값을 씁니다 |
| `cards` | 카드 목록(`cards.yaml` 순서 그대로). 카드마다 `offer`(없으면 `null`)와 `history` |

**숫자 항목은 정수와 소수가 섞입니다.** `75000.0`처럼 소수점 아래가 0인 값은 정수(`75000`)로 내보내고, `2.7`·`1.5`처럼 진짜 소수는 소수 그대로 둡니다(`parts[].value`, `min_spend`, `spend_months`, `annual_fee.amount`, `foreign_tx_fee_pct`, `earn[].rate`). 앱(Dart)은 이 값들을 `as int`가 아니라 **`num`으로 읽어야** 합니다(`(json['rate'] as num)`). `spend_months`는 검증에서 정수만 받습니다(`2.5`는 오류).

### 보너스가 바뀌었을 때 `start` 규칙 (D3)

**보너스가 더 오르면 `elevated.start`를 오늘 날짜로 바꾸세요(`start`가 이미 오늘이면 어제 날짜로).** 그래야 새 오퍼 id가 생겨 앱 사용자에게 다시 알림이 갑니다.

`start`를 그대로 둔 채 "높음" 오퍼의 `bonus.current.parts`를 바꾸면 빌드는 그대로 진행되고(오타 정정일 수 있으므로) 텔레그램으로 이런 경고가 옵니다.

```
[경고] chase-sapphire-preferred: '높음' 오퍼(chase-sapphire-preferred@2026-11-01)의 보너스가 75,000 points → 90,000 points로 바뀌었는데 elevated.start는 그대로입니다. 보너스가 더 올랐다면 start를 오늘 날짜로(start가 이미 오늘이면 어제 날짜로) 바꿔야 앱 사용자에게 다시 알림이 갑니다(오타 정정이면 그대로 두세요).
```

상향이었다면 `start`를 오늘(이미 오늘이면 어제)로 바꿔 다시 커밋하고, 오타 정정이었다면 무시하면 됩니다.

### 빌드 경고 (빌드는 계속됨, 데이터 수정 실행에서도 바로 텔레그램)

| 경고 | 언제 | 할 일 |
|---|---|---|
| `[경고] <id>: '높음' 오퍼(...)의 보너스가 ... 바뀌었는데 elevated.start는 그대로입니다` | 위 D3 | 상향이면 `start`를 오늘(이미 오늘이면 어제)로 |
| `[경고] <id>: 끝났던 오퍼가 같은 start로 다시 열렸습니다` | 직전 빌드에서 자동 종료(`end`가 지남)였던 오퍼가 같은 `start`로 다시 "높음"이 됨(예: `end`를 늦춤). `elevated`를 지웠다가 같은 `start`로 다시 넣은 경우는 잡지 못하니, 다시 넣을 때는 항상 `start`를 오늘로 | 다시 열린 것이면 `start`를 오늘(이미 오늘이면 어제)로. 종료일 연장이면 무시 |
| `[경고] <id>: start가 바뀌어 사용자에게 다시 알림이 갑니다` | "높음" 중에 `start`가 바뀌었는데 보너스가 오르지 않음(단위별로 모두 같거나 낮고 새 단위 없음) | 오르지 않았다면 `start`를 되돌리기 |
| `[경고] <id>: 카드가 cards.yaml에서 빠져 앱에서 사라지고 변동 기록(N건)도 지워졌습니다` | 이전 JSON에 있던 카드가 없어짐(**`id`를 바꾼 경우도 포함**) | 실수면 `cards.yaml`을 되돌리기 |
| `[경고] 이전 JSON 없음(첫 빌드): ...` | `docs/cards_v1.json`이 없을 때(첫 빌드). 요약 줄에도 `이전 JSON 없음(첫 빌드)` | 첫 빌드가 아니면 git에서 파일 되돌리기 |

### 텔레그램 메시지 뜻

모든 메시지는 서식 없는 글자(plain text)로 보냅니다. 시크릿 `TELEGRAM_BOT_TOKEN`·`TELEGRAM_CHAT_ID`가 없으면 보내지 않습니다(로그에 경고만).

| 메시지 | 언제 | 할 일 |
|---|---|---|
| `[실패] card-offer-cache 빌드 실패 (...)` + `[오류] ...` 목록 | 실패할 때마다(검증·테스트·저장·push 실패, 예기치 못한 오류, `force_fail`) | 오류 줄대로 `cards.yaml`을 고쳐 다시 커밋. 목록이 없으면 링크의 실행 로그 확인 |
| `[성공] card-offer-cache 빌드` + `요약: 카드 N장 · 높음 N개 · 자동 종료 N개 · 경고 N개 · ...` | 매일 실행·수동 실행이 성공했을 때. `JSON 커밋: true`면 앱 데이터가 바뀜 | 없음 |
| `[경고] ...` | 위 "빌드 경고"(데이터 수정 실행에서도 바로 옴) | 표의 할 일대로 |
| `마지막 확인이 7일 넘은 카드 N장` | 매일·수동 실행. `last_verified`가 8일 이상 지난 카드(7일째까지는 괜찮음) | 공식 페이지 확인 후 `last_verified`를 오늘로 |
| `종료일이 지나 자동 종료된 오퍼 N개` | 매일·수동 실행. 정리할 때까지 매일 다시 옴 | `elevated`를 지우고 `bonus.current`를 평소 값으로 |
| `평소보다 높은 보너스인데 '높음' 표시가 없습니다 — elevated를 넣거나 current를 평소 값으로 되돌리세요` | 매일·수동 실행. `elevated`가 없는데 `bonus.current.parts`가 `bonus.usual.parts`와 다른 카드(순서 무관) | 높아진 것이면 `elevated`를 넣고, 아니면 `current`를 평소 값으로 |

빌드 경고·확인 공백·자동 종료·높음 표시 누락은 `card-offer-cache 확인 필요 (날짜, 미국 서부 기준)` 아래에 한 메시지로 묶여 옵니다.

### 처음 한 번 설정 (진호님)

1. **Pages 켜기:** Settings → Pages → Build and deployment → Source: **Deploy from a branch** → Branch: **main**, 폴더 **/docs** → Save. 첫 빌드 뒤 `https://jinhom6225.github.io/card-offer-cache/cards_v1.json`이 열리는지 확인.
2. **시크릿:** Settings → Secrets and variables → Actions → New repository secret → `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. **확인:** Actions → Build cards JSON → Run workflow 두 번(한 번은 그대로, 한 번은 `force_fail` 켜고) → 성공·실패 텔레그램이 둘 다 오는지 확인.

예약 실행은 공개 저장소에서 60일 동안 활동이 없으면 GitHub가 멈추는데, workflow의 `keepalive` job이 매번 다시 켜 둡니다.

보안: workflow 전체 권한은 비워 두고(`permissions: {}`) 빌드 job만 `contents: write`, keepalive job만 `actions: write`를 받습니다. checkout은 토큰을 남기지 않고(`persist-credentials: false`), 커밋 단계의 pull/push에서만 토큰을 씁니다. 봇은 `docs/cards_v1.json` 한 파일만 커밋합니다. Actions는 커밋 SHA로 고정했고, CI 설치는 해시를 고정한 `requirements-ci.txt`(`pip install --require-hashes`)를 씁니다.

## 로컬 실행·테스트

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/validate.py                       # data/cards.yaml 검증 (오류면 exit 1)
.venv/bin/python scripts/validate.py path/to.yaml --today 2026-11-09
.venv/bin/python scripts/build_cards.py --output /tmp/cards_v1.json --warnings-file /tmp/warn.txt   # 시험 빌드(docs/는 안 건드림)
.venv/bin/python scripts/staleness.py --cards /tmp/cards_v1.json --warnings-file /tmp/warn.txt --daily  # 텔레그램 보고 글 미리 보기
.venv/bin/python -m unittest discover -s tests -v          # 네트워크 없이 단위 테스트
.venv/bin/python -m coverage run -m unittest discover -s tests && .venv/bin/python -m coverage report   # 80% 미만이면 실패(.coveragerc)
```

Python 3.11 이상(Actions는 3.12). 의존성은 `requirements.txt`(로컬 개발용, PyYAML·defusedxml·coverage)에 버전을 고정했습니다. CI는 `requirements-ci.txt`(PyYAML·defusedxml만, 파일 해시까지 고정)를 쓰고 커버리지 없이 `unittest`만 돌립니다. 버전을 바꾸면 두 파일을 함께 바꾸고, `requirements-ci.txt`의 해시는 PyPI(`https://pypi.org/pypi/<이름>/<버전>/json`)에서 다시 받아 적습니다. YAML은 `yaml.SafeLoader`를 바탕으로 한 전용 로더(`CardLoader`)로만 읽습니다. 파이썬 태그는 여전히 막히고, 위의 중복 항목·이상한 숫자·별칭·없는 날짜를 줄 번호와 함께 거부합니다.

## 파일 구조

```
data/cards.yaml          # 진호님이 고치는 카드 데이터
data/card_aliases.yaml   # RSS 신호용 카드 별칭 사전(다음 단계에서 채움, 앱에는 안 나감)
scripts/validate.py      # 검증 CLI
scripts/build_cards.py   # cards.yaml → docs/cards_v1.json 빌더
scripts/staleness.py     # 텔레그램 확인 보고(빌드 경고, 7일 확인 공백, 자동 종료, 높음 표시 누락)
scripts/cardlib/         # schema(검증 진입점), loader(YAML 읽기), fields(항목 규칙), urls(주소·발급사 도메인),
                         # phrases(금지 문구·커뮤니티·단축 주소 패턴), rules(모든 글자 검사), issues,
                         # offers(오퍼 id·자동 종료), parts(보너스 parts 비교·숫자 정리),
                         # history(변동 기록), offer_warnings(D3·재개·start 변경·카드 삭제 경고),
                         # payload(JSON 모양·저장 형식)
tests/                   # unittest + fixtures
docs/                    # GitHub Pages 배포 폴더(.nojekyll, cards_v1.json은 Actions가 커밋)
.github/workflows/build-cards.yml   # 검증·빌드·커밋·텔레그램·keepalive
requirements.txt         # 로컬 개발용(coverage 포함)
requirements-ci.txt      # CI 전용, 해시 고정
```
# card-offer-cache
