# MenuTree : 기능 테스트 › 프로젝트 사이드 바 › LLM 설정
# Summary : 프로젝트 사이드 바 -> LLM 설정에서 LLM 타입 미사용 설정을 할 수 있다.
from selenium.webdriver.common.keys import Keys
from time import sleep
import unittest
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import default_setting
import move_menu

case_id = os.path.basename(os.path.splitext(__file__)[0])

class C3629(unittest.TestCase):

    def setUp(self):
        # 1. WebDriver 초기화 및 로그인
        self.driver = default_setting.setup(case_id)
        default_setting.login(self.driver)

    def test_C3629(self):
        driver = self.driver

        # 2. SCM이 GIT인 프로젝트 생성
        #default_setting.create_project(driver, case_id, range="CSCI", scm_type="GIT", file_name=None, input_text="test")

        # 3. 프로젝트 진입
        move_menu.move_project(driver, case_id)

        # 4. LLM 설정 버튼 클릭
        llm_setting_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html[1]/body[1]/div[13]/div[1]/div[2]/div[1]/div[2]/button[2]"))
        )
        llm_setting_btn.click()
        sleep(5)

        # 5. LLM 설정 창에서 '미사용' Radio 버튼 클릭
        radio_unuse = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html[1]/body[1]/div[13]/div[1]/div[4]/div[1]/div[1]/div[3]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/label[1]"))
        )
        radio_unuse.click()
        sleep(5)

        # 6. LLM Type 콤보박스 비활성화 확인
        root = driver.find_element(By.XPATH,
                                   "//span[contains(@class,'multiselect__single') and normalize-space()='GPT']/ancestor::div[contains(@class,'multiselect')]")
        self.assertTrue('multiselect--disabled' in (root.get_attribute('class') or '') or (
                    (root.get_attribute('aria-disabled') or '').lower() == 'true'))

        # 7. LLM API Textarea 비활성화 확인
        el = driver.find_element(By.XPATH, "//textarea[@class='form-control' and @placeholder='API KEY']")
        self.assertTrue((not el.is_enabled()) or (el.get_attribute('disabled') is not None) or (
                    (el.get_attribute('aria-disabled') or '').lower() == 'true'))


        # 8. 저장 버튼 클릭
        save_btn = driver.find_element(By.XPATH, "/html/body/div[13]/div[1]/div[4]/div/div/div[4]/button[2]")
        close_btn = driver.find_element(By.XPATH, "/html/body/div[13]/div[1]/div[4]/div/div/div[4]/button[1]")
        save_btn.click()
        close_btn.click()

        # 9. 코드 관리 > 함수 정보 진입
        move_menu.move_functioninfo(driver, case_id)

        # 10. 코드 분석 실행 버튼 비활성화 확인
        el = driver.find_element(By.XPATH, "//button[.//span[normalize-space()='코드 분석 실행']]")
        self.assertTrue((not el.is_enabled()) or (el.get_attribute('disabled') is not None) or (
                    (el.get_attribute('aria-disabled') or '').lower() == 'true'))

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)