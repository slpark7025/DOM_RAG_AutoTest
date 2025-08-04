import os
import json
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import chromadb



# 1. 모델 로딩 (경량 임베딩 모델)
model = SentenceTransformer("all-MiniLM-L6-v2")

# 2. Chroma DB 초기화
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="dom_elements")

# 3. JSON 폴더 로드
json_dir = "./extracted_json"
file_list = [f for f in os.listdir(json_dir) if f.endswith(".json")]

# 4. DOM 요소 수집
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
        # ✅ 문장 생성 (벡터화 대상)
        doc_text = f"{item.get('tag', '')} with text '{item.get('text', '')}', description: {item.get('desc', '')}"
        docs.append(doc_text)

        # ✅ 'class' 문자열화 + None 제거
        clean_item = {
            k: ", ".join(v) if k == "class" and isinstance(v, list)
            else v for k, v in item.items() if v is not None
        }
        clean_item["source_file"] = filename
        clean_item["source_url"] = clean_item.get("url", "unknown")


        # ✅ 메타데이터 구성
        metadatas.append(clean_item)

        # ✅ 고유 ID 부여
        ids.append(f"{filename}_{global_id}")
        global_id += 1

# 5. 임베딩 및 DB 저장
embeddings = model.encode(docs, show_progress_bar=True).tolist()
collection.add(documents=docs, embeddings=embeddings, metadatas=metadatas, ids=ids)
#client.persist()

print("✅ 전체 JSON 요소 임베딩 완료! Chroma DB 저장됨.")
