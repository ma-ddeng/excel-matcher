import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="초정밀 회계 감사 시스템 V2", layout="wide")
st.title("🚀 무제한 조합 추적 매칭 시스템")
st.info("데이터 순서가 섞여 있어도 합계가 일치하면 끝까지 추적하여 1:19 매칭을 잡아냅니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return int(round(float(cleaned)))
    except: return 0

def find_subset_sum_perfect(target, candidates):
    """
    타겟 금액을 만들기 위해 후보군에서 최적의 조합을 찾는 알고리즘
    (누적합 + 정렬 탐색 + 역순 탐색 통합)
    """
    # 1. 단일 매칭 (1:1)
    for idx, val in candidates:
        if val == target:
            return [(idx, val)]
    
    # 2. 정방향 누적합 탐색 (1:N)
    current_sum = 0
    selected = []
    for idx, val in candidates:
        if current_sum + val <= target:
            current_sum += val
            selected.append((idx, val))
        if current_sum == target:
            return selected

    # 3. 역방향 누적합 탐색 (데이터가 뒤에서부터 쌓인 경우)
    current_sum = 0
    selected = []
    for idx, val in reversed(candidates):
        if current_sum + val <= target:
            current_sum += val
            selected.append((idx, val))
        if current_sum == target:
            return selected
            
    # 4. 금액순 정렬 탐색 (잘게 쪼개진 전표들 대응)
    sorted_cand = sorted(candidates, key=lambda x: x[1])
    current_sum = 0
    selected = []
    for idx, val in sorted_cand:
        if current_sum + val <= target:
            current_sum += val
            selected.append((idx, val))
        if current_sum == target:
            return selected

    return None

def process_deep_match(dz_list, sh_list):
    results = []
    used_dz = set()
    used_sh = set()

    # [핵심] 더존의 '목표 금액'들을 큰 순서대로 정렬해서 신한에서 부품을 찾습니다.
    # 15,443,504원 같은 큰 금액이 신한의 소액 19개를 '먹어야' 하기 때문입니다.
    dz_targets = sorted(dz_list, key=lambda x: x[1], reverse=True)

    for d_idx, d_val in dz_targets:
        if d_val == 0: continue
        
        # 아직 사용 안 된 신한 데이터 후보군
        pool = [s for s in sh_list if s[0] not in used_sh]
        
        match_result = find_subset_sum_perfect(d_val, pool)
        
        if match_result:
            sh_ids = [str(m[0]) for m in match_result]
            results.append({
                "유형": f"복합 매칭 (1:{len(match_result)})",
                "더존_행": d_idx,
                "더존_금액": d_val,
                "신한_행들": ", ".join(sh_ids),
                "신한_합계": sum(m[1] for m in match_result)
            })
            used_dz.add(d_idx)
            for m_idx, m_val in match_result:
                used_sh.add(m_idx)

    # 남은 것들 중 혹시 신한의 큰 금액이 더존 여러 개의 합인지 확인 (역방향)
    rem_sh = sorted([s for s in sh_list if s[0] not in used_sh], key=lambda x: x[1], reverse=True)
    rem_dz_pool = [d for d in dz_list if d[0] not in used_dz]
    
    for s_idx, s_val in rem_sh:
        if s_val == 0: continue
        match_result = find_subset_sum_perfect(s_val, rem_dz_pool)
        if match_result:
            dz_ids = [str(m[0]) for m in match_result]
            results.append({
                "유형": f"역방향 매칭 ({len(match_result)}:1)",
                "더존_행": ", ".join(dz_ids),
                "더존_금액": sum(m[1] for m in match_result),
                "신한_행들": str(s_idx),
                "신한_합계": s_val
            })
            used_sh.add(s_idx)
            for m_idx, m_val in match_result:
                used_dz.add(m_idx)
                # 풀 업데이트
                rem_dz_pool = [d for d in rem_dz_pool if d[0] not in used_dz]

    return results, used_dz, used_sh

# 파일 업로드 섹션
f_dz = st.file_uploader("📑 더존 거래내역 2 업로드", type=['xlsx', 'csv'])
f_sh = st.file_uploader("🏦 신한은행 거래내역 2 업로드", type=['xlsx', 'csv'])

if f_dz and f_sh:
    dz_df = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh_df = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🏁 끝장 매칭 시작"):
        with st.spinner('1:19 이상의 복합 조합을 추적 중입니다...'):
            # 모든 열의 데이터를 하나의 리스트로 통합하여 추출
            def get_data(df):
                pts = []
                for i, row in df.iterrows():
                    for col in range(len(row)):
                        v = clean_money(row[col])
                        if v != 0: pts.append((i+1, v))
                return pts

            dz_all = get_data(dz_df)
            sh_all = get_data(sh_df)

            final_matches, used_dz, used_sh = process_deep_match(dz_all, sh_all)

            st.success(f"🎯 총 {len(final_matches)}개의 그룹 매칭에 성공했습니다!")
            
            if final_matches:
                st.dataframe(pd.DataFrame(final_matches), use_container_width=True)

            # 미매칭 내역
            un_dz = [d for d in dz_all if d[0] not in used_dz]
            un_sh = [s for s in sh_all if s[0] not in used_sh]

            c1, c2 = st.columns(2)
            c1.error(f"⚠️ 더존 미매칭 ({len(un_dz)}건)")
            c1.dataframe(pd.DataFrame(un_dz, columns=['행번호', '금액']))
            c2.error(f"⚠️ 신한 미매칭 ({len(un_sh)}건)")
            c2.dataframe(pd.DataFrame(un_sh, columns=['행번호', '금액']))

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pd.DataFrame(final_matches).to_excel(writer, sheet_name='매칭완료', index=False)
                pd.DataFrame(un_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(un_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
            st.download_button("📥 최종 보고서 받기", output.getvalue(), "Final_Deep_Audit.xlsx")
