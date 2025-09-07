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
from selenium.webdriver.common.keys import Keys


# 크롬 드라이버 실행
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 15)

# 기본 폴더 생성
os.makedirs("html_pages/projects", exist_ok=True)

def save_html_with_url(filepath, html_content, url):
    canonical = url.split(" (", 1)[0].strip()   # 괄호 뒤 메모 제거
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"<!-- source_url: {canonical} -->\n")
        if canonical != url:
            f.write(f"<!-- source_context: {url} -->\n")     # 메모는 별도 키로 보존
        f.write(html_content)

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
CHECKBOX_REQUIRED_MENUS = [
    "ProjectDetailFileManage",     # 파일 정보
    "ProjectDetailFunctionManage", # 함수 정보
    # 필요시 추가 가능
]
saved_modals = set()

# ===================== ⋮ 드롭다운 스냅샷 헬퍼 (사이트 맞춤) =====================

def wait_dropdown_appears_for_button(driver, btn, timeout=4):
    """해당 '더보기' 버튼을 클릭 후 aria-expanded=true 또는 전형적 메뉴 DOM 등장까지 대기"""
    # 1) 먼저 aria-expanded=true 대기
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: btn.get_attribute("aria-expanded") in ("true", True)
        )
        return
    except TimeoutException:
        pass

    # 2) 메뉴 컨테이너 후보 대기 (body 포털 포함)
    menu_candidates = (
        # 부트스트랩/커스텀
        '.dropdown-menu.show, .dropdown-menu[style*="display"], .dropdown.open .dropdown-menu'
        # Ant/MUI 등
        ', .ant-dropdown, .ant-dropdown-menu, .MuiPopover-root, .MuiMenu-paper'
        ', [role="menu"], .popover.show, .Popper, .popper'
    )
    try:
        WebDriverWait(driver, 2).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, menu_candidates))
        )
    except TimeoutException:
        time.sleep(0.3)  # 아주 짧게 유예

def find_kebab_buttons(driver):
    """당신 페이지에 맞춰 .dropdown-more-btn 우선 수집 + 보이는 것만 반환(오른쪽부터)"""
    buttons = []
    # 1) 사이트 고유 셀렉터(가장 정확)
    try:
        buttons += driver.find_elements(By.CSS_SELECTOR, 'button.dropdown-more-btn')
    except Exception:
        pass

    # 2) 보조 후보(혹시 다른 화면에 클래스가 다른 경우 대비)
    xpaths = [
        '//*[self::button or self::a or @role="button"][@aria-haspopup="true" and contains(@class,"more") or contains(@class,"dropdown-more")]',
        '//*[self::button or self::a or @role="button"][contains(normalize-space(.),"더보기") or contains(normalize-space(.),"⋮")]'
    ]
    for xp in xpaths:
        try:
            buttons += driver.find_elements(By.XPATH, xp)
        except Exception:
            pass

    # 보이는 것만, 우측부터(툴바 케밥이 우측에 많음)
    seen, vis = set(), []
    for b in buttons:
        try:
            if not b.is_displayed():
                continue
            if b.id in seen:
                continue
            seen.add(b.id)
            x = b.location.get("x", 0)
            vis.append((x, b))
        except Exception:
            continue
    vis.sort(key=lambda t: t[0], reverse=True)
    return [b for _, b in vis]

def open_each_kebab_and_save(driver, save_basepath, rel_path, max_buttons=6):
    """
    .dropdown-more-btn 들을 하나씩 열고, 열린 상태 DOM을
    {save_basepath}__kebab{idx}.html 로 저장
    """
    kebabs = find_kebab_buttons(driver)
    if not kebabs:
        return 0

    count = 0
    base, ext = os.path.splitext(save_basepath)
    if not ext:
        ext = '.html'

    for idx, btn in enumerate(kebabs[:max_buttons]):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            time.sleep(0.1)
            driver.execute_script("arguments[0].click();", btn)  # JS 클릭로 안전하게
            wait_dropdown_appears_for_button(driver, btn, timeout=4)

            out_path = f"{base}__kebab{idx}{ext}"
            save_html_with_url(out_path, driver.page_source, f"{rel_path} (kebab:{idx})")
            count += 1

            # 다음 버튼을 위해 닫아두고 싶으면(선택): 다시 클릭 → expanded=false
            try:
                if btn.get_attribute("aria-expanded") in ("true", True):
                    driver.execute_script("arguments[0].click();", btn)
            except Exception:
                pass
        except Exception:
            continue
    return count
# ========================================================================

