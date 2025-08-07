import os
import re
from dotenv import load_dotenv
from urllib.parse import urljoin
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableMap
from langchain_core.output_parsers import StrOutputParser

from validate_selector_ids import validate_generated_code  # ID 정합성 검증 모듈

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

# ================ 매인로직================

# 1. 🔐 환경 변수 로딩
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# 2. 💬 LLM 초기화 (gpt-4o-mini)
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

# 3. 🧠 임베딩 모델 로드
#embedding = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
embedding = OpenAIEmbeddings(model="text-embedding-3-large")

# 4-1. 📦 Chroma DB 로드
db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embedding,
    collection_name="dom_elements"
)

# 4.2 📦 default_setting 함수 요약 Chroma DB 로드
default_setting_db = Chroma(
    persist_directory="./chroma_default_setting",
    embedding_function=embedding,
    collection_name="default_setting"
)

# 📦 move_menu 함수 요약 Chroma DB 로드
move_menu_db = Chroma(
    persist_directory="./chroma_move_menu",
    embedding_function=embedding,
    collection_name="move_menu"
)

# 5. 🌐 기본 URL
BASE_URL = "http://localhost:38080"

# 6. ✍️ Prompt 정의 (LLM이 의미 기반 URL 선택하도록 지시 포함)
prompt = PromptTemplate(
    input_variables=["context", "question", "function_context"],
    template="""
    당신은 Selenium 테스트 자동화 코드를 생성하는 전문가입니다.

    아래는 웹 페이지의 HTML DOM 요소 목록(context)과  
    기능 함수 요약(function_context), 그리고 테스트 시나리오(question)입니다.


    다음 지침을 반드시 지키세요:

    ✅ [기본 테스트 코드 구조]
    - `unittest.TestCase` 클래스를 사용하세요.
    - `setUp()`에서는 `default_setting.setup()`을 통해 WebDriver를 초기화하세요.
    - case_id를 반드시 import 문 아래에 선언하세요:
    - `case_id`는 아래처럼 추출하세요:
      => case_id = os.path.basename(os.path.splitext(__file__)[0])
    - 각 단계별로 어떤 동작을 하는 단계인지 주석 달아주세요.
    - `tearDown()`에서는 결과 업로드 및 `driver.quit()`을 반드시 호출하세요.
    - `if __name__ == "__main__":` 구문도 포함하세요.

    ✅ [기존 함수 활용 지침]
    - 아래의 `function_context`는 default_setting.py 및 move_menu.py에 정의된 함수들의 요약입니다.
    - default_setting.login(driver)는 로그인 후 자동으로 메인 페이지(/vpes)로 이동합니다.
    - 따라서 그 이후에 driver.get("/vpes") 코드를 다시 작성하지 마세요.
    - driver.get()이 포함된 함수는 이미 URL 이동을 수행하므로, 중복 호출을 피해야 합니다.
    - 시나리오와 의미적으로 동일하거나 유사한 기능이 존재한다면, 반드시 해당 함수를 재사용하세요.
    - 예: "로그인"과 관련된 시나리오는 `default_setting.login(driver)`을 직접 호출하세요.
    - 예: "프로젝트 설정 페이지"와 관련된 시나리오는 `move_projectSetting(driver, case_id)` 함수를 직접 호출하세요.
    - 불필요하게 driver.get(), send_keys(), click() 등을 반복하지 마세요.
    - 최대한 간결하게, 제공된 함수들을 활용해 테스트 코드를 구성하세요.
    - 각 함수 요약에 명시된 `모듈` 정보를 따라 정확하게 import하여 사용하세요.
    - 예: `모듈: default_setting`이면 → `default_setting.create_project(...)`

    ✅ [셀렉터 우선순위 및 규칙]
    - 각 DOM 요소는 반드시 아래 우선순위에 따라 선택하세요:
      1. ID가 있으면 → 반드시 By.ID 사용
      2. ID가 없고 class가 있으면 → By.CLASS_NAME 또는 By.CSS_SELECTOR 사용
      3. ID와 class가 모두 없으면 → context에 제공된 XPath를 그대로 사용
    - 셀렉터 값은 반드시 context에 명시된 값만 사용하세요.
    - 절대 임의 생성하거나 유추하지 마세요.

    ✅ [자연어 ↔ DOM 요소 매핑 지침]
    - 시나리오에서 언급된 의미를 이해하고,
    - context의 `text` 또는 `description` 필드에서 의미적으로 가장 유사한 DOM 요소를 선택하세요.
    - 해당 DOM 요소의 ID, class, xpath는 context에 나온 값만 사용하세요.
    - 절대 임의 추측으로 생성하지 마세요.
    - ID, class 등은 자연어 표현과 다를 수 있습니다. 의미적 유사도를 기준으로 정확히 매핑하세요.

    ❗ [URL 기준 DOM 요소 선택 지침]
    - 시나리오와 의미적으로 가장 유사한 URL (Full URL 기준)의 DOM 요소만 선택하세요.
    - 예: 시나리오에 "로그인 페이지"라고 되어 있다면, "/vpes/login"으로 끝나는 URL의 요소만 사용해야 합니다.
    - 관련 없는 URL의 DOM 요소는 절대 사용하지 마세요.

    ✅ [driver.get() 구성]
    - context에서 추출한 상대경로 예: "/vpes/xxx"
    - 아래처럼 전체 URL을 구성해 사용하세요:

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

    정확하고 실행 가능한 Python Selenium 테스트 코드를 생성하세요.
    ❗ 오직 코드와 고드에 대한 주석만 출력하세요. 마크다운 금지
    ❗ 절대 코드 블록(```python`), 마크다운 등을 포함하지 마세요.
    오직 파이썬 코드만 출력하세요. 출력 시작 전에 아무것도 붙이지 마세요.
    """
)

