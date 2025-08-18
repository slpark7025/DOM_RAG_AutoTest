import os
import re
from dotenv import load_dotenv
from urllib.parse import urljoin, urlsplit
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableMap
from langchain_core.output_parsers import StrOutputParser
from validate_selector_ids import validate_generated_code  # ID 정합성 검증 모듈

# =========== URL 정규화/전처리 유틸 ==============
# 뒤 segment(대개 프로젝트 ID 등)를 자를 대상
TRIM_WHITELIST  = {
    "/vpes/ProjectBuildConfig",
    "/vpes/ProjectReliabilityProcess",
    "/vpes/ProjectBuildExecution",
    "/vpes/ProjectDetailConsole",
    "/vpes/ProjectDetailDynamic",
    "/vpes/ProjectDetailException",
    "/vpes/ProjectDetailFileManage",
    "/vpes/ProjectDetailFunctionManage",
    "/vpes/ProjectDetailGroupManage",
    "/vpes/ProjectDetailMetric",
    "/vpes/ProjectDetailSoftwareProcess",
    "/vpes/ProjectDetailStatic",
    "/vpes/ProjectDetailTransition",
    "/vpes/ProjectReliabilityProcess",
    "/vpes/ProjectProgressHistory",
    "/vpes/ProjectModify",
    "/vpes/ProjectDocVerification",
    "/vpes/ProjectDocResult",
    "/vpes/ProjectRuleSetting",
    "/vpes/ProjectDetailTransition",
    "/vpes/ProjectDetailTransition"
    #필요 시 추가
}

def should_trim(path: str) -> bool:
     """경로가 화이트리스트에 해당하면 trim 대상"""
     p = urlsplit(path).path  # 쿼리/해시 제거
     # '/vpes/Project/...' 처럼 prefix + '/' 형태만 trim
     for prefix in TRIM_WHITELIST:
         if p.startswith(prefix + "/"):
             return True
     return False

def normalize_url(path: str) -> str:
    """
    쿼리/해시 제거만 기본 수행.
    화이트리스트(prefix 일치)일 때만 마지막 segment(대부분 프로젝트 식별자)를 제거.
    """
    p = urlsplit(path).path
    parts = [seg for seg in p.split("/") if seg]
    if not parts:
        return "/"
    if should_trim(p) and len(parts) > 1:
        parts = parts[:-1]
    return "/" + "/".join(parts)

def extract_clean_path(s: str) -> str:
    """
    메타 url 문자열에서 '(modal ...)' 같은 부가 설명 제거 후,
    화이트리스트에 해당하는 경우만 마지막 segment를 제거.
    """
    if not s:
        return ""
    s = s.strip()
    s = s.split("(")[0].strip()   # "/path (modal: ...)" → "/path"
    s = s.split()[0]              # "/path extra" → "/path"
    path_only = urlsplit(s).path
    parts = [seg for seg in path_only.split("/") if seg]
    if not parts:
        return "/"
    if should_trim(path_only) and len(parts) > 1:
        parts.pop()
    return "/" + "/".join(parts)

def load_all_docs(collection, batch=1000):
    """Chroma raw collection 전량 로드 (페이지네이션)"""
    total = collection.count()
    metadatas, documents = [], []
    for offset in range(0, total, batch):
        chunk = collection.get(
            include=["metadatas", "documents"],
            limit=batch,
            offset=offset
        )
        metadatas.extend(chunk["metadatas"])
        documents.extend(chunk["documents"])
    return {"metadatas": metadatas, "documents": documents}

def to_base_path(path: str) -> str:
    """ /vpes/<section> 까지만 남김 """
    parts = [seg for seg in path.split("/") if seg]
    return ("/" + "/".join(parts[:2])) if len(parts) >= 2 else path

def derive_base_path(s: str) -> str:
    """전체 URL/상대경로 무엇이든 받아 /vpes/<section> 형태로 변환"""
    return to_base_path(urlsplit(s).path)

# =============== LLM 출력 사후 가드: ID 화이트리스트 + XPath 대체 ===============
def extract_keywords(text):
    return [w.lower() for w in re.findall(r'\w+', text) if len(w) > 1]

