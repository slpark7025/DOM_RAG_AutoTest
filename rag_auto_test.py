# -*- coding: utf-8 -*-
# pip install -U langchain langchain-openai langchain-community chromadb tiktoken python-dotenv

import os
import re
import math
from urllib.parse import urljoin, urlsplit
from dotenv import load_dotenv

import chromadb
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableMap
from langchain_core.output_parsers import StrOutputParser

from validate_selector_ids import validate_generated_code  # ID 정합성 검증 모듈


# ========================= 공통 유틸 =========================
def derive_base_path(s: str) -> str:
    """전체 URL/상대경로 무엇이든 받아 /vpes/<section> 형태로 변환"""
    def to_base_path(path: str) -> str:
        parts = [seg for seg in path.split("/") if seg]
        return ("/" + "/".join(parts[:2])) if len(parts) >= 2 else path
    return to_base_path(urlsplit(s).path)

def extract_keywords(text):
    # 포함일반 키워드 - 영문/숫자 + 한글까지
    words = [w.lower() for w in re.findall(r'[A-Za-z0-9가-힣_-]+', text)]

    # 대괄호 안 [ ... ] 내용도 추가 (예: [dropdown-more-btn])
    bracket_hints = [h.lower() for h in re.findall(r'\[([^\]]+)\]', text)]
    paren_hints   = [h.lower() for h in re.findall(r'\(([^)]+)\)', text)]
    # 기존 호환 위해 전체 키워드는 그대로 반환
    return words + bracket_hints + paren_hints

def build_selector_inventory(dom_docs):
    """context(dom_docs)에서 허용 가능한 ID 집합과 XPath 후보 풀을 만든다."""
    allowed_ids = set()
    xpath_pool = []
    for d in dom_docs:
        m = getattr(d, "metadata", {}) or {}
        if not isinstance(m, dict):
            continue
        if m.get("id"):
            allowed_ids.add(m["id"])
        if m.get("xpath"):
            blob = " ".join([
                (m.get("text") or ""),
                (m.get("desc") or ""),
                (m.get("tag") or ""),
                (m.get("aria-label") or ""),
                (m.get("placeholder") or ""),
            ]).lower()
            xpath_pool.append({
                "xpath": m["xpath"],
                "blob": blob,
                "url": (m.get("url") or ""),
                "id": (m.get("id") or ""),  # 초기 선택에도 도움(가능하면 ID 우선)
            })
    return allowed_ids, xpath_pool

def pick_best_xpath(xpath_pool, keywords, preferred_paths=()):
    """키워드와 blob(text/desc/tag 조합)을 단순 매칭 + URL 가중치로 가장 관련도 높은 XPath 선택"""
    best = None
    best_score = -1
    for item in xpath_pool:
        score = sum(1 for kw in keywords if kw in item["blob"])
        # ✅ 해당 단계 URL이면 가점(강화)
        if any(p and p in (item.get("url") or "") for p in preferred_paths):
            score += 8
        if score > best_score:
            best = item
            best_score = score
    return best["xpath"] if best else (xpath_pool[0]["xpath"] if xpath_pool else None)

def enforce_known_selectors(generated_code: str, dom_docs, question: str, preferred_paths=()):
    """허구 ID → XPath로 자동 대체(화이트리스트 기반). (간단 버전: ID 관련만 처리)"""
    allowed_ids, xpath_pool = build_selector_inventory(dom_docs)
    if not xpath_pool:
        return generated_code
    keywords = extract_keywords(question)

    def best_xpath():
        xp = pick_best_xpath(xpath_pool, keywords, preferred_paths=preferred_paths)
        return xp or xpath_pool[0]["xpath"]

    # 1) .find_element(By.ID, "…")
    generated_code = re.sub(
        r'(\.find_element\()\s*By\.ID\s*,\s*["\']([^"\']+)["\']\s*(\))',
        lambda m: m.group(0) if m.group(2) in allowed_ids
        else f'{m.group(1)}By.XPATH, "{best_xpath()}"{m.group(3)}',
        generated_code
    )

    # 2) (By.ID, "…") — EC 패턴 포함 모든 곳
    generated_code = re.sub(
        r'\(\s*By\.ID\s*,\s*["\']([^"\']+)["\']\s*\)',
        lambda m: m.group(0) if m.group(1) in allowed_ids
        else f'(By.XPATH, "{best_xpath()}")',
        generated_code
    )

    return generated_code

def remove_markdown(generated_code: str) -> str:
    return generated_code.replace("```python", "").replace("```", "").strip()

def insert_sleep_before_assert(generated_code: str) -> str:
    # 첫 assert/ self.assert/ pytest-style 'assert ' 앞에 sleep(2) 한 번만 삽입
    pat = re.compile(r'^(\s*)(?:self\.)?assert', re.MULTILINE)
    m = pat.search(generated_code)
    if not m:
        return generated_code
    lead = m.group(1)
    g = generated_code[:m.start()] + f"{lead}sleep(2)\n" + generated_code[m.start():]
    if "sleep(" in g and "from time import sleep" not in g:
        g = "from time import sleep\n" + g
    return g

