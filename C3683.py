# MenuTree : 기능 테스트 › 신뢰성 시험 › 정적 시험 › 취약점 점검 결과
# Summary : 신뢰성 시험 -> 정적 시험 취약점 검증 결과 파일 별 결함 상세 결과에서 함수 필드 내 위배 목록에 대한 함수 정보가 존재한다.
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

class C3683(unittest.TestCase):

    def setUp(self):
        # 0. 드라이버 설정 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3683(self):
        # 1. SCM이 GIT인 프로젝트 생성
        #default_setting.create_project(self.driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 정적 시험 결과(STATIC) xml 파일 업로드
        #default_setting.upload_project(self.driver, case_id, "STATIC", "VPES_MIRO2010_git")

        # 3. 프로젝트 > 신뢰성 시험 > 정적 시험 진입
        move_menu.move_static(self.driver, case_id)

        # 4. "취약점 검증 결과" 탭 클릭
        self.driver.find_element(By.ID, "tabSN").click()

        # 일정한 결과 확인을 위한 테이블 정렬
        default_setting.sort_table(self.driver, "rteViolationDetailByFileTable", 3, "descending")

        # 5. "파일 별 상세 결과" 테이블의 두번째 행 - 세 번째 컬럼 값 확인
        cell_xpath = "//*[@id='rteViolationDetailByFile']/tr[1]/td[3]"
        cell_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, cell_xpath))
        )
        sleep(2)
        self.assertEqual(
            cell_element.text.strip(),
            "Q_make_add(struct link *, signed int)"
        )

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)