# requirements:
# pip install langchain chromadb tiktoken openai

import os
import json
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import TokenTextSplitter
import chromadb
from chromadb.config import Settings

# 1. OpenAI 임베딩 모델 설정
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",  # 사용할 OpenAI 임베딩 모델
    openai_api_key="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"
)

# 2. 토큰 기반 텍스트 분할기 설정
# text-embedding-3-large 모델의 최대 입력 토큰 수(8191 토큰) 내로 분할
splitter = TokenTextSplitter(
    model_name="text-embedding-3-large",
    chunk_size=8000,       # 최대 토큰 수보다 약간 작게
    chunk_overlap=200      # 앞뒤로 중복 토큰
)

# 3. Chroma DB 초기화
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="dom_elements")

# 4. JSON 폴더 로드
json_dir = "./extracted_json"
file_list = [f for f in os.listdir(json_dir) if f.endswith(".json")]

docs, metadatas, ids = [], [], []
global_id = 0

for filename in file_list:
    file_path = os.path.join(json_dir, filename)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ JSON 파싱 실패: {filename}")
        continue

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

        # 분할된 각 청크마다 docs/metadatas/ids에 추가
        for idx, chunk in enumerate(chunks):
            docs.append(chunk)

            # 각 청크에 인덱스 정보 추가
            metadata = clean_item.copy()
            metadata["chunk_index"] = idx
            metadatas.append(metadata)

            ids.append(f"{filename}_{global_id}")
            global_id += 1

# 5. 임베딩 수행 및 Chroma DB에 저장
embeddings_list = embeddings.embed_documents(docs)
collection.add(
    documents=docs,
    embeddings=embeddings_list,
    metadatas=metadatas,
    ids=ids
)

print(f"✅ {len(docs)}개의 청크 임베딩 완료 및 Chroma DB에 저장되었습니다.")
