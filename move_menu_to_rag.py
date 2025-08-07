import os
import ast
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# 🔐 환경 변수 로딩
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY가 .env에 없습니다.")

# 🔍 driver.get() 포함 여부 분석
def function_contains_driver_get(node):
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Call):
            if isinstance(subnode.func, ast.Attribute):
                if subnode.func.attr == "get":
                    if isinstance(subnode.func.value, ast.Name) and subnode.func.value.id in ["driver", "self.driver"]:
                        return True
    return False

# 📘 함수 요약 추출
def move_menu_function_summary(file_path: str) -> list:
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

            # 🔹 함수 정의 위쪽 주석 추출
            above_lineno = node.lineno - 2
            header_comments = []
            while above_lineno >= 0:
                line = lines[above_lineno].strip()
                if line.startswith("#"):
                    header_comments.insert(0, line[1:].strip())
                    above_lineno -= 1
                else:
                    break

            comment_summary = "\n".join(header_comments)

            # 🔍 driver.get() 포함 여부 분석
            contains_driver_get = function_contains_driver_get(node)

            # 🧾 설명
            explanation = docstring or comment_summary
            if contains_driver_get:
                explanation += "\n⚠️ 이 함수는 driver.get() 또는 self.driver.get()을 포함하고 있어 중복 호출은 피해야 합니다."

            summary = f"모듈: move_menu\n함수명: {name}\n인자: {args}\n설명: {explanation.strip() if explanation else ''}"
            summaries.append(summary)

    return summaries

# 📄 파일 경로
FILE_PATH = "move_menu.py"

# 📘 요약 추출
summaries = move_menu_function_summary(FILE_PATH)
summary_text = "\n\n".join(summaries)

# 📝 텍스트 저장
SUMMARY_FILE = "move_menu_summaries.txt"
with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    f.write(summary_text)
print(f"📄 move_menu 함수 요약 저장 완료 → {SUMMARY_FILE}")

# ✂️ 청킹
splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
chunks = splitter.split_text(summary_text)
print(f"✂️ 청크 개수: {len(chunks)}")

# 🔍 청크 디버깅 파일
with open("move_menu_chunks_debug.txt", "w", encoding="utf-8") as f:
    for i, chunk in enumerate(chunks):
        f.write(f"🧩 Chunk {i+1}:\n{chunk}\n{'-'*60}\n")
print("🔍 move_menu_chunks_debug.txt 저장 완료")

# 💾 벡터 DB 저장
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
chroma_db = Chroma.from_texts(
    chunks,
    embedding_model,
    persist_directory="./chroma_move_menu",
    collection_name="move_menu"
)
chroma_db.persist()
print("✅ Chroma DB 저장 완료: ./chroma_move_menu")