def build_selector_inventory(dom_docs):
    """context(dom_docs)에서 허용 가능한 ID 집합과 XPath 후보 풀을 만든다."""
    allowed_ids = set()
    xpath_pool = []
    for d in dom_docs:
        m = d.metadata if hasattr(d, "metadata") else {}
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


# 후처리 유틸 함수들
def remove_markdown(generated_code: str) -> str:
    return generated_code.replace("```python", "").replace("```", "").strip()


def insert_sleep_before_assert(generated_code: str) -> str:
    # logger.info() 줄에서 들여쓰기를 유지하여 sleep(2) 삽입
    # 현재 logger.info()를 쓰지 않아 필요 없을 시 삭제 예정
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
    return re.sub(
        r'def tearDown\(self\):.*?self\.driver\.quit\(\)',
        '''def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()''',
        generated_code,
        flags=re.DOTALL
    )
def postprocess_generated_code(generated_code: str) -> str:
    """
    전체 후처리 통합 함수
    """
    generated_code = remove_markdown(generated_code)
    generated_code = insert_sleep_before_assert(generated_code)
    generated_code = patch_unittest_main(generated_code)
    generated_code = patch_teardown(generated_code)
    return generated_code

# ================ 메인 로직================

# 1. 환경 변수 로딩
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# 2. LLM 초기화 (gpt-4o-mini)
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

# 3. 임베딩 모델 로드
#embedding = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
embedding = OpenAIEmbeddings(model="text-embedding-3-large")

# 4-1. Chroma DB 로드
db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embedding,
    collection_name="dom_elements"
)

# 4.2 default_setting 함수 요약 Chroma DB 로드
default_setting_db = Chroma(
    persist_directory="./chroma_default_setting",
    embedding_function=embedding,
    collection_name="default_setting"
)

# 4-3 move_menu 함수 요약 Chroma DB 로드
move_menu_db = Chroma(
    persist_directory="./chroma_move_menu",
    embedding_function=embedding,
    collection_name="move_menu"
)

# 5. 기본 URL
BASE_URL = "http://localhost:38080"

# 6. ✍️ Prompt 정의 (LLM이 의미 기반 URL 선택하도록 지시 포함)
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
  1) 시나리오 파싱: question을 단계별 행동으로 분해.
  2) URL 결정: 각 단계가 작동해야 할 페이지의 Full URL을 context에서 선택.
  3) 함수 재사용 매핑: function_context를 스캔해 시나리오 단계와 의미가 동일/유사한 함수 우선 매핑.
  4) DOM 매핑: 각 단계에 필요한 요소를 context의 text/description과 의미적으로 정합되게 선택.
     - 선택자 우선순위: ID > CLASS(또는 CSS) > XPath (context에 제공된 값만 사용).
  5) 중복 이동 제거: driver.get() 또는 이동을 포함한 함수 호출 중복 제거.
     - default_setting.login(driver) 호출 시 /vpes로 자동 이동하므로 재이동 금지.
  6) 코드 설계: unittest.TestCase 골격 → setUp → TC 메서드 → tearDown → main 순서로 구성.
  7) 주석 규칙: 각 주요 단계에 “숫자. 한 줄 요약”만. 설명/부연 금지.
  8) 형식·규칙 점검: import 최상단, case_id 추출, URL 조립 규칙, 선택자 규칙, 함수 재사용 준수 여부 확인.
  9) 자기검토: 불필요한 send_keys()/click()/driver.get() 제거, 중복 함수 호출 제거.
  10) 최종 산출: 아래 [최종 출력 규칙]을 지켜 오직 코드블록만 출력.

# [기본 테스트 코드 구조]
- `unittest.TestCase` 클래스를 사용하세요.
- `setUp()`에서는 `default_setting.setup()`을 통해 WebDriver를 초기화하세요.
- case_id를 반드시 import 문 아래에 선언하세요:
  => case_id = os.path.basename(os.path.splitext(__file__)[0])
- 각 주요 단계에는 반드시 **숫자 + 마침표 + 간단한 한 줄 설명** 형태의 주석을 작성하세요.
  => ❌ 절대 추가 설명을 덧붙이지 마세요. 예) "XPath로만 제공됨", "class=btn" 등 금지.
  => ❌ 주석은 사람이 읽기 쉬운 한 줄 요약만 작성하세요.