def patch_unittest_main(generated_code: str) -> str:
    return re.sub(
        r'if __name__ == ["\']__main__["\']:\s*unittest\.main\(\)',
        'if __name__ == "__main__":\n    unittest.main(argv=[\'first-arg-is-ignored\'], exit=False)',
        generated_code
    )

def patch_teardown(generated_code: str) -> str:
    # 과매칭 방지: 앵커/들여쓰기 기준 강화
    return re.sub(
        r'(?ms)^(\s*)def\s+tearDown\(self\):\s*\n(.*?\n)?\1\s*self\.driver\.quit\(\)\s*$',
        r'''\1def tearDown(self):
\1    result = default_setting.get_result(self)
\1    default_setting.upload_result(self, case_id, result)
\1    self.driver.quit()''',
        generated_code
    )

def ensure_import(g: str, line: str) -> str:
    return (line + "\n" + g) if line not in g else g

def postprocess_generated_code(generated_code: str) -> str:
    """전체 후처리 통합(필수 최소만 유지)"""
    generated_code = remove_markdown(generated_code)
    generated_code = insert_sleep_before_assert(generated_code)
    generated_code = patch_teardown(generated_code)
    generated_code = patch_unittest_main(generated_code)

    # 필수 import 보강(실제 생성 코드에서 자주 쓰는 것만)
    generated_code = ensure_import(generated_code, "import unittest")
    generated_code = ensure_import(generated_code, "from selenium.webdriver.common.by import By")
    generated_code = ensure_import(generated_code, "from selenium.webdriver.support.ui import WebDriverWait")
    generated_code = ensure_import(generated_code, "from selenium.webdriver.support import expected_conditions as EC")
    generated_code = ensure_import(generated_code, "from selenium.webdriver.common.keys import Keys")
    generated_code = ensure_import(generated_code, "import default_setting")

    before = generated_code
    generated_code = strip_document_prefix_xpaths(generated_code)
    if before != generated_code:
        print("🔧 Stripped '/[document][n]/' prefix from XPaths.")

    return generated_code


def strip_document_prefix_xpaths(g: str) -> str:
    """
    (By.XPATH, "...") 형태의 문자열 중
    XPath가 '/[document]/' 또는 '/[document][숫자]/' 로 시작하면 그 프리픽스만 제거.
    예) '/[document][1]/html[1]/body[1]/...' -> '/html[1]/body[1]/...'
    """
    # 1) 문자열 앞의 '/[document][n]/' 패턴만 없애는 헬퍼
    def _fix(xp: str) -> str:
        return re.sub(r'^\s*/\s*\[document\](?:\[\d+\])?/?', '/', xp)

    # 2) 공통 치환기: (By.XPATH, "...") 캡처해서 내부만 교체
    def _repl_tuple(m):
        quote = m.group(2)
        xp = m.group(3)
        fixed = _fix(xp)
        return f"{m.group(1)}{quote}{fixed}{quote}{m.group(4)}"

    # (a) (By.XPATH, "…")  — EC, until 등 모든 튜플 인자
    g = re.sub(r'(\(\s*By\.XPATH\s*,\s*)(["\'])(.+?)\2(\s*\))', _repl_tuple, g, flags=re.DOTALL)

    # (b) .find_element(By.XPATH, "…")
    g = re.sub(r'(\.find_element\(\s*By\.XPATH\s*,\s*)(["\'])(.+?)\2(\s*\))', _repl_tuple, g, flags=re.DOTALL)

    # (c) .find_elements(By.XPATH, "…")  (있을 수도 있으니 케어)
    g = re.sub(r'(\.find_elements\(\s*By\.XPATH\s*,\s*)(["\'])(.+?)\2(\s*\))', _repl_tuple, g, flags=re.DOTALL)

    return g

def backfill_step_docs_if_needed(dom_docs, selected_dirs, embedding, step_base_paths, min_per_step=40, hard_cap_per_step=200):
    """
    스텝별(base_path)로 컨텍스트 문서 수가 min_per_step 미만이면,
    각 DB의 'dom_elements' 컬렉션에서 메타데이터 url에 base_path가 포함된 문서를 직접 가져와 보충.
    (중복 방지, 최대 hard_cap_per_step까지)
    """
    # 이미 가진 문서의 중복 키 집합
    seen = set()
    for d in dom_docs:
        m = getattr(d, "metadata", {}) or {}
        seen.add((m.get("url") or "", m.get("xpath") or "", m.get("id") or ""))

    def count_for(base):
        return sum(1 for d in dom_docs if base and base in (getattr(d, "metadata", {}) or {}).get("url", ""))

    bases_in_order = [bp for bp in step_base_paths if bp]
    # 입력 순서 보존 + 중복 제거
    bases_in_order = list(dict.fromkeys(bases_in_order))

    for base in bases_in_order:
        if count_for(base) >= min_per_step:
            continue

        for db_dir in selected_dirs:
            try:
                client = chromadb.PersistentClient(path=db_dir)
                coll = client.get_collection(name="dom_elements")
                raw = coll.get(include=["metadatas", "documents"], limit=100000)
                mets = raw.get("metadatas", []) or []
                docs = raw.get("documents", []) or []

                added = 0
                for meta, doc in zip(mets, docs):
                    m = meta or {}
                    u = m.get("url") or ""
                    if base not in u:
                        continue
                    key = (u, m.get("xpath") or "", m.get("id") or "")
                    if key in seen:
                        continue
                    seen.add(key)
                    dom_docs.append(type("Doc", (object,), {"metadata": m, "page_content": doc}))
                    added += 1
                    if count_for(base) >= hard_cap_per_step:
                        break

                if count_for(base) >= min_per_step:
                    break  # 다음 base로
            except Exception as e:
                print(f"[백필 경고] {db_dir} 접근 실패: {e}")

    return dom_docs

