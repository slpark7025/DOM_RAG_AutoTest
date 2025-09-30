# MenuTree : 기능 테스트 › 프로젝트 사이드 바 › LLM 설정
# Summary : 프로젝트 사이드 바 -> LLM 설정에서 LLM 타입 선택 및 LLM 정보 입력이 가능하다. (GEMINI)
from selenium.webdriver.common.keys import Keys
import unittest
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import default_setting
import move_menu

case_id = os.path.basename(os.path.splitext(__file__)[0])

class C3626(unittest.TestCase):

    def setUp(self):
        # 0. 드라이버 초기화 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3626(self):
        driver = self.driver

        # 1. SCM이 GIT인 프로젝트 생성
        #default_setting.create_project(driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 프로젝트 진입
        move_menu.move_project(driver, case_id)

        # 3. Sidebar > "LLM 설정" 버튼 클릭
        llm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[span[text()='LLM 설정']]"))
        )
        llm_btn.click()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//span[text()='LLM 설정']"))
        )

        # 4. LLM 설정 - "사용" Radio 버튼 클릭
        radio_use = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//label[text()='사용']/../input"))
        )
        radio_use.click()

        # 5. LLM Type 하위 "GPT" 콤보박스 클릭 후 "GEMINI" 선택
        gpt_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='GPT']"))
        )
        gpt_option.click()
        gemini_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='TabAIRequest']/div[2]/div[2]/div/div[3]/ul/li[2]/span/span"))
        )
        gemini_option.click()

        # 6. LLM API 항목의 하위 Textarea에 "12345" 입력
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@placeholder='API KEY']"))
        )
        textarea.clear()
        textarea.send_keys("12345")

        # 7. [저장] 버튼 클릭
        save_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'저장')]"))
        )
        save_btn.click()

        # 8. "저장에 성공했습니다." 팝업창 출력 확인
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'저장에 성공했습니다.')]"))
        )

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()


if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)