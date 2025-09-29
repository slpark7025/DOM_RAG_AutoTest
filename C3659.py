# MenuTree : 기능 테스트 › 신뢰성 시험 › 정적 시험 › 코딩 규칙 결과
# Summary : 신뢰성 시험 -> 정적 시험 코딩 규칙 결과 파일 별 결함 상세 결과에서 함수 필드 내 위배 목록에 대한 함수 정보가 존재한다.
from selenium.webdriver.common.keys import Keys
from time import sleep
import os
import unittest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import default_setting
import move_menu

case_id = os.path.basename(os.path.splitext(__file__)[0])

class C3659(unittest.TestCase):

    def setUp(self):
        # 0. 드라이버 설정 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3659(self):
        driver = self.driver

        # 1. SCM이 GIT인 프로젝트 생성
        #default_setting.create_project(driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 정적 시험 결과(STATIC) xml 파일 업로드
        #default_setting.upload_project(driver, case_id, "STATIC", "VPES_MIRO2010_git")

        # 3. 프로젝트 > 신뢰성 시험 > 정적 시험 진입
        move_menu.move_static(driver, case_id)

        wait = WebDriverWait(driver, 10)

        # 4. "파일 별 상세 결과" 항목 테이블의 "함수" 컬럼의 각 행이 공란이 아님을 확인
        function_header = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='codingViolationDetailByFileTable']/thead/tr/th")))
        func_col_index = 3
        rows = driver.find_elements(By.XPATH, f"//table[contains(@id,'codingViolationDetailByFileTable')]/tbody/tr/td[{func_col_index}]")
        for row in rows:
            sleep(2)
            self.assertNotEqual(row.text.strip(), "")

        # 5. 콤보박스 "5" -> "10" 선택, 행 10개 확인 및 공란 아님 확인
        select_box = Select(wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='codingViolationDetailByFileTable_length']/label/select"))))
        select_box.select_by_visible_text("10")
        wait.until(lambda d: len(d.find_elements(By.XPATH, f"//table[contains(@id,'codingViolationDetailByFileTable')]/tbody/tr")) == 10)
        rows = driver.find_elements(By.XPATH, f"//table[contains(@id,'codingViolationDetailByFileTable')]/tbody/tr/td[{func_col_index}]")
        for row in rows:
            self.assertNotEqual(row.text.strip(), "")

        # 6. 콤보박스 "10" -> "30" 선택, 행 30개 확인 및 공란 아님 확인
        select_box.select_by_visible_text("30")
        wait.until(lambda d: len(d.find_elements(By.XPATH, f"//table[contains(@id,'codingViolationDetailByFileTable')]/tbody/tr")) == 30)
        rows = driver.find_elements(By.XPATH, f"//table[contains(@id,'codingViolationDetailByFileTable')]/tbody/tr/td[{func_col_index}]")
        for row in rows:
            self.assertNotEqual(row.text.strip(), "")

        # 7. 콤보박스 "30" -> "50" 선택, 행 50개 확인 및 공란 아님 확인
        select_box.select_by_visible_text("50")
        wait.until(lambda d: len(d.find_elements(By.XPATH, f"//table[contains(@id,'codingViolationDetailByFileTable')]/tbody/tr")) == 50)
        rows = driver.find_elements(By.XPATH, f"//table[contains(@id,'codingViolationDetailByFileTable')]/tbody/tr/td[{func_col_index}]")
        for row in rows:
            self.assertNotEqual(row.text.strip(), "")

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)