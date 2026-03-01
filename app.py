import streamlit as st
import pandas as pd
from itertools import combinations
import io
import re

st.set_page_config(page_title="회계 정밀 매칭 시스템", layout="wide")

st.title("⚖️ 회계 데이터 N:M 정밀 대조 시스템")
st.info("날짜별로 금액의 모든 조합을 뒤져서 '누가 누구랑 매칭됐는지' 행 번호를 추적합니다.")

# 데이터 세척 함수
def clean_money(val):
    try:
        if pd.isna(val): return 0.0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except:
        return 0.0

def find_best_matching(targets, sources):
    """
    targets: [(행번호, 금액), ...]
    sources: [(행번호, 금액), ...]
    """
    matched_results = []
    used_sources = set()
    unmatched_targets = targets[:]

    # 금액이 큰 것부터 매칭 (큰 금액 에러를 먼저 잡기 위함)
    targets_sorted = sorted(targets, key=lambda x: x[1], reverse=True)

    for t_idx, t_val in targets_sorted:
        if t_val == 0: continue
        found = False
        # 1:1부터 1:5 조합까지 탐색
        for r in range(1, 6):
            available = [s for s in sources if s not in used_sources]
            for combo in combinations(available, r):
                if abs(sum(c[1] for c in combo) - t_val) < 1: # 1원 미만 오차 허용
                    source_info = ", ".join([f"{c[0]}행({c[1]:,.0f})" for c in combo])
                    matched_results.append({
                        "상태": "✅ 매칭성공",
                        "기준_행번호": t_idx,
                        "기준_금액": t_val,
                        "대상_조합내역": source_info,
                        "대상_합계": sum(c[1] for c in combo),
                        "비고": f"{r}개 행 조합 일치"
                    })
                    for c in combo: used_sources.add(c)
                    unmatched_targets = [ut for ut in unmatched_targets if ut[0] != t_idx]
                    found = True
                    break
            if found: break
            
    unmatched_sources = [s for s in sources if s not in used_sources and s[1] != 0]
    return matched_results, unmatched_targets, unmatched_sources

# 파일 업로드
col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("🏦 엑셀 A (신한은행 등)", type=['xlsx', 'xls'])
with col2:
    file_b = st.file_uploader("📑 엑셀 B (더존 등)", type=['xlsx', 'xls'])

if file_a and file_b:
    try:
        # 데이터 로드 (첫 행 제목 무시하고 안전하게 읽기)
        df_a = pd.read_excel(file_a)
        df_b = pd.read_excel(file_b)

        if st.button("🔍 N:M 조합 매칭 분석 시작"):
            # 1. 날짜 데이터 정제 (에러 방지용 errors='coerce')
            # A열(0번째), B열(1번째) 가정
            df_a['std_date'] = pd.to_datetime(df_a.iloc[:, 0].astype(str).str.replace('.', '-').str.replace('/', '-'), errors='coerce').dt.date
            df_b['std_date'] = pd.to_datetime(df_b.iloc[:, 0].astype(str).str.replace('.', '-').str.replace('/', '-'), errors='coerce').dt.date
            
            # 2. 금액 데이터 정제
            df_a['std_amt'] = df_a.iloc[:, 1].apply(clean_money)
            df_b['std_amt'] = df_b.iloc[:, 1].apply(clean_money)

            all_match_logs = []
            all_error_logs = []

            # 두 파일의 유효한 날짜만 추출
            target_dates = sorted(list(set(df_a['std_date'].dropna()) | set(df_b['std_date'].dropna())))

            for d in target_dates:
                # 해당 날짜 데이터 추출 (엑셀 행 번호 = index + 2)
                sub_a = [(i+2, row['std_amt']) for i, row in df_a[df_a['std_date'] == d].iterrows() if row['std_amt'] != 0]
                sub_b = [(i+2, row['std_amt']) for i, row in df_b[df_b['std_date'] == d].iterrows() if row['std_amt'] != 0]

                if not sub_a and not sub_b: continue

                # 매칭 알고리즘 가동
                logs, un_a, un_b = find_best_matching(sub_a, sub_b)
                
                for l in logs:
                    l['날짜'] = d
                    all_match_logs.append(l)
                
                for ua in un_a:
                    all_error_logs.append({"날짜": d, "파일": "엑셀 A", "행번호": ua[0], "금액": ua[1], "상태": "❌ 미매칭"})
                for ub in un_b:
                    all_error_logs.append({"날짜": d, "파일": "엑셀 B", "행번호": ub[0], "금액": ub[1], "상태": "❌ 미매칭"})

            # 결과 화면
            st.subheader("✅ 상세 매칭 결과")
            if all_match_logs:
                res_df = pd.DataFrame(all_match_logs)
                st.dataframe(res_df, use_container_width=True)
            
            st.subheader("❌ 미매칭 내역 (확인 필요)")
            if all_error_logs:
                err_df = pd.DataFrame(all_error_logs)
                st.error("서로 일치하는 조합을 찾지 못한 내역입니다.")
                st.dataframe(err_df, use_container_width=True)

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                if all_match_logs: pd.DataFrame(all_match_logs).to_excel(writer, sheet_name='매칭성공', index=False)
                if all_error_logs: pd.DataFrame(all_error_logs).to_excel(writer, sheet_name='미매칭내역', index=False)
            
            st.download_button("📥 매칭 결과 보고서 다운로드", output.getvalue(), "matching_report.xlsx")

    except Exception as e:
        st.error(f"분석 중 오류 발생: {e}")
        st.info("엑셀의 A열이 날짜 형식이 맞는지, B열이 금액 형식이 맞는지 다시 한번 확인해주세요.")
