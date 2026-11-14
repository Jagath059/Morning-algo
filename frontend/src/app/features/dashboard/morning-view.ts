import { GlobalMarkets, Overview, Prediction, Quote } from '../../core/models';

export interface Move {
  text: string;
  tone: 'up' | 'down' | 'flat' | 'none';
}

export interface IndexChip {
  name: string;
  move: Move;
}

export interface PlanStep {
  time: string;
  label: string;
  active: boolean;
}

export interface MorningBoard {
  sample: boolean;
  giftPrice: string;
  giftMove: Move;
  giftUpdated: string;
  niftyPrice: string;
  niftyMove: Move;
  niftyNote: string;
  sensexPrice: string;
  sensexMove: Move;
  sensexNote: string;
  headline: string;
  headlineTone: Move['tone'];
  scoreLabel: string;
  scoreValue: number | null;
  experimental: boolean;
  usClosed: IndexChip[];
  asiaLive: IndexChip[];
  giftTrend: Move;
  usImpact: string;
  asiaImpact: string;
  fii: string;
  callTone: 'preferred' | 'avoid' | 'wait';
  putTone: 'preferred' | 'avoid' | 'wait';
  checks: { label: string; on: boolean }[];
  insights: string[];
  plan: PlanStep[];
}

const PLAN = [
  { time: '8:00 AM', label: 'Check GIFT Nifty', start: 8 * 60 },
  { time: '8:30 AM', label: 'Review US Markets', start: 8 * 60 + 30 },
  { time: '8:45 AM', label: 'Confirm GIFT Nifty Trend', start: 8 * 60 + 45 },
  { time: '9:00 AM', label: 'Watch NSE Pre-Open', start: 9 * 60 },
  { time: '9:10 AM', label: 'Check Indicative Opening', start: 9 * 60 + 10 },
  { time: '9:15 AM', label: 'Market Opens – Confirm Trend', start: 9 * 60 + 15 },
];

export function planFor(minutes: number): PlanStep[] {
  const reached = PLAN.filter((step) => step.start <= minutes);
  const active = reached.length ? reached[reached.length - 1].time : '';
  return PLAN.map((step) => ({ time: step.time, label: step.label, active: step.time === active }));
}

export function istMinutes(now: Date): number {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(now);
  const hour = Number(parts.find((part) => part.type === 'hour')?.value ?? 0);
  const minute = Number(parts.find((part) => part.type === 'minute')?.value ?? 0);
  return hour * 60 + minute;
}

function money(value: string | null | undefined): string {
  if (value == null || value === '') {
    return '—';
  }
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return '—';
  }
  return amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function moveFrom(change: number | null, percent: number | null, suffix = ''): Move {
  if (change == null || Number.isNaN(change)) {
    return { text: '—', tone: 'none' };
  }
  const tone = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
  const arrow = tone === 'up' ? '▲' : tone === 'down' ? '▼' : '•';
  const sign = change > 0 ? '+' : '';
  const pct = percent == null || Number.isNaN(percent) ? '' : ` (${percent > 0 ? '+' : ''}${percent.toFixed(2)}%)`;
  return { text: `${arrow} ${sign}${change.toFixed(2)}${suffix}${pct}`, tone };
}

function quoteMove(quote: Quote | undefined, points = false): Move {
  if (!quote || (quote.status !== 'ok' && quote.status !== 'stale')) {
    return { text: '—', tone: 'none' };
  }
  const change = quote.change == null ? null : Number(quote.change);
  const percent = quote.change_percent == null ? null : Number(quote.change_percent);
  return moveFrom(change, percent, points ? ' pts' : '');
}

function indexChip(markets: GlobalMarkets | null, id: string, name: string): IndexChip {
  const row = markets?.indices.find((item) => item.id === id);
  return { name, move: quoteMove(row?.quote) };
}

function impact(chips: IndexChip[]): string {
  const tones = chips.map((chip) => chip.move.tone).filter((tone) => tone === 'up' || tone === 'down');
  if (!tones.length) {
    return 'Unavailable';
  }
  if (tones.every((tone) => tone === 'up')) {
    return 'Positive';
  }
  if (tones.every((tone) => tone === 'down')) {
    return 'Negative';
  }
  return 'Mixed';
}

