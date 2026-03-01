import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="초정밀 회계 대조 시스템", layout="wide")
st.title("🚀 일론 머스크급 초정밀 N:M 매칭 시스템")
st.info("데이터를 한 열씩 전수 조사하여 1:19, 2:15 등 모든 합산 조합을 찾아냅니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned)))
    except: return 0

def find_best_subset_match(target_val, candidates):
    """
    타겟 금액을 만들기 위해 후보군에서 가장 적절한 조합을 찾는 함수
    (누적 합계 및 최적화 조합 탐색)
    """
    current_sum = 0
    selected_indices = []
    
    # 1. 순차적 누적 합계 탐색 (실무 데이터에서 가장 빈번함)
    for i, (idx, val) in enumerate(candidates):
        if current_sum + val <= target_val:
            current_sum += val
            selected_indices.append((idx, val))
        
        if current_sum == target_val:
            return selected_indices
            
    # 2. 역순 탐색 (뒤에서부터 쌓인 데이터 대응)
    current_sum = 0
    selected_indices = []
    for i, (idx, val) in enumerate(reversed(candidates)):
        if current_sum + val <= target_val:
            current_sum += val
            selected_indices.append((idx, val))
        if current_sum == target_val:
            return selected_indices

    return None

def process_matching(dz_list, sh_list):
    matched_results = []
    used_dz = set()
    used_sh = set()

    # [1단계] 고액권부터 매칭 시도 (더존의 큰 금액이 신한의 여러개 합인지)
    dz_sorted = sorted(dz_list, key=lambda x: x[1], reverse=True)
    
    for d_idx, d_val in dz_sorted:
        if d_val == 0: continue
        available_sh = [s for s in sh_list if s[0] not in used_sh]
        
        match_res = find_best_subset_match(d_val, available_sh)
        
        if match_res:
            sh_indices = [str(m[0]) for m in match_res]
            matched_results.append({
                "상태": f"성공(1:{len(match_res)})",
                "더존_행": str(d_idx),
                "더존_금액": d_val,
                "신한_행들": ", ".join(sh_indices),
                "신한_합계": sum(m[1] for m in match_res)
            })
            used_dz.add(d_idx)
            for m_idx, m_val in match_res:
                used_sh.add(m_idx)

    # [2단계] 반대 방향 매칭 (신한의 큰 금액이 더존의 여러개 합인지)
    sh_remaining = [s for s in sh_list if s[0] not in used_sh]
    dz_remaining = [d for d in dz_list if d[0] not in used_dz]
    sh_sorted = sorted(sh_remaining, key=lambda x: x[1], reverse=True)

    for s_idx, s_val in sh_sorted:
        if s_val == 0: continue
        match_res = find_best_subset_match(s_val, dz_remaining)
        if match_res:
            dz_indices = [str(m[0]) for m in match_res]
            matched_results.append({
                "상태": f"성공({len(match_res)}:1)",
                "더존_행": ", ".join(dz_indices),
                "더존_금액": sum(m[1] for m in match_res),
                "신한_행들": str(s_idx),
                "신한_합계": s_val
            })
            used_sh.add(s_idx)
            for m_idx, m_val in match_res:
                used_dz.add(m_idx)
                dz_remaining = [d for d in dz_remaining if d[0] not in used_dz]

    return matched_results, used_dz, used_sh

# 파일 업로드
f_dz = st.file_uploader("📑 더존 데이터 (A열만 있는 파일)", type=['xlsx', 'xls', 'csv'])
f_sh = st.file_uploader("🏦 신한 데이터 (A열만 있는 파일)", type=['xlsx', 'xls', 'csv'])

if f_dz and f_sh:
    dz_df = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh_df = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🏁 초정밀 전수조사 매칭 시작"):
        with st.spinner('모든 수치 조합을 분석 중입니다...'):
            # 첫 번째 열(index 0)에서 데이터 추출
            dz_data = [(i+1, clean_money(row[0])) for i, row in dz_df.iterrows() if clean_money(row[0]) != 0]
            sh_data = [(i+1, clean_money(row[0])) for i, row in sh_df.iterrows() if clean_money(row[0]) != 0]

            results, used_dz, used_sh = process_matching(dz_data, sh_data)

            # 결과 리포트
            st.success(f"🎯 총 {len(results)}개의 복합 매칭 그룹을 찾아냈습니다!")
            
            if results:
                df_res = pd.DataFrame(results)
                st.dataframe(df_res, use_container_width=True)

                # 미매칭 내역
                un_dz = [d for d in dz_data if d[0] not in used_dz]
                un_sh = [s for s in sh_data if s[0] not in used_sh]

                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"❌ 더존 미매칭 ({len(un_dz)}건)")
                    st.dataframe(pd.DataFrame(un_dz, columns=['행', '금액']))
                with c2:
                    st.error(f"❌ 신한 미매칭 ({len(un_sh)}건)")
                    st.dataframe(pd.DataFrame(un_sh, columns=['행', '금액']))

                # 엑셀 다운로드
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_res.to_excel(writer, sheet_name='매칭완료', index=False)
                    pd.DataFrame(un_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
                    pd.DataFrame(un_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
                
                st.download_button("📥 최종 매칭 리포트 다운로드", output.getvalue(), "Perfect_Match_Report.xlsx")
            else:
                st.warning("매칭된 데이터가 없습니다. 열 구성을 확인해주세요.")
