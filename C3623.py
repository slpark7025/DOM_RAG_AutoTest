# MenuTree : 기능 테스트 › 프로젝트 사이드 바 › LLM 설정
# Summary : 프로젝트 사이드 바 -> LLM 설정에서 응답 유형 선택이 가능하다.
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

class C3623(unittest.TestCase):

    def setUp(self):
        # 0. WebDriver 초기화
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3623(self):
        driver = self.driver

        # 1. SCM이 GIT인 프로젝트 생성
        default_setting.create_project(driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 프로젝트 진입
        move_menu.move_project(driver, case_id)

        # 3. 프로젝트 Sidebar > "LLM 설정" 버튼 클릭 후 "LLM 설정 창 출력 확인
        llm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html[1]/body[1]/div[13]/div[1]/div[2]/div[1]/div[2]/button[2]"))
        )
        llm_btn.click()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "tabFunc"))
        )

        # 4. LLM 설정 - "사용" Radio 버튼 클릭
        driver.find_element(By.ID, "aiUse").click()

        # 5. LLM Type 콤보박스 - "GPT" 선택
        driver.find_element(By.XPATH, "//span[contains(text(), 'GPT')]").click()

        # 6. LLM API Placeholder에 "12345" 입력
        api_input = driver.find_element(By.XPATH, "//*[@id='TabAIRequest']/div[3]/div[2]/textarea")
        api_input.clear()
        api_input.send_keys("12345")

        # 7. "부가 정보" 탭 클릭 후 "응답유형", "세부설정", "응답 예상 샘플" 항목 존재 확인
        driver.find_element(By.ID, "tabValid").click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//label[text()='응답 유형1']"))
        )
        driver.find_element(By.XPATH, "//span[text()='세부 설정']")
        driver.find_element(By.XPATH, "//span[text()='응답 예상 샘플']")

        # 8. 응답 유형 - "응답 유형1" 선택 후 응답 예상 샘플 Placeholder에 내용 확인
        driver.find_element(By.XPATH, "//label[text()='응답 유형1']").click()
        placeholder1 = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//span[text()='응답 예상 샘플']/following::textarea[1]"))
        ).get_attribute("value")

        sleep(2)

        self.assertTrue(placeholder1 is not None and placeholder1.strip() != "")

        # 9. 응답 유형2 선택 후 Placeholder 내용이 달라짐을 확인
        driver.find_element(By.ID, "aiwritingType2").click()
        placeholder2 = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//span[text()='응답 예상 샘플']/following::textarea[1]"))
        ).get_attribute("value")

        self.assertNotEqual(placeholder1, placeholder2)

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)