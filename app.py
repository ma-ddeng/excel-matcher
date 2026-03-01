import streamlit as st
import pandas as pd
from itertools import combinations
import io

st.set_page_config(page_title="회계 정밀 매칭 시스템", layout="wide")

st.title("⚖️ 회계 데이터 정밀 대조 및 추적 시스템")
st.markdown("날짜별로 입금/출금의 **행 조합(N:M)**을 찾아내고 매칭 내역을 상세히 기록합니다.")

# 1. 파일 업로드
col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("🏦 신한은행 거래내역 (A)", type=['xlsx', 'xls', 'csv'])
with col2:
    file_b = st.file_uploader("📑 더존 거래내역 (B)", type=['xlsx', 'xls', 'csv'])

def find_subset_sum(targets, sources, max_r=5):
    """
    targets: 대상 금액 리스트 [(행번호, 금액), ...]
    sources: 조합할 소스 리스트 [(행번호, 금액), ...]
    """
    matched_log = []
    used_sources = set()
    remaining_targets = targets[:]

    for t_idx, t_val in targets:
        found = False
        # 1:1부터 1:N까지 탐색
        for r in range(1, max_r + 1):
            available_sources = [s for s in sources if s not in used_sources]
            for combo in combinations(available_sources, r):
                if abs(sum(c[1] for c in combo) - t_val) < 1: # 오차범위 1원 미만
                    source_rows = [str(c[0]) for c in combo]
                    matched_log.append({
                        "결과": "✅ 매칭성공",
                        "기준_행": t_idx,
                        "기준_금액": t_val,
                        "대상_조합행": ", ".join(source_rows),
                        "대상_합계금액": sum(c[1] for c in combo),
                        "비고": f"{r}개 행 조합 일치"
                    })
                    for c in combo: used_sources.add(c)
                    remaining_targets = [rt for rt in remaining_targets if rt[0] != t_idx]
                    found = True
                    break
            if found: break
    
    # 매칭 안 된 남은 것들 기록
    unmatched_sources = [s for s in sources if s not in used_sources]
    return matched_log, remaining_targets, unmatched_sources

if file_a and file_b:
    # 데이터 로드
    df_a = pd.read_csv(file_a) if file_a.name.endswith('.csv') else pd.read_excel(file_a)
    df_b = pd.read_csv(file_b) if file_b.name.endswith('.csv') else pd.read_excel(file_b)

    # 날짜 처리 (A: 거래일시, B: 날짜)
    df_a['std_date'] = pd.to_datetime(df_a.iloc[:, 0].astype(str).str[:10].str.replace('.', '-')).dt.date
    df_b['std_date'] = pd.to_datetime(df_b.iloc[:, 0].astype(str).str[:10].str.replace('/', '-')).dt.date

    # 분석 버튼
    if st.button("🔍 행 단위 정밀 대조 시작"):
        all_logs = []
        all_unmatched = []
        
        target_dates = sorted(list(set(df_a['std_date'].dropna()) | set(df_b['std_date'].dropna())))

        for d in target_dates:
            # 해당 날짜 데이터 추출 (행 번호 보존을 위해 index+2 사용)
            sub_a = df_a[df_a['std_date'] == d]
            sub_b = df_b[df_b['std_date'] == d]

            # --- 입금(A) vs 차변(B) ---
            # A의 입금액(2번째 열), B의 차변(2번째 열)
            list_a_in = [(i+2, row[1]) for i, row in sub_a.iterrows() if row[1] > 0]
            list_b_in = [(i+2, row[1]) for i, row in sub_b.iterrows() if row[1] > 0]
            
            log, rem_a, rem_b = find_subset_sum(list_a_in, list_b_in)
            for l in log: 
                l['날짜'] = d
                l['구분'] = "입금(차변)"
                all_logs.append(l)
            
            # --- 출금(A) vs 대변(B) ---
            # A의 출금액(3번째 열), B의 대변(3번째 열)
            list_a_out = [(i+2, row[2]) for i, row in sub_a.iterrows() if row[2] > 0]
            list_b_out = [(i+2, row[2]) for i, row in sub_b.iterrows() if row[2] > 0]
            
            log_out, rem_a_out, rem_b_out = find_subset_sum(list_a_out, list_b_out)
            for l in log_out:
                l['날짜'] = d
                l['구분'] = "출금(대변)"
                all_logs.append(l)
            
            # 매칭 실패 기록
            for ra in rem_a + rem_a_out:
                all_unmatched.append({"날짜": d, "파일": "신한은행(A)", "행번호": ra[0], "금액": ra[1]})
            for rb in rem_b + rem_b_out:
                all_unmatched.append({"날짜": d, "파일": "더존(B)", "행번호": rb[0], "금액": rb[1]})

        # 결과 출력
        st.subheader("✅ 매칭 성공 내역 (상세 추적)")
        match_df = pd.DataFrame(all_logs)
        st.dataframe(match_df, use_container_width=True)

        st.subheader("❌ 매칭 실패 내역 (휴먼에러 의심)")
        unmatch_df = pd.DataFrame(all_unmatched)
        st.dataframe(unmatch_df, use_container_width=True)

        # 엑셀 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            match_df.to_excel(writer, sheet_name='매칭성공_추적', index=False)
            unmatch_df.to_excel(writer, sheet_name='매칭실패_확인필요', index=False)
        st.download_button("📥 최종 리포트 다운로드", output.getvalue(), "final_report.xlsx")
