import { Component, input } from '@angular/core';
import { Prediction } from '../../core/models';
import { SentimentScore } from './sentiment-score';

@Component({
  selector: 'app-nifty-prediction-card',
  imports: [SentimentScore],
  template: `
    <article class="card">
      <header><h2>Nifty 50</h2></header>
      @if (prediction(); as row) {
        <app-sentiment-score [prediction]="row" />
      } @else {
        <p class="reason">Prediction is not available yet.</p>
      }
    </article>
  `,
})
export class NiftyPredictionCard {
  readonly prediction = input<Prediction | null>(null);
}
