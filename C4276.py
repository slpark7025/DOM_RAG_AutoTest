# MenuTree : 기능 테스트 › 코드 관리 › 파일 정보 › 검색
# Summary : 코드 관리 -> 파일 정보 메뉴에서 파일 검색이 가능하다.
from time import sleep
import os
import unittest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import default_setting
import move_menu

case_id = os.path.basename(os.path.splitext(__file__)[0])

class C4276(unittest.TestCase):
    def setUp(self):
        # 1. WebDriver 초기화
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C4276(self):
        # 2. SCM이 GIT인 프로젝트 생성 및 검증 결과 업로드
        #default_setting.create_project(self.driver, case_id, "CSCI", "GIT", None, "test")
        #default_setting.upload_project(self.driver, case_id, "STATIC", "VPES_MIRO2010_git")

        # 3. 프로젝트 > 코드 관리 > 파일 정보 접속
        move_menu.move_fileinfo(self.driver, case_id)

        # 4. ".suo_2015" 검색 후 3번째 컬럼 확인
        search_input = self.driver.find_element(By.XPATH, "//*[@id='projectInfoTable_filter']/label[2]/input")
        search_input.clear()
        search_input.send_keys("manager.c")
        search_input.send_keys(Keys.ENTER)
        WebDriverWait(self.driver, 10).until(
            EC.text_to_be_present_in_element(
                (By.XPATH, "//*[@id='projectInfo']/tr[1]/td[3]"), "manager.c"
            )
        )
        cell_text = self.driver.find_element(By.XPATH, "//*[@id='projectInfo']/tr[1]/td[3]").text
        sleep(2)
        self.assertIn("manager.c", cell_text)

        # 5. "806" 검색 후 7번째 컬럼 확인
        search_input = self.driver.find_element(By.XPATH, "//*[@id='projectInfoTable_filter']/label[2]/input")
        search_input.clear()
        search_input.send_keys("806")
        search_input.send_keys(Keys.ENTER)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[@id='projectInfo']/tr[1]/td[7][contains(.,'806')]")
            )
        )
        cell_text = self.driver.find_element(By.XPATH, "//*[@id='projectInfo']/tr[1]/td[7]").text
        self.assertIn("806", cell_text)

        # 6. "42275317" 검색 후 8번째 컬럼 확인
        search_input = self.driver.find_element(By.XPATH, "//*[@id='projectInfoTable_filter']/label[2]/input")
        search_input.clear()
        search_input.send_keys("42275317")
        search_input.send_keys(Keys.ENTER)
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[@id='projectInfo']/tr[1]/td[8][contains(.,'42275317')]")
            )
        )
        cell_text = self.driver.find_element(By.XPATH, "//*[@id='projectInfo']/tr[1]/td[8]").text
        self.assertIn("42275317", cell_text)

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)