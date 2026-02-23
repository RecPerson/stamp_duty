import tkinter as tk
from tkinter import ttk, messagebox

# =========================
# Money-safe helpers
# =========================
def round_up_to(value: float, step_dollars: int) -> float:
    """
    Round value UP to the next multiple of `step_dollars` using integer cents
    to avoid binary floating-point precision issues.
    Example: round_up_to(110000.00, 100) -> 110000.00  (NOT 110100.00)
    """
    step_cents = step_dollars * 100
    value_cents = int(round(value * 100))  # normalize to exact cents
    rounded_cents = ((value_cents + step_cents - 1) // step_cents) * step_cents
    return rounded_cents / 100.0


def fmt_money(x: float) -> str:
    return f"${x:,.2f}"


def fmt_pct(x: float) -> str:
    return f"{x:.2%}"


# =========================
# GST helpers
# =========================
def gst_is_inclusive(mode: str) -> bool:
    return mode == "GST inclusive"


def to_inclusive(amount: float, mode: str) -> float:
    return amount if gst_is_inclusive(mode) else amount * 1.10


def to_exclusive(amount: float, mode: str) -> float:
    return amount if not gst_is_inclusive(mode) else amount / 1.10


# =========================
# Business Logic
# =========================
def calculate_all(
    state: str,
    price_entered: float,
    costs_entered: float,
    discount_entered: float,
    null_gst: float,
    gst_mode: str,
    lct_choice: str,                # "Fuel Efficient" | "Not Fuel Efficient" | "Exempt"
    qld_base: str = "New/Used",     # "New/Used" | "GVM"
    qld_cyl: str = "electric/hybrid",  # "electric/hybrid" | "1-4 cylinders" | "5-6 cylinders" | "7+ cylinders"
    tas_vehicle_type: str = "passenger (< 9 people and not utes, motor cycles, panel vans)",
    vic_category: str = "Private (passenger)"
):
    lines = []
    lines.append("=== Inputs & GST Mode ===")
    lines.append(f"GST Mode: {gst_mode}")
    lines.append(f"Price entered: {fmt_money(price_entered)}")
    lines.append(f"Other GSTable costs: {fmt_money(costs_entered)}")
    lines.append(f"Discount entered: {fmt_money(discount_entered)}")
    lines.append(f"CTP/rego (no GST): {fmt_money(null_gst)}")
    lines.append("")

    # Normalize for general invoice totals (GST calc, LCT thresholds use GST-inclusive)
    price_incl = to_inclusive(price_entered, gst_mode)
    costs_incl = to_inclusive(costs_entered, gst_mode)
    discount_incl = to_inclusive(discount_entered, gst_mode)

    lines.append("=== GST-normalized values (for invoice/LCT thresholds) ===")
    lines.append(f"Price (incl GST): {fmt_money(price_incl)}")
    lines.append(f"Costs (incl GST): {fmt_money(costs_incl)}")
    lines.append(f"Discount (incl GST): {fmt_money(discount_incl)}")
    lines.append("")

    # --- LCT (Luxury Car Tax) ---
    lct_base = price_incl + costs_incl
    LCT_FUEL_EFFICIENT_THRESHOLD = 91_387.0
    LCT_NON_EFFICIENT_THRESHOLD  = 80_567.0
    LCT_RATE = 0.33
    LCT_amount = 0.0

    lines.append("=== LCT Calculation ===")
    lines.append(f"LCT category: {lct_choice}")
    lines.append(f"LCT base (price + costs, incl GST): {fmt_money(lct_base)}")
    if lct_choice == "Fuel Efficient":
        thr = LCT_FUEL_EFFICIENT_THRESHOLD
        lines.append(f"Threshold (fuel efficient): {fmt_money(thr)}")
        if lct_base > thr:
            taxable = lct_base - thr
            lines.append(f"Amount above threshold: {fmt_money(taxable)}")
            lines.append(f"LCT rate: {fmt_pct(LCT_RATE)}")
            lines.append("LCT is on GST-inclusive component; amount is multiplied by 10/11 to remove GST.")
            LCT_amount = taxable * LCT_RATE * 10 / 11
            lines.append(f"LCT payable: {fmt_money(LCT_amount)}")
        else:
            lines.append("Below threshold: LCT = $0.00")
    elif lct_choice == "Not Fuel Efficient":
        thr = LCT_NON_EFFICIENT_THRESHOLD
        lines.append(f"Threshold (non-fuel efficient): {fmt_money(thr)}")
        if lct_base > thr:
            taxable = lct_base - thr
            lines.append(f"Amount above threshold: {fmt_money(taxable)}")
            lines.append(f"LCT rate: {fmt_pct(LCT_RATE)}")
            lines.append("LCT is on GST-inclusive component; amount is multiplied by 10/11 to remove GST.")
            LCT_amount = taxable * LCT_RATE * 10 / 11
            lines.append(f"LCT payable: {fmt_money(LCT_amount)}")
        else:
            lines.append("Below threshold: LCT = $0.00")
    else:
        lines.append("Exempt: LCT = $0.00")
    lines.append("")

    # --- State duty ---
    stamp_duty = 0.0
    rounded_dutiable = 0.0

    lines.append("=== Stamp Duty Calculation ===")
    lines.append(f"State: {state}")

    if state == "Queensland":
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")

        over_100k = rounded_dutiable > 100_000
        lines.append(f"Base type: {qld_base}")
        lines.append(f"Vehicle type: {qld_cyl}")
        lines.append(f"Threshold > $100,000? {'Yes' if over_100k else 'No'}")

        if qld_base == "New/Used":
            if qld_cyl == "electric/hybrid":
                rate = 4.0 if over_100k else 2.0
            elif qld_cyl == "1-4 cylinders":
                rate = 5.0 if over_100k else 3.0
            elif qld_cyl == "5-6 cylinders":
                rate = 5.5 if over_100k else 3.5
            elif qld_cyl == "7+ cylinders":
                rate = 6.0 if over_100k else 4.0
            else:
                rate = 0.0
        elif qld_base == "GVM":
            if qld_cyl == "electric/hybrid":
                rate = 2.0
            elif qld_cyl == "1-4 cylinders":
                rate = 3.0
            elif qld_cyl == "5-6 cylinders":
                rate = 3.5
            elif qld_cyl == "7+ cylinders":
                rate = 4.0
            else:
                rate = 0.0
        else:
            rate = 0.0

        lines.append(f"Duty rate applied: {rate:.2f}%")
        stamp_duty = rounded_dutiable * rate / 100.0
        lines.append(f"Stamp duty = {fmt_money(rounded_dutiable)} × {rate:.2f}% = {fmt_money(stamp_duty)}")

    elif state == "Tasmania":
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")

        vt = tas_vehicle_type
        lines.append(f"Vehicle type: {vt}")

        if vt.startswith("passenger"):
            if rounded_dutiable <= 600:
                stamp_duty = 20
                lines.append("Passenger ≤ $600: flat $20 duty.")
            elif rounded_dutiable <= 35_000:
                stamp_duty = rounded_dutiable * 0.03
                lines.append("Passenger $601–$35,000: 3% of dutiable value.")
            elif rounded_dutiable <= 40_000:
                stamp_duty = 1_050 + ((rounded_dutiable - 35_000) * 0.11)
                lines.append("Passenger $35,001–$40,000: $1,050 + 11% of amount over $35,000.")
            else:
                stamp_duty = rounded_dutiable * 0.04
                lines.append("Passenger > $40,000: 4% of dutiable value.")
        elif vt.startswith("commercial up to 4.5t"):
            stamp_duty = rounded_dutiable * 0.03
            lines.append("Commercial ≤ 4.5t: 3% of dutiable value.")
        elif vt.startswith("commercial more than 4.5t"):
            stamp_duty = rounded_dutiable * 0.01
            lines.append("Commercial > 4.5t: 1% of dutiable value.")
        elif vt.startswith("manufacturer fleet"):
            stamp_duty = rounded_dutiable * 0.035
            lines.append("Manufacturer fleet: 3.5% of dutiable value.")
        lines.append(f"Stamp duty: {fmt_money(stamp_duty)}")

    elif state == "New South Wales":
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")

        if rounded_dutiable <= 44_900:
            stamp_duty = rounded_dutiable * 0.03
            lines.append("NSW tier ≤ $44,900: 3% of dutiable value.")
        else:
            stamp_duty = 1_350 + (rounded_dutiable - 45_000) * 0.05
            lines.append("NSW tier > $44,900: $1,350 + 5% of amount over $45,000.")
        lines.append(f"Stamp duty: {fmt_money(stamp_duty)}")

    elif state == "Victoria":
        # VIC build-up is EX-GST -> apply GST once -> add LCT -> round UP to $200
        price_ex = to_exclusive(price_entered, gst_mode)
        discount_ex = to_exclusive(discount_entered, gst_mode)
        vic_dutiable_ex = max(price_ex - discount_ex, 0.0)
        vic_dutiable_incl = vic_dutiable_ex * 1.10
        vic_plus_lct = vic_dutiable_incl + LCT_amount

        lines.append("VIC build-up:")
        lines.append(f"  EX-GST base (price - discount): {fmt_money(vic_dutiable_ex)}")
        lines.append(f"  Add GST once (×1.10): {fmt_money(vic_dutiable_incl)}")
        lines.append(f"  Add LCT: {fmt_money(LCT_amount)} → {fmt_money(vic_plus_lct)} before rounding")

        rounded_dutiable = round_up_to(vic_plus_lct, 200)
        lines.append(f"  Round up to next $200: {fmt_money(rounded_dutiable)}")

        def vic_passenger_rate(value: float) -> float:
            if value <= 80_567:
                return 0.042
            elif value <= 100_000:
                return 0.052
            elif value <= 150_000:
                return 0.070
            else:
                return 0.090

        lines.append(f"Category: {vic_category}")
        if vic_category == "Private (passenger)":
            rate = vic_passenger_rate(rounded_dutiable)
            lines.append(f"Passenger tiered rate applied: {fmt_pct(rate)}")
        elif vic_category == "Low emission (passenger)":
            rate = 0.042
            lines.append("Low emission passenger: 4.2%")
        elif vic_category == "Primary producer (passenger)":
            rate = 0.042
            lines.append("Primary producer passenger: 4.2%")
        elif vic_category == "Commercial (new registration)":
            rate = 0.027
            lines.append("Commercial (new): 2.7%")
        elif vic_category == "Commercial (used/transfer)":
            rate = 0.042
            lines.append("Commercial (used/transfer): 4.2%")
        elif vic_category == "Demonstrator (passenger)":
            rate = vic_passenger_rate(rounded_dutiable)
            lines.append(f"Demonstrator passenger (tiered): {fmt_pct(rate)}")
        elif vic_category == "Demo commercial (used/transfer)":
            rate = 0.042
            lines.append("Demo commercial (used/transfer): 4.2%")
        else:
            rate = vic_passenger_rate(rounded_dutiable)
            lines.append(f"Default passenger tiered rate: {fmt_pct(rate)}")

        stamp_duty = rounded_dutiable * rate
        lines.append(f"Stamp duty = {fmt_money(rounded_dutiable)} × {fmt_pct(rate)} = {fmt_money(stamp_duty)}")

    elif state == "South Australia":
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")

        if rounded_dutiable <= 45_000:
            stamp_duty = rounded_dutiable * 0.03
            lines.append("SA tier ≤ $45,000: 3% of dutiable value.")
        elif rounded_dutiable <= 60_000:
            stamp_duty = 1_350 + (rounded_dutiable - 45_000) * 0.04
            lines.append("SA $45,001–$60,000: $1,350 + 4% of amount over $45,000.")
        else:
            stamp_duty = 1_950 + (rounded_dutiable - 60_000) * 0.05
            lines.append("SA > $60,000: $1,950 + 5% of amount over $60,000.")
        lines.append(f"Stamp duty: {fmt_money(stamp_duty)}")

    else:
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")
        lines.append("No duty calculation implemented for this state.")
        stamp_duty = 0.0

    lines.append("")
    lines.append("=== Invoice Totals ===")
    GST_component = (price_incl + costs_incl - discount_incl) / 11.0
    total = price_incl + costs_incl + stamp_duty + null_gst - discount_incl + LCT_amount
    lines.append(f"GST component (1/11 of GSTable items): {fmt_money(GST_component)}")
    lines.append(f"Rounded dutiable value used: {fmt_money(rounded_dutiable)}")
    lines.append(f"Stamp duty: {fmt_money(stamp_duty)}")
    lines.append(f"LCT: {fmt_money(LCT_amount)}")
    lines.append(f"Total purchase price: {fmt_money(total)}")

    breakdown = "\n".join(lines)

    return {
        "rounded_dutiable": rounded_dutiable,
        "stamp_duty": stamp_duty,
        "GST": GST_component,
        "LCT": LCT_amount,
        "total": total,
        "breakdown": breakdown,
    }


# =========================
# Minimal Tkinter UI with breakdown panel
# =========================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stamp Duty Calculator (Fixed Rounding + Breakdown)")
        self.geometry("820x680")

        # Vars
        self.state_var = tk.StringVar(value="Queensland")
        self.gst_mode_var = tk.StringVar(value="GST inclusive")
        self.price_var = tk.StringVar()
        self.costs_var = tk.StringVar()
        self.discount_var = tk.StringVar()
        self.null_gst_var = tk.StringVar()
        self.lct_var = tk.StringVar(value="Exempt")

        self.qld_base_var = tk.StringVar(value="New/Used")
        self.qld_cyl_var = tk.StringVar(value="electric/hybrid")

        self.tas_vt_var = tk.StringVar(value="passenger (< 9 people and not utes, motor cycles, panel vans)")
        self.vic_cat_var = tk.StringVar(value="Private (passenger)")

        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        def row(label, widget):
            r = ttk.Frame(frm)
            r.pack(fill="x", pady=4)
            ttk.Label(r, text=label, width=36, anchor="w").pack(side="left")
            widget.pack(side="left", fill="x", expand=True)
            return r

        row("State:", ttk.Combobox(frm, textvariable=self.state_var, state="readonly",
                                   values=["Queensland", "New South Wales", "South Australia", "Northern Territory", "Tasmania", "Victoria"]))
        row("Amounts entered are:", ttk.Combobox(frm, textvariable=self.gst_mode_var, state="readonly",
                                                values=["GST inclusive", "GST exclusive"]))
        row("Price (dutiable items):", ttk.Entry(frm, textvariable=self.price_var))
        row("Other costs (GSTable):", ttk.Entry(frm, textvariable=self.costs_var))
        row("Discount:", ttk.Entry(frm, textvariable=self.discount_var))
        row("CTP/rego (no GST):", ttk.Entry(frm, textvariable=self.null_gst_var))
        row("LCT Category:", ttk.Combobox(frm, textvariable=self.lct_var, state="readonly",
                                          values=["Fuel Efficient", "Not Fuel Efficient", "Exempt"]))

        # QLD specifics
        self.qld_frame = ttk.LabelFrame(frm, text="Queensland options")
        self.qld_frame.pack(fill="x", pady=(8, 0))
        r1 = ttk.Frame(self.qld_frame); r1.pack(fill="x", pady=4)
        ttk.Label(r1, text="Base Type:", width=36, anchor="w").pack(side="left")
        ttk.Combobox(r1, textvariable=self.qld_base_var, state="readonly",
                     values=["New/Used", "GVM"]).pack(side="left", fill="x", expand=True)
        r2 = ttk.Frame(self.qld_frame); r2.pack(fill="x", pady=4)
        ttk.Label(r2, text="Vehicle Type:", width=36, anchor="w").pack(side="left")
        ttk.Combobox(r2, textvariable=self.qld_cyl_var, state="readonly",
                     values=["electric/hybrid", "1-4 cylinders", "5-6 cylinders", "7+ cylinders"]
                     ).pack(side="left", fill="x", expand=True)

        # TAS specifics
        self.tas_frame = ttk.LabelFrame(frm, text="Tasmania options")
        self.tas_frame.pack(fill="x", pady=(8, 0))
        r3 = ttk.Frame(self.tas_frame); r3.pack(fill="x", pady=4)
        ttk.Label(r3, text="Vehicle Type:", width=36, anchor="w").pack(side="left")
        ttk.Combobox(
            r3, textvariable=self.tas_vt_var, state="readonly",
            values=[
                "passenger (< 9 people and not utes, motor cycles, panel vans)",
                "commercial up to 4.5t",
                "commercial more than 4.5t",
                "manufacturer fleet discount (except heavy vehicles)"
            ]
        ).pack(side="left", fill="x", expand=True)

        # VIC specifics
        self.vic_frame = ttk.LabelFrame(frm, text="Victoria options")
        self.vic_frame.pack(fill="x", pady=(8, 0))
        r4 = ttk.Frame(self.vic_frame); r4.pack(fill="x", pady=4)
        ttk.Label(r4, text="Category:", width=36, anchor="w").pack(side="left")
        ttk.Combobox(
            r4, textvariable=self.vic_cat_var, state="readonly",
            values=[
                "Private (passenger)",
                "Low emission (passenger)",
                "Primary producer (passenger)",
                "Commercial (new registration)",
                "Commercial (used/transfer)",
                "Demonstrator (passenger)",
                "Demo commercial (used/transfer)"
            ]
        ).pack(side="left", fill="x", expand=True)

        # Results summary
        self.results = tk.StringVar()
        summary_frame = ttk.LabelFrame(frm, text="Results Summary")
        summary_frame.pack(fill="x", pady=(10, 6))
        ttk.Label(summary_frame, textvariable=self.results, justify="left").pack(fill="x", padx=8, pady=6)

        # Breakdown panel (read-only Text widget)
        bframe = ttk.LabelFrame(frm, text="Detailed Calculation Breakdown")
        bframe.pack(fill="both", expand=True, pady=(6, 0))
        self.breakdown_text = tk.Text(bframe, height=18, wrap="word", font=("Courier New", 10))
        self.breakdown_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.breakdown_text.configure(state="disabled")

        # Buttons
        btns = ttk.Frame(frm); btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Calculate", command=self.on_calc).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.on_clear).pack(side="left", padx=6)

        # Show/hide state option groups
        self.state_var.trace_add("write", lambda *_: self._toggle_state_frames())
        self._toggle_state_frames()

    def _toggle_state_frames(self):
        s = self.state_var.get()
        # Simple visibility control
        for f in (self.qld_frame, self.tas_frame, self.vic_frame):
            f.pack_forget()
        if s == "Queensland":
            self.qld_frame.pack(fill="x", pady=(8, 0))
        elif s == "Tasmania":
            self.tas_frame.pack(fill="x", pady=(8, 0))
        elif s == "Victoria":
            self.vic_frame.pack(fill="x", pady=(8, 0))

    def on_clear(self):
        self.price_var.set("")
        self.costs_var.set("")
        self.discount_var.set("")
        self.null_gst_var.set("")
        self.results.set("")
        self._set_breakdown("")

    def _set_breakdown(self, text: str):
        self.breakdown_text.configure(state="normal")
        self.breakdown_text.delete("1.0", "end")
        self.breakdown_text.insert("1.0", text)
        self.breakdown_text.configure(state="disabled")

    def on_calc(self):
        try:
            price = float(self.price_var.get() or 0)
            costs = float(self.costs_var.get() or 0)
            discount = float(self.discount_var.get() or 0)
            null_gst = float(self.null_gst_var.get() or 0)
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numbers.")
            return

        res = calculate_all(
            state=self.state_var.get(),
            price_entered=price,
            costs_entered=costs,
            discount_entered=discount,
            null_gst=null_gst,
            gst_mode=self.gst_mode_var.get(),
            lct_choice=self.lct_var.get(),
            qld_base=self.qld_base_var.get(),
            qld_cyl=self.qld_cyl_var.get(),
            tas_vehicle_type=self.tas_vt_var.get(),
            vic_category=self.vic_cat_var.get()
        )

        self.results.set(
            "Rounded Dutiable Value: {}\nStamp Duty: {}\nGST: {}\nLCT: {}\nTotal: {}".format(
                fmt_money(res["rounded_dutiable"]),
                fmt_money(res["stamp_duty"]),
                fmt_money(res["GST"]),
                fmt_money(res["LCT"]),
                fmt_money(res["total"])
            )
        )
        self._set_breakdown(res["breakdown"])


if __name__ == "__main__":
    App().mainloop()
