export interface Quote {
  status: 'ok' | 'stale' | 'unavailable';
  value: string | null;
  previous_reference?: string | null;
  change?: string | null;
  change_percent?: string | null;
  as_of?: string | null;
  source?: string | null;
  reason?: string | null;
}

export interface IndicativeOpen extends Quote {
  kind: string;
}

export interface InstrumentOverview {
  previous_close: Quote;
  indicative_open: IndicativeOpen;
  official_open: Quote;
}

export interface Overview {
  trading_date: string;
  as_of: string;
  session_status: string;
  auth_mode: string;
  gift_nifty: Quote;
  nifty50: InstrumentOverview;
  sensex: InstrumentOverview;
}

export interface GlobalIndex {
  id: string;
  name: string;
  session_state: string;
  session_date: string | null;
  quote: Quote;
}

export interface GlobalMarkets {
  as_of: string;
  indices: GlobalIndex[];
  summary: { text: string; score_kind: string; inputs_used: string[] };
}

export interface Explanation {
  feature: string;
  contribution: string;
  note: string;
}

export interface Prediction {
  prediction_id: string;
  trading_date: string;
  instrument: string;
  direction: 'GREEN' | 'RED' | 'FLAT' | 'UNKNOWN';
  gap_up_score: string | null;
  gap_down_score: string | null;
  flat_score: string | null;
  score_kind: string;
  calibrated: boolean;
  confidence: string;
  model_version: string;
  data_quality: string;
  explanation: Explanation[];
  created_at: string;
}

export interface Candle {
  time: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface Intraday {
  instrument: string;
  interval: string;
  trading_date: string;
  candles: Candle[];
  status: string;
  reason: string | null;
}

export interface RangeWindow {
  status: string;
  high: string | null;
  low: string | null;
  reason: string | null;
}

export interface OpeningRange {
  instrument: string;
  range_5m: RangeWindow;
  range_15m: RangeWindow;
}

export interface Vwap {
  instrument: string;
  status: string;
  value: string | null;
  reason: string | null;
}

export interface Bias {
  trend: string;
  options_bias: string;
  rule_id: string;
  explanation: string;
  risk_warning: string;
  as_of: string;
}

export interface Health {
  checks: Record<string, string>;
  time: string;
}
