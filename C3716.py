# MenuTree : 기능 테스트 › 프로젝트 사이드 바 › SCM 설정
# Summary : 프로젝트 사이드 바 -> SCM 설정을 할 수 있다.(GIT)
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

class C3716(unittest.TestCase):

    def setUp(self):
        # 0. 드라이버 세팅 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3716(self):
        # 1. SCM이 GIT인 프로젝트 생성
        default_setting.create_project(self.driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 정적 시험 결과(STATIC) xml 파일 업로드
        default_setting.upload_project(self.driver, case_id, "STATIC", "VPES_MIRO2010_git")

        # 3. 프로젝트 > 신뢰성 시험 > 정적 시험 진입
        move_menu.move_static(self.driver, case_id)

        # 4. 파일별 상세 결과 첫번째 행 - 두 번째 컬럼 값 확인
        wait = WebDriverWait(self.driver, 10)
        first_row_second_col = wait.until(EC.presence_of_element_located((
            By.XPATH, "//*[@id='codingViolationDetailByFile']/tr[1]/td[2]"
        )))
        sleep(2)
        self.assertEqual(first_row_second_col.text.strip(), "miro_2010/miro_fun.c")

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)