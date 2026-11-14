import { Component, input } from '@angular/core';
import { Quote } from '../../core/models';

@Component({
  selector: 'app-gift-nifty-card',
  template: `
    <article class="card">
      <header>
        <h2>GIFT Nifty</h2>
        <span class="chip">{{ sessionName() }}</span>
      </header>
      <p class="price">{{ quote().value ?? '—' }}</p>
      <p class="change">{{ quote().change ?? '—' }} ({{ quote().change_percent ?? '—' }})</p>
      @if (quote().status !== 'ok') {
        <p class="reason">{{ quote().reason }}</p>
      }
      @if (quote().status === 'stale') {
        <p class="badge stale">Stale</p>
      }
    </article>
  `,
})
export class GiftNiftyCard {
  readonly quote = input.required<Quote>();
  readonly sessionName = input('closed');
}
