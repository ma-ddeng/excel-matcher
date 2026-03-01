import streamlit as st
import pandas as pd
from itertools import combinations
import io

st.set_page_config(page_title="회계 전표-통장 매칭 시스템", layout="wide")

st.title("📂 회계 데이터 스마트 대조기 (N:M 대응)")
st.info("날짜별로 입금(차변)과 출금(대변)의 합계를 대조하여 매칭 조합을 찾습니다.")

# 1. 파일 업로드
col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("🏦 통장 거래내역 (신한은행 등)", type=['xlsx', 'xls'])
with col2:
    file_b = st.file_uploader("📑 회계 장부 (더존 등)", type=['xlsx', 'xls'])

if file_a and file_b:
    df_a = pd.read_excel(file_a)
    df_b = pd.read_excel(file_b)

    st.sidebar.header("⚙️ 컬럼 설정")
    
    # 통장 파일 컬럼 설정
    st.sidebar.subheader("통장 파일 설정")
    date_a = st.sidebar.selectbox("날짜 열 (A)", df_a.columns, key='da')
    in_a = st.sidebar.selectbox("입금액 열 (B)", df_a.columns, key='ia')
    out_a = st.sidebar.selectbox("출금액 열 (C)", df_a.columns, key='oa')

    # 회계 파일 컬럼 설정
    st.sidebar.subheader("회계 파일 설정")
    date_b = st.sidebar.selectbox("날짜 열 (A)", df_b.columns, key='db')
    debit_b = st.sidebar.selectbox("차변(입금) 열 (B)", df_b.columns, key='deb')
    credit_b = st.sidebar.selectbox("대변(출금) 열 (C)", df_b.columns, key='cre')

    if st.button("🚀 데이터 대조 분석 시작"):
        # 전처리: 날짜 형식 통일 및 데이터 정리
        df_a[date_a] = pd.to_datetime(df_a[date_a]).dt.date
        df_b[date_b] = pd.to_datetime(df_b[date_b]).dt.date
        
        all_matches = []
        errors = []

        # 모든 유니크한 날짜 추출
        all_dates = sorted(list(set(df_a[date_a]) | set(df_b[date_b])))

        for target_date in all_dates:
            # 해당 날짜 데이터 필터링
            sub_a = df_a[df_a[date_a] == target_date].copy()
            sub_b = df_b[df_b[date_b] == target_date].copy()

            # --- 입금(차변) 대조 ---
            vals_a = sub_a[in_a].fillna(0).tolist()
            vals_b = sub_b[debit_b].fillna(0).tolist()
            
            sum_a = sum(vals_a)
            sum_b = sum(vals_b)

            if sum_a == sum_b and sum_a > 0:
                all_matches.append({
                    "날짜": target_date, "구분": "입금/차변",
                    "상태": "✅ 합계 일치", 
                    "내용": f"통장({len(vals_a)}건) 합계 {sum_a:,.0f} == 장부({len(vals_b)}건) 합계 {sum_b:,.0f}"
                })
            elif sum_a != sum_b:
                errors.append({
                    "날짜": target_date, "구분": "입금/차변 오류",
                    "통장합계": sum_a, "장부합계": sum_b, "차액": sum_a - sum_b,
                    "비고": "휴먼에러 의심 (금액 불일치)"
                })

            # --- 출금(대변) 대조 ---
            vals_a_out = sub_a[out_a].fillna(0).tolist()
            vals_b_out = sub_b[credit_b].fillna(0).tolist()
            
            sum_a_out = sum(vals_a_out)
            sum_b_out = sum(vals_b_out)

            if sum_a_out == sum_b_out and sum_a_out > 0:
                all_matches.append({
                    "날짜": target_date, "구분": "출금/대변",
                    "상태": "✅ 합계 일치", 
                    "내용": f"통장({len(vals_a_out)}건) 합계 {sum_a_out:,.0f} == 장부({len(vals_b_out)}건) 합계 {sum_b_out:,.0f}"
                })
            elif sum_a_out != sum_b_out:
                errors.append({
                    "날짜": target_date, "구분": "출금/대변 오류",
                    "통장합계": sum_a_out, "장부합계": sum_b_out, "차액": sum_a_out - sum_b_out,
                    "비고": "내역 누락 또는 금액 오기입"
                })

        # 결과 표시
        st.subheader("🔍 대조 결과 요약")
        res_col, err_col = st.columns(2)
        
        with res_col:
            st.success(f"정상 매칭: {len(all_matches)}건")
            st.dataframe(pd.DataFrame(all_matches))
        
        with err_col:
            st.error(f"불일치 오류: {len(errors)}건")
            df_errors = pd.DataFrame(errors)
            st.dataframe(df_errors)

        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if all_matches: pd.DataFrame(all_matches).to_excel(writer, sheet_name='정상매칭', index=False)
            if errors: df_errors.to_excel(writer, sheet_name='오류리스트', index=False)
        
        st.download_button(
            label="📥 대조 결과 리포트 다운로드",
            data=output.getvalue(),
            file_name=f"reconciliation_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
