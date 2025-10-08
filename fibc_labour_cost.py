import streamlit as st
import pandas as pd
import altair as alt
import io
import base64

st.set_page_config(page_title="FIBC Labour Cost Sheet", layout="wide")

# Setup
unit_passwords = {
    "Thandya Hall-1": "th1pass",
    "Thandya Hall-2": "th2pass",
    "Himmavu": "himmpass",
    "Unit-3": "u3pass"
}
unit_lines = {
    "Thandya Hall-1": ["Line-1", "Line-2", "Line-3", "Line-4", "Line-8"],
    "Thandya Hall-2": ["Line-5A", "Line-5B", "Line-6", "Line-7"],
    "Himmavu": ["Line-1", "Line-2", "Line-3", "Line-4"],
    "Unit-3": ["Line-1", "Line-2", "Line-3", "Line-4"]
}
line_capacity_kg = {
    "Thandya Hall-1": {"Line-1": 2000, "Line-2": 1800, "Line-3": 2000, "Line-4": 2000, "Line-8": 1500},
    "Thandya Hall-2": {"Line-5A": 2000, "Line-5B": 1000, "Line-6": 2500, "Line-7": 2500},
    "Himmavu": {"Line-1": 1600, "Line-2": 1400, "Line-3": 1800, "Line-4": 2000},
    "Unit-3": {"Line-1": 2000, "Line-2": 1500, "Line-3": 1500, "Line-4": 1500}
}
grade_salary = {
    "A": 867, "A+": 867, "A++": 867, "B+": 867, "B": 867, "C": 867,
    "H": 665, "Q": 667, "Supervisor": 1300, "General": 1500
}
grade_options = list(grade_salary.keys())
tailor_options = list(range(1, 19))

# Session state
if "work_orders" not in st.session_state:
    st.session_state.work_orders = {}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.active_unit = None
    st.session_state.active_line = None
    st.session_state.edit_mode = False
    st.session_state.edit_order_id = None
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

# Login screen
if not st.session_state.logged_in and not st.session_state.admin_logged_in:
    st.title("🔐 Login")
    login_type = st.radio("Login as", ["Unit", "Admin"])
    if login_type == "Unit":
        selected_unit = st.selectbox("Select Unit", list(unit_passwords.keys()))
        selected_line = st.selectbox("Select Line", unit_lines[selected_unit])
        unit_pass = st.text_input("Unit Password", type="password")
        if st.button("Login as Unit"):
            if unit_pass == unit_passwords[selected_unit]:
                st.session_state.logged_in = True
                st.session_state.active_unit = selected_unit
                st.session_state.active_line = selected_line
                st.rerun()
            else:
                st.error("❌ Incorrect unit password")
    else:
        admin_user = st.text_input("Admin Username")
        admin_pass = st.text_input("Admin Password", type="password")
        if st.button("Login as Admin"):
            if admin_user == "rishifibc" and admin_pass == "Fibc$2025":
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ Invalid admin credentials")
    st.stop()

# Logout button
if st.session_state.logged_in or st.session_state.admin_logged_in:
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.admin_logged_in = False
        st.session_state.active_unit = None
        st.session_state.active_line = None
        st.session_state.edit_mode = False
        st.session_state.edit_order_id = None
        st.rerun()
