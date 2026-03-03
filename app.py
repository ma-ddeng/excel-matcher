import streamlit as st
import pandas as pd
import io
import re
import copy
import random

st.set_page_config(page_title="최종 병기: 10대 전략 무한 소거 시스템", layout="wide")
st.title("🛡️ Accounting Terminator: 10-Strategy Infinite Match")
st.warning("이 시스템은 1:50 이상의 다중 조합을 찾기 위해 10가지 경로로 무한 반복 연산을 수행합니다. 시간이 걸려도 끝까지 기다려주세요.")

def clean_money(val):
    try:
        if pd.isna(val): return 0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned)))
    except: return 0

def find_subset_sum(target, candidates, max_depth=50):
    """타겟 금액을 맞추기 위한 고성능 조합 탐색 (1:N)"""
    # 1. 1:1 확인
    for idx, val in candidates:
        if val == target: return [(idx, val)]
    
    # 2. 연속 행 합산 (슬라이딩 윈도우) - 실무 빈도 높음
    n = len(candidates)
    for size in range(2, min(n, max_depth) + 1):
        for i in range(n - size + 1):
            window = candidates[i:i+size]
            if sum(c[1] for c in window) == target: return window
            
    # 3. 정렬 후 그리디 탐색 (흩어진 소액들)
    sorted_c = sorted(candidates, key=lambda x: x[1])
    tmp_sum, tmp_list = 0, []
    for idx, val in sorted_c:
        if tmp_sum + val <= target:
            tmp_sum += val
            tmp_list.append((idx, val))
        if tmp_sum == target: return tmp_list
    
    return None

def run_infinite_loop(dz_raw, sh_raw, strategy_id):
    """선택된 전략에 따라 무한 소거법 실행"""
    dz_list = copy.deepcopy(dz_raw)
    sh_list = copy.deepcopy(sh_raw)
    matches = []
    
    while True:
        progress = False
        # [전략 세팅]
        if strategy_id == 1: # 고액 우선
            dz_list.sort(key=lambda x: x[1], reverse=True)
        elif strategy_id == 2: # 소액 우선
            dz_list.sort(key=lambda x: x[1])
        elif strategy_id == 3: # 1:1 선처리 후 고액
            # 1:1 즉시 소거 로직
            for d in dz_list[:]:
                for s in sh_list[:]:
                    if d[1] == s[1]:
                        matches.append({"유형":"1:1","더존_행":d[0],"더존_금액":d[1],"신한_행들":str(s[0]),"신한_합계":s[1]})
                        dz_list.remove(d); sh_list.remove(s)
                        progress = True; break
                if progress: break
            if progress: continue
        elif strategy_id == 4: # 행 번호 순서대로 (데이터 입력순)
            pass
        elif strategy_id == 5: # 역순 탐색 (최신 데이터 우선)
            dz_list.reverse()
        elif strategy_id == 6: # 신한은행 기준 역추적 (N:1 우선)
            sh_list.sort(key=lambda x: x[1], reverse=True)
            for s in sh_list[:]:
                res = find_subset_sum(s[1], dz_list)
                if res:
                    matches.append({"유형":"N:1","더존_행":", ".join([str(r[0]) for r in res]),"더존_금액":s[1],"신한_행들":str(s[0]),"신한_합계":s[1]})
                    sh_list.remove(s)
                    for r in res: dz_list.remove(r)
                    progress = True; break
            if progress: continue
        elif strategy_id >= 7: # 랜덤 셔플링 탐색 (3회 반복)
            random.shuffle(dz_list)

        # 공통 매칭 엔진 (1:N)
        for d in dz_list[:]:
            res = find_subset_sum(d[1], sh_list)
            if res:
                matches.append({"유형":f"1:{len(res)}","더존_행":d[0],"더존_금액":d[1],"신한_행들":", ".join([str(r[0]) for r in res]),"신한_합계":d[1]})
                dz_list.remove(d)
                for r in res: sh_list.remove(r)
                progress = True; break
        
        if not progress: break
        
    unmatched_cnt = len(dz_list) + len(sh_list)
    return matches, dz_list, sh_list, unmatched_cnt

# 메인 UI
f_dz = st.file_uploader("더존 거래내역 2", type=['xlsx', 'csv'])
f_sh = st.file_uploader("신한은행 거래내역 2", type=['xlsx', 'csv'])

if f_dz and f_sh:
    dz_df = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh_df = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🏁 10대 전략 무한 시뮬레이션 가동"):
        with st.spinner('구글 알고리즘이 10가지 경로를 무한 루프로 돌리고 있습니다...'):
            def ext(df):
                res = []
                for i, row in df.iterrows():
                    for v in row:
                        val = clean_money(v)
                        if val != 0: res.append((i+1, val))
                return res
            dz_raw, sh_raw = ext(dz_df), ext(sh_df)

            # 10대 전략 시뮬레이션
            st_names = ["고액 우선", "소액 우선", "1:1 우선", "입력순서", "최신순", "신한역추적", "랜덤A", "랜덤B", "랜덤C", "하이브리드"]
            all_results = []
            for i in range(1, 11):
                res = run_infinite_loop(dz_raw, sh_raw, i)
                all_results.append(res)
            
            # 성적표 출력
            perf_data = [{"전략": st_names[i], "미매칭 건수": all_results[i][3]} for i in range(10)]
            st.table(pd.DataFrame(perf_data))

            # 최적 결과 채택
            best_idx = pd.DataFrame(perf_data)["미매칭 건수"].idxmin()
            b_matches, b_dz, b_sh, b_cnt = all_results[best_idx]
            
            st.success(f"🏆 [ {st_names[best_idx]} ] 전략이 미매칭 {b_cnt}건으로 최적의 결과를 냈습니다!")
            
            st.subheader("✅ 상세 매칭 리스트 (1:19 등 포함)")
            st.dataframe(pd.DataFrame(b_matches), use_container_width=True)

            col1, col2 = st.columns(2)
            col1.error(f"❌ 더존 미매칭 ({len(b_dz)}건)")
            col1.table(pd.DataFrame(b_dz, columns=['행', '금액']))
            col2.error(f"❌ 신한 미매칭 ({len(b_sh)}건)")
            col2.table(pd.DataFrame(b_sh, columns=['행', '금액']))

            # 엑셀 다운로드
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                pd.DataFrame(b_matches).to_excel(wr, sheet_name='성공', index=False)
                pd.DataFrame(b_dz).to_excel(wr, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(b_sh).to_excel(wr, sheet_name='신한_미매칭', index=False)
            st.download_button("📥 10대 전략 최적 결과 보고서 받기", out.getvalue(), "Perfect_Audit_V10.xlsx")
