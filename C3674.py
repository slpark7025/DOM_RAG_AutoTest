# MenuTree : 기능 테스트 › 산출물 › 산출물 생성
# Summary : 산출물 -> 개정안 2024-6호로 신뢰성 문서를 생성할 수 있다.(SDD)(xlsx)
from selenium.webdriver.common.keys import Keys
from time import sleep
import os
import unittest
import time
import openpyxl
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import default_setting
import move_menu

case_id = os.path.basename(os.path.splitext(__file__)[0])

class C3674(unittest.TestCase):

    def setUp(self):
        # 0. WebDriver 초기화
        self.driver = default_setting.setup("chrome")
        default_setting.login(self.driver)
        self.driver.implicitly_wait(10)

    def test_C3674(self):
        # 1. SCM이 GIT인 프로젝트 생성
        default_setting.create_project(self.driver, case_id, "CSCI", "GIT", None, "test")

        # 2. 정적 시험 결과(STATIC) xml 파일 업로드
        default_setting.upload_project(self.driver, case_id, "STATIC", "VPES_MIRO2010_git")

        # 3. 프로젝트 > 산출물 진입
        move_menu.move_reliabilityReport(self.driver, case_id)

        # 4. 개정안 값이 "방사청 제2024-6호"임을 확인
        amendment_label = self.driver.find_element(By.XPATH, "/html[1]/body[1]/div[13]/div[1]/div[6]/div[1]/div[1]/div[3]/form[1]/div[1]/span[1]")
        amendment_value = self.driver.find_element(By.XPATH, "/html[1]/body[1]/div[13]/div[1]/div[6]/div[1]/div[1]/div[3]/form[1]/div[1]/span[2]")
        sleep(2)
        self.assertEqual(amendment_label.text.strip(), "개정안")
        self.assertEqual(amendment_value.text.strip(), "방사청 제2024-6호")

        # 5. 공통 설정 - 신뢰성 문서 -> SW 문서 클릭 및 산출물 테이블 확인
        reliability_doc = self.driver.find_element(By.XPATH, "//*[@id='reportGenerateVue']/div[2]/div[2]/div[1]/div/div[2]")
        reliability_doc.click()
        time.sleep(1)
        sw_doc = self.driver.find_element(By.XPATH, "/html[1]/body[1]/div[13]/div[1]/div[6]/div[2]/div[2]/div[1]/div[1]/div[3]/ul[1]/li[2]/span[1]")
        sw_doc.click()
        WebDriverWait(self.driver,10).until(
            EC.presence_of_element_located((By.XPATH,"//*[@id='reportDataTable']/tbody/tr[1]/td[contains(text(),'(SPS) 소프트웨어 산출물 명세서')]"))
        )
        self.assertTrue(self.driver.find_element(By.XPATH,"//*[@id='reportDataTable']/tbody//td[contains(text(),'(SPS) 소프트웨어 산출물 명세서')]"))
        self.assertTrue(self.driver.find_element(By.XPATH,"//*[@id='reportDataTable']/tbody//td[contains(text(),'(SDD) 소프트웨어 설계 명세서')]"))

        # 6. 공통 설정 - 한글 개별 -> 엑셀 클릭
        default_setting.Report_type_SW(self.driver, "엑셀")

        # 7. "(SDD) 소프트웨어 설계 명세서" 클릭
        default_setting.Report_select(self.driver, "(SDD) 소프트웨어 설계 명세서")

        # 8. [산출물 생성] 버튼 클릭 후 "SW 문서 1종" 생성 확인
        default_setting.Report_generate(self.driver)
        WebDriverWait(self.driver,10).until(
            EC.presence_of_element_located((By.XPATH,"//div[contains(text(),'SW 문서 1종')]"))
        )
        self.assertTrue(self.driver.find_element(By.XPATH,"//div[contains(text(),'SW 문서 1종')]"))

        # 9. "SW 문서 1종" 항목 클릭 후 다운로드 파일 확인
        default_setting.enable_download(self)
        default_setting.Report_download(self.driver, "SW 문서 1종")
        download_path = os.path.expanduser("D:/DOM_RAG_AutoTest/report/C3674_test_test CSCI_통합 사전 시험 결과 보고서.xlsx")
        WebDriverWait(self.driver, 20).until(lambda d: os.path.exists(download_path))
        self.assertTrue(os.path.exists(download_path))

        # 10. 엑셀 파일 열어 C열 39번 행 값 확인
        wb = openpyxl.load_workbook(download_path)
        ws = wb.active
        cell_value = ws["C39"].value
        self.assertEqual(cell_value.strip(), "private const string")
        wb.close()

    def tearDown(self):
        result = default_setting.get_result(self)
        default_setting.upload_result(self, case_id, result)
        self.driver.quit()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)