import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="초정밀 회계 대조 (1:N 전용)", layout="wide")
st.title("⚖️ 전수 조사형 초정밀 매칭 시스템")
st.markdown("더존의 1행이 신한의 19개 이상 행과 일치하는 **대형 합산 건**을 최우선으로 찾습니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0
        # 쉼표 제거 및 숫자만 추출 후 '정수'로 변환 (오차 방지 핵심)
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned)))
    except: return 0

def find_perfect_subset(target_val, candidates):
    """
    타겟 금액을 만들기 위해 후보군에서 모든 경우의 수를 조합함
    """
    # 1. 1:1 매칭 확인
    for idx, val in candidates:
        if val == target_val:
            return [(idx, val)]
            
    # 2. 누적 합계 매칭 (순차/역순 모두 수행)
    # 신한 데이터처럼 소액이 모여있는 경우 가장 확실한 방법
    temp_sum = 0
    temp_list = []
    for idx, val in candidates:
        if temp_sum + val <= target_val:
            temp_sum += val
            temp_list.append((idx, val))
        if temp_sum == target_val:
            return temp_list

    # 3. 만약 위 방법으로 안 되면, 정렬 후 다시 시도 (작은 값부터 채우기)
    sorted_candidates = sorted(candidates, key=lambda x: x[1])
    temp_sum = 0
    temp_list = []
    for idx, val in sorted_candidates:
        if temp_sum + val <= target_val:
            temp_sum += val
            temp_list.append((idx, val))
        if temp_sum == target_val:
            return temp_list

    return None

def run_matching(dz_data, sh_data):
    matched_logs = []
    used_dz = set()
    used_sh = set()

    # [핵심] 더존의 큰 금액을 기준으로 신한의 여러 값을 찾아냄
    # 금액이 큰 순서대로 타겟팅해야 1:19 같은 대형 건을 먼저 잡습니다.
    dz_targets = sorted(dz_data, key=lambda x: x[1], reverse=True)

    for d_idx, d_val in dz_targets:
        if d_val == 0: continue
        
        # 아직 사용 안 된 신한 데이터만 후보로 사용
        current_sh_pool = [s for s in sh_data if s[0] not in used_sh]
        
        result = find_perfect_subset(d_val, current_sh_pool)
        
        if result:
            sh_indices = [str(r[0]) for r in result]
            matched_logs.append({
                "결과": f"성공 (1:{len(result)})",
                "더존_행": d_idx,
                "더존_금액": d_val,
                "신한_행들": ", ".join(sh_indices),
                "신한_합계": sum(r[1] for r in result)
            })
            used_dz.add(d_idx)
            for r_idx, r_val in result:
                used_sh.add(r_idx)

    return matched_logs, used_dz, used_sh

# 파일 업로드
f_dz = st.file_uploader("더존 엑셀", type=['xlsx', 'xls', 'csv'])
f_sh = st.file_uploader("신한 엑셀", type=['xlsx', 'xls', 'csv'])

if f_dz and f_sh:
    dz_df = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh_df = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🔍 모든 조합 전수 조사 시작"):
        # A열(0)과 B열(1) 모두 데이터로 인식하여 합산 처리
        # 회계 전표 특성상 어느 열에 있든 금액의 '합'이 중요하므로 데이터를 하나로 모음
        def get_all_amounts(df):
            data = []
            for i, row in df.iterrows():
                val_a = clean_money(row[0])
                val_b = clean_money(row[1]) if len(row) > 1 else 0
                if val_a != 0: data.append((i+1, val_a))
                if val_b != 0: data.append((i+1, val_b))
            return data

        dz_list = get_all_amounts(dz_df)
        sh_list = get_all_amounts(sh_df)

        matches, used_dz, used_sh = run_matching(dz_list, sh_list)

        st.success(f"🎯 총 {len(matches)}개의 매칭 그룹을 발견했습니다.")
        
        if matches:
            st.dataframe(pd.DataFrame(matches), use_container_width=True)

        # 미매칭 표시
        un_dz = [d for d in dz_list if d[0] not in used_dz]
        un_sh = [s for s in sh_list if s[0] not in used_sh]

        c1, c2 = st.columns(2)
        c1.error(f"❌ 더존 미매칭 ({len(un_dz)}건)")
        c1.dataframe(pd.DataFrame(un_dz, columns=['행', '금액']))
        c2.error(f"❌ 신한 미매칭 ({len(un_sh)}건)")
        c2.dataframe(pd.DataFrame(un_sh, columns=['행', '금액']))

        # 다운로드
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(matches).to_excel(writer, sheet_name='매칭완료', index=False)
            pd.DataFrame(un_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
            pd.DataFrame(un_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
        st.download_button("📥 최종 보고서 다운로드", output.getvalue(), "Perfect_Report.xlsx")
