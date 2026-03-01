import streamlit as st
import pandas as pd
from itertools import combinations

st.set_page_config(page_title="엑셀 금액 매칭 프로", layout="wide")
st.title("⚖️ 스마트 금액 매칭 시스템")
st.write("A파일의 금액이 B파일의 여러 금액 합과 일치하는지 찾아냅니다.")

# 파일 업로드
col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("기준 파일 업로드 (A)", type=['xlsx'])
with col2:
    file_b = st.file_uploader("대상 파일 업로드 (B)", type=['xlsx'])

if file_a and file_b:
    df_a = pd.read_excel(file_a)
    df_b = pd.read_excel(file_b)
    
    st.sidebar.header("설정")
    col_a = st.sidebar.selectbox("A파일 금액 컬럼", df_a.columns)
    col_b = st.sidebar.selectbox("B파일 금액 컬럼", df_b.columns)

    if st.button("매칭 분석 시작"):
        # 인덱스(행 번호) 보존을 위해 복사
        list_a = df_a[col_a].dropna().to_list()
        list_b = df_b[col_b].dropna().to_list()
        
        matched_results = []
        unmatched_a = list_a.copy()
        unmatched_b = list_b.copy()

        # 1. 간단한 1:1 매칭 먼저 제거
        for val in list_a:
            if val in unmatched_b:
                matched_results.append(f"✅ [1:1 매칭] A의 {val}원 ↔ B의 {val}원")
                unmatched_a.remove(val)
                unmatched_b.remove(val)

        # 2. 1:N 매칭 (A의 한 값이 B의 여러 값 합계와 같은지 확인)
        # ※ 성능을 위해 최대 5개 조합까지만 탐색
        for target in unmatched_a[:]:
            found = False
            for r in range(2, 6): 
                for combo in combinations(unmatched_b, r):
                    if sum(combo) == target:
                        matched_results.append(f"🔗 [1:N 매칭] A의 {target}원 ↔ B의 {combo} 조합")
                        unmatched_a.remove(target)
                        for item in combo:
                            unmatched_b.remove(item)
                        found = True
                        break
                if found: break

        # 결과 출력
        st.subheader("📊 분석 결과")
        res_col1, res_col2 = st.columns(2)
        
        with res_col1:
            st.success(f"매칭 성공: {len(matched_results)}건")
            for res in matched_results:
                st.write(res)
        
        with res_col2:
            st.error("⚠️ 매칭 실패 (남은 금액)")
            st.write("A파일 미매칭:", unmatched_a)
            st.write("B파일 미매칭:", unmatched_b)