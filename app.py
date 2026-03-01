import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="회계-통장 끝판왕 대조기", layout="wide")

st.title("⚖️ 회계 데이터 스마트 대조기 (오류 방지 버전)")
st.info("날짜 형식(./)이나 금액의 콤마(,)에 상관없이 당일 합계를 완벽하게 비교합니다.")

# --- 유틸리티 함수: 데이터 세척 ---

def clean_date(date_val):
    """어떤 날짜 형식이든 YYYY-MM-DD 형태의 날짜 객체로 변환"""
    try:
        if pd.isna(date_val): return None
        # 점(.)을 슬래시(/)나 대시(-)로 바꿔서 인식률 높임
        date_str = str(date_val).replace('.', '-').replace('/', '-')
        # 시간 정보가 포함되어 있다면 날짜만 추출
        return pd.to_datetime(date_str).date()
    except:
        return None

def clean_money(money_val):
    """금액 열의 콤마, 문자 등을 제거하고 순수 숫자로 변환"""
    try:
        if pd.isna(money_val) or money_val == "": return 0.0
        if isinstance(money_val, (int, float)): return float(money_val)
        # 숫자가 아닌 것(콤마 등)은 제거
        cleaned = re.sub(r'[^\d.-]', '', str(money_val))
        return float(cleaned) if cleaned else 0.0
    except:
        return 0.0

# --- 파일 업로드 섹션 ---

col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("🏦 통장 내역 업로드 (신한은행 등)", type=['xlsx', 'xls'])
with col2:
    file_b = st.file_uploader("📑 회계 장부 업로드 (더존 등)", type=['xlsx', 'xls'])

if file_a and file_b:
    try:
        # 파일 읽기
        df_a = pd.read_excel(file_a)
        df_b = pd.read_excel(file_b)
        
        st.success("파일 로드 완료! 아래에서 컬럼을 확인하고 매칭을 시작하세요.")
        
        # 컬럼 선택 가이드 (사이드바)
        st.sidebar.header("📍 컬럼 지정")
        
        with st.sidebar.expander("통장 파일(A) 컬럼"):
            date_col_a = st.selectbox("날짜(거래일시)", df_a.columns, key='da')
            in_col_a = st.selectbox("입금액", df_a.columns, key='ia')
            out_col_a = st.selectbox("출금액", df_a.columns, key='oa')

        with st.sidebar.expander("회계 장부(B) 컬럼"):
            date_col_b = st.selectbox("날짜(전표일자)", df_b.columns, key='db')
            debit_col_b = st.selectbox("차변(입금)", df_b.columns, key='deb')
            credit_col_b = st.selectbox("대변(출금)", df_b.columns, key='cre')

        if st.button("🔍 데이터 정밀 대조 시작"):
            # 1. 데이터 세척 (핵심 로직)
            # 날짜 통일
            df_a['clean_date'] = df_a[date_col_a].apply(clean_date)
            df_b['clean_date'] = df_b[date_col_b].apply(clean_date)
            
            # 금액 숫자화
            df_a['clean_in'] = df_a[in_col_a].apply(clean_money)
            df_a['clean_out'] = df_a[out_a_col] if 'out_a_col' in locals() else df_a[out_col_a].apply(clean_money)
            df_b['clean_debit'] = df_b[debit_col_b].apply(clean_money)
            df_b['clean_credit'] = df_b[credit_col_b].apply(clean_money)

            # 2. 날짜별 그룹화 합계 계산
            # 통장 날짜별 합계
            grp_a = df_a.groupby('clean_date').agg({'clean_in':'sum', 'clean_out':'sum'}).reset_index()
            # 장부 날짜별 합계
            grp_b = df_b.groupby('clean_date').agg({'clean_debit':'sum', 'clean_credit':'sum'}).reset_index()

            # 3. 날짜 기준으로 두 데이터 합치기 (Outer Join)
            total_dates = sorted(list(set(grp_a['clean_date'].dropna()) | set(grp_b['clean_date'].dropna())))
            comparison_results = []
            
            for d in total_dates:
                row_a = grp_a[grp_a['clean_date'] == d]
                row_b = grp_b[grp_b['clean_date'] == d]
                
                a_in = row_a['clean_in'].values[0] if not row_a.empty else 0
                a_out = row_a['clean_out'].values[0] if not row_a.empty else 0
                b_in = row_b['clean_debit'].values[0] if not row_b.empty else 0
                b_out = row_b['clean_credit'].values[0] if not row_b.empty else 0
                
                # 입금 매칭 여부
                in_status = "✅ 일치" if a_in == b_in else "❌ 불일치"
                # 출금 매칭 여부
                out_status = "✅ 일치" if a_out == b_out else "❌ 불일치"
                
                if a_in > 0 or b_in > 0:
                    comparison_results.append({
                        "날짜": d, "구분": "입금(차변)", 
                        "통장금액": a_in, "장부금액": b_in, "차액": a_in - b_in, "결과": in_status
                    })
                if a_out > 0 or b_out > 0:
                    comparison_results.append({
                        "날짜": d, "구분": "출금(대변)", 
                        "통장금액": a_out, "장부금액": b_out, "차액": a_out - b_out, "결과": out_status
                    })

            # 4. 결과 출력
            res_df = pd.DataFrame(comparison_results)
            
            st.subheader("📊 대조 리포트")
            if not res_df.empty:
                # 결과 테이블 스타일링
                def highlight_error(s):
                    return ['background-color: #ffcccc' if v == "❌ 불일치" else '' for v in s]
                
                st.dataframe(res_df.style.apply(highlight_error, subset=['결과']), use_container_width=True)
                
                # 엑셀 다운로드
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    res_df.to_excel(writer, index=False, sheet_name='대조결과')
                st.download_button("📥 대조 결과 엑셀 다운로드", output.getvalue(), "reconciliation_result.xlsx")
            else:
                st.warning("분석할 수 있는 데이터가 없습니다.")

    except Exception as e:
        st.error(f"프로그램 실행 중 예상치 못한 오류가 발생했습니다: {e}")
        st.info("사이드바에서 날짜와 금액 컬럼을 정확히 선택했는지 확인해주세요.")
