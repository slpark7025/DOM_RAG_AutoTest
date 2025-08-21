from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os
import re
from urllib.parse import urlsplit
from pathlib import Path

# 크롬 드라이버 실행
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)

# 기본 폴더 생성
os.makedirs("html_pages/projects", exist_ok=True)

def save_html_with_url(filepath, html_content, url):
    # HTML 주석 형태로 URL 삽입
    url_comment = f"<!-- source_url: {url} -->\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(url_comment + html_content)

### 1. 로그인 페이지 접속 및 저장
login_url = "http://localhost:38080/vpes/login"
driver.get(login_url)
time.sleep(2)
save_html_with_url("html_pages/login.html", driver.page_source, "/vpes/login")
print("[✅ 저장 완료] login.html")

### 2. 로그인 수행
driver.find_element(By.XPATH, '//input[@placeholder="아이디"]').send_keys("admin")
driver.find_element(By.XPATH, '//input[@placeholder="비밀번호"]').send_keys("suresoft")
driver.find_element(By.XPATH, '//button[contains(text(), "로그인")]').click()
time.sleep(3)

### 3. 대시보드 저장
dashboard_url = "http://localhost:38080/vpes"
driver.get(dashboard_url)
time.sleep(2)
save_html_with_url("html_pages/dashboard.html", driver.page_source, "/vpes")
print("[✅ 저장 완료] dashboard.html")

### 4. 슬러그 수동 입력
slug = input("📥 프로젝트 슬러그를 입력하세요 (예: slpark_test): ").strip()
print(f"[🎯 입력된 슬러그] {slug}")

project_path = f"html_pages/projects/{slug}"
menu_path = f"{project_path}/menus"
os.makedirs(menu_path, exist_ok=True)

### 5. 프로젝트 개요 페이지 저장
detail_path = f"/vpes/ProjectReliabilityProcess/{slug}"
detail_url = f"http://localhost:38080{detail_path}"
driver.get(detail_url)
time.sleep(2)
save_html_with_url(f"{project_path}/ProjectReliabilityProcess.html", driver.page_source, detail_path)
print("[✅ 저장 완료] ProjectReliabilityProcess.html")

### 6. 메뉴 목록
menu_paths = {
    #"프로젝트 개요": "ProjectReliabilityProcess",
    "기술 문서 검증": "ProjectDocVerification",
    "기술 문서 검증 결과": "ProjectDocResult",
    "파일 정보": "ProjectDetailFileManage",
    "함수 정보": "ProjectDetailFunctionManage",
    "그룹 정보": "ProjectDetailGroupManage",
    "결과 요약": "ProjectDetailTransition",
    "정적 시험": "ProjectDetailStatic",
    "동적 시험": "ProjectDetailDynamic",
    "소스코드 메트릭": "ProjectDetailMetric",
    "예외처리 결과": "ProjectDetailException",
    "통합 모의 시험": "ProjectDetailSoftwareProcess",
    "빌드 수행": "ProjectBuildExecution",
    "콘솔 출력": "ProjectDetailConsole",
    "산출물 생성": "ReportGenerate",
    "빌드 설정": "ProjectBuildConfig",
    "프로젝트 설정": "ProjectModify",
    "진행률 설정": "ProjectProgressHistory",
    "규칙 설정": "ProjectRuleSetting",
}

popup_button_texts = ["SCM 설정", "LLM 설정"]
saved_modals = set()

### 7. 메뉴 순회 저장
for menu_name, path in menu_paths.items():
    rel_path = f"/vpes/{path}/{slug}"
    url = f"http://localhost:38080{rel_path}"
    file_name = f"{path}.html"

    if path == "ProjectDetailFunctionManage":
        try:
            driver.get(detail_url)
            time.sleep(2)
            try:
                driver.find_element(By.ID, "projectSourceCode-tab").click()
            except:
                pass
            time.sleep(2)
            # 함수 정보 클릭
            driver.find_element(By.XPATH, "//a[contains(text(),'함수  정보')]").click()
            time.sleep(2)  # 페이지 로딩 대기
            save_html_with_url(f"{menu_path}/{file_name}", driver.page_source, rel_path)
            print(f"[✅ 저장 완료] {menu_name} → {file_name}")

        except Exception as e:
            print(f"[⚠️ 함수 정보 저장 실패] {e}")

        continue

    # === 나머지 메뉴는 기존처럼 URL 직접 이동해서 저장 ===
    driver.get(url)
    time.sleep(2)
    save_html_with_url(f"{menu_path}/{file_name}", driver.page_source, rel_path)
    print(f"[✅ 저장 완료] {menu_name} → {file_name}")

    # 모달 처리
    for popup_text in popup_button_texts:
        if popup_text in saved_modals:
            continue

        try:
            xpath = f'//button[span[contains(text(), "{popup_text}")]]'
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
            popup_btn = driver.find_element(By.XPATH, xpath)

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", popup_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", popup_btn)

            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "modal-content")))
            time.sleep(1)

            popup_safe = popup_text.replace(" ", "_")
            modal_filename = f"모달_{path}_{popup_safe}.html"
            modal_url = f"{rel_path} (modal: {popup_text})"
            save_html_with_url(f"{menu_path}/{modal_filename}", driver.page_source, modal_url)
            print(f"[✅ 저장 완료] {popup_text} 모달 → {modal_filename}")
            saved_modals.add(popup_text)

            close_btn = driver.find_element(By.XPATH, '//button[contains(text(), "닫기") or contains(text(), "×")]')
            driver.execute_script("arguments[0].click();", close_btn)
            time.sleep(1)

        except Exception as e:
            print(f"[⚠️ {popup_text} 버튼 실패] {menu_name}: {e}")

