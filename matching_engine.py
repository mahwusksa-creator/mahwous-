# -*- coding: utf-8 -*-
"""
محرك المقارنة والمطابقة الصارم للعطور.

القوانين الصارمة (الدستور):
1. تطابق الحجم: 100 مل = 100 مل فقط
2. تطابق النوع: Retail مع Retail، Tester مع Tester
3. فيتو: طرد فوري للعينات والتقسيمات
4. التحقق البصري: عرض اسم المنتج الأصلي
"""

import re
from io import BytesIO
from typing import Any, Dict, List, Tuple

import pandas as pd
from rapidfuzz import fuzz, process


class PerfumeMatchingEngine:
    """محرك المقارنة الذكي والصارم للعطور."""

    REJECTED = ["عينة", "sample", "تقسيم", "decant"]
    TESTER = ["تستر", "tester", "testeur"]
    HAIR_MIST = ["عطر شعر", "hair mist"]
    BODY_MIST = ["body mist", "body spray", "ميست"]
    SET = ["طقم", "set", "مجموعة", "gift set"]

    NOISE = [
        "عطر", "perfume", "parfum", "ml", "مل",
        "edp", "edt", "eau", "de", "toilette",
        "spray", "intense", "original", "اصلي",
    ]

    # ------------------------------------------------------------------
    # أدوات داخلية
    # ------------------------------------------------------------------

    def _classify(self, name: str) -> Tuple[str, int, bool]:
        """تصنيف المنتج واستخراج الحجم."""
        low = str(name).lower()

        # 1) هل مرفوض؟
        if any(k in low for k in self.REJECTED):
            return "Rejected", 0, True

        # 2) تحديد النوع
        if any(k in low for k in self.SET):
            ptype = "Set"
        elif any(k in low for k in self.HAIR_MIST):
            ptype = "Hair Mist"
        elif any(k in low for k in self.BODY_MIST):
            ptype = "Body Mist"
        elif any(k in low for k in self.TESTER):
            ptype = "Tester"
        else:
            ptype = "Retail"

        # 3) استخراج الحجم
        m = re.search(r"(\d+)\s*(?:ml|مل)", low)
        size = int(m.group(1)) if m else 0

        return ptype, size, False

    def _fingerprint(self, name: str) -> str:
        """بصمة نظيفة للمقارنة."""
        if not isinstance(name, str):
            return ""
        txt = name.lower()
        txt = re.sub("[إأآا]", "ا", txt)
        txt = re.sub("ة", "ه", txt)
        for w in self.NOISE:
            txt = txt.replace(w, "")
        txt = re.sub(r"[^\w\s]", "", txt)
        txt = re.sub(r"\d+", "", txt)
        return " ".join(sorted(txt.split())).strip()

    # ------------------------------------------------------------------
    # قراءة الملفات
    # ------------------------------------------------------------------

    @staticmethod
    def _guess_columns(df: pd.DataFrame) -> Tuple[str, str]:
        """تخمين عمود الاسم وعمود السعر."""
        cols = list(df.columns)
        name_col = cols[0]
        price_col = cols[-1]
        for c in cols:
            cl = str(c).lower()
            if "اسم" in cl or "name" in cl or "منتج" in cl:
                name_col = c
            if "سعر" in cl or "price" in cl:
                price_col = c
        return name_col, price_col

    def _read_file(self, file_dict: Dict[str, Any]) -> pd.DataFrame:
        """قراءة ملف من قاموس {name, data}."""
        buf = BytesIO(file_dict["data"])
        fname = file_dict["name"].lower()
        if fname.endswith(".csv"):
            return pd.read_csv(buf)
        return pd.read_excel(buf, engine="openpyxl")

    def _load_products(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """تحويل DataFrame إلى قائمة منتجات مع بصمات."""
        name_col, price_col = self._guess_columns(df)
        products = []
        for _, row in df.iterrows():
            raw_name = str(row[name_col])
            ptype, size, rejected = self._classify(raw_name)
            if rejected:
                continue
            try:
                price = float(row[price_col])
            except (ValueError, TypeError):
                continue
            products.append({
                "name": raw_name,
                "price": price,
                "type": ptype,
                "size": size,
                "fp": self._fingerprint(raw_name),
            })
        return products

    # ------------------------------------------------------------------
    # المطابقة الصارمة
    # ------------------------------------------------------------------

    def run_full_analysis(
        self,
        my_file: Dict[str, Any],
        comp_files: List[Dict[str, Any]],
        min_score: int = 75,
    ) -> List[Dict[str, Any]]:
        """تشغيل التحليل الكامل: قراءة + مطابقة."""
        df_my = self._read_file(my_file)
        my_products = self._load_products(df_my)

        all_matches: List[Dict[str, Any]] = []

        for cf in comp_files:
            comp_name = cf["name"].rsplit(".", 1)[0]
            df_comp = self._read_file(cf)
            comp_products = self._load_products(df_comp)

            for my_p in my_products:
                if my_p["size"] == 0:
                    continue

                # فلترة صارمة: نفس النوع + نفس الحجم
                candidates = [
                    c for c in comp_products
                    if c["type"] == my_p["type"]
                    and c["size"] == my_p["size"]
                ]
                if not candidates:
                    continue

                # مطابقة الاسم
                fps = [c["fp"] for c in candidates]
                result = process.extractOne(
                    my_p["fp"], fps, scorer=fuzz.WRatio
                )
                if result is None or result[1] < min_score:
                    continue

                best = candidates[fps.index(result[0])]
                diff = best["price"] - my_p["price"]

                if diff < 0:
                    decision = "🔴 خاسر"
                elif diff > 0:
                    decision = "🟢 قائد"
                else:
                    decision = "🟡 متعادل"

                all_matches.append({
                    "اسم_منتجي": my_p["name"],
                    "نوع_المنتج": my_p["type"],
                    "سعري": my_p["price"],
                    "المنافس": comp_name,
                    "منتج_المنافس": best["name"],
                    "سعر_المنافس": best["price"],
                    "الحجم_مل": my_p["size"],
                    "الفرق": round(diff, 2),
                    "القرار": decision,
                    "نسبة_التطابق": round(result[1]),
                })

        return all_matches

    # ------------------------------------------------------------------
    # بناء الجدول النهائي
    # ------------------------------------------------------------------

    @staticmethod
    def build_master_dataframe(
        matches: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """تحويل قائمة المطابقات إلى DataFrame منسق."""
        cols = [
            "اسم_منتجي", "نوع_المنتج", "سعري",
            "المنافس", "منتج_المنافس", "سعر_المنافس",
            "الحجم_مل", "الفرق", "القرار", "نسبة_التطابق",
        ]
        df = pd.DataFrame(matches)
        return df[[c for c in cols if c in df.columns]]
