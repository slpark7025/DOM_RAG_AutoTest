# MenuTree : 기능 테스트 › 프로젝트 사이드 바 › LLM 설정
# Summary : 프로젝트 사이드 바 -> LLM 설정에서 LLM 타입 선택 및 LLM 정보 입력이 가능하다. (SURESOFT)
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

class C3627(unittest.TestCase):
    def setUp(self):
        # 0. 드라이버 셋업 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3627(self):
        driver = self.driver

        # 1. SCM이 GIT인 프로젝트 생성
        #default_setting.create_project(driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 프로젝트 진입
        move_menu.move_project(driver, case_id)

        # 3. LLM 설정 버튼 클릭 후 LLM 설정 창 확인
        llm_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[span[text()='LLM 설정']]"))
        )
        llm_button.click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "tabFunc"))
        )

        # 4. LLM 설정 - "사용" Radio 버튼 클릭
        driver.find_element(By.ID, "aiUse").click()

        # 5. LLM Type 하위 MultiSelect - "SURESOFT" 선택
        llm_type = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='GPT']"))
        )
        llm_type.click()
        suresoft_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='TabAIRequest']/div[2]/div[2]/div/div[3]/ul/li[3]/span/span"))
        )
        suresoft_option.click()

        # 6. LLM IP Placeholder 입력
        llm_ip = driver.find_element(By.XPATH, "//textarea[@placeholder='http://127.0.0.1']")
        llm_ip.clear()
        llm_ip.send_keys("http://10.10.111.16")

        # 7. SureChat(Agent) IP Placeholder 입력
        surechat_ip = driver.find_element(By.XPATH, "//*[@id='TabAIRequest']/div[4]/div[2]/textarea")
        surechat_ip.clear()
        surechat_ip.send_keys("http://10.10.111.16")

        # 8. VPES IP Placeholder 입력
        vpes_ip = driver.find_element(By.XPATH, "//*[@id='TabAIRequest']/div[5]/div[2]/textarea")
        vpes_ip.clear()
        vpes_ip.send_keys("http://10.10.111.16")

        # 9. 저장 버튼 클릭
        save_btn = driver.find_element(By.XPATH, "//*[@id='aiSettingModal']/div/div/div[4]/button[2]")
        save_btn.click()

        # 10. "저장에 성공했습니다." 토스트 확인
        toast = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "toastBottomCenterVue"))
        )
        sleep(1)
        self.assertIn("저장에 성공했습니다.", toast.text)

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)