import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatChipsModule } from '@angular/material/chips';
import { MatToolbarModule } from '@angular/material/toolbar';
import { forkJoin, interval } from 'rxjs';
import { MarketApi } from '../../core/market-api';
import { Bias, GlobalMarkets, Intraday, OpeningRange, Overview, Prediction, Vwap } from '../../core/models';
import { DataSourceStatus } from './data-source-status';
import { GiftNiftyCard } from './gift-nifty-card';
import { GlobalMarketsComponent } from './global-markets';
import { IntradayBias } from './intraday-bias';
import { MarketChart } from './market-chart';
import { MarketOverview } from './market-overview';
import { MarketTimeline } from './market-timeline';
import { NiftyPredictionCard } from './nifty-prediction-card';
import { OpeningRangeComponent } from './opening-range';
import { SensexPredictionCard } from './sensex-prediction-card';
import { VwapIndicator } from './vwap-indicator';

const SESSION_LABELS: Record<string, string> = {
  pre_gift_review: 'Before GIFT review',
  gift_monitoring: 'GIFT monitoring',
  global_review: 'Global review',
  nse_preopen: 'NSE pre-open',
  opening_drive: 'Opening drive',
  cash_session: 'Cash session',
  closed: 'Cash session closed',
  weekend: 'Weekend',
};

@Component({
  selector: 'app-dashboard',
  imports: [
    DatePipe,
    MatToolbarModule,
    MatChipsModule,
    GiftNiftyCard,
    NiftyPredictionCard,
    SensexPredictionCard,
    MarketOverview,
    GlobalMarketsComponent,
    IntradayBias,
    MarketChart,
    OpeningRangeComponent,
    VwapIndicator,
    MarketTimeline,
    DataSourceStatus,
  ],
  templateUrl: './dashboard.html',
})
export class Dashboard {
  private readonly api = inject(MarketApi);
  private readonly destroyRef = inject(DestroyRef);
  private socket: WebSocket | null = null;

  readonly now = signal(new Date());
  readonly clock = signal(this.formatClock(new Date()));
  readonly connection = signal('connecting');
  readonly loadError = signal<string | null>(null);
  readonly overview = signal<Overview | null>(null);
  readonly giftSession = signal('closed');
  readonly globals = signal<GlobalMarkets | null>(null);
  readonly niftyPrediction = signal<Prediction | null>(null);
  readonly sensexPrediction = signal<Prediction | null>(null);
  readonly bias = signal<Bias | null>(null);
  readonly niftyIntraday = signal<Intraday | null>(null);
  readonly sensexIntraday = signal<Intraday | null>(null);
  readonly niftyRange = signal<OpeningRange | null>(null);
  readonly sensexRange = signal<OpeningRange | null>(null);
  readonly niftyVwap = signal<Vwap | null>(null);
  readonly sensexVwap = signal<Vwap | null>(null);
  readonly sources = signal<{ name: string; status: string }[]>([]);

  constructor() {
    const timer = setInterval(() => {
      const current = new Date();
      this.now.set(current);
      this.clock.set(this.formatClock(current));
    }, 1000);
    this.destroyRef.onDestroy(() => {
      clearInterval(timer);
      this.socket?.close();
    });
    this.load();
    interval(30000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.load());
    this.connect();
  }

  sessionLabel(status: string): string {
    return SESSION_LABELS[status] ?? status;
  }

  private formatClock(current: Date): string {
    return new Intl.DateTimeFormat('en-IN', {
      timeZone: 'Asia/Kolkata',
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hourCycle: 'h23',
    }).format(current);
  }

  private load(): void {
    forkJoin({
      overview: this.api.overview(),
      gift: this.api.gift(),
      globals: this.api.globals(),
      latest: this.api.latest(),
      bias: this.api.bias(),
      niftyIntraday: this.api.intraday('NIFTY50'),
      sensexIntraday: this.api.intraday('SENSEX'),
      niftyRange: this.api.openingRange('NIFTY50'),
      sensexRange: this.api.openingRange('SENSEX'),
      niftyVwap: this.api.vwap('NIFTY50'),
      sensexVwap: this.api.vwap('SENSEX'),
      health: this.api.health(),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.loadError.set(null);
          this.overview.set(data.overview);
          this.giftSession.set(data.gift.session_name);
          this.globals.set(data.globals);
          this.niftyPrediction.set(data.latest.predictions.find((row) => row.instrument === 'NIFTY50') ?? null);
          this.sensexPrediction.set(data.latest.predictions.find((row) => row.instrument === 'SENSEX') ?? null);
          this.bias.set(data.bias);
          this.niftyIntraday.set(data.niftyIntraday);
          this.sensexIntraday.set(data.sensexIntraday);
          this.niftyRange.set(data.niftyRange);
          this.sensexRange.set(data.sensexRange);
          this.niftyVwap.set(data.niftyVwap);
          this.sensexVwap.set(data.sensexVwap);
          this.sources.set([
            { name: 'Kite', status: data.health.checks['kite'] ?? 'unknown' },
            { name: 'GIFT Nifty', status: data.health.checks['gift_nifty'] ?? 'unknown' },
            { name: 'Global indices', status: data.health.checks['global_indices'] ?? 'unknown' },
            { name: 'Firestore', status: data.health.checks['firestore'] ?? 'unknown' },
          ]);
        },
        error: (error: HttpErrorResponse) => {
          this.loadError.set(error.message || 'The market API is not reachable.');
        },
      });
  }

  private connect(): void {
    if (typeof WebSocket === 'undefined') {
      this.connection.set('disconnected');
      return;
    }
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    try {
      const socket = new WebSocket(`${protocol}://${location.host}/ws/market`);
      this.socket = socket;
      socket.onopen = () => {
        this.connection.set('connected');
        socket.send(JSON.stringify({ type: 'auth', token: 'local-dev' }));
      };
      socket.onclose = () => this.connection.set('disconnected');
      socket.onerror = () => this.connection.set('disconnected');
      socket.onmessage = (event) => {
        const message = JSON.parse(String(event.data)) as {
          type?: string;
          overview?: Overview;
          prediction?: { predictions: Prediction[] };
          bias?: Bias;
        };
        if (message.type !== 'snapshot') {
          return;
        }
        if (message.overview) {
          this.overview.set(message.overview);
        }
        if (message.prediction) {
          this.niftyPrediction.set(message.prediction.predictions.find((row) => row.instrument === 'NIFTY50') ?? null);
          this.sensexPrediction.set(message.prediction.predictions.find((row) => row.instrument === 'SENSEX') ?? null);
        }
        if (message.bias) {
          this.bias.set(message.bias);
        }
      };
    } catch {
      this.connection.set('disconnected');
    }
  }
}
