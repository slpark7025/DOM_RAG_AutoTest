"""모든 페이지 이동 내용 포함"""
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

# 홈으로 이동
def move_home(driver):
    time.sleep(4)
    driver.find_element(By.ID, "TopNavBarLogoVue").click()
    time.sleep(1)

# 프로젝트 등록
def move_project_registration(driver):
    move_home(driver)
    driver.find_element(By.XPATH,'//span[contains(text(), "프로젝트 관리")]').click()
    driver.find_element(By.XPATH,'//span[contains(text(), "프로젝트 등록")]').click()
    time.sleep(1)

# 파일 검색
def search_project(driver, case_id):
    move_home(driver)
    driver.find_element(By.ID, "mainDashBoard-ProjectList_filter").click()
    driver.find_element(By.XPATH, "//div/div[2]/label/input").clear()
    driver.find_element(By.XPATH, "//div/div[2]/label/input").send_keys(case_id)
    driver.find_element(By.XPATH, "//div/div[2]/label/input").send_keys(Keys.ENTER)
    time.sleep(1)

# 프로젝트 이동
def move_project(driver, case_id):
    search_project(driver, case_id)
    time.sleep(1)
    driver.find_element(By.XPATH, "//font[contains(text(), '" + case_id + "')]").click()
    time.sleep(1)

def is_current_project_page(driver, case_id):
    current_url = driver.current_url
    return current_url.rstrip("/").split("/")[-1] == case_id

def safe_click(driver, by, value):
    try:
        driver.find_element(by, value).click()
    except:
        pass