### 8. 상단 메뉴 저장
top_menu_pages = {
    "과제 정보 조회": "http://localhost:38080/vpes/ProjectHistory",
    "Knowledge Hub 대시보드": "http://localhost:38080/vpes/KnowledgeHub/Dashboard",
    "Knowledge Hub 정적검증 - 규칙": "http://localhost:38080/vpes/KnowledgeHub/Board/STATIC/RULE",
    "Knowledge Hub 정적검증 - 개선 예제": "http://localhost:38080/vpes/KnowledgeHub/Board/STATIC/EXAMPLE",
    "설정": "http://localhost:38080/vpes/GlobalSettingUser",
    "도움말": "http://localhost:38080/vpes/HelpMetric",
    "그룹": "http://localhost:38080/vpes/ProjectGroup",
}
top_menu_path = "html_pages/top_menu"
os.makedirs(top_menu_path, exist_ok=True)

for name, url in top_menu_pages.items():
    driver.get(url)
    time.sleep(2)

    parsed = urlsplit(url)
    # 경로만 분해 (빈 조각 제거) → ['vpes','KnowledgeHub','Board','STATIC','RULE']
    parts_all = [p for p in parsed.path.split('/') if p]
    # /vpes 다음만 사용
    if "vpes" in parts_all:
        vpes_idx = parts_all.index("vpes")
        parts = parts_all[vpes_idx + 1:]
        rel_path = "/" + "/".join(parts_all[vpes_idx:])  # HTML 주석용: /vpes/...
    else:
        parts = parts_all
        rel_path = parsed.path if parsed.path.startswith("/") else "/" + parsed.path

    # 저장 경로 구성
    if not parts:
        file_path = os.path.join(top_menu_path, "index.html")
    elif len(parts) > 1:
        dir_path = os.path.join(top_menu_path, *parts[:-1])
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, parts[-1] + ".html")
    else:
        file_path = os.path.join(top_menu_path, parts[0] + ".html")

    save_html_with_url(file_path, driver.page_source, rel_path)
    print(f"[✅ 저장 완료] {name} → {file_path}")


def save_detail_trimmed(url):
    """
    RULE/EXAMPLE 상세 URL을
    html_pages/top_menu/KnowledgeHub/Board/STATIC/{RULE|EXAMPLE}/READ.html 로 저장
    """
    driver.get(url)
    time.sleep(2)

    parsed = urlsplit(driver.current_url)
    path = parsed.path

    # /vpes/KnowledgeHub/Board/READ/STATIC/RULE/...  또는  .../EXAMPLE/...
    m = re.search(r"/vpes/KnowledgeHub/Board/READ/STATIC/(RULE|EXAMPLE)", path, re.IGNORECASE)
    if not m:
        print(f"[⚠️ 저장 스킵] 예상 경로 아님: {path}")
        return

    page_type = m.group(1).upper()   # RULE or EXAMPLE

    # 저장 폴더: .../STATIC/RULE/ 또는 .../STATIC/EXAMPLE/
    base_dir = Path("html_pages/top_menu/KnowledgeHub/Board/STATIC") / page_type
    base_dir.mkdir(parents=True, exist_ok=True)

    # 파일명: READ.html (ID 사용하지 않음)
    out_path = base_dir / "READ.html"

    # 원본 경로는 READ 포함한 실제 상세 URL로 남김
    rel_path = path
    save_html_with_url(str(out_path), driver.page_source, rel_path)
    print(f"[✅ 저장 완료] {page_type} → {out_path}")

# ===== 여러 상세 페이지를 딕셔너리로 관리 =====
detail_pages = {
    "Knowledgehub RULE 예시(뒤 식별자 수정 필요) ": "http://localhost:38080/vpes/KnowledgeHub/Board/READ/STATIC/RULE/e6daa48c8f110d6a9c512531",
    "Knowledgehub EXAMPLE 예시(뒤 식별자 수정 필요) ": "http://localhost:38080/vpes/KnowledgeHub/Board/READ/STATIC/EXAMPLE/22931c3e7de14a3b9c72b96b9d11f96c1755667602163",
    # 필요 시 추가
}

for name, url in detail_pages.items():
    try:
        save_detail_trimmed(url)
    except Exception as e:
        print(f"[⚠️ {name} 저장 실패] {e}")

### 9. 종료
driver.quit()
