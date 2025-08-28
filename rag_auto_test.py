# -*- coding: utf-8 -*-
# pip install -U langchain langchain-openai langchain-community chromadb tiktoken python-dotenv

import os
import re
import math
from urllib.parse import urljoin, urlsplit
from dotenv import load_dotenv

import chromadb
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableMap
from langchain_core.output_parsers import StrOutputParser

from validate_selector_ids import validate_generated_code  # ID 정합성 검증 모듈


# ========================= 공통 유틸 =========================
def derive_base_path(s: str) -> str:
    """전체 URL/상대경로 무엇이든 받아 /vpes/<section> 형태로 변환"""
    def to_base_path(path: str) -> str:
        parts = [seg for seg in path.split("/") if seg]
        return ("/" + "/".join(parts[:2])) if len(parts) >= 2 else path
    return to_base_path(urlsplit(s).path)

def extract_keywords(text):
    return [w.lower() for w in re.findall(r'\w+', text) if len(w) > 1]

def build_selector_inventory(dom_docs):
    """context(dom_docs)에서 허용 가능한 ID 집합과 XPath 후보 풀을 만든다."""
    allowed_ids = set()
    xpath_pool = []
    for d in dom_docs:
        m = getattr(d, "metadata", {}) or {}
        if not isinstance(m, dict):
            continue
        if m.get("id"):
            allowed_ids.add(m["id"])
        if m.get("xpath"):
            blob = " ".join([
                (m.get("text") or ""),
                (m.get("desc") or ""),
                (m.get("tag") or "")
            ]).lower()
            xpath_pool.append({"xpath": m["xpath"], "blob": blob})
    return allowed_ids, xpath_pool

def pick_best_xpath(xpath_pool, keywords):
    """키워드와 blob(text/desc/tag 조합)을 단순 매칭해서 가장 관련도 높은 XPath 선택"""
    best = None
    best_score = -1
    for item in xpath_pool:
        score = sum(1 for kw in keywords if kw in item["blob"])
        if score > best_score:
            best = item
            best_score = score
    return best["xpath"] if best else (xpath_pool[0]["xpath"] if xpath_pool else None)

def enforce_known_selectors(generated_code: str, dom_docs, question: str) -> str:
    """허구 ID → XPath로 자동 대체(화이트리스트 기반)."""
    allowed_ids, xpath_pool = build_selector_inventory(dom_docs)
    if not xpath_pool:
        return generated_code

    keywords = extract_keywords(question)

    def best_xpath():
        xp = pick_best_xpath(xpath_pool, keywords)
        return xp or xpath_pool[0]["xpath"]

    # 1) .find_element(By.ID, "…")
    generated_code = re.sub(
        r'(\.find_element\()\s*By\.ID\s*,\s*["\']([^"\']+)["\']\s*(\))',
        lambda m: m.group(0) if m.group(2) in allowed_ids
        else f'{m.group(1)}By.XPATH, "{best_xpath()}"{m.group(3)}',
        generated_code
    )

    # 2) (By.ID, "…") — EC 패턴 포함 모든 곳
    generated_code = re.sub(
        r'\(\s*By\.ID\s*,\s*["\']([^"\']+)["\']\s*\)',
        lambda m: m.group(0) if m.group(1) in allowed_ids
        else f'(By.XPATH, "{best_xpath()}")',
        generated_code
    )

    return generated_code

def remove_markdown(generated_code: str) -> str:
    return generated_code.replace("```python", "").replace("```", "").strip()

def insert_sleep_before_assert(generated_code: str) -> str:
    # logger.info() 줄에서 들여쓰기를 유지하여 sleep(2) 삽입
    generated_code = re.sub(
        r'^(\s*)(log_setting\.logger\.info\(["\']Verifying navigation.*?["\']\))',
        r'\1sleep(2)\n\1\2',
        generated_code,
        flags=re.MULTILINE
    )
    if "sleep(" in generated_code and "from time import sleep" not in generated_code:
        generated_code = "from time import sleep\n" + generated_code
    return generated_code

def patch_unittest_main(generated_code: str) -> str:
    return re.sub(
        r'if __name__ == ["\']__main__["\']:\s*unittest\.main\(\)',
        'if __name__ == "__main__":\n    unittest.main(argv=[\'first-arg-is-ignored\'], exit=False)',
        generated_code
    )

