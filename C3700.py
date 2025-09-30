# MenuTree : 기능 테스트 › 코드 관리 › 파일 정보
# Summary : 코드 관리 -> 파일 관리에서 파일별 담당자를 지정할 수 있다.
from selenium.webdriver.common.keys import Keys
from time import sleep
import os
import unittest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import default_setting
import move_menu

case_id = os.path.basename(os.path.splitext(__file__)[0])

class C3700(unittest.TestCase):

    def setUp(self):
        # 0. 드라이버 초기화 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3700(self):
        driver = self.driver

        # 1. SCM이 GIT인 프로젝트 생성
        default_setting.create_project(driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 정적 시험 결과(STATIC) xml 파일 업로드
        default_setting.upload_project(driver, case_id, "STATIC", "VPES_MIRO2010_git")

        # 3. 프로젝트 > 설정 > 프로젝트 설정 진입
        move_menu.move_projectSetting(driver, case_id)

        # 4. "사용자 등록" 탭 클릭
        driver.find_element(By.ID, "projectRegister-memberRegistration-tab").click()

        # 5. "사용자 추가" 콤보박스 클릭 후 "slpark (slpark)" 클릭
        user_box = driver.find_element(By.ID, "projectRegister-memberBox")
        driver.find_element(By.XPATH, "//*[@id='projectRegister-memberRegistration']/div[1]/div/div[1]/div/div[2]").click()
        user_box.send_keys("slpark")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'slpark')]"))
        ).click()

        # 6. [저장] 버튼 클릭
        driver.find_element(By.XPATH, "//*[@id='projectBtn']").click()

        # 7. 프로젝트 > 코드 관리 > 파일 정보 진입
        move_menu.move_fileinfo(driver, case_id)

        # 8. kebab 버튼 클릭 > "소스코드 가져오기" 클릭
        driver.find_element(
            By.XPATH, "//*[@id='projectInfoTable_wrapper']/div[1]/button[2]"
        ).click()
        sleep(1)
        driver.find_element(
            By.XPATH, "/html[1]/body[1]/div[13]/div[1]/div[6]/div[2]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[2]/div[1]/button[1]"
        ).click()

        # 9. "경고!" 팝업 창에서 [확인] 버튼 클릭
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[@id='deleteY']")
            )
        ).click()
        sleep(15)
        # 10. 테이블의 두 번째 행 - 첫 번째 컬럼의 체크박스 클릭
        second_row_checkbox = driver.find_element(
            By.XPATH, "//table/tbody/tr[2]/td[1]/input[@type='checkbox']"
        )
        second_row_checkbox.click()

        # 11. kebab 버튼 클릭 > "사용자 파일 지정" 클릭 후 "파일 사용자 설정" 모달이 출력됨을 확인
        driver.find_element(
            By.XPATH, "//*[@id='projectInfoTable_wrapper']/div[1]/button[2]"
        ).click()
        sleep(1)
        driver.find_element(
            By.XPATH,
            "//span[contains(text(),'사용자 파일 지정')]"
        ).click()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'파일 사용자 설정')]"))
        )

        # 12. 파일 사용자 설정 모달에서 콤보박스 클릭 후 항목 확인
        combo = driver.find_element(By.XPATH, "//*[@id='fileManageEditModal']/div/div/div[2]/form[2]/div[2]/div/div[2]")
        combo.click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'admin')]"))
        )
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'slpark')]"))
        )

        # 13. 콤보박스에서 "admin" 선택 후 [저장] 버튼 클릭
        driver.find_element(By.XPATH, "//span[contains(text(),'admin')]").click()
        driver.find_element(By.XPATH, "//*[@id='fileManageEditModal']/div/div/div[3]/button[2]").click()
        sleep(3)

        # 14. 테이블의 두 번째 행 - 네 번째 컬럼의 값이 "admin"임을 확인
        cell_value = driver.find_element(
            By.XPATH, "//*[@id='projectInfo']/tr[2]/td[4]"
        ).text
        sleep(2)
        self.assertEqual(cell_value.strip(), "admin")

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)