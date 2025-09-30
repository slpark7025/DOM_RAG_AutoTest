# MenuTree : 기능 테스트 › 기술 문서 › 기술 문서 검증 결과(2024-6) › 일반 검증
# Summary : 기술 문서 -> 기술 문서의 일반 검증을 할 수 있다.(개정안 2024-6호)
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

class C3701(unittest.TestCase):

    def setUp(self):
        # 0. 드라이버 세팅 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3701(self):
        # 1. SCM이 GIT인 프로젝트 생성
        default_setting.create_project(self.driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 프로젝트 > 기술 문서 > 기술 문서 검증 진입
        move_menu.move_inputDocument(self.driver, case_id)

        # 3. "SRS" 업로드 후 검증
        default_setting.upload_document(self.driver, "word", "SRS.docx", "srs")
        default_setting.click_inspectionBtn_wait(self.driver, "SRS")

        # 4. "SDD" 업로드 후 검증
        default_setting.upload_document(self.driver, "word", "SDD.docx", "sdd")
        default_setting.click_inspectionBtn_wait(self.driver, "SDD")

        # 5. "STP" 업로드 후 검증
        default_setting.upload_document(self.driver, "word", "STP.docx", "stp")
        default_setting.click_inspectionBtn_wait(self.driver, "STP")

        # 6. "STD" 업로드 후 검증
        default_setting.upload_document(self.driver, "word", "STD.docx", "std")
        default_setting.click_inspectionBtn_wait(self.driver, "STD")

        # 7. "STR" 업로드 후 검증
        default_setting.upload_document(self.driver, "word", "STR.docx", "str")
        default_setting.click_inspectionBtn_wait(self.driver, "STR")

        # 8. 기술 문서 검증 결과 진입 후 항목 존재 확인
        move_menu.move_inspectionDocument(self.driver, case_id)
        normal_section = self.driver.find_element(By.ID, "DocResultNormal")
        matching_section = self.driver.find_element(By.ID, "DocResultMatching")
        sleep(2)
        self.assertTrue(normal_section.is_displayed())
        self.assertTrue(matching_section.is_displayed())

        # 9. 두 번째 행의 컬럼 값 검증
        cols = self.driver.find_elements(By.XPATH, "//*[@id='generalAndConsistencyTable']/tbody/tr[1]/*")
        expected = ["일반", "0건", "0건", "0건", "0건", "0건", "-", "-"]
        actual = [col.text.strip() for col in cols]
        self.assertEqual(actual, expected)

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)