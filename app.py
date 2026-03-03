import streamlit as st
import pandas as pd
import io
import re
import copy
import random

# [디자인] 페이지 설정 및 고급스러운 테마 적용
st.set_page_config(page_title="하이컨시 회계 매칭 시스템", layout="wide")

# 고유한 스타일 시트 적용 (고급스러운 폰트와 여백)
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #1E1E1E;
        color: white;
        font-weight: bold;
        border: None;
    }
    .stButton>button:hover {
        background-color: #3D3D3D;
        color: #00FFC8;
    }
    .report-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    h1 {
        color: #1E1E1E;
        font-family: 'Pretendard', sans-serif;
        font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)

# 사이드바: 사용 방법 안내 (예쁘고 간결하게)
with st.sidebar:
    st.markdown("### 💡 사용 방법")
    st.info("""
    **1. 데이터 준비**
    각 엑셀 파일의 **A열**에 매칭할 
    **금액**만 정확히 기재해 주세요.
    
    **2. 파일 업로드**
    아래의 업로드 함에 
    [더존]과 [신한은행] 파일을 
    각각 넣어주세요.
    
    **3. 엔진 가동**
    '최적화 매칭 시작' 버튼을 누르면
    10대 전략이 무한 반복 계산을 
    시작합니다.
    """)
    st.write("---")
    st.caption("High-Currency Accounting System v1.0")

# 메인 타이틀
st.title("🛰️ 하이컨시 회계 매칭 시스템")
st.markdown("##### *10대 전략 기반 무한 추적 및 최적 시나리오 도출 엔진*")
st.write("")

# [로직 시작] - 선생님의 '최적 로직' 보존
def clean_money(val):
    try:
        if pd.isna(val): return 0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned)))
    except: return 0

def find_subset_sum(target, candidates, max_depth=50):
    for idx, val in candidates:
        if val == target: return [(idx, val)]
    n = len(candidates)
    for size in range(2, min(n, max_depth) + 1):
        for i in range(n - size + 1):
            window = candidates[i:i+size]
            if sum(c[1] for c in window) == target: return window
    sorted_c = sorted(candidates, key=lambda x: x[1])
    tmp_sum, tmp_list = 0, []
    for idx, val in sorted_c:
        if tmp_sum + val <= target:
            tmp_sum += val
            tmp_list.append((idx, val))
        if tmp_sum == target: return tmp_list
    return None

def run_infinite_loop(dz_raw, sh_raw, strategy_id):
    dz_list = copy.deepcopy(dz_raw)
    sh_list = copy.deepcopy(sh_raw)
    matches = []
    while True:
        progress = False
        if strategy_id == 1: dz_list.sort(key=lambda x: x[1], reverse=True)
        elif strategy_id == 2: dz_list.sort(key=lambda x: x[1])
        elif strategy_id == 3:
            for d in dz_list[:]:
                for s in sh_list[:]:
                    if d[1] == s[1]:
                        matches.append({"유형":"1:1","더존_행":d[0],"더존_금액":d[1],"신한은행_행들":str(s[0]),"신한은행_합계":s[1]})
                        dz_list.remove(d); sh_list.remove(s)
                        progress = True; break
                if progress: break
            if progress: continue
        elif strategy_id == 4: pass
        elif strategy_id == 5: dz_list.reverse()
        elif strategy_id == 6:
            sh_list.sort(key=lambda x: x[1], reverse=True)
            for s in sh_list[:]:
                res = find_subset_sum(s[1], dz_list)
                if res:
                    matches.append({"유형":"N:1","더존_행":", ".join([str(r[0]) for r in res]),"더존_금액":s[1],"신한은행_행들":str(s[0]),"신한은행_합계":s[1]})
                    sh_list.remove(s)
                    for r in res: dz_list.remove(r)
                    progress = True; break
            if progress: continue
        elif strategy_id >= 7: random.shuffle(dz_list)

        for d in dz_list[:]:
            res = find_subset_sum(d[1], sh_list)
            if res:
                matches.append({"유형":f"1:{len(res)}","더존_행":d[0],"더존_금액":d[1],"신한은행_행들":", ".join([str(r[0]) for r in res]),"신한은행_합계":d[1]})
                dz_list.remove(d)
                for r in res: sh_list.remove(r)
                progress = True; break
        if not progress: break
    unmatched_cnt = len(dz_list) + len(sh_list)
    return matches, dz_list, sh_list, unmatched_cnt

# 파일 업로드 섹션
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("### 📑 더존")
    f_dz = st.file_uploader("더존 파일을 업로드하세요", type=['xlsx', 'csv'], label_visibility="collapsed")
with col_b:
    st.markdown("### 🏦 신한은행")
    f_sh = st.file_uploader("신한은행 파일을 업로드하세요", type=['xlsx', 'csv'], label_visibility="collapsed")

if f_dz and f_sh:
    dz_df = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh_df = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    st.write("")
    if st.button("🏁 하이컨시 최적화 매칭 엔진 가동"):
        with st.spinner('최적의 조합을 찾기 위해 시뮬레이션 중입니다...'):
            def ext(df):
                res = []
                for i, row in df.iterrows():
                    for v in row:
                        val = clean_money(v)
                        if val != 0: res.append((i+1, val))
                return res
            dz_raw, sh_raw = ext(dz_df), ext(sh_df)

            st_names = ["고액 우선", "소액 우선", "1:1 우선", "입력순서", "최신순", "신한역추적", "랜덤 시나리오 A", "랜덤 시나리오 B", "랜덤 시나리오 C", "하이브리드 엔진"]
            all_results = []
            for i in range(1, 11):
                res = run_infinite_loop(dz_raw, sh_raw, i)
                all_results.append(res)
            
            perf_data = [{"전략": st_names[i], "미매칭 건수": all_results[i][3]} for i in range(10)]
            
            # 성적표 시각화 (깔끔한 디자인)
            st.markdown("#### 📊 전략별 시뮬레이션 성적")
            st.table(pd.DataFrame(perf_data))

            best_idx = pd.DataFrame(perf_data)["미매칭 건수"].idxmin()
            b_matches, b_dz, b_sh, b_cnt = all_results[best_idx]
            
            st.success(f"🏆 선정된 최적 전략: **[ {st_names[best_idx]} ]** - 잔여 미매칭 {b_cnt}건")
            
            # 매칭 결과 테이블
            st.markdown("#### ✅ 최종 매칭 성공 내역")
            st.dataframe(pd.DataFrame(b_matches), use_container_width=True)

            # 미매칭 상세 정보
            c1, c2 = st.columns(2)
            with c1:
                st.error(f"❌ 더존 미매칭 ({len(b_dz)}건)")
                st.dataframe(pd.DataFrame(b_dz, columns=['행번호', '금액']), use_container_width=True)
            with c2:
                st.error(f"❌ 신한은행 미매칭 ({len(b_sh)}건)")
                st.dataframe(pd.DataFrame(b_sh, columns=['행번호', '금액']), use_container_width=True)

            # 엑셀 다운로드
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                pd.DataFrame(b_matches).to_excel(wr, sheet_name='매칭_성공', index=False)
                pd.DataFrame(b_dz).to_excel(wr, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(b_sh).to_excel(wr, sheet_name='신한은행_미매칭', index=False)
            
            st.write("")
            st.download_button("📥 최종 완결 보고서 다운로드 (.xlsx)", out.getvalue(), "High_Currency_Match_Report.xlsx")
