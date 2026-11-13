import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Quote } from '../../core/models';
import { Dashboard } from './dashboard';
import { GiftNiftyCard } from './gift-nifty-card';
import { IntradayBias } from './intraday-bias';
import { MarketTimeline } from './market-timeline';
import { SentimentScore } from './sentiment-score';

const blank = (reason: string): Quote => ({ status: 'unavailable', value: null, reason });

describe('SentimentScore', () => {
  it('labels an experimental heuristic score', () => {
    const fixture = TestBed.createComponent(SentimentScore);
    fixture.componentRef.setInput('prediction', {
      prediction_id: '1',
      trading_date: '2026-11-13',
      instrument: 'NIFTY50',
      direction: 'UNKNOWN',
      gap_up_score: null,
      gap_down_score: null,
      flat_score: null,
      score_kind: 'experimental_heuristic',
      calibrated: false,
      confidence: '0.00',
      model_version: 'heuristic-1',
      data_quality: 'none',
      explanation: [],
      created_at: '2026-11-13T02:00:00Z',
    });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Experimental');
    expect(text).toContain('not a statistically validated probability');
  });
});

describe('GiftNiftyCard', () => {
  it('leaves the price blank and shows the reason', () => {
    const fixture = TestBed.createComponent(GiftNiftyCard);
    fixture.componentRef.setInput('quote', blank('GIFT_NIFTY_BASE_URL is not set.'));
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('—');
    expect(text).toContain('GIFT_NIFTY_BASE_URL is not set.');
    expect(text).not.toMatch(/\d{4,}/);
  });
});

describe('MarketTimeline', () => {
  it('highlights NSE pre-open at 09:07 IST', () => {
    const fixture = TestBed.createComponent(MarketTimeline);
    fixture.componentRef.setInput('now', new Date('2026-11-13T03:37:00Z'));
    fixture.detectChanges();
    const active = (fixture.nativeElement as HTMLElement).querySelector('.active');
    expect(active?.textContent).toContain('NSE pre-open');
  });
});

describe('IntradayBias', () => {
  it('shows the risk warning and no order control', () => {
    const fixture = TestBed.createComponent(IntradayBias);
    fixture.componentRef.setInput('bias', {
      trend: 'neutral',
      options_bias: 'WAIT',
      rule_id: 'or15_vwap_v1',
      explanation: 'Before 09:15 IST the options label stays WAIT.',
      risk_warning: 'This application does not place orders.',
      as_of: '2026-11-13T02:00:00Z',
    });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('does not place orders');
    expect(text).not.toMatch(/Buy|Sell|Place order/);
  });
});

describe('Dashboard', () => {
  let fixture: ComponentFixture<Dashboard>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Dashboard],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    fixture = TestBed.createComponent(Dashboard);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    flushDashboard(http);
    fixture.detectChanges();
  });

  afterEach(() => {
    fixture.destroy();
  });

  it('renders the TradingEngineAI wordmark', () => {
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('TradingEngineAI');
  });
});

function flushDashboard(http: HttpTestingController): void {
  const overview = {
    trading_date: '2026-11-13',
    as_of: '2026-11-13T02:00:00Z',
    session_status: 'gift_monitoring',
    auth_mode: 'local-development',
    gift_nifty: blank('GIFT_NIFTY_BASE_URL is not set.'),
    nifty50: {
      previous_close: blank('Kite is not configured.'),
      indicative_open: { ...blank('No licensed indicative feed is configured.'), kind: 'unavailable' },
      official_open: blank('Cash session has not published an open.'),
    },
    sensex: {
      previous_close: blank('Kite is not configured.'),
      indicative_open: { ...blank('No licensed indicative feed is configured.'), kind: 'unavailable' },
      official_open: blank('Cash session has not published an open.'),
    },
  };
  http.expectOne('/api/v1/market/overview').flush(overview);
  http.expectOne('/api/v1/market/gift-nifty').flush({ quote: overview.gift_nifty, session_name: 'session_1' });
  http.expectOne('/api/v1/market/global-indices').flush({
    as_of: overview.as_of,
    indices: [],
    summary: { text: 'Unavailable', score_kind: 'descriptive', inputs_used: [] },
  });
  http.expectOne('/api/v1/predictions/latest').flush({ predictions: [] });
  http.expectOne('/api/v1/market/bias').flush({
    trend: 'neutral',
    options_bias: 'WAIT',
    rule_id: 'or15_vwap_v1',
    explanation: 'Before 09:15 IST the options label stays WAIT.',
    risk_warning: 'This application does not place orders.',
    as_of: overview.as_of,
  });
  http.match((request) => request.url.startsWith('/api/v1/market/intraday')).forEach((request) =>
    request.flush({ instrument: 'NIFTY50', interval: '1m', trading_date: '2026-11-13', candles: [], status: 'unavailable', reason: 'Kite is not configured.' }),
  );
  http.match((request) => request.url.startsWith('/api/v1/market/opening-range')).forEach((request) =>
    request.flush({
      instrument: 'NIFTY50',
      range_5m: { status: 'unavailable', high: null, low: null, reason: 'Kite is not configured.' },
      range_15m: { status: 'unavailable', high: null, low: null, reason: 'Kite is not configured.' },
    }),
  );
  http.match((request) => request.url.startsWith('/api/v1/market/vwap')).forEach((request) =>
    request.flush({ instrument: 'NIFTY50', status: 'unavailable', value: null, reason: 'Kite is not configured.' }),
  );
  http.expectOne('/api/v1/health').flush({
    checks: { kite: 'unconfigured', gift_nifty: 'unconfigured', global_indices: 'unconfigured', firestore: 'unconfigured' },
    time: overview.as_of,
  });
}
