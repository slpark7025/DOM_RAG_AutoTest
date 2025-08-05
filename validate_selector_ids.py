import re
from difflib import get_close_matches

def normalize(value):
    return str(value).strip().lower() if value else ""

def validate_generated_code(generated_code: str, docs: list, auto_fix: bool = False) -> str:
    # ✅ 1. context에서 유효한 값들 추출
    valid_ids = set()
    valid_classes = set()
    valid_xpaths = set()

    for doc in docs:
        meta = doc.metadata
        if meta.get("id"):
            valid_ids.add(normalize(meta["id"]))
        if meta.get("class"):
            for cls in str(meta["class"]).split(","):
                valid_classes.add(normalize(cls))
        if meta.get("xpath"):
            valid_xpaths.add(normalize(meta["xpath"]))

    # ✅ 2. LLM이 생성한 셀렉터 추출
    used_ids = re.findall(r'By\.ID,\s*["\'](.*?)["\']', generated_code)
    used_classes = re.findall(r'By\.CLASS_NAME,\s*["\'](.*?)["\']', generated_code)
    used_xpaths = re.findall(r'By\.XPATH,\s*["\'](.*?)["\']', generated_code)

    # ✅ 3. 검증 및 자동 수정
    def validate_items(used_list, valid_set, label):
        nonlocal generated_code
        for item in used_list:
            norm_item = normalize(item)
            if norm_item not in valid_set:
                print(f"⚠️ LLM이 사용한 {label} '{item}' 는 context에 존재하지 않습니다.")
                suggestion = get_close_matches(norm_item, valid_set, n=1, cutoff=0.6)
                if suggestion:
                    suggested = suggestion[0]
                    print(f"👉 대체 추천 {label}: '{suggested}'")
                    if auto_fix:
                        print(f"✅ 자동 교정됨: '{item}' → '{suggested}'")
                        # 정규식 패턴으로 By.ID, "username" → By.ID, "username"
                        generated_code = re.sub(
                            rf'By\.{label.upper()},\s*["\']{re.escape(item)}["\']',
                            f'By.{label.upper()}, "{suggested}"',
                            generated_code
                        )
                else:
                    print(f"❗ 대체 추천 없음 — 수동 검토 필요")

    validate_items(used_ids, valid_ids, "ID")
    validate_items(used_classes, valid_classes, "CLASS_NAME")
    validate_items(used_xpaths, valid_xpaths, "XPATH")

    return generated_code
