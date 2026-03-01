import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="무한 추적 회계 감사 시스템", layout="wide")
st.title("♾️ Infinite Trace: 끝장 매칭 엔진")
st.info("매칭이 안 되는 숫자가 없을 때까지 반복해서 계산합니다. (1:1 ~ 1:50 전수조사)")

def clean_money(val):
    try:
        if pd.isna(val): return 0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned)))
    except: return 0

def find_best_combination(target, candidates, max_depth=50):
    """
    타겟 금액을 만들기 위해 후보군에서 최적의 조합을 찾는 핵심 엔진
    """
    # 1. 단일 매칭 (1:1)
    for i, (idx, val) in enumerate(candidates):
        if val == target:
            return [(idx, val)]

    # 2. 연속된 행 합산 (1:N) - 실무 데이터에서 가장 많음
    n = len(candidates)
    for size in range(2, min(n, max_depth) + 1):
        for i in range(n - size + 1):
            window = candidates[i:i+size]
            if sum(c[1] for c in window) == target:
                return window

    # 3. 비연속 그리디 탐색 (정렬 후 작은 조각 모으기)
    sorted_cand = sorted(candidates, key=lambda x: x[1])
    temp_sum = 0
    temp_list = []
    for idx, val in sorted_cand:
        if temp_sum + val <= target:
            temp_sum += val
            temp_list.append((idx, val))
        if temp_sum == target:
            return temp_list
            
    return None

def iterative_matching_engine(dz_list, sh_list):
    """
    매칭되는 건이 더 이상 안 나올 때까지 무한 반복하는 엔진
    """
    all_matched_logs = []
    
    while True:
        initial_match_count = len(all_matched_logs)
        
        # 더존 리스트를 큰 금액순으로 정렬해서 타겟팅
        dz_list.sort(key=lambda x: x[1], reverse=True)
        
        temp_dz_list = []
        used_dz_indices = set()
        used_sh_indices = set()

        for d_idx, d_val in dz_list:
            if d_val == 0: continue
            
            # 현재 가용한 신한 풀
            available_sh = [s for s in sh_list if s[0] not in used_sh_indices]
            result = find_best_combination(d_val, available_sh)
            
            if result:
                sh_ids = [str(r[0]) for r in result]
                all_matched_logs.append({
                    "회차": f"{len(all_matched_logs)+1}차 탐색",
                    "유형": f"복합({len(result)}개 조합)",
                    "더존_행": d_idx,
                    "더존_금액": d_val,
                    "신한_행들": ", ".join(sh_ids),
                    "신한_합계": sum(r[1] for r in result)
                })
                used_dz_indices.add(d_idx)
                for r_idx, r_val in result:
                    used_sh_indices.add(r_idx)
        
        # 사용된 데이터 제거 후 리스트 업데이트
        dz_list = [d for d in dz_list if d[0] not in used_dz_indices]
        sh_list = [s for s in sh_list if s[0] not in used_sh_indices]

        # 이번 회차에서 새로 매칭된 게 없다면 종료
        if len(all_matched_logs) == initial_match_count:
            # 역방향으로도 한 번 더 시도 (신한의 한 값이 더존의 여러개 합인지)
            sh_list.sort(key=lambda x: x[1], reverse=True)
            for s_idx, s_val in sh_list:
                res_rev = find_best_combination(s_val, dz_list)
                if res_rev:
                    dz_ids = [str(r[0]) for r in res_rev]
                    all_matched_logs.append({
                        "회차": "역방향 탐색",
                        "유형": f"역방향({len(res_rev)}개 조합)",
                        "더존_행": ", ".join(dz_ids),
                        "더존_금액": sum(r[1] for r in res_rev),
                        "신한_행들": s_idx,
                        "신한_합계": s_val
                    })
                    used_dz_rev = [r[0] for r in res_rev]
                    dz_list = [d for d in dz_list if d[0] not in used_dz_rev]
                    sh_list = [s for s in sh_list if s[0] != s_idx]
                    break # 한 건 찾으면 다시 while 루프 처음으로
            else:
                break # 진짜 더 이상 매칭될 게 없으면 무한루프 탈출
                
    return all_matched_logs, dz_list, sh_list

f_dz = st.file_uploader("더존 데이터 업로드", type=['xlsx', 'csv'])
f_sh = st.file_uploader("신한 데이터 업로드", type=['xlsx', 'csv'])

if f_dz and f_sh:
    dz_df = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh_df = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🔥 끝장 추적 매칭 시작 (전수 반복)"):
        with st.spinner('모든 숫자의 짝을 찾을 때까지 무한 반복 중...'):
            def extract_data(df):
                res = []
                for i, row in df.iterrows():
                    for v in row:
                        val = clean_money(v)
                        if val != 0: res.append((i+1, val))
                return res

            dz_raw = extract_data(dz_df)
            sh_raw = extract_data(sh_df)

            matches, final_dz, final_sh = iterative_matching_engine(dz_raw, sh_raw)

            st.success(f"🎯 최종 매칭 완료! (총 {len(matches)}개 조합 발견)")
            
            if matches:
                st.dataframe(pd.DataFrame(matches), use_container_width=True)

            c1, c2 = st.columns(2)
            c1.error(f"❌ 최종 미매칭 더존: {len(final_dz)}건")
            c1.dataframe(pd.DataFrame(final_dz, columns=['행번호', '금액']))
            c2.error(f"❌ 최종 미매칭 신한: {len(final_sh)}건")
            c2.dataframe(pd.DataFrame(final_sh, columns=['행번호', '금액']))

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(matches).to_excel(writer, sheet_name='매칭_성공_내역', index=False)
                pd.DataFrame(final_dz).to_excel(writer, sheet_name='더존_미매칭_최종', index=False)
                pd.DataFrame(final_sh).to_excel(writer, sheet_name='신한_미매칭_최종', index=False)
            st.download_button("📥 최종 완결 보고서 다운로드", output.getvalue(), "Infinite_Audit_Report.xlsx")
