import { Component, input } from '@angular/core';
import { Vwap } from '../../core/models';

@Component({
  selector: 'app-vwap-indicator',
  template: `
    <article class="card">
      <header><h2>{{ title() }} VWAP</h2></header>
      <p class="price">{{ vwap().value ?? '—' }}</p>
      @if (vwap().status !== 'ok') {
        <p class="reason">{{ vwap().reason }}</p>
      }
    </article>
  `,
})
export class VwapIndicator {
  readonly title = input.required<string>();
  readonly vwap = input.required<Vwap>();
}
