import { Component, input } from '@angular/core';
import { InstrumentOverview } from '../../core/models';

@Component({
  selector: 'app-market-overview',
  template: `
    <article class="card">
      <header><h2>{{ title() }}</h2></header>
      <dl class="stack">
        <div>
          <dt>Previous close</dt>
          <dd>{{ overview().previous_close.value ?? '—' }}</dd>
          @if (overview().previous_close.status !== 'ok') {
            <p class="reason">{{ overview().previous_close.reason }}</p>
          }
        </div>
        <div>
          <dt>Indicative pre-open</dt>
          <dd>{{ overview().indicative_open.value ?? '—' }}</dd>
          <p class="reason">{{ overview().indicative_open.reason }}</p>
        </div>
        <div>
          <dt>Official open</dt>
          <dd>{{ overview().official_open.value ?? '—' }}</dd>
          <p class="reason">{{ overview().official_open.reason }}</p>
        </div>
      </dl>
    </article>
  `,
})
export class MarketOverview {
  readonly title = input.required<string>();
  readonly overview = input.required<InstrumentOverview>();
}
