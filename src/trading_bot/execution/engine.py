import logging
import os
import sqlite3
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def send_god_level_email(subject: str, html_content: str):
    sender = os.getenv("ALERT_EMAIL_SENDER")
    password = os.getenv("ALERT_EMAIL_PASSWORD")
    receiver = os.getenv("ALERT_EMAIL_RECEIVER")
    if not sender or not password or not receiver:
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"TURTLE QUANT LABS <{sender}>"
        msg["To"] = receiver
        msg.attach(MIMEText(html_content, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        logger.info(f"Dispatched email: {subject}")
    except Exception as e:
        logger.error(f"Email delivery failed: {e}")

class DatabaseManager:
    def __init__(self, db_path="data/trading_bot.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    side TEXT,
                    entry_price REAL,
                    quantity REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    entry_time TEXT,
                    highest_price REAL DEFAULT 0,
                    lowest_price REAL DEFAULT 0,
                    units INTEGER DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    side TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    quantity REAL,
                    pnl REAL,
                    roi REAL,
                    exit_time TEXT
                )
            """)
            conn.commit()
            
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(positions)")
            cols = [c[1] for c in cursor.fetchall()]
            if 'highest_price' not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN highest_price REAL DEFAULT 0")
            if 'lowest_price' not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN lowest_price REAL DEFAULT 0")
            if 'units' not in cols:
                conn.execute("ALTER TABLE positions ADD COLUMN units INTEGER DEFAULT 1")
            conn.commit()

    def save_position(self, symbol, side, price, qty, sl, tp, highest=0, lowest=0, units=1):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO positions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, side, price, qty, sl, tp, datetime.utcnow().isoformat(), highest or price, lowest or price, units))
            conn.commit()

    def update_position_state(self, symbol, qty, sl, highest, lowest, units):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE positions 
                SET quantity = ?, stop_loss = ?, highest_price = ?, lowest_price = ?, units = ? 
                WHERE symbol = ?
            """, (qty, sl, highest, lowest, units, symbol))
            conn.commit()

    def get_position(self, symbol):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT side, entry_price, quantity, stop_loss, take_profit, entry_time, highest_price, lowest_price, units 
                FROM positions WHERE symbol = ?
            """, (symbol,))
            row = cursor.fetchone()
            if row:
                return {
                    'side': row[0],
                    'entry_price': row[1],
                    'quantity': row[2],
                    'stop_loss': row[3],
                    'take_profit': row[4],
                    'entry_time': datetime.fromisoformat(row[5]),
                    'highest_price': row[6] or row[1],
                    'lowest_price': row[7] or row[1],
                    'units': row[8] or 1
                }
            return None

    def close_position(self, symbol, exit_price, pnl, roi):
        pos = self.get_position(symbol)
        if not pos:
            return
        with self._get_connection() as conn:
            conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
            conn.execute("""
                INSERT INTO trade_history (symbol, side, entry_price, exit_price, quantity, pnl, roi, exit_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, pos['side'], pos['entry_price'], exit_price, pos['quantity'], pnl, roi, datetime.utcnow().isoformat()))
            conn.commit()

    def get_recent_consecutive_losses(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pnl FROM trade_history ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            losses = 0
            for r in rows:
                if r[0] < 0:
                    losses += 1
                else:
                    break
            return losses

class ExecutionEngine:
    def __init__(self, exchange_adapter, dry_run: bool = True):
        self.exchange = exchange_adapter
        self.dry_run = dry_run
        self.db = DatabaseManager()
        self.processed_signals = set()
        self.circuit_breaker_until = None

    def check_filters(self, signal: dict) -> tuple[bool, str]:
        if self.circuit_breaker_until and datetime.utcnow() < self.circuit_breaker_until:
            return False, "CIRCUIT BREAKER ACTIVE: Trading paused due to 3 consecutive losses."

        ema200 = float(signal.get('ema200', 0.0))
        price = float(signal.get('price', 0.0))
        vol = float(signal.get('volume', 0.0))
        avg_vol = float(signal.get('avg_volume_20', 0.0))
        adx = float(signal.get('adx', 0.0))
        funding_rate = float(signal.get('funding_rate', 0.0))
        side = signal.get('side', 'BUY').upper()

        if ema200 > 0:
            if side == 'BUY' and price < ema200:
                return False, f"FILTER REJECT: Price (${price}) < 200 EMA (${ema200}) - Counter-trend long."
            if side == 'SELL' and price > ema200:
                return False, f"FILTER REJECT: Price (${price}) > 200 EMA (${ema200}) - Counter-trend short."

        if adx > 0 and adx < 22.0:
            return False, f"FILTER REJECT: Market is Choppy (ADX: {adx:.1f} < 22.0)."

        if avg_vol > 0 and vol < (1.15 * avg_vol):
            return False, f"FILTER REJECT: Insufficient Breakout Volume ({vol:.1f} vs avg {avg_vol:.1f})."

        if side == 'BUY' and funding_rate > 0.0006:
            return False, f"FILTER REJECT: Extreme Long Funding Drag ({funding_rate*100:.3f}%)."
        if side == 'SELL' and funding_rate < -0.0006:
            return False, f"FILTER REJECT: Extreme Short Funding Drag ({funding_rate*100:.3f}%)."

        return True, "FILTERS PASSED"

    def update_trailing_stop(self, symbol: str, current_price: float, atr: float):
        pos = self.db.get_position(symbol)
        if not pos or atr <= 0:
            return

        side = pos['side']
        highest = max(pos['highest_price'], current_price)
        lowest = min(pos['lowest_price'], current_price)
        curr_sl = pos['stop_loss']
        units = pos['units']
        qty = pos['quantity']

        if side == 'BUY':
            potential_sl = round(highest - (2.5 * atr), 2)
            if potential_sl > curr_sl:
                self.db.update_position_state(symbol, qty, potential_sl, highest, lowest, units)
                logger.info(f"Trailing SL Ratcheted UP for {symbol}: ${curr_sl} -> ${potential_sl}")
        elif side == 'SELL':
            potential_sl = round(lowest + (2.5 * atr), 2)
            if curr_sl == 0 or potential_sl < curr_sl:
                self.db.update_position_state(symbol, qty, potential_sl, highest, lowest, units)
                logger.info(f"Trailing SL Ratcheted DOWN for {symbol}: ${curr_sl} -> ${potential_sl}")

    def execute_order(self, signal: dict) -> dict:
        sym = signal.get('symbol', 'UNKNOWN')
        side = signal.get('side', 'BUY').upper()
        price = float(signal.get('price', 0.0))
        qty = float(signal.get('quantity', 0.0))
        sl = float(signal.get('stop_loss', 0.0))
        tp = float(signal.get('take_profit', 0.0))
        atr = float(signal.get('atr', 0.0))
        ts = signal.get('timestamp', int(datetime.utcnow().timestamp()))
        signal_id = f"{sym}-{side}-{ts}"

        if signal_id in self.processed_signals:
            return {'status': 'REJECTED', 'reason': 'Duplicate signal'}

        mode_label = "PAPER TRADING (SIMULATION)" if self.dry_run else "LIVE CAPITAL (REAL)"
        mode_badge_bg = "#334155" if self.dry_run else "#b91c1c"

        existing_pos = self.db.get_position(sym)
        if existing_pos and side == existing_pos['side'] and existing_pos['units'] < 3 and atr > 0:
            trigger_delta = 0.5 * atr
            is_pyramid = (price >= (existing_pos['entry_price'] + trigger_delta)) if side == 'BUY' else (price <= (existing_pos['entry_price'] - trigger_delta))
            if is_pyramid:
                new_units = existing_pos['units'] + 1
                new_qty = round(existing_pos['quantity'] + qty, 4)
                new_sl = existing_pos['entry_price']
                self.db.update_position_state(sym, new_qty, new_sl, max(existing_pos['highest_price'], price), min(existing_pos['lowest_price'], price), new_units)
                self.processed_signals.add(signal_id)
                logger.info(f"Pyramided unit {new_units} added to {sym} @ ${price}. New total qty: {new_qty}")
                return {'status': 'FILLED_PYRAMID', 'units': new_units, 'quantity': new_qty}

        if side in ['BUY', 'SELL']:
            passed, reason = self.check_filters(signal)
            if not passed:
                logger.warning(reason)
                return {'status': 'FILTERED', 'reason': reason}

            self.processed_signals.add(signal_id)
            self.db.save_position(sym, side, price, qty, sl, tp, highest=price, lowest=price, units=1)

            theme_color = "#06b6d4" if side == "BUY" else "#8b5cf6"
            badge_text = "LONG POSITION" if side == "BUY" else "SHORT POSITION"
            risk_per_unit = abs(price - sl) if sl > 0 else 0
            risk_pct = ((risk_per_unit / price) * 100) if price > 0 else 0

            html = f"""
            <!DOCTYPE html>
            <html>
            <body style="margin:0;padding:24px;background-color:#0b0f19;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f8fafc;">
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:580px;margin:0 auto;background:#111827;border:1px solid #1f2937;border-radius:14px;overflow:hidden;">
                <tr>
                  <td style="padding:24px 28px 16px 28px;border-bottom:1px solid #1f2937;">
                    <span style="background:{mode_badge_bg};color:#f1f5f9;font-size:10px;font-weight:700;padding:4px 10px;border-radius:20px;">{mode_label}</span>
                    <div style="margin-top:16px;">
                      <span style="background:{theme_color}22;color:{theme_color};font-size:12px;font-weight:800;padding:5px 12px;border-radius:6px;border:1px solid {theme_color}55;">{badge_text}</span>
                      <h1 style="font-size:26px;font-weight:800;margin:12px 0 0 0;color:#ffffff;">? {side} BREAKOUT: <span style="color:{theme_color};">{sym}</span></h1>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 28px;background:linear-gradient(180deg, #111827 0%, #172033 100%);">
                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                      <tr><td style="color:#94a3b8;font-size:12px;">ENTRY PRICE</td><td align="right" style="color:#94a3b8;font-size:12px;">INITIAL SIZE</td></tr>
                      <tr><td style="font-size:30px;font-weight:800;color:#ffffff;font-family:monospace;">${price:,.2f}</td><td align="right" style="font-size:20px;font-weight:700;color:#e2e8f0;font-family:monospace;">{qty} units</td></tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 28px;">
                    <table width="100%" border="0" cellspacing="0" cellpadding="10" style="background:#0f172a;border-radius:10px;border:1px solid #1e293b;font-size:13px;">
                      <tr style="border-bottom:1px solid #1e293b;"><td style="color:#94a3b8;">Turtle 2N Stop-Loss:</td><td align="right" style="font-weight:700;color:#f87171;font-family:monospace;">${sl:,.2f} (-{risk_pct:.2f}%)</td></tr>
                      <tr style="border-bottom:1px solid #1e293b;"><td style="color:#94a3b8;">Quant Quality Filters:</td><td align="right" style="font-weight:600;color:#34d399;">EMA200 + ADX Anti-Chop Active</td></tr>
                      <tr><td style="color:#94a3b8;">Ratchet ATR Trailing:</td><td align="right" style="font-weight:600;color:#38bdf8;">Dynamic Profit Lock Enabled</td></tr>
                    </table>
                  </td>
                </tr>
              </table>
            </body>
            </html>
            """
            send_god_level_email(f"? [ENTRY] {side} {sym} @ ${price:,.2f}", html)
            return {'status': 'FILLED', 'mode': 'PAPER' if self.dry_run else 'LIVE', 'signal_id': signal_id}

        elif side in ['CLOSE', 'EXIT']:
            pos = self.db.get_position(sym)
            if not pos:
                return {'status': 'REJECTED', 'reason': 'No active position found in database'}

            entry_p = pos['entry_price']
            pos_qty = pos['quantity']
            pos_side = pos['side']

            pnl = (price - entry_p) * pos_qty if pos_side == 'BUY' else (entry_p - price) * pos_qty
            roi = ((price - entry_p) / entry_p) * 100 if pos_side == 'BUY' else ((entry_p - price) / entry_p) * 100

            self.db.close_position(sym, price, pnl, roi)

            if pnl < 0 and self.db.get_recent_consecutive_losses() >= 3:
                self.circuit_breaker_until = datetime.utcnow() + timedelta(hours=24)
                logger.warning("CIRCUIT BREAKER TRIGGERED: 3 losses in a row.")

            is_profit = pnl >= 0
            accent_color = "#10b981" if is_profit else "#f43f5e"
            bg_gradient = "linear-gradient(180deg, #064e3b 0%, #022c22 100%)" if is_profit else "linear-gradient(180deg, #881337 0%, #4c0519 100%)"
            badge_status = "WINNER TAKE-PROFIT ??" if is_profit else "STOP-LOSS HIT ??"
            status_title = "PROFIT EXIT BOOKED" if is_profit else "RISK SHIELD TRIGGERED"
            pnl_sign = "+" if pnl > 0 else ""
            duration_str = str(datetime.utcnow() - pos['entry_time']).split('.')[0]

            html = f"""
            <!DOCTYPE html>
            <html>
            <body style="margin:0;padding:24px;background-color:#0b0f19;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#f8fafc;">
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width:580px;margin:0 auto;background:#111827;border:1px solid {accent_color}55;border-radius:14px;overflow:hidden;">
                <tr>
                  <td style="padding:24px 28px 16px 28px;border-bottom:1px solid #1f2937;">
                    <span style="background:{accent_color}22;color:{accent_color};font-size:12px;font-weight:800;padding:5px 12px;border-radius:6px;border:1px solid {accent_color}66;">{badge_status}</span>
                    <h1 style="font-size:26px;font-weight:800;margin:12px 0 0 0;color:#ffffff;">{status_title}: <span style="color:{accent_color};">{sym}</span></h1>
                  </td>
                </tr>
                <tr>
                  <td style="padding:28px;background:{bg_gradient};">
                    <table width="100%" border="0" cellspacing="0" cellpadding="0">
                      <tr><td style="color:#cbd5e1;font-size:13px;">REALIZED NET PNL</td><td align="right" style="color:#cbd5e1;font-size:13px;">ROI</td></tr>
                      <tr><td style="font-size:38px;font-weight:900;color:#ffffff;font-family:monospace;">{pnl_sign}${pnl:,.2f}</td><td align="right" style="font-size:34px;font-weight:900;color:#ffffff;font-family:monospace;">{pnl_sign}{roi:.2f}%</td></tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:20px 28px;">
                    <table width="100%" border="0" cellspacing="0" cellpadding="10" style="background:#0f172a;border-radius:10px;border:1px solid #1e293b;font-size:13px;">
                      <tr style="border-bottom:1px solid #1e293b;"><td style="color:#94a3b8;">Original Entry Price:</td><td align="right" style="font-weight:700;color:#e2e8f0;font-family:monospace;">${entry_p:,.2f}</td></tr>
                      <tr style="border-bottom:1px solid #1e293b;"><td style="color:#94a3b8;">Terminal Exit Price:</td><td align="right" style="font-weight:700;color:#ffffff;font-family:monospace;">${price:,.2f}</td></tr>
                      <tr><td style="color:#94a3b8;">Trade Duration:</td><td align="right" style="font-weight:700;color:#38bdf8;font-family:monospace;">? {duration_str}</td></tr>
                    </table>
                  </td>
                </tr>
              </table>
            </body>
            </html>
            """
            icon = "??" if is_profit else "??"
            send_god_level_email(f"{icon} [{status_title}] {sym} | PnL: {pnl_sign}${pnl:,.2f} ({pnl_sign}{roi:.2f}%)", html)
            return {'status': 'FILLED', 'mode': 'PAPER' if self.dry_run else 'LIVE', 'signal_id': signal_id}

        return {'status': 'UNKNOWN'}
