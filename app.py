import streamlit as st
import pandas as pd
from itertools import combinations
import io

st.set_page_config(page_title="금액 매칭 프로", layout="wide")

st.title("⚖️ 엑셀 금액 교차 매칭 시스템")
st.markdown("""
A파일의 한 금액이 B파일의 **여러 행 금액의 합**과 일치하는지 찾아냅니다. 
결과를 확인한 후 엑셀로 다운로드하세요.
""")

col1, col2 = st.columns(2)
with col1:
    file_a = st.file_uploader("📂 기준 파일 (A) 업로드", type=['xlsx'])
with col2:
    file_b = st.file_uploader("📂 비교 대상 파일 (B) 업로드", type=['xlsx'])

if file_a and file_b:
    df_a = pd.read_excel(file_a)
    df_b = pd.read_excel(file_b)

    c1, c2 = st.columns(2)
    with c1:
        col_a = st.selectbox("A파일 금액 컬럼", df_a.columns)
    with c2:
        col_b = st.selectbox("B파일 금액 컬럼", df_b.columns)

    if st.button("🔍 매칭 분석 시작"):
        # 데이터 정리: 행 번호(Index)를 포함하여 리스트화
        # 행 번호는 엑셀 기준으로 표시하기 위해 +2 (헤더 1행 + 인덱스 0부터 시작)
        list_a = [{"row": i+2, "val": v} for i, v in enumerate(df_a[col_a]) if pd.notna(v)]
        list_b = [{"row": i+2, "val": v} for i, v in enumerate(df_b[col_b]) if pd.notna(v)]

        matched_data = []
        unmatched_a = list_a[:]
        unmatched_b = list_b[:]

        # 1단계: 1:1 매칭 우선 처리
        for a_item in list_a:
            for b_item in unmatched_b:
                if a_item['val'] == b_item['val']:
                    matched_data.append({
                        "유형": "1:1 일치",
                        "A행": a_item['row'], "A금액": a_item['val'],
                        "B행": b_item['row'], "B금액": b_item['val']
                    })
                    if a_item in unmatched_a: unmatched_a.remove(a_item)
                    unmatched_b.remove(b_item)
                    break

        # 2단계: 1:N 매칭 (A의 1개 = B의 여러 개 합)
        # 성능을 위해 최대 4개 조합까지만 탐색
        for a_item in unmatched_a[:]:
            found = False
            for r in range(2, 5): 
                for combo in combinations(unmatched_b, r):
                    if sum(c['val'] for c in combo) == a_item['val']:
                        matched_data.append({
                            "유형": f"1:{r} 조합매칭",
                            "A행": a_item['row'], "A금액": a_item['val'],
                            "B행": ", ".join([str(c['row']) for c in combo]),
                            "B금액": " + ".join([str(c['val']) for c in combo])
                        })
                        unmatched_a.remove(a_item)
                        for c in combo: unmatched_b.remove(c)
                        found = True
                        break
                if found: break

        # 결과 전시
        st.subheader("📊 매칭 결과 리포트")
        if matched_data:
            res_df = pd.DataFrame(matched_data)
            st.dataframe(res_df, use_container_width=True)
            
            # 엑셀 다운로드 기능
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, index=False, sheet_name='Matching_Result')
            
            st.download_button(
                label="📥 매칭 결과 엑셀 다운로드",
                data=output.getvalue(),
                file_name="matching_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("일치하는 항목이 없습니다.")

        # 미매칭 항목 출력
        col_err1, col_err2 = st.columns(2)
        with col_err1:
            st.error(f"❌ A 미매칭 ({len(unmatched_a)}건)")
            st.write(pd.DataFrame(unmatched_a))
        with col_err2:
            st.error(f"❌ B 미매칭 ({len(unmatched_b)}건)")
            st.write(pd.DataFrame(unmatched_b))
