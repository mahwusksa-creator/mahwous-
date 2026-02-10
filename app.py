# -*- coding: utf-8 -*-
"""
نظام التسعير الذكي للعطور - التطبيق الرئيسي.

تطبيق Streamlit لمقارنة أسعار العطور مع المنافسين
باستخدام قوانين مطابقة صارمة (تطابق الحجم + النوع).
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

# --- إعدادات الصفحة (يجب أن تكون أول أمر Streamlit) ---
st.set_page_config(
    page_title="نظام التسعير الذكي للعطور",
    page_icon="💎",
    layout="wide",
)

# استيراد محرك المطابقة
try:
    from matching_engine import PerfumeMatchingEngine
except ImportError:
    st.error(
        "خطأ: تعذر العثور على ملف matching_engine.py. "
        "تأكد من وجوده في نفس المجلد."
    )
    st.stop()


# =================================================================
# CSS مخصص
# =================================================================
st.markdown(
    "<style>.main{direction:rtl;}</style>",
    unsafe_allow_html=True,
)


# =================================================================
# تهيئة الجلسة
# =================================================================
def _init():
    """تهيئة متغيرات الجلسة مرة واحدة."""
    defaults = {
        "master_df": None,
        "my_file": None,
        "comp_files": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init()


# =================================================================
# دوال مساعدة
# =================================================================
def _to_excel(df: pd.DataFrame) -> bytes:
    """تحويل DataFrame إلى bytes لملف Excel."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="النتائج", index=False)
    return buf.getvalue()


# =================================================================
# العنوان الرئيسي
# =================================================================
st.title("💎 نظام التسعير الذكي للعطور")
st.caption("مقارنة ذكية وصارمة لأسعار العطور مع المنافسين")

# =================================================================
# الشريط الجانبي
# =================================================================
with st.sidebar:
    st.header("📋 طريقة الاستخدام")
    st.info(
        "1. ارفع ملف متجرك (Excel أو CSV)\n"
        "2. ارفع ملفات المنافسين\n"
        "3. اضغط **ابدأ المعالجة**\n"
        "4. استعرض النتائج وحمّلها"
    )

    st.header("⚙️ الإعدادات")
    min_score = st.slider(
        "الحد الأدنى لنسبة التطابق",
        min_value=50,
        max_value=100,
        value=75,
        step=5,
        help="كلما زادت النسبة، كانت المطابقة أدق.",
    )

    st.markdown("---")
    st.header("📜 القوانين الصارمة")
    st.markdown(
        "- **تطابق الحجم**: 100 مل = 100 مل فقط\n"
        "- **تطابق النوع**: Retail↔Retail, Tester↔Tester\n"
        "- **فيتو**: طرد العينات والتقسيمات تلقائياً\n"
        "- **التحقق البصري**: عرض اسم المنتج الأصلي"
    )

# =================================================================
# التبويبات
# =================================================================
tab_upload, tab_process, tab_results = st.tabs(
    ["📤 رفع الملفات", "⚙️ المعالجة", "📊 النتائج"]
)

# -----------------------------------------------------------------
# 1) رفع الملفات
# -----------------------------------------------------------------
with tab_upload:
    st.header("📤 رفع ملفات البيانات")
    col_my, col_comp = st.columns(2)

    with col_my:
        st.subheader("🏪 ملف متجرك")
        up_my = st.file_uploader(
            "ارفع ملف Excel أو CSV لمتجرك",
            type=["xlsx", "csv"],
            key="up_my",
        )
        if up_my is not None:
            st.session_state.my_file = {
                "name": up_my.name,
                "data": up_my.getvalue(),
            }
            st.success(f"✅ تم رفع: {up_my.name}")

    with col_comp:
        st.subheader("🏢 ملفات المنافسين")
        up_comp = st.file_uploader(
            "ارفع ملفات المنافسين (عدة ملفات)",
            type=["xlsx", "csv"],
            accept_multiple_files=True,
            key="up_comp",
        )
        if up_comp:
            st.session_state.comp_files = [
                {"name": f.name, "data": f.getvalue()}
                for f in up_comp
            ]
            st.success(f"✅ تم رفع {len(up_comp)} ملف منافس")

# -----------------------------------------------------------------
# 2) المعالجة
# -----------------------------------------------------------------
with tab_process:
    st.header("⚙️ بدء المعالجة والمقارنة")

    if st.button("🚀 ابدأ المعالجة الآن", use_container_width=True):
        if st.session_state.my_file is None:
            st.error("❌ يجب رفع ملف متجرك أولاً.")
        elif not st.session_state.comp_files:
            st.error("❌ يجب رفع ملف واحد على الأقل للمنافسين.")
        else:
            with st.spinner("⏳ جاري تحليل ومقارنة الأسعار..."):
                try:
                    engine = PerfumeMatchingEngine()
                    matches = engine.run_full_analysis(
                        st.session_state.my_file,
                        st.session_state.comp_files,
                        min_score,
                    )
                    if matches:
                        df = engine.build_master_dataframe(matches)
                        st.session_state.master_df = df
                        st.success(
                            f"🎉 اكتملت المعالجة! "
                            f"تم العثور على {len(df)} مقارنة. "
                            f"اذهب إلى تبويب النتائج."
                        )
                    else:
                        st.warning(
                            "⚠️ لم يتم العثور على مطابقات. "
                            "حاول تقليل نسبة التطابق أو تحقق من الملفات."
                        )
                except Exception as exc:
                    st.error(f"❌ حدث خطأ: {exc}")

# -----------------------------------------------------------------
# 3) النتائج
# -----------------------------------------------------------------
with tab_results:
    st.header("📊 نتائج المقارنة النهائية")

    df = st.session_state.master_df
    if df is not None and not df.empty:
        # إحصائيات سريعة
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 إجمالي", len(df))
        c2.metric("🔴 خاسر", len(df[df["القرار"] == "🔴 خاسر"]))
        c3.metric("🟢 قائد", len(df[df["القرار"] == "🟢 قائد"]))
        c4.metric("🟡 متعادل", len(df[df["القرار"] == "🟡 متعادل"]))

        st.markdown("---")

        # فلاتر
        competitors = df["المنافس"].unique().tolist()
        sel_comp = st.multiselect(
            "تصفية حسب المنافس:",
            options=competitors,
            default=competitors,
        )
        decisions = df["القرار"].unique().tolist()
        sel_dec = st.multiselect(
            "تصفية حسب القرار:",
            options=decisions,
            default=decisions,
        )

        filtered = df[
            df["المنافس"].isin(sel_comp) & df["القرار"].isin(sel_dec)
        ]

        st.dataframe(
            filtered,
            use_container_width=True,
            height=450,
            hide_index=True,
        )

        st.markdown("---")

        # تصدير
        col_xl, col_csv = st.columns(2)
        with col_xl:
            st.download_button(
                label="📥 تحميل Excel",
                data=_to_excel(filtered),
                file_name=f"report_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                use_container_width=True,
            )
        with col_csv:
            st.download_button(
                label="📥 تحميل CSV",
                data=filtered.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"report_{datetime.now():%Y%m%d_%H%M}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.info(
            "📋 لا توجد نتائج بعد. "
            "ارفع الملفات وابدأ المعالجة أولاً."
        )
