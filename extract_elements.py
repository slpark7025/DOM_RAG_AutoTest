import os
import json
from bs4 import BeautifulSoup, Comment
from bs4.element import Tag  # ✅ leaf div 판별에 사용

TARGET_TAGS = ["button", "a", "input", "select", "textarea", "label", "th", "span", "p", "form", "font"]
INPUT_DIR = "html_pages"
OUTPUT_DIR = "extracted_json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_all_html_files(base_path):
    html_files = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".html"):
                html_files.append(os.path.join(root, file))
    return html_files

def build_xpath(el):
    parts = []
    while el and el.name:
        sibling_index = 1
        for sibling in el.find_previous_siblings(el.name):
            sibling_index += 1
        parts.insert(0, f"{el.name}[{sibling_index}]")
        el = el.parent
    return "/" + "/".join(parts)

def is_leaf_div(el):
    """하위에 다른 태그(Tag)가 없는 말단 div인지 판별"""
    if el.name != "div":
        return False
    return not any(isinstance(child, Tag) for child in el.children)

def extract_elements_from_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    # ✅ source_url 주석 추출
    source_url = None
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        if "source_url:" in comment:
            source_url = comment.strip().split("source_url:")[1].strip()
            break

    # ✅ 없으면 경고 로그 출력
    if source_url is None:
        rel_path = os.path.relpath(file_path, INPUT_DIR)
        print(f"[⚠️ 경고] {rel_path} → source_url 주석 없음")

    elements = []

    # 기존 TARGET_TAGS 수집
    for tag in TARGET_TAGS:
        for el in soup.find_all(tag):
            info = {
                "tag": tag,
                "text": el.get_text(strip=True) or None,
                "id": el.get("id"),
                "class": el.get("class"),
                "name": el.get("name"),
                "placeholder": el.get("placeholder"),
                "aria-label": el.get("aria-label"),
                "type_attr": el.get("type"),
                "xpath": build_xpath(el),
                "desc": f"{tag.upper()} - {el.get_text(strip=True) or el.get('name') or el.get('id') or 'unnamed'}",
                "url": source_url  # ✅ 모든 요소에 동일한 URL 삽입
            }
            elements.append(info)

    # ✅ 하위 요소가 없는 말단 div 추가 수집
    for el in soup.find_all("div"):
        if is_leaf_div(el):
            info = {
                "tag": "div",
                "text": el.get_text(strip=True) or None,
                "id": el.get("id"),
                "class": el.get("class"),
                "name": el.get("name"),
                "placeholder": el.get("placeholder"),
                "aria-label": el.get("aria-label"),
                "type_attr": el.get("type"),
                "xpath": build_xpath(el),
                "desc": f"DIV - {el.get_text(strip=True) or el.get('name') or el.get('id') or 'unnamed'}",
                "url": source_url
            }
            elements.append(info)

    return elements

def main():
    html_files = get_all_html_files(INPUT_DIR)
    for file_path in html_files:
        elements = extract_elements_from_html(file_path)
        rel_path = os.path.relpath(file_path, INPUT_DIR)
        json_name = rel_path.replace(os.sep, "_").replace(".html", ".json")
        json_path = os.path.join(OUTPUT_DIR, json_name)

        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(elements, jf, ensure_ascii=False, indent=2)

        print(f"[✅ 완료] {rel_path} → {json_path}")

if __name__ == "__main__":
    main()
