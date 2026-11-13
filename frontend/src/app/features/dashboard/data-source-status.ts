import { Component, input } from '@angular/core';

@Component({
  selector: 'app-data-source-status',
  template: `
    <article class="card">
      <header><h2>Data sources</h2></header>
      <ul class="index-list">
        @for (row of rows(); track row.name) {
          <li>
            <span>{{ row.name }}</span>
            <em>{{ row.status }}</em>
          </li>
        }
      </ul>
    </article>
  `,
})
export class DataSourceStatus {
  readonly rows = input.required<{ name: string; status: string }[]>();
}
