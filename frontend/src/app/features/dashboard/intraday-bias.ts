import { Component, input } from '@angular/core';
import { Bias } from '../../core/models';

@Component({
  selector: 'app-intraday-bias',
  template: `
    <article class="card bias">
      <header>
        <h2>Trading bias</h2>
        <span class="chip">{{ bias().options_bias }}</span>
      </header>
      <p class="direction">{{ bias().trend }}</p>
      <p>{{ bias().explanation }}</p>
      <p class="meta">{{ bias().rule_id }}</p>
      <p class="warning">{{ bias().risk_warning }}</p>
    </article>
  `,
})
export class IntradayBias {
  readonly bias = input.required<Bias>();
}
