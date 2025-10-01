# MenuTree : 기능 테스트 › 신뢰성 시험 › 정적 시험 › 파일 별 결함 상세 결과
# Summary : 신뢰성 시험 -> 정적 검증에 파일 관리에서 지정한 담당자가 표시된다.
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

class C3708(unittest.TestCase):
    def setUp(self):
        # 1. 드라이버 설정 및 로그인
        self.driver = default_setting.setup("vpes")
        default_setting.login(self.driver)

    def test_C3708(self):
        # 2. SCM이 GIT인 프로젝트 생성
        default_setting.create_project(self.driver, case_id, "CSCI", "GIT", None, "test")

        # 3. 정적 시험 결과 xml 파일 업로드
        default_setting.upload_project(self.driver, case_id, "STATIC", "VPES_MIRO2010_git")

        # 4. 프로젝트 > 설정 > 프로젝트 설정 진입
        move_menu.move_projectSetting(self.driver, case_id)

        # 5. "사용자 등록" 탭 클릭
        self.driver.find_element(By.ID, "projectRegister-memberRegistration-tab").click()

        # 6. "사용자 추가" 콤보박스 클릭 후 "slpark (slpark)" 클릭
        self.driver.find_element(By.XPATH,
                            "//*[@id='projectRegister-memberRegistration']/div[1]/div/div[1]/div/div[2]").click()
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'slpark')]"))
        ).click()

        # 7. [저장] 버튼 클릭
        self.driver.find_element(By.XPATH, "//*[@id='projectBtn']").click()

        # 8. 프로젝트 > 코드 관리 > 파일 정보 진입
        move_menu.move_fileinfo(self.driver, case_id)

        # 9. 테이블의 헤더 - 첫 번째 컬럼의 체크박스 클릭
        self.driver.find_element(By.ID, "fileInfoAllCheck").click()

        # 10. kebab 버튼 클릭 > "사용자 파일 지정" 클릭 후 모달 출력 확인
        kebab_btn = self.driver.find_element(By.XPATH, "//button[contains(@class,'dropdown-more-btn')]")
        kebab_btn.click()
        self.driver.find_element(By.XPATH, "//span[text()='사용자 파일 지정']").click()
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//*[contains(text(),'파일 사용자 설정')]"))
        )

        # 11. 파일 사용자 설정 모달에서 콤보박스 클릭 후 항목 확인
        combo = self.driver.find_element(By.XPATH, "//*[@id='fileManageEditModal']/div/div/div[2]/form[2]/div[2]/div/div[2]")
        combo.click()
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'admin')]"))
        )
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'slpark')]"))
        )

        # 12. 콤보박스에서 "slpark" 선택 후 [저장] 버튼 클릭
        self.driver.find_element(By.XPATH, "//span[contains(text(),'slpark')]").click()
        self.driver.find_element(By.XPATH, "//*[@id='fileManageEditModal']/div/div/div[3]/button[2]").click()
        sleep(3)

        # 13. 테이블의 첫 번째 행 - 네 번째 컬럼의 값 확인
        table_cell = self.driver.find_element(By.XPATH, "//table/tbody/tr[1]/td[4]")
        self.assertEqual(table_cell.text.strip(), "slpark")

        # 14. 프로젝트 > 신뢰성 시험 > 정적 시험 진입
        move_menu.move_static(self.driver, case_id)

        # 15. "파일별 결함 상세 결과" 테이블의 각 행의 네 번째 컬럼의 값이 "slpark"임을 확인
        rows = self.driver.find_elements(
            By.XPATH, '//div[contains(text(),"파일별 결함 상세 결과")]/following::table[1]/tbody/tr/td[4]'
        )
        for row in rows:
            self.assertEqual(row.text.strip(), "slpark")

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)