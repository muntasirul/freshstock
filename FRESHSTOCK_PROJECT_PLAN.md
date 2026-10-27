# FreshStock: Project Plan

An AI inventory planning application for small food retailers.

**Purpose:** Build a GitHub portfolio project that demonstrates AI/ML engineering, data analysis, and software engineering through a working product.

**Document status:** Implementation plan. Features and results described below are planned, not completed.

**Recommended first release:** One demonstration store, 20 to 50 products, daily purchasing recommendations, an inventory simulator, and a web dashboard.

**Planning estimate:** About 10 to 14 weeks at 12 to 15 focused hours per week, assuming familiarity with Python and basic web development. Adjust after completing the data and forecasting milestones.

---

## 1. Problem and intended outcome

A small retailer must decide how much stock to order before knowing future demand. Excess stock can expire. Insufficient stock creates missed sales.

FreshStock will combine demand forecasts with inventory records and business assumptions to recommend daily order quantities.

The application should answer:

- What should I order today, and when will it arrive?
- Which products may run out before their next delivery?
- Which batches may expire before they sell?
- How do delivery delays or different shelf lives change the recommendation?

The initial project will demonstrate an evaluated planning method using historical sales and simulated inventory. It will not establish real-world waste reduction without a retailer pilot.

### Portfolio evidence

| Role | Evidence the project should provide |
| --- | --- |
| AI/ML engineer | Reproducible training, time-aware features, probabilistic forecasts, baseline comparisons, saved model artifacts, and scheduled inference |
| Data analyst | SQL analysis, documented data quality checks, dashboards, cost analysis, and a written interpretation of results |
| Software engineer | A working API and frontend, database transactions, background jobs, authentication, automated checks, and deployment |

## 2. Product scope

### First release

- One store with a curated set of products.
- Sales CSV imports with row-level validation.
- Product settings for lead time and shelf life.
- Batch-level inventory records and an append-only movement history.
- Daily point forecasts and cumulative demand quantiles.
- Purchasing recommendations with explanations.
- Purchase-order drafts that a user can accept or edit.
- A historical simulation comparing ordering policies.
- A dashboard for sales, inventory risk, and simulation results.
- A scenario planner for delivery delays and cost assumptions.
- An authenticated owner account and a separate demonstration mode.

### Later extensions

- Multiple stores with isolated accounts.
- Supplier integrations and purchase-order export.
- A retailer pilot with observed expiry and inventory data.
- Delivery calendars, minimum order quantities, and case-pack rounding.
- Weather features if a suitable dataset and clear forecasting benefit exist.
- Model monitoring and feedback from accepted recommendations.

### Explicit exclusions from the first release

- Automatic supplier purchases or payments.
- Training a language model from scratch.
- Dynamic pricing, route optimization, or reinforcement learning.
- Forecasts that promise actual availability or guaranteed savings.

These features can wait until the core forecasting and inventory workflow is reliable.

## 3. Data strategy and limitations

### Starting dataset

Use the M5 forecasting dataset, restricted to food products.

Sources:

- Official competition guide: https://raw.githubusercontent.com/Mcompetitions/M5-methods/master/M5-Competitors-Guide.pdf
- Dataset download page: https://www.kaggle.com/competitions/m5-forecasting-accuracy/data
- Dataset mirror: https://zenodo.org/records/12636070

Review the applicable dataset terms before downloading or redistributing files. Keep raw data out of Git and provide acquisition instructions.

Expected files:

| File | Use |
| --- | --- |
| `sales_train_validation.csv` | Historical product-store unit sales |
| `calendar.csv` | Dates, calendar attributes, and event information |
| `sell_prices.csv` | Historical weekly selling prices |
| `sales_train_evaluation.csv` | Optional later extension containing a longer, overlapping sales history |

Use `sales_train_validation.csv` for the first experiment. Do not concatenate it with `sales_train_evaluation.csv`; their histories overlap.

### What the data supports

The dataset supports sales forecasting and experiments with ordering policies.

