import streamlit as st
import pandas as pd
import io
import re
import copy

st.set_page_config(page_title="최적화 매칭 엔진 V3", layout="wide")
st.title("🏆 Best-Fit Audit: 최적 매칭 토너먼트")
st.info("4가지 이상의 회계 로직을 동시에 시뮬레이션하여 미매칭이 가장 적은 최적의 결과를 도출합니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned)))
    except: return 0

def find_subset(target, candidates, limit=50):
    # 1:1 확인
    for idx, val in candidates:
        if val == target: return [(idx, val)]
    
    # 누적합 (1:N)
    cur_sum = 0
    selected = []
    for idx, val in candidates:
        if cur_sum + val <= target:
            cur_sum += val
            selected.append((idx, val))
        if cur_sum == target: return selected
    
    # 정렬 후 탐색
    sorted_c = sorted(candidates, key=lambda x: x[1])
    cur_sum = 0
    selected = []
    for idx, val in sorted_c:
        if cur_sum + val <= target:
            cur_sum += val
            selected.append((idx, val))
        if cur_sum == target: return selected
    return None

def run_strategy(dz_raw, sh_raw, priority="large"):
    """
    특정 전략에 따라 매칭을 수행하는 함수
    """
    dz_list = copy.deepcopy(dz_raw)
    sh_list = copy.deepcopy(sh_raw)
    
    if priority == "large":
        dz_list.sort(key=lambda x: x[1], reverse=True)
    elif priority == "small":
        dz_list.sort(key=lambda x: x[1])
    elif priority == "1to1":
        # 1:1을 가장 먼저 처리하기 위해 정렬하지 않음 (로직 내에서 처리)
        pass

    matched_logs = []
    used_dz = set()
    used_sh = set()

    # [단계 1] 1:1 매칭 우선 처리 (1to1 전략일 때만)
    if priority == "1to1":
        for d_idx, d_val in dz_list:
            for s_idx, s_val in sh_list:
                if s_idx not in used_sh and d_val == s_val:
                    matched_logs.append({"유형":"1:1","더존_행":d_idx,"더존_금액":d_val,"신한_행들":str(s_idx),"신한_합계":s_val})
                    used_dz.add(d_idx)
                    used_sh.add(s_idx)
                    break

    # [단계 2] N:M (인접 행 합산) 시도 - 선생님의 8,9행 케이스 해결용
    for i in range(len(dz_list)-1):
        if dz_list[i][0] in used_dz or dz_list[i+1][0] in used_dz: continue
        combined_target = dz_list[i][1] + dz_list[i+1][1]
        pool = [s for s in sh_list if s[0] not in used_sh]
        res = find_subset(combined_target, pool)
        if res:
            sh_ids = [str(r[0]) for r in res]
            matched_logs.append({"유형":"인접2행:N","더존_행":f"{dz_list[i][0]},{dz_list[i+1][0]}","더존_금액":combined_target,"신한_행들":", ".join(sh_ids),"신한_합계":combined_target})
            used_dz.add(dz_list[i][0]); used_dz.add(dz_list[i+1][0])
            for r in res: used_sh.add(r[0])

    # [단계 3] 1:N 반복 소거
    while True:
        found_any = False
        curr_dz = [d for d in dz_list if d[0] not in used_dz]
        if priority == "large": curr_dz.sort(key=lambda x: x[1], reverse=True)
        
        for d_idx, d_val in curr_dz:
            pool = [s for s in sh_list if s[0] not in used_sh]
            res = find_subset(d_val, pool)
            if res:
                sh_ids = [str(r[0]) for r in res]
                matched_logs.append({"유형":"1:N","더존_행":d_idx,"더존_금액":d_val,"신한_행들":", ".join(sh_ids),"신한_합계":d_val})
                used_dz.add(d_idx)
                for r in res: used_sh.add(r[0])
                found_any = True
                break
        if not found_any: break

    unmatched_count = len(dz_raw) - len(used_dz) + len(sh_raw) - len(used_sh)
    return matched_logs, used_dz, used_sh, unmatched_count

# 파일 업로드
f_dz = st.file_uploader("더존 데이터", type=['xlsx', 'csv'])
f_sh = st.file_uploader("신한 데이터", type=['xlsx', 'csv'])

if f_dz and f_sh:
    dz_df = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh_df = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🏁 최적 시나리오 토너먼트 시작"):
        with st.spinner('여러 시나리오를 비교하여 최적의 결과값을 산출 중입니다...'):
            def extract(df):
                res = []
                for i, row in df.iterrows():
                    for v in row:
                        val = clean_money(v)
                        if val != 0: res.append((i+1, val))
                return res
            dz_all = extract(dz_df); sh_all = extract(sh_df)

            # 시나리오 가동
            s1_logs, s1_udz, s1_ush, s1_count = run_strategy(dz_all, sh_all, "large")
            s2_logs, s2_udz, s2_ush, s2_count = run_strategy(dz_all, sh_all, "small")
            s3_logs, s3_udz, s3_ush, s3_count = run_strategy(dz_all, sh_all, "1to1")

            # 챔피언 결정 (미매칭 건수가 가장 적은 것)
            results = [(s1_logs, s1_udz, s1_ush, s1_count, "고액 우선 전략"),
                       (s2_logs, s2_udz, s2_ush, s2_count, "소액 우선 전략"),
                       (s3_logs, s3_udz, s3_ush, s3_count, "1:1 우선 전략")]
            
            results.sort(key=lambda x: x[3]) # 미매칭 건수 기준 정렬
            best_logs, best_udz, best_ush, best_count, best_name = results[0]

            st.success(f"🏆 선정된 최적 시나리오: [{best_name}] (미매칭 잔여: {best_count}건)")
            
            # 결과 표시
            st.subheader("✅ 매칭 성공 내역 (최적화 결과)")
            st.dataframe(pd.DataFrame(best_logs), use_container_width=True)

            c1, c2 = st.columns(2)
            final_dz = [d for d in dz_all if d[0] not in best_udz]
            final_sh = [s for s in sh_all if s[0] not in best_ush]
            c1.error(f"❌ 최종 미매칭 더존 ({len(final_dz)}건)")
            c1.dataframe(pd.DataFrame(final_dz, columns=['행번호', '금액']))
            c2.error(f"❌ 최종 미매칭 신한 ({len(final_sh)}건)")
            c2.dataframe(pd.DataFrame(final_sh, columns=['행번호', '금액']))

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(best_logs).to_excel(writer, sheet_name='최적매칭결과', index=False)
                pd.DataFrame(final_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(final_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
            st.download_button("📥 최적화 보고서 다운로드", output.getvalue(), "Optimal_Audit_Report.xlsx")
