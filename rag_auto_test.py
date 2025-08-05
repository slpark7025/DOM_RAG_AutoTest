import os
import re
from dotenv import load_dotenv
from urllib.parse import urljoin

from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableMap
from langchain_core.output_parsers import StrOutputParser

from validate_selector_ids import validate_generated_code  # ID 정합성 검증 모듈

# 1. 🔐 환경 변수 로딩
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# 2. 💬 LLM 초기화 (gpt-4o-mini)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 3. 🧠 임베딩 모델 로드
embedding = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# 4. 📦 Chroma DB 로드
db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embedding,
    collection_name="dom_elements"
)
retriever = db.as_retriever(search_kwargs={"k": 20})

# 5. 🌐 기본 URL
BASE_URL = "http://localhost:38080"

# 6. ✍️ Prompt 정의
prompt = PromptTemplate(
    input_variables=["context", "question"],
    template="""
당신은 Selenium 테스트 자동화 코드를 생성하는 전문가입니다.

아래는 웹 페이지의 HTML DOM 요소 목록(context)이며,  
사용자가 테스트 시나리오(question)를 자연어로 입력했습니다.

다음 지침을 반드시 지키세요:

✅ [기본 테스트 코드 구조]
- `unittest.TestCase` 클래스를 사용하세요.
- `setUp()`에서는 `default_setting.setup()`을 통해 WebDriver를 초기화하세요.
- `case_id`는 아래처럼 추출하세요:
  case_id = os.path.basename(os.path.splitext(__file__)[0])
- `log_setting.logger.info()`를 통해 각 단계를 로깅하세요.
- `tearDown()`에서는 결과 업로드 및 `driver.quit()`을 반드시 호출하세요.
- `if __name__ == "__main__":` 구문도 포함하세요.

✅ [셀렉터 우선순위 및 규칙]

- 각 DOM 요소는 반드시 아래 우선순위에 따라 선택하세요:
  1. ID가 있으면 → 반드시 By.ID 사용
  2. ID가 없고 class가 있으면 → By.CLASS_NAME 또는 By.CSS_SELECTOR 사용
  3. ID와 class가 모두 없으면 → context에 제공된 XPath를 그대로 사용

- 셀렉터 값은 반드시 context에 명시된 값만 사용하세요.
- 절대 임의 생성하거나 유추하지 마세요.

✅ [자연어 ↔ DOM 요소 매핑 지침]
- 시나리오에서 언급된 의미(예: “로그인”, “비밀번호 입력”)를 이해하고,
- context의 `text` 또는 `description` 필드에서 의미적으로 가장 유사한 DOM 요소를 선택하세요.
- 해당 DOM 요소의 ID, class, xpath는 context에 나온 값만 사용하세요.
- 절대 임의 추측으로 생성하지 마세요.
- ID, class 등은 자연어 표현과 다를 수 있습니다. 의미적 유사도를 기준으로 정확히 매핑하세요.

✅ [driver.get() 구성]
- context에서 추출한 상대경로 예: "/vpes/login"
- 아래처럼 전체 URL을 구성해 사용하세요:

  target_url = "/vpes/xxx"
  page_url = "http://localhost:38080" + target_url
  driver.get(page_url)

---

## DOM 요소 목록 (context):
{context}

## 테스트 시나리오 (question):
{question}

---

정확하고 실행 가능한 Python Selenium 테스트 코드를 생성하세요.
❗ 오직 코드만 출력하세요. 주석, 설명, 마크다운 금지
"""
)

# 7. 사용자 입력
query = input("💬 테스트 시나리오를 자연어로 입력하세요:\n> ").strip()

# 8. URL 추출
url_match = re.search(r"(/vpes/\S+)", query)
target_url = url_match.group(1) if url_match else None

# 9. 전체 문서에서 URL 필터링
'''
docs = retriever.invoke(query)
if target_url:
    print(f"\n🔎 필터링된 URL 경로: {target_url}")
    docs = [doc for doc in docs if doc.metadata.get("url", "").startswith(target_url)]
    if not docs:
        print("❗ 해당 URL에 해당하는 DOM 요소를 찾지 못했습니다.")
        exit()
'''
docs_raw = db._collection.get(include=["metadatas", "documents"], limit=1000)

if target_url:
    print(f"\n🔎 필터링된 URL 경로: {target_url}")
    docs = [
        type("Doc", (object,), {"metadata": meta, "page_content": doc})
        for doc, meta in zip(docs_raw["documents"], docs_raw["metadatas"])
        if meta.get("url", "").startswith(target_url)
    ]
    if not docs:
        print("❗ 해당 URL에 해당하는 DOM 요소를 찾지 못했습니다.")
        exit()
else:
    print("❗ URL 경로를 시나리오에서 추출하지 못했습니다.")
    exit()


# 10. context 구성
context = "\n".join([
    f"Full URL: {urljoin(BASE_URL, doc.metadata.get('url', ''))}, "
    f"Tag: {doc.metadata.get('tag')}, "
    f"ID: {doc.metadata.get('id')}, "
    f"Class: {doc.metadata.get('class')}, "
    f"XPath: {doc.metadata.get('xpath')}, "
    f"Text: {doc.metadata.get('text')}, "
    f"Description: {doc.metadata.get('desc')}"
    for doc in docs
])

print("\n🔎 최종 context (LLM에게 전달되는 값):\n")
print(context)
print("=" * 60)
print("\n📌 context에 포함된 ID 목록:")
for doc in docs:
    if doc.metadata.get("id"):
        print(f"- {doc.metadata['id']}")


# 11. LLMChain 실행
chain = (
    RunnableMap({"context": lambda _: context, "question": lambda _: query})
    | prompt
    | llm
    | StrOutputParser()
)

generated_code = chain.invoke({
    "context": context,
    "question": query
})

# 12. ID/XPath 유효성 검사 및 교정
generated_code = validate_generated_code(generated_code, docs, auto_fix=True)

# 13. 출력 및 저장
print("\n💻 생성된 Selenium 테스트 코드:")
print("=" * 60)
print(generated_code)
print("=" * 60)

file_name = "generated_test_final.py"
with open(file_name, "w", encoding="utf-8") as f:
    f.write(generated_code)

print(f"\n✅ 코드가 '{file_name}' 파일로 저장되었습니다.")