It does not provide a complete record of actual inventory, expiry dates, procurement costs, or lost demand. Food-category products also do not all have the short shelf lives of fresh bakery goods.

Therefore:

- Treat observed unit sales as a demand proxy for simulation.
- Explain that actual demand may exceed recorded sales during stockouts.
- Represent shelf life and lead time as scenario assumptions.
- Label procurement and disposal costs as assumed values.
- Do not interpret simulated waste as measured historical waste.
- Use a partner retailer's data to validate the fresh-food use case later.

### Product selection

1. Choose one store.
2. Filter to food-category products.
3. Establish chronological data boundaries.
4. Select 20 to 50 products using training-period statistics only.
5. Include a mixture of regular demand and intermittent demand.
6. Save the selected identifiers in a versioned configuration file.

Avoid selecting products because they perform well on the final test period.

### Scenario configuration

Store assumptions in YAML or database records rather than hard-coding them.

Required settings:

- Shelf life after arrival, in whole days.
- Supplier lead time, in whole days.
- Review interval, initially one day.
- Acquisition cost per unit.
- Holding cost per unit per day.
- Disposal cost per expired unit.
- Lost-sale penalty per unmet unit.
- Initial stock policy and simulation warm-up length.

Use multiple shelf-life scenarios, including a longer-life scenario. Short-life settings on M5 data are hypothetical stress tests.

## 4. Architecture and technology

### Recommended stack

| Layer | Choice | Purpose |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite | Dashboard and operational workflows |
| API | FastAPI and Pydantic | Validation and application endpoints |
| Database | PostgreSQL | Sales, inventory, users, and results |
| Database access | SQLAlchemy and Alembic | Transactions and schema migrations |
| Analysis | pandas, SQL, and notebooks | Exploration and reporting |
| Modeling | LightGBM and scikit-learn | Forecast training and baselines |
| Experiment tracking | MLflow locally | Parameters, metrics, and artifacts |
| Background processing | Celery with Redis | Imports, forecasts, and simulations |
| Charts | Recharts | Frontend visualization |
| Packaging | Docker and Docker Compose | Repeatable local execution |
| Automated checks | GitHub Actions | Tests, linting, and build checks |

Start with synchronous command-line jobs. Add the worker queue when connecting long-running work to the application.

### Data flow

```text
Historical CSV files / user imports
                  |
                  v
        Validation and normalization
                  |
                  v
              PostgreSQL
                  |
          +-------+--------+
          |                |
          v                v
   Feature pipeline   Inventory ledger
          |                |
          v                |
   Training / inference    |
          |                |
          +-------+--------+
                  |
                  v
       Recommendation policy
                  |
          +-------+--------+
          |                |
          v                v
   Simulation runner   FastAPI endpoints
                           |
                           v
                    React application
```

Store model artifacts on disk initially, outside Git. Use object storage if the deployment requires persistent shared artifacts.

### Proposed repository layout

```text
freshstock/
  README.md
  LICENSE
  .env.example
  .gitignore
  compose.yaml
  Makefile
  pyproject.toml
  apps/
    api/
      app/
        main.py
        routes/
        services/
        models/
        schemas/
      migrations/
    web/
      src/
        pages/
        components/
        api/
  src/
    freshstock/
      data/
      features/
      forecasting/
      inventory/
      simulation/
      jobs/
  configs/
    data.yaml
    model.yaml
    scenarios.yaml
  data/
    raw/
    processed/
  artifacts/
  notebooks/
  sql/
  tests/
    unit/
    integration/
    e2e/
  reports/
    figures/
    evaluation.md
  docs/
    architecture.md
    data_dictionary.md
    model_card.md
    assumptions.md
    demo_script.md
  .github/
    workflows/
      ci.yaml
```

Ignore raw data, generated artifacts, secrets, and local database volumes. Commit small synthetic fixtures for automated tests.

## 5. Database and API design

### Main tables

