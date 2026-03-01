import streamlit as st
import pandas as pd
from itertools import combinations
import io
import re
import time

st.set_page_config(page_title="회계 정밀 대조기", layout="wide")
st.title("⚖️ 회계 데이터 행 단위 조합 매칭")

def clean_money(val):
    try:
        if pd.isna(val): return 0.0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except: return 0.0

def solve_nm_matching(list_left, list_right, progress_text="계산 중..."):
    matches = []
    used_left = set()
    used_right = set()
    
    # 1. 1:1 매칭 (가장 빠름)
    for l_idx, l_val in list_left:
        for r_idx, r_val in list_right:
            if r_idx not in used_right and abs(l_val - r_val) < 1:
                matches.append({"유형": "1:1 매칭", "더존_행": str(l_idx), "더존_금액": l_val, "신한_행": str(r_idx), "신한_금액": r_val})
                used_left.add(l_idx)
                used_right.add(r_idx)
                break

    # 2. N:M 매칭 (조합 탐색 - 속도 제한을 위해 최대 3개까지만)
    rem_left = [x for x in list_left if x[0] not in used_left]
    rem_right = [x for x in list_right if x[0] not in used_right]
    
    total_steps = len(rem_left)
    pbar = st.progress(0, text=progress_text)

    for i, (l_idx, l_val) in enumerate(rem_left):
        if l_idx in used_left: continue
        found = False
        
        # 진행률 업데이트
        pbar.progress((i + 1) / total_steps, text=f"{progress_text} ({i+1}/{total_steps})")
        
        for r in range(1, 4): # 조합 개수를 3개로 제한하여 속도 향상
            current_right = [x for x in rem_right if x[0] not in used_right]
            for combo_r in combinations(current_right, r):
                if abs(l_val - sum(c[1] for c in combo_r)) < 1:
                    matches.append({
                        "유형": f"1:{r} 조합",
                        "더존_행": str(l_idx), "더존_금액": l_val,
                        "신한_행": ", ".join([str(c[0]) for c in combo_r]), "신한_금액": sum(c[1] for c in combo_r)
                    })
                    used_left.add(l_idx)
                    for c in combo_r: used_right.add(c[0])
                    found = True
                    break
            if found: break
            
    un_left = [{"행번호": l[0], "금액": l[1]} for l in list_left if l[0] not in used_left]
    un_right = [{"행번호": r[0], "금액": r[1]} for r in list_right if r[0] not in used_right]
    pbar.empty() # 작업 완료 후 바 제거
    return matches, un_left, un_right

f_dz = st.file_uploader("📑 더존 엑셀 (A:입금, B:출금)", type=['xlsx', 'xls', 'csv'])
f_sh = st.file_uploader("🏦 신한 엑셀 (A:입금, B:출금)", type=['xlsx', 'xls', 'csv'])

if f_dz and f_sh:
    dz = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🔍 데이터 조합 대조 시작"):
        with st.spinner('데이터를 분석하고 있습니다. 잠시만 기다려 주세요...'):
            dz_in = [(i+1, clean_money(row[0])) for i, row in dz.iterrows() if clean_money(row[0]) > 0]
            dz_out = [(i+1, clean_money(row[1])) for i, row in dz.iterrows() if clean_money(row[1]) > 0]
            sh_in = [(i+1, clean_money(row[0])) for i, row in sh.iterrows() if clean_money(row[0]) > 0]
            sh_out = [(i+1, clean_money(row[1])) for i, row in sh.iterrows() if clean_money(row[1]) > 0]

            in_match, in_un_dz, in_un_sh = solve_nm_matching(dz_in, sh_in, "입금 내역 대조 중")
            out_match, out_un_dz, out_un_sh = solve_nm_matching(dz_out, sh_out, "출금 내역 대조 중")

            st.success("✅ 분석 완료!")
            # (이하 결과 출력 및 다운로드 로직 동일)
            st.dataframe(pd.DataFrame(in_match + out_match))
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(in_match + out_match).to_excel(writer, sheet_name='매칭성공', index=False)
                pd.DataFrame(in_un_dz + out_un_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(in_un_sh + out_un_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
            st.download_button("📥 결과 엑셀 다운로드", output.getvalue(), "match_report.xlsx")
