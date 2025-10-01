# MenuTree : 기능 테스트 › 신뢰성 시험 › 소스코드 메트릭
# Summary : 신뢰성 시험 -> 소스코드 메트릭 검증에 할당 된 담당자가 삭제될 시 해당 담당자 이름이 취소선이 표시된다.
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

class C3724(unittest.TestCase):

    def setUp(self):
        # 0. 드라이버 세팅 및 로그인
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)

    def test_C3724(self):
        driver = self.driver

        # 1. SCM이 GIT인 프로젝트 생성
        default_setting.create_project(driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 정적 시험 결과(STATIC) xml 파일 업로드
        default_setting.upload_project(driver, case_id, "STATIC", "VPES_MIRO2010_git")

        # 3. 프로젝트 > 설정 > 프로젝트 설정 진입
        move_menu.move_projectSetting(driver, case_id)

        # 4. "사용자 등록" 탭 클릭
        driver.find_element(By.ID, "projectRegister-memberRegistration-tab").click()

        # 5. "사용자 추가" 콤보박스 클릭 후 "slpark (slpark)" 클릭
        user_box = driver.find_element(By.ID, "projectRegister-memberBox")
        driver.find_element(By.XPATH,
                            "//*[@id='projectRegister-memberRegistration']/div[1]/div/div[1]/div/div[2]").click()
        user_box.send_keys("slpark")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'slpark')]"))
        ).click()

        # 6. [저장] 버튼 클릭
        driver.find_element(By.XPATH, "//*[@id='projectBtn']").click()

        # 7. 프로젝트 > 코드 관리 > 파일 정보 진입
        move_menu.move_fileinfo(driver, case_id)

        # 8. 테이블의 모든 체크박스 체크
        checkbox = driver.find_element(By.ID, "fileInfoAllCheck")
        checkbox.click()

        # 9. kebab 버튼 클릭 > "사용자 파일 지정" 클릭 후 "파일 사용자 설정" 모달 확인
        kebab_btn = driver.find_element(By.XPATH, "//button[contains(@class,'dropdown-more-btn')]")
        kebab_btn.click()
        driver.find_element(By.XPATH, "//span[text()='사용자 파일 지정']").click()
        WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'파일 사용자 설정')]"))
        )

        # 10. 콤보박스에서 "slpark" 선택 후 [저장] 버튼 클릭
        combo = driver.find_element(By.XPATH, "//*[@id='fileManageEditModal']/div/div/div[2]/form[2]/div[2]/div/div[2]")
        combo.click()
        driver.find_element(By.XPATH, "//span[contains(text(),'slpark')]").click()
        driver.find_element(By.XPATH, "//*[@id='fileManageEditModal']/div/div/div[3]/button[2]").click()
        sleep(3)

        # 12. 테이블의 첫 번째 행 - 네 번째 컬럼 값이 "slpark" 확인
        table_cell = driver.find_element(By.XPATH, "//table/tbody/tr[1]/td[4]")
        self.assertEqual(table_cell.text.strip(), "slpark")

        # 12. 프로젝트 > 설정 > 프로젝트 설정 진입
        move_menu.move_projectSetting(driver, case_id)

        # 13. "사용자 등록" 탭 클릭
        driver.find_element(By.ID, "projectRegister-memberRegistration-tab").click()

        # 14. 사용자 등록 테이블의 첫번째 행 - "삭제" 컬럼 버튼 클릭
        driver.find_element(By.XPATH, "//*[@id='projectRegister-memberList']/tbody/tr/td[5]").click()

        # 15. [저장] 버튼 클릭
        driver.find_element(By.XPATH, "//*[@id='projectBtn']").click()

        # 16. 프로젝트 > 신뢰성 시험 > 소스코드 메트릭 진입
        move_menu.move_metric(driver, case_id)

        # 17. "상세 결과" 테이블의 각 행의 네 번째 컬럼의 값이 "slpark[삭제됨]"임을 확인
        rows = driver.find_elements(By.XPATH, "//div[contains(text(),'상세 결과')]/following::table[1]/tbody/tr")
        found = False
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) >= 4:
                c = cols[3]
                self.assertEqual(c.text.replace("\n", "").strip(), "slpark[삭제됨]")
                sl = c.find_element(By.XPATH,
                                    ".//*[normalize-space(.)='slpark' and (self::s or self::del or self::strike or contains(@style,'line-through') or contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'strike'))]")
                self.assertIn("line-through", ((sl.value_of_css_property("text-decoration-line") or "") + " " + (
                        sl.value_of_css_property("text-decoration") or "")).lower())

                de = c.find_element(By.XPATH, ".//*[normalize-space(.)='[삭제됨]']")
                self.assertNotIn("line-through", ((de.value_of_css_property("text-decoration-line") or "") + " " + (
                        de.value_of_css_property("text-decoration") or "")).lower())
                found = True
                break
        self.assertTrue(found, "담당자가 들어간 행을 찾을 수 없음")

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)