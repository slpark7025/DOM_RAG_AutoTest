import os
import json

INPUT_DIR = "extracted_json"

def enhance_desc(item):
    base = item.get("tag", "").upper()
    extras = []

    # 후보 정보 추출
    cls = item.get("class")
    if cls:
        extras.append(f"class={','.join(cls)}")

    label = item.get("aria-label")
    if label:
        extras.append(f"aria-label={label}")

    name = item.get("name")
    if name:
        extras.append(f"name={name}")

    type_attr = item.get("type_attr")
    if type_attr:
        extras.append(f"type={type_attr}")

    xpath = item.get("xpath")
    if xpath:
        parts = xpath.strip("/").split("/")
        extras.append(f"xpath-depth={len(parts)}")

    if extras:
        return f"{base} - unnamed ({'; '.join(extras)})"
    else:
        return f"{base} - unnamed"

def process_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    modified = False
    for item in data:
        if "unnamed" in item.get("desc", "").lower():
            new_desc = enhance_desc(item)
            if item["desc"] != new_desc:
                item["desc"] = new_desc
                modified = True

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[✨ 보강 완료] {os.path.basename(file_path)}")
    else:
        print(f"[✅ 그대로 유지] {os.path.basename(file_path)}")

def main():
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(INPUT_DIR, filename)
            process_file(file_path)

if __name__ == "__main__":
    main()
