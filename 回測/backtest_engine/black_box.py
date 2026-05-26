"""
Black Box Validator — Kaggle-style 2025 年驗證器

規則:
  1. 只接受策略名稱 + 參數
  2. 在 2025 年全部標的上執行
  3. 只回傳聚合分數，不回傳個別結果
  4. 限制提交次數（防暴力搜索測試集）
  5. 記錄所有提交，避免重複

使用方式:
  validator = BlackBoxValidator(data_dir)
  score = validator.submit("macd", {"fast": 12, "slow": 26, "signal_period": 9})
"""

import json
import hashlib
import time
from pathlib import Path
from dataclasses import dataclass, asdict

from .data_loader import load_and_resample, list_available_symbols, find_data_file
from .engine import run_backtest
from .strategy import BuyAndHold, SMACrossover, MACDStrategy, BollingerBands
from .scorer import RobustnessScore, compute_robustness


_STRATEGY_MAP = {
    'buyhold': BuyAndHold,
    'sma': SMACrossover,
    'macd': MACDStrategy,
    'bollinger': BollingerBands,
}

MAX_SUBMISSIONS = 50  # 最多提交 50 次


class BlackBoxValidator:

    def __init__(
        self,
        data_dir: str | Path,
        test_year: str = '25',
        freq: str = '1h',
        commission: float = 0.0,
        max_submissions: int = MAX_SUBMISSIONS,
    ):
        self.data_dir = Path(data_dir)
        self.test_year = test_year
        self.freq = freq
        self.commission = commission
        self.max_submissions = max_submissions
        self.cache_dir = self.data_dir / '.ohlcv_cache'

        # 提交記錄
        self._log_path = self.data_dir / '.blackbox_submissions.jsonl'
        self._submissions: list[dict] = []
        self._load_log()

        # 掃描可用 2025 標的
        available = list_available_symbols(self.data_dir)
        self._symbols = [
            sym for sym, years in available.items()
            if test_year in years
        ]

    def _load_log(self):
        if self._log_path.exists():
            for line in self._log_path.read_text(encoding='utf-8').splitlines():
                if line.strip():
                    self._submissions.append(json.loads(line))

    def _save_entry(self, entry: dict):
        with open(self._log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    @property
    def remaining_submissions(self) -> int:
        return self.max_submissions - len(self._submissions)

    @property
    def submission_count(self) -> int:
        return len(self._submissions)

    def _make_key(self, strategy_name: str, params: dict) -> str:
        raw = f"{strategy_name}|{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def submit(
        self,
        strategy_name: str,
        params: dict | None = None,
    ) -> RobustnessScore | None:
        """
        提交一組策略到 Black Box。

        回傳: RobustnessScore（只有聚合指標，沒有個別標的結果）
        如果超過提交次數限制，回傳 None。
        """
        if params is None:
            params = {}

        strategy_name = strategy_name.lower()

        # 檢查提交次數
        if self.remaining_submissions <= 0:
            print(f"已達提交上限 ({self.max_submissions} 次)。無法再提交。")
            return None

        # 檢查是否重複
        key = self._make_key(strategy_name, params)
        for s in self._submissions:
            if s.get('key') == key:
                print(f"重複提交。回傳快取結果。（不計次數）")
                return RobustnessScore(**s['score'])

        # 驗證策略名稱
        if strategy_name not in _STRATEGY_MAP:
            avail = ', '.join(_STRATEGY_MAP.keys())
            print(f"未知策略 '{strategy_name}'。可用: {avail}")
            return None

        print(f"\n{'='*50}")
        print(f" BLACK BOX VALIDATION")
        print(f" Strategy: {strategy_name} | Params: {params}")
        print(f" Test set: 20{self.test_year} | {len(self._symbols)} symbols")
        print(f" Submission: {self.submission_count + 1}/{self.max_submissions}")
        print(f"{'='*50}")

        # 執行回測（內部，不暴露細節）
        sharpes, sortinos, ars, mdds = [], [], [], []
        errors = 0

        for i, sym in enumerate(self._symbols):
            try:
                strategy = _STRATEGY_MAP[strategy_name](**params)
                path = find_data_file(self.data_dir, sym, self.test_year)
                prices = load_and_resample(path, self.freq, cache_dir=self.cache_dir)

                if len(prices) < 50:
                    continue

                result = run_backtest(
                    prices=prices,
                    strategy=strategy,
                    symbol=sym,
                    freq=self.freq,
                    commission=self.commission,
                )
                m = result.metrics
                sharpes.append(m['sharpe_ratio'])
                sortinos.append(m['sortino_ratio'])
                ars.append(m['annualized_return'])
                mdds.append(m['max_drawdown'])
            except Exception:
                errors += 1

            # 進度
            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(self._symbols)}] processing...")

        if len(sharpes) < 5:
            print("有效數據不足。")
            return None

        # 計算穩健性分數
        score = compute_robustness(sharpes, sortinos, ars, mdds)

        # 記錄提交
        entry = {
            'key': key,
            'strategy': strategy_name,
            'params': params,
            'freq': self.freq,
            'test_year': self.test_year,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'score': asdict(score),
        }
        self._submissions.append(entry)
        self._save_entry(entry)

        # 輸出（只有聚合分數）
        print(f"\n{'─'*40}")
        print(score.summary())
        print(f"{'─'*40}")
        print(f"  剩餘提交次數: {self.remaining_submissions}")
        print()

        return score

    def leaderboard(self) -> str:
        """顯示所有提交的排行榜。"""
        if not self._submissions:
            return "尚無提交記錄。"

        rows = []
        for s in self._submissions:
            sc = s['score']
            rows.append({
                'strategy': s['strategy'],
                'params': str(s['params']),
                'median_sharpe': sc['median_sharpe'],
                'pct_positive': sc['pct_positive'],
                'composite': sc['composite'],
            })

        # 排序
        rows.sort(key=lambda r: r['composite'], reverse=True)

        lines = [
            f"\n{'='*70}",
            f" BLACK BOX LEADERBOARD ({len(rows)} submissions)",
            f"{'='*70}",
            f" {'#':<3} {'Strategy':<28} {'Med.Sharpe':>10} {'%Pos':>7} {'Score':>8}",
            f" {'─'*3} {'─'*28} {'─'*10} {'─'*7} {'─'*8}",
        ]
        for i, r in enumerate(rows, 1):
            lines.append(
                f" {i:<3} {r['strategy']:<28} "
                f"{r['median_sharpe']:>10.3f} "
                f"{r['pct_positive']:>6.1%} "
                f"{r['composite']:>8.3f}"
            )
        lines.append(f"{'='*70}\n")
        return '\n'.join(lines)