| Table | Important fields and behavior |
| --- | --- |
| `stores` | Store identifier and timezone |
| `users` | Account identity, hashed password, and store membership |
| `products` | Product identifier, store identifier, and planning settings |
| `sales_daily` | Product, date, quantity, and source import |
| `inventory_batches` | Product, received date, expiry date, and batch identity |
| `inventory_movements` | Batch, signed quantity, reason, timestamp, and idempotency key |
| `purchase_orders` | Store, status, expected arrival, and creator |
| `purchase_order_items` | Product, quantity, and assumed or quoted unit cost |
| `import_jobs` | File hash, status, validation summary, and error report |
| `model_versions` | Artifact location, data cutoff, configuration, and metrics |
| `forecast_runs` | Store, forecast origin, model version, and run status |
| `forecast_values` | Product, horizon, forecast type, quantile, and value |
| `recommendations` | Forecast run, inventory snapshot, quantity, and explanation |
| `simulation_runs` | Policy, scenario, time range, configuration hash, and results |

Database constraints should prevent duplicate sales rows for the same store, product, and day.

For the first import contract, require daily product aggregates. A repeated identical import is a no-op; conflicting values produce a reviewable error. Do not silently overwrite sales.

Treat inventory movements as the source of truth. Record corrections with adjustment entries. If balances are cached, update them in the same transaction and provide reconciliation checks.

### Initial API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/auth/login` | Start an authenticated session |
| `POST` | `/imports/sales` | Validate and queue a sales import |
| `GET` | `/jobs/{job_id}` | Retrieve progress and errors |
| `GET` | `/products` | List products and planning settings |
| `PATCH` | `/products/{product_id}` | Update allowed planning settings |
| `POST` | `/inventory/receipts` | Receive stock into a batch |
| `POST` | `/inventory/adjustments` | Record a stock correction |
| `GET` | `/inventory` | Retrieve current batch balances |
| `POST` | `/forecast-runs` | Request forecasts for an allowed origin |
| `GET` | `/forecast-runs/{run_id}` | Retrieve a forecast run |
| `GET` | `/recommendations` | Retrieve current recommendations |
| `POST` | `/purchase-orders` | Save a draft or approved order |
| `PATCH` | `/purchase-orders/{order_id}` | Apply allowed status transitions |
| `POST` | `/simulations` | Queue a scenario comparison |
| `GET` | `/simulations/{run_id}` | Retrieve simulation results |
| `GET` | `/dashboard/summary` | Retrieve dashboard aggregates |

Use explicit statuses for imports and background jobs. Use transactions and idempotency keys for stock receipts and order updates.

Scope access by the authenticated store. Add authorization tests even if the first demo contains only one store.

## 6. Step-by-step implementation

### Phase 1: Define the experiment and scaffold the repository

**Tasks**

1. Write a short problem statement and define the intended user.
2. Create the repository layout and dependency files.
3. Add formatting, linting, and a basic CI workflow.
4. Add `.env.example` and dataset acquisition instructions.
5. Define the initial product scope and business assumptions.
6. Create commands such as `make setup`, `make test`, and `make dev`.

**Deliverables:** Repository scaffold, README, assumptions document, and a working local environment.

**Complete when:** A fresh checkout can install dependencies and run the initial checks without private credentials or manual code edits.

### Phase 2: Build the data pipeline

**Tasks**

1. Download the dataset according to its terms.
2. Record file checksums and source information.
3. Reshape daily sales columns into rows.
4. Join calendar records by day identifier.
5. Join prices by product, store, and week.
6. Validate uniqueness and join cardinality.
7. Check missing prices and invalid quantities.
8. Save normalized data as Parquet for analysis and load application records into PostgreSQL.
9. Create the data dictionary.

**Important checks**

- Joining prices must not multiply sales rows.
- A missing price is not automatically a zero price.
- Zero sales are not automatically proof of zero demand.
- Store dates must follow one explicit local-date convention.

**Deliverables:** Repeatable preparation command, data quality report, and normalized tables.

**Complete when:** Re-running the pipeline produces the same records without duplicates.