# ========================= 단계별(URL 스코프) 셀렉터 리라이트 =========================
def _inventory_for_paths(dom_docs, base_paths):
    """주어진 base_paths에 속한 DOM만 모아 allowed_ids / xpath_pool 생성"""
    allowed_ids = set()
    xpath_pool = []
    for d in dom_docs:
        m = getattr(d, "metadata", {}) or {}
        u = (m.get("url") or "")
        tag = (m.get("tag") or "").lower()
        xp = (m.get("xpath") or "")
        if base_paths and not any(p and p in u for p in base_paths):
            continue
        if m.get("id"):
            allowed_ids.add(m["id"])
        if m.get("xpath"):
            blob = " ".join([
                (m.get("text") or ""),
                (m.get("desc") or ""),
                (m.get("tag") or ""),
                (m.get("aria-label") or ""),
                (m.get("placeholder") or ""),
            ]).lower()
            xpath_pool.append({
                "xpath": m["xpath"],
                "id": (m.get("id") or ""),
                "url": u,
                "blob": blob,
                "aria": (m.get("aria-label") or ""),
                "placeholder": (m.get("placeholder") or ""),
                "tag": tag,
                "xpath_lower": xp.lower(),
                "desc": (m.get("desc") or ""),
            })
    return allowed_ids, xpath_pool

