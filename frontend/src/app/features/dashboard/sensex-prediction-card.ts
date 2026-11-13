import { Component, input } from '@angular/core';
import { Prediction } from '../../core/models';
import { SentimentScore } from './sentiment-score';

@Component({
  selector: 'app-sensex-prediction-card',
  imports: [SentimentScore],
  template: `
    <article class="card">
      <header><h2>Sensex</h2></header>
      @if (prediction(); as row) {
        <app-sentiment-score [prediction]="row" />
        <p class="reason">Sensex uses the shared morning score until a Sensex-specific pre-open quote exists.</p>
      } @else {
        <p class="reason">Prediction is not available yet.</p>
      }
    </article>
  `,
})
export class SensexPredictionCard {
  readonly prediction = input<Prediction | null>(null);
}
