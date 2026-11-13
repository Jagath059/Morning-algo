import { Component, computed, input } from '@angular/core';

const CHECKPOINTS = [
  { label: 'GIFT session 1', time: '05:15', start: 5 * 60 + 15 },
  { label: 'GIFT Nifty review', time: '08:00', start: 8 * 60 },
  { label: 'Global market review', time: '08:30', start: 8 * 60 + 30 },
  { label: 'NSE pre-open', time: '09:00', start: 9 * 60 },
  { label: 'Market open', time: '09:15', start: 9 * 60 + 15 },
  { label: 'Opening trend confirmation', time: '09:30', start: 9 * 60 + 30 },
];

@Component({
  selector: 'app-market-timeline',
  template: `
    <article class="card">
      <header><h2>Market timeline</h2></header>
      <ol class="timeline">
        @for (item of items(); track item.time) {
          <li [class.active]="item.active">
            <time>{{ item.time }}</time>
            <span>{{ item.label }}</span>
          </li>
        }
      </ol>
    </article>
  `,
})
export class MarketTimeline {
  readonly now = input(new Date());
  readonly items = computed(() => {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Kolkata',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(this.now());
    const hour = Number(parts.find((part) => part.type === 'hour')?.value ?? 0);
    const minute = Number(parts.find((part) => part.type === 'minute')?.value ?? 0);
    const minutes = hour * 60 + minute;
    const reached = CHECKPOINTS.filter((item) => item.start <= minutes);
    const active = reached.length ? reached[reached.length - 1].time : '';
    return CHECKPOINTS.map((item) => ({ ...item, active: item.time === active }));
  });
}