### Phase 3: Perform exploratory analysis

**Tasks**

1. Establish train, validation, and test boundaries.
2. Use only training data for initial exploration and product selection.
3. Analyze daily and weekly sales patterns.
4. Identify products with frequent zero-sales days.
5. Compare demand variability between products.
6. Investigate event-related patterns without claiming causation.
7. Examine missing prices and gaps in product history.
8. Write SQL queries that will support dashboard summaries.

**Suggested analysis questions**

- Which products have the most predictable weekly patterns?
- Which products have intermittent demand?
- Does a seasonal baseline work better for some product groups?
- How sensitive are ordering costs to lead-time assumptions?

**Deliverables:** One focused notebook, reusable SQL, and a short report with charts.

**Complete when:** Product selection and the first modeling choices have documented reasons.

### Phase 4: Establish baselines and backtesting

**Prediction convention**

Make recommendations after the close of day `t`. Observed sales through day `t` are available. Predictions target future days only.

**Initial baselines**

- Same weekday last week.
- Mean of the previous four matching weekdays.

**Tasks**

1. Reserve the final 168 available days as the untouched test period.
2. Reserve the preceding 168 days for validation.
3. Use the earlier history for training, with at least one year of usable history.
4. Create several expanding-window validation folds.
5. Purge training origins whose future target windows cross a fold boundary.
6. Fit preprocessing inside each training fold.
7. Generate baseline predictions at each forecast origin.
8. Save product-level and aggregate metrics.

Select final settings using validation results. Refit on training plus validation data, then evaluate once on the held-out test period.

For the first release, keep model parameters fixed during the test period while allowing features to use observations available by each forecast origin. Evaluate periodic retraining later as a separate experiment.

**Deliverables:** Backtesting runner and baseline results.

**Complete when:** A test verifies that changing future sales cannot alter earlier features or predictions.

### Phase 5: Train the forecasting models

**Primary model**

Train one global LightGBM model across the selected products, with product identity and demand-history features.

Start with next-day prediction. Extend to direct predictions for horizons from one to seven days.

A direct model predicts a specified future horizon from observations available at the forecast origin. This avoids inserting unknown future sales into lag features.

**Candidate features**

- Sales on the latest observed day and earlier lags.
- Rolling means and variability over documented historical windows.
- Weekday and month of the target date.
- Product and department identifiers.
- Event information known at prediction time.
- Price information genuinely available at prediction time.

Historical future-week prices must not be treated as known future prices unless the application explicitly assumes a published price schedule. A safer initial choice is the latest known price.

**Probabilistic forecasting**

1. Define cumulative targets as total demand over the next `H` days.
2. Train quantile models for the supported protection horizons.
3. Begin with the 0.1, 0.5, 0.8, and 0.9 quantiles.
4. Validate calibration by horizon and product group.
5. Record and handle negative predictions and quantile crossing.
6. Save postprocessing rules with the model artifact.

Daily quantiles cannot simply be added and described as a calibrated quantile of cumulative demand. Train cumulative targets directly for the ordering calculation.

**Training workflow**

1. Build versioned features and targets.
2. Train a default model.
3. Compare it with the baselines.
4. Perform a small validation-only parameter search.
5. Inspect errors by demand pattern and horizon.
6. Save the selected model with feature schema and training cutoff.
7. Register parameters, metrics, and artifacts in MLflow.
8. Create a model card describing intended use and limitations.

**Deliverables:** Training command, reproducible artifacts, prediction interface, and model card.

**Complete when:** The model can be loaded outside its training notebook and evaluated using the same backtesting interface as the baselines.

If the model does not improve performance, investigate and document the result. Do not hide baseline wins.

### Phase 6: Implement the inventory simulator

Build the simulator before adding complex ordering logic.

**Fixed initial assumptions**

- Daily time steps.
- Whole-unit demand and orders.
- Deterministic supplier lead times of at least one day.
- Lost sales rather than backorders.
- Earliest-expiring eligible stock is sold first.
- No returns, substitutions, or supplier capacity limits.

