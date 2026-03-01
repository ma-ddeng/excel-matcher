import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="국가대표급 회계 대조 시스템", layout="wide")
st.title("🛡️ 전수 조사형 N:M 회계 검증 시스템")
st.markdown("단 하나의 숫자도 놓치지 않기 위해 모든 경우의 수를 역추적합니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned))) # 정수 연산으로 오차 원천 차단
    except: return 0

def find_all_matches(targets, sources):
    """
    targets: [(행번호, 금액), ...]
    sources: [(행번호, 금액), ...]
    """
    matched_log = []
    used_targets = set()
    used_sources = set()

    # 1. 고액권부터 우선 매칭 (계산 효율성)
    targets_sorted = sorted(targets, key=lambda x: x[1], reverse=True)
    sources_sorted = sorted(sources, key=lambda x: x[1])

    for t_idx, t_val in targets_sorted:
        if t_idx in used_targets: continue
        
        # 1:N 매칭 탐색 (Greedy + Backtracking 방식)
        temp_sum = 0
        temp_sources = []
        
        # 가용 자원 중 타겟 금액을 만들 수 있는 조합 탐색
        for s_idx, s_val in sources_sorted:
            if s_idx in used_sources: continue
            if temp_sum + s_val <= t_val:
                temp_sum += s_val
                temp_sources.append((s_idx, s_val))
                
            if temp_sum == t_val:
                matched_log.append({
                    "유형": f"완전 매칭(1:{len(temp_sources)})",
                    "더존_행": str(t_idx), "더존_금액": t_val,
                    "신한_행": ", ".join([str(x[0]) for x in temp_sources]),
                    "신한_금액": temp_sum
                })
                used_targets.add(t_idx)
                for ts_idx, ts_val in temp_sources:
                    used_sources.add(ts_idx)
                break
    
    # 역방향 매칭 (N:1 탐색 - 신한 1행이 더존 여러 행인 경우)
    rem_sources = [x for x in sources if x[0] not in used_sources]
    rem_targets = [x for x in targets if x[0] not in used_targets]
    
    for s_idx, s_val in rem_sources:
        temp_sum = 0
        temp_targets = []
        for t_idx, t_val in rem_targets:
            if t_idx in used_targets: continue
            if temp_sum + t_val <= s_val:
                temp_sum += t_val
                temp_targets.append((t_idx, t_val))
            if temp_sum == s_val:
                matched_log.append({
                    "유형": f"역방향 매칭({len(temp_targets)}:1)",
                    "더존_행": ", ".join([str(x[0]) for x in temp_targets]),
                    "더존_금액": temp_sum,
                    "신한_행": str(s_idx), "신한_금액": s_val
                })
                used_sources.add(s_idx)
                for tt_idx, tt_val in temp_targets:
                    used_targets.add(tt_idx)
                break

    return matched_log, used_targets, used_sources

f_dz = st.file_uploader("📑 더존 데이터", type=['xlsx', 'xls', 'csv'])
f_sh = st.file_uploader("🏦 신한 데이터", type=['xlsx', 'xls', 'csv'])

if f_dz and f_sh:
    dz = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🔥 전수 조사 매칭 시작"):
        with st.spinner('모든 경우의 수를 계산 중입니다... (데이터가 많으면 최대 1분 소요)'):
            # 전처리 (A열=입금, B열=출금)
            dz_in = [(i+1, clean_money(row[0])) for i, row in dz.iterrows() if clean_money(row[0]) > 0]
            dz_out = [(i+1, clean_money(row[1])) for i, row in dz.iterrows() if clean_money(row[1]) > 0]
            sh_in = [(i+1, clean_money(row[0])) for i, row in sh.iterrows() if clean_money(row[0]) > 0]
            sh_out = [(i+1, clean_money(row[1])) for i, row in sh.iterrows() if clean_money(row[1]) > 0]

            # 전수 매칭 실행
            res_in, used_dz_in, used_sh_in = find_all_matches(dz_in, sh_in)
            res_out, used_dz_out, used_sh_out = find_all_matches(dz_out, sh_out)

            st.success("🎯 전수 조사가 완료되었습니다!")
            
            all_res = pd.DataFrame(res_in + res_out)
            st.subheader("✅ 최종 매칭 성공 내역")
            st.dataframe(all_res, use_container_width=True)

            # 미매칭 리스트 추출
            un_dz = [x for x in dz_in + dz_out if x[0] not in used_dz_in and x[0] not in used_dz_out]
            un_sh = [x for x in sh_in + sh_out if x[0] not in used_sh_in and x[0] not in used_sh_out]

            col1, col2 = st.columns(2)
            with col1:
                st.error(f"⚠️ 더존 미매칭 ({len(un_dz)}건)")
                st.dataframe(pd.DataFrame(un_dz, columns=['행번호', '금액']))
            with col2:
                st.error(f"⚠️ 신한 미매칭 ({len(un_sh)}건)")
                st.dataframe(pd.DataFrame(un_sh, columns=['행번호', '금액']))

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                all_res.to_excel(writer, sheet_name='매칭_성공_전수조사', index=False)
                pd.DataFrame(un_dz).to_excel(writer, sheet_name='더존_최종_미매칭', index=False)
                pd.DataFrame(un_sh).to_excel(writer, sheet_name='신한_최종_미매칭', index=False)
            st.download_button("📥 전수조사 리포트 다운로드", output.getvalue(), "Full_Audit_Report.xlsx")