export function liveBoard(input: {
  overview: Overview | null;
  markets: GlobalMarkets | null;
  prediction: Prediction | null;
  now: Date;
}): MorningBoard {
  const gift = input.overview?.gift_nifty;
  const nifty = input.overview?.nifty50.indicative_open;
  const sensex = input.overview?.sensex.indicative_open;
  const prediction = input.prediction;
  const direction = prediction?.direction ?? 'UNKNOWN';
  const score = prediction && direction !== 'UNKNOWN' ? Math.round(Number(prediction.confidence) * 100) : null;
  const us = [
    indexChip(input.markets, 'nasdaq', 'Nasdaq'),
    indexChip(input.markets, 'djia', 'Dow Jones'),
    indexChip(input.markets, 'spx', 'S&P 500'),
  ];
  const asia = [indexChip(input.markets, 'nikkei225', 'Nikkei 225'), indexChip(input.markets, 'hangseng', 'Hang Seng')];
  const usImpact = impact(us);
  const asiaImpact = impact(asia);
  const giftUp = gift?.status === 'ok' && Number(gift.change) > 0;
  const headline =
    direction === 'GREEN' ? 'Likely GREEN opening' : direction === 'RED' ? 'Likely RED opening' : direction === 'FLAT' ? 'Likely FLAT opening' : 'Awaiting inputs';
  const callTone = direction === 'GREEN' ? 'preferred' : direction === 'RED' ? 'avoid' : 'wait';
  const putTone = direction === 'RED' ? 'preferred' : direction === 'GREEN' ? 'avoid' : 'wait';
  const insights = [
    gift?.status === 'ok' ? `GIFT Nifty change is ${quoteMove(gift).text}.` : 'GIFT Nifty is not available from a licensed feed.',
    usImpact === 'Unavailable' ? 'US cash close is not available.' : `US market read is ${usImpact.toLowerCase()}.`,
    asiaImpact === 'Unavailable' ? 'Asian quotes are not available.' : `Asian market read is ${asiaImpact.toLowerCase()}.`,
    direction === 'UNKNOWN'
      ? 'The experimental score needs at least one fresh input.'
      : `Experimental heuristic leans ${direction}. This is not a validated probability.`,
    'CE and PE stay labels. This screen does not place orders.',
  ];
  return {
    sample: false,
    giftPrice: gift?.status === 'ok' || gift?.status === 'stale' ? money(gift.value) : '—',
    giftMove: quoteMove(gift),
    giftUpdated: gift?.status === 'ok' ? 'Quote loaded' : (gift?.reason ?? 'Feed not configured'),
    niftyPrice: nifty?.status === 'ok' ? money(nifty.value) : '—',
    niftyMove: quoteMove(nifty),
    niftyNote: nifty?.status === 'ok' ? 'Licensed indicative' : (nifty?.reason ?? 'Indicative open unavailable'),
    sensexPrice: sensex?.status === 'ok' ? money(sensex.value) : '—',
    sensexMove: quoteMove(sensex),
    sensexNote: sensex?.status === 'ok' ? 'Licensed indicative' : (sensex?.reason ?? 'Indicative open unavailable'),
    headline,
    headlineTone: direction === 'GREEN' ? 'up' : direction === 'RED' ? 'down' : direction === 'FLAT' ? 'flat' : 'none',
    scoreLabel: score == null ? 'No score yet' : 'Experimental score',
    scoreValue: score,
    experimental: prediction?.score_kind !== 'calibrated_probability',
    usClosed: us,
    asiaLive: asia,
    giftTrend: gift?.status === 'ok' ? quoteMove(gift, true) : { text: 'Unavailable', tone: 'none' },
    usImpact,
    asiaImpact,
    fii: 'Not in feed',
    callTone,
    putTone,
    checks: [
      { label: 'GIFT Nifty up', on: giftUp },
      { label: 'US markets positive', on: usImpact === 'Positive' },
      { label: 'Asian markets positive', on: asiaImpact === 'Positive' },
      { label: 'Pre-open momentum', on: direction === 'GREEN' },
    ],
    insights,
    plan: planFor(istMinutes(input.now)),
  };
}

export function sampleBoard(now: Date): MorningBoard {
  const up = (text: string): Move => ({ text, tone: 'up' });
  return {
    sample: true,
    giftPrice: '25,645.50',
    giftMove: up('▲ +72.00 (+0.28%)'),
    giftUpdated: 'Sample stamp 8:52 AM IST',
    niftyPrice: '25,642.10',
    niftyMove: up('▲ +68.40 (+0.27%)'),
    niftyNote: 'Sample pre-open window 9:00 – 9:15 AM',
    sensexPrice: '84,044.20',
    sensexMove: up('▲ +221.80 (+0.26%)'),
    sensexNote: 'Sample pre-open window 9:00 – 9:15 AM',
    headline: 'Likely GREEN opening',
    headlineTone: 'up',
    scoreLabel: 'Illustrative score',
    scoreValue: 78,
    experimental: true,
    usClosed: [
      { name: 'Nasdaq', move: up('+1.21%') },
      { name: 'Dow Jones', move: up('+0.69%') },
      { name: 'S&P 500', move: up('+0.72%') },
    ],
    asiaLive: [
      { name: 'Nikkei 225', move: up('+1.03%') },
      { name: 'Hang Seng', move: up('+0.65%') },
    ],
    giftTrend: up('▲ +72.00 pts'),
    usImpact: 'Positive',
    asiaImpact: 'Positive',
    fii: 'Sample only',
    callTone: 'preferred',
    putTone: 'avoid',
    checks: [
      { label: 'GIFT Nifty up', on: true },
      { label: 'US markets positive', on: true },
      { label: 'Asian markets positive', on: true },
      { label: 'Pre-open momentum', on: true },
    ],
    insights: [
      'Sample: GIFT Nifty is +72 pts in this layout.',
      'Sample: US and Asian marks are green in this layout.',
      'Illustrative score is 78. It is not a live or validated probability.',
      'CE is a label in the sample. It is not an order.',
    ],
    plan: planFor(istMinutes(now)),
  };
}