# ===================== ⋮ 드롭다운 스냅샷 헬퍼 (사이트 맞춤) =====================
def get_more_button(driver, timeout=6):
    selectors = [
        (By.CSS_SELECTOR, "button.dropdown-more-btn"),
        (By.CSS_SELECTOR, ".dropdown-more-btn.table-button-background"),
        (By.XPATH, '//*[self::button or self::a or @role="button"]'
                   '[contains(@class,"dropdown-more") or contains(normalize-space(.),"⋮")]'),
    ]
    for by, sel in selectors:
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, sel))
            )
            if el.is_displayed():
                return el
        except TimeoutException:
            continue
    return None


def wait_button_enabled(driver, button, timeout=6):
    end = time.time() + timeout
    while time.time() < end:
        try:
            dis = button.get_attribute("disabled")
            aria = button.get_attribute("aria-disabled")
            cls = button.get_attribute("class") or ""
            style = button.get_attribute("style") or ""
            enabled = (dis is None) and (aria not in ("true", True)) \
                      and ("disabled" not in cls) and ("pointer-events: none" not in style)
            if enabled and button.is_displayed():
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def click_dropdown_item_by_text(driver, item_text, timeout=6):
    menu_root_css = (
        '.dropdown-menu.show, .dropdown-menu[style*="display"], .dropdown.open .dropdown-menu,'
        '.ant-dropdown, .ant-dropdown-menu, .MuiPopover-root, .MuiMenu-paper,'
        '[role="menu"], .popover.show, .Popper, .popper'
    )
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, menu_root_css))
    )
    xp = ('//*[self::button or self::a or self::li or @role="menuitem"]'
          f'[contains(normalize-space(.), "{item_text}")]')
    el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xp)))
    driver.execute_script("arguments[0].scrollIntoView({block:" '"center"});', el)
    time.sleep(0.1)
    driver.execute_script("arguments[0].click();", el)


def wait_modal_open(driver, timeout=8):
    modal_css = (
        '.modal.show .modal-dialog, .modal-dialog, .modal-content,'
        '.ant-modal, .ant-modal-wrap,'
        '.MuiDialog-container, .MuiDialog-paper,'
        '[role="dialog"], [aria-modal="true"]'
    )
    modal = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, modal_css))
    )
    WebDriverWait(driver, timeout).until(EC.visibility_of(modal))
    return modal


def save_current_modal(driver, save_path, rel_label):
    # rel_label 예: "/vpes/ProjectDetailFileManage/slug (dropdown-modal: 사용자 파일 지정)"
    rel_url = rel_label.split(" (", 1)[0].strip()

    with open(save_path, "w", encoding="utf-8") as f:
        f.write(f"<!-- source_url: {rel_url} -->\n")          # 추출기가 읽는 키
        f.write(f"<!-- source_context: {rel_label} -->\n")    # 부가정보(있으면 좋음)
        f.write(driver.page_source)
def _top_visible_modal(driver, timeout=8):
    # 화면에 떠있는 모달들 중 가장 위(마지막) 모달만 반환
    modal_css = (
        '.modal.show, .ant-modal, .MuiDialog-paper, '
        '[role="dialog"], [aria-modal="true"]'
    )
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, modal_css))
    )
    modals = driver.find_elements(By.CSS_SELECTOR, modal_css)
    return modals[-1] if modals else None

def close_modal(driver, timeout=8):
    try:
        # 모달이 뜰 때까지 대기
        time.sleep(5)

        # 닫기 버튼 클릭 (텍스트 "닫기" 또는 "×")
        close_btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[contains(text(), "닫기") or contains(text(), "×")]')
            )
        )
        driver.execute_script("arguments[0].scrollIntoView({block:" '"center"});', close_btn)
        driver.execute_script("arguments[0].click();", close_btn)

        # 닫힐 때까지 대기
        WebDriverWait(driver, timeout).until_not(
            EC.presence_of_element_located((By.CLASS_NAME, "modal-content"))
        )
        print("[✅ 모달 닫기 성공]")
    except Exception as e:
        print(f"[⚠️ 모달 닫기 실패] {e}")

# ========================================================================

