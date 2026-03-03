import streamlit as st
import pandas as pd
import io
import re
import copy

st.set_page_config(page_title="최종 병기: 무한 시뮬레이션 매칭", layout="wide")
st.title("🛰️ Google DeepMatch: Infinite Tournament")
st.info("모든 매칭 전략을 '무한 추적' 로직으로 구동한 뒤, 미매칭 건수가 가장 적은 최적의 경로를 자동으로 채택합니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned)))
    except: return 0

def find_best_subset(target, candidates):
    """1:N 매칭을 위한 서브셋 탐색 엔진"""
    # 1. 1:1 확인
    for idx, val in candidates:
        if val == target: return [(idx, val)]
    # 2. 누적합 (순차)
    cur_sum = 0
    selected = []
    for idx, val in candidates:
        if cur_sum + val <= target:
            cur_sum += val
            selected.append((idx, val))
        if cur_sum == target: return selected
    # 3. 누적합 (정렬)
    sorted_c = sorted(candidates, key=lambda x: x[1])
    cur_sum = 0
    selected = []
    for idx, val in sorted_c:
        if cur_sum + val <= target:
            cur_sum += val
            selected.append((idx, val))
        if cur_sum == target: return selected
    return None

def run_infinite_trace(dz_raw, sh_raw, strategy="large"):
    """
    각 전략별로 '무한 추적'을 수행하여 최종 미매칭 상태를 반환
    """
    dz_list = copy.deepcopy(dz_raw)
    sh_list = copy.deepcopy(sh_raw)
    all_matched = []
    used_dz = set()
    used_sh = set()

    # 전략별 초기 세팅
    while True:
        found_match = False
        available_dz = [d for d in dz_list if d[0] not in used_dz]
        available_sh = [s for s in sh_list if s[0] not in used_sh]

        if not available_dz or not available_sh: break

        # 전략에 따른 정렬
        if strategy == "large":
            available_dz.sort(key=lambda x: x[1], reverse=True)
        elif strategy == "small":
            available_dz.sort(key=lambda x: x[1])
        elif strategy == "1to1_first":
            # 1:1을 찾으면 즉시 루프 탈출 후 소거
            for d in available_dz:
                for s in available_sh:
                    if d[1] == s[1]:
                        all_matched.append({"유형":"1:1","더존_행":d[0],"더존_금액":d[1],"신한_행들":str(s[0]),"신한_합계":s[1]})
                        used_dz.add(d[0]); used_sh.add(s[0])
                        found_match = True; break
                if found_match: break
            if found_match: continue

        # 1:N 탐색
        for d_idx, d_val in available_dz:
            res = find_best_subset(d_val, available_sh)
            if res:
                sh_ids = [str(r[0]) for r in res]
                all_matched.append({"유형":f"1:{len(res)}","더존_행":d_idx,"더존_금액":d_val,"신한_행들":", ".join(sh_ids),"신한_합계":d_val})
                used_dz.add(d_idx)
                for r in res: used_sh.add(r[0])
                found_match = True; break
        
        if not found_match: # 역방향 (N:1) 시도
            available_sh.sort(key=lambda x: x[1], reverse=True)
            for s_idx, s_val in available_sh:
                res = find_best_subset(s_val, available_dz)
                if res:
                    dz_ids = [str(r[0]) for r in res]
                    all_matched.append({"유형":f"{len(res)}:1","더존_행":", ".join(dz_ids),"더존_금액":s_val,"신한_행들":str(s_idx),"신한_합계":s_val})
                    used_sh.add(s_idx)
                    for r in res: used_dz.add(r[0])
                    found_match = True; break
            
        if not found_match: break # 더 이상 아무것도 안 나오면 종료

    unmatched_count = (len(dz_raw) - len(used_dz)) + (len(sh_raw) - len(used_sh))
    return all_matched, used_dz, used_sh, unmatched_count

f_dz = st.file_uploader("더존 거래내역", type=['xlsx', 'csv'])
f_sh = st.file_uploader("신한은행 거래내역", type=['xlsx', 'csv'])

if f_dz and f_sh:
    dz_df = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh_df = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🔥 전 시나리오 무한 추적 시뮬레이션 시작"):
        with st.spinner('구글 알고리즘이 모든 경우의 수를 무한 루프로 돌리고 있습니다...'):
            def extract(df):
                pts = []
                for i, row in df.iterrows():
                    for v in row:
                        val = clean_money(v)
                        if val != 0: pts.append((i+1, val))
                return pts
            dz_raw = extract(dz_df); sh_raw = extract(sh_df)

            # 3가지 무한 추적 전략 가동
            res_large = run_infinite_trace(dz_raw, sh_raw, "large")
            res_small = run_infinite_trace(dz_raw, sh_raw, "small")
            res_1to1 = run_infinite_trace(dz_raw, sh_raw, "1to1_first")

            # 전략별 성적표 작성
            performance = pd.DataFrame([
                {"전략": "고액 우선 무한추적", "미매칭 잔여 건수": res_large[3]},
                {"전략": "소액 우선 무한추적", "미매칭 잔여 건수": res_small[3]},
                {"전략": "1:1 우선 무한추적", "미매칭 잔여 건수": res_1to1[3]}
            ])
            
            st.subheader("📊 시나리오별 미매칭 성적표")
            st.table(performance)

            # 최적 시나리오 선택
            best_idx = performance["미매칭 잔여 건수"].idxmin()
            winner = [res_large, res_small, res_1to1][best_idx]
            best_name = performance.iloc[best_idx]["전략"]

            st.success(f"🏆 최종 채택 시나리오: [{best_name}]")
            
            best_logs, best_udz, best_ush, _ = winner
            st.subheader("✅ 최종 매칭 결과 내역")
            st.dataframe(pd.DataFrame(best_logs), use_container_width=True)

            c1, c2 = st.columns(2)
            final_dz = [d for d in dz_raw if d[0] not in best_udz]
            final_sh = [s for s in sh_raw if s[0] not in best_ush]
            c1.error(f"❌ 더존 미매칭 ({len(final_dz)}건)")
            c1.dataframe(pd.DataFrame(final_dz, columns=['행번호', '금액']))
            c2.error(f"❌ 신한 미매칭 ({len(final_sh)}건)")
            c2.dataframe(pd.DataFrame(final_sh, columns=['행번호', '금액']))

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(best_logs).to_excel(writer, sheet_name='무한추적_최적결과', index=False)
                pd.DataFrame(final_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(final_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
            st.download_button("📥 전수조사 완결 보고서 다운로드", output.getvalue(), "Google_DeepMatch_Final.xlsx")