**Daily event order**

1. Receive orders scheduled to arrive at the start of day `t`.
2. Remove stock whose expiry date is at or before day `t`.
3. Serve the day's demand from remaining batches.
4. Record unmet demand, holding costs, and closing inventory.
5. Generate forecasts using information available through day `t`.
6. Place orders that arrive at the start of day `t + lead_time`.

A batch arriving on day `t` with shelf life `S` receives expiry date `t + S`. It is usable on arrival day and expires before sales on its expiry date.

Use observed historical sales as the exogenous demand proxy for every policy. Keep the forecast input history identical across policies for the first experiment. Feeding each policy's simulated fulfilled sales back into its model would create a different, censored-demand experiment.

**Cost definition**

Report the components separately:

```text
Simulation cost =
    acquisition cost of sold and expired units
  + holding cost
  + disposal cost
  + lost-sale penalty
```

Reconcile consumed acquisition cost against receipts and opening/closing inventory valuation. Also show purchasing cash outflow separately. This prevents unsold terminal stock from being mistaken for consumed cost.

Define whether the lost-sale penalty represents missed margin or another business penalty. Avoid counting the same missed revenue twice.

**Inventory conservation check**

```text
Opening units + received units
  = fulfilled units + expired units + closing units
```

**Required tests**

- No demand.
- Demand greater than available stock.
- Stock expiring before the day's sales.
- An order arriving after an earlier stockout.
- Multiple batches with different expiry dates.
- No negative stock and no sale of expired stock.
- Correct accounting at the simulation boundary.
- A one-day lead-time order arriving on the next day.

Use a warm-up period to establish inventory and exclude warm-up metrics. Report terminal inventory and outstanding orders so end effects remain visible.

**Deliverables:** Deterministic simulator, event log, and hand-calculated test cases.

**Complete when:** Tiny scenarios match manual calculations exactly and conservation checks hold.

### Phase 7: Build and compare ordering policies

**Policies**

| Policy | Description |
| --- | --- |
| Historical baseline | Replenish toward an estimate based on recent matching weekdays |
| Point forecast policy | Replenish toward expected demand with a validation-tuned buffer |
| Quantile policy | Replenish toward a selected cumulative demand quantile |
| Shelf-life-aware quantile policy | Add an expiry-aware adjustment and ordering cap |

For the initial daily review convention, use protection horizon:

```text
H = lead_time + review_interval - 1
inventory_position = usable_on_hand + outstanding_order_units
order_quantity = max(0, target_stock - inventory_position)
```

With a daily review and one-day lead time, the protection horizon is one day. Test this timing with manual examples.

Round quantities to whole units. The basic inventory-position formula does not model the future expiry of every batch. Treat it as a starting policy.

For the shelf-life-aware version, use an explicit projection of existing batches and expected sales to discount stock likely to expire before use. Cap proposed purchases using expected sell-through before the incoming batch expires. Document that this is a heuristic and compare it with the simpler policy.

Choose the quantile and buffer on validation data. Do not tune them on the test period.

**Tasks**

1. Run every policy on identical demand and scenario assumptions.
2. Use identical starting conditions and accounting rules.
3. Compare costs, waste, and fill rate.
4. Repeat across plausible shelf lives and lead times.
5. Include products and scenarios where the AI policy loses.
6. Select a default policy based on validation evidence.

**Deliverables:** Recommendation service and policy comparison report.

**Complete when:** Every recommendation includes its model version, inventory snapshot, assumptions, and explanation.

### Phase 8: Build the backend and jobs

**Tasks**

1. Create database models and migrations.
2. Implement authentication using maintained security libraries.
3. Implement sales import validation and conflict handling.
4. Implement transactional stock receipts and adjustments.
5. Add forecast and recommendation endpoints.
6. Add purchase-order status transitions.
7. Move imports and simulations to background jobs.
8. Add retry-safe execution and visible failure states.
9. Add structured logs with job identifiers.
10. Generate API documentation and example requests.