- `tearDown()` 함수는 테스트 메서드 다음에 기입하세요.
- `if __name__ == "__main__":` 구문도 포함하세요.
- import 선언은 모두 맨 윗단에 작성하세요.

# [기존 함수 활용 지침]
- `function_context`는 default_setting.py 및 move_menu.py에 정의된 함수들의 요약입니다.
- default_setting.login(driver)는 로그인 후 자동으로 메인 페이지(/vpes)로 이동합니다.
  → 그 이후에 driver.get("/vpes") 코드를 다시 작성하지 마세요.
- driver.get()이 포함된 함수는 이미 URL 이동을 수행하므로, 중복 호출을 피하세요.
- 시나리오와 의미적으로 동일/유사한 기능이 존재한다면, 반드시 해당 함수를 재사용하세요.
  - 예: "로그인" → `default_setting.login(driver)`
  - 예: "프로젝트 설정 페이지" → `move_projectSetting(driver, case_id)`
- 불필요한 driver.get(), send_keys(), click() 등의 반복을 줄이고, 제공된 함수들을 활용하세요.
- 각 함수 요약에 명시된 `모듈` 정보를 따라 정확히 import하여 사용하세요.
  - 예: `모듈: default_setting` → `default_setting.create_project(...)`

# [셀렉터 우선순위 및 규칙]
- 각 DOM 요소는 아래 우선순위로 선택:
  1) ID가 있으면 → By.ID
  2) ID가 없고 class가 있으면 → By.CLASS_NAME 또는 By.CSS_SELECTOR
  3) ID와 class가 모두 없으면 → context에 제공된 XPath 그대로 사용
- 셀렉터 값은 반드시 context에 명시된 값만 사용. 임의 생성/유추 금지.

# [자연어 ↔ DOM 요소 매핑 지침]
- 시나리오의 의미와 context의 `text` 또는 `description`을 의미적으로 매칭.
- 해당 DOM 요소의 ID, class, xpath는 context에 나온 값만 사용.
- 자연어 표현과 DOM 속성명이 달라도 의미 기준으로 정확히 매핑.

# [URL 기준 DOM 요소 선택 지침]
- 시나리오와 의미적으로 가장 유사한 **Full URL 기준**의 DOM 요소만 선택.
- 예: 시나리오가 "로그인 페이지"라면, "/vpes/login"으로 끝나는 URL의 요소만 사용.

# [driver.get() 구성]
- context에서 추출한 상대경로 예: "/vpes/xxx"
- 아래처럼 전체 URL을 구성해 사용:
  target_url = "/vpes/xxx"
  page_url = "http://localhost:38080" + target_url
  driver.get(page_url)

---

## DOM 요소 목록 (context):
{context}

## 기능 함수 요약 (function_context):
{function_context}

## 테스트 시나리오 (question):
{question}
---