def rewrite_selectors_per_step(
    generated_code: str,
    dom_docs,
    step_texts: list[str],   # URL 제거된 단계 텍스트 (clean_steps)
    step_base_paths: list[str],
):
    """
    생성된 코드의 '# n.' 주석 블록을 단계별로 잘라,
    해당 단계의 URL 스코프 DOM만 보고 셀렉터를 보정한다.
    """
    def _best_item(pool, kw):
        # 키워드 점수 + aria/placeholder 포함 가점
        best, best_score = None, -1
        for it in pool:
            b = it["blob"] or ""
            tag = it.get("tag") or ""
            xp = it.get("xpath_lower") or ""
            idv = it.get("id") or ""
            desc = (it.get("desc") or "").lower()

            s = 0
            # 기본 blob 매칭 (text, desc, tag, aria, placeholder 통합)
            s += sum(1 for k in kw if k in b)

            # aria / placeholder 매칭 → 약한 가점
            if any(k in (it.get("aria") or "").lower() for k in kw):
                s += 2
            if any(k in (it.get("placeholder") or "").lower() for k in kw):
                s += 2

            # id 매칭 → 강한 가점
            if any(k in idv.lower() for k in kw):
                s += 5

            # desc 전용 매칭
            if any(k in desc for k in kw):
                s += 4

            # class/xpath 매칭 → 약한 가점
            if any(k in xp for k in kw):
                s += 1

            # 태그 힌트 ([button], [span] 등) 매칭 → 강한 가점
            if any(k == tag for k in kw):
                s += 10

            if s > best_score:
                best, best_score = it, s
        return best

    # 단계별 블록 정규식: '# 10.' 헤더부터 다음 '# 11.' 전까지
    for idx, (txt, url) in enumerate(zip(step_texts, step_base_paths), start=1):
        base = derive_base_path(url) if url else None
        if not base:
            continue

        # 해당 단계 블록을 찾는다
        pat = re.compile(rf'(^\s*#\s*{idx}\.\s.*?$)([\s\S]*?)(?=^\s*#\s*\d+\.\s|\Z)', re.MULTILINE)
        m = pat.search(generated_code)
        if not m:
            continue

        header, body = m.group(1), m.group(2)
        keywords = extract_keywords(txt)

        # 이 단계 URL 스코프 DOM 인벤토리
        allowed_ids, pool = _inventory_for_paths(dom_docs, [base])

        # 1) 허구 ID → XPATH 치환 (스코프 한정)
        def _best_xpath():
            if not pool:
                return None
            cand = _best_item(pool, keywords)
            return cand["xpath"] if cand else pool[0]["xpath"]

        body = re.sub(
            r'(\.find_element\()\s*By\.ID\s*,\s*["\']([^"\']+)["\']\s*(\))',
            lambda mm: mm.group(0) if mm.group(2) in allowed_ids
            else f'{mm.group(1)}By.XPATH, "{_best_xpath() or pool[0]["xpath"]}"{mm.group(3)}',
            body
        )
        body = re.sub(
            r'\(\s*By\.ID\s*,\s*["\']([^"\']+)["\']\s*\)',
            lambda mm: mm.group(0) if mm.group(1) in allowed_ids
            else f'(By.XPATH, "{_best_xpath() or pool[0]["xpath"]}")',
            body
        )

        # 2) 범용 input 찾기 코드 → 이 단계 스코프에서 가장 알맞은 input으로 교체
        input_pool = [
            it for it in pool
            if (
                    it.get("tag") == "input"
                    or "/input" in (it.get("xpath_lower") or "")
                    or it.get("placeholder")  # placeholder가 있으면 보통 입력칸
                    or it.get("aria")  # aria-label만 있는 입력도 존재
            )
        ]
        best_input = None
        if input_pool:
            input_pool.sort(key=lambda it: (0 if it.get("id") else 1, len(it.get("xpath") or "")))
            best_input = input_pool[0]
            # (b) find_element(By.XPATH, "//input...") 류 교체
            body = re.sub(
                r'((?:find_element|find_elements)\(\s*)By\.XPATH\s*,\s*(["\'])(?:(?!\2).)*//input(?:(?!\2).)*\2',
                (lambda mm: f'{mm.group(1)}By.ID, "{best_input["id"]}"' if best_input["id"]
                 else f'{mm.group(1)}By.XPATH, "{best_input["xpath"]}"'),
                body
            )

            # (c) "첫 번째 input에 쓴다" 같은 패턴 교체(있는 경우)
            generic_first_input = re.compile(
                r'inputs\s*=\s*driver\.find_elements\([^\)]*\)\)[\s\S]*?send_keys\(u?\'?\\?ue007\'?\)\s*#?\s*ENTER',
                re.MULTILINE
            )
            if generic_first_input.search(body):
                fixed = []
                if best_input["id"]:
                    fixed.append(f'elem = wait.until(EC.element_to_be_clickable((By.ID, "{best_input["id"]}")))')
                else:
                    fixed.append(f'elem = wait.until(EC.element_to_be_clickable((By.XPATH, "{best_input["xpath"]}")))')
                fixed.append('try:\n    elem.clear()\nexcept Exception:\n    pass')
                fixed.append('elem.send_keys(case_id)\nelem.send_keys(Keys.ENTER)')
                body = generic_first_input.sub("\n".join(fixed), body)

        # 3) 절대 XPath 튜플 인자도 이 단계 스코프에 맞춰 교체
        best_xp = _best_xpath()
        if best_xp:
            body = re.sub(
                r'(\(\s*By\.XPATH\s*,\s*)(["\'])(/\s*(?:\[document\](?:\[\d+\])?/)?html(?:(?!\2)[\s\S])*)\2(\s*\))',
                lambda mm: f'{mm.group(1)}"{best_xp}"{mm.group(4)}',
                body
            )

        # 블록 치환 반영
        generated_code = generated_code[:m.start()] + header + body + generated_code[m.end():]

    return generated_code



# ========================= URL 기반 컨텍스트 전처리(핵심) =========================
def filter_and_order_docs_by_urls(dom_docs, preferred_paths):
    """입력한 URL/베이스경로에 해당하는 문서만 남기고, 경로 순서대로 앞으로 정렬."""
    if not preferred_paths:
        return dom_docs

    def belongs(url: str) -> bool:
        return any(p and p in url for p in preferred_paths)

    kept, others = [], []
    for d in dom_docs:
        m = getattr(d, "metadata", {}) or {}
        u = (m.get("url") or "")
        (kept if belongs(u) else others).append(d)

    if not kept:
        return dom_docs  # 매칭 없으면 안전하게 원본 유지

    def ord_key(d):
        u = (getattr(d, "metadata", {}) or {}).get("url", "")
        for i, p in enumerate(preferred_paths):
            if p and p in u:
                return i
        return len(preferred_paths) + 1

    kept.sort(key=ord_key)
    return kept

def docs_for_base(dom_docs, base_path: str):
    """특정 단계의 base_path에 해당하는 문서만 반환(없으면 빈 목록)."""
    if not base_path:
        return []  # ✅ URL 없는 단계는 DOM 제공 안 함
    picked = []
    for d in dom_docs:
        m = getattr(d, "metadata", {}) or {}
        u = m.get("url") or ""
        if base_path in u:
            picked.append(d)
    return picked