Use secure cookies or a documented token approach. Keep secrets in environment variables. Apply file-size limits and reject unsupported upload formats.

Keep job retries idempotent: retrying a request must not receive stock twice or duplicate an approved order.

**Deliverables:** Running API, migrations, worker, and integration tests.

**Complete when:** API calls support the entire import-to-recommendation-to-order workflow.

### Phase 9: Build the frontend

**Pages**

| Page | Required behavior |
| --- | --- |
| Overview | Show inventory risk, recent demand, and last successful forecast |
| Products | Edit allowed planning settings |
| Imports | Upload data and inspect validation errors |
| Inventory | Inspect batches and record receipts or adjustments |
| Recommendations | Compare suggested quantities and create an order draft |
| Product detail | Show historical sales and forecast uncertainty |
| Scenario planner | Run assumptions through the historical simulator |
| Evaluation | Show baseline comparisons and known limitations |

**Tasks**

1. Build shared layout and API client.
2. Add loading, empty, and failed-request states.
3. Implement the import and correction workflow.
4. Add recommendation review and order editing.
5. Add charts with units and clear date ranges.
6. Add background-job progress and retry actions.
7. Add keyboard navigation and accessible form labels.
8. Test the complete workflow in a browser.

Show simulated results separately from observed sales. Display the last successful forecast time and make stale recommendations visible.

**Deliverables:** Usable web application and screenshots.

**Complete when:** Someone unfamiliar with the implementation can run the core workflow using the README and interface.

### Phase 10: Evaluate, deploy, and publish the portfolio

**Tasks**

1. Freeze model and policy choices.
2. Run the final held-out evaluation.
3. Write the analysis report, including failed cases.
4. Run automated checks and a browser smoke test.
5. Package services with Docker Compose.
6. Deploy a restricted demonstration application.
7. Add a resettable demo dataset or read-only demonstration mode.
8. Record a short walkthrough.
9. Complete the README and model card.
10. Write CV bullets using only measured outcomes.

A single-host deployment is sufficient. The main engineering evidence is that the application is reproducible and its workflows behave correctly.

**Deliverables:** Demonstration URL if hosting is available, tagged release, evaluation report, and video.

**Complete when:** A reviewer can understand the problem, reproduce a small experiment, and inspect the working product.

## 7. Evaluation specification

### Forecast metrics

| Metric | Purpose | Reporting rule |
| --- | --- | --- |
| MAE | Typical absolute unit error | Report per product and aggregate |
| WAPE | Error relative to total observed demand | Mark undefined when total demand is zero |
| Pinball loss | Quantile forecast quality | Report separately by quantile and horizon |
| Interval coverage | Whether uncertainty estimates match observations | Report coverage and interval width together |

Avoid relying on MAPE for products with zero demand.

Report error by demand pattern, not only one overall score. Define weighting explicitly so high-volume products do not silently dominate every conclusion.

### Inventory metrics

| Metric | Definition |
| --- | --- |
| Fill rate | Fulfilled demand divided by total demand |
| Expired units | Units removed because their shelf life ended |
| Waste rate | Expired units divided by opening units plus received units during the scored period |
| Stockout days | Days when at least one unit of demand is unfulfilled |
| Average inventory | Mean closing inventory over the scored period |
| Simulation cost | Sum of the documented cost components |
| Cost improvement | `(baseline_cost - policy_cost) / baseline_cost`, when baseline cost is positive |

Predefine a target fill rate and compare policies at similar service levels where possible. Lower costs caused only by failing to serve customers are not a useful result.

Use paired comparisons across the same product-days. If adding uncertainty intervals, use time blocks rather than treating consecutive days as independent observations.

### Software metrics

- Prediction time for the supported product set.
- API response latency for ordinary read endpoints.
- Time to complete a fixed-size import.
- Time to run a fixed-length simulation.

Record dataset size and hardware with timing results. Do not claim production scale from a small demo.

### Release success criteria

