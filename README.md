# card-offer-cache

카드 보너스 알림 앱이 읽는 **미국 신용카드 보너스 데이터**입니다.

진호님이 `data/cards.yaml` 하나를 GitHub 웹에서 고치면, 검증기가 틀린 데이터를 막습니다. (다음 단계에서 GitHub Actions가 이 파일을 `docs/cards_v1.json`으로 만들어 GitHub Pages로 배포합니다. 지금은 **검증기까지만** 들어 있습니다.)

- 카드사 페이지를 자동으로 긁어 오지 않습니다. 모든 숫자는 사람이 공식 페이지를 보고 적습니다.
- 커뮤니티(마일모아, Doctor of Credit, Frequent Miler, Reddit, The Points Guy) 내용과 단축 주소(bit.ly 등)는 이 파일에 **절대 넣지 않습니다**. 검증기가 막습니다.
- 지금 `data/cards.yaml`의 2장은 형식 확인용 **샘플(가짜)** 입니다. 실제 30종으로 교체할 예정입니다.

## GitHub 웹에서 고치는 법

1. 저장소에서 `data/cards.yaml`을 엽니다 → 오른쪽 위 연필(✏️ Edit this file) 버튼.
2. 고칠 카드를 찾아 값을 바꿉니다. **들여쓰기(앞쪽 빈칸)는 그대로** 두세요. 탭 대신 스페이스만 씁니다.
3. 아래 **Commit changes…** → 메시지(예: `Update sample-travel-card bonus`) → **Commit changes**.
4. (다음 단계부터) 검증에 실패하면 텔레그램으로 오류 목록이 오고, 앱 데이터는 바뀌지 않습니다. 오류 줄을 보고 다시 고치면 됩니다.

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
- **이미 높음인데 보너스가 더 오름**(예: 75,000 → 90,000): `bonus.current`를 고치고 **`start`를 오늘 날짜로 바꾸기**. `start`가 바뀌어야 새 오퍼로 보고 다시 알립니다. `start`를 그대로 두면 "오타 정정"으로 보고 알리지 않습니다.
- **보너스가 내려감·끝남**: `bonus.current`를 고치고 `elevated`를 지우면 됩니다. 알림은 가지 않습니다.
- **끝났다가 다시 열림**: 새로 `elevated`를 넣고 `start`를 오늘로. 새 오퍼로 다시 알립니다.
- `start`는 미래 날짜를 쓸 수 없습니다(오늘까지만, 미국 서부 기준).
- `bonus`·`elevated` 안에는 위 표에 있는 항목만 쓸 수 있습니다. 오타(`ends`, `min_spnd` 등)는 **오류**입니다(오퍼가 조용히 틀어지는 것을 막기 위해).
- `end`가 지나면 (다음 단계의 빌드가) 자동으로 "종료"로 보여 줍니다. YAML은 나중에 정리하면 됩니다.
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

## 로컬 실행·테스트

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/validate.py                       # data/cards.yaml 검증 (오류면 exit 1)
.venv/bin/python scripts/validate.py path/to.yaml --today 2026-11-09
.venv/bin/python -m unittest discover -s tests -v          # 네트워크 없이 단위 테스트
.venv/bin/python -m coverage run -m unittest discover -s tests && .venv/bin/python -m coverage report   # 80% 미만이면 실패(.coveragerc)
```

Python 3.11 이상(Actions는 3.12). 의존성은 `requirements.txt`에 버전을 고정했습니다(PyYAML, defusedxml, coverage). YAML은 `yaml.SafeLoader`를 바탕으로 한 전용 로더(`CardLoader`)로만 읽습니다. 파이썬 태그는 여전히 막히고, 위의 중복 항목·이상한 숫자·별칭·없는 날짜를 줄 번호와 함께 거부합니다.

## 파일 구조

```
data/cards.yaml          # 진호님이 고치는 카드 데이터
data/card_aliases.yaml   # RSS 신호용 카드 별칭 사전(다음 단계에서 채움, 앱에는 안 나감)
scripts/validate.py      # 검증 CLI
scripts/cardlib/         # schema(검증 진입점), loader(YAML 읽기), fields(항목 규칙), urls(주소·발급사 도메인),
                         # phrases(금지 문구·커뮤니티·단축 주소 패턴), rules(모든 글자 검사), issues
tests/                   # unittest + fixtures
docs/                    # GitHub Pages 배포 폴더(.nojekyll)
```
