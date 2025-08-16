# requirements:
# pip install langchain chromadb tiktoken openai python-dotenv

import os
import json
import uuid
from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import TokenTextSplitter
import chromadb

# ===== 0) 환경 변수 로드 =====
# .env 파일에 OPENAI_API_KEY=... 저장해두면 자동으로 사용됩니다.
load_dotenv()

# ===== 1) OpenAI 임베딩 모델 설정 =====
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large"  # openai_api_key는 환경변수 사용 권장
)

# ===== 2) 토큰 기반 텍스트 분할기 =====
# text-embedding-3-large 모델의 최대 입력 토큰 수(8191)보다 약간 작게 설정
splitter = TokenTextSplitter(
    model_name="text-embedding-3-large",
    chunk_size=8000,
    chunk_overlap=200
)

# ===== 3) 입력/출력 경로 =====
json_dir = "./extracted_json"
base_chroma_dir = "./chroma"
os.makedirs(base_chroma_dir, exist_ok=True)

# ===== 4) JSON 파일 목록 =====
file_list = [f for f in os.listdir(json_dir) if f.endswith(".json")]
if not file_list:
    print("⚠️ JSON 파일이 없습니다. 경로를 확인하세요:", json_dir)

# ===== 5) 각 JSON 파일별로 '개별 DB(폴더)' 생성하여 임베딩 =====
for filename in file_list:
    file_path = os.path.join(json_dir, filename)

    # 폴더명에서 ".json" 확장자를 제거하여 DB 폴더 생성
    folder_name = os.path.splitext(filename)[0]        # ← ".json" 제거
    db_dir = os.path.join(base_chroma_dir, folder_name)
    os.makedirs(db_dir, exist_ok=True)

    # 파일 파싱
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ JSON 파싱 실패: {filename}")
        continue

    # 문서/메타/ID 버퍼
    docs, metadatas, ids = [], [], []

    # 아이템을 분해하여 청크 생성
    for item in data:
        # 원본 텍스트 생성
        raw_text = (
            f"Tag: {item.get('tag', '')}, "
            f"ID: {item.get('id', '')}, "
            f"Class: {', '.join(item.get('class', [])) if isinstance(item.get('class'), list) else item.get('class', '')}, "
            f"Text: {item.get('text', '')}, "
            f"XPath: {item.get('xpath', '')}, "
            f"Description: {item.get('desc', '')}"
        )

        # 토큰 기반 분할 → 여러 청크 생성
        chunks = splitter.split_text(raw_text)

        # metadata 기본 정보 정리
        clean_item = {
            k: ", ".join(v) if k == "class" and isinstance(v, list)
            else v for k, v in item.items() if v is not None
        }
        clean_item["source_file"] = filename
        clean_item["source_url"] = clean_item.get("url", "unknown")
        clean_item["db_folder"] = folder_name  # 어떤 DB 폴더에 들어갔는지 기록

        # 분할된 각 청크마다 docs/metadatas/ids에 추가
        for idx, chunk in enumerate(chunks):
            docs.append(chunk)

            metadata = clean_item.copy()
            metadata["chunk_index"] = idx
            metadatas.append(metadata)

            # 각 청크마다 고유 ID 생성(재실행 시 중복 방지)
            ids.append(f"{folder_name}_{idx}_{uuid.uuid4().hex[:8]}")

    if not docs:
        print(f"ℹ️ 임베딩할 청크가 없습니다: {filename}")
        continue

    # ===== Chroma: JSON 파일별 개별 DB(폴더)로 저장 =====
    client = chromadb.PersistentClient(path=db_dir)
    collection = client.get_or_create_collection(name="dom_elements")

    # 임베딩 수행 및 저장 (파일 단위로 수행)
    embeddings_list = embeddings.embed_documents(docs)
    collection.add(
        documents=docs,
        embeddings=embeddings_list,
        metadatas=metadatas,
        ids=ids
    )

    print(f"✅ '{filename}' → {len(docs)}개 청크 임베딩 완료 (DB 폴더: {db_dir})")

print("🎉 모든 파일 처리 완료.")
