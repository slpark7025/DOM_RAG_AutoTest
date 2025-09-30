# MenuTree : 기능 테스트 › 프로젝트 사이드 바 › SCM 설정
# Summary : 프로젝트 사이드 바 -> SCM 설정을 할 수 있다.(SVN)
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep
import os
import unittest
from selenium.webdriver.common.by import By
import default_setting
import move_menu

case_id = os.path.basename(os.path.splitext(__file__)[0])

class C3719(unittest.TestCase):

    def setUp(self):
        # 0. 드라이버 세팅 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3719(self):
        # 1. SCM이 SVN인 프로젝트 생성
        default_setting.create_project(self.driver, case_id, "CSCI", "SVN")

        # 2. 동적 시험 결과(CT) xml 파일 업로드
        default_setting.upload_project(self.driver, case_id, "CT", "CT_study_sample_SVN")

        # 3. 프로젝트 > 신뢰성 시험 > 동적 시험 진입
        move_menu.move_dynamic(self.driver, case_id)

        # 4. "파일별 코드 실행률" 항목 하위 테이블 첫번째 행 - 두 번째 컬럼 값 확인
        first_row_second_col = self.driver.find_element(By.XPATH, "//*[@id='coverageByFile']/tr/td[2]").text
        sleep(2)
        self.assertEqual(first_row_second_col.strip(), "study_sample/study_sample.c")

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)