- Every policy has reproducible results.
- Data leakage checks pass.
- Inventory conservation and accounting tests pass.
- The application completes its core workflow.
- The analysis reports baseline wins and model wins honestly.
- Any CV performance claim can be traced to a saved run.

A project can still be technically strong if the trained model does not consistently beat the baseline. Explain the finding and choose the better default.

## 8. Scenario planner specification

The first scenario planner is a historical experiment, not a promise about future savings.

**Inputs**

- Product selection and historical date range.
- Shelf life and supplier lead time.
- Holding, disposal, and lost-sale costs.
- Ordering policy and supported quantile.

**Outputs**

- Cost comparison by policy.
- Waste and unmet demand.
- Inventory trajectory.
- Forecast uncertainty and assumptions used.

Only allow supported lead-time horizons. If a user requests a horizon that has no trained cumulative model, return a clear validation message or explicitly selected baseline fallback.

Keep fixed-demand scenarios separate from future extensions that change demand itself. A claimed promotion effect would require its own evidence.

## 9. Testing and reproducibility

### Essential automated checks

| Area | What to verify |
| --- | --- |
| Data | Duplicate handling, required columns, date parsing, and join cardinality |
| Features | No access to observations after the forecast origin |
| Models | Artifact loading, feature schema checks, and expected output shape |
| Simulator | Conservation, expiry timing, arrivals, and cost accounting |
| API | Store authorization, input validation, and transaction behavior |
| Jobs | Retry safety and recovery from failures |
| Frontend | Import, recommendation review, and order creation |

Focus tests on meaningful failure modes. Do not add tests that merely repeat implementation details.

### Reproducibility record

Each experiment should save:

- Code commit and dependency versions.
- Data checksum and selected product identifiers.
- Split dates and forecast-origin convention.
- Feature and model configuration.
- Scenario assumptions and policy settings.
- Random seeds and relevant runtime information.
- Metrics and predictions needed to reproduce the report.

### Target commands

These commands are intended interfaces to implement:

```bash
make setup
make prepare-data
make analyze
make train
make backtest
make simulate
make test
make dev
```

Provide a small synthetic demo mode that runs without downloading the full dataset. Label its charts as synthetic.

## 10. Suggested schedule

| Week | Main goal | Concrete output |
| --- | --- | --- |
| 1 | Scope and environment | Repository scaffold and assumptions |
| 2 | Data preparation | Clean data and quality report |
| 3 | Analysis and baselines | EDA report and backtesting runner |
| 4 | Point forecasts | Trained model and baseline comparison |
| 5 | Cumulative quantiles | Calibration report and saved artifacts |
| 6 | Inventory simulation | Tested simulator and accounting |
| 7 | Ordering policies | Policy comparison and recommendations |
| 8 | Backend | Database, API, and import workflow |
| 9 | Jobs and frontend | Working operational screens |
| 10 | Scenario planner | Interactive historical comparisons |
| 11 | Final evaluation | Held-out results and failure analysis |
| 12 | Deployment and presentation | Demo, README, and CV evidence |
| 13 and 14, if needed | Integration buffer | Resolve issues found during full workflow use |

If time becomes limited, preserve the evaluation and core workflow. Reduce product count, dashboard features, or deployment complexity.

## 11. Compute and practical requirements

### Skills to have or learn

- Python data manipulation and SQL joins.
- Time-series validation and regression metrics.
- HTTP APIs and relational database transactions.
- React forms, state management, and charting.

Learn advanced quantile evaluation while implementing that phase. Do not postpone the entire project until every topic is mastered.

### Hardware

A modern laptop should be sufficient for the scoped LightGBM experiments. A GPU is not required.

Read only the needed source columns and subset the product set early. The source files contain more products than the application needs.

### Services

- Git hosting for source and CI.
- Local PostgreSQL and Redis through Docker.
- Optional hosting for the demonstration.
- Optional object storage for deployed artifacts.

No paid language-model API is required. Check hosting prices when choosing a provider rather than building the plan around an assumed free tier.

## 12. Risks and responses