# 7.테스트케이스 명 및 테스트 시나리오 입력
tc_name = input("테스트케이스명을 입력하세요 (예: C8270): ").strip()
query = input("💬 테스트 시나리오를 자연어로 입력하세요:\n> ").strip()


# 의미 기반 URL 필터링
# 시나리오에서 키워드 추출
def extract_keywords(text):
    return [word.lower() for word in re.findall(r'\w+', text) if len(word) > 1]

keywords = extract_keywords(query)

# 1. 전체 문서 가져오기 (메타데이터 포함)
all_docs = db._collection.get(include=["metadatas", "documents"], limit=1000)

# 2. url 키워드 포함된 것만 필터링
filtered_indices = [
    i for i, meta in enumerate(all_docs["metadatas"])
    if any(kw in (meta.get("url") or "").lower() for kw in keywords)
]

# 3. 해당 문서 추출
filtered_dom_docs_raw = {
    "metadatas": [all_docs["metadatas"][i] for i in filtered_indices],
    "documents": [all_docs["documents"][i] for i in filtered_indices]
}

# 8-1. 전체 문서 로드 (최대 200개 제한)
#dom_docs_raw = db._collection.get(include=["metadatas", "documents"], limit=300)
dom_docs = [
    type("Doc", (object,), {"metadata": meta, "page_content": doc})
    for doc, meta in zip(filtered_dom_docs_raw["documents"], filtered_dom_docs_raw["metadatas"])

]

# 8.2 default_setting 요약 문서 로드
default_docs_raw = default_setting_db._collection.get(include=["documents"], limit=100)
default_docs = [
    type("Doc", (object,), {"metadata": {}, "page_content": doc})
    for doc in default_docs_raw["documents"]
]
# 8.3 move_menu 요약 문서 로드
move_menu_docs_raw = move_menu_db._collection.get(include=["documents"], limit=100)
move_menu_docs = [
    type("Doc", (object,), {"metadata": {}, "page_content": doc})
    for doc in move_menu_docs_raw["documents"]
]

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

# 🧠 default_setting, move_menu 함수 요약 따로 텍스트화
function_context = "\n\n".join(doc.page_content for doc in default_docs + move_menu_docs)

#DOM + 함수 문서를 하나로 병합 (validate 단계용)
# docs = dom_docs + default_docs
#
#
# print("\n🔎 최종 context (LLM에게 전달되는 값):\n")
# print(context[:3000])  # 너무 길면 생략 출력

print("\n📌 context에 포함된 ID 목록:")
for doc in dom_docs:
    if doc.metadata.get("id"):
        print(f"- {doc.metadata['id']}")


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

# 클래스명을 사용자 입력 값으로 변경
generated_code = re.sub(
    r'class [a-zA-Z0-9_]*\(unittest\.TestCase\):',
    f'class {tc_name}(unittest.TestCase):',
    generated_code,
    count=1
)

# 함수명을 사용자 입력 값으로 변경
generated_code = re.sub(
    r'def test_[a-zA-Z0-9_]*\(',
    f'def test_{tc_name}(',
    generated_code,
    count=1
)


# 11. 후처리 수행
generated_code = validate_generated_code(generated_code, dom_docs + default_docs, auto_fix=True)
generated_code = postprocess_generated_code(generated_code)

# 12. 출력 및 저장
print("\n💻 생성된 Selenium 테스트 코드:")
print("=" * 60)
print(generated_code)
print("=" * 60)

file_name = f"{tc_name}.py"
with open(file_name, "w", encoding="utf-8") as f:
    f.write(generated_code)

print(f"\n✅ 코드가 '{file_name}' 파일로 저장되었습니다.")
