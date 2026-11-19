"""
Database models and query builders for the trading platform.
"""
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .client import DataAPIClient
from .schemas import InstrumentCreate


class BaseModel:
    table_name: Optional[str] = None

    def __init__(self, db: DataAPIClient) -> None:
        self.db = db
        if not self.table_name:
            raise ValueError("table_name must be defined")

    def find_by_id(self, id_: Any) -> Optional[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE id = :id::uuid"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query_one(sql, [{"name": "id", "value": {"stringValue": str(id_)}}])

    def find_all(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        sql = f"SELECT * FROM {self.table_name} LIMIT :limit OFFSET :offset"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [
            {"name": "limit", "value": {"longValue": limit}},
            {"name": "offset", "value": {"longValue": offset}},
        ])

    def create(self, data: Dict, returning: str = "id") -> Optional[str]:
        return self.db.insert(self.table_name, data, returning=returning)

    def update(self, id_: Any, data: Dict) -> int:
        return self.db.update(self.table_name, data, "id = :id::uuid", {"id": str(id_)})

    def delete(self, id_: Any) -> int:
        return self.db.delete(self.table_name, "id = :id::uuid", {"id": str(id_)})


# ------------------------------------------------------------------ users

class Users(BaseModel):
    table_name = "users"

    def find_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE clerk_user_id = :cid"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query_one(sql, [{"name": "cid", "value": {"stringValue": clerk_user_id}}])

    def create_user(
        self,
        clerk_user_id: str,
        display_name: Optional[str] = None,
        years_until_retirement: Optional[int] = None,
        target_retirement_income: Optional[Decimal] = None,
    ) -> Optional[str]:
        data = {
            "clerk_user_id": clerk_user_id,
            "display_name": display_name,
            "years_until_retirement": years_until_retirement,
            "target_retirement_income": target_retirement_income,
        }
        data = {k: v for k, v in data.items() if v is not None}
        return self.db.insert(self.table_name, data, returning="clerk_user_id")


# ------------------------------------------------------------ instruments

class Instruments(BaseModel):
    table_name = "instruments"

    def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        return self.db.query(f"SELECT * FROM {self.table_name} ORDER BY symbol", [])  # nosec B608 - table_name is a class constant; values are bound

    def find_by_symbol(self, symbol: str) -> Optional[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE symbol = :symbol"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query_one(sql, [{"name": "symbol", "value": {"stringValue": symbol}}])

    def create_instrument(self, instrument: InstrumentCreate) -> Optional[str]:
        v = instrument.model_dump()
        data = {
            "symbol": v["symbol"],
            "name": v["name"],
            "instrument_type": v["instrument_type"],
            "current_price": v.get("current_price"),
            "allocation_regions": v["allocation_regions"],
            "allocation_sectors": v["allocation_sectors"],
            "allocation_asset_class": v["allocation_asset_class"],
            "source": v.get("source", "instrument_tagger"),
        }
        return self.db.insert(self.table_name, data, returning="symbol")

    def upsert(self, instrument: InstrumentCreate) -> Optional[str]:
        """Upsert by symbol; used by InstrumentTagger."""
        v = instrument.model_dump()
        sql = """
            INSERT INTO instruments (
                symbol, name, instrument_type, current_price,
                allocation_regions, allocation_sectors, allocation_asset_class,
                source, last_updated
            ) VALUES (
                :symbol, :name, :instrument_type, :current_price::numeric,
                :allocation_regions::jsonb, :allocation_sectors::jsonb,
                :allocation_asset_class::jsonb, :source, NOW()
            )
            ON CONFLICT (symbol) DO UPDATE SET
                name = EXCLUDED.name,
                instrument_type = EXCLUDED.instrument_type,
                current_price = EXCLUDED.current_price,
                allocation_regions = EXCLUDED.allocation_regions,
                allocation_sectors = EXCLUDED.allocation_sectors,
                allocation_asset_class = EXCLUDED.allocation_asset_class,
                source = EXCLUDED.source,
                last_updated = NOW()
            RETURNING symbol
        """
        params = [
            {"name": "symbol", "value": {"stringValue": v["symbol"]}},
            {"name": "name", "value": {"stringValue": v["name"]}},
            {"name": "instrument_type", "value": {"stringValue": v["instrument_type"]}},
            {"name": "current_price", "value": {"stringValue": str(v.get("current_price", 0) or 0)}},
            {"name": "allocation_regions", "value": {"stringValue": __import__("json").dumps(v["allocation_regions"])}},
            {"name": "allocation_sectors", "value": {"stringValue": __import__("json").dumps(v["allocation_sectors"])}},
            {"name": "allocation_asset_class", "value": {"stringValue": __import__("json").dumps(v["allocation_asset_class"])}},
            {"name": "source", "value": {"stringValue": v.get("source", "instrument_tagger")}},
        ]
        response = self.db.execute(sql, params)
        if response.get("records"):
            return response["records"][0][0].get("stringValue")
        return None

    def find_by_type(self, instrument_type: str) -> List[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE instrument_type = :t ORDER BY symbol"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [{"name": "t", "value": {"stringValue": instrument_type}}])

    def search(self, query: str) -> List[Dict]:
        sql = f"""
            SELECT * FROM {self.table_name}
            WHERE LOWER(symbol) LIKE LOWER(:q) OR LOWER(name) LIKE LOWER(:q)
            ORDER BY symbol LIMIT 20
        """  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [{"name": "q", "value": {"stringValue": f"%{query}%"}}])


# -------------------------------------------------------------- accounts

class Accounts(BaseModel):
    table_name = "accounts"

    def find_by_user(self, clerk_user_id: str) -> List[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE clerk_user_id = :uid ORDER BY created_at DESC"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [{"name": "uid", "value": {"stringValue": clerk_user_id}}])

    def create_account(
        self,
        clerk_user_id: str,
        account_name: str,
        account_purpose: Optional[str] = None,
        cash_balance: Decimal = Decimal("0"),
        cash_interest: Decimal = Decimal("0"),
    ) -> Optional[str]:
        data = {
            "clerk_user_id": clerk_user_id,
            "account_name": account_name,
            "account_purpose": account_purpose,
            "cash_balance": cash_balance,
            "cash_interest": cash_interest,
        }
        return self.db.insert(self.table_name, data, returning="id")


# -------------------------------------------------------------- positions

class Positions(BaseModel):
    table_name = "positions"

    def find_by_account(self, account_id: str) -> List[Dict]:
        sql = f"""
            SELECT p.*, i.name AS instrument_name, i.instrument_type, i.current_price
            FROM {self.table_name} p
            JOIN instruments i ON p.symbol = i.symbol
            WHERE p.account_id = :aid::uuid
            ORDER BY p.symbol
        """  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [{"name": "aid", "value": {"stringValue": account_id}}])

    def add_position(self, account_id: str, symbol: str, quantity: Decimal) -> Optional[str]:
        sql = """
            INSERT INTO positions (account_id, symbol, quantity, as_of_date)
            VALUES (:aid::uuid, :sym, :qty::numeric, :d::date)
            ON CONFLICT (account_id, symbol) DO UPDATE SET
                quantity = EXCLUDED.quantity,
                as_of_date = EXCLUDED.as_of_date,
                updated_at = NOW()
            RETURNING id
        """
        params = [
            {"name": "aid", "value": {"stringValue": account_id}},
            {"name": "sym", "value": {"stringValue": symbol}},
            {"name": "qty", "value": {"stringValue": str(quantity)}},
            {"name": "d", "value": {"stringValue": date.today().isoformat()}},
        ]
        response = self.db.execute(sql, params)
        if response.get("records"):
            return response["records"][0][0].get("stringValue")
        return None

    def get_portfolio_value(self, account_id: str) -> Dict:
        sql = """
            SELECT COUNT(DISTINCT p.symbol) AS num_positions,
                   SUM(p.quantity * i.current_price) AS total_value,
                   SUM(p.quantity) AS total_shares
            FROM positions p JOIN instruments i ON p.symbol = i.symbol
            WHERE p.account_id = :aid::uuid
        """
        result = self.db.query_one(sql, [{"name": "aid", "value": {"stringValue": account_id}}])
        if result:
            return {
                "num_positions": result.get("num_positions", 0),
                "total_value": float(result.get("total_value") or 0),
                "total_shares": float(result.get("total_shares") or 0),
            }
        return {"num_positions": 0, "total_value": 0, "total_shares": 0}


# ------------------------------------------------------------------- jobs

class Jobs(BaseModel):
    table_name = "jobs"

    def create_job(self, clerk_user_id: str, job_type: str, request_payload: Optional[Dict] = None) -> Optional[str]:
        data = {
            "clerk_user_id": clerk_user_id,
            "job_type": job_type,
            "status": "pending",
            "request_payload": request_payload,
        }
        return self.db.insert(self.table_name, data, returning="id")

    def update_status(self, job_id: str, status: str, error_message: Optional[str] = None) -> int:
        data: Dict = {"status": status}
        if status == "running":
            data["started_at"] = datetime.now(UTC)
        elif status in ("completed", "failed"):
            data["completed_at"] = datetime.now(UTC)
        if error_message:
            data["error_message"] = error_message
        return self.db.update(self.table_name, data, "id = :id::uuid", {"id": job_id})

    def update_report(self, job_id: str, payload: Dict) -> int:
        return self.db.update(self.table_name, {"report_payload": payload}, "id = :id::uuid", {"id": job_id})

    def update_charts(self, job_id: str, payload: Dict) -> int:
        return self.db.update(self.table_name, {"charts_payload": payload}, "id = :id::uuid", {"id": job_id})

    def update_retirement(self, job_id: str, payload: Dict) -> int:
        return self.db.update(self.table_name, {"retirement_payload": payload}, "id = :id::uuid", {"id": job_id})

    def update_summary(self, job_id: str, payload: Dict) -> int:
        return self.db.update(self.table_name, {"summary_payload": payload}, "id = :id::uuid", {"id": job_id})

    def find_by_user(self, clerk_user_id: str, status: Optional[str] = None, limit: int = 20) -> List[Dict]:
        if status:
            sql = f"SELECT * FROM {self.table_name} WHERE clerk_user_id = :uid AND status = :st ORDER BY created_at DESC LIMIT :lim"  # nosec B608 - table_name is a class constant; values are bound
            return self.db.query(sql, [
                {"name": "uid", "value": {"stringValue": clerk_user_id}},
                {"name": "st", "value": {"stringValue": status}},
                {"name": "lim", "value": {"longValue": limit}},
            ])
        sql = f"SELECT * FROM {self.table_name} WHERE clerk_user_id = :uid ORDER BY created_at DESC LIMIT :lim"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [
            {"name": "uid", "value": {"stringValue": clerk_user_id}},
            {"name": "lim", "value": {"longValue": limit}},
        ])


# -------------------------------------------------------- trading profiles

class TradingProfiles(BaseModel):
    table_name = "trading_profiles"

    def find_by_user(self, clerk_user_id: str) -> Optional[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE clerk_user_id = :cid"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query_one(sql, [{"name": "cid", "value": {"stringValue": clerk_user_id}}])

    def upsert(self, data: Dict) -> Optional[str]:
        sql = """
            INSERT INTO trading_profiles (
                clerk_user_id, risk_tolerance, investment_experience,
                income_bracket, max_drawdown_pct, kyc_status,
                kyc_provider_ref, jurisdiction
            ) VALUES (
                :cid, :rt, :ie, :ib, :mdd::numeric, :kyc, :kpr, :jur
            )
            ON CONFLICT (clerk_user_id) DO UPDATE SET
                risk_tolerance = EXCLUDED.risk_tolerance,
                investment_experience = EXCLUDED.investment_experience,
                income_bracket = EXCLUDED.income_bracket,
                max_drawdown_pct = EXCLUDED.max_drawdown_pct,
                kyc_status = EXCLUDED.kyc_status,
                kyc_provider_ref = EXCLUDED.kyc_provider_ref,
                jurisdiction = EXCLUDED.jurisdiction,
                updated_at = NOW()
            RETURNING clerk_user_id
        """
        params = [
            {"name": "cid", "value": {"stringValue": data["clerk_user_id"]}},
            {"name": "rt", "value": {"stringValue": data["risk_tolerance"]}},
            {"name": "ie", "value": {"stringValue": data.get("investment_experience") or ""}},
            {"name": "ib", "value": {"stringValue": data.get("income_bracket") or ""}},
            {"name": "mdd", "value": {"stringValue": str(data.get("max_drawdown_pct", 20))}},
            {"name": "kyc", "value": {"stringValue": data.get("kyc_status", "pending")}},
            {"name": "kpr", "value": {"stringValue": data.get("kyc_provider_ref") or ""}},
            {"name": "jur", "value": {"stringValue": data.get("jurisdiction") or ""}},
        ]
        response = self.db.execute(sql, params)
        if response.get("records"):
            return response["records"][0][0].get("stringValue")
        return None


# -------------------------------------------------------- trading signals

class TradingSignals(BaseModel):
    table_name = "trading_signals"

    def find_active_for_user(self, clerk_user_id: str, limit: int = 50) -> List[Dict]:
        sql = f"""
            SELECT * FROM {self.table_name}
            WHERE clerk_user_id = :cid
              AND status = 'active'
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC LIMIT :lim
        """  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [
            {"name": "cid", "value": {"stringValue": clerk_user_id}},
            {"name": "lim", "value": {"longValue": limit}},
        ])

    def create_signal(self, data: Dict) -> Optional[str]:
        return self.db.insert(self.table_name, data, returning="id")

    def expire_stale(self) -> int:
        return self.db.update(
            self.table_name,
            {"status": "expired"},
            "status = 'active' AND expires_at IS NOT NULL AND expires_at < NOW()",
        )


# --------------------------------------------------------------- trades

class Trades(BaseModel):
    table_name = "trades"

    def find_by_user(self, clerk_user_id: str, limit: int = 100) -> List[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE clerk_user_id = :cid ORDER BY placed_at DESC LIMIT :lim"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [
            {"name": "cid", "value": {"stringValue": clerk_user_id}},
            {"name": "lim", "value": {"longValue": limit}},
        ])

    def find_by_broker_order(self, broker_order_id: str) -> Optional[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE broker_order_id = :bid"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query_one(sql, [{"name": "bid", "value": {"stringValue": broker_order_id}}])

    def find_by_idempotency_key(self, key: str) -> Optional[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE idempotency_key = :k::uuid"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query_one(sql, [{"name": "k", "value": {"stringValue": key}}])

    def record_trade(self, data: Dict) -> Optional[str]:
        return self.db.insert(self.table_name, data, returning="id")

    def mark_filled(self, trade_id: str, filled_price: Decimal) -> int:
        return self.db.update(
            self.table_name,
            {"status": "filled", "filled_price": filled_price, "filled_at": datetime.now(UTC)},
            "id = :id::uuid",
            {"id": trade_id},
        )


# ---------------------------------------------------- researcher events

class ResearcherEvents(BaseModel):
    table_name = "researcher_events"

    def find_candidates(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
        if symbol:
            sql = f"SELECT * FROM {self.table_name} WHERE symbol = :sym AND status = 'candidate' ORDER BY discovered_at DESC LIMIT :lim"  # nosec B608 - table_name is a class constant; values are bound
            return self.db.query(sql, [
                {"name": "sym", "value": {"stringValue": symbol}},
                {"name": "lim", "value": {"longValue": limit}},
            ])
        sql = f"SELECT * FROM {self.table_name} WHERE status = 'candidate' ORDER BY discovered_at DESC LIMIT :lim"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query(sql, [{"name": "lim", "value": {"longValue": limit}}])

    def record_event(self, data: Dict) -> Optional[str]:
        return self.db.insert(self.table_name, data, returning="id")

    def find_by_event_id(self, event_id: str) -> Optional[Dict]:
        sql = f"SELECT * FROM {self.table_name} WHERE event_id = :eid"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query_one(sql, [{"name": "eid", "value": {"stringValue": event_id}}])

    def update_status(self, event_id: str, status: str) -> int:
        return self.db.update(self.table_name, {"status": status}, "event_id = :eid", {"eid": event_id})

    def expire_stale(self) -> int:
        return self.db.update(
            self.table_name,
            {"status": "expired"},
            "status IN ('candidate', 'validated') AND expires_at IS NOT NULL AND expires_at < NOW()",
        )


# ------------------------------------------------------ trading audit

class TradingAudit(BaseModel):
    table_name = "trading_audit"

    def append(self, entry: Dict) -> int:
        """Append-only audit write. Callers supply prev_hash/this_hash."""
        return self.db.insert(self.table_name, entry)

    def latest(self) -> Optional[Dict]:
        sql = f"SELECT * FROM {self.table_name} ORDER BY event_time DESC, id DESC LIMIT 1"  # nosec B608 - table_name is a class constant; values are bound
        return self.db.query_one(sql)

    def verify_chain(self, limit: int = 1000) -> bool:
        """Return True if the hash chain is unbroken for the last `limit` rows."""
        sql = f"""
            SELECT id, prev_hash, this_hash
            FROM {self.table_name}
            ORDER BY id ASC
            LIMIT :lim
        """  # nosec B608 - table_name is a class constant; values are bound
        rows = self.db.query(sql, [{"name": "lim", "value": {"longValue": limit}}])
        for i in range(1, len(rows)):
            if rows[i]["prev_hash"] != rows[i - 1]["this_hash"]:
                return False
        return True


# ----------------------------------------------------------- facade

class Database:
    def __init__(
        self,
        cluster_arn: Optional[str] = None,
        secret_arn: Optional[str] = None,
        database: Optional[str] = None,
        region: Optional[str] = None,
    ) -> None:
        self.client = DataAPIClient(cluster_arn, secret_arn, database, region)
        self.users = Users(self.client)
        self.instruments = Instruments(self.client)
        self.accounts = Accounts(self.client)
        self.positions = Positions(self.client)
        self.jobs = Jobs(self.client)
        self.trading_profiles = TradingProfiles(self.client)
        self.trading_signals = TradingSignals(self.client)
        self.trades = Trades(self.client)
        self.researcher_events = ResearcherEvents(self.client)
        self.trading_audit = TradingAudit(self.client)

    def execute_raw(self, sql: str, parameters: Optional[List[Dict]] = None) -> Dict:
        return self.client.execute(sql, parameters)

    def query_raw(self, sql: str, parameters: Optional[List[Dict]] = None) -> List[Dict]:
        return self.client.query(sql, parameters)