# ========================= 단계 텍스트에서 URL 추출 =========================
def parse_step_urls(lines):
    """
    각 단계 문자열에서 http.../vpes/... 또는 /vpes/... URL을 추출.
    반환: (clean_steps, step_base_paths, url_tags_for_prompt)
      - clean_steps: URL 제거 후의 단계 텍스트
      - step_base_paths: 각 단계가 참조할 base_path(/vpes/<section>)
         · 해당 줄에 URL이 있으면 그걸 사용, 없으면 None (직전 URL 계승 금지)
      - url_tags_for_prompt: 각 단계 뒤에 붙일 '@URL:/vpes/...' 태그 리스트
    """
    url_pat = re.compile(r'((?:https?://[^\s,)\]　]+)|(?:/vpes/[^\s,)\]　]+))', re.IGNORECASE)

    clean_steps = []
    step_base_paths = []
    url_tags = []

    for s_raw in lines:
        m = url_pat.search(s_raw)
        if m:
            u = m.group(1).strip()
            bp = derive_base_path(u) or u
            s2 = (s_raw[:m.start()] + s_raw[m.end():]).strip().rstrip(',').rstrip()
            clean_steps.append(s2)
            step_base_paths.append(bp)
            url_tags.append(f' @URL:{bp}')
        else:
            clean_steps.append(s_raw.strip())
            step_base_paths.append(None)   # ✅ 직전 URL 계승하지 않음
            url_tags.append('')

    return clean_steps, step_base_paths, url_tags


# ========================= 선택 DB 라우팅 & 검색 =========================
CHROMA_BASE_DIR = "./chroma"  # JSON별 DB 폴더들이 위치한 루트

def select_chroma_dirs(base_dir: str, user_inputs: list[str]) -> list[str]:
    """
    ./chroma 하위 폴더 중에서, 폴더명에 사용자가 입력한 텍스트(쉼표 분리 원본)가
    '부분 문자열'로 포함된 폴더만 선택 (대소문자 무시).
    """
    if not os.path.isdir(base_dir):
        return []
    keys = [u.strip().lower() for u in user_inputs if u and u.strip()]
    if not keys:
        return []
    selected = []
    for name in os.listdir(base_dir):
        p = os.path.join(base_dir, name)
        if not os.path.isdir(p):
            continue
        low = name.lower()
        if any(k in low for k in keys):
            selected.append(p)
    return selected

def retrieve_from_selected_dirs(
    selected_dirs: list[str],
    query: str,
    embedding,              # OpenAIEmbeddings 인스턴스
    k_total: int = 200,     # 전체 상한(필요시 100~400 조정)
    mmr_fetch_factor: int = 5,
    mmr_lambda: float = 0.35
):
    """
    선택된 여러 DB 폴더 각각에서 MMR 검색을 수행하고 결과를 합칩니다.
    각 DB당 k를 균등 분배(올림)하여 과도한 편중을 방지합니다.
    """
    if not selected_dirs:
        return []
    per_db = max(1, math.ceil(k_total / len(selected_dirs)))
    fetch_k = min(per_db * mmr_fetch_factor, 1000)

    all_docs = []
    for db_dir in selected_dirs:
        try:
            client = chromadb.PersistentClient(path=db_dir)
            vs = Chroma(
                client=client,
                collection_name="dom_elements",
                embedding_function=embedding,
            )
            docs = vs.max_marginal_relevance_search(
                query=query,
                k=per_db,
                fetch_k=fetch_k,
                lambda_mult=mmr_lambda
            )
            all_docs.extend(docs)
        except Exception as e:
            print(f"[경고] DB 접근 실패, 건너뜀: {db_dir} ({e})")
    return all_docs[:k_total]


# --- URL별 독립 검색 상한 ---
K_PER_BASE = 300  # URL 하나당 최대 몇 개까지 뽑을지 (원하면 200~400 사이로 조절)

def retrieve_dom_docs_per_base(
    base_paths: list[str],
    clean_steps: list[str],
    step_base_paths: list[str],
    embedding,
):
    """
    각 base_path(예: /vpes/ProjectModify)마다 그 base를 참조하는 스텝들만 모아
    그 URL에 해당하는 DB들만 대상으로 독립적으로 MMR 검색을 수행하고 결과를 합쳐 반환.
    """
    from collections import defaultdict

    all_docs = []
    # base_path -> 해당 URL을 참조하는 스텝 텍스트만 모은 쿼리
    steps_by_base = defaultdict(list)
    for txt, bp in zip(clean_steps, step_base_paths):
        if bp:
            steps_by_base[bp].append(txt)

    # 입력된 base_paths 순서대로 처리
    for bp in base_paths:
        if not bp:
            continue

        # (1) 이 base에 대응하는 디렉터리만 선택
        keys = [bp, os.path.basename(bp)]
        dirs_for_bp = select_chroma_dirs(CHROMA_BASE_DIR, keys)
        if not dirs_for_bp:
            # 해당되는 DB가 없으면 스킵(원하면 fallback 로직 추가 가능)
            continue

        # (2) 이 base가 참조된 스텝만 쿼리로 구성 (없으면 bp 자체를 쿼리로)
        query_for_bp = "\n".join(steps_by_base.get(bp, [])) or bp

        # (3) 이 base 전용 검색
        docs_bp = retrieve_from_selected_dirs(
            selected_dirs=dirs_for_bp,
            query=query_for_bp,
            embedding=embedding,
            k_total=K_PER_BASE,
            mmr_fetch_factor=5,
            mmr_lambda=0.35,
        )
        all_docs.extend(docs_bp)

    return all_docs