def patch_teardown(generated_code: str) -> str:
    # 과매칭 방지: 앵커/들여쓰기 기준 강화
    return re.sub(
        r'(?ms)^(\s*)def\s+tearDown\(self\):\s*\n(.*?\n)?\1\s*self\.driver\.quit\(\)\s*$',
        r'''\1def tearDown(self):
\1    result = default_setting.get_result(self)
\1    default_setting.upload_result(self, case_id, result)
\1    self.driver.quit()''',
        generated_code
    )

def ensure_import(g: str, line: str) -> str:
    return (line + "\n" + g) if line not in g else g

def postprocess_generated_code(generated_code: str) -> str:
    """전체 후처리 통합"""
    generated_code = remove_markdown(generated_code)
    generated_code = insert_sleep_before_assert(generated_code)
    generated_code = patch_teardown(generated_code)
    generated_code = patch_unittest_main(generated_code)

    # 필수 import 보강
    generated_code = ensure_import(generated_code, "import unittest")
    generated_code = ensure_import(generated_code, "from selenium.webdriver.common.by import By")
    generated_code = ensure_import(generated_code, "import default_setting")

    before = generated_code
    generated_code = strip_document_prefix_xpaths(generated_code)
    if before != generated_code:
        print("🔧 Stripped '/[document][n]/' prefix from XPaths.")

    return generated_code


def strip_document_prefix_xpaths(g: str) -> str:
    """
    (By.XPATH, "...") 형태의 문자열 중
    XPath가 '/[document]/' 또는 '/[document][숫자]/' 로 시작하면 그 프리픽스만 제거.
    예) '/[document][1]/html[1]/body[1]/...' -> '/html[1]/body[1]/...'
    """
    # 1) 문자열 앞의 '/[document][n]/' 패턴만 없애는 헬퍼
    def _fix(xp: str) -> str:
        return re.sub(r'^\s*/\s*\[document\](?:\[\d+\])?/?', '/', xp)

    # 2) 공통 치환기: (By.XPATH, "...") 캡처해서 내부만 교체
    def _repl_tuple(m):
        quote = m.group(2)
        xp = m.group(3)
        fixed = _fix(xp)
        return f"{m.group(1)}{quote}{fixed}{quote}{m.group(4)}"

    # (a) (By.XPATH, "…")  — EC, until 등 모든 튜플 인자
    g = re.sub(r'(\(\s*By\.XPATH\s*,\s*)(["\'])(.+?)\2(\s*\))', _repl_tuple, g, flags=re.DOTALL)

    # (b) .find_element(By.XPATH, "…")
    g = re.sub(r'(\.find_element\(\s*By\.XPATH\s*,\s*)(["\'])(.+?)\2(\s*\))', _repl_tuple, g, flags=re.DOTALL)

    # (c) .find_elements(By.XPATH, "…")  (있을 수도 있으니 케어)
    g = re.sub(r'(\.find_elements\(\s*By\.XPATH\s*,\s*)(["\'])(.+?)\2(\s*\))', _repl_tuple, g, flags=re.DOTALL)

    return g




# ========================= 선택 DB 라우팅 & 검색 =========================
CHROMA_BASE_DIR = "./chroma"  # JSON별 DB 폴더들이 위치한 루트

def select_chroma_dirs(base_dir: str, user_inputs: list[str]) -> list[str]:
    """
    ./chroma 하위 폴더 중에서, 폴더명에 사용자가 입력한 텍스트(쉼표 분리 원본)가
    '부분 문자열'로 포함된 폴더만 선택 (대소문자 무시).
    """
    if not os.path.isdir(base_dir):
        return []
    keys = [u.strip().lower() for u in user_inputs if u and u.strip()]
    if not keys:
        return []
    selected = []
    for name in os.listdir(base_dir):
        p = os.path.join(base_dir, name)
        if not os.path.isdir(p):
            continue
        low = name.lower()
        if any(k in low for k in keys):
            selected.append(p)
    return selected