# [최종 출력 규칙]
- 오직 **실행 가능한 Python 코드**만 하나의 코드블록으로 출력하세요: ```python ... ```
- 내부 사고, 근거, 설명, 텍스트는 출력하지 마세요(주석 규칙 외 일절 금지).
- 위 구조·지침을 위반하면 다시 내부적으로 수정한 뒤, 최종본 코드만 출력하세요.
    """
)

# 7. 테스트케이스 명 및 테스트 시나리오 입력
tc_name = input("테스트케이스명을 입력하세요 (예: C8270): ").strip()
print("💬 테스트 시나리오를 단계별로 입력하세요 (한 줄에 한 단계).")
print("    ↳ 빈 줄(Enter)을 입력하면 종료됩니다.")

steps = []
while True:
    try:
        line = input()
    except EOFError:
        break
    if not line.strip():  # 빈 줄이면 종료
        break
    steps.append(line.strip())

if not steps:
    raise ValueError("최소 1개 이상의 단계가 필요합니다. 예: '1. VPES 로그인'")

query = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))

# 6) URL 직접 입력 (여러 개 가능: 쉼표로 구분)
raw_urls = input('비교할 URL을 입력하세요 (여러 개면 쉼표로 구분): ').strip()
inputs = [u.strip() for u in raw_urls.split(",") if u.strip()]
if not inputs:
    raise ValueError("최소 1개 이상의 URL을 입력해주세요.")

# /vpes/<section> 형태의 base_paths 리스트(중복 제거 & 입력 순서 유지)
base_paths = list(dict.fromkeys(derive_base_path(u) for u in inputs))

print("\n🌐 입력 URL 목록:")
for u in inputs:
    print(" -", u)
print("📌 비교용 베이스 경로들:", base_paths)

# 7) 전체 문서 로드
all_docs = load_all_docs(db._collection, batch=1000)
print(f"[info] loaded docs: {len(all_docs['metadatas'])}")


def meta_url(meta):
    return (meta.get("url") or "")


# base_paths 중 하나라도 포함되는 문서로 필터(UNION)
filtered_indices = [
    i for i, meta in enumerate(all_docs["metadatas"])
    if any(bp in meta_url(meta) for bp in base_paths)
]
if not filtered_indices:
    print(f"[경고] {base_paths} 가 포함된 DOM 요소를 찾지 못했습니다. 전체 데이터 사용.")
    filtered_indices = list(range(len(all_docs["documents"])))

# 필터링 결과 저장
filtered_dom_docs_raw = {
    "metadatas": [all_docs["metadatas"][i] for i in filtered_indices],
    "documents": [all_docs["documents"][i] for i in filtered_indices]
}

# 8-1. 전체 문서 로드 (최대 200개 제한)
dom_docs = [
    type("Doc", (object,), {"metadata": meta, "page_content": doc})
    for doc, meta in zip(filtered_dom_docs_raw["documents"], filtered_dom_docs_raw["metadatas"])

]

# 8.2 default_setting, move_menu 요약 문서 로드
default_docs_raw = default_setting_db._collection.get(include=["documents"], limit=100)

default_docs = [type("Doc", (object,), {"metadata": {}, "page_content": doc}) for doc in default_docs_raw["documents"]]

move_menu_docs_raw = move_menu_db._collection.get(include=["documents"], limit=100)

move_menu_docs = [type("Doc", (object,), {"metadata": {}, "page_content": doc}) for doc in
                  move_menu_docs_raw["documents"]]

# 9. context 구성
context = "\n".join([
    f"Full URL: {urljoin(BASE_URL, doc.metadata.get('url', ''))}, "
    f"Tag: {doc.metadata.get('tag')}, "
    f"ID: {doc.metadata.get('id')}, "
    f"Class: {doc.metadata.get('class')}, "
    f"XPath: {doc.metadata.get('xpath')}, "
    f"Text: {doc.metadata.get('text')}, "
    f"Description: {doc.metadata.get('desc')}"
    for doc in dom_docs
])

# 10. default_setting, move_menu 함수 요약 따로 텍스트화
function_context = "\n\n".join(doc.page_content for doc in default_docs + move_menu_docs)

print("\n📌 context에 포함된 ID 목록:")
shown = 0
for doc in dom_docs:
    if doc.metadata.get("id"):
        print(f"- {doc.metadata['id']}")
        shown += 1
        if shown >= 60:
            print("... (생략)")
            break


# 11. LLMChain 실행
chain = (
    RunnableMap({"context": lambda _: context, "function_context": lambda _: function_context, "question": lambda _: query})
    | prompt
    | llm
    | StrOutputParser()
)

generated_code = chain.invoke({
    "context": context,
    "function_context": function_context,
    "question": query
})

# 12. 클래스명/함수명을 사용자 입력 값으로 변경
generated_code = re.sub(r'class [a-zA-Z0-9_]*\(unittest\.TestCase\):', f'class {tc_name}(unittest.TestCase):', generated_code, count=1)
generated_code = re.sub(r'def test_[a-zA-Z0-9_]*\(', f'def test_{tc_name}(', generated_code, count=1)

# 후처리 수행
generated_code = validate_generated_code(generated_code, dom_docs + default_docs, auto_fix=True)
generated_code = postprocess_generated_code(generated_code)

# 출력 및 저장
print("\n💻 생성된 Selenium 테스트 코드:")
print("=" * 60)
print(generated_code)
print("=" * 60)

file_name = f"{tc_name}.py"
with open(file_name, "w", encoding="utf-8") as f:
    f.write(generated_code)

print(f"\n✅ 코드가 '{file_name}' 파일로 저장되었습니다.")