| Risk | Response |
| --- | --- |
| Observed sales hide unmet demand | State the proxy assumption and defer real demand claims to a pilot |
| M5 products are not all fresh goods | Use multiple shelf-life scenarios and describe short-life cases as hypothetical |
| Leakage creates misleading accuracy | Fix the forecast-origin convention and test future-data independence |
| Added quantile forecasts are miscalibrated | Train cumulative targets directly and measure coverage |
| Better forecasts produce worse orders | Evaluate ordering policies and costs independently |
| Simulation timing has off-by-one errors | Use hand-calculated arrival and expiry tests |
| Costs improve because service worsens | Report fill rate alongside cost and compare similar service levels |
| Final inventory distorts comparisons | Use warm-up, reconcile asset values, and report terminal inventory |
| Repeated jobs duplicate inventory | Use idempotency keys and database transactions |
| Scope grows too large | Keep one store and a small product set until the workflow works |

## 13. GitHub presentation

### README contents

1. One-sentence problem statement.
2. Screenshot or short demonstration video.
3. What the application does.
4. Main measured results, clearly labeled as simulation results.
5. Architecture diagram.
6. Setup and demo instructions.
7. Data sources and assumptions.
8. Training and evaluation commands.
9. Known limitations and future work.
10. Links to the model card and analysis report.

### Demonstration walkthrough

1. Open the store dashboard.
2. Import a sample sales file and inspect validation feedback.
3. View a product's forecast and inventory batches.
4. Review a recommended purchase quantity.
5. Edit the quantity and save an order draft.
6. Run a historical delivery-delay scenario.
7. Compare costs and fill rates against the baseline.
8. Show the evaluation report and explain one failure case.

### CV templates

Replace every placeholder with a measured result. Use only the bullets that match the work actually completed.

**AI/ML emphasis**

> Trained and deployed LightGBM demand forecasting models for [N] products, improving [metric] by [X%] against a seasonal baseline on a chronological holdout.

**Data analyst emphasis**

> Built a SQL-based inventory analysis dashboard and evaluated ordering policies, identifying [X%] simulated cost improvement at a [Y%] fill rate under documented assumptions.

**Software engineering emphasis**

> Developed a React and FastAPI inventory application with PostgreSQL, idempotent stock transactions, and asynchronous forecasting jobs; measured [latency or throughput] under [documented workload].

**Combined project description**

> FreshStock: Built a full-stack inventory planning application with probabilistic demand forecasting and a batch-level simulator, reducing simulated inventory costs by [X%] against [baseline] while maintaining [Y%] fill rate.

Do not describe the application as deployed if it runs only locally. Do not describe simulation savings as a retailer's actual savings.

## 14. Final completion checklist

- [ ] Dataset source and usage terms are documented.
- [ ] Data preparation is reproducible.
- [ ] Product selection uses training-period information.
- [ ] Baselines and chronological evaluation are implemented.
- [ ] The trained model has a versioned artifact and model card.
- [ ] Forecast uncertainty is evaluated.
- [ ] The inventory simulator passes conservation and timing tests.
- [ ] Cost assumptions and accounting are documented.
- [ ] Ordering policies are compared under identical conditions.
- [ ] The API and frontend complete the main workflow.
- [ ] Imports and stock updates are safe to retry.
- [ ] Authorization and important error paths are tested.
- [ ] The demonstration clearly labels simulated and synthetic data.
- [ ] CI and fresh-checkout setup work.
- [ ] README, analysis report, and demo walkthrough are complete.
- [ ] Every published performance claim links to a reproducible result.

## 15. First implementation session

Start with these actions:

1. Create the `freshstock` repository and the initial folder structure.
2. Add Python dependencies and a minimal CI workflow.
3. Acquire the M5 files and record their checksums.
4. Write a preparation script that selects one store's food products.
5. Establish split dates and select 20 products using training data.
6. Produce a sales chart and a seasonal baseline.

Finish this session with a reproducible data pipeline and a baseline result. The recommendation engine depends on those foundations.
