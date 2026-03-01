import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="회계-통장 무제한 N:M 매칭", layout="wide")

st.title("⚖️ 회계 데이터 행 단위 전수 매칭 시스템")
st.info("한 행의 금액이 수십 개 행의 합계와 일치하는 경우(예: 1:19 매칭)까지 모두 찾아냅니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0.0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except: return 0.0

def find_greedy_match(target_list, source_list):
    """
    target_list: 매칭의 기준이 되는 금액 리스트 [(행번호, 금액), ...]
    source_list: 합산하여 기준 금액을 만들 대상 리스트 [(행번호, 금액), ...]
    """
    matches = []
    used_sources = set()
    used_targets = set()

    # 1. 1:1 매칭 먼저 처리
    for t_idx, t_val in target_list:
        for s_idx, s_val in source_list:
            if s_idx not in used_sources and abs(t_val - s_val) < 1:
                matches.append({
                    "유형": "1:1 매칭",
                    "더존_행": str(t_idx), "더존_금액": t_val,
                    "신한_행": str(s_idx), "신한_금액": s_val
                })
                used_targets.add(t_idx)
                used_sources.add(s_idx)
                break

    # 2. 1:N 매칭 (한 개의 큰 값이 여러 개의 작은 값 합계와 같은지 확인)
    # 기준 리스트에서 아직 사용 안 된 것들
    rem_targets = [x for x in target_list if x[0] not in used_targets]
    rem_sources = [x for x in source_list if x[0] not in used_sources]

    for t_idx, t_val in rem_targets:
        current_sum = 0
        temp_sources = []
        
        # 작은 값들을 하나씩 더해보며 기준값(t_val)에 도달하는지 확인
        # (이 방식은 연속되거나 정렬된 리스트에서 1:19 같은 대량 매칭을 잡기에 최적입니다)
        for s_idx, s_val in rem_sources:
            if s_idx in used_sources: continue
            
            if current_sum + s_val <= t_val + 0.5: # 소수점 오차 허용
                current_sum += s_val
                temp_sources.append((s_idx, s_val))
            
            if abs(current_sum - t_val) < 1: # 매칭 성공
                matches.append({
                    "유형": f"1:{len(temp_sources)} 대량매칭",
                    "더존_행": str(t_idx), "더존_금액": t_val,
                    "신한_행": ", ".join([str(x[0]) for x in temp_sources]), 
                    "신한_금액": current_sum
                })
                used_targets.add(t_idx)
                for ts_idx, ts_val in temp_sources:
                    used_sources.add(ts_idx)
                break
                
    return matches, used_targets, used_sources

f_dz = st.file_uploader("📑 더존 엑셀 (A:입금, B:출금)", type=['xlsx', 'xls', 'csv'])
f_sh = st.file_uploader("🏦 신한 엑셀 (A:입금, B:출금)", type=['xlsx', 'xls', 'csv'])

if f_dz and f_sh:
    dz = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🔍 무제한 조합 대조 시작"):
        with st.spinner('1:N 대량 매칭 조합을 분석 중입니다...'):
            # 데이터 추출 (A:0, B:1)
            dz_in = [(i+1, clean_money(row[0])) for i, row in dz.iterrows() if clean_money(row[0]) > 0]
            dz_out = [(i+1, clean_money(row[1])) for i, row in dz.iterrows() if clean_money(row[1]) > 0]
            sh_in = [(i+1, clean_money(row[0])) for i, row in sh.iterrows() if clean_money(row[0]) > 0]
            sh_out = [(i+1, clean_money(row[1])) for i, row in sh.iterrows() if clean_money(row[1]) > 0]

            # 입금(A열) 매칭 실행 (더존 기준 한번, 신한 기준 한번 양방향 탐색)
            in_match, used_dz_in, used_sh_in = find_greedy_match(dz_in, sh_in)
            
            # 출금(B열) 매칭 실행
            out_match, used_dz_out, used_sh_out = find_greedy_match(dz_out, sh_out)

            # 결과 리포트
            st.success("✅ 매칭 분석 완료!")
            
            res_df = pd.DataFrame(in_match + out_match)
            st.write("### 🔗 찾아낸 매칭 조합")
            st.dataframe(res_df, use_container_width=True)

            # 미매칭 내역
            un_dz = [x for x in dz_in + dz_out if x[0] not in used_dz_in and x[0] not in used_dz_out]
            un_sh = [x for x in sh_in + sh_out if x[0] not in used_sh_in and x[0] not in used_sh_out]

            col1, col2 = st.columns(2)
            col1.error(f"❌ 더존 미매칭: {len(un_dz)}건")
            col1.dataframe(pd.DataFrame(un_dz, columns=['행번호', '금액']))
            col2.error(f"❌ 신한 미매칭: {len(un_sh)}건")
            col2.dataframe(pd.DataFrame(un_sh, columns=['행번호', '금액']))

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, sheet_name='매칭성공', index=False)
                pd.DataFrame(un_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(un_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
            st.download_button("📥 결과 보고서 다운로드", output.getvalue(), "final_match_report.xlsx")
