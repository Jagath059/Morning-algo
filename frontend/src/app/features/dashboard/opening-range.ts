import { Component, input } from '@angular/core';
import { OpeningRange } from '../../core/models';

@Component({
  selector: 'app-opening-range',
  template: `
    <article class="card">
      <header><h2>{{ title() }} opening range</h2></header>
      <dl class="stack">
        <div>
          <dt>5-minute high / low</dt>
          <dd>{{ range().range_5m.high ?? '—' }} / {{ range().range_5m.low ?? '—' }}</dd>
          @if (range().range_5m.status !== 'ok') {
            <p class="reason">{{ range().range_5m.reason }}</p>
          }
        </div>
        <div>
          <dt>15-minute high / low</dt>
          <dd>{{ range().range_15m.high ?? '—' }} / {{ range().range_15m.low ?? '—' }}</dd>
          @if (range().range_15m.status !== 'ok') {
            <p class="reason">{{ range().range_15m.reason }}</p>
          }
        </div>
      </dl>
    </article>
  `,
})
export class OpeningRangeComponent {
  readonly title = input.required<string>();
  readonly range = input.required<OpeningRange>();
}