# ========================= 메인 로직 =========================
def main():
    # 1) 환경 변수 로딩
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 또는 환경변수를 확인하세요.")

    # 2) LLM/임베딩 초기화
    llm = ChatOpenAI(model="gpt-5")
    embedding = OpenAIEmbeddings(model="text-embedding-3-large")

    # 3) 기본 URL
    BASE_URL = "http://localhost:38080"

    # 4) Prompt 정의
    prompt = PromptTemplate(
        input_variables=["context", "question", "function_context"],
        template="""
# ===== CoT 적용 버전 (출력은 코드만) =====
단계적으로 내부에서 생각하되, 최종 출력에는 절대 사고 과정을 포함하지 마세요.
당신은 Selenium 테스트 자동화 코드를 생성하는 전문가입니다.

아래는 웹 페이지의 HTML DOM 요소 목록(context)과
기능 함수 요약(function_context), 그리고 테스트 시나리오(question)입니다.

# [내부 사고 프로세스 — 출력 금지]
- 이 섹션의 내용, 중간 메모, 근거, 체크리스트는 절대 출력하지 말 것.
- 내부적으로만 다음 단계를 거쳐 최선의 답을 선택하고, 최종 결과(테스트 코드)만 출력할 것.
  1) 시나리오 파싱 → 단계별 행동으로 분해.
  2) 각 **단계 라인 끝의 '@URL:/vpes/…' 태그**가 있으면 해당 URL 범위의 요소만 사용.
     - 태그가 없으면 DOM context를 사용하지 말고 function_context 함수만 사용.
  3) 함수 재사용 매핑 → function_context를 스캔해 동일/유사 기능 우선 매핑.
  4) DOM 매핑 → context의 text/description/aria/placeholder와 의미적으로 정합되게 선택.
     - **선택자 우선순위: ID > CSS > XPath** (context에 제공된 값만 사용).
  5) 중복 이동 제거: login 후 /vpes 재이동 금지 등.
  6) 코드 설계: unittest.TestCase 골격 → setUp → TC 메서드 → tearDown → main 순서.
  7) 주석 규칙: 각 주요 단계에 “숫자. 한 줄 요약”만.
  8) 형식 점검: import 최상단, case_id 추출, URL 조립 규칙, 선택자 규칙, 함수 재사용 준수.
  9) 자기검토: 불필요한 send_keys()/click()/driver.get() 제거.
 10) 최종 산출: 아래 [최종 출력 규칙]을 지켜 오직 코드블록만 출력.

# [기본 테스트 코드 구조]
- unittest.TestCase 사용.
- setUp()은 default_setting.setup()으로 WebDriver 초기화.
- case_id는 import 아래:
  => case_id = os.path.basename(os.path.splitext(__file__)[0])
- 각 주요 단계에 **숫자. 한 줄 요약** 주석.
- tearDown()은 테스트 메서드 다음.
- if __name__ == "__main__": 포함.
- import 선언은 모두 맨 윗단.

# [기존 함수 활용 지침]
- function_context는 default_setting.py 및 move_menu.py의 요약.
- default_setting.login(driver)는 로그인 후 /vpes로 이동. 이후 중복 이동 금지.
- driver.get()이 포함된 함수는 중복 호출 피하기.
- 제공된 함수가 시나리오와 의미가 같다면 반드시 재사용.

# [셀렉터 규칙]  ID > CLASS/CSS > XPath
- 단계 텍스트에 괄호로 태그가 명시되면(예: (div)/(span)/(input)/(button)), 해당 태그(또는 괄호 안에 CSS 표기가 있으면 그 CSS)를 최우선으로 선택한다. (우선순위: TagHint/CSSHilt > ID > CSS > XPath)

# [URL 기준 DOM 선택]
- 시나리오 단계의 @URL을 기준으로 context를 필터링하여 셀렉터 선택.
- 상대경로 "/vpes/xxx"는 아래식으로 Full URL 구성:
  target_url = "/vpes/xxx"
  page_url = "http://localhost:38080" + target_url
  driver.get(page_url)

# [ASSERT 규칙]
- page_source 금지. 요소 상태/속성/URL/토스트 등으로 검증.

---

## DOM 요소 목록 (context):
{context}

## 기능 함수 요약 (function_context):
{function_context}

## 테스트 시나리오 (question):
{question}
---

# [URL 기준 DOM 선택]eksrP
- 시나리오 단계의 @URL을 기준으로 context를 필터링하여 셀렉터 선택.
- 상대경로 "/vpes/xxx"는 아래식으로 Full URL 구성:
  target_url = "/vpes/xxx"
  page_url = "http://localhost:38080" + target_url
  driver.get(page_url)
- ✅ @URL이 없는 단계에서는 DOM context를 사용하지 말고, function_context의 함수만 사용(이동/유틸 호출). 셀렉터 생성 금지.

# [최종 출력 규칙]
- 오직 **실행 가능한 Python 코드**만 하나의 코드블록으로 출력: ```python ... ```
- 내부 사고, 근거, 설명 텍스트 출력 금지(주석 규칙 외).
- tc id 사용하는 class와 함수 외 추가 함수 생성 금지
        """.strip()
    )

    # 5) 테스트케이스명/시나리오 입력
    tc_name = input("테스트케이스명을 입력하세요 (예: C8270): ").strip()
    print("💬 테스트 시나리오를 단계별로 입력하세요 (한 줄에 한 단계).")
    print("    ↳ 각 단계 끝에 /vpes/... 또는 http(s)://.../vpes/... 를 붙이면 그 URL 스코프로 셀렉터를 고릅니다.")
    print("    ↳ 빈 줄(Enter)을 입력하면 종료됩니다.")

    steps_raw = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        steps_raw.append(line.strip())

    if not steps_raw:
        raise ValueError("최소 1개 이상의 단계가 필요합니다. 예: '1. VPES 로그인'")

    # 5-1) 단계에서 URL 추출
    clean_steps, step_base_paths, url_tags = parse_step_urls(steps_raw)

    # 프롬프트용 질문 문자열(각 단계 뒤에 URL 태그 추가)
    question_lines = [f"{i+1}. {txt}{url_tags[i]}" for i, txt in enumerate(clean_steps)]
    query = "\n".join(question_lines)

    # 6) URL(또는 키워드) 입력 → (단계에 URL이 있으면 생략)
    inputs = [bp for bp in step_base_paths if bp]  # 단계에서 추출한 base_path들을 우선 사용
    if not inputs:
        raw_urls = input('비교할 URL을 추가로 입력하세요 (여러 개면 쉼표로 구분, 없으면 Enter): ').strip()
        inputs = [u.strip() for u in raw_urls.split(",") if u.strip()]
        inputs = [derive_base_path(u) for u in inputs]

    # /vpes/<section> 형태의 base_paths
    base_paths = list(dict.fromkeys(inputs))
    print("\n🌐 입력/추출된 URL(base) 목록:")
    for u in base_paths:
        print(" -", u)

    # 7) 선택된 DB 폴더만 대상으로 Retrieval
    match_keys = base_paths + [os.path.basename(p) for p in base_paths]
    selected_dirs = select_chroma_dirs(CHROMA_BASE_DIR, match_keys)

    if not selected_dirs:
        print(f"[경고] 입력 텍스트와 일치하는 DB 폴더가 없습니다. 전체 DB 대상으로 검색합니다.")
        selected_dirs = [
            os.path.join(CHROMA_BASE_DIR, d)
            for d in os.listdir(CHROMA_BASE_DIR)
            if os.path.isdir(os.path.join(CHROMA_BASE_DIR, d))
        ]
        if not selected_dirs:
            raise RuntimeError(f"검색 가능한 DB 폴더가 없습니다: {CHROMA_BASE_DIR}")

    print("\n🔎 검색에 사용할 DB 폴더:")
    for d in selected_dirs:
        print(" -", d)
    '''
    # 우선 전체를 한 번 검색 (시나리오 전체를 쿼리로)
    dom_docs_lc = retrieve_from_selected_dirs(
        selected_dirs=selected_dirs,
        query=query,
        embedding=embedding,
        k_total=200,           # 필요 시 100~400로 조정
        mmr_fetch_factor=5,
        mmr_lambda=0.35
    )
    '''
    # URL별로 완전 분리해서 독립 검색 (URL마다 K_PER_BASE개까지)
    dom_docs_lc = retrieve_dom_docs_per_base(
        base_paths=base_paths,
        clean_steps=clean_steps,
        step_base_paths=step_base_paths,
        embedding=embedding,
    )

    # LangChain Document → 간단 객체로 변환
    dom_docs = [
        type("Doc", (object,), {"metadata": d.metadata, "page_content": d.page_content})
        for d in dom_docs_lc
    ]

    # 중복 제거 (url, xpath, id 기준)
    seen, dedup = set(), []
    for d in dom_docs:
        m = getattr(d, "metadata", {}) or {}
        key = (m.get("url") or "", m.get("xpath") or "", m.get("id") or "")
        if key in seen:
            continue
        seen.add(key)
        dedup.append(d)
    dom_docs = dedup

    # URL별로 최소 문서수 보장
    dom_docs = backfill_step_docs_if_needed(dom_docs, selected_dirs, embedding, step_base_paths, min_per_step=60,
                                            hard_cap_per_step=200)

    # 8) function_context 로드 (있을 때만)
    def safe_load_collection(persist_dir: str, collection_name: str):
        try:
            client = chromadb.PersistentClient(path=persist_dir)
            coll = client.get_collection(name=collection_name)
            raw = coll.get(include=["documents"], limit=200)
            docs = raw.get("documents") or []
            return [type("Doc", (object,), {"metadata": {}, "page_content": d}) for d in docs]
        except Exception:
            return []

    default_docs = safe_load_collection("./chroma_default_setting", "default_setting")
    move_menu_docs = safe_load_collection("./chroma_move_menu", "move_menu")

    # ===== 핵심: URL 기반으로 DOM 문서를 먼저 필터/정렬 =====
    preferred_paths = base_paths[:]  # 이미 base 형태(/vpes/Section)
    dom_docs = filter_and_order_docs_by_urls(dom_docs, preferred_paths)

    print("\n🧭 단계별 URL 매핑(미리보기):")
    for i, bp in enumerate(step_base_paths, start=1):
        docs_n = len(docs_for_base(dom_docs, bp))
        print(f" - STEP {i:02d}: base_path={bp or '-'} dom_count={docs_n}")


    #디버그 (최종에선 제외 예정)
    ids = [(getattr(d, "metadata", {}) or {}).get("id")
           for d in docs_for_base(dom_docs, "/vpes/ProjectModify")]
    print("in?", "projectBtn" in ids) #특정 id가 포함되었는지 확인 시


    # 9) context 구성 (단계별 URL 스코프로 쪼개서 제공)
    def _fmt(meta, key, maxlen=180):
        v = (meta.get(key) or "")
        sv = str(v)
        return (sv[:maxlen] + "…") if len(sv) > maxlen else sv

    BASE_URL_CONST = "http://localhost:38080"  # 클로저 캡쳐 안정화



    sections = []
    for i, (txt, bp) in enumerate(zip(clean_steps, step_base_paths), start=1):
        step_docs = docs_for_base(dom_docs, bp)
        frag = "\n".join([
            f"FullURL:{urljoin(BASE_URL_CONST, getattr(doc, 'metadata', {}).get('url',''))} "
            f"ID:{_fmt(getattr(doc, 'metadata', {}),'id')} "
            f"XPATH:{_fmt(getattr(doc, 'metadata', {}),'xpath')} "
            f"TEXT:{_fmt(getattr(doc, 'metadata', {}),'text', 160)} "
            f"DESC:{_fmt(getattr(doc, 'metadata', {}),'desc', 160)} "
            f"ARIA:{_fmt(getattr(doc, 'metadata', {}), 'aria-label', 160)} "
            f"PLACEHOLDER:{_fmt(getattr(doc, 'metadata', {}),'placeholder', 160)}"
            for doc in step_docs
        ])
        sections.append(f"[STEP {i} @URL:{bp or '-'}] {txt}\n{frag}")

    # LLM에 넘길 최종 context
    context = "\n\n".join(sections)

    function_context = "\n\n".join(doc.page_content[:2000] for doc in (default_docs + move_menu_docs))

    print("\n📌 context에 포함된 ID 목록(최대 60개 표시):")
    shown = 0
    for doc in dom_docs:
        mid = getattr(doc, "metadata", {}).get("id")
        if mid:
            print(f"- {mid}")
            shown += 1
            if shown >= 60:
                print("... (생략)")
                break

    # 10) LLMChain 실행
    chain = (
        RunnableMap({
            "context": lambda _: context,
            "function_context": lambda _: function_context,
            "question": lambda _: query
        })
        | prompt
        | llm
        | StrOutputParser()
    )
    generated_code = chain.invoke({})

    # 11) 클래스명/함수명 사용자 입력 값으로 변경
    generated_code = re.sub(r'class [a-zA-Z0-9_]*\(unittest\.TestCase\):', f'class {tc_name}(unittest.TestCase):', generated_code, count=1)
    generated_code = re.sub(r'def test_[a-zA-Z0-9_]*\(', f'def test_{tc_name}(', generated_code, count=1)

    # 12) 후처리/검증/가드(간단 버전 유지)
    generated_code = validate_generated_code(generated_code, dom_docs + default_docs, auto_fix=True)


    # 단계별(URL 스코프)로 셀렉터를 다시 한번 정밀 보정
    generated_code = rewrite_selectors_per_step(
        generated_code,
        dom_docs,
        clean_steps,  # URL 제거된 단계 텍스트 (parse_step_urls에서 만들어진 값)
        step_base_paths  # 각 단계에서 추출된 URL (parse_step_urls에서 만들어진 값)
    )
    # 전역 가드(허구 ID → XPATH 등)
    generated_code = enforce_known_selectors(generated_code, dom_docs, query, preferred_paths=preferred_paths)
    generated_code = postprocess_generated_code(generated_code)

    # 13) 출력 및 저장
    print("\n💻 생성된 Selenium 테스트 코드:")
    print("=" * 60)
    print(generated_code)
    print("=" * 60)

    file_name = f"{tc_name}.py"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(generated_code)
    print(f"\n✅ 코드가 '{file_name}' 파일로 저장되었습니다.")


if __name__ == "__main__":
    main()
