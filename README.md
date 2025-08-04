++ 작업 중 ++ 



# DOM_RAG_AutoTest

DOM 데이터 활용 테스트 자동화

- HTML → DOM 요소 추출
- 텍스트 정제 및 메타데이터 구성
- SentenceTransformer 기반 텍스트 임베딩
- ChromaDB 저장 및 검색 인덱스 생성
- 자동 테스트 시나리오 구성 기반 데이터 저장
- 추후 LangChain 연동 예정



## 📁 프로젝트 구조
```
├── embed_json.py # 임베딩 및 Chroma DB 저장
├── enhance_unnamed_desc.py # 정제되지 않은 설명 자동 보완
├── extract_elements.py # HTML → DOM 요소 추출
├── extract_vpes_dom.py # VPES HTML 크롤링 (초기 데이터 수집)
├── requirements.txt # 필요한 Python 패키지 명세
├── README.md # 프로젝트 설명 파일
```

+ 아래 폴더들은 **스크립트 실행 시 자동 생성됩니다** (Git에 포함되지 않음)
```
├── html_pages/ # 수집된 HTML 원본
├── extracted_json/ # DOM 요소가 JSON 형태로 저장됨
├── chroma_db/ # Chroma DB에 저장된 임베딩 벡터
```

## 실행 순서


0. 환경 설치 -> requirements.txt


1. extract_vpes_dom.py 수행 -> html_pages/ 폴더가 생성됨


2. python extract_elements.py 수행 -> xtracted_json/ 폴더 생성


3. python enhance_unnamed_desc.py 수행 -> xtracted_json/ 폴더 내 desc 파라미터 내 unnamed로 기입된 부분 보완


4. python embed_json.py 수행 -> 임베딩 + DB 저장 -> chroma_db/ 폴더 생성
