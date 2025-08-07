import re
from difflib import get_close_matches

def validate_generated_code(generated_code: str, docs: list, auto_fix: bool = False) -> str:
    def normalize_xpath(xpath: str) -> str:
        return xpath.replace("/[document][1]", "") if xpath else ""

    def normalize(value):
        return str(value).strip().lower() if value else ""

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
            valid_xpaths.add(normalize(normalize_xpath(meta["xpath"])))

    # ✅ 2. LLM이 생성한 셀렉터 추출
    used_ids = re.findall(r'By\.ID,\s*["\'](.*?)["\']', generated_code)
    used_classes = re.findall(r'By\.CLASS_NAME,\s*["\'](.*?)["\']', generated_code)
    used_xpaths = [
        normalize_xpath(xp)
        for xp in re.findall(r'By\.XPATH,\s*["\'](.*?)["\']', generated_code)
    ]

    # ✅ 3. 검증 및 자동 수정
    def validate_items(used_list, valid_set, label):
        nonlocal generated_code
        for item in used_list:
            if label == "XPATH":
                item = normalize_xpath(item)
            norm_item = normalize(item)
            if norm_item not in valid_set:
                print(f"⚠️ LLM이 사용한 {label} '{item}' 는 context에 존재하지 않습니다.")

                # 1차 추천: 문자열 유사도 기반
                suggestion = get_close_matches(norm_item, valid_set, n=1, cutoff=0.6)

                if suggestion:
                    suggested = suggestion[0]
                    print(f"👉 대체 추천 {label}: '{suggested}'")
                else:
                    # 의미 기반 대체 추천 시도
                    suggested = suggest_semantic_alternative(item, docs, label)
                    if suggested:
                        print(f"의미 기반 추천 {label}: '{suggested}'")

                # 자동 교정 적용
                if suggested and auto_fix:
                    print(f"✅ 자동 교정됨: '{item}' → '{suggested}'")
                    generated_code = re.sub(
                        rf'By\.{label.upper()},\s*["\']{re.escape(item)}["\']',
                        f'By.{label.upper()}, "{suggested}"',
                        generated_code
                    )
                elif not suggested:
                    print(f"❗ 대체 추천 없음 — 수동 검토 필요")

    validate_items(used_ids, valid_ids, "ID")
    validate_items(used_classes, valid_classes, "CLASS_NAME")
    validate_items(used_xpaths, valid_xpaths, "XPATH")
    generated_code = generated_code.replace("/[document][1]", "")
    return generated_code

#desc 또는 text 필드에 의미적으로 유사한 값이 있는 경우 해당 id/class/xpath 반환
def suggest_semantic_alternative(broken_item: str, docs: list, label: str) -> str or None:
    broken_lower = broken_item.lower()

    for doc in docs:
        meta = doc.metadata
        if label == "ID":
            candidate = meta.get("id")
        elif label == "CLASS_NAME":
            candidate = meta.get("class")
        elif label == "XPATH":
            candidate = meta.get("xpath")
        else:
            candidate = None

        if not candidate:
            continue

        desc = (meta.get("desc") or "").lower()
        text = (meta.get("text") or "").lower()

        if broken_lower in desc or broken_lower in text:
            return candidate.strip()

    return None
