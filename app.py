import streamlit as st
import pandas as pd
from itertools import combinations
import io
import re

st.set_page_config(page_title="회계 데이터 N:M 매칭 시스템", layout="wide")

st.title("⚖️ 회계 데이터 행 단위 조합 매칭 (최종)")
st.info("더존의 A, B열과 신한의 A, B열을 직접 대조하여 매칭된 행 조합을 찾습니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0.0
        # 숫자, 마이너스, 소수점 제외하고 모두 제거
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except: return 0.0

def solve_nm_matching(list_left, list_right):
    """
    N:M 매칭을 찾는 알고리즘 (최대 4:4 조합까지 탐색)
    """
    matches = []
    used_left = set()
    used_right = set()

    # 1. 1:1 매칭 우선 처리
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

    # 2. N:M 조합 매칭 (남은 데이터 대상)
    rem_left = [x for x in list_left if x[0] not in used_left]
    rem_right = [x for x in list_right if x[0] not in used_right]

    for r_l in range(1, 5): # 최대 4개 조합
        for r_r in range(1, 5):
            if r_l == 1 and r_r == 1: continue
            
            # 현재 미사용 중인 데이터만 추출
            current_left = [x for x in rem_left if x[0] not in used_left]
            current_right = [x for x in rem_right if x[0] not in used_right]

            for combo_l in combinations(current_left, r_l):
                sum_l = sum(c[1] for c in combo_l)
                if sum_l == 0: continue
                
                for combo_r in combinations(current_right, r_r):
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
    
    # 미매칭 내역
    un_left = [{"행번호": l[0], "금액": l[1]} for l in list_left if l[0] not in used_left]
    un_right = [{"행번호": r[0], "금액": r[1]} for r in list_right if r[0] not in used_right]
    
    return matches, un_left, un_right

# 파일 업로드
f_dz = st.file_uploader("📑 더존 엑셀 업로드", type=['xlsx', 'xls'])
f_sh = st.file_uploader("🏦 신한 엑셀 업로드", type=['xlsx', 'xls'])

if f_dz and f_sh:
    # 컬럼 이름에 의존하지 않고 위치(iloc)로 읽기 위해 header=None 고려 가능하나, 
    # 보통 첫 줄이 제목이므로 기본 로드 후 iloc 사용
    dz = pd.read_excel(f_dz)
    sh = pd.read_excel(f_sh)

    if st.button("🔍 데이터 조합 대조 시작"):
        try:
            # iloc를 사용하여 "무조건" 첫 번째 열(0)과 두 번째 열(1)을 가져옴
            # 더존 A열(차변), B열(대변) / 신한 A열(입금), B열(출금) 기준
            dz_a = [(i+2, clean_money(row[0])) for i, row in dz.iterrows() if clean_money(row[0]) > 0]
            dz_b = [(i+2, clean_money(row[1])) for i, row in dz.iterrows() if clean_money(row[1]) > 0]
            
            sh_a = [(i+2, clean_money(row[0])) for i, row in sh.iterrows() if clean_money(row[0]) > 0]
            sh_b = [(i+2, clean_money(row[1])) for i, row in sh.iterrows() if clean_money(row[1]) > 0]

            # 대조 실행 (A열끼리, B열끼리)
            match_a, un_dz_a, un_sh_a = solve_nm_matching(dz_a, sh_a)
            match_b, un_dz_b, un_sh_b = solve_nm_matching(dz_b, sh_b)

            # 결과 화면 출력
            st.subheader("📊 매칭 결과 요약")
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.success(f"A열 매칭 성공: {len(match_a)}건")
                st.dataframe(pd.DataFrame(match_a), use_container_width=True)
            with col_res2:
                st.success(f"B열 매칭 성공: {len(match_b)}건")
                st.dataframe(pd.DataFrame(match_b), use_container_width=True)

            # 미매칭 상세
            with st.expander("❌ 미매칭 내역 확인"):
                c1, c2 = st.columns(2)
                c1.write("더존 미매칭 (A열/B열)")
                c1.dataframe(pd.DataFrame(un_dz_a + un_dz_b))
                c2.write("신한 미매칭 (A열/B열)")
                c2.dataframe(pd.DataFrame(un_sh_a + un_sh_b))

            # 엑셀 다운로드 파일 생성
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(match_a).to_excel(writer, sheet_name='A열_매칭성공', index=False)
                pd.DataFrame(match_b).to_excel(writer, sheet_name='B열_매칭성공', index=False)
                pd.DataFrame(un_dz_a + un_dz_b).to_excel(writer, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(un_sh_a + un_sh_b).to_excel(writer, sheet_name='신한_미매칭', index=False)
            
            st.download_button("📥 전체 결과 엑셀 다운로드", output.getvalue(), "final_match_report.xlsx")
            
        except Exception as e:
            st.error(f"계산 중 오류가 발생했습니다: {e}")
