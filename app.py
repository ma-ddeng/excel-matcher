import streamlit as st
import pandas as pd
from itertools import combinations
import io
import re

st.set_page_config(page_title="회계 전표-통장 완전 대조기", layout="wide")

st.title("⚖️ 회계 데이터 행 단위 조합 매칭 시스템")
st.markdown("더존의 A, B열과 신한의 A, B열을 각각 독립적으로 대조하여 매칭된 행 조합을 찾아냅니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0.0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except: return 0.0

def solve_nm_matching(list_left, list_right):
    """
    N:M 매칭을 찾는 핵심 알고리즘
    list_left: [(행번호, 금액), ...]
    list_right: [(행번호, 금액), ...]
    """
    matches = []
    used_left = set()
    used_right = set()

    # 1. 1:1 매칭 먼저 빠르게 처리
    for l_idx, l_val in list_left:
        for r_idx, r_val in list_right:
            if r_idx not in used_right and abs(l_val - r_val) < 1:
                matches.append({
                    "유형": "1:1 매칭",
                    "더존_행": str(l_idx), "더존_합계": l_val,
                    "신한_행": str(r_idx), "신한_합계": r_val
                })
                used_left.add(l_idx)
                used_right.add(r_idx)
                break

    # 2. N:M 매칭 (남은 데이터들로 조합 탐색)
    # 계산 복잡도를 위해 최대 4개 조합까지만 탐색
    rem_left = [item for item in list_left if item[0] not in used_left]
    rem_right = [item for item in list_right if item[0] not in used_right]

    for r_l in range(1, 4):
        for r_r in range(1, 4):
            if r_l == 1 and r_r == 1: continue # 1:1은 위에서 함
            
            for combo_l in combinations([x for x in rem_left if x[0] not in used_left], r_l):
                sum_l = sum(c[1] for c in combo_l)
                for combo_r in combinations([x for x in rem_right if x[0] not in used_right], r_r):
                    sum_r = sum(c[1] for c in combo_r)
                    
                    if abs(sum_l - sum_r) < 1:
                        matches.append({
                            "유형": f"{r_l}:{r_r} 조합매칭",
                            "더존_행": ", ".join([str(c[0]) for c in combo_l]),
                            "더존_합계": sum_l,
                            "신한_행": ", ".join([str(c[0]) for c in combo_r]),
                            "신한_합계": sum_r
                        })
                        for c in combo_l: used_left.add(c[0])
                        for c in combo_r: used_right.add(c[0])
                        break
    
    # 미매칭 내역 정리
    unmatched_left = [{"행번호": l_idx, "금액": l_val} for l_idx, l_val in list_left if l_idx not in used_left]
    unmatched_right = [{"행번호": r_idx, "금액": r_val} for r_idx, r_val in list_right if r_idx not in used_right]
    
    return matches, unmatched_left, unmatched_right

# 파일 업로드
f_dz = st.file_uploader("📑 더존 엑셀 (A열: 입금/차변, B열: 출금/대변)", type=['xlsx', 'xls', 'csv'])
f_sh = st.file_uploader("🏦 신한 엑셀 (A열: 입금액, B열: 출금액)", type=['xlsx', 'xls', 'csv'])

if f_dz and f_sh:
    # 데이터 로드
    dz = pd.read_csv(f_dz) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz)
    sh = pd.read_csv(f_sh) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh)

    if st.button("🔍 데이터 조합 대조 시작"):
        # 1. 데이터 추출 (행번호는 엑셀 눈금 기준인 index+2)
        # 더존: A열(0), B열(1) / 신한: A열(1), B열(2) -> 샘플 구조에 맞춤
        dz_in = [(i+2, clean_money(row[1])) for i, row in dz.iterrows() if clean_money(row[1]) > 0]
        dz_out = [(i+2, clean_money(row[2])) for i, row in dz.iterrows() if clean_money(row[2]) > 0]
        
        sh_in = [(i+2, clean_money(row[1])) for i, row in sh.iterrows() if clean_money(row[1]) > 0]
        sh_out = [(i+2, clean_money(row[2])) for i, row in sh.iterrows() if clean_money(row[2]) > 0]

        # 2. 매칭 실행
        in_matches, in_un_dz, in_un_sh = solve_nm_matching(dz_in, sh_in)
        out_matches, out_un_dz, out_un_sh = solve_nm_matching(dz_out, sh_out)

        # 3. 결과 표시
        t1, t2, t3 = st.tabs(["✅ 매칭 성공 내역", "❌ 더존 미매칭", "❌ 신한 미매칭"])
        
        with t1:
            st.subheader("입금(차변) 매칭")
            df_in = pd.DataFrame(in_matches)
            st.dataframe(df_in, use_container_width=True)
            
            st.subheader("출금(대변) 매칭")
            df_out = pd.DataFrame(out_matches)
            st.dataframe(df_out, use_container_width=True)

        with t2:
            st.write("더존에서 짝을 찾지 못한 금액들입니다.")
            st.dataframe(pd.DataFrame(in_un_dz + in_un_sh), use_container_width=True)

        # 4. 엑셀 다운로드 (모든 정보 포함)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if in_matches: pd.DataFrame(in_matches).to_excel(writer, sheet_name='입금매칭_성공', index=False)
            if out_matches: pd.DataFrame(out_matches).to_excel(writer, sheet_name='출금매칭_성공', index=False)
            pd.DataFrame(in_un_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
            pd.DataFrame(in_un_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
        
        st.download_button("📥 전체 분석 결과 엑셀 다운로드", output.getvalue(), "match_report.xlsx")
