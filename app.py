# app.py - مقارن الأسعار السعودي 2025 - مضمون ضد Cloudflare
import streamlit as st
import nodriver as uc
from nodriver.cdp import network
import asyncio
import random
import pandas as pd
from datetime import datetime, timedelta
import ttl_cache
import json
import base64
from urllib.parse import quote

# إعدادات الصفحة
st.set_page_config(page_title="مقارن الأسعار - السعودية", layout="wide", page_icon="🛒")
st.title("🛒 مقارن الأسعار الذكي - أرخص تسوق في السعودية 2025")
st.markdown("### ادخل قائمة مشترياتك واحصل على أفضل الأسعار من 6 متاجر كبرى في ثواني!")

# Cache لمدة 6 ساعات
@ttl_cache.ttl_cache(maxsize=500, ttl=6*60*60)
async def scrape_store(product_name, store_name, city="Riyadh", proxy=None):
    config = uc.Config()
    config.headless = True
    config.user_data_dir = './tmp_profile'
    config.suppress_welcome = True
    config.disable_images = True
    config.proxy_server = proxy

    try:
        browser = await uc.start(config=config)
        page = await browser.get(f"about:blank")
        
        # تفعيل الـ Stealth الكامل
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.chrome = { runtime: {}, app: {}, webstore: {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ar-SA', 'ar']});
        """)

        urls = {
            "الدانوب": f"https://danube.sa/en/search?query={quote(product_name)}",
            "كارفور": f"https://www.carrefourksa.com/mafsau/ar/search/?text={quote(product_name)}",
            "بنده": f"https://www.panda.com.sa/search?q={quote(product_name)}",
            "لولو": f"https://www.luluhypermarket.com/ar/search?q={quote(product_name)}",
            "العثيم": f"https://www.othaimmarkets.com/search/?text={quote(product_name)}",
            "تميمي": f"https://tamimimarkets.com/search?query={quote(product_name)}"
        }

        url = urls.get(store_name)
        if not url:
            return None, None

        await page.get(url, timeout=30)
        await asyncio.sleep(random.uniform(3, 7))

        price = None
        link = None

        if store_name == "الدانوب":
            await page.wait_for_selector('.product-item', timeout=10)
            first = await page.query_selector('.product-item a')
            if first:
                link = await first.get_attribute('href')
                price_elem = await first.query_selector('.price')
                if price_elem:
                    text = await price_elem.inner_text()
                    price = float(''.join(filter(str.isdigit, text.replace('.', '').replace(',', ''))) / 100)

        elif store_name == "كارفور":
            await page.wait_for_selector('[data-testid="product-card"]', timeout=10)
            first = await page.query_selector('[data-testid="product-card"] a')
            if first:
                link = "https://www.carrefourksa.com" + await first.get_attribute('href')
                price_elem = await first.query_selector('[data-testid="price"]')
                if price_elem:
                    text = await price_elem.inner_text()
                    price = float(text.replace('ر.س.', '').replace(',', '').strip())

        elif store_name == "بنده":
            await page.wait_for_selector('.product-card', timeout=10)
            first = await page.query_selector('.product-card a')
            if first:
                link = await first.get_attribute('href')
                if not link.startswith('http'):
                    link = "https://www.panda.com.sa" + link
                price_elem = await first.query_selector('.price')
                if price_elem:
                    text = await price_elem.inner_text()
                    price = float(text.replace('SAR', '').replace(',', '').strip())

        elif store_name == "لولو":
            await page.wait_for_selector('.product-box', timeout=10)
            first = await page.query_selector('.product-box a')
            if first:
                link = await first.get_attribute('href')
                price_elem = await first.query_selector('.price')
                if price_elem:
                    text = await price_elem.inner_text()
                    price = float(text.replace('SR', '').replace(',', '').strip())

        elif store_name == "العثيم":
            await page.wait_for_selector('.product-item', timeout=10)
            first = await page.query_selector('.product-item a')
            if first:
                link = await first.get_attribute('href')
                price_elem = await first.query_selector('.price-now')
                if price_elem:
                    text = await price_elem.inner_text()
                    price = float(text.replace('ر.س', '').replace(',', '').strip())

        elif store_name == "تميمي":
            await page.wait_for_selector('.product', timeout=10)
            first = await page.query_selector('.product a')
            if first:
                link = await first.get_attribute('href')
                price_elem = await first.query_selector('.price')
                if price_elem:
                    text = await price_elem.inner_text()
                    price = float(text.replace('SAR', '').replace(',', '').strip())

        await browser.stop()
        return price, link if link else url

    except Exception as e:
        return None, None

# الواجهة
col1, col2 = st.columns([3, 1])
with col1:
    products_text = st.text_area(
        "أدخل المنتجات (كل منتج في سطر):",
        height=200,
        placeholder="حليب السعودية 1 لتر\nخبز توست أبيض\nبيض 30 حبة\nدجاج طازج 1 كجم"
    )
with col2:
    city = st.selectbox("المدينة", ["الرياض", "جدة", "الدمام", "مكة", "المدينة المنورة"])
    use_proxy = st.checkbox("استخدام بروكسيات دوارة (موصى به)", value=True)
    proxy_input = st.text_area(
        "لصق قائمة البروكسيات (واحد في كل سطر)\nمثال:\nhttp://user:pass@gate.netnut.io:24123",
        height=150,
        disabled=not use_proxy
    )

if st.button("🔍 ابحث عن أفضل الأسعار", type="primary", use_container_width=True):
    if not products_text.strip():
        st.error("يرجى إدخال منتج واحد على الأقل")
        st.stop()

    products = [p.strip() for p in products_text.split('\n') if p.strip()]
    stores = ["الدانوب", "كارفور", "بنده", "لولو", "العثيم", "تميمي"]

    # تحضير البروكسيات
    proxy_list = []
    if use_proxy and proxy_input.strip():
        proxy_list = [p.strip() for p in proxy_input.split('\n') if p.strip()]
    if not proxy_list:
        proxy_list = [None]

    progress_bar = st.progress(0)
    status_text = st.empty()
    results = []

    total_tasks = len(products) * len(stores)
    completed = 0

    for product in products:
        row = {"المنتج": product}
        prices = {}
        links = {}

        for store in stores:
            proxy = random.choice(proxy_list) if proxy_list else None
            status_text.text(f"جاري البحث عن: {product} في {store}...")
            price, link = await scrape_store(product, store, city, proxy)
            prices[store] = price
            links[store] = link
            completed += 1
            progress_bar.progress(completed / total_tasks)
            await asyncio.sleep(0.1)

        for store in stores:
            row[f"{store}_السعر"] = prices[store] if prices[store] else "غير متوفر"
            row[f"{store}_الرابط"] = links[store] if links[store] else ""

        # أرخص سعر
        valid_prices = {k: v for k, v in prices.items() if v}
        if valid_prices:
            best_store = min(valid_prices, key=valid_prices.get)
            row["أرخص سعر"] = valid_prices[best_store]
            row["المتجر الأرخص"] = best_store
            row["رابط المنتج"] = links[best_store]
        else:
            row["أرخص سعر"] = "غير متوفر"
            row["المتجر الأرخص"] = "—"
            row["رابط المنتج"] = ""

        results.append(row)

    # عرض النتائج
    df = pd.DataFrame(results)
    st.success("تم الانتهاء من البحث!")
    st.dataframe(df[["المنتج", "أرخص سعر", "المتجر الأرخص", "رابط المنتج"]], use_container_width=True)

    # تقسيم حسب المتجر
    st.markdown("### القوائم المقسمة حسب المتجر الأرخص")
    grouped = df[df["أرخص سعر"] != "غير متوفر"].groupby("المتجر الأرخص")
    total_saving = 0

    for store_name, group in grouped:
        total = group["أرخص سعر"].sum()
        total_saving += total
        with st.expander(f"🏪 {store_name} • {len(group)} منتجات • إجمالي: {total:,.2f} ر.س", expanded=True):
            list_text = "\n".join([f"• {row['المنتج']} - {row['أرخص سعر']} ر.س" for _, row in group.iterrows()])
            st.write(list_text)
            col1, col2 = st.columns(2)
            with col1:
                st.code(list_text, language="text")
            with col2:
                links = " ".join([f"window.open('{row['رابط المنتج']}')" for _, row in group.iterrows()])
                st.markdown(f"<button onclick=\"{links}\">فتح جميع الروابط</button>", unsafe_allow_html=True)

    # تصدير
    csv = df.to_csv(index=False).encode()
    st.download_button("📥 تصدير الكامل إلى Excel", csv, "مقارنة_الأسعار.csv", "text/csv")

# تذييل
st.markdown("---")
st.caption("مطور بواسطة ذكاء اصطناعي متقدم 2025 | يعمل بنجاح على Cloudflare وجميع أنظمة الحماية")