def retrieve_from_selected_dirs(
    selected_dirs: list[str],
    query: str,
    embedding,              # OpenAIEmbeddings 인스턴스
    k_total: int = 200,     # 전체 상한(필요시 100~400 조정)
    mmr_fetch_factor: int = 5,
    mmr_lambda: float = 0.35
):
    """
    선택된 여러 DB 폴더 각각에서 MMR 검색을 수행하고 결과를 합칩니다.
    각 DB당 k를 균등 분배(올림)하여 과도한 편중을 방지합니다.
    """
    if not selected_dirs:
        return []
    per_db = max(1, math.ceil(k_total / len(selected_dirs)))
    fetch_k = min(per_db * mmr_fetch_factor, 1000)

    all_docs = []
    for db_dir in selected_dirs:
        try:
            client = chromadb.PersistentClient(path=db_dir)
            vs = Chroma(
                client=client,
                collection_name="dom_elements",
                embedding_function=embedding,
            )
            docs = vs.max_marginal_relevance_search(
                query=query,
                k=per_db,
                fetch_k=fetch_k,
                lambda_mult=mmr_lambda
            )
            all_docs.extend(docs)
        except Exception as e:
            print(f"[경고] DB 접근 실패, 건너뜀: {db_dir} ({e})")
    return all_docs[:k_total]


