import { Component, ElementRef, effect, input, viewChild } from '@angular/core';
import { Candle } from '../../core/models';

@Component({
  selector: 'app-market-chart',
  template: `
    <article class="card chart-card">
      <header><h2>{{ title() }}</h2></header>
      @if (candles().length === 0) {
        <p class="reason">{{ reason() || 'Candles are unavailable.' }}</p>
      }
      <div #host class="chart-host"></div>
    </article>
  `,
})
export class MarketChart {
  readonly title = input.required<string>();
  readonly candles = input<Candle[]>([]);
  readonly reason = input<string | null>(null);
  private readonly host = viewChild<ElementRef<HTMLDivElement>>('host');

  constructor() {
    effect(() => {
      const element = this.host()?.nativeElement;
      const rows = this.candles();
      if (!element || rows.length === 0) {
        if (element) {
          element.replaceChildren();
        }
        return;
      }
      void this.draw(element, rows);
    });
  }

  private async draw(element: HTMLDivElement, rows: Candle[]): Promise<void> {
    const { createChart, CandlestickSeries, ColorType } = await import('lightweight-charts');
    element.replaceChildren();
    const chart = createChart(element, {
      height: 220,
      layout: { background: { type: ColorType.Solid, color: '#1a2332' }, textColor: '#e7ecf3' },
      grid: { vertLines: { color: '#243044' }, horzLines: { color: '#243044' } },
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    const series = chart.addSeries(CandlestickSeries);
    series.setData(
      rows.map((candle) => ({
        time: Math.floor(new Date(candle.time).getTime() / 1000) as never,
        open: Number(candle.open),
        high: Number(candle.high),
        low: Number(candle.low),
        close: Number(candle.close),
      })),
    );
    chart.timeScale().fitContent();
  }
}