# 개요 탭 클릭
def move_overview(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    driver.find_element(By.ID, "overView-tab").click()
    time.sleep(1)

# 기술 문서 탭 > 기술 문서 검증 클릭
def move_inputDocument(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "technicalDocument-tab")
    driver.find_element(By.ID, "inputDocument").click()
    time.sleep(1)

# 기술 문서 탭 > 기술 문서 검증 결과 클릭
def move_inspectionDocument(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "technicalDocument-tab")
    driver.find_element(By.ID, "inspectionDocument").click()
    time.sleep(1)

# 신뢰성 시험 탭 > 결과 요약 클릭
def move_progress(driver, case_id):
    move_project(driver, case_id)
    safe_click(driver, By.ID, "projectDetail-tab")
    driver.find_element(By.ID, "progress").click()
    time.sleep(1)

# 신뢰성 시험 탭 > 정적 시험 클릭
def move_static(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectDetail-tab")
    driver.find_element(By.ID, "static").click()
    time.sleep(3)

# 신뢰성 시험 탭 > 정적 시험 클릭 - 취약점 검증 결과 TAB 클릭
def move_vulnerability(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectDetail-tab")
    driver.find_element(By.ID, "static").click()
    time.sleep(1)
    driver.find_element(By.ID, "tabSN").click()
    time.sleep(1)

# 신뢰성 시험 탭 > 정적 시험 클릭 - 보안성 시험 결과 TAB 클릭
def move_Security(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectDetail-tab")
    driver.find_element(By.ID, "static").click()
    time.sleep(1)
    driver.find_element(By.ID, "tabSC").click()
    time.sleep(1)

# 신뢰성 시험 탭 > 동적 시험 클릭
def move_dynamic(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectDetail-tab")
    driver.find_element(By.ID, "dynamic").click()
    time.sleep(1)

# 신뢰성 시험 탭 > 소스 코드 메트릭 클릭
def move_metric(driver, case_id):
    move_project(driver, case_id)
    safe_click(driver, By.ID, "projectDetail-tab")
    driver.find_element(By.ID, "metric").click()
    time.sleep(1)

# 신뢰성 시험 탭 > 예외 처리 결과 클릭
def move_suppression(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectDetail-tab")
    driver.find_element(By.ID, "suppression").click()
    time.sleep(1)

# 코드 관리 탭 > 파일 정보 클릭
def move_fileinfo(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectSourceCode-tab")
    driver.find_element(By.ID, "fileinfo").click()
    time.sleep(1)

# # 신뢰성 시험 탭 > 통합 모의시험 클릭
def move_integraion_trial_exam(driver, case_id):
    move_project(driver, case_id)
    driver.find_element(By.ID,"projectDetail-tab").click()
    driver.find_element(By.XPATH, "//a[contains(text(),'통합 모의시험')]").click()
    time.sleep(1)

# 코드 관리 탭 > 그룹 정보 클릭
def move_groupinfo(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectSourceCode-tab")
    driver.find_element(By.XPATH, "//a[contains(text(),'그룹 정보')]").click()
    time.sleep(1)

# 시험 수행 관리 탭 > 빌드 수행 클릭
def move_buildExecution(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "testExecution-tab")
    driver.find_element(By.ID, "buildExecution").click()
    time.sleep(1)

# 시험 수행 관리 탭 > 콘솔 출력 클릭
def move_detailConsole(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "testExecution-tab")
    driver.find_element(By.ID, "detailConsole").click()
    time.sleep(1)

# 산출물 탭  > 신뢰성 문서 클릭
def move_reliabilityReport(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    driver.find_element(By.ID, "report-tab").click()
    driver.find_element(By.XPATH, '//*[@id="reportGenerateVue"]/div[2]/div[2]/div[1]/div/div[2]').click()
    driver.find_element(By.XPATH, '//*[@id="reportGenerateVue"]/div[2]/div[2]/div[1]/div/div[3]/ul/li[1]').click()
    time.sleep(1)

# 산출물 탭  > KOLAS 문서 클릭
def move_kolasReport(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    driver.find_element(By.ID, "report-tab").click()
    driver.find_element(By.XPATH, '//*[@id="reportGenerateVue"]/div[2]/div[2]/div[1]/div/div[2]').click()
    driver.find_element(By.XPATH, '//*[@id="reportGenerateVue"]/div[2]/div[2]/div[1]/div/div[3]/ul/li[3]').click()
    time.sleep(1)

# 산출물 탭  > SW 문서 클릭
def move_additionalReport(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    driver.find_element(By.ID, "report-tab").click()
    driver.find_element(By.XPATH, '//*[@id="reportGenerateVue"]/div[2]/div[2]/div[1]/div/div[2]').click()
    driver.find_element(By.XPATH, '//*[@id="reportGenerateVue"]/div[2]/div[2]/div[1]/div/div[3]/ul/li[2]').click()
    time.sleep(1)

# 설정 탭 > 빌드 설정 클릭
def move_buildSetting(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "setting-tab")
    driver.find_element(By.ID, "buildSetting").click()
    time.sleep(1)

# 설정 탭 > 프로젝트 설정 클릭
def move_projectSetting(driver, case_id):
    move_project(driver, case_id)
    safe_click(driver, By.ID, "setting-tab")
    driver.find_element(By.ID, "projectSetting").click()
    time.sleep(1)

# 설정 탭 > 진행률 설정 클릭
def move_projectPorgressHistoryInfo(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "setting-tab")
    driver.find_element(By.ID, "projectPorgressHistoryInfo").click()
    time.sleep(1)

# 홈 > 설정 클릭
def move_globalSetting(driver):
    move_home(driver)
    globalSetting_icon = driver.find_element(By.ID,"TopNavBarGlobalSetting")
    driver.execute_script("arguments[0].click();", globalSetting_icon)
    time.sleep(1)

# 프로젝트 현황 > 과제 정보 조회 클릭
def move_CheckAssignmentInformation(driver):
    move_home(driver)
    driver.find_element(By.ID,'TopNavBarProjectHistory').click()
    time.sleep(1)

# 프로젝트 설정 -> 필수 정보 탭 클릭
def move_projectRequiredInfo(driver, case_id):
    move_projectSetting(driver, case_id)
    driver.find_element(By.ID,"projectRegister-requiredOpt-tab").click()

# 프로젝트 설정 -> 추가 정보 탭 클릭
def move_projectAdditionalInfo(driver, case_id):
    move_projectSetting(driver, case_id)
    driver.find_element(By.ID,"projectRegister-additionalOpt-tab").click()

# 프로젝트 그룹
def move_project_group(driver):
    move_home(driver)
    group_icon = driver.find_element(By.ID,"TopNavBarGroupDashboard")
    driver.execute_script("arguments[0].click();", group_icon)
    time.sleep(0.5)
    driver.find_element(By.ID,"TopNavBarGroupDashboardGoToGroupBtn").click()
    time.sleep(2)

# 코드 관리 탭-> 함수 정보 클릭
def move_functioninfo(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectSourceCode-tab")
    driver.find_element(By.XPATH, "//a[contains(text(),'함수  정보')]").click()
    time.sleep(1)

# 프로젝트 -> 규칙 설정 탭 클릭
def move_ruleset(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "setting-tab")
    driver.find_element(By.ID, 'projectRuleSetting').click()
    time.sleep(1)

# 홈 > 설정 > SCM 설정 클릭
def move_globalSetting_scm(driver):
    move_globalSetting(driver)
    driver.find_element(By.ID, "scmSetting-tab").click()
    time.sleep(1)

# KnowledgeHub 이동
def move_KnowledgeHub(driver):
    move_home(driver)
    driver.find_element(By.ID,'TopNavBarKnowledgeHub').click()
    time.sleep(1)

# KnowledgeHub에서 검색
def search_KnowledgeHub(driver, case_id, type):
    if type == "static":
        move_knowledgehub_static_rule(driver)
    elif type == "metric":
        move_knowledgehub_metric_rule(driver)
    elif type == "static_exercise":
        move_knowledgehub_static_exercise(driver)
    elif type == "metric_exercise":
        move_knowledgehub_metric_exercise(driver)
    elif type == "setting":
        move_knowledgehub_tool_setting(driver)
    elif type == 'trouble':
        move_knowledgehub_tool_trouble(driver)
    elif type == 'qna':
        move_knowledgehub_qna(driver)

    driver.find_element(By.XPATH,'//*[@id="knowledgeTable_filter"]/label/input').send_keys(case_id)
    driver.find_element(By.XPATH,'//*[@id="knowledgeTable_filter"]/label/input').send_keys(Keys.ENTER)
    driver.find_element(By.XPATH,'//*[@id="knowledgeTable"]/tbody/tr').click()
    time.sleep(3)

# KnowledgeHub 정적검증 규칙
def move_knowledgehub_static_rule(driver):
    move_KnowledgeHub(driver)
    driver.find_element(By.ID,'staticknowledge-tab').click()
    driver.find_element(By.XPATH,'//*[@id="submenu_rulesetlist"]/ul/li[1]').click()
    time.sleep(1)

# KnowledgeHub 메트릭 검증 규칙
def move_knowledgehub_metric_rule(driver):
    move_KnowledgeHub(driver)
    driver.find_element(By.ID,'metricknowledge-tab').click()
    driver.find_element(By.XPATH,'//li[2]/div/ul/li[1]/a').click()
    time.sleep(1)

# KnowledgeHub 정적 검증 예제
def move_knowledgehub_static_exercise(driver):
    move_KnowledgeHub(driver)
    driver.find_element(By.ID,'staticknowledge-tab').click()
    driver.find_element(By.XPATH,'//li[1]/div/ul/li[2]').click()
    time.sleep(1)

# KnowledgeHub 메트릭 검증 예제
def move_knowledgehub_metric_exercise(driver):
    move_KnowledgeHub(driver)
    driver.find_element(By.ID,'metricknowledge-tab').click()
    driver.find_element(By.XPATH,'//li[2]/div/ul/li[2]/a').click()
    time.sleep(1)

# KnowledgeHub 도구 -> 환경 설정
def move_knowledgehub_tool_setting(driver):
    move_KnowledgeHub(driver)
    driver.find_element(By.XPATH,'//div[1]/div/ul/li[3]/a').click()
    driver.find_element(By.XPATH,'//li[3]/div/ul/li[1]/a').click()
    time.sleep(1)

# KnowledgeHub 도구 -> 트러블 슈팅
def move_knowledgehub_tool_trouble(driver):
    move_KnowledgeHub(driver)
    driver.find_element(By.XPATH,'//div[1]/div/ul/li[3]/a').click()
    driver.find_element(By.XPATH,'//li[3]/div/ul/li[2]/a').click()
    time.sleep(1)

# KnowledgeHub qna
def move_knowledgehub_qna(driver):
    move_KnowledgeHub(driver)
    driver.find_element(By.XPATH,'//div[1]/div/ul/li[4]/a').click()
    driver.find_element(By.XPATH,'//li[4]/div/ul/li/a').click()
    time.sleep(1)

# 사용자 -> 사용자 정보
def move_user_info(driver):
    move_home(driver)
    driver.find_element(By.ID, 'TopNavBarUserInfoDropDownBtn').click()
    driver.find_element(By.XPATH, '//*[@id="TopNavBarUserInfoVue"]/div/a[1]').click()
    driver.find_element(By.ID, 'privacy-tab').click()

# 사용자 -> 프로젝트 목록
def move_project_list(driver):
    move_home(driver)
    driver.find_element(By.ID, 'TopNavBarUserInfoDropDownBtn').click()
    driver.find_element(By.XPATH, '//*[@id="TopNavBarUserInfoVue"]/div/a[1]').click()
    driver.find_element(By.ID, 'projectList-tab').click()

# 홈 -> 설정 -> 시험 도구 설정
def move_globalSetting_cscSetting(driver):
    move_globalSetting(driver)
    driver.find_element(By.ID, "cscSetting-tab").click()
    time.sleep(1)

def move_globalSetting_sessionSetting(driver):
    move_globalSetting(driver)
    driver.find_element(By.ID,'sessionSetting-tab').click()
    time.sleep(1)

# 홈 > 프로젝트 복제
def move_copy_project(driver):
    move_home(driver)
    driver.find_element(By.XPATH,'//span[contains(text(), "프로젝트 관리")]').click()
    driver.find_element(By.XPATH,'//span[contains(text(), "프로젝트 복제")]').click()

# 홈 > 설정 > 라이센스 설정
def move_license_setting(driver):
    move_globalSetting(driver)
    driver.find_element(By.ID, 'licenseSetting-tab').click()
    time.sleep(1)

# 홈 > 설정 > 사용자 설정
def move_user_setting(driver):
    move_globalSetting(driver)
    driver.find_element(By.ID, 'userSetting-tab').click()
    time.sleep(1)

# 홈 > 실험실beta
def move_lab_beta(driver):
    move_home(driver)
    element = driver.find_element(By.ID, 'TopNavBarAboutRtms')
    driver.execute_script("arguments[0].click();", element)
    driver.find_element(By.ID, 'TopNavBarAboutRtmsLabBtn').click()
    time.sleep(1)

def move_project_scm_setting(driver, case_id):
    move_home(driver)
    move_project(driver, case_id)
    driver.find_element(By.XPATH, '//*[@id="projectSideBar"]/div[2]/button[1]').click()

# 코드 관리 탭-> 함수 정보 -> 변수 정보 클릭
def move_variableinfo(driver, case_id):
    if not is_current_project_page(driver, case_id):
        move_project(driver, case_id)
    safe_click(driver, By.ID, "projectSourceCode-tab")
    driver.find_element(By.XPATH, "//a[contains(text(),'함수  정보')]").click()
    driver.find_element(By.XPATH, "//div[6]/div[1]/div[2]/div/ul/li[2]/a").click()
    time.sleep(1)