# ========================= 메인 로직 =========================
def main():
    # 1) 환경 변수 로딩
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 또는 환경변수를 확인하세요.")

    # 2) LLM/임베딩 초기화
    # gpt-4.1을 사용할 경우 temperature 인자를 제거해야 함. 안전하게 gpt-4o-mini 권장.
    llm = ChatOpenAI(model="gpt-5")
    embedding = OpenAIEmbeddings(model="text-embedding-3-large")

    # 3) 기본 URL
    BASE_URL = "http://localhost:38080"

    # 4) Prompt 정의
    prompt = PromptTemplate(
        input_variables=["context", "question", "function_context"],
        template="""
# ===== CoT 적용 버전 (출력은 코드만) =====
단계적으로 내부에서 생각하되, 최종 출력에는 절대 사고 과정을 포함하지 마세요.
당신은 Selenium 테스트 자동화 코드를 생성하는 전문가입니다.

아래는 웹 페이지의 HTML DOM 요소 목록(context)과
기능 함수 요약(function_context), 그리고 테스트 시나리오(question)입니다.

# [내부 사고 프로세스 — 출력 금지]
- 이 섹션의 내용, 중간 메모, 근거, 체크리스트는 절대 출력하지 말 것.
- 내부적으로만 다음 단계를 거쳐 최선의 답을 선택하고, 최종 결과(테스트 코드)만 출력할 것.
  1) 시나리오 파싱 → 단계별 행동으로 분해.
  2) URL 결정 → 각 단계가 작동해야 할 페이지의 Full URL을 context에서 선택.
  3) 함수 재사용 매핑 → function_context를 스캔해 동일/유사 기능 우선 매핑.
  4) DOM 매핑 → context의 text/description과 의미적으로 정합되게 선택.
     - 선택자 우선순위: ID > CLASS/CSS > XPath (context에 제공된 값만 사용).
  5) 중복 이동 제거: login 후 /vpes 재이동 금지 등.
  6) 코드 설계: unittest.TestCase 골격 → setUp → TC 메서드 → tearDown → main 순서.
  7) 주석 규칙: 각 주요 단계에 “숫자. 한 줄 요약”만.
  8) 형식 점검: import 최상단, case_id 추출, URL 조립 규칙, 선택자 규칙, 함수 재사용 준수.
  9) 자기검토: 불필요한 send_keys()/click()/driver.get() 제거.
 10) 최종 산출: 아래 [최종 출력 규칙]을 지켜 오직 코드블록만 출력.

# [기본 테스트 코드 구조]
- unittest.TestCase 사용.
- setUp()은 default_setting.setup()으로 WebDriver 초기화.
- case_id는 import 아래:
  => case_id = os.path.basename(os.path.splitext(__file__)[0])
- 각 주요 단계에 **숫자. 한 줄 요약** 주석.
- tearDown()은 테스트 메서드 다음.
- if __name__ == "__main__": 포함.
- import 선언은 모두 맨 윗단.

# [기존 함수 활용 지침]
- function_context는 default_setting.py 및 move_menu.py의 요약.
- default_setting.login(driver)는 로그인 후 /vpes로 이동. 이후 중복 이동 금지.
- driver.get()이 포함된 함수는 중복 호출 피하기.
- 제공된 함수가 시나리오와 의미가 같다면 반드시 재사용.
- 함수 요약의 모듈 정보를 따라 정확히 import.

# [셀렉터 규칙]
- ID > CLASS/CSS > XPath 순.


# [자연어 ↔ DOM 매핑]
- 시나리오 의미와 context의 text/description을 의미적으로 매칭.

# [URL 기준 DOM 선택]
- 시나리오 단계에 맞는 Full URL 기준으로만 선택.
- 상대경로 "/vpes/xxx"는 아래식으로 Full URL 구성:
  target_url = "/vpes/xxx"
  page_url = "http://localhost:38080" + target_url
  driver.get(page_url)
  

# [ASSERT 규칙]
- '확인'이라는 단어가 포함된 문장이며 보통 사용자가 입력하는 테스트 시나리오의 가장 마지막 문장일 경우가 대부분.
- 금지: driver.page_source(문자열 포함/카운트), 하드 sleep만으로의 검증, 전역 텍스트 검색, URL로 이동에 대한 검증
- 표(테이블/그리드) 검증일 때:
  1) 내가 선택·변경한 행의 **키 값(예: 파일명)** 을 변수로 캡처한다.
  2) 헤더 텍스트로 열 인덱스를 구해 해당 셀의 텍스트/상태를 검증한다.
  3) 표가 비어 있으면 즉시 실패(“데이터가 존재하지 않습니다.” 탐지 또는 tbody tr 개수 0 확인).
  4) page_source 이용 금지. 행의 셀 텍스트만 검사.

- 비표(버튼/폼/토스트/페이지 전환) 검증일 때:
  - 토스트/알림: role='alert' 또는 class에 'toast'/'alert'가 포함된 요소의 텍스트로 성공/실패 확인.
  - URL/라우팅: 예상 경로/쿼리로 이동했는지 확인.
  - 요소 상태: aria-pressed/disabled/checked/value 변경, 클래스 토글 등 **속성**으로 확인.
  - 모달/드로어: 열림/닫힘 상태(visibility/display/aria-hidden)로 확인. 

---

## DOM 요소 목록 (context):
{context}

## 기능 함수 요약 (function_context):
{function_context}

## 테스트 시나리오 (question):
{question}
---

# [최종 출력 규칙]
- 오직 **실행 가능한 Python 코드**만 하나의 코드블록으로 출력: ```python ... ```
- 내부 사고, 근거, 설명 텍스트 출력 금지(주석 규칙 외).
- tc id 사용하는 class와 함수 외 추가 함수 생성 금지
        """.strip()
    )

    # 5) 테스트케이스명/시나리오 입력
    tc_name = input("테스트케이스명을 입력하세요 (예: C8270): ").strip()
    print("💬 테스트 시나리오를 단계별로 입력하세요 (한 줄에 한 단계).")
    print("    ↳ 빈 줄(Enter)을 입력하면 종료됩니다.")

    steps = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        steps.append(line.strip())

    if not steps:
        raise ValueError("최소 1개 이상의 단계가 필요합니다. 예: '1. VPES 로그인'")

    query = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))

    # 6) URL(또는 키워드) 입력 → 폴더명 매칭용 키로 사용
    raw_urls = input('비교할 URL을 입력하세요 (여러 개면 쉼표로 구분): ').strip()
    inputs = [u.strip() for u in raw_urls.split(",") if u.strip()]
    if not inputs:
        raise ValueError("최소 1개 이상의 URL 또는 텍스트를 입력해주세요.")

    # /vpes/<section> 형태의 base_paths (현재는 선택적; 필요시 활용)
    base_paths = list(dict.fromkeys(derive_base_path(u) for u in inputs))
    print("\n🌐 입력 목록:")
    for u in inputs:
        print(" -", u)
    print("📌 비교용 베이스 경로들:", base_paths)

    # 7) 선택된 DB 폴더만 대상으로 Retrieval
    #selected_dirs = select_chroma_dirs(CHROMA_BASE_DIR, inputs)
    match_keys = inputs + base_paths + [os.path.basename(p) for p in base_paths]
    selected_dirs = select_chroma_dirs(CHROMA_BASE_DIR, match_keys)

    if not selected_dirs:
        # 폴더명에 매치되는 게 없으면 전체 DB 대상으로 fallback
        print(f"[경고] 입력 텍스트와 일치하는 DB 폴더가 없습니다. 전체 DB 대상으로 검색합니다.")
        selected_dirs = [
            os.path.join(CHROMA_BASE_DIR, d)
            for d in os.listdir(CHROMA_BASE_DIR)
            if os.path.isdir(os.path.join(CHROMA_BASE_DIR, d))
        ]
        if not selected_dirs:
            raise RuntimeError(f"검색 가능한 DB 폴더가 없습니다: {CHROMA_BASE_DIR}")

    print("\n🔎 검색에 사용할 DB 폴더:")
    for d in selected_dirs:
        print(" -", d)

    dom_docs_lc = retrieve_from_selected_dirs(
        selected_dirs=selected_dirs,
        query=query,
        embedding=embedding,
        k_total=200,           # 필요 시 100~400로 조정
        mmr_fetch_factor=5,
        mmr_lambda=0.35
    )

    # LangChain Document → 간단 객체로 변환(기존 파이프라인 호환)
    dom_docs = [
        type("Doc", (object,), {"metadata": d.metadata, "page_content": d.page_content})
        for d in dom_docs_lc
    ]

    # 8) function_context 로드 (있을 때만)
    def safe_load_collection(persist_dir: str, collection_name: str):
        try:
            client = chromadb.PersistentClient(path=persist_dir)
            vs = Chroma(client=client, collection_name=collection_name, embedding_function=embedding)
            raw = vs._collection.get(include=["documents"], limit=200)
            return [type("Doc", (object,), {"metadata": {}, "page_content": doc}) for doc in raw.get("documents", [])]
        except Exception:
            return []

    default_docs = safe_load_collection("./chroma_default_setting", "default_setting")
    move_menu_docs = safe_load_collection("./chroma_move_menu", "move_menu")

    # 9) context 구성 (필드 최소화 + 길이 제한)
    def _fmt(meta, key, maxlen=180):
        v = (meta.get(key) or "")
        sv = str(v)
        return (sv[:maxlen] + "…") if len(sv) > maxlen else sv

    BASE_URL_CONST = BASE_URL  # 클로저 캡쳐 안정화
    context = "\n".join([
        f"FullURL:{urljoin(BASE_URL_CONST, getattr(doc, 'metadata', {}).get('url',''))} "
        f"ID:{_fmt(getattr(doc, 'metadata', {}),'id')} "
        f"XPATH:{_fmt(getattr(doc, 'metadata', {}),'xpath')} "
        f"TEXT:{_fmt(getattr(doc, 'metadata', {}),'text', 160)} "
        f"DESC:{_fmt(getattr(doc, 'metadata', {}),'desc', 160)}"
        for doc in dom_docs
    ])

    function_context = "\n\n".join(doc.page_content[:2000] for doc in (default_docs + move_menu_docs))

    print("\n📌 context에 포함된 ID 목록(최대 60개 표시):")
    shown = 0
    for doc in dom_docs:
        mid = getattr(doc, "metadata", {}).get("id")
        if mid:
            print(f"- {mid}")
            shown += 1
            if shown >= 60:
                print("... (생략)")
                break

    # 10) LLMChain 실행
    chain = (
        RunnableMap({"context": lambda _: context, "function_context": lambda _: function_context, "question": lambda _: query})
        | prompt
        | llm
        | StrOutputParser()
    )
    generated_code = chain.invoke({})

    # 11) 클래스명/함수명 사용자 입력 값으로 변경
    generated_code = re.sub(r'class [a-zA-Z0-9_]*\(unittest\.TestCase\):', f'class {tc_name}(unittest.TestCase):', generated_code, count=1)
    generated_code = re.sub(r'def test_[a-zA-Z0-9_]*\(', f'def test_{tc_name}(', generated_code, count=1)

    # 12) 후처리/검증/가드
    generated_code = validate_generated_code(generated_code, dom_docs + default_docs)
    generated_code = enforce_known_selectors(generated_code, dom_docs, query)
    generated_code = postprocess_generated_code(generated_code)

    # 13) 출력 및 저장
    print("\n💻 생성된 Selenium 테스트 코드:")
    print("=" * 60)
    print(generated_code)
    print("=" * 60)

    file_name = f"{tc_name}.py"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(generated_code)
    print(f"\n✅ 코드가 '{file_name}' 파일로 저장되었습니다.")


if __name__ == "__main__":
    main()
