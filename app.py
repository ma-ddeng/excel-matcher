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
    # 엔진 설정을 통해 .xls와 .xlsx 모두 대응
    try:
        df_a = pd.read_excel(file_a)
        df_b = pd.read_excel(file_b)
    except Exception as e:
        st.error(f"파일을 읽는 중 에러가 발생했습니다. requirements.txt에 xlrd가 있는지 확인하세요. 에러내용: {e}")
        st.stop()

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
        # 날짜 전처리 (다양한 형식을 날짜로 변환)
        df_a[date_a] = pd.to_datetime(df_a[date_a]).dt.date
        df_b[date_b] = pd.to_datetime(df_b[date_b]).dt.date
        
        all_matches = []
        errors = []

        # 두 파일의 모든 날짜 모으기
        all_dates = sorted(list(set(df_a[date_a].dropna()) | set(df_b[date_b].dropna())))

        for target_date in all_dates:
            # 해당 날짜 데이터 필터링
            sub_a = df_a[df_a[date_a] == target_date].copy()
            sub_b = df_b[df_b[date_b] == target_date].copy()

            # --- [입금액 vs 차변] 대조 ---
            bank_in = sub_a[in_a].fillna(0).sum()
            book_debit = sub_b[debit_b].fillna(0).sum()
            
            if (bank_in > 0 or book_debit > 0):
                if bank_in == book_debit:
                    all_matches.append({
                        "날짜": target_date, "구분": "입금/차변",
                        "상태": "✅ 합계 일치", 
                        "금액": f"{bank_in:,.0f}",
                        "상세": f"통장({len(sub_a[sub_a[in_a]>0])}건) == 장부({len(sub_b[sub_b[debit_b]>0])}건)"
                    })
                else:
                    errors.append({
                        "날짜": target_date, "구분": "입금/차변 오류",
                        "통장합계": bank_in, "장부합계": book_debit, "차액": bank_in - book_debit,
                        "비고": "금액 불일치 확인 필요"
                    })

            # --- [출금액 vs 대변] 대조 ---
            bank_out = sub_a[out_a].fillna(0).sum()
            book_credit = sub_b[credit_b].fillna(0).sum()
            
            if (bank_out > 0 or book_credit > 0):
                if bank_out == book_credit:
                    all_matches.append({
                        "날짜": target_date, "구분": "출금/대변",
                        "상태": "✅ 합계 일치", 
                        "금액": f"{bank_out:,.0f}",
                        "상세": f"통장({len(sub_a[sub_a[out_a]>0])}건) == 장부({len(sub_b[sub_b[credit_b]>0])}건)"
                    })
                else:
                    errors.append({
                        "날짜": target_date, "구분": "출금/대변 오류",
                        "통장합계": bank_out, "장부합계": book_credit, "차액": bank_out - book_credit,
                        "비고": "금액 불일치 확인 필요"
                    })

        # 결과 화면 출력
        st.subheader("🔍 대조 분석 완료")
        
        tab1, tab2 = st.tabs(["✅ 정상 매칭", "❌ 불일치 오류"])
        
        with tab1:
            if all_matches:
                st.dataframe(pd.DataFrame(all_matches), use_container_width=True)
            else:
                st.write("일치하는 내역이 없습니다.")
        
        with tab2:
            if errors:
                st.dataframe(pd.DataFrame(errors), use_container_width=True)
            else:
                st.success("모든 데이터의 합계가 일치합니다!")

        # 엑셀 다운로드 파일 생성
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            if all_matches: pd.DataFrame(all_matches).to_excel(writer, sheet_name='정상매칭', index=False)
            if errors: pd.DataFrame(errors).to_excel(writer, sheet_name='오류리스트', index=False)
        
        st.download_button(
            label="📥 대조 결과 리포트 다운로드",
            data=output.getvalue(),
            file_name=f"매칭결과_{all_dates[0]}_{all_dates[-1]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