if st.session_state.logged_in:
    selected_unit = st.session_state.active_unit
    selected_line = st.session_state.active_line
    shift_options = ["Shift-1", "Shift-2", "Shift-3"]
    criticallity_options = ["Low", "Medium", "High", "Very High"]

    st.title(f"🧵 Labour Costing – {selected_unit} / {selected_line}")
    col1, col2, col3 = st.columns(3)
    with col1:
        hall_no = st.text_input("Hall No", "")
    with col2:
        shift = st.selectbox("Shift", shift_options)
    with col3:
        work_order = st.text_input("Work Order No", "")
        customer = st.text_input("Customer", "")

    with st.expander("📋 Order Details"):
        po_number = st.text_input("P.Order No", "")
        spec_ref = st.text_input("Spec Ref", "")
        bag_type = st.text_input("Type of Bag", "")
        criticallity = st.selectbox("Criticallity", criticallity_options)
        order_qty = st.number_input("Order Quantity", min_value=0)
        bag_weight = st.number_input("Bag Weight (kg)", min_value=0.0)
        remarks = st.text_area("Remarks", "")
        bag_size = st.text_input("Bag Size", "")

    columns = ["Process", "No of Tailors", "Tailor Grade", "Production Target", "Remarks"]
    default_processes = [
        {"Process": "Cutting, Web cut,print & Kit", "No of Tailors": None, "Tailor Grade": "", "Production Target": None, "Remarks": ""},
        {"Process": "Bailing & Dispatch", "No of Tailors": None, "Tailor Grade": "", "Production Target": None, "Remarks": ""},
        {"Process": "Electricity/ Oil/Maintennance cost", "No of Tailors": None, "Tailor Grade": "", "Production Target": None, "Remarks": ""},
        {"Process": "General", "No of Tailors": 4, "Tailor Grade": "General", "Production Target": 1, "Remarks": ""},
        {"Process": "Supervisor (production & QA)", "No of Tailors": 2, "Tailor Grade": "Supervisor", "Production Target": 1, "Remarks": ""}
    ]
    extra_rows = [{"Process": "", "No of Tailors": None, "Tailor Grade": "", "Production Target": None, "Remarks": ""} for _ in range(30)]

    if st.session_state.edit_mode and st.session_state.edit_order_id:
        base_df = st.session_state.work_orders[st.session_state.edit_order_id]["Labour Cost Table"]
        base_df = base_df.drop(columns=["Sl.No"], errors="ignore")
        base_df = base_df.reindex(columns=columns).fillna("")
        base_df = base_df.head(35)
    else:
        base_df = pd.DataFrame((default_processes + extra_rows)[:35], columns=columns)

    st.subheader("🪡 Labour Process Entry")
    process_df = st.data_editor(
        base_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Tailor Grade": st.column_config.SelectboxColumn("Tailor Grade", options=grade_options),
            "No of Tailors": st.column_config.SelectboxColumn("No of Tailors", options=tailor_options),
            "Production Target": st.column_config.NumberColumn("Production Target", min_value=1, step=1)
        },
        hide_index=True,
        key="labour_editor"
    )

    process_df["Tailor Grade"] = process_df["Tailor Grade"].fillna("")
    process_df["No of Tailors"] = pd.to_numeric(process_df["No of Tailors"], errors="coerce").fillna(0)
    process_df["Production Target"] = pd.to_numeric(process_df["Production Target"], errors="coerce").replace(0, 1)

    def override_tailors(row):
        if row["Process"] == "Cutting, Web cut,print & Kit":
            return 5.59
        elif row["Process"] == "Bailing & Dispatch":
            return 1.1
        elif row["Process"] == "Electricity/ Oil/Maintennance cost":
            return 0.65
        else:
            return row["No of Tailors"]

    def auto_salary(row):
        return grade_salary.get(str(row["Tailor Grade"]).strip(), 0)

    def calculate_cost_pcs(row):
        if row["Process"] == "Cutting, Web cut,print & Kit":
            return 5.59 * bag_weight
        elif row["Process"] == "Bailing & Dispatch":
            return 1.1 * bag_weight
        elif row["Process"] == "Electricity/ Oil/Maintennance cost":
            return 0.65 * bag_weight
        else:
            return row["Total Salary/Day"] / row["Production Target"]

    process_df["No of Tailors"] = process_df.apply(override_tailors, axis=1)
    process_df["Salary/Day"] = process_df.apply(auto_salary, axis=1)
    process_df["Total Salary/Day"] = process_df["No of Tailors"] * process_df["Salary/Day"]
    process_df["Cost/Pcs"] = process_df.apply(calculate_cost_pcs, axis=1)
    process_df["Cost per kg"] = process_df["Cost/Pcs"] / bag_weight if bag_weight else 0
    process_df.insert(0, "Sl.No", range(1, len(process_df) + 1))
    display_df = process_df.drop(columns=["Salary/Day"], errors="ignore")

    st.subheader("📋 Labour Cost Table")
    st.dataframe(display_df)
    # Totals
    excluded = ["Cutting, Web cut,print & Kit", "Bailing & Dispatch", "Electricity/ Oil/Maintennance cost"]
    total_tailors = process_df[~process_df["Process"].isin(excluded)]["No of Tailors"].sum()
    total_salary = process_df["Total Salary/Day"].sum()
    total_cost_pcs = process_df["Cost/Pcs"].sum()
    total_cost_kgs = process_df["Cost per kg"].sum()

    total_row = pd.DataFrame([{
        "Unit": selected_unit,
        "Process": "Total",
        "No of Tailors": total_tailors,
        "Total Salary/Day": total_salary,
        "Cost/Pcs": total_cost_pcs,
        "Cost per kg": total_cost_kgs
    }])

    st.subheader("📊 Totals")
    st.dataframe(total_row)

    # Efficiency
    line_capacity = line_capacity_kg.get(selected_unit, {}).get(selected_line, 0)
    general_row = process_df[process_df["Process"] == "General"]
    general_target = general_row["Production Target"].values[0] if not general_row.empty else 0
    order_production_kg = general_target * bag_weight
    loss_production_kg = line_capacity - order_production_kg
    days_running = order_qty / general_target if general_target else 0
    total_loss_kg = days_running * loss_production_kg
    total_loss_cost = total_loss_kg * 35
    per_mt_loss = (total_loss_cost / total_loss_kg * 1000) if total_loss_kg else 0
    extra_conversion_usd = per_mt_loss / 86.1 if per_mt_loss else 0
    standard_conversion_usd = 856
    actual_expense_usd_per_mt = (total_cost_kgs / 86.1 * 1000) if total_cost_kgs else 0

    summary_data = {
        "Metric": [
            "Line Capacity",
            "From This Order Production",
            "Loss Production",
            "Days Running This Order",
            "Total Production Loss",
            "Total Loss in FIBC Avg Cost",
            "Per MT Loss in FIBC",
            "Extra Conversion Required (USD)",
            "Standard Conversion Considered",
            "FIBC Actual Expense per MT (USD)"
        ],
        "Value": [
            f"{line_capacity} kg",
            f"{order_production_kg:.2f} kg",
            f"{loss_production_kg:.2f} kg",
            f"{days_running:.2f} days",
            f"{total_loss_kg:.2f} kg",
            f"₹{total_loss_cost:,.2f}",
            f"₹{per_mt_loss:,.2f}",
            f"${extra_conversion_usd:,.2f}",
            f"${standard_conversion_usd:,.2f}",
            f"${actual_expense_usd_per_mt:,.2f}"
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    st.subheader("📉 Production Efficiency & Financial Impact")
    st.table(summary_df)

    # Save
    if st.button("💾 Save This Order", key="save_order_button"):
        if not work_order:
            next_id = len(st.session_state.work_orders) + 1
            work_order = f"WO-{next_id:03d}"
            st.info(f"ℹ️ Work Order No was auto-generated: {work_order}")
        else:
            work_order = work_order.strip()

        filtered_df = display_df[display_df["Process"].str.strip() != ""].copy()

        st.session_state.work_orders[work_order] = {
            "Month": pd.Timestamp.now().strftime("%B-%Y"),
            "Unit": selected_unit,
            "Hall No": hall_no,
            "Line No": selected_line,
            "Shift": shift,
            "Work Order No": work_order,
            "Customer": customer,
            "PO No": po_number,
            "Spec Ref": spec_ref,
            "Bag Type": bag_type,
            "Criticallity": criticallity,
            "Order Qty": order_qty,
            "Bag Weight": bag_weight,
            "Bag Size": bag_size,
            "Remarks": remarks,
            "Labour Cost Table": filtered_df,
            "Totals": total_row,
            "Financial Impact": summary_df
        }

        st.success(f"✅ Work Order '{work_order}' saved successfully!")
        st.session_state.edit_mode = False
        st.session_state.edit_order_id = None

    if not st.session_state.edit_mode:
        if st.button("🆕 Start New Work Order", key="new_order_button"):
            st.rerun()

    # View Work Orders for This Unit and Line
    st.subheader("📄 View Saved Work Orders")
    filter_month = st.selectbox("Filter by Month", ["All"] + sorted({data["Month"] for data in st.session_state.work_orders.values()}))
    filter_customer = st.text_input("Filter by Customer")
    filter_bag_type = st.text_input("Filter by Bag Type")

    filtered_orders = {
        wo: data for wo, data in st.session_state.work_orders.items()
        if data["Unit"] == selected_unit and data["Line No"] == selected_line
        and (filter_month == "All" or data["Month"] == filter_month)
        and (filter_customer.lower() in data["Customer"].lower() if filter_customer else True)
        and (filter_bag_type.lower() in data["Bag Type"].lower() if filter_bag_type else True)
    }

    if filtered_orders:
        selected_order = st.selectbox("Select Work Order", list(filtered_orders.keys()))
        order = filtered_orders[selected_order]

        st.markdown(f"### 📦 Work Order: {selected_order} – {order['Customer']}")
        st.write("🔹 PO No:", order["PO No"])
        st.write("🔹 Spec Ref:", order["Spec Ref"])
        st.write("🔹 Bag Type:", order["Bag Type"])
        st.write("🔹 Criticallity:", order["Criticallity"])
        st.write("🔹 Order Qty:", order["Order Qty"])
        st.write("🔹 Bag Weight:", order["Bag Weight"])
        st.write("🔹 Bag Size:", order["Bag Size"])
        st.write("🔹 Remarks:", order["Remarks"])

        st.subheader("🧵 Labour Cost Table")
        st.dataframe(order["Labour Cost Table"])

        st.subheader("📊 Totals")
        st.dataframe(order["Totals"])

        st.subheader("📉 Production Efficiency & Financial Impact")
        st.table(order["Financial Impact"])
    else:
        st.info("No saved work orders found for this line.")
if st.session_state.admin_logged_in:
    st.title("📊 Admin Summary Dashboard")
    search_term = st.text_input("🔍 Search by Customer, Hall, or Work Order")
    filter_month = st.selectbox("📅 Filter by Month", ["All"] + sorted({data["Month"] for data in st.session_state.work_orders.values()}))

    summary_rows = []
    for i, (wo_no, order) in enumerate(st.session_state.work_orders.items(), start=1):
        if search_term.lower() not in str(order).lower():
            continue
        if filter_month != "All" and order["Month"] != filter_month:
            continue

        cutting = 5.59
        bailing = 1.1
        power = 0.65
        spare = 0.87
        total = order["Totals"].iloc[0]["Cost per kg"]
        fibc_cost = total - (cutting + bailing + power + spare)

        summary_rows.append({
            "SL No": i,
            "Month": order["Month"],
            "Unit": order["Unit"],
            "Line": order["Line No"],
            "Shift": order["Shift"],
            "Customer": order["Customer"],
            "Work Order": wo_no,
            "Spec No": order["Spec Ref"],
            "Bag Type": order["Bag Type"],
            "Bag Weight": order["Bag Weight"],
            "Order Qty": order["Order Qty"],
            "FIBC Cost/kg (after deduction)": fibc_cost,
            "Cost/kg of Cutting": cutting,
            "Cost/kg of Bailing": bailing,
            "Cost/kg of Power": power,
            "Cost/kg of Spare": spare,
            "Total Cost/kg": total,
            "Critical": order["Criticallity"],
            "Remarks": order["Remarks"]
        })

    summary_df = pd.DataFrame(summary_rows)
    st.subheader("📋 Summary Table")
    st.dataframe(summary_df)

    # View full breakdown of any order
    st.subheader("📂 View Detailed Work Order")
    selected_order_id = st.selectbox("Select Work Order to View", list(st.session_state.work_orders.keys()))
    order = st.session_state.work_orders[selected_order_id]

    st.markdown(f"### 📦 Work Order: {selected_order_id} – {order['Customer']}")
    st.write("🔹 Month:", order["Month"])
    st.write("🔹 Hall No:", order["Hall No"])
    st.write("🔹 Line No:", order["Line No"])
    st.write("🔹 Shift:", order["Shift"])
    st.write("🔹 PO No:", order["PO No"])
    st.write("🔹 Spec Ref:", order["Spec Ref"])
    st.write("🔹 Bag Type:", order["Bag Type"])
    st.write("🔹 Criticallity:", order["Criticallity"])
    st.write("🔹 Order Qty:", order["Order Qty"])
    st.write("🔹 Bag Size:", order["Bag Size"])
    st.write("🔹 Bag Weight:", order["Bag Weight"])
    st.write("🔹 Cost/Kgs:", order["Totals"].iloc[0]["Cost per kg"])
    st.write("🔹 Remarks:", order["Remarks"])

    st.subheader("🧵 Labour Cost Table")
    st.dataframe(order["Labour Cost Table"])

    st.subheader("📉 Production Efficiency & Financial Impact")
    st.table(order["Financial Impact"])

    # Export summary sheet
    def export_summary_excel_grouped(df):
        output = io.BytesIO()
        grouped = df.sort_values(by=["Unit", "Line"])
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            grouped.to_excel(writer, index=False, sheet_name="All Units & Lines")
        output.seek(0)
        return output

    if st.button("📥 Download Full Summary Excel"):
        excel_data = export_summary_excel_grouped(summary_df)
        b64 = base64.b64encode(excel_data.read()).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="FIBC_Full_Summary.xlsx">📁 Click to download</a>'
        st.markdown(href, unsafe_allow_html=True)
def export_detailed_workbook(orders):
    import xlsxwriter

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        header_format = workbook.add_format({'bold': True, 'bg_color': '#DDEBF7'})
        table_format = workbook.add_format({'bg_color': '#F9F9F9'})
        alt_format = workbook.add_format({'bg_color': '#FFFFFF'})
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        label_format = workbook.add_format({'bold': True})

        for wo_no, order in orders.items():
            sheet_name = wo_no[:31]
            worksheet = workbook.add_worksheet(sheet_name)
            writer.sheets[sheet_name] = worksheet

            # Header
            worksheet.write("A1", f"FIBC Order wise Labour Cost Details Month of - {order['Month']}", title_format)

            # Order Details
            details = [
                ("Hall No", order["Hall No"]),
                ("Line No", order["Line No"]),
                ("Work Order No", wo_no),
                ("Customer", order["Customer"]),
                ("P.Order No", order["PO No"]),
                ("Spec Ref", order["Spec Ref"]),
                ("Type of Bag", order["Bag Type"]),
                ("Criticallity", order["Criticallity"]),
                ("Order Qty", order["Order Qty"]),
                ("Bag Size", order["Bag Size"]),
                ("Bag Weight", order["Bag Weight"]),
                ("Cost / Kgs", order["Totals"].iloc[0]["Cost per kg"]),
                ("Remarks", order["Remarks"])
            ]
            for i, (label, value) in enumerate(details, start=3):
                worksheet.write(f"A{i}", label, label_format)
                safe_value = "" if pd.isna(value) or value in [float("inf"), float("-inf")] else value
                worksheet.write(f"B{i}", safe_value)

            # Labour Cost Table
            start_row = len(details) + 5
            worksheet.write(start_row, 0, "Labour Cost Table", title_format)
            labour_df = order["Labour Cost Table"]
            for col_num, col_name in enumerate(labour_df.columns):
                worksheet.write(start_row + 1, col_num, col_name, header_format)
            for row_num, row in labour_df.iterrows():
                fmt = table_format if row_num % 2 == 0 else alt_format
                for col_num, value in enumerate(row):
                    safe_value = "" if pd.isna(value) or value in [float("inf"), float("-inf")] else value
                    worksheet.write(start_row + 2 + row_num, col_num, safe_value, fmt)

            # Efficiency Table
            eff_start = start_row + 4 + len(labour_df)
            worksheet.write(eff_start, 0, "Production Efficiency & Financial Impact", title_format)
            eff_df = order["Financial Impact"]
            for i, row in eff_df.iterrows():
                worksheet.write(eff_start + 1 + i, 0, row["Metric"], label_format)
                safe_value = "" if pd.isna(row["Value"]) or row["Value"] in [float("inf"), float("-inf")] else row["Value"]
                worksheet.write(eff_start + 1 + i, 1, safe_value, alt_format)

    output.seek(0)
    return output

# Button to trigger download
if st.session_state.admin_logged_in and st.button("📥 Download Full Costing Workbook"):
    excel_data = export_detailed_workbook(st.session_state.work_orders)
    b64 = base64.b64encode(excel_data.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="FIBC_WorkOrders.xlsx">📁 Click to download</a>'
    st.markdown(href, unsafe_allow_html=True)
