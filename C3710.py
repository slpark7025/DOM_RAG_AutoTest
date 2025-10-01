# MenuTree : 기능 테스트 › 신뢰성 시험 › 동적 시험 › 파일 별 코드 실행률
# Summary : 신뢰성 시험 -> 동적 검증에 파일 관리에서 지정한 담당자가 표시된다. (파일별 코드 실행률)
from selenium.webdriver.common.keys import Keys
from time import sleep
import unittest
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import default_setting
import move_menu

case_id = os.path.basename(os.path.splitext(__file__)[0])

class C3710(unittest.TestCase):
    def setUp(self):
        # 0. 드라이버 셋업 및 로그인
        self.driver = default_setting.setup()
        default_setting.login(self.driver)

    def test_C3710(self):
        driver = self.driver

        # 1. SCM이 GIT인 프로젝트 생성
        default_setting.create_project(driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 동적 시험 결과(CT) xml 파일 업로드
        default_setting.upload_project(driver, case_id, "CT", "CT_miro2010_git")

        # 3. 프로젝트 > 설정 > 프로젝트 설정 진입
        move_menu.move_projectSetting(driver, case_id)

        # 4. "사용자 등록" 탭 클릭
        driver.find_element(By.ID, "projectRegister-memberRegistration-tab").click()

        # 5. "사용자 추가" 콤보박스 클릭 후 "slpark (slpark)" 클릭
        user_box = driver.find_element(By.ID, "projectRegister-memberBox")
        driver.find_element(By.XPATH,
                            "//*[@id='projectRegister-memberRegistration']/div[1]/div/div[1]/div/div[2]").click()
        user_box.send_keys("slpark")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'slpark')]"))
        ).click()

        # 6. [저장] 버튼 클릭
        driver.find_element(By.XPATH, "//*[@id='projectBtn']").click()

        # 7. 프로젝트 > 코드 관리 > 파일 정보 진입
        move_menu.move_fileinfo(driver, case_id)

        # 8. 테이블의 헤더 - 첫 번째 컬럼의 체크박스 클릭
        driver.find_element(By.ID, "fileInfoAllCheck").click()

        # 9. kebab 버튼 클릭 > "사용자 파일 지정" 클릭 후 모달 출력 확인
        kebab_btn = driver.find_element(By.XPATH, "//button[contains(@class,'dropdown-more-btn')]")
        kebab_btn.click()
        driver.find_element(By.XPATH, "//span[text()='사용자 파일 지정']").click()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'파일 사용자 설정')]"))
        )

        # 10. 파일 사용자 설정 모달에서 콤보박스 클릭 후 항목 확인
        combo = driver.find_element(By.XPATH, "//*[@id='fileManageEditModal']/div/div/div[2]/form[2]/div[2]/div/div[2]")
        combo.click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'admin')]"))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'slpark')]"))
        )

        # 11. 콤보박스에서 "slpark" 선택 후 [저장] 버튼 클릭
        driver.find_element(By.XPATH, "//span[contains(text(),'slpark')]").click()
        driver.find_element(By.XPATH, "//*[@id='fileManageEditModal']/div/div/div[3]/button[2]").click()
        sleep(3)

        # 12. 테이블의 첫 번째 행 - 네 번째 컬럼의 값 확인
        table_cell = driver.find_element(By.XPATH, "//table/tbody/tr[1]/td[4]")
        self.assertEqual(table_cell.text.strip(), "slpark")

        # 13. 프로젝트 > 신뢰성 시험 > 동적 시험 진입
        move_menu.move_dynamic(driver, case_id)

        # 14. 파일별 코드 실행률 테이블 확인
        target_cell = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, "//table/tbody/tr[td[2]='miro_2010/miro_fun.c']/td[3]")))
        self.assertEqual(target_cell.text.strip(), "slpark")

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)