### 7. 메뉴 순회 저장
# ========================================================================
# 7. 메뉴 순회 저장 (들여쓰기 교정본)
# ========================================================================
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

            try:
                n = open_each_kebab_and_save(
                    driver,
                    save_basepath=f"{menu_path}/{file_name}",
                    rel_path=rel_path,
                    max_buttons=6
                )
                if n:
                    print(f"[✅ 더보기(⋮) 열린 상태 스냅샷 {n}건 추가 저장] {menu_name}")
            except Exception as e:
                print(f"[⚠️ 더보기 스냅샷 실패] {menu_name}: {e}")

        except Exception as e:
            print(f"[⚠️ 함수 정보 저장 실패] {e}")

        continue
    if path == "ProjectDetailGroupManage":
        try:
            driver.get(detail_url)
            time.sleep(2)
            try:
                driver.find_element(By.ID, "projectSourceCode-tab").click()
            except:
                pass
            time.sleep(2)
            # 함수 정보 클릭
            driver.find_element(By.XPATH, "//a[contains(text(),'그룹 정보')]").click()
            time.sleep(2)  # 페이지 로딩 대기
            save_html_with_url(f"{menu_path}/{file_name}", driver.page_source, rel_path)
            print(f"[✅ 저장 완료] {menu_name} → {file_name}")

            try:
                n = open_each_kebab_and_save(
                    driver,
                    save_basepath=f"{menu_path}/{file_name}",
                    rel_path=rel_path,
                    max_buttons=6
                )
                if n:
                    print(f"[✅ 더보기(⋮) 열린 상태 스냅샷 {n}건 추가 저장] {menu_name}")
            except Exception as e:
                print(f"[⚠️ 더보기 스냅샷 실패] {menu_name}: {e}")

        except Exception as e:
            print(f"[⚠️ 함수 정보 저장 실패] {e}")

        continue

    # === 나머지 메뉴는 기존처럼 URL 직접 이동해서 저장 ===
    driver.get(url)
    time.sleep(2)
    save_html_with_url(f"{menu_path}/{file_name}", driver.page_source, rel_path)
    print(f"[✅ 저장 완료] {menu_name} → {file_name}")

    # ▼▼▼ 체크박스 필수 메뉴 (파일정보/함수정보 등) 처리 ▼▼▼
    if path in CHECKBOX_REQUIRED_MENUS:
        try:
            # 1) 전체선택 체크박스 클릭
            checkbox_ids = {
                "ProjectDetailFileManage": "fileInfoAllCheck",
                "ProjectDetailFunctionManage": "functionAllCheck",  # 실제 ID 확인 필요
            }
            cb_id = checkbox_ids.get(path)
            if cb_id:
                try:
                    cb = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, cb_id))
                    )
                    driver.execute_script("arguments[0].click();", cb)
                    time.sleep(0.3)
                    print(f"[✅ 체크박스 클릭 완료] {menu_name}")
                except TimeoutException:
                    print(f"[⚠️ 체크박스 못 찾음] {menu_name}")

            # 2) ⋮ 버튼 찾아 클릭
            more_btn = get_more_button(driver, timeout=8)
            if not more_btn or not wait_button_enabled(driver, more_btn, timeout=6):
                print(f"[⚠️ 경고] {menu_name} - 더보기(⋮) 버튼을 찾지 못했거나 비활성 상태")
            else:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", more_btn)
                time.sleep(0.1)
                driver.execute_script("arguments[0].click();", more_btn)
                wait_dropdown_appears_for_button(driver, more_btn, timeout=5)

                for item_text in ["사용자 파일 지정", "검증 대상 설정", "파일 유형 설정"]:
                    try:
                        # ⋮ 열기(매번 새로 찾기)
                        more_btn = get_more_button(driver, timeout=8)
                        if not more_btn or not wait_button_enabled(driver, more_btn, timeout=6):
                            print(f"[⚠️ 경고] {menu_name} - 더보기(⋮) 버튼을 찾지 못했거나 비활성 상태")
                            continue
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", more_btn)
                        time.sleep(0.1)
                        driver.execute_script("arguments[0].click();", more_btn)
                        wait_dropdown_appears_for_button(driver, more_btn, timeout=5)

                        # 항목 클릭 → 모달 대기/저장
                        click_dropdown_item_by_text(driver, item_text, timeout=6)
                        WebDriverWait(driver, 8).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "modal-content"))
                        )
                        time.sleep(0.5)

                        safe = item_text.replace(" ", "_")
                        out_path = f"{menu_path}/모달_{path}_{safe}.html"
                        save_current_modal(driver, out_path, f"{rel_path} (dropdown-modal: {item_text})")
                        print(f"[✅ 모달 저장] {menu_name} - {item_text} → {out_path}")

                        # 닫기
                        close_modal(driver, timeout=8)

                        # 다음 항목 준비
                        time.sleep(0.2)

                    except Exception as e:
                        print(f"[⚠️ 모달 처리 실패] {menu_name} - {item_text}: {e}")
        except Exception as e:
            print(f"[⚠️ {menu_name} 드롭다운-모달 처리 블록 실패] {e}")
    # ▲▲▲ 끝 ▲▲▲

    # 2) ⋮ 열린 상태 스냅샷 추가
    try:
        n = open_each_kebab_and_save(
            driver,
            save_basepath=f"{menu_path}/{file_name}",
            rel_path=rel_path,
            max_buttons=6
        )
        if n:
            print(f"[✅ 더보기(⋮) 열린 상태 스냅샷 {n}건 추가 저장] {menu_name}")
    except Exception as e:
        print(f"[⚠️ 더보기 스냅샷 실패] {menu_name}: {e}")

    # 모달 처리 (SCM/LLM)
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
