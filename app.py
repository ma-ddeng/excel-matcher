import streamlit as st
import pandas as pd
from itertools import combinations
import io
import re

st.set_page_config(page_title="회계 정밀 대조기", layout="wide")

st.title("⚖️ 회계 데이터 행 단위 조합 매칭 (최종)")

# 금액 정제 함수
def clean_money(val):
    try:
        if pd.isna(val): return 0.0
        # 숫자, 마이너스, 소수점 외 모든 문자 제거
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except:
        return 0.0

# N:M 매칭 알고리즘
def solve_nm_matching(list_left, list_right):
    matches = []
    used_left = set()
    used_right = set()

    # 1. 1:1 매칭 우선
    for l_idx, l_val in list_left:
        for r_idx, r_val in list_right:
            if r_idx not in used_right and abs(l_val - r_val) < 1:
                matches.append({
                    "유형": "1:1 매칭",
                    "더존_행": str(l_idx), "더존_금액": l_val,
                    "신한_행": str(r_idx), "신한_금액": r_val
                })
                used_left.add(l_idx)
                used_right.add(r_idx)
                break

    # 2. 조합 매칭 (최대 4개 행 조합)
    for r_l in range(1, 5):
        for r_r in range(1, 5):
            if r_l == 1 and r_r == 1: continue
            
            curr_left = [x for x in list_left if x[0] not in used_left]
            curr_right = [x for x in list_right if x[0] not in used_right]

            for combo_l in combinations(curr_left, r_l):
                sum_l = sum(c[1] for c in combo_l)
                if sum_l == 0: continue
                for combo_r in combinations(curr_right, r_r):
                    sum_r = sum(c[1] for c in combo_r)
                    if abs(sum_l - sum_r) < 1:
                        matches.append({
                            "유형": f"{r_l}:{r_r} 조합",
                            "더존_행": ", ".join([str(c[0]) for c in combo_l]),
                            "더존_금액": sum_l,
                            "신한_행": ", ".join([str(c[0]) for c in combo_r]),
                            "신한_금액": sum_r
                        })
                        for c in combo_l: used_left.add(c[0])
                        for c in combo_r: used_right.add(c[0])
                        break
    
    un_left = [{"행번호": l[0], "금액": l[1]} for l in list_left if l[0] not in used_left]
    un_right = [{"행번호": r[0], "금액": r[1]} for r in list_right if r[0] not in used_right]
    
    return matches, un_left, un_right

# 파일 업로드
f_dz = st.file_uploader("📑 더존 엑셀 (A:입금, B:출금)", type=['xlsx', 'xls', 'csv'])
f_sh = st.file_uploader("🏦 신한 엑셀 (A:입금, B:출금)", type=['xlsx', 'xls', 'csv'])

if f_dz and f_sh:
    # 어떤 형식이든 무조건 제목 없는 상태로 로드 (인덱스 접근을 위해)
    dz = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🔍 데이터 조합 대조 시작"):
        try:
            # 0번째 열(A), 1번째 열(B)에서 금액 추출 (헤더가 있어도 clean_money가 0처리함)
            # 행 번호는 눈금 그대로 (index+1)
            dz_in = [(i+1, clean_money(row[0])) for i, row in dz.iterrows() if clean_money(row[0]) > 0]
            dz_out = [(i+1, clean_money(row[1])) for i, row in dz.iterrows() if clean_money(row[1]) > 0]
            
            sh_in = [(i+1, clean_money(row[0])) for i, row in sh.iterrows() if clean_money(row[0]) > 0]
            sh_out = [(i+1, clean_money(row[1])) for i, row in sh.iterrows() if clean_money(row[1]) > 0]

            # 대조 실행
            in_match, in_un_dz, in_un_sh = solve_nm_matching(dz_in, sh_in)
            out_match, out_un_dz, out_un_sh = solve_nm_matching(dz_out, sh_out)

            # 결과 리포트 생성
            st.success("✅ 대조 완료!")
            
            t1, t2 = st.tabs(["매칭 성공 내역", "미매칭(불일치)"])
            with t1:
                st.write("### 입금 매칭 (더존 A ↔ 신한 A)")
                st.dataframe(pd.DataFrame(in_match), use_container_width=True)
                st.write("### 출금 매칭 (더존 B ↔ 신한 B)")
                st.dataframe(pd.DataFrame(out_match), use_container_width=True)
            
            with t2:
                st.warning("어떤 조합으로도 맞지 않는 금액들입니다.")
                col_e1, col_e2 = st.columns(2)
                col_e1.write("더존 미매칭")
                col_e1.dataframe(pd.DataFrame(in_un_dz + out_un_dz))
                col_e2.write("신한 미매칭")
                col_e2.dataframe(pd.DataFrame(in_un_sh + out_un_sh))

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(in_match + out_match).to_excel(writer, sheet_name='매칭성공', index=False)
                pd.DataFrame(in_un_dz + out_un_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(in_un_sh + out_un_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
            
            st.download_button("📥 결과 엑셀 다운로드", output.getvalue(), "match_report.xlsx")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
