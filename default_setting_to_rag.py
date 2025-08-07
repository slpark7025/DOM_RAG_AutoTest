import os
import ast
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# 🔐 환경변수 로딩
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY가 .env에 없습니다.")


# 🔍 driver.get() 호출 여부 감지 함수
def function_contains_driver_get(node):
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Call):
            if isinstance(subnode.func, ast.Attribute):
                if subnode.func.attr == "get":
                    if isinstance(subnode.func.value, ast.Name) and subnode.func.value.id in ["driver", "self.driver"]:
                        return True
    return False

# 📘 함수 요약 추출
def default_setting_function_summary(file_path: str) -> list:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    lines = source.splitlines()
    summaries = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            name = node.name
            args = [arg.arg for arg in node.args.args]
            docstring = ast.get_docstring(node)

            # 🔹 주석 수집 버퍼
            all_comments = []

            # 1. 함수 선언 바로 위 주석
            above_lineno = node.lineno - 2
            while above_lineno >= 0:
                line = lines[above_lineno].strip()
                if line.startswith("#"):
                    all_comments.insert(0, line[1:].strip())  # 앞에 추가
                    above_lineno -= 1
                else:
                    break

            # 2. 함수 내부 주석
            body_lineno = node.body[0].lineno if node.body else node.lineno
            end_line = node.body[-1].lineno if node.body else node.lineno
            for line in lines[body_lineno - 1:end_line]:
                line = line.strip()
                if "#" in line:
                    comment_part = line.split("#", 1)[1].strip()
                    all_comments.append(comment_part)

            # driver.get() 포함 여부 분석
            contains_driver_get = function_contains_driver_get(node)

            # 최종 설명
            explanation = docstring or "\n".join(all_comments)
            if contains_driver_get:
                explanation += "\n⚠️ 이 함수는 driver.get() 또는 self.driver.get()을 포함하고 있어, 테스트 코드에서 동일한 URL로 이동하는 중복 호출은 피해야 합니다."

            summary = f"모듈: default_setting\n함수명: {name}\n인자: {args}\n설명: {explanation.strip() if explanation else ''}"
            summaries.append(summary)

    return summaries


# 1. 파일 경로
FILE_PATH = "default_setting.py"

# 2. 요약 추출
summaries = default_setting_function_summary(FILE_PATH)
summary_text = "\n\n".join(summaries)

# 3. 저장
SUMMARY_FILE = "function_summaries.txt"
with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    f.write(summary_text)
print(f"📄 함수 요약 저장 완료 → {SUMMARY_FILE}")

# 4. 청킹
# 한 청크의 문자 수가 최대 512이고, 다음 청크와 앞 청크의 마지막 50자가 겹치게
splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
chunks = splitter.split_text(summary_text)
print(f"✂️ 청크 개수: {len(chunks)}")

# 청크 디버깅용 (정상 반영 확인)
with open("chunks_debug.txt", "w", encoding="utf-8") as f:
    for i, chunk in enumerate(chunks):
        f.write(f"🧩 Chunk {i+1}:\n{chunk}\n{'-'*60}\n")
print("🔍 chunks_debug.txt 저장 완료")

# 5. 임베딩 + Chroma 저장
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
chroma_db = Chroma.from_texts(chunks, embedding_model, persist_directory="./chroma_default_setting", collection_name="default_setting")
chroma_db.persist()
print("✅ Chroma DB 저장 완료: ./chroma_default_setting")
