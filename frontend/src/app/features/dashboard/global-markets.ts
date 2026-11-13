import { Component, input } from '@angular/core';
import { GlobalMarkets } from '../../core/models';

@Component({
  selector: 'app-global-markets',
  template: `
    <article class="card">
      <header><h2>Global markets</h2></header>
      <ul class="index-list">
        @for (row of markets().indices; track row.id) {
          <li>
            <span>{{ row.name }}</span>
            <strong>{{ row.quote.value ?? '—' }}</strong>
            @if (row.quote.status !== 'ok') {
              <em>{{ row.quote.status }}</em>
            }
          </li>
        }
      </ul>
      <p class="reason">{{ markets().summary.text }}</p>
    </article>
  `,
})
export class GlobalMarketsComponent {
  readonly markets = input.required<GlobalMarkets>();
}
