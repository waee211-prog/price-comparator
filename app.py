import streamlit as st
import pandas as pd
import time
import random
import asyncio
from io import BytesIO
import plotly.express as px

# إعدادات الصفحة
st.set_page_config(
    page_title="مقارن الأسعار الذكي",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- دوال مساعدة (Simulation) ---

async def simulate_search_product(product_name, store_name, proxy=None):
    """دالة تحاكي عملية البحث عن منتج في متجر معين"""
    delay = random.uniform(0.3, 1.5)
    await asyncio.sleep(delay)
    
    # جعل النتائج أكثر واقعية
    base_prices = {
        "حليب المراعي": 18, "أرز بسمتي": 28, "زيت نباتي": 35,
        "سكر": 12, "دقيق": 9, "مكرونة": 7, "شاي": 25, "قهوة": 45,
        "تمر": 40, "عسل": 60, "مياه معبأة": 5
    }
    
    base_price = base_prices.get(product_name, random.randint(10, 200))
    
    # احتمالية عدم التوفر تختلف حسب المتجر
    availability_rates = {
        "الدانوب": 0.95, "كارفور": 0.92, "بنده": 0.94,
        "لولو ماركت": 0.90, "العثيم": 0.88, "التميمي": 0.93
    }
    
    if random.random() > availability_rates.get(store_name, 0.9):
        return None
    
    has_discount = random.random() < 0.3  # 30% فرصة للتخفيض
    
    price = base_price
    original_price = base_price
    discount_percent = 0
    
    if has_discount:
        discount_percent = random.randint(5, 30)
        price = base_price * (1 - discount_percent / 100)
        price = round(price, 2)

    return {
        "product_name": product_name,
        "store": store_name,
        "price": price,
        "original_price": original_price if has_discount else None,
        "discount_percent": discount_percent if has_discount else 0,
        "url": f"https://www.{store_name.replace(' ', '').lower()}.sa/search?q={product_name}",
        "available": True,
        "delivery_time": random.randint(1, 5)
    }

async def process_products(products_list, selected_stores):
    results = []
    
    # شريط التقدم
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_operations = len(products_list) * len(selected_stores)
    completed_operations = 0
    
    tasks = []
    
    for product in products_list:
        if not product.strip():
            continue
        for store in selected_stores:
            tasks.append(simulate_search_product(product, store))
    
    # تنفيذ المهام بشكل متوازي
    batch_results = await asyncio.gather(*tasks)
    
    for res in batch_results:
        completed_operations += 1
        progress = completed_operations / total_operations
        progress_bar.progress(progress)
        if res:
            results.append(res)
            
    status_text.text("تم الانتهاء من المعالجة!")
    time.sleep(0.5)
    status_text.empty()
    progress_bar.empty()
    
    return results

# --- دوال التنسيق والتصفية ---

def highlight_cheapest(row, df):
    """تلوين أرخص سعر لكل منتج"""
    min_price = df[df['product_name'] == row['product_name']]['price'].min()
    if row['price'] == min_price:
        return ['background-color: #e6f7e6'] * len(row)
    return [''] * len(row)

# --- واجهة المستخدم ---

def main():
    st.title("🛒 مقارن أسعار المنتجات الذكي")
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 10px;
        border-right: 5px solid #2E86AB;
    }
    </style>
    
    <div class="info-box">
    <strong>💡 تطبيق ذكي لمقارنة أسعار المنتجات بين المتاجر المختلفة</strong><br>
    أدخل قائمة المنتجات واختر المتاجر لمقارنة الأسعار وإيجاد أفضل العروض
    </div>
    """, unsafe_allow_html=True)

    # --- القائمة الجانبية ---
    st.sidebar.header("⚙️ إعدادات البحث")
    
    city = st.sidebar.selectbox(
        "اختر المدينة",
        ["الرياض", "جدة", "الدمام", "مكة المكرمة", "المدينة المنورة", "جميع المدن"]
    )
    
    use_proxy = st.sidebar.toggle("تفعيل البروكسي (محاكاة)", value=False)
    proxy_list = ""
    if use_proxy:
        proxy_list = st.sidebar.text_area("أدخل قائمة البروكسي (اختياري)", 
                                        placeholder="http://user:pass@host:port\nhttp://user:pass@host:port")

    st.sidebar.markdown("---")
    st.sidebar.info("""
    **ℹ️ معلومات عن التطبيق:**
    - يحاكي البحث في المتاجر الحقيقية
    - يعرض أفضل الأسعار والعروض
    - يحسب إجمالي التوفير المتوقع
    - يدعم التحميل بصيغة Excel
    """)

    # --- المدخلات الرئيسية ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 قائمة المنتجات")
        products_input = st.text_area(
            "أدخل قائمة المنتجات (كل منتج في سطر)",
            height=150,
            placeholder="مثال:\nحليب المراعي\nأرز بسمتي\nزيت نباتي\nسكر\nدقيق",
            help="اكتب كل منتج في سطر منفصل"
        )
    
    with col2:
        st.subheader("🏪 المتاجر")
        stores = [
            "الدانوب", "كارفور", "بنده", 
            "لولو ماركت", "العثيم", "التميمي"
        ]
        selected_stores = []
        for store in stores:
            if st.checkbox(store, value=True, key=store):
                selected_stores.append(store)
        
        st.markdown("---")
        if st.button("✅ تحديد الكل", key="select_all"):
            selected_stores = stores
        if st.button("❌ إلغاء الكل", key="deselect_all"):
            selected_stores = []

    start_btn = st.button("🔍 بدء مقارنة الأسعار", type="primary", use_container_width=True)

    # --- معالجة النتائج ---
    if start_btn and products_input:
        products = [p.strip() for p in products_input.split('\n') if p.strip()]
        
        if not products:
            st.warning("⚠️ الرجاء إدخال منتجات صالحة.")
            return

        if not selected_stores:
            st.warning("⚠️ الرجاء اختيار متجر واحد على الأقل.")
            return

        with st.spinner('🔄 جاري البحث ومقارنة الأسعار...'):
            results = asyncio.run(process_products(products, selected_stores))
        
        if not results:
            st.error("❌ لم يتم العثور على نتائج. حاول مرة أخرى.")
            return

        # تحويل النتائج إلى DataFrame
        df = pd.DataFrame(results)
        
        # --- خيارات التصفية والترتيب ---
        st.markdown("---")
        st.subheader("🔍 خيارات التصفية والترتيب")
        
        col_filter1, col_filter2, col_filter3 = st.columns(3)

        with col_filter1:
            sort_by = st.selectbox("ترتيب النتائج حسب:", 
                                ["السعر (من الأقل)", "السعر (من الأعلى)", "المتجر", "المنتج"])

        with col_filter2:
            selected_stores_filter = st.multiselect("تصفية حسب المتجر:", stores, default=selected_stores)

        with col_filter3:
            min_price, max_price = st.slider("نطاق السعر:", 0, 200, (0, 200), help="حدد نطاق السعر المطلوب")

        # تطبيق التصفية والترتيب
        filtered_df = df[
            (df['store'].isin(selected_stores_filter)) & 
            (df['price'] >= min_price) & 
            (df['price'] <= max_price)
        ]
        
        if sort_by == "السعر (من الأقل)":
            filtered_df = filtered_df.sort_values('price')
        elif sort_by == "السعر (من الأعلى)":
            filtered_df = filtered_df.sort_values('price', ascending=False)
        elif sort_by == "المتجر":
            filtered_df = filtered_df.sort_values('store')
        elif sort_by == "المنتج":
            filtered_df = filtered_df.sort_values('product_name')

        # --- عرض الجدول التفصيلي ---
        st.subheader("📋 نتائج مقارنة الأسعار")
        
        # تنسيق العرض
        display_df = filtered_df.copy()
        display_df['السعر'] = display_df['price'].apply(lambda x: f"{x:.2f} ر.س")
        display_df['السعر الأصلي'] = display_df['original_price'].apply(
            lambda x: f"<s>{x:.2f} ر.س</s>" if pd.notnull(x) else "-"
        )
        display_df['التخفيض'] = display_df['discount_percent'].apply(
            lambda x: f"🟢 {x}%" if x > 0 else "-"
        )

        # تطبيق التلوين على أرخص الأسعار
        styled_df = display_df.style.format({
            'السعر الأصلي': lambda x: x
        }).apply(lambda row: highlight_cheapest(row, filtered_df), axis=1)

        st.dataframe(
            styled_df[['product_name', 'store', 'السعر', 'السعر الأصلي', 'التخفيض', 'url']],
            column_config={
                "product_name": "المنتج",
                "store": "المتجر", 
                "url": st.column_config.LinkColumn("رابط الشراء", display_text="🛒 اشتري الآن")
            },
            use_container_width=True,
            hide_index=True
        )

        # --- الرسوم البيانية ---
        st.markdown("---")
        st.subheader("📊 مقارنة مرئية بين المتاجر")
        
        if not filtered_df.empty:
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # رسم بياني شريطي لمتوسط الأسعار
                avg_prices = filtered_df.groupby('store')['price'].mean().reset_index()
                fig1 = px.bar(avg_prices, x='store', y='price',
                             title='متوسط الأسعار حسب المتجر',
                             labels={'store': 'المتجر', 'price': 'متوسط السعر (ر.س)'},
                             color='price')
                st.plotly_chart(fig1, use_container_width=True)
            
            with col_chart2:
                # رسم بياني للمنتجات
                fig2 = px.scatter(filtered_df, x='store', y='price', color='product_name',
                                title='توزيع أسعار المنتجات بين المتاجر',
                                labels={'store': 'المتجر', 'price': 'السعر (ر.س)'})
                st.plotly_chart(fig2, use_container_width=True)

        # --- التحليل الذكي ---
        st.markdown("---")
        st.subheader("🏆 التحليل الذكي: أين تشتري؟")

        # إيجاد أرخص سعر لكل منتج
        cheapest_products = filtered_df.loc[filtered_df.groupby('product_name')['price'].idxmin()]
        
        # تجميع حسب المتجر
        store_stats = cheapest_products.groupby('store').agg(
            عدد_المنتجات=('product_name', 'count'),
            إجمالي_السعر=('price', 'sum')
        ).reset_index().sort_values('إجمالي_السعر')

        if not store_stats.empty:
            best_store = store_stats.iloc[0]
            
            col_res1, col_res2 = st.columns(2)
            
            with col_res1:
                st.success(f"**🏆 الخيار الأوفر:** {best_store['store']}")
                st.metric("عدد المنتجات الأرخص لديهم", f"{best_store['عدد_المنتجات']} منتج")
                st.metric("إجمالي الفاتورة المتوقع", f"{best_store['إجمالي_السعر']:.2f} ر.س")

            with col_res2:
                st.write("**💰 تفاصيل التوفير:**")
                # حساب متوسط الأسعار للمقارنة
                avg_market_price = filtered_df.groupby('product_name')['price'].mean().sum()
                savings = avg_market_price - best_store['إجمالي_السعر']
                savings_percent = (savings / avg_market_price) * 100 if avg_market_price > 0 else 0
                
                st.metric("متوسط سعر السوق", f"{avg_market_price:.2f} ر.س")
                st.metric("إجمالي التوفير", f"{savings:.2f} ر.س", 
                         delta=f"-{savings_percent:.1f}%", delta_color="normal")

        # --- الإحصائيات العامة ---
        st.markdown("---")
        st.subheader("📈 إحصائيات عامة")
        
        if not filtered_df.empty:
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            with col_stat1:
                total_products = filtered_df['product_name'].nunique()
                st.metric("عدد المنتجات", total_products)
            
            with col_stat2:
                total_stores = filtered_df['store'].nunique()
                st.metric("عدد المتاجر", total_stores)
            
            with col_stat3:
                avg_price = filtered_df['price'].mean()
                st.metric("متوسط الأسعار", f"{avg_price:.2f} ر.س")
            
            with col_stat4:
                total_discounts = (filtered_df['discount_percent'] > 0).sum()
                st.metric("عروض التخفيض", total_discounts)

        # --- نصائح التوفير ---
        st.info("""
        💡 **نصائح ذكية للتوفير:**
        - ✨ قارن الأسعار بين 3 متاجر على الأقل قبل الشراء
        - 🎯 تابع عروض نهاية الأسبوع والمناسبات
        - 📦 فكر في الشراء بكميات كبيرة للمواد الأساسية
        - 🔔 اشترك في نشرات المتاجر الإلكترونية للحصول على أحدث العروض
        """)

        # --- التصدير ---
        st.markdown("---")
        st.subheader("💾 حفظ النتائج")
        
        col_export1, col_export2 = st.columns(2)
        
        with col_export1:
            # تحويل لملف Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='نتائج_مقارنة_الأسعار')
                workbook = writer.book
                worksheet = writer.sheets['نتائج_مقارنة_الأسعار']
                format1 = workbook.add_format({'num_format': '#,##0.00'})
                worksheet.set_column('C:C', None, format1)
            
            excel_data = output.getvalue()
            
            st.download_button(
                label="📥 تحميل النتائج (Excel)",
                data=excel_data,
                file_name="نتائج_مقارنة_الأسعار.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col_export2:
            # تصدير كـ CSV
            csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📄 تحميل النتائج (CSV)",
                data=csv_data,
                file_name="نتائج_مقارنة_الأسعار.csv",
                mime="text/csv",
                use_container_width=True
            )

    elif start_btn and not products_input:
        st.warning("⚠️ الرجاء إدخال قائمة المنتجات أولاً.")

# تشغيل التطبيق
if __name__ == "__main__":
    main()
