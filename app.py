import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="회계 정밀 감사 시스템", layout="wide")
st.title("🏦 회계사+개발자 모드: N:M 정밀 대조 시스템")
st.markdown("1:1 매칭을 우선 처리한 후, **1:N 대량 합산 내역(예: 1:19)**을 정밀하게 추적합니다.")

def clean_money(val):
    try:
        if pd.isna(val): return 0.0
        cleaned = re.sub(r'[^\d.-]', '', str(val))
        return float(cleaned) if cleaned else 0.0
    except: return 0.0

def find_subset_sum(target_val, candidates, current_combination=[]):
    """
    특정 타겟 금액을 만들기 위한 최적의 조합을 찾는 재귀 함수
    """
    # 소수점 오차 방지를 위해 정수화하여 비교 (원 단위)
    target_int = int(round(target_val))
    
    # 1. 단일 행 매칭 시도 (1:1)
    for i, (idx, val) in enumerate(candidates):
        if int(round(val)) == target_int:
            return [(idx, val)]
    
    # 2. 누적 합계 매칭 (실무적으로 전표는 보통 시간순/행순으로 쌓이므로 누적합이 강력함)
    temp_sum = 0
    temp_list = []
    for idx, val in candidates:
        temp_sum += val
        temp_list.append((idx, val))
        if int(round(temp_sum)) == target_int:
            return temp_list
        if temp_sum > target_val + 100: # 타겟보다 너무 커지면 중단
            break
            
    return None

def advanced_matching(dz_list, sh_list):
    matched_log = []
    used_dz = set()
    used_sh = set()

    # [Step 1] 1:1 매칭 (정확히 일치하는 것부터 제거)
    for d_idx, d_val in dz_list:
        for s_idx, s_val in sh_list:
            if s_idx not in used_sh and int(round(d_val)) == int(round(s_val)):
                matched_log.append({
                    "유형": "1:1 일치",
                    "더존_행": str(d_idx), "더존_금액": d_val,
                    "신한_행": str(s_idx), "신한_금액": s_val
                })
                used_dz.add(d_idx)
                used_sh.add(s_idx)
                break

    # [Step 2] 1:N 매칭 (더존 1행 = 신한 여러 행 합계)
    rem_dz = [x for x in dz_list if x[0] not in used_dz]
    rem_sh = [x for x in sh_list if x[0] not in used_sh]

    for d_idx, d_val in rem_dz:
        # 아직 사용 안 된 신한은행 행들 중 조합 찾기
        available_sh = [x for x in rem_sh if x[0] not in used_sh]
        result = find_subset_sum(d_val, available_sh)
        
        if result:
            sh_indices = [str(r[0]) for r in result]
            sh_sum = sum(r[1] for r in result)
            matched_log.append({
                "유형": f"1:{len(result)} 합산매칭",
                "더존_행": str(d_idx), "더존_금액": d_val,
                "신한_행": ", ".join(sh_indices), "신한_금액": sh_sum
            })
            used_dz.add(d_idx)
            for r_idx, r_val in result:
                used_sh.add(r_idx)

    return matched_log, used_dz, used_sh

# 파일 업로드
f_dz = st.file_uploader("📑 더존 데이터 (A:차변, B:대변)", type=['xlsx', 'xls', 'csv'])
f_sh = st.file_uploader("🏦 신한 데이터 (A:입금, B:출금)", type=['xlsx', 'xls', 'csv'])

if f_dz and f_sh:
    dz = pd.read_csv(f_dz, header=None) if f_dz.name.endswith('.csv') else pd.read_excel(f_dz, header=None)
    sh = pd.read_csv(f_sh, header=None) if f_sh.name.endswith('.csv') else pd.read_excel(f_sh, header=None)

    if st.button("🚀 전문가 모드 대조 시작"):
        with st.spinner('회계 전표 조합을 정밀 분석 중입니다...'):
            # 전처리 (A열=0, B열=1)
            dz_in = [(i+1, clean_money(row[0])) for i, row in dz.iterrows() if clean_money(row[0]) > 0]
            dz_out = [(i+1, clean_money(row[1])) for i, row in dz.iterrows() if clean_money(row[1]) > 0]
            sh_in = [(i+1, clean_money(row[0])) for i, row in sh.iterrows() if clean_money(row[0]) > 0]
            sh_out = [(i+1, clean_money(row[1])) for i, row in sh.iterrows() if clean_money(row[1]) > 0]

            # 대조 실행
            in_results, in_used_dz, in_used_sh = advanced_matching(dz_in, sh_in)
            out_results, out_used_dz, out_used_sh = advanced_matching(dz_out, sh_out)

            # 결과 리포트
            st.success("✅ 대조 완료!")
            
            final_match = pd.DataFrame(in_results + out_results)
            st.subheader("🔗 매칭 성공 내역 (1:1 및 1:N 합산)")
            st.dataframe(final_match, use_container_width=True)

            # 미매칭
            un_dz = [x for x in dz_in + dz_out if x[0] not in in_used_dz and x[0] not in out_used_dz]
            un_sh = [x for x in sh_in + sh_out if x[0] not in in_used_sh and x[0] not in out_used_sh]

            col1, col2 = st.columns(2)
            with col1:
                st.error(f"❌ 더존 미매칭 ({len(un_dz)}건)")
                st.dataframe(pd.DataFrame(un_dz, columns=['행', '금액']))
            with col2:
                st.error(f"❌ 신한 미매칭 ({len(un_sh)}건)")
                st.dataframe(pd.DataFrame(un_sh, columns=['행', '금액']))

            # 엑셀 다운로드
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                final_match.to_excel(writer, sheet_name='매칭성공', index=False)
                pd.DataFrame(un_dz).to_excel(writer, sheet_name='더존_미매칭', index=False)
                pd.DataFrame(un_sh).to_excel(writer, sheet_name='신한_미매칭', index=False)
            st.download_button("📥 최종 보고서 다운로드", output.getvalue(), "Account_Audit_Report.xlsx")
