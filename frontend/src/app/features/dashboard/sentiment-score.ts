import { DatePipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { Prediction } from '../../core/models';

@Component({
  selector: 'app-sentiment-score',
  imports: [DatePipe],
  template: `
    <div class="score" [attr.data-direction]="prediction().direction">
      <p class="direction">{{ prediction().direction }}</p>
      @if (prediction().score_kind === 'experimental_heuristic') {
        <p class="badge">Experimental</p>
        <p class="disclaimer">Experimental heuristic score. This is not a statistically validated probability.</p>
      }
      <dl>
        <div><dt>Gap-up score</dt><dd>{{ prediction().gap_up_score ?? '—' }}</dd></div>
        <div><dt>Gap-down score</dt><dd>{{ prediction().gap_down_score ?? '—' }}</dd></div>
        <div><dt>Flat score</dt><dd>{{ prediction().flat_score ?? '—' }}</dd></div>
        <div><dt>Confidence</dt><dd>{{ prediction().confidence }}</dd></div>
      </dl>
      <p class="meta">Calculated {{ prediction().created_at | date: 'HH:mm:ss' : '+0530' }} IST · {{ prediction().model_version }}</p>
    </div>
  `,
})
export class SentimentScore {
  readonly prediction = input.required<Prediction>();
}
