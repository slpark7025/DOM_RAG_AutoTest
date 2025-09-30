# MenuTree : 기능 테스트 › 프로젝트 사이드 바 › LLM 설정
# Summary : 프로젝트 사이드 바 -> LLM 설정에서 LLM 타입 선택 및 LLM 정보 입력이 가능하다. (GPT)
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

class C3624(unittest.TestCase):

    def setUp(self):
        # 1. 드라이버 설정 및 로그인
        self.driver = default_setting.setup()
        default_setting.login(self.driver)

    def test_C3624(self):
        driver = self.driver

        # 2. SCM이 GIT인 프로젝트 생성
        #default_setting.create_project(driver, case_id, "CSCI", "GIT", None, "test")

        # 3. 프로젝트 진입
        move_menu.move_project(driver, case_id)

        # 4. Sidebar > LLM 설정 버튼 클릭
        llm_setting_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[span[text()='LLM 설정']]"))
        )
        llm_setting_btn.click()

        # 5. LLM 설정 창에서 "사용" Radio 버튼 클릭
        radio_use = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "aiUse"))
        )
        radio_use.click()

        # 6. LLM Type이 "GPT"로 선택되어 있는지 확인
        llm_type_selected = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[text()='GPT']"))
        )
        sleep(2)
        self.assertEqual(llm_type_selected.text, "GPT")

        # 7. LLM API 항목의 Textarea에 "12345" 입력
        textarea = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='LLM API']/parent::div/following-sibling::div//textarea"))
        )
        textarea.clear()
        textarea.send_keys("12345")

        # 8. 저장 버튼 클릭
        save_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'저장')]"))
        )
        save_btn.click()

        # 9. "저장에 성공했습니다." 팝업창 출력 확인
        popup = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "toastBottomCenterVue"))
        )
        sleep(1)
        self.assertIn("저장에 성공했습니다.", popup.text)

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)