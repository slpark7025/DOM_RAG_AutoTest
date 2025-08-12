from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os

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
login_url = "http://10.10.111.41:38080/vpes/login"
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
dashboard_url = "http://10.10.111.41:38080/vpes"
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
detail_url = f"http://10.10.111.41:38080{detail_path}"
driver.get(detail_url)
time.sleep(2)
save_html_with_url(f"{project_path}/ProjectReliabilityProcess.html", driver.page_source, detail_path)
print("[✅ 저장 완료] ProjectReliabilityProcess.html")

### 6. 메뉴 목록
menu_paths = {
    "프로젝트 개요": "ProjectReliabilityProcess",
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
    url = f"http://10.10.111.41:38080{rel_path}"
    file_name = f"{path}.html"

    if path == "ProjectDetailFunctionManage":
        try:
            driver.get(detail_url)
            time.sleep(2)
            # 코드 관리 탭 클릭 (없으면 그냥 넘어감)
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
    "과제 정보 조회": "http://10.10.111.41:38080/vpes/ProjectHistory",
    "Knowledge Hub": "http://10.10.111.41:38080/vpes/KnowledgeHub/Dashboard",
    "설정": "http://10.10.111.41:38080/vpes/GlobalSettingUser",
    "도움말": "http://10.10.111.41:38080/vpes/HelpMetric",
    "그룹": "http://10.10.111.41:38080/vpes/ProjectGroup",
}
top_menu_path = "html_pages/top_menu"
os.makedirs(top_menu_path, exist_ok=True)

for name, url in top_menu_pages.items():
    driver.get(url)
    time.sleep(2)
    safe_name = url.strip("/").split("/")[-1]
    rel_path = "/" + "/".join(url.split("/")[3:])  # /vpes/...
    save_html_with_url(f"{top_menu_path}/{safe_name}.html", driver.page_source, rel_path)
    print(f"[✅ 저장 완료] {name} → {safe_name}.html")

### 9. 종료
driver.quit()
