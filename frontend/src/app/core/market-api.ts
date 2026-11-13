import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Bias, GlobalMarkets, Health, Intraday, OpeningRange, Overview, Prediction, Quote, Vwap } from './models';

@Injectable({ providedIn: 'root' })
export class MarketApi {
  private readonly http = inject(HttpClient);

  overview() {
    return this.http.get<Overview>('/api/v1/market/overview');
  }

  gift() {
    return this.http.get<{ quote: Quote; session_name: string }>('/api/v1/market/gift-nifty');
  }

  globals() {
    return this.http.get<GlobalMarkets>('/api/v1/market/global-indices');
  }

  latest() {
    return this.http.get<{ predictions: Prediction[] }>('/api/v1/predictions/latest');
  }

  intraday(instrument: string) {
    const params = new HttpParams().set('instrument', instrument).set('interval', '1m');
    return this.http.get<Intraday>('/api/v1/market/intraday', { params });
  }

  openingRange(instrument: string) {
    return this.http.get<OpeningRange>('/api/v1/market/opening-range', {
      params: new HttpParams().set('instrument', instrument),
    });
  }

  vwap(instrument: string) {
    return this.http.get<Vwap>('/api/v1/market/vwap', {
      params: new HttpParams().set('instrument', instrument),
    });
  }

  bias() {
    return this.http.get<Bias>('/api/v1/market/bias');
  }

  health() {
    return this.http.get<Health>('/api/v1/health');
  }
}
