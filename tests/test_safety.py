"""Tests for cli.safety — SafetyGuard (kill switch + daily loss limit)."""

from datetime import date

from cli.safety import SafetyGuard, SafetyResult


class TestSafetyResult:
    def test_allowed(self):
        r = SafetyResult(allowed=True)
        assert r.allowed is True
        assert r.reason == ""

    def test_blocked(self):
        r = SafetyResult(allowed=False, reason="halt")
        assert r.allowed is False
        assert r.reason == "halt"


class TestKillSwitch:
    def test_kill_switch_on_blocks(self):
        g = SafetyGuard(kill_switch=True)
        r = g.check()
        assert r.allowed is False
        assert "Kill switch" in r.reason

    def test_kill_switch_off_allows(self):
        g = SafetyGuard(kill_switch=False)
        assert g.check().allowed is True

    def test_kill_switch_property(self):
        g = SafetyGuard(kill_switch=True)
        assert g.kill_switch is True


class TestMaxDailyLoss:
    def test_no_loss_allows(self):
        g = SafetyGuard(max_daily_loss_pct=3.0, initial_cash=100_000)
        assert g.check().allowed is True

    def test_small_loss_allows(self):
        g = SafetyGuard(max_daily_loss_pct=3.0, initial_cash=100_000)
        today = date(2026, 2, 17)
        g.record_pnl(-2_500.0, today=today)
        r = g.check(today=today)
        assert r.allowed is True

    def test_exact_limit_blocks(self):
        g = SafetyGuard(max_daily_loss_pct=3.0, initial_cash=100_000)
        today = date(2026, 2, 17)
        g.record_pnl(-3_000.0, today=today)
        r = g.check(today=today)
        assert r.allowed is False
        assert "Daily loss limit" in r.reason

    def test_over_limit_blocks(self):
        g = SafetyGuard(max_daily_loss_pct=3.0, initial_cash=100_000)
        today = date(2026, 2, 17)
        g.record_pnl(-3_500.0, today=today)
        r = g.check(today=today)
        assert r.allowed is False

    def test_positive_pnl_allows(self):
        g = SafetyGuard(max_daily_loss_pct=3.0, initial_cash=100_000)
        today = date(2026, 2, 17)
        g.record_pnl(5_000.0, today=today)
        assert g.check(today=today).allowed is True

    def test_cumulative_losses(self):
        g = SafetyGuard(max_daily_loss_pct=2.0, initial_cash=50_000)
        today = date(2026, 2, 17)
        g.record_pnl(-500.0, today=today)
        assert g.check(today=today).allowed is True
        g.record_pnl(-600.0, today=today)
        r = g.check(today=today)
        assert r.allowed is False
        assert g.daily_pnl == -1_100.0

    def test_loss_then_win_recovers(self):
        g = SafetyGuard(max_daily_loss_pct=3.0, initial_cash=100_000)
        today = date(2026, 2, 17)
        g.record_pnl(-2_800.0, today=today)
        g.record_pnl(1_000.0, today=today)
        assert g.daily_pnl == -1_800.0
        assert g.check(today=today).allowed is True

    def test_max_daily_loss_property(self):
        g = SafetyGuard(max_daily_loss_pct=5.0, initial_cash=200_000)
        assert g.max_daily_loss == 10_000.0


class TestDayReset:
    def test_new_day_resets_pnl(self):
        g = SafetyGuard(max_daily_loss_pct=3.0, initial_cash=100_000)
        day1 = date(2026, 2, 17)
        g.record_pnl(-3_000.0, today=day1)
        assert g.check(today=day1).allowed is False

        day2 = date(2026, 2, 18)
        r = g.check(today=day2)
        assert r.allowed is True
        assert g.daily_pnl == 0.0

    def test_recording_on_new_day_resets_then_accumulates(self):
        g = SafetyGuard(max_daily_loss_pct=3.0, initial_cash=100_000)
        day1 = date(2026, 2, 17)
        g.record_pnl(-2_000.0, today=day1)

        day2 = date(2026, 2, 18)
        g.record_pnl(-500.0, today=day2)
        assert g.daily_pnl == -500.0
        assert g.check(today=day2).allowed is True


class TestCombined:
    def test_kill_switch_takes_precedence_over_pnl(self):
        g = SafetyGuard(kill_switch=True, max_daily_loss_pct=99.0, initial_cash=100_000)
        today = date(2026, 2, 17)
        g.record_pnl(50_000.0, today=today)
        r = g.check(today=today)
        assert r.allowed is False
        assert "Kill switch" in r.reason

    def test_kill_switch_off_loss_ok(self):
        g = SafetyGuard(kill_switch=False, max_daily_loss_pct=5.0, initial_cash=100_000)
        assert g.check().allowed is True


class TestConfigIntegration:
    def test_execution_config_fields(self):
        from config.loader import ExecutionConfig

        ec = ExecutionConfig()
        assert ec.kill_switch is False
        assert ec.max_daily_loss_pct == 3.0

    def test_execution_config_custom(self):
        from config.loader import ExecutionConfig

        ec = ExecutionConfig(kill_switch=True, max_daily_loss_pct=5.0)
        assert ec.kill_switch is True
        assert ec.max_daily_loss_pct == 5.0

    def test_load_config_parses_fields(self, tmp_path):
        import yaml
        from config.loader import load_config

        cfg_data = {
            "symbol": "SPY",
            "timeframe": "15m",
            "data": {"source": "alpaca", "bar_store_path": "data/bars.db"},
            "execution": {
                "kill_switch": True,
                "max_daily_loss_pct": 2.5,
            },
        }
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(yaml.dump(cfg_data))

        cfg = load_config(cfg_file)
        assert cfg.execution.kill_switch is True
        assert cfg.execution.max_daily_loss_pct == 2.5
